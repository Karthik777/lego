import re
from fastcore.all import AttrDict, L
from .cfg import cfg
from .data import DBS, get_db, table_names, reflect, profile, rowcount, ident, cached
from .infer import roles, label_col, fmt_of, _h
from .filters import parse, where

__all__ = ['payload', 'stats', 'sparkline', 'page_rows', 'row_get', 'child_rows', 'child_count',
           'headline', 'count_rows', 'best_pair']

# Reads that name rows go through fastlite's table API; the aggregates below stay hand-written
# because GROUP BY is not something rows_where models.
KINDS = {'bar', 'hbar', 'line', 'area', 'doughnut', 'scatter', 'box', 'heat', 'corr', 'map'}
AGGS = {'sum', 'avg', 'count', 'hist', 'raw'}
BUCKETS = {'%Y', '%Y-%m', '%Y-%m-%d'}
NONE = '(none)'
# every chart aliases its base table to the same thing, so the filter's correlated
# subqueries have one name to point at whatever shape the surrounding query is
BASE = '"_b"'

def _cols(db, tbl): return {c.name for c in reflect(db, tbl).cols}

def _ref(q, p, tk, ck, lk, alias):
    '''A dimension that lives on a *parent* table, reached through a declared foreign key —
    the artist's name rather than the ArtistId the track happens to store.

    Both the category axis (`join`/`jcol`/`jlabel`) and the split-by (`sj`/`scol`/`slabel`)
    are the same idea pointed at different parts of the chart, so they share this. Returns
    None when the request did not ask for one.'''
    t = p.get(tk)
    if not t: return None
    if t not in table_names(q.db): raise ValueError('unknown join table')
    col, lbl = p.get(ck), p.get(lk)
    fk = reflect(q.db, q.t).fk_by_col.get(col)
    if not fk or fk.ref_table != t: raise ValueError('join is not a declared foreign key')
    tq, pcols = ident(t, table_names(q.db)), _cols(q.db, t)
    return AttrDict(t=t, c=lbl, expr=f'{alias}.{ident(lbl, pcols)}',
                    sql=f'join {tq} {alias} on {alias}.{ident(fk.ref_col, pcols)} = {BASE}.{ident(col, q.cols)}')

def _check(p):
    'Every identifier in a chart request has to match something the schema reported. Nothing else reaches SQL.'
    db = p.get('db')
    if db not in DBS: raise ValueError('unknown database')
    tbl = p.get('t')
    if tbl not in table_names(db): raise ValueError('unknown table')
    cols = _cols(db, tbl)
    q = AttrDict(db=db, t=tbl, tq=ident(tbl, table_names(db)), cols=cols,
                 kind=p.get('kind'), agg=p.get('agg'), bucket=p.get('bucket'),
                 ord=str(p.get('ord') or '') in ('1', 'true'),
                 stack=str(p.get('stack') or '') in ('1', 'true'))
    if q.kind not in KINDS: raise ValueError('unknown chart kind')
    if q.agg not in AGGS: raise ValueError('unknown aggregate')
    if q.bucket and q.bucket not in BUCKETS: raise ValueError('unknown bucket')
    q.x, q.y = p.get('x') or None, p.get('y') or None
    q.xq = ident(q.x, cols) if q.x else None
    q.yq = ident(q.y, cols) if q.y else None
    q.fs = p.get('fs') if p.get('fs') is not None else parse(db, p.get('f'))
    # `cols` on the request names the measures a correlation matrix should cover; `q.cols`
    # is the set of every column the table has, and the two must not be the same attribute
    q.mcols = [c for c in str(p.get('cols') or '').split(',') if c in cols]
    q.jx = _ref(q, p, 'join', 'jcol', 'jlabel', 'px')
    q.js = _ref(q, p, 'sj', 'scol', 'slabel', 'ps')
    s = p.get('s') or None
    q.sp = q.js or (AttrDict(t=tbl, c=s, expr=f'{BASE}.{ident(s, cols)}') if s else None)
    # the axis is either a column of this table or a parent's label; everything downstream
    # only ever needs the expression and what clicking it should filter on
    q.ax = q.jx or (AttrDict(t=tbl, c=q.x, expr=f'{BASE}.{q.xq}') if q.x else None)
    q.joins = ' '.join(r.sql for r in (q.jx, q.js) if r)
    return q

def payload(p):
    'Run a validated chart spec and return the JSON the browser draws.'
    q = _check(p)
    if q.kind == 'map': return _map(q)
    if q.kind == 'corr': return _corr(q)
    if q.kind == 'heat': return _heat(q)
    if q.kind == 'box': return _box(q)
    if q.agg == 'hist': return _hist(q)
    if q.agg == 'raw': return _scatter(q)
    return _agg(q)

def _out(q, labels, series, fmt, **kw):
    return dict(kind=q.kind, agg=q.agg, labels=labels, fmt=fmt, series=series,
                stacked=bool(q.get('stack')), **kw)

def _clip(s, n=32): return s if len(s) <= n else s[:n - 1] + '…'
def _lbl(v): return NONE if v is None else _clip(str(v))

_YESNO = {0: 'no', 1: 'yes'}

def _labeller(db, tbl, col):
    '''How to write this column's values on an axis.

    A two-valued 0/1 integer is a yes-or-no, and an axis reading "0" and "1" makes the
    reader do the translation every time they look at it. The raw value still travels in
    `keys`, so clicking the bar filters on 1, not on "yes".'''
    s = (profile(db, tbl)['cols'].get(col) or {}) if col else {}
    if s.get('kind') == 'num' and s.get('distinct') == 2 and (s.get('lo'), s.get('hi')) == (0, 1):
        return lambda v: _lbl(_YESNO.get(v, v))
    return _lbl

def _guard(q, *own):
    '''A chart's own guards and the active filter as one where clause, plus its binds.
    Every builder goes through here, so a filter reaches a chart by existing, not by each
    query remembering to ask for it.'''
    w = where(q.db, q.t, q.fs, BASE)
    parts = [c for c in own if c] + ([w.sql] if w.sql else [])
    return ('where ' + ' and '.join(parts) if parts else ''), w.params

def _val(q):
    'The aggregate expression. `count` needs no column; the others are read off the base table.'
    if q.agg == 'count' or not q.y: return 'count(*)', 'int', 'Rows'
    fmt = fmt_of(q.y, '')
    s = profile(q.db, q.t)['cols'].get(q.y) or {}
    # the mean of a column that is only ever 0 or 1 is a proportion, and reading "0.37"
    # off an axis when the answer is "37% survived" is the chart failing at its one job
    if q.agg == 'avg' and s.get('distinct') == 2 and (s.get('lo'), s.get('hi')) == (0, 1): fmt = 'pct'
    return f'{q.agg}({BASE}.{q.yq})', fmt, _h(q.y)

def _log(vals):
    '''Should this axis be logarithmic?

    Only when the numbers make it necessary and legal. Necessary: they span at least
    `cfg.log_span` orders of magnitude, which is where a linear axis stops being a scale
    and becomes a picture of its own maximum — Factbook populations run from ten thousand
    to a billion, and every country but three lands on the baseline. Legal: every value is
    strictly positive, because log has nothing to say about zero or a negative delay.

    Bars never get one, which is why this is only called from the box and scatter builders.
    A bar means its length, that length is measured from zero, and a log axis has no zero —
    a "twice as long" bar on one would be ten times the value.'''
    vs = [v for v in vals if v is not None]
    if len(vs) < 3 or min(vs) <= 0: return False
    return max(vs) / min(vs) >= 10 ** cfg.log_span

def _groups(totals):
    '''Which split values get a series, and in what order.

    The widest ones are kept, because a series carrying four rows is a line of noise. But
    they are then ordered by *name*, not by size: a colour belongs to a category, and if
    the order came from the totals then filtering the data would repaint every series and
    the reader would have to re-learn the legend.'''
    keep = sorted(totals, key=lambda g: -(totals[g] or 0))[:cfg.max_series]
    return sorted(keep, key=lambda g: (g is None, str(g)))

# ── the one grouped-aggregate builder ─────────────────────────────────────────

def _agg(q):
    '''Every bar, line, area and doughnut in the block comes out of here.

    One SQL shape covers all of them because they differ only in what the category is
    (a column, a parent's label, or a date bucket) and whether a second category splits
    the result into series. Splitting is the difference between "signal over time" and
    "signal over time, per region" — on this data the second is the only one that says
    anything, and it is one more `group by` term.'''
    db = get_db(q.db)
    val, fmt, label = _val(q)
    xf = f'strftime(:_b, {q.ax.expr})' if q.bucket else q.ax.expr
    # a "(none)" bar for a half-empty column outranks every real category and says
    # nothing the column profile doesn't already report
    w, p = _guard(q, f'{q.ax.expr} is not null')
    if q.bucket: p = dict(_b=q.bucket, **p)
    sel = f'{xf} as k, {val} as v' + (f', {q.sp.expr} as g' if q.sp else '')
    grp = 'k' + (', g' if q.sp else '')
    rows = db.q(f'select {sel} from {q.tq} {BASE} {q.joins} {w} group by {grp}', p)
    return _pivot(q, rows, label, fmt)

def _order(q, rows):
    '''Category order. A date bucket or an ordered number reads left to right; anything
    else reads biggest first, because that is the question a bar chart is asked.'''
    tot = {}
    for r in rows: tot[r['k']] = tot.get(r['k'], 0) + (r['v'] or 0)
    if q.bucket or q.ord: return sorted(tot, key=lambda k: (k is None, k))
    return sorted(tot, key=lambda k: -tot[k])

def _pivot(q, rows, label, fmt):
    'Long rows into the labels-and-series shape Chart.js wants.'
    keys = _order(q, rows)
    xl = _labeller(q.db, q.ax.t, q.ax.c) if q.ax else _lbl
    gl = _labeller(q.db, q.sp.t, q.sp.c) if q.sp else _lbl
    # a top-N is only honest on a chart that says so; the sideways bar is the one that does
    keep = keys[:cfg.top_n] if (q.kind == 'hbar' and not q.ord) else keys
    if not q.sp:
        by = {r['k']: r['v'] for r in rows}
        out = _out(q, [xl(k) for k in keep], [dict(label=label, data=[by.get(k) for k in keep])], fmt,
                   omitted=len(keys) - len(keep))
        return _clickable(out, keep, q.ax.t, q.ax.c, 'sw' if q.bucket else 'eq')
    gt = {}
    for r in rows: gt[r['g']] = gt.get(r['g'], 0) + (r['v'] or 0)
    groups = _groups(gt)
    cell = {(r['k'], r['g']): r['v'] for r in rows}
    series = [dict(label=gl(g), data=[cell.get((k, g)) for k in keep]) for g in groups]
    out = _out(q, [xl(k) for k in keep], series, fmt, omitted=len(keys) - len(keep),
               omitted_series=len(gt) - len(groups),
               split=dict(t=q.sp.t, c=q.sp.c, keys=[None if g is None else str(g) for g in groups]))
    return _clickable(out, keep, q.ax.t, q.ax.c, 'sw' if q.bucket else 'eq')

def _clickable(out, keys, tbl, col, op='eq'):
    '''What clicking a mark filters by. Labels are clipped for the axis and stringified for
    JSON, so the untouched group key travels separately — filtering by "Symphony No. 5 in C…"
    would match nothing.'''
    if not tbl or not col: return out
    out['on'] = dict(t=tbl, c=col, op=op)
    out['keys'] = [None if k is None else str(k) for k in keys]
    return out

# ── distributions: the quantile box ───────────────────────────────────────────

def _box(q):
    '''Five numbers per category instead of one.

    A bar of average price by cut answers "which is bigger"; it cannot answer "do these
    overlap", which on measurement data is the whole question — the means of two iris
    species are ten pixels apart and their spreads do not touch. So the box carries the
    median, the middle half, and the 5th–95th range.

    Nearest-rank quantiles off `row_number()`, in one pass. Whiskers are p05/p95 rather
    than Tukey fences: fences need a second pass to find the last point inside them, and a
    percentile is the thing a reader can state without knowing what a fence is.'''
    db = get_db(q.db)
    if not q.y: raise ValueError('a box needs a measure')
    w, p = _guard(q, f'{q.ax.expr} is not null', f'{BASE}.{q.yq} is not null')
    at = lambda f: (f'max(case when rn = max(1, min(n, cast(n * {f} + 0.5 as integer))) then v end)')
    rows = db.q(
        f'with d as (select {q.ax.expr} as k, {BASE}.{q.yq} as v, '
        f'  row_number() over (partition by {q.ax.expr} order by {BASE}.{q.yq}) as rn, '
        f'  count(*) over (partition by {q.ax.expr}) as n '
        f'  from {q.tq} {BASE} {q.joins} {w}) '
        f'select k, max(n) as n, min(v) as lo, max(v) as hi, {at(0.05)} as p05, {at(0.25)} as q1, '
        f'{at(0.5)} as med, {at(0.75)} as q3, {at(0.95)} as p95, avg(v) as mean from d group by k', p)
    rows = [r for r in rows if (r['n'] or 0) >= cfg.box_min]
    if not rows: raise ValueError('no category has enough rows to quantify')
    rows.sort(key=lambda r: -(r['med'] or 0))
    keep = rows[:cfg.top_n] if q.kind == 'hbar' else rows
    data = [dict(lo=r['lo'], p05=r['p05'], q1=r['q1'], med=r['med'], q3=r['q3'], p95=r['p95'],
                 hi=r['hi'], mean=r['mean'], n=r['n']) for r in keep]
    xl = _labeller(q.db, q.ax.t, q.ax.c)
    lo = min(r['p05'] for r in keep)
    hi = max(r['p95'] for r in keep)
    # Chart.js scales to the floating bar, which is only the middle half — left to itself
    # it crops the whiskers it is drawn to show
    log = _log([v for r in keep for v in (r['p05'], r['p95'])])
    if log: rng = [lo / 1.3, hi * 1.3]      # padding on a log axis is a ratio, not a gap
    else:
        pad = (hi - lo) * 0.08 or abs(hi) * 0.08 or 1
        # padding a price down to −$600 to make room for a whisker invents a negative price
        rng = [max(0, lo - pad) if lo >= 0 else lo - pad, hi + pad]
    out = _out(q, [xl(r['k']) for r in keep], [dict(label=_h(q.y), data=data)], fmt_of(q.y, ''),
               omitted=len(rows) - len(keep), range=rng, log=log)
    return _clickable(out, [r['k'] for r in keep], q.ax.t, q.ax.c)

# ── the choropleth ────────────────────────────────────────────────────────────

def _map(q):
    '''A measure per place.

    The geography is not declared anywhere. `geo.match` decides a column is a place column
    because its values resolve to shapes, so `Customer.Country`, `Abbrev.abbrev` and the
    Factbook's "Korea, South" all arrive here the same way.

    Colour is assigned by **quantile class**, not by a linear ramp. Country data is almost
    always heavy-tailed — China and India hold a third of the world's population between
    them — and a linear ramp on that paints two countries dark and the other hundred and
    seventy the same near-white, which is a picture of the two largest values rather than
    of the distribution. Equal-count classes spend the colour where the countries are, and
    the legend prints the break points so the classes are readable as numbers.'''
    from .geo import resolve, geo_of
    if not q.ax: raise ValueError('a map needs a place column')
    g = geo_of(q.db, q.ax.t, q.ax.c)
    if not g: raise ValueError('that column does not name places')
    val, fmt, label = _val(q)
    db = get_db(q.db)
    w, p = _guard(q, f'{q.ax.expr} is not null')
    rows = db.q(f'select {q.ax.expr} as k, {val} as v from {q.tq} {BASE} {q.joins} {w} group by k', p)
    hit = resolve(g.pack, [r['k'] for r in rows])
    cells, keys, dropped = {}, {}, []
    for r in rows:
        s = hit.get(r['k'])
        if s is None: dropped.append(r['k']); continue
        # two rows can land on one shape — "UK" and "United Kingdom" in the same column
        cells[s] = (cells.get(s) or 0) + (r['v'] or 0) if q.agg in ('sum', 'count') else r['v']
        keys[s] = str(r['k'])
    if not cells: raise ValueError('nothing in that column resolved to a place')
    vals = sorted(v for v in cells.values() if v is not None)
    out = dict(kind='map', agg=q.agg, pack=g.pack, labels=[], fmt=fmt, label=label,
               cells=cells, keys=keys, breaks=_quantiles(vals, cfg.map_classes),
               lo=vals[0], hi=vals[-1], n=len(cells),
               unmatched=len(dropped), series=[dict(label=label, data=list(cells.values()))])
    if q.ax.t and q.ax.c: out['on'] = dict(t=q.ax.t, c=q.ax.c, op='eq')
    return out

def _quantiles(vals, k):
    '''Upper bound of each class, equal counts per class.

    Duplicates collapse — a column where two thirds of the places share one value cannot
    have six distinct classes, and inventing empty ones would put breaks in the legend
    that no place falls between.'''
    if not vals: return []
    out = []
    for i in range(1, k):
        v = vals[min(len(vals) - 1, int(len(vals) * i / k))]
        if not out or v > out[-1]: out.append(v)
    return out

# ── density: the scatter that survives fifty thousand rows ────────────────────

def _heat(q):
    '''A 2D histogram of two measures.

    A scatter of 53,940 diamonds is a solid black blob with a `limit 2000` in front of it,
    which is two lies at once — the shape is wrong and the sample is arbitrary. Binning
    counts every row and puts the density where the density is.'''
    db = get_db(q.db)
    if not (q.x and q.y): raise ValueError('a density needs two measures')
    pr = profile(q.db, q.t)['cols']
    ax, ay = pr[q.x], pr[q.y]
    n = cfg.heat_bins
    ex = _extent(ax); ey = _extent(ay)
    if not (ex and ey): raise ValueError('a column has no spread to bin')
    wx, wy = (ex[1] - ex[0]) / n, (ey[1] - ey[0]) / n
    w, p = _guard(q, f'{BASE}.{q.xq} is not null', f'{BASE}.{q.yq} is not null',
                  f'{BASE}.{q.xq} between :_x0 and :_x1', f'{BASE}.{q.yq} between :_y0 and :_y1')
    b = lambda c, lo, wd, t: f'max(0, min(:_n, cast(({BASE}.{c} - :{lo}) / :{wd} as integer)))'
    rows = db.q(f'select {b(q.xq, "_x0", "_wx", "x")} as bx, {b(q.yq, "_y0", "_wy", "y")} as by, '
                f'count(*) as v from {q.tq} {BASE} {w} group by bx, by',
                dict(_x0=ex[0], _x1=ex[1], _y0=ey[0], _y1=ey[1], _wx=wx, _wy=wy, _n=n - 1, **p))
    cells = [[r['bx'], r['by'], r['v']] for r in rows]
    return dict(kind='heat', agg='count', labels=[], fmt='int',
                xfmt=fmt_of(q.x, ax['type']), yfmt=fmt_of(q.y, ay['type']),
                xlabel=_h(q.x), ylabel=_h(q.y),
                bins=dict(n=n, x0=ex[0], wx=wx, y0=ey[0], wy=wy),
                max=max((c[2] for c in cells), default=0), total=sum(c[2] for c in cells),
                series=[dict(label='Rows', data=cells)])

def _extent(s):
    '''The range to bin over, trimmed to the middle 99% when a tail would otherwise own the
    axis. `y` on the diamonds table runs to 58mm on one typo'd row; binning to it spends
    every cell but one on empty space.'''
    lo, hi = s.get('lo'), s.get('hi')
    if lo is None or hi is None or hi <= lo: return None
    mean, sd = s.get('mean'), s.get('sd') or 0
    if mean is not None and sd > 0:
        lo, hi = max(lo, mean - 4 * sd), min(hi, mean + 4 * sd)
    return (lo, hi) if hi > lo else None

# ── correlation ───────────────────────────────────────────────────────────────

def _corr(q):
    '''Pearson r for every pair of measures, in one pass.

    The sums for all pairs come out of a single scan, so the cost is one query however
    many columns there are. Rows missing any measure are dropped rather than dropped
    per pair, which keeps every cell in the matrix computed over the same rows — a matrix
    whose cells disagree about which rows they describe is not one you can read across.'''
    db = get_db(q.db)
    ms = (q.mcols or _measures(q.db, q.t))[:cfg.corr_max]
    if len(ms) < 2: raise ValueError('need two measures to correlate')
    qc = {m: f'{BASE}.{ident(m, q.cols)}' for m in ms}
    sel = ['count(*) as n'] + [f'avg({qc[m]}) as m_{i}' for i, m in enumerate(ms)]
    pairs = [(i, j) for i in range(len(ms)) for j in range(i, len(ms))]
    sel += [f'avg({qc[ms[i]]} * {qc[ms[j]]}) as p_{i}_{j}' for i, j in pairs]
    w, p = _guard(q, *[f'{c} is not null' for c in qc.values()])
    r = db.q(f'select {", ".join(sel)} from {q.tq} {BASE} {q.joins} {w}', p)[0]
    if not r['n']: raise ValueError('no rows with every measure present')
    cov = {(i, j): r[f'p_{i}_{j}'] - r[f'm_{i}'] * r[f'm_{j}'] for i, j in pairs}
    sd = [max(0.0, cov[(i, i)]) ** 0.5 for i in range(len(ms))]
    m = [[None] * len(ms) for _ in ms]
    for i, j in pairs:
        v = cov[(i, j)] / (sd[i] * sd[j]) if sd[i] and sd[j] else None
        m[i][j] = m[j][i] = None if v is None else max(-1.0, min(1.0, v))
    return dict(kind='corr', agg='count', fmt='float', n=r['n'],
                labels=[_h(c) for c in ms], cols=ms, matrix=m,
                series=[dict(label='r', data=m)])

def _measures(db, tbl):
    from .infer import roles
    return [c for c, s in roles(db, tbl).items() if s.role == 'measure']

def best_pair(db, tbl):
    '''The two measures worth putting on a pair of axes.

    Picking the first two columns in declared order is how a diamonds dashboard ends up
    charting price against depth — a genuine non-relationship, drawn at full size. The pair
    with the strongest correlation is the one with something to show.

    Above r = 0.95 the two columns are the same quantity written down twice (a diamond's x
    and y are its width and its length, and every stone is round), and a scatter of those
    is a picture of a straight line. Those are skipped, which leaves the strongest
    *informative* pair rather than the strongest one.'''
    def compute():
        ms = _measures(db, tbl)
        if len(ms) < 2: return None
        m = _corr(_check(dict(db=db, t=tbl, kind='corr', agg='count', cols=','.join(ms[:cfg.corr_max]),
                              f=[])))
        cols, best = m['cols'], None
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = m['matrix'][i][j]
                if r is None or abs(r) > 0.95: continue
                if not best or abs(r) > best[2]: best = (cols[i], cols[j], abs(r))
        return list(best[:2]) if best else None
    try: return cached(db, tbl, 'pair', compute)
    except ValueError: return None

def _hist(q):
    db = get_db(q.db)
    s = profile(q.db, q.t)['cols'][q.x]
    lo, hi = s.get('lo'), s.get('hi')
    if lo is None or hi is None or hi == lo: raise ValueError('column has no spread to bin')
    bins = cfg.hist_bins
    w = (hi - lo) / bins
    # bin edges come from the unfiltered profile on purpose: the same column keeps the same
    # axis whatever is filtered, so two filters can be compared instead of just read
    wh, p = _guard(q, f'{BASE}.{q.xq} is not null')
    sel = f'min(cast(({BASE}.{q.xq} - :lo) / :w as integer), :top) as b, count(*) as v'
    grp = 'b' + (', g' if q.sp else '')
    if q.sp: sel += f', {q.sp.expr} as g'
    rows = db.q(f'select {sel} from {q.tq} {BASE} {q.joins} {wh} group by {grp}',
                dict(lo=lo, w=w, top=bins - 1, **p))
    fmt = fmt_of(q.x, s['type'])
    labels = [_edge(lo + i * w, fmt) for i in range(bins)]
    if not q.sp:
        counts = {r['b']: r['v'] for r in rows}
        series = [dict(label='Rows', data=[counts.get(i, 0) for i in range(bins)])]
    else:
        # overlaid histograms per category: how two distributions sit against each other is
        # a question one histogram of the pooled column cannot be asked
        gt = {}
        for r in rows: gt[r['g']] = gt.get(r['g'], 0) + r['v']
        groups = _groups(gt)
        cell = {(r['b'], r['g']): r['v'] for r in rows}
        gl = _labeller(q.db, q.sp.t, q.sp.c)
        series = [dict(label=gl(g), data=[cell.get((i, g), 0) for i in range(bins)]) for g in groups]
    return dict(kind='bar', agg='hist', labels=labels, fmt='int', xfmt=fmt, series=series,
                stacked=bool(q.get('stack')))

def _edge(v, fmt):
    if fmt == 'ms': return f'{v / 60000:.1f}m'
    if fmt == 'bytes': return f'{v / 1048576:.1f}MB'
    if fmt == 'money': return f'{v:,.2f}'
    return f'{v:,.0f}' if abs(v) >= 100 else f'{v:,.2f}'.rstrip('0').rstrip('.')

SCATTER_MAX = 4000

def _scatter(q):
    '''Raw points, optionally coloured by a category — the shape of iris, and of most of the rest.

    Past a few thousand points the browser is the constraint, so the query takes every
    n-th row rather than the first few thousand. That matters more than it sounds: these
    files are written in sorted order, and `limit 4000` on the diamonds table is a chart
    of the four thousand cheapest diamonds labelled as a chart of all of them.'''
    db = get_db(q.db)
    n = rowcount(q.db, q.t)
    step = max(1, n // SCATTER_MAX)
    w, p = _guard(q, f'{BASE}.{q.xq} is not null', f'{BASE}.{q.yq} is not null',
                  f'{BASE}.rowid % :_st = 0' if step > 1 else None)
    if step > 1: p = dict(_st=step, **p)
    sel = f'{BASE}.{q.xq} as x, {BASE}.{q.yq} as y' + (f', {q.sp.expr} as g' if q.sp else '')
    rows = db.q(f'select {sel} from {q.tq} {BASE} {q.joins} {w} limit :_lim', dict(_lim=SCATTER_MAX, **p))
    out = dict(kind='scatter', agg='raw', labels=[], fmt=fmt_of(q.y, ''), xfmt=fmt_of(q.x, ''),
               xlabel=_h(q.x), ylabel=_h(q.y),
               xlog=_log([r['x'] for r in rows]), log=_log([r['y'] for r in rows]),
               note=f'every {step:,}th row · {len(rows):,} of {n:,}' if step > 1 else None)
    if not q.sp:
        out['series'] = [dict(label=f'{_h(q.y)} vs {_h(q.x)}', data=[dict(x=r['x'], y=r['y']) for r in rows])]
        return out
    by = {}
    for r in rows: by.setdefault(r['g'], []).append(dict(x=r['x'], y=r['y']))
    groups = _groups({g: len(v) for g, v in by.items()})
    gl = _labeller(q.db, q.sp.t, q.sp.c)
    out['series'] = [dict(label=gl(g), data=by[g]) for g in groups]
    out['split'] = dict(t=q.sp.t, c=q.sp.c, keys=[None if g is None else str(g) for g in groups])
    return out

# ── stats & sparklines (server-rendered, no JS) ───────────────────────────────

def stats(db, tbl, col, fs=()):
    '''Mean, σ and the quantiles that make a stat tile worth reading.

    A quantile is `order by ... limit 1 offset k`, which sqlite answers by sorting the
    whole column into a temp b-tree: on 336,776 flights that is a third of a second, twice,
    for a tile that says the same thing every time the page is drawn. Unfiltered, it is a
    fact about the table, so it is cached like one. Filtered, it has to be measured.'''
    s = profile(db, tbl)['cols'][col]
    if s['kind'] != 'num' or not s.get('sd'): return None
    if fs: return _stats(db, tbl, col, fs)
    # `fs` rather than the compiled `where`: a filter that does not reach this table
    # compiles to nothing, and caching that under the unfiltered key would be right by
    # accident today and wrong the first time the compiler learns a new route
    v = cached(db, tbl, f'stats.{col}', lambda: _as_dict(_stats(db, tbl, col)))
    return AttrDict(v) if v else None

def _as_dict(o): return dict(o) if o else None

def _stats(db, tbl, col, fs=()):
    s = profile(db, tbl)['cols'][col]
    t, qc = _t(db, tbl), ident(col, _cols(db, tbl))
    w = where(db, tbl, fs)
    nn = f'{qc} is not null' + (f' and {w.sql}' if w.sql else '')
    n = t.count_where(nn, w.params)
    if not n: return None
    def pick(frac):
        r = list(t.rows_where(nn, w.params, order_by=qc, select=qc, limit=1, offset=max(0, int(n * frac) - 1)))
        return r[0][col] if r else None
    a = AttrDict(mean=s['mean'], sd=s['sd'], lo=s['lo'], hi=s['hi'])
    if w.sql:
        # the cached profile describes the whole column; once something is filtered out the
        # tile has to be measured, or it reports the mean of rows it is no longer showing
        r = get_db(db).q(f'select avg({qc}) as mean, avg({qc}*{qc}) as m2, min({qc}) as lo, '
                         f'max({qc}) as hi from {ident(tbl, table_names(db))} where {nn}', w.params)[0]
        a = AttrDict(mean=r['mean'], lo=r['lo'], hi=r['hi'],
                     sd=max(0.0, (r['m2'] or 0) - (r['mean'] or 0) ** 2) ** 0.5)
    return AttrDict(n=n, **a, median=pick(0.5), p95=pick(0.95), fmt=fmt_of(col, s['type']))

def sparkline(vals, w=120, h=28):
    'Inline SVG polyline — no canvas, no JS, inherits the theme through currentColor.'
    from fastcore.xml import Svg, Polyline, FT
    vals = [v for v in vals if v is not None]
    if len(vals) < 2: return None
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    step = w / (len(vals) - 1)
    pts = ' '.join(f'{i * step:.1f},{h - (v - lo) / rng * (h - 2) - 1:.1f}' for i, v in enumerate(vals))
    return Svg(Polyline(points=pts, fill='none', stroke='var(--chart-1)', stroke_width='1.5',
                        stroke_linejoin='round', stroke_linecap='round'),
               viewBox=f'0 0 {w} {h}', preserveAspectRatio='none', cls='spark', aria_hidden='true')

def headline(db, fs=()):
    'The handful of numbers worth putting above the charts, found the same way the charts are.'
    from .data import schema
    from .infer import roles, _h
    sch = schema(db)
    rows, all_rows = sum(count_rows(db, t, fs) for t in sch), sum(rowcount(db, t) for t in sch)
    tiles = [AttrDict(label='Tables', value=f'{len(sch):,}'),
             AttrDict(label='Rows', value=f'{rows:,}', sub=f'of {all_rows:,}' if fs else None)]
    # a summed *total* is revenue; a summed *unit price* is nothing anybody asked for,
    # so per-unit columns only get the headline when there is no true total anywhere
    best = None
    for rank, pat in enumerate((r'total|revenue|amount|sales', r'price|cost|balance')):
        for t in sch:
            rl = roles(db, t)
            money = [c for c, s in rl.items() if s.role == 'measure' and re.search(pat, c, re.I)
                     and (s.get('total') or 0) > 0]
            if not money: continue
            c = max(money, key=lambda c: rl[c].total)
            if not best or rl[c].total > best[2]: best = (t, c, rl[c].total)
        if best: break
    if not best: return tiles + _lead_tiles(db, sch, fs)
    t, c, total = best
    # which column leads is decided from the whole database, so the dashboard keeps its
    # subject as facets come and go; only the numbers on the tile move with the filter
    if fs: total = _sum(db, t, c, fs)
    st = stats(db, t, c, fs)
    spark = None
    tcol = next((k for k, s in roles(db, t).items() if s.role == 'temporal'), None)
    if tcol:
        pl = payload(dict(db=db, t=t, kind='line', x=tcol, y=c, agg='sum', bucket='%Y-%m', fs=fs))
        spark = pl['series'][0]['data']
    lbl = _h(c) if re.match(r'total', c, re.I) else f'Total {_h(c)}'
    tiles.append(AttrDict(label=lbl, value=_money(total), spark=spark,
                          sub=f'{_h(t)} · {count_rows(db, t, fs):,} rows'))
    if st: tiles += [AttrDict(label=f'Mean {_h(c).lower()}', value=_money(st.mean), sub=f'median {_money(st.median)}'),
                     AttrDict(label='Std deviation', value=_money(st.sd), sub=f'p95 {_money(st.p95)}')]
    return tiles

def _lead_tiles(db, sch, fs):
    '''Tiles for a database with nothing to add up.

    Half of these have no money and no dates in them at all, and "2 tables, 891 rows" is
    not a summary of anything. What they do have is a measure worth a mean, and a category
    the rows fall into — so the tiles report the centre and spread of the widest table's
    leading measure, and how many groups the biggest category has. Which measure leads is
    decided from the unfiltered database, so the tiles keep their subject as facets come
    and go.'''
    from .infer import roles, _h, label_col
    t = max(sch, key=lambda t: rowcount(db, t))
    rl = roles(db, t)
    ms = [c for c, s in rl.items() if s.role == 'measure' and (s.get('sd') or 0) > 0]
    out = []
    if ms:
        c = max(ms, key=lambda c: rl[c].distinct)
        st = stats(db, t, c, fs)
        if st:
            out.append(AttrDict(label=f'Mean {_h(c).lower()}', value=_num(st.mean),
                                sub=f'{_h(t)} · median {_num(st.median)}'))
            out.append(AttrDict(label='Std deviation', value=_num(st.sd),
                                sub=f'{_num(st.lo)} – {_num(st.hi)}'))
    # a rate is the one number a two-valued column has, and it is usually the headline
    # the table was collected to produce
    for c, s in rl.items():
        if s.role != 'bool': continue
        w = where(db, t, fs)
        sql = f'select avg({ident(c, _cols(db, t))}) as v from {ident(t, table_names(db))}'
        v = get_db(db).q(sql + (f' where {w.sql}' if w.sql else ''), w.params)[0]['v']
        if v is not None:
            out.append(AttrDict(label=f'{_h(c)} rate', value=f'{v * 100:,.1f}%', sub=_h(t)))
        break
    for k, r in sch.items():
        lab = label_col(db, k, strict=True)
        if lab and k != t:
            out.append(AttrDict(label=_h(k), value=f'{rowcount(db, k):,}', sub='distinct values'))
            break
    return out[:3]

def _num(v):
    try:
        f = float(v)
        return f'{f:,.0f}' if abs(f) >= 1000 else f'{f:,.3g}'
    except Exception: return str(v)

def _money(v):
    try: return f'{float(v):,.2f}'
    except Exception: return str(v)

# ── row access for the explorer ───────────────────────────────────────────────

def _t(db, tbl):
    if tbl not in table_names(db): raise KeyError(tbl)
    return get_db(db).t[tbl]

def page_rows(db, tbl, page=0, fs=(), sort=None, desc=False):
    order = f'{ident(sort, _cols(db, tbl))} {"desc" if desc else "asc"}' if sort else None
    w = where(db, tbl, fs)
    return list(_t(db, tbl).rows_where(w.sql or None, w.params, order_by=order,
                                       limit=cfg.rows_per_page, offset=page * cfg.rows_per_page))

def count_rows(db, tbl, fs=()):
    'Rows a table has under the active filter; its plain count when nothing reaches it.'
    w = where(db, tbl, fs) if fs else None
    return _t(db, tbl).count_where(w.sql, w.params) if w and w.sql else rowcount(db, tbl)

def _sum(db, tbl, col, fs):
    w = where(db, tbl, fs)
    sql = f'select sum({ident(col, _cols(db, tbl))}) as v from {ident(tbl, table_names(db))}'
    return get_db(db).q(sql + (f' where {w.sql}' if w.sql else ''), w.params)[0]['v'] or 0

def row_get(db, tbl, pk):
    '''One row by primary key, or None when the table has no single-column key to look it
    up by. A composite key needs every part, and a row page is reached from a URL carrying
    one value — so those tables have rows to list but no row page.'''
    if len(reflect(db, tbl).pk) != 1: return None
    return _t(db, tbl).get(pk, as_cls=False, default=None)

def _where(db, child, col): return f'{ident(col, _cols(db, child))} = :v'

def child_count(db, child, col, val):
    return _t(db, child).count_where(_where(db, child, col), dict(v=val))

def child_rows(db, child, col, val, limit=None):
    return list(_t(db, child).rows_where(_where(db, child, col), dict(v=val), limit=limit or cfg.rel_preview))
