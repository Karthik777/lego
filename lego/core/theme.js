// lego's page script. Mode, theme, corners, shadows and text size are fhoat's (window.fhoat).

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
