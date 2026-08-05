import ujson as json
from fastcore.xml import *
from fastcore.net import urlread
from fasthtml.common import *
from fasthtml.xtend import On, Now, Surreal, Script, Style
from fasthtml.components import Ot_dropdown, Dialog, Menu
from fastcore.all import timed_cache, ifnone, NotStr, globtastic, Path, AttrDict
from itertools import islice, cycle
from .cfg import cfg as s, RouteOverrides as r, not_prod
from .icons import lc_icon, lc_sprites, lc_sprite_nms
from .utils import loadX

__all__ = ['landing', 'welcome_page', 'placeholder', 'navbar', 'theme_switcher', 'logout', 'mode_switcher',
           'svg_img', 'montage', 'typewriter', 'base', 'Badge', 'BadgeT', 'BadgePresetsT', 'PresetsT',
           'welcome', 'not_found', 'email_template', 'main', 'themes', 'github_star', 'stringify', 'sprites', 'rendered',
           'ButtonT', 'TextT', 'ThemeRadii', 'ThemeShadows', 'ThemeFont', 'NavBarT', 'THEMES',
           'LabelInput', 'LabelTextArea', 'LabelSelect', 'modal', 'CmdPalette', 'asset_js', 'asset_css', 'vendor_js', 'vlink',
           'vendor_hdrs']

def stringify(o):
    'Join class fragments (str | list | tuple, arbitrarily nested) into one class string.'
    if isinstance(o, (list, tuple)): return ' '.join(filter(None, (stringify(i) for i in o)))
    return o or ''

# ── Oat-flavoured style vocabularies (franken/tailwind replacements) ─────────
class ButtonT:
    primary, secondary, default = 'button', 'button secondary', 'button outline'
    ghost, danger, text = 'button ghost', 'button danger', 'link-btn'
    xs, sm, lg, icon = 'small', 'small', 'large', 'button icon ghost'

class TextT:
    muted = gray = 'text-light'
    xs, sm, lg, xl, lead = 'text-xs', 'text-sm', 'text-lg', 'text-xl', 'text-lead'
    bold, medium, italic, mono = 'font-bold', 'font-medium', 'italic', 'font-mono'
    center, left, right = 'align-center', 'align-left', 'align-right'
    break_ = 'break-words'

class ThemeRadii: none, sm, md, lg = 'radii-none', 'radii-sm', 'radii-md', 'radii-lg'
class ThemeShadows: none, sm, md, lg = 'shadows-none', 'shadows-sm', 'shadows-md', 'shadows-lg'
class ThemeFont: default, sm, lg = 'font-base', 'font-sm', 'font-lg'

THEMES = [('theme-paper', '#8a1f11'),
          ('theme-zinc', '#71717a'), ('theme-slate', '#64748b'), ('theme-stone', '#78716c'),
          ('theme-red', '#dc2626'), ('theme-rose', '#e11d48'), ('theme-orange', '#ea580c'),
          ('theme-green', '#16a34a'), ('theme-blue', '#2563eb'), ('theme-violet', '#7c3aed'),
          ('theme-yellow', '#ca8a04')]

class PresetsT:
    animate_shine = 'shadow-md'
    shine = 'bg-card %s p-2' % animate_shine
    primary = 'bg-primary'
    transparent = 'bg-transparent backdrop-blur'
    glass = stringify([transparent, animate_shine])
    standout = 'bg-muted muted-border %s relative p-2' % animate_shine

class BadgeT:
    md, sm = 'px-2 py-1', 'chip-sm'
    current, primary = 'bg-secondary', 'bg-primary'
    rounded, pill = 'rounded-md', 'rounded-full'
    red, yellow, green, gray = 'chip-red', 'chip-yellow', 'chip-green', 'chip-gray'
    blue, indigo, purple, pink = 'chip-blue', 'chip-indigo', 'chip-purple', 'chip-pink'
    invert = 'inout'

class BadgePresetsT:
    default = stringify([BadgeT.current, BadgeT.md, BadgeT.rounded])
    primary = stringify([BadgeT.primary, BadgeT.md, BadgeT.rounded])
    sm = stringify([BadgeT.current, BadgeT.sm, BadgeT.rounded])
    primary_sm = stringify([BadgeT.primary, BadgeT.sm, BadgeT.rounded])
    sm_strike = stringify([BadgeT.gray, BadgeT.sm, BadgeT.rounded, 'line-through'])

def Badge(*c, cls=BadgePresetsT.default, **kwargs):
    return Span(c, cls=(stringify(cls), 'inline-flex text-xs'), **kwargs)

# ── Form helpers (LabelInput et al., minus monsterui) ────────────────────────
def LabelInput(label, id=None, cls='', lbl_cls='', **kw):
    kw.setdefault('name', id)
    return Label(label, Input(id=id, cls=stringify(cls), **kw), cls=stringify(lbl_cls), for_=id)

def LabelTextArea(label, id=None, cls='', lbl_cls='', input_cls='', value='', **kw):
    kw.setdefault('name', id)
    return Label(label, Textarea(value, id=id, cls=stringify((cls, input_cls)), **kw), cls=stringify(lbl_cls), for_=id)

def LabelSelect(*options, label='', id=None, cls='', lbl_cls='', **kw):
    kw.setdefault('name', id)
    return Label(label, Select(*options, id=id, cls=stringify(cls), **kw), cls=stringify(lbl_cls), for_=id)

# ── Modal / command palette (native <dialog>, no franken JS) ─────────────────
def modal(*content, id='modal', dialog_cls='', remove_on_close=True, **kw):
    'Native <dialog> that opens itself when inserted (htmx-friendly) and closes on backdrop click.'
    rm = 'd.addEventListener("close",()=>d.remove(),{once:true});' if remove_on_close else ''
    js = ('(function(){const d=document.getElementById("%s");if(!d||d._init)return;d._init=1;'
          'if(!d.open)d.showModal();d.addEventListener("click",e=>{if(e.target===d)d.close();});%s})();') % (id, rm)
    return Dialog(Div(*content), Script(js), id=id, cls=stringify(dialog_cls))

def CmdPalette(*items, id='cmd-palette', placeholder='Type to search…', hotkey='k'):
    'Lightweight command palette: Ctrl/Cmd+hotkey opens a dialog with a filter input over `items`.'
    js = ('(function(){const d=document.getElementById("%s");if(!d||d._init)return;d._init=1;'
          'const i=d.querySelector("input"),l=[...d.querySelectorAll("menu li")];'
          'i.addEventListener("input",()=>{const q=i.value.toLowerCase();'
          'l.forEach(x=>x.style.display=x.textContent.toLowerCase().includes(q)?"":"none");});'
          'document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key==="%s")'
          '{e.preventDefault();d.open?d.close():(d.showModal(),i.focus());}});'
          'd.addEventListener("click",e=>{if(e.target===d)d.close();});})();') % (id, hotkey)
    return Dialog(Input(type='search', placeholder=placeholder), Menu(*[Li(i) for i in items]),
                  Script(js), id=id, cls='cmd-palette')

# ── App chrome ───────────────────────────────────────────────────────────────
#
# The chrome is the same markup on nearly every response. Building it costs four times
# what serialising it costs — a navbar is a few hundred FT objects, each one a __setattr__
# per attribute and an isinstance sweep per child — and then fasthtml walks the finished
# tree again looking for hx- targets to resolve.
#
# Rendered once and kept as a NotStr, all three go away: no objects to build, nothing to
# serialise, and the walk skips it because it is no longer a tree. What is left is a string
# concatenated into the page.
#
# Only for markup that is genuinely invariant. Anything that can differ has to be in the
# key, which is why `navbar` keys on the star count and the nav list and not just on `usr`.
_chrome = {}

def rendered(key, build):
    'Serialise `build()` once per distinct `key` and hand back the same NotStr after that.'
    v = _chrome.get(key)
    if v is None: v = _chrome[key] = NotStr(to_xml(build()))
    return v

def logout(usr=None):
    if not usr or not r.lgt: return None
    btn_cls = f'{ButtonT.icon} {ButtonT.sm} text-danger'
    return Div(A(lc_icon('log-out'), href=r.lgt, cls=btn_cls, id='logout-btn'))

def login(): return Div(A('Login', hx_get=r.lgn, hx_target='body', hx_swap='beforeend', cls=f'{ButtonT.primary} {ButtonT.xs} lgn-btn'))

_GH_SVG = '<svg height="16" width="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'

@timed_cache(seconds=3600)
def _fetch_stars(repo):
    try: n = urlread(f'https://api.github.com/repos/{repo}', return_json=True, timeout=3).get('stargazers_count', 0)
    except: n=0
    return f'{n / 1000:.1f}k' if n >= 1000 else str(n)

def _stars(repo=None):
    repo = ifnone(repo, s.github_repo)
    return _fetch_stars(repo) if repo else None

def github_star(repo=None):
    repo = ifnone(repo, s.github_repo)
    if not repo: return None
    stars = _fetch_stars(repo)
    inner = [NotStr(_GH_SVG)]
    if stars: inner.append(Span(stars))
    return A(*inner, href=f'https://github.com/{repo}', target='_blank', rel='noopener noreferrer', cls='gh-pill')

class NavBarT:
    default = 'navbar'
    glass = 'navbar navbar-glass'
    shining = 'navbar navbar-shining'

def nav_link(txt, href, tag=None, gated=False, usr=None):
    inner = [Span(txt), Span(tag, cls='nav-tag') if tag else None]
    # A gated link would otherwise bounce a signed-out visitor to the login route, which
    # renders as a bare modal on an otherwise empty page. Open it in place instead,
    # the same way the Login button does.
    if gated and not usr:
        # href stays real so the link still works with JS off; htmx cancels it otherwise
        return A(*inner, href=href, cls='nav-pill',
                 hx_get=r.lgn, hx_target='body', hx_swap='beforeend')
    # unboosted: a block brings its own <script src> and <link>, and a real navigation is
    # the one thing guaranteed to run them
    return A(*inner, href=href, cls='nav-pill', hx_boost='false')

def nav_links(usr=None):
    if not r.nav: return None
    return Div(*[nav_link(*x, usr=usr) for x in r.nav], cls='flex items-center gap-2')

def navbar(usr=None, title='', style=NavBarT.default, cls='w-full sticky', mobile_cls=''):
    # `usr` only ever reaches this as a boolean — the bar shows a log-out icon or a login
    # button, never a name — so two signed-in readers get the same bar and the same string.
    # The star count is in the key because _fetch_stars refreshes hourly behind us.
    return rendered(('nav', bool(usr), title, style, cls, mobile_cls, _stars(), r.lgn, r.lgt, tuple(r.nav)),
                    lambda: _navbar(usr, title, style, cls, mobile_cls))

def _navbar(usr=None, title='', style=NavBarT.default, cls='w-full sticky', mobile_cls=''):
    usr_ok = bool(usr)
    inc_fnt_sz, inc_mode_sw, inc_th_sw, inc_avtr = True, True, not_prod(), usr_ok
    sep = Div('|', cls='text-light text-xl px-2')
    cmps = [(font_size_switcher(), inc_fnt_sz), (mode_switcher(), inc_mode_sw), (theme_switcher(), inc_th_sw),
            (sep, True), (github_star(), True), (logout(usr), inc_avtr), (login(), not inc_avtr)]
    lft = Div(A(H4(title, cls='m-0'), href='/'), nav_links(usr), cls='flex items-center gap-4')
    rgt = Div(*[c for c, inc in cmps if inc], cls='flex items-center gap-1')
    return Div(Nav(lft, rgt, cls=mobile_cls), cls=[style, cls])

def theme_switcher(cls='relative', heading='Customise', sub_heading='theme selection'):
    swatches = Div(*[Button(type='button', cls='swatch', style=f'background:{c}',
                            title=t.removeprefix('theme-'), onclick=f"setTheme('{t}')") for t, c in THEMES],
                   cls='swatch-grid')
    def opts(setter, pairs):
        return Div(*[Button(lbl, type='button', cls='button outline small', onclick=f"{setter}('{v}')")
                     for v, lbl in pairs], cls='opt-row')
    menu = Div(H3(heading), P(sub_heading, cls='text-light text-sm'), swatches,
               P('Corners', cls='text-sm font-medium mb-1'),
               opts('setRadii', [(ThemeRadii.none, 'Sharp'), (ThemeRadii.sm, 'Subtle'), (ThemeRadii.md, 'Round'), (ThemeRadii.lg, 'Rounder')]),
               P('Shadows', cls='text-sm font-medium mb-1'),
               opts('setShadows', [(ThemeShadows.none, 'Flat'), (ThemeShadows.sm, 'Soft'), (ThemeShadows.md, 'Medium'), (ThemeShadows.lg, 'Deep')]),
               popover=True, id='theme-menu', cls='theme-menu card')
    btn = Button(lc_icon('palette', 20), type='button', popovertarget='theme-menu',
                 cls=f'{ButtonT.icon} {ButtonT.sm}', aria_label='Customise theme')
    return Ot_dropdown(btn, menu, cls=cls)

def mode_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(Div(lc_icon('sun-moon', 20), On('setMode("dark");'), cls=[btn_cls], id='auto-mode-btn'),
               Div(lc_icon('moon', 20), On('setMode("light");'), cls=btn_cls, id='dark-mode-btn'),
               Div(lc_icon('sun', 20), On('setMode("auto");'), cls=btn_cls, id='light-mode-btn'))

def font_size_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(
        Div(lc_icon('case-lower', 20), On('setFont("%s");' % ThemeFont.default), cls=[btn_cls], id='sm-font-btn'),
        Div(lc_icon('case-lower', 24), On('setFont("%s");' % ThemeFont.lg), cls=[btn_cls], id='lg-font-btn'),
        Div(lc_icon('case-lower', 28), On('setFont("%s");' % ThemeFont.sm), cls=[btn_cls], id='xl-font-btn'))

def svg_img(svg_path, cls='', w=16, h=16, outer_cls='', loading='lazy', **kw):
    return Div(Img(src=f'/{svg_path}', cls=f'inout {cls}', width=w, height=h, loading=loading, **kw),
               cls=f'inline-flex justify-center {outer_cls}')

def placeholder(message='placeholder text', back_link='/', back_text='Go Back Home'):
    btn_cls, txt_cls = f'{ButtonT.primary} {ButtonT.sm}', f'{TextT.lead} mb-4'
    return Div(P(message, cls=txt_cls), A(back_text, href=back_link, cls=btn_cls), cls=TextT.center)

@timed_cache(seconds=3600)
def montage(svg_paths, cols_sm=3, cols_md=5, cols_lg=6, rows=8, fill_screen=True, cls=PresetsT.primary, svg_cls=None):
    l=len(svg_paths or [])
    if not l: return None
    svg_cls, outer_cls = ifnone(svg_cls, 'size-4-6'), f'border-2-dotted m-2 {PresetsT.standout}'
    svgs = islice(cycle(svg_paths.map(svg_img, cls=svg_cls, outer_cls=outer_cls)), int(l*rows) if fill_screen else l)
    return Div(*svgs, cls=stringify(('montage', cls)))

@timed_cache(seconds=3600)
def typewriter(stat_txt=None, dyn_txt_lst=None, type_sp=250, del_sp=100, pause_end=1000,
               pause_start=500, txt_cls=None, cls=f'm-4 p-4 min-w-64 active'):
    stat_txt = ifnone(stat_txt, f' {s.typwrtr_stat_txt}')
    dyn_txt_lst = ifnone(dyn_txt_lst, s.typwrtr_dyn_txt.split(','))
    txt_cls = ifnone(txt_cls, f'{TextT.lg} {TextT.bold}')
    dyn_con = Span('', id='typewriter', cls='line border-r-2 border-current blink')
    code = f'let a={dyn_txt_lst},i=0,j=0,d=false,t;' \
           'function w(){if(!e)return;const s=a[i];e.text(d?s.slice(0,j):s.slice(0,j+1));' \
           f'if(!d&&j==s.length-1)setTimeout(()=>(d=true,w()),{pause_end});' \
           f'else if(d&&j==0){{d=false;i=(i+1)%a.length;setTimeout(w,{pause_start});}}' \
           f'else{{t=setTimeout(w,d?{del_sp}:{type_sp});j+=d?-1:1;}}' \
           '}w();'
    return Div(P(dyn_con, Span(stat_txt), cls=txt_cls), Now(code, sel='#typewriter'), cls=cls)

@timed_cache(seconds=3600)
def welcome_page(img_dir=s.svg, content=None, title=None, cls=None, cont_cls=None):
    img_paths = globtastic(img_dir, file_re='.svg|.png|.jpg')
    cls = ifnone(cls, 'align-center backdrop-blur-xl p-6 border border-current')
    cont_cls = ifnone(cont_cls, 'min-h-screen flex items-center justify-center mt-8 max-w-xs mx-auto')
    t = Title(title) if title else None
    m = Div(montage(img_paths), cls='overflow-hidden pos-cover mt-10 opacity-60') if img_paths else None
    ftr = P(s.ftr_txt, cls='text-xs mt-4')
    con = Div(Div(H2(title, cls=PresetsT.shine), typewriter(), content, ftr, cls=cls), cls=stringify(('container', cont_cls)))
    return t, Section(m, con, cls='relative')

def landing(content, title=s.app_nm, usr=None):
    return base(welcome_page(content=content, title=title), usr=usr, style=NavBarT.glass)

def sprites():
    'The symbol sheet, serialised once per set of seeded names.'
    # keyed on the names themselves: lc_icon seeds a new one the first time a fragment asks
    # for an icon nothing had used yet, and the sheet has to grow to match
    return rendered(('sprites', tuple(lc_sprite_nms())), lc_sprites)

def base(content=None, usr=None, title=s.app_nm, sh=s.app_sh, style=NavBarT.glass, **kwargs):
    return Title(title), Div(sprites(), navbar(usr=usr, title=sh, style=style), main(content, **kwargs))

def main(content=None, cls=None, **kw):
    return Div(content if content else None, cls=stringify(['w-full', cls]), id='main-content', **kw)

def email_template(content, title=s.app_nm, usr=None):
    if isinstance(usr, dict): content = f'Hello {usr.get("usr_name", "Vedic Reader Patron")} \n\n {content}'
    header = Div(cls='bg-primary p-4')(H1(title, cls='text-lg font-bold'))
    body = Div(cls='p-4')(content)
    footer = Div(cls='bg-secondary p-2 text-xs')('This email was sent by our team.')
    return Div(cls='border rounded-md overflow-hidden')(header, body, footer)

def welcome(usr=None): return landing(placeholder(f'Welcome to {s.app_nm}'), usr=usr)
def not_found(): return landing(placeholder("The page you're looking for doesn't exist or has been moved."))

def _nosleep(): return vendor_js('nosleep.min.js', defer=True)

def vendor_hdrs():
    '''What `fast_app(default_hdrs=True)` would put in the head, served from static/vendor.

    Every one of these was a separate origin — two jsdelivr paths, cdnjs, and the font CSS
    that chains to a fourth host for the files it names. A cold visit paid a DNS lookup, a
    TLS handshake and a round trip before it could finish the head, and three of the URLs
    were `@latest` or `@main`, which cannot be cached for long and can change under a
    deployed app. Locally they are the connection the browser already has, behind the
    immutable mount and a content-hashed ?v=.

    Refresh with tools/vendor_fetch.py. Order follows fasthtml's `def_hdrs` so nothing
    that expects htmx to be defined runs before it is.'''
    return [Meta(charset='utf-8'),
            Meta(name='viewport', content='width=device-width, initial-scale=1, viewport-fit=cover'),
            vendor_js('htmx.min.js'), vendor_js('fasthtml.js'),
            vendor_js('surreal.js'), vendor_js('css-scope-inline.js'),
            vendor_js('htmx-ext-preload.js'),
            Link(rel='stylesheet', href=vlink('/static/vendor/fonts.css'))]

_css, _js = Path(__file__).parent / 'theme.css', Path(__file__).parent / 'theme.js'
_assets = Path('static') / 'assets'

def vlink(path):
    'Content-hashed URL (?v=) so immutable caching busts when the file changes; plain path if unhashable.'
    try: return vurl(path)
    except Exception: return path

def _asset(nm, content):
    'Write a derived asset if its content changed; None on read-only filesystems (serverless).'
    try:
        p = _assets / nm
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_text() != content: p.write_text(content)
        return p
    except OSError: return None

def asset_js(path, **kw):
    'Script tag for a package .js file — served from static/assets when writable, inlined when not.'
    p = Path(path)
    c = loadX(p)
    return Script(src=vlink(f'/static/assets/{p.name}'), **kw) if _asset(p.name, c) else Script(c, **kw)

def asset_css(path, **kw):
    'Link tag for a block-local .css file, so a block can ship its own styles instead of adding to the core theme.'
    p = Path(path)
    c = loadX(p)
    return Link(rel='stylesheet', href=vlink(f'/static/assets/{p.name}'), **kw) if _asset(p.name, c) else Style(c, **kw)

def vendor_js(nm, **kw): return Script(src=vlink(f'/static/vendor/{nm}'), **kw)

@timed_cache(seconds=3600)
def themes(color='paper', radii=ThemeRadii.md, shadows=ThemeShadows.sm, font=ThemeFont.default):
    radii, shadows = getattr(radii, 'value', radii), getattr(shadows, 'value', shadows)
    d = AttrDict(mode='auto', theme='theme-%s' % color, radii=radii, shadows=shadows, font=font)
    j = loadX(_js, dict(state=json.dumps(d), theme=d.theme), r'\{\{__(\w+)__\}\}')
    c = loadX(_css)
    oat = [Link(rel='stylesheet', href=vlink('/static/vendor/oat.min.css')),
           Script(src=vlink('/static/vendor/oat.min.js'), type='module')]
    thm = [Link(rel='stylesheet', href=vlink('/static/assets/theme.css')) if _asset('theme.css', c) else Style(c),
           Script(src=vlink('/static/assets/theme.js')) if _asset('theme.js', j) else Script(j)]
    return oat + thm + [_nosleep(), Surreal("me('body').remove_class('hidden');")]
