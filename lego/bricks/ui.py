"The gallery a person browses, and the bare document a brick is embedded as."

import json
from pathlib import Path
from fasthtml.common import *
from .bricks import BRICKS, GROUPS, find
from .cfg import Routes

__all__ = ['gallery', 'frame', 'asset', 'bare']

HERE = Path(__file__).parent

def asset(*names):
    "This block's own files, concatenated: fasthtml's static route claims any path with an extension."
    return '\n'.join((HERE/n).read_text() for n in names if (HERE/n).exists())

def frame(name, props=None, frame_id='', theme='light'):
    "A brick as a whole HTML document, so a canvas can put it in an iframe and talk to it."
    b = find(name)
    if b is None: return f'<!doctype html><body>no brick named {name}</body>'
    props = props if props is not None else b.sample()
    head = Head(Meta(charset='utf-8'), Meta(name='viewport', content='width=device-width,initial-scale=1'),
                Title(b.title), Link(rel='stylesheet', href=Routes.css))
    body = Body(Div(id='brick', data_name=name, data_frame=frame_id or name,
                    data_props=json.dumps(props), data_manifest=json.dumps(b.dict())),
                Script(src=Routes.js))
    return '<!doctype html>' + to_xml(Html(head, body, data_theme=theme))

def bare(content, title='Bricks'):
    "The gallery with no host shell around it, for a mount that has none of its own."
    head = Head(Meta(charset='utf-8'), Meta(name='viewport', content='width=device-width,initial-scale=1'),
                Title(title), Link(rel='stylesheet', href=Routes.css))
    return '<!doctype html>' + to_xml(Html(head, Body(content)))

def _card(b):
    ports = ', '.join(p.name for p in b.ports) or '—'
    emits = ', '.join(p.name for p in b.emits) or '—'
    return Div(cls='bg-card border rounded-lg overflow-hidden')(
        Div(cls='px-3 py-2 border-b flex justify-between items-baseline')(
            Div(Strong(b.title), Div(b.doc, cls='text-xs opacity-70')),
            Code(b.src, cls='text-xs opacity-60')),
        Iframe(src=f'/bricks/f/{b.name}', style=f'width:100%;height:{b.height}px;border:0', loading='lazy'),
        Div(cls='px-3 py-2 border-t text-xs opacity-75 flex gap-4')(
            Span(f'in: {ports}'), Span(f'out: {emits}')))

def gallery():
    "Every brick, drawn with its sample data, grouped by the block that owns it."
    secs = []
    for g, doc in GROUPS.items():
        bs = [b for b in BRICKS.values() if b.group == g]
        if not bs: continue
        secs.append(Section(cls='mb-8')(
            H2(g, cls='text-lg font-bold'), P(doc, cls='text-sm opacity-70 mb-3'),
            Div(cls='grid gap-4 md:grid-cols-2')(*[_card(b) for b in bs])))
    return Div(cls='max-w-5xl mx-auto p-4')(
        H1('Bricks', cls='text-2xl font-bold'),
        P('Every embeddable component lego offers a document. Each declares the ports it draws from, '
          'what it hands back when you click it, and the code that fills it from the package that owns it.',
          cls='text-sm opacity-70 mb-6'),
        *secs)
