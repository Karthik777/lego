from fasthtml.common import *
from monsterui.franken import *
from lego.core.ui import *
from .data import hist, shared as hist_shared, get_projects

__all__ = ['history', 'chats', 'chat_window', 'message_bubble', 'chat_input']

def btn_ico(ico_nm, txt=None, cls=None, ico_cls=None, code=None, **kw):
    t, btn_cls=Span(txt, cls='text-center') if txt else None, f'{ButtonT.icon if not txt else ''} {ButtonT.ghost}'
    c = ('w-full items-left justify-start flex gap-2 px-0.75 cursor-pointer' if txt else '') + f'{btn_cls} {cls if cls else ''}'
    return Button(UkIcon(ico_nm, cls=ico_cls), code, t, cls=c, **kw)

def nav_i(*c, cls='', **kw): return Li(*c, cls=f'cursor-pointer {cls}', **kw)
def new(ico=False): return nav_i(btn_ico('square-pen', 'Chat' if not ico else None))
def files(ico=False): return nav_i(btn_ico('file-text', 'Files' if not ico else None))

def search(ico=False):
    if ico: return nav_i(btn_ico('search', cls='mt-2'))
    return nav_i(Div(A(UkIcon('search'), cls='absolute ml-0 pl-2 top-1/2 -translate-y-1/2'), Input(placeholder='Search', cls='pl-8'),cls='-ml-1 mr-4'))

def projects(pr=get_projects(1001), ico=False):
    if ico: return nav_i(btn_ico('box'), cls='mt-0.5')
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Div(Span(ch.name, cls='truncate font-bold'), Div(ch.description,cls=f'uk-nav-subtitle truncate {TextT.xs} opacity-80')), href='#', id=ch.id, cls='py-0.5')))
    hsts = pr.map(lambda c: hst_pm(c)).reduce(lambda x, y: x + y) if pr else L()
    cnt = NavContainer(*hsts, id='projects-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('box', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('Projects', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt))

def shr(shared:L=hist_shared(2002), ico=False):
    if not shared: return None
    if ico: return nav_i(btn_ico('folder-kanban'), cls='mt-0')
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch.name, cls='truncate group-hover:opacity-30'), UkIcon('book-copy', cls='group-hover:block hidden'), href='#', id=ch.id), cls='group'))
    hsts = shared.map(lambda c: hst_pm(c)).reduce(lambda x, y: x + y) if shared else L()
    cnt = NavContainer(*hsts, id='shared-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('folder-kanban', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('Shared with me', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt))

def history(hst:L=hist(1001), ico=False):
    if not hst: return None
    if ico: return nav_i(btn_ico('history'), cls='mt-0')
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch[0], cls='truncate opacity-80'), UkIcon('ellipsis-vertical', cls='item-end group-hover:block hidden'), href='#', id=ch[1], cls='pl-2.5'), cls='group'))
    hsts = hst.map(lambda c: (NavHeaderLi(c[0], cls=(TextT.xs,'py-0')),*hst_pm(c[1]))).reduce(lambda x,y: x+y)
    cnt=NavContainer(*hsts, id='history-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('history', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('History', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt), cls='uk-open')

def nav(ico=False, mob=False, hide=False):
    d,cls = 'hidden' if hide else '', ''
    snap=nav_click=None
    if not mob:
        tgl = 'any(".chat-nav",me(".desktop-layout")).classToggle("hidden");any(".chat-icon",me(".desktop-layout")).classToggle("hidden");'
        ign = "if (ev.target.closest('button, a, input, textarea, [data-uk-toggle]')) return;"
        on_snap, nav_click, snap_cls = On(tgl), On(ign + tgl), 'grow-1 absolute justify-end items-end'
        btn = btn_ico('chevrons-right') if ico else btn_ico('chevrons-left')
        snap = Div(on_snap, btn, cls=f'pt-4 chat-icon {d} {snap_cls}')
        nav_click = On(ign + tgl)
        cls = 'pl-2 pr-3 pt-0 cursor-e-resize' if ico else 'w-64 min-w-64 ml-2 p-2 mb-2 cursor-w-resize'
    con = (search(ico=ico), new(ico=ico), files(ico=ico), projects(ico=ico), shr(ico=ico), history(ico=ico))
    nav_cls=f'chat-nav border-r muted-border h-screen my-2 {d} {cls} transition-all duration-300 ease-in-out'
    bar = NavContainer(*con, cls=[NavT.secondary, 'border-none mx-0 gap-1 z-10'], id='sidebar-container', parent=False, data_uk_nav='multiple: true')
    return Card(bar, snap, nav_click, body_cls=nav_cls, cls='p-0 border-none shadow-none rounded-none', uk_overflow_auto='selContainer: #chatbot-container; selContent: .chat-window')

def chatbot():
    mob_nav = Div(Div(nav(False, mob=True), cls='uk-offcanvas-bar'), id='mob-nav',data_uk_offcanvas='overlay: true;')
    mob_icon = Button(UkIcon('menu'), aria_label="Open navigation", data_uk_toggle="target: #mob-nav", cls=f'lg:hidden p-2 {ButtonT.icon}')
    desktop_nav = Div(nav(ico=True, hide=True), nav(), chat_window(), cls='hidden lg:flex w-full desktop-layout')
    chat = Div(chat_window(), cls='lg:hidden w-full')
    return Div(mob_icon,desktop_nav,chat,mob_nav)


def message_bubble(content, is_user=True, timestamp=None):
    """Create a message bubble for user or bot"""
    bubble_cls = f'{PresetsT.secondary} ml-auto' if is_user else ''
    align_cls = 'justify-end' if is_user else 'justify-start'
    
    message_content = Div(
        Div(content, cls='whitespace-pre-wrap break-words'),
        Small(timestamp, cls='text-xs opacity-60 mt-1 block') if timestamp else None,
        cls=f'max-w-2xl px-4 py-3 rounded-tl-4xl rounded-bl-4xl rounded-tr-3xl rounded-sm {bubble_cls}'
    )
    
    return Div(message_content, cls=f'flex {align_cls} mb-4 mx-4')

def chat_messages():
    """Sample chat messages with Grok-style content"""
    messages = [
        ("Hello! I'm your AI assistant. How can I help you today?", False, "10:30 AM"),
        ("I need help analyzing some documents and understanding the key insights from them.", True, "10:31 AM"),
        ("I'd be happy to help you analyze your documents! Please upload the files you'd like me to review, and I'll provide insights, summaries, and answer any questions you have about the content.", False, "10:31 AM"),
        ("Perfect, let me upload a few files now.", True, "10:32 AM"),
    ]
    
    return Div(
        *(message_bubble(msg, is_user, time) for msg, is_user, time in messages),
        cls='flex-1 py-4'
    )

def file_upload_area():
    """Clean file upload component"""
    return Div(
        Input(type='file', multiple=True, accept='.pdf,.doc,.docx,.txt,.md', 
              cls='hidden', id='file-upload'),
        Label(
            Div(
                Span('📎', cls='text-lg mr-2'),
                Span('Upload files', cls='text-sm text-gray-600 dark:text-gray-400'),
                cls='flex items-center justify-center py-2 px-3 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 hover:border-blue-500 transition-colors cursor-pointer'
            ),
            For='file-upload'
        ),
        cls='mb-3'
    )

def chat_input():
    """Clean chat input similar to Grok interface"""
    return Div(
        file_upload_area(),
        Form(
            Div(
                Textarea(
                    placeholder='Message...',
                    cls='flex-1 resize-none border-0 focus:ring-0 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400',
                    rows=1,
                    id='chat-input'
                ),
                Button(
                    Div(
                        Span('→', cls='text-lg'),
                        cls='w-8 h-8 flex items-center justify-center'
                    ),
                    type='submit',
                    cls='bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors'
                ),
                cls='flex items-end gap-3 bg-gray-50 dark:bg-gray-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-gray-700'
            ),
            cls='w-full'
        ),
        cls='p-4 border-t border-gray-200 dark:border-gray-700'
    )


def a_container():
    control, pos = 'audio-controls', 'px-2 pt-2 pb-3 justify-center items-center'
    w, bg='w-full rounded-lg min-h-24', PresetsT.shine
    cls = [control, pos, w, bg]
    return Div(Div(a_ctrl_btns(), cls=cls), id='audio-container', cls=('fixed z-50 bottom-4 m-2 w-24/25 md:w-128'))


def a_ctrl_btns():
    btn=f'{ButtonT.icon} {ButtonT.sm}'
    p_btn, g_btn = f'{btn} {ButtonT.primary}',f'{btn} {ButtonT.ghost}'
    cap_do = 'window.toggleCaptions(m);'
    cls, lft, mid, rgt = 'w-1/3 flex item-center', 'justify-left gap-1.5', 'justify-center gap-2', 'justify-end gap-0.5'

    caption = Button(UkIcon('captions'), On(cap_do), cls=f'{g_btn}', id='captions-btn')
    japa_do = 'window.toggleJapa(m);'
    japa = Button(UkIcon('circle'), On(japa_do), cls=f'{g_btn}', id='japa-btn')
    loop_do='if(!window.snd.loop()){window.snd.loop(true);window.sel(m);}else{window.snd.loop(false);window.unsel(m);}'
    loop = Button(UkIcon('repeat-2'), On(loop_do), cls=f'{g_btn}', id='loop-btn')
    stop = Button(UkIcon('square'), On('window.snd.stop();'), cls=f'{btn}', id='bck-btn')
    play = Button(UkIcon('play'), On('window.snd.play();'), cls=f'{p_btn}', id='play-btn')
    pause = Button(UkIcon('pause'), On('window.snd.pause();'), cls=f'{p_btn} selected hidden', id='pause-btn')
    vol_on = Button(UkIcon('volume-2'), On('window.snd.mute(true);'), cls=f'{g_btn}', id='vol-on-btn')
    vol_off = Button(UkIcon('volume-x'), On('window.snd.mute(false);'), cls=f'{g_btn} {TextT.muted} hidden',id='vol-off-btn')
    return Div(
        Div(japa, cls=[cls,lft]),
        Div(*[stop,play,pause],cls=[cls,mid]),
        Div(caption,loop,*[vol_on,vol_off],cls=[cls, rgt]),
        cls='w-full flex items-center justify-between')

def chat_window():
    """Main chatbot window with clean Grok-style design"""
    return Div(
        chat_messages(),
        a_container(),
        cls='flex flex-col'
    )

def chats(): return chatbot()