import re
from fastcore.all import AttrDict, L
from .cfg import cfg
from .data import reflect, schema, profile, rowcount

__all__ = ['roles', 'label_col', 'specs_for_table', 'specs_for_db', 'fmt_of', 'agg_for', 'Spec']

# name heuristics — a column's declared type only gets you so far
_MEASURE = re.compile(r'total|price|amount|cost|value|revenue|sales|qty|quantity|count|score|rate|'
                      r'duration|millisec|bytes|size|weight|length|balance|salary', re.I)
_TEMPORAL = re.compile(r'date|_at$|time$|timestamp|year|month|created|updated|birth|hire', re.I)
_LABEL = re.compile(r'name|title|label|subject|description', re.I)
_MONEY = re.compile(r'price|total|amount|cost|revenue|sales|salary|balance', re.I)
# Which measure a table leads with. Twenty numeric columns is common and alphabetical order
# is not an opinion about any of them — a Factbook dashboard headed by `area` because it
# sorts before `population` has picked the least interesting column in the table.
_LEAD = re.compile(r'^total|revenue|sales|amount|price|population|gdp|income|passengers|'
                   r'score|rating|signal|mpg|fare', re.I)
# …and a *level* leads over a rate of change. "GDP growth by country" is a real chart and
# a poor first impression of a table that also holds GDP per head.
_DELTA = re.compile(r'growth|inflation|rate$|_rate|change', re.I)

def _rank(c):
    'Sort order for the measures a table offers. Lower leads.'
    if _MONEY.search(c): return 0
    if _LEAD.search(c): return 2 if _DELTA.search(c) else 1
    return 3
_ISO = re.compile(r'^\d{4}-\d{2}-\d{2}')
# Adding these up answers something; adding up the others does not. The sum of every
# invoice is the revenue, and the sum of every unit price is a number no one asked for —
# it tracks how many products there are. So a measure carries the aggregate that suits it
# rather than the one that is easiest to write.
_ADDITIVE = re.compile(r'^total|amount|revenue|sales|freight|qty|quantity|count|passengers|'
                       r'^sibsp$|^parch$|units', re.I)
# an ordered number reads left to right and belongs on a line, not in a top-10 bar chart.
# `order` is deliberately absent: it matches `UnitsOnOrder`, which counts stock rather than
# ordering anything.
_SEQ = re.compile(r'year|month|day|time|point|seq|age|level|coherence', re.I)
# …unless it is an identifier. Subject 1 through 20 is a dense run of integers and a
# perfectly meaningless x axis: the subjects have no order, they have names that are numbers.
_IDENT = re.compile(r'^id$|_id$|^subject$|^number$|^no$|code', re.I)
# A surrogate key is not a category either. `planets.number` counts the planets in a system
# and groups perfectly well, so only the row identifiers are barred here.
_ROWID = re.compile(r'^id$|_id$|^subject$', re.I)

def agg_for(col): return 'sum' if _ADDITIVE.search(col) else 'avg'

def _measureish(nm): return bool(_MEASURE.search(nm))

def roles(db, tbl):
    'Tag every column with the job it can do in a chart: temporal, measure, dimension, ref, key, bool or text.'
    r, p = reflect(db, tbl), profile(db, tbl)
    n, out = p['rows'], {}
    for c in r.cols:
        s = AttrDict(p['cols'][c.name])
        s.role = _role(c.name, s, n, pk=c.name in r.pk, fk=c.name in r.fk_by_col)
        s.fk = r.fk_by_col.get(c.name)
        out[c.name] = s
    return out

def _role(nm, s, n, pk=False, fk=False):
    if fk: return 'ref'
    if s.kind == 'date': return 'temporal'
    if pk: return 'key'
    # an undeclared identifier is still an identifier. `exercise.id` numbers the subjects
    # 1–30 and has a mean and a standard deviation, neither of which is about anything.
    if s.kind == 'num' and _ROWID.search(nm): return 'key'
    if s.distinct <= 1: return 'const'
    # a column that is mostly empty makes a chart about its own missingness
    sparse = s.sampled and s.nulls / s.sampled > 0.5
    if s.kind == 'num':
        intish = 'INT' in s.type.upper()
        if s.distinct == 2 and intish and not _measureish(nm): return 'bool'
        # an integer that never looks like a quantity but repeats a lot is a category (a year,
        # a tier). "A lot" has to be read against the table: forty distinct pulse readings in
        # ninety rows is a measurement, and the same forty across a million rows is a tier.
        if not _measureish(nm) and intish and s.distinct <= min(cfg.max_cats, max(2, n * 0.25)):
            return 'dimension'
        return 'measure' if (s.get('sd') or 0) > 0 else 'const'
    if _TEMPORAL.search(nm) and _ISO.match(str(s.get('lo') or '')): return 'temporal'
    if s.distinct <= cfg.max_cats and s.distinct < n * 0.9 and not sparse: return 'dimension'
    return 'text'

def label_col(db, tbl, strict=False):
    '''The human-readable column to show instead of a raw id when linking to this table.
    strict=True returns None unless the table really names its rows — grouping a chart by
    "Invoice.BillingAddress" because it happened to be the first text column is worse than
    not drawing the chart.

    Two things count as naming. A column called name/title/label, which is what the
    business schemas use. Or a lookup table's one text column, unique across every row:
    `Cut(cut_id, cut)` never says "name" anywhere, but `cut` is unmistakably what a Cut is
    called, and without this every chart over those tables would be grouped by an integer.'''
    r, p = reflect(db, tbl), profile(db, tbl)
    named = [c.name for c in r.cols if _LABEL.search(c.name) and p['cols'][c.name]['kind'] == 'text']
    if named: return max(named, key=lambda c: p['cols'][c]['distinct'])
    txt = [c.name for c in r.cols if p['cols'][c.name]['kind'] == 'text' and c.name not in r.pk]
    if strict:
        n = p['rows']
        sole = txt[0] if len(txt) == 1 and len(r.cols) <= 3 else None
        return sole if sole and n and p['cols'][sole]['distinct'] == n else None
    return txt[0] if txt else (r.pk[0] if r.pk else None)

def fmt_of(nm, typ=''):
    n = nm.lower()
    if re.search(r'millisec', n): return 'ms'
    if re.search(r'bytes|size', n): return 'bytes'
    if re.search(r'price|total|amount|cost|revenue|sales|salary|balance', n): return 'money'
    if 'INT' in (typ or '').upper(): return 'int'
    return 'float'

def _span_years(lo, hi):
    try: return (int(str(hi)[:4]) - int(str(lo)[:4])) or 0
    except Exception: return 0

def _bucket(lo, hi):
    y = _span_years(lo, hi)
    if y >= 8: return 'year', '%Y'
    if y >= 1: return 'month', '%Y-%m'
    return 'day', '%Y-%m-%d'

class Spec(AttrDict):
    'A chart the picker decided is worth drawing. Serialises to the query string of /dash/chart.json.'
    KEYS = ('db', 't', 'kind', 'x', 'y', 'agg', 'bucket', 'join', 'jcol', 'jlabel',
            's', 'sj', 'scol', 'slabel', 'stack', 'ord', 'cols')
    @property
    def qs(self): return {k: self[k] for k in self.KEYS if self.get(k) is not None}
    @property
    def key(self): return '|'.join(f'{k}={v}' for k, v in sorted(self.qs.items()))

def _spec(**kw): return Spec({'score': 0, **kw})

def _kind_for(distinct):
    'Few enough to read as a share, few enough to label upright, or lay it on its side.'
    if distinct <= cfg.pie_cats: return 'doughnut'
    return 'bar' if distinct <= cfg.bar_cats else 'hbar'

# ── what a table offers a chart ───────────────────────────────────────────────

def _cats(db, tbl):
    '''Every category this table can be grouped by, whether it owns the column or reaches
    it through a foreign key.

    Both end up as the same thing to a chart — a set of names to put on an axis — so they
    are one list here, each carrying the spec fragment that puts it on the category axis
    (`on`) or splits a chart into series by it (`split`). Sorted narrowest first: the
    category with four values is the one worth splitting by.'''
    rl, out = roles(db, tbl), []
    taken = {a.c for a in _axes(db, tbl)}   # a column that reads in order is a line, not a ranking
    for c, s in rl.items():
        if s.role in ('dimension', 'bool') and c not in taken and not _ROWID.search(c):
            out.append(AttrDict(t=tbl, c=c, nd=s.distinct, title=_h(c), own=True,
                                on=dict(x=c), split=dict(s=c)))
    for c, s in rl.items():
        if s.role != 'ref' or not s.get('fk'): continue
        f = s.fk
        lab = label_col(db, f.ref_table, strict=True)
        if not lab: continue
        nd = profile(db, f.ref_table)['cols'].get(lab, {}).get('distinct') or rowcount(db, f.ref_table)
        out.append(AttrDict(t=f.ref_table, c=lab, nd=nd, title=_h(f.ref_table), own=False,
                            on=dict(join=f.ref_table, jcol=c, jlabel=lab),
                            split=dict(sj=f.ref_table, scol=c, slabel=lab)))
    # narrowest first, and a parent's label ahead of a raw column of the same width: `Sex`
    # puts "male" and "female" on the axis, `adult_male` puts 0 and 1
    return sorted(out, key=lambda a: (a.nd, a.own))

def _axes(db, tbl):
    '''Columns that carry an order, so a chart over them is a line rather than a ranking.

    A real date is one. So is an integer that counts something off — a year, a model year,
    an fMRI timepoint. Those stay measures as well; being countable in order does not stop
    `mpg.model_year` being a number, it just means putting it on the category axis produces
    a trend instead of a top-10.

    A date leads a dashboard almost every time, so it scores far above the rest. An integer
    run is a good trend but not automatically the story — unless its name says outright
    that it is one, which is the difference between `fmri.timepoint` and `titanic.sibsp`.'''
    rl, n = roles(db, tbl), profile(db, tbl)['rows']
    out = []
    for c, s in rl.items():
        if s.role == 'temporal':
            unit, fmt = _bucket(s.get('lo'), s.get('hi'))
            out.append(AttrDict(c=c, bucket=fmt, unit=unit, on=unit, nd=s.distinct, base=104))
            continue
        if s.role not in ('measure', 'dimension') or s.kind != 'num': continue
        if s.distinct < 4 or s.distinct > cfg.max_cats or s.distinct > n * 0.5: continue
        if _IDENT.search(c): continue
        named = bool(_SEQ.search(c))
        # a *dense run of integers* is a sequence whatever it is called. The integer part
        # matters: 4.3 to 7.9 in 35 steps is dense too, and a sepal is not a timeline. So
        # does how tight the run is — a real sequence very nearly fills its own range, and
        # ten distinct order quantities scattered over 0–100 do not.
        intish = 'INT' in (s.type or '').upper()
        lo, hi = s.get('lo'), s.get('hi')
        dense = intish and lo is not None and hi is not None and (hi - lo + 1) <= s.distinct * 1.5
        # a float only gets on the axis if its name claims an order and it has few enough
        # levels to be one — `dots.coherence` has six, `gammas.timepoint` has hundreds
        if dense or (named and s.distinct <= cfg.bar_cats):
            out.append(AttrDict(c=c, bucket=None, unit=_h(c).lower(), on=_h(c), nd=s.distinct,
                                base=94 if named else 88))
    return sorted(out, key=lambda a: -a.base)

def _places(db, tbl, cats):
    '''Columns that name places, which is not the same set as columns that make categories.

    A column of 255 country names is a hopeless bar chart and so never reaches `_cats` — it
    is `text`, effectively unique, exactly the kind of column the picker is built to refuse.
    On a map it is the best column in the table. So the map rule looks past the category
    list at any column whose values resolve to shapes, and only then falls back to the
    categories, which is where a foreign key to a `Country` lookup would come from.'''
    from .geo import geo_of
    out, seen = [], set()
    for c, s in roles(db, tbl).items():
        if s.role in ('key', 'const'): continue
        g = geo_of(db, tbl, c)
        if not g: continue
        seen.add((tbl, c))
        # `factbook.Country.name` is the table's own label, so "by Country" is what it is
        # by; "by Name" is what the column is called, which is not the same sentence
        title = _h(tbl) if c == label_col(db, tbl) else _h(c)
        out.append(AttrDict(t=tbl, c=c, nd=s.distinct, title=title, own=True, geo=g,
                            on=dict(x=c), split=dict(s=c)))
    for c in cats:
        if (c.t, c.c) in seen: continue
        g = geo_of(db, c.t, c.c)
        if g: out.append(AttrDict({**c, 'geo': g}))
    # the column that puts the most places on the map is the one the table is about
    return sorted(out, key=lambda c: -c.geo.n)

def _rate_cols(db, tbl):
    'Two-valued integers. Their average is a rate, which is the only summary they have.'
    return [c for c, s in roles(db, tbl).items() if s.role == 'bool']

def _determines(db, tbl, cat, col):
    '''Does knowing the category already tell you the column?

    Real schemas carry the same fact twice. Titanic has `survived` as 0/1 *and* `Alive` as
    a lookup of "yes"/"no", and a survival rate broken down by Alive is two bars at 100%
    and 0% — a chart that has passed every check the picker makes and says nothing at all.
    One grouped query settles it, cached against the table like everything else here.'''
    from .charts import _check, BASE
    from .data import get_db, cached, ident, reflect
    def compute():
        q = _check(dict(db=db, t=tbl, kind='bar', agg='count', y=col, f=[], **cat))
        rows = get_db(db).q(f'select count(distinct {BASE}.{q.yq}) as n '
                            f'from {q.tq} {BASE} {q.joins} group by {q.ax.expr}')
        return all((r['n'] or 0) <= 1 for r in rows)
    key = 'det.%s.%s' % (col, cat.get('join') or cat.get('x') or '')
    try: return cached(db, tbl, key, compute)
    except (ValueError, KeyError): return False

# ── the rules ─────────────────────────────────────────────────────────────────

def specs_for_table(db, tbl, limit=None):
    'Score every chart this table can support, best first.'
    rl, p = roles(db, tbl), profile(db, tbl)
    n = p['rows']
    if not n: return []
    base = dict(db=db, t=tbl)
    # summing money is almost always the interesting total; summing durations or byte
    # counts rarely is, so those only lead when nothing better exists
    measures = sorted([c for c, s in rl.items() if s.role == 'measure'],
                      key=lambda c: (_rank(c), c))
    cats, axes, rates = _cats(db, tbl), _axes(db, tbl), _rate_cols(db, tbl)
    # narrow first, and a parent's label ahead of a raw column of the same width: splitting
    # by Sex draws two lines called "male" and "female", splitting by `adult_male` draws
    # two called "0" and "1"
    splits = sorted((c for c in cats if 2 <= c.nd <= cfg.max_series), key=lambda c: (c.nd, c.own))
    out = []
    def add(**kw): out.append(_spec(**base, **kw))
    def other(*not_these):
        'The best split-by that is not already doing another job in this chart.'
        skip = {(t, c) for t, c in not_these}
        return [s for s in splits if (s.t, s.c) not in skip][:1]

    # ── a measure over an ordered axis, split by a category where there is one ──
    dated = sum(1 for a in axes if a.bucket)
    for a in axes[:2]:
        line = dict(bucket=a.bucket) if a.bucket else dict(ord=1)
        over = f'over {_h(a.c)}' + (f', bucketed by {a.unit}' if a.bucket else '')
        # "by month" only names the axis while there is one date column; a table with an
        # ordered date and a shipped date needs both charts to say which one they are
        a.on = a.unit if (a.bucket and dated == 1) else f'{_h(a.c)}'
        for m in measures[:2]:
            if m == a.c: continue    # a measure plotted against itself is a diagonal line
            ag = agg_for(m)
            # the split is what makes this readable on measurement data: one averaged line
            # through fourteen subjects and two brain regions is a line through nothing
            for sp in other((tbl, a.c), (tbl, m)):
                add(kind='line', x=a.c, y=m, agg=ag, **line, **sp.split, score=a.base + 6,
                    title=f'{_h(m)} by {a.on}, per {sp.title}',
                    why=f'{ag} of {_h(m)} {over}, one line per {sp.title.lower()}')
            add(kind='area' if ag == 'sum' else 'line', x=a.c, y=m, agg=ag, **line, score=a.base,
                title=f'{_h(m)} by {a.on}', why=f'{ag} of {_h(m)} {over}')
        for sp in other((tbl, a.c)):
            add(kind='bar', x=a.c, y=None, agg='count', stack=1, **line, **sp.split, score=a.base - 14,
                title=f'{_plural(tbl)} by {a.on}, split by {sp.title}',
                why=f'row volume {over}, stacked by {sp.title.lower()}')
        add(kind='line', x=a.c, y=None, agg='count', **line, score=a.base - 16,
            title=f'{_plural(tbl)} by {a.on}', why=f'row volume {over}')

    # ── a two-valued column averages to a rate, which is what it is for ──
    for rc in rates[:1]:
        # a category that already tells you the answer is barred from both jobs: splitting
        # by it produces the same two useless bars the axis would have
        usable = [c for c in cats if not (c.own and c.c == rc) and not _determines(db, tbl, c.on, rc)]
        keys = {(c.t, c.c) for c in cats} - {(c.t, c.c) for c in usable}
        for c in usable[:4]:
            k = 'bar' if c.nd <= cfg.bar_cats else 'hbar'
            why = f'share of {_h(tbl).lower()} rows where {_h(rc).lower()} is 1'
            for sp in other((tbl, rc), (c.t, c.c), *keys):
                add(kind=k, y=rc, agg='avg', **c.on, **sp.split, score=97,
                    title=f'{_h(rc)} rate by {c.title} and {sp.title}',
                    why=f'{why}, one bar per {sp.title.lower()}')
            add(kind=k, y=rc, agg='avg', **c.on, score=92, title=f'{_h(rc)} rate by {c.title}', why=why)

    # ── a measure against a category, and the category's own frequency ──
    for c in cats:
        k = _kind_for(c.nd)
        wide = k == 'hbar'
        head = f'Top {cfg.top_n} ' if wide else ''
        sc = (80 if c.nd <= cfg.max_cats else 52) - min(c.nd, 40) * 0.4
        why = f'{c.nd:,} distinct {c.title.lower()} values' + (f' · showing {cfg.top_n}' if wide else '')
        if measures:
            m = measures[0]
            ag = agg_for(m)
            bk = 'bar' if k == 'doughnut' else k   # a share-of-total ring cannot show an average
            for sp in other((c.t, c.c), (tbl, m)):
                add(kind=bk, y=m, agg=ag, **c.on, **sp.split, score=sc + 10,
                    title=f'{head}{_h(m)} by {c.title} and {sp.title}',
                    why=f'{why} · {ag} of {_h(m)}, one bar per {sp.title.lower()}')
            add(kind=bk, y=m, agg=ag, **c.on, score=sc + 6,
                title=f'{head}{_h(m)} by {c.title}', why=f'{why} · {ag} of {_h(m)}')
        if k != 'doughnut':
            for sp in other((c.t, c.c)):
                add(kind=k, y=None, agg='count', stack=1, **c.on, **sp.split, score=sc + 2,
                    title=f'{head}{_plural(tbl)} by {c.title}, split by {sp.title}',
                    why=f'{why} · stacked by {sp.title.lower()}')
        # "how many rows per category" is only a question when categories hold more than
        # one row; one state per state is a bar chart of the number 1, ten times over
        if n / max(c.nd, 1) >= 1.5:
            add(kind=k, y=None, agg='count', **c.on, score=sc,
                title=f'{head}{_plural(tbl)} by {c.title}', why=why)

    # ── a measure per place ──
    # Ranked above the bar chart of the same numbers on purpose. When the category *is*
    # geography, the map answers a question the ranking cannot: where the values are next
    # to each other. Top-10 bars of countries hide every regional pattern in the data.
    for c in _places(db, tbl, cats):
        g = c.geo
        where = (f'{g.n} of {c.nd:,} {c.title.lower()} values placed on the '
                 f'{"world" if g.pack == "world" else "US state"} map')
        for m in measures[:2]:
            ag = agg_for(m)
            add(kind='map', y=m, agg=ag, **c.on, score=96,
                title=f'{_h(m)} by {c.title}', why=f'{ag} of {_h(m)} · {where}')
        # one row per place makes a map of the number 1; the measures above still work
        if n / max(c.nd, 1) >= 2:
            add(kind='map', y=None, agg='count', **c.on, score=90 if measures else 96,
                title=f'{_plural(tbl)} by {c.title}', why=where)
        break   # one place column per table is *the* place column

    # ── how a measure is spread inside each category ──
    for c in cats:
        if c.nd > cfg.bar_cats or n / max(c.nd, 1) < cfg.box_min * 2: continue
        for m in measures[:2]:
            add(kind='box', y=m, agg='avg', **c.on, score=76,
                title=f'{_h(m)} spread by {c.title}',
                why=f'median, middle half and 5th–95th of {_h(m)} in each of {c.nd} {c.title.lower()} groups')

    # ── how the measures move together ──
    if len(measures) >= 3:
        add(kind='corr', agg='count', cols=','.join(measures[:cfg.corr_max]), score=70,
            title=f'How {_h(tbl).lower()} measures move together',
            why=f'Pearson r across {min(len(measures), cfg.corr_max)} numeric columns, '
                f'over rows where all of them are present')

    # ── two measures on one pair of axes ──
    if len(measures) >= 2:
        from .charts import best_pair
        a, b = best_pair(db, tbl) or measures[:2]
        if n > 4000:
            # past a few thousand points a scatter draws its own overplotting, not the data
            add(kind='heat', x=a, y=b, agg='count', score=68,
                title=f'Where {_plural(tbl).lower()} sit on {_h(a)} and {_h(b)}',
                why=f'{n:,} rows binned into a {cfg.heat_bins}×{cfg.heat_bins} grid — '
                    f'every row counted, none plotted twice')
        for sp in other((tbl, a), (tbl, b)):
            # on a few hundred measurements this is usually the most legible chart there
            # is: the groups separate, or they visibly do not
            add(kind='scatter', x=a, y=b, agg='raw', **sp.split, score=72 if n <= 4000 else 50,
                title=f'{_h(b)} vs {_h(a)} by {sp.title}',
                why=f'each row a point, coloured by {sp.title.lower()}')
        add(kind='scatter', x=a, y=b, agg='raw', score=44 if n <= 4000 else 30,
            title=f'{_h(b)} vs {_h(a)}', why='two numeric columns on one pair of axes')

    # ── distribution of one measure — the histogram that carries mean/σ ──
    for m in measures:
        s = rl[m]
        if s.distinct < 4: continue
        for sp in other((tbl, m)):
            add(kind='bar', x=m, y=None, agg='hist', **sp.split, score=58,
                title=f'Distribution of {_h(m)} by {sp.title}',
                why=f'σ {_num(s.sd)} · mean {_num(s.mean)} · one distribution per {sp.title.lower()}')
        add(kind='bar', x=m, y=None, agg='hist', score=55,
            title=f'Distribution of {_h(m)}',
            why=f'σ {_num(s.sd)} · mean {_num(s.mean)} over {s.distinct:,} distinct values')

    out = _dedupe(sorted(out, key=lambda s: -s.score))
    return out[:limit] if limit else out

def _shape(s):
    '''What two specs have to share to be the same chart twice.

    Exact repeats come from a table with two date columns reaching the same title. The
    subtler pair is a transposition: "fare by class, split by sex" and "fare by sex, split
    by class" are one chart drawn two ways round, and a dashboard that shows both has spent
    two cards saying one thing. Which of the two survives is the one that scored higher.'''
    cat = (s.get('join') or '', s.get('jlabel') or '', s.get('x') or '')
    sp = (s.get('sj') or '', s.get('slabel') or '', s.get('s') or '')
    return (s.kind if s.kind != 'hbar' else 'bar', s.get('y') or '', s.get('agg'),
            frozenset((cat, sp)) if s.get('bucket') is None else (cat, sp))

def _dedupe(specs):
    seen, keys, out = set(), set(), []
    for s in specs:
        sh, k = _shape(s), s.key
        if sh in seen or k in keys: continue
        seen.add(sh); keys.add(k); out.append(s)
    return out

def specs_for_db(db, limit=None):
    '''Dashboard for a whole database: every table\'s specs pooled, weighted by table, best first.

    Two caps shape what comes out. No table may own the dashboard — on Chinook that keeps
    Track from taking all eight slots. And no chart *kind* may either, which is what stops
    a single-table database from returning eight bar charts that differ only in which
    column they are grouped by.'''
    sch, pool = schema(db), []
    for t in sch:
        n = rowcount(db, t)
        if n < 12: continue   # a dozen rows is a list, not a chart
        w = _weight(n, len(sch[t].fks))
        pool += [Spec({**s, 'score': s.score * w, 'rows': n}) for s in specs_for_table(db, t)]
    want = limit or cfg.max_charts
    # counted off what actually produced charts, not off what has rows: a lookup table of
    # 51 state abbreviations passes the row test and supports nothing, and letting it claim
    # a share of the page is how a one-fact-table database ends up half empty
    wide = len({s.t for s in pool}) or 1
    per_t = max(2, -(-want // wide))
    ranked = sorted(pool, key=lambda s: -s.score)
    picks, byt, byk, seen = [], {}, {}, set()
    # two passes. The first holds every chart kind to two cards, which is what stops a
    # single-table database returning eight bar charts that differ only in the column they
    # group by. The second fills whatever is left over without that rule, because a page
    # eight slots wide and half full is a worse outcome than a third histogram.
    for kindcap in (2, want):
        for s in ranked:
            if len(picks) >= want: break
            sh = (s.t, _shape(s))
            if sh in seen or byt.get(s.t, 0) >= per_t or byk.get(s.kind, 0) >= kindcap: continue
            seen.add(sh)
            picks.append(s)
            byt[s.t] = byt.get(s.t, 0) + 1
            byk[s.kind] = byk.get(s.kind, 0) + 1
    return sorted(picks, key=lambda s: -s.score)[:want]

def _weight(n, nfks):
    'Fact tables — many rows, many foreign keys — make the more interesting charts.'
    from math import log10
    return (0.6 + log10(max(n, 10)) / 5) * (1 + nfks * 0.12)

def _plural(s):
    h = _h(s)
    if h.endswith('s'): return h
    if re.search(r'[^aeiou]y$', h): return h[:-1] + 'ies'    # Country → Countries, not Countrys
    return h + 'es' if re.search(r'(sh|ch|x|z)$', h) else h + 's'

# words that are shouted, not capitalised — "Gdp per capita" reads as a typo
_CAPS = {'gdp': 'GDP', 'id': 'ID', 'url': 'URL', 'api': 'API', 'usa': 'USA', 'us': 'US',
         'uk': 'UK', 'iso': 'ISO', 'bold': 'BOLD', 'roi': 'ROI', 'mpg': 'MPG', 'fmri': 'fMRI'}

def _h(s):
    t = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', str(s)).replace('_', ' ').strip()
    words = [(_CAPS.get(w.lower()) or w) for w in t.split()]
    if words and words[0] not in _CAPS.values(): words[0] = words[0].capitalize()
    return ' '.join(words)
def _num(v):
    try: return f'{float(v):,.2f}'.rstrip('0').rstrip('.')
    except Exception: return str(v)
