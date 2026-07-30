'''Finding litesearch stores, and reading enough about them to search one safely.

The dashboards block is handed its databases: a fixed list, each with a packaged dump.
This one is pointed at directories instead, because the databases it is for are written
somewhere else — by a `kosha` sync, by an eval run, by a script that called
`db.get_store()` and went home. So the unit here is not "a database we shipped", it is
"a table that turned out to be a store": `content` + `embedding` + `metadata`, an FTS5
index kept in sync by triggers, and optionally a row in `usearch_indices` naming an HNSW
sidecar. Nothing else in those files is reachable — a directory that also holds an
application database exposes none of it, because none of its tables have that shape.

The one genuinely hard part is the **dtype**. A litesearch store keeps vectors as raw
bytes, and the width of the scalar those bytes decode to is not written down next to
them. `get_store(ann=True)` defaults its registry entry to `f16`, while `model2vec`
static embedders — what kosha indexes with — return `f32`. When those two disagree the
bytes still decode, into twice as many numbers of the wrong magnitude, and every
distance computed from them is arithmetic on noise. Nothing raises. So `_dtype` decodes
the same blob every way it could have been written and keeps the reading that looks like
an embedding, the registry's claim included only as a tie-breaker; `ann_ok` then says
whether the sidecar was built under that same reading. Both answers are shown on the
store page, because a silently wrong distance is the failure this block exists to make
visible.
'''
import json, threading, time
import numpy as np
from fastcore.all import AttrDict, Path, first
from lego.core import quick_lgr, cache, database
from .cfg import cfg

__all__ = ['dbs', 'stores', 'store', 'get_conn', 'table', 'vectors', 'facets', 'sample_rows',
           'record_embedder', 'seed_demo', 'STORE_COLS']

info, error, warn = quick_lgr()

STORE_COLS = ('content', 'embedding')   # what makes a table a store rather than a table
# Bump when `_describe` changes what it collects. The cache key is otherwise the file's
# mtime and size, which a change to this code does not move — so without it a rule that
# now finds different facets keeps serving the ones it found under the old rule.
_DESC_V = 1
_NP = {'i8': np.int8, 'f16': np.float16, 'f32': np.float32, 'f64': np.float64}
_SUF = {np.dtype(v): k for k, v in _NP.items()}

# ── where the databases are ───────────────────────────────────────────────────

def _dirs():
    '''Directories searched for litesearch databases.

    The seed directory always, whatever ATLAS_DIRS names, and — if this app is running
    inside a repo that has one — the kosha index sitting in `.kosha/`. That last one is
    the whole point of the block existing next to kosha: sync a repo, open /atlas, and
    the code search is already there with nothing configured.'''
    out = [cfg.seed_dir, *[Path(d).expanduser() for d in cfg.dirs]]
    for p in (Path('.kosha'), Path.home() / '.local/share/kosha'):
        if p.is_dir(): out.append(p)
    seen, uniq = set(), []
    for d in out:
        try: r = d.resolve()
        except OSError: continue
        if r not in seen and d.is_dir(): seen.add(r); uniq.append(d)
    return uniq

def _key(p, taken):
    'A URL-safe name for a database file, made unique by climbing its path when it collides.'
    k, up = p.stem, p.parent
    while k in taken and up.name: k, up = f'{up.name}-{k}', up.parent
    return k

def _files():
    return [f for d in _dirs() for f in sorted(Path(d).glob('*.db'))]

def _sig(p):
    'Cheap change detector: everything derived from a file is keyed on this.'
    try: s = p.stat(); return f'{s.st_mtime_ns}.{s.st_size}'
    except OSError: return '0.0'

# ── connections ───────────────────────────────────────────────────────────────
#
# One connection per database per thread, for the reason the dashboards block gives:
# starlette runs sync handlers on a threadpool, a store page fires several requests at
# once, and apsw will not run a cursor on a connection busy in another thread. Unlike
# that block these are opened *with* the usearch extension — `distance_cosine_f32` is
# the vector leg, so without it there is no vector leg.
_local = threading.local()
_reg_lock = threading.Lock()
_registry = AttrDict(sig=None, dbs=AttrDict())

def _scan():
    'The current set of database files, as {key: record}. Re-read when the directory changes.'
    files = _files()
    sig = '|'.join(f'{f}:{_sig(f)}' for f in files)
    if _registry.sig == sig: return _registry.dbs
    with _reg_lock:
        out, taken = AttrDict(), set()
        for f in files:
            k = _key(f, taken); taken.add(k)
            out[k] = AttrDict(key=k, path=f, nm=f.stem.replace('_', ' ').replace('-', ' ').title(), sig=_sig(f))
        _registry.dbs, _registry.sig = out, sig
    return out

def dbs():
    'Every database file the atlas can see, keyed by its URL name.'
    return _scan()

def get_conn(key):
    d = dbs().get(key)
    if d is None: raise KeyError(key)
    conns = getattr(_local, 'conns', None)
    if conns is None: conns = _local.conns = {}
    hit = conns.get(key)
    if hit and hit[0] == d.sig: return hit[1]
    conns[key] = (d.sig, database(d.path))
    return conns[key][1]

def table(st):
    'The fastlite Table behind a store record, on this thread.'
    return get_conn(st.db).t[st.name]

# ── what a store is ───────────────────────────────────────────────────────────

def _is_store(db, nm):
    if nm.startswith('sqlite_') or '_fts' in nm: return False
    try: cols = {c.name for c in db.t[nm].columns}
    except Exception: return False
    return all(c in cols for c in STORE_COLS)

def _ann_meta(db, nm):
    if 'usearch_indices' not in db.t: return None
    try: return first(db.t.usearch_indices(where=f'name={nm!r}'))
    except Exception: return None

def _plausible(buf, dt):
    '''How much a blob read at this width looks like an embedding.

    Real vectors are finite, bounded, and — for every encoder in this block — unit
    length. A float32 buffer read as float16 gives twice as many numbers, a good share of
    them inf, nan or wildly out of range, and a norm nowhere near one. So score on
    exactly that, and return -1 for a reading that cannot be right.'''
    if len(buf) % np.dtype(dt).itemsize: return -1.0
    v = np.frombuffer(buf, dtype=dt).astype(np.float32)
    if not v.size or not np.isfinite(v).all(): return -1.0
    n = float(np.linalg.norm(v))
    if not n or n > 1e4 or np.abs(v).max() > 1e3: return -1.0
    return 1.0 / (1.0 + abs(np.log(n)))   # 1.0 at unit norm, falling away either side

def _dtype(blobs, hint=None):
    'The scalar width these vectors were written at, and whether the registry agrees.'
    cands = ['f32', 'f16', 'f64', 'i8']
    scored = sorted(((sum(_plausible(b, _NP[c]) for b in blobs) / len(blobs), c) for c in cands),
                    key=lambda s: (-s[0], cands.index(s[1])))
    best, top = scored[0][1], scored[0][0]
    if top <= 0: return AttrDict(dtype=hint or 'f32', guessed=False, agrees=True)
    # a hint that reads just as well as the winner is the hint we keep — the registry
    # knows things the bytes cannot say, and only disagreement is worth reporting
    if hint and hint in _NP:
        h = sum(_plausible(b, _NP[hint]) for b in blobs) / len(blobs)
        if h >= top - 1e-9: return AttrDict(dtype=hint, guessed=False, agrees=True)
        return AttrDict(dtype=best, guessed=True, agrees=False)
    return AttrDict(dtype=best, guessed=True, agrees=True)

def _meta_tbl(db):
    'Where the atlas records what it knows about a store it wrote. Created on demand.'
    t = db.t.atlas_stores
    if 'atlas_stores' not in db.t:
        t.create(name=str, embedder=str, dim=int, dtype=str, built_at=float, pk='name', if_not_exists=True)
    return t

def record_embedder(db, nm, enc):
    '''Remember which encoder wrote a store.

    This is what lets `encode.check` refuse a query later: two encoders of the same width
    produce vectors that subtract without complaint and mean nothing to each other, and
    the name is the only thing that can tell them apart after the fact.'''
    _meta_tbl(db).upsert(dict(name=nm, embedder=enc.name, dim=int(enc.dim),
                              dtype=_SUF.get(np.dtype(enc.dtype), 'f32'), built_at=time.time()), pk='name')

def _recorded(db):
    if 'atlas_stores' not in db.t: return {}
    try: return {r['name']: r for r in db.t.atlas_stores()}
    except Exception: return {}

@cache(ttl=24 * 3600)
def _describe(key, nm, sig):
    '''Everything about one store that costs a scan. Keyed on the file's mtime and size,
    so it is recomputed the moment anything writes to the database and never otherwise.'''
    db = get_conn(key)
    t, out = db.t[nm], AttrDict(db=key, name=nm)
    cols = list(t.columns)
    out.cols = [AttrDict(name=c.name, type=c.type) for c in cols]
    out.rows = t.count
    out.embedded = db.q(f'select count(*) as n from [{nm}] where embedding is not null')[0]['n']
    out.hash_id = any(c.name == 'id' and 'INT' not in (c.type or '').upper() for c in cols)
    out.extra = [c.name for c in cols if c.name not in
                 ('content', 'embedding', 'metadata', 'uploaded_at', 'id', 'rowid')]
    try: out.fts = bool(t.detect_fts())
    except Exception: out.fts = False
    am = _ann_meta(db, nm)
    blobs = [r['embedding'] for r in db.q(f'select embedding from [{nm}] where embedding is not null limit 24')]
    if blobs:
        d = _dtype(blobs, am['dtype'] if am else None)
        out.dtype, out.dtype_guessed, out.dtype_agrees = d.dtype, d.guessed, d.agrees
        out.ndim = len(blobs[0]) // np.dtype(_NP[out.dtype]).itemsize
        out.ragged = len({len(b) for b in blobs}) > 1
    else:
        out.dtype, out.ndim, out.dtype_guessed, out.dtype_agrees, out.ragged = None, 0, False, True, False
    out.ann = AttrDict(am) if am else None
    # the sidecar was built by reading the blobs at the registry's width; if that is not
    # the width they were written at, its keys index vectors of the wrong length
    out.ann_ok = bool(am and out.ndim and am['ndim'] == out.ndim and am['dtype'] == out.dtype)
    out.ann_why = None
    if am and not out.ann_ok:
        out.ann_why = (f"index registered {am['ndim']}-d {am['dtype']} against {out.ndim}-d {out.dtype} rows — "
                       'rebuild it with `store.rebuild_index()`')
    rec = _recorded(db).get(nm)
    out.embedder = rec['embedder'] if rec else None
    out.facet_keys = _meta_keys(db, nm)
    return dict(out)

def _meta_keys(db, nm):
    'Metadata keys worth offering as a filter, with their commonest values.'
    rows = db.q(f'select metadata from [{nm}] where metadata is not null limit :n', dict(n=cfg.facet_scan))
    counts = {}
    for r in rows:
        try: m = json.loads(r['metadata'])
        except (ValueError, TypeError): continue
        if not isinstance(m, dict): continue
        for k, v in m.items():
            if v is None or isinstance(v, (list, dict)): continue
            counts.setdefault(k, {}).setdefault(str(v), 0)
            counts[k][str(v)] += 1
    out, n = [], max(1, len(rows))
    for k, vals in counts.items():
        # a key whose values are nearly all distinct is an identifier, not a facet.
        # `lineno` and `name` on a code store are the case that matters: offering 413
        # one-row values as things to filter by is offering a list of the whole table.
        # Both conditions, not either — over a small store every key looks near-unique by
        # ratio, and twenty-eight file paths are a facet whatever share of the rows they are
        if len(vals) < 2 or (len(vals) > n * cfg.facet_share and len(vals) > cfg.facet_vals * 2): continue
        top = sorted(vals.items(), key=lambda kv: -kv[1])[:cfg.facet_vals]
        out.append(dict(key=k, distinct=len(vals), pickable=True, rows=n,
                        top=[dict(v=v, n=c) for v, c in top]))
    return sorted(out, key=lambda d: (d['distinct'], d['key']))

def stores(key=None):
    'Every store the atlas can see, or just the ones in one database.'
    out = []
    for k, d in dbs().items():
        if key and k != key: continue
        try: db = get_conn(k)
        except Exception as e:
            warn(f'atlas: cannot open {d.path}: {e}')
            continue
        for nm in sorted(db.table_names()):
            if not _is_store(db, nm): continue
            try: out.append(AttrDict(_describe(k, nm, f'{_DESC_V}.{d.sig}'), path=str(d.path), db_nm=d.nm))
            except Exception as e: warn(f'atlas: cannot describe {k}.{nm}: {e}')
    return out

def store(key, nm):
    'One store record, or None. The only way a route turns a URL into a table.'
    return first(stores(key), lambda s: s.name == nm)

# ── reading vectors ───────────────────────────────────────────────────────────

def np_dtype(st): return _NP.get(st.dtype or 'f32', np.float32)

def vectors(st, limit=None, where=None):
    '''Row ids and their vectors as one float32 matrix, ready to cluster or project.

    Rows whose blob is the wrong length are dropped rather than reshaped: a store part
    way through a re-embed at a new width holds both, and stacking them would either
    raise or silently truncate. Returns `(ids, matrix)`, both possibly empty.'''
    dt, n = np_dtype(st), np.dtype(np_dtype(st)).itemsize
    sql = f'select rowid as rowid, embedding from [{st.name}] where embedding is not null'
    if where: sql += f' and {where}'
    if limit:
        # take every k-th row, not the first k: these files are written in insert order,
        # and the first four thousand chunks of a code index are one directory
        step = max(1, (st.embedded or 1) // limit)
        if step > 1: sql += f' and rowid % {step} = 0'
        sql += f' limit {int(limit)}'
    rows = get_conn(st.db).q(sql)
    keep = [r for r in rows if st.ndim and len(r['embedding']) == st.ndim * n]
    if not keep: return np.zeros(0, dtype=np.int64), np.zeros((0, st.ndim or 1), dtype=np.float32)
    ids = np.array([r['rowid'] for r in keep], dtype=np.int64)
    M = np.stack([np.frombuffer(r['embedding'], dtype=dt) for r in keep]).astype(np.float32)
    return ids, M

def sample_rows(st, ids, columns=('content', 'metadata')):
    'The named columns for a set of rowids, as {rowid: row}. Order is the caller\'s business.'
    if len(ids) == 0: return {}
    sel = ','.join(['rowid as rowid'] + [c for c in columns if c != 'rowid'])
    ins = ','.join(str(int(i)) for i in ids)
    return {r['rowid']: r for r in get_conn(st.db).q(f'select {sel} from [{st.name}] where rowid in ({ins})')}

def facets(st): return st.get('facet_keys') or []

# ── the demo corpus ───────────────────────────────────────────────────────────

def _rel(p, root):
    'A path as the repo sees it, whether the walk that produced it was absolute or not.'
    try: return str(p.resolve().relative_to(root))
    except ValueError: return str(p)

def _md_chunks(p, root):
    from litesearch.data import chunk_markdown
    txt = p.read_text(errors='replace')
    return [dict(content=c, metadata=dict(path=_rel(p, root), lang='.md', type='prose', title=p.stem))
            for c in chunk_markdown(txt) if c.strip()]

def _py_chunks(p, root):
    from litesearch.data import file_parse
    out = []
    for c in file_parse(p):
        m = dict(c.get('metadata') or {})
        m['path'] = _rel(p, root)
        out.append(dict(content=c['content'], metadata=m))
    return out

_seeded, _seed_lock = set(), threading.Lock()

def seed_demo(enc):
    '''Index this app's own prose and source into `data/db/atlas/lego.db`, once.

    Every other database the atlas opens was written by something else, which makes a
    fresh checkout show an empty index and no way to tell whether that is the block
    failing or the machine simply having nothing on it. So the app indexes itself: two
    stores over content that ships in the repo, one of prose and one of code, which is
    also the pairing worth demonstrating — the same query ranks very differently across
    them, and that is visible on one screen.

    Idempotent by construction: `Table.sync` diffs content hashes, so a second call after
    an edit re-embeds the chunks that changed and nothing else.'''
    if not cfg.seed or 'lego' in _seeded: return None
    with _seed_lock:
        if 'lego' in _seeded: return None
        _seeded.add('lego')
        try: return _seed_demo(enc)
        except Exception as e:
            error(f'atlas: demo seed failed: {e}')
            return None

def _seed_demo(enc):
    if enc.kind in ('broken', 'missing'):
        warn('atlas: no encoder, skipping demo seed')
        return None
    cfg.seed_dir.mkdir(parents=True, exist_ok=True)
    pth = cfg.seed_dir / 'lego.db'
    root = Path('.').resolve()
    docs, code = [], []
    for d in cfg.seed_dirs:
        base = Path(d)
        if not base.exists(): continue
        for p in sorted(base.rglob('*.md')): docs += _md_chunks(p, root)
        for p in sorted(base.rglob('*.py')): code += _py_chunks(p, root)
    for p in sorted(root.glob('*.md')): docs += _md_chunks(p, root)
    if not (docs or code): return None
    db = database(pth)
    efn = lambda txts: enc.doc(txts)
    n = {}
    for nm, chunks in (('docs', docs), ('code', code)):
        if not chunks: continue
        st = db.get_store(nm, hash=True, ann=True, ndim=enc.dim, dtype=enc.dtype)
        rows = [dict(content=c['content'], metadata=json.dumps(c['metadata'])) for c in chunks]
        n[nm] = st.sync(rows, emb_fn=efn)
        record_embedder(db, nm, enc)
    _registry.sig = None   # a new file, and the directory listing is what notices
    info(f'atlas: seeded demo corpus {n}')
    return n
