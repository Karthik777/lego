from collections import Counter
from fasthtml.common import *
from monsterui.all import *
from monsterui.franken import render_md, FrankenRenderer
from lego.auth.cfg import Routes as AR, Step
from lego.blog.data import posts
from lego.core import RouteOverrides

class BlogRenderer(FrankenRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._img_idx = 0

    def render_image(self, token):
        title = f' title="{token.title}"' if hasattr(token, 'title') and token.title else ''
        src = token.src
        if self.img_dir and not src.startswith(('http://', 'https://', '/')): src = f'{self.img_dir}/{src}'
        alt = token.children[0].content if token.children else ''
        float_cls = 'float-right ml-6 mb-2 clear-right' if self._img_idx % 2 == 0 else 'float-left mr-6 mb-2 clear-left'
        self._img_idx += 1
        return (f'<figure class="w-40 sm:w-52 {float_cls} mt-1">'
                f'<img src="{src}" alt="{alt}"{title} class="w-full h-auto rounded-lg">'
                f'<figcaption class="text-xs text-center mt-1 text-muted-foreground">{alt}</figcaption>'
                f'</figure>')

__all__ = ['blog_hero', 'post_card', 'post_list', 'locked_teaser', 'post_detail',
           'new_post_form', 'showcase_cta']

# ── UI helpers ────────────────────────────────────────────────────────────────

_ACCENT    = 'text-primary'
_ACCENT_BG = 'bg-primary/10 border border-primary/20'
_LOCK_CLS  = 'absolute inset-0 backdrop-blur-sm flex flex-col items-center justify-center rounded-md z-10'

# Strip hardcoded size/weight from the default franken_class_map so uk-* and theme control sizing.
_MD_MODS = {
    'h1': 'uk-h1 mt-12 mb-6',
    'h2': 'uk-h2 mt-10 mb-5',
    'h3': 'uk-h3 mt-8 mb-4',
    'h4': 'uk-h4 mt-6 mb-3',
    'p':  'leading-relaxed mb-6',
    'ul': 'uk-list uk-list-bullet space-y-2 mb-6 ml-6',
    'ol': 'uk-list uk-list-decimal space-y-2 mb-6 ml-6',
    'hr': 'clear-both my-8 border-border',
}

def _fmt_date(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime('%b %d, %Y')

def _author_chip(name, date_ts):
    return ArticleMeta(Span(name, cls=f'font-medium {_ACCENT}'), Span('·', cls='mx-1 opacity-40'),
        Span(_fmt_date(date_ts), cls='font-mono'), cls='flex items-center')

def _visibility_badge(v):
    if v != 'members': return ''
    return Label(UkIcon('lock', width=10, height=10), ' Members', cls='inline-flex items-center gap-1')

def _first_image(body):
    m = re.search(r'!\[.*?\]\((.+?)\)', body)
    if not m: return None
    src = m.group(1)
    return src if src.startswith('/') else f'/static/blog/{src}'

def _sign_in_cta(_slug):
    return Div(UkIcon('lock', width=16, height=16, cls='text-muted-foreground'),
        P('Members only', cls=f'{TextT.sm} m-0'),
        A('Sign in to read', href=RouteOverrides.lgn, cls=f'uk-btn {ButtonT.primary} {ButtonT.xs}'),
        cls=_LOCK_CLS)


# ── Hero ──────────────────────────────────────────────────────────────────────

_CODE_PEEK = '''\
@rt('/blog/{slug}')
def blog_post(req, auth, slug:str):
    post = posts[slug]
    if post.visibility != 'members': return post_detail(post, auth)
    return locked_teaser(post)
'''

def blog_hero(usr=None):
    _counts = Counter(p['visibility'] for p in posts())
    pub_ct, mem_ct = _counts['public'], _counts['members']

    left = Div(
        Div(_visibility_badge('members'), Span(f'{pub_ct + mem_ct} posts', cls=f'{TextT.sm} font-mono'),
            cls='flex items-center gap-2 mb-4'),
        H1('The Obsession Journal', cls='mb-3 tracking-tight'),
        P('Side projects. Package maintenance. The slow accumulation of taste.', cls='mb-6 leading-relaxed'),
        Div((A('Write a post', href='/blog/new', hx_get='/blog/new', hx_target='#main-content',
               hx_push_url='true', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}') if usr else
             A('Sign in to write', href=RouteOverrides.lgn, cls=f'uk-btn {ButtonT.default} {ButtonT.sm}')),
            A('Read the story', href='#blog-posts', cls=f'uk-btn {ButtonT.ghost} {ButtonT.sm}'),
            cls='flex gap-3'), cls='flex flex-col justify-center')

    # Terminal-style code window
    right = Div(
        Div(
            Div(
                Div(cls='w-2.5 h-2.5 rounded-full bg-red-500/80'),
                Div(cls='w-2.5 h-2.5 rounded-full bg-yellow-500/80'),
                Div(cls='w-2.5 h-2.5 rounded-full bg-green-500/80'),
                Span('blog.py', cls='text-xs text-zinc-400 font-mono ml-2'),
                Span(f'{len(_CODE_PEEK.splitlines())} lines', cls='text-xs text-zinc-600 font-mono ml-auto'),
                cls='flex items-center gap-1.5 mb-3 pb-2 border-b border-zinc-800'),
            Pre(Code(_CODE_PEEK, cls='text-xs leading-relaxed text-zinc-300 whitespace-pre-wrap break-all'),
                cls='overflow-x-auto'),
            cls='bg-zinc-950 rounded-xl p-4 font-mono text-xs shadow-xl ring-1 ring-zinc-800 overflow-hidden'),
        cls='flex items-center min-w-0')

    return Section(
        Div(left, right,
            cls='grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-8 md:gap-16 items-center [&>*]:min-w-0'),
        cls='px-4 py-12 md:py-20 max-w-5xl mx-auto')


# ── Post card ─────────────────────────────────────────────────────────────────

def _section_label(text):
    return P(text, cls='text-xs font-mono tracking-widest uppercase text-muted-foreground border-t border-border pt-2 mb-3')

def _featured_card(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    img_src = _first_image(post.get('body', ''))
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    headline = H2(post['title'], cls='tracking-tight leading-tight mb-3')
    img_el = Div(Img(src=img_src, alt='', cls='w-full h-56 sm:h-72 md:h-80 object-cover object-top'),
                 cls='overflow-hidden mb-4') if img_src else None
    byline = Div(
        Span(f'BY {post["author_name"].upper()}', cls='text-xs font-mono tracking-wider text-muted-foreground'),
        Span(' · ', cls='mx-1 text-muted-foreground/40 text-xs'),
        Span(_fmt_date(post['created_at']), cls='text-xs font-mono text-muted-foreground'),
        cls='flex items-center mt-3')
    if locked:
        body = Div(Div(cls='absolute inset-0 bg-gradient-to-b from-transparent via-background/60 to-background'),
                   _sign_in_cta(post['slug']), cls='relative min-h-[60px] overflow-hidden')
    else:
        body = Div(P(post['summary'], cls='leading-relaxed'), byline)
    return Div(_section_label('Featured'), headline, img_el, body,
               cls='cursor-pointer hover:opacity-90 transition-opacity', **kw)

def _sidebar_item(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    tag = Span('Members', cls='text-xs font-mono tracking-wider uppercase text-primary block mb-1') if locked else ''
    title = H3(post['title'], cls='leading-snug tracking-tight mb-1')
    date = Span(_fmt_date(post['created_at']), cls='text-xs font-mono text-muted-foreground')
    return Div(tag, title, date,
               cls='py-3 border-b border-border cursor-pointer hover:opacity-70 transition-opacity', **kw)

def _grid_card(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    img_src = _first_image(post.get('body', ''))
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    img_el = Div(Img(src=img_src, alt='', cls='w-full h-40 object-cover object-top'),
                 cls='overflow-hidden mb-3') if img_src else None
    tag = Span('Members', cls='text-xs font-mono tracking-wider uppercase text-primary block mb-1') if locked else ''
    title = H3(post['title'], cls='leading-snug tracking-tight mb-2')
    summary = P(post['summary'], cls=f'{TextT.sm} line-clamp-3 text-muted-foreground')
    return Article(img_el, tag, title, summary,
                   cls='cursor-pointer hover:opacity-80 transition-opacity', **kw)

def post_card(post, usr=None, featured=False):
    return _featured_card(post, usr) if featured else _grid_card(post, usr)


# ── Post list ─────────────────────────────────────────────────────────────────

def post_list(all_posts, usr=None):
    if not all_posts:
        return Div(UkIcon('notebook', width=32, height=32, cls='text-muted-foreground mb-3'),
            P('No posts yet.', cls=TextT.sm), cls='flex flex-col items-center justify-center py-20 gap-2')

    featured, rest = all_posts[0], all_posts[1:]
    secondary, grid_posts = rest[:4], rest[4:]

    feature_col = Div(_featured_card(featured, usr), cls='md:border-r md:border-border md:pr-8')
    sidebar = Div(_section_label('Latest'), *[_sidebar_item(p, usr) for p in secondary],
                  cls='md:pl-6 mt-8 md:mt-0')
    top = Div(feature_col, sidebar, cls='grid grid-cols-1 md:grid-cols-[2fr_1fr] mb-12')

    if not grid_posts:
        return Div(top, id='blog-posts', cls='max-w-5xl mx-auto px-4 py-8')

    grid_section = Div(
        _section_label('More'),
        Div(*[_grid_card(p, usr) for p in grid_posts],
            cls='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 mt-2'))

    return Div(top, Div(cls='border-t border-border mb-8'), grid_section,
               id='blog-posts', cls='max-w-5xl mx-auto px-4 py-8')


# ── Post detail ───────────────────────────────────────────────────────────────

def locked_teaser(post):
    return Section(
        Div(
            _author_chip(post['author_name'], post['created_at']),
            _visibility_badge(post['visibility']),
            cls='flex items-center gap-3 mb-4'),
        ArticleTitle(post['title'], cls='mb-4 tracking-tight'),
        P(post['summary'], cls='mb-8 leading-relaxed'),
        Div(Div(cls='absolute inset-0 bg-gradient-to-b from-transparent via-background/60 to-background'),
            Div(Div(UkIcon('lock', width=24, height=24, cls=_ACCENT),
                    H3('Members only', cls='m-0 tracking-tight'),
                    P('Sign in to read the full post.', cls=f'{TextT.sm} m-0'),
                    A('Sign in with Google', href=RouteOverrides.lgn, cls=f'uk-btn {ButtonT.primary} {ButtonT.sm} mt-2'),
                    A('or create a free account', href=RouteOverrides.lgn, cls=f'{_ACCENT} text-xs underline-offset-2 hover:underline'),
                    cls='flex flex-col items-center gap-2 text-center'),
                cls='absolute bottom-8 left-0 right-0 flex justify-center'),
            cls='relative min-h-[200px] overflow-hidden rounded-lg'),
        cls='max-w-2xl mx-auto px-4 py-12')

def post_detail(post, usr=None):
    if post['visibility'] == 'members' and not usr: return locked_teaser(post)
    back = A('← All posts', href='/blog',
         cls=f'{_ACCENT} text-xs font-mono hover:underline mb-8 block transition-opacity opacity-70 hover:opacity-100')
    meta = Div(
        _author_chip(post['author_name'], post['created_at']),
        _visibility_badge(post['visibility']), cls='flex items-center gap-3 mb-6')
    title = ArticleTitle(post['title'], cls='mb-4 tracking-tight')
    body = Article(render_md(post['body'], class_map_mods=_MD_MODS, img_dir='/static/blog', renderer=BlogRenderer),
                   cls='overflow-auto')
    return Section(back, meta, title, body, cls='max-w-3xl mx-auto px-4 py-12')


# ── New post form ─────────────────────────────────────────────────────────────

def new_post_form(err_msg=None):
    back = A('← All posts', href='/blog',
         cls=f'{_ACCENT} text-xs font-mono hover:underline mb-6 block transition-opacity opacity-70 hover:opacity-100')
    heading = H1('Write a post', cls='mb-8 tracking-tight')
    err = P(err_msg, cls='text-danger text-sm') if err_msg else None

    return Section(
        Div(back, heading,
            Form(err,
                LabelInput('Title', id='title', placeholder='What did you build, learn, or break?'),
                LabelInput('Summary', id='summary', placeholder='One sentence. What should readers expect?'),
                LabelTextArea('Body', id='body', rows=14, placeholder='Write in Markdown.', input_cls='font-mono text-xs'),
                LabelSelect(
                    Option('Public — anyone can read', value='public', selected=True),
                    Option('Members only — requires sign-in', value='members'),
                    label='Visibility', id='visibility', name='visibility'),
                Div(
                    Button('Publish', cls=[ButtonT.primary, ButtonT.sm]),
                    A('Cancel', href='/blog', cls=f'uk-btn {ButtonT.ghost} {ButtonT.sm}'),
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
              cls=f'{TextT.sm} mb-4'),
            A('Write your first post', href='/blog/new', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}'),
            cls='text-center')
    else:
        cta = Div(
            P('Sign in with Google and this becomes your blog. Same code, your content.',
              cls=f'{TextT.sm} mb-4'),
            A('Sign in with Google', href=RouteOverrides.lgn, cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}'),
            cls='text-center')

    return Section(
        Card(CardBody(
            H2('lego is the template', cls='mb-2 text-center tracking-tight'),
            P('8 packages. 4 years. One side project that kept growing.',
              cls=f'{TextT.sm} text-center'),
            pkg_badges,
            P('Each package started as a problem in a side project. lego wraps the ones you need for a '
              'production-ready web app: auth, caching, backups, theming, this blog.',
              cls='text-center mx-auto mb-6 text-sm'),
            cta)),
        cls='max-w-2xl mx-auto px-4 py-16')
