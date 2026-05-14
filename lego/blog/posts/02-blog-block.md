---
slug: blog-block
title: The blog block
summary: Four files, one connect() call, under 300 lines including this post. The data model, why there is no migration framework, and how content gating works.
visibility: members
author_name: Karthik
---

The blog block has four files: `cfg.py` for route strings, `data.py` for the database, `ui.py` for components, `app.py` for route handlers. Same structure as the auth block.

## The table

`data.py` creates one table:

```python
db.t.posts.create(
    id=int, slug=str, title=str, summary=str, body=str,
    author_id=int, author_name=str, visibility=str,
    created_at=float, updated_at=float,
    pk='id', if_not_exists=True, transform=True,
)
```

The `visibility` column is either `'public'` or `'members'`. The route handler checks it. Members-only without auth returns the teaser. That is the entire content-gating implementation: one string comparison in one route handler.

## No migrations

`if_not_exists=True` means the `create()` call is safe to run on every startup. `transform=True` means adding a column to the schema definition causes fastlite to run `ALTER TABLE` automatically on next start. No migration files, no migration runner, no version tracking. For a blog with one table and one developer, Alembic is solving a problem that does not exist here.

## Seeding

```python
def seed_posts(tbl=None):
    tbl = tbl or posts
    ex = {p['slug'] for p in tbl(select='slug')}
    [tbl.insert(p) for p in _SEED if p['slug'] not in ex]
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
