from fasthtml.common import *
from monsterui.franken import *
from monsterui.foundations import stringify
from lego.core.ui import *
from .cfg import AIPresetsT
from .data import hist, shared as hist_shared, get_projects

__all__ = ['chats']

def _nav_btn(ico_nm, txt=None, cls=None, ico_cls=None, code=None, **kw):
    t, btn_cls=Span(txt, cls='text-center') if txt else None, f'{ButtonT.icon if not txt else ''} {ButtonT.ghost}'
    c = ('w-full items-left justify-start flex gap-2 px-0.75 cursor-pointer' if txt else '') + f'{btn_cls} {cls if cls else ''}'
    return Button(UkIcon(ico_nm, cls=ico_cls), code, t, cls=c, **kw)

def _nav_i(*c, cls='', **kw): return Li(*c, cls=f'cursor-pointer {cls}', **kw)
def new(ico=False): return _nav_i(_nav_btn('square-pen', 'Chat' if not ico else None))
def files(ico=False): return _nav_i(_nav_btn('file-text', 'Files' if not ico else None))

def smpl_navi(txt, sub_t='', ico=None, cls='', ico_cls='', a_cls='', **kw):
    """Create a navigation item with optional icon, name, and description"""
    if not txt: return None
    nm, dsc = lambda n: Span(n, cls='truncate font-semibold nav-text'), lambda d: NavSubtitle(d, cls='truncate')
    c = A(UkIcon(ico, cls=ico_cls) if ico else None, Div(nm(txt), dsc(sub_t) if sub_t else None, cls='flex flex-col'), href='#', cls=[stringify(a_cls), 'py-0.5 gap-2'])
    return _nav_i(c, cls=cls, **kw)

def search(ico=False):
    if ico: return _nav_i(_nav_btn('search', cls='mt-2'))
    s_ico = A(UkIcon('search'), cls='uk-form-icon ml-0 pl-2')
    si = Input(placeholder='Search', cls='uk-input', type='text', aria_label='Clickable Icon')
    return _nav_i(Div(s_ico, si, cls='uk-inline -ml-1 mr-4'))

def projects(pr=get_projects(1001), ico=False):
    if ico: return _nav_i(_nav_btn('box'), cls='mt-0.5')
    proj_i = lambda chs: L(chs).map(lambda ch: smpl_navi(ch.name, ch.description, id=ch.id))
    proj = pr.map(lambda c: proj_i(c)).concat() if pr else L()
    cnt = NavContainer(*proj, id='projects-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('box', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('Projects', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt))

def shr(shared:L=hist_shared(2002), ico=False):
    if not shared: return None
    if ico: return _nav_i(_nav_btn('folder-kanban'), cls='mt-0')
    ch_itm = lambda ch: A(Span(ch.name, cls='truncate group-hover:opacity-30'), UkIcon('book-copy', cls='group-hover:block hidden'), href='#', id=ch.id)
    hst_pm = lambda chs: L(chs).map(lambda ch: _nav_i(ch_itm(ch), cls='group'))
    hsts = shared.map(lambda c: hst_pm(c)).concat() if shared else L()
    cnt = NavContainer(*hsts, id='shared-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('folder-kanban', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('Shared with me', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt))

def history(hst:L=hist(1001), ico=False):
    if not hst: return None
    if ico: return _nav_i(_nav_btn('history'), cls='mt-0')
    hst_pm = lambda chs: L(chs).map(lambda ch: _nav_i(A(Span(ch[0], cls='truncate opacity-80'), UkIcon('ellipsis-vertical', cls='item-end group-hover:block hidden'), href='#', id=ch[1], cls='pl-2.5'), cls='group'))
    hsts = hst.map(lambda c: (NavHeaderLi(c[0], cls=(TextT.xs,'py-0')),*hst_pm(c[1]))).concat()
    cnt=NavContainer(*hsts, id='history-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('history', cls='group-hover:hidden block'))
    hst_modal_trg = Span('History', cls=[TextT.medium, 'w-4/5'])
    lnk = A(*icon, hst_modal_trg, href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt), cls='uk-open')

def lg_nav(ico=False, hide=False):
    d,cls = 'hidden' if hide else '', ''
    tgl = 'any(".nav-container",me(".desktop-layout")).classToggle("hidden");'
    ign = "if (ev.target.closest('button, a, input, textarea, [data-uk-toggle]')) return;"
    on_snap, nav_click, snap_cls = On(tgl), On(ign + tgl), 'grow-1 absolute bottom-24 right-2 justify-end items-end'
    btn = _nav_btn('chevrons-right') if ico else _nav_btn('chevrons-left')
    snap = Div(on_snap, btn, cls=f'pt-4 chat-icon {snap_cls}')
    nav_click = On(ign + tgl)
    cls = 'pl-2 pr-3 pt-0 cursor-e-resize' if ico else 'w-64 min-w-64 ml-2 p-2 mb-2 cursor-w-resize'
    con = (search(ico=ico), new(ico=ico), files(ico=ico), projects(ico=ico), shr(ico=ico), history(ico=ico))
    nav_cls=f'chat-nav border-r muted-border h-screen mt-0 my-2 {cls} transition-all duration-300 ease-in-out relative'
    bar = NavContainer(*con, cls=[NavT.secondary, 'border-none mx-0 gap-1 z-10'], parent=False, data_uk_nav='multiple: true')
    return Card(bar, snap, nav_click, body_cls=nav_cls, cls=f'{PresetsT.glass} border-none shadow-none rounded-none {d} nav-container')

def mob_nav():
    con = (search(), new(), files(), projects(), shr(), history())
    nav_cls=f'chat-nav border-r muted-border h-screen mt-0 my-2 transition-all duration-300 ease-in-out relative'
    bar = NavContainer(*con, cls=[NavT.secondary, 'border-none mx-0 gap-1 z-10'], parent=False, data_uk_nav='multiple: true')
    return Card(bar, body_cls=nav_cls, cls=f'border-none shadow-none rounded-none mob-nav-container')

def msg(c, usr=True, tmstmp=None):
    """Create a message bubble for user or bot"""
    m_cls, align, tm = '', 'justify-start', None
    if usr: m_cls, align = AIPresetsT.usr_msg, 'justify-end'
    if tmstmp: tm = Small(tmstmp, cls='text-xs opacity-60 mt-1 block')
    mc=Div(Div(c, cls=['whitespace-pre-wrap break-words',m_cls]), tm, cls='flex flex-col')
    return Div(mc, cls=f'flex {align} mb-4 mx-4')

messages = L([
    ("Hello! I'm your AI assistant. How can I help you today?", False, "10:30 AM"),
    ("I need help analyzing some documents and understanding the key insights from them.", True, "10:31 AM"),
    ("I'd be happy to help you analyze your documents! Please upload the files you'd like me to review, and I'll provide insights, summaries, and answer any questions you have about the content.", False, "10:31 AM"),
    ("Perfect, let me upload a few files now.", True, "10:32 AM"),
])
def chat_messages(msgs=messages):
    return Div(Div(*(msg(*m) for m in msgs*10), Div(cls='h-48'), cls='mx-auto max-w-[48rem]'), cls='flex-1 py-4', uk_overflow_auto='selContainer: .chat-window; selContent: .chat-messages;')

def chat_inp(cls=None):
    ta_cls = 'w-full p-4 pr-16 min-h-12 max-h-96 resize-none focus:outline-none chat-text h-auto'
    ta = Textarea(placeholder="What do you want to know?", cls=ta_cls)
    code = "console.log(e);e.style.height = 'auto';if(!e.value){e.style.height = '4rem';} else {e.style.height = `${e.scrollHeight}px';}"
    ip = Div(ta, On(code, 'input', '.chat-text', me=False), opts(), cls=f'relative w-full rounded-2xl shadow-lg {PresetsT.shine}')
    ch_cls=f'absolute z-50 w-full max-w-[52rem] left-1/2 -translate-x-1/2 items-center px-4 {stringify(cls)}'
    return Div(ip, id='chat-container', cls=ch_cls)

def opts():
    btn_sm = f'{ButtonT.icon} {ButtonT.sm} {ButtonT.ghost}'
    attach, proj = Button(UkIcon('paperclip'), cls=btn_sm), Button(UkIcon('box'), cls=btn_sm)
    lft = Div(attach, proj, mode(), cls='flex items-center gap-0')
    rgt = Button(UkIcon('arrow-up'),cls=f'{ButtonT.primary} {ButtonT.icon} absolute right-3 bottom-2.5')
    return Div(lft, rgt, cls='flex items-center justify-between p-2')

m = dict2obj([
        {'icon': 'rocket', 'name': 'Auto', 'description': 'Chooses best mode'},
        {'icon': 'zap', 'name': 'Fast', 'description': 'Quick responses (using Grok 3)'},
        {'icon': 'lightbulb', 'name': 'Expert', 'description': 'Thinks hard (using Grok 4)'},
        {'icon': 'layout-grid', 'name': 'Heavy', 'description': 'Team of experts (using Grok 4 Heavy)'}])

def mode(mdls=m, default=0):
    chk, drama = UkIcon('check', cls='ml-auto text-primary pr-4 hidden mode-select'), UkIcon('drama', cls='ml-auto')
    rgt, down = UkIcon('chevron-right', cls='ml-auto pr-4'), UkIcon('chevron-down', cls='h-4 w-4')
    mdl_i = lambda mdl: Div(smpl_navi(mdl.name, mdl.description, ico=mdl.icon, ico_cls='h-4 w-6 nav-ico', cls='p-2',a_cls='hover:bg-background'),chk, cls='flex items-center mode-option')
    its = lambda chs: mdls.map(lambda mdl: mdl_i(mdl)) if mdls else L()
    sel = UkIcon(mdls[default].icon, cls='model-icon'), Span(mdls[default].name, cls='font-semibold text-muted-foreground model-name')
    btn = Button(*sel, drama, down, cls=f'{ButtonT.ghost} {ButtonT.sm} {ButtonT.icon} flex items-center gap-1 p-2 ')
    drop = lambda *c: Div(cls='uk-drop uk-dropdown w-96 rounded-xl shadow-lg border muted-border bg-background', uk_dropdown='mode: click')(*c)
    code=On('''const [mi,mn,ams,ms]=[me(".model-icon",m),me(".model-name",m),any(".mode-select"),me(".mode-select",e)]; mi.attribute("icon",me(".nav-ico",e).attribute("icon"));
    mi.innerHTML=me(".nav-ico",e).innerHTML;mn.text(me(".nav-text",e).text());ams.classAdd("hidden");ms.classRemove("hidden");''', me=False, sel='.mode-option')
    instr = Div(smpl_navi('Custom Instructions', 'Understand the context and answer appr...', ico='drama', ico_cls='h-4 w-6 nav-ico', cls='p-2',a_cls='hover:bg-background'),rgt, cls='flex items-center border-t muted-border pt-2 mt-1')
    return Div(btn,drop(NavContainer(*its(mdls), instr, cls=('uk-dropdown-nav', NavT.default))),code)

def chat_window(cls='grow-0 w-full h-screen', ip_cls='mt-auto bottom-14', msg_cls='w-full'):
    c = Div(chat_messages(), cls=f'chat-messages {stringify(msg_cls)}'), chat_inp(ip_cls)
    return Div(*c, cls=[cls, 'chat-window relative'])

def lg_chat():
    d_nav = Div(lg_nav(ico=True, hide=True), lg_nav(), cls='grow-0')
    cls, cw_cls ='hidden lg:flex w-full desktop-layout h-auto', [PresetsT.glass, 'relative', 'w-full flex items-center lg-chat-window']
    return Grid(d_nav, Div(chat_window(), cls=cw_cls), cls=cls, id='lg-chatbot-container', cols=4)

def mob_chat():
    m_nav = Div(Div(mob_nav(), cls='uk-offcanvas-bar'), id='mob-nav', data_uk_offcanvas='overlay: true; container: false;')
    m_ico = Button(UkIcon('menu'), aria_label="Open navigation", data_uk_toggle="target: #mob-nav", cls=f'p-2 {ButtonT.icon}')
    m_chat = Div(chat_window(ip_cls='bottom-8 mt-auto h-1/5'), cls='w-full',id='mob-chat-window')
    return Div(m_nav, m_ico, m_chat, cls='lg:hidden w-full', id='mob-chatbot-container')

def chatbot(): return Div(mob_chat(),lg_chat(), id='chatbot-container', cls='h-[90vh]')
def chats(): return chatbot()