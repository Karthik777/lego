'''What the vectors in a store look like when you stand back from them.

A search result list tells you about one query. This tells you about the corpus: how
many distinct things are in it, how tight each one is, how far apart they sit, and
whether the answer means anything at all. That last part is the reason the scores here
are reported rather than hidden — k-means returns k clusters whatever you give it, so
"12 clusters" is not a finding, and a silhouette of 0.04 next to it is what says so.

Everything is spherical: vectors are L2-normalised on the way in and centroids are
renormalised after every update, so the only similarity in this file is a dot product.
That is the same geometry `distance_cosine_*` uses inside the store, which is what makes
these clusters describe the space the search actually ranks in rather than a
Euclidean one nobody queries.

The projection is PCA, and it reports the share of variance its two axes carry. Two
components out of several hundred usually carry a small share, and points that look
adjacent on screen may not be neighbours at all — a number saying so beside the picture
is worth more than a prettier picture without one.
'''
import re
import numpy as np
from fastcore.all import AttrDict
from lego.core import quick_lgr, cache
from .cfg import cfg
from .data import vectors, sample_rows, store

__all__ = ['analysis', 'assign', 'project', 'KS']

info, error, warn = quick_lgr()

# k values tried. Geometric-ish rather than every integer: the silhouette curve is smooth,
# and thirteen fits of a 4000-row matrix to separate k=11 from k=12 is not a good trade.
KS = (2, 3, 4, 5, 6, 7, 8)
_AN_V = 1   # bump when `_analyse` changes what it computes — see `_DESC_V` in data.py

_STOP = set('''the a an and or of to in is are was were be been being for on at by with from this that these those
it its as not but if then than so such can will would could should may might do does did have has had he she they
we you i him her them our your their about into over under after before between out up down off only own same too
very just also each other more most some any no nor own s t don now here there when where why how all both''' .split())
_WORD = re.compile(r'[A-Za-z_][A-Za-z0-9_]{2,}')

# ── spherical k-means ─────────────────────────────────────────────────────────

def _unit(M):
    n = np.linalg.norm(M, axis=1, keepdims=True)
    return M / np.where(n == 0, 1, n)

def _seed(M, k, rng):
    '''k-means++ on the sphere: each new centre is drawn with probability proportional to
    how far the nearest existing centre already is. Plain random seeding on text
    embeddings reliably puts two centres inside the same dense blob and leaves a real
    cluster unclaimed, which reads downstream as "these two topics are one topic".'''
    idx = [int(rng.integers(len(M)))]
    d = 1.0 - M @ M[idx[0]]
    for _ in range(1, k):
        p = np.maximum(d, 0) ** 2
        s = p.sum()
        idx.append(int(rng.choice(len(M), p=p / s)) if s > 0 else int(rng.integers(len(M))))
        d = np.minimum(d, 1.0 - M @ M[idx[-1]])
    return M[idx].copy()

def _kmeans(M, k, rng, iters=None):
    'Lloyd on unit vectors: assign by largest dot product, re-mean, re-normalise.'
    C = _seed(M, k, rng)
    lab = np.zeros(len(M), dtype=np.int32)
    for it in range(iters or cfg.kiter):
        new = (M @ C.T).argmax(1).astype(np.int32)
        if it and (new == lab).all(): break
        lab = new
        for j in range(k):
            m = M[lab == j]
            # an emptied centre is re-seeded on the worst-served point rather than dropped,
            # so k stays the k that was asked for and scored
            C[j] = m.mean(0) if len(m) else M[int((M * C[lab]).sum(1).argmin())]
        C = _unit(C)
    return lab, C

def _silhouette(M, lab, C, rng):
    '''Mean silhouette over a sample, computed against centroids rather than every pair.

    The textbook silhouette is O(n²) in distances; against centroids it is O(nk) and
    keeps the property that matters here — negative means points sit closer to a
    neighbouring cluster than their own, near zero means the split is arbitrary.'''
    n = min(len(M), cfg.sil_sample)
    idx = rng.choice(len(M), n, replace=False) if len(M) > n else np.arange(len(M))
    S, l = M[idx], lab[idx]
    d = 1.0 - S @ C.T                      # cosine distance to every centroid
    own = d[np.arange(len(S)), l]
    d2 = d.copy(); d2[np.arange(len(S)), l] = np.inf
    nxt = d2.min(1)
    den = np.maximum(own, nxt)
    return float(np.mean(np.where(den > 0, (nxt - own) / den, 0.0)))

def _kmax(n):
    '''The largest k worth trying on n rows.

    A centroid-based silhouette rises monotonically as clusters approach singletons — a
    cluster of one sits at distance zero from its own centre, which scores perfectly and
    means nothing. Left alone, twenty-five documents come back as one cluster each, and
    the number stops describing the corpus. `sqrt(n/2)` is the usual rule of thumb and it
    is the honest one here: it keeps clusters large enough that "how tight is this
    cluster" is a question about several documents.'''
    return max(cfg.kmin, min(cfg.kmax, int(np.sqrt(n / 2))))

def _score(M, lab, C, rng):
    'Silhouette plus the Davies–Bouldin index — one wants to be high, the other low.'
    k = len(C)
    sil = _silhouette(M, lab, C, rng)
    spread = np.array([float((1.0 - M[lab == j] @ C[j]).mean()) if (lab == j).any() else 0.0 for j in range(k)])
    cc = 1.0 - C @ C.T
    np.fill_diagonal(cc, np.inf)
    db = float(np.mean([max((spread[i] + spread[j]) / cc[i, j] for j in range(k) if j != i) for i in range(k)])) if k > 1 else 0.0
    return sil, db, spread

# ── labelling ─────────────────────────────────────────────────────────────────

def _labels(texts, lab, k):
    '''Name each cluster by the words that are common in it and rare everywhere else.

    Straight term frequency names every cluster after the same handful of words the
    corpus is made of; weighting by inverse document frequency across the *clusters*
    (not the documents) is what makes the names differ from each other, which is the
    only job they have.'''
    tf = [{} for _ in range(k)]
    for t, j in zip(texts, lab):
        for w in set(_WORD.findall((t or '').lower())):
            if w in _STOP or len(w) < 3: continue
            tf[j][w] = tf[j].get(w, 0) + 1
    df = {}
    for d in tf:
        for w in d: df[w] = df.get(w, 0) + 1
    out = []
    for j, d in enumerate(tf):
        n = max(1, sum(1 for x in lab if x == j))
        sc = {w: (c / n) * np.log(k / df[w]) for w, c in d.items() if c > 1}
        top = sorted(sc.items(), key=lambda kv: -kv[1])[:cfg.label_terms]
        out.append(' · '.join(w for w, _ in top) or f'cluster {j + 1}')
    return out

# ── projection ────────────────────────────────────────────────────────────────

def _pca(M):
    'Two principal axes, the mean they are measured from, and the variance they carry.'
    mu = M.mean(0)
    X = M - mu
    # economy SVD: n×d with d in the hundreds, so this is cheap and exact
    _, s, Vt = np.linalg.svd(X, full_matrices=False)
    var = (s ** 2)
    ratio = float(var[:2].sum() / var.sum()) if var.sum() else 0.0
    return mu, Vt[:2], ratio

def _box(P):
    '''The raw component ranges, kept alongside the drawing coordinates.

    Points go to the client scaled into a unit box so the canvas has one coordinate
    system whatever the model's units are — but a query embedded later has to land on the
    same axes, and it can only be scaled the same way if the scaling is written down.
    Hence the raw bounds travel with the payload and `project()` reuses them.'''
    lo, hi = P.min(0), P.max(0)
    span = np.where(hi - lo == 0, 1, hi - lo)
    return (P - lo) / span, [float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1])]

# ── the cached analysis ───────────────────────────────────────────────────────

@cache(ttl=24 * 3600)
def _analyse(key, nm, sig, k_req):
    st = store(key, nm)
    if st is None: return None
    ids, M = vectors(st, limit=cfg.cluster_max)
    if len(ids) < 4:
        return dict(ok=False, why=f'{len(ids)} usable vectors — not enough to cluster', n=len(ids))
    M = _unit(M)
    rng = np.random.default_rng(0)     # a dashboard that renumbers its clusters on reload is unreadable
    top = _kmax(len(M))
    if k_req:
        k = max(2, min(int(k_req), len(M) - 1, cfg.kmax))
        lab, C = _kmeans(M, k, rng)
        sil, db, spread = _score(M, lab, C, rng)
        chosen = [dict(k=k, sil=sil, db=db)]
    else:
        tried = []
        for k in [x for x in KS if cfg.kmin <= x <= top]:
            l_, C_ = _kmeans(M, k, rng)
            s_, d_, sp_ = _score(M, l_, C_, rng)
            tried.append(dict(k=k, sil=s_, db=d_, _l=l_, _C=C_, _sp=sp_))
        best = max(tried, key=lambda t: t['sil'])
        lab, C, spread, sil, db, k = best['_l'], best['_C'], best['_sp'], best['sil'], best['db'], best['k']
        chosen = [dict(k=t['k'], sil=t['sil'], db=t['db']) for t in tried]

    rows = sample_rows(st, ids, ('content', 'metadata'))
    texts = [(rows.get(int(i)) or {}).get('content') or '' for i in ids]
    names = _labels(texts, lab, len(C))
    mu, comps, ratio = _pca(M)
    P, bounds = _box((M - mu) @ comps.T)

    cc = 1.0 - C @ C.T
    np.fill_diagonal(cc, np.inf)
    clusters = []
    for j in range(len(C)):
        m = lab == j
        near = int(cc[j].argmin()) if len(C) > 1 else j
        sim = M[m] @ C[j] if m.any() else np.zeros(1)
        order = np.argsort(-sim)[:5] if m.any() else []
        ex = [int(ids[np.flatnonzero(m)[o]]) for o in order]
        clusters.append(dict(i=j, name=names[j], n=int(m.sum()),
                             cohesion=float(sim.mean()) if m.any() else 0.0,
                             spread=float(spread[j]), nearest=near,
                             separation=float(cc[j][near]) if len(C) > 1 else 1.0,
                             examples=ex))
    step = max(1, len(ids) // cfg.proj_max)
    pts = [dict(i=int(ids[x]), x=round(float(P[x, 0]), 4), y=round(float(P[x, 1]), 4), c=int(lab[x]),
                t=(texts[x] or '').strip().replace('\n', ' ')[:72])
           for x in range(0, len(ids), step)]
    return dict(ok=True, n=len(ids), sampled=len(ids) < (st.embedded or 0), k=len(C),
                sil=sil, db=db, ratio=ratio, clusters=clusters, tried=chosen, points=pts,
                centroids=C.astype(np.float32).tolist(), mu=mu.astype(np.float32).tolist(),
                comps=comps.astype(np.float32).tolist(),
                bounds=bounds, member={int(i): int(c) for i, c in zip(ids, lab)})

def analysis(st, k=None):
    'The clustering for a store, computed once per version of the file.'
    try: return AttrDict(_analyse(st.db, st.name, f'{_AN_V}.{st.rows}.{st.embedded}.{st.ndim}', k or 0) or
                         dict(ok=False, why='store went away', n=0))
    except Exception as e:
        error(f'atlas: clustering {st.db}.{st.name} failed: {e}')
        return AttrDict(ok=False, why=f'{type(e).__name__}: {e}', n=0)

def assign(an, qvec):
    'Which cluster a query vector lands in, and how close it is to that centre.'
    if not an.get('ok') or qvec is None: return None
    C = np.asarray(an['centroids'], dtype=np.float32)
    v = np.asarray(qvec, dtype=np.float32)
    n = np.linalg.norm(v)
    if not n: return None
    sim = C @ (v / n)
    j = int(sim.argmax())
    return AttrDict(i=j, sim=float(sim[j]), name=an['clusters'][j]['name'])

def project(an, qvec):
    'Where a query vector falls on the same two axes the points were drawn on.'
    if not an.get('ok') or qvec is None: return None
    mu, comps = np.asarray(an['mu'], np.float32), np.asarray(an['comps'], np.float32)
    v = np.asarray(qvec, np.float32)
    n = np.linalg.norm(v)
    if not n: return None
    p = (v / n - mu) @ comps.T
    b = an['bounds']
    sx = (b[1] - b[0]) or 1.0
    sy = (b[3] - b[2]) or 1.0
    return [round(float((p[0] - b[0]) / sx), 4), round(float((p[1] - b[2]) / sy), 4)]
