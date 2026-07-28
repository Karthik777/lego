---
name: lego
description: >
  Build performant webapps with FastHTML + Oat, hetzner deployment, docker containers, cloudflare tunnels,
  and a full auth system. Each feature is a **block**: a folder with `cfg.py`, `data.py`, `ui.py`, `app.py`, and a `connect(app)` function.
---

# lego

lego is a FastHTML + Oat web app template. Each feature is a **block**: a folder with `cfg.py`, `data.py`, `ui.py`, `app.py`, and a `connect(app)` function. Blocks are wired in `lego/app.py`. Auth always connects last.

## CLI entrypoints

Defined under `[project.scripts]` in `pyproject.toml`. Always invoke via `uv run` — never `python …` directly, and never `pip install`.

| command | calls | purpose |
|---|---|---|
| `uv run python main.py` | `lego.launch()` | start the dev server (port from `PORT`, default 5001) |
| `uv run lego-setup` | `setup:setup` | init gheasy config, set git-lfs patterns, write `.env.example`, generate `.github/workflows/deploy.yml`, install SKILL.md files |
| `uv run lego-skill` | `setup:install_skills` | (re)copy `SKILL.md` into `.claude/skills/lego/` and `.agents/skills/lego/` (plus any installed companions: dockeasy, gheasy, vpseasy, cfeasy, kosha, litesearch) |
| `uv run lego-push` | `setup:push_cli` | push `.env` values to GitHub — `None`-default keys become secrets, string-default keys become variables. Append `--dry-run` to preview |
| `uv run lego-deploy compose` | `deploy:deploy_cli` | build `Dockerfile` + `docker-compose.yml` only |
| `uv run lego-deploy deploy` | `deploy:deploy_cli` | provision Hetzner VPS (if needed), create Cloudflare tunnel, deploy |
| `uv run lego-deploy nuke` | `deploy:deploy_cli` | delete VPS + tunnel (interactive confirmation) |
| `uv run lego-deploy env` | `deploy:deploy_cli` | refresh `.env` from `env2push()` only |

`SKILL.md` is the canonical source — `.claude/skills/lego/SKILL.md` and `.agents/skills/lego/SKILL.md` are copies produced by `lego-skill`. Edit the root file, then re-run the command.

## Block pattern

```python
def connect(app):
    seed_data()                          # idempotent, runs every start
    RouteOverrides.skip += Routes.skip   # declare public routes before auth
    app.get(Routes.base)(my_index)
    app.post(Routes.new)(my_create)
```

Connect order matters. Auth reads `RouteOverrides.skip` at connect time to build the middleware allowlist. Any block with public routes must append to the skip list before auth connects.

```python
# lego/app.py — correct order
b.connect(lego)   # blog: appends its public routes to skip list
a.connect(lego)   # auth: always last, reads the complete skip list
```

## Core imports

```python
from lego.core import (
    cfg, quick_lgr, cache, kv, get_lock, release_lock,
    get_pth, get_db_pth, in_static, get_db_dir, slug,
    RouteOverrides, AppErr, home, send_email, not_prod,
    base, landing, navbar, not_found, email_template,
    Badge, BadgeT, BadgePresetsT, PresetsT, NavBarT,
)
from lego.core.utils import scheduler, loadX, timeit, arun
from lego.core.backups import run_backup, clone
```

## Config

`cfg` is an `AttrDictDefault` in `lego/core/cfg.py`. All values come from env vars:

| env var | default | description |
|---|---|---|
| `APP_NAME` | `Lego` | Display name |
| `APP_SH` | `lego` | Short name used in the navbar |
| `MODE` | `dev` | `dev` or `production` |
| `DOMAIN` | `http://localhost:5001` | Full URL (used in emails, OAuth callbacks) |
| `PORT` | `5001` | Server port |
| `JWT_SCRT` | auto-generated | JWT signing secret |
| `RESEND_API_KEY` | `''` | Resend email API key |
| `NEED_BACKUP` | `false` | Enable scheduled backups |
| `PURGE` | `false` | Clear diskcache on startup |
| `GITHUB_REPO` | `Karthik777/lego` | Repo for the GitHub star widget |
| `CF_ACCESS_KEY_ID` | `''` | Cloudflare R2 access key |
| `CF_SCRT_ACCESS_KEY` | `''` | Cloudflare R2 secret |
| `CF_ENDPOINT` | `''` | Cloudflare R2 endpoint |

`not_prod()` returns `True` when `MODE != 'production'`. Theme switcher only appears in dev mode.

## Logging

```python
from lego.core import quick_lgr

info, error, warn = quick_lgr()
info("started")
```

`quick_lgr()` reads the calling file's name and uses it as the log filename. No config needed. Rotating file handler, 10 MB max, 5 backups.

## Caching

```python
from lego.core import cache

@cache(ttl=3600)
def expensive(param):
    return compute(param)
```

DiskCache-backed with stampede protection. Key scoped to `__qualname__` + args — no collisions between functions with the same signature. `clear_cache()` flushes all entries. `PURGE=true` clears on startup.

## Key-value store and distributed lock

```python
from lego.core import kv, get_lock, release_lock

kv.set('key', value, expire=3600)
kv.get('key')

if get_lock('my-job', ttl=60):
    do_work()
    release_lock('my-job')
```

`get_lock` uses the same DiskCache. Safe across multiple processes on the same host. `start_scheduler` in `utils.py` uses it to prevent duplicate scheduler instances.

## Scheduler

```python
from lego.core.utils import scheduler

scheduler.add_job(my_fn, trigger='cron', hour='8,20', minute=0)
scheduler.add_job(my_fn, trigger='interval', hours=24, id='daily_job')
```

`AsyncIOScheduler` from APScheduler. `start_scheduler` / `stop_scheduler` are wired to FastHTML's `on_startup` / `on_shutdown` in `app.py`.

## Backups

```python
from lego.core.backups import run_backup, clone

run_backup(src="data/db", max_ages="2,14,60")   # age-tiered local snapshots
clone(src="data/db", bucket="my-app-db")         # sync to Cloudflare R2 or S3
```

Both are scheduled automatically in `app.py` when `NEED_BACKUP=true`. Requires `RC_TYPE`, `CF_ACCESS_KEY_ID`, `CF_SCRT_ACCESS_KEY`, `CF_ENDPOINT`.

## Paths

```python
from lego.core import get_pth, get_db_pth, in_static, get_db_dir

get_pth('myfile.log', sf='logs')   # data/logs/myfile.log
get_db_pth('myblock')              # data/db/myblock.db
in_static('svg/logo.svg')          # static/svg/logo.svg
get_db_dir()                       # Path to data/db/
```

## Database

```python
from lego.core.cfg import database, get_db_pth

db = database(get_db_pth('myblock'))
db.t.items.create(id=int, name=str, pk='id', if_not_exists=True, transform=True)
items = db.t.items
items.insert(dict(name='hello'))
items(order_by='id desc')
```

`database` is `fastlite.database` — SQLite in WAL mode. `transform=True` allows additive schema changes without data loss.

## Slug

```python
from lego.core import slug

s = slug("my post title" + str(time.time()))   # 11-char MD5 hex
```

## UI layouts

```python
from lego.core import base, landing, not_found

def dashboard(req, auth):
    return base(Div("content"), auth, title='Dashboard')

def index(req):
    return landing(Div("welcome"))

return not_found()
```

`base(content, usr, title, style)` — navbar + `#main-content` wrapper.  
`landing(content, title, usr)` — welcome page with typewriter animation + background montage.  
`not_found()` — 404 landing page.

## UI components

```python
from lego.core import Badge, BadgeT, BadgePresetsT, PresetsT, NavBarT

Badge("New",   cls=BadgePresetsT.primary)
Badge("Draft", cls=BadgePresetsT.sm)
```

`PresetsT.shine`, `PresetsT.glass`, `PresetsT.standout` — card/container presets.  
`NavBarT.default`, `NavBarT.glass`, `NavBarT.shining` — navbar style variants.

## Email

```python
from lego.core import send_email, email_template

send_email(
    to='user@example.com',
    subject='Verify your email',
    html=email_template(Div("Click here to verify"), title='Verify'),
)
```

`send_email` is `@threaded` — non-blocking. Requires `RESEND_API_KEY`.

## CSS / JS utilities

```python
from lego.core.utils import loadX, minjs, mincss

js = loadX('path/to/file.js', kw={'variable': 'value'})
```

`__varname__` placeholders in the file are replaced by `kw['varname']`. Output is minified automatically based on file extension.

**A block owns its assets.** Put a block's CSS and JS in the block folder and pull them in from a per-page head function, rather than adding to `lego/core/theme.css`:

```python
from lego.core import asset_js, asset_css, vendor_js

asset_js(path)     # Script tag for a block's .js — static/assets when writable, inline when not
asset_css(path)    # Link tag for a block's .css — same fallback; keeps styles with the block
vendor_js(name)    # Script tag for static/vendor/<name>, content-hashed
```

## Navbar links

```python
RouteOverrides.nav += [('Dashboards', Routes.index, 'new', not cfg.public)]
#                       label          href          tag    gated
```

`navbar()` renders nav entries as pills, deliberately smaller than the wordmark; `tag` puts a badge to the right. A `gated` entry opens the login modal in place for signed-out visitors rather than bouncing them to `/lgn`, which renders as a bare modal on an otherwise empty page. Nav pills carry `hx-boost="false"` so a block's page-level `<script src>` tags load through a real navigation.

## Themes

`THEMES` in `lego/core/ui.py` lists the palettes the theme switcher offers; `themes(color=...)` sets the default (`paper`). Every palette but `paper` only overrides `--primary`/`--primary-foreground` — `theme-paper` moves the surface colors too, so a new palette of that kind belongs in the same block of `theme.css`.

`theme.js` wraps every appearance change in `withUiAnim`, which adds `.ui-anim` to `<html>` for 220ms so the swap cross-fades instead of snapping. It is skipped on the initial paint and under `prefers-reduced-motion`.

Add `dropcap` to an article's class to get a drop capital on its first paragraph.

## Auth block (`lego/auth/`)

```python
import lego.auth as a
a.connect(lego)   # always last
```

Sets up session middleware and registers all auth routes. `before()` in `app.py` hydrates `req.scope['auth']` from the session on every request.

**Routes:**

| route | purpose |
|---|---|
| `GET  /a/m` | auth modal (login/register step) |
| `GET  /a/ok` | 200 if authenticated, 401 otherwise |
| `POST /a/lgn` | process login |
| `POST /a/reg` | register |
| `GET  /a/ver-em` | verify email |
| `GET  /a/fgt-pw` | forgot password |
| `GET  /a/lgt` | logout |
| `GET  /a/google/callback` | Google OAuth callback |
| `GET  /a/github/callback` | GitHub OAuth callback |

**Route overrides:**

```python
from lego.core import RouteOverrides

RouteOverrides.lgn  = '/a/m'        # where unauthenticated requests are redirected
RouteOverrides.lgt  = '/a/lgt'      # logout route
RouteOverrides.home = cfg.domain    # post-login redirect
RouteOverrides.skip += ['/public']  # additional public routes
```

**Env vars:**

| env var | default | purpose |
|---|---|---|
| `RESEND_API_KEY` | `''` | email verification + password reset |
| `WANT_GOOGLE` | `true` | enable Google OAuth |
| `GOOGLE_CLI` | `''` | Google client ID |
| `GOOGLE_SCRT` | `''` | Google client secret |
| `WANT_GIT` | `false` | enable GitHub OAuth |
| `GIT_CLI` | `''` | GitHub client ID |
| `GIT_SCRT` | `''` | GitHub client secret |

OAuth is disabled silently if credentials env vars are empty, even if `WANT_GOOGLE=true`.

**User table:**

```
users: id, email, password_hash, status (pending/active/suspended/deleted),
       display_name, avatar_url, auth_provider, provider_user_id,
       last_active_at, preferences, created_at, updated_at
```

**Auth check in route handlers:**

```python
def my_route(req, auth):
    if not auth: return home()
    # auth is the user dict from session
    display_name = auth['display_name']
```

`auth` is the user dict or `None`. FastHTML injects it via the `before()` middleware in `app.py`.

## Blog block (`lego/blog/`)

```python
import lego.blog as b
b.connect(lego)   # before auth
```

Posts are seeded from `lego/blog/posts/*.md` on every `connect()` call. Files are sorted by filename before seeding — use numeric prefixes (`00-`, `01-`) to control order.

**Frontmatter keys:**

| key | required | description |
|---|---|---|
| `slug` | yes | URL key (`/blog/{slug}`) |
| `title` | yes | Post title |
| `summary` | no | One-line summary for list view |
| `date` | no | `YYYY-MM-DD`, falls back to file ctime |
| `author_name` | no | Defaults to `Karthik` |
| `visibility` | no | `public` (default) or `members` |
| `layout` | no | `single` (default) or `newspaper` |

**Newspaper layout column break** — force the second column to start here:

````md
```col
```
````

Code blocks never split across columns.

**Routes:**

| route | purpose |
|---|---|
| `GET /blog` | post list |
| `GET /` | same as `/blog` (pinned post shown first) |
| `GET /blog/new` | new post form (auth required) |
| `POST /blog/new` | create post |
| `GET /blog/{slug}` | post detail |

Pinned post: set `cfg.pinned_slug` in `lego/blog/cfg.py`.

## Dash block (`lego/dash/`)

```python
import lego.dash as d
d.connect(lego)   # before auth
```

Reflects a database, profiles its columns, and picks charts from what it finds. Nothing is hardcoded to a schema. Ships with Chinook and Northwind.

**Routes** (from `lego/dash/cfg.py` `Routes`):

| attribute | path |
|---|---|
| `Routes.index` | `/dash` |
| `Routes.db` | `/dash/{db}` |
| `Routes.table` | `/dash/{db}/{table}` |
| `Routes.row` | `/dash/{db}/{table}/{pk}` |
| `Routes.rel` | `/dash/{db}/{table}/{pk}/rel/{child}` (htmx partial) |
| `Routes.chart` | `/dash/chart.json` (registered first — `/dash/{db}` would otherwise match it) |
| `Routes.fopts` | `/dash/filter.opts` (htmx partial: the filter form's operator and value controls; registered first for the same reason) |

**Registering a database.** Only what's in `DBS` (`lego/dash/data.py`) is reachable.

```python
DBS.mydb = AttrDict(nm='My DB', dump='mydb.sql.gz', about='...')
```

Each entry is a SQLite file of its own at `data/db/<key>.db`, opened with `database(..., sem_search=False)` — a file per database is what keeps `users` and `posts` out of the explorer, since reflection reports whatever the connection has. Drop `dump` for a database that already exists at that path.

**Seeding.** Dumps live in `lego/dash/seed/` as gzipped SQL, statements split on a `\n--;--\n` separator, rejoined and applied as one script in one transaction. `seed()` runs only when the file has no tables in it, so it costs one `PRAGMA` per cold start after the first. `pragma defer_foreign_keys = on` holds the key checks until that commit — a dump loads a table at a time, so children land before parents and the database is only consistent once the whole script is in. A second process racing the same cold file gets "table already exists" and treats it as done.

The dump ships with the block rather than being downloaded: SQL pulled off the network at runtime is SQL that executes without review.

**Column roles** (`lego/dash/infer.py`) — assigned from declared type, name, and sampled stats:

| role | assigned when |
|---|---|
| `temporal` | date/time type, or a date-ish name whose min value parses as ISO |
| `measure` | numeric, non-key, non-zero σ |
| `dimension` | ≤ `cfg.max_cats` distinct, not mostly null, not effectively unique |
| `ref` | declared foreign key |
| `key` / `bool` / `text` / `const` | primary key · two-valued int · high-cardinality text · single-valued |

Chart rules score against these and the best `cfg.max_charts` render, at most 2 per table. Aggregation happens in SQL — no raw rows are pulled into Python. SQLite has no `STDDEV`, so σ comes from `sqrt(avg(x*x) - avg(x)^2)` in a single pass.

**Filters** (`lego/dash/filters.py`). One filter is `table:column:op:value`, carried in repeated `f=` query parameters — so a filtered dashboard is a URL you can share, the back button undoes a facet, and nothing is stored server-side.

```
/dash/chinook?f=Artist%3AName%3Aeq%3AAC%2FDC        every chart and tile on the dashboard
/dash/chinook/Track?f=Genre%3AName%3Aeq%3ARock&f=Genre%3AName%3Aeq%3AJazz
```

Two filters on the *same* column read as "either"; on different columns as "and". That is what ticking a second box in a facet list means, and the only reading under which it widens the result.

The load-bearing part is that a filter is not applied literally. "Only AC/DC" is a predicate on `Artist.Name`, but the chart it has to change is drawn from `Track`, or `InvoiceLine`, and those have no artist column. `path(db, src, dst)` breadth-first searches the declared foreign keys — walked **both** ways, down to a parent and up into a child — for the shortest route from the chart's own table to the filtered one, up to `cfg.max_hops`. `where()` renders that route as a correlated `EXISTS`. Track → Album → Artist is two hops; Orders → Order Details → Products → Categories is three.

A table with no route is reported in `where().dropped` rather than quietly returning everything, and the UI says so on the card (`Unfiltered — Customer has no relation to Artist`) and in the row counts. A chart that silently ignored the filter beside charts that honoured it would be read as data.

Applying it: `payload()` takes the parsed filters as `p['fs']` (or raw `f=` strings as `p['f']`); `count_rows`, `page_rows`, `stats` and `headline` all take `fs=`. Every chart aliases its base table to `"_b"` so the correlated subquery has one name to point at. Histogram bin edges keep coming from the *unfiltered* profile, so the same column keeps the same axis and two filters can be compared rather than just read; `stats` is the opposite case and re-measures in SQL, because the cached profile's mean describes rows the tile is no longer showing.

Adding one: charts are clickable (the mark already names the thing, so `spec.on` + `spec.keys[i]` become a filter — raw group keys travel separately from the clipped axis labels), dimension cells in the rows table are links, and the filter bar has a three-control form. That form posts `fc`/`fop`/`fv` separately, because one `<select>` cannot compose a `table:column:op:value` string without JS; `_added()` folds them in and 303s to the canonical `f=` URL, so what is in the address bar is always the filter.

**Identifier safety.** `ident(name, allowed)` raises unless `name` matches something the schema reported, then quotes it. Every table and column in a generated query goes through it; values are always bound. `_check()` in `charts.py` validates a whole chart request — including that a join is a *declared* foreign key — before any SQL is built. `parse()` holds filters to the same rule: a table, column or operator the schema does not report is dropped, never corrected, so a hand-edited URL never reaches SQL.

**fastlite, not fastsql.** Reflection reads `table.columns`, `table.pks` and `table.foreign_keys` rather than SQLAlchemy metadata, and `db.q(sql, params)` takes its binds as a dict. A rowid table reports `pks == ['rowid']`; `reflect()` returns `pk=[]` for it, and only a single-column key gets linked to a row page — a composite key needs every part, and a row URL carries one value.

**Profiles** are cached in `data/db/dash.db` under a hash of the schema plus row count, so they survive restarts and invalidate when the data changes. Bump `_PROFILE_V` when the stats collected in `_measure` change.

**Config** (`lego/dash/cfg.py`): `public` (`DASH_PUBLIC`, default on), `rows_per_page`, `sample_rows`, `max_cats`, `bar_cats`, `pie_cats`, `top_n`, `hist_bins`, `max_charts`, `rel_preview`, `max_filters`, `max_hops`, `filter_values`.

`filter_values` is deliberately not `max_cats`: that one is about what makes a readable *chart*, and 275 artists is a hopeless doughnut but a perfectly good dropdown.

### Charts

Chart.js 4 is vendored at `static/vendor/chart.umd.min.js` (204 KB raw / 69 KB gzip, no runtime deps) and only loaded on `/dash` routes, via `dash_head()`, alongside `lego/dash/chart.js` (the wrapper) and `lego/dash/dash.css` (every style `/dash` renders, including the `--chart-*` tokens). Nothing the block needs lives outside the block.

Series colours are `--chart-1` … `--chart-8` in `dash.css`. They are **fixed across all themes on purpose**: the hue *order* is what keeps adjacent series apart under protanopia and deuteranopia, so re-tinting per palette would break it. Chart chrome — `--chart-grid`, `--chart-axis`, `--chart-tick` — does follow the theme.

Three light-mode slots sit under 3:1 contrast, so every chart ships the relief channel: direct value labels on bars plus a "Show data" table built from the same payload.

Reading a custom property with `getComputedStyle` returns its raw token stream, so `light-dark(...)` comes back unresolved. `chart.js` paints each var onto a throwaway probe element and reads back the computed colour instead. A `MutationObserver` on `documentElement`'s class list repaints every live chart when `setTheme`/`setMode` fires.

Charts fetch their data from `/dash/chart.json` on intersection, so a page of eight charts issues eight small parallel queries rather than one slow render.

## Adding a new block

1. Create `lego/myblock/` with `__init__.py`, `cfg.py`, `data.py`, `ui.py`, `app.py`
2. Declare public routes in `cfg.py`:
   ```python
   @dataclass(frozen=True)
   class Routes:
       base = '/myblock'
       skip = ['/myblock', r'/myblock/.*']
   ```
3. Implement `connect(app)` in `app.py`:
   ```python
   def connect(app):
       seed_data()
       RouteOverrides.skip += Routes.skip
       app.get(Routes.base)(my_index)
   ```
4. Wire it in `lego/app.py` before `a.connect(lego)`:
   ```python
   import lego.myblock as mb
   mb.connect(lego)
   a.connect(lego)   # still last
   ```

## Conventions

- **No decorator-style route registration.** Use `app.get(route)(handler)` inside `connect()`, not `@app.get(route)`.
- Auth **always connects last** — it reads the complete `RouteOverrides.skip` list at connect time.
- Route handlers take `req` first, then `auth` — injected by `before()` in `app.py`.
- Use fastai/fastcore idioms: `L`, `AttrDict`, `Path`, `ifnone`, `store_attr`, `patch`. No classes unless genuinely needed.
- No ruff, no PEP 8. Short functions, no docstrings unless the function name isn't self-explanatory.
- `seed_*` functions are idempotent: check for existing records by slug/key before inserting.
- Use `partition` from fasthtml to pin or reorder query results without a full sort.
