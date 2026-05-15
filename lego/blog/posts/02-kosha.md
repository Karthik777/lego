---
slug: kosha-code-context-for-agents
date: 2026-04-20
title: kosha: what a coding agent should know before it types
summary: A dev-time knowledge base that indexes your repo and installed packages into a hybrid search database and builds a call graph. Agents query it to understand patterns before writing code.
visibility: public
author_name: Karthik
---

The problem with coding agents is not that they write bad code. It is that they write code without knowing what already exists.

Ask an agent to add a new route and it will write one from scratch, in the pattern it remembers from training data, ignoring the twelve routes already in your codebase that all follow a slightly different convention. Ask it to write an atomic file save and it will roll one from scratch, ignoring `fastcore.xtras.atomic_save` sitting in your environment.

kosha (कोश, treasury) is the index that fixes this. The code is at [github.com/vedicreader/kosha](https://github.com/vedicreader/kosha).

## Two databases

kosha maintains two indexes: one for your project files, one for your installed packages. Both are litesearch databases — FTS5 plus vector search in SQLite. Both update incrementally. Re-indexing a changed file takes milliseconds.

```python
from kosha import Kosha
k = Kosha()
k.status()   # {files: 47, packages: 172, stale_files: 0}
k.sync()     # only re-embeds what changed
```

## Context before code

The main query is `k.context()`. It returns the most relevant code from both your project and your packages, with graph metadata attached.

```python
results = k.context('atomic write temp file', limit=8)
# → surfaces fastcore.xtras.atomic_save before you write your own
```

`env_context` does the same against packages only, faster, with filter syntax:

```python
k.env_context('package:fastcore path:xtras atomic', limit=5)
```

## The call graph

Semantic search finds candidates. The call graph tells you whether touching them is safe.

Every function has a PageRank score. High PageRank means many things depend on it — it's load-bearing. `k.ni()` gives you callers, callees, and one field that has no equivalent elsewhere: `co_dispatched`.

`co_dispatched` lists functions assigned together in the same table, list, or dict. Route handlers registered in the same `connect()` call. Plugin functions appended to the same list. If you need to add a new handler, `co_dispatched` shows you the peer functions and the registration site. You pattern-match and add yours in the right place.

```python
to_date_co = k.ni('fastcore.basics.to_date')
'''
{'node': 'fastcore.basics.to_date',
 'flavor': 'function',
 'file': '~/code/kosha/.venv/lib/python3.13/site-packages/fastcore/basics.py',
 'pagerank': 3e-05,
 'in_degree': 0,
 'out_degree': 2,
 'callers': [],
 'callees': ['fastcore.basics._typeerr', 'fastcore.basics.str2date'],
 'co_dispatched': ['fastcore.basics.to_int', 'fastcore.basics.to_float', 'fastcore.basics.to_bool']}
'''
```

## Where to add

`k.where_to_add('add a new route handler')` combines context and graph to return a `file:line` insertion point, with peers.

## Claude Code skill

kosha ships a Claude Code skill that gets installed into `.claude/skills/kosha/` when you run `k.sync()`. 
Open any project that uses it and the agent loads the skill automatically, runs `k.status()` first, 
and queries before it reads files.

---

The combination of litesearch for retrieval and pyan3 for AST call graphs is the core. Everything else is scaffolding.
