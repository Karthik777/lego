import hashlib as hl
from fasthtml.common import Redirect, Path, Database, FT, to_xml, threaded, dataclass, AttrDictDefault, str2bool, str2int, get_key
import os

__all__ = ['cfg', 'database', 'AppErr', 'home', 'send_email', 'RouteOverrides', 'get_pth','get_db_pth',
           'in_static', 'get_log_pth', 'get_db_dir', 'not_prod', 'get_caller_fn']

data_root, backups, static=Path('data'), Path('backups'), Path('static')
def get_pth(nm, sf='',mk=False):
    p = data_root / sf / nm
    if not p.exists() and mk:p.mk_write('')
    return p

def get_db_pth(nm='lego'): return get_pth(f'{nm}.db', 'db')
def in_static(nm, sf=''): return static / sf / nm # for static folder access
def get_log_pth(nm='lego', create=True): return get_pth(f'{nm}.log', 'logs', create)

cfg = AttrDictDefault(app_nm=os.getenv('APP_NAME','Lego'),
                      app_sh=os.getenv('APP_SH','lego'),
                      site_author=os.getenv('SITE_AUTHOR','Karthik Rajgopal'),
                      site_description=os.getenv('SITE_DESCRIPTION','Build modern performant webapps one block at a time'),
                      site_keywords=os.getenv('SITE_KEYWORDS','lego, fastHTML, MonsterUI, webapp, python'),
                      jwt_scrt=os.getenv('JWT_SCRT',get_key()),
                      mode=os.getenv('MODE','test'),
                      domain=os.getenv('DOMAIN','http://localhost:5001'),
                      resend_api_key=os.getenv('RESEND_API_KEY', ''),
                      need_backup=str2bool(os.getenv('NEED_BACKUP', 'false')),
                      port=str2int(os.getenv('PORT', '5001')),
                      tkn_exp=str2int(os.getenv('TOKEN_EXP', '691200')),
                      rc_typ=os.getenv('RC_TYPE', 's3'),
                      rc_remote=dict(provider=os.getenv('RC_PROVIDER', 'Cloudflare'), access_key_id=os.getenv('CF_ACCESS_KEY_ID', ''),
                                 secret_access_key=os.getenv('CF_SCRT_ACCESS_KEY', ''), endpoint=os.getenv('CF_ENDPOINT', '')),
                      purge=str2bool(os.getenv('PURGE', 'true')),
                      redis_host=os.getenv('REDIS_HOST', 'localhost'),
                      redis_pwd=os.getenv('REDIS_PWD', None),
                      typwrtr_dyn_txt='Build, Expand, Innovate',
                      typwrtr_stat_txt='like lego',
                      data_root=data_root, backup_path=backups,
                      db=get_db_pth(), static=static,
                      svg=in_static('svg'), log_file=get_log_pth())

def not_prod(): return cfg.mode != 'production'
def get_db_dir(): return Path(cfg.db).parent if cfg.db else Path(data_root) / 'db'

# TODO: support Postgres using fastsql
def database(path=cfg.db, wal=True) -> Database:
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    tracer = lambda sql, params: print('SQL: {} - params: {}'.format(sql, params))
    db = Database(path, tracer=tracer if cfg.mode == 'dev' else None)
    if wal: db.enable_wal()
    return db

class AppErr(Exception):
    def __init__(self, msg=None, fields=None):
        super().__init__(msg)
        self.msg, self.fields = msg, fields or []

@threaded
def send_email(to, subject, html: FT):
    if isinstance(html, FT): html = to_xml(html)
    import resend
    resend.api_key = cfg.resend_api_key
    print(f'Resend Result: {html}')
    r = resend.Emails.send({'from': 'accounts@vedicreader.com', 'to': to, 'subject': subject, 'html': html})

def home(): return Redirect(RouteOverrides.home)

@dataclass
class RouteOverrides: lgt,home,skip='/lgt',cfg.domain,['/health']

def get_caller_fn(skip=None):
    """Get the path of the outermost non-library script in the call stack."""
    import inspect
    skip = skip or set(); skip.add(__file__)
    skip = {Path(f).resolve() for f in skip}
    for finfo in inspect.stack():
        fp = Path(finfo.filename).resolve()
        if fp not in skip: return fp.stem
    return None

def slug(word: str): return hl.md5(word.lower().encode()).hexdigest()[:11]