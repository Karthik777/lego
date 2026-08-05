"""Attribute a request's cost to its three layers: HTTP/dispatch, FT tree build
+ serialise, and data access. Compares against a bare Starlette app to bound how
much of the total any faster HTTP core could possibly remove."""
import asyncio, os, time
os.environ.setdefault('MODE', 'production')

def bench(f, n=50, warm=5):
    for _ in range(warm): f()
    t = time.perf_counter()
    for _ in range(n): f()
    return (time.perf_counter() - t) / n * 1000

# ---------- floor: bare Starlette, same ASGI driver ----------
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

def drive(app, path='/x'):
    scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method='GET',
                 scheme='http', path=path, raw_path=path.encode(), query_string=b'',
                 root_path='', headers=[(b'host', b'h')], client=('1.1.1.1', 1), server=('h', 80))
    async def receive(): return {'type': 'http.request', 'body': b'', 'more_body': False}
    out = bytearray()
    async def send(m):
        if m['type'] == 'http.response.body': out.extend(m.get('body', b''))
    loop = asyncio.new_event_loop()
    def go():
        out.clear(); loop.run_until_complete(app(dict(scope), receive, send)); return bytes(out)
    return go

big = b'<div>x</div>' * 2000  # ~23KB, same order as lego's home page
bare = Starlette(routes=[Route('/x', lambda r: JSONResponse({'status': 'ok'}))])
bare_html = Starlette(routes=[Route('/x', lambda r: HTMLResponse(big))])
sess_html = Starlette(routes=[Route('/x', lambda r: HTMLResponse(big))],
                      middleware=[Middleware(SessionMiddleware, secret_key='k'*32)])
print('--- floor (bare Starlette, no framework) ---')
print(f'  no-op JSONResponse          {bench(drive(bare), 300):7.3f} ms')
print(f'  23KB HTMLResponse           {bench(drive(bare_html), 300):7.3f} ms')
print(f'  23KB + SessionMiddleware    {bench(drive(sess_html), 300):7.3f} ms')

# ---------- lego: whole request ----------
import lego
from lego.app import lego as app
print('\n--- lego, whole request through the stack ---')
for p in ('/health', '/', '/dash', '/dash/nycflights'):
    print(f'  {p:22s}      {bench(drive(app, p), 30):7.3f} ms')

# ---------- lego: the pieces, called directly ----------
from fastcore.xml import to_xml
from lego.core import base
from lego.blog.app import _blog
from lego.dash.ui import index_view, db_view
from lego.dash.data import DBS, reflect, table_names

print('\n--- the pieces of / , called directly (no HTTP at all) ---')
print(f'  build FT tree (_blog+base)  {bench(lambda: base(_blog(None), None, title="t"), 30):7.3f} ms')
tree = base(_blog(None), None, title='t')
print(f'  to_xml(tree)                {bench(lambda: to_xml(tree), 30):7.3f} ms')

print('\n--- the pieces of /dash ---')
print(f'  build FT tree (index_view)  {bench(lambda: index_view(), 20):7.3f} ms')
iv = index_view()
print(f'  to_xml(index_view)          {bench(lambda: to_xml(iv), 20):7.3f} ms')
db0 = list(DBS)[0]
print(f'  reflect({db0!r}, one table)   {bench(lambda: reflect(db0, table_names(db0)[0]), 50):7.3f} ms')
print(f'  table_names({db0!r})          {bench(lambda: table_names(db0), 200):7.3f} ms')
print(f'\n  DBS: {list(DBS)}')
for d in DBS: print(f'    {d}: {len(table_names(d))} tables')
