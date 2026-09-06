from fasthtml.common import HTMLResponse, JSONResponse
from starlette.responses import PlainTextResponse
from lego.core import RouteOverrides, base
from .bricks import manifest, find
from .data import fill, remote_wire
from .cfg import Routes
from . import ui

__all__ = ['connect']

def connect(app):
    RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Bricks', Routes.index, None, False)]

    @app.get(Routes.index)
    def bricks_index(req, auth=None): return base(ui.gallery(), title='Bricks')

    @app.get(Routes.manifest)
    def bricks_manifest(): return JSONResponse(manifest())

    @app.get(Routes.frame)
    def bricks_frame(name: str, theme: str = 'light', frame: str = ''):
        return HTMLResponse(ui.frame(name, frame_id=frame, theme=theme))

    @app.get(Routes.wire)
    def bricks_wire(req, name: str):
        "The snippet that fills this brick's ports: as an import, and as a call to this host."
        b = find(name)
        if b is None: return JSONResponse({'ok': False, 'error': f'no brick named {name}'}, status_code=404)
        base = str(req.base_url).rstrip('/')
        return JSONResponse({'ok': True, 'name': b.name, 'wire': b.wire, 'remote': remote_wire(b.name, base),
                             'binds': {p.name: p.name for p in b.ports}, 'height': b.height,
                             'emits': [p.name for p in b.emits]})

    @app.get(Routes.data)
    def bricks_data(name: str):
        "This brick's ports, filled by the package that owns them."
        r = fill(name)
        if r is None: return JSONResponse({'error': f'no brick named {name}'}, status_code=404)
        return JSONResponse(r)

    @app.get(Routes.js)
    def bricks_js(): return PlainTextResponse(ui.asset('bricks.js', 'frame.js'), media_type='text/javascript')

    @app.get(Routes.css)
    def bricks_css(): return PlainTextResponse(ui.asset('bricks.css'), media_type='text/css')
