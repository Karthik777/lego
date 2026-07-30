'''Running a query against a store, one leg at a time.

litesearch already fuses FTS5 and vector search in `db.search()`, and for a script that
is the right shape: one call, one ranked list. A dashboard wants the opposite. The
question a reader has in front of a result list is *why is this here* — whether the
keyword index found it, whether the vector index found it, whether both did and that
agreement is what floated it — and a single fused list cannot answer it, because fusing
is exactly the step that throws the per-leg ranks away.

So the legs are run separately here and fused afterwards by `_fuse`, which is
`litesearch.rrf_merge` with the ranks kept instead of discarded. Same arithmetic, same
ordering; every hit additionally carries where each index put it, what each cost, and
what the other leg thought. `compare()` takes that one step further and runs all four
strategies over one query so the exact-versus-approximate trade can be read as a number
rather than assumed — an HNSW index that has drifted from its table looks exactly like a
working one until something measures its agreement with a brute-force scan.
'''
import re, time
import numpy as np
from fastcore.all import AttrDict, first
from lego.core import quick_lgr
from .cfg import cfg
from .data import table, np_dtype, get_conn
from .encode import check

__all__ = ['parse_q', 'run', 'compare', 'more_like', 'snippet', 'MODES']

info, error, warn = quick_lgr()

MODES = (('hybrid', 'Hybrid (RRF)'), ('fts', 'Keyword only'), ('vector', 'Vector only'))

# `path:lego/*` and `lang!:.py` — a key, an optional bang, a value or comma-list. The
# same shape kosha's SKILL.md teaches, so a query that works in an agent's search works
# in the box.
_TOK = re.compile(r'(-?)(\w+)(!?):("[^"]*"|\S+)')
_WORD = re.compile(r'[A-Za-z0-9_]{2,}')

def parse_q(q):
    'Split a raw query into its free text and its `key:value` filters.'
    fs = []
    for neg, key, bang, val in _TOK.findall(q or ''):
        fs.append(AttrDict(key=key, vals=[v for v in val.strip('"').split(',') if v],
                           neg=bool(neg), hard=bool(bang)))
    return AttrDict(text=_TOK.sub('', q or '').strip(), filters=fs)

def _col_or_json(st, key):
    'Where a filter key lives: a real column when the store has one, else inside `metadata`.'
    if any(c.name == key for c in st.cols): return f'[{key}]'
    return f"json_extract(metadata, '$.{key}')"

def _glob(v): return v.replace('*', '%').replace('?', '_')

def where_of(st, filters):
    'One WHERE clause and its bindings for a parsed filter list. Values never reach SQL as text.'
    parts, args = [], {}
    for i, f in enumerate(filters):
        col, ors = _col_or_json(st, f.key), []
        for j, v in enumerate(f.vals):
            p = f'_f{i}_{j}'
            if '*' in v or '?' in v: ors.append(f'{col} LIKE :{p}'); args[p] = _glob(v)
            else: ors.append(f'{col} = :{p}'); args[p] = v
        if not ors: continue
        clause = '(' + ' OR '.join(ors) + ')'
        parts.append(f'NOT {clause}' if f.neg else clause)
    return (' AND '.join(parts) if parts else None), args

def _fts_query(text, wide=True):
    'FTS5 syntax for the words the reader typed. litesearch\'s `pre` does the widening.'
    from litesearch.data import pre
    t = (text or '').strip()
    if not t: return None
    try: return pre(t, wide=wide, extract_kw=False) or None
    except Exception: return ' OR '.join(f'"{w}"' for w in _WORD.findall(t)) or None

def _timed(fn):
    t0 = time.perf_counter()
    try: rows, err = fn(), None
    except Exception as e:
        rows, err = [], f'{type(e).__name__}: {e}'
        warn(f'atlas: leg failed — {err}')
    return AttrDict(rows=rows, ms=(time.perf_counter() - t0) * 1000, err=err)

def _fts_leg(st, text, depth, wh, args, wide=True):
    fq = _fts_query(text, wide)
    if not fq or not st.fts: return AttrDict(rows=[], ms=0.0, err=None, q=fq, skipped=True)
    tbl = table(st)
    cols = ['rowid', 'content', 'metadata'] + st.extra
    def go():
        try: return tbl.fts_search(fq, cols, 'rank', depth, None, wh, args, quote=False)
        except Exception:
            # a query the reader typed is not required to be valid FTS5; quoting it turns
            # `foo(bar` from a syntax error into a search for those words
            return tbl.fts_search(text, cols, 'rank', depth, None, wh, args, quote=True)
    out = _timed(go)
    return AttrDict(out, q=fq, skipped=False)

def _ann_takes_where():
    'litesearch grew a WHERE clause on `ann_search` after 0.0.35; work with either.'
    from inspect import signature
    from apswutils.db import Table
    return 'where' in signature(Table.ann_search).parameters

def _ann(tbl, emb, cols, limit, wh, args, dt):
    '''An ANN search that filters, on the versions of litesearch that cannot.

    HNSW returns its neighbours before anything gets to say which rows were eligible, so
    a filter has to be applied afterwards either way. Where the installed litesearch does
    that itself, let it; where it does not, ask for a deeper slice and re-select the
    survivors, keeping the index's order — the alternative is a filtered ANN search that
    silently returns fewer rows than asked for, or none.'''
    if not wh: return tbl.ann_search(emb, cols, limit, dtype=dt)
    if _ann_takes_where(): return tbl.ann_search(emb, cols, limit, wh, args, dt)
    rows = tbl.ann_search(emb, cols, limit * 4, dtype=dt)
    if not rows: return rows
    ids = ','.join(str(int(r['rowid'])) for r in rows)
    ok = {r['rowid'] for r in tbl.db.q(f'select rowid as rowid from [{tbl.name}] where rowid in ({ids}) and {wh}', args)}
    return [r for r in rows if r['rowid'] in ok][:limit]

def _vec_leg(st, qvec, depth, wh, args, ann=False):
    tbl, dt = table(st), np_dtype(st)
    cols = ['rowid', 'content', 'metadata'] + st.extra
    emb = qvec.astype(dt).tobytes()
    if ann: fn = lambda: _ann(tbl, emb, cols, depth, wh, args, dt)
    else:   fn = lambda: tbl.vec_search(emb, cols, wh, args, 'embedding', 'cosine', dt, depth, None)
    out = _timed(fn)
    return AttrDict(out, skipped=False, ann=ann)

def _fuse(legs, k=60, limit=50):
    '''Reciprocal Rank Fusion over any number of ranked lists, keeping the ranks.

    Identical in outcome to `litesearch.rrf_merge` — a row scores `1/(k+rank)` per list it
    appears in, summed — but each survivor records the rank it held in every leg. That is
    what lets a result say "keyword #14, vector #2" instead of only "0.031", and it costs
    one dict per hit.'''
    out = {}
    for nm, rows in legs:
        for rank, r in enumerate(rows):
            rid = r.get('rowid')
            if rid is None: continue
            hit = out.get(rid)
            if hit is None: hit = out[rid] = AttrDict(r, _rrf=0.0, _ranks={}, rowid=rid)
            elif r.get('_dist') is not None and hit.get('_dist') is None: hit['_dist'] = r['_dist']
            # item assignment, not attribute: fastcore's AttrDict sends a name starting
            # with an underscore to the real attribute namespace, so `hit._rrf +=` would
            # accumulate somewhere the template never reads and leave the key at zero
            hit['_rrf'] += 1.0 / (k + rank)
            hit['_ranks'][nm] = rank + 1
    return sorted(out.values(), key=lambda h: -h['_rrf'])[:limit]

def run(st, q, enc, mode='hybrid', ann=False, k=None, limit=None, page=0, wide=True, rerank=False):
    '''One search. Returns the fused hits plus everything the page needs to explain them.

    `mode` picks which legs run; `ann` swaps the brute-force vector scan for the HNSW
    index. A leg that cannot run — no FTS index, no usable encoder, a stale ANN sidecar —
    is not an error and does not empty the result: it comes back with `skipped` and a
    reason, and the remaining leg answers the query on its own.'''
    k = min(max(int(k or cfg.rrf_k), 1), cfg.rrf_k_max)
    limit = min(int(limit or cfg.hits), cfg.max_hits)
    p = parse_q(q)
    wh, args = where_of(st, p.filters)
    gate = check(st, enc)
    depth = max(cfg.depth, limit * 2)
    want_v = mode in ('hybrid', 'vector') and gate.ok
    want_f = mode in ('hybrid', 'fts')
    use_ann = bool(ann and st.ann_ok)

    qvec, legs, t0 = None, [], time.perf_counter()
    if want_v and p.text:
        qvec = np.asarray(enc.query([p.text]))[0]
    fts = _fts_leg(st, p.text, depth, wh, args, wide) if want_f else AttrDict(rows=[], ms=0.0, err=None, skipped=True, q=None)
    vec = (_vec_leg(st, qvec, depth, wh, args, use_ann) if qvec is not None
           else AttrDict(rows=[], ms=0.0, err=None, skipped=True, ann=use_ann))
    if want_f and not fts.skipped: legs.append(('keyword', fts.rows))
    if not vec.skipped: legs.append(('vector', vec.rows))

    hits = _fuse(legs, k, (page + 1) * limit) if len(legs) > 1 else [
        AttrDict(r, _rrf=1.0 / (k + i), _ranks={legs[0][0]: i + 1}, rowid=r.get('rowid'))
        for i, r in enumerate(legs[0][1][:(page + 1) * limit])] if legs else []
    reranked, rr_err = False, None
    if rerank and hits:
        try:
            from litesearch import rerank_hits
            hits, reranked = rerank_hits(p.text, list(hits)), True
        except Exception as e:
            # flashrank fetches its cross-encoder on first use, so this is the one leg that
            # can fail on a machine where every other leg works. Say so on the page: a
            # ranking that quietly is not the ranking you asked for is the worse outcome
            rr_err = f'{type(e).__name__}: {e}'.split('\n')[0]
            warn(f'atlas: reranker unavailable: {e}')
    total_ms = (time.perf_counter() - t0) * 1000
    page_hits = hits[page * limit:(page + 1) * limit]
    for i, h in enumerate(page_hits): h['_pos'] = page * limit + i + 1
    return AttrDict(
        q=q, text=p.text, filters=p.filters, where=wh, mode=mode, k=k, limit=limit, page=page,
        hits=page_hits, n=len(hits), more=len(hits) > (page + 1) * limit,
        fts=fts, vec=vec, gate=gate, ann=use_ann, ann_asked=bool(ann), rerank=reranked,
        ms=total_ms, terms=_WORD.findall(p.text.lower()), qvec=qvec,
        why=_why(st, mode, gate, ann, use_ann, fts, vec, rr_err))

def _why(st, mode, gate, ann_asked, ann_used, fts, vec, rr_err=None):
    'Everything the reader needs told about legs that did not run the way they asked.'
    out = []
    if mode in ('hybrid', 'vector') and not gate.ok: out.append(f'Vector leg off — {gate.why}')
    elif gate.caveat: out.append(gate.caveat)
    if mode in ('hybrid', 'fts') and not st.fts: out.append('Keyword leg off — this store has no FTS5 index')
    if ann_asked and not ann_used:
        out.append('ANN off — ' + (st.ann_why or 'this store has no HNSW index registered'))
    if fts.get('err'): out.append(f'Keyword leg failed — {fts.err}')
    if vec.get('err'): out.append(f'Vector leg failed — {vec.err}')
    if rr_err: out.append(f'Not reranked — the flashrank cross-encoder did not load: {rr_err}')
    return out

# ── comparing strategies ──────────────────────────────────────────────────────

def _ids(rows, n): return [r['rowid'] for r in rows[:n]]

def _agree(a, b):
    'Overlap of two rankings at the same depth, as a fraction of the shorter one.'
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(1, min(len(sa), len(sb)))

def compare(st, q, enc, k=None, depth=None):
    '''Every strategy over one query, side by side.

    The number worth having is the last one: ANN agreement is the share of the exact
    top-k that the HNSW index also returned. HNSW is approximate by design, so anything
    from about 0.9 up is the trade working as intended — but a sidecar that was never
    rebuilt after an insert, or was built by reading the blobs at the wrong scalar width,
    scores near zero while still returning a confident-looking ranking. There is no other
    cheap way to notice that.'''
    k = min(max(int(k or cfg.rrf_k), 1), cfg.rrf_k_max)
    p = parse_q(q)
    wh, args = where_of(st, p.filters)
    gate, d = check(st, enc), depth or cfg.depth
    rows = []
    fts = _fts_leg(st, p.text, d, wh, args)
    if not fts.skipped: rows.append(AttrDict(nm='Keyword (FTS5)', leg=fts, ids=_ids(fts.rows, d)))
    exact = ann = None
    if gate.ok and p.text:
        qv = np.asarray(enc.query([p.text]))[0]
        exact = _vec_leg(st, qv, d, wh, args, ann=False)
        rows.append(AttrDict(nm='Vector (exact scan)', leg=exact, ids=_ids(exact.rows, d)))
        if st.ann_ok:
            ann = _vec_leg(st, qv, d, wh, args, ann=True)
            rows.append(AttrDict(nm='Vector (HNSW ANN)', leg=ann, ids=_ids(ann.rows, d)))
            if ann.err or not ann.rows: ann = None      # nothing to compare an empty leg against
        legs = [('keyword', fts.rows)] if not fts.skipped else []
        for nm, lg in (('vector', exact), ('vector', ann)):
            if lg is None or not lg.rows: continue
            fused = _fuse(legs + [(nm, lg.rows)], k, d)
            rows.append(AttrDict(nm=f'Hybrid RRF ({"ANN" if lg is ann else "exact"})',
                                 leg=AttrDict(ms=(fts.ms if not fts.skipped else 0) + lg.ms, err=None),
                                 ids=_ids(fused, d)))
    n = cfg.ann_recall_k
    agreement = (_agree(_ids(exact.rows, n), _ids(ann.rows, n)) if (exact and ann) else None)
    # overlap is read down a column, so every row has to be measured at the same depth as
    # every other — compared over whatever each leg happened to return, a leg that fetched
    # fewer rows scores higher for having fetched fewer rows
    base = rows[0].ids[:n] if rows else []
    for r in rows: r.overlap = _agree(base, r.ids[:n])
    return AttrDict(rows=rows, agreement=agreement, at=n, gate=gate, text=p.text, k=k, depth=d)

# ── neighbours ────────────────────────────────────────────────────────────────

def more_like(st, rowid, n=None):
    'The rows nearest this one in the store\'s own vector space — no query, no encoder.'
    n = n or cfg.nbrs
    db, dt = get_conn(st.db), np_dtype(st)
    r = first(db.q(f'select embedding from [{st.name}] where rowid = :r', dict(r=int(rowid))))
    if not r or not r['embedding']: return []
    cols = ['rowid', 'content', 'metadata'] + st.extra
    try: rows = table(st).vec_search(r['embedding'], cols, f'rowid != {int(rowid)}', None,
                                     'embedding', 'cosine', dt, n, None)
    except Exception as e:
        warn(f'atlas: neighbours failed — {e}')
        return []
    return rows

# ── presentation ──────────────────────────────────────────────────────────────

def snippet(text, terms, width=None):
    '''A window of the content centred on the first matched term, split into
    (text, is_term) runs so the caller can mark them without building HTML here.'''
    width = width or cfg.snippet
    t = (text or '').strip()
    if not terms: return [(t[:width] + ('…' if len(t) > width else ''), False)]
    pat = re.compile('|'.join(re.escape(w) for w in sorted(set(terms), key=len, reverse=True)), re.I)
    m = pat.search(t)
    st = max(0, m.start() - width // 3) if m else 0
    cut = t[st:st + width]
    out, i = [], 0
    if st: out.append(('…', False))
    for mm in pat.finditer(cut):
        if mm.start() > i: out.append((cut[i:mm.start()], False))
        out.append((mm.group(0), True)); i = mm.end()
    out.append((cut[i:] + ('…' if st + width < len(t) else ''), False))
    return [(s, h) for s, h in out if s]
