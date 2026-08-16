from datetime import datetime
from pathlib import Path
from fasthtml.common import *
from fastcore.all import timed_cache
from lego.core import RouteOverrides, TextT, ButtonT, asset_css, lc_icon
from .cfg import Routes, cfg, CATALOG
from .data import item, live, sub_of

__all__ = ['pay_head', 'pricing', 'receipt', 'money', 'mode_chip']

_SYMS = dict(usd='$', eur='€', gbp='£', inr='₹', aud='A$', cad='C$')

def money(cents, cur=None):
    s, v = _SYMS.get(cur or cfg.currency, ''), cents / 100
    return f'{s}{v:,.0f}' if cents % 100 == 0 else f'{s}{v:,.2f}'

@timed_cache(seconds=3600)
def pay_head(): return [asset_css(Path(__file__).parent / 'pay.css')]

def _chip(txt, tone, note): return Span(txt, cls=f'badge chip-{tone}'), note

def mode_chip():
    'Which key the block is running on, said out loud on the page.'
    if not live(): return _chip('Sandbox', 'yellow',
                                'No Stripe key set. Orders are written to the local database so you can walk the flow.')
    if cfg.scrt.startswith('sk_test'): return _chip('Stripe test mode', 'blue',
                                                    'Test key in use. Pay with card 4242 4242 4242 4242, any future expiry, any CVC.')
    return _chip('Live', 'green', 'Live key in use. Cards are charged for real.')

def _icon(it): return lc_icon('cloud' if it.get('interval') else 'monitor', 18)

def _buy_btn(it, owned):
    if owned: return A('View receipt', href=f'{Routes.done}?sid={owned["id"]}', cls=f'{ButtonT.secondary} {ButtonT.sm}')
    # unboosted so the 303 to Stripe is a plain navigation, and so it still works with JS off
    return Form(Button(it.cta, cls=ButtonT.primary), method='post',
                action=Routes.buy.format(key=it.key), hx_boost='false')

def _card(it, owned=None):
    per = Span(f'/{it.interval}', cls=TextT.sm) if it.get('interval') else Span('once', cls=TextT.sm)
    head = Div(_icon(it), Span(it.kind, cls=f'{TextT.xs} font-mono tracking-wider uppercase'),
               Span('Owned', cls='badge chip-green') if owned else None,
               cls='flex items-center gap-2 mb-4')
    price = Div(Span(money(it.amount), cls='pay-price'), per, cls='pay-price-row')
    perks = Ul(*[Li(lc_icon('check', 14), Span(p)) for p in it.perks], cls='pay-perks')
    return Div(head, H2(it.nm, cls='mb-3 tracking-tight'), price,
               P(it.blurb, cls=f'{TextT.sm} mb-5 leading-relaxed'), perks,
               Div(_buy_btn(it, owned), cls='pay-foot'), cls='card pay-card')

def _hero(err=None):
    chip, note = mode_chip()
    return Section(
        Div(chip, Span(note, cls=TextT.sm), cls='flex items-center gap-3 mb-5'),
        H1('Charge once, or charge every month', cls='mb-3 tracking-tight'),
        P('Both Stripe workflows on one page. A desktop app sold outright, and a hosted service on a '
          'monthly plan. Same block, same five routes, one field apart in the catalogue.',
          cls='max-w-2xl leading-relaxed'),
        P(err, cls='text-danger text-sm mt-4') if err else None,
        cls='section-pad max-w-5xl mx-auto')

def _owned(rows):
    if not rows: return None
    def _row(o):
        it = item(o['item'])
        chip = 'chip-green' if o['status'] in ('paid', 'active') else 'chip-gray'
        return Tr(Td(it.nm if it else o['item']),
                  Td(money(o['amount'], o['currency']), cls='font-mono'),
                  Td(Span(o['status'], cls=f'badge {chip}')),
                  Td(datetime.fromtimestamp(o['created_at']).strftime('%b %d, %Y'), cls=f'{TextT.xs} font-mono'),
                  Td(A('Receipt', href=f'{Routes.done}?sid={o["id"]}', cls='underline-h')))
    sub = sub_of(rows)
    manage = Form(Button('Manage subscription', cls=f'{ButtonT.secondary} {ButtonT.sm}'), method='post',
                  action=Routes.portal, hx_boost='false') if sub else None
    return Section(H2('What you own', cls='mb-5 tracking-tight'),
                   Table(Thead(Tr(*[Th(h) for h in ('Item', 'Paid', 'Status', 'When', '')])),
                         Tbody(*[_row(o) for o in rows]), cls='pay-tbl mb-6'),
                   manage, cls='pay-sec')

_STEPS = [('Get a key', 'Create a Stripe account and copy the test secret key from the dashboard.'),
          ('Set it', 'Put it in .env as STRIPE_SECRET_KEY and restart. Nothing else changes.'),
          ('Pay', 'Card 4242 4242 4242 4242 clears every test charge Stripe will accept.'),
          ('Forward events', 'stripe listen --forward-to localhost:5001/pay/hook, then set STRIPE_WEBHOOK_SECRET.')]

def _connect():
    return Section(
        Div(H2('Point it at your own account', cls='mb-2 tracking-tight'),
            P('The catalogue is a list of dicts and the prices go inline on the Checkout Session, so '
              'nothing has to exist in the Stripe dashboard before the first sale.', cls=f'{TextT.sm} mb-6'),
            Ol(*[Li(Strong(t), Br(), Span(d, cls=TextT.sm)) for t, d in _STEPS], cls='pay-steps'),
            cls='card'), cls='pay-sec')

def pricing(rows=(), err=None):
    owned = {o['item']: o for o in rows if o['status'] in ('paid', 'active')}
    return Div(_hero(err),
               Section(Div(*[_card(it, owned.get(it.key)) for it in CATALOG], cls='pay-grid'), cls='pay-sec'),
               _owned(rows), _connect())

def receipt(o, usr=None):
    it = item(o['item'])
    rows = [('Item', it.nm if it else o['item']), ('Amount', money(o['amount'], o['currency'])),
            ('Billing', 'Monthly, until you cancel' if o['sub'] else 'One payment'),
            ('Status', o['status']), ('Email', o['email'] or '—'),
            ('Reference', o['id'])]
    cta = (A('Back to pricing', href=Routes.index, cls=f'{ButtonT.secondary} {ButtonT.sm}') if usr else
           A('Sign in to keep it', hx_get=f'{RouteOverrides.lgn}?next={Routes.index}', hx_target='body',
             hx_swap='beforeend', cls=f'{ButtonT.primary} {ButtonT.sm}'))
    return Section(
        Div(Div(lc_icon('check', 20),
                H2('Subscription started' if o['sub'] else 'Payment received', cls='m-0 tracking-tight'),
                cls='flex items-center gap-2 mb-5'),
            Table(Tbody(*[Tr(Td(k, cls=TextT.muted), Td(v, cls='font-mono break-words')) for k, v in rows]),
                  cls='pay-tbl mb-6'),
            Div(cta, cls='flex gap-3'), cls='card'),
        cls='max-w-2xl mx-auto px-4 py-16')
