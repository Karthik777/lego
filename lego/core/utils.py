import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastcore.all import patch, ifnone, Path, L
from functools import wraps
from time import time
from .cfg import cfg, get_lock, quick_lgr

__all__ = ['init_js_then_use', 'get_usr_ini', 'start_scheduler', 'stop_scheduler', 'scheduler', 'loadX',
           'timeit', 'clean_dev', 'rm_special', 'arun']

def init_js_then_use(script_src:str, pkg_name_in_js:str, js_code:str):
    from fasthtml.common import Script, Surreal
    js = '''function d(){%s};if(typeof %s === 'undefined'){me('script[src*="%s"]').on('load', ev=> {d();});}else{d();}'''
    return Script(src=script_src), Surreal(js % (js_code, pkg_name_in_js, script_src))

def get_usr_ini(usr=None, default='A'):
    if not usr or not isinstance(usr, dict): return default
    return usr.get('display_name', default)[0] or default

scheduler = AsyncIOScheduler()
async def start_scheduler():
    if cfg.serverless: return
    scheduler.start() if get_lock(ttl=60) else None

async def stop_scheduler():
    if cfg.serverless: return
    scheduler.shutdown() if scheduler and scheduler.running else None

@patch
def with_name_add(self:Path, add="_1", suffix=None, force=False):
    """Add a suffix to the file name before the extension."""
    nw_p= self.stem + add + ifnone(suffix, self.suffix)
    self=self.parent/nw_p
    return self.with_name_add(add) if self.exists() and force else self

def minjs(js:str): from rjsmin import jsmin; return jsmin(js)
def mincss(js:str): from rcssmin import cssmin; return cssmin(js)
def loadX(fn:Path, kw=None, pattern=r'__(\w+)__',minify=True):
    fn=Path(fn)
    sa=fn.read_text()
    if kw: import re; sa = re.sub(pattern, lambda m: kw.get(m.group(1), m.group(0)), sa)
    if minify: sa = minjs(sa) if fn.suffix == '.js' else mincss(sa) if fn.suffix == '.css' else sa
    return sa

i,e,w = quick_lgr()
def timeit(f):
    @wraps(f)
    def w(*a, **kw):
        st = time()
        result = f(*a, **kw)
        et = time()
        i(f"{f.__name__}: {a}: {kw} took {et - st:.4f} seconds")
        return result
    return w

def clean_dev(text): return re.sub(r'[।॥०-९a-zA-Z().\*\s+]', ' ', text).strip()
def rm_special(q: str) -> str: return re.sub(r'[^\w\s]|[।॥०-९.]', '', q, flags=re.UNICODE).strip()

def arun(coro:callable) -> any:
    'Run an async coroutine from sync code, even if already inside an event loop'
    import asyncio
    try: asyncio.get_running_loop()
    except RuntimeError: return L(asyncio.run(coro))
    # We're in a running loop → use a temporary loop in a thread
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool: return L(pool.submit(asyncio.run, coro).result())
