from fasthtml.common import *
from itertools import islice, cycle
from monsterui.all import *
from monsterui.foundations import *
from .cfg import cfg as s, RouteOverrides as r, is_prod
from .icons import icon_auto
from .cache import cache

__all__ = ['landing', 'welcome_page', 'placeholder', 'navbar', 'theme_switcher', 'logout', 'mode_switcher',
           'svg_img', 'montage', 'typewriter', 'base', 'Badge', 'BadgeT', 'BadgePresetsT', 'PresetsT',
           'welcome', 'not_found','email_template', 'main', 'adaptive_layout', 'adaptive_layout_responsive',
           'layout_with_featured']

class PresetsT:
    animate_shine = 'shadow-md'
    shine = 'bg-card %s' % animate_shine
    primary = 'bg-primary text-primary-foreground'
    transparent = 'bg-transparent backdrop-blur-lg'
    glass = stringify([transparent, animate_shine])
    standout = 'bg-muted muted-border %s relative' % animate_shine

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
    sm_strike = stringify([BadgeT.gray, BadgeT.sm, BadgeT.rounded, 'line-through'])

def Badge(*c, cls=BadgePresetsT.default, **kwargs):
    return Span(c,cls=('inline-flex items-center text-xs font-medium', stringify(cls)),**kwargs)

def logout(usr=None):
    if not usr or not r.lgt: return None
    btn_cls = f'{ButtonT.ghost} {ButtonT.sm} text-destructive'
    return Div(A(UkIcon('log-out'), href=r.lgt, cls=btn_cls, id='logout-btn'))

def login(): return Div(A('Login', href=r.lgn, cls=f'uk-btn {ButtonT.primary} {ButtonT.xs} lgn-btn'))
class NavBarT:
    default = 'top-0 right-0 left-0 z-50 border-b border-muted bg-background'
    glass = 'top-0 right-0 left-0 z-50 bg-background/80 backdrop-blur-md border-b border-muted/50'
    shining = 'top-0 right-0 left-0 z-50 bg-background shadow-md border-b border-muted'

def navbar(usr=None, title='', style=NavBarT.default, cls='w-full sticky', mobile_cls=''):
    usr_ok = bool(usr)
    inc_fnt_sz, inc_mode_sw, inc_th_sw, inc_avtr = True, True, not is_prod(), usr_ok
    sep = Div('|', cls=f'{ButtonT.icon} {ButtonT.sm} {TextT.gray} {TextT.xl}')
    cmps = [(font_size_switcher(), inc_fnt_sz), (mode_switcher(), inc_mode_sw),(theme_switcher(), inc_th_sw),
            (sep, True), (logout(usr), inc_avtr), (login(), not inc_avtr)]
    lft = A(H4(title, cls='m-0'), href='/')
    rgt = Div(*[c for c, inc in cmps if inc], cls='flex items-center gap-1')
    return Div(Nav(lft, rgt, cls=f'pl-4 pr-2 py-1 justify-between flex items-center {mobile_cls}'), cls=[style, cls])

## If you're going to be using this, you will need to include the monsterUI themes in your HTML. Refer vr.app.py
def theme_switcher(cls='uk-position-relative', heading='Customise', sub_heading='theme selection'):
    h = H3(heading, cls='m-2')
    sub = P(sub_heading, cls=(TextT.muted, 'mt-2 p-2'))
    con= [h,sub,ThemePicker(custom_themes=[('default','#000')])]
    return Div(Div(
        Div(UkIcon('palette'), cls=(ButtonT.icon, ButtonT.sm)),
            CardBody(*con,cls='dropdown-content w-96',data_uk_dropdown='mode: click; pos: bottom-right; offset: 8')),
        cls=f'{cls}')

def mode_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(Div(icon_auto(w=20,h=20), On('setMode("dark");'), cls=[btn_cls], id='auto-mode-btn'),
         Div(UkIcon('moon'), On('setMode("light");'), cls=btn_cls, id='dark-mode-btn'),
         Div(UkIcon('sun'), On('setMode("auto");'), cls=btn_cls, id='light-mode-btn'))

def font_size_switcher():
    btn_cls = f'{ButtonT.icon} {ButtonT.sm}'
    return Div(
        Div(UkIcon('case-lower',height=20,width=20), On('setFont("%s");' % ThemeFont.default), cls=[btn_cls], id='sm-font-btn'),
         Div(UkIcon('case-lower',height=24,width=24), On('setFont("%s");' % 'uk-font-lg'), cls=[btn_cls], id='lg-font-btn'),
        Div(UkIcon('case-lower',height=28,width=28), On('setFont("%s");' % ThemeFont.sm), cls=[btn_cls], id='xl-font-btn'),)

def svg_img(svg_path, cls='', w=16, h=16, outer_cls='', loading='lazy', **kw):
    return Div(
        Img(src=f'/{svg_path}', cls=cls, width=w, height=h, loading=loading, **kw),
        cls=f'inline-flex items-center justify-center {outer_cls}'
    )

def placeholder(message='placeholder text', back_link='/', back_text='Go Back Home'):
    btn_cls, txt_cls = f'{ButtonT.primary} {ButtonT.sm} uk-btn', f'{TextT.lead} mb-4'
    return Div(P(message, cls=txt_cls), A(back_text, href=back_link, cls=btn_cls), cls=TextT.center)

@cache(ttl=3600*24*30)
def montage(svg_paths, cols_sm=3, cols_md=5, cols_lg=6, rows=8, fill_screen=True, cls=BackgroundT.primary, svg_cls=None):
    l=len(svg_paths or [])
    if not l: return None
    svg_cls, outer_cls = ifnone(svg_cls, f'size-4/6 {BadgeT.invert}'), f'border-2 border-current border-dotted m-2 {PresetsT.standout}'
    svgs = islice(cycle(svg_paths.map(svg_img, cls=svg_cls, outer_cls=outer_cls)), int(l * rows) if fill_screen else l)
    return Grid(*svgs, cols_sm=cols_sm, cols_md=cols_md, cols_lg=cols_lg, cols_min=2, cols_xl=cols_lg, cls=cls)

@cache()
def typewriter(stat_txt=None, dyn_txt_lst=None,type_sp=250, del_sp=100, pause_end=1000,
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
    return Div(P(dyn_con, Span(stat_txt), cls=txt_cls), Now(code, sel='#typewriter'),cls=cls)

@cache()
def welcome_page(img_dir=s.svg, content=None, title=None, cls=None, cont_cls=None):
    img_paths = globtastic(img_dir, file_re='.svg|.png|.jpg')
    cls = ifnone(cls,'text-center backdrop-blur-xl p-4 sm:p-8 border border-current')
    cont_cls = ifnone(cont_cls,'min-h-screen flex items-center justify-center mt-8 max-w-80')
    t = Title(title) if title else None
    m = Div(montage(img_paths), cls='overflow-hidden uk-position-cover mt-10 opacity-50') if img_paths else None
    ftr = P(s.ftr_txt, cls='text-xs mt-4')
    con = Container(Div(H2(title, cls=PresetsT.shine), typewriter(), content, ftr, cls=cls), cls=cont_cls)
    return t, Section(m, con)

def landing(content, title=s.app_nm, usr=None):
    return base(welcome_page(content=content, title=title), usr=usr, style=NavBarT.glass)

def base(content=None, usr=None, title=s.app_nm, sh=s.app_sh, style=NavBarT.glass, **kwargs):
    return Title(title), Div(navbar(usr=usr, title=sh, style=style), main(content, **kwargs), cls='min-h-screen figma-board')

def main(content=None, cls=None, **kw): return Div(content if content else None, cls=stringify(['uk-width-1-1',cls]), id='main-content', **kw)

def email_template(content, title=s.app_nm, usr=None):
    if isinstance(usr,dict): content = f'Hello {usr.get('usr_name', 'Vedic Reader Patron')} \n\n {content}'
    header = Div(cls='bg-primary p-4 text-white')(H1(title, cls='text-lg font-bold'))
    body = Div(cls='p-4')(content)
    footer = Div(cls='bg-secondary p-2 text-white text-xs')('This email was sent by our team.')
    return Div(cls='border border-muted rounded-md overflow-hidden')(header, body, footer)

def adaptive_layout(divs, layout_spec, gap='gap-4', cls=''):
    """Create flexible, responsive layouts from a list of divs based on specified layout patterns.
    
    Args:
        divs: List of div components to layout
        layout_spec: List specifying number of columns per row (e.g., [1, 3, 2, 1, 1])
        gap: Tailwind gap class for spacing between items (default: 'gap-4')
        cls: Additional CSS classes to apply to the container
    
    Returns:
        Div containing the arranged components in rows
    
    Example:
        divs = [Div('Item 1'), Div('Item 2'), Div('Item 3'), Div('Item 4')]
        adaptive_layout(divs, [1, 3], gap='gap-6')
        # Creates: 1 item in first row, 3 items in second row
    """
    rows = []
    idx = 0
    
    for cols in layout_spec:
        if idx >= len(divs): break
        row_items = divs[idx:idx+cols]
        if not row_items: break
        
        # Create responsive grid for each row
        if cols == 1:
            row_cls = 'grid grid-cols-1 w-full'
        elif cols == 2:
            row_cls = 'grid grid-cols-1 sm:grid-cols-2'
        elif cols == 3:
            row_cls = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
        elif cols == 4:
            row_cls = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
        else:  # 5 or more
            row_cls = f'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-{min(cols, 6)}'
        
        rows.append(Div(*row_items, cls=f'{row_cls} {gap}'))
        idx += cols
    
    return Div(*rows, cls=stringify(['flex flex-col', gap, cls]))

def adaptive_layout_responsive(divs, layout_specs, gap='gap-4', cls=''):
    """Advanced responsive layout with breakpoint-specific layout specifications.
    
    Args:
        divs: List of div components to layout
        layout_specs: Dict with breakpoint keys ('sm', 'md', 'lg', 'xl') and layout spec values
                     e.g., {'sm': [1, 2], 'md': [2, 3], 'lg': [1, 3, 2]}
        gap: Tailwind gap class for spacing (default: 'gap-4')
        cls: Additional CSS classes
    
    Returns:
        Div with responsive layout that adapts to different screen sizes
    
    Example:
        adaptive_layout_responsive(
            divs,
            {'sm': [1, 1, 1], 'lg': [1, 3, 2]},
            gap='gap-6'
        )
    """
    # Use the largest breakpoint layout as base
    breakpoints = ['xl', 'lg', 'md', 'sm']
    base_spec = None
    for bp in breakpoints:
        if bp in layout_specs:
            base_spec = layout_specs[bp]
            break
    
    if not base_spec:
        # Fallback to equal distribution
        base_spec = [3] * (len(divs) // 3) + ([len(divs) % 3] if len(divs) % 3 else [])
    
    rows = []
    idx = 0
    
    for cols in base_spec:
        if idx >= len(divs): break
        row_items = divs[idx:idx+cols]
        if not row_items: break
        
        # Build responsive classes based on provided breakpoints
        responsive_classes = []
        
        # Base mobile
        responsive_classes.append('grid grid-cols-1')
        
        # Add responsive breakpoints
        if 'sm' in layout_specs and cols <= len(layout_specs['sm']):
            responsive_classes.append(f'sm:grid-cols-{min(cols, 4)}')
        elif cols >= 2:
            responsive_classes.append('sm:grid-cols-2')
            
        if 'md' in layout_specs and cols <= len(layout_specs['md']):
            responsive_classes.append(f'md:grid-cols-{min(cols, 6)}')
        elif cols >= 3:
            responsive_classes.append(f'md:grid-cols-{min(cols, 3)}')
            
        if 'lg' in layout_specs and cols <= len(layout_specs['lg']):
            responsive_classes.append(f'lg:grid-cols-{cols}')
        elif cols >= 3:
            responsive_classes.append(f'lg:grid-cols-{cols}')
        
        row_cls = ' '.join(responsive_classes)
        rows.append(Div(*row_items, cls=f'{row_cls} {gap}'))
        idx += cols
    
    return Div(*rows, cls=stringify(['flex flex-col', gap, cls]))

def layout_with_featured(featured_div, grid_divs, featured_cls='', grid_cols=3, gap='gap-4', cls=''):
    """Create a layout with a featured/hero section followed by a grid.
    
    Args:
        featured_div: Featured/hero component to display at the top (full width)
        grid_divs: List of components for the grid section
        featured_cls: Additional CSS classes for the featured section
        grid_cols: Number of columns in the grid (default: 3)
        gap: Tailwind gap class for spacing (default: 'gap-4')
        cls: Additional CSS classes for the container
    
    Returns:
        Div with featured section on top and grid below
    
    Example:
        layout_with_featured(
            Div('Hero Content', cls='h-64 bg-primary'),
            [Div(f'Card {i}') for i in range(6)],
            grid_cols=3
        )
    """
    # Featured section - full width
    featured_section = Div(featured_div, cls=stringify(['w-full', featured_cls]))
    
    # Grid section - responsive based on grid_cols
    if grid_cols == 1:
        grid_cls = 'grid grid-cols-1'
    elif grid_cols == 2:
        grid_cls = 'grid grid-cols-1 sm:grid-cols-2'
    elif grid_cols == 3:
        grid_cls = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
    elif grid_cols == 4:
        grid_cls = 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4'
    else:  # 5 or more
        grid_cls = f'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-{min(grid_cols, 6)}'
    
    grid_section = Div(*grid_divs, cls=f'{grid_cls} {gap}')
    
    return Div(featured_section, grid_section, cls=stringify(['flex flex-col', gap, cls]))

def welcome(usr=None): return landing(placeholder(f'Welcome to {s.app_nm}'),usr=usr)
def not_found(): return landing(placeholder("The page you're looking for doesn't exist or has been moved."))
