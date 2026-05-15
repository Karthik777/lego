import ujson as json
from fasthtml.common import *
from fastcore.net import urlread
from itertools import islice, cycle
from monsterui.all import *
from monsterui.foundations import *
from monsterui.core import ThemeRadii, ThemeShadows
from .cfg import cfg as s, RouteOverrides as r, not_prod
from .icons import icon_auto
from .utils import loadX

__all__ = ['landing', 'welcome_page', 'placeholder', 'navbar', 'theme_switcher', 'logout', 'mode_switcher',
           'svg_img', 'montage', 'typewriter', 'base', 'Badge', 'BadgeT', 'BadgePresetsT', 'PresetsT',
           'welcome', 'not_found', 'email_template', 'main', 'themes', 'github_star']

class PresetsT:
    animate_shine = 'shadow-md'
    shine = 'bg-card %s p-2' % animate_shine
    primary = 'bg-primary text-primary-foreground'
    transparent = 'bg-transparent backdrop-blur-lg'
    glass = stringify([transparent, animate_shine])
    standout = 'bg-muted muted-border %s relative p-2' % animate_shine

class BadgeT:
    md, sm = 'px-2 py-1', 'px-1.5 py-0.5'
    current, primary = 'bg-secondary text-secondary-foreground', 'bg-primary text-primary-foreground'
    rounded, pill = 'rounded-md', 'rounded-full'
    red = 'bg-red-50 text-red-900 dark:bg-red-400/10 dark:text-red-400'
    yellow = 'bg-yellow-50 text-yellow-900 dark:bg-yellow-400/10 dark:text-yellow-500'
    green = 'bg-green-50 text-green-900 dark:bg-green-500/10 dark:text-green-500'
    gray = 'bg-gray-50 text-gray-900 dark:bg-gray-400/10 dark:text-gray-400'
    blue = 'bg-blue-50 text-blue-900 dark:bg-blue-400/10 dark:text-blue-400'
    indigo = 'bg-indigo-50 text-indigo-900 dark:bg-indigo-400/10 dark:text-indigo-400'
    purple = 'bg-purple-50 text-purple-900 dark:bg-purple-400/10 dark:text-purple-400'
    pink = 'bg-pink-50 text-pink-900 dark:bg-pink-400/10 dark:text-pink-400'
    invert = 'dark:invert'

class BadgePresetsT:
    default = stringify([BadgeT.current, BadgeT.md, BadgeT.rounded])
    primary = stringify([BadgeT.primary, BadgeT.md, BadgeT.rounded])
    sm = stringify([BadgeT.current, BadgeT.sm, BadgeT.rounded])
    primary_sm = stringify([BadgeT.primary, BadgeT.sm, BadgeT.rounded])
    sm_strike = stringify([BadgeT.gray, BadgeT.sm, BadgeT.rounded, 'line-through'])

def Badge(*c, cls=BadgePresetsT.default, **kwargs):
    return Span(c, cls=(stringify(cls), 'inline-flex items-center text-xs'), **kwargs)

def logout(usr=None):
    if not usr or not r.lgt: return None
    btn_cls = f'{ButtonT.ghost} {ButtonT.sm} text-destructive'
    return Div(A(UkIcon('log-out'), href=r.lgt, cls=btn_cls, id='logout-btn'))

def login(): return Div(A('Login', hx_get=r.lgn, hx_target='body', hx_swap='beforeend', cls=f'uk-btn {ButtonT.primary} {ButtonT.xs} lgn-btn'))

_GH_SVG = '<svg height="16" width="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'

@timed_cache(seconds=3600)
def _fetch_stars(repo):
    n = urlread(f'https://api.github.com/repos/{repo}', return_json=True, timeout=3).get('stargazers_count', 0)
    print(n)
    return f'{n / 1000:.1f}k' if n >= 1000 else str(n)

def github_star(repo=None):
    repo = ifnone(repo, s.github_repo)
    if not repo: return None
    stars = _fetch_stars(repo)
    pill_cls = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs hover:bg-zinc-800 transition-colors no-underline'
    inner = [NotStr(_GH_SVG)]
    if stars: inner.append(Span(stars))
    return A(*inner, href=f'https://github.com/{repo}', target='_blank', rel='noopener noreferrer', cls=pill_cls)

class NavBarT:
    default = 'top-0 right-0 left-0 z-50 border-b border-muted bg-background'
    glass = 'top-0 right-0 left-0 z-50 bg-background/80 backdrop-blur-md border-b border-muted/50'
    shining = 'top-0 right-0 left-0 z-50 bg-background shadow-md border-b border-muted'

def navbar(usr=None, title='', style=NavBarT.default, cls='w-full sticky', mobile_cls=''):
    usr_ok = bool(usr)
    inc_fnt_sz, inc_mode_sw, inc_th_sw, inc_avtr = True, True, not_prod(), usr_ok
    sep = Div('|', cls=f'{ButtonT.icon} {ButtonT.sm} {TextT.gray} {TextT.xl}')
    cmps = [(font_size_switcher(), inc_fnt_sz), (mode_switcher(), inc_mode_sw), (theme_switcher(), inc_th_sw),
            (sep, True), (github_star(), True), (logout(usr), inc_avtr), (login(), not inc_avtr)]
    lft = A(H4(title, cls='m-0'), href='/')
    rgt = Div(*[c for c, inc in cmps if inc], cls='flex items-center gap-1')
    return Div(Nav(lft, rgt, cls=f'pl-4 pr-2 py-1 justify-between flex items-center {mobile_cls}'), cls=[style, cls])

def theme_switcher(cls='uk-position-relative', heading='Customise', sub_heading='theme selection'):
    h = H3(heading, cls='m-2')
    sub = P(sub_heading, cls=(TextT.muted, 'mt-2 p-2'))
    con = [h, sub, ThemePicker(mode=False)]
    return Div(Div(
        Div(UkIcon('palette'), cls=(ButtonT.icon, ButtonT.sm)),
        CardBody(*con, cls='dropdown-content w-96', data_uk_dropdown='mode: click; pos: bottom-right; offset: 8')),
        cls=f'{cls}')

def mode_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(Div(icon_auto(w=20, h=20), On('setMode("dark");'), cls=[btn_cls], id='auto-mode-btn'),
               Div(UkIcon('moon'), On('setMode("light");'), cls=btn_cls, id='dark-mode-btn'),
               Div(UkIcon('sun'), On('setMode("auto");'), cls=btn_cls, id='light-mode-btn'))

def font_size_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(
        Div(UkIcon('case-lower', height=20, width=20), On('setFont("%s");' % ThemeFont.default), cls=[btn_cls], id='sm-font-btn'),
        Div(UkIcon('case-lower', height=24, width=24), On('setFont("%s");' % 'uk-font-lg'), cls=[btn_cls], id='lg-font-btn'),
        Div(UkIcon('case-lower', height=28, width=28), On('setFont("%s");' % ThemeFont.sm), cls=[btn_cls], id='xl-font-btn'))

def svg_img(svg_path, cls='', w=16, h=16, outer_cls='', loading='lazy', **kw):
    return Div(Img(src=f'/{svg_path}', cls=f'inout {cls}', width=w, height=h, loading=loading, **kw),
               cls=f'inline-flex items-center justify-center {outer_cls}')

def placeholder(message='placeholder text', back_link='/', back_text='Go Back Home'):
    btn_cls, txt_cls = f'{ButtonT.primary} {ButtonT.sm} uk-btn', f'{TextT.lead} mb-4'
    return Div(P(message, cls=txt_cls), A(back_text, href=back_link, cls=btn_cls), cls=TextT.center)

@timed_cache(seconds=3600)
def montage(svg_paths, cols_sm=3, cols_md=5, cols_lg=6, rows=8, fill_screen=True, cls=BackgroundT.primary, svg_cls=None):
    l=len(svg_paths or [])
    if not l: return None
    svg_cls, outer_cls = ifnone(svg_cls, f'size-4/6'), f'border-2 border-current border-dotted m-2 {PresetsT.standout}'
    svgs = islice(cycle(svg_paths.map(svg_img, cls=svg_cls, outer_cls=outer_cls)), int(l*rows) if fill_screen else l)
    return Grid(*svgs, cols_sm=cols_sm, cols_md=cols_md, cols_lg=cols_lg, cols_min=2, cols_xl=cols_lg, cls=cls)

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
    cls = ifnone(cls, 'text-center backdrop-blur-xl p-4 sm:p-8 border border-current')
    cont_cls = ifnone(cont_cls, 'min-h-screen flex items-center justify-center mt-8 max-w-80')
    t = Title(title) if title else None
    m = Div(montage(img_paths), cls='overflow-hidden uk-position-cover mt-10 opacity-60') if img_paths else None
    ftr = P(s.ftr_txt, cls='text-xs mt-4')
    con = Container(Div(H2(title, cls=PresetsT.shine), typewriter(), content, ftr, cls=cls), cls=cont_cls)
    return t, Section(m, con)

def landing(content, title=s.app_nm, usr=None):
    return base(welcome_page(content=content, title=title), usr=usr, style=NavBarT.glass)

def base(content=None, usr=None, title=s.app_nm, sh=s.app_sh, style=NavBarT.glass, **kwargs):
    return Title(title), Div(navbar(usr=usr, title=sh, style=style), main(content, **kwargs))

def main(content=None, cls=None, **kw):
    return Div(content if content else None, cls=stringify(['uk-width-1-1', cls]), id='main-content', **kw)

def email_template(content, title=s.app_nm, usr=None):
    if isinstance(usr, dict): content = f'Hello {usr.get("usr_name", "Vedic Reader Patron")} \n\n {content}'
    header = Div(cls='bg-primary p-4 text-white')(H1(title, cls='text-lg font-bold'))
    body = Div(cls='p-4')(content)
    footer = Div(cls='bg-secondary p-2 text-white text-xs')('This email was sent by our team.')
    return Div(cls='border border-muted rounded-md overflow-hidden')(header, body, footer)

def welcome(usr=None): return landing(placeholder(f'Welcome to {s.app_nm}'), usr=usr)
def not_found(): return landing(placeholder("The page you're looking for doesn't exist or has been moved."))

def _tw(): return Script(src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4')
def _ujs(): return Script(src='https://cdn.jsdelivr.net/npm/underscore@1.13.7/underscore-umd-min.js')
def _nosleep(): return Script(src='https://cdnjs.cloudflare.com/ajax/libs/nosleep/0.12.0/NoSleep.min.js', defer=True)

def _franken(): return [
    Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/franken-ui@2.1.0-next.16/dist/css/core.min.css'),
    Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/franken-ui@2.1.0-next.16/dist/css/utilities.min.css'),
    Script(type='module', src='https://cdn.jsdelivr.net/npm/franken-ui@2.1.0-next.16/dist/js/core.iife.js'),
    Script(type='module', src='https://cdn.jsdelivr.net/npm/franken-ui@2.1.0-next.16/dist/js/icon.iife.js'),
    ]

_css, _js = Path(__file__).parent / 'theme.css', Path(__file__).parent / 'theme.js'

@timed_cache(seconds=3600)
def themes(color='zinc', radii=ThemeRadii.md, shadows=ThemeShadows.sm, font=ThemeFont.default):
    d = AttrDict(mode='auto', theme='uk-theme-%s' % color, radii=radii.value, shadows=shadows, font=font)
    j = loadX(_js, dict(state=json.dumps(d), theme=d.theme), r'\{\{__(\w+)__\}\}')
    return _franken() + [_tw(), _ujs(), _nosleep(), Style(loadX(_css)), Script(j), Surreal("me('body').remove_class('hidden');")]
