'''The calendar itself: a month that reads like a printed almanac, and a day that tells you
everything the almanac would.

Rendered on the server, because the panchanga is computed on the server -- the browser gets
finished markup and one small script whose only job is to know what time it is.

The block used to ship a whole document of its own, which made it read as a different site
that happened to share a domain. It now renders into the app shell like every other block:
one navbar, one theme, one set of chrome. Its styles are scoped under `.mh` so an almanac
layout stays an almanac layout without leaking a body rule onto the rest of the app.'''

from datetime import date as Date, datetime, timedelta
from calendar import monthrange, month_name
from hashlib import md5
from fasthtml.common import (Meta, Title, Link, Script, Style, Div, Span, P, A,
                             H1, H2, H3, Button, Input, Label, Table, Thead, Tbody, Tr, Th, Td,
                             Ol, Li, Ul, Small, B, I, NotStr, Dialog, Form, Header, Footer,
                             Section, Nav)
from fastcore.all import Path
from lego.core import asset_css, asset_js, vlink, base, lc_icon
from .cfg import cfg, Routes, LAYERS, DEFAULT_LAYERS
from .panchanga import Place, day_panchanga, month_panchanga
from .names import PLANET_GLYPH, RASI_GLYPH, RASI

__all__ = ['page', 'mh_head', 'month_view', 'day_view', 'subscribe_view', 'now_band', 'UI_VERSION']

here = Path(__file__).parent
UI_VERSION = md5(b''.join((here / name).read_bytes() for name in ('ui.py', 'muhurtha.css', 'muhurtha.js'))).hexdigest()[:8]

# Diacritics belong on the page, not in the data: a calendar app may render an .ics in any
# font it likes, but this document picks its own.
DIA = {'Muhurtha': 'Muhūrta', 'Tithi': 'Tithi', 'Nakshatra': 'Nakṣatra', 'Yoga': 'Yoga',
       'Karana': 'Karaṇa', 'Vara': 'Vāra', 'Hora': 'Horā', 'Muhurta': 'Muhūrta',
       'Panchangam': 'Pañcāṅga', 'Paksha': 'Pakṣa'}
def dia(w): return DIA.get(w, w)

MOON_GLYPH = {'New': '●', 'Waxing crescent': '☽', 'First quarter': '◑', 'Waxing gibbous': '◕',
              'Full': '○', 'Waning gibbous': '◔', 'Last quarter': '◐', 'Waning crescent': '☾'}

def _hm(iso): return datetime.fromisoformat(iso).strftime('%H:%M')
def _hm_d(iso, ref):
    t = datetime.fromisoformat(iso)
    return t.strftime('%H:%M') if t.date() == ref else t.strftime('%H:%M') + '⁺'

def lbl(t): return Div(t, cls='lbl')

# === document shell ===

def mh_head(boot=None):
    """The block's own stylesheet and script, hoisted into the app-wide head.

    fasthtml lifts Link, Script and Title out of a returned tuple, which is how a block adds
    to the head without the app having to know it exists -- the same trick dash uses for its
    chart bundle."""
    return [Link(rel='stylesheet', href=vlink('/static/vendor/inter.css')),
            asset_css(here / 'muhurtha.css'),
            Script(NotStr(f'window.MH={boot or "{}"};')),
            asset_js(here / 'muhurtha.js')]

def zone_label(place):
    'Short zone and offset for the place, as its own clock reads them right now.'
    t = datetime.now(place.tz)
    off = t.strftime('%z')
    return f"{t.strftime('%Z')} {off[:3]}:{off[3:]}" if off else t.strftime('%Z')

def coords(place):
    'Readable coordinates, for when a place has no name to show.'
    lat, lon = place.lat, place.lon
    return f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'} {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"

def place_chip(place):
    """Which city this almanac is for -- the one fact every number on the page depends on.

    It is the control as well as the label. A separate Place button said the same thing
    twice and left the city looking like a caption, when it is the subject. A place with no
    name falls back to its coordinates, which are at least true."""
    return Button(lc_icon('map-pin', 14, cls='pin'),
                  Span(place.name or coords(place), cls='city'),
                  Span(zone_label(place), cls='zone'),
                  cls='chip', onclick='mh.openPlace()',
                  title='Change place — sunrise, and every boundary with it, is local')

def controls(place, active='month'):
    """The page's own controls -- which place, which month, which day.

    No title and no theme picker: the navbar already carries both, and a second set of site
    chrome inside the page is what made this look like a separate window."""
    q = f'?{place_q(place)}'
    return Header(
        place_chip(place),
        Nav(A(Button('Month', cls=f"btn{' on' if active=='month' else ''}"), href=f'{Routes.month}{q}'),
            A(Button('Today', cls=f"btn{' on' if active=='day' else ''}"), href=f'{Routes.day}{q}'),
            A(Button('Subscribe', cls=f"btn accent{' on' if active=='subscribe' else ''}"),
              href=f'{Routes.subscribe}{q}')),
        cls='mast')

def page(title, place, body, auth=None, active='month', boot=None):
    'The block rendered into the app shell, navbar and theme and all.'
    inner = Div(controls(place, active), body, footer(), place_dialog(), cls='mh')
    return (*base(inner, auth, title=title), *mh_head(boot))

def footer():
    return Footer(
        P(f'All positions are sidereal. The ayanamsa is {cfg.ayanamsa}.'),
        P('The sun and moon positions come from VSOP87 and ELP2000-82. They agree with '
          'JPL DE421 to a few arcseconds.'),
        P('This is a dṛk panchangam. It uses observed positions. A vākya almanac uses older '
          'tables. The two can differ by more than one hour. Both methods are correct.'),
        P(A('Subscribe', href=f'{Routes.subscribe}'), ' · ',
          A('JSON', href=Routes.api_day), ' · ',
          A('iCalendar', href=Routes.feed)),
        cls='foot')

def place_q(place):
    from urllib.parse import urlencode
    return urlencode(dict(lat=round(place.lat, 4), lon=round(place.lon, 4),
                          tz=place.tzname, place=place.name or ''))

def place_dialog():
    return Dialog(
        Div(Div('Choose a place', cls='serif', style='font-size:18px'),
            Div('The panchangam is local. Sunrise starts the day. All times change with the place.',
                cls='note', style='margin-top:5px'),
            cls='hd'),
        Div(Input(type='text', id='mh-q', placeholder='Search a city…', autocomplete='off'),
            Ul(id='mh-hits', cls='hits'),
            Div(Button('Use my location', cls='btn', id='mh-gps', onclick='mh.gps()'),
                Button('Close', cls='btn ghost', onclick='mh.closePlace()'),
                style='display:flex;gap:8px;margin-top:14px'),
            cls='bd'),
        id='mh-place', cls='place')

# === the now band ===

def now_band(p):
    '''Hora, muhurta and the two limbs that are running, as of this second.

    The old hora page was a page about horas. A hora is one limb of a much larger clock, so
    here it sits inside the panchangam instead of standing in for it -- same computation,
    same sub-horas, but next to the tithi and the muhurta it shares the day with.'''
    return Div(
        Div(lbl(dia('Hora')),
            Div(Span('', cls='glyph', id='n-hora-g'), Span('—', id='n-hora'), cls='big serif'),
            Div('—', cls='meta', id='n-hora-t'),
            Div(I(style='width:0', id='n-hora-bar'), cls='bar'),
            Div('—', cls='meta', id='n-hora-sub')),
        Div(lbl(dia('Muhurta')),
            Div('—', cls='mid serif', id='n-mu'),
            Div('—', cls='meta', id='n-mu-t'),
            Div(I(style='width:0', id='n-mu-bar'), cls='bar')),
        Div(lbl(dia('Tithi')),
            Div(p['tithi']['name'], cls='mid serif'),
            Div(f"until {_hm_d(p['tithi']['end'], Date.fromisoformat(p['date']))}", cls='meta'),
            Div('—', cls='meta', id='n-ti-left')),
        Div(lbl(dia('Nakshatra')),
            Div(p['nakshatra']['name'], cls='mid serif'),
            Div(f"pada {p['nakshatra']['pada']} · {p['nakshatra']['lord']}", cls='meta'),
            Div(f"until {_hm_d(p['nakshatra']['end'], Date.fromisoformat(p['date']))}", cls='meta')),
        cls='now')

# === month ===

def month_view(place, year, month, today=None):
    rows = month_panchanga(place, year, month)
    today = today or datetime.now(place.tz).date()
    first = Date(year, month, 1)
    lead = (first.weekday() + 1) % 7                     # Sunday-first grid
    prev = (first - timedelta(days=1)).replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    q = place_q(place)
    ref = day_panchanga(place, rows[len(rows)//2]['date'] and Date.fromisoformat(rows[0]['date']),
                        planets=False, spans=False)
    cells = [Div(cls='cell pad') for _ in range(lead)]
    for r in rows:
        d = Date.fromisoformat(r['date'])
        cls = 'cell' + (' krishna' if r['paksha'] == 'Krishna' else '') \
              + (' today' if d == today else '') + (' sun' if r['weekday'] == 0 else '')
        mark = r['tithi_short'] in ('Purnima', 'Amavasya')
        cells.append(A(Div(
            Div(cls='mark') if mark else None,
            Div(Span(str(r['day']), cls='d serif'),
                Span(MOON_GLYPH.get(r['moon_phase'], ''), cls='phase',
                     title=r['moon_phase']), cls='top'),
            Div(Span(r['tithi_short'], cls='t-word'),
                Span(f"{'S' if r['paksha'] == 'Shukla' else 'K'}{(r['tithi_index'] - 1) % 15 + 1}",
                     cls='t-num'), cls='ti'),
            Div(r['nakshatra'], cls='nk'),
            Div(f"↑{r['sunrise']} ↓{r['sunset']}", cls='tm num'),
            cls=cls), href=f"{Routes.day}?date={r['date']}&{q}"))
    tail = (7 - (lead + len(rows)) % 7) % 7
    cells += [Div(cls='cell pad') for _ in range(tail)]
    dows = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
    return Div(
        now_band(day_panchanga(place, today, planets=False, spans=False)),
        Div(Div(H2(Span(month_name[month], cls='serif'), ' ',
                   Span(str(year), cls='serif yr')),
                Div(f"{ref['masa']} · {ref['ritu']} ritu · {ref['ayana']} · "
                    f"{ref['samvatsara']} · Shaka {ref['shaka']}", cls='lbl season')),
            Div(A(Button('‹', cls='btn'), href=f'{Routes.month}?y={prev.year}&m={prev.month}&{q}'),
                A(Button('›', cls='btn'), href=f'{Routes.month}?y={nxt.year}&m={nxt.month}&{q}'),
                cls='daynav'),
            cls='monthbar'),
        Div(*[Div(x[:3], cls='lbl') for x in dows], cls='dow'),
        Div(*cells, cls='grid'))

# === day ===

def _rw(k, v, t=None, live=False, sub=None):
    return Div(Div(k, cls='k lbl'),
               Div(v, Small(f' {sub}') if sub else None, cls='v'),
               Div(t, cls='t num') if t else None,
               cls='rw' + (' live' if live else ''))

def _seq(spans, ref):
    'A limb and the ones that follow it before the next sunrise.'
    return Div(*[Span(f"{s['name']} till {_hm_d(s['end'], ref)}",
                      cls='past' if i else '') for i, s in enumerate(spans)], cls='seq')

def _jg_block(place, p, d):
    'Present only when the jyotishganit extra is switched on and its ephemeris is in place.'
    from . import jg
    c = jg.chart_for(place, datetime.fromisoformat(p['sunrise']))
    if not c: return None
    return Section(H3(lbl('Chart at sunrise · jyotishganit')),
        Div(_rw('Lagna', f"{c['lagna']} {c['lagna_deg']}°"),
            *[_rw(x['level'], x['lord'], f"{x['start']} → {x['end']}") for x in c['dasha']],
            cls='rows'),
        P(f"{len(c['divisional'])} divisional charts and the ashtakavarga are in the JSON.",
          cls='lbl', style='text-transform:none;letter-spacing:0;font-size:11.5px;margin-top:10px'),
        cls='blk')

def day_view(place, d, today=None):
    p = day_panchanga(place, d)
    today = today or datetime.now(place.tz).date()
    ref, q = d, place_q(place)
    prev, nxt = d - timedelta(days=1), d + timedelta(days=1)
    is_today = d == today

    left = Div(
        Section(H3(lbl(f"The five limbs · {dia('Panchangam')}")),
            Div(_rw(dia('Tithi'), _seq(p['tithis'], ref), sub=p['paksha']),
                _rw(dia('Nakshatra'), _seq(p['nakshatras'], ref),
                    sub=f"pada {p['nakshatra']['pada']} · {p['nakshatra']['lord']}"),
                _rw(dia('Vara'), p['vara'], sub=p['vara_lord']),
                _rw(dia('Yoga'), _seq(p['yogas'], ref)),
                _rw(dia('Karana'), _seq(p['karanas'], ref)),
                cls='rows'), cls='blk'),

        Section(H3(lbl(f"{dia('Hora')} · planetary hours")),
            Div(*[I(cls=('night ' if h['phase'] == 'night' else '') + 'r',
                     **{'data-s': h['start'], 'data-e': h['end']}) for h in p['horas']],
                cls='ribbon', id='hora-ribbon'),
            Div(*[Div(Span(PLANET_GLYPH[h['name']], cls='g'),
                      Span(f"{h['index']}. {h['name']}", cls='n'),
                      Span(f"{_hm(h['start'])}–{_hm(h['end'])}", cls='t num'),
                      cls='hr' + (' night' if h['phase'] == 'night' else ''),
                      **{'data-s': h['start'], 'data-e': h['end']}) for h in p['horas']],
                cls='horas', id='hora-list'), cls='blk'),

        Section(H3(lbl(f"Thirty {dia('Muhurta')}s · sunrise to sunrise")),
            Div(*[Div(B(m['name']), Div(f"{_hm(m['start'])}–{_hm(m['end'])}", cls='t num'),
                      cls='mu ' + {'auspicious': 'good', 'inauspicious': 'bad'}.get(m['quality'], ''),
                      **{'data-s': m['start'], 'data-e': m['end']}) for m in p['muhurtas']],
                cls='mus', id='mu-list'), cls='blk'))

    right = Div(
        Section(H3(lbl('Sun and moon')),
            Div(*[Div(lbl(k), Div(v, cls='v serif num')) for k, v in (
                    ('Sunrise', _hm(p['sunrise'])), ('Solar noon', _hm(p['solar_noon'])),
                    ('Sunset', _hm(p['sunset'])),
                    ('Day length', f"{int(p['day_length'])}h {round(p['day_length'] % 1 * 60):02d}m"),
                    ('Moonrise', _hm(p['moonrise']) if p['moonrise'] else '—'),
                    ('Moonset', _hm(p['moonset']) if p['moonset'] else '—'))], cls='kv'),
            Div(f"{MOON_GLYPH.get(p['moon_phase'],'')} {p['moon_phase']} · "
                f"moon in {p['moon_rasi']} · sun in {p['sun_rasi']}",
                cls='lbl', style='margin:14px 0 4px;text-transform:none;letter-spacing:.02em;font-size:12px'),
            cls='blk'),

        Section(H3(lbl('Inauspicious · kalam')),
            Div(*[_rw(k['name'].replace(' Kalam', '').replace('Yamagandam', 'Yama'), '',
                      f"{_hm(k['start'])}–{_hm(k['end'])}") for k in p['kalams']], cls='rows'),
            cls='blk'),

        Section(H3(lbl('Auspicious windows')),
            Div(*[_rw(w['name'].split()[0], '', f"{_hm_d(w['start'], ref)}–{_hm_d(w['end'], ref)}")
                  for w in p['windows']], cls='rows'), cls='blk'),

        Section(H3(lbl('Cautions')),
            Div(_rw('Soolam', p['soolam'], sub='avoid setting out'),
                _rw('Chandrashtama', ', '.join(p['chandrashtama']['nakshatras']),
                    sub=f"moon in 8th from {p['chandrashtama']['rasi']}"),
                cls='rows'), cls='blk'),

        _jg_block(place, p, d),

        Section(H3(lbl('Grahas · sidereal')),
            Table(Thead(Tr(Th(''), Th('Graha'), Th('Rasi'), Th('Deg'), Th('Nakshatra'))),
                  Tbody(*[Tr(Td(x['glyph'], cls='g'), Td(x['name'], cls='nm'),
                             Td(f"{RASI_GLYPH[RASI.index(x['rasi'])]} {x['rasi']}"),
                             Td(f"{x['deg']:.1f}°", cls='num'), Td(x['nakshatra']))
                          for x in p['planets']]), cls='tab'), cls='blk'))

    era = Div(
        Span(B(p['samvatsara']), ' samvatsara · Shaka ', B(str(p['shaka'])),
             ' · Vikrama ', B(str(p['vikrama']))), NotStr('<br>'),
        Span(B(p['masa']), ' (adhika)' if p['adhika'] else '', ' māsa · ',
             B(p['tamil_masa']), ' · ', p['ritu'], ' ṛtu · ', p['ayana'],
             ' · ', B(p['paksha']), ' pakṣa'), cls='era')

    return Div(
        now_band(p) if is_today else None,
        Header(Div(Div(str(d.day), cls='dnum serif'),
                   Div(Div(p['vara'], cls='vara serif'),
                       Div(d.strftime('%A, %d %B %Y'), cls='lbl gdate')),
                   Div(A(Button('‹', cls='btn'), href=f'{Routes.day}?date={prev}&{q}'),
                       A(Button('Today', cls='btn'), href=f'{Routes.day}?{q}'),
                       A(Button('›', cls='btn'), href=f'{Routes.day}?date={nxt}&{q}'),
                       A(Button('Month', cls='btn ghost'),
                         href=f'{Routes.month}?y={d.year}&m={d.month}&{q}'),
                       cls='daynav'),
                   cls='row'),
               era, cls='dayhead'),
        Div(left, right, cls='cols'),
        **{'data-date': d.isoformat()})

# === subscribe ===

def _steps(*items): return Ol(*[Li(*(x if isinstance(x, tuple) else (x,))) for x in items], cls='steps')

def subscribe_view(place, base_url):
    """How to add the feed, in the fewest words that still work.

    Written to ASD-STE100 rules: short sentences, active voice, one instruction to a line.
    The first draft explained why each protocol existed, which is interesting and is not
    what somebody reads this page to find out."""
    from .dav import encode_token
    q = place_q(place)
    feed = f'{base_url}{Routes.feed}?{q}&layers=day,kalam,window'
    dav = f'{base_url}{Routes.dav}/{encode_token(place, DEFAULT_LAYERS)}/'
    return Div(
        Header(Div(Div('Subscribe', cls='vara serif', style='font-size:34px'),
                   Div('Add the traditional day to the calendar you already use.',
                       cls='lbl gdate'),
                   cls='row'), cls='dayhead'),
        Div(
            Div(Section(H3(lbl('1 · Select the entries')),
                    Div(*[Label(Input(type='checkbox', name='layer', value=k,
                                      checked=k in DEFAULT_LAYERS, onchange='mh.rebuild()'),
                                Div(B(k.title()), Span(v)), cls='layer') for k, v in LAYERS.items()],
                        cls='layers'),
                    P('The hora layer adds 24 entries each day. The muhurta layer adds 30. '
                      'Select them only if you want the full almanac. They are off by default.',
                      cls='note'),
                    cls='blk'),
                Section(H3(lbl('2 · Copy the link')),
                    Div(lbl('Calendar feed'), style='margin-top:4px'),
                    Div(Input(type='text', id='feed-url', value=feed, readonly=True),
                        Button('Copy', cls='btn accent', onclick='mh.copy("feed-url")'), cls='url'),
                    Div(Button('Open in Calendar', cls='btn', onclick='mh.webcal()', id='webcal-btn'),
                        Span('This sends the feed to your calendar app.', cls='note'),
                        style='display:flex;gap:10px;align-items:center;margin-top:9px;flex-wrap:wrap'),
                    Div(lbl('CalDAV address'), style='margin-top:20px'),
                    Div(Input(type='text', id='dav-url', value=dav, readonly=True),
                        Button('Copy', cls='btn', onclick='mh.copy("dav-url")'), cls='url'),
                    P('Use the calendar feed for Google. Use either one for Apple.', cls='note'),
                    cls='blk')),
            Div(Section(H3(lbl('Google Calendar')),
                    _steps('Open Google Calendar in a web browser. You cannot add a feed on a phone.',
                           ('Find ', B('Other calendars'), ' in the left column. Click ', B('+'), '.'),
                           ('Click ', B('From URL'), '.'),
                           ('Paste the calendar feed link. Click ', B('Add calendar'), '.'),
                           'Google reads the feed again every 8 to 24 hours.'),
                    cls='blk'),
                Section(H3(lbl('Apple Calendar · Mac')),
                    _steps(('Click ', B('File'), '. Then click ', B('New Calendar Subscription'), '.'),
                           'Paste the calendar feed link. Click Subscribe.',
                           ('Set ', B('Auto-refresh'), ' to Every hour.')),
                    cls='blk'),
                Section(H3(lbl('Apple Calendar · iPhone')),
                    _steps(('Open ', B('Settings'), '. Go to Apps, then Calendar, then Accounts.'),
                           ('Tap ', B('Add Account'), ', then ', B('Other'), '.'),
                           ('Tap ', B('Add Subscribed Calendar'), ' for the feed. '
                            'Tap ', B('Add CalDAV Account'), ' for CalDAV.'),
                           'Paste the link. For CalDAV, leave the user name and the password empty. '
                           'The calendar is public and read-only.'),
                    cls='blk'),
                Section(H3(lbl('Other apps')),
                    P('The feed uses the iCalendar format. Outlook, Fantastical, Thunderbird '
                      'and other apps accept the same link.', cls='note'),
                    cls='blk')),
            cls='sub-grid'))
