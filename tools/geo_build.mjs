// Build the geometry packs the map chart draws from.
//
//     cd tools && npm i && node geo_build.mjs
//
// A build-time script, like tools/dash_seeds.py — what it writes is committed, and the app
// never fetches geometry at runtime.
//
// The output is deliberately not GeoJSON or TopoJSON. It is a dict of ready-made SVG path
// strings in a fixed viewBox, so drawing a choropleth is `<path d="…" fill="…">` and
// nothing else. No projection at request time, no topojson client, no mapping library in
// the bundle — the block already refuses to load Chart.js outside /dash and a second
// 200 KB dependency for one chart kind would not have earned its place.
//
// World geometry is projected with **Equal Earth** (Šavrič, Patterson & Jenny 2018).
// Equal-area is not a preference on a choropleth: a Mercator map colours Greenland as
// though it mattered fourteen times more than it does, and the whole point of the chart is
// that area reads as quantity. Equal Earth is the equal-area projection that still looks
// like a map. The US pack needs no projection at all — us-atlas ships an Albers USA
// version already in pixel space, insets and all.
//
// Each pack also carries an alias index: every string that should resolve to a shape.
// Data does not say "DEU", it says "Germany", or "DE", or "Deutschland", or "West Germany".
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { gzipSync } from 'zlib';
import { feature } from 'topojson-client';
import { createRequire } from 'module';
const countries = createRequire(import.meta.url)('world-countries');

const OUT = new URL('../lego/dash/geo/', import.meta.url);
const W = 1000;                 // viewBox width; everything is scaled into it
const PREC = 1;                 // decimal places kept on each coordinate

// ── Equal Earth ───────────────────────────────────────────────────────────────
const [A1, A2, A3, A4] = [1.340264, -0.081106, 0.000893, 0.003796];
const M = Math.sqrt(3) / 2;
function equalEarth(lon, lat) {
  const t = Math.asin(M * Math.sin(lat * Math.PI / 180));
  const t2 = t * t, t6 = t2 * t2 * t2;
  const den = A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2);
  return [2 * Math.sqrt(3) * (lon * Math.PI / 180) * Math.cos(t) / (3 * den),
          t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))];
}

// ── geometry → path ───────────────────────────────────────────────────────────
function rings(geom) {
  if (geom.type === 'Polygon') return geom.coordinates;
  if (geom.type === 'MultiPolygon') return geom.coordinates.flat();
  return [];
}

function pathOf(geom, project, fit) {
  const parts = [];
  for (const ring of rings(geom)) {
    let d = '', last = null;
    for (const [a, b] of ring) {
      const [px, py] = fit(...project(a, b));
      const x = px.toFixed(PREC), y = py.toFixed(PREC);
      // consecutive identical points survive the rounding and double the file for nothing
      if (last === x + ',' + y) continue;
      last = x + ',' + y;
      d += (d ? 'L' : 'M') + x + ',' + y;
    }
    if (d) parts.push(d + 'Z');
  }
  return parts.join('');
}

function bounds(features, project) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of features)
    for (const ring of rings(f.geometry))
      for (const [a, b] of ring) {
        const [x, y] = project(a, b);
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
  return [x0, y0, x1, y1];
}

function build(features, project, key) {
  const [x0, y0, x1, y1] = bounds(features, project);
  const k = W / (x1 - x0);
  const H = (y1 - y0) * k;
  // SVG y grows downward and both projections grow upward, so the flip happens here once
  const fit = (x, y) => [(x - x0) * k, H - (y - y0) * k];
  const shapes = {};
  for (const f of features) {
    const id = key(f);
    if (!id) continue;
    const d = pathOf(f.geometry, project, fit);
    if (d) shapes[id] = shapes[id] ? shapes[id] + d : d;
  }
  return { w: Math.round(W), h: Math.round(H), shapes };
}

// ── aliases ───────────────────────────────────────────────────────────────────
const norm = (s) => String(s).toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

function addAlias(index, key, ...names) {
  for (const n of names) {
    if (!n) continue;
    const k = norm(n);
    // first writer wins: "Georgia" is a country and a US state, and inside the world pack
    // the country is the right answer. Ambiguity across packs is settled by pack choice.
    if (k && !(k in index)) index[k] = key;
  }
}

// Names real data uses that no ISO table lists. Each one is a spelling seen in the sample
// databases or in the Factbook's own country list.
const EXTRA = {
  USA: ['usa', 'us', 'united states', 'united states of america', 'america'],
  GBR: ['uk', 'united kingdom', 'great britain', 'britain', 'england', 'scotland', 'wales'],
  RUS: ['russia', 'russian federation'],
  KOR: ['korea south', 'south korea', 'republic of korea'],
  PRK: ['korea north', 'north korea'],
  MMR: ['burma', 'myanmar'],
  CZE: ['czech republic', 'czechia'],
  TUR: ['turkey', 'turkiye'],
  CIV: ["cote d ivoire", 'ivory coast'],
  COD: ['congo kinshasa', 'democratic republic of the congo', 'dr congo'],
  COG: ['congo brazzaville', 'republic of the congo'],
  SWZ: ['swaziland', 'eswatini'],
  MKD: ['macedonia', 'north macedonia'],
  CPV: ['cape verde', 'cabo verde'],
  TLS: ['east timor', 'timor leste'],
  VAT: ['holy see', 'vatican city'],
  BHS: ['bahamas the', 'the bahamas'],
  GMB: ['gambia the', 'the gambia'],
  NLD: ['netherlands the', 'holland'],
  IRN: ['iran islamic republic of'],
  SYR: ['syrian arab republic'],
  VEN: ['venezuela bolivarian republic of'],
  BOL: ['bolivia plurinational state of'],
  TZA: ['tanzania united republic of'],
  LAO: ['laos', 'lao pdr'],
  MDA: ['moldova republic of'],
  VNM: ['vietnam', 'viet nam'],
  BRN: ['brunei darussalam'],
  MIC: ['micronesia federated states of'],
  PSE: ['west bank', 'gaza strip', 'palestine'],
};

// ── world ─────────────────────────────────────────────────────────────────────
function world() {
  const topo = JSON.parse(readFileSync(createRequire(import.meta.url).resolve('world-atlas/countries-110m.json')));
  const fc = feature(topo, topo.objects.countries);
  // world-atlas ids are ISO 3166-1 *numeric*; everything else in the world speaks alpha-3
  const byNum = Object.fromEntries(countries.map(c => [String(+c.ccn3), c]));
  const pack = build(fc.features, equalEarth, f => (byNum[String(+f.id)] || {}).cca3 || null);
  const index = {}, names = {};
  for (const f of fc.features) {
    const c = byNum[String(+f.id)];
    if (!c || !pack.shapes[c.cca3]) continue;
    names[c.cca3] = c.name.common;
    addAlias(index, c.cca3, c.cca3, c.cca2, c.cioc, String(+c.ccn3).padStart(3, '0'),
             c.name.common, c.name.official, f.properties.name, ...(c.altSpellings || []));
  }
  for (const [k, ns] of Object.entries(EXTRA)) if (pack.shapes[k]) addAlias(index, k, ...ns);
  return { ...pack, key: 'ISO 3166-1 alpha-3', index, names };
}

// ── US states ─────────────────────────────────────────────────────────────────
const POSTAL = {
  Alabama: 'AL', Alaska: 'AK', Arizona: 'AZ', Arkansas: 'AR', California: 'CA', Colorado: 'CO',
  Connecticut: 'CT', Delaware: 'DE', 'District of Columbia': 'DC', Florida: 'FL', Georgia: 'GA',
  Hawaii: 'HI', Idaho: 'ID', Illinois: 'IL', Indiana: 'IN', Iowa: 'IA', Kansas: 'KS',
  Kentucky: 'KY', Louisiana: 'LA', Maine: 'ME', Maryland: 'MD', Massachusetts: 'MA',
  Michigan: 'MI', Minnesota: 'MN', Mississippi: 'MS', Missouri: 'MO', Montana: 'MT',
  Nebraska: 'NE', Nevada: 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
  'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', Ohio: 'OH', Oklahoma: 'OK',
  Oregon: 'OR', Pennsylvania: 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
  'South Dakota': 'SD', Tennessee: 'TN', Texas: 'TX', Utah: 'UT', Vermont: 'VT',
  Virginia: 'VA', Washington: 'WA', 'West Virginia': 'WV', Wisconsin: 'WI', Wyoming: 'WY',
  'Puerto Rico': 'PR',
};

function usStates() {
  const topo = JSON.parse(readFileSync(createRequire(import.meta.url).resolve('us-atlas/states-albers-10m.json')));
  const fc = feature(topo, topo.objects.states);
  // already in Albers USA pixel space, Alaska and Hawaii inset where they belong
  const pack = build(fc.features, (x, y) => [x, -y], f => POSTAL[f.properties.name] || null);
  const index = {}, names = {};
  for (const f of fc.features) {
    const p = POSTAL[f.properties.name];
    if (!p || !pack.shapes[p]) continue;
    names[p] = f.properties.name;
    addAlias(index, p, p, f.properties.name);
  }
  return { ...pack, key: 'USPS state code', index, names };
}

// ── write ─────────────────────────────────────────────────────────────────────
mkdirSync(OUT, { recursive: true });
for (const [nm, pack] of Object.entries({ world: world(), 'us-states': usStates() })) {
  const buf = gzipSync(Buffer.from(JSON.stringify(pack)), { level: 9 });
  writeFileSync(new URL(`${nm}.json.gz`, OUT), buf);
  console.log(`${nm.padEnd(10)} ${Object.keys(pack.shapes).length.toString().padStart(4)} shapes · ` +
              `${Object.keys(pack.index).length} aliases · ${pack.w}×${pack.h} · ` +
              `${(buf.length / 1024).toFixed(0)} KB gz`);
}
