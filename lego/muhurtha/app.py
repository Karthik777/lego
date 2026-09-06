'''Routes.

Two audiences share one computation: a browser that wants a calendar to look at, and a
calendar client that wants a file to subscribe to. The engine does not know the difference,
so neither do these handlers -- they differ only in what they serialise.'''

import json
from datetime import date as Date, datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones
from calendar import month_name
from urllib.parse import quote, unquote
from fasthtml.common import JSONResponse, NotStr, RedirectResponse, cookie, to_xml
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response
from starlette.routing import Route
from lego.core import RouteOverrides, cache, quick_lgr
from .cfg import cfg, Routes, LAYERS, DEFAULT_LAYERS
from .panchanga import Place, day_panchanga, month_panchanga
from .feed import build_feed
from .dav import dav_handle, encode_token, well_known
from . import ui

__all__ = ['connect']

info, error, warn = quick_lgr()
_TZS = available_timezones()

# === request parsing ===

def _f(qp, k, d):
    try: return float(qp.get(k, d))
    except (TypeError, ValueError): return float(d)

PLACE_COOKIE = 'mh_place'
_COOKIE_AGE = 365*24*3600

def _wrap_lon(x):
    """Fold a longitude into -180..180, exactly, when it is already there.

    `((x + 180) % 360) - 180` is the usual one-liner and it is not exact: 80.2707 comes back
    as 80.27070000000003, which is close enough for the ephemeris and not close enough for
    an equality test. That is how the default place lost its name and the page started
    calling Chennai 13.08°N 80.27°E."""
    return x if -180 <= x <= 180 else ((x + 180) % 360) - 180

def _named(lat, lon, tz, nm):
    'Fill in the configured name when the coordinates are the configured ones.'
    if not nm and abs(lat - cfg.lat) < 1e-6 and abs(lon - cfg.lon) < 1e-6:
        nm = cfg.place_name
    return Place(lat, lon, tz, nm)

def _default_place(): return _named(cfg.lat, cfg.lon, cfg.tz, '')

def _from_qp(qp):
    lat = max(-89.9, min(89.9, _f(qp, 'lat', cfg.lat)))
    lon = _wrap_lon(_f(qp, 'lon', cfg.lon))
    tz = qp.get('tz') or cfg.tz
    if tz not in _TZS: tz = cfg.tz
    return _named(lat, lon, tz, (qp.get('place') or '').strip()[:60])

def _remembered(req):
    'The place the reader last chose, off the cookie.'
    raw = req.cookies.get(PLACE_COOKIE)
    if not raw: return None
    try:
        lat, lon, tz, nm = unquote(raw).split('|', 3)
        if tz not in _TZS: return None
        return _named(max(-89.9, min(89.9, float(lat))), _wrap_lon(float(lon)), tz, nm[:60])
    except (ValueError, KeyError): return None

def chose_place(req): return any(k in req.query_params for k in ('lat', 'lon', 'tz', 'place'))

def place_of(req):
    """The place a request is about.

    Query string first, then the place the reader last chose, then the block default. The
    middle one is the whole point: the place used to live only in the URL, so the navbar
    pill -- which cannot carry a query string, it is registered once at connect time -- and
    any plain reload dropped it back to the default."""
    return _from_qp(req.query_params) if chose_place(req) else (_remembered(req) or _default_place())

def remember(place, req):
    'Set-Cookie for a place the reader picked; nothing when they did not pick one.'
    if not chose_place(req): return None
    v = quote(f'{place.lat:.4f}|{place.lon:.4f}|{place.tzname}|{place.name}')
    return cookie(PLACE_COOKIE, v, max_age=_COOKIE_AGE, path='/', samesite='lax')

def layers_of(req, default=DEFAULT_LAYERS):
    raw = req.query_params.get('layers')
    if not raw: return list(default)
    want = [x.strip() for x in raw.split(',')]
    return [l for l in LAYERS if l in want] or list(default)

def date_of(req, place, key='date'):
    v = req.query_params.get(key)
    try: return Date.fromisoformat(v) if v else datetime.now(place.tz).date()
    except ValueError: return datetime.now(place.tz).date()

def _int(req, k, d):
    try: return int(req.query_params.get(k, d))
    except (TypeError, ValueError): return d

def base_url(req):
    # Behind Caddy and a Cloudflare tunnel the scheme on the socket is http; the forwarded
    # header is what the visitor actually typed, and what a calendar client must be given.
    proto = req.headers.get('x-forwarded-proto') or req.url.scheme
    host = req.headers.get('x-forwarded-host') or req.headers.get('host') or cfg.domain
    return f'{proto}://{host}'

# === cached builders ===
# The panchangam for a place and a day is the same for everybody who asks, and costs real
# arithmetic, so it is memoised on its inputs rather than recomputed per request.

@cache(ttl=cfg.cache_ttl)
def _feed(key, tz, nm, layers, back, days):
    lat, lon = (float(x) for x in key.split(','))
    return build_feed(Place(lat, lon, tz, nm), layers, back, days)

@cache(ttl=cfg.cache_ttl)
def _month_body(key, tz, nm, y, m, today, ui_version):
    """The month grid and its boot payload, memoised.

    Only the block's own markup is cached, not the page around it: the navbar differs
    between a signed-in and a signed-out reader, and the shell is cheap to rebuild."""
    place = _mk(key, tz, nm)
    d = Date.fromisoformat(today)
    return to_xml(ui.month_view(place, y, m, d)), _boot(day_panchanga(place, d))

def _mk(key, tz, nm):
    lat, lon = (float(x) for x in key.split(','))
    return Place(lat, lon, tz, nm)

# === handlers ===

def _boot(p, **extra):
    """What the page script needs that the markup does not already carry.

    The now band appears on every page, but the hora and muhurta lists it reads only exist
    on a day page -- so the running blocks travel here instead, and the band works the same
    whether or not the day it describes is on screen."""
    return json.dumps(dict(
        tz=p['tz'], tithiEnd=p['tithi']['end'], nakEnd=p['nakshatra']['end'],
        horas=[[h['name'], h['start'], h['end'], h['phase']] for h in p['horas']],
        muhurtas=[[m['name'], m['start'], m['end'], m['index']] for m in p['muhurtas']],
        subs={h['start']: [[s['planet'], s['start'], s['end']] for s in h['subs']]
              for h in p['horas']}, **extra))

def index(req):
    return RedirectResponse(f'{Routes.month}?{req.url.query}' if req.url.query else Routes.month)

def month_page(req, auth=None):
    place = place_of(req)
    today = datetime.now(place.tz).date()
    y, m = _int(req, 'y', today.year), _int(req, 'm', today.month)
    if not (1 <= m <= 12) or not (1900 <= y <= 2200): y, m = today.year, today.month
    key = f'{place.lat:.4f},{place.lon:.4f}'
    body, boot = _month_body(key, place.tzname, place.name, y, m, today.isoformat(), ui.UI_VERSION)
    return (*ui.page(f'{month_name[m]} {y} · {place.name or ui.coords(place)} · Muhurtha',
                     place, NotStr(body), auth, active='month', boot=boot), remember(place, req))

def day_page(req, auth=None):
    place = place_of(req)
    d = date_of(req, place)
    p = day_panchanga(place, d, planets=False, spans=False)
    body = ui.day_view(place, d, datetime.now(place.tz).date())
    return (*ui.page(f"{d.isoformat()} · {p['tithi']['name']} · {place.name or ui.coords(place)}",
                     place, body, auth, active='day', boot=_boot(day_panchanga(place, d))),
            remember(place, req))

def subscribe_page(req, auth=None):
    place = place_of(req)
    boot = json.dumps(dict(davBase=f'{base_url(req)}{Routes.dav}/',
                           place=[round(place.lat, 4), round(place.lon, 4),
                                  place.tzname, place.name]))
    return (*ui.page(f'Subscribe · {place.name or ui.coords(place)} · Muhurtha', place,
                     ui.subscribe_view(place, base_url(req)), auth, active='subscribe', boot=boot),
            remember(place, req))

def feed_ics(req):
    place, layers = place_of(req), layers_of(req)
    back, days = _int(req, 'back', None), _int(req, 'days', None)
    body = _feed(f'{place.lat:.4f},{place.lon:.4f}', place.tzname, place.name,
                 tuple(layers), back, days)
    fn = (place.name or 'muhurtha').lower().replace(' ', '-')
    return Response(body, media_type='text/calendar; charset=utf-8', headers={
        'Content-Disposition': f'inline; filename="{fn}-panchangam.ics"',
        'Cache-Control': 'public, max-age=3600'})

def api_day(req):
    place = place_of(req)
    d = date_of(req, place)
    out = day_panchanga(place, d)
    from . import jg
    c = jg.chart_for(place, datetime.fromisoformat(out['sunrise']))
    if c: out['chart'] = c
    return JSONResponse(out)

def api_month(req):
    place = place_of(req)
    today = datetime.now(place.tz).date()
    return JSONResponse(month_panchanga(place, _int(req, 'y', today.year),
                                        _int(req, 'm', today.month)))

# === CalDAV ===

async def dav_root(req):
    """Everything under /muhurtha/dav.

    One handler for the whole tree because CalDAV is a protocol over a path, not a set of
    endpoints -- the method and the depth header decide far more than the URL does.

    The handler has to be async to read the request body, but everything after that is
    arithmetic: a depth-1 PROPFIND generates months of panchangam and takes seconds. Run on
    the event loop that starves every other request in the worker -- /health included, which
    is how one crawler hitting /.well-known/caldav takes the whole site to 502. Starlette
    puts plain `def` handlers on a threadpool for exactly this reason; an `async def` one
    has to ask."""
    tok = req.path_params.get('tok') or ''
    rest = req.path_params.get('rest') or ''
    if not tok:
        return RedirectResponse(well_known(), status_code=302)
    body = (await req.body()).decode('utf-8', 'replace') if req.method in ('REPORT', 'PROPFIND', 'PUT') else ''
    hdrs = {k.lower(): v for k, v in req.headers.items()}
    try:
        st, h, out = await run_in_threadpool(dav_handle, req.method, tok, rest, hdrs, body)
    except Exception as e:
        error(f'caldav {req.method} {req.url.path}: {e}')
        return Response('error', status_code=500)
    return Response(out, status_code=st, headers=h)

async def wk_caldav(req):
    return RedirectResponse(well_known(), status_code=301)

# === wiring ===

_DAV_METHODS = ['GET', 'HEAD', 'OPTIONS', 'PROPFIND', 'REPORT', 'PUT', 'DELETE',
                'MKCALENDAR', 'MKCOL', 'PROPPATCH', 'POST']

def connect(app):
    RouteOverrides.skip += Routes.skip
    # Prepended, not appended: this one sits leftmost whatever order the blocks connect in.
    RouteOverrides.nav = [('Muhurtha', Routes.index, 'new', False)] + RouteOverrides.nav
    app.get(Routes.index)(index)
    app.get(Routes.month)(month_page)
    app.get(Routes.day)(day_page)
    app.get(Routes.subscribe)(subscribe_page)
    app.get(Routes.feed)(feed_ics)
    app.get(Routes.api_day)(api_day)
    app.get(Routes.api_month)(api_month)
    app.get(Routes.wk_caldav)(wk_caldav)
    # Starlette's decorators cover the ordinary verbs; PROPFIND and REPORT are not among
    # them, so the CalDAV routes go on the router directly with the methods spelled out.
    for path in (f'{Routes.dav}', f'{Routes.dav}/', '%s/{tok}' % Routes.dav,
                 '%s/{tok}/' % Routes.dav, '%s/{tok}/{rest:path}' % Routes.dav):
        app.router.routes.insert(0, Route(path, dav_root, methods=_DAV_METHODS))
