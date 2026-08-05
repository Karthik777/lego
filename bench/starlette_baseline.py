from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
big = '<div>x</div>' * 2000
app = Starlette(routes=[Route('/health', lambda r: JSONResponse({'status':'ok'})),
                        Route('/html', lambda r: HTMLResponse(big))])
