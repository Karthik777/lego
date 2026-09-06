'''The five limbs, and the day they describe.

A panchangam is not a list of events on a clock. It is a different clock: the day begins at
sunrise, the lunar day ends when the moon has gained another twelve degrees on the sun, and
neither boundary lands on the hour. So everything here is computed as a span with real start
and end instants, and the calendar is assembled out of those spans rather than out of dates.

Positions are sidereal (Lahiri) except the tithi, yoga and karana, which are differences and
sums of longitudes and so do not care which zodiac you measure from.'''

from datetime import datetime, timedelta, timezone, date as Date
from zoneinfo import ZoneInfo
from math import floor
from . import ephem as E
from .names import *

__all__ = ['Place', 'Span', 'day_panchanga', 'month_panchanga', 'sunrise_day']

# === place ===

class Place:
    'A latitude, a longitude and the timezone whose civil clock the day is read on.'
    def __init__(self, lat, lon, tz='UTC', name=''):
        self.lat, self.lon, self.name = float(lat), float(lon), name
        self.tzname = tz
        self.tz = ZoneInfo(tz)
    def local(self, jd): return E.dt_from_jd(jd).astimezone(self.tz)
    def key(self): return f'{self.lat:.4f},{self.lon:.4f},{self.tzname}'
    def __repr__(self): return f'Place({self.key()})'

def _jd(dt): return E.jd_from_dt(dt.astimezone(timezone.utc))

class Span:
    'A named stretch of time with an index, carried around as JD and handed out as datetimes.'
    def __init__(self, kind, index, name, start, end, **extra):
        self.kind, self.index, self.name, self.start, self.end = kind, index, name, start, end
        self.extra = extra
    def dt(self, place): return place.local(self.start), place.local(self.end)
    def d(self, place):
        s, e = self.dt(place)
        return dict(kind=self.kind, index=self.index, name=self.name,
                    start=s.isoformat(), end=e.isoformat(), **self.extra)

# === angle series the limbs are cut from ===

def _tithi_angle(jd): return E.norm360(E.moon_long(jd) - E.sun_long(jd))
def _nak_angle(jd):   return E.norm360(E.moon_long(jd) - E.ayanamsa(jd))
def _yoga_angle(jd):  return E.norm360(E.moon_long(jd) + E.sun_long(jd) - 2*E.ayanamsa(jd))
def _sun_angle(jd):   return E.norm360(E.sun_long(jd) - E.ayanamsa(jd))

def _root(f, lo, hi):
    'Root of a function that rises through zero on [lo, hi], to about a tenth of a second.'
    return E.brent_root(f, lo, hi, tol=1e-6)

def _segment(angle, jd, step, rate):
    '''Start and end JD of the `step`-degree segment holding jd, for a monotone angle.

    The angles below all increase without ever going backwards -- the moon outruns the sun,
    always -- so each boundary is a single sign change, and bisection finds it exactly.
    Wrapping to +/-180 is safe because the search window is under half a turn of motion.'''
    a0 = angle(jd)
    lo_t = floor(a0/step)*step
    w = 2.2*step/rate
    d = lambda tgt: (lambda t: (angle(t) - tgt + 180) % 360 - 180)
    return _root(d(lo_t), jd-w, jd), _root(d(lo_t+step), jd, jd+w)

_RATE = dict(tithi=12.19, nak=13.17, yoga=14.15, karana=12.19)

def _limb(kind, angle, jd, step, rate, namer):
    idx = int(angle(jd)//step)
    s, e = _segment(angle, jd, step, rate)
    return Span(kind, idx, *namer(idx), s, e) if isinstance(namer(idx), tuple) else \
           Span(kind, idx, namer(idx), s, e)

# === the five limbs at an instant ===

def tithi_at(jd):
    i = int(_tithi_angle(jd)//12)
    s, e = _segment(_tithi_angle, jd, 12, _RATE['tithi'])
    paksha = 'Shukla' if i < 15 else 'Krishna'
    nm = TITHI[i % 15] if i != 29 else 'Amavasya'
    return Span('tithi', i+1, f'{paksha} {nm}', s, e, paksha=paksha, short=nm)

def nakshatra_at(jd):
    a = _nak_angle(jd); i = int(a//(360/27))
    s, e = _segment(_nak_angle, jd, 360/27, _RATE['nak'])
    pada = int((a % (360/27))//(360/108)) + 1
    return Span('nakshatra', i+1, NAKSHATRA[i], s, e, pada=pada, lord=NAK_LORD[i])

def yoga_at(jd):
    i = int(_yoga_angle(jd)//(360/27))
    s, e = _segment(_yoga_angle, jd, 360/27, _RATE['yoga'])
    return Span('yoga', i+1, YOGA[i], s, e)

def karana_at(jd):
    i = int(_tithi_angle(jd)//6)
    s, e = _segment(_tithi_angle, jd, 6, _RATE['karana'])
    nm = KARANA_FIXED[0] if i == 0 else KARANA_FIXED[i-56] if i >= 57 else KARANA_MOVABLE[(i-1) % 7]
    return Span('karana', i+1, nm, s, e)

def _run(fn, start, end, first=None):
    'Every span of one kind that overlaps [start, end), reusing the one already read at start.'
    sp = first or fn(start)
    out = [sp]
    while sp.end < end and len(out) < 12:
        sp = fn(sp.end + 1e-6); out.append(sp)
    return out

# === the sunrise-to-sunrise day ===

def sunrise_day(place, d):
    'Sunrise, solar noon, sunset and the next sunrise bounding the ahoratra that starts on d.'
    def rise_set(dd):
        noon_guess = E.jd_from_dt(datetime(dd.year, dd.month, dd.day, 12, tzinfo=timezone.utc)) - place.lon/360
        return E.sun_events(noon_guess, place.lat, place.lon)
    a, b = rise_set(d), rise_set(d + timedelta(days=1))
    if a['rise'] is None or a['set'] is None:      # polar day or night: fall back on transit
        a = dict(a, rise=a['noon']-0.5, set=a['noon']+0.5)
    nxt = b['rise'] if b['rise'] is not None else b['noon']-0.5
    return a['rise'], a['noon'], a['set'], nxt

# === derived blocks ===

def _slices(start, end, n, kind, names, quality=None):
    'n equal blocks that abut exactly and finish on `end`.'
    step = (end - start)/n
    at = lambda i: end if i == n else start + step*i
    return [Span(kind, i+1, names[i], at(i), at(i+1),
                 **({'quality': quality(names[i])} if quality else {}))
            for i in range(n)]

def _muhurta_quality(nm):
    return 'auspicious' if nm in AUSPICIOUS_MUHURTAS else \
           'inauspicious' if nm in INAUSPICIOUS_MUHURTAS else 'neutral'

def muhurtas(rise, sset, nxt):
    '''The thirty muhurtas: fifteen across the day, fifteen across the night.

    A muhurta is about forty-eight minutes, but only about -- it is a thirtieth of the
    stretch from sunrise to sunrise, so it breathes with the season and is only exactly
    48 minutes twice a year.'''
    return (_slices(rise, sset, 15, 'muhurta', MUHURTA_DAY, _muhurta_quality)
            + _slices(sset, nxt, 15, 'muhurta', MUHURTA_NIGHT, _muhurta_quality))

# Which of the eight parts of daylight each kalam falls in, Sunday first.
_RAHU, _YAMA, _GULIKA = (8,2,7,5,6,4,3), (5,4,3,2,1,7,6), (7,6,5,4,3,2,1)

def kalams(rise, sset, weekday):
    'Rahu kalam, Yamagandam and Gulika kalam: one eighth of daylight each, placed by weekday.'
    step = (sset - rise)/8
    part = lambda n: (rise + step*(n-1), rise + step*n)
    out = []
    for nm, tbl in (('Rahu Kalam',_RAHU), ('Yamagandam',_YAMA), ('Gulika Kalam',_GULIKA)):
        s, e = part(tbl[weekday])
        out.append(Span('kalam', tbl[weekday], nm, s, e, quality='inauspicious'))
    return out

def horas(rise, sset, nxt, weekday):
    '''Twenty-four planetary hours, twelve of day and twelve of night, each split into seven.

    The day's first hora belongs to the planet the day is named for; the rest follow the
    Chaldean order. A day hora is a twelfth of daylight and a night hora a twelfth of dark,
    so the two are the same length only at an equinox.'''
    lord = VARA_LORD[weekday]
    first = PLANETS.index(lord)
    dh, nh = (sset-rise)/12, (nxt-sset)/12
    # Each bound is derived from the anchor rather than from the previous end, so the blocks
    # abut exactly instead of drifting apart by a float ulp per step, and the twelfth day
    # hora ends on sunset itself.
    bound = lambda i: (sset if i == 12 else rise + dh*i) if i <= 12 else \
                      (nxt if i == 24 else sset + nh*(i-12))
    out = []
    for i in range(24):
        day = i < 12
        s, e = bound(i), bound(i+1)
        p = PLANETS[(first+i) % 7]
        subs = [dict(planet=PLANETS[(first+i+j) % 7], index=j+1,
                     start=s+(e-s)*j/7, end=s+(e-s)*(j+1)/7) for j in range(7)]
        out.append(Span('hora', i+1, p, s, e, phase='day' if day else 'night', subs=subs))
    return out

def special_windows(rise, sset, noon, nxt):
    'The named windows people actually look up: Abhijit, Brahma muhurta, Godhuli, Nishita.'
    dm, nm = (sset-rise)/15, (nxt-sset)/15
    return [Span('window', 1, 'Brahma Muhurta', rise-2*nm, rise-nm, quality='auspicious'),
            Span('window', 2, 'Abhijit', rise+7*dm, rise+8*dm, quality='auspicious'),
            Span('window', 3, 'Godhuli', sset-dm/3, sset+dm/3, quality='neutral'),
            Span('window', 4, 'Nishita', sset+7*nm, sset+8*nm, quality='neutral')]

# === lunar month, year, season ===

def _new_moon_before(jd):
    'JD of the new moon at or before jd -- the start of the current amanta month.'
    return _segment(_tithi_angle, jd, 360, 12.19)[0] if _tithi_angle(jd) < 1e-9 else \
           _root(lambda t: (_tithi_angle(t) - 0 + 180) % 360 - 180, jd-30, jd) if False else _nm(jd)

def _nm(jd):
    # The tithi angle runs 0->360 once a synodic month; walk back to where it last was 0.
    a = _tithi_angle(jd)
    approx = jd - a/12.19
    return _root(lambda t: (_tithi_angle(t) + 180) % 360 - 180, approx-2, approx+2)

def masa_at(jd):
    '''Amanta lunar month, and whether it is an intercalary one.

    A lunar month takes its name from the solar month the sun steps into while it runs. When
    the sun steps into none -- which happens because a lunar month is the shorter of the two
    -- the month is adhika, repeated, and the calendar gains a thirteenth.'''
    start = _nm(jd)
    end = _nm(start + 31)
    r0, r1 = int(_sun_angle(start)//30), int(_sun_angle(end - 1e-4)//30)
    adhika = r0 == r1
    i = (r0 + 1) % 12
    return dict(index=i, name=MASA[i], adhika=adhika, start=start, end=end,
                ritu=RITU[i//2], tamil=TAMIL_MASA[int(_sun_angle(jd)//30)])

def year_at(jd, greg_year, greg_month, masa_index):
    'Shaka and Vikrama years, and the name of the year in the sixty-year cycle.'
    shaka = greg_year - 78 if greg_month >= 4 else greg_year - 79 if greg_month <= 2 else \
            (greg_year - 79 if masa_index == 11 else greg_year - 78)
    return dict(shaka=shaka, vikrama=shaka+135, samvatsara=SAMVATSARA[(shaka+11) % 60])

def _moon_phase(angle):
    return MOON_PHASE[int((angle + 22.5) % 360 // 45)]

# === the day ===

def day_panchanga(place, d, planets=True, spans=True):
    '''Everything about one sunrise-to-sunrise day at one place.

    The five limbs are read at sunrise, which is the convention that names the day, but the
    spans that follow within the day are carried too -- an almanac that says only "Trayodashi"
    is hiding the fact that it stops at nine in the morning.'''
    rise, noon, sset, nxt = sunrise_day(place, d)
    weekday = (place.local(rise).weekday() + 1) % 7        # 0 = Sunday
    t, n, y, k = tithi_at(rise), nakshatra_at(rise), yoga_at(rise), karana_at(rise)
    m = masa_at(rise)
    sun_sid, moon_sid = _sun_angle(rise), _nak_angle(rise)
    moon_rasi = int(moon_sid//30)
    # Chandrashtama: the moon is sitting in the eighth house from these janma rasis.
    ca_rasi = (moon_rasi - 7) % 12
    ca_naks = sorted({NAKSHATRA[int(x//(360/27))] for x in
                      (ca_rasi*30 + 0.01, ca_rasi*30 + 15, ca_rasi*30 + 29.99)})
    mo = E.moon_events(E.jd_from_dt(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
                       - place.lon/360 - 0.5, place.lat, place.lon)
    out = dict(
        date=d.isoformat(), place=place.key(), place_name=place.name, tz=place.tzname,
        weekday=weekday, vara=VARA[weekday], vara_lord=VARA_LORD[weekday],
        sunrise=place.local(rise).isoformat(), solar_noon=place.local(noon).isoformat(),
        sunset=place.local(sset).isoformat(), next_sunrise=place.local(nxt).isoformat(),
        moonrise=place.local(mo['rise']).isoformat() if mo['rise'] else None,
        moonset=place.local(mo['set']).isoformat() if mo['set'] else None,
        day_length=round((sset-rise)*24, 4),
        tithi=t.d(place), nakshatra=n.d(place), yoga=y.d(place), karana=k.d(place),
        paksha=t.extra['paksha'], moon_phase=_moon_phase(_tithi_angle(rise)),
        masa=m['name'], adhika=m['adhika'], ritu=m['ritu'], tamil_masa=m['tamil'],
        ayana='Uttarayana' if (sun_sid >= 270 or sun_sid < 90) else 'Dakshinayana',
        sun_rasi=RASI[int(sun_sid//30)], moon_rasi=RASI[moon_rasi],
        soolam=SOOLAM[weekday],
        chandrashtama=dict(rasi=RASI[ca_rasi], nakshatras=ca_naks),
        muhurtas=[s.d(place) for s in muhurtas(rise, sset, nxt)],
        horas=[_hora_d(s, place) for s in horas(rise, sset, nxt, weekday)],
        kalams=[s.d(place) for s in kalams(rise, sset, weekday)],
        windows=[s.d(place) for s in special_windows(rise, sset, noon, nxt)])
    out.update(year_at(rise, d.year, d.month, m['index']))
    # The spans that run on past sunrise. Only the day summary needs them, and each one is
    # two more root-finds, so a hora-only feed does not pay for them.
    if spans:
        for key, fn, first in (('tithis', tithi_at, t), ('nakshatras', nakshatra_at, n),
                               ('yogas', yoga_at, y), ('karanas', karana_at, k)):
            out[key] = [x.d(place) for x in _run(fn, rise, nxt, first)]
    else:
        for key, first in (('tithis', t), ('nakshatras', n), ('yogas', y), ('karanas', k)):
            out[key] = [first.d(place)]
    if planets:
        out['planets'] = [dict(name=k2, lon=round(v, 3), rasi=RASI[int(v//30)],
                               deg=round(v % 30, 2), nakshatra=NAKSHATRA[int(v//(360/27))],
                               glyph=PLANET_GLYPH[k2]) for k2, v in E.planet_longs(rise).items()]
    return out

def _hora_d(s, place):
    d = s.d(place)
    d['subs'] = [dict(planet=x['planet'], index=x['index'],
                      start=place.local(x['start']).isoformat(),
                      end=place.local(x['end']).isoformat()) for x in s.extra['subs']]
    return d

def month_panchanga(place, year, month):
    'A light row per day -- what a month grid can show without computing thirty full days.'
    from calendar import monthrange
    out = []
    for dd in range(1, monthrange(year, month)[1] + 1):
        d = Date(year, month, dd)
        rise, noon, sset, nxt = sunrise_day(place, d)
        t, n = tithi_at(rise), nakshatra_at(rise)
        wd = (place.local(rise).weekday() + 1) % 7
        out.append(dict(date=d.isoformat(), day=dd, weekday=wd,
                        tithi=t.name, tithi_index=t.index, tithi_short=t.extra['short'],
                        paksha=t.extra['paksha'], tithi_end=place.local(t.end).isoformat(),
                        nakshatra=n.name, nakshatra_end=place.local(n.end).isoformat(),
                        moon_phase=_moon_phase(_tithi_angle(rise)),
                        sunrise=place.local(rise).strftime('%H:%M'),
                        sunset=place.local(sset).strftime('%H:%M')))
    return out
