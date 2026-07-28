from urllib.parse import quote
from fasthtml.common import JSONResponse, RedirectResponse
from fastcore.xml import Div
from lego.core import base, not_found, RouteOverrides
from .cfg import Routes, cfg
from .data import DBS, table_names, reflect
from .charts import payload, row_get
from .filters import parse, merge, wire
from .ui import dash_head, index_view, db_view, table_view, row_view, rel_view, filt_input

__all__ = ['connect', 'Routes']

def _page(content, auth, title):
    return (*base(content, auth, title=title), *dash_head())

def _known(db, tbl=None):
    if db not in DBS: return False
    return tbl is None or tbl in table_names(db)

def _fs(req, db):
    'The active filter, straight off the query string — nothing about it is remembered between requests.'
    return parse(db, req.query_params.getlist('f'))

def _added(req, db, fs):
    '''The add-filter form posts its three controls separately, because one <select> cannot
    build a `table:column:op:value` string on its own without JS. Fold them in and send the
    reader to the canonical URL, so what they can copy out of the address bar is the filter.'''
    q = req.query_params
    if not q.get('fc'): return None
    out = merge(db, fs, q.get('fc'), q.get('fop'), q.get('fv'))
    qs = '&'.join('f=%s' % quote(wire(f), safe='') for f in out)
    return RedirectResponse(req.url.path + (f'?{qs}' if qs else ''), status_code=303)

def dash_index(req, auth=None): return _page(index_view(), auth, 'Dashboards')

def dash_db(req, db: str, auth=None):
    if not _known(db): return not_found()
    fs = _fs(req, db)
    return _added(req, db, fs) or _page(db_view(db, fs), auth, f'{DBS[db].nm} · Dashboards')

def dash_table(req, db: str, table: str, page: int = 0, auth=None):
    if not _known(db, table): return not_found()
    fs = _fs(req, db)
    return _added(req, db, fs) or _page(table_view(db, table, max(0, page), fs), auth, f'{table} · {DBS[db].nm}')

def dash_row(req, db: str, table: str, pk: str, auth=None):
    if not _known(db, table): return not_found()
    row = row_get(db, table, pk)
    if row is None: return not_found()
    return _page(row_view(db, table, pk, row, _fs(req, db)), auth, f'{table} {pk}')

def dash_fopts(req, db: str = '', fc: str = ''):
    'htmx partial: the operator and value controls that fit the column just chosen.'
    if not _known(db): return not_found()
    return filt_input(db, fc)

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
    app.get(Routes.index)(dash_index)
    app.get(Routes.db)(dash_db)
    app.get(Routes.table)(dash_table)
    app.get(Routes.row)(dash_row)
    app.get(Routes.rel)(dash_rel)
