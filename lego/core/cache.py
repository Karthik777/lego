from _pickle import loads, dumps
from abc import ABC, abstractmethod
import hashlib as hl
from functools import wraps
from fastlite import NotFoundError, SQLError, noop, threaded, startthread
import redis
import time
from .logging import get_logger
from .cfg import  get_log_pth, cfg, database

lgr = get_logger(get_log_pth('cache'))
info, err, warn = lgr.info, lgr.error, lgr.warning

__all__ = ['cache', 'clear_cache', 'kv', 'get_lock']

def _loads(v):
    try: return loads(v) if v else None
    except Exception as e: err(f'error loading value {v}: {e}'); return None

def _dumps(v):
    try: return dumps(v,protocol=-1) if v else dumps({})
    except Exception as e: err(f'error encoding value {v}: {e}');return dumps({})

class Cache(ABC):
    @abstractmethod
    def get(self, k): pass
    @abstractmethod
    def set(self, k, v, ttl=3600, nx=False, **kw): pass
    @abstractmethod
    def purge(self, k=None, flush=False): pass

class Redis(Cache):
    def __init__(self, h=cfg.redis_host, p=6379, db=0, pwd=cfg.redis_pwd):
        try:
            self.c = redis.Redis(host=h, port=p, db=db, password=pwd)
            self.c.ping()
        except (redis.ConnectionError, redis.RedisError) as e: err(f"Redis connection failed: {e}"); raise ValueError(e)

    def get(self, k):
        try:
            v = self.c.get(k) if k else None
            return (_loads(v), self.c.ttl(k)) if v else None
        except redis.RedisError: return None

    def set(self, k, v, ttl=3600, nx=False, **kw):
        try: return self.c.set(k,_dumps(v),ex=ttl,nx=nx) if (k and v) else False
        except redis.RedisError: return False

    def purge(self, key=None, flush=False):
        try: self.c.delete(key) if key else self.c.flushdb() if flush else noop()
        except redis.RedisError: err("Redis: Purge failed")

class SQlite(Cache):
    def __init__(self, path=cfg.db):
        self.db = database(path)
        self.t = self.db.t.key_value
        self.create()

    def create(self, replace=False):
        self.t.create(key=str, value=bytes, expiry=float, last_access=float, size=int, pk='key', not_null={'value', 'size'},
                      defaults=dict(expiry=0.0, last_access=0.0, size=0), if_not_exists=True, replace=replace)
        self.t.dataclass()

    def get(self, k):
        try:
            if not k: return None
            r=self.t.selectone(where='key=? and expiry>?', where_args=[k, time.time()])
            return _loads(r.value), r.expiry - time.time()
        except (NotFoundError, SQLError): return None

    def set(self, k, v, ttl=3600.0, nx=False, **kw):
        if not (k and v) or (nx and self.get(k)): return False
        exp=time.time() + ttl if ttl > 0 else 0.0
        try:
            self._cull()
            return self.t.insert(dict(key=k, value=_dumps(v), expiry=exp), replace=True)
        except SQLError: return False

    @threaded
    def _cull(self): self.t.delete_where(where='expiry != 0 and expiry<?', where_args=[time.time()])

    def purge(self, key=None, flush=False):
        try:
            if flush: self.create(True)
            if key: self.t.delete(key)
            self._cull()
        except SQLError: err('SQLite: Purge failed')

class CacheTyp: redis, sqlite ='redis','sqlite'
def _mk_cache(typ=CacheTyp.sqlite):
    try: return Redis() if typ == 'redis' else SQlite()
    except ValueError: return SQlite()

kv = _mk_cache()
def slug(word: str): return hl.md5(word.lower().encode()).hexdigest()[:11]
def cache(p=None, ttl=3600, func=noop, autoref=True):
    def d(f):
        @wraps(f)
        def w(*a, **kw):
            k= slug(f'{p or f.__name__}:{a}:{kw}')
            if kw.get('purge', False): kv.purge(k)
            hit = kv.get(k)
            if hit:
                v,exp = hit
                if autoref and exp < ttl*0.2 and get_lock(f.__name__, 60): startthread(lambda: kv.set(k,f(*a,**kw), ttl))
                return v
            r = f(*a, **kw)
            if get_lock(f.__name__, 60):
                startthread(lambda :kv.set(k, r, ttl))
                if callable(func): startthread(lambda: func(*a,**kw))
            return r
        return w
    return d

def get_lock(k='dlock', ttl=None): return kv.set(k, 'locked', ttl=ttl, nx=True)
def release_lock(k='dlock'): kv.purge(k)
def clear_cache(): startthread(lambda: kv.purge(flush=True))
