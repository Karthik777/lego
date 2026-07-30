from urllib.parse import urlencode, quote
from fastcore.xml import *
from fasthtml.common import *
from fastcore.all import timed_cache
from lego.core import lc_icon, TextT, ButtonT, PresetsT, asset_js, asset_css, vendor_js, Badge, BadgePresetsT
from .cfg import Routes, cfg
from .data import DBS, schema, reflect, profile, table_names, rowcount
from .infer import roles, specs_for_db, specs_for_table, label_col, fmt_of, _h
from .charts import stats, sparkline, page_rows, row_get, child_rows, child_count, headline, count_rows
from .filters import SEP, wire, describe, applies, columns, ops_for, values_for
from .build import KINDS, AGGS, options, pin_qs, wire_pin

__all__ = ['dash_head', 'index_view', 'db_view', 'table_view', 'row_view', 'rel_view', 'filt_input',
           'build_bar', 'build_input']

@timed_cache(seconds=3600)
def dash_head():
    'Everything the block needs and nothing else asks for: its own styles, Chart.js, the lego wrapper.'
    from pathlib import Path
    here = Path(__file__).parent
    return [asset_css(here / 'dash.css'), vendor_js('chart.umd.min.js'), asset_js(here / 'chart.js', defer=True)]

# ── chrome ────────────────────────────────────────────────────────────────────

def crumbs(*parts):
    out = []
    for i, (txt, href) in enumerate(parts):
        if i: out.append(Span('/', cls='sep'))
        out.append(dlink(txt, href=href) if href else Span(txt))
    return Div(*out, cls='crumbs')

def dlink(*c, href, **kw):
    '''Every in-dashboard link is a real navigation, never an hx-boost body swap.
    Boost is the one step in this path that fails *silently*: on a non-2xx htmx fires
    htmx:responseError and does nothing at all — no navigation, no error page. That is
    exactly what "clicking does nothing" looks like. Unboosted, the browser shows
    whatever the server actually returned. Dash pages also carry their own
    <script src> for Chart.js, which a real load is guaranteed to run.'''
    return A(*c, href=href, hx_boost='false', **kw)

def wrap(*content, head=None): return Div(head, *content, cls='dash-wrap')

def _fmt_cell(v, kind='text'):
    if v is None: return Td('null', cls='null')
    if kind == 'num': return Td(f'{v:,}' if isinstance(v, int) else f'{v:,.2f}' if isinstance(v, float) else str(v), cls='num')
    s = str(v)
    return Td(s if len(s) <= 60 else s[:57] + '…', title=s if len(s) > 60 else None)

def _pk_href(db, tbl, pk): return Routes.row.format(db=db, table=quote(tbl), pk=quote(str(pk)))

# ── filters ───────────────────────────────────────────────────────────────────

def _url(path, fs=(), pins=(), **kw):
    '''A dashboard URL carrying the active filter and any charts the reader built. Every
    in-dash link goes through here, so a facet and a hand-built chart both survive
    navigation — and both are things you can copy out of the address bar and send.'''
    q = [('f', wire(f)) for f in fs] + pin_qs(pins) + [(k, v) for k, v in kw.items() if v]
    return path + ('?' + urlencode(q) if q else '')

def _plus(path, fs, t, c, v, op='eq', pins=()):
    'The same page with one filter more — what a value in a table links to.'
    q, nf = [('f', wire(f)) for f in fs], SEP.join((t, c, op, str(v)))
    if nf not in [x[1] for x in q]: q.append(('f', nf))
    return path + '?' + urlencode(q + pin_qs(pins))

def filt_chip(path, fs, i, tbl=None, pins=()):
    txt = describe(fs[i], tbl)
    return Span(Span(txt), dlink('×', href=_url(path, [g for j, g in enumerate(fs) if j != i], pins),
                                 cls='filt-x', aria_label=f'Remove filter: {txt}'), cls='filt-chip')

def filt_input(db, fc, sel_op=None):
    '''The operator and value controls for one column — swapped in when the column changes.
    A column with few enough distinct values is a list to pick from rather than a box to
    type in: "AC/DC" is only findable if the spelling is not yours to guess.'''
    t, c = (fc.split(SEP, 1) + [''])[:2] if fc and SEP in fc else (None, None)
    if not t or t not in table_names(db) or c not in {x.name for x in reflect(db, t).cols}:
        return Select(Option('is', value='eq'), name='fop', aria_label='Condition'), Input(name='fv', aria_label='Value')
    kind = profile(db, t)['cols'][c]['kind']
    ops = ops_for(kind) or [('eq', 'is')]
    vals = values_for(db, t, c)
    val = (Select(Option('', value=''), *[Option(str(v), value=str(v)) for v in vals], name='fv', aria_label='Value')
           if vals is not None else
           Input(name='fv', aria_label='Value', type='number' if kind == 'num' else 'text',
                 step='any' if kind == 'num' else None, placeholder='value'))
    return (Select(*[Option(l, value=k, selected=(k == sel_op)) for k, l in ops], name='fop', aria_label='Condition'), val)

def filter_bar(db, path, fs, tbl=None, pins=()):
    'Active filters as removable chips, plus the one form that adds another.'
    cols = columns(db, tbl)
    first = f'{cols[0][0]}{SEP}{cols[0][1][0][0]}' if cols and cols[0][1] else ''
    sel = Select(*[Optgroup(*[Option(f'{c} · {role}', value=f'{t}{SEP}{c}') for c, role, _ in cs], label=t)
                   for t, cs in cols],
                 name='fc', aria_label='Column', hx_get=f'{Routes.fopts}?db={db}',
                 hx_target='#filt-in', hx_swap='innerHTML', hx_trigger='change')
    add = Form(*_carry(fs, pins), sel,
               Div(*filt_input(db, first), id='filt-in', cls='filt-in'),
               Button('Add', type='submit', cls=f'{ButtonT.default} {ButtonT.xs}'),
               method='get', action=path, cls='filt-add', hx_boost='false')
    chips = [filt_chip(path, fs, i, tbl, pins) for i in range(len(fs))]
    return Div(Div(Span('Filter', cls='filt-lbl'),
                   *(chips or [Span('everything', cls='filt-none')]),
                   dlink('Clear all', href=_url(path, (), pins), cls='filt-clear') if fs else None,
                   cls='filt-chips'),
               add, cls='filt-bar')

def _carry(fs, pins):
    'The state a GET form must not drop on its way to the next URL.'
    return ([Input(type='hidden', name='f', value=wire(f)) for f in fs] +
            [Input(type='hidden', name='c', value=wire_pin(s)) for s in pins])

# ── the builder ───────────────────────────────────────────────────────────────

def _opt(sel, *pairs, **kw):
    return Select(*[Option(l, value=v, selected=(v == sel)) for v, l in pairs], **kw)

def build_input(db, tbl, sel=None):
    '''The controls that fit the table just chosen — swapped in when it changes.

    Which columns a table has is not something a static form can know, and offering
    `petal_length` as a category on a table that has no petals is how a builder teaches
    people not to trust it.'''
    sel = sel or {}
    o = options(db, tbl)
    splits = [('', 'nothing')] + [(c.tok, c.title) for c in o.splits]
    ms = [(m, _h(m)) for m in o.measures]
    # one select serves as the second axis for every kind. On a bar it is the category; on
    # a scatter or a density it is the other measure. Grouping them says which is which
    # without needing a fourth control that is disabled most of the time.
    groups = [g for g in (
        ('by category', [(c.tok, c.label) for c in o.cats]),
        ('against measure', [(f'own:{m}', l) for m, l in ms])) if g[1]]
    bx = Select(Option('—', value=''),
                *[Optgroup(*[Option(l, value=v, selected=(v == sel.get('bx'))) for v, l in items], label=lbl)
                  for lbl, items in groups],
                name='bx', aria_label='Group by')
    return (
        _opt(sel.get('bkind'), *[(k, l) for k, l, _ in KINDS], name='bkind', aria_label='Chart kind'),
        _opt(sel.get('bagg'), *AGGS, name='bagg', aria_label='Aggregate'),
        _opt(sel.get('by'), ('', '—'), *ms, name='by', aria_label='Measure') if ms
            else Input(type='hidden', name='by', value=''),
        bx if groups else Input(type='hidden', name='bx', value=''),
        _opt(sel.get('bs'), *splits, name='bs', aria_label='Split by'),
        Label(Input(type='checkbox', name='bstack', value='1'), Span('stack'), cls='filt-check'),
    )

def build_bar(db, path, fs, pins, tbl=None):
    'Compose a chart the picker did not think of. Charts already built show as chips.'
    tables = [t for t in table_names(db) if rowcount(db, t) >= 12] or table_names(db)
    first = tbl if tbl in tables else tables[0]
    tsel = Select(*[Option(t, value=t, selected=(t == first)) for t in tables],
                  name='bt', aria_label='Table', hx_get=f'{Routes.bopts}?db={db}',
                  hx_target='#build-in', hx_swap='innerHTML', hx_trigger='change')
    form = Form(*_carry(fs, pins), tsel,
                Div(*build_input(db, first), id='build-in', cls='filt-in'),
                Button('Add chart', type='submit', cls=f'{ButtonT.default} {ButtonT.xs}'),
                method='get', action=path, cls='filt-add', hx_boost='false')
    chips = [Span(Span(s.title),
                  dlink('×', href=_url(path, fs, [p for j, p in enumerate(pins) if j != i]),
                        cls='filt-x', aria_label=f'Remove chart: {s.title}'), cls='filt-chip')
             for i, s in enumerate(pins)]
    return Div(Div(Span('Build', cls='filt-lbl'),
                   *(chips or [Span('nothing yet — pick a shape and add it', cls='filt-none')]),
                   dlink('Clear charts', href=_url(path, fs), cls='filt-clear') if pins else None,
                   cls='filt-chips'),
               form, cls='filt-bar')

# ── /dash ─────────────────────────────────────────────────────────────────────

def _db_card(k, d):
    sch = schema(k)
    return dlink(Div(H3(d.nm), P(d.about, cls='chart-why'),
                     Div(*[Span(f'{t} · {rowcount(k, t):,}', cls='role-chip') for t in list(sch)[:6]],
                         Span(f'+{len(sch) - 6} more', cls='role-chip') if len(sch) > 6 else None,
                         cls='flex flex-wrap gap-1 mt-2'),
                     cls='chart-card'), href=Routes.db.format(db=k), cls='block')

# What each group is for, said once, so the index explains the collection rather than
# listing it. The two kinds of schema are what the picker has to cope with.
GROUPS = {'Business': 'Normalised schemas with dates and money: what the rollup, the running '
                      'total and the top-N were designed for.',
          'Statistical': 'One wide table of measurements and a few lookups. No dates, nothing to '
                         'add up — the charts here are distributions, spreads and correlations.'}

def index_view():
    out = []
    for g, about in GROUPS.items():
        ks = [(k, d) for k, d in DBS.items() if d.get('group', 'Statistical') == g]
        if not ks: continue
        out += [H2(g, cls='mt-6 mb-1'), P(about, cls='chart-why mb-3'),
                Div(*[_db_card(k, d) for k, d in ks], cls='chart-grid')]
    return wrap(Div(H1('Dashboards', cls='m-0'),
                    P('Charts and tables inferred from whatever the database happens to contain.', cls='chart-why'),
                    cls='dash-head'),
                *out)

# ── /dash/{db} ────────────────────────────────────────────────────────────────

def tile(t):
    return Div(Div(t.label, cls='tile-label'), Div(t.value, cls='tile-value'),
               Div(t.sub, cls='tile-sub') if t.get('sub') else None,
               sparkline(t.spark) if t.get('spark') else None, cls='tile')

# A chart's shape decides the box it needs. Ten sideways bars want vertical room; a
# density grid and a correlation matrix are square and want the full width of the row,
# because squeezing either into a half-column column is what turns them into wallpaper.
TALL = ('hbar', 'box')
WIDE = ('area', 'line', 'heat', 'corr', 'map')

def chart_card(spec, wide=None, fs=()):
    # a chart drawn from a table the filter cannot reach says so; quietly showing everything
    # next to charts that did filter is the one outcome that would be read as data
    on = [f for f in fs if applies(spec.db, spec.t, f)]
    off = [f for f in fs if f not in on]
    src = f'{Routes.chart}?{urlencode({**spec.qs, "f": [wire(f) for f in on]}, doseq=True)}'
    if wide is None: wide = spec.kind in WIDE
    box = ('chart-box' + (' tall' if spec.kind in TALL else '')
           + (' square' if spec.kind in ('heat', 'corr') else '') + (' map' if spec.kind == 'map' else ''))
    return Div(Header(H3(spec.title), P(spec.why, cls='chart-why'),
                      P(f'Unfiltered — {_h(spec.t)} has no relation to '
                        + ', '.join(sorted({f.t for f in off})), cls='chart-why filt-off') if off else None),
               Div(Div('Loading…', cls='chart-skel'), Canvas(data_chart_src=src), cls=box),
               Div(Div(cls='chart-legend'), cls='chart-foot'),
               # the light-mode palette runs under 3:1 on three slots, so the numbers
               # are always reachable without reading a colour
               Details(Summary('Show data'), Div(cls='tbl-scroll')(Table(cls='dash-tbl')), cls='chart-data'),
               cls=f'chart-card{" wide" if wide else ""}')

def _rows_cell(db, t, fs):
    'How far the filter reached into this table — the honest answer is per table, not per dashboard.'
    n = count_rows(db, t, fs)
    off = fs and not any(applies(db, t, f) for f in fs)
    return Td(f'{n:,}', Span('unfiltered' if off else f'of {rowcount(db, t):,}', cls='filt-of') if fs else None,
              cls='num')

def db_view(db, fs=(), pins=()):
    sch, path = schema(db), Routes.db.format(db=db)
    # a chart somebody asked for outranks every chart the picker guessed at, so the built
    # ones lead and the inferred set shrinks to make room rather than scrolling away
    specs = specs_for_db(db, limit=max(2, cfg.max_charts - len(pins)))
    tiles = Div(*[tile(t) for t in headline(db, fs)], cls='tile-grid')
    charts = Div(*[chart_card(s, fs=fs) for s in list(pins) + specs], cls='chart-grid')
    tbls = Div(cls='tbl-scroll')(Table(cls='dash-tbl')(
        Thead(Tr(Th('Table'), Th('Rows', cls='num'), Th('Columns'), Th('References'), Th('Referenced by'))),
        Tbody(*[Tr(Td(dlink(t, href=_url(Routes.table.format(db=db, table=quote(t)), fs, pins))),
                   _rows_cell(db, t, fs), Td(str(len(sch[t].cols))),
                   Td(', '.join(f.ref_table for f in sch[t].fks) or '—'),
                   Td(', '.join(c.table for c in sch[t].children) or '—'))
                for t in sch])))
    return wrap(Div(crumbs(('Dashboards', Routes.index), (DBS[db].nm, None)), cls='dash-head'),
                H1(DBS[db].nm, cls='m-0'), P(DBS[db].about, cls='chart-why mb-4'),
                filter_bar(db, path, fs, pins=pins),
                build_bar(db, path, fs, pins),
                tiles, charts,
                H2('Tables', cls='mt-6 mb-2'), tbls)

# ── /dash/{db}/{table} ────────────────────────────────────────────────────────

def _col_row(db, tbl, name, s):
    bits = []
    if s.role in ('measure',):
        bits = [f'min {_n(s.lo)}', f'max {_n(s.hi)}', f'mean {_n(s.mean)}', f'σ {_n(s.sd)}']
    elif s.role == 'temporal': bits = [str(s.get('lo'))[:10], '→', str(s.get('hi'))[:10]]
    elif s.get('maxlen') is not None: bits = [f'max len {s.maxlen}']
    ref = dlink(f'{s.fk.ref_table}.{s.fk.ref_col}', href=Routes.table.format(db=db, table=quote(s.fk.ref_table))) if s.get('fk') else '—'
    return Tr(Td(Div(Span(name), Span(s.role, cls='role-chip'), cls='col-head')),
              Td(s.type), Td(f'{s.distinct:,}', cls='num'), Td(f'{s.nulls:,}', cls='num'),
              Td(ref), Td(' '.join(bits)))

def _n(v):
    if v is None: return '—'
    if isinstance(v, float): return f'{v:,.2f}'
    return f'{v:,}' if isinstance(v, int) else str(v)

def table_view(db, tbl, page=0, fs=(), pins=()):
    r, rl = reflect(db, tbl), roles(db, tbl)
    path, total = Routes.table.format(db=db, table=quote(tbl)), rowcount(db, tbl)
    n = count_rows(db, tbl, fs)
    page = min(page, max(0, (n - 1) // cfg.rows_per_page))   # a filter can strand you past the last page
    rows = page_rows(db, tbl, page, fs)
    kinds = {c.name: rl[c.name].kind for c in r.cols}
    # only a single-column key identifies a row in a URL, so only that one is worth linking
    pk = r.pk[0] if len(r.pk) == 1 else None
    specs = specs_for_table(db, tbl, limit=max(1, 4 - len(pins)))
    body = []
    for row in rows:
        tds = []
        for c in r.cols:
            v, td = row[c.name], _fmt_cell(row[c.name], kinds[c.name])
            f = r.fk_by_col.get(c.name)
            if f and v is not None: td = Td(dlink(str(v), href=_url(_pk_href(db, f.ref_table, v), fs)), cls='num')
            elif c.name == pk and v is not None: td = Td(dlink(str(v), href=_url(_pk_href(db, tbl, v), fs)), cls='num')
            # a category is a column whose values repeat, which is the same thing as saying
            # its cells are worth clicking; a track title is not
            elif rl[c.name].role in ('dimension', 'bool') and v is not None:
                td = Td(dlink(str(v), href=_plus(path, fs, tbl, c.name, v, pins=pins), cls='filt-cell',
                              title=f'Filter to {c.name} = {v}'))
            tds.append(td)
        body.append(Tr(*tds))
    pages = (n + cfg.rows_per_page - 1) // cfg.rows_per_page
    nav = Div(Span(f'Rows {min(n, page * cfg.rows_per_page + 1):,}–{min(n, (page + 1) * cfg.rows_per_page):,} of {n:,}'),
              Div(dlink('← Prev', href=_url(path, fs, pins, page=page - 1), cls=f'{ButtonT.default} {ButtonT.xs}') if page else None,
                  dlink('Next →', href=_url(path, fs, pins, page=page + 1), cls=f'{ButtonT.default} {ButtonT.xs}') if page + 1 < pages else None,
                  cls='flex gap-2'), cls='pager')
    cols_tbl = Div(cls='tbl-scroll')(Table(cls='dash-tbl')(
        Thead(Tr(Th('Column'), Th('Type'), Th('Distinct', cls='num'), Th('Nulls', cls='num'), Th('References'), Th('Profile'))),
        Tbody(*[_col_row(db, tbl, c.name, rl[c.name]) for c in r.cols])))
    return wrap(Div(crumbs(('Dashboards', Routes.index), (DBS[db].nm, _url(Routes.db.format(db=db), fs, pins)), (tbl, None)), cls='dash-head'),
                H1(tbl, cls='m-0'), P(f'{n:,}{f" of {total:,}" if fs else ""} rows · {len(r.cols)} columns · '
                                      f'{len(r.fks)} outbound, {len(schema(db)[tbl].children)} inbound references',
                                      cls='chart-why mb-4'),
                filter_bar(db, path, fs, tbl, pins),
                build_bar(db, path, fs, pins, tbl),
                Div(*[chart_card(s, fs=fs) for s in list(pins) + specs], cls='chart-grid mb-6') if (specs or pins) else None,
                H2('Columns', cls='mt-6 mb-2'), cols_tbl,
                H2('Rows', cls='mt-6 mb-2'),
                Div(cls='tbl-scroll')(Table(cls='dash-tbl')(
                    Thead(Tr(*[Th(c.name) for c in r.cols])), Tbody(*body))), nav)

# ── /dash/{db}/{table}/{pk} — the nested view ─────────────────────────────────

def _title_for(db, tbl, row):
    # strict: a row is titled by a real name column or not at all — heading an invoice
    # with its billing address because that was the first text column reads as a bug
    lab = label_col(db, tbl, strict=True)
    return str(row.get(lab) or '') if lab else ''

def row_view(db, tbl, pk, row, fs=()):
    'One row is already a filter of one, so nothing here is filtered — the links just carry it onward.'
    r, rl = reflect(db, tbl), roles(db, tbl)
    fields = []
    for c in r.cols:
        v = row[c.name]
        f = r.fk_by_col.get(c.name)
        if f and v is not None:
            parent = row_get(db, f.ref_table, v)
            lab = _title_for(db, f.ref_table, parent) if parent else None
            dd = dlink(lab or str(v), href=_url(_pk_href(db, f.ref_table, v), fs))
        else:
            dd = 'null' if v is None else str(v)
        fields.append(Div(Dt(c.name), Dd(dd), cls='field'))
    kids = schema(db)[tbl].children
    return wrap(Div(crumbs(('Dashboards', Routes.index), (DBS[db].nm, _url(Routes.db.format(db=db), fs)),
                           (tbl, _url(Routes.table.format(db=db, table=quote(tbl)), fs)), (str(pk), None)), cls='dash-head'),
                H1(_title_for(db, tbl, row) or f'{tbl} {pk}', cls='m-0'),
                P(f'{tbl} · {r.pk[0] if r.pk else "row"} {pk}', cls='chart-why mb-4'),
                Dl(*fields, cls='field-grid'),
                H2('Related', cls='mt-6 mb-2') if kids else None,
                Div(*[_rel_node(db, tbl, pk, k, 0) for k in kids], cls='rel-tree') if kids else None)

def _rel_node(db, parent, pk, kid, depth):
    n = child_count(db, kid.table, kid.col, pk)
    url = Routes.rel.format(db=db, table=quote(parent), pk=quote(str(pk)), child=quote(kid.table)) + f'?col={quote(kid.col)}&depth={depth}'
    return Details(Summary(lc_icon('table-2', 14), Span(f'{kid.table}'),
                           Span(f'via {kid.col}', cls='role-chip'), Span(f'{n:,}', cls='rel-count')),
                   Div(Div('Loading…', cls='chart-skel'), cls='rel-body',
                       hx_get=url, hx_trigger='toggle once from:closest details', hx_swap='innerHTML'),
                   cls='rel-node')

def rel_view(db, child, col, val, depth=0):
    'One nesting level: the child rows, each able to open its own children.'
    r = reflect(db, child)
    rows = child_rows(db, child, col, val, limit=cfg.rel_preview)
    n = child_count(db, child, col, val)
    kinds = {c.name: k for c, k in [(c, profile(db, child)['cols'][c.name]['kind']) for c in r.cols]}
    pk = r.pk[0] if len(r.pk) == 1 else None
    body = []
    for row in rows:
        tds = []
        for c in r.cols:
            v = row[c.name]
            f = r.fk_by_col.get(c.name)
            if f and v is not None: tds.append(Td(dlink(str(v), href=_pk_href(db, f.ref_table, v)), cls='num'))
            elif c.name == pk and v is not None: tds.append(Td(dlink(str(v), href=_pk_href(db, child, v)), cls='num'))
            else: tds.append(_fmt_cell(v, kinds[c.name]))
        body.append(Tr(*tds))
    tbl = Div(cls='tbl-scroll')(Table(cls='dash-tbl')(
        Thead(Tr(*[Th(c.name) for c in r.cols])), Tbody(*body)))
    more = None
    if n > len(rows):
        more = P(dlink(f'View all {n:,} in {child} →', href=Routes.table.format(db=db, table=quote(child))),
                 cls='chart-why mt-2')
    # one level of inline nesting, then the row page takes over — otherwise a deep
    # schema would try to open the whole database in one response
    deeper = None
    if depth < 2 and pk:
        kids = schema(db)[child].children
        if kids and rows:
            deeper = Div(P(f'Inside {child} {rows[0][pk]}', cls='chart-why mt-3'),
                         Div(*[_rel_node(db, child, rows[0][pk], k, depth + 1) for k in kids], cls='rel-tree'))
    return Div(tbl, more, deeper)
