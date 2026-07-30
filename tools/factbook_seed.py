#!/usr/bin/env python3
'''Build the `factbook` seed from a checkout of

    https://github.com/factbook/factbook.json

    uv run python tools/factbook_seed.py ~/src/factbook.json

The CIA World Factbook is public domain and current, which makes it the one geographic
dataset here that is worth putting on a map rather than just next to one. It arrives as one
JSON file per country, grouped into directories by region, and every value in it is prose:

    "Area": {"total ": {"text": "357,022 sq km"}}
    "Population": {"total": {"text": "84,012,284 (2025 est.)"}}
    "Real GDP per capita": {"text": "$66,700 (2023 est.)"}

So the work is extraction. Each field below names a path into that structure and the shape
of the number to pull out of the text at the end of it. Anything that does not parse is
left null rather than guessed at — a dashboard that quietly invents a birth rate is worse
than one with a gap, and the block already draws the gap honestly.

The country *name* is the join to the map. There is no ISO code in these files (the
filename is a FIPS 10-4 code, which nothing else uses), and lego/dash/geo.py resolves
names anyway — including the Factbook's own "Korea, South" and "Bahamas, The" inversions.
'''
import json, re, sys
from pathlib import Path
from dash_seeds import SEP, ddl, inserts, q   # same dump format, same escaping

OUT = Path(__file__).resolve().parent.parent / 'lego' / 'dash' / 'seed'

# Directory name → the region a country is filed under. These are the Factbook's own
# groupings, not a continent list, which is why Mexico is in North America and Egypt is
# in Africa but Turkey is in the Middle East.
REGIONS = {
    'africa': 'Africa', 'antarctica': 'Antarctica', 'australia-oceania': 'Australia & Oceania',
    'central-america-n-caribbean': 'Central America & Caribbean', 'central-asia': 'Central Asia',
    'east-n-southeast-asia': 'East & Southeast Asia', 'europe': 'Europe',
    'middle-east': 'Middle East', 'north-america': 'North America',
    'south-america': 'South America', 'south-asia': 'South Asia',
}

NUM = r'-?[\d,]+(?:\.\d+)?'

def _text(d, *path):
    'Walk the nested {"text": …} structure, tolerating the trailing spaces in some keys.'
    for p in path:
        if not isinstance(d, dict): return None
        # "total " with a trailing space is in the real data; so is "total"
        d = d.get(p) if p in d else next((v for k, v in d.items() if k.strip() == p), None)
    if isinstance(d, dict): d = d.get('text')
    return d if isinstance(d, str) else None

SCALE = {'trillion': 1e12, 'billion': 1e9, 'million': 1e6}

def _num(s, after=''):
    'The first number in the text, with its magnitude word applied if it has one.'
    if not s: return None
    if after:
        m = re.search(re.escape(after) + r'[^\d\-]{0,20}(' + NUM + ')', s)
    else:
        m = re.search(r'(' + NUM + ')', s)
    if not m: return None
    try: v = float(m.group(1).replace(',', ''))
    except ValueError: return None
    # "43.772 million" is a labour force of forty-three million, not of forty-three
    word = re.match(r'\s*(trillion|billion|million)', s[m.end():])
    return v * SCALE[word.group(1)] if word else v

def _int(s, after=''):
    v = _num(s, after)
    return None if v is None else int(v)

_YEAR = re.compile(r'(\d{4})\s*$')

def _latest(d, *path):
    '''The most recent year of a field the Factbook reports as a series.

    Economy figures come keyed by year — "Real GDP per capita 2024", "… 2023", "… 2022" —
    with no marker for which is current beyond the number in the key. Taking the highest
    year keeps the table current as the source is rebuilt, where hardcoding 2024 would
    quietly freeze it.'''
    for p in path:
        if not isinstance(d, dict): return None
        d = d.get(p) if p in d else next((v for k, v in d.items() if k.strip() == p), None)
    if not isinstance(d, dict): return d if isinstance(d, str) else None
    years = [(int(m.group(1)), v) for k, v in d.items() if (m := _YEAR.search(k))]
    if years:
        best = max(years)[1]
        return best.get('text') if isinstance(best, dict) else best
    return d.get('text') if isinstance(d.get('text'), str) else None

# column → (sqlite type, how to get it out of one country's JSON)
FIELDS = [
    ('region_id',        'INTEGER', None),   # filled from the directory
    ('area',             'INTEGER', lambda d: _int(_text(d, 'Geography', 'Area', 'total'))),
    ('area_land',        'INTEGER', lambda d: _int(_text(d, 'Geography', 'Area', 'land'))),
    ('area_water',       'INTEGER', lambda d: _int(_text(d, 'Geography', 'Area', 'water'))),
    ('coastline',        'INTEGER', lambda d: _int(_text(d, 'Geography', 'Coastline'))),
    ('population',       'INTEGER', lambda d: _int(_text(d, 'People and Society', 'Population', 'total'))),
    ('population_growth', 'REAL',   lambda d: _num(_text(d, 'People and Society', 'Population growth rate'))),
    ('birth_rate',       'REAL',    lambda d: _num(_text(d, 'People and Society', 'Birth rate'))),
    ('death_rate',       'REAL',    lambda d: _num(_text(d, 'People and Society', 'Death rate'))),
    ('migration_rate',   'REAL',    lambda d: _num(_text(d, 'People and Society', 'Net migration rate'))),
    ('median_age',       'REAL',    lambda d: _num(_text(d, 'People and Society', 'Median age', 'total'))),
    ('life_expectancy',  'REAL',    lambda d: _num(_text(d, 'People and Society', 'Life expectancy at birth', 'total population'))),
    ('infant_mortality', 'REAL',    lambda d: _num(_text(d, 'People and Society', 'Infant mortality rate', 'total'))),
    ('fertility_rate',   'REAL',    lambda d: _num(_text(d, 'People and Society', 'Total fertility rate'))),
    ('urban_population', 'REAL',    lambda d: _num(_text(d, 'People and Society', 'Urbanization', 'urban population'))),
    ('gdp_per_capita',   'INTEGER', lambda d: _int(_latest(d, 'Economy', 'Real GDP per capita'))),
    ('gdp_growth',       'REAL',    lambda d: _num(_latest(d, 'Economy', 'Real GDP growth rate'))),
    ('inflation_rate',   'REAL',    lambda d: _num(_latest(d, 'Economy', 'Inflation rate (consumer prices)'))),
    ('unemployment_rate', 'REAL',   lambda d: _num(_latest(d, 'Economy', 'Unemployment rate'))),
    ('labor_force',      'INTEGER', lambda d: _int(_latest(d, 'Economy', 'Labor force'))),
    ('internet_users',   'REAL',    lambda d: _num(_text(d, 'Communications', 'Internet users', 'percent of population'))),
]

def _name(d, code):
    'The country name, which is what joins this table to a map.'
    for path in (('Government', 'Country name', 'conventional short form'),
                 ('Government', 'Country name', 'conventional long form')):
        s = _text(d, *path)
        if s and s.lower() not in ('none', 'n/a'): return s.strip()
    return code.upper()

def read(root):
    out = []
    for slug, region in REGIONS.items():
        for f in sorted((Path(root) / slug).glob('*.json')):
            try: d = json.loads(f.read_text())
            except ValueError: continue
            if not isinstance(d, dict) or 'Government' not in d: continue
            row = dict(code=f.stem.upper(), name=_name(d, f.stem), region=region)
            for col, _, get in FIELDS:
                if get: row[col] = get(d)
            out.append(row)
    return out

def build(root):
    rows = read(root)
    if not rows: raise SystemExit(f'no country files under {root}')
    regions = sorted({r['region'] for r in rows})
    rid = {r: i + 1 for i, r in enumerate(regions)}
    rcols = [('region_id', 'INTEGER'), ('region', 'TEXT')]
    ccols = [('code', 'TEXT'), ('name', 'TEXT')] + [(c, t) for c, t, _ in FIELDS]
    stmts = [ddl('Region', rcols, pk='region_id')]
    stmts += list(inserts('Region', rcols, [(rid[r], r) for r in regions]))
    stmts.append(ddl('Country', ccols, rowid_pk='id',
                     fks=[('region_id', ('Region', 'region_id'))]))
    data = [tuple(rid[r['region']] if c == 'region_id' else r.get(c) for c, _ in ccols) for r in rows]
    stmts += list(inserts('Country', ccols, data))
    sql = SEP.join(stmts)
    path = OUT / 'factbook.sql.gz'
    import gzip
    path.write_bytes(gzip.compress(sql.encode(), 9))
    filled = {c: sum(1 for r in rows if r.get(c) is not None) for c, _, g in FIELDS if g}
    return path, rows, filled

if __name__ == '__main__':
    p, rows, filled = build(sys.argv[1] if len(sys.argv) > 1 else '.')
    print(f'{len(rows):,} countries → {p.name} ({p.stat().st_size / 1024:,.0f} KB)')
    for c, n in sorted(filled.items(), key=lambda kv: -kv[1]):
        print(f'  {c:<18} {n:>4} / {len(rows)}')
