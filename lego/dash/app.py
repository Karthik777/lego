from urllib.parse import quote, urlencode
from fasthtml.common import JSONResponse, RedirectResponse
from fastcore.xml import Div
from lego.core import base, not_found, RouteOverrides
from .cfg import Routes, cfg
from .data import DBS, table_names, reflect
from .charts import payload, row_get
from .filters import parse, merge, wire
from .build import compose, pins, wire_pin
from .ui import (dash_head, index_view, db_view, table_view, row_view, rel_view, filt_input,
                 build_input)

__all__ = ['connect', 'Routes']

def _page(content, auth, title):
    return (*base(content, auth, title=title), *dash_head())

def _known(db, tbl=None):
    if db not in DBS: return False
    return tbl is None or tbl in table_names(db)

def _fs(req, db):
    'The active filter, straight off the query string — nothing about it is remembered between requests.'
    return parse(db, req.query_params.getlist('f'))

def _pins(req, db):
    'Charts the reader built, likewise — one `c=` each, and likewise nothing remembered.'
    return pins(db, req.query_params.getlist('c'))

def _added(req, db, fs, ps):
    '''The add-filter and build-a-chart forms both post their controls separately, because
    one <select> cannot assemble a whole spec on its own without JS. Fold them in and send
    the reader to the canonical URL, so what they can copy out of the address bar is the
    dashboard they are looking at.'''
    q = req.query_params
    if not (q.get('fc') or q.get('bt')): return None
    if q.get('fc'): fs = merge(db, fs, q.get('fc'), q.get('fop'), q.get('fv'))
    if q.get('bt'):
        s = compose(db, dict(q))
        if s and all(s.key != p.key for p in ps): ps = list(ps) + [s]
    qs = urlencode([('f', wire(f)) for f in fs] + [('c', wire_pin(p)) for p in ps[:cfg.max_charts]])
    return RedirectResponse(req.url.path + (f'?{qs}' if qs else ''), status_code=303)

def dash_index(req, auth=None): return _page(index_view(), auth, 'Dashboards')

def dash_db(req, db: str, auth=None):
    if not _known(db): return not_found()
    fs, ps = _fs(req, db), _pins(req, db)
    return _added(req, db, fs, ps) or _page(db_view(db, fs, ps), auth, f'{DBS[db].nm} · Dashboards')

def dash_table(req, db: str, table: str, page: int = 0, auth=None):
    if not _known(db, table): return not_found()
    fs, ps = _fs(req, db), _pins(req, db)
    return _added(req, db, fs, ps) or _page(table_view(db, table, max(0, page), fs, ps), auth,
                                            f'{table} · {DBS[db].nm}')

def dash_row(req, db: str, table: str, pk: str, auth=None):
    if not _known(db, table): return not_found()
    row = row_get(db, table, pk)
    if row is None: return not_found()
    return _page(row_view(db, table, pk, row, _fs(req, db)), auth, f'{table} {pk}')

def dash_fopts(req, db: str = '', fc: str = ''):
    'htmx partial: the operator and value controls that fit the column just chosen.'
    if not _known(db): return not_found()
    return filt_input(db, fc)

def dash_bopts(req, db: str = '', bt: str = ''):
    'htmx partial: the builder controls that fit the table just chosen.'
    if not _known(db, bt): return not_found()
    return build_input(db, bt)

def dash_geo(req, pack: str):
    '''The map geometry, as pre-projected SVG paths.

    Served apart from the chart data because it is the same however the chart is filtered,
    and every map on the page wants the same one. Immutable: the packs only change when
    tools/geo_build.mjs is re-run and the file is committed, so the browser should fetch
    world.json once and never ask again.'''
    from .geo import pack as geo_pack
    try: g = geo_pack(pack)
    except KeyError: return not_found()
    return JSONResponse(dict(w=g.w, h=g.h, key=g.key, shapes=g.shapes, names=g.names),
                        headers={'cache-control': 'public, max-age=31536000, immutable'})

def dash_rel(req, db: str, table: str, pk: str, child: str, col: str = '', depth: int = 0, auth=None):
    'htmx partial: one level of children, loaded when the reader opens the section.'
    if not _known(db, child): return not_found()
    if col not in reflect(db, child).fk_by_col: return Div('Not a foreign key', cls='chart-why')
    return rel_view(db, child, col, pk, depth=min(int(depth), 2))

def dash_chart(req):
    # dict() over the query params keeps only the last value of a repeated key, and `f` is
    # repeated once per filter — the whole list has to be pulled out by hand
    p = dict(req.query_params) | {'f': req.query_params.getlist('f')}
    try: return JSONResponse(payload(p))
    except (ValueError, KeyError) as e: return JSONResponse({'error': str(e)}, status_code=400)

def connect(app):
    if cfg.public: RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Dashboards', Routes.index, 'new', not cfg.public)]
    app.get(Routes.chart)(dash_chart)   # before /dash/{db}, which would otherwise swallow it
    app.get(Routes.fopts)(dash_fopts)   # likewise
    app.get(Routes.bopts)(dash_bopts)   # likewise
    app.get(Routes.geo)(dash_geo)       # likewise
    app.get(Routes.index)(dash_index)
    app.get(Routes.db)(dash_db)
    app.get(Routes.table)(dash_table)
    app.get(Routes.row)(dash_row)
    app.get(Routes.rel)(dash_rel)
