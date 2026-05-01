import os
from dataclasses import dataclass
from fastcore.all import AttrDictDefault, str2int, Path
from lego.core import cfg as core_cfg, get_db_pth, RouteOverrides

# Make solv routes available to unauthenticated requests for static assets.
# The actual auth gate is enforced inside each handler via _require_user().
# This list is consulted by lego.auth.setup_beforeware() at app.connect time.
for _pat in [r'/solv/static/.*']:
    if _pat not in RouteOverrides.skip: RouteOverrides.skip.append(_pat)

# === Block-level config ===
cfg = core_cfg
cfg.update(AttrDictDefault(
    solv_db=get_db_pth('solv'),
    solv_dialog_root=Path(os.getenv('SOLV_DIALOG_ROOT', 'data/dialogs')),
    solv_kernel_idle_min=str2int(os.getenv('SOLV_KERNEL_IDLE_MIN', '30')),
    llm_default_model=os.getenv('LLM_DEFAULT_MODEL', 'claude-sonnet-4-20250514'),
    llm_completion_model=os.getenv('LLM_COMPLETION_MODEL', 'claude-haiku-4-20250514'),
    llm_default_mode=os.getenv('LLM_DEFAULT_MODE', 'standard'),
    llm_max_context_tokens=str2int(os.getenv('LLM_MAX_CONTEXT_TOKENS', '180000')),
    solv_embed_model=os.getenv('SOLV_EMBED_MODEL', 'minishlab/potion-retrieval-32M'),
    solv_bash_allowlist=os.getenv('SOLV_BASH_ALLOWLIST', 'ls,pwd,cat,head,tail,wc,grep,find,echo,which,git').split(','),
))
cfg.solv_dialog_root.mkdir(parents=True, exist_ok=True)


# === AI modes ===
class Mode:
    learning, concise, standard = 'learning', 'concise', 'standard'
    all = (learning, concise, standard)


# === Cell / message types ===
class MsgT:
    code, note, prompt = 'code', 'note', 'prompt'
    all = (code, note, prompt)


# === Model registry ===
@dataclass(frozen=True)
class ModelSpec:
    name: str
    litellm_id: str
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_prefill: bool = False
    max_tokens: int = 180000


MODELS = {
    'claude-sonnet-4': ModelSpec('Claude Sonnet 4', 'claude-sonnet-4-20250514', True, True, True, 200000),
    'claude-haiku-4': ModelSpec('Claude Haiku 4', 'claude-haiku-4-20250514', True, True, True, 200000),
    'gpt-4o': ModelSpec('GPT-4o', 'openai/gpt-4o', True, True, False, 128000),
    'gpt-4o-mini': ModelSpec('GPT-4o mini', 'openai/gpt-4o-mini', True, True, False, 128000),
    'gemini-2.5-flash': ModelSpec('Gemini 2.5 Flash', 'gemini/gemini-2.5-flash', True, True, False, 1000000),
}


def model_for(name_or_id):
    if name_or_id in MODELS: return MODELS[name_or_id]
    for s in MODELS.values():
        if s.litellm_id == name_or_id: return s
    return ModelSpec(name_or_id, name_or_id)


# === Routes ===
class Routes:
    base = '/solv'
    index = base + '/'
    search = base + '/search'
    import_ = base + '/import'

    @staticmethod
    def view(name): return f'{Routes.base}/{name}'
    @staticmethod
    def add_msg(name): return f'{Routes.base}/{name}/msg'
    @staticmethod
    def msg(name, cid): return f'{Routes.base}/{name}/msg/{cid}'
    @staticmethod
    def msg_action(name, cid, action): return f'{Routes.base}/{name}/msg/{cid}/{action}'
    @staticmethod
    def run(name, cid): return f'{Routes.base}/{name}/run/{cid}'
    @staticmethod
    def stream(name, cid): return f'{Routes.base}/{name}/stream/{cid}'
    @staticmethod
    def stop(name, cid): return f'{Routes.base}/{name}/stop/{cid}'
    @staticmethod
    def split(name, cid): return f'{Routes.base}/{name}/split/{cid}'
    @staticmethod
    def kernel_restart(name): return f'{Routes.base}/{name}/kernel/restart'
    @staticmethod
    def vars(name): return f'{Routes.base}/{name}/vars'
    @staticmethod
    def export(name): return f'{Routes.base}/{name}/export'
    @staticmethod
    def meta(name): return f'{Routes.base}/{name}/meta'
    @staticmethod
    def delete(name): return f'{Routes.base}/{name}/delete'


PROMPTS_DIR = Path(__file__).parent / 'prompts'
STATIC_DIR = Path(__file__).parent / 'static'


def load_prompt(mode):
    p = PROMPTS_DIR / f'{mode}.md'
    if not p.exists(): p = PROMPTS_DIR / f'{Mode.standard}.md'
    return p.read_text() if p.exists() else ''
