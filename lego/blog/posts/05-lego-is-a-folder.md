---
slug: lego-is-a-folder
title: lego is a folder you copy
summary: VedicReader has a shloka block. If I build a karaoke app next year, I copy that folder into the new project, call connect(), and it works. That is the whole idea.
visibility: public
author_name: Karthik
---

Each lego block is a folder: `cfg.py`, `data.py`, `ui.py`, `app.py`. One function called `connect()` that takes the app and wires everything: routes, database table, seed data. The block owns everything it needs to exist.

VedicReader has a shloka block that renders Sanskrit texts with transliteration. If I build a karaoke app next year that needs the same functionality, I copy the folder into the new lego project and add one line to `app.py`:

```python
shloka.connect(lego)
```

The block brings its own table, seeds its own data, registers its own routes. The host app knows nothing about it beyond that one line.

This blog is a block. Auth is a block. Each one is self-contained. The combination is an app.

## The template

When you copy lego for a new project, you get auth, caching, theming, and this blog out of the box. The blocks you do not want, delete the folder and remove the `connect()` call. Nothing else breaks because nothing depends on them.

The alternative is how most projects grow: auth scattered across six files, database setup in two modules, config keys hardcoded in three places. Copying that to a new project means archaeology. Lego's version means `cp -r`.
