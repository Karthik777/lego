'''Sun and moon positions, and sunrise/sunset, in pure Python.

Everything the panchanga needs is the apparent geocentric ecliptic longitude of the sun and
the moon at an instant, plus the times the sun crosses the horizon. Swiss Ephemeris does
this better and is a licence problem; skyfield does it better and wants a 17MB kernel it
downloads at import. Neither is worth it here: the series below are Meeus' truncations of
VSOP87 (sun, 0.01deg) and ELP2000-82 (moon, ~10 arcsec), which put every tithi boundary
inside a minute of a printed panchangam. No dependencies, no data files, no network.

Angles are degrees, times are Julian Day in TT unless a name says otherwise.'''

from math import radians as rad, degrees as deg, sin, cos, tan, asin, acos, atan2, floor, fmod

__all__ = ['J2000', 'jd_from_dt', 'dt_from_jd', 'sun_long', 'moon_long', 'moon_lat', 'ayanamsa',
           'obliquity', 'nutation_long', 'norm360', 'sun_alt', 'moon_alt', 'solar_noon',
           'sun_events', 'moon_events', 'planet_longs', 'delta_t', 'brent_root']

J2000 = 2451545.0

def norm360(x): return x % 360.0

def _cycles(t, *c):
    'Polynomial in Julian centuries, normalised to a circle.'
    return norm360(sum(k*t**i for i,k in enumerate(c)))

# === time ===

def jd_from_dt(dt):
    'Julian Day from a naive/aware UTC datetime.'
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond/1e6)/60)/60)/24
    if m <= 2: y, m = y-1, m+12
    a = floor(y/100); b = 2 - a + floor(a/4)
    return floor(365.25*(y+4716)) + floor(30.6001*(m+1)) + d + b - 1524.5

def dt_from_jd(jd):
    'Naive UTC datetime from a Julian Day.'
    from datetime import datetime, timedelta, timezone
    z = floor(jd + 0.5); f = jd + 0.5 - z
    a = z if z < 2299161 else z + 1 + (al := floor((z-1867216.25)/36524.25)) - floor(al/4)
    b = a + 1524; c = floor((b-122.1)/365.25); d = floor(365.25*c); e = floor((b-d)/30.6001)
    day = b - d - floor(30.6001*e) + f
    mth = e - 1 if e < 14 else e - 13
    yr  = c - 4716 if mth > 2 else c - 4715
    di  = int(day)
    return datetime(yr, mth, di, tzinfo=timezone.utc) + timedelta(days=day-di)

def delta_t(jd):
    '''TT - UT1 in seconds (Espenak/Meeus polynomials, 1986-2150 branch).

    Sunrise is wanted in civil time, and the series are in TT. Ignoring this puts sunrise
    over a minute out and drags every hora boundary with it.'''
    y = 2000 + (jd - J2000)/365.25
    if y < 1986:  t = y - 1900; return -2.79 + 1.494119*t - 0.0598939*t**2 + 0.0061966*t**3 - 0.000197*t**4
    if y < 2005:  t = y - 2000; return 63.86 + 0.3345*t - 0.060374*t**2 + 0.0017275*t**3 + 0.000651814*t**4 + 0.00002373599*t**5
    if y < 2050:  t = y - 2000; return 62.92 + 0.32217*t + 0.005589*t**2
    if y < 2150:  return -20 + 32*((y-1820)/100)**2 - 0.5628*(2150-y)
    u = (y-1820)/100; return -20 + 32*u*u

# === obliquity and nutation ===

def nutation_long(t):
    'Nutation in longitude, degrees. Four largest terms of the IAU 1980 series (~0.5 arcsec).'
    om = _cycles(t, 125.04452, -1934.136261, 0.0020708, 1/450000)
    ls = _cycles(t, 280.4665, 36000.7698)
    lm = _cycles(t, 218.3165, 481267.8813)
    return (-17.20*sin(rad(om)) - 1.32*sin(rad(2*ls)) - 0.23*sin(rad(2*lm)) + 0.21*sin(rad(2*om)))/3600

def obliquity(jd):
    'True obliquity of the ecliptic, degrees.'
    t = (jd - J2000)/36525
    e0 = 23 + 26/60 + (21.448 - 46.8150*t - 0.00059*t**2 + 0.001813*t**3)/3600
    om = _cycles(t, 125.04452, -1934.136261)
    return e0 + (9.20*cos(rad(om)) + 0.57*cos(rad(2*_cycles(t,280.4665,36000.7698))))/3600

# === sun ===

def sun_long(jd):
    'Apparent geocentric ecliptic longitude of the sun, degrees.'
    t  = (jd - J2000)/36525
    l0 = _cycles(t, 280.46646, 36000.76983, 0.0003032)
    m  = _cycles(t, 357.52911, 35999.05029, -0.0001537)
    mr = rad(m)
    c  = ((1.914602 - 0.004817*t - 0.000014*t*t)*sin(mr)
          + (0.019993 - 0.000101*t)*sin(2*mr) + 0.000289*sin(3*mr))
    om = _cycles(t, 125.04, -1934.136)
    return norm360(l0 + c - 0.00569 - 0.00478*sin(rad(om)))

# === moon: Meeus ch.47, ELP2000-82 truncated ===
# (D, M, M', F, sin-coefficient for longitude in 1e-6 deg, cos-coefficient for distance in km)
_ML = (
    (0,0,1,0,6288774),(2,0,-1,0,1274027),(2,0,0,0,658314),(0,0,2,0,213618),
    (0,1,0,0,-185116),(0,0,0,2,-114332),(2,0,-2,0,58793),(2,-1,-1,0,57066),
    (2,0,1,0,53322),(2,-1,0,0,45758),(0,1,-1,0,-40923),(1,0,0,0,-34720),
    (0,1,1,0,-30383),(2,0,0,-2,15327),(0,0,1,2,-12528),(0,0,1,-2,10980),
    (4,0,-1,0,10675),(0,0,3,0,10034),(4,0,-2,0,8548),(2,1,-1,0,-7888),
    (2,1,0,0,-6766),(1,0,-1,0,-5163),(1,1,0,0,4987),(2,-1,1,0,4036),
    (2,0,2,0,3994),(4,0,0,0,3861),(2,0,-3,0,3665),(0,1,-2,0,-2689),
    (2,0,-1,2,-2602),(2,-1,-2,0,2390),(1,0,1,0,-2348),(2,-2,0,0,2236),
    (0,1,2,0,-2120),(0,2,0,0,-2069),(2,-2,-1,0,2048),(2,0,1,-2,-1773),
    (2,0,0,2,-1595),(4,-1,-1,0,1215),(0,0,2,2,-1110),(3,0,-1,0,-892),
    (2,1,1,0,-810),(4,-1,-2,0,759),(0,2,-1,0,-713),(2,2,-1,0,-700),
    (2,1,-2,0,691),(2,-1,0,-2,596),(4,0,1,0,549),(0,0,4,0,537),
    (4,-1,0,0,520),(1,0,-2,0,-487),(2,1,0,-2,-399),(0,0,2,-2,-381),
    (1,1,1,0,351),(3,0,-2,0,-340),(4,0,-3,0,330),(2,-1,2,0,327),
    (0,2,1,0,-323),(1,1,-1,0,299),(2,0,3,0,294),(2,0,-1,-2,0))

# (D, M, M', F, sin-coefficient for latitude in 1e-6 deg)
_MB = (
    (0,0,0,1,5128122),(0,0,1,1,280602),(0,0,1,-1,277693),(2,0,0,-1,173237),
    (2,0,-1,1,55413),(2,0,-1,-1,46271),(2,0,0,1,32573),(0,0,2,1,17198),
    (2,0,1,-1,9266),(0,0,2,-1,8822),(2,-1,0,-1,8216),(2,0,-2,-1,4324),
    (2,0,1,1,4200),(2,1,0,-1,-3359),(2,-1,-1,1,2463),(2,-1,0,1,2211),
    (2,-1,-1,-1,2065),(0,1,-1,-1,-1870),(4,0,-1,-1,1828),(0,1,0,1,-1794),
    (0,0,0,3,-1749),(0,1,-1,1,-1565),(1,0,0,1,-1491),(0,1,1,1,-1475),
    (0,1,1,-1,-1410),(0,1,0,-1,-1344),(1,0,0,-1,-1335),(0,0,3,1,1107),
    (4,0,0,-1,1021),(4,0,-1,1,833),(0,0,1,-3,777),(4,0,-2,1,671),
    (2,0,0,-3,607),(2,0,2,-1,596),(2,-1,1,-1,491),(2,0,-2,1,-451),
    (0,0,3,-1,439),(2,0,2,1,422),(2,0,-3,-1,421),(2,1,-1,1,-366),
    (2,1,0,1,-351),(4,0,0,1,331),(2,-1,1,1,315),(2,-2,0,-1,302),
    (0,0,1,3,-283),(2,1,1,-1,-229),(1,1,0,-1,223),(1,1,0,1,223),
    (0,1,-2,-1,-220),(2,1,-1,-1,-220),(1,0,1,1,-185),(2,-1,-2,-1,181),
    (0,1,2,1,-177),(4,0,-2,-1,176),(4,-1,-1,-1,166),(1,0,1,-1,-164),
    (4,0,1,-1,132),(1,0,-1,-1,-119),(4,-1,0,-1,115),(2,-2,0,1,107))

def _moon_args(jd):
    t = (jd - J2000)/36525
    lp = _cycles(t, 218.3164477, 481267.88123421, -0.0015786, 1/538841, -1/65194000)
    d  = _cycles(t, 297.8501921, 445267.1114034, -0.0018819, 1/545868, -1/113065000)
    m  = _cycles(t, 357.5291092, 35999.0502909, -0.0001536, 1/24490000)
    mp = _cycles(t, 134.9633964, 477198.8675055, 0.0087414, 1/69699, -1/14712000)
    f  = _cycles(t, 93.2720950, 483202.0175233, -0.0036539, -1/3526000, 1/863310000)
    e  = 1 - 0.002516*t - 0.0000074*t*t
    return t, lp, d, m, mp, f, e

def _sigma(table, d, m, mp, f, e):
    tot = 0.0
    for cd, cm, cmp_, cf, co in table:
        arg = rad(cd*d + cm*m + cmp_*mp + cf*f)
        tot += co * sin(arg) * (e**abs(cm) if cm else 1)
    return tot

def moon_long(jd):
    'Apparent geocentric ecliptic longitude of the moon, degrees.'
    t, lp, d, m, mp, f, e = _moon_args(jd)
    a1, a2 = _cycles(t, 119.75, 131.849), _cycles(t, 53.09, 479264.290)
    sl = _sigma(_ML, d, m, mp, f, e)
    sl += 3958*sin(rad(a1)) + 1962*sin(rad(lp-f)) + 318*sin(rad(a2))
    return norm360(lp + sl/1e6 + nutation_long(t))

def moon_lat(jd):
    'Geocentric ecliptic latitude of the moon, degrees.'
    t, lp, d, m, mp, f, e = _moon_args(jd)
    a1, a3 = _cycles(t, 119.75, 131.849), _cycles(t, 313.45, 481266.484)
    sb = _sigma(_MB, d, m, mp, f, e)
    sb += -2235*sin(rad(lp)) + 382*sin(rad(a3)) + 175*sin(rad(a1-f)) + 175*sin(rad(a1+f)) \
          + 127*sin(rad(lp-mp)) - 115*sin(rad(lp+mp))
    return sb/1e6

# === ayanamsa ===

def ayanamsa(jd):
    '''Lahiri (Chitrapaksha) ayanamsa, degrees.

    The one number that decides whether the nakshatra printed here is the nakshatra printed
    in a Tamil almanac. It is the offset between the tropical zodiac western astronomy
    measures against and the fixed-star zodiac Indian tradition measures against: 23.85 deg
    at J2000 plus the general precession in longitude accumulated since.'''
    t = (jd - J2000)/36525
    p = (5028.796195*t + 1.1054348*t**2 + 0.00007964*t**3 - 0.000023857*t**4)/3600
    return 23.853056 + p

# === horizon ===

def _equatorial(lam, beta, eps):
    lr, br, er = rad(lam), rad(beta), rad(eps)
    ra  = atan2(sin(lr)*cos(er) - tan(br)*sin(er), cos(lr))
    dec = asin(sin(br)*cos(er) + cos(br)*sin(er)*sin(lr))
    return deg(ra) % 360, deg(dec)

def _gmst(jd):
    'Greenwich mean sidereal time, degrees.'
    t = (jd - J2000)/36525
    return norm360(280.46061837 + 360.98564736629*(jd-J2000) + 0.000387933*t*t - t**3/38710000)

def _alt(ra, dec, jd, lat, lon):
    h = rad(_gmst(jd) + lon - ra)
    p, d = rad(lat), rad(dec)
    return deg(asin(sin(p)*sin(d) + cos(p)*cos(d)*cos(h)))

def sun_alt(jd, lat, lon):
    'Sun altitude in degrees. jd is UT; the series get TT.'
    jt = jd + delta_t(jd)/86400
    ra, dec = _equatorial(sun_long(jt), 0.0, obliquity(jt))
    return _alt(ra, dec, jd, lat, lon)

def moon_alt(jd, lat, lon):
    'Moon altitude in degrees, geocentric.'
    jt = jd + delta_t(jd)/86400
    ra, dec = _equatorial(moon_long(jt), moon_lat(jt), obliquity(jt))
    return _alt(ra, dec, jd, lat, lon)

def solar_noon(jd_guess, lat, lon):
    'UT Julian Day of local solar transit nearest jd_guess.'
    t = jd_guess
    for _ in range(3):
        jt = t + delta_t(t)/86400
        ra, _d = _equatorial(sun_long(jt), 0.0, obliquity(jt))
        h = (_gmst(t) + lon - ra + 180) % 360 - 180
        t -= h/360.98564736629
    return t

def brent_root(f, lo, hi, tol=1e-7):
    """Illinois-regula-falsi root of f on a bracketing interval.

    Plain bisection needs about twenty steps to reach a second of time and these functions
    are smooth, so it is twenty evaluations of a sixty-term lunar series to find one tithi
    boundary. Illinois keeps the bracket -- it cannot walk off a root the way Newton can --
    and gets there in six or seven. Returns None when [lo, hi] does not bracket a root."""
    a, b = lo, hi
    fa, fb = f(a), f(b)
    if fa == 0: return a
    if fb == 0: return b
    if (fa > 0) == (fb > 0): return None
    side = 0
    for _ in range(60):
        c = (a*fb - b*fa)/(fb - fa)
        if abs(b - a) < tol: break
        fc = f(c)
        if fc == 0: return c
        if (fc > 0) == (fb > 0):
            b, fb = c, fc
            if side == -1: fa /= 2
            side = -1
        else:
            a, fa = c, fc
            if side == 1: fb /= 2
            side = 1
    return (a*fb - b*fa)/(fb - fa)

def _cross(f, lo, hi, target):
    'Time in [lo, hi] where f reaches target; None when it does not cross there.'
    return brent_root(lambda t: f(t) - target, lo, hi)

_H0_SUN = -0.8333   # refraction plus the sun's semidiameter: upper limb on the horizon

def sun_events(jd_local_noon_guess, lat, lon, h0=_H0_SUN):
    'Dict of rise/noon/set as UT Julian Days. rise/set are None inside a polar day or night.'
    noon = solar_noon(jd_local_noon_guess, lat, lon)
    f = lambda t: sun_alt(t, lat, lon)
    return dict(rise=_cross(f, noon-0.5, noon, h0), noon=noon, set=_cross(f, noon, noon+0.5, h0))

def moon_events(jd_from, lat, lon):
    'Moonrise and moonset as UT Julian Days, searched forward 1 day in 20-minute steps.'
    f = lambda t: moon_alt(t, lat, lon) + 0.125   # mean parallax less refraction
    step, out, prev = 1/72, {}, f(jd_from)
    t = jd_from
    while t < jd_from + 1 and len(out) < 2:
        nxt = t + step; cur = f(nxt)
        k = 'rise' if prev < 0 <= cur else 'set' if prev >= 0 > cur else None
        if k and k not in out: out[k] = _cross(f, t, nxt, 0)
        prev, t = cur, nxt
    return dict(rise=out.get('rise'), set=out.get('set'))

# === planets: Meeus ch.31 VSOP87 mean elements, good to a few arcmin ===
# name: (L, a, e, i, node, peri) each as a polynomial in Julian centuries
_EL = {
 'Mercury':((252.250906,149474.0722491,0.00030350,0.000000018),0.387098310,(0.20563175,0.000020407,-0.0000000283,-0.00000000018),
            (7.004986,0.0018215,-0.00001810,0.000000056),(48.330893,1.1861883,0.00017542,0.000000215),(77.456119,1.5564776,0.00029544,0.000000009)),
 'Venus':  ((181.979801,58519.2130302,0.00031014,0.000000015),0.723329820,(0.00677192,-0.000047765,0.0000000981,0.00000000046),
            (3.394662,0.0010037,-0.00000088,-0.000000007),(76.679920,0.9011206,0.00040618,-0.000000093),(131.563703,1.4022288,-0.00107618,-0.000005678)),
 'Mars':   ((355.433000,19141.6964471,0.00031052,0.000000016),1.523679342,(0.09340065,0.000090484,-0.0000000806,-0.00000000025),
            (1.849726,-0.0006011,0.00001276,-0.000000007),(49.558093,0.7720959,0.00001557,0.000002267),(336.060234,1.8410449,0.00013477,0.000000536)),
 'Jupiter':((34.351519,3036.3027748,0.00022330,0.000000037),5.202603209,(0.04849793,0.000163225,-0.0000004714,-0.00000000201),
            (1.303267,-0.0054965,0.00000466,-0.000000002),(100.464407,1.0209774,0.00040315,0.000000404),(14.331207,1.6126352,0.00103042,-0.000004464)),
 'Saturn': ((50.077444,1223.5110686,0.00051908,-0.000000030),9.554909192,(0.05554814,-0.000346641,-0.0000006436,0.00000000340),
            (2.488879,-0.0037362,-0.00001519,0.000000087),(113.665503,0.8770880,-0.00012176,-0.000002249),(93.057237,1.9637613,0.00083753,0.000004928))}

def _kepler(m, e):
    'Eccentric anomaly, radians.'
    ex = m
    for _ in range(12):
        d = (ex - e*sin(ex) - m)/(1 - e*cos(ex))
        ex -= d
        if abs(d) < 1e-12: break
    return ex

def _heliocentric(nm, t):
    (l0,l1,l2,l3), a, ec, ic, nd, pe = _EL[nm]
    L = _cycles(t, l0, l1, l2, l3)
    e = ec[0] + ec[1]*t + ec[2]*t*t + ec[3]*t**3
    i = ic[0] + ic[1]*t + ic[2]*t*t + ic[3]*t**3
    o = _cycles(t, *nd); p = _cycles(t, *pe)
    mm = rad(L - p); w = rad(p - o)
    ex = _kepler(mm, e)
    v  = 2*atan2((1+e)**0.5*sin(ex/2), (1-e)**0.5*cos(ex/2))
    r  = a*(1 - e*cos(ex))
    u  = v + w; ir = rad(i); onr = rad(o)
    x = r*(cos(onr)*cos(u) - sin(onr)*sin(u)*cos(ir))
    y = r*(sin(onr)*cos(u) + cos(onr)*sin(u)*cos(ir))
    z = r*sin(u)*sin(ir)
    return x, y, z

def planet_longs(jd):
    '''Sidereal (Lahiri) ecliptic longitudes of the nine grahas, degrees.

    Mean orbital elements rather than the full VSOP87 series: a few arcminutes, which names
    the right rasi except within a whisker of a cusp. The five limbs never touch these --
    they are the day view's planet table, not the almanac.'''
    jt = jd + delta_t(jd)/86400
    t  = (jt - J2000)/36525
    ay = ayanamsa(jt)
    out = {'Sun': norm360(sun_long(jt) - ay), 'Moon': norm360(moon_long(jt) - ay)}
    ex, ey, _ez = _earth_xyz(t)
    for nm in _EL:
        px, py, pz = _heliocentric(nm, t)
        out[nm] = norm360(deg(atan2(py-ey, px-ex)) - ay)
    # Rahu is the moon's mean ascending node; Ketu sits opposite it.
    rahu = _cycles(t, 125.0445479, -1934.1362891, 0.0020754, 1/467441, -1/60616000)
    out['Rahu'] = norm360(rahu - ay); out['Ketu'] = norm360(rahu - ay + 180)
    return out

def _earth_xyz(t):
    'Earth heliocentric rectangular coordinates, from the sun geocentric longitude.'
    jt = J2000 + t*36525
    lam = rad(sun_long(jt) + 180)
    # Radius vector, Meeus 25.5.
    m = rad(_cycles(t, 357.52911, 35999.05029, -0.0001537))
    e = 0.016708634 - 0.000042037*t - 0.0000001267*t*t
    v = m + rad((1.914602 - 0.004817*t)*sin(m) + 0.019993*sin(2*m) + 0.000289*sin(3*m))
    r = 1.000001018*(1 - e*e)/(1 + e*cos(v))
    return r*cos(lam), r*sin(lam), 0.0
