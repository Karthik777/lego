import os
from dataclasses import dataclass
from fastcore.all import AttrDict

@dataclass(frozen=True)
class Routes:
    index    = '/muhurtha'
    day      = '/muhurtha/day'
    month    = '/muhurtha/month'
    subscribe= '/muhurtha/subscribe'
    feed     = '/muhurtha/feed.ics'
    api_day  = '/muhurtha/api/day'
    api_month= '/muhurtha/api/month'
    api_place= '/muhurtha/api/place'
    dav      = '/muhurtha/dav'
    wk_caldav= '/.well-known/caldav'
    skip     = ['/muhurtha', r'/muhurtha/.*', r'/\.well-known/caldav']

# Layers a subscriber can switch on. Keeping them separate is the whole point: a calendar
# with 30 muhurta blocks a day is unreadable, and one with none is not a panchangam.
LAYERS = {
    'day':      'One all-day entry per day, carrying the full panchangam',
    'panchanga':'Tithi and nakshatra as timed spans, ending when they actually end',
    'kalam':    'Rahu kalam, Yamagandam, Gulika kalam',
    'window':   'Brahma muhurta, Abhijit, Godhuli, Nishita',
    'hora':     'All 24 planetary hours',
    'muhurta':  'All 30 muhurtas',
}
DEFAULT_LAYERS = ('day', 'kalam', 'window')
# Layers that emit many events a day are capped harder, or a year's feed is tens of MB.
DENSE_LAYERS = ('hora', 'muhurta', 'panchanga')

cfg = AttrDict(
    domain      = os.getenv('MUHURTHA_DOMAIN') or os.getenv('HORA_DOMAIN') or 'sankalpa.sh',
    title       = os.getenv('MUHURTHA_TITLE') or 'Muhurtha',
    tagline     = 'A calendar that keeps the traditional day: panchangam, muhurta and hora, subscribable from any calendar app.',
    theme_color = '#8C2F1E',
    # Default place when a visitor has not chosen one and has not shared their location.
    lat  = float(os.getenv('MUHURTHA_LAT') or 13.0827),
    lon  = float(os.getenv('MUHURTHA_LON') or 80.2707),
    tz   = os.getenv('MUHURTHA_TZ') or 'Asia/Kolkata',
    place_name = os.getenv('MUHURTHA_PLACE') or 'Chennai',
    ayanamsa = 'Lahiri (Chitrapaksha)',
    # Rolling feed window. Calendar apps refetch, so this only has to cover the horizon a
    # person actually plans against.
    feed_back = int(os.getenv('MUHURTHA_FEED_BACK') or 30),
    feed_days = int(os.getenv('MUHURTHA_FEED_DAYS') or 180),
    feed_dense_days = int(os.getenv('MUHURTHA_FEED_DENSE_DAYS') or 45),
    feed_max_days = 400,
    cache_ttl = int(os.getenv('MUHURTHA_CACHE_TTL') or 6*3600),
)
