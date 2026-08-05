"""In-process ASGI driver: times and profiles a request without any socket,
so what we measure is the framework and the handler, not uvicorn or the client."""
import asyncio, cProfile, pstats, io, os, sys, time

os.environ.setdefault('MODE', 'production')
import lego
from lego.app import lego as app

async def call(path, method='GET'):
    scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method=method,
                 scheme='http', path=path, raw_path=path.encode(), query_string=b'',
                 root_path='', headers=[(b'host', b'127.0.0.1'), (b'accept', b'*/*')],
                 client=('127.0.0.1', 1234), server=('127.0.0.1', 5001))
    body = bytearray(); status = [0]
    async def receive(): return {'type': 'http.request', 'body': b'', 'more_body': False}
    async def send(m):
        if m['type'] == 'http.response.start': status[0] = m['status']
        elif m['type'] == 'http.response.body': body.extend(m.get('body', b''))
    await app(scope, receive, send)
    return status[0], bytes(body)

def timeit(path, n=200):
    asyncio.run(call(path))
    t = time.perf_counter()
    for _ in range(n): asyncio.run(call(path))
    el = (time.perf_counter() - t) / n * 1000
    s, b = asyncio.run(call(path))
    print(f'{path:30s} {s} {len(b)/1024:7.1f}KB  {el:7.3f}ms/req  {1000/el:8.1f} rps-1core')
    return el

def profile(path, n=100, top=25):
    asyncio.run(call(path))
    pr = cProfile.Profile(); pr.enable()
    for _ in range(n): asyncio.run(call(path))
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(top)
    print(f'\n===== profile {path} (n={n}) =====')
    print('\n'.join(s.getvalue().splitlines()[4:top + 12]))

if __name__ == '__main__':
    paths = sys.argv[1:] or ['/health', '/', '/dash']
    for p in paths: timeit(p)
    for p in paths: profile(p)
