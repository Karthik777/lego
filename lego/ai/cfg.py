import os
from dataclasses import dataclass
from fasthtml.common import *
from lego.core import cfg as core_cfg, AppErr, get_db_pth, RouteOverrides, PresetsT

cfg = core_cfg

@dataclass(frozen=True)
class Routes:
    base = '/ai'
    skip = ['/ai', r'/ai/.*']   # let handlers gate auth themselves (they check `if not auth`); keeps the auth beforeware from short-circuiting
cfg.update(AttrDictDefault(db=get_db_pth('ai')))
cfg.update(AttrDictDefault(
    anthropic_api_key = os.getenv('OPENAI_API_KEY', ''),
    ai_default_model  = os.getenv('AI_DEFAULT_MODEL', 'gpt-5.4'),
))

class AIPresetsT:
    usr_msg = f'{PresetsT.secondary} rounded-tl-4xl rounded-bl-4xl rounded-tr-3xl rounded-sm px-4 py-3'