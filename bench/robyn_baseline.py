from robyn import Robyn
app = Robyn(__file__)
big = '<div>x</div>' * 2000  # ~23KB, same order as lego's home page

@app.get('/health')
async def health(request): return {'status': 'ok'}

@app.get('/html')
async def html(request): return big

# a stand-in for the work lego's handlers actually do: build an FT tree and serialise it.
try:
    from fastcore.xml import Div, P, to_xml
    tree = Div(*[P(f'row {i}', cls='x') for i in range(300)])
    @app.get('/render')
    async def render(request): return to_xml(tree)
except ImportError: pass

if __name__ == '__main__': app.start(host='127.0.0.1', port=5002)
