import re
from datetime import datetime
from fasthtml.common import *
from monsterui.all import *
from monsterui.franken import render_md, FrankenRenderer, Iframe
from lego.core import cfg as s, RouteOverrides as r, not_prod, main, mode_switcher, NavBarT, PresetsT, \
    Badge, BadgePresetsT
from lego.church.cfg import Routes, cfg

__all__ = ['church_base', 'church_not_found', 'home_page', 'about_page', 'teachings_index', 'teaching_detail',
           'assembly_page', 'beliefs_page', 'contact_page']

# ── Video embed markdown renderer ──────────────────────────────────────────────

def _yt_video_id(url):
    for pat in (r'youtu\.be/([^?&\s]+)', r'youtube\.com/watch\?.*v=([^&\s]+)', r'youtube\.com/shorts/([^?&\s]+)'):
        m = re.search(pat, url)
        if m: return m.group(1)
    return None

def _gdrive_video_id(url):
    for pat in (r'drive\.google\.com/file/d/([^/?&\s]+)', r'drive\.google\.com/open\?id=([^&\s]+)',
                r'drive\.google\.com/uc\?id=([^&\s]+)'):
        m = re.search(pat, url)
        if m: return m.group(1)
    return None

def _video_embed(src):
    return to_xml(Div(Iframe(src=src, cls='absolute inset-0 w-full h-full rounded-xl', allowfullscreen=True,
                       data_uk_responsive=True), cls='relative aspect-video my-6'))

class ChurchRenderer(FrankenRenderer):
    def render_block_code(self, token):
        lang = (token.language or 'text').strip()
        url = (token.children[0].content if token.children else '').strip()
        if lang == 'youtube':
            vid = _yt_video_id(url)
            return _video_embed(f'https://www.youtube.com/embed/{vid}') if vid else to_xml(A(url, href=url))
        if lang == 'gdrive':
            vid = _gdrive_video_id(url)
            return _video_embed(f'https://drive.google.com/file/d/{vid}/preview') if vid else to_xml(A(url, href=url))
        return super().render_block_code(token)

_MD_MODS = {'h1': 'uk-h1 mt-10 mb-5', 'h2': 'uk-h2 mt-8 mb-4', 'h3': 'uk-h3 mt-6 mb-3',
            'p': 'leading-relaxed mb-5', 'ul': 'uk-list uk-list-bullet space-y-2 mb-5 ml-6',
            'ol': 'uk-list uk-list-decimal space-y-2 mb-5 ml-6', 'hr': 'my-8 border-border'}

def _fmt_date(ts): return datetime.fromtimestamp(ts).strftime('%b %d, %Y')

def _yt_thumb(body):
    m = re.search(r'```youtube\s+(https?://\S+)\s*```', body, re.DOTALL)
    if not m: return None
    vid = _yt_video_id(m.group(1).strip())
    return f'https://img.youtube.com/vi/{vid}/maxresdefault.jpg' if vid else None


# ── Shell: nav + footer ────────────────────────────────────────────────────────

_NAV_LINKS = [(Routes.about, 'About'), (Routes.teachings, 'Teachings'),
              (Routes.assembly, 'Online Assembly'), (Routes.beliefs, 'Beliefs'), (Routes.contact, 'Contact')]

def _boost(href, **kw): return dict(href=href, hx_get=href, hx_target='#main-content', hx_push_url='true', **kw)

def _nav_link(href, label, active):
    cls = 'text-sm font-medium hover:opacity-70 transition-opacity whitespace-nowrap' + \
        (' underline underline-offset-4' if active else ' opacity-80')
    return A(label, cls=cls, **_boost(href))

def church_navbar(active='/'):
    brand = A(H4(s.app_nm, cls='m-0 tracking-tight'), **_boost('/'))
    links = Div(*[_nav_link(h, l, active == h) for h, l in _NAV_LINKS],
                cls='flex flex-wrap items-center gap-x-6 gap-y-2')
    cta = A('Join Online Assembly', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm} whitespace-nowrap',
            **_boost(Routes.assembly))
    right = Div(links, mode_switcher(), cta, cls='flex flex-wrap items-center gap-4 justify-end')
    return Div(Nav(brand, right, cls='pl-4 pr-2 py-3 justify-between flex flex-wrap items-center gap-3'),
               cls=[NavBarT.default, 'w-full sticky'])

def church_footer():
    bits = [A(s.contact_email, href=f'mailto:{s.contact_email}', cls='hover:underline')]
    if s.instagram_handle:
        handle = s.instagram_handle.lstrip('@')
        bits.append(A(f'@{handle}', href=f'https://instagram.com/{handle}', target='_blank',
                       rel='noopener noreferrer', cls='hover:underline'))
    return Footer(
        Div(P(f'© {datetime.now().year} {s.app_nm}', cls='text-xs opacity-70'),
            Div(*bits, cls='flex gap-4 text-xs'),
            cls='max-w-5xl mx-auto px-4 py-8 flex flex-col sm:flex-row justify-between items-center gap-3 '
                'border-t border-border mt-16'))

def church_base(content, title=None, active='/'):
    ttl = f'{title} · {s.app_nm}' if title else s.app_nm
    return Title(ttl), Div(church_navbar(active), main(content), church_footer())

def church_not_found():
    content = Div(H2("Page not found", cls='mb-3 tracking-tight'),
                  P("The page you're looking for doesn't exist or has moved.", cls='opacity-80 mb-6'),
                  A('← Back home', cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}', **_boost('/')),
                  cls='max-w-md mx-auto text-center py-32 px-4')
    return church_base(content, title='Not Found')


# ── Home ────────────────────────────────────────────────────────────────────────

def home_page():
    hero = Section(
        Div(H1('Belonging in Christ for life on the move.', cls='tracking-tight mb-4'),
            P(f'Weekly online assembly · {s.assembly_day_time}.', cls=f'{TextT.lg} opacity-80 mb-8'),
            A('Join Online Assembly', cls=f'uk-btn {ButtonT.primary} {ButtonT.lg}', **_boost(Routes.assembly)),
            cls='max-w-2xl mx-auto text-center'),
        cls='px-4 py-24 md:py-32')
    values = [('Christ-centred', 'Every gathering points back to Jesus.'),
              ('Bible-rooted', 'Scripture shapes what we teach and how we live.'),
              ('Online-first', 'Wherever you are, you belong.')]
    strip = Section(
        Div(*[Div(H3(t, cls='mb-1'), P(d, cls=f'{TextT.sm} opacity-80')) for t, d in values],
            cls='grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto text-center mb-8'),
        Div(A('Learn more about us →', cls='text-sm hover:underline', **_boost(Routes.about)), cls='text-center'),
        cls='px-4 pb-24')
    return Div(hero, strip)


# ── About ───────────────────────────────────────────────────────────────────────

def about_page():
    values = [('Christ-centred', 'Jesus is the centre of everything we do — our teaching, our gathering, our life together.'),
              ('Bible-rooted', 'Scripture is our foundation. We teach it plainly and trust it fully.'),
              ('Online-first', 'We exist online first, built for people whose life keeps them on the move.')]
    cards = Div(*[Card(CardBody(H3(t, cls='mb-2'), P(d, cls=f'{TextT.sm} opacity-80'))) for t, d in values],
                cls='grid grid-cols-1 md:grid-cols-3 gap-6 mb-12')
    note = Card(CardBody(
        H3('Not a replacement for local churches', cls='mb-2'),
        P(f'{s.app_nm} is not meant to replace your local church. We encourage every believer to connect with a '
          'local church wherever possible — this online assembly is here for those who, for a season or because '
          'life keeps them moving, don\'t currently have one nearby.', cls=f'{TextT.sm} opacity-80')),
        cls=PresetsT.standout)
    return Section(H1('About Us', cls='mb-8 tracking-tight'), cards, note, cls='max-w-4xl mx-auto px-4 py-16')


# ── Teachings ─────────────────────────────────────────────────────────────────

def _teaching_card(t):
    href = f'/teachings/{t["slug"]}'
    thumb = _yt_thumb(t.get('body', ''))
    img = Div(Img(src=thumb, alt='', cls='w-full h-48 object-cover'), cls='overflow-hidden rounded-t-md') \
        if thumb else Div(UkIcon('player-play', width=28, height=28, cls='opacity-60'),
                           cls='w-full h-48 flex items-center justify-center bg-muted rounded-t-md')
    body = Div(H3(t['title'], cls='mb-1 tracking-tight leading-snug'),
               Span(_fmt_date(t['created_at']), cls='text-xs font-mono opacity-60 block mb-2'),
               P(t['summary'], cls=f'{TextT.sm} opacity-80'), cls='p-4')
    return Div(img, body, cls='rounded-md border border-border cursor-pointer hover:opacity-90 '
               'transition-opacity overflow-hidden', **_boost(href))

def teachings_index(all_teachings):
    hero = Div(H1('Teachings', cls='mb-3 tracking-tight'),
               P('Weekly videos, short Bible reflections, and scripture posts. Downloadable notes are coming soon.',
                 cls=f'{TextT.lg} opacity-80 mb-10'))
    if not all_teachings:
        empty = Div(UkIcon('player-play', width=32, height=32, cls='opacity-50 mb-3'),
                    P('New teachings are posted weekly — check back soon.'),
                    cls='flex flex-col items-center py-20 gap-2 text-center')
        return Section(hero, empty, cls='max-w-4xl mx-auto px-4 py-16')
    cards = Div(*[_teaching_card(t) for t in all_teachings], cls='grid grid-cols-1 md:grid-cols-2 gap-8')
    return Section(hero, cards, cls='max-w-5xl mx-auto px-4 py-16')

def teaching_detail(t):
    back = A('← All teachings', cls='text-xs font-mono hover:underline mb-8 block opacity-70 hover:opacity-100',
              **_boost(Routes.teachings))
    title = H1(t['title'], cls='mb-2 tracking-tight')
    meta = Span(_fmt_date(t['created_at']), cls='text-xs font-mono opacity-60 block mb-6')
    summary = P(t['summary'], cls=f'{TextT.lg} opacity-80 mb-8') if t['summary'] else None
    body = Article(render_md(t['body'], class_map_mods=_MD_MODS, renderer=ChurchRenderer))
    return Section(back, title, meta, summary, body, cls='max-w-3xl mx-auto px-4 py-16')


# ── Online Assembly ─────────────────────────────────────────────────────────────

def assembly_page():
    if s.zoom_join_url:
        zoom_cta = A('Join Zoom Meeting', href=s.zoom_join_url, target='_blank', rel='noopener noreferrer',
                      cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}')
    else:
        zoom_cta = A('Email us for the Zoom link', href=f'mailto:{s.contact_email}?subject=Join Sunday Online Assembly',
                      cls=f'uk-btn {ButtonT.primary} {ButtonT.sm}')
    hero = Div(H1('Online Assembly', cls='mb-3 tracking-tight'),
               P(f'{s.assembly_day_time}, on Zoom.', cls=f'{TextT.lg} opacity-80 mb-6'),
               zoom_cta, cls='mb-16 text-center max-w-xl mx-auto')
    expect = [('book-open', 'Bible Teaching', 'A clear, practical look at Scripture each week.'),
              ('heart-handshake', 'Prayer', 'We bring our lives — and each other — before God.'),
              ('users', 'Fellowship', 'Real connection, even at a distance.'),
              ('sparkles', 'Encouragement', 'A word to carry with you into the week.')]
    expect_grid = Div(*[Div(UkIcon(ic, width=28, height=28, cls='mb-3 opacity-80 mx-auto'), H3(t, cls='mb-1'),
                             P(d, cls=f'{TextT.sm} opacity-80')) for ic, t, d in expect],
                       cls='grid grid-cols-2 md:grid-cols-4 gap-8 mb-20 text-center')
    gathering = Card(CardBody(
        Badge('Annual Gathering', cls=BadgePresetsT.primary_sm),
        H2('Easter Gathering', cls='mt-3 mb-2 tracking-tight'),
        P(f'Once a year we hope to gather in person — {s.gathering_info}. Details will be shared here and on our '
          'socials as they\'re confirmed.', cls=f'{TextT.sm} opacity-80')), cls=PresetsT.standout)
    return Section(hero, expect_grid, gathering, cls='max-w-4xl mx-auto px-4 py-16')


# ── Beliefs ─────────────────────────────────────────────────────────────────────

def beliefs_page():
    return Section(H1('Statement of Beliefs', cls='mb-8 tracking-tight'),
                   Article(render_md(cfg.beliefs_md, class_map_mods=_MD_MODS)),
                   cls='max-w-3xl mx-auto px-4 py-16')


# ── Contact ─────────────────────────────────────────────────────────────────────

def contact_page():
    cards = [Card(CardBody(UkIcon('mail', width=24, height=24, cls='mb-3 opacity-80'), H3('Email', cls='mb-1'),
                            A(s.contact_email, href=f'mailto:{s.contact_email}', cls=f'{TextT.sm} hover:underline')))]
    if s.instagram_handle:
        handle = s.instagram_handle.lstrip('@')
        cards.append(Card(CardBody(UkIcon('brand-instagram', width=24, height=24, cls='mb-3 opacity-80'),
                                    H3('Instagram', cls='mb-1'),
                                    A(f'@{handle}', href=f'https://instagram.com/{handle}', target='_blank',
                                      rel='noopener noreferrer', cls=f'{TextT.sm} hover:underline'))))
    cards.append(Card(CardBody(
        UkIcon('heart-handshake', width=24, height=24, cls='mb-3 opacity-80'),
        H3('Prayer & Pastoral Support', cls='mb-1'),
        P('Going through something and need prayer or to talk?', cls=f'{TextT.sm} opacity-80 mb-3'),
        A('Request prayer', href=f'mailto:{s.contact_email}?subject=Prayer Request',
          cls=f'uk-btn {ButtonT.primary} {ButtonT.xs}'))))
    grid = Div(*cards, cls='grid grid-cols-1 md:grid-cols-3 gap-6')
    return Section(H1('Contact Us', cls='mb-8 tracking-tight'), grid, cls='max-w-4xl mx-auto px-4 py-16')
