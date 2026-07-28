import re
from fastcore.all import AttrDict, L
from .cfg import cfg
from .data import reflect, schema, profile, rowcount

__all__ = ['roles', 'label_col', 'specs_for_table', 'specs_for_db', 'fmt_of', 'Spec']

# name heuristics — a column's declared type only gets you so far
_MEASURE = re.compile(r'total|price|amount|cost|value|revenue|sales|qty|quantity|count|score|rate|'
                      r'duration|millisec|bytes|size|weight|length|balance|salary', re.I)
_TEMPORAL = re.compile(r'date|_at$|time$|timestamp|year|month|created|updated|birth|hire', re.I)
_LABEL = re.compile(r'name|title|label|subject|description', re.I)
_MONEY = re.compile(r'price|total|amount|cost|revenue|sales|salary|balance', re.I)
_ISO = re.compile(r'^\d{4}-\d{2}-\d{2}')

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
    if s.distinct <= 1: return 'const'
    # a column that is mostly empty makes a chart about its own missingness
    sparse = s.sampled and s.nulls / s.sampled > 0.5
    if s.kind == 'num':
        intish = 'INT' in s.type.upper()
        if s.distinct == 2 and intish and not _measureish(nm): return 'bool'
        # an integer that never looks like a quantity but repeats a lot is a category (a year, a tier)
        if not _measureish(nm) and intish and s.distinct <= cfg.max_cats: return 'dimension'
        return 'measure' if (s.get('sd') or 0) > 0 else 'const'
    if _TEMPORAL.search(nm) and _ISO.match(str(s.get('lo') or '')): return 'temporal'
    if s.distinct <= cfg.max_cats and s.distinct < n * 0.9 and not sparse: return 'dimension'
    return 'text'

def label_col(db, tbl, strict=False):
    '''The human-readable column to show instead of a raw id when linking to this table.
    strict=True returns None unless the table has a real name/title column — grouping a
    chart by "Invoice.BillingAddress" because it happened to be the first text column is worse
    than not drawing the chart.'''
    r, p = reflect(db, tbl), profile(db, tbl)
    named = [c.name for c in r.cols if _LABEL.search(c.name) and p['cols'][c.name]['kind'] == 'text']
    if named: return max(named, key=lambda c: p['cols'][c]['distinct'])
    if strict: return None
    txt = [c.name for c in r.cols if p['cols'][c.name]['kind'] == 'text' and c.name not in r.pk]
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
    @property
    def qs(self):
        keys = ('db', 't', 'kind', 'x', 'y', 'agg', 'bucket', 'join', 'jcol', 'jlabel')
        return {k: self[k] for k in keys if self.get(k) is not None}
    @property
    def key(self): return '|'.join(f'{k}={v}' for k, v in sorted(self.qs.items()))

def _spec(**kw): return Spec({'score': 0, **kw})

def _kind_for(distinct):
    'Few enough to read as a share, few enough to label upright, or lay it on its side.'
    if distinct <= cfg.pie_cats: return 'doughnut'
    return 'bar' if distinct <= cfg.bar_cats else 'hbar'

def specs_for_table(db, tbl, limit=None):
    'Score every chart this table can support, best first.'
    rl, p = roles(db, tbl), profile(db, tbl)
    n = p['rows']
    if not n: return []
    by = lambda *want: [c for c, s in rl.items() if s.role in want]
    temporal, dims, refs = by('temporal'), by('dimension', 'bool'), by('ref')
    # summing money is almost always the interesting total; summing durations or byte
    # counts rarely is, so those only lead when nothing better exists
    measures = sorted(by('measure'), key=lambda c: (0 if _MONEY.search(c) else 1, c))
    money = [c for c in measures if _MONEY.search(c)]
    out = []

    # measure over time — the "yearly metrics" case
    for t in temporal[:1]:
        s = rl[t]
        bname, bfmt = _bucket(s.get('lo'), s.get('hi'))
        for m in measures[:2]:
            out.append(_spec(db=db, t=tbl, kind='area', x=t, y=m, agg='sum', bucket=bfmt, score=100,
                             title=f'{_h(m)} by {bname}', why=f'{_h(m)} summed over {_h(t)}, bucketed by {bname}'))
        out.append(_spec(db=db, t=tbl, kind='line', x=t, y=None, agg='count', bucket=bfmt, score=88,
                         title=f'{_h(tbl)} records by {bname}', why=f'row volume over {_h(t)}'))

    # a category against a measure, or just its own frequency
    for d in dims:
        s = rl[d]
        k = _kind_for(s.distinct)
        sc = 80 - min(s.distinct, 40) * 0.4
        head = f'Top {cfg.top_n} ' if k == 'hbar' else ''
        why = f'{s.distinct} distinct {_h(d)} values'
        if k == 'hbar': why += f' · showing {cfg.top_n}'
        if measures:
            m = measures[0]
            out.append(_spec(db=db, t=tbl, kind=k, x=d, y=m, agg='sum', score=sc + 6,
                             title=f'{head}{_h(m)} by {_h(d)}', why=why))
        out.append(_spec(db=db, t=tbl, kind=k, x=d, y=None, agg='count', score=sc,
                         title=f'{head}{_plural(tbl)} by {_h(d)}', why=why))

    # roll up through a foreign key so the category is the parent's name, not its id
    for c in refs:
        f = rl[c].fk
        if not f: continue
        lab = label_col(db, f.ref_table, strict=True)
        if not lab: continue
        pn = profile(db, f.ref_table)['cols'].get(lab, {})
        nd = pn.get('distinct') or rowcount(db, f.ref_table)
        k = _kind_for(nd)
        # a rollup onto thousands of parents is a top-10 list; still useful, but it
        # answers a narrower question than one onto a real category
        sc = 72 if nd <= cfg.max_cats else 45
        agg_y = money[0] if money else None
        head = f'Top {cfg.top_n} ' if k == 'hbar' else ''
        why = f'grouped through {_h(c)} → {f.ref_table}.{lab}'
        if k == 'hbar': why += f' · {cfg.top_n} of {nd:,}'
        out.append(_spec(db=db, t=tbl, kind=k, x=None, y=agg_y, agg='sum' if agg_y else 'count',
                         join=f.ref_table, jcol=c, jlabel=lab, score=sc,
                         title=head + f'{_h(agg_y) + " by " if agg_y else _plural(tbl) + " by "}{_h(f.ref_table)}',
                         why=why))

    # distribution of a measure — the histogram that carries mean/σ
    for m in measures:
        s = rl[m]
        if s.distinct < 4: continue
        out.append(_spec(db=db, t=tbl, kind='bar', x=m, y=None, agg='hist', score=55,
                         title=f'Distribution of {_h(m)}',
                         why=f'σ {_num(s.sd)} · mean {_num(s.mean)} over {s.distinct} distinct values'))

    # two measures against each other
    if len(measures) >= 2:
        a, b = measures[0], measures[1]
        out.append(_spec(db=db, t=tbl, kind='scatter', x=a, y=b, agg='raw', score=40,
                         title=f'{_h(b)} vs {_h(a)}', why='two numeric columns on one pair of axes'))

    out = sorted(out, key=lambda s: -s.score)
    return out[:limit] if limit else out

def specs_for_db(db, limit=None):
    'Dashboard for a whole database: every table\'s specs pooled, weighted by table, best first.'
    sch, pool = schema(db), []
    for t in sch:
        n = rowcount(db, t)
        if n < 12: continue   # a dozen rows is a list, not a chart
        w = _weight(n, len(sch[t].fks))
        pool += [Spec({**s, 'score': s.score * w, 'rows': n}) for s in specs_for_table(db, t)]
    picks, per = [], {}
    for s in sorted(pool, key=lambda s: -s.score):
        if per.get(s.t, 0) >= 2: continue   # no single table gets to own the dashboard
        picks.append(s); per[s.t] = per.get(s.t, 0) + 1
        if len(picks) >= (limit or cfg.max_charts): break
    return picks

def _weight(n, nfks):
    'Fact tables — many rows, many foreign keys — make the more interesting charts.'
    from math import log10
    return (0.6 + log10(max(n, 10)) / 5) * (1 + nfks * 0.12)

def _plural(s):
    h = _h(s)
    return h if h.endswith('s') else h + 'es' if re.search(r'(sh|ch|x|z)$', h) else h + 's'

def _h(s): return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', str(s)).replace('_', ' ').strip().capitalize()
def _num(v):
    try: return f'{float(v):,.2f}'.rstrip('0').rstrip('.')
    except Exception: return str(v)
