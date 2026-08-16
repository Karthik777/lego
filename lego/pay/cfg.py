import os
from dataclasses import dataclass
from fastcore.all import L, AttrDict

@dataclass(frozen=True)
class Routes:
    index  = '/pay'
    buy    = '/pay/buy/{key}'
    done   = '/pay/done'
    portal = '/pay/portal'
    hook   = '/pay/hook'
    skip   = ['/pay', '/pay/done', '/pay/portal', '/pay/hook', r'/pay/buy/.*']

# The names Stripe's own docs and CLI use, so a key copied from the dashboard lands where
# faststripe already looks for it.
cfg = AttrDict(scrt     = os.getenv('STRIPE_SECRET_KEY', ''),
               pub      = os.getenv('STRIPE_PUBLISHABLE_KEY', ''),
               hook     = os.getenv('STRIPE_WEBHOOK_SECRET', ''),
               currency = os.getenv('STRIPE_CURRENCY', 'usd'))

# Amounts are in the currency's smallest unit, which is what Stripe takes and what avoids
# float money. `interval` is what makes an item a subscription rather than a one-off.
CATALOG = L(
    AttrDict(key='studio', nm='Lego Studio', kind='Desktop app', mode='payment', amount=20000,
             blurb='The block editor for macOS and Windows. Pay once, keep the app.',
             perks=['Signed builds for macOS 13+ and Windows 11',
                    'One licence, three machines',
                    'A year of updates; the version you have keeps working after that',
                    'Runs offline, no account needed'],
             cta='Buy for $200'),
    AttrDict(key='cloud', nm='Lego Cloud', kind='Subscription', mode='subscription', amount=1900,
             interval='month',
             blurb='Hosted builds and a shared block library, billed monthly.',
             perks=['Build for macOS and Windows without owning either',
                    'Shared block library across your team',
                    'Nightly backups kept for 30 days',
                    'Cancel from the billing portal, no email needed'],
             cta='Subscribe at $19/mo'))
