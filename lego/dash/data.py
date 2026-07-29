'''Connections, seeding and reflection for the dashboards block.

Every logical database is a SQLite file of its own under the app's db directory, opened
through fastlite. That is the whole storage story: lego has a writable filesystem, so a
sample database is seeded once from its packaged dump and read from the file forever
after. A file per database is also what keeps the explorer honest — it reports whatever
tables its connection has, and this one has only the sample data, never the `users` table
auth keeps on the app's own database.
'''
import gzip, hashlib, json, threading
from fastcore.all import AttrDict
from lego.core.cfg import database, get_db_pth, get_db_dir
from .cfg import cfg

__all__ = ['DBS', 'get_db', 'seed', 'schema', 'table_names', 'reflect', 'profile', 'rowcount', 'ident', 'cached']

def _db(nm, about, group='Statistical'):
    return AttrDict(nm=nm, dump=None, about=about, group=group)

# only databases listed here are reachable from /dash. `dump` defaults to `<key>.sql.gz`.
# The two business schemas make the relational charts — money over time, rollups through a
# foreign key. The fourteen below them are the seaborn teaching sets, converted by
# tools/dash_seeds.py: one wide fact table, a handful of lookups, and no dates or money at
# all. They are here because a picker that only ever sees invoices is a picker tuned to
# invoices, and half the chart kinds in this block exist because these did not fit.
DBS = AttrDict(
    chinook   = _db('Chinook', 'The classic digital-media store sample: artists, albums, tracks, invoices.', 'Business'),
    northwind = _db('Northwind', 'The other classic: a specialty-foods importer, its orders, products and staff.', 'Business'),

    diamonds  = _db('Diamonds', '53,940 diamonds priced against carat, cut, colour and clarity — '
                                'big enough that the honest picture of two measures is a density, not a scatter.'),
    titanic   = _db('Titanic', 'Every passenger on the 1912 crossing, with who lived. Survival is a rate, '
                               'and a rate splits by class, sex and deck.'),
    tips      = _db('Tips', 'Two hundred restaurant bills: what was spent, what was tipped, by whom and when.'),
    iris      = _db('Iris', "Fisher's three species of iris, four petal and sepal measurements each — "
                            'the dataset every scatter-by-species chart is descended from.'),
    mpg       = _db('Fuel economy', '398 cars from 1970–82: mileage against weight, power and displacement, '
                                    'by year and origin.'),
    planets   = _db('Exoplanets', 'A thousand confirmed planets — mass, orbit, distance, and the method '
                                  'and year each was found by.'),
    flights   = _db('Air travel', 'Monthly airline passengers, 1949–1960. Twelve years of seasonality in 144 rows.'),
    car_crashes = _db('Car crashes', 'One row per US state: crash rate broken into causes, against '
                                     'what insurance costs there.'),
    fmri      = _db('fMRI', 'Brain signal over time for fourteen subjects, two regions, two event types — '
                            'a time series that only makes sense split by something.'),
    gammas    = _db('BOLD gammas', 'Six thousand BOLD measurements across three regions of interest, '
                                   'sampled along a timecourse.'),
    dots      = _db('Motion decision', 'Neural firing rate against motion coherence, by what the '
                                       'subject chose and how the trial was aligned.'),
    exercise  = _db('Exercise', 'Pulse measured at rest, walking and running, on two diets.'),
    attention = _db('Attention', 'Twenty subjects solving puzzles under divided and focused attention.'),
    anscombe  = _db('Anscombe', "Four tiny datasets with near-identical means, variances and regression "
                                'lines, and nothing else in common. The argument for drawing the chart.'),
)
for _k, _v in DBS.items(): _v.dump = _v.dump or f'{_k}.sql.gz'

# sqlite keeps its own bookkeeping in the same namespace as the data; none of it is a table
# anybody wants to chart
_INTERNAL = ('sqlite_',)

# One connection per database per thread.
#
# Starlette runs sync handlers on a threadpool, and a dashboard page fires one chart
# request per card — eight of them, in parallel, the moment it loads. apsw refuses to run a
# cursor on a connection that is busy in another thread, so a single cached connection per
# database turns a full dashboard into a race that some cards lose. These files are opened
# read-only and never written after seeding, so a connection each costs nothing to keep
# consistent.
_local = threading.local()
_seeded, _seed_lock = set(), threading.Lock()

def get_db(nm):
    if nm not in DBS: raise KeyError(nm)
    conns = getattr(_local, 'conns', None)
    if conns is None: conns = _local.conns = {}
    if nm not in conns:
        # sem_search loads the usearch extension, which these read-only reference databases
        # have no use for — and it is a network fetch on first call
        conns[nm] = database(get_db_dir() / f'{nm}.db', sem_search=False)
        _ensure_seeded(nm, conns[nm])
    return conns[nm]

def _ensure_seeded(nm, db):
    'Seed once per process, whichever thread gets here first.'
    if nm in _seeded: return
    with _seed_lock:
        if nm in _seeded: return
        seed(nm, db)
        _seeded.add(nm)

# ── seeding ───────────────────────────────────────────────────────────────────

def _dump_sql(nm):
    'The packaged dump as one script. Statements are stored `--;--`-separated, one per chunk.'
    sql = gzip.decompress((cfg.seed_dir / DBS[nm].dump).read_bytes()).decode()
    return ';\n'.join(s.strip() for s in sql.split('\n--;--\n') if s.strip()) + ';'

def seed(nm, db):
    '''Put the dump in the database if the file is still empty.

    The dump ships with the block rather than being fetched, because SQL pulled off the
    network at runtime is SQL that executes unreviewed. One transaction over the whole
    script, so a cold start cut off part-way through leaves an empty file to seed again
    rather than half a database to reason about.

    `defer_foreign_keys` holds the key checks until that commit. A dump loads a table at a
    time, so a child row lands before the parent it points at more often than not; the
    database is consistent once the whole script is in, which is the only point the check
    is meaningful. It resets itself at the end of the transaction.'''
    if _tables(db): return
    try:
        with db.conn: db.conn.execute('pragma defer_foreign_keys = on;\n' + _dump_sql(nm))
    except Exception:
        # sqlite serialises the writers, so a second process seeding the same cold file
        # gets here on "table already exists" — which means the job is done, not failed
        if not _tables(db): raise

def ident(name, allowed):
    'Quote an identifier, but only after it matches something the schema actually reported.'
    if name not in allowed: raise ValueError(f'unknown identifier: {name!r}')
    return '"%s"' % name.replace('"', '""')

# ── reflection ────────────────────────────────────────────────────────────────

def _tables(db): return sorted(t for t in db.table_names() if not t.startswith(_INTERNAL))

def table_names(nm): return _tables(get_db(nm))

def reflect(nm, tbl):
    'Columns, primary key and foreign keys, straight off the PRAGMAs fastlite exposes.'
    if tbl not in table_names(nm): raise KeyError(tbl)
    t = get_db(nm).t[tbl]
    cols = [AttrDict(name=c.name, type=c.type, nullable=not c.notnull) for c in t.columns]
    order = {c.name: i for i, c in enumerate(t.columns)}
    # PRAGMA foreign_key_list reports in neither declared nor meaningful order; column order
    # is the order the table reads in, which is the order a reader is looking for them in
    fks = sorted((AttrDict(col=f.column, ref_table=f.other_table, ref_col=f.other_column)
                  for f in t.foreign_keys), key=lambda f: order.get(f.col, 99))
    # a rowid table has no primary key of its own; `pks` names the rowid anyway, and a
    # row page keyed on it would be a link to a number the table never shows
    pk = [] if t.use_rowid else list(t.pks)
    return AttrDict(name=tbl, cols=cols, pk=pk, fks=fks, fk_by_col={f.col: f for f in fks})

def schema(nm):
    'Whole-database shape: every table with its columns, keys and inbound child references.'
    tbls = {t: reflect(nm, t) for t in table_names(nm)}
    for t in tbls.values(): t.children = []
    for t in tbls.values():
        for f in t.fks:
            if f.ref_table in tbls: tbls[f.ref_table].children.append(AttrDict(table=t.name, col=f.col, ref_col=f.ref_col))
    return tbls

def rowcount(nm, tbl):
    if tbl not in table_names(nm): raise KeyError(tbl)
    return get_db(nm).t[tbl].count

# ── profiling ─────────────────────────────────────────────────────────────────

_NUM = ('INT', 'REAL', 'FLOA', 'DOUB', 'NUM', 'DEC')
_DATE = ('DATE', 'TIME', 'STAMP')

def _kind(sqltype):
    t = (sqltype or '').upper()
    if any(k in t for k in _DATE): return 'date'
    if any(k in t for k in _NUM): return 'num'
    return 'text'

_PROFILE_V = 3   # bump when the stats collected in _measure change

def _cache():
    'The profile cache table, on this thread\'s connection — same reason as get_db.'
    t = getattr(_local, 'meta', None)
    if t is None:
        m = database(get_db_pth('dash'), sem_search=False)
        t = _local.meta = m.t.dash_profile
        t.create(k=str, body=str, pk='k', if_not_exists=True)
    return t

def _schema_hash(nm, tbl):
    r = reflect(nm, tbl)
    body = json.dumps([[c.name, c.type] for c in r.cols], sort_keys=True)
    return hashlib.md5(f'{_PROFILE_V}.{nm}.{tbl}.{body}.{rowcount(nm, tbl)}'.encode()).hexdigest()[:16]

def cached(nm, tbl, tag, fn):
    '''Any derived fact about a table, memoised beside its profile and invalidated by the
    same schema-and-rowcount hash. What is expensive about the picker is never the rules,
    it is the scans they need to apply them.'''
    key = f'{nm}.{tbl}.{tag}.{_schema_hash(nm, tbl)}'
    row = _cache().get(key, as_cls=False, default=None)
    if row:
        try: return json.loads(row['body'])
        except ValueError: pass
    v = fn()
    _cache().upsert(dict(k=key, body=json.dumps(v)), pk='k')
    return v

def profile(nm, tbl, force=False):
    'Per-column stats used by the chart picker. Cached in dash.db against a schema+rowcount hash.'
    key = f'{nm}.{tbl}.{_schema_hash(nm, tbl)}'
    if not force:
        row = _cache().get(key, as_cls=False, default=None)
        if row:
            try: return AttrDict(json.loads(row['body']))
            except (ValueError, KeyError): pass
    p = _measure(nm, tbl)
    _cache().upsert(dict(k=key, body=json.dumps(p)), pk='k')
    return AttrDict(p)

def _measure(nm, tbl):
    '''Per-column statistics.

    The min, max, mean, total and sigma are read off *every* row. They have to be: a table
    is not stored in a random order, and taking the first five thousand diamonds off a file
    sorted by carat reports the mean price of the cheapest tenth as the mean price. Those
    aggregates are a single sequential scan, so the whole table is affordable.

    Only `count(distinct)` is sampled, and that one is worth sampling — it is the expensive
    aggregate, it decides nothing but whether a column reads as a category, and past a few
    thousand distinct values every answer means the same thing.'''
    db, names = get_db(nm), table_names(nm)
    r, qt = reflect(nm, tbl), ident(tbl, names)
    allowed = {c.name for c in r.cols}
    n = rowcount(nm, tbl)
    sampled = min(n, cfg.sample_rows)
    src = qt if n <= cfg.sample_rows else f'(select * from {qt} limit {cfg.sample_rows})'
    out = dict(table=tbl, rows=n, cols={})
    for c in r.cols:
        qc, kind = ident(c.name, allowed), _kind(c.type)
        agg = [f'count({qc}) as nn']
        if kind == 'num':
            # sqlite has no stddev; one pass over avg(x) and avg(x*x) gives the population sigma
            agg += [f'min({qc}) as lo', f'max({qc}) as hi', f'avg({qc}) as mean',
                    f'avg({qc}*{qc}) as m2', f'sum({qc}) as total']
        elif kind == 'date':
            agg += [f'min({qc}) as lo', f'max({qc}) as hi']
        else:
            agg += [f'max(length({qc})) as maxlen', f'min({qc}) as lo', f'max({qc}) as hi']
        row = db.q(f'select {", ".join(agg)} from {qt}')[0]
        nd = db.q(f'select count(distinct {qc}) as nd from {src}')[0]['nd'] or 0
        seen = row['nn'] or 0
        d = dict(name=c.name, type=c.type, kind=kind, nullable=c.nullable, distinct=nd,
                 nulls=n - seen, sampled=sampled)
        if kind == 'num' and seen:
            var = max(0.0, (row['m2'] or 0) - (row['mean'] or 0) ** 2)
            d.update(lo=row['lo'], hi=row['hi'], mean=row['mean'], total=row['total'], sd=var ** 0.5)
        elif kind == 'date':
            d.update(lo=row['lo'], hi=row['hi'])
        else:
            d.update(maxlen=row['maxlen'] or 0, lo=row['lo'], hi=row['hi'])
        out['cols'][c.name] = d
    return out
