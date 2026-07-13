# lego/ai/app.py
from fasthtml.common import *
from monsterui.franken import render_md
from lego.core import base, home, RouteOverrides
from . import data as d, llm, ui
from .cfg import cfg, Routes

def _cid_for(req, auth):
    ch = d.latest_chat(auth['id'])
    return ch.id if ch else d.new_chat(auth['id'])

def ai_home(req, auth):
    if not auth: return home()
    return base(ui.chats(_cid_for(req, auth)), auth, title='AI')

def ai_new(req, auth):
    if not auth: return home()
    cid = d.new_chat(auth['id'])
    return Response(headers={'HX-Redirect': f'/ai/c/{cid}'})

def ai_load(req, auth, cid: str):
    if not auth: return home()
    if not d.get_chat(cid, auth['id']): return home()
    return base(ui.chats(cid), auth, title='AI')

def ai_send(req, auth, cid: str, message: str):
    if not auth: return home()
    if not d.get_chat(cid, auth['id']): return home()
    d.add_msg(cid, 'user', message)
    return ui.msg(message, usr=True), ui.sse_bubble(cid)

async def ai_stream(req, auth, cid: str):
    if not auth: return home()
    if not d.get_chat(cid, auth['id']): return home()
    async def gen():
        acc = ''
        try:
            async for delta in llm.astream(cid):
                acc += delta
                yield sse_message(Div(render_md(acc)), event='message')  # wrap: render_md is a NotStr
        except Exception as e:
            acc = acc or f'*Error: {e}*'
            yield sse_message(Div(render_md(acc)), event='message')  # wrap: render_md is a NotStr
        finally:
            if acc.strip(): d.add_msg(cid, 'assistant', acc)
            yield sse_message(Div(), event='close')
    return EventStream(gen())

def connect(app):
    d.get_db()                        # idempotent: ensure tables exist
    RouteOverrides.skip += Routes.skip   # before auth connects: handlers self-gate via `if not auth`
    app.get('/ai')(ai_home)
    app.post('/ai/c')(ai_new)
    app.get('/ai/c/{cid}')(ai_load)
    app.post('/ai/c/{cid}/msg')(ai_send)
    app.get('/ai/c/{cid}/stream')(ai_stream)
