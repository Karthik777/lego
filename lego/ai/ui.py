from fasthtml.common import *
from monsterui.franken import *
from lego.core.ui import *
from .cfg import AIPresetsT
from .data import hist, shared as hist_shared, get_projects

__all__ = ['chats']

def btn_ico(ico_nm, txt=None, cls=None, ico_cls=None, code=None, **kw):
    t, btn_cls=Span(txt, cls='text-center') if txt else None, f'{ButtonT.icon if not txt else ''} {ButtonT.ghost}'
    c = ('w-full items-left justify-start flex gap-2 px-0.75 cursor-pointer' if txt else '') + f'{btn_cls} {cls if cls else ''}'
    return Button(UkIcon(ico_nm, cls=ico_cls), code, t, cls=c, **kw)

def nav_i(*c, cls='', **kw): return Li(*c, cls=f'cursor-pointer {cls}', **kw)
def new(ico=False): return nav_i(btn_ico('square-pen', 'Chat' if not ico else None))
def files(ico=False):
    if ico: return nav_i(btn_ico('file-text', 'Files' if not ico else None, data_uk_toggle="target: #files-history-modal", onclick="UIkit.tab('#modal-tabs').show(0);"))
    return nav_i(btn_ico('file-text', 'Files' if not ico else None), data_uk_toggle="target: #files-history-modal", onclick="UIkit.tab('#modal-tabs').show(0);")

def search(ico=False):
    if ico: return nav_i(btn_ico('search', cls='mt-2'))
    s_ico = A(UkIcon('search'), cls='uk-form-icon ml-0 pl-2')
    si = Input(placeholder='Search', cls='uk-input', type='text', aria_label='Clickable Icon')
    return nav_i(Div(s_ico, si, cls='uk-inline -ml-1 mr-4'))

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
    if ico: return nav_i(btn_ico('history'), cls='mt-0', data_uk_toggle="target: #files-history-modal", onclick="UIkit.tab('#modal-tabs').show(1);")
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch[0], cls='truncate opacity-80'), UkIcon('ellipsis-vertical', cls='item-end group-hover:block hidden'), href='#', id=ch[1], cls='pl-2.5'), cls='group'))
    hsts = hst.map(lambda c: (NavHeaderLi(c[0], cls=(TextT.xs,'py-0')),*hst_pm(c[1]))).reduce(lambda x,y: x+y)
    cnt=NavContainer(*hsts, id='history-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    icon = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('history', cls='group-hover:hidden block'))
    lnk = A(*icon, Span('History', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group', data_uk_toggle="target: #files-history-modal", onclick="UIkit.tab('#modal-tabs').show(1);")
    return NavParentLi((lnk, cnt), cls='uk-open')

def nav(ico=False, hide=False):
    d,cls = 'hidden' if hide else '', ''
    tgl = 'any(".nav-container",me(".desktop-layout")).classToggle("hidden");'
    ign = "if (ev.target.closest('button, a, input, textarea, [data-uk-toggle]')) return;"
    on_snap, nav_click, snap_cls = On(tgl), On(ign + tgl), 'grow-1 absolute bottom-24 right-2 justify-end items-end'
    btn = btn_ico('chevrons-right') if ico else btn_ico('chevrons-left')
    snap = Div(on_snap, btn, cls=f'pt-4 chat-icon {snap_cls}')
    nav_click = On(ign + tgl)
    cls = 'pl-2 pr-3 pt-0 cursor-e-resize' if ico else 'w-64 min-w-64 ml-2 p-2 mb-2 cursor-w-resize'
    con = (search(ico=ico), new(ico=ico), files(ico=ico), projects(ico=ico), shr(ico=ico), history(ico=ico))
    nav_cls=f'chat-nav border-r muted-border h-screen mt-0 my-2 {cls} transition-all duration-300 ease-in-out relative'
    bar = NavContainer(*con, cls=[NavT.secondary, 'border-none mx-0 gap-1 z-10'], parent=False, data_uk_nav='multiple: true')
    return Card(bar, snap, nav_click, body_cls=nav_cls, cls=f'border-none shadow-none rounded-none {d} nav-container')

def lg_chat():
    d_nav = Div(nav(ico=True, hide=True), nav(), cls='grow-0')
    divider = Div(cls='root-divider grow')
    cls='hidden lg:flex w-full desktop-layout'
    return Grid(d_nav, divider, Div(chat_window(), cls=[PresetsT.glass,'relative']), divider, cls=cls, id='lg-chatbot-container', cols=4)

def mob_nav():
    con = (search(), new(), files(), projects(), shr(), history())
    nav_cls=f'chat-nav border-r muted-border h-screen mt-0 my-2 transition-all duration-300 ease-in-out relative'
    bar = NavContainer(*con, cls=[NavT.secondary, 'border-none mx-0 gap-1 z-10'], parent=False, data_uk_nav='multiple: true')
    return Card(bar, body_cls=nav_cls, cls=f'border-none shadow-none rounded-none mob-nav-container')

def mob_chat():
    m_nav = Div(Div(mob_nav(), cls='uk-offcanvas-bar'), id='mob-nav', data_uk_offcanvas='overlay: true; container: false;')
    m_ico = Button(UkIcon('menu'), aria_label="Open navigation", data_uk_toggle="target: #mob-nav", cls=f'p-2 {ButtonT.icon}')
    m_chat = Div(chat_window(), cls='w-full',id='mob-chat-window')
    return Div(m_nav, m_ico, m_chat, cls='lg:hidden w-full', id='mob-chatbot-container')

def chatbot():
    main_modal, preview_drawer = files_history_modal()
    return Div(mob_chat(),lg_chat(), main_modal, preview_drawer, id='chatbot-container', cls='h-[90vh]')

def msg(c, usr=True, tmstmp=None):
    """Create a message bubble for user or bot"""
    m_cls, align, tm = '', 'justify-start', None
    if usr: m_cls, align = AIPresetsT.usr_msg, 'justify-end'
    if tmstmp: tm = Small(tmstmp, cls='text-xs opacity-60 mt-1 block')
    mc=Div(Div(c, cls=['whitespace-pre-wrap break-words',m_cls]), tm, cls='flex flex-col')
    return Div(mc, cls=f'flex {align} mb-4 mx-4')

def chat_messages():
    """Sample chat messages with Grok-style content"""
    messages = [
        ("Hello! I'm your AI assistant. How can I help you today?", False, "10:30 AM"),
        ("I need help analyzing some documents and understanding the key insights from them.", True, "10:31 AM"),
        ("I'd be happy to help you analyze your documents! Please upload the files you'd like me to review, and I'll provide insights, summaries, and answer any questions you have about the content.", False, "10:31 AM"),
        ("Perfect, let me upload a few files now.", True, "10:32 AM"),
    ]
    return Div(*(msg(*m) for m in messages*10), cls='flex-1 py-4', uk_overflow_auto='selContainer: .chat-window; selContent: .chat-messages;')

def chat_inp():
    control, pos = 'chat-controls', 'px-2 pt-2 pb-3 justify-center items-center'
    w, bg='w-full rounded-lg min-h-24', PresetsT.shine
    opt = Div(ctrls(), cls=[control, pos, w, bg])
    return Div(opt, id='chat-container', cls='absolute z-50 bottom-16 w-full lg:w-2/3 flex justify-center px-4')


def ctrls():
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

def chat_window(cls='grow-0 w-full h-screen'):
    """Main chatbot window with clean Grok-style design"""
    return Div(
        Div(chat_messages(), cls='chat-messages'),
        # chat_input(),
        chat_inp(),
        cls=[cls, 'chat-window h-full']
    )
    return Div(chat_messages(), chat_inp(), cls=[cls, 'chat-window'])

def files_history_modal(hst:L=hist(1001)):
    files = [
        {'name': 'document-1.pdf', 'content': 'This is the content of document-1.pdf'},
        {'name': 'document-2.docx', 'content': 'This is the content of document-2.docx'},
        {'name': 'presentation.pptx', 'content': 'This is the content of presentation.pptx'},
    ]

    preview_drawer = Modal(
        Div(P(), id='mobile-preview-content'),
        header=ModalTitle("Preview"),
        footer=ModalCloseButton("Close", cls=ButtonT.default, submit=False),
        id="item-preview-drawer-mobile",
        dialog_cls="uk-margin-auto-vertical"
    )

    def file_list_item(f):
        onclick_js = f"document.getElementById('desktop-preview-content').innerHTML='<p>{f['content']}</p>'; document.getElementById('mobile-preview-content').innerHTML='<p>{f['content']}</p>';"
        return Li(A(
            Span(f['name']),
            href="#",
            onclick=onclick_js,
            data_uk_toggle="target: #item-preview-drawer-mobile",
            cls="lg:!p-0"
        ))

    def history_list_item(item):
        content = f"Preview for {item[0]}"
        onclick_js = f"document.getElementById('desktop-preview-content').innerHTML='<p>{content}</p>'; document.getElementById('mobile-preview-content').innerHTML='<p>{content}</p>';"
        return Li(A(
            item[0],
            href="#",
            onclick=onclick_js,
            data_uk_toggle="target: #item-preview-drawer-mobile",
            cls="lg:!p-0"
        ))

    file_list = Ul(*[file_list_item(f) for f in files], cls='uk-list uk-list-divider')

    history_list_items = []
    if hst:
        for group, items in hst:
            history_list_items.append(NavHeaderLi(group, cls=(TextT.xs, 'py-0')))
            for item in items:
                history_list_items.append(history_list_item(item))
    history_list = Ul(*history_list_items, cls='uk-list uk-list-divider')

    list_pane_files = Div(file_list, cls='w-full lg:w-1/3 p-4 overflow-y-auto border-r muted-border')
    list_pane_history = Div(history_list, cls='w-full lg:w-1/3 p-4 overflow-y-auto border-r muted-border')

    preview_pane = Div(
        Div(P("Select an item to see a preview."), id="desktop-preview-content"),
        cls='hidden lg:block w-2/3 p-4'
    )

    files_tab_content = Div(list_pane_files, preview_pane, cls='flex h-[calc(100vh-70px)]')
    history_tab_content = Div(list_pane_history, preview_pane, cls='flex h-[calc(100vh-70px)]')

    main_modal = Modal(
        Ul(
            Li(A("Files", href="#")),
            Li(A("History", href="#")),
            data_uk_tab=True,
            id="modal-tabs",
            cls='w-full'
        ),
        Ul(
            Li(files_tab_content),
            Li(history_tab_content),
            cls='uk-switcher'
        ),
        header=ModalHeader(
            ModalTitle("Workspace"),
            ModalCloseButton(UkIcon('x'), cls='uk-modal-close-full uk-close-large', submit=False)
        ),
        id="files-history-modal",
        cls="uk-modal-full",
        body_cls="p-0",
        dialog_cls="!p-0 !m-0 !w-full !max-w-full !h-screen"
    )

    return main_modal, preview_drawer

def chats(): return chatbot()