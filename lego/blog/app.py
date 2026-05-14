import time
from fasthtml.common import dataclass, Redirect, Div, is_full_page
from fastlite import NotFoundError
from lego.core import slug, base, landing, placeholder, not_found, RouteOverrides
from lego.auth import Routes as AR, Step
from lego.blog.data import posts, seed_posts
from lego.blog.ui import blog_hero, post_list, post_detail, new_post_form, showcase_cta
from .cfg import Routes
__all__ = ['connect']

@dataclass
class NewPost: title: str; summary: str; body: str; visibility: str = 'public'

def _get_usr(req): return req.scope.get('auth') or req.scope.get('session', {}).get('auth')
def _scaf(req, it, title='The Obsession Journal'):
    return it if is_full_page(req, None) else base(it, _get_usr(req), title=title)

def _login_redirect():
    href = f'{AR.auth_modal}?step={Step.login}'
    return landing(placeholder('Sign in to write a post', back_link=href, back_text='Sign in'))

def blog_index(req, auth=None):
    auth = auth or _get_usr(req)
    all_posts = posts(order_by='created_at desc')
    v = Div(blog_hero(auth), post_list(all_posts, auth), showcase_cta(auth))
    return base(v, auth, title='The Obsession Journal')

def blog_new_get(req, auth):
    if not auth: return _login_redirect()
    return _scaf(req, new_post_form(), title='Write a post')

def blog_new_post(req, auth, p: NewPost):
    if not (p.title and p.body):
        return _scaf(req, new_post_form(err_msg='Title and body are required.'), title='Write a post')
    s = slug(p.title + str(time.time()))
    posts.insert(dict(slug=s, title=p.title, summary=p.summary or p.title, body=p.body, author_id=auth['id'],
          author_name=auth['display_name'], visibility=p.visibility, created_at=time.time(), updated_at=time.time()))
    return Redirect(f'/blog/{s}')

def blog_post_get(req, slug: str, auth):
    try: post = dict(posts.selectone(where='slug=:s', where_args=dict(s=slug)))
    except (NotFoundError, StopIteration): return not_found()
    return _scaf(req, post_detail(post, auth), title=post['title'])

def connect(app):
    seed_posts()
    app.get(Routes.base)(blog_index)
    app.get('/')(blog_index)
    RouteOverrides.skip += Routes.skip
    app.get(Routes.new)(blog_new_get)
    app.post(Routes.new)(blog_new_post)
    app.get(Routes.post)(blog_post_get)
