import json
from urllib.parse import urlencode, quote
from fastcore.xml import *
from fasthtml.common import *
from fastcore.all import timed_cache, AttrDict
from lego.core import lc_icon, ButtonT, asset_js, asset_css, cfg as core_cfg
from .cfg import Routes, cfg
from .data import dbs, facets
from .encode import ENCODERS, encoder_for, get_encoder
from .search import MODES, snippet
from . import cluster as cl

__all__ = ['atlas_head', 'index_view', 'store_view', 'doc_view', 'legs_view', 'score_badge', 'proj_payload']

@timed_cache(seconds=3600)
def atlas_head():
    from pathlib import Path
    here = Path(__file__).parent
    return [asset_css(here / 'atlas.css'), asset_js(here / 'atlas.js', defer=True)]

def wrap(*c): return Div(*c, cls='atlas-wrap')

def alink(*c, href, **kw):
    '''Unboosted, for the reason the dashboards block gives: on a non-2xx, hx-boost fires
    an error event and does nothing at all, which looks exactly like a dead link. These
    pages also carry their own <script>, which only a real navigation runs.'''
    return A(*c, href=href, hx_boost='false', **kw)

def crumbs(*parts):
    out = []
    for i, (txt, href) in enumerate(parts):
        if i: out.append(Span('/', cls='sep'))
        out.append(alink(txt, href=href) if href else Span(txt))
    return Div(*out, cls='crumbs')

def _n(v, d=0):
    if v is None: return '—'
    return f'{v:,.{d}f}' if isinstance(v, float) else f'{v:,}'

def _fmt(k, v):
    '''A metadata value as something to read.

    Only one rule, because only one is earned: litesearch\'s parsers write the file\'s
    mtime into `uploaded_at`, and 1785446242.88 is a number nobody can check against
    anything. Everything else is shown as the store wrote it.'''
    if k.endswith('_at') and isinstance(v, (int, float)) and 1e8 < v < 4e9:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(v, timezone.utc).strftime('%Y-%m-%d %H:%M')
    return str(v)

def _url(path, **kw):
    q = urlencode({k: v for k, v in kw.items() if v not in (None, '', False)})
    return path + (f'?{q}' if q else '')

def store_url(st, **kw): return _url(Routes.store.format(db=st.db, store=quote(st.name)), **kw)
def doc_url(st, i, **kw): return _url(Routes.doc.format(db=st.db, store=quote(st.name), id=i), **kw)

# ── badges ────────────────────────────────────────────────────────────────────

def chip(*c, cls='', **kw): return Span(*c, cls=f'chip {cls}', **kw)

def _vec_chips(st):
    'What the vectors in this store are, said in the same breath every time it is said.'
    out = [chip(f'{st.ndim}-d' if st.ndim else 'no vectors'),
           chip(st.dtype or '—', cls='ghost',
                title='scalar width the bytes decode at' + (' — inferred from the data' if st.dtype_guessed else ''))]
    if st.embedder: out.append(chip(st.embedder, cls='ghost', title='encoder that wrote these vectors'))
    out.append(chip('FTS5', cls='ok' if st.fts else 'off'))
    out.append(chip('ANN', cls='ok' if st.ann_ok else ('warn' if st.ann else 'off'),
                    title=st.ann_why or ('HNSW index in sync' if st.ann_ok else 'no HNSW index registered')))
    return out

def warnings(st):
    'The two failures that are invisible from a result list, said before the result list.'
    out = []
    if st.ndim and not st.dtype_agrees:
        out.append(f"The usearch registry records {st.ann['dtype']} vectors, but these bytes decode as "
                   f'{st.dtype}. Everything below reads them as {st.dtype}; anything that trusted the '
                   'registry — including the HNSW index — did not.')
    if st.ann and not st.ann_ok: out.append(f'ANN index unusable: {st.ann_why}')
    if st.ragged and st.embedded: out.append('Rows in this store hold vectors of different lengths — '
                                             'the ones that do not match the majority width are skipped.')
    if st.rows and not st.embedded: out.append('No row in this store has an embedding, so only keyword search can run.')
    elif st.embedded and st.embedded < st.rows:
        out.append(f'{_n(st.rows - st.embedded)} of {_n(st.rows)} rows have no embedding — '
                   'the vector leg cannot return them.')
    return [Div(lc_icon('triangle-alert', 14), Span(w), cls='note warn') for w in out]

# ── /atlas ────────────────────────────────────────────────────────────────────

def _store_card(st):
    return Div(
        Div(alink(H3(st.name, cls='m-0'), href=store_url(st)),
            Span(st.db_nm, cls='card-db'), cls='card-head'),
        P(f'{_n(st.rows)} rows · {_n(st.embedded)} embedded', cls='atlas-why'),
        Div(*_vec_chips(st), cls='chips'),
        Div(Span('measuring…', cls='atlas-why'), cls='score-slot',
            hx_get=_url(Routes.score.format(db=st.db, store=quote(st.name))), hx_trigger='load', hx_swap='innerHTML'),
        Form(Input(name='q', placeholder='search this store…', aria_label=f'Search {st.name}', cls='mini-q'),
             Button(lc_icon('search', 14), type='submit', cls=f'{ButtonT.default} {ButtonT.xs}'),
             method='get', action=store_url(st), cls='mini-form', hx_boost='false'),
        cls='store-card')

def index_view(sts):
    by_db = {}
    for s in sts: by_db.setdefault(s.db, []).append(s)
    enc = get_encoder()
    out = []
    for k, ss in by_db.items():
        d = dbs().get(k)
        out += [Div(H2(ss[0].db_nm, cls='m-0'), Code(str(d.path) if d else k, cls='path'), cls='db-head'),
                Div(*[_store_card(s) for s in ss], cls='store-grid')]
    if not sts:
        out = [Div(P('No litesearch stores found.', cls='atlas-why'),
                   P('The atlas opens every ', Code('.db'), ' under ', Code('data/db/atlas'),
                     ', anything in ', Code('ATLAS_DIRS'), ', and a ', Code('.kosha/'),
                     ' index in the working directory — and reads the tables in them that have a ',
                     Code('content'), ' and an ', Code('embedding'), ' column.', cls='atlas-why'), cls='empty')]
    return wrap(Div(crumbs(('Atlas', None)), cls='atlas-head'),
                H1('Embedding atlas', cls='m-0'),
                P('Every litesearch store this app can see: what is in it, how it clusters, '
                  'and one box to search it with.', cls='atlas-why mb-3'),
                _enc_bar(enc), *out)

def _enc_bar(enc):
    kind = {'model': 'ok', 'fallback': 'warn', 'broken': 'bad', 'missing': 'bad'}.get(enc.kind, 'off')
    msg = (enc.get('about') or '') if enc.kind in ('model', 'fallback') else (enc.err or '')
    extra = None
    if enc.kind == 'fallback':
        extra = ('Queries embed with hashed words and character trigrams — real vectors, no semantics. '
                 'Set ATLAS_EMBEDDER to one of: ' + ', '.join(k for k in ENCODERS if k != 'hash') + '.')
    if enc.kind in ('broken', 'missing'):
        extra = 'Vector search is off until a model loads. Keyword search is unaffected.'
    return Div(chip(f'query encoder · {enc.name}', cls=kind),
               Span(msg, cls='atlas-why'), Span(extra, cls='atlas-why') if extra else None, cls='enc-bar')

def score_badge(st):
    'The clustering headline for one card — loaded after the page, because it is a scan.'
    an = cl.analysis(st)
    if not an.ok: return Span(an.get('why') or 'not clusterable', cls='atlas-why')
    return Div(chip(f'{an.k} clusters'),
               chip(f'silhouette {an.sil:.2f}', cls=_sil_cls(an.sil), title=_sil_help(an.sil)),
               chip(f'PCA {an.ratio:.0%}', cls='ghost', title='variance the two drawn axes carry'),
               cls='chips')

def _sil_cls(s): return 'ok' if s >= 0.35 else 'warn' if s >= 0.15 else 'bad'

def _sil_help(s):
    if s >= 0.35: return 'clusters are well separated'
    if s >= 0.15: return 'clusters overlap — treat the grouping as a hint'
    return 'no real cluster structure; k-means split it anyway'

# ── the search form ───────────────────────────────────────────────────────────

def _opt(nm, sel, pairs, **kw):
    return Select(*[Option(l, value=v, selected=(str(v) == str(sel))) for v, l in pairs], name=nm, **kw)

def search_bar(st, res=None):
    r = res or AttrDict(q='', mode='hybrid', k=cfg.rrf_k, ann_asked=False, rerank=False)
    return Form(
        Div(Input(name='q', value=r.q or '', placeholder='Type anything — it gets embedded and matched both ways',
                  aria_label='Search', autofocus=True, cls='big-q'),
            Button(lc_icon('search', 16), Span('Search'), type='submit', cls=f'{ButtonT.primary}'), cls='q-row'),
        Div(Label('Legs', _opt('mode', r.mode, MODES, aria_label='Which legs run')),
            Label('RRF k', Input(name='k', type='number', min='1', max=str(cfg.rrf_k_max), value=str(r.k),
                                 aria_label='RRF k', cls='num',
                                 title='higher k flattens the contribution of rank, so agreement between '
                                       'the legs matters more than either leg\'s ordering')),
            Label(Input(type='checkbox', name='ann', value='1', checked=bool(r.ann_asked),
                        disabled=not st.ann_ok), Span('ANN'),
                  cls='check', title=st.ann_why or 'search the HNSW index instead of scanning every row'),
            Label(Input(type='checkbox', name='rerank', value='1', checked=bool(r.rerank)), Span('rerank'),
                  cls='check', title='reorder the fused hits with a flashrank cross-encoder'),
            cls='opt-row'),
        method='get', action=store_url(st), cls='search-bar', hx_boost='false')

def facet_bar(st, res):
    'The metadata keys this store actually has, as one-click query tokens.'
    ks, q = facets(st), (res.q if res else '')
    if not ks: return None
    out = []
    for k in ks[:6]:
        shown = k['top'][:cfg.facet_vals]
        vals = [alink(f'{v["v"]}', href=store_url(st, q=f'{q} {k["key"]}:{v["v"]}'.strip()), cls='facet-v',
                      title=f'{v["n"]} rows') for v in shown]
        if k['distinct'] > len(shown):
            vals.append(Span(f'+{k["distinct"] - len(shown)} more — type ', Code(f'{k["key"]}:…'), cls='atlas-why'))
        out.append(Div(Span(k['key'], cls='facet-k'), *vals, cls='facet'))
    return Div(Span('Filter', cls='facet-lbl'), Div(*out, cls='facets'), cls='facet-bar')

# ── results ───────────────────────────────────────────────────────────────────

def _meta(h):
    try: return json.loads(h.get('metadata') or '{}') or {}
    except (ValueError, TypeError): return {}

def _title(h, m):
    for k in ('title', 'name', 'path', 'source', 'url'):
        if m.get(k): return str(m[k])
    return f'row {h.get("rowid")}'

def _src_link(m):
    '''Where this chunk came from, as somewhere to click.

    A `url` in the metadata is already a link. A `path` is one only if it is inside the
    repo this app was built from and that repo is known — an absolute path out of
    somebody\'s site-packages is not something a browser can open, and a link that 404s
    on GitHub is worse than no link.'''
    if m.get('url'): return m['url'], 'source'
    p, repo = m.get('path'), core_cfg.github_repo
    if not (p and repo) or str(p).startswith('/') or '..' in str(p): return None, None
    ln = m.get('lineno')
    return f'https://github.com/{repo}/blob/main/{p}' + (f'#L{ln}' if ln else ''), 'github'

_META_SKIP = ('title', 'name', 'path', 'url', 'source')

def hit_card(st, h, res, an=None):
    m = _meta(h)
    cid = (an or {}).get('member', {}).get(h.get('rowid')) if an and an.get('ok') else None
    href, kind = _src_link(m)
    ranks = h.get('_ranks') or {}
    bits = [Span(f'{nm} #{r}', cls=f'rank {nm}') for nm, r in ranks.items()]
    if h.get('_dist') is not None: bits.append(Span(f'cos {h["_dist"]:.3f}', cls='rank dist',
                                                    title='cosine distance — 0 is identical'))
    bits.append(Span(f'rrf {h["_rrf"]:.4f}', cls='rank rrf') if h.get('_rrf') is not None else None)
    return Article(
        Div(Span(f'{h.get("_pos", "")}', cls='pos'),
            alink(_title(h, m), href=doc_url(st, h['rowid'], q=res.q), cls='hit-title'),
            Span(cl_dot(cid), an['clusters'][cid]['name'], cls='chip cluster') if cid is not None else None,
            *[chip(f'{k}:{m[k]}', cls='ghost') for k in ('lang', 'type', 'package') if m.get(k)],
            cls='hit-head'),
        P(*[Mark(s) if hit else Span(s) for s, hit in snippet(h.get('content'), res.terms)], cls='snip'),
        Div(*[b for b in bits if b],
            alink('more like this', href=doc_url(st, h['rowid']) + '#nbrs', cls='hit-more'),
            alink(kind, lc_icon('external-link', 12), href=href, target='_blank', rel='noopener',
                  cls='hit-more') if href else None,
            cls='hit-foot'),
        cls='hit')

def cl_dot(i): return Span(cls=f'dot c{(i or 0) % 8}')

def leg_tiles(res):
    'What each index did, in the units the reader can act on: rows, milliseconds.'
    def tile(lbl, rows, ms, sub=None, off=None):
        return Div(Div(lbl, cls='tile-label'),
                   Div(f'{_n(rows)}' if not off else '—', cls='tile-value'),
                   Div(off or (f'{ms:.0f} ms' + (f' · {sub}' if sub else '')), cls='tile-sub'), cls='tile')
    fts, vec = res.fts, res.vec
    return Div(tile('Keyword', len(fts.rows), fts.ms, f'FTS5 rank', 'not run' if fts.get('skipped') else None),
               tile('Vector', len(vec.rows), vec.ms, 'HNSW ANN' if res.ann else 'exact scan',
                    'not run' if vec.get('skipped') else None),
               tile('Fused', res.n, res.ms, f'RRF k={res.k}' + (' · reranked' if res.rerank else '')),
               cls='tile-grid')

def results_view(st, res, an):
    if not (res.q or '').strip():
        return Div(P('Nothing searched yet. The box embeds whatever you type and runs it through both '
                     'indexes at once; ', Code('key:value'), ' tokens filter on metadata before either '
                     'index sees the query.', cls='atlas-why'), cls='empty')
    if not res.hits:
        return Div(P(f'No rows matched “{res.text}”.', cls='atlas-why'),
                   *[Div(w, cls='note') for w in res.why], cls='empty')
    q = res.q
    pager = Div(
        alink('← Previous', href=store_url(st, q=q, mode=res.mode, k=res.k, ann=res.ann_asked and 1,
                                           rerank=res.rerank and 1, page=res.page - 1),
              cls=f'{ButtonT.default} {ButtonT.xs}') if res.page else None,
        alink('More →', href=store_url(st, q=q, mode=res.mode, k=res.k, ann=res.ann_asked and 1,
                                       rerank=res.rerank and 1, page=res.page + 1),
              cls=f'{ButtonT.default} {ButtonT.xs}') if res.more else None, cls='pager')
    return Div(leg_tiles(res),
               *[Div(lc_icon('info', 14), Span(w), cls='note') for w in res.why],
               Div(*[hit_card(st, h, res, an) for h in res.hits], cls='hits'), pager)

# ── the strategy comparison ───────────────────────────────────────────────────

def legs_view(st, cmp):
    if not cmp.rows: return Div(P('Nothing to compare — no leg ran.', cls='atlas-why'), cls='empty')
    head = Tr(Th('Strategy'), Th('Rows', cls='num'), Th('Time', cls='num'),
              Th(f'Agrees with {cmp.rows[0].nm}', cls='num'), Th('Top result'))
    body = []
    for r in cmp.rows:
        body.append(Tr(Td(r.nm), Td(_n(len(r.ids)), cls='num'),
                       Td(f'{r.leg.ms:.0f} ms', cls='num'),
                       Td(f'{r.overlap:.0%}', cls='num'),
                       Td(Code(str(r.ids[0]) if r.ids else '—'))))
    note = None
    if cmp.agreement is not None:
        cls = 'ok' if cmp.agreement >= 0.9 else 'warn' if cmp.agreement >= 0.6 else 'bad'
        note = Div(chip(f'ANN agreement {cmp.agreement:.0%} @{cmp.at}', cls=cls),
                   Span('share of the exact top-%d the HNSW index also returned. Approximate search '
                        'trades a few percent for speed; near zero means the sidecar no longer matches '
                        'the table it indexes.' % cmp.at, cls='atlas-why'), cls='note')
    return Div(note, Div(cls='tbl-scroll')(Table(cls='atlas-tbl')(Thead(head), Tbody(*body))))

# ── clusters and the projection ───────────────────────────────────────────────

def cluster_panel(st, an, res=None):
    if not an.ok:
        return Div(H2('Clusters', cls='mt-6 mb-2'), P(an.get('why') or 'not clusterable', cls='atlas-why'))
    qc = cl.assign(an, res.qvec) if (res and res.get('qvec') is not None) else None
    rows = [Tr(Td(Div(cl_dot(c['i']), Span(c['name']), cls='col-head')),
               Td(_n(c['n']), cls='num'),
               Td(f'{c["cohesion"]:.3f}', cls='num'),
               Td(f'{c["separation"]:.3f}', cls='num'),
               Td(an['clusters'][c['nearest']]['name'] if c['nearest'] != c['i'] else '—'),
               Td(Div(*[alink(f'#{i}', href=doc_url(st, i), cls='ex') for i in c['examples'][:4]], cls='exs')))
            for c in an.clusters]
    scores = Div(
        _score_tile('k', str(an.k), 'clusters chosen by silhouette'),
        _score_tile('Silhouette', f'{an.sil:.3f}', _sil_help(an.sil), _sil_cls(an.sil)),
        _score_tile('Davies–Bouldin', f'{an.db:.2f}', 'ratio of spread to separation — lower is better'),
        _score_tile('PCA variance', f'{an.ratio:.0%}', 'what the two drawn axes carry of the whole space',
                    'ok' if an.ratio >= 0.4 else 'warn'),
        _score_tile('Vectors', _n(an.n), 'sampled from the store' if an.sampled else 'every embedded row'),
        cls='tile-grid')
    tried = Div(Span('k tried: ', cls='atlas-why'),
                *[chip(f'{t["k"]}: {t["sil"]:.2f}', cls='ghost' if t['k'] != an.k else 'ok') for t in an.tried],
                cls='chips mt-2') if len(an.tried) > 1 else None
    return Div(H2('Clusters', cls='mt-6 mb-1'),
               P('k-means on the unit sphere — the same geometry the cosine distance in the store uses. '
                 'Cohesion is the mean similarity of a cluster to its own centre; separation is the '
                 'cosine distance to the nearest other centre.', cls='atlas-why mb-3'),
               scores, tried,
               Div(chip(cl_dot(qc.i), f'your query lands in “{qc.name}” (cos {1 - qc.sim:.3f})', cls='ok'),
                   cls='chips mt-3') if qc else None,
               Div(cls='tbl-scroll mt-3')(Table(cls='atlas-tbl')(
                   Thead(Tr(Th('Cluster'), Th('Rows', cls='num'), Th('Cohesion', cls='num'),
                            Th('Separation', cls='num'), Th('Nearest'), Th('Examples'))),
                   Tbody(*rows))))

def _score_tile(lbl, val, sub, cls=''):
    return Div(Div(lbl, cls='tile-label'), Div(val, cls=f'tile-value {cls}'), Div(sub, cls='tile-sub'), cls='tile')

def proj_payload(st, an):
    'The static half of the map: points, cluster names, and how much to trust the axes.'
    if not an.ok: return dict(ok=False, why=an.get('why') or 'no projection')
    return dict(ok=True, points=an.points, ratio=an.ratio, n=an.n,
                clusters=[dict(i=c['i'], name=c['name'], n=c['n']) for c in an.clusters],
                store=st.name, db=st.db, doc=Routes.doc.format(db=st.db, store=quote(st.name), id='__ID__'))

def projection(st, an, res=None):
    if not an.ok: return None
    hits = [h['rowid'] for h in (res.hits if res else [])]
    qxy = cl.project(an, res.qvec) if (res and res.get('qvec') is not None) else None
    src = Routes.proj.format(db=st.db, store=quote(st.name))
    return Div(
        Div(H2('Projection', cls='m-0'),
            chip(f'PCA · {an.ratio:.0%} of variance', cls='ok' if an.ratio >= 0.4 else 'warn',
                 title='two axes out of %d. Points far apart here really are far apart; points close '
                       'together may not be.' % (st.ndim or 0)), cls='panel-head'),
        P('Every embedded row, coloured by cluster. Search hits are ringed; the cross is where the '
          'query itself lands.' if hits else 'Every embedded row, coloured by cluster. Hover a point to '
          'read it, click to open it.', cls='atlas-why mb-2'),
        Div(Div('Loading…', cls='proj-skel'),
            Canvas(data_proj_src=src, data_hits=json.dumps(hits), data_q=json.dumps(qxy)),
            Div(cls='proj-tip'), cls='proj-box'),
        Div(cls='proj-legend'), cls='panel')

# ── /atlas/{db}/{store} ───────────────────────────────────────────────────────

def store_view(st, res, an):
    enc = encoder_for(st)
    head = Div(crumbs(('Atlas', Routes.index), (st.db_nm, None), (st.name, None)), cls='atlas-head')
    sub = f'{_n(st.rows)} rows · {_n(st.embedded)} embedded'
    compare = None
    if (res.q or '').strip():
        compare = Details(Summary('Compare strategies'),
                          Div(Div('Measuring…', cls='proj-skel'), cls='legs-body',
                              hx_get=_url(Routes.legs.format(db=st.db, store=quote(st.name)), q=res.q, k=res.k),
                              hx_trigger='toggle once from:closest details', hx_swap='innerHTML'),
                          cls='panel legs')
    return wrap(head, H1(st.name, cls='m-0'),
                P(sub, cls='atlas-why'), Div(*_vec_chips(st), cls='chips mb-3'),
                *warnings(st), _enc_bar(enc),
                search_bar(st, res), facet_bar(st, res),
                results_view(st, res, an),
                compare, projection(st, an, res), cluster_panel(st, an, res))

# ── /atlas/{db}/{store}/doc/{id} ──────────────────────────────────────────────

def doc_view(st, rowid, row, nbrs, an, back=''):
    m = _meta(row)
    href, kind = _src_link(m)
    cid = (an.get('member') or {}).get(rowid) if an.ok else None
    fields = [Div(Dt(k), Dd(_fmt(k, v)), cls='field') for k, v in sorted(m.items())]
    for c in st.extra: fields.append(Div(Dt(c), Dd(str(row.get(c))), cls='field'))
    return wrap(
        Div(crumbs(('Atlas', Routes.index), (st.db_nm, None),
                   (st.name, store_url(st, q=back)), (str(rowid), None)), cls='atlas-head'),
        H1(_title(row, m), cls='m-0'),
        Div(chip(f'row {rowid}', cls='ghost'),
            Span(cl_dot(cid), an['clusters'][cid]['name'], cls='chip cluster') if cid is not None else None,
            alink(kind, lc_icon('external-link', 12), href=href, target='_blank', rel='noopener',
                  cls='chip ghost') if href else None, cls='chips mb-3'),
        Div(Pre(Code(row.get('content') or '')), cls='doc-body'),
        Dl(*fields, cls='field-grid') if fields else None,
        H2('Nearest in this store', cls='mt-6 mb-1', id='nbrs'),
        P('Closest by cosine distance in the store\'s own vectors — no query, no encoder, so this works '
          'even when the model that wrote them is not installed here.', cls='atlas-why mb-2'),
        Div(*[Article(Div(Span(f'{n["_dist"]:.3f}', cls='pos'),
                          alink(_title(n, _meta(n)), href=doc_url(st, n['rowid']), cls='hit-title'),
                          cls='hit-head'),
                      P(*[Span(s) for s, _ in snippet(n.get('content'), [])], cls='snip'), cls='hit')
              for n in nbrs], cls='hits') if nbrs else P('No neighbours — this row has no vector.', cls='atlas-why'))
