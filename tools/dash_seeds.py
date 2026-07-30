#!/usr/bin/env python3
'''Turn the seaborn-derived SQLite files in

    https://github.com/davidjamesknight/SQLite_databases_for_learning_data_science

into seed dumps the dashboards block can load. Run it against a checkout of that repo:

    uv run python tools/dash_seeds.py ~/src/SQLite_databases_for_learning_data_science

It is a build-time script, not part of the package — the dumps it writes are committed,
so nothing fetches SQL over the network at runtime.

Why there is a script here at all: those files ship with no primary keys and no foreign
keys. Every one of them is a fact table called `Observation` holding `<thing>_id` integers
beside lookup tables holding the matching text, but the relationship is a naming
convention rather than a declaration. The dashboards block reads relationships off the
PRAGMAs — it is what decides that a column is a category rather than a number, what lets a
chart be grouped by "Ideal" instead of by `cut_id = 3`, and what the cross-table filter
walks. Loaded as-is, all fourteen would chart their surrogate keys.

So the import declares what the layout already implies, and nothing more:

  * a lookup table's `<x>_id` becomes its primary key,
  * `Observation.<x>_id` becomes a foreign key to it when a lookup owns that exact column,
  * the fact table gets an `id` primary key — sqlite's own rowid, made addressable, which
    is what gives each observation a page of its own,
  * pandas's unnamed index column is dropped,
  * types are folded onto sqlite's four affinities,
  * `Observation` is renamed to whatever the rows actually are, because every chart title
    is built from the table name and "Observations by Cut" says less than "Diamonds by Cut".

No column is added, renamed or recomputed beyond that.
'''
import gzip, sqlite3, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'lego' / 'dash' / 'seed'

# What one row of each fact table is. The source calls all fourteen `Observation`.
FACT = dict(anscombe='Point', attention='Trial', car_crashes='State', diamonds='Diamond',
            dots='Trial', exercise='Reading', flights='Flight', fmri='Scan', gammas='Sample',
            iris='Flower', mpg='Car', planets='Planet', tips='Bill', titanic='Passenger')

# sqlite has four storage classes; pandas wrote a dozen type names onto them. Folding them
# now is what lets the profiler read `BOOLEAN` as the two-valued integer it is.
TYPES = {'BIGINT': 'INTEGER', 'INTEGER': 'INTEGER', 'INT': 'INTEGER', 'BOOLEAN': 'INTEGER',
         'FLOAT': 'REAL', 'REAL': 'REAL', 'DOUBLE': 'REAL', 'TEXT': 'TEXT', 'VARCHAR': 'TEXT'}

JUNK = ('Unnamed: 0',)     # pandas wrote its index out as a column in two of the files
SEP = '\n--;--\n'
BATCH = 400                # rows per INSERT — one statement per row triples the dump

def q(name): return '"%s"' % str(name).replace('"', '""')

def cols(con, tbl):
    return [(r[1], TYPES.get(str(r[2]).upper().split('(')[0], 'TEXT')) for r in
            con.execute(f'pragma table_info({q(tbl)})')]

def read(src):
    'The source database as {table: (columns, rows)}, minus the junk columns.'
    con = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    out = {}
    for (t,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
        cs = [c for c in cols(con, t) if c[0] not in JUNK]
        rows = con.execute('select %s from %s' % (', '.join(q(c) for c, _ in cs), q(t))).fetchall()
        out[t] = (cs, rows)
    con.close()
    return out

def plan(name, tbls):
    '''Which table is the fact table, and which of its columns point where.

    A lookup is any table that is not the fact table; the column it is keyed on is the one
    ending `_id`. A fact column is a foreign key when some lookup is keyed on that exact
    name — `ROI_id` finds `Roi`, which no amount of singularising the table name would.
    `gammas.subject` and `exercise.id` are integers with no lookup behind them, and stay
    plain integers.'''
    fact = 'Observation'
    if fact not in tbls: raise SystemExit(f'{name}: no Observation table')
    keyed = {}
    for t, (cs, _) in tbls.items():
        if t == fact: continue
        k = next((c for c, _ in cs if c.lower().endswith('_id')), None)
        if not k: raise SystemExit(f'{name}.{t}: no *_id column to key on')
        keyed[k] = (t, k)
    fks = {c: keyed[c] for c, _ in tbls[fact][0] if c in keyed}
    return fact, FACT[name], keyed, fks

def ddl(tbl, cs, pk=None, fks=(), rowid_pk=None):
    lines = []
    if rowid_pk: lines.append(f'  {q(rowid_pk)} INTEGER PRIMARY KEY')
    lines += [f'  {q(c)} {t}' for c, t in cs]
    if pk: lines.append(f'  PRIMARY KEY ({q(pk)})')
    lines += [f'  FOREIGN KEY ({q(c)}) REFERENCES {q(rt)} ({q(rc)})' for c, (rt, rc) in fks]
    return 'CREATE TABLE %s (\n%s\n)' % (q(tbl), ',\n'.join(lines))

def lit(v):
    if v is None: return 'NULL'
    if isinstance(v, (int, float)): return repr(v)
    if isinstance(v, bytes): return "X'%s'" % v.hex()
    return "'%s'" % str(v).replace("'", "''")

def inserts(tbl, cs, rows):
    head = 'INSERT INTO %s (%s) VALUES' % (q(tbl), ', '.join(q(c) for c, _ in cs))
    for i in range(0, len(rows), BATCH):
        yield head + '\n' + ',\n'.join('(%s)' % ', '.join(map(lit, r)) for r in rows[i:i + BATCH])

def build(name, src):
    tbls = read(src)
    fact, factnm, keyed, fks = plan(name, tbls)
    stmts = []
    # lookups first: a dump loads a table at a time, and the reader of the file should meet
    # the small named things before the wide table that points at them
    for t in sorted(k[0] for k in keyed.values()):
        cs, rows = tbls[t]
        pk = next(c for c, _ in cs if c.lower().endswith('_id'))
        stmts.append(ddl(t, cs, pk=pk))
        stmts += list(inserts(t, cs, rows))
    cs, rows = tbls[fact]
    # `id` is the rowid the table already has, spelled out. Only a declared key gets a row
    # page, and an observation with no page is one the relation tree cannot open.
    idc = 'id' if not any(c == 'id' for c, _ in cs) else 'observation_id'
    stmts.append(ddl(factnm, cs, fks=sorted(fks.items()), rowid_pk=idc))
    stmts += list(inserts(factnm, cs, rows))
    sql = SEP.join(stmts)
    if SEP.strip() in sql.replace(SEP, ''): raise SystemExit(f'{name}: data contains the statement separator')
    path = OUT / f'{name}.sql.gz'
    path.write_bytes(gzip.compress(sql.encode(), 9))
    return path, len(rows), len(keyed)

def _ordered(con, tbls):
    '''Tables parents-first.

    Alphabetical order puts `address` before `city`, and inserting an address then needs a
    city table that is not there yet — apsw resolves a foreign key's parent when it
    prepares the statement, which `defer_foreign_keys` does not help with because that
    defers the *violation* check and not the lookup. Loading parents first sidesteps it,
    and is the order the file reads best in anyway.'''
    dep = {t: {r[2] for r in con.execute(f'pragma foreign_key_list({q(t)})')} & set(tbls) - {t}
           for t in tbls}
    out, seen = [], set()
    def visit(t, path=()):
        if t in seen or t in path: return   # a cycle just keeps its alphabetical position
        for p in sorted(dep[t]): visit(p, path + (t,))
        seen.add(t); out.append(t)
    for t in tbls: visit(t)
    return out

def from_sqlite(name, src, skip=(), drop_cols=()):
    '''Seed an already well-formed SQLite file — keys declared, tables named — by keeping
    its own DDL and re-emitting its rows.

    Nothing to repair here, which is the point of the contrast with `build()` above: given
    a database that says what its relationships are, the importer is a copy. Views,
    triggers and indexes are dropped, because the block reads tables and rebuilds
    everything else it needs from the PRAGMAs.'''
    con = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    tbls = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    tbls = _ordered(con, [t for t in tbls if t not in skip])
    # Every CREATE first, then every INSERT. A real schema has cycles in it — Sakila's
    # store names a manager and staff name a store — so no ordering of whole tables can put
    # both parents before both children. Creating all of them up front means any foreign
    # key resolves whenever its rows arrive, and `defer_foreign_keys` holds the value checks
    # to the commit at the end.
    ddls, body, total = [], [], 0
    for t in tbls:
        n = con.execute(f'select count(*) from {q(t)}').fetchone()[0]
        if not n: continue          # an empty table is a schema, not a dataset
        cs = [c for c in cols(con, t) if (t, c[0]) not in drop_cols]
        ddls.append(' '.join(con.execute('select sql from sqlite_master where type=? and name=?',
                                         ('table', t)).fetchone()[0].split()))
        rows = con.execute('select %s from %s' % (', '.join(q(c) for c, _ in cs), q(t))).fetchall()
        body += list(inserts(t, cs, rows))
        total += n
    con.close()
    stmts = ddls + body
    if not stmts: raise SystemExit(f'{name}: nothing to seed from {src}')
    sql = SEP.join(stmts)
    path = OUT / f'{name}.sql.gz'
    path.write_bytes(gzip.compress(sql.encode(), 9))
    return path, total, len([s for s in stmts if s.startswith('CREATE')])

def main(root):
    root = Path(root).expanduser()
    srcs = sorted(root.glob('*.db'))
    if not srcs: raise SystemExit(f'no .db files under {root}')
    OUT.mkdir(parents=True, exist_ok=True)
    for s in srcs:
        if s.stem not in FACT:
            print(f'skip {s.name} — no fact-table name registered'); continue
        p, n, k = build(s.stem, s)
        print(f'{s.stem:<12} {n:>6,} rows · {k} lookups → {p.name} ({p.stat().st_size / 1024:,.0f} KB)')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
