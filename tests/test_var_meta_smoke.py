"""Smoke tests for inline-variable metadata (codenb spec §16).

Covers:
  * `assigned_lines` AST extraction (incl. tuple unpacking, walrus,
    comprehension scoping, for/with targets).
  * `var_meta` duck-typed inspection for ints, strings, lists, classes,
    plus optional numpy/pandas paths when those packages are importable.
  * `KernelPool.run_meta` for the live `changed=True` flow that requires
    a real CaptureShell.
"""
from __future__ import annotations

import sys
import pytest

from lego.solv.varmeta import (VarMeta, assigned_lines, var_meta, badge_text,
                                BADGE_MAX)


# ---------- assigned_lines ----------

def test_simple_assign():
    assert assigned_lines("x = 42") == {'x': 1}


def test_multiline_assign_pandas_like():
    src = "import pandas as pd\ndf = pd.DataFrame({'a': range(5), 'b': range(5)})"
    lines = assigned_lines(src)
    assert lines['pd'] == 1
    assert lines['df'] == 2


def test_tuple_unpacking_yields_each_target():
    assert assigned_lines("x, y = 1, 2") == {'x': 1, 'y': 1}


def test_nested_unpacking():
    lines = assigned_lines("x, (y, z) = 1, (2, 3)")
    assert lines == {'x': 1, 'y': 1, 'z': 1}


def test_starred_unpacking():
    lines = assigned_lines("a, *rest = [1, 2, 3]")
    assert lines == {'a': 1, 'rest': 1}


def test_aug_assign_recorded():
    lines = assigned_lines("x = 1\nx += 10")
    # Last assignment wins.
    assert lines['x'] == 2


def test_ann_assign_with_value():
    assert assigned_lines("x: int = 5") == {'x': 1}


def test_ann_assign_without_value_is_skipped():
    assert assigned_lines("x: int") == {}


def test_walrus():
    lines = assigned_lines("if (n := 10) > 0: pass")
    assert lines.get('n') == 1


def test_for_target():
    assert assigned_lines("for i in range(3): pass") == {'i': 1}


def test_with_target():
    src = "with open('x') as f: pass"
    assert assigned_lines(src) == {'f': 1}


def test_listcomp_targets_excluded():
    # `n` is comprehension-scoped in py3 and must NOT leak.
    lines = assigned_lines("items = [n*n for n in range(4)]")
    assert lines == {'items': 1}


def test_dictcomp_excluded():
    lines = assigned_lines("d = {k: v for k, v in pairs}")
    assert lines == {'d': 1}


def test_genexp_excluded():
    lines = assigned_lines("g = (x for x in range(3))")
    assert lines == {'g': 1}


def test_class_and_function_def_recorded():
    src = "class Foo:\n    def __init__(self): self.x = 1\nfoo = Foo()"
    lines = assigned_lines(src)
    assert lines['Foo'] == 1
    assert lines['foo'] == 3


def test_import_aliases():
    src = "import numpy as np\nfrom os.path import join as j"
    lines = assigned_lines(src)
    assert lines == {'np': 1, 'j': 2}


def test_syntax_error_returns_empty():
    assert assigned_lines("x =") == {}


# ---------- var_meta ----------

def test_int_meta():
    m = var_meta('x', 42, line=1, changed=False)
    assert m.type == 'int' and m.shape is None and m.length is None
    assert '42' in m.repr_short


def test_string_short_meta():
    m = var_meta('s', 'hi', line=1, changed=False)
    assert m.type == 'str' and m.length is None  # short string -> no len badge


def test_string_long_meta():
    long = 'x' * 200
    m = var_meta('s', long, line=1, changed=False)
    assert m.length == 200


def test_list_meta_uses_length():
    m = var_meta('xs', [1, 2, 3], line=1, changed=False)
    assert m.type == 'list' and m.length == 3 and m.shape is None


def test_custom_class_no_shape_no_len():
    class Foo: pass
    m = var_meta('foo', Foo(), line=1, changed=False)
    assert m.type == 'Foo' and m.shape is None and m.length is None


def test_repr_failure_falls_back():
    class Boom:
        def __repr__(self): raise RuntimeError('nope')
    m = var_meta('b', Boom(), line=1, changed=False)
    assert m.repr_short == '<Boom>'


# numpy / pandas paths (optional)

def test_numpy_shape_dtype():
    np = pytest.importorskip('numpy')
    arr = np.zeros((3, 3), dtype=np.float64)
    m = var_meta('arr', arr, line=2, changed=False)
    assert m.type == 'ndarray'
    assert m.shape == '(3, 3)'
    assert m.dtype == 'float64'


def test_pandas_dataframe_shape():
    pd = pytest.importorskip('pandas')
    df = pd.DataFrame({'a': range(5), 'b': range(5)})
    m = var_meta('df', df, line=2, changed=False)
    assert m.type == 'DataFrame'
    assert m.shape == '(5, 2)'


# ---------- badge_text ----------

def test_badge_int():
    assert badge_text(var_meta('x', 42, 1, False)) == 'int 42'


def test_badge_list_len():
    assert badge_text(var_meta('xs', list(range(12)), 1, False)) == 'list len=12'


def test_badge_caps_length():
    big = 'x' * 500
    text = badge_text(var_meta('s', big, 1, False))
    assert len(text) <= BADGE_MAX


def test_badge_numpy_short_dtype():
    np = pytest.importorskip('numpy')
    arr = np.zeros((3, 3), dtype=np.float64)
    text = badge_text(var_meta('arr', arr, 2, False))
    assert text == 'ndarray (3, 3) f64'


# ---------- KernelPool.run_meta (live shell required) ----------

@pytest.fixture
def pool():
    pytest.importorskip('execnb')
    from lego.solv.kernel import KernelPool
    p = KernelPool()
    yield p
    # cleanup
    for sid in list(p._shells):
        p.close(sid)


def test_run_meta_basic(pool):
    outs, metas = pool.run_meta('s1', "x = 42")
    by_name = {m.name: m for m in metas}
    assert 'x' in by_name
    assert by_name['x'].line == 1
    assert by_name['x'].changed is False
    assert by_name['x'].type == 'int'


def test_run_meta_excludes_baseline(pool):
    # First run primes the shell; only user assignment should appear.
    outs, metas = pool.run_meta('s2', "y = 7")
    names = {m.name for m in metas}
    assert 'In' not in names and 'Out' not in names and 'get_ipython' not in names
    assert 'y' in names


def test_run_meta_changed_flag(pool):
    pool.run_meta('s3', "x = 1")
    _, metas = pool.run_meta('s3', "x = 'hello'")  # rebind to a different obj
    by_name = {m.name: m for m in metas}
    assert by_name['x'].changed is True
    assert by_name['x'].type == 'str'


def test_run_meta_unpacking_two_vars(pool):
    _, metas = pool.run_meta('s4', "a, b = 10, 20")
    by_name = {m.name: m for m in metas}
    assert {'a', 'b'} <= set(by_name)
    assert by_name['a'].line == 1 and by_name['b'].line == 1


def test_run_meta_for_loop_var(pool):
    _, metas = pool.run_meta('s5', "for i in range(3): pass")
    by_name = {m.name: m for m in metas}
    assert 'i' in by_name and by_name['i'].line == 1


def test_run_meta_listcomp_target_not_emitted(pool):
    _, metas = pool.run_meta('s6', "items = [n*n for n in range(4)]")
    names = {m.name for m in metas}
    assert 'items' in names
    assert 'n' not in names  # comprehension-scoped


def test_run_meta_class_then_instance(pool):
    src = "class Foo:\n    def __init__(self): self.x = 1\nfoo = Foo()"
    _, metas = pool.run_meta('s7', src)
    by_name = {m.name: m for m in metas}
    assert 'Foo' in by_name and 'foo' in by_name
    assert by_name['foo'].type == 'Foo'
    assert by_name['Foo'].shape is None and by_name['foo'].shape is None


def test_run_meta_pandas_dataframe(pool):
    pytest.importorskip('pandas')
    src = "import pandas as pd\ndf = pd.DataFrame({'a': range(5), 'b': range(5)})"
    _, metas = pool.run_meta('s8', src)
    by_name = {m.name: m for m in metas}
    assert by_name['df'].shape == '(5, 2)'
    assert by_name['df'].line == 2


def test_run_meta_numpy_array(pool):
    pytest.importorskip('numpy')
    src = "import numpy as np\narr = np.zeros((3, 3), dtype=np.float64)"
    _, metas = pool.run_meta('s9', src)
    by_name = {m.name: m for m in metas}
    assert by_name['arr'].shape == '(3, 3)'
    assert by_name['arr'].dtype == 'float64'
    assert by_name['arr'].line == 2
