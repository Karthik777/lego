from fasthtml.common import Meta, Favicon, Socials, Link, serve
from monsterui.core import *
from core import cfg, welcome, not_found as nf
import auth

hdrs = [
    Meta(charset='UTF-8'),
    Meta(name='description', content=cfg.site_description),
    Meta(name='author', content=cfg.site_author),
    Meta(name='keywords', content=cfg.site_keywords),
    *Favicon('/static/favicon.ico', '/static/favicon-dark.ico'),
    *Socials(title=cfg.app_nm, description=cfg.site_description, site_name=cfg.domain, image=f'/static/site.png', url=''),
    Theme.neutral.headers(daisy=False, katex=False, radii=ThemeRadii.md),
    Link(rel="stylesheet", href="/static/css/theme.css")
    ]


def not_found(req, exc): return nf()
bodykw = {"class": "neo-brutalism"}
exc_h = {404: not_found}
app, rt = fast_app(hdrs=hdrs, bodykw=bodykw, secret_key=cfg.jwt_scrt, live=True, exception_handlers=exc_h)
app.get("/")(welcome)

# connect your blocks. you can override the routes in blocks placed before the last one
auth.connect(app)
serve()