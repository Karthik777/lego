from fasthtml.common import JSONResponse
from fastcore.all import threaded, first
from lego.core import base, not_found, RouteOverrides, quick_lgr
from .cfg import Routes, cfg
from .data import stores, store, seed_demo, get_conn
from .encode import get_encoder, encoder_for
from .search import run, compare, more_like
from . import cluster as cl
from .ui import atlas_head, index_view, store_view, doc_view, legs_view, score_badge, proj_payload

__all__ = ['connect', 'Routes']

info, error, warn = quick_lgr()

def _page(content, auth, title): return (*base(content, auth, title=title), *atlas_head())

def _st(db, name):
    'The store a URL names, or None. Every route starts here — nothing else turns text into a table.'
    return store(db, name) if db and name else None

def atlas_index(req, auth=None): return _page(index_view(stores()), auth, 'Embedding atlas')

def atlas_store(req, db: str, store: str, q: str = '', mode: str = 'hybrid', k: int = 0,
                ann: bool = False, rerank: bool = False, page: int = 0, auth=None):
    st = _st(db, store)
    if st is None: return not_found()
    enc = encoder_for(st)
    res = run(st, q, enc, mode=mode, ann=ann, k=k or None, page=max(0, page), rerank=rerank)
    # the clustering is what colours the results and the map, and it is cached against the
    # file's row counts — so asking for it on every search costs a dict lookup, not a scan
    an = cl.analysis(st)
    return _page(store_view(st, res, an), auth, f'{store} · Atlas')

def atlas_doc(req, db: str, store: str, id: int, q: str = '', auth=None):
    st = _st(db, store)
    if st is None: return not_found()
    row = first(get_conn(db).q(f'select rowid as rowid, * from [{st.name}] where rowid = :r', dict(r=int(id))))
    if row is None: return not_found()
    return _page(doc_view(st, int(id), row, more_like(st, id), cl.analysis(st), back=q), auth,
                 f'{store} {id} · Atlas')

def atlas_legs(req, db: str, store: str, q: str = '', k: int = 0):
    'htmx partial: every strategy over the current query, measured against each other.'
    st = _st(db, store)
    if st is None: return not_found()
    return legs_view(st, compare(st, q, encoder_for(st), k=k or None))

def atlas_score(req, db: str, store: str):
    'htmx partial: the clustering headline for an index card. Loaded after the page for a reason.'
    st = _st(db, store)
    if st is None: return not_found()
    return score_badge(st)

def atlas_proj(req, db: str, store: str):
    '''The map's points.

    Served apart from the page because it is the same however the store was searched — the
    query only decides which points get ringed, and that travels on the canvas as an
    attribute. Cache-keyed by row counts through the analysis, so a re-index changes it and
    nothing else does.'''
    st = _st(db, store)
    if st is None: return not_found()
    return JSONResponse(proj_payload(st, cl.analysis(st)))

@threaded
def _warm():
    '''Load the encoder and index the app's own docs, off the request path.

    A static embedder is tens of megabytes and may need downloading; doing that inside the
    first request means the first visitor waits for it, and doing it at import means the
    app does not start without it.'''
    try: seed_demo(get_encoder())
    except Exception as e: error(f'atlas: warm-up failed: {e}')

def connect(app):
    if cfg.public: RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Atlas', Routes.index, 'new', not cfg.public)]
    app.get(Routes.proj)(atlas_proj)     # before /atlas/{db}/{store}, which would swallow them
    app.get(Routes.legs)(atlas_legs)
    app.get(Routes.score)(atlas_score)
    app.get(Routes.doc)(atlas_doc)
    app.get(Routes.index)(atlas_index)
    app.get(Routes.store)(atlas_store)
    if cfg.seed: _warm()
