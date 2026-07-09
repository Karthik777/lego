from fasthtml.common import *
from lego.core import cfg as core_cfg, AppErr, get_db_pth, RouteOverrides, PresetsT

cfg = core_cfg
cfg.update(AttrDictDefault(db=get_db_pth('ai')))

class AIPresetsT:
    usr_msg = f'{PresetsT.secondary} rounded-tl-4xl rounded-bl-4xl rounded-tr-3xl rounded-sm px-4 py-3'