"""Persistent in-process IPython kernel pool, one shell per dialog.

Backed by execnb's CaptureShell which runs in the parent process and produces
nbformat-shaped output dicts (stream/display_data/execute_result/error).
"""
import asyncio, time, threading, traceback

try:
    from execnb.shell import CaptureShell
except ImportError:  # pragma: no cover
    CaptureShell = None


class KernelPool:
    def __init__(self):
        self._shells = {}      # sid -> CaptureShell
        self._touched = {}     # sid -> last-used timestamp
        self._locks = {}       # sid -> threading.Lock (CaptureShell.run is sync)
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
        return self.get(sid)

    def close(self, sid):
        with self._guard:
            self._shells.pop(sid, None)
            self._touched.pop(sid, None)
            self._locks.pop(sid, None)

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
