"""Routes for the solv block.

All routes are mounted under /solv. They require an authenticated user; if the
auth block is connected, its Beforeware will redirect unauthenticated users.
"""
from pathlib import Path
from fasthtml.common import (Beforeware, FileResponse, JSONResponse, Redirect, Response,
                              StreamingResponse, Link, Script, Style)
from monsterui.all import ButtonT
from starlette.requests import Request

from lego.core import landing, base
from lego.auth.cfg import Routes as AuthRoutes

from . import data as D, kernel, llm as L, tools as T, search as S, ui as U
from .cfg import cfg, MsgT, Mode, Routes, MODELS, model_for, STATIC_DIR
from .render import render_outputs

__all__ = ['connect']


# ---------- helpers ----------

def _user_id(req):
    auth = req.scope.get('auth') or {}
    return auth.get('id') if isinstance(auth, dict) else None


def _require_user(req):
    uid = _user_id(req)
    if uid is None: return None, Redirect(AuthRoutes.login)
    return uid, None


def _hdrs():
    return [Link(rel='stylesheet', href='/static/solv/solv.css'),
            Script(src='/static/solv/solv.js', defer=True)]


def _frame(content, usr=None, title='solv'):
    'Wrap full-page UI in lego base + inject solv assets.'
    extras = _hdrs()
    page = base(content, usr=usr, title=title)
    return *extras, page


# ---------- dialog routes ----------

async def index(req):
    uid, redir = _require_user(req)
    if redir: return redir
    dialogs = D.list_dialogs(uid)
    return _frame(U.index_view(uid, dialogs), usr=req.scope.get('auth'), title='solv · dialogs')


async def create_dialog(req):
    uid, redir = _require_user(req)
    if redir: return redir
    form = await req.form()
    name = (form.get('name') or '').strip()
    if not name: return Redirect(Routes.index)
    try: D.new_dialog(uid, name)
    except FileExistsError: pass
    return Redirect(Routes.view(D.slugify(name)))


async def view_dialog(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    try: p, nb = D.load(uid, name)
    except FileNotFoundError: return Redirect(Routes.index)
    dialogs = D.list_dialogs(uid)
    sid = kernel.session_id(uid, name)
    vars_ = kernel.pool.get_vars(sid)
    S.index_dialog(uid, name, nb)
    return _frame(U.dialog_view(uid, name, nb, dialogs, vars_=vars_),
                  usr=req.scope.get('auth'), title=f'solv · {name}')


async def delete_dialog(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    D.delete(uid, name)
    S.remove_dialog(uid, name)
    kernel.pool.close(kernel.session_id(uid, name))
    return Redirect(Routes.index)


async def update_meta(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    form = await req.form()
    meta = nb.metadata.setdefault('solv', {})
    for k in ('title', 'description', 'model', 'ai_mode'):
        v = form.get(k)
        if v is not None: meta[k] = v
    D.save(p, nb)
    return Response(status_code=204)


async def export_dialog(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p = D.dialog_path(uid, name)
    return FileResponse(str(p), filename=p.name, media_type='application/x-ipynb+json')


# ---------- message routes ----------

async def add_message(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    qp = dict(req.query_params)
    form = (await req.form()) if req.method == 'POST' else {}
    msg_type = qp.get('msg_type') or form.get('msg_type') or MsgT.code
    content = form.get('content', '')
    pos = qp.get('position') or form.get('position')
    pos = int(pos) if pos not in (None, '') else None
    cell = D.add_msg(nb, msg_type, content, pos)
    D.save(p, nb)
    return U.cell(name, cell)


async def update_message(req, name: str, cid: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    form = await req.form()
    content = form.get('content')
    c = D.update_msg(nb, cid, content=content)
    if c is None: return Response(status_code=404)
    D.save(p, nb)
    return Response(status_code=204)


async def delete_message(req, name: str, cid: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    if D.del_msg(nb, cid): D.save(p, nb)
    return Response(status_code=200)


async def msg_action(req, name: str, cid: str, action: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    _, c = D.find_cell(nb, cid)
    if c is None: return Response(status_code=404)
    m = c.metadata.setdefault('solv', {})
    if action == 'pin':    m['pinned']  = not bool(m.get('pinned'))
    elif action == 'hide': m['hidden']  = not bool(m.get('hidden'))
    elif action == 'export': m['exported'] = not bool(m.get('exported'))
    else: return Response(status_code=400)
    D.save(p, nb)
    return U.cell(name, c)


# ---------- execution / chat ----------

async def run_cell(req, name: str, cid: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    _, c = D.find_cell(nb, cid)
    if c is None or D.cell_type(c) != MsgT.code:
        return Response(status_code=404)
    form = await req.form()
    new_src = form.get('content')
    if new_src is not None and new_src != (c.source or ''):
        D.update_msg(nb, cid, content=new_src)
    sid = kernel.session_id(uid, name)
    outs = await kernel.pool.arun(sid, c.source or '')
    D.set_outputs(nb, cid, outs)
    D.save(p, nb)
    return render_outputs(outs, cell_id=cid)


async def stream_chat(req, name: str, cid: str):
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    _, c = D.find_cell(nb, cid)
    if c is None or D.cell_type(c) != MsgT.prompt:
        return Response(status_code=404)
    qp = dict(req.query_params)
    new_src = qp.get('content')
    if new_src is not None and new_src != (c.source or ''):
        D.update_msg(nb, cid, content=new_src)
        D.save(p, nb)
    sid = kernel.session_id(uid, name)
    meta = nb.metadata.get('solv', {})
    model = meta.get('model', cfg.llm_default_model)
    mode = meta.get('ai_mode', cfg.llm_default_mode)
    tool_fns = L.collect_tool_refs(nb, cid, T.registry.all())

    async def gen():
        # Set context vars so tools know which dialog/session is active.
        tok_s = L.current_session.set(sid)
        tok_d = L.current_dialog.set(p)
        try:
            async for chunk in L.stream_response(nb, c, model=model, mode=mode, tools=tool_fns or None):
                # SSE: data lines must not contain bare newlines.
                for line in chunk.splitlines() or ['']:
                    yield f'data: {line}\n'
                yield '\n'
            # Persist final response (already set on cell metadata by stream_response).
            D.save(p, nb)
            yield 'event: done\ndata: ok\n\n'
        finally:
            L.current_session.reset(tok_s)
            L.current_dialog.reset(tok_d)

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


async def stop_stream(req, name: str, cid: str):
    # Best-effort: actual cancellation requires a per-session control channel.
    return Response(status_code=204)


async def split_response(req, name: str, cid: str):
    'Split a prompt response into separate code/note cells (W key).'
    uid, redir = _require_user(req)
    if redir: return redir
    p, nb = D.load(uid, name)
    i, c = D.find_cell(nb, cid)
    if c is None or D.cell_type(c) != MsgT.prompt: return Response(status_code=404)
    text = c.metadata.get('solv', {}).get('response', '') or ''
    blocks, buf, in_code, lang = [], [], False, None
    for line in text.splitlines():
        if line.startswith('```'):
            if in_code:
                blocks.append((MsgT.code if (lang or '').lower().startswith(('py', 'python')) else MsgT.note,
                                '\n'.join(buf)))
                buf = []; in_code = False; lang = None
            else:
                if buf: blocks.append((MsgT.note, '\n'.join(buf))); buf = []
                in_code = True; lang = line[3:].strip()
        else:
            buf.append(line)
    if buf: blocks.append((MsgT.code if in_code else MsgT.note, '\n'.join(buf)))
    insert_at = i + 1
    for typ, body in blocks:
        if not body.strip(): continue
        D.add_msg(nb, typ, body, insert_at)
        insert_at += 1
    D.save(p, nb)
    return U.cell_list(name, nb)


async def restart_kernel(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    sid = kernel.session_id(uid, name)
    kernel.pool.restart(sid)
    return Response(status_code=204)


async def kernel_vars(req, name: str):
    uid, redir = _require_user(req)
    if redir: return redir
    sid = kernel.session_id(uid, name)
    vars_ = kernel.pool.get_vars(sid)
    return U.symbol_browser(name, vars_)


# ---------- search ----------

async def search_route(req):
    uid, redir = _require_user(req)
    if redir: return redir
    q = (req.query_params.get('q') or '').strip()
    if not q: return U.search_results([])
    rows = S.search(uid, q)
    return U.search_results(rows)


# ---------- static ----------

async def serve_static(req, fname: str):
    # Fallback handler for /solv/static/* — most requests are matched first by
    # FastHTML's global `/{fname:path}.{ext:static}` route, which serves from
    # `static/solv/...` (we mirror our assets there in `connect()`).
    p = (STATIC_DIR / fname).resolve()
    if STATIC_DIR.resolve() not in p.parents or not p.exists():
        return Response(status_code=404)
    return FileResponse(str(p))


def _mirror_static():
    'Copy solv/static/* into project static/solv/ so FastHTML can serve them.'
    import shutil
    dst = Path('static') / 'solv'
    dst.mkdir(parents=True, exist_ok=True)
    for src in STATIC_DIR.glob('*'):
        if src.is_file():
            try: shutil.copy2(src, dst / src.name)
            except Exception: pass


# ---------- scheduler ----------

def _kernel_gc():
    try: kernel.pool.gc(idle_seconds=cfg.solv_kernel_idle_min * 60)
    except Exception: pass


# ---------- registration ----------

def connect(app):
    'Mount all solv routes onto the lego app.'
    # Mirror static assets into project static/ so FastHTML's global static
    # handler serves them at /static/solv/*.
    _mirror_static()

    # Static (fallback)
    app.get('/solv/static/{fname:path}')(serve_static)

    # Dialogs
    app.get(Routes.index)(index)
    app.post(Routes.index)(create_dialog)

    app.get(Routes.search)(search_route)

    app.get(Routes.base + '/{name}')(view_dialog)
    app.delete(Routes.base + '/{name}')(delete_dialog)
    app.put(Routes.base + '/{name}/meta')(update_meta)
    app.get(Routes.base + '/{name}/export')(export_dialog)

    # Messages
    app.post(Routes.base + '/{name}/msg')(add_message)
    app.post(Routes.base + '/{name}/msg/{cid}')(update_message)
    app.delete(Routes.base + '/{name}/msg/{cid}')(delete_message)
    app.post(Routes.base + '/{name}/msg/{cid}/{action}')(msg_action)

    # Execution
    app.post(Routes.base + '/{name}/run/{cid}')(run_cell)
    app.get(Routes.base + '/{name}/stream/{cid}')(stream_chat)
    app.post(Routes.base + '/{name}/stop/{cid}')(stop_stream)
    app.post(Routes.base + '/{name}/split/{cid}')(split_response)
    app.post(Routes.base + '/{name}/kernel/restart')(restart_kernel)
    app.get(Routes.base + '/{name}/vars')(kernel_vars)

    # Schedule kernel GC
    try:
        from lego.core.utils import scheduler
        scheduler.add_job(_kernel_gc, trigger='interval', minutes=15, id='solv_kernel_gc',
                           replace_existing=True)
    except Exception: pass
