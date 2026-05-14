---
slug: connect
title: connect()
summary: Each lego block registers its routes, creates its table, and seeds its data in one function. The app does not need to know the block exists.
visibility: members
author_name: Karthik
---

The `connect()` function in the blog block is five lines:

```python
def connect(app):
    seed_posts()
    app.get('/blog')(blog_index)
    app.get('/blog/new')(blog_new_get)
    app.post('/blog/new')(blog_new_post)
    app.get('/blog/{slug}')(blog_post_get)
```

No decorators. No class inheritance. No framework scanning for annotated functions. You call it in `app.py` and the block registers its routes, creates its table, and seeds its data. The app does not need to know the block exists beyond that one call.

Auth works the same way. The full wiring in `app.py` is two lines:

```python
a.connect(lego)
blog.connect(lego)
```

Adding a new block is one more line.

## Why not decorators

The common alternative is decorating route handler functions directly:

```python
@lego.get('/blog')
def blog_index(req): ...
```

This scatters route definitions. To understand everything a block handles, you read all of its files in order. With `connect()`, you read one function and you are done. Thirty seconds to understand the full surface area.

## Caching

The `cache()` decorator wraps diskcache's `memoize_stampede`:

```python
@cache('showcase', ttl=3600 * 24 * 30)
def showcase(auth):
    ...
```

I could use Redis. Redis has cluster mode, better pub/sub, and years of production hardening. It also requires a separate process, a connection pool, and something to restart it when it crashes. For VedicReader running on one Hetzner CAX11, that is three more things to operate. diskcache gives TTL, LRU eviction, and stampede protection using SQLite on disk. When I need Redis, I swap the backend. The `cache()` decorator API does not change.

One process, one SQLite file for the app DB, one for the cache, one for the blog. Backups run via cfeasy to Cloudflare R2 on a cron. The whole thing fits comfortably on a 4-euro VPS.
