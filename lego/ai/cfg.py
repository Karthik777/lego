from fasthtml.common import *
from lego.core import cfg as core_cfg, AppErr, get_db_pth, RouteOverrides

cfg = core_cfg
cfg.update(AttrDictDefault(db=get_db_pth('ai')))