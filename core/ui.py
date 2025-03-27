from fasthtml.common import *
from monsterui.franken import *
from monsterui.foundations import *
from .cfg import cfg as s

__all__ = ['avatar_menu', 'language_switcher', 'landing', 'welcome_page', 'placeholder',
           'navbar', 'theme_switcher', 'svg', 'montage', 'typewriter', 'base',
           'Badge', 'BadgeT', 'BadgePresetsT', 'PresetsT', 'welcome', 'not_found']

class PresetsT:
    shine = "bg-background shadow-[0_4px_20px_rgba(0,0,0,0.1)] animate-shine"


class BadgeT:
    md, sm = "px-2 py-1", "px-1.5 py-0.5"
    current = "text-primary bg-secondary"
    rounded, pill = "rounded-md", "rounded-full"
    red = "bg-red-50 text-red-900 dark:bg-red-400/10 dark:text-red-400"
    yellow = "bg-yellow-50 text-yellow-900 dark:bg-yellow-400/10 dark:text-yellow-500"
    green = "bg-green-50 text-green-900 dark:bg-green-500/10 dark:text-green-500"
    gray = "bg-gray-50 text-gray-900 dark:bg-gray-400/10 dark:text-gray-400"
    blue = "bg-blue-50 text-blue-900 dark:bg-blue-400/10 dark:text-blue-400"
    indigo = "bg-indigo-50 text-indigo-900 dark:bg-indigo-400/10 dark:text-indigo-400"
    purple = "bg-purple-50 text-purple-900 dark:bg-purple-400/10 dark:text-purple-400"
    pink = "bg-pink-50 text-pink-900 dark:bg-pink-400/10 dark:text-pink-400"
    invert = "dark:invert"


class BadgePresetsT:
    default = stringify([BadgeT.current, BadgeT.md, BadgeT.rounded])
    sm = stringify([BadgeT.current, BadgeT.sm, BadgeT.rounded])
    sm_strike = stringify([BadgeT.gray, BadgeT.sm, BadgeT.rounded, "line-through"])

def Badge(*c, cls=BadgePresetsT.default, **kwargs):
    return Span(c,cls=('inline-flex items-center text-xs font-medium', stringify(cls)),**kwargs)


def avatar_menu(img_path=None):
    return Div(
        Div(
            Button(cls=(ButtonT.icon, ButtonT.sm))(
                svg(img_path, cls="uk-comment-avatar uk-border-circle uk-box-shadow-small uk-border-primary")
                if img_path else UkIcon("user")),
            Div(
                Ul(cls="uk-nav uk-nav-default")(
                    Li("Getting Started", cls="uk-nav-header"),
                    Li(A("Home", href="/")),
                    Li(A("Documentation", href="/docs")),
                    Li(cls="uk-nav-divider"),
                    Li("Features", cls="uk-nav-header"),
                    Li(A("Karaoke Player", href="/karaoke")),
                    Li(A("Showcase", href="/showcase"))
                ),
                cls="uk-card uk-card-body uk-card-default uk-drop",
                uk_drop="mode: click; offset: 8; pos: bottom-right"
            ),
            cls="uk-inline"
        ),
        cls="uk-position-relative"
    )


def language_switcher(cls="", langs: list[dict[str, str]] = None):
    langs = langs if langs else [
        {"key": "sa", "text": "सं"},{"key": "hi", "text": "हि"},{"key": "en", "text": "en"},
        {"key": "ta", "text": "த"},{"key": "te", "text": "తె"},{"key": "kn", "text": "ಕ"},
        {"key": "ml", "text": "മ"},
    ]
    return Div(Div(
            Button(cls=(ButtonT.icon, ButtonT.sm))(UkIcon("globe")),
            Div(
                Div("Language", cls="uk-card-title uk-margin-medium-bottom"),
                Div(
                    *[Button(lang["text"], cls=f"{ButtonT.sm} {ButtonT.secondary} {ButtonT.icon}", data_language=lang["key"],
                             onclick="setLanguage(this.dataset.language); return false;") for lang in langs],
                    cls="uk-grid-small uk-child-width-auto uk-grid gap-4"
                ),
                cls="uk-card uk-card-body uk-card-default uk-drop",
                uk_drop="mode: click; offset: 8; pos: bottom-right"
            ),
            cls="uk-inline"
        ),
        cls=f"flex gap-4 {cls}")


class NavBarT:
    default = "top-0 right-0 left-0 z-50 border-b border-muted bg-background"
    glass = "top-0 right-0 left-0 z-50 bg-background/80 backdrop-blur-md border-b border-muted/50"
    shining = ("top-0 right-0 left-0 z-50 bg-background shadow-[0_4px_20px_rgba(0,0,0,0.1)] "
               "border-b border-muted animate-shine")


def navbar(auth, title="", style=NavBarT.default, cls="w-full sticky", mobile_cls=""):
    auth_ok = bool(auth)
    inc_th_sw, inc_lang, inc_avtr, avtr_url = True, True, auth_ok, None
    if auth_ok: avtr_url = auth.get("avatar_url", None)
    cmps = [(avatar_menu(avtr_url), inc_avtr), (language_switcher(), inc_lang), (theme_switcher(), inc_th_sw)]
    right_content = Div(*[c for c, inc in cmps if inc], cls="flex items-center gap-4")
    return Div(cls=(style, cls))(Nav(H4(title, cls="m-0"), right_content,
                                     cls=f"px-4 py-1 justify-between flex items-center {mobile_cls}"))


def theme_switcher(cls="", heading="Customise", sub_heading="theme selection"):
    return DivCentered(cls=f"flex gap-4 {cls}", vstack=False)(
        Div(cls="relative inline-block")(
            Button(cls=(ButtonT.icon, ButtonT.sm))(UkIcon("palette")),
            Div(
                H3(heading, cls="m-2"),
                P(sub_heading, cls=(TextT.muted, "mt-2 p-2")),
                ThemePicker(),
                cls="dropdown-content card card-body w-96",
                data_uk_dropdown="mode: click; pos: bottom-right; offset: 8"
            )
        ))


def svg(svg_path, cls="", stroke_width=1, stroke_color="currentColor", w=16, h=16):
    svg_path = str(svg_path)
    svg_path = f"/{svg_path}" if not svg_path.startswith("/") else svg_path
    return Div(
        Img(src=svg_path, cls=cls, fill="currentColor", data_uk_svg=True, width=w, height=h,
            style=f"stroke:{stroke_color};stroke-width:{stroke_width}; max-width: 100%; max-height: 100%;"),
        cls="inline-flex items-center justify-center"
    )


def placeholder(message="placeholder text", back_link="/", back_text="Go Back Home"):
        return Div(cls=TextT.center)(
            P(cls=f"{TextT.lead} mb-4")(message),
            A(href=back_link, cls=f"{ButtonT.primary} uk-btn {ButtonT.sm}")(back_text)
        )


def montage(svg_paths, cols_sm=3, cols_md=5, cols_lg=6, rows=12, fill_screen=True, cls=BackgroundT.primary, svg_cls=None):
    if not svg_paths or len(svg_paths) == 0: return None
    svg_cls = ifnone(svg_cls, f"size-24 md:size-4/6 border-2 border-current border-dotted m-2 {PresetsT.shine}")
    svgs = [svg(str(p), svg_cls) for p in svg_paths]
    svg_list = svgs * (cols_lg*rows*2 // len(svgs) + 1 if fill_screen else 1)  # Rough fill estimate
    return Grid(*svg_list, cols_sm=cols_sm, cols_md=cols_md, cols_lg=cols_lg, cols_min=3, cols_xl=8, cls=cls,
                data_uk_grid="masonry: True")



def typewriter(stat_txt=None, dyn_txt_lst=None,
               type_sp=250, del_sp=100, pause_end=1000, pause_start=500, txt_cls=None,
               cls=f"m-4 p-4 min-w-64"):
    stat_txt, dyn_txt_lst = ifnone(stat_txt, f" {s.typwrtr_stat_txt}"), ifnone(dyn_txt_lst, s.typwrtr_dyn_txt.split(","))
    txt_cls = ifnone(txt_cls, f"{TextT.lg} {TextT.bold}")
    return Div(P(cls=txt_cls)(
        Span("", id="typewriter", cls="pop border-r-2 border-current blink"), Span(stat_txt)),
        Now(
            f"let a={dyn_txt_lst},i=0,j=0,d=false,t;"
            "function w(){if(!e)return;const s=a[i];e.text(d?s.slice(0,j):s.slice(0,j+1));"
            f"if(!d&&j==s.length-1)setTimeout(()=>(d=true,w()),{pause_end});"
            f"else if(d&&j==0){{d=false;i=(i+1)%a.length;setTimeout(w,{pause_start});}}"
            f"else{{t=setTimeout(w,d?{del_sp}:{type_sp});j+=d?-1:1;}}"
            "}w()", sel="#typewriter"
        ),
        On("clearTimeout(timeout);",event="htmx:beforeCleanupElement", sel="#typewriter", me=False), cls=cls)


def welcome_page(img_dir=Path("static/svg"), content=None, title=None, cls=None, cont_cls=None):
    img_paths = globtastic(img_dir, file_re=".svg|.png|.jpg")
    cls = ifnone(cls,"text-center bg-background/80 backdrop-blur-md p-4 sm:p-8 border-2 border-current")
    cont_cls = ifnone(cont_cls,"min-h-screen flex items-center justify-center mt-8")
    t = Title(title) if title else None
    m = Div(montage(img_paths), cls="overflow-hidden uk-position-cover mt-10") if img_paths else None
    con = Container(Div(H2(title, cls=(PresetsT.shine)), typewriter(), content, cls=cls), cls=cont_cls)
    return t, Section(m, con)


def landing(content, title=s.app_nm, auth=None):
    return base(welcome_page(content=content, title=title), auth=auth, style=NavBarT.glass)


def base(content=None, auth=None, title=s.app_sh, style=NavBarT.glass):
    return Div(cls="figma-board min-h-screen")(
        Title(title),
        navbar(auth=auth, title=title, style=style),
        Div(content if content else None, cls=f"uk-width-1-1")
    )

def welcome(): return landing(placeholder(f"Welcome to {s.app_nm}"))
def not_found(): return landing(placeholder("The page you're looking for doesn't exist or has been moved."))