'''Turning a column of names into a map.

The block never asks a schema where its geography is, for the same reason it never asks
which column is a measure: it looks. A column is geographic when enough of its distinct
values resolve to shapes in one of the packs under `geo/`, and that is the whole test.
`Customer.Country` says "USA" and "Germany", `car_crashes.abbrev` says "AL" and "AK",
Factbook says "Korea, South" — all three land on a shape without anything being declared.

The packs are built by tools/geo_build.mjs and hold pre-projected SVG path strings, so
nothing here projects anything. A pack is:

    w, h      the viewBox the paths are drawn in
    shapes    {key: "M…Z"}      key is ISO alpha-3, or a USPS state code
    index     {normalised: key} every spelling that should resolve to that key
    names     {key: label}      what to call it in a tooltip

The resolve threshold is the load-bearing number. Too low and a column of customer *names*
matches a handful of countries and gets drawn as a map of nothing; too high and a real
country column with a few territories in it is refused. It sits at 60% of distinct values,
measured against the values themselves rather than the row count, so one enormous country
cannot carry a column that is otherwise unmatched.
'''
import gzip, json, re, unicodedata
from functools import lru_cache
from fastcore.all import AttrDict, Path
from .cfg import cfg

__all__ = ['PACKS', 'pack', 'resolve', 'match', 'geo_of']

PACKS = ('world', 'us-states')
_DIR = Path(__file__).parent / 'geo'

def _norm(s):
    'The same normalisation the pack builder used: case, accents and punctuation all go.'
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

@lru_cache(maxsize=None)
def pack(nm):
    if nm not in PACKS: raise KeyError(nm)
    return AttrDict(json.loads(gzip.decompress((_DIR / f'{nm}.json.gz').read_bytes())))

_PAREN = re.compile(r'\s*\([^)]*\)')

def _variants(v):
    '''Spellings to try, in order of how much they trust the original.

    Two rewrites cover most of what real data does to a country name. A parenthetical
    gloss — "Turkey (Turkiye)", "Congo (Kinshasa)" — is an editorial aside on a name that
    is already there. And an inverted-comma form — "Congo, Democratic Republic of the",
    "Bahamas, The", "Korea, South" — is a sorting convention, which reads correctly once
    the two halves are put back in speaking order. Both are far more common than any
    single hand-written alias, so they are rules rather than table entries.'''
    yield v
    bare = _PAREN.sub('', v).strip()
    if bare != v: yield bare
    if ',' in bare:
        head, tail = bare.split(',', 1)
        yield f'{tail.strip()} {head.strip()}'

def resolve(nm, values):
    'Map each value to a shape key in this pack, dropping the ones that do not land.'
    ix = pack(nm).index
    out = {}
    for v in values:
        if v is None: continue
        k = next((ix[n] for n in map(_norm, _variants(str(v))) if n in ix), None)
        if k: out[v] = k
    return out

def match(values):
    '''The best pack for this column, or None.

    Both packs are tried and the one matching most values wins, which is what settles a
    column of "Georgia" — a US state column matches 50 states in `us-states` and a handful
    of country names in `world`, so the state pack wins on count rather than on a rule
    somebody had to write down.'''
    vals = [v for v in values if v is not None]
    if len(vals) < cfg.geo_min: return None
    best = None
    for nm in PACKS:
        hit = resolve(nm, vals)
        share = len(hit) / len(vals)
        if share >= cfg.geo_share and (not best or len(hit) > len(best.hit)):
            best = AttrDict(pack=nm, hit=hit, share=share, n=len(vals))
    return best

def geo_of(db, tbl, col):
    '''Is this column geographic? Cached against the table like every other derived fact.

    Resolution runs over the column's *distinct* values, which the profiler has already
    capped, so this is one small query however large the table is.'''
    from .data import get_db, table_names, ident, cached, profile
    from .filters import values_for
    s = profile(db, tbl)['cols'].get(col) or {}
    if s.get('kind') != 'text' and not (s.get('kind') == 'num' and s.get('distinct', 0) <= cfg.max_cats):
        return None
    if not (cfg.geo_min <= (s.get('distinct') or 0) <= cfg.filter_values): return None
    def compute():
        vals = values_for(db, tbl, col)
        m = match(vals or [])
        return dict(pack=m.pack, share=round(m.share, 3), n=len(m.hit)) if m else None
    got = cached(db, tbl, f'geo.{col}', compute)
    return AttrDict(got) if got else None
