from fasthtml.common import *
from monsterui.franken import *
from lego.core.ui import *
from .data import hist, shared as hist_shared, get_projects

__all__ = ['history', 'chats', 'chat_window', 'message_bubble', 'chat_input']

def chatbot(): pass
hd=[
        ("August", [
            "FastHTML Chatbot: WebScrapper for Grok-like Chatbots",
            "Valmiki and Narada: Question Answering with Grok",
            "Creating Grok-like Chat Bots with FastHTML",
        ]),
        ("July", [
            "Training Model for Ramayana: A Grok-like Chatbot",
            "Fixing TA-Lib Installation Error on Mac",
            "Chunking PDFs with Python for Grok-like Chatbots",
            "Japa Mode Integration in Anthropic API for Grok-like Chatbots",
            "Understanding Python Glob Module for Grok-like Chatbots",
            "Asynchronous Anthropic API for Grok-like Chatbots",
            "Nginx Sticky Sessions with Grok-like Chatbots"
        ])
    ]

def btn_ico(icon_cls, txt): return Button(UkIcon(icon_cls), Span(txt), cls=f'{ButtonT.ghost} w-full flex items-left justify-start gap-2 px-1 cursor-pointer')
def nav_i(*c, cls='', **kw): return Li(*c, cls=f'cursor-pointer {cls}', **kw)
def search(): return nav_i(Div(A(UkIcon('search'), cls='absolute left-3 top-1/2 -translate-y-1/2'), Input(placeholder='Search', cls='pl-9'), cls='relative mr-4'))
def new(): return nav_i(btn_ico('square-pen', 'Chat'), cls='mt-2')
def files(): return nav_i(btn_ico('file-text', 'Files'), cls='mt-1')
# # TODO: treat projects similar to history, with a list of projects

def projects(pr=get_projects(1001)):
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch.name, cls='truncate'), href='#', id=ch.id)))
    hsts = pr.map(lambda c: hst_pm(c)).reduce(lambda x, y: x + y) if pr else L()
    cnt = NavContainer(*hsts, id='shared-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    ico = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('box', cls='group-hover:hidden block'))
    lnk = A(*ico, Span('Projects', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt), cls='uk-open')

def shr(shared:L=hist_shared(2002)):
    if not shared: return None
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch.name, cls='truncate group-hover:opacity-30'), UkIcon('book-copy', cls='group-hover:block hidden'), href='#', id=ch.id), cls='group'))
    hsts = shared.map(lambda c: hst_pm(c)).reduce(lambda x, y: x + y) if shared else L()
    cnt = NavContainer(*hsts, id='shared-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    ico = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('folder-kanban', cls='group-hover:hidden block'))
    lnk = A(*ico, Span('Shared with me', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt), cls='uk-open')

def history(hst:L=hist(1001)):
    if not hst: return None
    hst_pm = lambda chs: L(chs).map(lambda ch: nav_i(A(Span(ch[0], cls='truncate group-hover:opacity-30'), UkIcon('message-square-share', cls='group-hover:block hidden'), href='#', id=ch[1]), cls='group'))
    hsts = hst.map(lambda c: (NavHeaderLi(c[0], cls=TextT.xs),*hst_pm(c[1]))).reduce(lambda x,y: x+y)
    cnt=NavContainer(*hsts, id='history-container', parent=False, cls=[NavT.secondary, 'ml-3 border-l muted-border'])
    ico = (UkIcon('chevron-down', cls='group-hover:block hidden'), UkIcon('history', cls='group-hover:hidden block'))
    lnk = A(*ico, Span('History', cls=TextT.medium), href='#', cls='flex gap-2 px-1 ml-0 group')
    return NavParentLi((lnk, cnt), cls='uk-open')

def nav():
    con = (search(), new(), files(), projects(), shr(), history())
    bar = NavContainer(*con, cls=NavT.secondary, id='sidebar-container', uk_nav=True)
    return Div(bar, cls=f'{PresetsT.shine} overflow-y-auto w-72 min-w-72 m-2 p-2')

def message_bubble(content, is_user=True, timestamp=None):
    """Create a message bubble for user or bot"""
    bubble_cls = f'{PresetsT.secondary} ml-auto' if is_user else ''
    align_cls = 'justify-end' if is_user else 'justify-start'
    
    message_content = Div(
        Div(content, cls='whitespace-pre-wrap break-words'),
        Small(timestamp, cls='text-xs opacity-60 mt-1 block') if timestamp else None,
        cls=f'max-w-2xl px-4 py-3 rounded-2xl {bubble_cls}'
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
    control, pos = 'audio-controls', 'relative px-2 pt-2 pb-3 justify-center items-center'
    w, bg='w-full rounded-lg min-h-24', PresetsT.shine
    cls = [control, pos, w, bg]
    return Div(Div(a_ctrl_btns(), cls=cls), id='audio-container', cls=('sticky z-50 bottom-4 m-2'))


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

def chats(): 
    return Card(Div(
        nav(),
        chat_window(),
        cls='flex gap-0 w-full h-screen'
    ))