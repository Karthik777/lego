'''Filtering for the dashboards block.

One filter is `table:column:op:value`, carried in repeated `f=` query parameters, so a
filtered dashboard is a URL you can share and the back button undoes a facet. Nothing is
stored server-side and nothing is remembered between requests.

The part worth explaining is *cross-table* filtering. "Only AC/DC" is a predicate on
`Artist.Name`, but the chart you want it to change is drawn from `Track`, or from
`InvoiceLine`, and those tables have no artist column. So a filter is not applied
literally: it is applied through the foreign keys the schema already declares, walked in
both directions (down to a parent, up into a child) and rendered as a correlated EXISTS.
Track → Album → Artist is two hops; Invoice → InvoiceLine → Track → Album → Artist is
four. Tables with no route to the filtered one are reported as *dropped* rather than
silently returning everything, because a chart that quietly ignored the filter next to
charts that honoured it would be read as data.
'''
import re
from fastcore.all import AttrDict
from .cfg import cfg
from .data import get_db, table_names, reflect, schema, profile, ident, cached
from .infer import roles, _h

__all__ = ['OPS', 'SEP', 'parse', 'wire', 'describe', 'applies', 'where', 'merge',
           'columns', 'ops_for', 'values_for', 'path']

SEP = ':'

# `sql` is formatted with the qualified column and the bind placeholder; `wrap` reshapes the
# bound value instead of the SQL, which keeps LIKE patterns out of the user's typed text
OPS = AttrDict(
    eq   = AttrDict(lbl='is',           sql='{c} = {p}',      kinds='num text date'),
    ne   = AttrDict(lbl='is not',       sql='{c} <> {p}',     kinds='num text date'),
    ct   = AttrDict(lbl='contains',     sql='{c} like {p}',   kinds='text',      wrap='%{}%'),
    sw   = AttrDict(lbl='starts with',  sql='{c} like {p}',   kinds='text date', wrap='{}%'),
    ge   = AttrDict(lbl='at least',     sql='{c} >= {p}',     kinds='num date'),
    le   = AttrDict(lbl='at most',      sql='{c} <= {p}',     kinds='num date'),
    gt   = AttrDict(lbl='more than',    sql='{c} > {p}',      kinds='num'),
    lt   = AttrDict(lbl='less than',    sql='{c} < {p}',      kinds='num'),
    nul  = AttrDict(lbl='is empty',     sql='{c} is null',    kinds='num text date', noval=True),
    nnul = AttrDict(lbl='is not empty', sql='{c} is not null', kinds='num text date', noval=True),
)

def ops_for(kind): return [(k, o.lbl) for k, o in OPS.items() if kind in o.kinds.split()]

def _cols(db, t): return {c.name for c in reflect(db, t).cols}

def _kind(db, t, c): return profile(db, t)['cols'][c]['kind']

# ── the wire format ───────────────────────────────────────────────────────────

def wire(f):
    'The query-string form of a filter. The value goes last so it may contain colons.'
    return SEP.join((f.t, f.c, f.op, f.v))

def parse(db, raw):
    '''Validated filters from the raw `f=` parameters. Every identifier has to match
    something the schema reported; anything else is dropped rather than corrected, on the
    same principle as the chart endpoint — a hand-edited URL never reaches SQL.'''
    out, seen = [], set()
    for s in (raw or []):
        p = str(s).split(SEP, 3)
        if len(p) < 3: continue
        t, c, op = p[0], p[1], p[2]
        v = p[3] if len(p) > 3 else ''
        if t not in table_names(db) or c not in _cols(db, t) or op not in OPS: continue
        if OPS[op].get('noval'): v = ''
        elif not v: continue
        f = AttrDict(t=t, c=c, op=op, v=v)
        k = wire(f)
        if k in seen: continue
        seen.add(k); out.append(f)
        if len(out) >= cfg.max_filters: break
    return out

def merge(db, fs, fc, fop, fv):
    'Fold the add-filter form back into the list. `fc` is the `table:column` the select carried.'
    if not fc or SEP not in str(fc): return fs
    t, c = str(fc).split(SEP, 1)
    return parse(db, [wire(f) for f in fs] + [SEP.join((t, c, str(fop or 'eq'), str(fv or '')))])

def describe(f, tbl=None):
    'Chip text. The table is implied when you are already looking at it.'
    head = _h(f.c) if f.t == tbl else f'{f.t}.{_h(f.c)}'
    return f'{head} {OPS[f.op].lbl}' + ('' if OPS[f.op].get('noval') else f' {f.v}')

# ── routes through the foreign keys ───────────────────────────────────────────

_hops, _paths = {}, {}

def _neighbours(db):
    '''One hop between two tables, both ways round each declared foreign key.
    A hop is (column on the current table, next table, column on the next table), which
    is the same shape either way and so joins the same way.'''
    if db not in _hops:
        sch, out = schema(db), {}
        for t, r in sch.items():
            for f in r.fks:
                if f.ref_table not in sch: continue
                out.setdefault(t, []).append((f.col, f.ref_table, f.ref_col))
                out.setdefault(f.ref_table, []).append((f.ref_col, t, f.col))
        _hops[db] = {t: sorted(set(v)) for t, v in out.items()}   # sorted: one route, deterministically
    return _hops[db]

def path(db, src, dst):
    '''The shortest foreign-key route from `src` to `dst`, or None when there is none.
    Shortest wins on the assumption that the closest relationship is the intended one —
    Track → Album → Artist, not Track → InvoiceLine → Invoice → Customer.'''
    if src == dst: return []
    key = (db, src, dst)
    if key in _paths: return _paths[key]
    nb, seen, level, found = _neighbours(db), {src}, [(src, [])], None
    for _ in range(cfg.max_hops):          # breadth-first, a hop at a time, so the first hit is the shortest
        nxt = []
        for t, sofar in level:
            for hop in nb.get(t, ()):
                if hop[1] in seen: continue
                if hop[1] == dst: found = sofar + [hop]; break
                seen.add(hop[1]); nxt.append((hop[1], sofar + [hop]))
            if found: break
        if found or not nxt: break
        level = nxt
    _paths[key] = found
    return found

def applies(db, base, f):
    'Can this filter reach `base`? Charts over a table with no route say so instead of ignoring it.'
    return f.t == base or path(db, base, f.t) is not None

# ── SQL ───────────────────────────────────────────────────────────────────────

def _bind(db, f):
    'The value as SQLite will compare it — a text bind against an INTEGER column matches nothing.'
    w = OPS[f.op].get('wrap')
    if w: return w.format(f.v)
    if _kind(db, f.t, f.c) == 'num':
        try: return int(f.v) if re.fullmatch(r'\s*-?\d+\s*', f.v) else float(f.v)
        except ValueError: return f.v
    return f.v

def _preds(db, fs, alias, params):
    '''Predicates for filters that all name one table: two values for the same column read
    as "either", every other pairing as "and". That is what a facet list means when you
    tick two boxes, and the only reading under which ticking a second one widens the result.'''
    cols, out, bycol = _cols(db, fs[0].t), [], {}
    for f in fs: bycol.setdefault(f.c, []).append(f)
    for c, g in bycol.items():
        q = f'{alias}.{ident(c, cols)}'
        def bind(f):
            k = 'f%d' % len(params)
            params[k] = _bind(db, f)
            return OPS[f.op].sql.format(c=q, p=f':{k}')
        eqs = [f for f in g if f.op == 'eq']
        if eqs: out.append('(%s)' % ' or '.join(bind(f) for f in eqs))
        out += [OPS[f.op].sql.format(c=q, p='') if OPS[f.op].get('noval') else bind(f)
                for f in g if f.op != 'eq']
    return out

def _exists(db, base, fs, alias, params):
    'The filter as a correlated EXISTS, walking the foreign keys from `base` to the filtered table.'
    p = path(db, base, fs[0].t)
    if p is None: return None
    names, frm, on = table_names(db), [], []
    cur, curcols = alias, _cols(db, base)
    for i, (fc, tt, tc) in enumerate(p):
        a = f'x{i}'
        frm.append(f'{ident(tt, names)} {a}')
        on.append(f'{a}.{ident(tc, _cols(db, tt))} = {cur}.{ident(fc, curcols)}')
        cur, curcols = a, _cols(db, tt)
    return 'exists (select 1 from %s where %s)' % (', '.join(frm), ' and '.join(on + _preds(db, fs, cur, params)))

def where(db, base, fs, alias=None):
    '''SQL restricting `base` to the rows the filters allow.

    Returns the bare condition (no `where` keyword), its bind parameters, and the filters
    that could not be routed to `base` — the caller decides whether to say so or ignore it.
    `alias` is the already-quoted name the base table goes by in the caller's query.'''
    alias = alias or ident(base, table_names(db))
    ands, params, dropped, bytbl = [], {}, [], {}
    for f in fs: bytbl.setdefault(f.t, []).append(f)
    for t, g in bytbl.items():
        if t == base: ands += _preds(db, g, alias, params)
        else:
            e = _exists(db, base, g, alias, params)
            if e is None: dropped += g
            else: ands.append(e)
    return AttrDict(sql=' and '.join(ands), params=params, dropped=dropped)

# ── the pickers the filter bar is built from ──────────────────────────────────

# the order a *picker* wants, which is not the order the table reads in: a category is what
# people filter by, a surrogate key is what they never do, and the first option is a default
_RANK = dict(dimension=0, bool=1, temporal=2, measure=3, text=4, ref=5, key=6, const=7)

def columns(db, tbl=None):
    'Every filterable column, grouped by table, the one you are looking at first.'
    names = table_names(db)
    order = ([tbl] + [t for t in names if t != tbl]) if tbl in names else names
    out = []
    for t in order:
        cs = [(c, s.role, s.kind) for c, s in roles(db, t).items()]
        out.append((t, sorted(cs, key=lambda x: _RANK.get(x[1], 9))))   # stable: declared order within a rank
    return out

def values_for(db, t, c):
    '''Distinct values, when a column has few enough to choose from instead of type at.

    The cap is its own setting rather than `max_cats`, which is about what makes a readable
    *chart*: 275 artists is a hopeless doughnut and a perfectly good dropdown. Picking
    "AC/DC" off a list is the difference between finding it and having to guess the
    punctuation.'''
    s = profile(db, t)['cols'][c]
    if s['distinct'] > cfg.filter_values: return None
    # `select distinct` is a scan of the whole column however few values come back, and the
    # filter bar asks for one on every table page. Cached like any other derived fact.
    return cached(db, t, f'vals.{c}', lambda: _values(db, t, c))

def _values(db, t, c):
    qc = ident(c, _cols(db, t))
    rows = get_db(db).q(f'select distinct {qc} as v from {ident(t, table_names(db))} '
                        f'where {qc} is not null order by 1 limit :n', dict(n=cfg.filter_values))
    return [r['v'] for r in rows]
