"Lego's seam onto the brick package: its own page shell, and its public routes."

from lego.core import RouteOverrides, base
from .cfg import Routes
from .serve import connect as serve

__all__ = ['connect']

def connect(app):
    RouteOverrides.skip += Routes.skip
    RouteOverrides.nav = RouteOverrides.nav + [('Bricks', Routes.index, None, False)]
    serve(app, page=lambda content, **kw: base(content, **kw))
