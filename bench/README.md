# Where lego's request time goes

Measured on this branch, Python 3.13, loopback, `MODE=production`. p50 unless noted.
Reproduce with the scripts here.

## The question that started it

Would putting lego on a Rust-cored HTTP server (Robyn) instead of Starlette + uvicorn make
it snappier?

No. Same client, same machine, no-op JSON route:

| stack | p50 | rps (1 conn) | rps (8 conns) |
| --- | --- | --- | --- |
| Robyn 0.88 (Rust core) | 0.23 ms | 3921 | 6056 |
| bare Starlette + uvicorn | 0.33 ms | 2036 | 3525 |
| lego on FastHTML (`/health`) | 1.38 ms | 675 | 787 |

Robyn beats Starlette by **0.10 ms**. FastHTML costs **1.05 ms** on top of Starlette. And
lego's real pages cost 9 ms to 851 ms against an HTTP floor of 0.52 ms — so the transport
was never what anyone was waiting for.

Robyn as a host, factually: runs on 3.13, but has **no ASGI or WSGI bridge**. Its own Rust
core and request types, so Starlette's `SessionMiddleware`, `StaticFiles`, `Mount`,
`exception_handlers` and `fasthtml.oauth` (written against Starlette's `Request`) do not
carry over. Its `Request` exposes `body files form_data headers identity ip_addr json
method path_params query_params session url` — no `scope`, and `lego/auth` reads
`req.scope['auth']` and `req.scope['session']` throughout.

## What was done instead

Five changes, all measured back to back against `main` in one session:

| route | main | now | |
| --- | --- | --- | --- |
| `/health` | 2.27 ms | 1.69 ms | 1.3x |
| `/` | 12.05 ms | 9.38 ms | 1.3x |
| `/blog` | 12.86 ms | 10.20 ms | 1.3x |
| `/dash` | 149.0 ms | 8.12 ms | **18x** |
| `/dash/chinook` | 137.2 ms | 34.6 ms | 4.0x |
| `/dash/nycflights` | 1140.3 ms | 18.9 ms | **60x** |
| `/dash/nycflights/Flight` | 521.6 ms | 69.4 ms | 7.5x |

Throughput at 8 concurrent connections, 4 workers on a 4-core box (load generator on the
same box, so this is a floor): `/health` 787 → 1419 rps, `/` 82 → 151, `/dash` 81 → 199,
`/dash/nycflights` 45 → 110.

Bytes on the wire, which is what a reader on mobile actually waits for:

| route | before | after (gzip) | |
| --- | --- | --- | --- |
| `/` | 23.0 KB | 5.9 KB | 3.9x |
| `/dash` | 20.5 KB | 4.9 KB | 4.2x |
| `/dash/nycflights` | 26.1 KB | 5.2 KB | 5.0x |
| `/dash/chinook/Track` | 63.2 KB | 7.5 KB | 8.4x |

Plus eleven blocking third-party subresources across four hosts removed from the head.

### 1. Reflection was never memoised (`lego/dash/data.py`)

`/dash` asked all nineteen databases for their schema and every table's row count to draw
the cards, and the profile cache in dash.db then asked for both again to build the key it
looks itself up by: **1147 SQL statements and 18 fresh apsw connections per request** for a
page whose answer never changes. `table_names`, `schema`, `reflect`, `rowcount`, the schema
hash and the profile are now memoised against the database file's `(mtime_ns, size)`, so a
file swapped under a running app still invalidates itself.

Two scans survived that, both derived facts that were not going through the cache built for
them: `values_for` ran `select distinct` over a whole column to fill a dropdown, and
`stats()` took its median and p95 with `order by ... limit 1 offset k`, which sqlite answers
by sorting the column into a temp b-tree — 300 ms twice on 336,776 flights.

### 2. Concurrent requests crashed (`lego/core/cfg.py`)

Eight concurrent requests to `/` raised `apsw.ThreadingViolationError` and dropped the
response. Starlette runs sync handlers on a threadpool; blog and auth bound their tables to
one connection at import. Binding is what made it one connection — `posts = db.t.posts`
holds the connection it was built from — so `thread_db` resolves both the database and the
table per thread. 800 concurrent requests across three routes now complete clean.

### 3. Nothing was compressed, everything was remote

No gzip middleware at all, and eleven subresources from jsdelivr, cdnjs and Google Fonts —
three of them on `@latest` or `@main`, which cannot be cached for long and can change under
a deployed app. `tools/vendor_fetch.py` pulls them into `static/vendor` behind the immutable
mount; `GZipMiddleware` at a 1 KB floor keeps compression off the small htmx fragments.

### 4. The chrome was rebuilt every response (`lego/core/ui.py`)

Building a page's FT tree costs ~4x serialising it, and most of what got built was
invariant. The navbar takes `usr` as a boolean and nothing else that varies; the sprite
sheet is fixed; the head is a constant. Held as `NotStr` they cost nothing to build, nothing
to serialise, and fasthtml's `_find_targets` walk skips them.

fasthtml also deep-copies app `hdrs` on every request so a handler can add to the head for
one response. Nothing here does, and lego's list is thirty-odd nodes including the whole
theme stylesheet: ~350 recursive `deepcopy` calls per request, `/health` included.

The sprite sheet emitted in **set-iteration order**, so the same page was different bytes in
each process. Now sorted — which is also what makes it cacheable.

### 5. One worker, and the reloader on in production

`serve` defaults to `reload=True` and `launch()` never overrode it, so production ran
uvicorn's file-watching supervisor against a container whose files do not change. It is also
mutually exclusive with workers. Now: reload in dev, `min(4, cpu_count)` workers in
production, `WEB_CONCURRENCY` to override.

## What is left, and where Robyn's premise finally applies

`/dash/nycflights/Flight` is 69 ms for a 100 KB page, and its profile now has **no SQL in it
at all** — 1973 `ft_html` calls, 3951 `FT.__init__`, 19763 `FT.__setattr__`, 1037400
`typing.__subclasscheck__` per request. The same is true of `/` at 9 ms: 3.3 ms is
`_blog()` building the post list, 0.02 ms is the chrome, and the rest is fasthtml around it.

So the shape of the problem has inverted. It started 75% SQLite and 0.2% HTTP; it is now
essentially all FT tree construction. That is the ~1 ms/page FastHTML overhead from the top
of this file, and it is now the dominant term rather than a rounding error.

If the leaner-FastHTML idea is worth revisiting, this is the evidence for it — and note that
it is still an argument about the **rendering layer**, not the HTTP core. Robyn's 0.10 ms is
as irrelevant now as it was before. The targets are `FT.__init__`/`__setattr__`, the
`typing.__subclasscheck__` storm in `_preproc`, and the `_find_targets` walk.

## Scripts

| script | what it does |
| --- | --- |
| `bench.py PORT [paths...]` | keep-alive load generator, p50/p95/rps |
| `prof.py [paths...]` | drives the ASGI app in-process, cProfile per route |
| `split.py` | attributes cost to HTTP floor vs FT build vs serialise vs SQL |
| `snap.py` | renders a fixed route set and hashes the bodies, to prove output is unchanged |
| `robyn_baseline.py` | Robyn no-op + 23 KB HTML on :5002 |
| `starlette_baseline.py` | bare Starlette equivalents on :5003 |

```bash
MODE=production uv run uvicorn lego:lego --port 5001 --no-access-log &
uv run python bench/bench.py 5001 /health / /dash
MODE=production uv run python bench/split.py
MODE=production uv run python bench/prof.py /dash

# output-unchanged check: pin the hash seed, snapshot, switch, snapshot, diff
PYTHONHASHSEED=0 MODE=production uv run python bench/snap.py > after.txt
```
