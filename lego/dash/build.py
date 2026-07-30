'''Charts the reader composes, rather than the ones the picker chose.

The inferred dashboard answers "what is in here". It cannot answer "show me average tip by
day, split by whether they smoked", because nobody asked it that. This module is the other
half: the same `Spec`, the same `/dash/chart.json`, assembled from six selects instead of
from the schema.

Nothing is stored. A composed chart lives in the URL as one `c=` parameter holding its
query string, exactly as a filter lives in an `f=`. So a dashboard somebody built is a link
they can send, the back button removes the last chart they added, and the server keeps no
per-user state to expire, migrate or leak. Every `c=` is re-validated on arrival by the
same `_check` the chart endpoint uses, so a hand-edited URL can no more reach SQL here than
it can there.

The vocabulary of a composed chart is deliberately the picker's own: a dimension is
whatever `_cats` says the table can be grouped by, which means "Cut" is offered as a
category even though the column holding it is an integer on another table.
'''
from urllib.parse import urlencode, parse_qsl
from fastcore.all import AttrDict
from .cfg import cfg
from .data import DBS, table_names, reflect, rowcount
from .infer import Spec, roles, _cats, _axes, agg_for, _h, _plural

__all__ = ['KINDS', 'AGGS', 'options', 'compose', 'pins', 'pin_qs', 'wire_pin']

# What the builder offers, in the order the selects list it. `needs` is what a kind cannot
# be drawn without, and is the whole of the validation the form does — everything else is
# caught by the chart endpoint, which has to catch it anyway.
KINDS = [
    ('bar',      'Bars',              ('cat',)),
    ('hbar',     'Bars, sideways',    ('cat',)),
    ('line',     'Line',              ('cat',)),
    ('area',     'Area',              ('cat',)),
    ('doughnut', 'Share of total',    ('cat',)),
    ('box',      'Spread (box)',      ('cat', 'y')),
    ('scatter',  'Scatter',           ('x', 'y')),
    ('heat',     'Density',           ('x', 'y')),
    ('corr',     'Correlation',       ()),
]
AGGS = [('count', 'count of rows'), ('sum', 'sum of'), ('avg', 'average of')]
_KIND = {k: (lbl, needs) for k, lbl, needs in KINDS}

def _tok(c): return ('own:' if c.own else 'ref:') + (c.on.get('x') or c.on.get('jcol'))

def options(db, tbl):
    '''Everything the form needs to describe one table: its categories, its measures and
    the ordered axes that make a line mean something.'''
    if tbl not in table_names(db): raise KeyError(tbl)
    rl = roles(db, tbl)
    cats = [AttrDict(tok=_tok(c), label=f'{c.title} · {c.nd:,}', **c) for c in _cats(db, tbl)]
    axes = {a.c: a for a in _axes(db, tbl)}
    for a in axes.values():
        if not any(c.own and c.on.get('x') == a.c for c in cats):
            # an ordered column is not in `_cats` by design — the picker puts it on a line
            # instead. The builder still has to offer it, or "signal by timepoint" is a
            # chart the dashboard draws and the reader cannot ask for.
            cats.append(AttrDict(tok=f'own:{a.c}', label=f'{_h(a.c)} · {a.nd:,}', t=tbl, c=a.c,
                                 nd=a.nd, title=_h(a.c), own=True, on=dict(x=a.c), split=dict(s=a.c)))
    return AttrDict(
        table=tbl, cats=cats, axes=axes,
        measures=[c for c, s in rl.items() if s.role in ('measure', 'bool')],
        splits=[c for c in cats if 2 <= c.nd <= cfg.max_series],
        rows=rowcount(db, tbl))

def _find(opts, tok, key):
    for c in opts.cats:
        if c.tok == tok: return dict(c[key])
    return None

def compose(db, p):
    '''One `Spec` from the builder's raw form fields, or None when they do not describe a
    chart. Returning None rather than raising is deliberate: a half-filled form is the
    normal state of a form, not an error to show somebody.'''
    tbl = p.get('bt')
    if not tbl or tbl not in table_names(db): return None
    kind = p.get('bkind') or 'bar'
    if kind not in _KIND: return None
    opts = options(db, tbl)
    agg = p.get('bagg') if p.get('bagg') in dict(AGGS) else 'count'
    y = p.get('by') if p.get('by') in opts.measures else None
    cat = _find(opts, p.get('bx'), 'on')
    split = _find(opts, p.get('bs'), 'split')
    needs = _KIND[kind][1]
    spec = dict(db=db, t=tbl, kind=kind, agg=agg)
    if kind == 'corr': spec.update(agg='count')
    elif kind in ('scatter', 'heat'):
        # both axes are measures here, so the group-by select is read as the second one and
        # the aggregate does not apply — there is nothing to aggregate over
        x = str(p.get('bx') or '').split(':', 1)[-1]
        if not (x and y) or x not in opts.measures or x == y: return None
        spec.update(x=x, y=y, agg='raw' if kind == 'scatter' else 'count')
    else:
        if agg == 'count': y = None
        elif not y: return None
        if 'cat' in needs and not cat: return None
        if 'y' in needs and not y: return None
        spec.update(y=y, **(cat or {}))
        a = opts.axes.get(spec.get('x'))
        # an ordered axis reads left to right whatever kind was asked for; a line through
        # categories sorted by size is a shape with no meaning
        if a: spec.update(bucket=a.bucket) if a.bucket else spec.update(ord=1)
    if split and kind not in ('corr',): spec.update(split)
    if split and kind in ('bar', 'hbar') and str(p.get('bstack') or '') in ('1', 'on'): spec.update(stack=1)
    return Spec({**spec, 'score': 0, 'custom': True, **_titled(db, tbl, spec, cat, split, y, agg, kind)})

def _titled(db, tbl, spec, cat, split, y, agg, kind):
    'A sentence describing what was asked for, in the same voice the picker writes in.'
    # "Total total bill" — a column already named for its aggregate keeps its own name
    total = _h(y) if y and y.lower().startswith('total') else f'Total {_h(y).lower()}' if y else ''
    what = {'count': _plural(tbl), 'sum': total,
            'avg': f'Average {_h(y).lower()}' if y else ''}.get(agg) or _plural(tbl)
    if kind == 'corr': return dict(title=f'How {_h(tbl).lower()} measures move together',
                                   why='Pearson r across every numeric column')
    if kind in ('scatter', 'heat'):
        t = f'{_h(y)} vs {_h(spec["x"])}'
        why = 'each row a point' if kind == 'scatter' else 'every row counted into a grid of cells'
    elif kind == 'box':
        t, why = f'{_h(y)} spread by {_catname(db, tbl, cat)}', 'median, middle half and 5th–95th'
    else:
        t, why = f'{what} by {_catname(db, tbl, cat)}', f'{agg} over {_plural(tbl).lower()}'
    if split: t += f', per {_splitname(db, tbl, split)}'
    return dict(title=t, why=f'{why} · built by hand')

def _catname(db, tbl, cat):
    if not cat: return _h(tbl)
    return _h(cat.get('join') or cat.get('x'))

def _splitname(db, tbl, split):
    return _h(split.get('sj') or split.get('s'))

# ── the wire format ───────────────────────────────────────────────────────────

def wire_pin(spec): return urlencode(spec.qs)

def pin_qs(pins, extra=()):
    return [('c', wire_pin(s)) for s in pins] + list(extra)

def pins(db, raw):
    '''Composed charts off the `c=` parameters, dropped rather than corrected when they no
    longer describe anything — the same rule the filters follow.'''
    from .charts import _check
    out, seen = [], set()
    for s in (raw or [])[:cfg.max_charts]:
        p = dict(parse_qsl(str(s)))
        if p.get('db') not in (None, db): continue
        p['db'] = db
        try: _check(dict(p, f=[]))
        except (ValueError, KeyError): continue
        spec = Spec({'score': 0, 'custom': True, **p,
                     **_titled(db, p['t'], p, _cat_of(p), _split_of(p), p.get('y'), p.get('agg'), p['kind'])})
        if spec.key in seen: continue
        seen.add(spec.key)
        out.append(spec)
    return out

def _cat_of(p):
    if p.get('join'): return dict(join=p['join'], jcol=p.get('jcol'), jlabel=p.get('jlabel'), title=_h(p['join']))
    return dict(x=p['x'], title=_h(p['x'])) if p.get('x') else None

def _split_of(p):
    if p.get('sj'): return dict(sj=p['sj'], scol=p.get('scol'), slabel=p.get('slabel'))
    return dict(s=p['s']) if p.get('s') else None
