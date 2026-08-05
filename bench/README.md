# Where lego's request time actually goes

Measured on this repo at `1909505`, Python 3.13, one uvicorn worker, loopback,
`MODE=production`. Numbers are p50 unless noted. Reproduce with the scripts here.

## The question

Would putting lego on a Rust-cored HTTP server (Robyn) instead of Starlette +
uvicorn make it snappier?

## The answer, in one table

Same client, same machine, no-op JSON route:

| stack | p50 | rps (1 conn) | rps (8 conns) |
| --- | --- | --- | --- |
| Robyn 0.88 (Rust core) | 0.23 ms | 3921 | 6056 |
| bare Starlette + uvicorn | 0.33 ms | 2036 | 3525 |
| lego on FastHTML (`/health`) | 1.38 ms | 675 | 787 |

Robyn beats Starlette by **0.10 ms**. FastHTML costs **1.05 ms** on top of
Starlette. The overhead worth removing is 10x larger than the overhead Robyn
removes, and it is not in the HTTP core — it is in Python, and it moves with the
handler wherever you host it.

Against real pages the HTTP layer disappears entirely:

| route | total | HTTP floor | share of total the HTTP core can touch |
| --- | --- | --- | --- |
| `/health` | 1.8 ms | 0.52 ms | ~6% |
| `/` (23 KB) | 9.1 ms | 0.52 ms | ~1% |
| `/dash` (21 KB) | 50 ms | 0.52 ms | ~0.2% |
| `/dash/nycflights` | 851 ms | 0.52 ms | ~0.01% |

## Where it really goes

`/` — 9.1 ms, and 5.9 ms of it is building and serialising the FT tree:

- `base(_blog(None))` tree construction: **4.7 ms**
- `to_xml(tree)`: **1.2 ms**
- per request: 2245 `FT.__setattr__`, 449 `FT.__init__`, 1600
  `typing.__subclasscheck__`, 10512 `isinstance`, 355 `_find_targets` walks

Tree construction costs 4x what serialising it costs. The head, nav and theme
block are byte-identical on every request and get rebuilt every time.

`/dash` — 50 ms, 88% of it inside the handler, 75% inside SQLite metadata:

- `index_view` → `_db_card` × 19 databases → `schema()` + `rowcount()` each
- **1147 `apsw.Connection.execute` per request**
- **18 fresh `apswutils.Database` objects per request**, each running apsw
  `bestpractice` pragmas (90 `pragma` calls/request)
- 529 `table_names()` and 89 `reflect()` calls per request

`/dash/nycflights` — 851 ms, worst single page. `table_view` on the `Flight`
table alone is 323 ms, of which 276 ms is raw `execute` over 1225 statements:
59 `rowcount()` (`COUNT(*)` on a large table), 51 `_schema_hash()`, 47
`profile()`.

Nothing in either dash number is HTTP. It is uncached schema reflection.

## Two things found on the way

**`apsw.ThreadingViolationError` under concurrent load.** Eight concurrent
requests to `/` produce `Cursor couldn't run because the Connection is busy in
another thread` and drop connections. Sync handlers run in Starlette's
threadpool while the apsw connection is shared, so this is a live production
bug — and a faster, more parallel front end makes it *more* likely, not less.

**No response compression.** `/` ships 23,652 bytes uncompressed; there is no
gzip/brotli middleware. The head also pulls 11 blocking third-party assets
(jsdelivr, cdnjs, Google Fonts), several pinned to `@latest` / `@main`. On a
mobile connection those two facts cost more than every framework number on this
page put together.

## Robyn as a host, factually

- Installs and runs on 3.13. Not a blocker.
- **No ASGI or WSGI bridge.** Its own Rust core and its own request/response
  types, so Starlette's `SessionMiddleware`, `StaticFiles`, `Mount`,
  `exception_handlers` and `fasthtml.oauth` (which is written against Starlette's
  `Request`) do not carry over.
- `Request` exposes `body files form_data headers identity ip_addr json method
  path_params query_params session url` — but no `scope`, and lego reads
  `req.scope['auth']` and `req.scope['session']` throughout `lego/auth`.

## Scripts

| script | what it does |
| --- | --- |
| `bench.py PORT [paths...]` | keep-alive load generator, p50/p95/rps |
| `prof.py [paths...]` | drives the ASGI app in-process, cProfile per route |
| `split.py` | attributes cost to HTTP floor vs FT build vs serialise vs SQL |
| `robyn_baseline.py` | Robyn no-op + 23 KB HTML on :5002 |
| `starlette_baseline.py` | bare Starlette equivalents on :5003 |

```bash
MODE=production uv run uvicorn lego:lego --port 5001 --no-access-log &
uv run python bench/bench.py 5001 /health / /dash
MODE=production uv run python bench/split.py
MODE=production uv run python bench/prof.py /dash
```
