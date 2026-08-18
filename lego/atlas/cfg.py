import os
from dataclasses import dataclass
from fastcore.all import Path, AttrDict, str2bool

@dataclass(frozen=True)
class Routes:
    index = '/atlas'
    store = '/atlas/{db}/{store}'
    doc   = '/atlas/{db}/{store}/doc/{id}'
    proj  = '/atlas/{db}/{store}/proj.json'
    legs  = '/atlas/{db}/{store}/legs'
    score = '/atlas/{db}/{store}/score'
    skip  = ['/atlas', r'/atlas/.*']

ATLAS_EMBEDDERS = 'code.store=code,lego.code=code,lego.docs=bge,env.store=code'
cfg = AttrDict(
    public      = str2bool(os.getenv('ATLAS_PUBLIC', '1')),
    dirs        = [p for p in os.getenv('ATLAS_DIRS', '').split(',') if p.strip()],
    seed_dir    = Path('data') / 'db' / 'atlas',
    embedder    = os.getenv('ATLAS_EMBEDDER', 'bge'),
    # per-store overrides: ATLAS_EMBEDDERS='code.code=code,papers.store=science'
    embedders   = dict(p.split('=', 1) for p in os.getenv('ATLAS_EMBEDDERS', ATLAS_EMBEDDERS).split(',') if '=' in p),
    seed        = str2bool(os.getenv('ATLAS_SEED', '1')),
    seed_dirs   = [p for p in os.getenv('ATLAS_SEED_DIRS', 'lego,static/blog').split(',') if p.strip()],

    hits        = 20,      # results on a page
    max_hits    = 100,     # ceiling a URL may ask for
    depth       = 200,     # rows each leg fetches before fusion — RRF only ranks what it is given
    snippet     = 360,     # characters of content shown per hit
    rrf_k       = 60,
    rrf_k_max   = 600,
    nbrs        = 8,       # more-like-this neighbours on a document page

    proj_max    = 4000,    # points the projection draws — past this the browser is the constraint
    cluster_max = 6000,    # vectors k-means reads
    kmin        = 2,
    # eight, because the palette has eight slots whose *order* is what keeps them apart
    # under colour blindness. A ninth cluster would reuse a colour, and two dots the same
    # colour on the map is the one thing the map must not say.
    kmax        = 8,
    kiter       = 25,      # Lloyd iterations
    sil_sample  = 1200,    # rows the silhouette is averaged over
    label_terms = 3,       # words naming a cluster
    facet_vals  = 12,      # values a metadata key offers before the rest are behind a count
    facet_share = 0.4,     # distinct values above this share of rows and a key is an id, not a facet
    facet_scan  = 2000,    # rows sampled to find metadata keys
    ann_recall_k= 20,      # depth the ANN-vs-exact agreement is measured at
)
