'''Tests for the bricks block.

A brick is a declaration in Python and a drawing in JavaScript, and nothing checks that the two
agree at import time. These do: every registered brick has a renderer, every port a sample, and
every wiring snippet either fills its ports or is honest about why it could not.'''

import json, re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import lego.app as legoapp
from lego.bricks.bricks import BRICKS, GROUPS, find, manifest
from lego.bricks.data import fill, remote_wire

HERE = Path(__file__).parent.parent/'lego'/'bricks'

@pytest.fixture(scope='module')
def client(): return TestClient(legoapp.lego)

def test_every_brick_has_a_renderer_of_the_same_name():
    js = (HERE/'bricks.js').read_text()
    drawn = set(re.findall(r"B\['([\w.]+)'\]", js))
    assert set(BRICKS) == drawn

def test_every_brick_names_a_group_that_exists():
    assert {b.group for b in BRICKS.values()} <= set(GROUPS)

def test_every_port_carries_a_sample_so_a_brick_draws_unwired():
    missing = [(b.name, p.name) for b in BRICKS.values() for p in b.ports if p.required and p.sample is None]
    assert missing == []

def test_the_manifest_names_each_brick_by_its_import_path():
    m = manifest()
    assert {b['src'] for b in m['bricks']} == {f'lego.bricks:{n}' for n in BRICKS}

def test_a_wiring_snippet_fills_the_ports_it_declares():
    for name, b in BRICKS.items():
        if not b.wire: continue
        got = fill(name)
        assert '_error' not in got, f'{name}: {got.get("_error")}'
        assert set(got) == {p.name for p in b.ports}

def test_the_remote_wiring_reads_the_same_ports_back():
    code = remote_wire('panchanga.day', 'http://host')
    assert '/bricks/data/panchanga.day' in code
    assert code.strip().endswith("day = _ports['day']")

def test_a_frame_is_a_whole_document_with_its_props_inlined(client):
    r = client.get('/bricks/f/viz.tiles')
    assert r.status_code == 200
    assert '<!doctype html>' in r.text and 'data-name="viz.tiles"' in r.text
    props = json.loads(re.search(r"data-props='([^']*)'", r.text)[1])
    assert [t['label'] for t in props['tiles']] == ['Pipeline', 'Win rate', 'Cycle']

def test_the_wire_route_offers_both_an_import_and_a_call(client):
    r = client.get('/bricks/wire/thrifty.costs').json()
    assert r['ok'] and 'import' in r['wire'] and 'urlopen' in r['remote']
    assert r['binds'] == {'rows': 'rows'}

def test_asking_for_a_brick_that_does_not_exist_says_so(client):
    assert client.get('/bricks/wire/nope.nope').status_code == 404
    assert client.get('/bricks/data/nope.nope').status_code == 404

def test_the_client_bundle_serves_from_a_path_with_no_extension(client):
    js = client.get('/bricks/js')
    assert js.status_code == 200 and 'LEGO_BRICKS' in js.text and 'brick:ready' in js.text
    assert client.get('/bricks/css').status_code == 200
