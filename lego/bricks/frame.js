/* The brick frame's half of the protocol. A brick announces itself, takes props from the host,
 * and posts back what the person did with it. The host is the document; the frame knows nothing
 * about it beyond these four messages. */
(function () {
  const root = document.getElementById('brick');
  const name = root.dataset.name, manifest = JSON.parse(root.dataset.manifest || '{}');
  let props = JSON.parse(root.dataset.props || '{}'), teardown = null;
  const post = m => parent.postMessage({...m, brick: name, id: root.dataset.frame}, '*');

  function draw() {
    const fn = (window.LEGO_BRICKS || {})[name];
    if (!fn) { root.innerHTML = `<div class="bk-missing">no renderer for <code>${name}</code></div>`; return; }
    if (teardown) { try { teardown(); } catch (e) {} }
    root.innerHTML = '';
    try { teardown = fn(root, props, (port, value) => post({type: 'brick:emit', port, value})) || null; }
    catch (e) { root.innerHTML = `<div class="bk-missing">${name} failed: ${e.message}</div>`; }
    post({type: 'brick:height', px: Math.ceil(document.body.scrollHeight)});
  }

  window.addEventListener('message', ev => {
    const d = ev.data || {};
    if (d.type === 'brick:props' && (!d.id || d.id === root.dataset.frame)) {
      props = {...props, ...(d.props || {})};
      if (!root.dataset.busy) draw();                    // a value coming back mid-drag must not restart the drag
    }
    if (d.type === 'brick:ping') post({type: 'brick:ready', manifest});
  });
  new ResizeObserver(() => post({type: 'brick:height', px: Math.ceil(document.body.scrollHeight)})).observe(document.body);
  draw();
  post({type: 'brick:ready', manifest});
})();
