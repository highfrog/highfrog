#!/usr/bin/env python3
"""The horned-frog mark, as SVG, in a palette chosen by the sun over Greenville.

Geometry lives in 0..1 space so the caller can scale it to any size. Colours are
driven by solar elevation, so the mark tracks real daylight rather than clock time.
"""
import json
import math
import urllib.request

# Greenville, SC
LAT, LON = 34.8526, -82.3940

# WMO weather codes → overlay. Anything unmapped falls through to "clear", so a new
# or odd code degrades to no overlay rather than breaking the render.
WMO = {
    0: ("clear", "CLEAR"),
    1: ("clear", "CLEAR"), 2: ("cloud", "PARTLY"), 3: ("cloud", "OVERCAST"),
    45: ("fog", "FOG"), 48: ("fog", "FOG"),
    51: ("rain", "DRIZZLE"), 53: ("rain", "DRIZZLE"), 55: ("rain", "DRIZZLE"),
    56: ("rain", "FRZ DRIZZLE"), 57: ("rain", "FRZ DRIZZLE"),
    61: ("rain", "RAIN"), 63: ("rain", "RAIN"), 65: ("rain", "HEAVY RAIN"),
    66: ("rain", "FRZ RAIN"), 67: ("rain", "FRZ RAIN"),
    71: ("snow", "SNOW"), 73: ("snow", "SNOW"), 75: ("snow", "HEAVY SNOW"),
    77: ("snow", "SNOW GRAINS"),
    80: ("rain", "SHOWERS"), 81: ("rain", "SHOWERS"), 82: ("rain", "HEAVY SHOWERS"),
    85: ("snow", "SNOW SHOWERS"), 86: ("snow", "SNOW SHOWERS"),
    95: ("storm", "STORM"), 96: ("storm", "STORM"), 99: ("storm", "STORM"),
}


def weather():
    """Current conditions over Greenville. Never raises — the frog renders regardless."""
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           "&current=temperature_2m,weather_code&temperature_unit=fahrenheit")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "highfrog-profile"})
        with urllib.request.urlopen(req, timeout=12) as r:
            cur = json.load(r)["current"]
        kind, label = WMO.get(int(cur["weather_code"]), ("clear", "CLEAR"))
        return {"kind": kind, "label": label, "temp": round(cur["temperature_2m"])}
    except Exception:
        return {"kind": "clear", "label": "", "temp": None}

PALETTES = {
    "dawn": dict(
        skull=("#FB7185", "#9F1239"), horn=("#FDE68A", "#F59E0B"),
        facet=("#FDA4AF", "#F472B6"), jaw="#881337",
        ring="#2A0A14", iris="#FDE047", pupil="#3F1D0B",
        mouth="#4C0519", ground=("#2A1020", "#4C1D3D"),
        label="DAWN"),
    "day": dict(
        skull=("#38BDF8", "#0E7490"), horn=("#7DD3FC", "#0284C7"),
        facet=("#BAE6FD", "#38BDF8"), jaw="#075985",
        ring="#0B1024", iris="#FACC15", pupil="#1C1207",
        mouth="#082F49", ground=("#0F172A", "#1E293B"),
        label="DAY"),
    "dusk": dict(
        skull=("#38BDF8", "#6D28D9"), horn=("#FB7185", "#BE123C"),
        facet=("#7DD3FC", "#A855F7"), jaw="#3B0764",
        ring="#0B1024", iris="#BEF264", pupil="#1A2E05",
        mouth="#180B33", ground=("#0F172A", "#291A4D"),
        label="DUSK"),
    "night": dict(
        skull=("#A855F7", "#4C1D95"), horn=("#F0ABFC", "#9333EA"),
        facet=("#38BDF8", "#7C3AED"), jaw="#3B0764",
        ring="#1A0B2E", iris="#4ADE80", pupil="#0B2E16",
        mouth="#2E1065", ground=("#140E2E", "#2A1B5E"),
        label="NIGHT"),
}

# Not part of the solar rotation: the fixed identity mark used for the avatar and
# favicon. GitHub has no API for setting an avatar, so this one is uploaded by hand.
SIGNATURE = dict(
    skull=("#4ADE80", "#065F46"), horn=("#F0ABFC", "#9333EA"),
    facet=("#86EFAC", "#22D3EE"), jaw="#064E3B",
    ring="#0B1F17", iris="#FDE047", pupil="#0B2E16",
    mouth="#052E1B", ground=("#140E2E", "#2A1B5E"),
    label="SIGNATURE")


def solar_phase(now):
    """Return (phase, elevation_degrees) for `now` (an aware UTC datetime)."""
    doy = now.timetuple().tm_yday
    hour = now.hour + now.minute / 60
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)

    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))

    tst = (now.hour * 60 + now.minute + now.second / 60) + eqtime + 4 * LON
    ha = math.radians(tst / 4 - 180)
    lat = math.radians(LAT)
    cosz = (math.sin(lat) * math.sin(decl)
            + math.cos(lat) * math.cos(decl) * math.cos(ha))
    elev = 90 - math.degrees(math.acos(max(-1.0, min(1.0, cosz))))

    rising = math.degrees(ha) < 0  # before solar noon
    if elev > 8:
        return "day", elev
    if elev > -10:
        return ("dawn" if rising else "dusk"), elev
    return "night", elev


# ------------------------------------------------------------------ geometry

SKULL = [(0.500, 0.240), (0.680, 0.265), (0.845, 0.375), (0.900, 0.520),
         (0.845, 0.680), (0.700, 0.815), (0.500, 0.865),
         (0.300, 0.815), (0.155, 0.680), (0.100, 0.520),
         (0.155, 0.375), (0.320, 0.265)]
HORNS = [[(0.300, 0.215), (0.100, 0.045), (0.200, 0.252)],
         [(0.212, 0.268), (0.010, 0.210), (0.152, 0.392)]]
SNOUT = [(0.500, 0.330), (0.640, 0.430), (0.605, 0.610), (0.500, 0.655),
         (0.395, 0.610), (0.360, 0.430)]
JAW = [(0.180, 0.660), (0.820, 0.660), (0.700, 0.815), (0.500, 0.865), (0.300, 0.815)]
GRIN = [(0.140, 0.612), (0.500, 0.700), (0.860, 0.612),
        (0.860, 0.660), (0.500, 0.752), (0.140, 0.660)]


def _ngon(cx, cy, rx, ry, n=9, rot=0.0):
    return [(cx + rx * math.cos(rot + 2 * math.pi * i / n),
             cy + ry * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def _pts(poly):
    return " ".join(f"{x:.4f},{y:.4f}" for x, y in poly)


def _mirror(poly):
    return [(1 - x, y) for x, y in poly]


# The horn tips reach 0.605 from centre, past the ground circle's 0.5 radius. On a
# rectangular card that overhang is the point; inside a circular avatar crop it gets
# sliced off, so the avatar shrinks the figure until the points fit.
INSET = 0.46 / 0.605


def overlay(kind, uid):
    """Weather drawn over the mark, clipped to the ground circle.

    Every position is deterministic — random drops would rewrite the SVG on each
    run and the Action would commit hourly with nothing actually changed.
    """
    if kind == "clear":
        return ""

    css, el = [], []
    tint = {"rain": ("#0C2340", .22), "storm": ("#0A1A33", .28),
            "cloud": ("#94A3B8", .14), "fog": ("#CBD5E1", .24),
            "snow": ("#E2E8F0", .12)}.get(kind)
    if tint:
        el.append(f'<circle cx=".5" cy=".5" r=".5" fill="{tint[0]}" opacity="{tint[1]}"/>')

    if kind in ("rain", "storm"):
        n = 22 if kind == "storm" else 18
        css.append(f".rn{uid}{{animation:fall{uid} .8s linear infinite}}"
                   f"@keyframes fall{uid}{{from{{transform:translate(0,-.34px)}}"
                   f"to{{transform:translate(.06px,.36px)}}}}")
        for i in range(n):
            px = 0.03 + ((i * 0.1379) % 0.94)
            py = 0.08 + ((i * 0.2411) % 0.72)
            el.append(f'<line x1="{px:.3f}" y1="{py:.3f}" x2="{px - .022:.3f}" '
                      f'y2="{py + .085:.3f}" stroke="#BAE6FD" stroke-width=".009" '
                      f'stroke-linecap="round" opacity=".62" class="rn{uid}" '
                      f'style="animation-delay:-{i * 0.043:.3f}s"/>')

    if kind == "storm":
        css.append(f".bolt{uid}{{animation:flash{uid} 4s steps(1,end) infinite}}"
                   f"@keyframes flash{uid}{{0%,88%{{opacity:0}}90%,93%{{opacity:.95}}"
                   f"95%{{opacity:.3}}97%,100%{{opacity:0}}}}")
        el.append(f'<polygon points="0.60,0.10 0.47,0.40 0.55,0.40 0.44,0.68 '
                  f'0.66,0.34 0.57,0.34 0.68,0.10" fill="#FDE047" '
                  f'class="bolt{uid}"/>')

    if kind == "snow":
        css.append(f".sn{uid}{{animation:drift{uid} 3.4s linear infinite}}"
                   f"@keyframes drift{uid}{{from{{transform:translate(-.03px,-.36px)}}"
                   f"to{{transform:translate(.03px,.38px)}}}}")
        for i in range(16):
            px = 0.04 + ((i * 0.1811) % 0.92)
            py = 0.06 + ((i * 0.3121) % 0.78)
            r = 0.008 + (i % 3) * 0.003
            el.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{r:.3f}" fill="#F8FAFC" '
                      f'opacity=".85" class="sn{uid}" '
                      f'style="animation-delay:-{i * 0.21:.2f}s"/>')

    if kind == "fog":
        css.append(f".fg{uid}{{animation:slide{uid} 11s ease-in-out infinite alternate}}"
                   f"@keyframes slide{uid}{{from{{transform:translateX(-.05px)}}"
                   f"to{{transform:translateX(.05px)}}}}")
        for i, (fy, op) in enumerate(((0.34, .28), (0.50, .34), (0.66, .24), (0.80, .18))):
            el.append(f'<rect x="-.1" y="{fy:.2f}" width="1.2" height="0.052" rx="0.026" '
                      f'fill="#E2E8F0" opacity="{op}" class="fg{uid}" '
                      f'style="animation-delay:-{i * 1.7:.1f}s"/>')

    if kind == "cloud":
        css.append(f".cl{uid}{{animation:roll{uid} 14s ease-in-out infinite alternate}}"
                   f"@keyframes roll{uid}{{from{{transform:translateX(-.04px)}}"
                   f"to{{transform:translateX(.04px)}}}}")
        for cx_, cy_, r in ((0.26, 0.15, 0.075), (0.36, 0.12, 0.095),
                            (0.48, 0.15, 0.070), (0.70, 0.19, 0.062)):
            el.append(f'<circle cx="{cx_}" cy="{cy_}" r="{r}" fill="#E2E8F0" '
                      f'opacity=".42" class="cl{uid}"/>')

    style = f"<style>{''.join(css)}</style>" if css else ""
    return (f'<defs><clipPath id="wc{uid}">'
            f'<circle cx=".5" cy=".5" r=".5"/></clipPath></defs>{style}'
            f'<g clip-path="url(#wc{uid})">{"".join(el)}</g>')


def mark(phase, uid, size=1.0, x=0.0, y=0.0, inset=1.0, weather_kind="clear"):
    """SVG group for the frog mark, scaled to `size` and placed at (x, y).

    `phase` is a key in PALETTES, or "signature" for the fixed identity mark.
    `inset` shrinks the figure about its centre without shrinking the ground.
    """
    p = SIGNATURE if phase == "signature" else PALETTES[phase]
    d = []   # gradient defs
    g = []   # drawn elements

    def grad(name, c0, c1, vertical=True):
        gid = f"{name}{uid}"
        x2, y2 = ("0%", "100%") if vertical else ("100%", "0%")
        d.append(f'<linearGradient id="{gid}" x1="0%" y1="0%" x2="{x2}" y2="{y2}">'
                 f'<stop offset="0%" stop-color="{c0}"/>'
                 f'<stop offset="100%" stop-color="{c1}"/></linearGradient>')
        return f"url(#{gid})"

    ground = grad("gr", p["ground"][0], p["ground"][1])
    skull = grad("sk", p["skull"][0], p["skull"][1])
    horn_l = grad("hl", p["horn"][0], p["horn"][1], vertical=False)
    horn_r = grad("hr", p["horn"][1], p["horn"][0], vertical=False)
    facet = grad("fc", p["facet"][0], p["facet"][1])
    dome = grad("dm", p["facet"][0], p["skull"][0])

    g.append(f'<circle cx=".5" cy=".5" r=".5" fill="{ground}"/>')
    for horn in HORNS:
        g.append(f'<polygon points="{_pts(horn)}" fill="{horn_l}"/>')
        g.append(f'<polygon points="{_pts(_mirror(horn))}" fill="{horn_r}"/>')
    for ex in (0.300, 0.700):
        g.append(f'<polygon points="{_pts(_ngon(ex, 0.310, 0.150, 0.140, 9, 0.3))}" '
                 f'fill="{dome}"/>')
    g.append(f'<polygon points="{_pts(SKULL)}" fill="{skull}"/>')
    g.append(f'<polygon points="{_pts(SNOUT)}" fill="{facet}" opacity=".55"/>')
    g.append(f'<polygon points="{_pts(JAW)}" fill="{p["jaw"]}" opacity=".55"/>')
    for ex in (0.300, 0.700):
        g.append(f'<polygon points="{_pts(_ngon(ex, 0.318, 0.112, 0.102, 8, 0.39))}" '
                 f'fill="{p["ring"]}"/>')
        g.append(f'<polygon points="{_pts(_ngon(ex, 0.318, 0.082, 0.074, 8, 0.39))}" '
                 f'fill="{p["iris"]}"/>')
        g.append(f'<rect x="{ex - 0.086:.4f}" y="0.300" width="0.172" height="0.038" '
                 f'fill="{p["pupil"]}" opacity=".92"/>')
    g.append(f'<polygon points="{_pts(GRIN)}" fill="{p["mouth"]}" opacity=".92"/>')
    for nx in (0.452, 0.548):
        g.append(f'<polygon points="{_pts([(nx, 0.512), (nx + 0.030, 0.520), (nx + 0.012, 0.552)])}" '
                 f'fill="{p["mouth"]}" opacity=".7"/>')

    ground_el, figure = g[0], g[1:]
    inner = "".join(figure)
    if inset != 1.0:
        inner = (f'<g transform="translate(.5 .5) scale({inset:.5f}) '
                 f'translate(-.5 -.5)">{inner}</g>')
    return (f'<defs>{"".join(d)}</defs>'
            f'<g transform="translate({x} {y}) scale({size})">'
            f'{ground_el}{inner}{overlay(weather_kind, uid)}</g>')
