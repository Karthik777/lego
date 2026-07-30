// lego atlas: the embedding projection, drawn straight onto a canvas.
//
// Chart.js draws this block's neighbour, and it would draw a scatter here too — but four
// thousand points with a per-point hit ring, a query marker and a hover that has to read
// the text behind the dot is not the chart library's shape. A quadtree-free nearest-point
// scan over a flat typed array is about thirty lines, redraws in one frame, and keeps the
// picture honest: one dot is one row, never a bucket.
(function () {
  if (window.legoAtlasScan) return;
  const SLOTS = ['--atlas-1', '--atlas-2', '--atlas-3', '--atlas-4',
                 '--atlas-5', '--atlas-6', '--atlas-7', '--atlas-8'];
  const CHROME = { grid: '--atlas-grid', ink: '--foreground', card: '--card', muted: '--muted-foreground' };
  const live = new Set();

  // Unregistered custom properties compute to their raw token stream, so a light-dark()
  // value comes back unresolved. Painting each on its own probe forces it — one probe per
  // token, because re-reading a single element gives a stale answer whenever the browser
  // has not been made to recompute in between.
  function palette() {
    const names = [...SLOTS, ...Object.values(CHROME)];
    const host = document.createElement('div');
    host.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;visibility:hidden';
    for (const v of names) {
      const s = document.createElement('span');
      s.style.color = `var(${v})`;
      host.appendChild(s);
    }
    document.body.appendChild(host);
    const read = [...host.children].map((s) => getComputedStyle(s).color);
    host.remove();
    const out = { series: read.slice(0, SLOTS.length) };
    Object.keys(CHROME).forEach((k, i) => { out[k] = read[SLOTS.length + i]; });
    return out;
  }

  const alpha = (c, a) => c.replace(/^rgba?\(([^)]+)\)$/, (_, b) => `rgba(${b.split(',').slice(0, 3).join(',')},${a})`);
  const PAD = 14;

  function layout(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  }

  // The payload's coordinates are already scaled into a unit box, so the only mapping
  // left is unit box -> pixels, and the y flip that makes "up" mean "more".
  const sx = (x, w) => PAD + x * (w - 2 * PAD);
  const sy = (y, h) => h - PAD - y * (h - 2 * PAD);

  function draw(canvas) {
    const st = canvas.$atlas;
    if (!st) return;
    const { ctx, w, h } = layout(canvas);
    const pal = st.pal;
    ctx.clearRect(0, 0, w, h);

    // A faint grid, because a projection with no frame reads as a picture rather than as
    // axes — and these axes are principal components, which is exactly the thing readers
    // over-interpret. The label under the canvas says what share of the variance they are.
    ctx.strokeStyle = alpha(pal.grid, 0.7);
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const gx = sx(i / 4, w), gy = sy(i / 4, h);
      ctx.beginPath(); ctx.moveTo(gx, PAD); ctx.lineTo(gx, h - PAD); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PAD, gy); ctx.lineTo(w - PAD, gy); ctx.stroke();
    }

    const pts = st.points, hits = st.hits, dim = hits.size > 0;
    const r = pts.length > 2500 ? 1.6 : pts.length > 800 ? 2.2 : 3;
    for (const p of pts) {
      const on = hits.has(p.i);
      if (on) continue;                       // hits are drawn last, on top of the field
      ctx.fillStyle = alpha(pal.series[p.c % 8], dim ? 0.22 : 0.6);
      ctx.beginPath();
      ctx.arc(sx(p.x, w), sy(p.y, h), r, 0, 6.284);
      ctx.fill();
    }
    for (const p of pts) {
      if (!hits.has(p.i)) continue;
      const px = sx(p.x, w), py = sy(p.y, h);
      ctx.fillStyle = pal.series[p.c % 8];
      ctx.beginPath(); ctx.arc(px, py, r + 1.2, 0, 6.284); ctx.fill();
      ctx.strokeStyle = pal.ink; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(px, py, r + 4, 0, 6.284); ctx.stroke();
    }
    if (st.q) {
      // the query is not a row, so it is not a dot: a cross says "this is where you are
      // standing", which is a different kind of thing from "this is a document"
      const qx = sx(st.q[0], w), qy = sy(st.q[1], h);
      ctx.strokeStyle = pal.ink; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(qx - 7, qy); ctx.lineTo(qx + 7, qy);
      ctx.moveTo(qx, qy - 7); ctx.lineTo(qx, qy + 7);
      ctx.stroke();
      ctx.beginPath(); ctx.arc(qx, qy, 10, 0, 6.284); ctx.stroke();
    }
    if (st.hover != null) {
      const p = pts[st.hover];
      ctx.strokeStyle = pal.ink; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(sx(p.x, w), sy(p.y, h), r + 5, 0, 6.284); ctx.stroke();
    }
  }

  function nearest(canvas, mx, my) {
    const st = canvas.$atlas;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    let best = -1, bd = 144;                  // 12px, squared — beyond that nothing is "under" the cursor
    for (let i = 0; i < st.points.length; i++) {
      const p = st.points[i];
      const dx = sx(p.x, w) - mx, dy = sy(p.y, h) - my;
      const d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }

  function wire(canvas) {
    const box = canvas.parentNode;
    const tip = box.querySelector('.proj-tip');
    canvas.addEventListener('mousemove', (e) => {
      const b = canvas.getBoundingClientRect();
      const mx = e.clientX - b.left, my = e.clientY - b.top;
      const st = canvas.$atlas;
      const i = nearest(canvas, mx, my);
      if (i !== st.hover) { st.hover = i; draw(canvas); }
      if (i < 0) { tip.style.opacity = 0; canvas.style.cursor = 'crosshair'; return; }
      const p = st.points[i];
      tip.textContent = `${st.names[p.c] || 'cluster ' + (p.c + 1)} · ${p.t}`;
      tip.style.opacity = 1;
      tip.style.left = Math.min(mx + 12, canvas.clientWidth - tip.offsetWidth - 6) + 'px';
      tip.style.top = Math.max(4, my - tip.offsetHeight - 10) + 'px';
      canvas.style.cursor = 'pointer';
    });
    canvas.addEventListener('mouseleave', () => {
      tip.style.opacity = 0;
      canvas.$atlas.hover = null;
      draw(canvas);
    });
    canvas.addEventListener('click', () => {
      const st = canvas.$atlas;
      if (st.hover == null || st.hover < 0) return;
      window.location.href = st.doc.replace('__ID__', st.points[st.hover].i);
    });
    if ('ResizeObserver' in window) new ResizeObserver(() => draw(canvas)).observe(canvas);
  }

  function legend(canvas, spec, pal) {
    const el = canvas.parentNode.parentNode.querySelector('.proj-legend');
    if (!el) return;
    el.textContent = '';
    for (const c of spec.clusters) {
      const s = document.createElement('span');
      const d = document.createElement('span');
      d.className = 'dot';
      d.style.background = pal.series[c.i % 8];
      s.appendChild(d);
      s.appendChild(document.createTextNode(`${c.name} (${c.n.toLocaleString()})`));
      el.appendChild(s);
    }
    const note = document.createElement('span');
    note.textContent = `${spec.n.toLocaleString()} vectors · ${Math.round(spec.ratio * 100)}% of variance on these axes`;
    el.appendChild(note);
  }

  function render(canvas, spec) {
    const pal = palette();
    let hits = [], q = null;
    try { hits = JSON.parse(canvas.dataset.hits || '[]') || []; } catch (_) { hits = []; }
    try { q = JSON.parse(canvas.dataset.q || 'null'); } catch (_) { q = null; }
    canvas.$atlas = {
      points: spec.points, pal, hits: new Set(hits), q, hover: null, doc: spec.doc,
      names: Object.fromEntries(spec.clusters.map((c) => [c.i, c.name])),
    };
    canvas.$spec = spec;
    live.add(canvas);
    legend(canvas, spec, pal);
    draw(canvas);
  }

  function load(canvas) {
    if (canvas.$loading) return;
    canvas.$loading = true;
    fetch(canvas.dataset.projSrc, { headers: { accept: 'application/json' } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((spec) => {
        const skel = canvas.parentNode.querySelector('.proj-skel');
        if (!spec.ok) { if (skel) skel.textContent = spec.why || 'No projection'; return; }
        if (skel) skel.remove();
        render(canvas, spec);
        wire(canvas);
      })
      .catch(() => {
        const s = canvas.parentNode.querySelector('.proj-skel');
        if (s) s.textContent = 'Projection unavailable';
        canvas.$loading = false;
      });
  }

  function scan(root) {
    (root || document).querySelectorAll('canvas[data-proj-src]').forEach((c) => {
      if (c.$seen) return;
      c.$seen = true;
      load(c);
    });
  }

  function repaint() {
    const pal = palette();
    live.forEach((canvas) => {
      canvas.$atlas.pal = pal;
      legend(canvas, canvas.$spec, pal);
      draw(canvas);
    });
  }

  // theme.js swaps classes on <html>; auto mode follows the OS instead
  new MutationObserver(repaint).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
  document.addEventListener('htmx:afterSwap', (e) => scan(e.target));
  if (document.readyState !== 'loading') scan();
  else document.addEventListener('DOMContentLoaded', () => scan());
  window.legoAtlasScan = scan;
})();
