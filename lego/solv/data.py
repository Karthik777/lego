"""Dialog persistence as `.ipynb` files (nbformat v4).

Each notebook cell is a SolveIt message. Mapping:
  code   message  -> nbformat code cell      (metadata.solv.type='code')
  note   message  -> nbformat markdown cell  (metadata.solv.type='note')
  prompt message  -> nbformat markdown cell  (metadata.solv.type='prompt'),
                     with metadata.solv.response and .tool_calls populated after streaming.
"""
import time, uuid, re
from pathlib import Path
from .cfg import cfg, MsgT, Mode

try:
    import nbformat
    from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
except ImportError:  # pragma: no cover - graceful degradation while deps install
    nbformat = None

_SLUG_RE = re.compile(r'[^a-z0-9._-]+')


def slugify(name):
    s = _SLUG_RE.sub('-', (name or '').lower().strip()).strip('-._')
    return s or 'untitled'


def user_root(user_id):
    'Return the dialog root for a user, creating it if needed.'
    p = cfg.solv_dialog_root / str(user_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def dialog_path(user_id, name):
    'Resolved, traversal-safe path to a user dialog. Raises ValueError on traversal.'
    root = user_root(user_id).resolve()
    name = slugify(name)
    if not name.endswith('.ipynb'): name = name + '.ipynb'
    p = (root / name).resolve()
    if root not in p.parents and p != root:
        raise ValueError(f'invalid dialog path: {name}')
    return p


def list_dialogs(user_id):
    root = user_root(user_id)
    out = []
    for p in sorted(root.glob('*.ipynb'), key=lambda x: x.stat().st_mtime, reverse=True):
        try: nb = nbformat.read(str(p), as_version=4) if nbformat else None
        except Exception: nb = None
        meta = (nb.metadata.get('solv', {}) if nb else {})
        out.append(dict(name=p.stem, path=str(p),
                        title=meta.get('title') or p.stem,
                        description=meta.get('description', ''),
                        ai_mode=meta.get('ai_mode', cfg.llm_default_mode),
                        model=meta.get('model', cfg.llm_default_model),
                        n_cells=len(nb.cells) if nb else 0,
                        updated_at=p.stat().st_mtime))
    return out


def now(): return time.time()
def new_id(): return uuid.uuid4().hex[:12]


def _default_meta(typ, **extra):
    return dict(id=new_id(), type=typ, hidden=False, pinned=False, exported=True,
                created_at=now(), updated_at=now(), tokens=0, **extra)


def _ensure_solv_meta(cell, typ=None):
    'Make sure cell.metadata.solv exists with defaults; fix up legacy cells.'
    meta = cell.metadata.setdefault('solv', {})
    if 'id' not in meta: meta['id'] = new_id()
    if 'type' not in meta:
        meta['type'] = typ or (MsgT.code if cell.cell_type == 'code' else MsgT.note)
    meta.setdefault('hidden', False)
    meta.setdefault('pinned', False)
    meta.setdefault('exported', True)
    meta.setdefault('created_at', now())
    meta.setdefault('updated_at', now())
    meta.setdefault('tokens', 0)
    return meta


def new_dialog(user_id, name, title=None, ai_mode=None, model=None):
    if nbformat is None: raise RuntimeError('nbformat not installed')
    p = dialog_path(user_id, name)
    if p.exists(): raise FileExistsError(p)
    nb = new_notebook()
    nb.metadata['solv'] = dict(
        title=title or name, description='',
        ai_mode=ai_mode or cfg.llm_default_mode,
        model=model or cfg.llm_default_model,
        created_at=now(), updated_at=now(),
        owner_id=user_id)
    nb.metadata['kernelspec'] = dict(name='python3', display_name='Python 3', language='python')
    nb.metadata['language_info'] = dict(name='python')
    save(p, nb)
    return p, nb


def load(user_id, name):
    if nbformat is None: raise RuntimeError('nbformat not installed')
    p = dialog_path(user_id, name)
    nb = nbformat.read(str(p), as_version=4)
    nb.metadata.setdefault('solv', {})
    for c in nb.cells: _ensure_solv_meta(c)
    return p, nb


def save(p, nb):
    nb.metadata.setdefault('solv', {})['updated_at'] = now()
    nbformat.write(nb, str(p))


def delete(user_id, name):
    p = dialog_path(user_id, name)
    if p.exists(): p.unlink()
    return True


def make_cell(typ, content=''):
    'Build a new nbformat cell of the given solv message type.'
    if nbformat is None: raise RuntimeError('nbformat not installed')
    if typ == MsgT.code: cell = new_code_cell(content)
    else: cell = new_markdown_cell(content)
    cell.metadata['solv'] = _default_meta(typ)
    if typ == MsgT.prompt:
        cell.metadata['solv']['response'] = ''
        cell.metadata['solv']['tool_calls'] = []
    return cell


def find_cell(nb, cid):
    for i, c in enumerate(nb.cells):
        if c.metadata.get('solv', {}).get('id') == cid: return i, c
    return -1, None


def add_msg(nb, typ, content='', position=None):
    cell = make_cell(typ, content)
    if position is None or position >= len(nb.cells): nb.cells.append(cell)
    else: nb.cells.insert(max(0, position), cell)
    return cell


def update_msg(nb, cid, content=None, **meta_updates):
    i, c = find_cell(nb, cid)
    if i < 0: return None
    if content is not None: c.source = content
    m = c.metadata['solv']
    m.update(meta_updates)
    m['updated_at'] = now()
    return c


def del_msg(nb, cid):
    i, _ = find_cell(nb, cid)
    if i < 0: return False
    nb.cells.pop(i); return True


def move_msg(nb, cid, new_pos):
    i, c = find_cell(nb, cid)
    if i < 0: return False
    nb.cells.pop(i)
    nb.cells.insert(max(0, min(new_pos, len(nb.cells))), c)
    return True


def find_msgs(nb, pattern=None, typ=None):
    out, rx = [], re.compile(pattern, re.I) if pattern else None
    for c in nb.cells:
        m = c.metadata.get('solv', {})
        if typ and m.get('type') != typ: continue
        if rx and not rx.search(c.source or ''): continue
        out.append(dict(id=m.get('id'), type=m.get('type'), source=c.source,
                        pinned=m.get('pinned'), hidden=m.get('hidden')))
    return out


def set_outputs(nb, cid, outputs):
    'Persist nbformat outputs onto a code cell.'
    i, c = find_cell(nb, cid)
    if i < 0 or c.cell_type != 'code': return False
    c.outputs = outputs or []
    return True


def cell_type(c): return c.metadata.get('solv', {}).get('type', MsgT.note)
def is_hidden(c): return bool(c.metadata.get('solv', {}).get('hidden'))
def is_pinned(c): return bool(c.metadata.get('solv', {}).get('pinned'))
def cid_of(c): return c.metadata.get('solv', {}).get('id')
