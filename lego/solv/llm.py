"""LLM streaming + context building via lisette (LiteLLM under the hood)."""
import asyncio, contextvars
from . import data as D
from .cfg import cfg, Mode, MsgT, load_prompt, model_for

try:
    from lisette import AsyncChat, Chat
except ImportError:  # pragma: no cover
    AsyncChat = Chat = None


# Per-stream context for tools to know which dialog they're acting on.
current_session = contextvars.ContextVar('current_session', default=None)
current_dialog  = contextvars.ContextVar('current_dialog', default=None)


def estimate_tokens(text):
    'Rough heuristic when we have no usage info (≈ 4 chars per token).'
    return max(1, len(text or '') // 4)


def _format_cell(c, output_text=''):
    'Render a cell as XML for LLM context.'
    m = c.metadata.get('solv', {})
    typ = m.get('type', MsgT.note)
    src = c.source or ''
    if typ == MsgT.code:
        body = f'<code>\n{src}\n</code>'
        if output_text: body += f'\n<output>\n{output_text}\n</output>'
        return body
    if typ == MsgT.note: return f'<note>\n{src}\n</note>'
    if typ == MsgT.prompt:
        body = f'<prompt>\n{src}\n</prompt>'
        resp = m.get('response') or ''
        if resp: body += f'\n<response>\n{resp}\n</response>'
        return body
    return f'<message>\n{src}\n</message>'


def _outputs_to_text(outputs):
    bits = []
    for o in outputs or []:
        t = o.get('output_type')
        if t == 'stream': bits.append(_join(o.get('text', '')))
        elif t == 'error': bits.append(f"{o.get('ename','')}: {o.get('evalue','')}")
        elif t in ('display_data', 'execute_result'):
            data = o.get('data') or {}
            if 'text/plain' in data: bits.append(_join(data['text/plain']))
    return '\n'.join(b for b in bits if b)


def _join(s): return ''.join(s) if isinstance(s, list) else (s or '')


def build_context(nb, until_cell_id, max_tokens=None):
    """Produce an ordered list of XML-formatted strings for messages preceding the prompt cell.

    Rules:
      - skip cells where solv.hidden == True
      - always include cells where solv.pinned == True (even if old)
      - truncate from the top (oldest non-pinned) when over budget
    """
    max_tokens = max_tokens or cfg.llm_max_context_tokens
    entries = []  # (idx, pinned, formatted, est_tokens)
    for i, c in enumerate(nb.cells):
        if D.cid_of(c) == until_cell_id: break
        if D.is_hidden(c): continue
        out_text = _outputs_to_text(getattr(c, 'outputs', None)) if c.cell_type == 'code' else ''
        s = _format_cell(c, out_text)
        entries.append((i, D.is_pinned(c), s, estimate_tokens(s)))

    total = sum(e[3] for e in entries)
    if total <= max_tokens: return [e[2] for e in entries]

    # truncate non-pinned, oldest first
    keep = list(entries)
    for i, _e in enumerate(entries):
        if total <= max_tokens: break
        if _e[1]: continue  # pinned: never drop
        keep[i] = None
        total -= _e[3]
    return [e[2] for e in keep if e is not None]


def collect_tool_refs(nb, until_cell_id, registry):
    """Scan messages above the prompt for `& \\`name\\`` references; resolve via registry."""
    from .tools import parse_refs
    names = []
    for c in nb.cells:
        if D.cid_of(c) == until_cell_id: break
        if D.is_hidden(c): continue
        names.extend(parse_refs(c.source or ''))
    seen, out = set(), []
    for n in names:
        if n in seen: continue
        seen.add(n)
        f = registry.get(n)
        if f is not None: out.append(f)
    return out


def build_chat(model=None, mode=None, tools=None, async_=True):
    if AsyncChat is None: raise RuntimeError('lisette is not installed')
    m = model_for(model or cfg.llm_default_model)
    sp = load_prompt(mode or cfg.llm_default_mode)
    Cls = AsyncChat if async_ else Chat
    return Cls(m.litellm_id, sp=sp, tools=list(tools or []))


async def stream_response(nb, prompt_cell, model=None, mode=None, tools=None):
    """Async-generate text chunks for a prompt cell. Persists final text and usage on the cell.

    Yields strings (deltas). The caller is responsible for encoding them as SSE events
    and persisting the dialog after the stream completes.
    """
    chat = build_chat(model=model, mode=mode, tools=tools)
    ctx = build_context(nb, D.cid_of(prompt_cell))
    user_msg = (prompt_cell.source or '').strip()
    msgs = ctx + [user_msg] if ctx else [user_msg]
    full = []
    try:
        async for chunk in chat(msgs, stream=True):
            # lisette yields strings or message-shaped deltas; coerce to str
            if chunk is None: continue
            if isinstance(chunk, str): text = chunk
            else: text = getattr(chunk, 'content', None) or str(chunk)
            if not text: continue
            full.append(text)
            yield text
    except Exception as e:  # pragma: no cover - surfaces back to user as error chunk
        yield f"\n\n**[stream error]** {e}"
    # Persist
    final = ''.join(full)
    m = prompt_cell.metadata.setdefault('solv', {})
    m['response'] = final
    m['model'] = model_for(model or cfg.llm_default_model).litellm_id
    m['ai_mode'] = mode or cfg.llm_default_mode
    # Token bookkeeping (best-effort: prefer lisette usage if exposed on chat)
    usage = getattr(chat, 'usage', None) or getattr(chat, 'last_usage', None)
    if usage is not None:
        try: m['tokens'] = int(getattr(usage, 'total_tokens', 0)) or estimate_tokens(final)
        except Exception: m['tokens'] = estimate_tokens(final)
    else:
        m['tokens'] = estimate_tokens(final)


async def complete(prefix, model=None):
    'Single-shot ghost-text completion using the smaller completion model.'
    if AsyncChat is None: return ''
    m = model_for(model or cfg.llm_completion_model)
    chat = AsyncChat(m.litellm_id, sp='Complete the user prompt with the most likely continuation. Reply with the completion only.')
    try: r = await chat(prefix)
    except Exception: return ''
    if isinstance(r, str): return r
    return getattr(r, 'content', None) or str(r)
