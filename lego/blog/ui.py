import html, re
from collections import Counter
from datetime import datetime
from fastcore.xml import *
from fastcore.xtras import timed_cache
from fastcore.basics import NotStr
from fasthtml.common import *
from fasthtml.components import Iframe
from mistletoe import Document
try: from mistletoe.html_renderer import HtmlRenderer
except ImportError: from mistletoe.html_renderer import HTMLRenderer as HtmlRenderer
from lego.blog.data import posts
from lego.core import RouteOverrides, init_js_then_use, lc_icon, TextT, ButtonT
from lego.blog.cfg import Routes

class BlogRenderer(HtmlRenderer):
    'Semantic-HTML markdown renderer: Oat styles the output tags, no class soup needed.'
    img_dir = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._img_idx = 0

    def render_image(self, token):
        title = f' title="{token.title}"' if getattr(token, 'title', None) else ''
        src = token.src
        if self.img_dir and not src.startswith(('http://', 'https://', '/')): src = f'{self.img_dir}/{src}'
        alt = token.children[0].content if token.children else ''
        float_cls = 'float-r' if self._img_idx % 2 == 0 else 'float-l'
        self._img_idx += 1
        return (f'<figure class="blog-figure {float_cls}">'
                f'<img src="{src}" alt="{alt}"{title}>'
                f'<figcaption>{alt}</figcaption>'
                f'</figure>')

    def render_block_code(self, token):
        lang = (token.language or 'text').strip()
        if lang == 'col': return '<div style="break-after:column"></div>'
        if lang == 'youtube':
            url = (token.children[0].content if token.children else '').strip()
            vid = _yt_video_id(url)
            if not vid: return to_xml(A(url, href=url))
            return to_xml(Div(Iframe(src=f'https://www.youtube.com/embed/{vid}?enablejsapi=1&mute=1',
                                     allowfullscreen=True, allow='autoplay; encrypted-media'),
                              cls='aspect-video my-6 yt-inview'))
        code = html.escape(token.children[0].content if token.children else '')
        return (
            f'<div class="my-6" style="break-inside:avoid">'
            f'<pre style="margin:0">'
            f'<code class="language-{lang}">{code}</code>'
            f'</pre>'
            f'</div>'
        )

def render_md(md, img_dir=None, renderer=None, **kw):
    with (renderer or BlogRenderer)() as r:
        r.img_dir = img_dir
        return NotStr(r.render(Document(md)))

__all__ = ['blog_hero', 'post_card', 'post_list', 'locked_teaser', 'post_detail', 'new_post_form', 'showcase_cta',
           'render_md', 'BlogRenderer']

# ── UI helpers ────────────────────────────────────────────────────────────────

_ACCENT    = 'text-primary'
_ACCENT_BG = 'bg-primary-soft'

def _fmt_date(ts): return datetime.fromtimestamp(ts).strftime('%b %d, %Y')

def _author_chip(name, date_ts):
    return Div(Span(name, cls=f'font-medium {_ACCENT}'),
        Span('·', cls='mx-1 opacity-40'), Span(_fmt_date(date_ts), cls='font-mono'),
        cls='flex items-center text-sm text-light')

def _visibility_badge(v):
    if v != 'members': return ''
    return Span(lc_icon('lock', 10), ' Members', cls='badge outline')

def _yt_video_id(url):
    for pat in (r'youtu\.be/([^?&\s]+)', r'youtube\.com/watch\?.*v=([^&\s]+)', r'youtube\.com/shorts/([^?&\s]+)'):
        m = re.search(pat, url)
        if m: return m.group(1)
    return None

def _first_image(body):
    m = re.search(r'!\[.*?\]\((.+?)\)', body)
    if m:
        src = m.group(1)
        return src if src.startswith('/') else f'/static/blog/{src}'
    m = re.search(r'```youtube\s+(https?://\S+)\s*```', body, re.DOTALL)
    if m:
        vid = _yt_video_id(m.group(1).strip())
        if vid: return f'https://img.youtube.com/vi/{vid}/maxresdefault.jpg'
    return None

def _sign_in_cta(_slug):
    return Div(lc_icon('lock', 16, cls='text-light'),
        P('Members only', cls=f'{TextT.sm} m-0'),
        A('Sign in to read', hx_get=f'{RouteOverrides.lgn}?next=/blog/{_slug}',
          hx_target='body', hx_swap='beforeend', cls=f'{ButtonT.primary} {ButtonT.xs}'),
        cls='locked-overlay')


# ── Hero ──────────────────────────────────────────────────────────────────────

_CODE_PEEK = '''\
@rt('/blog/{slug}')
def blog_post(req, auth, slug:str):
    post = posts[slug]
    if post.visibility == 'public':
        return post_detail(post, auth)
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
        Div(A('Write a post' if usr else 'Sign in to write', hx_get=f'{RouteOverrides.lgn}?next={Routes.new}',
              hx_target='body', hx_swap='beforeend', cls=f'{ButtonT.primary} {ButtonT.sm}'),
            A('Read the story', href='#blog-posts', cls=f'{ButtonT.ghost} {ButtonT.sm}'),
            cls='flex gap-3'), cls='flex flex-col justify-center')

    # Terminal-style code window
    right = Div(
        Div(
            Div(
                Div(cls='dot', style='background:rgb(239 68 68 / .8)'),
                Div(cls='dot', style='background:rgb(234 179 8 / .8)'),
                Div(cls='dot', style='background:rgb(34 197 94 / .8)'),
                Span('blog.py', cls='text-xs font-mono ml-2', style='color:#a1a1aa'),
                Span(f'{len(_CODE_PEEK.splitlines())} lines', cls='text-xs font-mono ml-auto', style='color:#52525b'),
                cls='win-bar'),
            Pre(Code(_CODE_PEEK, cls='language-python text-xs leading-relaxed')),
            cls='code-window'),
        cls='flex items-center min-w-0')

    return Section(
        *_hljs(),
        Div(left, right, cls='hero-grid'),
        cls='section-pad max-w-5xl mx-auto')


# ── Post card ─────────────────────────────────────────────────────────────────

def _section_label(text):
    return P(text, cls='text-xs font-mono tracking-widest uppercase text-light border-t pt-2 mb-3')

def _featured_card(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    img_src = _first_image(post.get('body', ''))
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    headline = H2(post['title'], cls='tracking-tight leading-tight mb-3')
    img_el = Div(Img(src=img_src, alt='', cls='img-featured'),
                 cls='overflow-hidden mb-4') if img_src else None
    byline = Div(
        Span(f'BY {post["author_name"].upper()}', cls='text-xs font-mono tracking-wider text-light'),
        Span(' · ', cls='mx-1 text-light text-xs opacity-40'),
        Span(_fmt_date(post['created_at']), cls='text-xs font-mono text-light'),
        cls='flex items-center mt-3')
    if locked:
        body = Div(Div(cls='fade-overlay'),
                   _sign_in_cta(post['slug']), cls='relative min-h-60px overflow-hidden')
    else:
        body = Div(P(post['summary'], cls='leading-relaxed'), byline)
    return Div(_section_label('Featured'), headline, img_el, body,
               cls='cursor-pointer hover-dim', **kw)

def _sidebar_item(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    tag = Span('Members', cls='text-xs font-mono tracking-wider uppercase text-primary block mb-1') if locked else ''
    title = H3(post['title'], cls='leading-snug tracking-tight mb-1')
    date = Span(_fmt_date(post['created_at']), cls='text-xs font-mono text-light')
    return Div(tag, title, date,
               cls='py-3 border-b cursor-pointer hover-dim', **kw)

def _grid_card(post, usr=None):
    locked = post['visibility'] == 'members' and not usr
    slug_href = f'/blog/{post["slug"]}'
    img_src = _first_image(post.get('body', ''))
    kw = dict(hx_get=slug_href, hx_target='#main-content', hx_push_url='true')
    img_el = Div(Img(src=img_src, alt='', cls='w-full h-40 object-cover'),
                 cls='overflow-hidden mb-3') if img_src else None
    tag = Span('Members', cls='text-xs font-mono tracking-wider uppercase text-primary block mb-1') if locked else ''
    title = H3(post['title'], cls='leading-snug tracking-tight mb-2')
    summary = P(post['summary'], cls=f'{TextT.sm} line-clamp-3 text-light')
    return Article(img_el, tag, title, summary,
                   cls='cursor-pointer hover-dim', **kw)

def post_card(post, usr=None, featured=False):
    return _featured_card(post, usr) if featured else _grid_card(post, usr)


# ── Post list ─────────────────────────────────────────────────────────────────
def post_list(all_posts, usr=None):
    if not all_posts:
        return Div(lc_icon('notebook', 32, cls='text-light mb-3'),
            P('No posts yet.', cls=TextT.sm), cls='flex flex-col items-center justify-center py-20 gap-2')

    featured, rest = all_posts[0], all_posts[1:]
    secondary, grid_posts = rest[:4], rest[4:]

    feature_col = Div(_featured_card(featured, usr), cls='feature-col')
    sidebar = Div(_section_label('Latest'), *[_sidebar_item(p, usr) for p in secondary],
                  cls='sidebar-col mt-8')
    top = Div(feature_col, sidebar, cls='post-top-grid mb-12')

    if not grid_posts:
        return Div(top, id='blog-posts', cls='max-w-5xl mx-auto px-4 py-8')

    grid_section = Div(
        _section_label('More'),
        Div(*[_grid_card(p, usr) for p in grid_posts],
            cls='post-grid mt-2'))

    return Div(top, grid_section, id='blog-posts', cls='max-w-5xl mx-auto px-4 py-8')


# ── Post detail ───────────────────────────────────────────────────────────────
def locked_teaser(post):
    _next = f'/blog/{post["slug"]}'
    _hx = dict(hx_get=f'{RouteOverrides.lgn}?next={_next}', hx_target='body', hx_swap='beforeend')
    return Section(
        Div(
            _author_chip(post['author_name'], post['created_at']),
            _visibility_badge(post['visibility']),
            cls='flex items-center gap-3 mb-4'),
        H1(post['title'], cls='mb-4 tracking-tight'),
        P(post['summary'], cls='mb-8 leading-relaxed'),
        Div(Div(cls='fade-overlay'),
            Div(Div(lc_icon('lock', 24, cls=_ACCENT),
                H3('Members only', cls='m-0 tracking-tight'),
                P('Sign in to read the full post.', cls=f'{TextT.sm} m-0'),
                A('Sign in with Google', **_hx, cls=f'{ButtonT.primary} {ButtonT.sm} mt-2'),
                A('or create a free account', **_hx, cls=f'{_ACCENT} text-xs underline-h'),
                    cls='flex flex-col items-center gap-2 align-center'),
            cls='bottom-strip'),
        cls='relative min-h-200px overflow-hidden rounded-lg'),
    cls='max-w-2xl mx-auto px-4 py-12')

def _hljs():
    base = 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@latest/build'
    hjc  = 'https://cdn.jsdelivr.net/gh/arronhunt/highlightjs-copy@latest/dist'
    dark_href  = f'{base}/styles/atom-one-dark.min.css'
    light_href = f'{base}/styles/atom-one-light.min.css'
    init = (f"const _hd='{dark_href}',_hl='{light_href}',_he=document.getElementById('hljs-theme');"
            "function _st(){if(_he)_he.href=document.documentElement.classList.contains('dark')?_hl:_hd;}"
            "_st();"
            "new MutationObserver(_st).observe(document.documentElement,{attributes:true,attributeFilter:['class']});"
            "hljs.addPlugin(new CopyButtonPlugin());"
            "htmx.onLoad(hljs.highlightAll);")
    return [
        Link(id='hljs-theme', rel='stylesheet', href=dark_href),
        Script(src=f'{base}/highlight.min.js'),
        Script(src=f'{base}/languages/python.min.js'),
        Link(rel='stylesheet', href=f'{hjc}/highlightjs-copy.min.css'),
        Style('code.hljs{display:block;padding:1.25rem;border-radius:.75rem;font-size:.875rem;line-height:1.625;overflow-x:auto}'
              'pre:has(>code.hljs){background:transparent!important;padding:0!important;margin:0!important}'),
        *init_js_then_use(f'{hjc}/highlightjs-copy.min.js', 'CopyButtonPlugin', init),
        ]
_NP_STYLE= Style('''.np-body{column-count:1} @media(min-width:768px){
.np-body{column-count:2;column-gap:2.5rem}.np-body p,.np-body h2,.np-body h3,.np-body h4,.np-body ul,
.np-body ol{break-inside:avoid}.np-body h2,.np-body h3,.np-body h4{break-before:avoid}}
''')

@timed_cache(3600)
def post_detail(post, usr=None):
    if post['visibility'] == 'members' and not usr: return locked_teaser(post)
    newspaper = post.get('layout', 'single') == 'newspaper'
    back = A('← All posts', href='/blog',
         cls=f'{_ACCENT} text-xs font-mono underline-h mb-8 block')
    meta = Div(_author_chip(post['author_name'], post['created_at']),
        _visibility_badge(post['visibility']), cls='flex items-center gap-3 mb-6')
    title = H1(post['title'], cls='mb-4 tracking-tight')
    body = Article(render_md(post['body'], img_dir='/static/blog'),
                   cls='np-body overflow-auto' if newspaper else 'overflow-auto')
    section_cls = 'max-w-5xl mx-auto px-4 py-12' if newspaper else 'max-w-3xl mx-auto px-4 py-12'
    extras = _hljs() + ([_NP_STYLE] if newspaper else [])
    return *extras, Section(back, meta, title, body, cls=section_cls)


# ── New post form ─────────────────────────────────────────────────────────────
@timed_cache(3600)
def new_post_form(err_msg=None):
    from lego.core import LabelInput, LabelTextArea, LabelSelect
    back = A('← All posts', href='/blog',
         cls=f'{_ACCENT} text-xs font-mono underline-h mb-6 block')
    heading = H1('Write a post', cls='mb-8 tracking-tight')
    err = P(err_msg, cls='text-danger text-sm') if err_msg else None

    return Section(Div(back, heading,
        Form(err,
            LabelInput('Title', id='title', placeholder='What did you build, learn, or break?'),
            LabelInput('Summary', id='summary', placeholder='One sentence. What should readers expect?'),
            LabelTextArea('Body', id='body', rows=14, placeholder='Write in Markdown.', input_cls='font-mono text-xs'),
            LabelSelect(
                Option('Public: anyone can read', value='public', selected=True),
                Option('Members only: requires sign-in', value='members'),
                label='Visibility', id='visibility', name='visibility'),
            Div(
                Button('Publish', cls=[ButtonT.primary, ButtonT.sm]),
                A('Cancel', href='/blog', cls=f'{ButtonT.ghost} {ButtonT.sm}'),
                cls='flex gap-3 pt-2'),
            cls='space-y-5 max-w-2xl mx-auto',
            hx_post='/blog/new', hx_target='#main-content'),cls='px-4 py-12'))


# ── Showcase CTA ──────────────────────────────────────────────────────────────

_PACKAGES = ['kosha', 'litesearch', 'dockeasy', 'vpseasy', 'cfeasy', 'lego', 'gheasy']

def showcase_cta(usr=None):
    pkg_badges = Div(
        *[Span(p, cls=f'{_ACCENT_BG} text-xs px-2 py-1 rounded-full font-mono') for p in _PACKAGES],
        cls='flex flex-wrap gap-2 justify-center my-6')

    if usr:
        cta = Div(
            P(f'You\'re signed in as {usr["display_name"]}. This is your blog now.', cls=f'{TextT.sm} mb-4'),
            A('Write your first post', href=Routes.new, cls=f'{ButtonT.primary} {ButtonT.sm}'), cls='align-center')
    else:
        cta = Div(
            P('Sign in with Google and this becomes your blog. Same code, your content.', cls=f'{TextT.sm} mb-4'),
            A('Sign in with Google', hx_get=f'{RouteOverrides.lgn}?next=/blog',
              hx_target='body', hx_swap='beforeend', cls=f'{ButtonT.primary} {ButtonT.sm}'), cls='align-center')

    return Section(
        Div(
            H2('lego is the template', cls='mb-2 align-center tracking-tight'),
            P('8 packages. 2 years. One side project that kept growing.',cls=f'{TextT.sm} align-center'),
            pkg_badges,
            P('Each package started as a problem in a side project. lego wraps the ones you need for a '
              'production-ready web app: auth, caching, backups, theming, this blog.',
              cls='align-center mx-auto mb-6 text-sm'),
            cta, cls='card'),
        cls='max-w-2xl mx-auto px-4 py-16')
