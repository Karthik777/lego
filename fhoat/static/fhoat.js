/* fhoat: light/dark mode, theme choice and htmx toasts for Oat. Runs in <head> before paint. */
(() => {
  const K = 'fhoat', h = document.documentElement, base = h.dataset.theme, q = matchMedia('(prefers-color-scheme: dark)'), MODES = ['auto', 'light', 'dark'];
  let s = {};
  try { s = JSON.parse(localStorage.getItem(K)) || {}; } catch {}
  const save = () => { try { localStorage.setItem(K, JSON.stringify(s)); } catch {} };
  const paint = () => {
    const m = s.mode || h.dataset.mode || 'auto', d = m === 'dark' || (m === 'auto' && q.matches);
    h.classList.toggle('dark', d); h.classList.toggle('light', !d); h.dataset.mode = m;
    const t = s.theme || base; t ? (h.dataset.theme = t) : delete h.dataset.theme;
  };
  const mode = m => { s.mode = m; save(); paint(); };
  const theme = t => { t ? (s.theme = t) : delete s.theme; save(); paint(); };
  const cycle = () => mode(MODES[(MODES.indexOf(h.dataset.mode) + 1) % MODES.length]);
  const toast = d => window.ot ? ot.toast(d.msg ?? '', d.title, d) : addEventListener('DOMContentLoaded', () => toast(d), { once: true });
  q.addEventListener('change', paint);
  addEventListener('toast', e => toast(e.detail || {}));
  paint();
  window.fhoat = { mode, theme, cycle, toast };
})();
