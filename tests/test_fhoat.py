"lego on fhoat: the head, the <html> attrs and the reader controls (fhoat's own tests are its notebooks, fhoat/nbs)."
from starlette.testclient import TestClient
from lego import lego

def page(p='/'): return TestClient(lego).get(p)

def test_head_and_files():
    t = page().text
    for nm in ('oat.min.css', 'oat10.css', 'themes.css', 'components.css', 'oat.min.js', 'oat10.js'): assert f'/fhoat/{nm}?v=' in t
    assert '/fhoat/fhoat.css' not in t and 'window.fhoat' in t   # lego keeps its own look
    assert page('/fhoat/oat.min.css').headers['cache-control'].endswith('immutable')

def test_html_attrs():
    t = page().text
    assert 'data-theme="paper"' in t and 'data-radius="md"' in t and 'data-shadow="sm"' in t and 'data-store="lego"' in t

def test_controls():
    t = page().text
    assert 'data-cycle="mode:auto,dark,light"' in t and 'data-cycle="size:,lg,sm"' in t
