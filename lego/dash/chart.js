// lego dashboards: Chart.js defaults, theme-reactive colours, card tooltips.
(function () {
  // hx-boost swaps the body, which re-runs this file; without the guard every
  // in-dashboard navigation would stack another set of observers
  if (window.legoChartScan) return;
  const SLOTS = ['--chart-1','--chart-2','--chart-3','--chart-4','--chart-5','--chart-6','--chart-7','--chart-8'];
  const CHROME = { grid: '--chart-grid', axis: '--chart-axis', tick: '--chart-tick',
                   card: '--card', ink: '--foreground' };
  const live = new Map();

  // Unregistered custom properties compute to their raw token stream, so a
  // light-dark() value comes back unresolved. Painting it on a probe forces it.
  function palette() {
    const p = document.createElement('span');
    p.style.cssText = 'position:absolute;width:0;height:0;visibility:hidden';
    document.body.appendChild(p);
    const read = (v) => { p.style.color = 'rgb(0,0,0)'; p.style.color = `var(${v})`; return getComputedStyle(p).color; };
    const out = { series: SLOTS.map(read) };
    for (const k in CHROME) out[k] = read(CHROME[k]);
    out.font = getComputedStyle(document.body).fontFamily;
    p.remove();
    return out;
  }

  const alpha = (c, a) => c.replace(/^rgba?\(([^)]+)\)$/, (_, b) => `rgba(${b.split(',').slice(0, 3).join(',')},${a})`);
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const FMT = {
    int:   (v) => Math.abs(v) >= 1e4 ? Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(v) : Intl.NumberFormat().format(v),
    float: (v) => Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(v),
    money: (v) => '$' + Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v),
    ms:    (v) => { const s = Math.round(v / 1000); return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`; },
    bytes: (v) => { const u = ['B','KB','MB','GB']; let i = 0; while (v >= 1024 && i < 3) { v /= 1024; i++; } return `${v.toFixed(i ? 1 : 0)} ${u[i]}`; },
  };
  const fmtr = (k) => FMT[k] || FMT.int;

  function tooltip(ctx) {
    const { chart, tooltip: tt } = ctx;
    const host = chart.canvas.parentNode;
    let el = host.querySelector('.lego-tip');
    if (!el) { el = document.createElement('div'); el.className = 'lego-tip'; host.appendChild(el); }
    if (!tt.opacity) { el.style.opacity = 0; return; }
    const f = fmtr(chart.$lego.fmt);
    // on a sideways bar the measure is parsed.x — parsed.y is the category index
    const vAxis = chart.options.indexAxis === 'y' ? 'x' : 'y';
    const rows = tt.dataPoints.map(p => {
      const c = p.dataset.$key || p.element.options.backgroundColor;
      const label = chart.$lego.series > 1 ? p.dataset.label : p.label;
      const v = typeof p.parsed === 'number' ? p.parsed : p.parsed[vAxis];
      return `<div class="t-row"><i style="background:${c}"></i><span>${label}</span><b>${f(v)}</b></div>`;
    }).join('');
    const head = chart.$lego.series > 1 ? `<div class="t-title">${tt.dataPoints[0].label}</div>` : '';
    el.innerHTML = head + rows;
    el.style.opacity = 1;
    const { offsetLeft: x, offsetTop: y } = chart.canvas;
    el.style.left = x + tt.caretX + 'px';
    el.style.top = y + tt.caretY - 12 + 'px';
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

  // Clicking a category is the shortest route to "only AC/DC": the mark already names the
  // thing, so the click adds the filter the reader would otherwise have had to spell out.
  // The raw group key travels in spec.keys — spec.labels is clipped for the axis.
  function drill(spec, i) {
    const on = spec.on, k = spec.keys && spec.keys[i];
    if (!on || k == null) return;
    const u = new URL(window.location.href);
    const v = [on.t, on.c, on.op || 'eq', k].join(':');
    if (!u.searchParams.getAll('f').includes(v)) u.searchParams.append('f', v);
    u.searchParams.delete('page');   // page 3 of the old result set means nothing in the new one
    window.location.href = u.toString();
  }

  function build(spec, pal) {
    const kind = spec.kind;
    const bar = kind === 'bar' || kind === 'hbar';
    const line = kind === 'line' || kind === 'area';
    const round = kind === 'doughnut';
    const f = fmtr(spec.fmt);
    const many = spec.series.length > 1;

    const datasets = spec.series.map((s, i) => {
      const c = round ? s.data.map((_, j) => pal.series[j % 8]) : pal.series[i % 8];
      const d = { label: s.label, data: s.data, $key: round ? pal.series[0] : c, backgroundColor: c, borderColor: c };
      if (bar) Object.assign(d, { borderRadius: 4, borderSkipped: 'start', maxBarThickness: 44 });
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
    const axis = (val) => {
      const ticks = { color: pal.tick, padding: 8, font: { family: pal.font, size: 11 },
                      maxRotation: 0, autoSkipPadding: 12 };
      if (val) ticks.callback = (v) => f(v);
      // a sideways bar chart has ten roomy rows and every one gets its name; a date
      // axis has sixty and has to thin them out
      else if (kind === 'hbar') Object.assign(ticks, { autoSkip: false, crossAlign: 'far' });
      else Object.assign(ticks, { autoSkip: true, maxTicksLimit: 12 });
      return {
        grid: { display: val, color: pal.grid, drawTicks: false, drawOnChartArea: true },
        border: { display: false, dash: [3, 3] },
        ticks, beginAtZero: val || undefined,
      };
    };

    return {
      type: round ? 'doughnut' : kind === 'scatter' ? 'scatter' : bar ? 'bar' : 'line',
      data: { labels: spec.labels, datasets },
      plugins: [crosshair, valueLabels],
      options: {
        responsive: true, maintainAspectRatio: false,
        indexAxis: kind === 'hbar' ? 'y' : 'x',
        animation: reduced() ? false : { duration: 320 },
        layout: { padding: { top: 4, right: 4 } },
        interaction: line ? { mode: 'index', intersect: false } : { mode: 'nearest', intersect: true },
        onClick: (e, els) => { if (els.length) drill(spec, els[0].index); },
        onHover: (e, els, ch) => { ch.canvas.style.cursor = (spec.on && els.length) ? 'pointer' : 'default'; },
        scales: round ? {} : {
          x: kind === 'hbar' ? axis(true) : axis(false),
          y: kind === 'hbar' ? axis(false) : axis(true),
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
    if (spec.kind === 'scatter') {
      const pts = spec.series[0].data.slice(0, 200);
      t.innerHTML = `<thead><tr><th>x</th><th>y</th></tr></thead><tbody>` +
        pts.map(p => `<tr><td class="num">${xf(p.x)}</td><td class="num">${f(p.y)}</td></tr>`).join('') + '</tbody>';
      return;
    }
    const head = ['', ...spec.series.map(s => s.label)];
    t.innerHTML = `<thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>` +
      spec.labels.map((l, i) => `<tr><td>${l}</td>${spec.series.map(s => `<td class="num">${f(s.data[i])}</td>`).join('')}</tr>`).join('') +
      '</tbody>';
  }

  // a cursor change is only discoverable once you are already hovering the right thing
  function hint(canvas, spec) {
    const foot = canvas.closest('.chart-card')?.querySelector('.chart-foot');
    if (!foot) return;
    let el = foot.querySelector('.chart-hint');
    if (!spec.on) { if (el) el.remove(); return; }
    if (!el) { el = document.createElement('span'); el.className = 'chart-hint'; foot.appendChild(el); }
    el.textContent = 'Click to filter';
  }

  function meta(spec, pal) {
    const bars = spec.kind === 'bar' || spec.kind === 'hbar';
    return { fmt: spec.fmt, series: spec.series.length, pal,
             crosshair: spec.kind === 'line' || spec.kind === 'area',
             labels: { show: bars && spec.agg !== 'hist' && spec.series.length === 1, horizontal: spec.kind === 'hbar' } };
  }

  function render(canvas, spec) {
    const pal = palette();
    const cfg = build(spec, pal);
    const m = meta(spec, pal);
    // plugins draw during the first update, so $lego has to exist before construction
    cfg.plugins.push({ id: 'legoInit', beforeInit: (c) => { c.$lego = m; } });
    const prev = live.get(canvas);
    if (prev) prev.destroy();
    const ch = new Chart(canvas, cfg);
    live.set(canvas, ch);
    canvas.$spec = spec;
    legend(canvas, spec, pal);
    dataTable(canvas, spec);
    hint(canvas, spec);
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
  }

  // theme.js swaps classes on <html>; auto mode follows the OS instead
  new MutationObserver(repaint).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
  document.addEventListener('htmx:afterSwap', (e) => scan(e.target));
  if (document.readyState !== 'loading') scan(); else document.addEventListener('DOMContentLoaded', () => scan());
  window.legoChartScan = scan;
})();
