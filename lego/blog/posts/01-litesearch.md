---
slug: litesearch-hybrid-search-sqlite
date: 2026-05-01
title: litesearch: hybrid search that fits in a file
summary: SQLite FTS5 meets vector similarity in one library. No Postgres, no Elasticsearch, no servers. Keyword precision and semantic recall, merged with reciprocal rank fusion.
visibility: public
author_name: Karthik
---

Search has two modes that both fall short alone.

Keyword search is precise. If you type "reciprocal rank fusion" it will find the document that uses those words. If the document says "merging ranked lists" instead, you get nothing. Full-text search does not understand intent.

Vector search understands intent. Embed the query, find the nearest neighbours, surface semantically similar content. But it floats. Ask it for the exact error message you saw yesterday and it may return something thematically related but not the thing itself.

litesearch runs both in parallel and merges them. The code is at [github.com/Karthik777/litesearch](https://github.com/Karthik777/litesearch).

## One SQLite file

The database is a SQLite file with a usearch SIMD extension loaded. A store is a table with `content`, `embedding`, and `metadata` columns, plus an FTS5 shadow table kept in sync with triggers. No external server. No Postgres. No Elasticsearch. The whole index is a file you can copy, version, or delete.

```python
from litesearch import database, FastEncode

db    = database('docs.db')
store = db.get_store('notes')
enc   = FastEncode()

embs = enc.encode_document([doc for doc, name in docs])
store.insert_all([
    {'content': doc, 'embedding': e.tobytes(), 'metadata': json.dumps({'file': name})}
    for (doc, name), e in zip(docs, embs)
])
```

`FastEncode` downloads an ONNX model from HuggingFace on first use and runs it with onnxruntime. No GPU required, no Transformers dependency.

## Reciprocal rank fusion

The merge algorithm is simple. Run FTS5. Run vector search. Each result gets a score of `1 / (k + rank)`. A document appearing in both lists gets the scores added. Documents that satisfy both keyword and semantic relevance rise naturally. Documents unique to one list still appear, ranked lower.

```python
q = "meaning of this mantra"
q_emb = enc.encode_query([q])[0].tobytes()
db.search(q, q_emb, columns=['content'])
```

## Query preprocessing

Raw keyword queries are not great FTS5 input. `pre()` expands them: extracts keywords via YAKE, adds wildcards, builds OR clauses. A query like `"atomic file write"` becomes something FTS5 can actually use across partial matches.

## Claude Code skill

litesearch ships with a Claude Code skill. Open a session in a project that uses it, and the agent knows the API before you say anything.

---

Used in VedicReader for cross-script mantra search. The FTS5 side handles exact Sanskrit terms; the vector side handles questions about meaning. Both are needed.