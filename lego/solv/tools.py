"""Tools system for solv.

- `& \\`name\\`` and `& \\`[a, b, c]\\`` reference parsing
- Built-in tool sets:
    * dialog meta-tools (add/update/del/find/get/pin/hide messages)
    * execution tools (pyrun, bash with allowlist)
    * file tools (read_file, write_file, grep, list_dir)
    * web tools (url2note)
- Tools resolve `session_id` and `dialog_path` via context vars set in `llm.py` so the
  schemas exposed to the LLM stay clean.
"""
import re, os, subprocess, shlex, html
from pathlib import Path
from typing import Optional
from . import data as D
from .cfg import cfg, MsgT
from .kernel import pool
from .llm import current_session, current_dialog


# ===== reference parser =====
# Matches `& \`name\`` or `& \`[a, b, c]\``
_REF_RE = re.compile(r"&\s*`([^`]+)`")


def parse_refs(text):
    out = []
    for m in _REF_RE.finditer(text or ''):
        body = m.group(1).strip()
        if body.startswith('[') and body.endswith(']'):
            for n in body[1:-1].split(','):
                n = n.strip()
                if n: out.append(n)
        else:
            out.append(body)
    return out


# ===== tool registry =====
class ToolRegistry:
    def __init__(self): self._tools = {}

    def register(self, fn=None, *, name=None):
        if fn is None:
            return lambda f: self.register(f, name=name)
        self._tools[name or fn.__name__] = fn
        return fn

    def get(self, name): return self._tools.get(name)
    def all(self): return dict(self._tools)
    def __contains__(self, k): return k in self._tools


registry = ToolRegistry()
tool = registry.register


# ===== helpers =====
def _ctx_dialog():
    'Load (path, nb) from contextvars set by llm.stream_response.'
    p = current_dialog.get()
    if p is None: raise RuntimeError('tool called outside a dialog context')
    import nbformat
    nb = nbformat.read(str(p), as_version=4)
    return p, nb


def _save(p, nb):
    import nbformat
    nb.metadata.setdefault('solv', {})
    nbformat.write(nb, str(p))


# ===== dialog meta-tools =====
@tool
def add_msg(content: str, msg_type: str = 'note', position: Optional[int] = None) -> str:
    """Add a new message to the current dialog.

    Args:
      content: The message body. For code cells this is Python; for notes/prompts it's markdown.
      msg_type: One of 'code', 'note', 'prompt'.
      position: Insertion index (0-based). If None or beyond end, appends.

    Returns: The new cell's id.
    """
    p, nb = _ctx_dialog()
    if msg_type not in MsgT.all: raise ValueError(f"msg_type must be one of {MsgT.all}")
    cell = D.add_msg(nb, msg_type, content, position)
    _save(p, nb)
    return D.cid_of(cell)


@tool
def update_msg(cell_id: str, content: str) -> bool:
    """Replace the content of a message identified by cell_id."""
    p, nb = _ctx_dialog()
    c = D.update_msg(nb, cell_id, content=content)
    if c is None: return False
    _save(p, nb); return True


@tool
def del_msg(cell_id: str) -> bool:
    """Delete a message by cell_id."""
    p, nb = _ctx_dialog()
    ok = D.del_msg(nb, cell_id)
    if ok: _save(p, nb)
    return ok


@tool
def get_msg(cell_id: str) -> dict:
    """Get a single message by cell_id, including its content and metadata."""
    _, nb = _ctx_dialog()
    _, c = D.find_cell(nb, cell_id)
    if c is None: return {}
    return dict(id=cell_id, source=c.source, type=D.cell_type(c),
                pinned=D.is_pinned(c), hidden=D.is_hidden(c))


@tool
def find_msgs(pattern: Optional[str] = None, msg_type: Optional[str] = None) -> list:
    """Find messages in the current dialog matching a regex pattern and/or message type."""
    _, nb = _ctx_dialog()
    return D.find_msgs(nb, pattern, msg_type)


@tool
def msg_strs_replace(cell_id: str, replacements: list) -> bool:
    """Apply a list of [old, new] string replacements to a cell's content (in order).

    Args:
      cell_id: Target cell id.
      replacements: List of two-element [old, new] pairs.
    """
    p, nb = _ctx_dialog()
    _, c = D.find_cell(nb, cell_id)
    if c is None: return False
    src = c.source or ''
    for pair in replacements:
        if not (isinstance(pair, (list, tuple)) and len(pair) == 2): continue
        src = src.replace(pair[0], pair[1])
    D.update_msg(nb, cell_id, content=src)
    _save(p, nb); return True


@tool
def msg_insert_line(cell_id: str, line_num: int, text: str) -> bool:
    """Insert `text` at line `line_num` (1-indexed) of the message identified by cell_id."""
    p, nb = _ctx_dialog()
    _, c = D.find_cell(nb, cell_id)
    if c is None: return False
    lines = (c.source or '').splitlines()
    idx = max(0, min(line_num - 1, len(lines)))
    lines.insert(idx, text)
    D.update_msg(nb, cell_id, content='\n'.join(lines))
    _save(p, nb); return True


@tool
def pin_msg(cell_id: str, pinned: bool = True) -> bool:
    """Pin or unpin a message; pinned messages are never truncated from context."""
    p, nb = _ctx_dialog()
    if D.update_msg(nb, cell_id, pinned=bool(pinned)) is None: return False
    _save(p, nb); return True


@tool
def hide_msg(cell_id: str, hidden: bool = True) -> bool:
    """Hide or unhide a message; hidden messages are excluded from AI context."""
    p, nb = _ctx_dialog()
    if D.update_msg(nb, cell_id, hidden=bool(hidden)) is None: return False
    _save(p, nb); return True


# ===== execution tools =====
@tool
def pyrun(code: str) -> str:
    """Execute Python code in this dialog's persistent kernel and return the textual output."""
    sid = current_session.get()
    if sid is None: raise RuntimeError('pyrun called outside a session context')
    outs = pool.run(sid, code)
    bits = []
    for o in outs:
        t = o.get('output_type')
        if t == 'stream': bits.append(_join(o.get('text', '')))
        elif t == 'error': bits.append(f"{o.get('ename','')}: {o.get('evalue','')}\n" + '\n'.join(o.get('traceback') or []))
        elif t in ('display_data', 'execute_result'):
            data = o.get('data') or {}
            if 'text/plain' in data: bits.append(_join(data['text/plain']))
    return '\n'.join(bits)


@tool
def bash(cmd: str, timeout: int = 30) -> str:
    """Run a single allowlisted shell command and return combined stdout/stderr.

    Only commands whose first token is in `cfg.solv_bash_allowlist` are permitted.
    """
    parts = shlex.split(cmd or '')
    if not parts: return ''
    head = os.path.basename(parts[0])
    if head not in cfg.solv_bash_allowlist:
        return f"refused: '{head}' not in allowlist"
    try:
        r = subprocess.run(parts, capture_output=True, text=True, timeout=timeout, check=False)
        return (r.stdout or '') + (('\n' + r.stderr) if r.stderr else '')
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"
    except Exception as e:
        return f"error: {e}"


# ===== file tools =====
def _safe_path(path):
    p = Path(path).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if cwd not in p.parents and p != cwd: raise ValueError(f'path outside cwd: {path}')
    return p


@tool
def read_file(path: str, start: int = 0, end: Optional[int] = None) -> str:
    """Read a text file, optionally limited to a [start, end) line range."""
    p = _safe_path(path)
    text = p.read_text(errors='replace')
    if start or end is not None:
        lines = text.splitlines()
        text = '\n'.join(lines[start:end])
    return text


@tool
def write_file(path: str, content: str) -> bool:
    """Write `content` to `path`, creating parent directories as needed."""
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return True


@tool
def grep(pattern: str, path: str = '.') -> list:
    """Recursively search `path` for `pattern` (regex). Returns list of [file, lineno, line]."""
    rx = re.compile(pattern)
    base = _safe_path(path)
    out = []
    files = [base] if base.is_file() else [f for f in base.rglob('*') if f.is_file()]
    for f in files:
        try: text = f.read_text(errors='replace')
        except Exception: continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                out.append([str(f), i, line])
                if len(out) >= 500: return out
    return out


@tool
def list_dir(path: str = '.') -> list:
    """List entries in a directory."""
    p = _safe_path(path)
    if not p.is_dir(): return []
    return [str(c.relative_to(p)) for c in sorted(p.iterdir())]


# ===== web tools =====
@tool
def url2note(url: str) -> str:
    """Fetch a public http(s) URL and add its content (HTML stripped to text) as a new note message.

    Returns the new cell id. Refuses non-http(s) URLs and any host that resolves to a
    loopback / private / link-local / multicast address (basic SSRF protection).
    """
    import urllib.request, urllib.parse, ipaddress, socket
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'unsupported scheme: {parsed.scheme!r} (only http/https allowed)')
    host = parsed.hostname
    if not host: raise ValueError('url has no host')
    # Resolve and reject private / loopback / link-local / multicast / reserved.
    try: addrs = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except socket.gaierror as e: raise ValueError(f'could not resolve host: {e}')
    for a in addrs:
        try: ip = ipaddress.ip_address(a)
        except ValueError: continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ValueError(f'refused: {host} resolves to non-public address {a}')
    req = urllib.request.Request(url, headers={'User-Agent': 'solv/0.1'})
    # Only http(s) is allowed; the scheme check + IP check above mitigate SSRF/file://.
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - scheme + host validated
        ctype = resp.headers.get('Content-Type', '')
        body = resp.read(2 * 1024 * 1024).decode('utf-8', 'replace')
    text = body if 'text/html' not in ctype.lower() else _strip_html(body)
    note = f"# {url}\n\n{text}"
    p, nb = _ctx_dialog()
    cell = D.add_msg(nb, MsgT.note, note)
    _save(p, nb)
    return D.cid_of(cell)


_TAG_RE = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)
_HTML_RE = re.compile(r'<[^>]+>')
def _strip_html(s):
    s = _TAG_RE.sub('', s)
    s = _HTML_RE.sub(' ', s)
    return re.sub(r'\s+\n', '\n', html.unescape(s)).strip()


def _join(s): return ''.join(s) if isinstance(s, list) else (s or '')


# ===== public bundles =====
def tool_info():
    'Dialog meta-tools. Mirrors dialoghelper.tool_info().'
    return [add_msg, update_msg, del_msg, get_msg, find_msgs, msg_strs_replace,
            msg_insert_line, pin_msg, hide_msg]


def fc_tool_info():
    'File / shell tools. Mirrors dialoghelper.fc_tool_info().'
    return [read_file, write_file, grep, list_dir, bash]


def exec_tool_info():
    'Kernel execution tools.'
    return [pyrun]


def web_tool_info():
    return [url2note]


def all_tools():
    return tool_info() + fc_tool_info() + exec_tool_info() + web_tool_info()
