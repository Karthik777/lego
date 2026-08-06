            (() => {
                if (!window.luxon?.DateTime) {
                    document.getElementById("status").textContent =
                        "Error: Luxon failed to load.";
                    return;
                }
                if (!window.Astronomy) {
                    document.getElementById("status").textContent =
                        "Error: Astronomy Engine failed to load.";
                    return;
                }

                const { DateTime } = window.luxon;
                const Astronomy = window.Astronomy;

                const planets = [
                    "Sun",
                    "Venus",
                    "Mercury",
                    "Moon",
                    "Saturn",
                    "Jupiter",
                    "Mars",
                ];
                const dayToPlanet = {
                    0: 0,
                    1: 3,
                    2: 6,
                    3: 2,
                    4: 5,
                    5: 1,
                    6: 4,
                };
                const planetColors = {
                    Sun: "planet-sun",
                    Venus: "planet-venus",
                    Mercury: "planet-mercury",
                    Moon: "planet-moon",
                    Saturn: "planet-saturn",
                    Jupiter: "planet-jupiter",
                    Mars: "planet-mars",
                };

                const tithiNames = [
                    "Pratipada",
                    "Dvitiya",
                    "Tritiya",
                    "Chaturthi",
                    "Panchami",
                    "Shashthi",
                    "Saptami",
                    "Ashtami",
                    "Navami",
                    "Dashami",
                    "Ekadashi",
                    "Dwadashi",
                    "Trayodashi",
                    "Chaturdashi",
                    "Purnima",
                    "Pratipada",
                    "Dvitiya",
                    "Tritiya",
                    "Chaturthi",
                    "Panchami",
                    "Shashthi",
                    "Saptami",
                    "Ashtami",
                    "Navami",
                    "Dashami",
                    "Ekadashi",
                    "Dwadashi",
                    "Trayodashi",
                    "Chaturdashi",
                    "Amavasya",
                ];

                const nakshatraNames = [
                    "Ashwini",
                    "Bharani",
                    "Krittika",
                    "Rohini",
                    "Mrigashirsha",
                    "Ardra",
                    "Punarvasu",
                    "Pushya",
                    "Ashlesha",
                    "Magha",
                    "Purva Phalguni",
                    "Uttara Phalguni",
                    "Hasta",
                    "Chitra",
                    "Swati",
                    "Vishakha",
                    "Anuradha",
                    "Jyeshtha",
                    "Mula",
                    "Purva Ashadha",
                    "Uttara Ashadha",
                    "Shravana",
                    "Dhanishta",
                    "Shatabhisha",
                    "Purva Bhadrapada",
                    "Uttara Bhadrapada",
                    "Revati",
                ];

                const rasiNames = [
                    "Mesha",
                    "Vrishabha",
                    "Mithuna",
                    "Karka",
                    "Simha",
                    "Kanya",
                    "Tula",
                    "Vrishchika",
                    "Dhanu",
                    "Makara",
                    "Kumbha",
                    "Meena",
                ];

                const el = {
                    subtitle: document.getElementById("subtitle"),
                    controls: document.getElementById("controls"),

                    panchangSource: document.getElementById("panchang-source"),
                    panchangTithiSnap: document.getElementById(
                        "panchang-tithi-snap",
                    ),
                    panchangTithiSnapRange: document.getElementById(
                        "panchang-tithi-snap-range",
                    ),
                    panchangNakshatraSnap: document.getElementById(
                        "panchang-nakshatra-snap",
                    ),
                    panchangNakshatraSnapRange: document.getElementById(
                        "panchang-nakshatra-snap-range",
                    ),
                    panchangRasiSnap:
                        document.getElementById("panchang-rasi-snap"),
                    panchangRasiSnapRange: document.getElementById(
                        "panchang-rasi-snap-range",
                    ),

                    locationLabel: document.getElementById("location-label"),
                    locationMeta: document.getElementById("location-meta"),
                    tz: document.getElementById("tz"),
                    clock: document.getElementById("clock"),
                    clockDate: document.getElementById("clock-date"),

                    sunrise: document.getElementById("sunrise"),
                    sunset: document.getElementById("sunset"),
                    nextSunrise: document.getElementById("next-sunrise"),
                    sunNote: document.getElementById("sun-note"),

                    currentHora: document.getElementById("current-hora"),
                    currentSub: document.getElementById("current-sub"),
                    currentRange: document.getElementById("current-range"),
                    currentCountdown:
                        document.getElementById("current-countdown"),

                    status: document.getElementById("status"),
                    horaGrid: document.getElementById("hora-grid"),

                    date: document.getElementById("date"),
                    time: document.getElementById("time"),
                    whenControls: document.getElementById("when-controls"),
                    btnDatePrev: document.getElementById("btn-date-prev"),
                    btnDateNext: document.getElementById("btn-date-next"),
                    lat: document.getElementById("lat"),
                    lon: document.getElementById("lon"),
                    nowMode: document.getElementById("now-mode"),

                    btnSearch: document.getElementById("btn-search"),
                    btnCloseSearch: document.getElementById("btn-close-search"),
                    btnUseLocation: document.getElementById("btn-use-location"),
                    btnShare: document.getElementById("btn-share"),
                    btnUpdate: document.getElementById("btn-update"),
                    btnRecalc: document.getElementById("btn-recalc"),
                    btnClear: document.getElementById("btn-clear"),
                    btnJumpCurrent: document.getElementById("btn-jump-current"),

                    bottomHora: document.getElementById("bottom-hora"),
                    bottomSub: document.getElementById("bottom-sub"),
                    bottomCountdown:
                        document.getElementById("bottom-countdown"),
                    btnBottomJump: document.getElementById("btn-bottom-jump"),

                    searchModal: document.getElementById("search-modal"),
                    cityQuery: document.getElementById("city-query"),
                    searchStatus: document.getElementById("search-status"),
                    searchResults: document.getElementById("search-results"),

                    loadingOverlay: document.getElementById("loading-overlay"),
                };

                const state = {
                    label: "",
                    lat: null,
                    lon: null,
                    tz: null,
                    tzSource: null, // "gps" | "search" | "ip" | "url" | "stored" | "manual" | null
                    schedule: null,
                    horas: [],
                    currentKey: "",
                    panchang: null,
                    nowTicker: null,
                    search: { timer: null, abort: null, results: [] },
                    sunCache: new Map(),

                };

                function escapeHtml(text) {
                    return String(text)
                        .replaceAll("&", "&amp;")
                        .replaceAll("<", "&lt;")
                        .replaceAll(">", "&gt;")
                        .replaceAll('"', "&quot;")
                        .replaceAll("'", "&#39;");
                }

                function setStatus(message, kind = "info") {
                    const color =
                        kind === "error"
                            ? "text-rose-700"
                            : kind === "success"
                              ? "text-emerald-700"
                              : "text-slate-600";
                    el.status.className = `min-h-[1.25rem] text-sm ${color}`;
                    el.status.textContent = message || "";
                }

                function showLoading() {
                    if (el.loadingOverlay) {
                        el.loadingOverlay.classList.remove("hidden");
                        el.loadingOverlay.classList.add("flex");
                    }
                }

                function hideLoading() {
                    if (el.loadingOverlay) {
                        el.loadingOverlay.classList.add("hidden");
                        el.loadingOverlay.classList.remove("flex");
                    }
                }

                function setSearchStatus(message, kind = "info") {
                    const color =
                        kind === "error"
                            ? "text-rose-700"
                            : kind === "success"
                              ? "text-emerald-700"
                              : "text-slate-600";
                    el.searchStatus.className = `px-4 py-2 text-sm ${color} sm:px-6`;
                    el.searchStatus.textContent = message || "";
                }

                function parseNumber(value) {
                    const n = Number(value);
                    return Number.isFinite(n) ? n : null;
                }

                function isIanaZone(zone) {
                    return typeof zone === "string" && zone.includes("/");
                }

                function toFixedCoord(value) {
                    if (!Number.isFinite(value)) return "";
                    return value
                        .toFixed(6)
                        .replace(/0+$/, "")
                        .replace(/\.$/, "");
                }

                function formatTime(dt) {
                    return dt.toFormat("HH:mm");
                }

                function formatClock(dt) {
                    return dt.toFormat("HH:mm:ss");
                }

                function formatPrettyDate(dt) {
                    return dt.toFormat("ccc, LLL dd");
                }

                function nextISODate(dateISO, days) {
                    return DateTime.fromISO(dateISO, { zone: "UTC" })
                        .plus({ days })
                        .toISODate();
                }

                function formatCountdown(ms) {
                    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
                    const hours = Math.floor(totalSeconds / 3600);
                    const minutes = Math.floor((totalSeconds % 3600) / 60);
                    const seconds = totalSeconds % 60;
                    if (hours > 0)
                        return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
                    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
                }

                function normalizeAngle(deg) {
                    const x = deg % 360;
                    return x < 0 ? x + 360 : x;
                }

                function unwrapNear(angleDeg, referenceDeg) {
                    const k = Math.round((referenceDeg - angleDeg) / 360);
                    return angleDeg + 360 * k;
                }

                function getEclipticLongitudeDegrees(body, date) {
                    const vec = Astronomy.GeoVector(body, date, true);
                    const ecl = Astronomy.Ecliptic(vec);
                    return normalizeAngle(ecl.elon);
                }

                function lahiriAyanamsaDegrees(date) {
                    const j2000 = Date.UTC(2000, 0, 1, 12, 0, 0);
                    const years =
                        (date.getTime() - j2000) / 86400000 / 365.2425;
                    const baseDeg = 23.85675;
                    const rateDegPerYear = 50.290966 / 3600;
                    return baseDeg + rateDegPerYear * years;
                }

                function getSiderealMoonLongitudeDegrees(date) {
                    const tropical = getEclipticLongitudeDegrees("Moon", date);
                    const ayan = lahiriAyanamsaDegrees(date);
                    return normalizeAngle(tropical - ayan);
                }

                function getSunMoonDeltaDegrees(date) {
                    const moon = getEclipticLongitudeDegrees("Moon", date);
                    const sun = getEclipticLongitudeDegrees("Sun", date);
                    return normalizeAngle(moon - sun);
                }

                function findCrossingMillis({
                    startMillis,
                    targetAngleUnwrapped,
                    direction,
                    angleGetter,
                    maxSteps = 96,
                    stepMillis = 60 * 60 * 1000,
                }) {
                    const startAngleRaw = angleGetter(startMillis);
                    let prev = startAngleRaw;

                    const startAngleUnwrapped = startAngleRaw;
                    let lowMillis, highMillis, lowAngle, highAngle;

                    if (direction < 0) {
                        highMillis = startMillis;
                        highAngle = startAngleUnwrapped;
                        lowMillis = startMillis;
                        lowAngle = highAngle;

                        for (let i = 0; i < maxSteps; i++) {
                            const t = startMillis - stepMillis * (i + 1);
                            const raw = angleGetter(t);
                            const unwrapped = unwrapNear(raw, prev);
                            prev = unwrapped;
                            lowMillis = t;
                            lowAngle = unwrapped;
                            if (lowAngle <= targetAngleUnwrapped) break;
                        }

                        if (
                            !(
                                lowAngle <= targetAngleUnwrapped &&
                                targetAngleUnwrapped <= highAngle
                            )
                        ) {
                            throw new Error(
                                "Could not bracket panchang boundary.",
                            );
                        }
                    } else {
                        lowMillis = startMillis;
                        lowAngle = startAngleUnwrapped;
                        highMillis = startMillis;
                        highAngle = lowAngle;

                        for (let i = 0; i < maxSteps; i++) {
                            const t = startMillis + stepMillis * (i + 1);
                            const raw = angleGetter(t);
                            const unwrapped = unwrapNear(raw, prev);
                            prev = unwrapped;
                            highMillis = t;
                            highAngle = unwrapped;
                            if (highAngle >= targetAngleUnwrapped) break;
                        }

                        if (
                            !(
                                lowAngle <= targetAngleUnwrapped &&
                                targetAngleUnwrapped <= highAngle
                            )
                        ) {
                            throw new Error(
                                "Could not bracket panchang boundary.",
                            );
                        }
                    }

                    let leftT = lowMillis;
                    let leftA = lowAngle;
                    let rightT = highMillis;
                    let rightA = highAngle;

                    for (let i = 0; i < 40; i++) {
                        const midT = Math.floor((leftT + rightT) / 2);
                        const raw = angleGetter(midT);
                        const midA = unwrapNear(raw, leftA);

                        if (midA < targetAngleUnwrapped) {
                            leftT = midT;
                            leftA = midA;
                        } else {
                            rightT = midT;
                            rightA = midA;
                        }
                        if (rightT - leftT <= 1000) break;
                    }

                    return rightT;
                }

                function formatRange({ startMillis, endMillis, zone }) {
                    const start = DateTime.fromMillis(Math.round(startMillis), {
                        zone,
                    });
                    const end = DateTime.fromMillis(Math.round(endMillis), {
                        zone,
                    });
                    if (start.toISODate() === end.toISODate()) {
                        return `${start.toFormat("HH:mm")}–${end.toFormat("HH:mm")}`;
                    }
                    return `${start.toFormat("LLL dd HH:mm")} → ${end.toFormat("LLL dd HH:mm")}`;
                }

                function computePanchang(moment, zone) {
                    const date = moment.toJSDate();
                    const nowMillis = date.getTime();

                    const tithiStep = 12;
                    const nakStep = 360 / 27;
                    const rasiStep = 30;

                    const deltaNow = getSunMoonDeltaDegrees(date);
                    const moonSidNow = getSiderealMoonLongitudeDegrees(date);

                    const tithiNumber = Math.floor(deltaNow / tithiStep) + 1;
                    const tithiName =
                        tithiNames[tithiNumber - 1] || `Tithi ${tithiNumber}`;
                    const paksha = tithiNumber <= 15 ? "Shukla" : "Krishna";
                    const tithiLabel = `${paksha} ${tithiName}`;

                    const nakNumber = Math.floor(moonSidNow / nakStep) + 1;
                    const nakLabel =
                        nakshatraNames[nakNumber - 1] ||
                        `Nakshatra ${nakNumber}`;

                    const rasiNumber = Math.floor(moonSidNow / rasiStep) + 1;
                    const rasiLabel =
                        rasiNames[rasiNumber - 1] || `Rasi ${rasiNumber}`;

                    const deltaStartAngle =
                        Math.floor(deltaNow / tithiStep) * tithiStep;
                    const deltaEndAngle = deltaStartAngle + tithiStep;

                    const moonStartAngle =
                        Math.floor(moonSidNow / nakStep) * nakStep;
                    const moonEndAngle = moonStartAngle + nakStep;

                    const rasiStartAngle =
                        Math.floor(moonSidNow / rasiStep) * rasiStep;
                    const rasiEndAngle = rasiStartAngle + rasiStep;

                    const deltaGetter = (ms) =>
                        getSunMoonDeltaDegrees(new Date(ms));
                    const moonSidGetter = (ms) =>
                        getSiderealMoonLongitudeDegrees(new Date(ms));

                    const tithiStartMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: deltaStartAngle,
                        direction: -1,
                        angleGetter: deltaGetter,
                    });
                    const tithiEndMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: deltaEndAngle,
                        direction: +1,
                        angleGetter: deltaGetter,
                    });

                    const nakStartMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: moonStartAngle,
                        direction: -1,
                        angleGetter: moonSidGetter,
                    });
                    const nakEndMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: moonEndAngle,
                        direction: +1,
                        angleGetter: moonSidGetter,
                    });

                    const rasiStartMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: rasiStartAngle,
                        direction: -1,
                        angleGetter: moonSidGetter,
                    });
                    const rasiEndMillis = findCrossingMillis({
                        startMillis: nowMillis,
                        targetAngleUnwrapped: rasiEndAngle,
                        direction: +1,
                        angleGetter: moonSidGetter,
                    });

                    const nextChangeMillis = Math.min(
                        tithiEndMillis,
                        nakEndMillis,
                        rasiEndMillis,
                    );

                    return {
                        zone,
                        tithi: {
                            label: tithiLabel,
                            startMillis: tithiStartMillis,
                            endMillis: tithiEndMillis,
                        },
                        nakshatra: {
                            label: nakLabel,
                            startMillis: nakStartMillis,
                            endMillis: nakEndMillis,
                        },
                        rasi: {
                            label: rasiLabel,
                            startMillis: rasiStartMillis,
                            endMillis: rasiEndMillis,
                        },
                        nextChangeMillis,
                    };
                }

                function updatePanchangUI(p) {
                    if (!p) return;
                    if (el.panchangSource)
                        el.panchangSource.textContent =
                            "Sidereal (Lahiri approx)";

                    if (el.panchangTithiSnap)
                        el.panchangTithiSnap.textContent = p.tithi.label;
                    if (el.panchangTithiSnapRange)
                        el.panchangTithiSnapRange.textContent = formatRange({
                            startMillis: p.tithi.startMillis,
                            endMillis: p.tithi.endMillis,
                            zone: p.zone,
                        });

                    if (el.panchangNakshatraSnap)
                        el.panchangNakshatraSnap.textContent =
                            p.nakshatra.label;
                    if (el.panchangNakshatraSnapRange)
                        el.panchangNakshatraSnapRange.textContent = formatRange(
                            {
                                startMillis: p.nakshatra.startMillis,
                                endMillis: p.nakshatra.endMillis,
                                zone: p.zone,
                            },
                        );

                    if (el.panchangRasiSnap)
                        el.panchangRasiSnap.textContent = p.rasi.label;
                    if (el.panchangRasiSnapRange)
                        el.panchangRasiSnapRange.textContent = formatRange({
                            startMillis: p.rasi.startMillis,
                            endMillis: p.rasi.endMillis,
                            zone: p.zone,
                        });

                }

                async function fetchJSON(url, { signal } = {}) {
                    const res = await fetch(url, {
                        method: "GET",
                        signal,
                        headers: { Accept: "application/json" },
                    });
                    if (!res.ok) {
                        let detail = "";
                        try {
                            detail = await res.text();
                        } catch {
                            // ignore
                        }
                        const err = new Error(`Request failed (${res.status})`);
                        err.status = res.status;
                        err.detail = detail;
                        throw err;
                    }
                    return res.json();
                }

                function openMeteoSearchUrl(query) {
                    const base =
                        "https://geocoding-api.open-meteo.com/v1/search";
                    const params = new URLSearchParams({
                        name: query,
                        count: "12",
                        language: "en",
                        format: "json",
                    });
                    return `${base}?${params.toString()}`;
                }

                function openMeteoReverseUrl(lat, lon) {
                    const base =
                        "https://geocoding-api.open-meteo.com/v1/reverse";
                    const params = new URLSearchParams({
                        latitude: String(lat),
                        longitude: String(lon),
                        count: "1",
                        language: "en",
                        format: "json",
                    });
                    return `${base}?${params.toString()}`;
                }

                function openMeteoForecastSunUrl(
                    lat,
                    lon,
                    startDateISO,
                    endDateISO,
                    timezone,
                ) {
                    const base = "https://api.open-meteo.com/v1/forecast";
                    const tzParam = isIanaZone(timezone) ? timezone : "auto";
                    const params = new URLSearchParams({
                        latitude: String(lat),
                        longitude: String(lon),
                        daily: "sunrise,sunset",
                        timezone: tzParam,
                        start_date: startDateISO,
                        end_date: endDateISO,
                    });
                    return `${base}?${params.toString()}`;
                }

                function openMeteoArchiveSunUrl(
                    lat,
                    lon,
                    startDateISO,
                    endDateISO,
                    timezone,
                ) {
                    const base =
                        "https://archive-api.open-meteo.com/v1/archive";
                    const tzParam = isIanaZone(timezone) ? timezone : "auto";
                    const params = new URLSearchParams({
                        latitude: String(lat),
                        longitude: String(lon),
                        daily: "sunrise,sunset",
                        timezone: tzParam,
                        start_date: startDateISO,
                        end_date: endDateISO,
                    });
                    return `${base}?${params.toString()}`;
                }

                function openIpWhoUrl() {
                    return "https://ipwho.is/?output=json";
                }

                function persistLocation() {
                    try {
                        localStorage.setItem(
                            "horaViewer:lastLocation",
                            JSON.stringify({
                                label: state.label,
                                lat: state.lat,
                                lon: state.lon,
                                tz: state.tz,
                            }),
                        );
                    } catch {
                        // ignore
                    }
                }

                function restoreLocation() {
                    try {
                        const raw = localStorage.getItem(
                            "horaViewer:lastLocation",
                        );
                        if (!raw) return null;
                        const data = JSON.parse(raw);
                        if (
                            !data ||
                            !Number.isFinite(data.lat) ||
                            !Number.isFinite(data.lon) ||
                            (data.lat === 0 && data.lon === 0)
                        )
                            return null;
                        return data;
                    } catch {
                        return null;
                    }
                }

                async function ensureTimezoneForCoords(lat, lon) {
                    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
                    if (isIanaZone(state.tz)) return;
                    try {
                        const reverse = await fetchJSON(
                            openMeteoReverseUrl(lat, lon),
                        );
                        const best = Array.isArray(reverse?.results)
                            ? reverse.results[0]
                            : null;
                        if (best?.timezone) state.tz = best.timezone;
                        if (!state.label && best?.name) {
                            state.label = [best.name, best.admin1, best.country]
                                .filter(Boolean)
                                .join(", ");
                        }
                    } catch {
                        // optional
                    }
                }

                async function locateByIp() {
                    const data = await fetchJSON(openIpWhoUrl());
                    if (!data || data.success === false)
                        throw new Error("IP location unavailable.");
                    const lat = Number(data.latitude);
                    const lon = Number(data.longitude);
                    if (!Number.isFinite(lat) || !Number.isFinite(lon))
                        throw new Error("IP location invalid.");
                    const tz =
                        typeof data?.timezone?.id === "string" &&
                        data.timezone.id
                            ? data.timezone.id
                            : typeof data?.timezone === "string"
                              ? data.timezone
                              : null;
                    const label = [data.city, data.region, data.country]
                        .filter(Boolean)
                        .join(", ");
                    return { lat, lon, tz, label };
                }

                function parseUrlParams() {
                    try {
                        const url = new URL(window.location.href);
                        const label = url.searchParams.get("label") || "";
                        const lat = parseNumber(url.searchParams.get("lat"));
                        const lon = parseNumber(url.searchParams.get("lon"));
                        const tz = url.searchParams.get("tz");
                        const now = url.searchParams.get("now") === "1";
                        const date = url.searchParams.get("date");
                        const time = url.searchParams.get("time");
                        return {
                            label,
                            lat,
                            lon,
                            tz: tz || null,
                            now,
                            date,
                            time,
                        };
                    } catch {
                        return null;
                    }
                }

                function updateUrl() {
                    const url = new URL(window.location.href);
                    const params = url.searchParams;
                    if (state.label) params.set("label", state.label);
                    else params.delete("label");

                    if (Number.isFinite(state.lat))
                        params.set("lat", String(state.lat));
                    else params.delete("lat");

                    if (Number.isFinite(state.lon))
                        params.set("lon", String(state.lon));
                    else params.delete("lon");

                    if (state.schedule?.tz) params.set("tz", state.schedule.tz);
                    else params.delete("tz");

                    params.set("now", el.nowMode.checked ? "1" : "0");
                    if (!el.nowMode.checked) {
                        if (el.date.value) params.set("date", el.date.value);
                        if (el.time.value) params.set("time", el.time.value);
                    } else {
                        params.delete("date");
                        params.delete("time");
                    }
                    history.replaceState(null, "", url.toString());
                }

                function updateLocationUI() {
                    const label =
                        state.label ||
                        (Number.isFinite(state.lat) &&
                        Number.isFinite(state.lon)
                            ? `${toFixedCoord(state.lat)}, ${toFixedCoord(state.lon)}`
                            : "—");
                    el.locationLabel.textContent = label;
                    el.locationMeta.textContent =
                        Number.isFinite(state.lat) && Number.isFinite(state.lon)
                            ? `${toFixedCoord(state.lat)}, ${toFixedCoord(state.lon)}`
                            : "—";
                }

                function setInputsEnabled() {
                    const nowOn = el.nowMode.checked;
                    el.date.disabled = nowOn;
                    el.time.disabled = nowOn;
                    el.date.classList.toggle("bg-slate-100", nowOn);
                    el.time.classList.toggle("bg-slate-100", nowOn);
                    if (el.whenControls)
                        el.whenControls.classList.toggle("hidden", nowOn);
                }

                function updateClock() {
                    const tz =
                        state.schedule?.tz ||
                        state.tz ||
                        Intl.DateTimeFormat().resolvedOptions().timeZone;
                    const dt = DateTime.now().setZone(tz);
                    el.tz.textContent = tz || "—";
                    el.clock.textContent = formatClock(dt);
                    el.clockDate.textContent = `${formatPrettyDate(dt)} • ${dt.toISODate()}`;
                    el.subtitle.textContent = tz
                        ? `Local time in ${tz}`
                        : "Responsive planetary hours • sunrise-based";
                }

                function stopNowTicker() {
                    if (state.nowTicker) {
                        clearInterval(state.nowTicker);
                        state.nowTicker = null;
                    }
                }

                function startNowTicker() {
                    stopNowTicker();
                    state.nowTicker = setInterval(() => {
                        updateClock();
                        if (!state.schedule) return;
                        const now = DateTime.now().setZone(state.schedule.tz);
                        if (
                            now.toMillis() >=
                                state.schedule.nextSunriseMillis ||
                            now.toMillis() < state.schedule.sunriseMillis
                        ) {
                            refreshAll({ reason: "tick-crossed-cycle" });
                            return;
                        }
                        updateCurrentUI(now);
                        if (
                            state.panchang &&
                            now.toMillis() >= state.panchang.nextChangeMillis
                        ) {
                            try {
                                state.panchang = computePanchang(
                                    now,
                                    state.schedule.tz,
                                );
                                updatePanchangUI(state.panchang);
                            } catch {
                                // ignore panchang failures during ticking
                            }
                        }
                    }, 1000);
                }

                function getLatLonFromInputs() {
                    const lat = parseNumber(el.lat.value);
                    const lon = parseNumber(el.lon.value);
                    if (!Number.isFinite(lat) || !Number.isFinite(lon))
                        throw new Error(
                            "Enter a city (Search) or valid coordinates.",
                        );
                    state.lat = lat;
                    state.lon = lon;
                    return { lat, lon };
                }

                function requireDateTimeInputs() {
                    const dateISO = el.date.value;
                    const timeStr = el.time.value;
                    if (!dateISO) throw new Error("Pick a date.");
                    if (!timeStr) throw new Error("Pick a time.");
                    return { dateISO, timeStr };
                }

                function setDateTimeInputsForZone(zone) {
                    const now = DateTime.now().setZone(zone);
                    el.date.value = now.toISODate();
                    el.time.value = now.toFormat("HH:mm");
                }

                function formatMonthLabel(dt) {
                    return dt.toFormat("LLLL yyyy");
                }

                function getStartOfMonthGrid(monthStart) {
                    // monthStart is at startOf('month') in tz
                    // Calendar grid starts on Sunday (weekday 7 in Luxon = Sunday)
                    const weekday = monthStart.weekday; // 1..7 (Mon..Sun)
                    const daysBack = weekday % 7; // Sun=0, Mon=1, ... Sat=6
                    return monthStart.minus({ days: daysBack });
                }

                function getMiddayMomentForISO(iso, zone) {
                    // Use midday to avoid DST edge cases and get stable tithi for that civil day.
                    return DateTime.fromISO(iso, { zone }).set({
                        hour: 12,
                        minute: 0,
                        second: 0,
                        millisecond: 0,
                    });
                }

                async function fetchSunRange(
                    lat,
                    lon,
                    startDateISO,
                    endDateISO,
                    timezone,
                ) {
                    const tzKey = timezone || "auto";
                    const key = `${lat.toFixed(4)}|${lon.toFixed(4)}|${tzKey}|${startDateISO}|${endDateISO}`;
                    if (state.sunCache.has(key)) return state.sunCache.get(key);

                    const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
                    if (
                        !ISO_DATE_RE.test(startDateISO) ||
                        !ISO_DATE_RE.test(endDateISO)
                    ) {
                        throw new Error("Invalid date range for sunrise data.");
                    }

                    const start = DateTime.fromISO(startDateISO, {
                        zone: "UTC",
                    }).startOf("day");
                    const end = DateTime.fromISO(endDateISO, {
                        zone: "UTC",
                    }).startOf("day");
                    if (!start.isValid || !end.isValid || start > end) {
                        throw new Error("Invalid date range for sunrise data.");
                    }

                    const todayISO = DateTime.now().setZone("UTC").toISODate();

                    async function fetchRangeOnce(
                        source,
                        rangeStartISO,
                        rangeEndISO,
                    ) {
                        const url =
                            source === "archive"
                                ? openMeteoArchiveSunUrl(
                                      lat,
                                      lon,
                                      rangeStartISO,
                                      rangeEndISO,
                                      timezone,
                                  )
                                : openMeteoForecastSunUrl(
                                      lat,
                                      lon,
                                      rangeStartISO,
                                      rangeEndISO,
                                      timezone,
                                  );
                        const data = await fetchJSON(url);
                        if (
                            !data?.daily?.time ||
                            !data?.daily?.sunrise ||
                            !data?.daily?.sunset
                        ) {
                            throw new Error(
                                "Sunrise/sunset data not available.",
                            );
                        }
                        return {
                            timezone: data.timezone,
                            utcOffsetSeconds: data.utc_offset_seconds,
                            timezoneAbbreviation: data.timezone_abbreviation,
                            times: data.daily.time,
                            sunrise: data.daily.sunrise,
                            sunset: data.daily.sunset,
                        };
                    }

                    async function fetchRangeWithFallback(
                        rangeStartISO,
                        rangeEndISO,
                    ) {
                        const preferArchiveFirst = rangeEndISO < todayISO;
                        const first = preferArchiveFirst
                            ? "archive"
                            : "forecast";
                        const second =
                            first === "archive" ? "forecast" : "archive";
                        try {
                            return await fetchRangeOnce(
                                first,
                                rangeStartISO,
                                rangeEndISO,
                            );
                        } catch (err) {
                            const status = err?.status;
                            const isBadRequest =
                                status === 400 || status === 404;
                            if (!isBadRequest) throw err;
                            return await fetchRangeOnce(
                                second,
                                rangeStartISO,
                                rangeEndISO,
                            );
                        }
                    }

                    // Defensive chunking to avoid API range limits.
                    const MAX_DAYS_PER_REQUEST = 31;
                    let cursor = start;
                    const merged = {
                        timezone: null,
                        utcOffsetSeconds: null,
                        timezoneAbbreviation: null,
                        times: [],
                        sunrise: [],
                        sunset: [],
                    };

                    while (cursor <= end) {
                        const chunkStart = cursor;
                        const candidateEnd = chunkStart.plus({
                            days: MAX_DAYS_PER_REQUEST - 1,
                        });
                        const chunkEnd =
                            candidateEnd > end ? end : candidateEnd;
                        const chunkStartISO = chunkStart.toISODate();
                        const chunkEndISO = chunkEnd.toISODate();
                        const part = await fetchRangeWithFallback(
                            chunkStartISO,
                            chunkEndISO,
                        );
                        if (merged.timezone == null)
                            merged.timezone = part.timezone;
                        if (merged.utcOffsetSeconds == null)
                            merged.utcOffsetSeconds = part.utcOffsetSeconds;
                        if (merged.timezoneAbbreviation == null)
                            merged.timezoneAbbreviation =
                                part.timezoneAbbreviation;
                        merged.times.push(...part.times);
                        merged.sunrise.push(...part.sunrise);
                        merged.sunset.push(...part.sunset);
                        cursor = chunkEnd.plus({ days: 1 });
                    }

                    state.sunCache.set(key, merged);
                    return merged;
                }

                async function fetchSunWindow(
                    lat,
                    lon,
                    centerDateISO,
                    timezone,
                ) {
                    const startDateISO = nextISODate(centerDateISO, -1);
                    const endDateISO = nextISODate(centerDateISO, 1);
                    return fetchSunRange(
                        lat,
                        lon,
                        startDateISO,
                        endDateISO,
                        timezone,
                    );
                }

                function findByDate(listDates, listValues, dateISO) {
                    const idx = listDates.indexOf(dateISO);
                    if (idx < 0) return null;
                    return listValues[idx] ?? null;
                }

                function getEffectiveZone(...candidates) {
                    for (const z of candidates) {
                        if (isIanaZone(z)) return z;
                    }
                    for (const z of candidates) {
                        if (typeof z === "string" && z) return z;
                    }
                    return (
                        Intl.DateTimeFormat().resolvedOptions().timeZone ||
                        "UTC"
                    );
                }

                function computeSchedule({ windowData, moment }) {
                    const tz = getEffectiveZone(state.tz, windowData?.timezone);
                    if (!tz)
                        throw new Error(
                            "Timezone unavailable for this location.",
                        );

                    const dateISO = moment.toISODate();
                    const prevISO = nextISODate(dateISO, -1);
                    const nextISO = nextISODate(dateISO, 1);

                    const sunrisePrevISO = findByDate(
                        windowData.times,
                        windowData.sunrise,
                        prevISO,
                    );
                    const sunsetPrevISO = findByDate(
                        windowData.times,
                        windowData.sunset,
                        prevISO,
                    );
                    const sunriseTodayISO = findByDate(
                        windowData.times,
                        windowData.sunrise,
                        dateISO,
                    );
                    const sunsetTodayISO = findByDate(
                        windowData.times,
                        windowData.sunset,
                        dateISO,
                    );
                    const sunriseNextISO = findByDate(
                        windowData.times,
                        windowData.sunrise,
                        nextISO,
                    );

                    if (!sunriseTodayISO || !sunsetTodayISO)
                        throw new Error(
                            "Sunrise/sunset missing for that date.",
                        );
                    if (!sunrisePrevISO || !sunsetPrevISO)
                        throw new Error(
                            "Sunrise/sunset missing for the previous date.",
                        );
                    if (!sunriseNextISO)
                        throw new Error(
                            "Next sunrise missing for the next date.",
                        );

                    const sunriseToday = DateTime.fromISO(sunriseTodayISO, {
                        zone: tz,
                    });
                    const sunsetToday = DateTime.fromISO(sunsetTodayISO, {
                        zone: tz,
                    });
                    const sunrisePrev = DateTime.fromISO(sunrisePrevISO, {
                        zone: tz,
                    });
                    const sunsetPrev = DateTime.fromISO(sunsetPrevISO, {
                        zone: tz,
                    });
                    const sunriseNext = DateTime.fromISO(sunriseNextISO, {
                        zone: tz,
                    });

                    if (
                        !sunriseToday.isValid ||
                        !sunsetToday.isValid ||
                        !sunrisePrev.isValid ||
                        !sunsetPrev.isValid ||
                        !sunriseNext.isValid
                    ) {
                        throw new Error("Invalid sunrise/sunset timestamps.");
                    }

                    const momentMillis = moment.toMillis();
                    const usePrevCycle = momentMillis < sunriseToday.toMillis();

                    if (usePrevCycle) {
                        return {
                            tz,
                            sunriseDayISO: prevISO,
                            sunriseMillis: sunrisePrev.toMillis(),
                            sunsetMillis: sunsetPrev.toMillis(),
                            nextSunriseMillis: sunriseToday.toMillis(),
                            shownSunrise: sunrisePrev,
                            shownSunset: sunsetPrev,
                            shownNextSunrise: sunriseToday,
                        };
                    }

                    return {
                        tz,
                        sunriseDayISO: dateISO,
                        sunriseMillis: sunriseToday.toMillis(),
                        sunsetMillis: sunsetToday.toMillis(),
                        nextSunriseMillis: sunriseNext.toMillis(),
                        shownSunrise: sunriseToday,
                        shownSunset: sunsetToday,
                        shownNextSunrise: sunriseNext,
                    };
                }

                function computeHoras(schedule) {
                    const dayMs =
                        schedule.sunsetMillis - schedule.sunriseMillis;
                    const nightMs =
                        schedule.nextSunriseMillis - schedule.sunsetMillis;
                    if (!(dayMs > 0) || !(nightMs > 0))
                        throw new Error(
                            "Invalid day/night duration for this date/location.",
                        );

                    const dayHoraMs = dayMs / 12;
                    const nightHoraMs = nightMs / 12;

                    const sunriseDay = DateTime.fromMillis(
                        schedule.sunriseMillis,
                        { zone: schedule.tz },
                    );
                    const weekday = sunriseDay.weekday % 7;
                    const startPlanetIndex = dayToPlanet[weekday];

                    const dayBounds = Array.from({ length: 13 }, (_, i) =>
                        i === 12
                            ? schedule.sunsetMillis
                            : schedule.sunriseMillis + dayHoraMs * i,
                    );
                    const nightBounds = Array.from({ length: 13 }, (_, i) =>
                        i === 12
                            ? schedule.nextSunriseMillis
                            : schedule.sunsetMillis + nightHoraMs * i,
                    );

                    const horas = [];
                    for (let i = 0; i < 24; i++) {
                        const isDay = i < 12;
                        const bounds = isDay ? dayBounds : nightBounds;
                        const localIndex = isDay ? i : i - 12;
                        const startMillis = bounds[localIndex];
                        const endMillis = bounds[localIndex + 1];
                        const planetIndex = (startPlanetIndex + i) % 7;
                        const planet = planets[planetIndex];

                        const subCount = 7;
                        const horaMs = endMillis - startMillis;
                        const subMs = horaMs / subCount;
                        const subHoras = Array.from(
                            { length: subCount },
                            (_, j) => {
                                const subStart = startMillis + subMs * j;
                                const subEnd =
                                    j === subCount - 1
                                        ? endMillis
                                        : startMillis + subMs * (j + 1);
                                const subPlanet =
                                    planets[(planetIndex + j) % 7];
                                return {
                                    planet: subPlanet,
                                    startMillis: subStart,
                                    endMillis: subEnd,
                                    subIndex: j + 1,
                                };
                            },
                        );

                        horas.push({
                            index: i + 1,
                            type: isDay ? "Day" : "Night",
                            planet,
                            startMillis,
                            endMillis,
                            planetIndex,
                            subHoras,
                        });
                    }
                    return horas;
                }

                function updateSunUI(schedule, moment) {
                    el.sunrise.textContent = formatTime(schedule.shownSunrise);
                    el.sunset.textContent = formatTime(schedule.shownSunset);
                    el.nextSunrise.textContent = formatTime(
                        schedule.shownNextSunrise,
                    );
                    const momentDate = moment.toISODate();
                    el.sunNote.textContent =
                        schedule.sunriseDayISO !== momentDate
                            ? `Selected moment is before sunrise; using sunrise cycle starting ${schedule.sunriseDayISO}.`
                            : `Sunrise cycle date: ${schedule.sunriseDayISO}.`;
                }

                function findCurrent(moment) {
                    const nowMillis = moment.toMillis();
                    for (const h of state.horas) {
                        if (
                            !(
                                nowMillis >= h.startMillis &&
                                nowMillis < h.endMillis
                            )
                        )
                            continue;
                        let currentSub = null;
                        for (const s of h.subHoras) {
                            if (
                                nowMillis >= s.startMillis &&
                                nowMillis < s.endMillis
                            ) {
                                currentSub = s;
                                break;
                            }
                        }
                        return { hora: h, sub: currentSub };
                    }
                    return { hora: null, sub: null };
                }

                function renderHoras(schedule, moment) {
                    const nowMillis = moment.toMillis();
                    el.horaGrid.innerHTML = state.horas
                        .map((h) => {
                            const isCurrent =
                                nowMillis >= h.startMillis &&
                                nowMillis < h.endMillis;
                            const start = DateTime.fromMillis(
                                Math.round(h.startMillis),
                                { zone: schedule.tz },
                            );
                            const end = DateTime.fromMillis(
                                Math.round(h.endMillis),
                                { zone: schedule.tz },
                            );
                            const planetClass =
                                planetColors[h.planet] || "bg-white";
                            const ring = isCurrent
                                ? "ring-2 ring-indigo-500"
                                : "ring-1 ring-slate-200";
                            const badge = isCurrent
                                ? `<span class="rounded-full bg-indigo-600 px-2 py-0.5 text-[11px] font-semibold text-white">CURRENT</span>`
                                : "";

                            const subList = h.subHoras
                                .map((s) => {
                                    const isSub =
                                        isCurrent &&
                                        nowMillis >= s.startMillis &&
                                        nowMillis < s.endMillis;
                                    const subStart = DateTime.fromMillis(
                                        Math.round(s.startMillis),
                                        { zone: schedule.tz },
                                    );
                                    const subEnd = DateTime.fromMillis(
                                        Math.round(s.endMillis),
                                        { zone: schedule.tz },
                                    );
                                    const rowClass = isSub
                                        ? "bg-indigo-100 font-semibold"
                                        : "bg-white/60";
                                    return `
                    <li data-hora="${h.index}" data-sub="${s.subIndex}" class="flex items-center justify-between gap-3 rounded-lg px-3 py-2 ${rowClass}">
                      <span class="text-slate-800">${escapeHtml(s.planet)}</span>
                      <span class="tabular-nums text-slate-600">${escapeHtml(formatTime(subStart))}–${escapeHtml(formatTime(subEnd))}</span>
                    </li>
                  `;
                                })
                                .join("");

                            return `
                <div id="hora-${h.index}" data-hora="${h.index}" class="${ring} overflow-hidden rounded-2xl shadow-sm ${planetClass}">
                  <details ${isCurrent ? "open" : ""} class="group">
                    <summary class="flex cursor-pointer list-none items-start justify-between gap-3 p-4">
                      <div class="min-w-0">
                        <div class="flex items-center gap-2">
                          <div class="text-xl font-extrabold text-slate-900">${h.index}</div>
                          ${badge}
                        </div>
                        <div class="mt-0.5 truncate text-base font-bold text-slate-900">${escapeHtml(h.planet)}</div>
                        <div class="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-700">${escapeHtml(h.type)} hora</div>
                      </div>
                      <div class="shrink-0 text-right">
                        <div class="text-sm font-extrabold tabular-nums text-slate-900">${escapeHtml(formatTime(start))}–${escapeHtml(
                            formatTime(end),
                        )}</div>
                        <div class="mt-1 text-xs text-slate-600 group-open:hidden">Sub‑horas</div>
                        <div class="mt-1 hidden text-xs text-slate-600 group-open:block">Hide</div>
                      </div>
                    </summary>
                    <div class="border-t border-white/40 px-4 pb-4">
                      <div class="pt-3 text-xs font-semibold uppercase tracking-wide text-slate-600">Sub‑horas (7)</div>
                      <ul class="mt-2 space-y-2">${subList}</ul>
                    </div>
                  </details>
                </div>
              `;
                        })
                        .join("");

                    el.horaGrid.querySelectorAll('details').forEach((details, idx) => {
                        details.addEventListener('toggle', (e) => {
                            if (details.open) {
                                const cols = window.innerWidth >= 1024 ? 3 : window.innerWidth >= 640 ? 2 : 1;
                                const rowStart = Math.floor(idx / cols) * cols;
                                const rowEnd = rowStart + cols;
                                el.horaGrid.querySelectorAll('details').forEach((d, i) => {
                                    if (i >= rowStart && i < rowEnd) d.open = true;
                                });
                            }
                        });
                    });
                }

                function updateCurrentUI(moment) {
                    if (!state.schedule || !state.horas.length) return;
                    const { hora, sub } = findCurrent(moment);
                    const tz = state.schedule.tz;
                    const nowMillis = moment.toMillis();

                    if (!hora) {
                        el.currentHora.textContent = "No current hora.";
                        el.currentSub.textContent = "";
                        el.currentRange.textContent = "";
                        el.currentCountdown.textContent = "—";
                        el.bottomHora.textContent = "No current hora";
                        el.bottomSub.textContent = "";
                        el.bottomCountdown.textContent = "";
                        return;
                    }

                    const start = DateTime.fromMillis(
                        Math.round(hora.startMillis),
                        { zone: tz },
                    );
                    const end = DateTime.fromMillis(
                        Math.round(hora.endMillis),
                        { zone: tz },
                    );
                    el.currentHora.textContent = `Hora ${hora.index} • ${hora.planet}`;
                    el.currentRange.textContent = `${formatTime(start)}–${formatTime(end)} • ${hora.type} hora`;
                    el.bottomHora.textContent = `Hora ${hora.index} • ${hora.planet}`;

                    let nextLabel = "Next hora in";
                    let remainingMs = Math.max(0, hora.endMillis - nowMillis);
                    let bottomSub = `${formatTime(start)}–${formatTime(end)}`;

                    if (sub) {
                        const subStart = DateTime.fromMillis(
                            Math.round(sub.startMillis),
                            { zone: tz },
                        );
                        const subEnd = DateTime.fromMillis(
                            Math.round(sub.endMillis),
                            { zone: tz },
                        );
                        el.currentSub.textContent = `Sub‑hora: ${sub.planet}`;
                        nextLabel = "Next sub in";
                        remainingMs = Math.max(0, sub.endMillis - nowMillis);
                        bottomSub = `Sub: ${sub.planet} • ${formatTime(subStart)}–${formatTime(subEnd)}`;
                    } else {
                        el.currentSub.textContent = "";
                    }

                    const countdown = formatCountdown(remainingMs);
                    el.currentCountdown.textContent = `${nextLabel} ${countdown}`;
                    el.bottomCountdown.textContent = countdown;
                    el.bottomSub.textContent = bottomSub;

                    const key = `${hora.index}-${sub ? sub.subIndex : 0}`;
                    if (key !== state.currentKey) {
                        state.currentKey = key;
                        renderHoras(state.schedule, moment);
                    }
                }

                function getMomentForUI() {
                    const tz =
                        state.schedule?.tz ||
                        state.tz ||
                        Intl.DateTimeFormat().resolvedOptions().timeZone;
                    if (el.nowMode.checked) return DateTime.now().setZone(tz);
                    const dt = DateTime.fromISO(
                        `${el.date.value}T${el.time.value}`,
                        { zone: tz },
                    );
                    return dt.isValid ? dt : DateTime.now().setZone(tz);
                }

                async function refreshAll({ reason = "manual" } = {}) {
                    try {
                        showLoading();
                        setStatus("Calculating…");
                        setInputsEnabled();

                        const { lat, lon } = getLatLonFromInputs();
                        if (!el.nowMode.checked) requireDateTimeInputs();

                        await ensureTimezoneForCoords(lat, lon);

                        const zoneForNow = getEffectiveZone(state.tz);
                        const seedDateISO = el.nowMode.checked
                            ? DateTime.now().setZone(zoneForNow).toISODate()
                            : el.date.value;
                        let windowData = await fetchSunWindow(
                            lat,
                            lon,
                            seedDateISO,
                            getEffectiveZone(state.tz),
                        );

                        let tz = getEffectiveZone(
                            state.tz,
                            windowData.timezone,
                        );
                        let moment = el.nowMode.checked
                            ? DateTime.now().setZone(tz)
                            : DateTime.fromISO(
                                  `${el.date.value}T${el.time.value}`,
                                  { zone: tz },
                              );
                        if (!moment.isValid)
                            throw new Error("Invalid date/time.");

                        if (el.nowMode.checked) setDateTimeInputsForZone(tz);

                        if (moment.toISODate() !== seedDateISO) {
                            windowData = await fetchSunWindow(
                                lat,
                                lon,
                                moment.toISODate(),
                                tz,
                            );
                            tz = getEffectiveZone(
                                state.tz,
                                windowData.timezone,
                                tz,
                            );
                            moment = DateTime.now().setZone(tz);
                            if (el.nowMode.checked)
                                setDateTimeInputsForZone(tz);
                        }

                        const schedule = computeSchedule({
                            windowData,
                            moment,
                        });
                        state.schedule = schedule;
                        state.tz = schedule.tz;

                        updateLocationUI();
                        updateClock();
                        updateSunUI(schedule, moment);

                        state.horas = computeHoras(schedule);
                        state.currentKey = "";
                        renderHoras(schedule, moment);
                        updateCurrentUI(moment);

                        try {
                            state.panchang = computePanchang(
                                moment.setZone(schedule.tz),
                                schedule.tz,
                            );
                            updatePanchangUI(state.panchang);
                        } catch {
                            state.panchang = null;
                            if (el.panchangSource)
                                el.panchangSource.textContent = "—";
                            if (el.panchangTithiSnap)
                                el.panchangTithiSnap.textContent = "—";
                            if (el.panchangTithiSnapRange)
                                el.panchangTithiSnapRange.textContent = "—";
                            if (el.panchangNakshatraSnap)
                                el.panchangNakshatraSnap.textContent = "—";
                            if (el.panchangNakshatraSnapRange)
                                el.panchangNakshatraSnapRange.textContent = "—";
                            if (el.panchangRasiSnap)
                                el.panchangRasiSnap.textContent = "—";
                            if (el.panchangRasiSnapRange)
                                el.panchangRasiSnapRange.textContent = "—";
                        }

                        persistLocation();
                        updateUrl();
                        setStatus(reason === "manual" ? "Updated." : "");
                        hideLoading();
                    } catch (err) {
                        hideLoading();
                        setStatus(
                            err?.message || "Something went wrong.",
                            "error",
                        );
                    }
                }

                function scrollToCurrent() {
                    const moment = getMomentForUI();
                    const { hora } = findCurrent(moment);
                    if (!hora) return;
                    const node = document.getElementById(`hora-${hora.index}`);
                    if (!node) return;
                    node.scrollIntoView({ behavior: "smooth", block: "start" });
                }

                function openSearch() {
                    el.searchModal.classList.remove("hidden");
                    setSearchStatus("Type at least 2 characters.");
                    el.searchResults.innerHTML = "";
                    el.cityQuery.value = "";
                    setTimeout(() => el.cityQuery.focus(), 30);
                }

                function closeSearch() {
                    el.searchModal.classList.add("hidden");
                    if (state.search.abort) state.search.abort.abort();
                    state.search.results = [];
                    setSearchStatus("");
                }

                function renderSearchResults(results) {
                    state.search.results = results;
                    if (!results.length) {
                        el.searchResults.innerHTML = "";
                        setSearchStatus("No results.");
                        return;
                    }

                    el.searchResults.innerHTML = results
                        .map((r, idx) => {
                            const title = [r.name, r.admin1, r.country]
                                .filter(Boolean)
                                .join(", ");
                            const tz = r.timezone || "—";
                            const time = r.timezone
                                ? DateTime.now()
                                      .setZone(r.timezone)
                                      .toFormat("HH:mm")
                                : "—";
                            return `
                <button type="button" data-idx="${idx}" class="w-full px-4 py-3 text-left hover:bg-slate-50 focus:bg-slate-50 focus:outline-none sm:px-6">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="truncate text-sm font-semibold text-slate-900">${escapeHtml(title)}</div>
                      <div class="mt-1 truncate text-xs text-slate-500">${escapeHtml(toFixedCoord(r.latitude))}, ${escapeHtml(
                          toFixedCoord(r.longitude),
                      )} • ${escapeHtml(tz)}</div>
                    </div>
                    <div class="shrink-0 text-sm font-extrabold tabular-nums text-indigo-700">${escapeHtml(time)}</div>
                  </div>
                </button>
              `;
                        })
                        .join("");
                    setSearchStatus("");
                }

                async function searchCities(query) {
                    const q = query.trim();
                    if (q.length < 2) {
                        state.search.results = [];
                        el.searchResults.innerHTML = "";
                        setSearchStatus("Type at least 2 characters.");
                        return;
                    }

                    if (state.search.abort) state.search.abort.abort();
                    const controller = new AbortController();
                    state.search.abort = controller;

                    try {
                        setSearchStatus("Searching…");
                        const data = await fetchJSON(openMeteoSearchUrl(q), {
                            signal: controller.signal,
                        });
                        const results = Array.isArray(data.results)
                            ? data.results
                            : [];
                        renderSearchResults(results);
                    } catch (err) {
                        if (err?.name === "AbortError") return;
                        setSearchStatus("Search failed. Try again.", "error");
                    }
                }

                function debounceSearch(value) {
                    if (state.search.timer) clearTimeout(state.search.timer);
                    state.search.timer = setTimeout(
                        () => searchCities(value),
                        250,
                    );
                }

                function selectSearchResult(result) {
                    state.label = [result.name, result.admin1, result.country]
                        .filter(Boolean)
                        .join(", ");
                    state.lat = Number(result.latitude);
                    state.lon = Number(result.longitude);
                    state.tz = result.timezone || null;
                    state.tzSource = "search";

                    el.lat.value = toFixedCoord(state.lat);
                    el.lon.value = toFixedCoord(state.lon);

                    updateLocationUI();
                    persistLocation();
                    closeSearch();
                    refreshAll({ reason: "city-selected" });
                }

                async function useMyLocation({
                    auto = false,
                    refresh = true,
                } = {}) {
                    if (!navigator.geolocation) {
                        setStatus("Geolocation not supported.", "error");
                        return false;
                    }
                    showLoading();
                    setStatus(auto ? "Detecting location…" : "Requesting GPS…");

                    const getPosition = () =>
                        new Promise((resolve, reject) => {
                            navigator.geolocation.getCurrentPosition(
                                resolve,
                                reject,
                                {
                                    enableHighAccuracy: true,
                                    timeout: 10000,
                                    maximumAge: 60_000,
                                },
                            );
                        });

                    try {
                        const pos = await getPosition();
                        state.lat = pos.coords.latitude;
                        state.lon = pos.coords.longitude;
                        state.tz = null;
                        state.tzSource = "gps";

                        el.lat.value = toFixedCoord(state.lat);
                        el.lon.value = toFixedCoord(state.lon);

                        try {
                            const reverse = await fetchJSON(
                                openMeteoReverseUrl(state.lat, state.lon),
                            );
                            const best = Array.isArray(reverse?.results)
                                ? reverse.results[0]
                                : null;
                            if (best?.name)
                                state.label = [
                                    best.name,
                                    best.admin1,
                                    best.country,
                                ]
                                    .filter(Boolean)
                                    .join(", ");
                            if (best?.timezone) state.tz = best.timezone;
                        } catch {
                            // optional
                        }

                        updateLocationUI();
                        if (refresh) {
                            await refreshAll({
                                reason: auto ? "auto-gps" : "geolocation",
                            });
                        } else {
                            hideLoading();
                        }
                        return true;
                    } catch {
                        hideLoading();
                        setStatus(
                            "Location permission blocked. Falling back to IP location…",
                            "error",
                        );
                        return false;
                    }
                }

                async function copyShareLink() {
                    updateUrl();
                    try {
                        await navigator.clipboard.writeText(
                            window.location.href,
                        );
                        setStatus("Share link copied.", "success");
                        setTimeout(() => setStatus(""), 1200);
                    } catch {
                        setStatus("Could not copy link.", "error");
                    }
                }

                function clearAll() {
                    state.label = "";
                    state.lat = null;
                    state.lon = null;
                    state.tz = null;
                    state.schedule = null;
                    state.horas = [];
                    state.currentKey = "";

                    el.lat.value = "";
                    el.lon.value = "";
                    el.horaGrid.innerHTML = "";

                    el.locationLabel.textContent = "—";
                    el.locationMeta.textContent = "—";
                    el.tz.textContent = "—";
                    el.sunrise.textContent = "—";
                    el.sunset.textContent = "—";
                    el.nextSunrise.textContent = "—";
                    el.sunNote.textContent = "";
                    if (el.panchangSource) el.panchangSource.textContent = "—";
                    if (el.panchangTithiSnap)
                        el.panchangTithiSnap.textContent = "—";
                    if (el.panchangTithiSnapRange)
                        el.panchangTithiSnapRange.textContent = "—";
                    if (el.panchangNakshatraSnap)
                        el.panchangNakshatraSnap.textContent = "—";
                    if (el.panchangNakshatraSnapRange)
                        el.panchangNakshatraSnapRange.textContent = "—";
                    if (el.panchangRasiSnap)
                        el.panchangRasiSnap.textContent = "—";
                    if (el.panchangRasiSnapRange)
                        el.panchangRasiSnapRange.textContent = "—";

                    el.currentHora.textContent = "—";
                    el.currentSub.textContent = "—";
                    el.currentRange.textContent = "—";
                    el.currentCountdown.textContent = "—";
                    el.bottomHora.textContent = "—";
                    el.bottomSub.textContent = "—";
                    el.bottomCountdown.textContent = "—";

                    setStatus("Cleared.");
                    updateUrl();
                }

                function wireEvents() {
                    el.btnSearch.addEventListener("click", openSearch);
                    el.btnCloseSearch.addEventListener("click", closeSearch);
                    el.searchModal.addEventListener("click", (e) => {
                        if (e.target === el.searchModal) closeSearch();
                    });
                    el.cityQuery.addEventListener("input", (e) =>
                        debounceSearch(e.target.value),
                    );
                    el.cityQuery.addEventListener("keydown", (e) => {
                        if (e.key === "Escape") closeSearch();
                    });
                    el.searchResults.addEventListener("click", (e) => {
                        const btn = e.target.closest("button[data-idx]");
                        if (!btn) return;
                        const idx = Number(btn.getAttribute("data-idx"));
                        const item = state.search.results[idx];
                        if (item) selectSearchResult(item);
                    });

                    el.btnUseLocation.addEventListener("click", () =>
                        useMyLocation(),
                    );
                    el.btnShare.addEventListener("click", copyShareLink);
                    el.btnUpdate.addEventListener("click", () =>
                        refreshAll({ reason: "manual" }),
                    );
                    el.btnRecalc.addEventListener("click", () =>
                        refreshAll({ reason: "manual" }),
                    );
                    el.btnClear.addEventListener("click", clearAll);
                    el.btnJumpCurrent.addEventListener(
                        "click",
                        scrollToCurrent,
                    );
                    el.btnBottomJump.addEventListener("click", scrollToCurrent);

                    const viewISOInMain = (iso, { defaultTime } = {}) => {
                        if (!iso) return;
                        const wasNow = el.nowMode.checked;
                        const zone = getEffectiveZone(
                            state.schedule?.tz,
                            state.tz,
                            Intl.DateTimeFormat().resolvedOptions().timeZone,
                            "UTC",
                        );
                        if (wasNow) {
                            el.nowMode.checked = false;
                            stopNowTicker();
                        }
                        setInputsEnabled();
                        el.date.value = iso;
                        if (!el.time.value || defaultTime || wasNow) {
                            el.time.value =
                                defaultTime ||
                                DateTime.now().setZone(zone).toFormat("HH:mm");
                        }
                        refreshAll({ reason: "manual" });
                    };

                    if (el.btnDatePrev) {
                        el.btnDatePrev.addEventListener("click", () => {
                            const zone = getEffectiveZone(
                                state.schedule?.tz,
                                state.tz,
                                Intl.DateTimeFormat().resolvedOptions()
                                    .timeZone,
                                "UTC",
                            );
                            const baseISO =
                                el.date.value ||
                                DateTime.now().setZone(zone).toISODate();
                            viewISOInMain(nextISODate(baseISO, -1));
                        });
                    }
                    if (el.btnDateNext) {
                        el.btnDateNext.addEventListener("click", () => {
                            const zone = getEffectiveZone(
                                state.schedule?.tz,
                                state.tz,
                                Intl.DateTimeFormat().resolvedOptions()
                                    .timeZone,
                                "UTC",
                            );
                            const baseISO =
                                el.date.value ||
                                DateTime.now().setZone(zone).toISODate();
                            viewISOInMain(nextISODate(baseISO, 1));
                        });
                    }
                    el.nowMode.addEventListener("change", () => {
                        setInputsEnabled();
                        if (el.nowMode.checked) startNowTicker();
                        else stopNowTicker();
                        refreshAll({ reason: "now-toggled" });
                    });
                    el.date.addEventListener("change", () => {
                        refreshAll({ reason: "date-changed" });
                    });
                    el.time.addEventListener("change", () =>
                        refreshAll({ reason: "time-changed" }),
                    );
                    el.lat.addEventListener("change", () => {
                        state.label = "";
                        state.tz = null;
                        state.tzSource = "manual";
                        refreshAll({ reason: "coords-changed" });
                    });
                    el.lon.addEventListener("change", () => {
                        state.label = "";
                        state.tz = null;
                        state.tzSource = "manual";
                        refreshAll({ reason: "coords-changed" });
                    });
                }

                async function init() {
                    wireEvents();
                    updateClock();

                    const params = parseUrlParams();
                    if (params?.now) el.nowMode.checked = true;
                    if (params?.date) el.date.value = params.date;
                    if (params?.time) el.time.value = params.time;
                    if (params?.label) state.label = params.label;
                    const defaultZone =
                        Intl.DateTimeFormat().resolvedOptions().timeZone ||
                        "UTC";
                    if (!el.date.value || !el.time.value)
                        setDateTimeInputsForZone(defaultZone);
                    setInputsEnabled();

                    const hasUrlLocation =
                        Number.isFinite(params?.lat) &&
                        Number.isFinite(params?.lon) &&
                        !(params.lat === 0 && params.lon === 0);
                    if (hasUrlLocation) {
                        state.lat = params.lat;
                        state.lon = params.lon;
                        state.tz = params?.tz || null;
                        state.tzSource = "url";
                    } else {
                        // If you don't have a location selected, auto-detect current location:
                        // GPS first (may prompt), then IP-based fallback; if both fail, use last saved.
                        setStatus("Detecting location…");
                        const didGps = await useMyLocation({
                            auto: true,
                            refresh: false,
                        });
                        if (!didGps) {
                            try {
                                showLoading();
                                setStatus("Getting location from IP…");
                                const ip = await locateByIp();
                                state.lat = ip.lat;
                                state.lon = ip.lon;
                                state.label = ip.label || "";
                                state.tz = ip.tz || null;
                                state.tzSource = "ip";
                                hideLoading();
                            } catch {
                                hideLoading();
                                const restored = restoreLocation();
                                if (restored) {
                                    state.label = restored.label || "";
                                    state.lat = restored.lat;
                                    state.lon = restored.lon;
                                    state.tz = restored.tz || null;
                                    state.tzSource = "stored";
                                }
                            }
                        }
                    }

                    if (
                        Number.isFinite(state.lat) &&
                        Number.isFinite(state.lon)
                    ) {
                        el.lat.value = toFixedCoord(state.lat);
                        el.lon.value = toFixedCoord(state.lon);
                    }

                    updateLocationUI();

                    if (el.nowMode.checked) startNowTicker();

                    if (
                        Number.isFinite(state.lat) &&
                        Number.isFinite(state.lon)
                    ) {
                        await refreshAll({ reason: "init" });
                    } else {
                        setStatus(
                            "Tip: click “Search city” or “Use GPS” to begin.",
                        );
                    }
                }

                init();
            })();
