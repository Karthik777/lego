from fasthtml.common import JSONResponse, Redirect
from fastlite import NotFoundError
from lego.core import base, not_found, RouteOverrides
from .cfg import Routes
from .data import StripeError, StripeSignatureError, apply_hook, buy, item, mine, portal_url, settle, sub_of
from .ui import pay_head, pricing, receipt

__all__ = ['connect', 'Routes']

def _page(content, auth, title): return (*base(content, auth, title=title), *pay_head())
def _pricing(auth, err=None): return _page(pricing(mine(auth), err), auth, 'Pricing')

def pay_index(req, auth=None): return _pricing(auth)

async def pay_buy(req, key: str, auth=None):
    it = item(key)
    if not it: return not_found()
    try: sid, url = await buy(it, auth)
    except StripeError as e: return _pricing(auth, str(e))
    return Redirect(url or f'{Routes.done}?sid={sid}')

async def pay_done(req, sid: str = '', auth=None):
    if not sid: return Redirect(Routes.index)
    try: o = await settle(sid)
    except (StripeError, NotFoundError, StopIteration): return not_found()
    return _page(receipt(o, auth), auth, 'Receipt')

async def pay_portal(req, auth=None):
    s = sub_of(mine(auth))
    if not (s and s['customer']): return Redirect(Routes.index)
    try: return Redirect(await portal_url(s['customer']))
    except StripeError as e: return _pricing(auth, str(e))

async def pay_hook(req):
    try: t = await apply_hook(req)
    except (StripeError, StripeSignatureError, ValueError) as e: return JSONResponse({'error': str(e)}, status_code=400)
    return JSONResponse({'received': t})

def connect(app):
    RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Pricing', Routes.index, None, False)]
    app.get(Routes.index)(pay_index)
    app.get(Routes.done)(pay_done)
    app.post(Routes.buy)(pay_buy)
    app.post(Routes.portal)(pay_portal)
    app.post(Routes.hook)(pay_hook)
