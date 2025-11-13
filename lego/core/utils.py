from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastcore.all import patch, ifnone, Path
from functools import wraps
from time import time
from fastcore.parallel import threaded
from fastcore.xml import FT, to_xml
from .cfg import cfg
from .cache import get_lock
from .logging import quick_lgr

__all__ = ['init_js_then_use', 'get_usr_ini', 'start_scheduler', 'mk_dest', 'stop_scheduler', 'scheduler', 'loadX', 'timeit']

i,e,w = quick_lgr()

def init_js_then_use(script_src:str, pkg_name_in_js:str, js_code:str):
    from fasthtml.common import Script, Surreal
    js = '''function d(){%s};if(typeof %s === 'undefined'){me('script[src*="%s"]').on('load', ev=> {d();});}else{d();}'''
    return Script(src=script_src), Surreal(js % (js_code, pkg_name_in_js, script_src))

def get_usr_ini(usr=None, default='A'):
    if not usr or not isinstance(usr, dict): return default
    return usr.get('display_name', default)[0] or default

scheduler = AsyncIOScheduler()
async def start_scheduler(): scheduler.start() if get_lock(ttl=60) else None
async def stop_scheduler(): scheduler.shutdown() if scheduler and scheduler.running else None

@patch
def mk_dest(self:Path, add=None, suffix=None, force=False):
    """Add a suffix to the file name before the extension."""
    if not self.exists(): return self
    if not add: import uuid; add = str(uuid.uuid1())
    self=self.parent/self.stem + add + ifnone(suffix, self.suffix)
    return self.mk_dest(add, suffix, force) if self.exists() and force else self

def minjs(js:str): from rjsmin import jsmin; return jsmin(js)
def mincss(js:str): from rcssmin import cssmin; return cssmin(js)
def loadX(fn:Path, kw=None, pattern=r'__(\w+)__',minify=True):
    fn=Path(fn)
    sa=fn.read_text()
    if kw: import re; sa = re.sub(pattern, lambda m: kw.get(m.group(1), m.group(0)), sa)
    if minify: sa = minjs(sa) if fn.suffix == '.js' else mincss(sa) if fn.suffix == '.css' else sa
    return sa

def timeit(f):
    @wraps(f)
    def w(*a, **kw):
        st = time()
        result = f(*a, **kw)
        et = time()
        i(f"{f.__name__}: {a}: {kw} took {et - st:.4f} seconds")
        return result
    return w

@threaded
def send_email(to, subject, html: FT):
    if isinstance(html, FT): html = to_xml(html)
    import resend
    resend.api_key = cfg.resend_api_key
    i(f'Resend Result: {html}')
    resend.Emails.send({'from': 'accounts@vedicreader.com', 'to': to, 'subject': subject, 'html': html})