"Oat UI for FastHTML: a drop-in for Pico. `app, rt = fast_app(oat=True)`."
import hashlib, json, uuid
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from fastcore.meta import delegates
from fastcore.xml import FT, NotStr
from fasthtml.common import *
from fasthtml.common import fast_app as fh_fast_app
from fasthtml.components import Ot_dropdown, Ot_tabs
from starlette.responses import FileResponse, Response
from starlette.routing import Route

__all__ = ['OAT_VER', 'oatcss', 'oatjs', 'THEMES', 'Theme', 'oat_hdrs', 'oat_htmlkw', 'serve_oat', 'fast_app',
           'Card', 'Group', 'Search', 'Grid', 'Row', 'Col', 'DialogX', 'DialogOpen', 'DialogClose', 'Container', 'OatBusy',
           'Btn', 'ABtn', 'Badge', 'Alert', 'Field', 'Switch', 'Tabs', 'Dropdown', 'Avatar', 'Skeleton',
           'Navbar', 'Hero', 'PageFooter', 'ModeToggle', 'ThemePicker', 'Toast', 'toast_hdr']

OAT_VER = '1.1.0'
STATIC, PREFIX = Path(__file__).parent/'static', '/fhoat'
FILES = ('oat.min.css', 'oat.min.js', 'fhoat.css', 'fhoat.js')
oatcss = f'https://cdn.jsdelivr.net/npm/@knadh/oat@{OAT_VER}/oat.min.css'
oatjs = f'https://cdn.jsdelivr.net/npm/@knadh/oat@{OAT_VER}/oat.min.js'
THEMES = dict(default='#262626', slate='#334155', stone='#44403c', rose='#e11d48', orange='#ea580c', amber='#b45309',
              green='#15803d', teal='#0f766e', blue='#2563eb', indigo='#4f46e5', violet='#7c3aed', paper='#8a1f11', ink='#000000')

# ── Theme ────────────────────────────────────────────────────────────────────
RADII = dict(none=(0, 0, 0), sm=(.125, .25, .375), md=(.25, .5, .75), lg=(.375, .75, 1.25), full=(.5, 1, 1.5))
SHADOWS = dict(none=('none',)*3, sm=('0 1px 2px rgb(0 0 0 / .05)', '0 1px 3px rgb(0 0 0 / .08)', '0 8px 20px -8px rgb(0 0 0 / .18)'),
               md=('0 1px 3px rgb(0 0 0 / .08)', '0 4px 10px -2px rgb(0 0 0 / .12)', '0 14px 30px -10px rgb(0 0 0 / .25)'),
               lg=('0 2px 6px rgb(0 0 0 / .1)', '0 8px 20px -4px rgb(0 0 0 / .18)', '0 24px 48px -12px rgb(0 0 0 / .32)'))
FONTS = dict(sans=None, serif='var(--font-serif)', mono='var(--font-mono)')

def _fg(c):
    "Black or white text for a `#rrggbb` background."
    h = c.lstrip('#')
    if len(h) == 3: h = ''.join(x*2 for x in h)
    try: r, g, b = (int(h[i:i+2], 16)/255 for i in (0, 2, 4))
    except ValueError: return None
    return '#0a0a0a' if .2126*r + .7152*g + .0722*b > .55 else '#fafafa'

def _ld(v, f=lambda x: x):
    "A token value: one colour, or `light-dark()` of a (light, dark) pair."
    if isinstance(v, (tuple, list)):
        a, b = map(f, v)
        return None if a is None or b is None else f'light-dark({a}, {b})'
    return f(v)

@dataclass
class Theme:
    "One look: a preset `name`, an accent (`#hex` or a (light, dark) pair), corners, shadows, type, scale and raw tokens."
    name: str = None; primary: str | tuple = None; radius: str = None; shadow: str = None
    font: str = None; display: str = None; scale: float = None; tokens: dict = None

    def vars(self) -> dict:
        "The CSS custom properties this theme sets, beyond its preset."
        d = {}
        if self.primary: d |= {'--primary': _ld(self.primary), '--primary-foreground': _ld(self.primary, _fg), '--ring': _ld(self.primary)}
        if self.radius: d |= dict(zip(('--radius-small', '--radius-medium', '--radius-large'), (f'{x}rem' for x in RADII[self.radius])))
        if self.shadow: d |= dict(zip(('--shadow-small', '--shadow-medium', '--shadow-large'), SHADOWS[self.shadow]))
        if self.font: d['--font-sans'] = FONTS.get(self.font, self.font)
        if self.display: d['--font-display'] = FONTS.get(self.display, self.display) or 'var(--font-sans)'
        for k, v in (self.tokens or {}).items(): d['--' + k.lstrip('-').replace('_', '-')] = v
        return {k: v for k, v in d.items() if v}

    def css(self) -> str:
        "Unlayered `:root` rules, so they beat the preset and Oat's defaults."
        v, sz = self.vars(), f'html{{font-size:{self.scale*100:g}%}}' if self.scale else ''
        return (':root{' + ';'.join(f'{k}:{x}' for k, x in v.items()) + '}' if v else '') + sz

def _theme(o) -> Theme:
    "Normalise `oat=`: True, a preset name, a dict or a `Theme`."
    if isinstance(o, Theme): return o
    if isinstance(o, str): return Theme(name=o)
    if isinstance(o, dict): return Theme(**o)
    return Theme()

# ── Headers and static files ─────────────────────────────────────────────────
@cache
def _read(nm): return (STATIC/nm).read_text()
@cache
def _ver(nm): return hashlib.md5((STATIC/nm).read_bytes()).hexdigest()[:10]
def _src(nm, prefix=PREFIX): return f'{prefix}/{nm}?v={_ver(nm)}'

def oat_hdrs(theme=True, cdn=False, prefix=PREFIX):
    "Head tags for Oat and the fhoat layer; `cdn` pulls Oat from jsDelivr and inlines the layer."
    t = _theme(theme)
    css = (Link(rel='stylesheet', href=oatcss), Style(_read('fhoat.css'))) if cdn else \
          (Link(rel='stylesheet', href=_src('oat.min.css', prefix)), Link(rel='stylesheet', href=_src('fhoat.css', prefix)))
    js = Script(src=oatjs if cdn else _src('oat.min.js', prefix), defer=True)
    own = Style(t.css()) if t.css() else None
    return tuple(o for o in (Meta(name='color-scheme', content='light dark'), *css, own, Script(_read('fhoat.js')), js) if o is not None)

def oat_htmlkw(theme=True, mode='auto'):
    "The `<html>` attrs fhoat.js reads: default theme and mode."
    t = _theme(theme)
    return dict(data_mode=mode) | (dict(data_theme=t.name) if t.name else {})

def serve_oat(app, prefix=PREFIX):
    "Serve the vendored Oat and fhoat files, ahead of fast_app's static catch-all, cached for a year."
    async def oat_file(req):
        nm = req.path_params['fname']
        if nm not in FILES: return Response(status_code=404)
        return FileResponse(STATIC/nm, headers={'Cache-Control': 'public, max-age=31536000, immutable'})
    app.router.routes.insert(0, Route(f'{prefix}/{{fname}}', oat_file, name='fhoat'))
    return app

@delegates(fh_fast_app, keep=True)
def fast_app(*args, oat=True, mode='auto', cdn=False, hdrs=None, htmlkw=None, **kw):
    "fasthtml's `fast_app` with `oat` in place of `pico`: True, a preset name, a dict or a `Theme`."
    if not oat: return fh_fast_app(*args, hdrs=hdrs, htmlkw=htmlkw, **kw)
    t = _theme(oat)
    res = fh_fast_app(*args, pico=False, hdrs=(*oat_hdrs(t, cdn), *(hdrs or ())), htmlkw=oat_htmlkw(t, mode) | (htmlkw or {}), **kw)
    if not cdn: serve_oat(res[0])
    return res

# ── Pico parity ──────────────────────────────────────────────────────────────
def _cls(*c): return ' '.join(o for o in c if o) or None
def _uid(p='ot'): return f'{p}-{uuid.uuid4().hex[:8]}'

@delegates(ft_hx, keep=True)
def Card(*c, header=None, footer=None, cls='', **kw) -> FT:
    "An Oat card: an Article with optional Header and Footer."
    if header: c = (Header(header),) + c
    if footer: c += (Footer(footer),)
    return Article(*c, cls=_cls('card', cls), **kw)

@delegates(ft_hx, keep=True)
def Group(*c, cls='', **kw) -> FT:
    "Joined inputs and buttons: a Fieldset with class `group`."
    return Fieldset(*c, cls=_cls('group', cls), role='group', **kw)

@delegates(ft_hx, keep=True)
def Search(*c, **kw) -> FT:
    "A Form with role `search`."
    return Form(*c, role='search', **kw)

@delegates(ft_hx, keep=True)
def Grid(*c, min=None, cls='', **kw) -> FT:
    "Equal auto-fit columns at least `min` wide (CSS length); each child in a Div."
    c = tuple(o if isinstance(o, list) else Div(o) for o in c)
    return Div(*c, cls=_cls('grid', cls), style=f'--min:{min}' if min else None, **kw)

def Row(*c, cls='', **kw) -> FT:
    "Oat's 12-column row."
    return Div(*c, cls=_cls('row', cls), **kw)

def Col(*c, span=None, offset=None, cls='', **kw) -> FT:
    "A column in a Row spanning `span` of 12."
    return Div(*c, cls=_cls(f'col-{span}' if span else 'col', offset and f'offset-{offset}', cls), **kw)

@delegates(ft_hx, keep=True)
def DialogX(*c, open=None, header=None, footer=None, id=None, **kw) -> FT:
    "An Oat dialog: header, body and footer as its direct children; a backdrop click closes it."
    return Dialog(Header(header) if header else None, Div(*c), Footer(footer) if footer else None, open=open, id=id, closedby='any', **kw)

def DialogOpen(*c, id, cls='', **kw) -> FT:
    "A button that opens dialog `id` as a modal (invoker commands; Oat polyfills them)."
    return Button(*c, commandfor=id, command='show-modal', cls=_cls(cls), **kw)

def DialogClose(*c, cls='outline', **kw) -> FT:
    "A button that closes its dialog."
    return Button(*(c or ('Close',)), type='button', onclick="this.closest('dialog').close()", cls=_cls(cls), **kw)

@delegates(ft_hx, keep=True)
def Container(*c, cls='', **kw) -> FT:
    "A Main with class `container`."
    return Main(*c, cls=_cls('container', cls), **kw)

def OatBusy():
    "Mark the element of a running htmx request `aria-busy`, which Oat draws as a spinner."
    elt = '(event.detail.ctx?.sourceElement || event.detail.elt)'
    return (HtmxOn('beforeRequest', f"{elt}.setAttribute('aria-busy', 'true' )"),
            HtmxOn('afterRequest', f"{elt}.setAttribute('aria-busy', 'false')"))

# ── Oat components ───────────────────────────────────────────────────────────
def _btn(variant, look, size, icon): return dict(data_variant=variant) if variant else {}, (look, size, icon and 'icon')

def Btn(*c, variant=None, look=None, size=None, icon=False, cls='', **kw) -> FT:
    "A button: `variant` secondary|danger, `look` outline|ghost, `size` small|large."
    a, k = _btn(variant, look, size, icon)
    return Button(*c, cls=_cls(*k, cls), **a, **kw)

def ABtn(*c, href='#', variant=None, look=None, size=None, icon=False, cls='', **kw) -> FT:
    "A link drawn as a button."
    a, k = _btn(variant, look, size, icon)
    return A(*c, href=href, cls=_cls('button', *k, cls), **a, **kw)

def Badge(*c, variant=None, cls='', **kw) -> FT:
    "A pill: `variant` secondary|success|warning|danger, or cls `outline`."
    return Span(*c, cls=_cls('badge', cls), data_variant=variant, **kw)

def Alert(*c, title=None, variant=None, **kw) -> FT:
    "A callout: `variant` success|warning|danger|error."
    return Div(Div(Strong(title) if title else None, Div(*c) if c else None), role='alert', data_variant=variant, **kw)

def Field(label, inp, hint=None, error=None, **kw) -> FT:
    "A labelled input with a hint and an error shown when the input is `aria-invalid`."
    return Div(Label(label, inp), Small(hint, data_hint=True) if hint else None, Small(error, cls='error') if error else None, data_field=True, **kw)

def Switch(label, **kw) -> FT:
    "A toggle switch."
    return Label(Input(type='checkbox', role='switch', **kw), label)

def Tabs(*tabs, anchor=None, **kw) -> FT:
    "Tabs from (label, content) pairs; `anchor` deep-links the active tab in the URL hash."
    return Ot_tabs(Div(*[Button(l, role='tab', type='button') for l, _ in tabs], role='tablist'),
                   *[Div(c, role='tabpanel') for _, c in tabs], data_anchor=anchor, **kw)

def _item(o): return o(role='menuitem') if isinstance(o, FT) else Button(o, role='menuitem', type='button')

def Dropdown(trigger, *items, id=None, cls='', **kw) -> FT:
    "A menu under `trigger` (a string or a Button); items are links, buttons or strings."
    id = id or _uid('menu')
    t = trigger(popovertarget=id) if isinstance(trigger, FT) else Button(trigger, popovertarget=id, cls='outline', type='button')
    return Ot_dropdown(t, Menu(*map(_item, items), popover=True, id=id), cls=_cls(cls), **kw)

def Avatar(src=None, initials=None, alt='', size=None, **kw) -> FT:
    "A round avatar: an image or initials; `size` small|large."
    return Figure(Img(src=src, alt=alt) if src else Span(initials), data_variant='avatar', cls=size, **kw)

def Skeleton(n=3, box=False, **kw) -> FT:
    "Loading placeholders: `n` lines, after a box when `box`."
    return Div(Div(role='status', cls='skeleton box') if box else None, *[Div(role='status', cls='skeleton line') for _ in range(n)], **kw)

# ── Page chrome ──────────────────────────────────────────────────────────────
def _svg(body, cls=''):
    "A Lucide icon (ISC) from its inner markup."
    return NotStr(f'<svg class="{cls}" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
                  f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')
_SUN = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2m-7.07-14.07 1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'
_MOON = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'
_AUTO = '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8M12 17v4"/>'
_PALETTE = ('<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>'
            '<circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>'
            '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.65-.75 1.65-1.69 0-.44-.18-.84-.44-1.13-.29-.29-.44-.65-.44-1.12a1.64 1.64 0 0 1 '
            '1.67-1.67h2c3.05 0 5.55-2.5 5.55-5.55C21.97 6.01 17.46 2 12 2z"/>')

def ModeToggle(**kw) -> FT:
    "One button cycling auto, light and dark; the icon shows the current mode."
    return Button(_svg(_AUTO, 'auto'), _svg(_SUN, 'light'), _svg(_MOON, 'dark'), type='button', onclick='fhoat.cycle()',
                  cls='ghost icon small ot-mode', aria_label='Colour mode: auto, light or dark', **kw)

def ThemePicker(themes=None, id='ot-themes', **kw) -> FT:
    "A swatch menu that sets and remembers the reader's theme."
    sw = [Button(type='button', role='menuitem', cls='ot-swatch', style=f'--sw:{c}', aria_label=n, title=n, onclick=f"fhoat.theme('{n}')")
          for n, c in (themes or THEMES).items()]
    return Ot_dropdown(Button(_svg(_PALETTE), popovertarget=id, type='button', cls='ghost icon small', aria_label='Theme'),
                       Div(*sw, popover=True, id=id, cls='ot-swatches'), **kw)

def _link(o): return A(o[0], href=o[1]) if isinstance(o, tuple) else o

def Navbar(brand, *links, end=None, href='/', cls='', **kw) -> FT:
    "A sticky glass bar: brand, links as (text, href) or FT, then `end` items (default: mode toggle)."
    end = (ModeToggle(),) if end is None else (end if isinstance(end, (tuple, list)) else (end,))
    return Header(Nav(A(brand, href=href, cls='brand'), Ul(*[Li(_link(l)) for l in links]) if links else None,
                      Div(*end, cls='end')), cls=_cls('ot-nav', cls), **kw)

def Hero(title, *c, sub=None, eyebrow=None, actions=(), cls='', **kw) -> FT:
    "A centred page opener: eyebrow, title, subtitle, then actions."
    return Section(Span(eyebrow, cls='eyebrow') if eyebrow else None, H1(title), P(sub) if sub else None, *c,
                   Div(*actions, cls='hstack') if actions else None, cls=_cls('hero', cls), **kw)

def PageFooter(*c, cls='', **kw) -> FT:
    "A quiet page footer."
    return Footer(Div(*c), cls=_cls('ot-footer', cls), **kw)

# ── Toasts ───────────────────────────────────────────────────────────────────
def _toast(msg, title, variant, **o): return dict(msg=msg, title=title, variant=variant or 'info') | o

def Toast(msg, title=None, variant=None, **opts) -> FT:
    "A script that shows a toast where it lands: a page or an htmx swap; opts: placement, duration."
    return Script(f'fhoat.toast({json.dumps(_toast(msg, title, variant, **opts))})')

def toast_hdr(msg, title=None, variant=None, **opts):
    "An `HX-Trigger` header that shows a toast after an htmx request."
    return HtmxResponseHeaders(trigger=json.dumps(dict(toast=_toast(msg, title, variant, **opts))))
