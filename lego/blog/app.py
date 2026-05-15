import time
from fasthtml.common import dataclass, Redirect, Div, is_full_page
from fastlite import NotFoundError
from lego.core import slug, base, not_found, RouteOverrides
from lego.blog.data import posts, seed_posts
from lego.blog.ui import blog_hero, post_list, post_detail, new_post_form, showcase_cta
from .cfg import Routes, cfg

__all__ = ['connect']

@dataclass
class NewPost: title: str; summary: str; body: str; visibility: str = 'public'

def _get_usr(req): return req.scope.get('auth') or req.scope.get('session', {}).get('auth')
def _scaf(req, it, auth=None, title=''): return it if is_full_page(req, None) else base(it, auth, title=title)
def _blog(usr=None): return Div(blog_hero(usr),post_list(posts(order_by='created_at desc'), usr),showcase_cta(usr))
def blog_index(req, auth=None): return base(_blog(auth), auth, title='The Obsession Journal')
def _trig(next): return Div(hx_get=next, hx_target='body', hx_swap='beforeend', hx_trigger='load')
def member_only(c, title, next): return *base(c, None, title=title), _trig(next)
def blog_new_get(req, auth):
    if not auth: return member_only(_blog(),'The Obsession Journal',f'{RouteOverrides.lgn}?next={Routes.new}')
    return _scaf(req, new_post_form(), auth, title='Write a post')

def blog_new_post(req, auth, p: NewPost):
    if not (p.title and p.body):
        return _scaf(req, new_post_form(err_msg='Title and body are required.'), auth, title='Write a post')
    s = slug(p.title + str(time.time()))
    posts.insert(dict(slug=s, title=p.title, summary=p.summary or p.title, body=p.body, author_id=auth['id'],
          author_name=auth['display_name'], visibility=p.visibility, created_at=time.time(), updated_at=time.time()))
    return Redirect(f'/blog/{s}')

def blog_post_get(req, slug: str, auth):
    try: post = dict(posts.selectone(where='slug=:s', where_args=dict(s=slug)))
    except (NotFoundError, StopIteration): return not_found()
    v = post_detail(post, auth)
    if post['visibility'] == 'members' and not (auth and is_full_page(req, None)):
        _get = f'{RouteOverrides.lgn}?next=/blog/{slug}'
        trigger = Div(hx_get=_get, hx_target='body', hx_swap='beforeend', hx_trigger='load')
        return *base(v, None, title=post['title']), trigger
    return _scaf(req, v, auth, title=post['title'])

def connect(app):
    seed_posts(cfg.posts_seed_force)
    app.get(Routes.base)(blog_index)
    app.get('/')(blog_index)
    RouteOverrides.skip += Routes.skip
    app.get(Routes.new)(blog_new_get)
    app.post(Routes.new)(blog_new_post)
    app.get(Routes.post)(blog_post_get)
