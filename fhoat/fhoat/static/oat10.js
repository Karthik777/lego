/* Oat 1.0's title sweep on Oat 1.1: each title= becomes data-tooltip (and aria-label when it has none) as the page loads and as nodes arrive.
   1.1 converts a title only on hover; an app drawn on 1.0 reads data-tooltip before that. oat_hdrs(compat=True), deferred before oat.min.js. */
(() => {
  const S = '[title]', mv = e => {
    const t = e.getAttribute?.('title'); if (!t) return;
    e.setAttribute('data-tooltip', t); e.hasAttribute('aria-label') || e.setAttribute('aria-label', t); e.removeAttribute('title');
  };
  addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll(S).forEach(mv);
    new MutationObserver(ms => { for (const m of ms) { mv(m.target); for (const n of m.addedNodes) if (n.nodeType === 1) { mv(n); n.querySelectorAll(S).forEach(mv); } } })
      .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['title'] });
  });
})();
