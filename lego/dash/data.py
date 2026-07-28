'''Connections, seeding and reflection for the dashboards block.

Every logical database is a SQLite file of its own under the app's db directory, opened
through fastlite. That is the whole storage story: lego has a writable filesystem, so a
sample database is seeded once from its packaged dump and read from the file forever
after. A file per database is also what keeps the explorer honest — it reports whatever
tables its connection has, and this one has only the sample data, never the `users` table
auth keeps on the app's own database.
'''
import gzip, hashlib, json
from fastcore.all import AttrDict
from lego.core.cfg import database, get_db_pth, get_db_dir
from .cfg import cfg

__all__ = ['DBS', 'get_db', 'seed', 'schema', 'table_names', 'reflect', 'profile', 'rowcount', 'ident']

# only databases listed here are reachable from /dash
DBS = AttrDict(
    chinook=AttrDict(nm='Chinook', dump='chinook.sql.gz',
                     about='The classic digital-media store sample: artists, albums, tracks, invoices.'),
    northwind=AttrDict(nm='Northwind', dump='northwind.sql.gz',
                       about='The other classic: a specialty-foods importer, its orders, products and staff.'),
)

# sqlite keeps its own bookkeeping in the same namespace as the data; none of it is a table
# anybody wants to chart
_INTERNAL = ('sqlite_',)

_conns = {}

def get_db(nm):
    if nm not in DBS: raise KeyError(nm)
    if nm not in _conns:
        # sem_search loads the usearch extension, which these read-only reference databases
        # have no use for — and it is a network fetch on first call
        _conns[nm] = database(get_db_dir() / f'{nm}.db', sem_search=False)
        seed(nm)
    return _conns[nm]

# ── seeding ───────────────────────────────────────────────────────────────────

def _dump_sql(nm):
    'The packaged dump as one script. Statements are stored `--;--`-separated, one per chunk.'
    sql = gzip.decompress((cfg.seed_dir / DBS[nm].dump).read_bytes()).decode()
    return ';\n'.join(s.strip() for s in sql.split('\n--;--\n') if s.strip()) + ';'

def seed(nm):
    '''Put the dump in the database if the file is still empty.

    The dump ships with the block rather than being fetched, because SQL pulled off the
    network at runtime is SQL that executes unreviewed. One transaction over the whole
    script, so a cold start cut off part-way through leaves an empty file to seed again
    rather than half a database to reason about.

    `defer_foreign_keys` holds the key checks until that commit. A dump loads a table at a
    time, so a child row lands before the parent it points at more often than not; the
    database is consistent once the whole script is in, which is the only point the check
    is meaningful. It resets itself at the end of the transaction.'''
    db = _conns[nm]
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

_PROFILE_V = 2   # bump when the stats collected in _measure change

_meta = database(get_db_pth('dash'), sem_search=False)
_meta.t.dash_profile.create(k=str, body=str, pk='k', if_not_exists=True)
_cache = _meta.t.dash_profile

def _schema_hash(nm, tbl):
    r = reflect(nm, tbl)
    body = json.dumps([[c.name, c.type] for c in r.cols], sort_keys=True)
    return hashlib.md5(f'{_PROFILE_V}.{nm}.{tbl}.{body}.{rowcount(nm, tbl)}'.encode()).hexdigest()[:16]

def profile(nm, tbl, force=False):
    'Per-column stats used by the chart picker. Cached in dash.db against a schema+rowcount hash.'
    key = f'{nm}.{tbl}.{_schema_hash(nm, tbl)}'
    if not force:
        row = _cache.get(key, as_cls=False, default=None)
        if row:
            try: return AttrDict(json.loads(row['body']))
            except (ValueError, KeyError): pass
    p = _measure(nm, tbl)
    _cache.upsert(dict(k=key, body=json.dumps(p)), pk='k')
    return AttrDict(p)

def _measure(nm, tbl):
    db, names = get_db(nm), table_names(nm)
    r, qt = reflect(nm, tbl), ident(tbl, names)
    allowed = {c.name for c in r.cols}
    n = rowcount(nm, tbl)
    src = qt if n <= cfg.sample_rows else f'(select * from {qt} limit {cfg.sample_rows})'
    out = dict(table=tbl, rows=n, cols={})
    for c in r.cols:
        qc, kind = ident(c.name, allowed), _kind(c.type)
        agg = [f'count({qc}) as nn', f'count(distinct {qc}) as nd']
        if kind == 'num':
            # sqlite has no stddev; one pass over sum(x) and sum(x*x) gives the population sigma
            agg += [f'min({qc}) as lo', f'max({qc}) as hi', f'avg({qc}) as mean',
                    f'avg({qc}*{qc}) as m2', f'sum({qc}) as total']
        elif kind == 'date':
            agg += [f'min({qc}) as lo', f'max({qc}) as hi']
        else:
            agg += [f'max(length({qc})) as maxlen', f'min({qc}) as lo', f'max({qc}) as hi']
        row = db.q(f'select {", ".join(agg)} from {src}')[0]
        seen = row['nn'] or 0
        d = dict(name=c.name, type=c.type, kind=kind, nullable=c.nullable, distinct=row['nd'] or 0,
                 nulls=(n if n <= cfg.sample_rows else cfg.sample_rows) - seen, sampled=min(n, cfg.sample_rows))
        if kind == 'num' and seen:
            var = max(0.0, (row['m2'] or 0) - (row['mean'] or 0) ** 2)
            d.update(lo=row['lo'], hi=row['hi'], mean=row['mean'], total=row['total'], sd=var ** 0.5)
        elif kind == 'date':
            d.update(lo=row['lo'], hi=row['hi'])
        else:
            d.update(maxlen=row['maxlen'] or 0, lo=row['lo'], hi=row['hi'])
        out['cols'][c.name] = d
    return out
