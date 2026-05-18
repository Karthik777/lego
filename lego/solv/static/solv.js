// solv frontend: Monaco bootstrap, keyboard shortcuts, SSE streaming, ghost text.
(function () {
  'use strict';

  const MONACO_CDN = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.0/min/vs';

  function loadMonaco(cb) {
    if (window.monaco) return cb();
    if (window.__solvMonacoLoading) {
      window.__solvMonacoCallbacks = window.__solvMonacoCallbacks || [];
      window.__solvMonacoCallbacks.push(cb); return;
    }
    window.__solvMonacoLoading = true;
    window.__solvMonacoCallbacks = [cb];
    const loader = document.createElement('script');
    loader.src = MONACO_CDN + '/loader.js';
    loader.onload = () => {
      window.require.config({ paths: { vs: MONACO_CDN } });
      window.require(['vs/editor/editor.main'], () => {
        (window.__solvMonacoCallbacks || []).forEach(fn => { try { fn(); } catch (e) {} });
        window.__solvMonacoCallbacks = [];
      });
    };
    document.head.appendChild(loader);
  }

  function initEditor(textarea) {
    if (textarea.dataset.solvInit === '1') return;
    textarea.dataset.solvInit = '1';
    const lang = textarea.dataset.monaco || 'python';
    const host = document.createElement('div');
    host.className = 'solv-monaco-host';
    host.style.minHeight = '4rem';
    host.style.height = Math.max(80, Math.min(400, textarea.value.split('\n').length * 18 + 24)) + 'px';
    textarea.style.display = 'none';
    textarea.parentNode.insertBefore(host, textarea);
    const editor = window.monaco.editor.create(host, {
      value: textarea.value, language: lang,
      automaticLayout: true, minimap: { enabled: false },
      fontSize: 13, lineNumbers: 'off', wordWrap: 'on',
      scrollBeyondLastLine: false, theme: matchMedia('(prefers-color-scheme: dark)').matches ? 'vs-dark' : 'vs',
    });
    editor.onDidChangeModelContent(() => {
      textarea.value = editor.getValue();
      textarea.dispatchEvent(new Event('change', { bubbles: true }));
    });
    editor.onDidBlurEditorText(() => {
      textarea.dispatchEvent(new Event('blur', { bubbles: true }));
    });
    editor.addCommand(window.monaco.KeyMod.Shift | window.monaco.KeyCode.Enter, () => {
      const cell = textarea.closest('.solv-cell');
      if (!cell) return;
      const btn = cell.querySelector('.uk-btn-primary, .uk-btn.uk-btn-primary, [hx-post*="/run/"], [hx-get*="/stream/"]');
      if (btn) btn.click();
    });
    editor.addCommand(window.monaco.KeyCode.Escape, () => {
      const cell = textarea.closest('.solv-cell');
      if (cell) cell.classList.remove('editing');
      editor.getDomNode().blur();
    });
  }

  function bootstrapEditors(root) {
    root = root || document;
    const tas = root.querySelectorAll('textarea.solv-monaco:not([data-solv-init="1"])');
    if (!tas.length) return;
    loadMonaco(() => tas.forEach(initEditor));
  }

  // SSE stream handler for prompt cells. The /stream/{cid} endpoint is hooked via hx-get
  // and HTMX swaps the response into #resp-{cid}. For true streaming, we intercept the
  // request and pipe chunks directly (HTMX SSE ext is also acceptable; this stays minimal).
  function attachStream(btn) {
    btn.addEventListener('click', (ev) => {
      const url = btn.getAttribute('hx-get');
      const cell = btn.closest('.solv-cell');
      if (!url || !cell) return;
      const cid = cell.dataset.cid;
      const target = document.getElementById('resp-' + cid);
      if (!target) return;
      ev.preventDefault();
      ev.stopPropagation();
      target.innerHTML = '<div class="solv-streaming"></div>';
      const sink = target.firstChild;
      const stop = cell.querySelector('.solv-stop-btn');
      if (stop) stop.classList.remove('hidden');
      const ta = cell.querySelector('textarea[name="content"]');
      const u = new URL(url, location.origin);
      if (ta) u.searchParams.set('content', ta.value);
      const es = new EventSource(u.toString());
      cell.__solvES = es;
      es.addEventListener('message', (e) => {
        sink.textContent += e.data;
      });
      es.addEventListener('done', () => {
        es.close();
        if (stop) stop.classList.add('hidden');
        // refresh cell to render markdown + persist response
        htmx.ajax('GET', location.pathname, { target: '#cell-list-wrap', swap: 'innerHTML' });
      });
      es.addEventListener('error', () => {
        es.close();
        if (stop) stop.classList.add('hidden');
      });
    });
  }

  function bootstrapStreams(root) {
    (root || document).querySelectorAll('.solv-cell-prompt [hx-get*="/stream/"]:not([data-solv-stream="1"])')
      .forEach(b => { b.dataset.solvStream = '1'; attachStream(b); });
  }

  // Keyboard shortcuts (selection mode H/P/E/X, W on prompt response)
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    if (document.activeElement.classList && document.activeElement.classList.contains('monaco-editor')) return;
    const sel = document.querySelector('.solv-cell.selected');
    if (!sel) return;
    const cid = sel.dataset.cid;
    const map = { h: 'hide', p: 'pin', e: 'export', w: 'split' };
    const action = map[e.key.toLowerCase()];
    if (action) {
      const url = location.pathname.replace(/\/$/, '') + '/msg/' + cid + '/' + action;
      htmx.ajax('POST', url, { target: '#cell-' + cid, swap: 'outerHTML' });
      e.preventDefault();
    } else if (e.key.toLowerCase() === 'x') {
      if (confirm('Delete cell?'))
        htmx.ajax('DELETE', location.pathname.replace(/\/$/, '') + '/msg/' + cid,
                  { target: '#cell-' + cid, swap: 'outerHTML' });
      e.preventDefault();
    }
  });

  document.addEventListener('click', (e) => {
    const cell = e.target.closest && e.target.closest('.solv-cell');
    document.querySelectorAll('.solv-cell.selected').forEach(c => c.classList.remove('selected'));
    if (cell && !e.target.closest('button, a, textarea, .monaco-editor')) cell.classList.add('selected');
    if (cell && e.target.closest('.solv-md, .solv-cell-note > .solv-md')) cell.classList.add('editing');
  });

  function bootstrap(root) { bootstrapEditors(root); bootstrapStreams(root); }
  document.addEventListener('DOMContentLoaded', () => bootstrap(document));
  document.body.addEventListener('htmx:afterSwap', (ev) => bootstrap(ev.target));
  window.solv = { bootstrap };
})();
