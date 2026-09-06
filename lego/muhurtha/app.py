'''Routes.

Two audiences share one computation: a browser that wants a calendar to look at, and a
calendar client that wants a file to subscribe to. The engine does not know the difference,
so neither do these handlers -- they differ only in what they serialise.'''

import json
from datetime import date as Date, datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones
from fasthtml.common import HTMLResponse, JSONResponse, RedirectResponse
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

def place_of(req):
    'The place a request is about: query string, else the block default.'
    qp = req.query_params
    lat = max(-89.9, min(89.9, _f(qp, 'lat', cfg.lat)))
    lon = ((_f(qp, 'lon', cfg.lon) + 180) % 360) - 180
    tz = qp.get('tz') or cfg.tz
    if tz not in _TZS: tz = cfg.tz
    nm = (qp.get('place') or '').strip()[:60]
    if not nm and (lat, lon) == (cfg.lat, cfg.lon): nm = cfg.place_name
    return Place(lat, lon, tz, nm)

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
def _month_html(key, tz, nm, y, m, today):
    place = _mk(key, tz, nm)
    d = Date.fromisoformat(today)
    return ui.document(f'{y}-{m:02d} · Muhurtha · {nm or key}', place,
                       ui.month_view(place, y, m, d), active='month',
                       boot=_boot(day_panchanga(place, d)))

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

def month_page(req):
    place = place_of(req)
    today = datetime.now(place.tz).date()
    y, m = _int(req, 'y', today.year), _int(req, 'm', today.month)
    if not (1 <= m <= 12) or not (1900 <= y <= 2200): y, m = today.year, today.month
    key = f'{place.lat:.4f},{place.lon:.4f}'
    return HTMLResponse(_month_html(key, place.tzname, place.name, y, m, today.isoformat()))

def day_page(req):
    place = place_of(req)
    d = date_of(req, place)
    p = day_panchanga(place, d, planets=False, spans=False)
    body = ui.day_view(place, d, datetime.now(place.tz).date())
    return HTMLResponse(ui.document(
        f"{d.isoformat()} · {p['tithi']['name']} · {p['nakshatra']['name']}",
        place, body, active='day', boot=_boot(day_panchanga(place, d))))

def subscribe_page(req):
    place = place_of(req)
    boot = json.dumps(dict(davBase=f'{base_url(req)}{Routes.dav}/',
                           place=[round(place.lat, 4), round(place.lon, 4),
                                  place.tzname, place.name]))
    return HTMLResponse(ui.document('Subscribe · Muhurtha', place,
                                    ui.subscribe_view(place, base_url(req)),
                                    active='subscribe', boot=boot))

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
    '''Everything under /muhurtha/dav.

    One handler for the whole tree because CalDAV is a protocol over a path, not a set of
    endpoints -- the method and the depth header decide far more than the URL does.'''
    tok = req.path_params.get('tok') or ''
    rest = req.path_params.get('rest') or ''
    if not tok:
        return RedirectResponse(well_known(), status_code=302)
    body = (await req.body()).decode('utf-8', 'replace') if req.method in ('REPORT', 'PROPFIND', 'PUT') else ''
    hdrs = {k.lower(): v for k, v in req.headers.items()}
    try:
        st, h, out = dav_handle(req.method, tok, rest, hdrs, body)
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
    RouteOverrides.nav = RouteOverrides.nav + [('Muhurtha', Routes.index, None, False)]
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
