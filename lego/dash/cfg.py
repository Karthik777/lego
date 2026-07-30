import os
from dataclasses import dataclass
from fastcore.all import Path, AttrDict, str2bool

@dataclass(frozen=True)
class Routes:
    index = '/dash'
    db    = '/dash/{db}'
    table = '/dash/{db}/{table}'
    row   = '/dash/{db}/{table}/{pk}'
    rel   = '/dash/{db}/{table}/{pk}/rel/{child}'
    chart = '/dash/chart.json'
    fopts = '/dash/filter.opts'
    bopts = '/dash/build.opts'
    geo   = '/dash/geo/{pack}.json'
    skip  = ['/dash', r'/dash/.*']

# public=False keeps /dash behind the auth middleware; DASH_PUBLIC=true opens it up
cfg = AttrDict(
    public       = str2bool(os.getenv('DASH_PUBLIC', '1')),
    seed_dir     = Path(__file__).parent / 'seed',
    rows_per_page= 50,
    sample_rows  = 5000,    # profiler stats are computed over at most this many rows
    max_cats     = 50,      # distinct values above this and a column stops being a dimension
    bar_cats     = 12,      # at or below this a dimension gets a vertical bar
    pie_cats     = 5,       # at or below this it can also be a share-of-total doughnut
    top_n        = 10,      # top-N + "Other" for wide dimensions
    hist_bins    = 24,
    max_series   = 6,       # split-by series drawn before the palette starts repeating itself
    heat_bins    = 26,      # cells per axis on a density heatmap
    box_min      = 8,       # rows a category needs before its quartiles mean anything
    corr_max     = 8,       # measures a correlation matrix will put on a side
    geo_min      = 6,       # distinct values below which a column is not worth mapping
    geo_share    = 0.6,     # fraction of them that must resolve to shapes before it is one
    map_classes  = 6,       # quantile classes a choropleth colours by
    log_span     = 3,       # orders of magnitude past which an axis goes logarithmic
    max_charts   = 8,
    rel_preview  = 5,       # child rows shown per nested relation before "view all"
    max_filters  = 8,       # active filters per request — bounds the SQL a URL can ask for
    max_hops     = 6,       # foreign keys a filter may be routed through to reach another table
    filter_values= 500,     # distinct values above which a filter is typed, not picked from a list
)
