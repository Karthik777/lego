"""FastHTML + MonsterUI components for the SolveIt-like UI."""
from fasthtml.common import (Div, A, P, Span, Input, Button, Form, Pre, Textarea, NotStr,
                              H3, H4, Ul, Li, Aside, Section, Header, Main, I, Label,
                              Select, Option)
from monsterui.all import (UkIcon, ButtonT, TextT, ContainerT, Container, Card, CardBody,
                            CardHeader, Grid, LabelInput)
from . import data as D
from .cfg import cfg, MsgT, Mode, MODELS, Routes
from .render import render_outputs, render_markdown, render_response, render_annotated_source


# ---------- helpers ----------

def _badge(text, cls=''):
    return Span(text, cls=f'inline-flex items-center text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground {cls}')


def _icon(name): return UkIcon(name, cls='w-4 h-4')


def _flags_for(c):
    m = c.metadata.get('solv', {})
    flags = []
    if m.get('hidden'): flags.append('H')
    if m.get('pinned'): flags.append('P')
    if m.get('exported'): flags.append('E')
    return flags


def _data_attrs(c):
    m = c.metadata.get('solv', {})
    return dict(data_pinned=str(bool(m.get('pinned'))).lower(),
                data_hidden=str(bool(m.get('hidden'))).lower(),
                data_export=str(bool(m.get('exported'))).lower(),
                data_type=m.get('type', 'note'),
                data_cid=m.get('id', ''))


def _toolbar(name, c):
    cid = D.cid_of(c)
    base_url = Routes.msg_action(name, cid, '')[:-1]  # /solv/{name}/msg/{cid}
    btn = lambda key, ic, title: Button(_icon(ic), title=title,
                                          hx_post=f'{base_url}/{key}', hx_target=f'#cell-{cid}', hx_swap='outerHTML',
                                          cls=f'{ButtonT.icon} {ButtonT.xs}')
    return Div(
        btn('pin', 'pin', 'Pin/unpin (P)'),
        btn('hide', 'eye-off', 'Hide/show (H)'),
        btn('export', 'check', 'Toggle export (E)'),
        Button(_icon('trash-2'), title='Delete (X)',
               hx_delete=f'{base_url}', hx_target=f'#cell-{cid}', hx_swap='outerHTML',
               hx_confirm='Delete this cell?',
               cls=f'{ButtonT.icon} {ButtonT.xs} text-destructive'),
        cls='flex gap-1 solv-cell-toolbar')


def _flag_row(c):
    flags = _flags_for(c)
    if not flags: return Div('', cls='solv-flags')
    return Div(*[_badge(f, 'solv-flag-%s' % f.lower()) for f in flags], cls='flex gap-1 solv-flags')


# ---------- cells ----------

def code_cell(name, c):
    cid = D.cid_of(c)
    src = c.source or ''
    annotated = render_annotated_source(src, [], cell_id=cid)
    outputs = render_outputs(getattr(c, 'outputs', []) or [], cell_id=cid)
    runres = Div(annotated, outputs, id=f'runres-{cid}', cls='solv-runres')
    editor = Div(
        Textarea(src, name='content', cls='solv-monaco', data_monaco='python', spellcheck='false',
                  hx_post=Routes.msg(name, cid), hx_trigger='blur changed', hx_swap='none', hx_include='this'),
        cls='solv-editor-wrap')
    run_btn = Button(_icon('play'), 'Run', title='Run (Shift+Enter)',
                     hx_post=Routes.run(name, cid), hx_target=f'#runres-{cid}', hx_swap='outerHTML',
                     hx_include=f'#cell-{cid} textarea[name=content]',
                     cls=f'{ButtonT.primary} {ButtonT.xs}')
    head = Div(_badge('code', 'solv-type-code'), _flag_row(c), Div(cls='flex-1'),
               Span(f"{c.metadata['solv'].get('tokens', 0)}t", cls='text-xs text-muted-foreground'),
               run_btn, _toolbar(name, c),
               cls='flex items-center gap-2 solv-cell-head')
    return Div(head, editor, runres, id=f'cell-{cid}', cls='solv-cell solv-cell-code', **_data_attrs(c))


def note_cell(name, c):
    cid = D.cid_of(c)
    src = c.source or ''
    rendered = render_markdown(src)
    editor = Div(
        Textarea(src, name='content', cls='solv-monaco', data_monaco='markdown', spellcheck='false',
                  hx_post=Routes.msg(name, cid), hx_trigger='blur changed', hx_swap='none', hx_include='this'),
        cls='solv-editor-wrap hidden')
    head = Div(_badge('note', 'solv-type-note'), _flag_row(c), Div(cls='flex-1'),
               Span(f"{c.metadata['solv'].get('tokens', 0)}t", cls='text-xs text-muted-foreground'),
               _toolbar(name, c),
               cls='flex items-center gap-2 solv-cell-head')
    return Div(head, rendered, editor,
               id=f'cell-{cid}', cls='solv-cell solv-cell-note', **_data_attrs(c))


def prompt_cell(name, c):
    cid = D.cid_of(c)
    src = c.source or ''
    m = c.metadata.get('solv', {})
    response = m.get('response') or ''
    tcs = m.get('tool_calls') or []
    resp_div = render_response(response, tcs) if response else Div('', id=f'resp-{cid}', cls='solv-response')
    if response: resp_div = Div(resp_div, id=f'resp-{cid}')

    editor = Div(
        Textarea(src, name='content', cls='solv-monaco', data_monaco='markdown',
                  spellcheck='false', placeholder='Ask…',
                  hx_post=Routes.msg(name, cid), hx_trigger='blur changed', hx_swap='none', hx_include='this'),
        cls='solv-editor-wrap')

    send_btn = Button(_icon('send'), 'Send', title='Send (Shift+Enter)',
                      hx_get=Routes.stream(name, cid),
                      hx_target=f'#resp-{cid}', hx_swap='innerHTML',
                      hx_include=f'#cell-{cid} textarea[name=content]',
                      cls=f'{ButtonT.primary} {ButtonT.xs}')
    stop_btn = Button(_icon('square'), title='Stop (Esc)',
                      hx_post=Routes.stop(name, cid), hx_swap='none',
                      cls=f'{ButtonT.icon} {ButtonT.xs} solv-stop-btn hidden')
    split_btn = Button(_icon('split'), 'W', title='Split response into cells (W)',
                       hx_post=Routes.split(name, cid), hx_target='#cell-list', hx_swap='outerHTML',
                       cls=f'{ButtonT.default} {ButtonT.xs}')
    head = Div(_badge('prompt', 'solv-type-prompt'),
               _badge(m.get('ai_mode') or cfg.llm_default_mode, 'solv-mode'),
               _flag_row(c), Div(cls='flex-1'),
               Span(f"{m.get('tokens', 0)}t", cls='text-xs text-muted-foreground'),
               send_btn, stop_btn, split_btn, _toolbar(name, c),
               cls='flex items-center gap-2 solv-cell-head')
    return Div(head, editor, resp_div,
               id=f'cell-{cid}', cls='solv-cell solv-cell-prompt', **_data_attrs(c))


def cell(name, c):
    typ = D.cell_type(c)
    if typ == MsgT.code: return code_cell(name, c)
    if typ == MsgT.prompt: return prompt_cell(name, c)
    return note_cell(name, c)


# ---------- list / sidebar / view ----------

def cell_list(name, nb):
    return Div(*[cell(name, c) for c in nb.cells],
               id='cell-list', cls='solv-cell-list flex flex-col gap-3 p-2')


def add_cell_bar(name):
    def b(label, typ):
        return Button(label, hx_post=Routes.add_msg(name) + f'?msg_type={typ}',
                      hx_target='#cell-list', hx_swap='beforeend',
                      cls=f'{ButtonT.default} {ButtonT.xs}')
    return Div(b('+ Code', MsgT.code), b('+ Note', MsgT.note), b('+ Prompt', MsgT.prompt),
               cls='flex gap-2 p-2 border-t border-muted')


def sidebar(user_id, dialogs, current=None):
    def item(d):
        active = 'bg-muted' if d['name'] == current else ''
        return Li(A(d['title'], href=Routes.view(d['name']),
                    cls=f'block p-2 hover:bg-muted rounded {active}'),
                  cls='solv-dialog-item')
    new_form = Form(
        Input(name='name', placeholder='New dialog name', cls='uk-input uk-form-small'),
        Button('+', cls=f'{ButtonT.primary} {ButtonT.xs}'),
        hx_post=Routes.index, hx_target='#main-content', hx_swap='outerHTML',
        cls='flex gap-1 p-2')
    search_form = Form(
        Input(name='q', placeholder='Search…', cls='uk-input uk-form-small',
              hx_get=Routes.search, hx_target='#solv-search-results',
              hx_trigger='keyup changed delay:300ms', hx_swap='innerHTML'),
        cls='p-2')
    return Aside(
        Div(H4('Dialogs', cls='p-2 m-0'),
            new_form, search_form,
            Div(id='solv-search-results', cls='p-2 text-xs'),
            Ul(*[item(d) for d in dialogs], cls='solv-dialog-list space-y-1 p-1'),
            cls='flex flex-col gap-1'),
        cls='solv-sidebar w-64 border-r border-muted h-full overflow-y-auto')


def model_mode_picker(name, nb):
    meta = nb.metadata.get('solv', {})
    cur_model = meta.get('model', cfg.llm_default_model)
    cur_mode = meta.get('ai_mode', cfg.llm_default_mode)
    model_opts = [Option(v.name, value=k, selected=(v.litellm_id == cur_model or k == cur_model))
                  for k, v in MODELS.items()]
    mode_opts = [Option(m.title(), value=m, selected=(m == cur_mode)) for m in Mode.all]
    return Div(
        Select(*model_opts, name='model', cls='uk-select uk-form-small w-44',
               hx_put=Routes.meta(name), hx_swap='none', hx_trigger='change'),
        Select(*mode_opts, name='ai_mode', cls='uk-select uk-form-small w-32',
               hx_put=Routes.meta(name), hx_swap='none', hx_trigger='change'),
        cls='flex gap-2')


def symbol_browser(name, vars_):
    rows = [Li(Span(v['name'], cls='font-mono text-xs'),
                Span(v['type'], cls='text-xs text-muted-foreground ml-2'),
                cls='solv-var-row p-1') for v in vars_]
    return Div(
        H4('Symbols', cls='m-0 p-2'),
        Ul(*rows, cls='solv-var-list', id='solv-vars'),
        cls='solv-symbols border-l border-muted w-56 h-full overflow-y-auto p-1',
        hx_get=Routes.vars(name), hx_trigger='every 5s', hx_swap='outerHTML')


def dialog_view(user_id, name, nb, dialogs, vars_=None):
    title = nb.metadata.get('solv', {}).get('title') or name
    head = Div(H3(title, cls='m-0 p-2'),
               Div(cls='flex-1'),
               model_mode_picker(name, nb),
               Button(_icon('refresh-cw'), 'Restart kernel', title='Clear kernel state',
                      hx_post=Routes.kernel_restart(name), hx_swap='none',
                      cls=f'{ButtonT.default} {ButtonT.xs}'),
               cls='flex items-center gap-2 p-2 border-b border-muted solv-dialog-head')
    center = Section(head,
                     Div(cell_list(name, nb), id='cell-list-wrap',
                         cls='flex-1 overflow-y-auto'),
                     add_cell_bar(name),
                     cls='flex flex-col flex-1 min-w-0')
    return Div(sidebar(user_id, dialogs, current=name),
               center,
               symbol_browser(name, vars_ or []),
               id='solv-app', cls='flex h-[calc(100vh-3.5rem)]')


def index_view(user_id, dialogs):
    if not dialogs:
        empty = Div(P('No dialogs yet. Create one to get started.', cls='text-center mt-8'),
                    cls='flex-1 p-4')
    else:
        items = [Li(A(d['title'], href=Routes.view(d['name']), cls='font-medium'),
                     P(d['description'] or '', cls='text-xs text-muted-foreground'),
                     cls='p-2 border-b border-muted') for d in dialogs]
        empty = Div(Ul(*items, cls='solv-dialog-grid'), cls='flex-1 p-4 overflow-y-auto')
    return Div(sidebar(user_id, dialogs), empty,
               id='solv-app', cls='flex h-[calc(100vh-3.5rem)]')


def search_results(rows):
    if not rows: return Span('no matches', cls='text-muted-foreground')
    return Ul(*[Li(A(r['content'][:80], href=Routes.view(r.get('dialog', '')),
                      cls='block hover:bg-muted p-1 rounded'))
                for r in rows], cls='space-y-1')
