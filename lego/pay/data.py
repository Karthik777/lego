import time
from fastcore.all import AttrDict, first
from faststripe.core import StripeApi, StripeError
from faststripe.core import StripeSignatureError
from lego.core import cfg as app_cfg, thread_db, get_db_pth, quick_lgr, slug
from .cfg import Routes, cfg, CATALOG

__all__ = ['orders', 'sapi', 'live', 'item', 'mine', 'sub_of', 'buy', 'settle', 'portal_url', 'apply_hook',
           'StripeError', 'StripeSignatureError']

info, error, warn = quick_lgr()

def _setup(db, first):
    if not first: return
    db.t.orders.create(id=str, user_id=int, email=str, item=str, mode=str, amount=int, currency=str,
                       status=str, customer=str, sub=str, created_at=float, pk='id', if_not_exists=True,
                       transform=True)
    db.t.orders.create_index(['email'], if_not_exists=True)

_db    = thread_db(get_db_pth('pay'), setup=_setup)
orders = _db.table('orders')

sapi = StripeApi(api_key=cfg.scrt, webhook_key=cfg.hook, publishable_key=cfg.pub)

def live(): return bool(cfg.scrt)
def item(key): return first(CATALOG, lambda i: i.key == key)
def mine(auth): return orders(where='email = ?', where_args=[auth['email']], order_by='created_at desc') if auth else []
def sub_of(rows): return first(rows, lambda o: o['sub'] and o['status'] == 'active')

def _line(it):
    'A price built inline, so the block needs no products set up in the dashboard first.'
    p = dict(currency=cfg.currency, unit_amount=it.amount, product_data=dict(name=it.nm, description=it.blurb))
    if it.get('interval'): p['recurring'] = dict(interval=it.interval)
    return dict(quantity=1, price_data=p)

def _save(s):
    'One row per Checkout Session, whichever way it reached us — the return trip or the webhook.'
    d = dict(id=s.id, user_id=int(s.get('client_reference_id') or 0),
             email=(s.get('customer_details') or {}).get('email') or s.get('customer_email') or '',
             item=(s.get('metadata') or {}).get('item', ''), mode=s.get('mode', ''),
             amount=s.get('amount_total') or 0, currency=s.get('currency') or cfg.currency,
             status='active' if s.get('subscription') else
                    ('paid' if s.get('payment_status') == 'paid' else s.get('status', '')),
             customer=s.get('customer') or '', sub=s.get('subscription') or '',
             created_at=float(s.get('created') or time.time()))
    orders.insert(d, replace=True)
    return d

def _sandbox(it, auth):
    'No key set: write the row Stripe would have sent back, so the flow is walkable before signup.'
    return _save(AttrDict(id=f'sandbox_{slug(it.key + str(time.time()))}', mode=it.mode, amount_total=it.amount,
                          currency=cfg.currency, payment_status='paid', created=time.time(),
                          subscription=f'sandbox_sub_{it.key}' if it.get('interval') else '',
                          client_reference_id=str(auth['id']) if auth else '',
                          customer_email=auth['email'] if auth else 'buyer@example.com',
                          metadata=dict(item=it.key)))

async def buy(it, auth):
    'Checkout Session for `it`, or a sandbox order when no key is configured.'
    if not live(): return _sandbox(it, auth)['id'], None
    root = app_cfg.domain.rstrip('/')
    kw = dict(mode=it.mode, line_items=[_line(it)], metadata=dict(item=it.key),
              success_url=f'{root}{Routes.done}?sid={{CHECKOUT_SESSION_ID}}', cancel_url=f'{root}{Routes.index}')
    if auth: kw |= dict(customer_email=auth['email'], client_reference_id=str(auth['id']))
    s = await sapi.v1.checkout.sessions.post(**kw)
    return s.id, s.url

async def settle(sid):
    '''Record the session the buyer came back with.

    Webhooks are the source of truth in production, but they need a public URL and a
    signing secret. Reading the session on return means a fresh test key pays and shows a
    receipt with neither of those, and the webhook only ever writes the same row again.'''
    if sid.startswith('sandbox_'): return orders[sid]
    return _save(await sapi.v1.checkout.sessions.session.get(session=sid))

async def portal_url(customer):
    s = await sapi.v1.billing_portal.sessions.post(customer=customer,
                                                   return_url=f'{app_cfg.domain.rstrip("/")}{Routes.index}')
    return s.url

async def apply_hook(req):
    evt = await sapi.parse_webhook(req)
    o = evt.data
    if evt.type == 'checkout.session.completed': _save(o)
    elif evt.type.startswith('customer.subscription.'):
        for r in orders(where='sub = ?', where_args=[o.id]): orders.update(dict(id=r['id'], status=o.status))
    info(f'stripe hook {evt.type} {o.get("id")}')
    return evt.type
