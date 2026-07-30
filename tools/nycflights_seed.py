#!/usr/bin/env python3
'''Build the `nycflights` seed from a checkout of

    https://github.com/tidyverse/nycflights13

    uv pip install rdata
    uv run python tools/nycflights_seed.py ~/src/nycflights13

This is the heaviest seed by an order of magnitude — nine megabytes against about one for
every other one put together, because it is 336,776 flights. It earns it: nothing else here
is a large time series, and 336k rows at hourly resolution over a full year against weather
at the same resolution is the shape that exercises date bucketing, density and the ordered
axis properly. The next biggest table in the block is fifty-four thousand diamonds with no
dates in them at all.

If you are vendoring this block into something where nine megabytes is not worth it, delete
`lego/dash/seed/nycflights.sql.gz`: `DBS` drops any database whose dump is missing, and
`/dash` will simply not list it.

Two things happen on the way in. The flight tables ship as R binaries (`.rda`), so `rdata`
reads them — the repo has CSVs for everything *except* the flights themselves. And the six
columns holding the scheduled departure — year, month, day, hour, minute and a Unix
`time_hour` — collapse into one `sched_dep` timestamp. Six spellings of one fact is what a
data frame does for convenience; a database wants the column the picker can bucket, and
`year` being constant at 2013 across every row makes it a `const` the block would discard
anyway.
'''
import gzip, sys, warnings
from datetime import datetime, timezone
from pathlib import Path
from dash_seeds import SEP, ddl, inserts

OUT = Path(__file__).resolve().parent.parent / 'lego' / 'dash' / 'seed'

# table → (source frame, primary key, foreign keys, columns to drop)
SPEC = {
    'Airline': ('airlines', 'carrier', {}, ()),
    'Airport': ('airports', 'faa', {}, ()),
    'Plane':   ('planes', 'tailnum', {}, ()),
    'Weather': ('weather', None, {'origin': ('Airport', 'faa')},
                ('year', 'month', 'day', 'hour', 'time_hour')),
    'Flight':  ('flights', None, {'carrier': ('Airline', 'carrier'),
                                  'tailnum': ('Plane', 'tailnum'),
                                  'origin': ('Airport', 'faa'),
                                  'dest': ('Airport', 'faa')},
                ('year', 'month', 'day', 'hour', 'minute', 'time_hour')),
}
ORDER = ['Airline', 'Airport', 'Plane', 'Weather', 'Flight']

TYPES = {'object': 'TEXT', 'float64': 'REAL', 'int64': 'INTEGER', 'int32': 'INTEGER',
         'bool': 'INTEGER'}

def _stamp(v):
    'The Unix `time_hour` column as an ISO timestamp — what the profiler reads as temporal.'
    try: return datetime.fromtimestamp(float(v), timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError, OSError): return None

def _clean(v):
    import math
    if v is None: return None
    if isinstance(v, float) and math.isnan(v): return None
    if hasattr(v, 'item'): v = v.item()
    return v

def frames(root):
    import rdata
    warnings.filterwarnings('ignore')
    out = {}
    for f in sorted(Path(root, 'data').glob('*.rda')):
        out.update(rdata.conversion.convert(rdata.parser.parse_file(f)))
    return out

def build(root):
    fr = frames(root)
    missing = [s[0] for s in SPEC.values() if s[0] not in fr]
    if missing: raise SystemExit(f'missing frames: {", ".join(missing)} — is that a nycflights13 checkout?')
    # A key is only declared if the data keeps it. nycflights13 is honest about being real
    # data: thousands of flights carry a tailnum with no row in `planes`, and fly to
    # airports `airports` has never heard of. Declaring those anyway makes the dump fail to
    # load; declaring them and disabling enforcement would make the block's filter router
    # walk a relationship that is not there. So each one is checked first, and the ones that
    # do not hold are reported rather than quietly asserted.
    keys = {t: {str(c): set(fr[SPEC[t][0]][c].dropna()) for c in [SPEC[t][1]] if c} for t in ORDER}
    ddls, body, counts, refused = [], [], {}, []
    for tbl in ORDER:
        src, pk, fks, drop = SPEC[tbl]
        df = fr[src]
        good = {}
        for col, (ptbl, pcol) in fks.items():
            have = keys.get(ptbl, {}).get(pcol, set())
            miss = set(df[col].dropna()) - have
            if miss: refused.append(f'{tbl}.{col} → {ptbl}.{pcol} ({len(miss):,} values absent)')
            else: good[col] = (ptbl, pcol)
        keep = [c for c in df.columns if str(c) not in drop]
        cols = [(str(c), TYPES.get(str(df[c].dtype), 'TEXT')) for c in keep]
        if 'time_hour' in df.columns: cols.append(('sched_dep', 'TIMESTAMP'))
        ddls.append(ddl(tbl, cols, pk=pk, rowid_pk=None if pk else 'id',
                        fks=[(c, ref) for c, ref in good.items()]))
        rows = []
        for r in df.itertuples(index=False, name=None):
            d = dict(zip((str(c) for c in df.columns), r))
            row = [_clean(d[c]) for c in (str(k) for k in keep)]
            if 'time_hour' in d: row.append(_stamp(d['time_hour']))
            rows.append(tuple(row))
        body += list(inserts(tbl, cols, rows))
        counts[tbl] = len(rows)
    path = OUT / 'nycflights.sql.gz'
    path.write_bytes(gzip.compress(SEP.join(ddls + body).encode(), 9))
    return path, counts, refused

if __name__ == '__main__':
    p, counts, refused = build(sys.argv[1] if len(sys.argv) > 1 else '.')
    for t, n in counts.items(): print(f'  {t:<10} {n:>7,} rows')
    for r in refused: print(f'  key not declared — the data does not keep it: {r}')
    print(f'-> {p.name} ({p.stat().st_size / 1e6:,.1f} MB)')
