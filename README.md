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

**muhurtha** is a panchangam that is also a calendar server. It computes the five limbs — tithi, vara, nakshatra, yoga, karana — the thirty muhurtas, the twenty-four horas and the kalams, and it publishes all of it as an iCalendar feed and a read-only CalDAV collection, so Google Calendar and Apple Calendar can subscribe to the traditional day. It serves `/muhurtha` here and the whole of [sankalpa.sh](https://sankalpa.sh).

**hora** is Vedic planetary hours, computed in the browser from the local sunrise and sunset. It is the block that shows what "self-contained" can stretch to: it brings its own head, its own Tailwind stylesheet and its own document, so none of the app-wide chrome reaches it. It still answers at `/hora`; the muhurtha block carries the same computation next to the rest of the almanac.

**thrifty** prices the total cost of ownership of LLM and agent platforms — models, agents, iterations and volumes in, per-request and monthly cost out, against pricing it fetches live from LiteLLM and OpenRouter. Like hora it is a whole document of its own, on its own stylesheet. It serves `/thrifty` here and the whole of [thrifty.sankalpa.sh](https://thrifty.sankalpa.sh).

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
│   ├── hora/            # hora block
│   ├── muhurtha/        # panchangam calendar + ICS/CalDAV server — also serves sankalpa.sh
│   ├── thrifty/         # thrifty block — also serves thrifty.sankalpa.sh
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

## Muhurtha — the panchangam as a calendar

The small version of "put the panchangam in my calendar" adds events to a calendar. The large version replaces the clock. A tithi is not a day: it ends when the moon has gained another twelve degrees on the sun, somewhere between nineteen and twenty-six hours later. A muhurta is not forty-eight minutes: it is a thirtieth of sunrise to sunrise, so it breathes with the season. None of it lands on the hour, and none of it is the same in two places.

So the block computes spans, not dates, and publishes them in the two formats every calendar app already speaks.

### Subscribing

Visit `/muhurtha/subscribe`, pick which layers you want, and take the link.

| layer | what it puts in your calendar |
|---|---|
| `day` | one all-day entry per day, with the whole almanac in the description |
| `panchanga` | tithi and nakshatra as timed spans, ending when they actually end |
| `kalam` | Rahu kalam, Yamagandam, Gulika kalam |
| `window` | Brahma muhurta, Abhijit, Godhuli, Nishita |
| `hora` | all 24 planetary hours |
| `muhurta` | all 30 muhurtas |

```
https://lego.sankalpa.sh/muhurtha/feed.ics?lat=13.0827&lon=80.2707&tz=Asia/Kolkata&place=Chennai&layers=day,kalam,window
```

**Google Calendar** — web only, *Other calendars* → **+** → **From URL**. Google refreshes external calendars on its own schedule, usually every 8 to 24 hours.

**Apple Calendar** — **File → New Calendar Subscription**, or the CalDAV collection below, which refreshes on the client's schedule instead of Google's. Google Calendar cannot subscribe to CalDAV at all, which is why the .ics feed is the primary path.

```
https://lego.sankalpa.sh/muhurtha/dav/<token>/
```

The CalDAV tree is read-only and needs no credentials. The token is the place and the layer choice, base64url'd — a URL is a complete description of the calendar it returns, so nothing is stored server-side.

Timed events go out in UTC with a trailing `Z` rather than carrying a `VTIMEZONE`. These are astronomical instants, not wall-clock appointments; every client renders them correctly in its own zone, and there is no zone definition to disagree over. All-day entries use local `DATE` values, because "which day" is a local question.

There is also `/muhurtha/api/day` and `/muhurtha/api/month`, which return the same computation as JSON.

### Where the numbers come from

No Swiss Ephemeris — the licence is a problem for anything you want to ship freely. No skyfield either, which is excellent and wants a 17MB kernel it downloads at import.

`lego/muhurtha/ephem.py` is Meeus' truncations of VSOP87 for the sun and ELP2000-82 for the moon, in about two hundred lines of pure Python with no dependencies and no data files. Checked against Meeus' own worked examples and against JPL DE421:

| | vs DE421 |
|---|---|
| moon longitude | within 7″ |
| sun longitude | within 21″ |
| tithi / nakshatra boundaries | within ~4 seconds of time |

Sunrise and sunset are found by bracketing the altitude and rooting it, which handles the polar cases by returning nothing to root rather than by dividing by zero.

Positions are sidereal, **Lahiri (Chitrapaksha)** ayanamsa — the choice that decides whether the nakshatra here matches the one in a printed almanac.

One caveat worth stating plainly: this is a **dṛk** (observational) panchangam. A **vākya** almanac computed from the older Sūrya Siddhānta tables — which is what many printed Tamil calendars are — will differ, sometimes by more than an hour on a tithi ending. Neither is a mistake; they are different reckonings.

### Optional: jyotishganit

The calendar does not need it. For the layer above an almanac — divisional charts, vimshottari dasha, ashtakavarga — set `MUHURTHA_JYOTISHGANIT=true` and install [jyotishganit](https://github.com/northtara/jyotishganit). It brings skyfield, and downloads `de421.bsp` and the Hipparcos catalogue on first use, which is exactly why it is opt-in. If it is off, absent or broken, the calendar is unchanged.

### Config

```
MUHURTHA_LAT=13.0827          # default place when a visitor has not chosen one
MUHURTHA_LON=80.2707
MUHURTHA_TZ=Asia/Kolkata
MUHURTHA_PLACE=Chennai
MUHURTHA_DOMAIN=sankalpa.sh   # canonical and og: URLs
MUHURTHA_FEED_DAYS=180        # rolling window; dense layers are capped shorter
MUHURTHA_JYOTISHGANIT=false
APEX_ROUTE=/muhurtha          # what sankalpa.sh serves at its root
```

## Deployment

lego is an ASGI app. `deploy.py` uses dockeasy + vpseasy + cfeasy for a full Hetzner + Cloudflare tunnel deploy:

```bash
uv run lego-deploy deploy    # provisions VPS, wires tunnel, deploys
uv run lego-deploy compose   # generate docker-compose.yml only
uv run lego-deploy nuke      # delete VPS and tunnel (irreversible)
uv run lego-push             # push .env values to GitHub Actions
```

The app runs at [lego.sankalpa.sh](https://lego.sankalpa.sh).

### Three hostnames, one deployment

[sankalpa.sh](https://sankalpa.sh) and [thrifty.sankalpa.sh](https://thrifty.sankalpa.sh) are the same deployment. Not a second server, a second container, a second tunnel or even a second Cloudflare zone — the hora block already answers at `/hora` and thrifty at `/thrifty`, so all the extra hosts need is for Caddy to know about them:

```
http://lego.sankalpa.sh {
	reverse_proxy app:5001
}
http://sankalpa.sh {
	rewrite / /muhurtha
	reverse_proxy app:5001
}
http://thrifty.sankalpa.sh {
	rewrite / /thrifty
	reverse_proxy app:5001
}
```

`cloudflared` runs with `--url http://caddy`, so every hostname routed through the tunnel arrives at that same Caddy, and Caddy tells them apart by the Host header it was going to read anyway. `deploy2prod` adds each extra host as a proxied CNAME to the tunnel it just set up — proxied because an apex cannot hold a CNAME in plain DNS and Cloudflare serves one by flattening it. Any A record or parked CNAME already on the name is replaced. If a host fails it warns with the record to add by hand, carries on to the rest, and the lego deploy is unaffected.

Only the bare `/` is rewritten, so `/static` and every other path still resolve normally on every hostname. `deploy.py`'s `SITES` is the whole list: a hostname to the route it should serve. To move a block elsewhere set `HORA_DOMAIN` or `THRIFTY_DOMAIN` — each feeds both the Caddyfile and its block's canonical and `og:` URLs.

For remote storage, point `get_pth` in `core/cfg.py` at an S3 bucket via fsspec.

## Style

No ruff, no PEP 8. The code uses fastai idioms: `store_attr`, `patch`, `AttrDict`, `L`. Short functions, no docstrings unless the function name isn't enough. It reads fine on a phone.

## License

MIT
