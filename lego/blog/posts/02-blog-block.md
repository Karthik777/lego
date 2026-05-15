---
slug: blog-block
title: The blog block
summary: Four files, one connect() call, under 300 lines including this post. The data model, why there is no migration framework, and how content gating works.
visibility: members
author_name: Karthik
---

The blog block has four files: `cfg.py` for route strings, `data.py` for the database, `ui.py` for components, `app.py` for route handlers.
Same structure as any lego block.

## The table

`data.py` creates one table:

```python
db.t.posts.create(
    id=int, slug=str, title=str, summary=str, body=str,
    author_id=int, author_name=str, visibility=str,
    created_at=float, updated_at=float,
    pk='id', if_not_exists=True, transform=True,
)
posts = db.t.posts
```

The `visibility` column is either `'public'` or `'members'`. The route handler checks it. Members-only without auth returns the teaser. That is the entire content-gating implementation: one string comparison in one route handler.

## Seeding

```python
def seed_posts(force=False):
    ex = [r['slug'] for r in posts(select='slug')]
    for p in seeds:
        if force or p['slug'] not in ex:
            posts.insert(p, replace=True)
```

Two lines. Idempotent. Runs on every `connect()` call.

## The route handlers

`app.py` has five route handlers. The auth check in each guarded route is one line:

```python
def blog_new_get(req, auth):
    if not auth: return _login_redirect()
    ...
```

The longest handler is `blog_new_post` at six lines: auth check, validate title and body are present, build slug from title plus timestamp, insert, redirect. FastHTML parses the form automatically from the `NewPost` dataclass type annotation on the handler parameter. No form parsing code anywhere.
