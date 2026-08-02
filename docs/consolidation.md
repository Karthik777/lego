# lego's part in the search consolidation

Full review and roadmap: [`litesearch/docs/consolidation.md`](https://github.com/Karthik777/litesearch/blob/main/docs/consolidation.md).

## Note on scope

`lego/atlas/cluster.py` is cited in `litesearch/graph.py` as the source of the c-TF-IDF labelling
approach, but the `atlas` block is **not in this repository** — it appears to be local-only. This
plan is written against the litesearch API rather than against that code, so it should hold either
way, but it has not been checked against the source.

## What already moved down

c-TF-IDF cluster labelling is in `litesearch.graph.ctfidf_labels`, and the clustering it labels is
now a public API rather than a private helper inside `topic_nodes`:

```python
res = store.clusters(columns=['content','metadata'])
res.method                     # 'usearch' (HNSW cut) or 'knn' (fallback)
res.note                       # '23 clusters over 8412 vectors (usearch)'
for c in res.clusters:
    c.centroid, c.size, c.label, c.member_keys, c.members
```

## Plan for the atlas block

1. **Projection moves into litesearch too.** `store.project(keys=None, dims=2)` — PCA over the
   stored vectors, numpy only, with UMAP optional behind an extra. A scatter plot needs x/y per
   point, and computing that from vectors is a retrieval concern rather than a rendering one. The
   UI should receive coordinates, not embeddings.
2. **The block takes a store name, not a corpus.** Given a litesearch database path and a store
   name, `atlas` renders `clusters()` + `project()`. Nothing in it should know what the corpus is.
3. **That makes it reusable for leela.** `kosha.code_st` *is* a litesearch store, so pointing the
   same block at `.kosha/code.db` gives a code atlas with no new backend — leela's cluster list
   and this scatter view read an identical payload.
4. **Render `note`.** It is the reason `note` exists. "23 clusters over 8,412 chunks (usearch)"
   and "index has 340 chunks; showing nearest neighbours" both need to reach the user; an empty
   plot and a broken index look the same otherwise.

## Known weakness to fix in passing

On code corpora, c-TF-IDF names clusters after unique identifiers — `integrate_4, integrate_6,
integrate_0` — because unique tokens are exactly what IDF rewards. A code-aware label wants
numeric suffixes stripped and the shared stem preferred. That is a tokeniser/`stop=` argument to
`ctfidf_labels`, not a different algorithm.

## Not in scope

The `dash` block (chart inference over arbitrary SQLite tables) has nothing to do with retrieval
and is unaffected by any of this.
