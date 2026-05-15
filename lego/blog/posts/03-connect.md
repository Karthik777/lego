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

You call it in `app.py` and the block registers its routes, creates its table, and seeds its data. 
The app does not need to know the block exists beyond that one call.

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
