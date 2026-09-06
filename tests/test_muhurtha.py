'''Tests for the muhurtha block.

The engine is checked two ways: against Meeus' own worked examples, which pin the series,
and against internal consistency, which catches a boundary solver that has stopped landing
on the angle it was asked for. The feed is checked by parsing it back with an independent
RFC 5545 implementation rather than by matching strings.'''

import re
from datetime import date, datetime, timedelta, timezone

import pytest

from lego.muhurtha import ephem as E
from lego.muhurtha.panchanga import (Place, day_panchanga, month_panchanga, sunrise_day,
                                     tithi_at, nakshatra_at, yoga_at, karana_at, _tithi_angle,
                                     _nak_angle, _yoga_angle)
from lego.muhurtha.feed import build_feed, iter_events, as_object
from lego.muhurtha.dav import encode_token, decode_token, dav_handle, _time_range
from lego.muhurtha.cfg import LAYERS, DEFAULT_LAYERS

CHENNAI = Place(13.0827, 80.2707, 'Asia/Kolkata', 'Chennai')
LONDON  = Place(51.5072, -0.1276, 'Europe/London', 'London')
TROMSO  = Place(69.6496, 18.9560, 'Europe/Oslo', 'Tromso')      # polar day and polar night
SYDNEY  = Place(-33.8688, 151.2093, 'Australia/Sydney', 'Sydney')

# === ephemeris ===

def test_moon_matches_meeus_example_47a():
    'Meeus ch.47 worked example: 1992 April 12.0 TD.'
    jd = 2448724.5
    assert abs(E.moon_long(jd) - 133.167265) < 0.001
    assert abs(E.moon_lat(jd) - (-3.229126)) < 0.001

def test_sun_matches_meeus_example_25b():
    'Meeus ch.25 worked example: 1992 October 13.0 TD, apparent longitude.'
    assert abs(E.sun_long(2448908.5) - 199.90988) < 0.01

def test_julian_day_roundtrip():
    for dt in (datetime(1900, 1, 1, tzinfo=timezone.utc),
               datetime(2026, 9, 6, 17, 43, 21, tzinfo=timezone.utc),
               datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc)):
        back = E.dt_from_jd(E.jd_from_dt(dt))
        assert abs((back - dt).total_seconds()) < 0.01

def test_ayanamsa_is_lahiri_and_increasing():
    a2000, a2026 = E.ayanamsa(E.J2000), E.ayanamsa(E.J2000 + 26*365.25)
    assert abs(a2000 - 23.85) < 0.02
    assert abs(a2026 - 24.21) < 0.05
    assert a2026 > a2000

@pytest.mark.parametrize('place', [CHENNAI, LONDON, SYDNEY])
def test_sunrise_precedes_noon_precedes_sunset(place):
    for m in (1, 4, 7, 10):
        rise, noon, sset, nxt = sunrise_day(place, date(2026, m, 15))
        assert rise < noon < sset < nxt
        assert 0.1 < sset - rise < 0.95       # a day is neither instant nor 24 hours

def test_sun_is_on_the_horizon_at_the_times_returned():
    rise, _noon, sset, _n = sunrise_day(CHENNAI, date(2026, 6, 21))
    assert abs(E.sun_alt(rise, CHENNAI.lat, CHENNAI.lon) + 0.8333) < 0.01
    assert abs(E.sun_alt(sset, CHENNAI.lat, CHENNAI.lon) + 0.8333) < 0.01

def test_polar_day_and_night_do_not_raise():
    'Above the arctic circle the sun does not cross the horizon; the day still has to exist.'
    for d in (date(2026, 6, 21), date(2026, 12, 21)):
        p = day_panchanga(TROMSO, d)
        assert p['tithi']['name'] and p['nakshatra']['name']
        assert datetime.fromisoformat(p['sunrise']) < datetime.fromisoformat(p['next_sunrise'])

# === the five limbs ===

@pytest.mark.parametrize('fn,angle,step', [
    (tithi_at, _tithi_angle, 12), (nakshatra_at, _nak_angle, 360/27),
    (yoga_at, _yoga_angle, 360/27), (karana_at, _tithi_angle, 6)])
def test_boundaries_land_on_their_target_angle(fn, angle, step):
    'A span must start and end exactly where its definition says it does.'
    jd = E.jd_from_dt(datetime(2026, 9, 6, 3, tzinfo=timezone.utc))
    for i in range(12):
        sp = fn(jd + i*7)
        assert abs(angle(sp.start) % step) < 1e-5 or abs(angle(sp.start) % step - step) < 1e-5
        assert abs(angle(sp.end) % step) < 1e-5 or abs(angle(sp.end) % step - step) < 1e-5
        assert sp.start <= jd + i*7 < sp.end

def test_tithi_lengths_are_within_the_traditional_range():
    'A tithi runs roughly 19 to 26 hours -- if one falls outside, the solver has slipped.'
    jd = E.jd_from_dt(datetime(2026, 1, 1, tzinfo=timezone.utc))
    for i in range(40):
        sp = tithi_at(jd + i)
        assert 18 < (sp.end - sp.start)*24 < 27, (i, (sp.end - sp.start)*24)

def test_known_day_matches_a_published_panchangam():
    '1 January 2026 at Chennai, cross-checked against a printed Tamil almanac.'
    p = day_panchanga(CHENNAI, date(2026, 1, 1))
    assert p['tithi']['name'] == 'Shukla Trayodashi'
    assert p['nakshatra']['name'] == 'Rohini'
    assert p['vara'] == 'Guruvara'
    assert p['samvatsara'] == 'Vishvavasu'
    assert p['shaka'] == 1947
    assert p['ayana'] == 'Dakshinayana'
    assert p['ritu'] == 'Hemanta'
    assert p['tamil_masa'] == 'Margazhi'
    assert p['paksha'] == 'Shukla'
    assert p['soolam'] == 'South'
    assert p['sunrise'][11:16] == '06:31'
    # The moon is in Vrishabha, so the eighth house from Tula holds it.
    assert p['chandrashtama']['rasi'] == 'Tula'
    assert 'Swati' in p['chandrashtama']['nakshatras']

def test_amavasya_and_purnima_fall_where_the_moon_puts_them():
    rows = month_panchanga(CHENNAI, 2026, 9)
    names = {r['day']: r['tithi_short'] for r in rows}
    assert names[11] == 'Amavasya'
    assert names[26] == 'Purnima'

def test_thirty_muhurtas_tile_the_day_exactly():
    p = day_panchanga(CHENNAI, date(2026, 9, 6))
    ms = p['muhurtas']
    assert len(ms) == 30
    assert ms[0]['start'] == p['sunrise']
    assert ms[-1]['end'] == p['next_sunrise']
    for a, b in zip(ms, ms[1:]):
        assert a['end'] == b['start']

def test_twenty_four_horas_tile_the_day_and_start_with_the_weekday_lord():
    p = day_panchanga(CHENNAI, date(2026, 9, 6))     # a Sunday
    hs = p['horas']
    assert len(hs) == 24
    assert hs[0]['name'] == 'Sun' == p['vara_lord']
    assert hs[0]['start'] == p['sunrise']
    assert hs[-1]['end'] == p['next_sunrise']
    for a, b in zip(hs, hs[1:]):
        assert a['end'] == b['start']
    for h in hs:
        assert len(h['subs']) == 7
        assert h['subs'][0]['planet'] == h['name']

def test_kalams_sit_inside_daylight():
    p = day_panchanga(CHENNAI, date(2026, 9, 6))
    for k in p['kalams']:
        assert p['sunrise'] <= k['start'] < k['end'] <= p['sunset']

def test_karana_cycle_uses_the_fixed_names_at_the_month_boundary():
    'Kimstughna opens a lunar month and Shakuni, Chatushpada and Naga close it.'
    seen = set()
    jd = E.jd_from_dt(datetime(2026, 9, 8, tzinfo=timezone.utc))
    for i in range(120):
        seen.add(karana_at(jd + i*0.25).name)
    assert {'Kimstughna', 'Shakuni', 'Chatushpada', 'Naga'} <= seen
    assert {'Bava', 'Vishti'} <= seen

def test_southern_hemisphere_day_is_sane():
    p = day_panchanga(SYDNEY, date(2026, 12, 21))
    assert datetime.fromisoformat(p['sunrise']) < datetime.fromisoformat(p['sunset'])
    assert p['day_length'] > 13          # midsummer south of the equator

# === iCalendar ===

def _cal(text):
    from icalendar import Calendar
    return Calendar.from_ical(text)

def test_feed_parses_with_an_independent_ics_implementation():
    for layers in ([l] for l in LAYERS):
        ics = build_feed(CHENNAI, layers, back=1, days=3, today=date(2026, 1, 1))
        cal = _cal(ics)
        evs = list(cal.walk('VEVENT'))
        assert evs and not cal.errors
        for e in evs:
            assert e.get('UID') and e.get('DTSTAMP') and e.get('DTSTART') and e.get('SUMMARY')
            assert not e.errors

def test_feed_lines_obey_the_75_octet_fold():
    ics = build_feed(CHENNAI, list(LAYERS), back=1, days=2, today=date(2026, 1, 1))
    for line in ics.split('\r\n'):
        assert len(line.encode()) <= 75, line[:60]

def test_feed_uids_are_stable_across_rebuilds():
    'A subscriber must see the same event updated, not a duplicate added.'
    a = build_feed(CHENNAI, ['day'], back=0, days=3, today=date(2026, 1, 1))
    b = build_feed(CHENNAI, ['day'], back=0, days=3, today=date(2026, 1, 1))
    uids = lambda t: re.findall(r'^UID:(.+)$', t, re.M)
    assert uids(a) == uids(b) and len(set(uids(a))) == 3

def test_uids_differ_by_place():
    'The same day at two places is two different events, not one contested one.'
    u = lambda p: set(re.findall(r'^UID:(.+)$',
                                build_feed(p, ['day'], back=0, days=2, today=date(2026, 1, 1)), re.M))
    assert not (u(CHENNAI) & u(LONDON))

def test_day_event_is_all_day_and_free():
    ics = build_feed(CHENNAI, ['day'], back=0, days=1, today=date(2026, 1, 1))
    assert 'DTSTART;VALUE=DATE:20260101' in ics
    assert 'DTEND;VALUE=DATE:20260102' in ics
    assert 'TRANSP:TRANSPARENT' in ics

def test_timed_events_are_utc_so_no_vtimezone_is_needed():
    ics = build_feed(CHENNAI, ['kalam'], back=0, days=1, today=date(2026, 1, 1))
    assert 'BEGIN:VTIMEZONE' not in ics
    for m in re.findall(r'^DTSTART:(.+)$', ics, re.M):
        assert m.rstrip('\r').endswith('Z')

def test_description_carries_the_whole_almanac():
    ics = build_feed(CHENNAI, ['day'], back=0, days=1, today=date(2026, 1, 1))
    desc = str(list(_cal(ics).walk('VEVENT'))[0].get('DESCRIPTION'))
    for want in ('Tithi:', 'Nakshatra:', 'Yoga:', 'Karana:', 'Sunrise', 'Rahu Kalam',
                 'Vishvavasu', 'Ayanamsa'):
        assert want in desc

def test_dense_layers_are_capped_to_a_shorter_window():
    'A year of horas is nine thousand events; the cap is what keeps the feed fetchable.'
    ics = build_feed(CHENNAI, ['hora'], back=0, days=365, today=date(2026, 1, 1))
    assert ics.count('BEGIN:VEVENT') <= 46*24

def test_unknown_layer_falls_back_to_the_default():
    ics = build_feed(CHENNAI, ['nonsense'], back=0, days=1, today=date(2026, 1, 1))
    assert ics.count('BEGIN:VEVENT') > 0

# === CalDAV ===

def test_token_roundtrips():
    tok = encode_token(CHENNAI, ['day', 'hora'])
    p, layers = decode_token(tok)
    assert (round(p.lat, 4), round(p.lon, 4), p.tzname) == (13.0827, 80.2707, 'Asia/Kolkata')
    assert layers == ['day', 'hora']

def test_malformed_token_falls_back_rather_than_raising():
    p, layers = decode_token('!!!not-base64!!!')
    assert p.tzname and layers

def test_time_range_parses_both_attributes():
    s, e = _time_range('<c:time-range start="20260101T000000Z" end="20260105T000000Z"/>')
    assert s.year == 2026 and e.day == 5
    assert _time_range('<c:time-range start="20260101T000000Z"/>')[1] is None
    assert _time_range('<c:comp-filter name="VEVENT"/>') == (None, None)

def test_options_advertises_calendar_access():
    st, h, _b = dav_handle('OPTIONS', encode_token(CHENNAI, DEFAULT_LAYERS), '', {}, '')
    assert st == 200 and 'calendar-access' in h['DAV']

def test_propfind_exposes_a_principal_and_a_calendar_home():
    tok = encode_token(CHENNAI, DEFAULT_LAYERS)
    st, _h, body = dav_handle('PROPFIND', tok, '', {'depth': '0'}, '')
    assert st == 207
    assert 'current-user-principal' in body and 'calendar-home-set' in body

def test_calendar_collection_declares_itself_a_calendar():
    tok = encode_token(CHENNAI, DEFAULT_LAYERS)
    st, _h, body = dav_handle('PROPFIND', tok, 'c/', {'depth': '0'}, '')
    assert st == 207 and '<c:calendar/>' in body and 'getctag' in body

def test_writes_are_refused():
    tok = encode_token(CHENNAI, DEFAULT_LAYERS)
    for m in ('PUT', 'DELETE', 'MKCALENDAR', 'PROPPATCH'):
        st, _h, _b = dav_handle(m, tok, 'c/x.ics', {}, '')
        assert st == 403

def test_each_dav_object_is_a_standalone_calendar():
    evs = list(iter_events(CHENNAI, ['day'], date(2026, 1, 1), 0, 2))
    for uid, lines in evs:
        cal = _cal(as_object(uid, lines))
        assert len(list(cal.walk('VEVENT'))) == 1 and not cal.errors

# === HTTP ===

@pytest.fixture(scope='module')
def client():
    from starlette.testclient import TestClient
    import lego.app as A
    return TestClient(A.lego)

@pytest.fixture
def fresh():
    'A client with no cookies. `client` is module-scoped and now remembers a chosen place.'
    from starlette.testclient import TestClient
    import lego.app as A
    return TestClient(A.lego)

Q = 'lat=13.0827&lon=80.2707&tz=Asia/Kolkata&place=Chennai'

@pytest.mark.parametrize('path', [
    f'/muhurtha/month?{Q}', f'/muhurtha/day?date=2026-01-01&{Q}', f'/muhurtha/subscribe?{Q}',
    f'/muhurtha/api/day?date=2026-01-01&{Q}', f'/muhurtha/api/month?y=2026&m=1&{Q}'])
def test_pages_answer_without_auth(client, path):
    r = client.get(path)
    assert r.status_code == 200 and len(r.content) > 1000

def test_feed_route_serves_calendar_content_type(client):
    r = client.get(f'/muhurtha/feed.ics?{Q}&back=1&days=3')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/calendar')
    assert 'filename=' in r.headers['content-disposition']
    assert not _cal(r.text).errors

def test_well_known_caldav_redirects_into_the_collection(client):
    r = client.get('/.well-known/caldav', follow_redirects=False)
    assert r.status_code == 301 and '/muhurtha/dav/' in r.headers['location']

def test_bad_query_params_do_not_crash_a_page(client):
    for q in ('lat=abc&lon=xyz', 'tz=Mars/Olympus', 'date=not-a-date', 'y=0&m=99',
              'lat=999&lon=999', 'layers=;drop'):
        assert client.get(f'/muhurtha/month?{q}').status_code == 200
        assert client.get(f'/muhurtha/day?{q}').status_code == 200

def test_caldav_sync_over_http(client):
    tok = encode_token(CHENNAI, ['day'])
    base = f'/muhurtha/dav/{tok}'
    pf = '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getetag/></d:prop></d:propfind>'
    r = client.request('PROPFIND', base + '/c/', headers={'Depth': '1'}, content=pf)
    assert r.status_code == 207
    hrefs = re.findall(r'<d:href>([^<]+\.ics)</d:href>', r.text)
    assert hrefs
    r = client.get(hrefs[0])
    assert r.status_code == 200 and not _cal(r.text).errors


def test_caldav_work_does_not_run_on_the_event_loop():
    '''A depth-1 PROPFIND is seconds of arithmetic, so it must not sit on the event loop.

    It did once, and one crawler on /.well-known/caldav was enough to starve /health in the
    same worker and take every route on the box to 502 -- including the ones this block
    never touched.'''
    import inspect
    from lego.muhurtha.app import dav_root
    src = inspect.getsource(dav_root)
    assert 'run_in_threadpool' in src, 'dav_handle must be offloaded, not awaited inline'

def test_collection_get_redirects_instead_of_building_a_feed_inline(client):
    'A browser on the collection is sent to the cached feed route, not served a fresh build.'
    tok = encode_token(CHENNAI, ['day'])
    r = client.get(f'/muhurtha/dav/{tok}/c/', follow_redirects=False)
    assert r.status_code == 302 and '/muhurtha/feed.ics' in r.headers['location']


# === it must live inside the app, not beside it ===

def test_pages_render_inside_the_app_shell(client):
    'One document, one navbar. The block used to ship its own and read as a separate site.'
    r = client.get(f'/muhurtha/month?{Q}')
    assert r.text.count('<html') == 1
    assert 'navbar' in r.text and 'nav-pill' in r.text

def test_block_does_not_ship_a_second_theme_picker(client):
    'The navbar owns appearance. A second picker inside the page is what looked wrong.'
    r = client.get(f'/muhurtha/month?{Q}')
    assert 'appearance-menu' not in r.text

def test_muhurtha_is_leftmost_in_the_nav_and_flagged_new():
    from lego.core import RouteOverrides
    import lego.app  # noqa: F401  -- connecting the blocks is what populates the nav
    labels = [x[0] for x in RouteOverrides.nav]
    assert labels[0] == 'Muhurtha'
    assert RouteOverrides.nav[0][2] == 'new'
    assert labels[-1] == 'Dashboards'

def test_stylesheet_is_scoped_to_the_block():
    '''No bare element selectors: this stylesheet now loads on every page in the app.

    An unscoped `body` or `a` rule here would restyle the blog and the dashboards too.'''
    import re
    from pathlib import Path
    css = Path('lego/muhurtha/muhurtha.css').read_text()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    bare = []
    depth = 0
    for line in css.split('\n'):
        st = line.strip()
        if depth == 0 and '{' in st and not st.startswith(('@', ':root')):
            sel = st.split('{')[0]
            bare += [x.strip() for x in sel.split(',')
                     if x.strip() and not x.strip().startswith('.mh')]
        depth += line.count('{') - line.count('}')
    assert not bare, f'unscoped selectors would leak onto other pages: {bare}'


def test_only_muhurtha_is_flagged_new():
    from lego.core import RouteOverrides
    import lego.app  # noqa: F401
    tagged = [x[0] for x in RouteOverrides.nav if x[2] == 'new']
    assert tagged == ['Muhurtha']

@pytest.mark.parametrize('q,want', [
    ('lat=13.0827&lon=80.2707&tz=Asia/Kolkata&place=Chennai', 'Chennai'),
    ('lat=-33.8688&lon=151.2093&tz=Australia/Sydney', '33.87°S 151.21°E'),
])
def test_the_page_names_the_place_it_was_computed_for(client, q, want):
    'Every number on the page depends on the place, so the place has to be on the page.'
    r = client.get(f'/muhurtha/month?{q}')
    assert want in r.text

def test_unnamed_place_falls_back_to_coordinates():
    from lego.muhurtha.ui import coords
    assert coords(Place(13.0827, 80.2707, 'Asia/Kolkata')) == '13.08°N 80.27°E'
    assert coords(Place(-33.8688, -70.6693, 'UTC')) == '33.87°S 70.67°W'


# === the place has to survive a reload ===

def test_default_place_keeps_its_name_on_a_bare_url(fresh):
    '''The configured place is Chennai, not 13.08°N 80.27°E.

    Normalising the longitude through `((x + 180) % 360) - 180` returned 80.27070000000003,
    so the equality test against the configured default failed and the name was dropped.'''
    assert 'Chennai' in fresh.get('/muhurtha/month').text

def test_longitude_wrap_is_exact_inside_the_normal_range():
    from lego.muhurtha.app import _wrap_lon
    for x in (0.0, 80.2707, -0.1276, 151.2093, 180.0, -180.0):
        assert _wrap_lon(x) == x
    assert _wrap_lon(200.0) == -160.0
    assert _wrap_lon(-200.0) == 160.0

def test_a_chosen_place_survives_a_reload_and_the_navbar_pill(fresh):
    'It used to live only in the URL, so anything without a query string lost it.'
    c = fresh
    r = c.get('/muhurtha/month?lat=-37.8136&lon=144.9631&tz=Australia/Melbourne&place=Melbourne')
    assert 'mh_place' in r.headers.get('set-cookie', '')
    for path in ('/muhurtha/month', '/muhurtha/day', '/muhurtha/subscribe'):
        assert 'Melbourne' in c.get(path).text, path
    assert 'Melbourne' in c.get('/muhurtha', follow_redirects=True).text

def test_a_reader_who_never_chose_gets_the_default(fresh):
    assert 'Chennai' in fresh.get('/muhurtha/month').text

def test_a_bad_cookie_falls_back_instead_of_erroring(fresh):
    c = fresh
    for bad in ('garbage', 'a|b|c|d', '1|2|Mars/Olympus|x', ''):
        c.cookies.set('mh_place', bad)
        assert c.get('/muhurtha/month').status_code == 200

def test_links_meant_for_other_people_carry_the_place(client):
    'A cookie is for this browser. A copied link has to stand on its own.'
    q = 'lat=-37.8136&lon=144.9631&tz=Australia/Melbourne&place=Melbourne'
    t = client.get(f'/muhurtha/subscribe?{q}').text
    assert 'lat=-37.8136' in t and 'place=Melbourne' in t
    assert t.count('feed.ics?lat=-37.8136') >= 1
