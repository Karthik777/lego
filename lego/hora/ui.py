from fasthtml.common import Html, Head, Body, Meta, Title, Link, Socials, NotStr
from fastcore.all import Path
from lego.core import asset_css, asset_js, vendor_js, vlink, rendered
from .cfg import cfg

__all__ = ['page']

here = Path(__file__).parent
# The one class the shell needs that is not inside page.html, because page.html is the body
# and this is the body's own attribute.
body_cls = 'min-h-screen bg-gradient-to-b from-slate-50 to-white text-slate-900'

def head():
    '''hora's own head, not the app's.

    Every other page in lego shares one head built in `lego/app.py` — Oat, the theme
    stylesheet, htmx, the icon sprites. None of it belongs here: this page is styled by
    Tailwind, which brings its own preflight, and the two resets fight over the same
    elements. So the block renders a whole document and the app-wide head never reaches it.

    What the standalone version loaded from four third-party origins — Tailwind's in-browser
    compiler, luxon, astronomy-engine and Google Fonts — is served from static/vendor with a
    content-hashed ?v=, behind the immutable mount.'''
    url = f'https://{cfg.domain}'
    return Head(
        Meta(charset='UTF-8'),
        Meta(name='viewport', content='width=device-width, initial-scale=1.0, viewport-fit=cover'),
        Meta(name='theme-color', content=cfg.theme_color),
        Meta(name='description', content=cfg.tagline),
        Meta(name='robots', content='index, follow'),
        Meta(name='apple-mobile-web-app-capable', content='yes'),
        Meta(name='mobile-web-app-capable', content='yes'),
        Title(cfg.title),
        Link(rel='canonical', href=url),
        Link(rel='icon', type='image/svg+xml', href='/static/favicon.svg'),
        *Socials(title=cfg.title, description=cfg.tagline, site_name=cfg.domain,
                 image='/static/favicon.svg', url=url),
        Link(rel='stylesheet', href=vlink('/static/vendor/inter.css')),
        asset_css(here / 'hora.css'),
        vendor_js('luxon.min.js'), vendor_js('astronomy.browser.min.js'))

def _doc():
    # hora.js is an IIFE that reads the document the moment it runs, so it stays where it
    # was: last thing in the body, after everything it looks up by id exists.
    body = Body(NotStr((here / 'page.html').read_text()), asset_js(here / 'hora.js'), cls=body_cls)
    return Html(head(), body, lang='en')

def page():
    'The document, serialised once — nothing in it varies by request. `to_xml` adds the doctype.'
    return str(rendered('hora', _doc))
