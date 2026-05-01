"""litesearch-backed index over dialogs and messages, plus Symbol Browser helpers.

The index is best-effort: if litesearch isn't installed we degrade to brute-force
filename + content scanning so the rest of the app still works.
"""
import json
from pathlib import Path
from . import data as D
from .cfg import cfg

try:
    from litesearch import database
    _HAS_LS = True
except ImportError:
    database = None
    _HAS_LS = False

_db = None
_dialogs = None
_messages = None


def get_db():
    global _db, _dialogs, _messages
    if not _HAS_LS: return None
    if _db is None:
        cfg.solv_db.parent.mkdir(parents=True, exist_ok=True)
        _db = database(str(cfg.solv_db))
        _dialogs = _db.get_store(name='solv_dialogs', hash=True)
        _messages = _db.get_store(name='solv_messages', hash=True)
    return _db


def _encoder():
    'Return a function that maps text -> bytes (vector). None if encoder unavailable.'
    try:
        from litesearch.utils import FastEncode  # type: ignore
        enc = FastEncode()
        def _e(s):
            try: v = enc.encode([s or ''])
            except Exception: return None
            return v.ravel().tobytes() if v is not None else None
        return _e
    except Exception: return None


def index_dialog(user_id, name, nb):
    if not _HAS_LS: return
    get_db()
    enc = _encoder()
    title = nb.metadata.get('solv', {}).get('title') or name
    desc = nb.metadata.get('solv', {}).get('description', '')
    blob = f'{title}\n{desc}'
    row = dict(content=blob, metadata=json.dumps(dict(user_id=user_id, name=name, title=title)))
    if enc:
        v = enc(blob)
        if v: row['embedding'] = v
    _dialogs.insert_all([row], upsert=True, hash_id='id')
    rows = []
    for c in nb.cells:
        cid = D.cid_of(c)
        if not cid: continue
        body = c.source or ''
        meta = dict(user_id=user_id, dialog=name, cell_id=cid, type=D.cell_type(c))
        r = dict(content=body, metadata=json.dumps(meta))
        if enc:
            v = enc(body)
            if v: r['embedding'] = v
        rows.append(r)
    if rows: _messages.insert_all(rows, upsert=True, hash_id='id')


def search(user_id, q, limit=20):
    if not _HAS_LS or not q: return []
    get_db()
    enc = _encoder()
    q_vec = enc(q) if enc else None
    try:
        if q_vec is not None:
            import numpy as np
            rows = _db.search(q, q_vec, columns=['id', 'content', 'metadata'], dtype=np.float32, quote=True, k=limit)
        else:
            rows = _messages(where="content like ?", where_args=[f'%{q}%'], limit=limit)
    except Exception:
        rows = []
    out = []
    for r in rows or []:
        try: meta = json.loads(r.get('metadata') or '{}')
        except Exception: meta = {}
        if meta.get('user_id') != user_id: continue
        out.append(dict(content=(r.get('content') or '')[:400], **meta,
                        score=r.get('_rrf_score'), distance=r.get('_dist')))
    return out


def remove_dialog(user_id, name):
    if not _HAS_LS: return
    get_db()
    try:
        _messages.delete_where("json_extract(metadata,'$.user_id')=? and json_extract(metadata,'$.dialog')=?",
                               [user_id, name])
        _dialogs.delete_where("json_extract(metadata,'$.user_id')=? and json_extract(metadata,'$.name')=?",
                              [user_id, name])
    except Exception: pass
