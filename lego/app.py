import os
from fasthtml.common import Meta, Favicon, Socials, Link, serve, Script, JSONResponse, Div, P
from fasthtml.common import *
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from .core import *
from lego import auth as a, blog as b, dash as d, hora as h

__all__ = ['launch', 'lego']

if cfg.purge: clear_cache()

hdrs = [
    *vendor_hdrs(),
    Meta(name='description', content=cfg.site_description),
    Meta(name='author', content=cfg.site_author),
    Meta(name='keywords', content=cfg.site_keywords),
    Meta(name='robots', content='index, follow'),
    Meta(name='theme-color', content='#FCA847'),
    Meta(name='apple-mobile-web-app-capable', content='yes'),
    Meta(name='apple-mobile-web-app-status-bar-style', content='default'),
    Meta(name='mobile-web-app-capable', content='yes'),
    Meta(name='mobile-web-app-status-bar-style', content='default'),
    *Favicon('/static/favicon.ico', '/static/favicon-dark.ico'),
    Link(rel='icon', type='image/svg+xml', href='/static/favicon.svg'),
    *Socials(title=cfg.app_nm, description=cfg.site_description, site_name=cfg.domain, image='/static/favicon.svg',
             url=cfg.domain), *themes()]

# fasthtml does `req.hdrs = deepcopy(self.hdrs)` on every request so a handler can add to
# the head for that response alone. Nothing here does, and the copy is not free: this list
# is thirty-odd nodes including the whole theme stylesheet, which came to ~350 recursive
# deepcopy calls on every request — including /health, which has no head at all.
# Serialised up front it is one string, and deepcopy of a str hands back the same object.
hdrs = [NotStr(to_xml(tuple(hdrs)))]

def nf(req, exc): return not_found()
kw,exh = {'class': 'hidden', 'hx-ext': 'preload', 'hx-boost': 'true'}, {404: nf, 500: nf, 403: nf}

# A page is 20-60KB of highly repetitive markup, which is what gzip is best at; the pages
# here go out at roughly a fifth of their size. minimum_size keeps it off the small htmx
# fragments, where the compression costs more than the bytes it saves.
mw = [Middleware(GZipMiddleware, minimum_size=1024)]

# default_hdrs=False and no `exts`: both would put CDN <script src> back in the head.
# vendor_hdrs() is the same set, served locally — see lego/core/ui.py.
lego, rt = fast_app(hdrs=hdrs, bodykw=kw, live=not_prod(), title=cfg.app_nm, default_hdrs=False, pico=False,
                    exception_handlers=exh, middleware=mw,
                    on_startup=start_scheduler, on_shutdown=stop_scheduler)

# serve versioned css/js (vurl ?v= links) immutable, ahead of the default static route
from starlette.routing import Mount
for _d in ('vendor', 'assets'):
    if (Path('static')/_d).exists():
        lego.router.routes.insert(0, Mount(f'/static/{_d}', app=StaticImmutable(directory=f'static/{_d}'), name=f'static_{_d}'))

# connect your blocks
b.connect(lego)
d.connect(lego) # dashboards
h.connect(lego) # hora — also the whole of sankalpa.sh, which Caddy rewrites / to /hora
a.connect(lego) # auth needs to be the last to connect. it reads RouteOverrides skip list to skip auth

# optionally add a scheduled backup of data folders
if cfg.need_backup and not not_prod():
    run_backup(get_db_dir())
    clone(cfg.static)
    clone(cfg.backup_path, sync=False)  # initial clone to ensure backups are in place
    scheduler.add_job(run_backup,args=[get_db_dir()],trigger='cron',hour='8,20',minute=0)
    scheduler.add_job(clone,trigger='cron', hour='10,22',minute=0)
    scheduler.add_job(clone,args=[cfg.backup_path],kwargs=dict(sync=False),trigger='interval',hours=24, id='daily_bkp')

def showcase(auth):
    if auth: return home()
    txt = Div(
        P('Welcome to Lego', cls='text-xl font-bold align-center'),
        P('make coding fun again', cls='text-xs font-bold mb-4 align-center'),
        P('Write code one block at a time. Use syntactic sugars like multi process locking, backups, caching and more. Modify, hack and refactor anything.', cls='mb-2'),
        P('Lego uses functional, succinct code. So no ruff, pep or linters. Its optimised for reading on mobiles.',cls='mb-2'),
        cls='mx-auto mt-4')
    td_get, td_tgt, bj_get, bj_tgt = '/', '#main-content', f'{a.Routes.auth_modal}?step={a.Step.login}', '#showcase'
    btns = Div(cls='flex justify-center space-x-4 mt-4')(
        Button('Test Drive', hx_get=td_get, hx_target=td_tgt, cls=[ButtonT.default, TextT.sm]),
        Button('Begin Journey', hx_get=bj_get, hx_target=bj_tgt, cls=[ButtonT.primary, TextT.sm]))
    c = Div(txt, btns, id='showcase', cls='max-w-xs align-center mx-auto')
    return landing(c)

# add default routes. the blocks can override these. the first in line wins.
# lego.get('/')(showcase)
lego.get('/health')(lambda req: JSONResponse({'status': 'ok'}))

def n_workers():
    '''How many processes to serve on.

    Rendering a page is Python holding the GIL, so one process answers requests strictly
    one at a time however many threads are behind it — the whole app tops out around 800
    requests a second no matter how little each one costs. Processes are what lifts that,
    and every worker gets its own copy of the memos in dash and ui, which is fine: they
    are all derived from files on disk and none of them is authoritative.

    Capped rather than one per core because each worker holds its own sqlite connections
    and its own reflection cache, and a 32-core box does not want 32 of those. Set
    WEB_CONCURRENCY to override.'''
    if cfg.workers: return cfg.workers
    return max(1, min(4, (os.cpu_count() or 1)))

def launch():
    # reload=True is `serve`'s default, and it was running in production: a file-watching
    # supervisor and a stat sweep of the tree, for a container whose files never change.
    # It is also incompatible with workers, so this is one switch.
    if not_prod(): return serve('lego', 'lego', port=cfg.port, reload=True)
    serve('lego', 'lego', port=cfg.port, reload=False, workers=n_workers())

if __name__ == '__main__': launch()
