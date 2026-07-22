import hashlib as hl
import logging
import os
import secrets
from diskcache import Cache as DiskCache, memoize_stampede
from fasthtml.common import Redirect, FT, dataclass
from fastcore.all import threaded, AttrDictDefault, str2bool, str2int, startthread, to_xml, Path
from litesearch import database
from logging.handlers import RotatingFileHandler as RFH

__all__ = ['cfg', 'database', 'AppErr', 'home', 'send_email', 'RouteOverrides', 'get_pth', 'get_db_pth', 'in_static',
           'get_log_pth', 'get_db_dir', 'not_prod', 'get_caller_fn', 'slug', 'rot_log', 'get_logger', 'quick_lgr',
           'cache', 'clear_cache', 'kv', 'get_lock', 'release_lock']

# === Paths ===
data_root, backups, static = Path('data'), Path('backups'), Path('static')
def get_pth(nm, sf='', mk=False):
    p = data_root / sf / nm
    if not p.exists() and mk: p.mk_write('')
    return p

def get_db_pth(nm='vr'): return get_pth(f'{nm}.db', 'db')
def in_static(nm, sf=''): return static / sf / nm
def get_log_pth(nm='vr', mk=True): return get_pth(f'{nm}.log', 'logs', mk)

kv = DiskCache(str(data_root / 'cache'), eviction_policy='least-recently-used', size_limit=500*1024*1024)
def get_lock(k='dlock', ttl=None): return kv.add(k, 'locked', expire=ttl)
def release_lock(k='dlock'): kv.delete(k)
def clear_cache(): startthread(kv.clear)
def cache(p=None, ttl=3600, **_):
    def d(f): return memoize_stampede(kv, expire=ttl, name=p)(f)
    return d

@cache('jwt_scrt', ttl=10*365*24*3600)
def generate_jwt_scrt(): return secrets.token_urlsafe(32)

def _env_url(k, default):
    v = os.getenv(k, default)
    return v if v.startswith(('http://','https://')) else f'https://{v}'

cfg = AttrDictDefault(app_nm=os.getenv('APP_NAME','Lego'),
                      app_sh=os.getenv('APP_SH','lego'),
                      site_author=os.getenv('SITE_AUTHOR','Karthik Rajgopal'),
                      site_description=os.getenv('SITE_DESCRIPTION','Build performant webapps one block at a time'),
                      site_keywords=os.getenv('SITE_KEYWORDS','lego, fastHTML, Oat, webapp, python'),
                      jwt_scrt=os.getenv('JWT_SCRT', generate_jwt_scrt()),
                      mode=os.getenv('MODE','dev'),
                      domain=_env_url('DOMAIN','http://localhost:5001'),
                      resend_api_key=os.getenv('RESEND_API_KEY', ''),
                      need_backup=str2bool(os.getenv('NEED_BACKUP', 'false')),
                      port=str2int(os.getenv('PORT', '5001')),
                      tkn_exp=str2int(os.getenv('TOKEN_EXP', '691200')),
                      rc_typ=os.getenv('RC_TYPE', 's3'),
                      rc_remote=dict(provider=os.getenv('RC_PROVIDER', 'Cloudflare'),
                                     access_key_id=os.getenv('CF_ACCESS_KEY_ID', ''),
                                     secret_access_key=os.getenv('CF_SCRT_ACCESS_KEY', ''),
                                     endpoint=os.getenv('CF_ENDPOINT', '')),
                      purge=str2bool(os.getenv('PURGE', 'false')),
                      redis_host=os.getenv('REDIS_HOST', 'localhost'),
                      redis_pwd=os.getenv('REDIS_PWD', None),
                      typwrtr_dyn_txt='Build, Expand, Innovate',
                      typwrtr_stat_txt='like lego',
                      data_root=data_root, backup_path=backups,
                      db=get_db_pth(), static=static,
                      svg=in_static('svg'), log_file=get_log_pth(),
                      github_repo=os.getenv('GITHUB_REPO', 'Karthik777/lego'))

def not_prod(): return cfg.mode != 'production'
def get_db_dir(): return Path(cfg.db).parent if cfg.db else Path(data_root) / 'db'
def slug(word: str): return hl.md5(word.lower().encode()).hexdigest()[:11]

class AppErr(Exception):
    def __init__(self, msg=None, fields=None):
        super().__init__(msg)
        self.msg, self.fields = msg, fields or []

@threaded
def send_email(to, subject, html: FT, from_='accounts@lego.com'):
    if isinstance(html, FT): html = to_xml(html)
    import resend
    resend.api_key = cfg.resend_api_key
    r = resend.Emails.send({'from': from_, 'to': to, 'subject': subject, 'html': html})
    print(f'Resend Result: {r}')

def home(next=None): return Redirect(next or RouteOverrides.home)

@dataclass
class RouteOverrides: lgn, lgt, home, skip = '/lgn', '/lgt', cfg.domain, ['/health']

def get_caller_fn(skip=None):
    import inspect
    skip = skip or set(); skip.add(__file__)
    skip = {Path(f).resolve() for f in skip}
    for finfo in inspect.stack():
        fp = Path(finfo.filename).resolve()
        if fp not in skip: return fp.stem
    return None

_fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
def rot_log(log_file=cfg.log_file, lvl=logging.WARN): return get_logger(fn=log_file, lvl=lvl, rot=True)

def get_logger(fn=cfg.log_file, lvl=logging.INFO, rot=True):
    fn = str(fn)
    lgr = logging.getLogger(fn)
    lgr.setLevel(lvl)
    for h in lgr.handlers[:]: lgr.removeHandler(h) if isinstance(h, (logging.FileHandler, RFH)) else None
    h = logging.FileHandler(fn) if not rot else RFH(fn, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    h.setLevel(lvl); h.setFormatter(_fmt); lgr.addHandler(h)
    ch = logging.StreamHandler(); ch.setLevel(logging.INFO); ch.setFormatter(_fmt); lgr.addHandler(ch)
    return lgr

def quick_lgr(p=None):
    lgr = get_logger(fn=get_log_pth(p or get_caller_fn({__file__}) or Path(__file__).stem), lvl=logging.INFO, rot=False)
    return lgr.info, lgr.error, lgr.warning