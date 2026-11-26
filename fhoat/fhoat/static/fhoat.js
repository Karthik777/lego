/* fhoat: light/dark mode, the reader's look (theme, radius, shadow, size) and htmx toasts for Oat. Runs in <head> before paint. */
(() => {
  const h = document.documentElement, K = h.dataset.store || 'fhoat', q = matchMedia('(prefers-color-scheme: dark)');
  const KEYS = ['mode', 'theme', 'radius', 'shadow', 'size'], CYCLE = { mode: ['auto', 'light', 'dark'] };
  const base = Object.fromEntries(KEYS.map(k => [k, h.dataset[k]]));
  let s = {}, ready = false, t;
  try { s = JSON.parse(localStorage.getItem(K)) || {}; } catch {}
  const save = () => { try { localStorage.setItem(K, JSON.stringify(s)); } catch {} };
  const get = k => s[k] || base[k] || (k === 'mode' ? 'auto' : '');
  const paint = () => {
    for (const k of KEYS) { const v = get(k); v ? (h.dataset[k] = v) : delete h.dataset[k]; }
    const m = get('mode'), d = m === 'dark' || (m === 'auto' && q.matches);
    h.classList.toggle('dark', d); h.classList.toggle('light', !d); h.classList.toggle('auto', m === 'auto');
    mark();
    if (ready) h.dispatchEvent(new CustomEvent('fhoat', { bubbles: true, detail: Object.fromEntries(KEYS.map(k => [k, get(k)])) }));
  };
  const fade = () => {
    if (!ready || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    h.classList.add('ot-anim'); clearTimeout(t); t = setTimeout(() => h.classList.remove('ot-anim'), 220);
  };
  const mark = () => document.querySelectorAll('[data-set]').forEach(b => { const [k, v] = b.dataset.set.split('='); b.ariaPressed = String(get(k) === v); });
  const set = (k, v) => { v ? (s[k] = v) : delete s[k]; save(); fade(); paint(); };
  const cycle = (k = 'mode', vs = CYCLE[k]) => set(k, vs[(vs.indexOf(get(k)) + 1) % vs.length]);
  const toast = d => window.ot ? ot.toast(d.msg ?? '', d.title, d) : addEventListener('DOMContentLoaded', () => toast(d), { once: true });
  q.addEventListener('change', paint);
  addEventListener('DOMContentLoaded', mark); addEventListener('htmx:afterSettle', mark);
  addEventListener('toast', e => toast(e.detail || {}));
  paint(); ready = true;
  window.fhoat = { get, set, cycle, toast, mode: m => set('mode', m), theme: v => set('theme', v) };
})();
