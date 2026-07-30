// lego dashboards: Chart.js defaults, theme-reactive colours, card tooltips.
(function () {
  // hx-boost swaps the body, which re-runs this file; without the guard every
  // in-dashboard navigation would stack another set of observers
  if (window.legoChartScan) return;
  const SLOTS = ['--chart-1','--chart-2','--chart-3','--chart-4','--chart-5','--chart-6','--chart-7','--chart-8'];
  const CHROME = { grid: '--chart-grid', axis: '--chart-axis', tick: '--chart-tick',
                   card: '--card', ink: '--foreground' };
  const live = new Map();

  // Unregistered custom properties compute to their raw token stream, so a light-dark()
  // value comes back unresolved. Painting it on a probe forces it.
  //
  // One probe per token, not one probe read repeatedly. Re-assigning `style.color` on a
  // single element and reading it back gives a stale answer whenever the browser has not
  // been made to recompute in between — under `prefers-reduced-motion: reduce` every slot
  // comes back as the first one, and the whole dashboard renders in one colour. A separate
  // element per token has nothing to go stale.
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
    const read = [...host.children].map(s => getComputedStyle(s).color);
    host.remove();
    const out = { series: read.slice(0, SLOTS.length) };
    Object.keys(CHROME).forEach((k, i) => { out[k] = read[SLOTS.length + i]; });
    out.font = getComputedStyle(document.body).fontFamily;
    return out;
  }

  const alpha = (c, a) => c.replace(/^rgba?\(([^)]+)\)$/, (_, b) => `rgba(${b.split(',').slice(0, 3).join(',')},${a})`);
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const FMT = {
    int:   (v) => Math.abs(v) >= 1e4 ? Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(v) : Intl.NumberFormat().format(v),
    float: (v) => Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(v),
    money: (v) => '$' + Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v),
    // the mean of a 0/1 column is a share; "37%" is the sentence, "0.37" is the storage
    pct:   (v) => Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(v),
    ms:    (v) => { const s = Math.round(v / 1000); return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`; },
    bytes: (v) => { const u = ['B','KB','MB','GB']; let i = 0; while (v >= 1024 && i < 3) { v /= 1024; i++; } return `${v.toFixed(i ? 1 : 0)} ${u[i]}`; },
  };
  const fmtr = (k) => FMT[k] || FMT.int;

  const rgb = (c) => (c.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);
  // a sequential ramp is one hue running light to dark. Mixing from the card colour rather
  // than from white is what makes it come out light-to-dark on a light surface and
  // dark-to-light on a dark one, off the same two tokens.
  const ramp = (from, to, t) => {
    const a = rgb(from), b = rgb(to);
    return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')})`;
  };

  function tipEl(canvas) {
    const host = canvas.parentNode;
    let el = host.querySelector('.lego-tip');
    if (!el) { el = document.createElement('div'); el.className = 'lego-tip'; host.appendChild(el); }
    return el;
  }

  function place(canvas, el, x, y) {
    el.style.opacity = 1;
    el.style.left = canvas.offsetLeft + x + 'px';
    el.style.top = canvas.offsetTop + y - 12 + 'px';
  }

  function tooltip(ctx) {
    const { chart, tooltip: tt } = ctx;
    const el = tipEl(chart.canvas);
    if (!tt.opacity) { el.style.opacity = 0; return; }
    const f = fmtr(chart.$lego.fmt);
    // on a sideways bar the measure is parsed.x — parsed.y is the category index
    const vAxis = chart.options.indexAxis === 'y' ? 'x' : 'y';
    const box = chart.$lego.box;
    if (box) {
      // five numbers, not one: a box that hovers to its median alone has thrown away
      // the reason it is a box
      const p = tt.dataPoints[0];
      const s = chart.data.datasets[p.datasetIndex].$box[p.dataIndex];
      const row = (k, v) => `<div class="t-row"><span>${k}</span><b>${f(v)}</b></div>`;
      el.innerHTML = `<div class="t-title">${p.label} · ${FMT.int(s.n)} rows</div>` +
        row('p95', s.p95) + row('upper quartile', s.q3) + row('median', s.med) +
        row('lower quartile', s.q1) + row('p05', s.p05) + row('mean', s.mean);
      place(chart.canvas, el, tt.caretX, tt.caretY);
      return;
    }
    if (chart.$lego.scatter) {
      // a point is a pair, and reading one half of it off the tooltip is not reading the point
      const p = tt.dataPoints[0], s = chart.$lego.scatter;
      const c = p.dataset.$key || p.element.options.backgroundColor;
      el.innerHTML = (chart.$lego.series > 1
          ? `<div class="t-title"><i style="background:${c}"></i>${p.dataset.label}</div>` : '') +
        `<div class="t-row"><span>${s.x}</span><b>${fmtr(s.xfmt)(p.parsed.x)}</b></div>` +
        `<div class="t-row"><span>${s.y}</span><b>${f(p.parsed.y)}</b></div>`;
      place(chart.canvas, el, tt.caretX, tt.caretY);
      return;
    }
    const rows = tt.dataPoints.map(p => {
      const c = p.dataset.$key || p.element.options.backgroundColor;
      const label = chart.$lego.series > 1 ? p.dataset.label : p.label;
      const v = typeof p.parsed === 'number' ? p.parsed : p.parsed[vAxis];
      return `<div class="t-row"><i style="background:${c}"></i><span>${label}</span><b>${f(v)}</b></div>`;
    }).join('');
    const head = chart.$lego.series > 1 ? `<div class="t-title">${tt.dataPoints[0].label}</div>` : '';
    el.innerHTML = head + rows;
    place(chart.canvas, el, tt.caretX, tt.caretY);
  }

  // vertical crosshair on the hovered index — line/area only
  const crosshair = {
    id: 'crosshair',
    afterDatasetsDraw(chart) {
      const a = chart.tooltip?.getActiveElements?.() || [];
      if (!a.length || !chart.$lego?.crosshair) return;
      const { ctx, chartArea: ca } = chart;
      ctx.save();
      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      ctx.strokeStyle = chart.$lego.pal.axis;
      ctx.moveTo(a[0].element.x, ca.top);
      ctx.lineTo(a[0].element.x, ca.bottom);
      ctx.stroke();
      ctx.restore();
    },
  };

  // direct labels on bars while they still fit — the relief channel the light-mode
  // palette owes, and simply easier to read than hunting the axis
  const valueLabels = {
    id: 'valueLabels',
    afterDatasetsDraw(chart) {
      const n = chart.data.labels.length;
      const { horizontal, show } = chart.$lego?.labels || {};
      if (!show || n > 15) return;
      const { ctx } = chart;
      const f = fmtr(chart.$lego.fmt);
      ctx.save();
      ctx.font = `600 11px ${chart.$lego.pal.font}`;
      ctx.fillStyle = chart.$lego.pal.ink;
      ctx.textBaseline = 'middle';
      ctx.textAlign = horizontal ? 'left' : 'center';
      chart.getDatasetMeta(0).data.forEach((el, i) => {
        const v = chart.data.datasets[0].data[i];
        if (v == null) return;
        const t = f(v);
        if (horizontal) {
          if (el.x + ctx.measureText(t).width + 8 > chart.chartArea.right) return;
          ctx.fillText(t, el.x + 6, el.y);
        } else {
          if (el.y - 8 < chart.chartArea.top) return;
          ctx.fillText(t, el.x, el.y - 9);
        }
      });
      ctx.restore();
    },
  };

  // The bar Chart.js draws for a box chart is the middle half — a floating bar from the
  // lower to the upper quartile. Everything that makes it a box goes on here: the whiskers
  // out to p05/p95, the median rule across the box, and the mean as a hollow dot, so the
  // two summaries that get confused with each other are visibly different marks.
  const boxParts = {
    id: 'boxParts',
    afterDatasetsDraw(chart) {
      const stats = chart.data.datasets[0]?.$box;
      if (!chart.$lego?.box || !stats) return;
      const { ctx, chartArea: ca } = chart;
      const horiz = chart.options.indexAxis === 'y';
      const vs = horiz ? chart.scales.x : chart.scales.y;
      const pal = chart.$lego.pal;
      ctx.save();
      ctx.lineCap = 'round';
      chart.getDatasetMeta(0).data.forEach((el, i) => {
        const s = stats[i];
        if (!s) return;
        const thick = (horiz ? el.height : el.width) || 12;
        const mid = horiz ? el.y : el.x;
        const at = (v) => vs.getPixelForValue(v);
        const line = (a, b, span) => {
          ctx.beginPath();
          if (horiz) { ctx.moveTo(a, mid - span / 2); ctx.lineTo(a, mid + span / 2); }
          else { ctx.moveTo(mid - span / 2, a); ctx.lineTo(mid + span / 2, a); }
          ctx.stroke();
        };
        ctx.strokeStyle = pal.axis;
        ctx.lineWidth = 1.5;
        // the stem, drawn from each quartile outward so it never crosses the box fill
        ctx.beginPath();
        if (horiz) { ctx.moveTo(at(s.p05), mid); ctx.lineTo(at(s.q1), mid); ctx.moveTo(at(s.q3), mid); ctx.lineTo(at(s.p95), mid); }
        else { ctx.moveTo(mid, at(s.p05)); ctx.lineTo(mid, at(s.q1)); ctx.moveTo(mid, at(s.q3)); ctx.lineTo(mid, at(s.p95)); }
        ctx.stroke();
        line(at(s.p05), null, thick * 0.45);
        line(at(s.p95), null, thick * 0.45);
        ctx.strokeStyle = pal.card;
        ctx.lineWidth = 2.5;
        line(at(s.med), null, thick);
        ctx.strokeStyle = pal.card;
        ctx.fillStyle = pal.ink;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        const mx = horiz ? at(s.mean) : mid, my = horiz ? mid : at(s.mean);
        if (mx >= ca.left && mx <= ca.right) { ctx.arc(mx, my, 2.6, 0, 7); ctx.fill(); ctx.stroke(); }
      });
      ctx.restore();
    },
  };

  // A density heatmap has no marks Chart.js knows how to draw, so it borrows the two
  // linear scales and paints the cells itself. Every row of the table is in here — the
  // scatter it replaces could only ever show the first two thousand.
  const heatCells = {
    id: 'heatCells',
    afterDatasetsDraw(chart) {
      const spec = chart.$lego?.heat;
      if (!spec) return;
      const { ctx, scales: { x: sx, y: sy } } = chart;
      const b = spec.bins, pal = chart.$lego.pal, max = spec.max || 1;
      ctx.save();
      for (const [bx, by, v] of spec.cells) {
        const x0 = sx.getPixelForValue(b.x0 + bx * b.wx), x1 = sx.getPixelForValue(b.x0 + (bx + 1) * b.wx);
        const y0 = sy.getPixelForValue(b.y0 + by * b.wy), y1 = sy.getPixelForValue(b.y0 + (by + 1) * b.wy);
        // a square-root ramp: linear on counts, a single busy cell washes every other
        // one out to the background and the shape disappears
        ctx.fillStyle = ramp(pal.card, pal.series[0], 0.12 + 0.88 * Math.sqrt(v / max));
        ctx.fillRect(x0, Math.min(y0, y1), Math.max(1, x1 - x0), Math.max(1, Math.abs(y1 - y0)));
      }
      ctx.restore();
    },
  };

  function heatHover(canvas, spec) {
    const b = spec.bins, at = new Map(spec.series[0].data.map(([x, y, v]) => [x + ',' + y, v]));
    const f = fmtr('int'), xf = fmtr(spec.xfmt), yf = fmtr(spec.yfmt);
    const el = tipEl(canvas);
    const move = (e) => {
      const ch = live.get(canvas);
      if (!ch) return;
      const r = canvas.getBoundingClientRect();
      const px = e.clientX - r.left, py = e.clientY - r.top;
      const { chartArea: ca, scales: { x: sx, y: sy } } = ch;
      if (px < ca.left || px > ca.right || py < ca.top || py > ca.bottom) { el.style.opacity = 0; return; }
      const bx = Math.floor((sx.getValueForPixel(px) - b.x0) / b.wx);
      const by = Math.floor((sy.getValueForPixel(py) - b.y0) / b.wy);
      const v = at.get(bx + ',' + by);
      if (!v) { el.style.opacity = 0; return; }
      el.innerHTML = `<div class="t-title">${f(v)} rows</div>` +
        `<div class="t-row"><span>${spec.xlabel}</span><b>${xf(b.x0 + bx * b.wx)}–${xf(b.x0 + (bx + 1) * b.wx)}</b></div>` +
        `<div class="t-row"><span>${spec.ylabel}</span><b>${yf(b.y0 + by * b.wy)}–${yf(b.y0 + (by + 1) * b.wy)}</b></div>`;
      place(canvas, el, px, py);
    };
    canvas.removeEventListener('mousemove', canvas.$heatMove);
    canvas.removeEventListener('mouseleave', canvas.$heatOut);
    canvas.$heatMove = move;
    canvas.$heatOut = () => { el.style.opacity = 0; };
    canvas.addEventListener('mousemove', move);
    canvas.addEventListener('mouseleave', canvas.$heatOut);
  }

  // Correlation is a table of numbers that happens to be worth colouring, so it is built
  // as one — real text in real cells, which is legible without the colour, sortable by eye
  // along a row, and the only form here that needs no canvas at all.
  function corrGrid(canvas, spec, pal) {
    const host = canvas.parentNode;
    canvas.style.display = 'none';
    let box = host.querySelector('.corr-grid');
    if (!box) { box = document.createElement('div'); box.className = 'corr-grid'; host.appendChild(box); }
    const cell = (v, i, j) => {
      if (v == null) return '<td class="corr-na">—</td>';
      if (i === j) return '<td class="corr-diag">1</td>';
      // diverging: one hue for negative, another for positive, the surface itself as the
      // neutral midpoint — never a hue at zero
      const bg = ramp(pal.card, v < 0 ? pal.series[1] : pal.series[0], Math.abs(v) * 0.9);
      return `<td style="background:${bg}" title="r = ${v.toFixed(3)}">${v.toFixed(2)}</td>`;
    };
    box.innerHTML = '<table><thead><tr><th></th>' +
      spec.labels.map(l => `<th><span>${l}</span></th>`).join('') + '</tr></thead><tbody>' +
      spec.matrix.map((row, i) => `<tr><th>${spec.labels[i]}</th>` +
        row.map((v, j) => cell(v, i, j)).join('') + '</tr>').join('') +
      `</tbody></table><p class="chart-why">Pearson r over ${FMT.int(spec.n)} complete rows. ` +
      `Blue is a positive relationship, orange a negative one; the stronger the colour, the tighter the fit.</p>`;
  }

  // ── the choropleth ──────────────────────────────────────────────────────────
  // Inline SVG, not a canvas. The geometry arrives as ready-made path strings — projected
  // at build time by tools/geo_build.mjs — so a map is `<path d="…" fill="…">` and there
  // is no mapping library in the page. Every place is also a real DOM node, which is what
  // makes it hoverable, focusable and clickable without hit-testing anything by hand.
  const geoPacks = new Map();
  const geoPack = (nm) => {
    if (!geoPacks.has(nm))
      // one fetch per pack per page, shared by every map on it, and immutable thereafter
      geoPacks.set(nm, fetch(`/dash/geo/${encodeURIComponent(nm)}.json`, { headers: { accept: 'application/json' } })
        .then(r => r.ok ? r.json() : Promise.reject(r.status)));
    return geoPacks.get(nm);
  };

  const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // which quantile class a value falls in — the breaks are upper bounds, computed server-side
  function classOf(v, breaks) {
    let i = 0;
    while (i < breaks.length && v > breaks[i]) i++;
    return i;
  }

  function mapSvg(canvas, spec, pal, geo) {
    const host = canvas.parentNode;
    canvas.style.display = 'none';
    let box = host.querySelector('.map-wrap');
    if (!box) { box = document.createElement('div'); box.className = 'map-wrap'; host.appendChild(box); }
    const f = fmtr(spec.fmt);
    const n = spec.breaks.length + 1;
    // one hue, light to dark, stepped rather than continuous — the classes are the legend
    const step = (i) => ramp(pal.card, pal.series[0], n === 1 ? 0.6 : 0.15 + 0.85 * (i / (n - 1)));
    const paths = Object.entries(geo.shapes).map(([k, d]) => {
      const v = spec.cells[k];
      if (v == null) return `<path d="${d}" class="geo-nil"/>`;
      const nm = geo.names[k] || k;
      return `<path d="${d}" fill="${step(classOf(v, spec.breaks))}" class="geo-on"` +
             ` data-k="${esc(k)}" tabindex="0" role="listitem"` +
             ` aria-label="${esc(nm)}: ${esc(f(v))}"><title>${esc(nm)}: ${esc(f(v))}</title></path>`;
    }).join('');
    const edges = [spec.lo, ...spec.breaks, spec.hi];
    const key = Array.from({ length: n }, (_, i) =>
      `<span><i style="background:${step(i)}"></i>${f(edges[i])}–${f(edges[i + 1])}</span>`).join('');
    box.innerHTML =
      `<svg viewBox="0 0 ${geo.w} ${geo.h}" role="list" aria-label="${esc(spec.label)} by place"` +
      ` preserveAspectRatio="xMidYMid meet">${paths}</svg>` +
      `<div class="map-key">${key}</div>`;
    mapHover(box, canvas, spec, geo);
  }

  function mapHover(box, canvas, spec, geo) {
    const f = fmtr(spec.fmt), el = tipEl(canvas);
    const show = (e) => {
      const k = e.target.dataset?.k;
      if (!k) return;
      const r = box.getBoundingClientRect();
      el.innerHTML = `<div class="t-title">${esc(geo.names[k] || k)}</div>` +
        `<div class="t-row"><span>${esc(spec.label)}</span><b>${f(spec.cells[k])}</b></div>`;
      const p = e.target.getBoundingClientRect();
      place(canvas, el, p.left + p.width / 2 - r.left, p.top - r.top);
    };
    box.addEventListener('mouseover', show);
    box.addEventListener('focusin', show);
    box.addEventListener('mouseout', () => { el.style.opacity = 0; });
    box.addEventListener('focusout', () => { el.style.opacity = 0; });
    if (!spec.on) return;
    const pick = (k) => { const i = Object.keys(spec.cells).indexOf(k); if (i >= 0) drillKey(spec, spec.keys[k]); };
    box.addEventListener('click', (e) => { if (e.target.dataset?.k) pick(e.target.dataset.k); });
    box.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset?.k) { e.preventDefault(); pick(e.target.dataset.k); }
    });
  }

  // Clicking a category is the shortest route to "only AC/DC": the mark already names the
  // thing, so the click adds the filter the reader would otherwise have had to spell out.
  // The raw group key travels in spec.keys — spec.labels is clipped for the axis.
  function drill(spec, i) { drillKey(spec, spec.keys && spec.keys[i]); }

  function drillKey(spec, k) {
    const on = spec.on;
    if (!on || k == null) return;
    const u = new URL(window.location.href);
    const v = [on.t, on.c, on.op || 'eq', k].join(':');
    if (!u.searchParams.getAll('f').includes(v)) u.searchParams.append('f', v);
    u.searchParams.delete('page');   // page 3 of the old result set means nothing in the new one
    window.location.href = u.toString();
  }

  function build(spec, pal) {
    const kind = spec.kind;
    const box = kind === 'box';
    const heat = kind === 'heat';
    const bar = kind === 'bar' || kind === 'hbar' || box;
    const line = kind === 'line' || kind === 'area';
    const round = kind === 'doughnut';
    const f = fmtr(spec.fmt);
    const many = spec.series.length > 1;

    if (heat) return buildHeat(spec, pal);

    const datasets = spec.series.map((s, i) => {
      const c = round ? s.data.map((_, j) => pal.series[j % 8]) : pal.series[i % 8];
      const data = box ? s.data.map(b => [b.q1, b.q3]) : s.data;
      const d = { label: s.label, data, $key: round ? pal.series[0] : c, backgroundColor: c, borderColor: c };
      if (box) Object.assign(d, { $box: s.data, borderRadius: 3, borderSkipped: false, maxBarThickness: 56 });
      else if (bar) Object.assign(d, { borderRadius: 4, borderSkipped: 'start', maxBarThickness: 44 });
      if (bar && spec.stacked) Object.assign(d, { borderWidth: 2, borderColor: pal.card, borderSkipped: false });
      if (line) Object.assign(d, {
        borderWidth: 2, tension: 0.32, pointRadius: 0, pointHoverRadius: 4, pointHitRadius: 14,
        pointHoverBorderWidth: 2, pointHoverBorderColor: pal.card, fill: kind === 'area' && !many,
        backgroundColor: kind === 'area' ? alpha(c, many ? 0.18 : 0.14) : c,
      });
      if (kind === 'scatter') Object.assign(d, { pointRadius: 4, pointHoverRadius: 6, backgroundColor: alpha(c, 0.65) });
      if (round) Object.assign(d, { borderWidth: 2, borderColor: pal.card, hoverOffset: 6 });
      return d;
    });

    // value axis formats its numbers; the category axis must keep Chart.js's own
    // callback, which is what turns a tick index back into its label
    const axis = (val, opts = {}) => {
      const ticks = { color: pal.tick, padding: 8, font: { family: pal.font, size: 11 },
                      maxRotation: 0, autoSkipPadding: 12 };
      if (val) ticks.callback = (v) => (opts.fmt ? fmtr(opts.fmt) : f)(v);
      // a sideways bar chart has ten roomy rows and every one gets its name; a date
      // axis has sixty and has to thin them out
      else if (kind === 'hbar') Object.assign(ticks, { autoSkip: false, crossAlign: 'far' });
      else Object.assign(ticks, { autoSkip: true, maxTicksLimit: 12 });
      return {
        // A log axis is the server's call — it has seen every value, the browser has seen
        // a sample. `.chart-hint` says so on the card, because an axis whose gridlines are
        // not evenly spaced in value is one the reader has to be told about.
        //
        // Spread rather than `type: opts.log ? … : undefined`: a `type` key that is present
        // and undefined is not the same as an absent one. Chart.js infers a bar or line
        // chart's category axis from the scale *id* only when the key is missing, and a
        // present-but-undefined one leaves it linear — which draws tick indices, 0 to 22,
        // where the years should be.
        ...(opts.log ? { type: 'logarithmic' } : {}),
        grid: { display: val, color: pal.grid, drawTicks: false, drawOnChartArea: true },
        border: { display: false, dash: [3, 3] },
        ticks,
        // a bar has to start at zero or its lengths lie. A box or a cloud of points has
        // no length to misread, and zeroing it spends the plot on empty space instead —
        // petal widths run 0.1 to 2.5, so a zeroed axis throws away most of the picture.
        beginAtZero: val && !box && kind !== 'scatter' ? true : undefined,
        // a box is drawn from its quartiles but describes p05 to p95, so the scale has to
        // cover what the whiskers reach or the plugin draws them outside the plot.
        // Suggested rather than fixed: a hard min puts "-4.51" on the axis as a tick.
        suggestedMin: val && box && spec.range ? spec.range[0] : undefined,
        suggestedMax: val && box && spec.range ? spec.range[1] : undefined,
        title: opts.text
          ? { display: true, text: opts.text, color: pal.tick, font: { family: pal.font, size: 11 } }
          : undefined,
      };
    };

    // a scatter has two measured axes, and neither is named by the series label
    if (kind === 'scatter') return {
      type: 'scatter',
      data: { labels: spec.labels, datasets },
      plugins: [],
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: reduced() ? false : { duration: 320 },
        layout: { padding: { top: 4, right: 8 } },
        interaction: { mode: 'nearest', intersect: true },
        scales: { x: axis(true, { fmt: spec.xfmt, text: spec.xlabel, log: spec.xlog }),
                  y: axis(true, { fmt: spec.fmt, text: spec.ylabel, log: spec.log }) },
        plugins: { legend: { display: false },
                   tooltip: { enabled: false, external: tooltip, position: 'nearest' } },
      },
    };

    // stacking is what turns "how many of each" into "of which how many" — two series
    // side by side compare, two stacked compose
    const stack = spec.stacked && (bar || kind === 'area');
    // only a box asks for a log value axis; a bar's length is measured from zero and a log
    // scale has no zero to measure it from
    const vscale = () => Object.assign(axis(true, { log: box && spec.log }), stack ? { stacked: true } : {});
    const cscale = () => Object.assign(axis(false), stack ? { stacked: true } : {});

    return {
      type: round ? 'doughnut' : kind === 'scatter' ? 'scatter' : bar ? 'bar' : 'line',
      data: { labels: spec.labels, datasets },
      plugins: [crosshair, valueLabels, boxParts],
      options: {
        responsive: true, maintainAspectRatio: false,
        indexAxis: kind === 'hbar' ? 'y' : 'x',
        animation: reduced() ? false : { duration: 320 },
        layout: { padding: { top: 4, right: 4 } },
        interaction: line ? { mode: 'index', intersect: false } : { mode: 'nearest', intersect: true },
        onClick: (e, els) => { if (els.length) drill(spec, els[0].index); },
        onHover: (e, els, ch) => { ch.canvas.style.cursor = (spec.on && els.length) ? 'pointer' : 'default'; },
        scales: round ? {} : {
          x: kind === 'hbar' ? vscale() : cscale(),
          y: kind === 'hbar' ? cscale() : vscale(),
        },
        elements: { bar: { borderRadius: 4 } },
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false, external: tooltip, position: 'nearest' },
        },
        cutout: round ? '62%' : undefined,
        barPercentage: 0.82, categoryPercentage: 0.82,
      },
    };
  }

  function buildHeat(spec, pal) {
    const b = spec.bins;
    const num = (fmt, title) => ({
      type: 'linear', title: { display: true, text: title, color: pal.tick, font: { family: pal.font, size: 11 } },
      grid: { color: pal.grid, drawTicks: false },
      border: { display: false },
      ticks: { color: pal.tick, padding: 6, maxTicksLimit: 8, font: { family: pal.font, size: 11 },
               callback: (v) => fmtr(fmt)(v) },
    });
    return {
      type: 'scatter',
      data: { datasets: [{ data: [], showLine: false, pointRadius: 0 }] },
      plugins: [heatCells],
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        layout: { padding: { top: 4, right: 8 } },
        events: [],   // hit-testing is per cell, and the cells are not Chart.js elements
        scales: {
          x: Object.assign(num(spec.xfmt, spec.xlabel), { min: b.x0, max: b.x0 + b.n * b.wx }),
          y: Object.assign(num(spec.yfmt, spec.ylabel), { min: b.y0, max: b.y0 + b.n * b.wy }),
        },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
      },
    };
  }

  function legend(host, spec, pal) {
    const box = host.closest('.chart-card')?.querySelector('.chart-legend');
    if (!box) return;
    const round = spec.kind === 'doughnut';
    // one series is named by the chart title; a legend box would just repeat it
    const items = round ? spec.labels.map((l, i) => [l, pal.series[i % 8]])
                        : spec.series.length > 1 ? spec.series.map((s, i) => [s.label, pal.series[i % 8]]) : [];
    box.innerHTML = items.map(([l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join('');
  }

  // the relief channel for the light-mode slots that run under 3:1 — every chart
  // can hand over its numbers as text
  function dataTable(canvas, spec) {
    const t = canvas.closest('.chart-card')?.querySelector('details.chart-data table');
    if (!t) return;
    const f = fmtr(spec.fmt), xf = fmtr(spec.xfmt || 'float');
    const rows = (head, body) =>
      `<thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${body}</tbody>`;
    if (spec.kind === 'map') {
      const es = Object.entries(spec.cells).sort((a, b) => b[1] - a[1]);
      t.innerHTML = rows(['place', spec.label], es.map(([k, v]) =>
        `<tr><td>${esc(spec.keys[k] || k)}</td><td class="num">${f(v)}</td></tr>`).join(''));
      return;
    }
    if (spec.kind === 'corr') {
      t.innerHTML = rows(['', ...spec.labels], spec.matrix.map((r, i) =>
        `<tr><td>${spec.labels[i]}</td>${r.map(v => `<td class="num">${v == null ? '—' : v.toFixed(3)}</td>`).join('')}</tr>`).join(''));
      return;
    }
    if (spec.kind === 'box') {
      const st = spec.series[0].data;
      t.innerHTML = rows(['', 'n', 'min', 'p05', 'q1', 'median', 'q3', 'p95', 'max', 'mean'],
        spec.labels.map((l, i) => `<tr><td>${l}</td>` +
          [st[i].n, st[i].lo, st[i].p05, st[i].q1, st[i].med, st[i].q3, st[i].p95, st[i].hi, st[i].mean]
            .map((v, j) => `<td class="num">${j === 0 ? FMT.int(v) : f(v)}</td>`).join('') + '</tr>').join(''));
      return;
    }
    if (spec.kind === 'heat') {
      const b = spec.bins, yf = fmtr(spec.yfmt || 'float');
      const cells = [...spec.series[0].data].sort((a, c) => c[2] - a[2]).slice(0, 200);
      t.innerHTML = rows([spec.xlabel, spec.ylabel, 'rows'], cells.map(([x, y, v]) =>
        `<tr><td class="num">${xf(b.x0 + x * b.wx)}–${xf(b.x0 + (x + 1) * b.wx)}</td>` +
        `<td class="num">${yf(b.y0 + y * b.wy)}–${yf(b.y0 + (y + 1) * b.wy)}</td>` +
        `<td class="num">${FMT.int(v)}</td></tr>`).join(''));
      return;
    }
    if (spec.kind === 'scatter') {
      const head = spec.series.length > 1 ? ['series', 'x', 'y'] : ['x', 'y'];
      const body = spec.series.flatMap(s => s.data.slice(0, 200).map(p =>
        `<tr>${spec.series.length > 1 ? `<td>${s.label}</td>` : ''}` +
        `<td class="num">${xf(p.x)}</td><td class="num">${f(p.y)}</td></tr>`)).join('');
      t.innerHTML = rows(head, body);
      return;
    }
    t.innerHTML = rows(['', ...spec.series.map(s => s.label)],
      spec.labels.map((l, i) => `<tr><td>${l}</td>` +
        spec.series.map(s => `<td class="num">${s.data[i] == null ? '—' : f(s.data[i])}</td>`).join('') + '</tr>').join(''));
  }

  // a cursor change is only discoverable once you are already hovering the right thing.
  // A chart drawn from part of the table has to say which part, in the same place.
  function hint(canvas, spec) {
    const foot = canvas.closest('.chart-card')?.querySelector('.chart-foot');
    if (!foot) return;
    const bits = [];
    // an axis whose gridlines are not evenly spaced in value has to announce itself
    if (spec.log && spec.xlog) bits.push('both axes logarithmic');
    else if (spec.log) bits.push(spec.kind === 'scatter' ? 'y axis logarithmic' : 'logarithmic scale');
    else if (spec.xlog) bits.push('x axis logarithmic');
    if (spec.note) bits.push(spec.note);
    // a place the geometry has no shape for is dropped, and a map that dropped rows
    // silently is a map you would read as "nothing there"
    if (spec.unmatched) bits.push(`${FMT.int(spec.unmatched)} unmapped`);
    if (spec.omitted) bits.push(`${FMT.int(spec.omitted)} more not shown`);
    if (spec.omitted_series) bits.push(`${FMT.int(spec.omitted_series)} more series not shown`);
    if (spec.on) bits.push('Click to filter');
    let el = foot.querySelector('.chart-hint');
    if (!bits.length) { if (el) el.remove(); return; }
    if (!el) { el = document.createElement('span'); el.className = 'chart-hint'; foot.appendChild(el); }
    el.textContent = bits.join(' · ');
  }

  function meta(spec, pal) {
    const bars = spec.kind === 'bar' || spec.kind === 'hbar';
    return { fmt: spec.fmt, series: spec.series.length, pal,
             box: spec.kind === 'box',
             scatter: spec.kind === 'scatter'
               ? { x: spec.xlabel, y: spec.ylabel, xfmt: spec.xfmt } : null,
             heat: spec.kind === 'heat'
               ? { bins: spec.bins, max: spec.max, cells: spec.series[0].data } : null,
             crosshair: spec.kind === 'line' || spec.kind === 'area',
             labels: { show: bars && spec.agg !== 'hist' && spec.series.length === 1, horizontal: spec.kind === 'hbar' } };
  }

  function render(canvas, spec) {
    const pal = palette();
    canvas.$spec = spec;
    if (spec.kind === 'corr') { corrGrid(canvas, spec, pal); dataTable(canvas, spec); hint(canvas, spec); return; }
    if (spec.kind === 'map') {
      dataTable(canvas, spec); hint(canvas, spec);
      geoPack(spec.pack).then(geo => mapSvg(canvas, spec, pal, geo))
        .catch(() => { const s = canvas.parentNode.querySelector('.chart-skel'); if (s) s.textContent = 'Map unavailable'; });
      return;
    }
    const cfg = build(spec, pal);
    const m = meta(spec, pal);
    // plugins draw during the first update, so $lego has to exist before construction
    cfg.plugins.push({ id: 'legoInit', beforeInit: (c) => { c.$lego = m; } });
    const prev = live.get(canvas);
    if (prev) prev.destroy();
    const ch = new Chart(canvas, cfg);
    live.set(canvas, ch);
    legend(canvas, spec, pal);
    dataTable(canvas, spec);
    hint(canvas, spec);
    if (spec.kind === 'heat') heatHover(canvas, spec);
  }

  function load(canvas) {
    if (canvas.$loading) return;
    canvas.$loading = true;
    fetch(canvas.dataset.chartSrc, { headers: { accept: 'application/json' } })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(spec => { canvas.parentNode.querySelector('.chart-skel')?.remove(); render(canvas, spec); })
      .catch(() => {
        const s = canvas.parentNode.querySelector('.chart-skel');
        if (s) s.textContent = 'Chart unavailable';
        canvas.$loading = false;
      });
  }

  const io = 'IntersectionObserver' in window
    ? new IntersectionObserver((es, o) => es.forEach(e => { if (e.isIntersecting) { o.unobserve(e.target); load(e.target); } }), { rootMargin: '200px' })
    : null;

  function scan(root) {
    (root || document).querySelectorAll('canvas[data-chart-src]').forEach(c => {
      if (c.$seen) return;
      c.$seen = true;
      io ? io.observe(c) : load(c);
    });
  }

  function repaint() {
    const pal = palette();
    live.forEach((ch, canvas) => {
      const spec = canvas.$spec;
      const next = build(spec, pal);
      ch.data.datasets.forEach((d, i) => Object.assign(d, next.data.datasets[i]));
      ch.options.scales = next.options.scales;
      ch.$lego = meta(spec, pal);
      ch.update('none');
      legend(canvas, spec, pal);
    });
    // correlation grids and maps are DOM, not canvas, so they are not in `live`
    document.querySelectorAll('canvas[data-chart-src]').forEach(c => {
      if (c.$spec?.kind === 'corr') corrGrid(c, c.$spec, pal);
      else if (c.$spec?.kind === 'map') geoPack(c.$spec.pack).then(g => mapSvg(c, c.$spec, pal, g));
    });
  }

  // theme.js swaps classes on <html>; auto mode follows the OS instead
  new MutationObserver(repaint).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
  document.addEventListener('htmx:afterSwap', (e) => scan(e.target));
  if (document.readyState !== 'loading') scan(); else document.addEventListener('DOMContentLoaded', () => scan());
  window.legoChartScan = scan;
})();
