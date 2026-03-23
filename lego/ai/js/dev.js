// Initializes Monaco once and allows spawning multiple editors across pages
// Functional, succinct style; responsive-friendly
(function(){
  // --- Loader (single-instance) ---
  function ensureMonaco(){
    if (window.monaco) return Promise.resolve(window.monaco);
    if (window.__legoMonacoReady) return window.__legoMonacoReady;
    window.__legoMonacoReady = new Promise((resolve, reject) => {
      const start = () => {
        try { resolve(window.monaco); } catch (e) { console.error('[lego:monaco] init error', e); reject(e); }
      };
      const configureAndLoad = () => {
        if (typeof window.require === 'function' && window.require.config){
          try { window.require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.47.0/min/vs' } }); } catch(err) {}
          window.require(['vs/editor/editor.main'], start, reject);
        } else {
          // If an AMD loader is not yet available, wait a tick and retry
          setTimeout(() => { if (window.require) configureAndLoad(); else start(); }, 0);
        }
      };
      if (!document.querySelector('script[src*="monaco-editor"][src*="loader.js"]')){
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.47.0/min/vs/loader.js';
        s.onload = configureAndLoad; s.onerror = reject; document.head.appendChild(s);
      } else configureAndLoad();
    });
    return window.__legoMonacoReady;
  }

  // --- Utilities ---
  function pickTheme(){ return htmlElement && htmlElement.classList && htmlElement.classList.contains('dark') ? 'vs-dark' : 'vs'; }
  function resolveEl(elOrSel){ return typeof elOrSel === 'string' ? me(elOrSel) : elOrSel; }

  // Track editors for theme updates / disposal
  const editors = new Set();

  // --- Core creation ---
  function createEditor(elOrSel, opts){
    const el = resolveEl(elOrSel || '#dev-cb-editor');
    if (!el || el._editor) return el && el._editor;
    const options = opts || {};
    const language = options.language || el?.dataset?.lang || 'javascript';
    const stateKey = options.stateKey || el?.dataset?.key || 'lego:cb';
    const defaultValue = options.defaultValue || [
      'function cb(msg){','  // Return ctx or a transformed value; this runs client-side.','  return msg;','}'
    ].join('\n');
    const value = (typeof options.value === 'string' ? options.value : (getState(stateKey) || defaultValue));
    const theme = options.theme || pickTheme();

    const editor = monaco.editor.create(el, {
      value: value,
      language: language,
      automaticLayout: true,
      theme: theme,
      minimap: { enabled: false },
      wordWrap: 'on',
      fontSize: 14,
      ...(options.monaco || {})
    });
    el._editor = editor;
    editors.add(editor);

    const sync = () => {
      try {
        const v = editor.getValue();
        storeState(stateKey, v);
        const ta = me('#fs-dev-cb');
        if (ta) ta.value = v;
      } catch(e) {}
    };
    editor.onDidChangeModelContent(sync); sync();
    return editor;
  }

  // Create editors for all matching elements on the page
  function createEditorsForPage(root){
    const scope = root || document;
    const nodes = Array.from(scope.querySelectorAll('#dev-cb-editor, [data-monaco], .lego-monaco'));
    nodes.forEach((n) => { if (!n._editor) createEditor(n); });
  }

  // Update theme on all editors when theme toggles
  function applyThemeToAll(){
    if (!window.monaco) return;
    const th = pickTheme();
    try { monaco.editor.setTheme(th); } catch(e) {}
  }

  // Public API
  window.LegoMonaco = {
    load: ensureMonaco,
    create: function(elOrSel, opts){ return ensureMonaco().then(() => createEditor(elOrSel, opts)); },
    createAll: function(root){ return ensureMonaco().then(() => createEditorsForPage(root)); },
    dispose: function(elOrSel){
      const el = resolveEl(elOrSel);
      if (el && el._editor){ try { el._editor.dispose(); editors.delete(el._editor); delete el._editor; } catch(e) {} }
    },
    applyTheme: function(){ applyThemeToAll(); }
  };

  // Back-compat: keep initEditor used elsewhere
  function initEditorCompat(lng){ return window.LegoMonaco.create('#dev-cb-editor', { language: lng || 'javascript' }); }

  // Boot on DOM ready, then on HTMX swaps
  function boot(){ ensureMonaco().then(() => { createEditorsForPage(); applyThemeToAll(); }).catch(() => {}); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  document.addEventListener('htmx:afterSwap', function(){ boot(); });

  // Expose compat function name
  window.initEditor = initEditorCompat;
})();


