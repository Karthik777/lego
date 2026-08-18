# tests/test_thrifty.py
import json, re
from starlette.testclient import TestClient
import lego.app as legoapp
from lego.thrifty.data import get_all_platforms, get_use_case_templates, page_data
from lego.thrifty.ui import page

def test_thrifty_page_is_a_whole_document():
    'The block ships its own head, so it must not be wrapped in the app-wide one.'
    h = page()
    assert h.startswith('<!doctype html>')
    assert 'thrifty.css' in h and 'lodash.min.js' in h
    assert 'oat.min.css' not in h   # the core theme would restyle every card and input

def test_catalogue_reaches_the_browser_as_json():
    'thrifty.js reads the catalogue out of a script tag rather than being generated with it.'
    d = json.loads(re.search(r'id="thrifty-data">(.*?)</script>', page(), re.S).group(1))
    assert set(d) == {'platforms', 'useCases'}
    assert set(d['platforms']) == set(get_all_platforms())
    assert len(d['useCases']) == len(get_use_case_templates())
    p = d['platforms']['agent_frameworks']['openai_agents']
    assert p['scale_fit'] == ['startup', 'growth', 'scale', 'enterprise']   # enums flattened
    assert '<' not in page_data()   # would end the script tag early

def test_every_handler_the_markup_calls_is_exported():
    h, js = page(), (__import__('pathlib').Path(legoapp.__file__).parent / 'thrifty/thrifty.js').read_text()
    called = set(re.findall(r'on(?:click|change|input)="(\w+)\(', h))
    assert called and called <= set(re.findall(r'window\.(\w+) =', js))

def test_thrifty_route_is_public():
    'It is the root of its own hostname, so auth must skip it.'
    r = TestClient(legoapp.lego).get('/thrifty')
    assert r.status_code == 200 and 'Cost Calculator' in r.text

def test_deploy_serves_thrifty_on_its_own_host():
    import deploy
    assert deploy.SITES['thrifty.sankalpa.sh'] == '/thrifty'
    assert deploy.zone_of('thrifty.sankalpa.sh') == 'sankalpa.sh'
    caddy = deploy.caddy_site('thrifty.sankalpa.sh', 'rewrite / /thrifty')
    assert 'http://thrifty.sankalpa.sh {' in caddy and 'rewrite / /thrifty' in caddy
