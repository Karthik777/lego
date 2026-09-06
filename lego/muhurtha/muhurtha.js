/* The only thing the browser computes is what time it is.

   Everything else arrived rendered, with its start and end stamped on the element. So this
   walks those stamps once a second, marks whatever is running now, and fills the four
   readouts in the now band. No ephemeris in the browser, no clock skew to reconcile. */
(() => {
    const $ = (id) => document.getElementById(id);
    const boot = window.MH || {};
    const GLYPH = {
        Sun: "☉", Moon: "☽", Mars: "♂", Mercury: "☿",
        Jupiter: "♃", Venus: "♀", Saturn: "♄",
    };

    const ms = (el, k) => Date.parse(el.dataset[k]);

    /* Formatted in the calendar's timezone, never the browser's. A panchangam computed for
       Chennai and read in London still says sunrise at 05:57 -- the whole point is that the
       day belongs to the place, so a viewer in another zone must not see it shifted. */
    const HM = new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit", minute: "2-digit", hour12: false,
        timeZone: (window.MH || {}).tz || undefined,
    });
    const hm = (t) => HM.format(new Date(t));

    function left(to) {
        const s = Math.max(0, Math.round((to - Date.now()) / 1000));
        const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
        return h ? `${h}h ${m}m left` : `${m}m ${String(s % 60).padStart(2, "0")}s left`;
    }

    /* Mark the element whose [start, end) holds now, clear the rest, return it. */
    function mark(nodes, now) {
        let hit = null;
        for (const el of nodes) {
            const on = now >= ms(el, "s") && now < ms(el, "e");
            el.classList.toggle("on", on);
            if (on) hit = el;
        }
        return hit;
    }

    /* The band is driven by the boot arrays, not by the DOM, so it reads the same on a
       month page that has no hora list on it. The lists, when present, are marked too. */
    const running = (rows, now) =>
        rows && rows.find((r) => now >= Date.parse(r[1]) && now < Date.parse(r[2]));

    function set(id, txt) { const e = $(id); if (e) e.textContent = txt; }

    function bar(id, row, now) {
        const b = $(id);
        if (!b) return;
        if (!row) { b.style.width = "0"; return; }
        const a = Date.parse(row[1]), z = Date.parse(row[2]);
        b.style.width = `${Math.min(100, Math.max(0, ((now - a) / (z - a)) * 100))}%`;
    }

    function tick() {
        const now = Date.now();
        mark(document.querySelectorAll("#hora-list .hr"), now);
        mark(document.querySelectorAll("#hora-ribbon i"), now);
        mark(document.querySelectorAll("#mu-list .mu"), now);

        const h = running(boot.horas, now);
        if (h) {
            set("n-hora", h[0]);
            set("n-hora-g", GLYPH[h[0]] || "");
            set("n-hora-t", `${hm(Date.parse(h[1]))}–${hm(Date.parse(h[2]))} · ${left(Date.parse(h[2]))}`);
            bar("n-hora-bar", h, now);
            const subs = boot.subs && boot.subs[h[1]];
            const s = subs && subs.find((x) => now >= Date.parse(x[1]) && now < Date.parse(x[2]));
            set("n-hora-sub", s ? `sub-hora ${s[0]} · until ${hm(Date.parse(s[2]))}` : "");
        }
        const m = running(boot.muhurtas, now);
        if (m) {
            set("n-mu", `${m[3]}. ${m[0]}`);
            set("n-mu-t", `${hm(Date.parse(m[1]))}–${hm(Date.parse(m[2]))} · ${left(Date.parse(m[2]))}`);
            bar("n-mu-bar", m, now);
        }
        if (boot.tithiEnd) set("n-ti-left", left(Date.parse(boot.tithiEnd)));
    }

    // === place picking ===
    const dlg = () => $("mh-place");
    const api = {
        openPlace() { dlg()?.showModal(); $("mh-q")?.focus(); },
        closePlace() { dlg()?.close(); },
        copy(id) {
            const el = $(id);
            el.select();
            navigator.clipboard?.writeText(el.value);
            const b = el.nextElementSibling;
            const t = b.textContent;
            b.textContent = "Copied";
            setTimeout(() => (b.textContent = t), 1400);
        },
        go(lat, lon, tz, name) {
            const u = new URL(location.href);
            u.searchParams.set("lat", (+lat).toFixed(4));
            u.searchParams.set("lon", (+lon).toFixed(4));
            u.searchParams.set("tz", tz);
            u.searchParams.set("place", name || "");
            location.href = u.toString();
        },
        gps() {
            if (!navigator.geolocation) return;
            const btn = $("mh-gps");
            if (btn) { btn.disabled = true; btn.textContent = "Locating\u2026"; }
            const done = () => { if (btn) { btn.disabled = false; btn.textContent = "Use my location"; } };
            navigator.geolocation.getCurrentPosition(
                async (p) => {
                    const { latitude: lat, longitude: lon } = p.coords;
                    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                    api.go(lat, lon, tz, await cityAt(lat, lon));
                },
                () => { done(); alert("Could not read your location."); },
                { timeout: 8000 },
            );
        },
        /* webcal:// is https with a scheme calendar apps claim, so one click hands the
           feed to whichever app owns it instead of downloading a file. */
        webcal() {
            const u = $("feed-url");
            if (u) location.href = u.value.replace(/^https?:/, "webcal:");
        },
        /* The subscribe page rebuilds its URLs from the ticked layers, in place. */
        rebuild() {
            const on = [...document.querySelectorAll('input[name=layer]:checked')].map((x) => x.value);
            for (const [id, key] of [["feed-url", "layers"], ["dav-url", null]]) {
                const el = $(id);
                if (!el) continue;
                if (key) {
                    const u = new URL(el.value, location.origin);
                    u.searchParams.set(key, on.join(","));
                    el.value = u.toString();
                } else if (boot.davBase) {
                    el.value = boot.davBase + btoa(JSON.stringify([...boot.place, on.sort()]))
                        .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "") + "/";
                }
            }
        },
    };
    window.mh = api;

    /* Turn coordinates into a place name.

       GPS used to label itself "My location", which is the one thing the reader already
       knows and tells them nothing about what the almanac was computed for. A city name is
       the answer; the coordinates are the honest fallback when the lookup fails, and the
       page renders those itself when this returns nothing. */
    async function cityAt(lat, lon) {
        try {
            const r = await fetch(
                "https://api.bigdatacloud.net/data/reverse-geocode-client" +
                `?latitude=${lat}&longitude=${lon}&localityLanguage=en`,
            );
            const d = await r.json();
            return d.city || d.locality || d.principalSubdivision || "";
        } catch {
            return "";
        }
    }

    // City search, debounced, against open-meteo's public geocoder.
    let timer;
    $("mh-q")?.addEventListener("input", (e) => {
        clearTimeout(timer);
        const q = e.target.value.trim();
        const hits = $("mh-hits");
        if (q.length < 2) { hits.innerHTML = ""; return; }
        timer = setTimeout(async () => {
            try {
                const r = await fetch(
                    `https://geocoding-api.open-meteo.com/v1/search?count=8&language=en&format=json&name=${encodeURIComponent(q)}`,
                );
                const d = await r.json();
                hits.innerHTML = "";
                for (const p of d.results || []) {
                    const li = document.createElement("li");
                    li.innerHTML = `${p.name}<small>${[p.admin1, p.country].filter(Boolean).join(", ")} · ${p.timezone}</small>`;
                    li.onclick = () => api.go(p.latitude, p.longitude, p.timezone, p.name);
                    hits.appendChild(li);
                }
            } catch { /* offline: the dialog still offers GPS */ }
        }, 250);
    });

    tick();
    setInterval(tick, 1000);
})();
