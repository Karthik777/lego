/* Every brick's drawing, keyed by the name `bricks.py` registered. A brick gets its element and
 * its resolved ports, and calls `emit` when the person does something the document should know. */
const B = {};
const NS = 'http://www.w3.org/2000/svg';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
const sv = (tag, at = {}) => { const n = document.createElementNS(NS, tag); for (const k in at) n.setAttribute(k, at[k]); return n; };
const num = v => typeof v === 'number' ? v : parseFloat(v) || 0;
const money = v => v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'k' : '$' + Number(v).toFixed(v < 1 ? 4 : 2);
const hhmm = s => { const d = new Date(s); return isNaN(d) ? String(s ?? '') : d.toTimeString().slice(0, 5); };
const PLANET = {Sun: '☉', Moon: '☾', Mars: '♂', Mercury: '☿', Jupiter: '♃', Venus: '♀', Saturn: '♄', Rahu: '☊', Ketu: '☋'};
const RASI = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya', 'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena'];
const HUE = {Sun: 32, Moon: 210, Mars: 4, Mercury: 140, Jupiter: 44, Venus: 320, Saturn: 250};

/* === panchanga === */

B['panchanga.day'] = (root, p, emit) => {
  const d = p.day || {};
  const limbs = [['tithi', 'Tithi'], ['nakshatra', 'Nakshatra'], ['yoga', 'Yoga'], ['karana', 'Karana']];
  root.innerHTML = `<div class="bk-head"><b>${esc(d.place_name || 'here')}</b><span>${esc(d.date || '')} · ${esc(d.vara || '')}</span></div>`;
  const grid = el('div', 'bk-limbs');
  for (const [k, label] of limbs) {
    const v = d[k] || {};
    const card = el('button', 'bk-limb', `<i>${esc(label)}</i><b>${esc(v.name || '—')}</b>` +
      (v.end ? `<span>until ${hhmm(v.end)}</span>` : '<span>&nbsp;</span>'));
    card.onclick = () => { emit('limb', k); root.querySelectorAll('.bk-limb').forEach(x => x.classList.remove('on')); card.classList.add('on'); };
    grid.appendChild(card);
  }
  root.appendChild(grid);
  root.appendChild(el('div', 'bk-foot', [
    d.masa && `${esc(d.masa)} ${esc(d.paksha || '')}`, d.moon_phase && esc(d.moon_phase),
    d.sunrise && `sunrise ${hhmm(d.sunrise)}`, d.sunset && `sunset ${hhmm(d.sunset)}`
  ].filter(Boolean).join(' · ')));
};

B['panchanga.horas'] = (root, p, emit) => {
  const hs = p.horas || [];
  root.innerHTML = '<div class="bk-head"><b>Horas</b><span>the twenty-four planetary hours</span></div>';
  const strip = el('div', 'bk-ribbon');
  hs.forEach((h, i) => {
    const pl = h.planet || h.name, hue = HUE[pl] ?? 200;
    const cell = el('button', 'bk-hora', `<b>${PLANET[pl] || '·'}</b><span>${hhmm(h.start)}</span>`);
    cell.style.background = `hsl(${hue} 62% ${i % 2 ? 92 : 88}%)`;
    cell.style.color = `hsl(${hue} 70% 24%)`;
    cell.title = `${pl} · ${hhmm(h.start)}–${hhmm(h.end)}`;
    cell.onclick = () => { strip.querySelectorAll('.bk-hora').forEach(x => x.classList.remove('on')); cell.classList.add('on'); emit('hora', h); };
    strip.appendChild(cell);
  });
  root.appendChild(strip);
};

B['panchanga.wheel'] = (root, p, emit) => {
  const planets = p.planets || [], R = 150, C = 170;
  root.innerHTML = '';
  const s = sv('svg', {viewBox: '0 0 340 340', class: 'bk-wheel'});
  const ring = (r, cls) => s.appendChild(sv('circle', {cx: C, cy: C, r, class: cls}));
  ring(R, 'bk-ring'); ring(R * 0.62, 'bk-ring');
  for (let i = 0; i < 12; i++) {
    const a0 = (i * 30 - 90) * Math.PI / 180, a1 = ((i + 1) * 30 - 90) * Math.PI / 180, am = (a0 + a1) / 2;
    s.appendChild(sv('line', {x1: C + Math.cos(a0) * R * 0.62, y1: C + Math.sin(a0) * R * 0.62,
                              x2: C + Math.cos(a0) * R, y2: C + Math.sin(a0) * R, class: 'bk-spoke'}));
    const wedge = sv('path', {class: 'bk-wedge' + (p.highlight === RASI[i] ? ' on' : ''),
      d: `M ${C + Math.cos(a0) * R * 0.62} ${C + Math.sin(a0) * R * 0.62} A ${R * 0.62} ${R * 0.62} 0 0 1 ${C + Math.cos(a1) * R * 0.62} ${C + Math.sin(a1) * R * 0.62}`
        + ` L ${C + Math.cos(a1) * R} ${C + Math.sin(a1) * R} A ${R} ${R} 0 0 0 ${C + Math.cos(a0) * R} ${C + Math.sin(a0) * R} Z`});
    const here = planets.filter(x => Math.floor(num(x.lon) / 30) === i);
    wedge.onclick = () => { emit('rasi', {name: RASI[i], index: i, planets: here.map(x => x.name)});
      s.querySelectorAll('.bk-wedge').forEach(x => x.classList.remove('on')); wedge.classList.add('on'); };
    wedge.appendChild(sv('title')).textContent = RASI[i] + (here.length ? ' · ' + here.map(x => x.name).join(', ') : '');
    s.appendChild(wedge);
    const t = sv('text', {x: C + Math.cos(am) * R * 0.81, y: C + Math.sin(am) * R * 0.81, class: 'bk-rasi'});
    t.textContent = RASI[i].slice(0, 3); s.appendChild(t);
  }
  planets.forEach((x, j) => {
    const a = (num(x.lon) - 90) * Math.PI / 180, r = R * 0.5 - (j % 3) * 22;
    const g = sv('g', {class: 'bk-graha'});
    const t = sv('text', {x: C + Math.cos(a) * r, y: C + Math.sin(a) * r});
    t.textContent = x.glyph || PLANET[x.name] || x.name?.[0] || '·';
    g.appendChild(t); g.appendChild(sv('title')).textContent = `${x.name} ${num(x.lon).toFixed(1)}°`;
    s.appendChild(g);
  });
  root.appendChild(s);
};

/* === thrifty === */

B['thrifty.costs'] = (root, p, emit) => {
  const rows = (p.rows || []).slice().sort((a, b) => num(a.monthly) - num(b.monthly));
  const top = Math.max(1, ...rows.map(r => num(r.monthly)));
  root.innerHTML = '<div class="bk-head"><b>Cost</b><span>monthly, cheapest first</span></div>';
  const t = el('div', 'bk-rows');
  rows.forEach((r, i) => {
    const row = el('button', 'bk-row' + (i === 0 ? ' best' : ''));
    row.innerHTML = `<span class="bk-lbl">${esc(r.label ?? r.name ?? '?')}</span>` +
      `<span class="bk-bar"><i style="width:${(num(r.monthly) / top * 100).toFixed(1)}%"></i></span>` +
      `<span class="bk-val">${money(num(r.monthly))}</span>` +
      `<span class="bk-sub">${r.per_request != null ? money(num(r.per_request)) + '/req' : ''}</span>`;
    row.onclick = () => emit('row', r);
    t.appendChild(row);
  });
  root.appendChild(t);
};

/* === viz === */

B['viz.tiles'] = (root, p, emit) => {
  root.innerHTML = '';
  const wrap = el('div', 'bk-tiles');
  (p.tiles || []).forEach(t => {
    const d = num(t.delta), tile = el('button', 'bk-tile',
      `<i>${esc(t.label)}</i><b>${esc(t.value)}</b>` + (t.delta != null ? `<span class="${d < 0 ? 'dn' : 'up'}">${d > 0 ? '▲' : '▼'} ${Math.abs(d)}%</span>` : ''));
    tile.onclick = () => emit('tile', t);
    wrap.appendChild(tile);
  });
  root.appendChild(wrap);
};

B['viz.series'] = (root, p, emit) => {
  const labels = p.labels || [], series = p.series || [];
  const W = 560, H = 220, PAD = 34;
  const all = series.flatMap(s => (s.values || []).map(num));
  const lo = Math.min(0, ...all), hi = Math.max(1, ...all);
  const x = i => PAD + i * (W - PAD * 1.4) / Math.max(1, labels.length - 1);
  const y = v => H - PAD - (v - lo) / (hi - lo || 1) * (H - PAD * 1.6);
  root.innerHTML = '';
  const s = sv('svg', {viewBox: `0 0 ${W} ${H}`, class: 'bk-svg'});
  for (let g = 0; g <= 3; g++) {
    const yy = PAD * 0.6 + g * (H - PAD * 1.6) / 3;
    s.appendChild(sv('line', {x1: PAD, x2: W - PAD * 0.4, y1: yy, y2: yy, class: 'bk-grid'}));
  }
  series.forEach((ser, si) => {
    const vs = (ser.values || []).map(num);
    const d = vs.map((v, i) => `${i ? 'L' : 'M'} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
    s.appendChild(sv('path', {d, class: 'bk-line', style: `stroke:hsl(${si * 88 + 200} 70% 46%)`}));
    vs.forEach((v, i) => {
      const c = sv('circle', {cx: x(i), cy: y(v), r: 4, class: 'bk-dot', style: `fill:hsl(${si * 88 + 200} 70% 46%)`});
      c.onclick = () => emit('point', {series: ser.name, label: labels[i], value: v});
      c.appendChild(sv('title')).textContent = `${ser.name} ${labels[i] ?? i}: ${v}`;
      s.appendChild(c);
    });
    const lg = sv('text', {x: W - PAD * 0.4, y: 18 + si * 15, class: 'bk-legend', style: `fill:hsl(${si * 88 + 200} 70% 40%)`});
    lg.textContent = ser.name; s.appendChild(lg);
  });
  labels.forEach((l, i) => { const t = sv('text', {x: x(i), y: H - 8, class: 'bk-axis'}); t.textContent = l; s.appendChild(t); });
  root.appendChild(s);
};

B['viz.funnel'] = (root, p, emit) => {
  let stages = (p.stages || []).map(s => ({...s, value: num(s.value)}));
  const W = 560, H = 250;
  let top = Math.max(1, ...stages.map(s => s.value));
  root.innerHTML = '<div class="bk-head"><b>Funnel</b><span>drag a bar: the document recomputes</span></div>';
  const s = sv('svg', {viewBox: `0 0 ${W} ${H}`, class: 'bk-svg bk-funnel'});
  const bw = (W - 40) / Math.max(1, stages.length);
  let drag = -1;
  //: The handlers live on the svg, not on the bars: a repaint replaces every bar under the pointer.
  const valueAt = clientY => {
    const box = s.getBoundingClientRect();
    return Math.max(0, Math.round((H - 34 - (clientY - box.top) / box.height * H) / (H - 70) * top));
  };
  const paint = () => {
    top = Math.max(1, ...stages.map(x => x.value));         // a bar dragged past the old ceiling stays in the box
    s.innerHTML = '';
    stages.forEach((st, i) => {
      const h = st.value / top * (H - 70), y = H - 34 - h;
      s.appendChild(sv('rect', {x: 20 + i * bw + 5, y, width: bw - 10, height: Math.max(2, h), rx: 5, 'data-i': i,
                                class: 'bk-fbar' + (drag === i ? ' on' : ''),
                                style: `fill:hsl(${205 + i * 12} ${62 - i * 4}% ${48 + i * 6}%)`}));
      const v = sv('text', {x: 20 + i * bw + bw / 2, y: y - 6, class: 'bk-fval'}); v.textContent = st.value; s.appendChild(v);
      const l = sv('text', {x: 20 + i * bw + bw / 2, y: H - 14, class: 'bk-axis'}); l.textContent = st.name; s.appendChild(l);
      if (i) {
        const pc = stages[i - 1].value ? (st.value / stages[i - 1].value * 100).toFixed(0) : '0';
        const c = sv('text', {x: 20 + i * bw, y: 20, class: 'bk-conv'}); c.textContent = pc + '%'; s.appendChild(c);
      }
    });
  };
  let moved = false;
  s.addEventListener('pointerdown', ev => {
    const i = ev.target.dataset?.i; if (i == null) return;
    drag = +i; moved = false; root.dataset.busy = '1'; s.setPointerCapture(ev.pointerId);
    emit('stage', stages[drag]);
  });
  s.addEventListener('pointermove', ev => {
    if (drag < 0) return;
    moved = true;
    stages[drag].value = valueAt(ev.clientY); paint(); emit('stages', stages);
  });
  const stop = () => {
    if (drag < 0) return;
    drag = -1; delete root.dataset.busy; paint();
    if (moved) emit('stages', stages);                     // a click picks a stage; only a drag rewrites them
  };
  s.addEventListener('pointerup', stop);
  s.addEventListener('pointercancel', stop);
  paint();
  root.appendChild(s);
};

/* === learn === */

const ORGANELLES = [
  {name: 'Nucleus', cx: 205, cy: 190, rx: 62, ry: 54, hue: 268, doc: 'Holds the DNA. Transcription happens here; translation does not.'},
  {name: 'Nucleolus', cx: 214, cy: 186, rx: 20, ry: 17, hue: 282, doc: 'Where ribosomal RNA is made and ribosome subunits assembled.'},
  {name: 'Mitochondrion', cx: 100, cy: 120, rx: 46, ry: 25, hue: 8, doc: 'Oxidative phosphorylation. Has its own circular genome, inherited maternally.'},
  {name: 'Mitochondrion ', cx: 330, cy: 300, rx: 44, ry: 24, hue: 8, doc: 'Cells that spend a lot of energy carry hundreds of these.'},
  {name: 'Golgi apparatus', cx: 120, cy: 300, rx: 58, ry: 28, hue: 40, doc: 'Sorts and modifies proteins, then ships them where the address says.'},
  {name: 'Rough ER', cx: 300, cy: 118, rx: 60, ry: 30, hue: 190, doc: 'Ribosome-studded, so it makes membrane and secreted protein.'},
  {name: 'Lysosome', cx: 210, cy: 320, rx: 22, ry: 22, hue: 130, doc: 'Acidic. Digests what the cell has finished with.'},
  {name: 'Vacuole', cx: 386, cy: 200, rx: 28, ry: 34, hue: 200, doc: 'Storage. Small and many in an animal cell, one huge one in a plant cell.'},
  {name: 'Centrosome', cx: 268, cy: 258, rx: 18, ry: 18, hue: 320, doc: 'Organises the microtubules that pull chromosomes apart in mitosis.'}];

B['learn.cell'] = (root, p, emit) => {
  root.innerHTML = '';
  const s = sv('svg', {viewBox: '0 0 480 400', class: 'bk-cell'});
  s.appendChild(sv('ellipse', {cx: 240, cy: 200, rx: 226, ry: 186, class: 'bk-membrane'}));
  s.appendChild(sv('ellipse', {cx: 240, cy: 200, rx: 214, ry: 174, class: 'bk-cytosol'}));
  const note = el('div', 'bk-note', '<b>Click an organelle.</b> What it does appears here, and the document is told.');
  ORGANELLES.forEach(o => {
    const g = sv('g', {class: 'bk-org' + (p.label === o.name.trim() ? ' on' : '')});
    g.appendChild(sv('ellipse', {cx: o.cx, cy: o.cy, rx: o.rx, ry: o.ry, style: `fill:hsl(${o.hue} 62% 74%);stroke:hsl(${o.hue} 52% 42%)`}));
    const t = sv('text', {x: o.cx, y: o.cy + 4}); t.textContent = o.name.trim().split(' ')[0]; g.appendChild(t);
    g.onclick = () => {
      s.querySelectorAll('.bk-org').forEach(x => x.classList.remove('on')); g.classList.add('on');
      note.innerHTML = `<b>${esc(o.name.trim())}</b> ${esc(o.doc)}`;
      emit('organelle', {name: o.name.trim(), doc: o.doc});
    };
    s.appendChild(g);
  });
  root.appendChild(s); root.appendChild(note);
};

B['learn.wavepacket'] = (root, p, emit) => {
  const N = 420, dx = 1, dt = 0.06;
  const V0 = num(p.barrier ?? 1.02), bw = Math.max(1, Math.round(num(p.width ?? 6))), k0 = num(p.k0 ?? 0.7);
  const re = new Float64Array(N), im = new Float64Array(N), V = new Float64Array(N);
  const x0 = N * 0.24, sig = 26, b0 = Math.round(N * 0.56);
  for (let i = 0; i < N; i++) {
    const g = Math.exp(-((i - x0) ** 2) / (2 * sig * sig));
    re[i] = g * Math.cos(k0 * i); im[i] = g * Math.sin(k0 * i);
    V[i] = (i >= b0 && i < b0 + bw) ? V0 * k0 * k0 / 2 : 0;
  }
  root.innerHTML = '';
  const cv = el('canvas', 'bk-canvas'); cv.width = 840; cv.height = 260; root.appendChild(cv);
  const read = el('div', 'bk-note'); root.appendChild(read);
  const ctx = cv.getContext('2d');
  const H = (a, i) => -0.5 * (a[i + 1] - 2 * a[i] + a[i - 1]) / (dx * dx) + V[i] * a[i];
  const soak = new Float64Array(N);                      // absorbing edges, so a wall reflection is not mistaken for physics
  for (let i = 0; i < N; i++) { const e = Math.min(i, N - 1 - i); soak[i] = e < 30 ? Math.exp(-((30 - e) ** 2) * 0.0016) : 1; }
  const step = () => {                                   // staggered leapfrog on dre/dt = H im, dim/dt = -H re
    for (let i = 1; i < N - 1; i++) im[i] -= dt * H(re, i);
    for (let i = 1; i < N - 1; i++) re[i] += dt * H(im, i);
    for (let i = 0; i < N; i++) { re[i] *= soak[i]; im[i] *= soak[i]; }
  };
  let peak0 = 0;
  const draw = () => {
    const W = cv.width, H = cv.height, sx = W / N;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(120,120,160,.22)'; ctx.fillRect(b0 * sx, 0, Math.max(5, bw * sx), H);
    let peak = 1e-9, tot = 0, past = 0;
    for (let i = 0; i < N; i++) { const pr = re[i] ** 2 + im[i] ** 2; peak = Math.max(peak, pr); tot += pr; if (i > b0 + bw) past += pr; }
    peak = Math.max(peak0 || peak, 1e-9);
    if (!peak0) peak0 = peak;
    ctx.beginPath();
    for (let i = 0; i < N; i++) { const y = H - 12 - (re[i] ** 2 + im[i] ** 2) / peak * (H - 30); i ? ctx.lineTo(i * sx, y) : ctx.moveTo(i * sx, y); }
    ctx.strokeStyle = '#2f6df6'; ctx.lineWidth = 2; ctx.stroke();
    ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath(); ctx.fillStyle = 'rgba(47,109,246,.16)'; ctx.fill();
    ctx.beginPath();
    for (let i = 0; i < N; i++) { const y = H / 2 - re[i] * 46; i ? ctx.lineTo(i * sx, y) : ctx.moveTo(i * sx, y); }
    ctx.strokeStyle = 'rgba(220,80,60,.55)'; ctx.lineWidth = 1; ctx.stroke();
    return past / (tot || 1);
  };
  const reset = () => { for (let i = 0; i < N; i++) {
    const g = Math.exp(-((i - x0) ** 2) / (2 * sig * sig));
    re[i] = g * Math.cos(k0 * i); im[i] = g * Math.sin(k0 * i); } };
  let frames = 0, timer = null, best = 0, shown = 0;
  const tick = () => {
    for (let k = 0; k < 40; k++) step();
    const T = draw(); frames++; best = Math.max(best, T);
    const say = Math.max(best, shown);                     // the last full run's answer stands while the next one runs
    read.textContent = `barrier ${V0.toFixed(2)}× the packet energy · width ${bw} · transmitted ${(say * 100).toFixed(1)}%`;
    if (frames % 60 === 0) emit('transmission', +say.toFixed(4));   // once a second: every emit reruns the document
    if (frames > 230) { shown = best; frames = 0; best = 0; peak0 = 0; reset(); }   // it loops: a concept brick is watched more than once
    timer = requestAnimationFrame(tick);
  };
  tick();
  return () => cancelAnimationFrame(timer);
};

B['learn.orbit'] = (root, p, emit) => {
  const mr = Math.max(0.02, num(p.mass_ratio ?? 0.3)), e = Math.min(0.92, Math.max(0, num(p.eccentricity ?? 0.5)));
  root.innerHTML = '';
  const cv = el('canvas', 'bk-canvas'); cv.width = 840; cv.height = 300; root.appendChild(cv);
  const read = el('div', 'bk-note'); root.appendChild(read);
  const ctx = cv.getContext('2d'), G = 4000, m1 = 1, m2 = mr;
  const a = 110, r0 = a * (1 + e);
  let p1 = {x: 420 - r0 * m2 / (m1 + m2), y: 150}, p2 = {x: 420 + r0 * m1 / (m1 + m2), y: 150};
  const v = Math.sqrt(G * (m1 + m2) / r0 * (1 - e) / (1 + e));
  let v1 = {x: 0, y: v * m2 / (m1 + m2)}, v2 = {x: 0, y: -v * m1 / (m1 + m2)};
  const trail = [];
  const acc = () => {
    const dx = p2.x - p1.x, dy = p2.y - p1.y, r = Math.hypot(dx, dy) + 1e-6, f = G / (r * r * r);
    return [{x: f * m2 * dx, y: f * m2 * dy}, {x: -f * m1 * dx, y: -f * m1 * dy}];
  };
  let [a1, a2] = acc(), t = 0, timer = null, laps = 0, was = 0;
  const dt = 0.05;
  const tick = () => {
    for (let k = 0; k < 10; k++) {
      p1.x += v1.x * dt + 0.5 * a1.x * dt * dt; p1.y += v1.y * dt + 0.5 * a1.y * dt * dt;
      p2.x += v2.x * dt + 0.5 * a2.x * dt * dt; p2.y += v2.y * dt + 0.5 * a2.y * dt * dt;
      const [n1, n2] = acc();
      v1.x += 0.5 * (a1.x + n1.x) * dt; v1.y += 0.5 * (a1.y + n1.y) * dt;
      v2.x += 0.5 * (a2.x + n2.x) * dt; v2.y += 0.5 * (a2.y + n2.y) * dt;
      a1 = n1; a2 = n2; t += dt;
    }
    trail.push({x: p2.x, y: p2.y}); if (trail.length > 900) trail.shift();
    const ang = Math.atan2(p2.y - p1.y, p2.x - p1.x);
    if (was < 0 && ang >= 0) { laps++; emit('period', laps); }
    was = ang;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.beginPath(); trail.forEach((q, i) => i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y));
    ctx.strokeStyle = 'rgba(47,109,246,.35)'; ctx.stroke();
    const dot = (q, r, c) => { ctx.beginPath(); ctx.arc(q.x, q.y, r, 0, 7); ctx.fillStyle = c; ctx.fill(); };
    dot(p1, 12 * Math.cbrt(m1), '#e8a13a'); dot(p2, 10 * Math.cbrt(m2), '#2f6df6');
    read.textContent = `mass ratio ${mr.toFixed(2)} · eccentricity ${e.toFixed(2)} · orbits ${laps}`;
    timer = requestAnimationFrame(tick);
  };
  tick();
  return () => cancelAnimationFrame(timer);
};

window.LEGO_BRICKS = B;
