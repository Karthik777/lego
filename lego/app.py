from fasthtml.common import Meta, Favicon, Socials, Link, serve, Script, JSONResponse, Div, P, Redirect
from monsterui.all import *
from .core import *
from lego import auth as a, gun, ai

__all__ = ['launch', 'lego']

if cfg.purge: clear_cache()
f = ['Playfair+Display', 'DM+Sans', 'Space+Mono']
fonts= '&'.join(map(lambda x: 'family=%s:wght@300;400;500;600;700' %x, f)) + '&display=swap'

hdrs = [
    Meta(charset='UTF-8'),
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
    Link(rel='stylesheet', href='https://fonts.googleapis.com/css2?%s' % fonts, defer=True),
    *Socials(title=cfg.app_nm, description=cfg.site_description, site_name=cfg.domain, image='/static/favicon.svg', url=cfg.domain),
    *themes()]

track = Script(src="https://cloud.umami.is/script.js", data_website_id="04fffb06-484c-4c59-b6e0-72e522c54837", defer=True)
ftrs= [track if not not_prod() else None]
def before(req, sess): req.scope['auth'] = sess['auth'] if 'auth' in sess else None# add auth to request scope
def nf(req, exc): return not_found()
kw,exh = {'class': 'neo-brutalism hidden', 'hx-ext': 'preload', 'hx-boost': 'true'}, {404: nf, 500: nf, 403: nf}
lego, rt = fast_app(hdrs=hdrs, ftrs=ftrs, bodykw=kw, secret_key=cfg.jwt_scrt, live=not_prod(), title=cfg.app_nm, before=before,
                    exts='preload', exception_handlers=exh, on_startup=start_scheduler, on_shutdown=stop_scheduler)

RouteOverrides.skip.append('/chatbot')
# connect your blocks
a.connect(lego)

# optionally add a scheduled backup of data folders
if cfg.need_backup and not not_prod():
    run_backup(get_db_dir()); clone(); clone(cfg.backup_path, sync=False)  # initial clone to ensure backups are in place
    scheduler.add_job(run_backup,args=[get_db_dir()],trigger='cron',hour='8,20',minute=0)
    scheduler.add_job(clone,trigger='cron', hour='10,22',minute=0)
    scheduler.add_job(clone,args=[cfg.backup_path],kwargs=dict(sync=False),trigger='interval',hours=24, id='daily_backup')

@cache('showcase', ttl=3600*24*30)
def showcase(auth):
    if auth: return home()
    txt= Div(
        P('Welcome to Lego', cls='text-xl font-bold text-center'),
        P('make coding fun again', cls='text-xs font-bold mb-4 text-center'),
        P('Write code one block at a time. Use syntactic sugars like multi process locking, backups, caching and more. Modify, hack and refactor anything.', cls='mb-2'),
        P('Lego uses functional, succinct code. So no ruff, pep or linters. It\'s optimised for reading on mobiles.', cls='mb-2'),
        cls='mx-auto mt-4')

    td_get, td_tgt, bj_get, bj_tgt = '/', '#main-content', f'{a.Routes.auth_modal}?step={a.Step.login}', '#showcase'
    btns= Div(cls='flex justify-center space-x-4 mt-4')(
        Button('Test Drive', hx_get=td_get, hx_target=td_tgt, cls=[ButtonT.default, TextT.sm]),
        Button('Begin Journey', hx_get=bj_get, hx_target=bj_tgt, cls=[ButtonT.primary, TextT.sm]))

    return landing(Div(txt,btns, id='showcase', cls='w-80 text-center mx-auto'))

def chatbot(): return base(simple_page(Div(ai.chats(), id='chatbot', cls='h-screen text-left mx-auto')))

# add default routes. the blocks can override these. the first in line wins.
lego.get('/')(showcase)  # override home route to point to chatbot
lego.get('/chatbot')(chatbot)
lego.get('/health')(lambda req: JSONResponse({'status': 'ok'}))


def launch(): serve('lego', 'lego', port=cfg.port) if not_prod() else gun.launch(lego)
if __name__ == '__main__': launch()
