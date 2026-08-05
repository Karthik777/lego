"""Minimal keep-alive HTTP load generator. Raw asyncio streams so the client
adds as little as possible to the number we are trying to measure."""
import asyncio, sys, time, statistics as st
PORT=int(sys.argv[1])

async def worker(host, port, path, n, lats, hdrs=''):
    r, w = await asyncio.open_connection(host, port)
    req = (f'GET {path} HTTP/1.1\r\nHost: {host}:{PORT}\r\n'
           f'Connection: keep-alive\r\nAccept-Encoding: identity\r\n{hdrs}\r\n').encode()
    for _ in range(n):
        t = time.perf_counter()
        w.write(req); await w.drain()
        # read headers
        cl, chunked, sz = None, False, 0
        while True:
            line = await r.readline()
            if line in (b'\r\n', b''): break
            k, _, v = line.decode('latin1').partition(':')
            if k.lower() == 'content-length': cl = int(v.strip())
            if k.lower() == 'transfer-encoding' and 'chunked' in v.lower(): chunked = True
        if cl is not None:
            body = await r.readexactly(cl); sz = len(body)
        elif chunked:
            while True:
                ln = (await r.readline()).strip()
                m = int(ln.split(b';')[0] or b'0', 16)
                if m == 0: await r.readline(); break
                sz += len(await r.readexactly(m)); await r.readexactly(2)
        lats.append((time.perf_counter() - t, sz))
    w.close(); await w.wait_closed()

async def run(path, conc=1, n=200, hdrs=''):
    lats = []
    t0 = time.perf_counter()
    await asyncio.gather(*[worker('127.0.0.1', PORT, path, n, lats, hdrs) for _ in range(conc)])
    el = time.perf_counter() - t0
    ms = sorted(l * 1000 for l, _ in lats)
    sz = st.mean(s for _, s in lats)
    print(f'{path:38s} c={conc} n={len(ms):5d}  p50={ms[len(ms)//2]:7.2f}ms  '
          f'p95={ms[int(len(ms)*.95)]:7.2f}ms  rps={len(ms)/el:8.1f}  body={sz/1024:.1f}KB')
    return ms

async def main():
    paths = sys.argv[2:] or ['/health']
    for p in paths:
        await run(p, 1, 30)          # warm
        for c in (1, 8):
            await run(p, c, 200 if c == 1 else 100)

asyncio.run(main())
