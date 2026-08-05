"""Render a fixed set of routes through the ASGI app and hash the bodies, so a
performance change can be shown not to have changed a single byte of output."""
import asyncio, hashlib, os, sys
os.environ.setdefault('MODE', 'production')
from lego.app import lego as app

ROUTES = ['/health', '/', '/dash', '/dash/chinook', '/dash/nycflights', '/dash/titanic',
          '/dash/chinook/Album', '/dash/chinook/Track', '/dash/nycflights/Flight',
          '/dash/nycflights/Weather', '/dash/sakila/payment', '/dash/factbook/facts',
          '/dash/chinook/Album/1', '/dash/titanic/passenger/1',
          '/dash/fopts?db=chinook&fc=Album:Title', '/dash/bopts?db=chinook&bt=Album',
          '/dash/chart?db=chinook&t=Album&kind=bar&x=Title&agg=count',
          '/blog', '/lgn', '/auth/login', '/nope-404']

async def call(path):
    p, _, qs = path.partition('?')
    scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method='GET',
                 scheme='http', path=p, raw_path=p.encode(), query_string=qs.encode(),
                 root_path='', headers=[(b'host', b'h')], client=('1.1.1.1', 1), server=('h', 80))
    async def receive(): return {'type': 'http.request', 'body': b'', 'more_body': False}
    body, st = bytearray(), [0]
    async def send(m):
        if m['type'] == 'http.response.start': st[0] = m['status']
        elif m['type'] == 'http.response.body': body.extend(m.get('body', b''))
    await app(scope, receive, send)
    return st[0], bytes(body)

async def main():
    for r in ROUTES:
        try:
            s, b = await call(r)
            print(f'{r:52s} {s} {len(b):8d} {hashlib.sha256(b).hexdigest()[:16]}')
        except Exception as e:
            print(f'{r:52s} EXC {type(e).__name__}: {str(e)[:70]}')

asyncio.run(main())
