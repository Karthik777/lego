'''Query embedding for the atlas.

A search box is only a search box if typing in it produces a vector, so the encoder is
part of the block rather than something the caller passes in. Which one is a choice
though: a store of Python chunks and a store of prose want different models, and the
vectors already in a store were written by exactly one of them.

Two rules follow, and both are enforced rather than documented:

* an encoder is loaded **lazily** and once — the first search pays for the model, no
  import does, and a model that will not load leaves the block running rather than
  failing at start-up;
* an encoder is only allowed to answer for a store whose vectors it could have written.
  Dimensions have to agree, and when the store records which encoder built it, the name
  has to agree too. A 512-d query against 384-d rows is not a worse search, it is a
  different question — `check()` says no and the vector leg goes dark with a reason.

`hash` is the fallback: signed hashing over words and character trigrams, pure numpy,
nothing to download. It is a real vector — a lexical one — so the pipeline (ANN, RRF,
clustering, projection) works end to end offline. It is not a semantic model, and every
surface that uses it says so.
'''
import hashlib, re, threading
import numpy as np
from fastcore.all import AttrDict
from lego.core import quick_lgr
from .cfg import cfg

__all__ = ['ENCODERS', 'get_encoder', 'encoder_for', 'check', 'HashEncoder']

info, error, warn = quick_lgr()

# name -> (what it is for, how to build it). The builders are litesearch's, so a model
# that works in a kosha or litesearch script works here under the same name.
ENCODERS = AttrDict(
    hash      = AttrDict(about='Hashed words + trigrams, 256-d. No download, lexical only.', build=None),
    retrieval = AttrDict(about='potion-retrieval-32M — static, fast, general prose.',
                         build=lambda: _static('static_retrieval_embedder')),
    code      = AttrDict(about='potion-code-16M-v2 — static, tuned for source code. What kosha indexes with.',
                         build=lambda: _static('static_code_embedder')),
    science   = AttrDict(about='potion-science-32M — static, tuned for papers.',
                         build=lambda: _static('static_science_embedder')),
    multi     = AttrDict(about='potion-multilingual-128M — static, many languages.',
                         build=lambda: _static('static_embedder')),
    bge       = AttrDict(about='bge-micro-v2 via ONNX — small transformer, asymmetric prompts.',
                         build=lambda: _onnx('bge_model')),
    nomic     = AttrDict(about='nomic-embed-text-v1.5 via ONNX — search_document/search_query prompts.',
                         build=lambda: _onnx('nomic_text_v15')),
    coderank  = AttrDict(about='CodeRankEmbed int8 via ONNX — code, with a query instruction.',
                         build=lambda: _onnx('model')),
    gemma     = AttrDict(about='embeddinggemma-300m via ONNX — the largest here, and the slowest to load.',
                         build=lambda: _onnx('embedding_gemma')),
)

def _static(fn_nm):
    'A model2vec static embedder: one call encodes both sides, and it returns float32.'
    import litesearch.utils as u
    m = getattr(u, fn_nm)()
    enc = lambda txts: np.asarray(m.encode(list(txts)))
    return enc, enc

def _onnx(model_nm):
    'A FastEncode model: document and query go through different prompts, so keep them apart.'
    import litesearch.utils as u
    from litesearch.utils import FastEncode
    m = FastEncode(getattr(u, model_nm))
    assert m.sess, 'ONNX session did not initialise'
    return (lambda txts: np.asarray(m.encode_document(list(txts))),
            lambda txts: np.asarray(m.encode_query(list(txts))))

# ── the offline fallback ──────────────────────────────────────────────────────

_WORD = re.compile(r'[a-z0-9_]+')

class HashEncoder:
    '''Signed hashing over words and character trigrams, L2-normalised.

    Every other encoder here is a download, and a download is a thing that can be
    unavailable — behind a proxy, on a fresh container, on a box with no HF token. This
    one is arithmetic, so the atlas has a vector leg no matter what, and a store seeded
    on a machine with no model is still searchable, clusterable and projectable.

    Trigrams are what keep it from being a slower FTS5: `tokenizer` and `tokenize` share
    no whole word but seven trigrams, so morphology survives where an exact-match index
    would need the stemmer to have guessed right.'''
    def __init__(self, dim=256): self.dim = dim

    def _feats(self, text):
        ws = _WORD.findall((text or '').lower())
        for w in ws:
            yield w, 1.0
            if len(w) > 4:
                for i in range(len(w) - 2): yield f'#{w[i:i+3]}', 0.4

    def _vec(self, text):
        v = np.zeros(self.dim, dtype=np.float32)
        for f, wt in self._feats(text):
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), 'big')
            v[h % self.dim] += wt * (1.0 if (h >> 63) & 1 else -1.0)
        n = np.linalg.norm(v)
        return v / n if n else v

    def encode(self, txts): return np.stack([self._vec(t) for t in txts]) if len(txts) else np.zeros((0, self.dim), np.float32)

# ── loading ───────────────────────────────────────────────────────────────────

_loaded, _lock = {}, threading.Lock()

def _load(name):
    'Build one encoder. Returns the record whether or not the model came up.'
    spec = ENCODERS.get(name)
    if spec is None: return AttrDict(name=name, kind='missing', err=f'no encoder named {name!r}', dim=None, dtype=None)
    if name == 'hash' or spec.build is None:
        h = HashEncoder()
        return AttrDict(name='hash', kind='fallback', doc=h.encode, query=h.encode, dim=h.dim,
                        dtype=np.float32, err=None, about=ENCODERS.hash.about)
    try:
        doc, query = spec.build()
        probe = query(['probe'])
        # the scalar *type*, not a dtype instance: litesearch keys its `f16`/`f32` suffix
        # table on np.float16 and friends, and a np.dtype object misses every entry
        return AttrDict(name=name, kind='model', doc=doc, query=query, dim=int(probe.shape[-1]),
                        dtype=probe.dtype.type, err=None, about=spec.about)
    except Exception as e:
        # a model that will not load is a fact about this machine, not a reason for the
        # page to 500 — the vector leg reports it and the keyword leg carries the search
        warn(f'atlas: encoder {name!r} unavailable: {e}')
        return AttrDict(name=name, kind='broken', err=f'{type(e).__name__}: {e}', dim=None, dtype=None,
                        about=spec.about)

def get_encoder(name=None):
    'The named encoder, built once per process. Never raises — inspect `.kind` and `.err`.'
    name = name or cfg.embedder
    if name not in _loaded:
        with _lock:
            if name not in _loaded: _loaded[name] = _load(name)
    return _loaded[name]

def encoder_for(store):
    '''The encoder this store should be queried with.

    The store's own record wins: rows written by `code` are only comparable to a query
    written by `code`. Then an explicit override, then the app default.'''
    key = f'{store.db}.{store.name}'
    return get_encoder(store.get('embedder') or cfg.embedders.get(key) or cfg.embedder)

def check(store, enc):
    '''Whether `enc` may answer for `store`, and if not, why in one sentence.

    Read this as the precondition for every vector leg on the page. It is deliberately
    strict about dimension and deliberately soft about provenance: a store nobody
    recorded an encoder for gets the benefit of the doubt, with a caveat, because the
    common case is a database built by a kosha or litesearch script that never knew the
    atlas existed.'''
    if enc.kind in ('broken', 'missing'): return AttrDict(ok=False, why=f'encoder {enc.name!r} unavailable — {enc.err}', caveat=None)
    if not store.ndim: return AttrDict(ok=False, why='no embeddings in this store yet', caveat=None)
    if enc.dim != store.ndim:
        return AttrDict(ok=False, caveat=None,
                        why=f'{enc.name} writes {enc.dim}-d vectors and this store holds {store.ndim}-d — '
                            'a distance between them would be arithmetic, not similarity')
    if store.get('embedder') and store.embedder != enc.name:
        return AttrDict(ok=False, caveat=None,
                        why=f'built with {store.embedder!r}, queried with {enc.name!r} — same width, different space')
    if not store.get('embedder'):
        return AttrDict(ok=True, why=None,
                        caveat=f'this store does not record which encoder wrote it; {enc.name} matches on width alone')
    if enc.kind == 'fallback':
        return AttrDict(ok=True, why=None,
                        caveat='hashed lexical vectors, not a semantic model — set ATLAS_EMBEDDER to change that')
    return AttrDict(ok=True, why=None, caveat=None)
