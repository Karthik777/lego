"fhoat: fast_app(oat=...) headers, static files, themes and component contracts."
import json
from starlette.testclient import TestClient
from fhoat import *
from fhoat.core import FILES, oatcss

def client(**kw):
    app, rt = fast_app(**kw)
    @rt('/')
    def index(): return P('hi')
    @rt('/t')
    def post(): return toast_hdr('Saved', 'Done', 'success')
    return TestClient(app)

def test_oat_replaces_pico():
    t = client().get('/').text
    assert '/fhoat/oat.min.css?v=' in t and '/fhoat/fhoat.css?v=' in t and '/fhoat/oat.min.js?v=' in t
    assert 'pico' not in t and 'window.fhoat' in t and '=>' in t   # inline script not escaped

def test_oat_false_is_plain_fasthtml():
    t = client(oat=False).get('/').text
    assert 'pico' in t and 'fhoat' not in t

def test_static_files_served_and_cached():
    c = client()
    for nm in FILES:
        r = c.get(f'/fhoat/{nm}')
        assert r.status_code == 200 and 'immutable' in r.headers['cache-control']
    assert c.get('/fhoat/core.py').status_code == 404

def test_cdn_mode_needs_no_route():
    c = client(cdn=True)
    t = c.get('/').text
    assert oatcss in t and '/fhoat/fhoat.css' not in t
    assert c.get('/fhoat/oat.min.css').status_code == 404

def test_theme_preset_and_mode_on_html():
    t = client(oat='paper', mode='dark').get('/').text
    assert 'data-theme="paper"' in t and 'data-mode="dark"' in t

def test_custom_theme_css():
    th = Theme(primary=('#8a1f11', '#dcae6d'), radius='lg', font='serif', tokens=dict(container_max='60rem'), scale=1.1)
    css = th.css()
    assert '--primary:light-dark(#8a1f11, #dcae6d)' in css and '--primary-foreground:light-dark(#fafafa, #0a0a0a)' in css
    assert '--font-sans:var(--font-serif)' in css and '--container-max:60rem' in css and 'radius' not in css
    assert 'font-size:110%' in css and css in client(oat=th).get('/').text
    assert Theme().css() == '' and client(oat=dict(primary='#2563eb')).get('/').text.count('--primary:#2563eb') == 1

def test_settings_on_html():
    t = client(oat=Theme(name='ink', radius='lg', shadow='none', size='lg'), tips=False, store='__APP__').get('/').text
    for a in ('data-theme="ink"', 'data-radius="lg"', 'data-shadow="none"', 'data-size="lg"', 'data-tips="off"', 'data-store="__APP__"'): assert a in t
    try: Theme(radius='huge'); assert False
    except ValueError: pass

def test_hdrs_opt_out():
    h = to_xml(oat_hdrs(look=False, script=False, prefix='/css/fhoat'))
    assert '/css/fhoat/oat.min.css?v=' in h and '/css/fhoat/oat.min.js?v=' in h and 'fhoat.css' not in h and 'window.fhoat' not in h

def test_toast_header():
    r = client().post('/t')
    assert json.loads(r.headers['hx-trigger'])['toast'] == dict(msg='Saved', title='Done', variant='success')

def test_components():
    x = lambda o: to_xml(o)
    assert 'class="card"' in x(Card('b', header='h', footer='f')) and '<header>h</header>' in x(Card('b', header='h'))
    assert 'class="group"' in x(Group(Input())) and 'role="search"' in x(Search())
    assert '--min:10rem' in x(Grid('a', 'b', min='10rem')) and x(Grid('a')).count('<div>') == 1
    assert 'class="col-8 offset-2"' in x(Col(span=8, offset=2))
    d = x(DialogX('b', header='h', footer='f', id='d'))
    assert 'closedby="any"' in d and 'id="d"' in d and 'commandfor="d"' in x(DialogOpen('o', id='d'))
    assert 'data-variant="danger"' in x(Btn('x', variant='danger')) and 'class="outline small"' in x(Btn('x', look='outline', size='small'))
    assert 'class="button ghost"' in x(ABtn('a', look='ghost'))
    assert 'data-variant="success"' in x(Badge('ok', variant='success')) and 'role="alert"' in x(Alert('a', variant='warning'))
    assert 'data-field' in x(Field('L', Input(), hint='h')) and 'role="switch"' in x(Switch('s'))
    t = x(Tabs(('A', 'a'), ('B', 'b')))
    assert '<ot-tabs' in t and t.count('role="tab"') == 2 and t.count('role="tabpanel"') == 2
    m = x(Dropdown('Menu', A('a', href='#'), 'b', id='m'))
    assert '<ot-dropdown' in m and 'popovertarget="m"' in m and m.count('role="menuitem"') == 2
    assert 'data-variant="avatar"' in x(Avatar(initials='KR')) and x(Skeleton(2)).count('skeleton line') == 2
    n = x(Navbar('B', ('Docs', '/d')))
    assert 'class="ot-nav"' in n and 'href="/d"' in n and "fhoat.cycle('mode'" in n
    p = x(ThemePicker())
    assert p.count('fhoat.theme(') == len(THEMES) and 'data-set="radius=lg"' in p and 'data-set="shadow=none"' in p
    assert 'data-set' not in x(ThemePicker(radii=None, shadows=None))
    assert "fhoat.cycle('size'," in x(FontToggle())
    assert 'fhoat.toast(' in x(Toast('hi'))
