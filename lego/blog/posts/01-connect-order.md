---
slug: connect-order
title: Why auth.connect() goes last
summary: Each block declares which of its routes are public. Auth reads the full list. Connect in the wrong order and every public route requires a login.
visibility: public
author_name: Karthik
---

The wiring in app.py for a lego project looks like this:

```python
blog.connect(app)
a.connect(app)   # auth always last
```

The order is not arbitrary. Each block's `connect()` appends its public routes to a shared list called `RouteOverrides.skip`:

```python
def connect(app):
    seed_posts()
    RouteOverrides.skip += Routes.skip
    app.get(Routes.base)(blog_index)
    ...
```

`RouteOverrides.skip` starts empty. Blog adds `/blog` and `/blog/{slug}`. A shloka block would add its own public routes. Each block knows which of its own routes need no auth, and registers exactly those.

`auth.connect()` runs last. At that point `RouteOverrides.skip` contains the complete public route list from every block. The auth middleware is configured once with that final list. Any route not on the list requires a valid session.

If you flip the order and auth connects first, it reads an empty skip list. Every route in every block that was registered after auth requires a login, including the public ones. The bug shows up as auth walls on pages that should be open.

## Adding a new block

A new block declares its skip list in `cfg.py`:

```python
@dataclass(frozen=True)
class Routes:
    base: str = '/shloka'
    post: str = '/shloka/{slug}'
    skip: tuple = ('/shloka', '/shloka/{slug}')
```

Then in `connect()`:

```python
RouteOverrides.skip += Routes.skip
```

One line. The auth middleware picks it up automatically on next start. The new block's public routes are open without touching auth code.
