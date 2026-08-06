from fasthtml.common import HTMLResponse
from lego.core import RouteOverrides
from .cfg import Routes
from .ui import page

__all__ = ['connect']

def hora_page(req):
    # Returned as a response rather than an FT tree: fasthtml would otherwise wrap whatever
    # comes back in the app-wide head, and this block ships its own document.
    return HTMLResponse(page())

def connect(app):
    RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Hora', Routes.index, None, False)]
    app.get(Routes.index)(hora_page)
