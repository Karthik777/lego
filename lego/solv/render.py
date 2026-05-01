"""Render nbformat outputs and notebook cells to FastHTML FT components."""
from fasthtml.common import Pre, Div, Img, NotStr, Details, Summary

try:
    from ansi2html import Ansi2HTMLConverter
    _ansi = Ansi2HTMLConverter(inline=True, scheme='ansi2html')
    def ansi_html(s): return _ansi.convert(s, full=False)
except ImportError:  # pragma: no cover
    import re
    _ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
    def ansi_html(s): return _ANSI_RE.sub('', s or '')

try:
    from markdown_it import MarkdownIt
    _md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': True})
    _md.enable(['table', 'strikethrough'])
    def md_html(s): return _md.render(s or '')
except ImportError:  # pragma: no cover
    def md_html(s): return f'<pre>{(s or "")}</pre>'


def _join(text):
    if isinstance(text, list): return ''.join(text)
    return text or ''


def _render_one(o):
    typ = o.get('output_type')
    if typ == 'stream':
        txt = _join(o.get('text', ''))
        cls = 'solv-stream solv-stderr' if o.get('name') == 'stderr' else 'solv-stream solv-stdout'
        return Pre(NotStr(ansi_html(txt)), cls=cls)
    if typ == 'error':
        tb = '\n'.join(o.get('traceback') or [])
        head = f"{o.get('ename', 'Error')}: {o.get('evalue', '')}"
        return Details(Summary(head, cls='solv-err-head'),
                       Pre(NotStr(ansi_html(tb)), cls='solv-traceback'),
                       cls='solv-err', open=True)
    if typ in ('display_data', 'execute_result', 'update_display_data'):
        data = o.get('data') or {}
        # priority: html -> markdown -> image -> json -> text
        if 'text/html' in data:
            html = _join(data['text/html'])
            return Div(NotStr(html), cls='solv-html')
        if 'image/png' in data:
            return Img(src=f'data:image/png;base64,{_join(data["image/png"]).strip()}', cls='solv-img')
        if 'image/jpeg' in data:
            return Img(src=f'data:image/jpeg;base64,{_join(data["image/jpeg"]).strip()}', cls='solv-img')
        if 'image/svg+xml' in data:
            return Div(NotStr(_join(data['image/svg+xml'])), cls='solv-svg')
        if 'text/markdown' in data:
            return Div(NotStr(md_html(_join(data['text/markdown']))), cls='solv-md')
        if 'application/json' in data:
            import json as _json
            try: pretty = _json.dumps(data['application/json'], indent=2)
            except Exception: pretty = str(data['application/json'])
            return Pre(pretty, cls='solv-json')
        if 'text/plain' in data:
            return Pre(NotStr(ansi_html(_join(data['text/plain']))), cls='solv-text')
    return None


def render_outputs(outputs, cell_id=None):
    parts = [r for r in (_render_one(o) for o in (outputs or [])) if r is not None]
    if not parts: parts = [Div('', cls='solv-output-empty')]
    return Div(*parts, id=f'out-{cell_id}' if cell_id else None, cls='solv-output')


def render_markdown(src):
    return Div(NotStr(md_html(src or '')), cls='solv-md')


def render_response(text, tool_calls=None):
    body = [Div(NotStr(md_html(text or '')), cls='solv-md')]
    for tc in tool_calls or []:
        body.append(Details(Summary(f"tool: {tc.get('name', '?')}", cls='solv-tc-head'),
                            Pre(str(tc.get('args', {})), cls='solv-tc-args'),
                            Pre(str(tc.get('result', '')), cls='solv-tc-result'),
                            cls='solv-tool-call'))
    return Div(*body, cls='solv-response')
