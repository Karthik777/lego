import logging
from logging.handlers import RotatingFileHandler
from .cfg import cfg, get_log_pth, get_caller_fn

__all__ = ['rot_log', 'get_logger', 'quick_lgr']

fmt=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
def rot_log(log_file=cfg.log_file, lvl=logging.WARN): return get_logger(fn=log_file, lvl=lvl, rot=True)

def get_logger(fn=cfg.log_file, lvl=logging.INFO, rot=True):
    fn = str(fn)
    lgr = logging.getLogger(fn)
    lgr.setLevel(lvl)
    for h in lgr.handlers[:]: lgr.removeHandler(h) if isinstance(h, (logging.FileHandler, RotatingFileHandler)) else None
    h = logging.FileHandler(fn) if not rot else RotatingFileHandler(fn, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
    h.setLevel(lvl)
    h.setFormatter(fmt)
    lgr.addHandler(h)
    return lgr

def quick_lgr(p=None):
    from fastcore.all import Path
    lgr=get_logger(fn=get_log_pth(p or get_caller_fn({__file__}) or Path(__file__).stem), lvl=logging.INFO, rot=False)
    return lgr.info, lgr.error, lgr.warning