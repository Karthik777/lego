from fasthtml.common import Meta, Favicon, Socials, Link, serve, Script, JSONResponse
from monsterui.all import *
from .core import *
from lego import church as c

__all__ = ['launch', 'lego']

if cfg.purge: clear_cache()
f = ['Libre+Baskerville', 'Fira+Code', 'Playfair+Display']
fonts = ('&'.join(map(lambda x: 'family=%s:wght@300;400;500;600;700' % x, f)) + '&display=swap')

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
    *Socials(title=cfg.app_nm, description=cfg.site_description, site_name=cfg.domain, image='/static/favicon.svg',
             url=cfg.domain), *themes()]

def nf(req, exc): return c.church_not_found()
kw,exh = {'class': 'hidden', 'hx-ext': 'preload', 'hx-boost': 'true'}, {404: nf, 500: nf, 403: nf}
lego, rt = fast_app(hdrs=hdrs, bodykw=kw, live=not_prod(), title=cfg.app_nm, exts='preload', exception_handlers=exh,
                    on_startup=start_scheduler, on_shutdown=stop_scheduler)

# connect your blocks
c.connect(lego)

# optionally add a scheduled backup of data folders
if cfg.need_backup and not not_prod():
    run_backup(get_db_dir())
    clone(cfg.static)
    clone(cfg.backup_path, sync=False)  # initial clone to ensure backups are in place
    scheduler.add_job(run_backup,args=[get_db_dir()],trigger='cron',hour='8,20',minute=0)
    scheduler.add_job(clone,trigger='cron', hour='10,22',minute=0)
    scheduler.add_job(clone,args=[cfg.backup_path],kwargs=dict(sync=False),trigger='interval',hours=24, id='daily_bkp')

lego.get('/health')(lambda req: JSONResponse({'status': 'ok'}))

def launch(): serve('lego', 'lego', port=cfg.port)
if __name__ == '__main__': launch()
