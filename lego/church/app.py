from fastlite import NotFoundError
from lego.core import RouteOverrides
from lego.church.data import teachings, seed_teachings
from lego.church.ui import church_base, church_not_found, home_page, about_page, teachings_index, teaching_detail, \
    assembly_page, beliefs_page, contact_page
from .cfg import Routes, cfg

__all__ = ['connect']

def _scaf(req, content, title, active):
    return content if 'hx-request' in req.headers else church_base(content, title=title, active=active)

def _ordered_teachings(): return list(teachings(order_by='created_at desc'))

def home(req): return _scaf(req, home_page(), None, '/')
def about(req): return _scaf(req, about_page(), 'About', Routes.about)
def teachings_list(req): return _scaf(req, teachings_index(_ordered_teachings()), 'Teachings', Routes.teachings)
def assembly(req): return _scaf(req, assembly_page(), 'Online Assembly', Routes.assembly)
def beliefs(req): return _scaf(req, beliefs_page(), 'Statement of Beliefs', Routes.beliefs)
def contact(req): return _scaf(req, contact_page(), 'Contact Us', Routes.contact)

def teaching_post(req, slug: str):
    try: t = teachings[slug]
    except (NotFoundError, StopIteration): return church_not_found()
    return _scaf(req, teaching_detail(t), t['title'], Routes.teachings)

def connect(app):
    seed_teachings(cfg.teachings_seed_force)
    RouteOverrides.skip += Routes.skip
    app.get(Routes.home)(home)
    app.get(Routes.about)(about)
    app.get(Routes.teachings)(teachings_list)
    app.get(Routes.teaching)(teaching_post)
    app.get(Routes.assembly)(assembly)
    app.get(Routes.beliefs)(beliefs)
    app.get(Routes.contact)(contact)
