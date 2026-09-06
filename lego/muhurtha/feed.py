'''The panchangam as an iCalendar feed (RFC 5545).

This is the part that matters. A calendar app will not learn a new time system, but every
one of them already knows how to read a .ics file over https and refresh it -- so the
traditional day arrives inside the ordinary one, in the app the person already uses, with
no client to install.

Timed events go out in UTC with a trailing Z rather than carrying a VTIMEZONE: the spans
here are astronomical instants, not wall-clock appointments, and every client renders them
in its own zone correctly without a zone definition to disagree over. All-day entries use
local DATE values, because "which day" is a local question.'''

from datetime import datetime, timedelta, timezone, date as Date
from hashlib import md5
from .cfg import cfg, LAYERS, DEFAULT_LAYERS, DENSE_LAYERS
from .panchanga import Place, day_panchanga

__all__ = ['build_feed', 'feed_name', 'iter_events', 'as_object', 'day_description', 'window_for']

PRODID = '-//lego//muhurtha//EN'

def _esc(s):
    'RFC 5545 text escaping: backslash, semicolon, comma, newline.'
    return (str(s).replace('\\', '\\\\').replace(';', r'\;')
                  .replace(',', r'\,').replace('\n', r'\n'))

def _fold(line):
    '''Fold to 75 octets, continuing with a leading space.

    Counted in octets, not characters -- the nakshatra names are ASCII but the place name
    a subscriber passes in need not be, and splitting a UTF-8 sequence corrupts the file.'''
    b = line.encode()
    if len(b) <= 73: return line
    out, cur = [], b''
    for ch in line:
        e = ch.encode()
        if len(cur) + len(e) > (73 if not out else 72):
            out.append(cur.decode()); cur = b''
        cur += e
    out.append(cur.decode())
    return '\r\n '.join(out)

def _utc(iso):
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def _uid(*parts):
    return md5('|'.join(str(p) for p in parts).encode()).hexdigest() + '@muhurtha'

def _ev(uid, dtstamp, summary, start=None, end=None, all_day=None, desc='', cats='', transp='TRANSPARENT'):
    'One VEVENT, as (uid, lines) -- the feed concatenates these, CalDAV serves them one by one.'
    L = ['BEGIN:VEVENT', f'UID:{uid}', f'DTSTAMP:{dtstamp}']
    if all_day:
        L += [f'DTSTART;VALUE=DATE:{all_day[0]}', f'DTEND;VALUE=DATE:{all_day[1]}']
    else:
        L += [f'DTSTART:{start}', f'DTEND:{end}']
    L.append(f'SUMMARY:{_esc(summary)}')
    if desc: L.append(f'DESCRIPTION:{_esc(desc)}')
    if cats: L.append(f'CATEGORIES:{_esc(cats)}')
    L += [f'TRANSP:{transp}', 'X-MICROSOFT-CDO-BUSYSTATUS:FREE', 'END:VEVENT']
    return uid, L

# === the day summary, which is what most subscribers actually want ===

def _hm(iso): return datetime.fromisoformat(iso).strftime('%H:%M')

def _hm_rel(iso, ref):
    'HH:MM, tagged with the weekday when it falls on a later date than the day being described.'
    t = datetime.fromisoformat(iso)
    return t.strftime('%H:%M') if t.date() == ref else t.strftime('%H:%M (%a)')

def _spans_line(label, spans, ref):
    return f'{label}: ' + ', '.join(f"{s['name']} till {_hm_rel(s['end'], ref)}" for s in spans)

def day_description(p):
    'The whole almanac for a day, as the plain text a calendar app will show.'
    ref = Date.fromisoformat(p['date'])
    L = [f"{p['vara']} · {p['paksha']} paksha · {p['masa']}{' (adhika)' if p['adhika'] else ''} · {p['tamil_masa']}",
         f"{p['samvatsara']} samvatsara · Shaka {p['shaka']} · Vikrama {p['vikrama']} · {p['ayana']} · {p['ritu']} ritu",
         '',
         _spans_line('Tithi', p['tithis'], ref),
         _spans_line('Nakshatra', p['nakshatras'], ref),
         _spans_line('Yoga', p['yogas'], ref),
         _spans_line('Karana', p['karanas'], ref),
         '',
         f"Sunrise {_hm(p['sunrise'])} · Solar noon {_hm(p['solar_noon'])} · Sunset {_hm(p['sunset'])}"]
    if p['moonrise'] or p['moonset']:
        L.append(f"Moonrise {_hm(p['moonrise']) if p['moonrise'] else '--'} · "
                 f"Moonset {_hm(p['moonset']) if p['moonset'] else '--'} · {p['moon_phase']}")
    L += ['',
          ' · '.join(f"{k['name']} {_hm(k['start'])}-{_hm(k['end'])}" for k in p['kalams']),
          ' · '.join(f"{w['name']} {_hm(w['start'])}-{_hm(w['end'])}" for w in p['windows']),
          '',
          f"Sun in {p['sun_rasi']} · Moon in {p['moon_rasi']} · Soolam {p['soolam']}",
          f"Chandrashtama: {', '.join(p['chandrashtama']['nakshatras'])}"]
    if p.get('planets'):
        L += ['', 'Sidereal positions: ' + ', '.join(
            f"{x['glyph']} {x['name']} {x['deg']:.0f}° {x['rasi']}" for x in p['planets'])]
    L += ['', f"Ayanamsa {cfg.ayanamsa} · computed for {p['place_name'] or p['place']}"]
    return '\n'.join(L)

def _day_events(p, stamp):
    d = Date.fromisoformat(p['date'])
    title = f"{p['tithi']['name']} · {p['nakshatra']['name']}"
    return [_ev(_uid('day', p['place'], p['date']), stamp, title,
                all_day=(d.strftime('%Y%m%d'), (d+timedelta(days=1)).strftime('%Y%m%d')),
                desc=day_description(p), cats='Panchangam')]

def _panchanga_events(p, stamp):
    return [_ev(_uid(kind, p['place'], s['start']), stamp, s['name'],
                _utc(s['start']), _utc(s['end']),
                desc=f"{s['kind'].title()} {s['index']}", cats=s['kind'].title())
            for kind in ('tithis', 'nakshatras') for s in p[kind]]

def _kalam_events(p, stamp):
    return [_ev(_uid('kalam', p['place'], k['start']), stamp, k['name'],
                _utc(k['start']), _utc(k['end']), cats='Kalam') for k in p['kalams']]

def _window_events(p, stamp):
    return [_ev(_uid('window', p['place'], w['start']), stamp, w['name'],
                _utc(w['start']), _utc(w['end']), cats='Muhurta') for w in p['windows']]

def _hora_events(p, stamp):
    return [_ev(_uid('hora', p['place'], h['start']), stamp, f"{h['name']} hora",
                _utc(h['start']), _utc(h['end']),
                desc='Sub-horas: ' + ', '.join(f"{s['planet']} {_hm(s['start'])}" for s in h['subs']),
                cats='Hora') for h in p['horas']]

def _muhurta_events(p, stamp):
    return [_ev(_uid('muhurta', p['place'], m['start']), stamp, f"{m['index']}. {m['name']}",
                _utc(m['start']), _utc(m['end']),
                desc=f"Muhurta {m['index']} of 30 · {m['quality']}", cats='Muhurta')
            for m in p['muhurtas']]

_EMIT = dict(day=_day_events, panchanga=_panchanga_events, kalam=_kalam_events,
             window=_window_events, hora=_hora_events, muhurta=_muhurta_events)

def feed_name(place, layers):
    base = place.name or place.key()
    return f"Muhurtha · {base}" if set(layers) - {'day'} else f"Panchangam · {base}"

def window_for(layers, back, days):
    'Clamp the span so a feed stays a file a phone will fetch.'
    dense = any(l in DENSE_LAYERS for l in layers)
    cap = cfg.feed_dense_days if dense else cfg.feed_max_days
    return min(back if back is not None else cfg.feed_back, 60), \
           min(days if days is not None else (cfg.feed_dense_days if dense else cfg.feed_days), cap)

def build_feed(place, layers=DEFAULT_LAYERS, back=None, days=None, today=None):
    'The whole .ics as a CRLF-joined string.'
    layers = [l for l in layers if l in LAYERS] or list(DEFAULT_LAYERS)
    back, days = window_for(layers, back, days)
    t0 = today or datetime.now(place.tz).date()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    nm = feed_name(place, layers)
    L = ['BEGIN:VCALENDAR', 'VERSION:2.0', f'PRODID:{PRODID}', 'CALSCALE:GREGORIAN',
         'METHOD:PUBLISH', f'X-WR-CALNAME:{_esc(nm)}', f'NAME:{_esc(nm)}',
         f'X-WR-TIMEZONE:{place.tzname}',
         f'X-WR-CALDESC:{_esc(cfg.tagline)}', f'DESCRIPTION:{_esc(cfg.tagline)}',
         'REFRESH-INTERVAL;VALUE=DURATION:PT12H', 'X-PUBLISHED-TTL:PT12H',
         f'SOURCE;VALUE=URI:https://{cfg.domain}/muhurtha/feed.ics',
         'COLOR:maroon']
    for _uid_, lines in iter_events(place, layers, t0, back, days, stamp):
        L += lines
    L.append('END:VCALENDAR')
    return '\r\n'.join(_fold(x) for x in L) + '\r\n'

def iter_events(place, layers, t0, back, days, stamp=None):
    'Yield (uid, lines) for every event in the window -- the feed and CalDAV share this.'
    stamp = stamp or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    rich = 'day' in layers
    for i in range(-back, days):
        d = t0 + timedelta(days=i)
        p = day_panchanga(place, d, planets=rich, spans=rich)
        for l in layers:
            yield from _EMIT[l](p, stamp)

def as_object(uid, lines, name='Muhurtha'):
    'One event wrapped as a standalone calendar object resource, which is what CalDAV serves.'
    L = ['BEGIN:VCALENDAR', 'VERSION:2.0', f'PRODID:{PRODID}', 'CALSCALE:GREGORIAN',
         f'X-WR-CALNAME:{_esc(name)}'] + list(lines) + ['END:VCALENDAR']
    return '\r\n'.join(_fold(x) for x in L) + '\r\n'
