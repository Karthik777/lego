'''Pull the third-party CSS/JS/fonts the app links to into static/vendor.

A page that links out to jsdelivr, cdnjs and Google Fonts pays a DNS lookup, a TLS
handshake and a round trip *per host* before it can finish rendering, and the font CSS
chains to a second host for the files it names. Served from static/vendor they are the
connection the browser already has, behind the immutable mount and a content-hashed ?v=.

Pins matter as much as latency: several of these were on `@latest` or `@main`, which is a
URL whose contents can change under a deployed app and cannot be cached for long. Every
pin here is exact.

Run after changing PKGS, then commit what lands in static/vendor:

    uv run python tools/vendor_fetch.py
'''
import re, sys
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen, Request

VENDOR = Path('static/vendor')
FONTS = VENDOR / 'fonts'

# name in static/vendor -> exact upstream URL
PKGS = {
    # what fast_app puts in the head by default (fasthtml.core: htmxsrc, fhjsscr, surrsrc,
    # scopesrc) plus the preload extension lego asks for by name
    'htmx.min.js':              'https://cdn.jsdelivr.net/npm/htmx.org@2.0.7/dist/htmx.min.js',
    'fasthtml.js':              'https://cdn.jsdelivr.net/gh/answerdotai/fasthtml-js@1.0.12/fasthtml.js',
    'surreal.js':               'https://cdn.jsdelivr.net/gh/answerdotai/surreal@1.3.2/surreal.js',
    # css-scope-inline publishes no tags at all, so @main is the only URL there is. That is
    # the strongest argument for vendoring it: the copy in static/vendor is the pin, and
    # the digest printed below is what says whether upstream has moved since.
    'css-scope-inline.js':      'https://cdn.jsdelivr.net/gh/gnat/css-scope-inline@main/script.js',
    'htmx-ext-preload.js':      'https://cdn.jsdelivr.net/npm/htmx-ext-preload@2.1.1/preload.js',
    # the blog's code blocks
    'highlight.min.js':         'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.11.1/build/highlight.min.js',
    'highlight-python.min.js':  'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.11.1/build/languages/python.min.js',
    # both, because the blog swaps the href when the page flips between light and dark
    'highlight-dark.min.css':   'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.11.1/build/styles/atom-one-dark.min.css',
    'highlight-light.min.css':  'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.11.1/build/styles/atom-one-light.min.css',
    'highlightjs-copy.min.js':  'https://cdn.jsdelivr.net/gh/arronhunt/highlightjs-copy@v1.0.6/dist/highlightjs-copy.min.js',
    'highlightjs-copy.min.css': 'https://cdn.jsdelivr.net/gh/arronhunt/highlightjs-copy@v1.0.6/dist/highlightjs-copy.min.css',
    'nosleep.min.js':           'https://cdnjs.cloudflare.com/ajax/libs/nosleep/0.12.0/NoSleep.min.js',
    # the hora block: date/timezone maths and the ephemeris the planetary hours are built from
    'luxon.min.js':             'https://cdn.jsdelivr.net/npm/luxon@3.5.0/build/global/luxon.min.js',
    'astronomy.browser.min.js': 'https://cdn.jsdelivr.net/npm/astronomy-engine@2.1.19/astronomy.browser.min.js',
}

# A UA modern enough that Google serves woff2 rather than the ttf fallback, which is
# roughly twice the bytes for the same glyphs.
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')
FAMILIES = ['Libre+Baskerville', 'Fira+Code', 'Playfair+Display']
WEIGHTS = '300;400;500;600;700'
# The hora block is a standalone document — it does not carry the core head — and Inter is
# the only face it wants, so it gets its own sheet rather than the 20KB one every other
# page links.
HORA_FAMILIES = ['Inter']

def get(url, ua=False):
    req = Request(url, headers={'User-Agent': UA} if ua else {})
    with urlopen(req, timeout=60) as r: return r.read()

def fetch_pkgs():
    VENDOR.mkdir(parents=True, exist_ok=True)
    for nm, url in PKGS.items():
        b = get(url)
        (VENDOR / nm).write_bytes(b)
        print(f'  {nm:26s} {len(b)/1024:7.1f}KB  sha256:{sha256(b).hexdigest()[:16]}  {url}')

def fetch_fonts(families=None, out='fonts.css'):
    '''The @font-face CSS, with every file it names pulled down beside it.

    Google returns one src per family/weight/subset; the CSS is rewritten to point at the
    local copies so the browser never learns fonts.gstatic.com exists.'''
    FONTS.mkdir(parents=True, exist_ok=True)
    q = '&'.join(f'family={f}:wght@{WEIGHTS}' for f in (families or FAMILIES)) + '&display=swap'
    css = get(f'https://fonts.googleapis.com/css2?{q}', ua=True).decode()
    seen, total = {}, 0
    for url in dict.fromkeys(re.findall(r'url\((https://[^)]+)\)', css)):
        nm = url.rsplit('/', 2)[-2] + '-' + url.rsplit('/', 1)[-1]
        nm = re.sub(r'[^A-Za-z0-9._-]', '_', nm)
        b = get(url, ua=True)
        (FONTS / nm).write_bytes(b)
        seen[url], total = nm, total + len(b)
        css = css.replace(url, f'/static/vendor/fonts/{nm}')
    (VENDOR / out).write_text(css)
    print(f'  {out:26s} {len(css)/1024:7.1f}KB  {len(seen)} files, {total/1024:.0f}KB of woff2')

if __name__ == '__main__':
    print('packages:'); fetch_pkgs()
    print('fonts:');    fetch_fonts()
    fetch_fonts(HORA_FAMILIES, out='inter.css')
    print('\nvendored into', VENDOR.resolve())
