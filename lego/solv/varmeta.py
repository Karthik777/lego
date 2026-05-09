"""Inline variable metadata for PyCharm-style badges.

Pure helpers — no notebook/kernel coupling. Two main responsibilities:

1. `assigned_lines(source)` — AST walk that maps each top-level assigned
   name to the LAST line in the source where it gets bound. Used to
   place a badge on the right line. Comprehension-scoped names
   (list/set/dict/generator) are intentionally excluded since they do
   not leak to the enclosing scope in Python 3.

2. `var_meta(name, value, line, changed)` + `badge_text(meta)` — duck-typed
   inspection that produces a short, PyCharm-flavored label per value.
   No hard dependency on numpy/pandas/torch — we only probe `.shape`,
   `.dtype`, `__len__`.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

REPR_MAX = 60                # truncated repr length kept on VarMeta
BADGE_MAX = 24               # short badge label length cap
SMALL_STR_LEN = 32           # str shorter than this gets rendered as full repr


@dataclass
class VarMeta:
    name: str
    line: int                # 1-indexed line within the cell source
    type: str                # type(v).__name__
    shape: str | None        # str(v.shape) if hasattr
    dtype: str | None        # str(v.dtype) if hasattr
    length: int | None       # len(v) if hasattr and no shape
    repr_short: str          # truncated repr (~REPR_MAX chars)
    changed: bool            # True if name pre-existed with a different id()


# ---------- AST line extraction ----------

_COMP_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _target_names(node):
    """Yield names bound by an assignment target (handles tuple/list unpacking)."""
    if isinstance(node, ast.Name):
        yield node.id
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            yield from _target_names(elt)
    elif isinstance(node, ast.Starred):
        yield from _target_names(node.value)
    # Attribute / Subscript targets do not introduce new names.


def _walk_excluding_comprehensions(root):
    """Like ast.walk, but treats comprehension generator targets as a separate
    sub-scope: we DO descend into the comprehension to capture nested walrus
    assignments etc., but we never yield the generator's `target` subtree."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _COMP_NODES):
            # Visit the elt (and key/value for DictComp) and each generator's
            # iter / ifs, but skip the .target nodes.
            children = []
            if isinstance(node, ast.DictComp):
                children += [node.key, node.value]
            else:
                children.append(node.elt)
            for gen in node.generators:
                children.append(gen.iter)
                children.extend(gen.ifs)
            stack.extend(reversed(children))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # The def/class statement itself binds a top-level name, but names
            # assigned inside its body are scoped locally and must not steal the
            # badge line for an outer/user namespace variable.
            continue
        else:
            stack.extend(reversed(list(ast.iter_child_nodes(node))))


def assigned_lines(source: str) -> dict[str, int]:
    """Return ``{name: 1-indexed line}`` for the LAST assignment of each name.

    Handles ``Assign``, ``AugAssign``, ``AnnAssign``, walrus ``NamedExpr``,
    ``For``/``AsyncFor`` targets, ``With``/``AsyncWith`` ``optional_vars``
    items, and tuple/list unpacking. Comprehension-scoped targets are
    excluded because they do not leak to the enclosing scope.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    out: dict[str, int] = {}

    def record(name, lineno):
        # last write wins
        out[name] = lineno

    for node in _walk_excluding_comprehensions(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                for n in _target_names(tgt):
                    record(n, node.lineno)
        elif isinstance(node, ast.AugAssign):
            for n in _target_names(node.target):
                record(n, node.lineno)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:  # `x: int` (no value) is just a hint
                for n in _target_names(node.target):
                    record(n, node.lineno)
        elif isinstance(node, ast.NamedExpr):  # walrus
            for n in _target_names(node.target):
                record(n, node.lineno)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for n in _target_names(node.target):
                record(n, node.lineno)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    for n in _target_names(item.optional_vars):
                        record(n, node.lineno)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            record(node.name, node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                record((alias.asname or alias.name).split('.')[0], node.lineno)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == '*': continue
                record(alias.asname or alias.name, node.lineno)

    return out


# ---------- value inspection ----------

def _safe_repr(value: Any, limit: int = REPR_MAX) -> str:
    try:
        r = repr(value)
    except Exception:
        return f'<{type(value).__name__}>'
    if len(r) > limit:
        r = r[: limit - 1] + '…'
    return r


def _safe_len(value: Any) -> int | None:
    try:
        return len(value)
    except Exception:
        return None


def _safe_attr(value: Any, name: str) -> Any:
    try:
        return getattr(value, name)
    except Exception:
        return None


def var_meta(name: str, value: Any, line: int, changed: bool) -> VarMeta:
    """Duck-typed VarMeta extraction. Never raises."""
    typ = type(value).__name__
    shape = dtype = None
    length = None

    raw_shape = _safe_attr(value, 'shape')
    if raw_shape is not None and not callable(raw_shape):
        try: shape = str(tuple(raw_shape))
        except Exception:
            try: shape = str(raw_shape)
            except Exception: shape = None
        raw_dtype = _safe_attr(value, 'dtype')
        if raw_dtype is not None:
            try: dtype = str(raw_dtype)
            except Exception: dtype = None

    if shape is None and hasattr(value, '__len__') and not isinstance(value, (str, bytes)):
        length = _safe_len(value)
    elif shape is None and isinstance(value, (str, bytes)) and len(value) > SMALL_STR_LEN:
        length = _safe_len(value)

    return VarMeta(name=name, line=line, type=typ, shape=shape, dtype=dtype,
                   length=length, repr_short=_safe_repr(value), changed=changed)


# ---------- badge label ----------

# Common dtype shorthands so badges stay narrow.
_DTYPE_SHORT = {
    'float64': 'f64', 'float32': 'f32', 'float16': 'f16',
    'int64': 'i64', 'int32': 'i32', 'int16': 'i16', 'int8': 'i8',
    'uint64': 'u64', 'uint32': 'u32', 'uint16': 'u16', 'uint8': 'u8',
    'bool': 'b', 'object': 'obj',
    'complex64': 'c64', 'complex128': 'c128',
}


def _short_dtype(d: str) -> str:
    return _DTYPE_SHORT.get(d, d)


def badge_text(m: VarMeta) -> str:
    """Short label, kept under ~BADGE_MAX chars when possible."""
    if m.shape is not None:
        parts = [m.type, m.shape]
        if m.dtype: parts.append(_short_dtype(m.dtype))
        text = ' '.join(parts)
    elif m.type in ('int', 'float', 'bool') or (m.type == 'str' and m.length is None):
        # Small scalars / short strings get the value inline.
        text = f'{m.type} {m.repr_short}'
    elif m.length is not None:
        text = f'{m.type} len={m.length}'
    else:
        text = m.type
    if len(text) > BADGE_MAX:
        text = text[: BADGE_MAX - 1] + '…'
    return text
