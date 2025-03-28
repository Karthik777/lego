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
def wlcm(req): return welcome()
bodykw = {"class": "neo-brutalism"}
exc_h = {404: not_found}
app, rt = fast_app(hdrs=hdrs, bodykw=bodykw, secret_key=cfg.jwt_scrt, live=True, exception_handlers=exc_h)

# connect your blocks. you can override the routes in blocks placed before the last one
auth.connect(app)

# add default routes. these can be overridden by the blocks. the first in line wins.
app.get("/")(wlcm)
serve()


# if you want to log into a file instead of default stream logging
# This would replace the default stream logging
# import uvicorn
# from core import setup_logging
# if __name__ == "__main__":
#     setup_logging()
#     uvicorn.run(f'app:app', host='0.0.0.0', port=5001,
#                 reload=cfg.mode=="dev", reload_includes=None,
#                 reload_excludes=None)

