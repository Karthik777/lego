const htmlElement = document.documentElement;
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
const lego = '__LEGO__';
let __LEGO__ = JSON.parse(localStorage.getItem(lego) || '{{__state__}}');
// migrate stored franken-era class names (uk-theme-x -> theme-x, uk-font-* -> font-*)
for (const [k, p] of [['theme','theme-'],['radii','radii-'],['shadows','shadows-'],['font','font-']]) {
    const v = __LEGO__[k];
    if (typeof v === 'string' && v.startsWith('uk-')) __LEGO__[k] = v.replace(/^uk-(theme|radii|shadows|font)-/, p.slice(0, -1) + '-');
}
function storeState(key, value) {__LEGO__[key] = value; localStorage.setItem(lego, JSON.stringify(__LEGO__));}
function getState(key){return __LEGO__[key];}
function removeState(key) {delete  __LEGO__[key]; localStorage.setItem(key, JSON.stringify(__LEGO__)); }
function setCls(key, value, fn=null, ...args) {
    if (value === null || value === undefined) {return;}
    if (__LEGO__[key]) htmlElement.classList.remove(__LEGO__[key]);
    htmlElement.classList.add(value);
    storeState(key, value);
    if (typeof fn === 'function') {fn(...args);}
}
function setTheme(color, fn=null, ...args) {setCls('theme', color, fn, ...args);}
function setRadii(radii, fn=null, ...args) {setCls('radii', radii, fn, ...args);}
function setShadows(shadows, fn=null, ...args) {setCls('shadows', shadows, fn, ...args);}
function setFont(font, fn=null, ...args) {setCls('font', font, fn, ...args);}
function setMode(mode, fn=null, ...args) {
    if (mode === null || mode === undefined) {return;}
    if (mode === 'dark') {htmlElement.classList.remove('light', 'auto'); htmlElement.classList.add('dark'); storeState('mode', mode);}
    if (mode === 'light') {htmlElement.classList.remove('dark', 'auto'); htmlElement.classList.add('light'); storeState('mode', mode);}
    if (mode === 'auto') {
        const isDark = mediaQuery.matches;
        htmlElement.classList.remove(isDark ? 'light' : 'dark');
        htmlElement.classList.add(isDark ? 'dark' : 'light', 'auto');
        storeState('mode', mode);
    }
    if (typeof fn === 'function') {fn(...args);}
}
function setup() {
    setTheme('{{__theme__}}');
    setMode(__LEGO__.mode);
    setRadii(__LEGO__.radii);
    setShadows(__LEGO__.shadows);
    setFont(__LEGO__.font);}

mediaQuery.addEventListener('change', (event) => {if (!htmlElement.classList.contains('auto')) return; setMode('auto');});
setTimeout(setup, 50);

// autoplay/pause .yt-inview iframes when scrolled into/out of view (replaces uk-video)
function ytInview() {
    document.querySelectorAll('.yt-inview iframe').forEach((f) => {
        if (f._ytObs) return;
        f._ytObs = new IntersectionObserver((es) => es.forEach((e) => {
            try {f.contentWindow.postMessage(JSON.stringify({event: 'command', func: e.isIntersecting ? 'playVideo' : 'pauseVideo', args: []}), '*');} catch (_) {}
        }), {threshold: 0.5});
        f._ytObs.observe(f);
    });
}
document.addEventListener('DOMContentLoaded', ytInview);
document.addEventListener('htmx:afterSettle', ytInview);

function* cycle(...items) {
  while(true)
    yield* items;
}
