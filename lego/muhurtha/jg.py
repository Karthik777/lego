'''Optional depth, borrowed from jyotishganit when it is installed.

The calendar does not need this. The five limbs, the muhurtas, the horas and the kalams are
all computed in `ephem.py` and `panchanga.py` with no dependencies and no data files, and
they agree with JPL to a few arcseconds -- adding a 17MB kernel to recompute them would buy
nothing.

What jyotishganit does bring is the layer above an almanac: a full varga set, the vimshottari
dasha, ashtakavarga, planetary strengths. That is a chart cast for an instant rather than a
day described, so it lives behind a switch: set MUHURTHA_JYOTISHGANIT=true and it appears on
the day page. Off, absent or broken, the calendar is unchanged -- every call here returns
None rather than raising, because a missing ephemeris download must not take a page down.'''

import os
from datetime import datetime
from functools import lru_cache
from lego.core import quick_lgr

__all__ = ['available', 'chart_for']

info, error, warn = quick_lgr()

def wanted(): return (os.getenv('MUHURTHA_JYOTISHGANIT') or '').lower() in ('1', 'true', 'yes')

@lru_cache(maxsize=1)
def available():
    'True when the package imports and its ephemeris is actually on disk.'
    if not wanted(): return False
    try:
        from jyotishganit.core.astronomical import get_ephemeris
        get_ephemeris()
        return True
    except Exception as e:
        warn(f'jyotishganit unavailable, day pages stay on the built-in engine: {e}')
        return False

def _offset_hours(dt):
    off = dt.utcoffset()
    return off.total_seconds()/3600 if off else 0.0

@lru_cache(maxsize=256)
def _chart(iso, lat, lon, off, name):
    from jyotishganit.main import calculate_birth_chart
    return calculate_birth_chart(datetime.fromisoformat(iso).replace(tzinfo=None),
                                 lat, lon, off, location_name=name)

def chart_for(place, when, name=''):
    '''A full chart cast for an instant, or None if the extra is not switched on.

    Keyed on the instant rather than the day: casting at sunrise is what makes the result a
    property of the day rather than of the moment somebody loaded the page.'''
    if not available(): return None
    try:
        c = _chart(when.isoformat(), round(place.lat, 4), round(place.lon, 4),
                   _offset_hours(when), name or place.name)
        return _summarise(c)
    except Exception as e:
        error(f'jyotishganit chart failed for {place.key()} {when}: {e}')
        return None

def _summarise(c):
    """The parts of a full chart worth putting on a calendar page.

    Kept to what a day view can show without becoming a horoscope: the lagna rising at
    sunrise, the three running vimshottari periods, and the list of vargas the chart carries
    so the JSON consumer knows what it can ask for."""
    asc = c.d1_chart.houses[0]
    return dict(
        lagna=asc.sign, lagna_deg=round(asc.sign_degrees or 0, 2),
        dasha=_running_dasha(c.dashas.current),
        divisional=sorted(c.divisional_charts),
        ayanamsa=round(getattr(c.ayanamsa, 'value', 0) or 0, 4))

# The tree is {"mahadashas": {lord: {start, end, "antardashas": {lord: {...}}}}} -- one key
# per level, named for the level below it.
_LEVELS = (('mahadashas', 'Mahadasha'), ('antardashas', 'Antardasha'),
           ('pratyantardashas', 'Pratyantardasha'))

def _running_dasha(current):
    'Flatten the nested current-period tree into mahadasha, antardasha, pratyantardasha.'
    out, node = [], current or {}
    for key, label in _LEVELS:
        branch = node.get(key) or {}
        if not branch: break
        lord, data = next(iter(branch.items()))
        out.append(dict(level=label, lord=lord,
                        start=str(data.get('start'))[:10], end=str(data.get('end'))[:10]))
        node = data
    return out
