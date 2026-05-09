"""Persistent in-process IPython kernel pool, one shell per dialog.

Backed by execnb's CaptureShell which runs in the parent process and produces
nbformat-shaped output dicts (stream/display_data/execute_result/error).
"""
import asyncio, time, threading, traceback

try:
    from execnb.shell import CaptureShell
except ImportError:  # pragma: no cover
    CaptureShell = None

from .varmeta import VarMeta, var_meta, assigned_lines


class KernelPool:
    def __init__(self):
        self._shells = {}      # sid -> CaptureShell
        self._touched = {}     # sid -> last-used timestamp
        self._locks = {}       # sid -> threading.Lock (CaptureShell.run is sync)
        self._baselines = {}   # sid -> set[str] of names present at shell init
        self._guard = threading.Lock()

    def get(self, sid):
        with self._guard:
            sh = self._shells.get(sid)
            if sh is None:
                if CaptureShell is None:
                    raise RuntimeError('execnb is not installed; cannot create kernel')
                sh = CaptureShell()
                self._shells[sid] = sh
                self._locks[sid] = threading.Lock()
                # Capture IPython's startup namespace so user-var diffs can
                # exclude In/Out/exit/get_ipython/etc.
                self._baselines[sid] = set((getattr(sh, 'user_ns', {}) or {}).keys())
            self._touched[sid] = time.time()
            return sh

    def run(self, sid, code):
        sh = self.get(sid)
        with self._locks[sid]:
            try:
                outs = sh.run(code) or []
            except Exception:
                outs = [{'output_type': 'error', 'ename': 'KernelError',
                         'evalue': 'kernel run failed', 'traceback': traceback.format_exc().splitlines()}]
            self._touched[sid] = time.time()
            return outs

    async def arun(self, sid, code):
        return await asyncio.to_thread(self.run, sid, code)

    # ---------- variable-metadata aware execution ----------

    def snapshot_ns(self, sid):
        """Return ``{name: id(value)}`` for non-baseline, non-underscore names."""
        sh = self._shells.get(sid)
        if sh is None: return {}
        ns = getattr(sh, 'user_ns', {}) or {}
        baseline = self._baselines.get(sid, set())
        out = {}
        for k, v in list(ns.items()):
            if k.startswith('_') or k in baseline: continue
            try: out[k] = id(v)
            except Exception: pass
        return out

    def _build_var_metas(self, sid, source, pre, post):
        sh = self._shells.get(sid)
        ns = getattr(sh, 'user_ns', {}) if sh is not None else {}
        lines = assigned_lines(source) if source else {}
        metas = []
        _MISSING = object()
        for name, new_id in post.items():
            old_id = pre.get(name)
            if old_id is not None and old_id == new_id:
                continue  # unchanged
            line = lines.get(name)
            if line is None:
                # name changed but does not appear as an assignment target in
                # this cell (e.g. mutated in place via a function call). We
                # cannot place a badge on a specific source line, so skip.
                continue
            value = ns.get(name, _MISSING)
            if value is _MISSING:
                # Raced — name vanished between snapshot and inspection.
                continue
            metas.append(var_meta(name, value, line, changed=(old_id is not None)))
        # Stable-sort by line then name for deterministic rendering.
        metas.sort(key=lambda m: (m.line, m.name))
        return metas

    def run_meta(self, sid, code):
        """Run `code` and return ``(outputs, var_metas)``. ``var_metas`` is
        derived state — never persisted."""
        # Ensure shell exists and baseline is captured BEFORE the snapshot.
        self.get(sid)
        pre = self.snapshot_ns(sid)
        outs = self.run(sid, code)
        post = self.snapshot_ns(sid)
        try:
            metas = self._build_var_metas(sid, code, pre, post)
        except Exception:
            metas = []
        return outs, metas

    async def arun_meta(self, sid, code):
        return await asyncio.to_thread(self.run_meta, sid, code)

    def get_vars(self, sid, max_repr=200):
        sh = self._shells.get(sid)
        if sh is None: return []
        ns = getattr(sh, 'user_ns', {}) or {}
        out = []
        for k, v in list(ns.items()):
            if k.startswith('_') or k in ('In', 'Out', 'exit', 'quit', 'get_ipython'): continue
            if callable(v) and getattr(v, '__module__', '') in ('builtins',): continue
            try: r = repr(v)
            except Exception: r = '<unrepresentable>'
            if len(r) > max_repr: r = r[:max_repr] + '…'
            try: sz = len(v) if hasattr(v, '__len__') else None
            except Exception: sz = None
            out.append(dict(name=k, type=type(v).__name__, repr=r, size=sz))
        return out

    def restart(self, sid):
        with self._guard:
            self._shells.pop(sid, None)
            self._touched.pop(sid, None)
            self._locks.pop(sid, None)
            self._baselines.pop(sid, None)
        return self.get(sid)

    def close(self, sid):
        with self._guard:
            self._shells.pop(sid, None)
            self._touched.pop(sid, None)
            self._locks.pop(sid, None)
            self._baselines.pop(sid, None)

    def gc(self, idle_seconds):
        cutoff = time.time() - idle_seconds
        with self._guard:
            stale = [s for s, t in self._touched.items() if t < cutoff]
        for s in stale: self.close(s)
        return len(stale)


# global singleton
pool = KernelPool()


def session_id(user_id, dialog_name):
    return f'{user_id}::{dialog_name}'
