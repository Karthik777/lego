# lego

A FastHTML + Oat web app starter. Powers [vedicreader.com](https://vedicreader.com/).

Clone it, connect your blocks, ship it.

## Getting started

```bash
git clone https://github.com/Karthik777/lego.git
cd lego
uv sync
uv run lego-setup       # scaffold .env.example, .github workflow, and SKILL.md files
uv run python main.py   # http://localhost:5001
```

`lego-setup` is idempotent and safe to re-run. The console scripts shipped with the package:

| script | purpose |
|---|---|
| `uv run lego-setup` | init gheasy config, git-lfs patterns, `.env.example`, deploy workflow, install skills |
| `uv run lego-skill` | (re)install `SKILL.md` into `.claude/skills/lego/` and `.agents/skills/lego/` |
| `uv run lego-push` | push values from `.env` to GitHub Actions secrets/vars (use `--dry-run` to preview) |
| `uv run lego-deploy` | Docker + Hetzner + Cloudflare tunnel deploy (`compose` \| `deploy` \| `nuke` \| `env`) |

## How it works

Each feature is a block: a self-contained module with its own config, routes, and database. You connect blocks to the app in order. Auth reads the full skip list at connect time, so it goes last.

```python
# lego/app.py
b.connect(lego)   # blog
a.connect(lego)   # auth — always last
```

Each block exposes a `connect(app)` function that registers routes, seeds data, and wires up any middleware it needs. Blocks can share a database or borrow config from each other. They can also override routes registered by earlier blocks — first in line wins.

## What's included

**core** handles config, logging, caching, scheduled jobs, backups, and the base UI (navbar, theme switcher, page layouts). Everything else builds on it.

**auth** covers email/password registration with Resend verification, Google OAuth, and GitHub OAuth. One `connect()` call sets up all routes and session middleware. Route paths are overridable via `RouteOverrides`.

**blog** is a full publishing block. Posts are seeded from Markdown files with YAML frontmatter. The list page uses a newspaper-style featured/sidebar/grid layout. Post detail pages support single-column or two-column newspaper layout, set per-post via `layout: newspaper` in the frontmatter. Code blocks never split across columns. To force a column break at a specific point in a post, add:

````md
```col
```
````

## Project structure

```
lego/
├── main.py
├── lego/
│   ├── app.py           # wire up blocks, scheduled jobs
│   ├── auth/            # auth block
│   ├── blog/            # blog block
│   └── core/            # config, cache, logging, backups, UI
├── data/
│   ├── db/              # SQLite databases
│   ├── logs/
│   └── cache/           # DiskCache
└── static/
```

## Core utilities

### Logging

```python
from lego.core import quick_lgr

info, error, warn = quick_lgr()
info("started")
```

`quick_lgr()` reads the calling file's name and uses it as the log filename. No configuration needed.

### Caching

```python
from lego.core import cache

@cache(ttl=3600)
def expensive(param):
    return compute(param)
```

DiskCache-backed with stampede protection. Keys are scoped to the function by `__qualname__` plus arguments.

### Backups

```python
from lego.core.backups import run_backup, clone

run_backup(src="data/db", max_ages="2,14,60")
clone(src="data/db", bucket="my-app-db")   # Cloudflare R2 or S3 via rclone
```

`run_backup` keeps age-tiered snapshots. `clone` syncs to remote storage. Both are scheduled in `app.py` by default when `NEED_BACKUP=true`.

### Distributed lock

```python
from lego.core import get_lock, release_lock

if get_lock('my-job', ttl=60):
    do_work()
    release_lock('my-job')
```

## Auth setup

Email/password:
```
RESEND_API_KEY=re_...
```

Google OAuth:
```
WANT_GOOGLE=true
GOOGLE_CLI=...
GOOGLE_SCRT=...
# callback: {DOMAIN}/a/google/callback
```

GitHub OAuth:
```
WANT_GIT=true
GIT_CLI=...
GIT_SCRT=...
# callback: {DOMAIN}/a/github/callback
```

Google and GitHub users are activated immediately. Email/password users get a verification link via Resend.

To change the default route paths:

```python
from lego.core import RouteOverrides
RouteOverrides.lgn = "/login"
RouteOverrides.home = "/dashboard"
RouteOverrides.skip += ["/public"]
```

## Extensions

The dev toolchain that ships with lego:

- **[kosha](https://github.com/vedicreader/kosha)** — indexes your repo and installed packages into a hybrid search + call graph database. Agents query it before writing code.
- **[dockeasy](https://github.com/vedicreader/dockeasy)** — Dockerfile, Caddyfile, and Compose builder in Python. Framework-aware defaults, cache mounts by default, Cloudflare tunnel support.
- **[vpseasy](https://github.com/vedicreader/vpseasy)** — provisions Hetzner VPS servers, deploys with Docker Compose, handles Caddy and tunnels. Same cloud-init YAML runs in local Multipass VMs and production.
- **[cfeasy](https://github.com/vedicreader/cfeasy)** — idempotent Cloudflare DNS and Zero Trust tunnel management. One call to create a tunnel, wire the DNS, and get the token back.
- **[gheasy](https://github.com/vedicreader/gheasy)** — GitHub Actions workflows in Python. Pre-built jobs for test, lint, and PyPI publish. Secret routing from env schema to `gh secret set`.

`deploy.py` in the repo shows all of them composing together — Dockerfile, Compose stack, tunnel, VPS provision, and env wiring in one script.

## Deployment

lego is an ASGI app. `deploy.py` uses dockeasy + vpseasy + cfeasy for a full Hetzner + Cloudflare tunnel deploy:

```bash
uv run lego-deploy deploy    # provisions VPS, wires tunnel, deploys
uv run lego-deploy compose   # generate docker-compose.yml only
uv run lego-deploy nuke      # delete VPS and tunnel (irreversible)
uv run lego-push             # push .env values to GitHub Actions
```

The app runs at [lego.sankalpa.sh](https://lego.sankalpa.sh).

For remote storage, point `get_pth` in `core/cfg.py` at an S3 bucket via fsspec.

## Style

No ruff, no PEP 8. The code uses fastai idioms: `store_attr`, `patch`, `AttrDict`, `L`. Short functions, no docstrings unless the function name isn't enough. It reads fine on a phone.

## License

MIT
