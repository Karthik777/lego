'''A read-only CalDAV collection (RFC 4791), so Apple Calendar can mount this as an account.

Subscribing to the .ics feed is the better path and the only one Google Calendar offers for
an external calendar, but Apple speaks CalDAV natively and a CalDAV calendar refreshes on
the client's own schedule rather than whenever Google next feels like fetching. So both.

Read-only means the write half of the protocol is simply absent: no PUT, no DELETE, no
MKCALENDAR, and every collection reports an empty current-user-privilege-set beyond read.
A client that tries to write gets 403, which is a thing clients handle.

The whole tree hangs off an opaque token that carries the place and the layer choice, so a
URL is a complete description of the calendar it returns and nothing needs storing.'''

import base64, json
from functools import lru_cache
from datetime import datetime, timedelta, timezone, date as Date
from hashlib import md5
from xml.sax.saxutils import escape as xesc
from .cfg import cfg, Routes, LAYERS, DEFAULT_LAYERS
from .panchanga import Place
from .feed import iter_events, as_object, feed_name, window_for

__all__ = ['encode_token', 'decode_token', 'dav_handle', 'well_known']

NS = ('xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" '
      'xmlns:cs="http://calendarserver.org/ns/" xmlns:ic="http://apple.com/ns/ical/"')

# === token: the whole calendar definition, in a path segment ===

def encode_token(place, layers):
    raw = json.dumps([round(place.lat, 4), round(place.lon, 4), place.tzname,
                      place.name, sorted(layers)], separators=(',', ':'))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip('=')

def decode_token(tok):
    'Place and layers from a token; falls back to the default place on anything malformed.'
    try:
        pad = '=' * (-len(tok) % 4)
        lat, lon, tz, nm, layers = json.loads(base64.urlsafe_b64decode(tok + pad))
        return Place(lat, lon, tz, nm), [l for l in layers if l in LAYERS] or list(DEFAULT_LAYERS)
    except Exception:
        return Place(cfg.lat, cfg.lon, cfg.tz, cfg.place_name), list(DEFAULT_LAYERS)

# === hrefs ===

def _base(tok): return f'{Routes.dav}/{tok}'
def home(tok):  return f'{_base(tok)}/'
def calhref(tok): return f'{_base(tok)}/c/'
def objhref(tok, uid): return f'{calhref(tok)}{uid}.ics'

def _ctag(place, layers):
    'Changes when the content would change. The window rolls daily, so the date is enough.'
    return md5(f"{place.key()}|{','.join(sorted(layers))}|{datetime.now(timezone.utc):%Y%m%d}".encode()).hexdigest()

# === XML ===

def _ms(responses):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<d:multistatus {NS}>' + ''.join(responses) + '</d:multistatus>')

def _resp(href, found, missing=()):
    'One response element: the props that exist at 200, the ones that do not at 404.'
    out = [f'<d:response><d:href>{xesc(href)}</d:href>',
           '<d:propstat><d:prop>', ''.join(found), '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>']
    if missing:
        out += ['<d:propstat><d:prop>', ''.join(f'<{m}/>' for m in missing),
                '</d:prop><d:status>HTTP/1.1 404 Not Found</d:status></d:propstat>']
    out.append('</d:response>')
    return ''.join(out)

_READ_PRIV = ('<d:current-user-privilege-set>'
              '<d:privilege><d:read/></d:privilege>'
              '<d:privilege><d:read-current-user-privilege-set/></d:privilege>'
              '</d:current-user-privilege-set>')

def _root_props(tok):
    return [f'<d:current-user-principal><d:href>{home(tok)}</d:href></d:current-user-principal>',
            f'<d:principal-URL><d:href>{home(tok)}</d:href></d:principal-URL>',
            '<d:resourcetype><d:collection/></d:resourcetype>',
            '<d:displayname>Muhurtha</d:displayname>', _READ_PRIV]

def _principal_props(tok, place):
    return [f'<d:current-user-principal><d:href>{home(tok)}</d:href></d:current-user-principal>',
            f'<d:principal-URL><d:href>{home(tok)}</d:href></d:principal-URL>',
            '<d:resourcetype><d:collection/><d:principal/></d:resourcetype>',
            f'<d:displayname>{xesc(place.name or "Muhurtha")}</d:displayname>',
            f'<c:calendar-home-set><d:href>{home(tok)}</d:href></c:calendar-home-set>',
            f'<c:calendar-user-address-set><d:href>{home(tok)}</d:href></c:calendar-user-address-set>',
            _READ_PRIV]

def _calendar_props(tok, place, layers):
    return ['<d:resourcetype><d:collection/><c:calendar/></d:resourcetype>',
            f'<d:displayname>{xesc(feed_name(place, layers))}</d:displayname>',
            f'<cs:getctag>{_ctag(place, layers)}</cs:getctag>',
            f'<d:sync-token>{_ctag(place, layers)}</d:sync-token>',
            '<c:supported-calendar-component-set><c:comp name="VEVENT"/></c:supported-calendar-component-set>',
            '<c:supported-calendar-data><c:calendar-data content-type="text/calendar" version="2.0"/></c:supported-calendar-data>',
            f'<c:calendar-description>{xesc(cfg.tagline)}</c:calendar-description>',
            f'<c:calendar-timezone-id>{xesc(place.tzname)}</c:calendar-timezone-id>',
            '<ic:calendar-color>#8C2F1EFF</ic:calendar-color>',
            '<d:getcontenttype>text/calendar</d:getcontenttype>',
            '<d:current-user-privilege-set><d:privilege><d:read/></d:privilege></d:current-user-privilege-set>',
            '<d:owner><d:href>' + home(tok) + '</d:href></d:owner>']

# === objects ===

def _range(place, layers, start=None, end=None):
    """The days to generate: the feed's own window, narrowed to any time-range asked for.

    A client may ask for a range this calendar does not cover, and the honest answer is an
    empty collection rather than the nearest thing -- hence None when the two do not meet."""
    back, days = window_for(layers, None, None)
    t0 = datetime.now(place.tz).date()
    lo, hi = t0 - timedelta(days=back), t0 + timedelta(days=days)
    if start: lo = max(lo, start.date() - timedelta(days=1))
    if end:   hi = min(hi, end.date() + timedelta(days=1))
    return (lo, hi) if lo <= hi else None

@lru_cache(maxsize=4)
def _objects(key, tz, nm, layers, lo, hi):
    place = Place(*(float(x) for x in key.split(',')), tz, nm)
    label = feed_name(place, list(layers))
    return tuple((uid, as_object(uid, lines, label)) for uid, lines in
                 iter_events(place, list(layers), Date.fromisoformat(lo), 0,
                             (Date.fromisoformat(hi) - Date.fromisoformat(lo)).days + 1))

def objects(place, layers, start=None, end=None):
    """Every calendar object resource in range, as (uid, ics_text).

    Memoised on the window rather than the request: a sync is a PROPFIND followed by a
    multiget of everything it just listed, and generating two hundred days of panchangam
    twice in a row for one client is the difference between a fast account and a slow one.
    The key carries the date bounds, so the roll to a new day evicts it by itself."""
    r = _range(place, layers, start, end)
    if r is None: return []
    lo, hi = r
    return list(_objects(f'{place.lat:.4f},{place.lon:.4f}', place.tzname, place.name,
                         tuple(sorted(layers)), lo.isoformat(), hi.isoformat()))

def _obj_resp(tok, uid, text, want_data=True):
    props = [f'<d:getetag>"{md5(text.encode()).hexdigest()}"</d:getetag>',
             '<d:getcontenttype>text/calendar; component=vevent; charset=utf-8</d:getcontenttype>',
             '<d:resourcetype/>']
    if want_data: props.append(f'<c:calendar-data>{xesc(text)}</c:calendar-data>')
    return _resp(objhref(tok, uid), props)

# === request handling ===

def _depth(headers): return headers.get('depth', '0')

def _hrefs_in(body):
    import re
    return re.findall(r'<[a-zA-Z0-9]*:?href[^>]*>([^<]+)</[a-zA-Z0-9]*:?href>', body or '')

def _time_range(body):
    'start/end of a calendar-query time-range filter, either of which may be absent.'
    import re
    m = re.search(r'<[^>]*time-range\b([^>]*)>|<[^>]*time-range\b([^>]*?)/>', body or '')
    if not m: return None, None
    attrs = m.group(1) or m.group(2) or ''
    def get(k):
        a = re.search(k + r'="([0-9]{8}T[0-9]{6}Z)"', attrs)
        if not a: return None
        try: return datetime.strptime(a.group(1), '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        except ValueError: return None
    return get('start'), get('end')

def dav_handle(method, tok, rest, headers, body):
    '''Answer one CalDAV request. Returns (status, headers, body).

    `rest` is the path under the token: '' for the principal/home, 'c/' for the calendar
    collection, 'c/<uid>.ics' for one object.'''
    place, layers = decode_token(tok)
    common = {'DAV': '1, 2, 3, calendar-access', 'Content-Type': 'application/xml; charset=utf-8'}

    if method == 'OPTIONS':
        return 200, {'DAV': '1, 2, 3, calendar-access',
                     'Allow': 'OPTIONS, GET, HEAD, PROPFIND, REPORT'}, ''

    if method in ('GET', 'HEAD'):
        if rest.startswith('c/') and rest.endswith('.ics'):
            uid = rest[2:-4]
            for u, text in objects(place, layers):
                if u == uid:
                    return 200, {'Content-Type': 'text/calendar; charset=utf-8',
                                 'ETag': f'"{md5(text.encode()).hexdigest()}"'}, text
            return 404, {}, 'Not found'
        # A browser landing on the collection gets pointed at the feed route rather than a
        # protocol error -- and by redirecting rather than building inline, the work happens
        # behind the feed's cache instead of once per curious visitor.
        from urllib.parse import urlencode
        q = urlencode(dict(lat=round(place.lat, 4), lon=round(place.lon, 4), tz=place.tzname,
                           place=place.name or '', layers=','.join(sorted(layers))))
        return 302, {'Location': f'{Routes.feed}?{q}'}, ''

    if method == 'PROPFIND':
        depth = _depth(headers)
        if rest in ('', '/'):
            rs = [_resp(home(tok), _principal_props(tok, place))]
            if depth != '0': rs.append(_resp(calhref(tok), _calendar_props(tok, place, layers)))
            return 207, common, _ms(rs)
        if rest in ('c', 'c/'):
            rs = [_resp(calhref(tok), _calendar_props(tok, place, layers))]
            if depth == '1':
                rs += [_obj_resp(tok, u, t, want_data=False) for u, t in objects(place, layers)]
            return 207, common, _ms(rs)
        if rest.startswith('c/') and rest.endswith('.ics'):
            uid = rest[2:-4]
            for u, t in objects(place, layers):
                if u == uid: return 207, common, _ms([_obj_resp(tok, u, t, want_data=False)])
            return 404, {}, 'Not found'
        return 404, {}, 'Not found'

    if method == 'REPORT':
        if 'calendar-multiget' in (body or ''):
            want = {h.rsplit('/', 1)[-1][:-4] for h in _hrefs_in(body) if h.endswith('.ics')}
            rs = [_obj_resp(tok, u, t) for u, t in objects(place, layers) if u in want]
            return 207, common, _ms(rs)
        if 'sync-collection' in (body or ''):
            rs = [_obj_resp(tok, u, t) for u, t in objects(place, layers)]
            return 207, common, _ms(rs + [f'<d:sync-token>{_ctag(place, layers)}</d:sync-token>'])
        start, end = _time_range(body)
        rs = [_obj_resp(tok, u, t) for u, t in objects(place, layers, start, end)]
        return 207, common, _ms(rs)

    if method in ('PUT', 'DELETE', 'MKCALENDAR', 'MKCOL', 'PROPPATCH', 'POST'):
        return 403, {'DAV': '1, 2, 3, calendar-access'}, 'This calendar is read-only.'
    return 405, {'Allow': 'OPTIONS, GET, HEAD, PROPFIND, REPORT'}, 'Method not allowed'

def well_known(tok=None):
    'Where /.well-known/caldav points: the default calendar, or a token if one was given.'
    return home(tok) if tok else home(encode_token(
        Place(cfg.lat, cfg.lon, cfg.tz, cfg.place_name), DEFAULT_LAYERS))
