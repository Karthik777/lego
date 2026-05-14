from collections import Counter
from fasthtml.common import *
from monsterui.all import *
from monsterui.franken import render_md
from lego.core.ui import PresetsT
from lego.auth.cfg import Routes as AR, Step
from lego.blog.data import posts

__all__ = ['blog_hero', 'post_card', 'post_list', 'locked_teaser', 'post_detail',
           'new_post_form', 'showcase_cta']

# ── UI helpers ────────────────────────────────────────────────────────────────

_ACCENT    = 'text-primary'
_ACCENT_BG = 'bg-primary/10 border border-primary/20'
_LOCK_CLS  = 'absolute inset-0 backdrop-blur-sm flex flex-col items-center justify-center gap-3 rounded-md z-10'

# Strip hardcoded size/weight from the default franken_class_map so uk-* and theme control sizing.
_MD_MODS = {
    'h1': 'uk-h1 mt-12 mb-6',
    'h2': 'uk-h2 mt-10 mb-5',
    'h3': 'uk-h3 mt-8 mb-4',
    'h4': 'uk-h4 mt-6 mb-3',
    'p':  'leading-relaxed mb-6',
    'ul': 'uk-list uk-list-bullet space-y-2 mb-6 ml-6',
    'ol': 'uk-list uk-list-decimal space-y-2 mb-6 ml-6',
}

def _fmt_date(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime('%b %d, %Y')

def _author_chip(name, date_ts):
    return ArticleMeta(
        Span(name, cls=f'font-medium {_ACCENT}'),
        Span('·', cls='mx-1'),
        _fmt_date(date_ts),
        cls='flex items-center')

def _visibility_badge(v):
    if v != 'members': return None
    return Label(UkIcon('lock', width=10, height=10), ' Members', cls='inline-flex items-center gap-1')

def _sign_in_cta(_slug):
    href = f'{AR.auth_modal}?step={Step.login}'
    return Div(UkIcon('lock', width=16, height=16, cls='text-muted-foreground'),
        P('Members only', cls=f'{TextPresets.muted_sm} m-0'),
        A('Sign in to read', href=href, cls=f'uk-btn {ButtonT.primary} {ButtonT.xs}'),
        cls=_LOCK_CLS)

_CODE_PEEK = '''\
@rt('/blog/{slug}')
def blog_post(req, slug:str):
    post = posts[slug]
    auth = req.scope['auth']
    if post.visibility=='members':
        if not auth: return locked_teaser(post)
    return post_detail(post, auth)
'''

def blog_hero(usr=None):
    _counts = Counter(p['visibility'] for p in posts())
    pub_ct, mem_ct = _counts['public'], _counts['members']

    left = Div(Div(_visibility_badge('members') or '',
                   Span(f'{pub_ct + mem_ct} posts', cls=TextPresets.muted_sm), cls='flex items-center gap-2 mb-4'),
        H1('The Obsession Journal', cls='mb-3'),
        P('Side projects. Package maintenance. The slow accumulation of taste.', cls=f'{TextT.muted} mb-6'),
        Div((A('Write a post', href='/blog/new', hx_get='/blog/new', hx_target='#main-content',
               hx_push_url='true', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}') if usr else
             A('Sign in to write', href='/a/m?step=login', cls=f'uk-btn {ButtonT.default} {ButtonT.sm}')),
            A('Read the story', href='#blog-posts', cls=f'uk-btn {ButtonT.ghost} {ButtonT.sm}'), cls='flex gap-3'),
        cls='flex flex-col justify-center')

    right = Div(
        Div(
            Div(
                Span('blog.py', cls=f'{_ACCENT} font-mono text-xs'),
                Span(f'{len(_CODE_PEEK.splitlines())} lines', cls=TextPresets.muted_sm),
                cls='flex justify-between items-center mb-3 pb-2 border-b border-muted'),
            Pre(Code(_CODE_PEEK, cls='text-xs leading-relaxed'), cls='overflow-x-auto'),
            cls=f'{PresetsT.shine} rounded-lg p-4 font-mono text-xs'),
        cls='flex items-center')

    return Section(
        Div(left, right, cls='grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-8 md:gap-16 items-center'),
        cls='px-4 py-12 md:py-20 max-w-5xl mx-auto')

def post_card(post, usr=None, featured=False):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    title_el = H2(post['title'], cls='mb-2') if featured else H3(post['title'], cls='mb-2')
    summary = P(post['summary'], cls=f'{TextPresets.muted_sm} mb-3 line-clamp-3')
    meta = Div(_author_chip(post['author_name'], post['created_at']), _visibility_badge(post['visibility']),
               cls='flex items-center gap-3 mb-3')
    read_link = A('Read →', href=slug_href, hx_get=slug_href, hx_target='#main-content', hx_push_url='true',
                  cls=f'{_ACCENT} text-xs font-medium hover:underline')

    body_area = Div(
        Div(cls='absolute inset-0 bg-gradient-to-b from-transparent to-background/80 rounded-md z-0'),
        _sign_in_cta(post['slug']),
        cls='relative rounded-md overflow-hidden min-h-[80px]') if locked else read_link

    if featured:
        return Card(CardBody(meta, title_el, summary, body_area))
    return Article(meta, title_el, summary, body_area, cls='py-5')


# ── Post list ─────────────────────────────────────────────────────────────────

def post_list(all_posts, usr=None):
    if not all_posts:
        return Div(
            UkIcon('notebook', width=32, height=32, cls='text-muted-foreground mb-3'),
            P('No posts yet.', cls=TextPresets.muted_sm),
            cls='flex flex-col items-center justify-center py-20 gap-2')

    featured, rest = all_posts[0], all_posts[1:]
    items = [post_card(featured, usr, featured=True)]
    items += [post_card(p, usr) for p in rest]
    return Div(*items, id='blog-posts', cls='max-w-2xl mx-auto px-4 divide-y divide-border')


# ── Post detail ───────────────────────────────────────────────────────────────

def locked_teaser(post):
    href = f'{AR.auth_modal}?step={Step.login}'
    return Section(
        Div(
            _author_chip(post['author_name'], post['created_at']),
            _visibility_badge(post['visibility']),
            cls='flex items-center gap-3 mb-4'),
        ArticleTitle(post['title'], cls='mb-4'),
        P(post['summary'], cls=f'{TextT.muted} mb-8'),
        Div(
            Div(cls='absolute inset-0 bg-gradient-to-b from-transparent via-background/60 to-background'),
            Div(
                Div(
                    UkIcon('lock', width=24, height=24, cls=_ACCENT),
                    H3('Members only', cls='m-0'),
                    P('Sign in to read the full post.', cls=f'{TextPresets.muted_sm} m-0'),
                    A('Sign in with Google', href=href, hx_get=href, hx_target='#main-content',
                      cls=f'uk-btn {ButtonT.primary} {ButtonT.sm} mt-2'),
                    A('or create a free account', href=href, hx_get=href, hx_target='#main-content',
                      cls=f'{_ACCENT} text-xs underline-offset-2 hover:underline'),
                    cls='flex flex-col items-center gap-2 text-center'),
                cls='absolute bottom-8 left-0 right-0 flex justify-center'),
            cls='relative min-h-[200px] overflow-hidden rounded-lg'),
        cls='max-w-2xl mx-auto px-4 py-12')

def post_detail(post, usr=None):
    if post['visibility'] == 'members' and not usr: return locked_teaser(post)
    back = A('← All posts', href='/blog', cls=f'{_ACCENT} text-xs font-medium hover:underline mb-8 block')
    meta = Div(_author_chip(post['author_name'], post['created_at']), _visibility_badge(post['visibility']),
               cls='flex items-center gap-3 mb-6')
    title = ArticleTitle(post['title'], cls='mb-4')
    body = Article(render_md(post['body'], class_map_mods=_MD_MODS), cls='max-w-prose')

    return Section(back, meta, title, body, cls='max-w-2xl mx-auto px-4 py-12')


# ── New post form ─────────────────────────────────────────────────────────────

def new_post_form(usr=None, err_msg=None):
    back = A('← All posts', href='/blog', hx_get='/blog', hx_target='#main-content',
             hx_push_url='true', cls=f'{_ACCENT} text-xs font-medium hover:underline mb-6 block')
    heading = H1('Write a post', cls='mb-8')
    err = P(err_msg, cls='text-danger text-sm') if err_msg else None

    return Section(
        Div(back, heading,
            Form(
                err,
                LabelInput('Title', id='title',
                           placeholder='What did you build, learn, or break?'),
                LabelInput('Summary', id='summary',
                           placeholder='One sentence. What should readers expect?'),
                LabelTextArea('Body', id='body', rows=14,
                              placeholder='Write in Markdown.',
                              input_cls='font-mono text-xs'),
                LabelSelect(
                    Option('Public — anyone can read', value='public', selected=True),
                    Option('Members only — requires sign-in', value='members'),
                    label='Visibility', id='visibility', name='visibility'),
                Div(
                    Button('Publish', cls=[ButtonT.primary, ButtonT.sm]),
                    A('Cancel', href='/blog', hx_get='/blog', hx_target='#main-content',
                      hx_push_url='true', cls=f'uk-btn {ButtonT.ghost} {ButtonT.sm}'),
                    cls='flex gap-3 pt-2'),
                cls='space-y-5 max-w-2xl mx-auto',
                hx_post='/blog/new', hx_target='#main-content'),
            cls='px-4 py-12'))


# ── Showcase CTA ──────────────────────────────────────────────────────────────

_PACKAGES = ['kosha', 'litesearch', 'dockeasy', 'vpseasy', 'cfeasy', 'lego', 'gheasy']

def showcase_cta(usr=None):
    pkg_badges = Div(
        *[Span(p, cls=f'{_ACCENT_BG} text-xs px-2 py-1 rounded-full font-mono') for p in _PACKAGES],
        cls='flex flex-wrap gap-2 justify-center my-6')

    if usr:
        cta = Div(
            P(f'You\'re signed in as {usr["display_name"]}. This is your blog now.',
              cls=f'{TextPresets.muted_sm} mb-4'),
            A('Write your first post', href='/blog/new', hx_get='/blog/new', hx_target='#main-content',
              hx_push_url='true', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}'),
            cls='text-center')
    else:
        href = f'{AR.auth_modal}?step={Step.login}'
        cta = Div(
            P('Sign in with Google and this becomes your blog. Same code, your content.',
              cls=f'{TextPresets.muted_sm} mb-4'),
            A('Sign in with Google', href=href, hx_get=href, hx_target='#main-content',
              cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}'),
            cls='text-center')

    return Section(
        Card(CardBody(
            H2('lego is the template', cls='mb-2 text-center'),
            P('8 packages. 4 years. One side project that kept growing.',
              cls=f'{TextPresets.muted_sm} text-center'),
            pkg_badges,
            P('Each package started as a problem in a side project. lego wraps the ones you need for a '
              'production-ready web app: auth, caching, backups, theming, this blog.',
              cls='text-center mx-auto mb-6 text-sm'),
            cta)),
        cls='max-w-2xl mx-auto px-4 py-16')
