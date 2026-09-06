"Running a brick's own wiring snippet here, for a document that has the component but not the package."

import json, math
from dataclasses import is_dataclass, asdict
from .bricks import find

__all__ = ['fill', 'jsonable', 'remote_wire']

def jsonable(v, depth=0):
    if v is None or isinstance(v, (bool, int, str)): return v
    if isinstance(v, float): return v if math.isfinite(v) else repr(v)
    if depth > 6: return repr(v)
    if isinstance(v, dict): return {str(k): jsonable(x, depth + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)): return [jsonable(x, depth + 1) for x in v]
    if is_dataclass(v) and not isinstance(v, type): return jsonable(asdict(v), depth + 1)
    if hasattr(v, 'tolist'): return jsonable(v.tolist(), depth + 1)
    return repr(v)

def fill(name):
    "Run the snippet this brick ships and hand back the values its ports name."
    b = find(name)
    if b is None: return None
    ns = {}
    try:
        if b.wire: exec(compile(b.wire, f'<wire:{name}>', 'exec'), ns)
    except Exception as e: ns['_error'] = f'{type(e).__name__}: {e}'
    out = {p.name: jsonable(ns.get(p.name, p.sample)) for p in b.ports}
    return {**out, **({'_error': ns['_error']} if '_error' in ns else {})}

def remote_wire(name, base):
    "The same wiring, for a document whose interpreter does not have this package installed."
    b = find(name)
    if b is None or not b.wire or not b.ports: return ''
    ports = ', '.join(p.name for p in b.ports)
    return (f"import json, urllib.request\n"
            f"_ports = json.load(urllib.request.urlopen('{base}/bricks/data/{name}'))\n"
            f"{ports} = {', '.join(f'_ports[{p.name!r}]' for p in b.ports)}\n")
