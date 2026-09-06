from dataclasses import dataclass

@dataclass(frozen=True)
class Routes:
    index    = '/bricks'
    manifest = '/bricks/manifest.json'
    frame    = '/bricks/f/{name}'
    wire     = '/bricks/wire/{name}'
    data     = '/bricks/data/{name}'
    js       = '/bricks/js'
    css      = '/bricks/css'
    skip     = ['/bricks', r'/bricks/.*']
