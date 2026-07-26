#!/usr/bin/env python3
"""Render the profile SVG cards from live GitHub data.

Stdlib only — no pip install in the Action. Writes assets/*.svg and bumps the
?v= cache-buster in README.md so GitHub's image proxy picks up new renders.
"""

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import frogmark

USER = "highfrog"
ORG = "reedylab"
ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

W = 880

THEMES = {
    "dark": {
        "bg": "#0F172A", "surface": "#1E293B", "surface2": "#273548",
        "accent": "#38BDF8", "accent2": "#7DD3FC", "text": "#F1F5F9",
        "dim": "#94A3B8", "border": "#334155", "grid": "#1E293B",
        "good": "#4ADE80", "warn": "#FACC15",
    },
    "light": {
        "bg": "#FFFFFF", "surface": "#F8FAFC", "surface2": "#F1F5F9",
        "accent": "#0284C7", "accent2": "#0369A1", "text": "#0F172A",
        "dim": "#64748B", "border": "#CBD5E1", "grid": "#E2E8F0",
        "good": "#16A34A", "warn": "#CA8A04",
    },
}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"


# ---------------------------------------------------------------- data

def gql(query, variables):
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "highfrog-profile-render",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


QUERY = """
query($user:String!, $org:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$user) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar { totalContributions }
      totalCommitContributions
      totalPullRequestContributions
    }
    repositories(first:100, ownerAffiliations:[OWNER], privacy:PUBLIC, isFork:false) {
      nodes { name stargazerCount }
    }
  }
  organization(login:$org) {
    repositories(first:50, privacy:PUBLIC, orderBy:{field:STARGAZERS, direction:DESC}) {
      nodes {
        name description stargazerCount forkCount isArchived
        primaryLanguage { name color }
        languages(first:8, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch():
    now = datetime.now(timezone.utc)
    data = gql(QUERY, {
        "user": USER,
        "org": ORG,
        "from": now.replace(month=1, day=1, hour=0, minute=0, second=0,
                            microsecond=0).isoformat(),
        "to": now.isoformat(),
    })
    contrib = data["user"]["contributionsCollection"]
    org_repos = [r for r in data["organization"]["repositories"]["nodes"]
                 if not r["isArchived"]]
    stars = (sum(r["stargazerCount"] for r in org_repos)
             + sum(r["stargazerCount"] for r in data["user"]["repositories"]["nodes"]))

    langs = {}
    for r in org_repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            langs.setdefault(n, {"size": 0, "color": e["node"]["color"] or "#64748B"})
            langs[n]["size"] += e["size"]
    total = sum(v["size"] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1]["size"])[:5]

    phase, elev = frogmark.solar_phase(now)
    return {
        "phase": phase,
        "phase_label": frogmark.PALETTES[phase]["label"],
        "sun_elevation": round(elev, 1),
        "contributions": contrib["contributionCalendar"]["totalContributions"],
        "commits": contrib["totalCommitContributions"],
        "prs": contrib["totalPullRequestContributions"],
        "stars": stars,
        "repos": org_repos,
        "languages": [{"name": n, "pct": v["size"] / total * 100, "color": v["color"]}
                      for n, v in top],
        "year": now.year,
        "updated": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------- svg helpers

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def frame(c, w, h, label):
    """Panel background: rounded card, engineering grid, corner ticks."""
    ticks = []
    for x, y, dx, dy in ((14, 14, 1, 1), (w - 14, 14, -1, 1),
                         (14, h - 14, 1, -1), (w - 14, h - 14, -1, -1)):
        ticks.append(
            f'<path d="M{x} {y + 9 * dy} L{x} {y} L{x + 9 * dx} {y}" '
            f'stroke="{c["accent"]}" stroke-width="1.25" fill="none" opacity=".55"/>')
    return f'''<defs>
  <pattern id="g{label}" width="22" height="22" patternUnits="userSpaceOnUse">
    <path d="M22 0 L0 0 0 22" fill="none" stroke="{c["grid"]}" stroke-width="1"/>
  </pattern>
</defs>
<rect width="{w}" height="{h}" rx="12" fill="{c["bg"]}"/>
<rect width="{w}" height="{h}" rx="12" fill="url(#g{label})" opacity=".5"/>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="none"
      stroke="{c["border"]}" stroke-width="1"/>
{''.join(ticks)}'''


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img">\n{body}\n</svg>\n')


# ---------------------------------------------------------------- cards

def hero(d, c):
    h = 236
    readouts = [("NODES", "2"), ("GUESTS", "9"), ("VLANS", "5")]
    panel = []
    px = W - 232
    tx = 214  # text column, right of the mark
    panel.append(f'<rect x="{px}" y="42" width="192" height="152" rx="9" '
                 f'fill="{c["surface"]}" stroke="{c["border"]}"/>')
    panel.append(f'<text x="{px + 16}" y="66" font-family="{MONO}" font-size="9" '
                 f'letter-spacing="1.6" fill="{c["dim"]}">HOMELAB</text>')
    for i, (k, v) in enumerate(readouts):
        y = 96 + i * 34
        panel.append(f'<text x="{px + 16}" y="{y}" font-family="{MONO}" font-size="10" '
                     f'letter-spacing="1.2" fill="{c["dim"]}">{k}</text>')
        panel.append(f'<text x="{px + 176}" y="{y}" text-anchor="end" font-family="{MONO}" '
                     f'font-size="19" font-weight="600" fill="{c["accent"]}">{v}</text>')
        if i < 2:
            panel.append(f'<line x1="{px + 16}" y1="{y + 11}" x2="{px + 176}" y2="{y + 11}" '
                         f'stroke="{c["border"]}" stroke-width="1"/>')

    body = f'''{frame(c, W, h, "h")}
<style>
  .fi {{ opacity: 0; animation: fi .7s ease-out forwards; }}
  .d1 {{ animation-delay: .05s }} .d2 {{ animation-delay: .18s }}
  .d3 {{ animation-delay: .31s }} .d4 {{ animation-delay: .44s }}
  @keyframes fi {{ from {{ opacity: 0; transform: translateY(6px) }}
                   to {{ opacity: 1; transform: translateY(0) }} }}
  @media (prefers-reduced-motion: reduce) {{ .fi {{ animation: none; opacity: 1 }} }}
</style>
<g class="fi d1">{frogmark.mark(d["phase"], "H", size=150, x=40, y=40)}
  <text x="115" y="212" text-anchor="middle" font-family="{MONO}" font-size="9"
        letter-spacing="1.6" fill="{c["dim"]}">{d["phase_label"]} · GREENVILLE</text>
</g>
<g class="fi d1">
  <text x="{tx}" y="80" font-family="{MONO}" font-size="36" font-weight="700"
        fill="{c["text"]}" letter-spacing="-1">highfrog</text>
  <text x="{tx + 186}" y="80" font-family="{MONO}" font-size="13"
        fill="{c["accent"]}">reedylab.com</text>
</g>
<line x1="{tx}" y1="100" x2="{W - 262}" y2="100" stroke="{c["border"]}" stroke-width="1"/>
<g class="fi d2">
  <text x="{tx}" y="128" font-family="{SANS}" font-size="14.5" fill="{c["text"]}">
    Mechanical Engineer, P.E. — Greenville, SC</text>
  <text x="{tx}" y="152" font-family="{SANS}" font-size="13.5" fill="{c["dim"]}">
    Consulting engineering by day.</text>
  <text x="{tx}" y="172" font-family="{SANS}" font-size="13.5" fill="{c["dim"]}">
    Self-hosted infrastructure by night.</text>
</g>
<g class="fi d3">
  <text x="{tx}" y="205" font-family="{MONO}" font-size="10.5" letter-spacing="2.2"
        fill="{c["accent2"]}">PRECISION TOOLS. ZERO COMPROMISE.</text>
</g>
<g class="fi d4">{''.join(panel)}</g>'''
    return svg(W, h, body)


def stats(d, c):
    h = 168
    cells = [
        (f'{d["contributions"]:,}', f'CONTRIBUTIONS {d["year"]}'),
        (f'{d["commits"]:,}', "COMMITS"),
        (f'{d["stars"]:,}', "STARS EARNED"),
        (f'{len(d["repos"])}', "SHIPPED TOOLS"),
    ]
    cw = (W - 92) / 4
    out = []
    for i, (val, lab) in enumerate(cells):
        x = 46 + i * cw
        out.append(f'<text x="{x}" y="66" font-family="{MONO}" font-size="30" '
                   f'font-weight="600" fill="{c["text"]}">{val}</text>')
        out.append(f'<text x="{x}" y="86" font-family="{MONO}" font-size="9.5" '
                   f'letter-spacing="1.4" fill="{c["dim"]}">{lab}</text>')
        if i:
            out.append(f'<line x1="{x - 22}" y1="40" x2="{x - 22}" y2="92" '
                       f'stroke="{c["border"]}" stroke-width="1"/>')

    bx, bw = 46, W - 92
    out.append(f'<text x="{bx}" y="120" font-family="{MONO}" font-size="9.5" '
               f'letter-spacing="1.4" fill="{c["dim"]}">LANGUAGE MIX</text>')
    cx = bx
    for lang in d["languages"]:
        seg = bw * lang["pct"] / 100
        out.append(f'<rect x="{cx:.1f}" y="128" width="{max(seg - 2, 1):.1f}" height="7" '
                   f'rx="3.5" fill="{lang["color"]}"/>')
        cx += seg
    lx = bx
    for lang in d["languages"]:
        out.append(f'<circle cx="{lx + 4}" cy="{152}" r="4" fill="{lang["color"]}"/>')
        label = f'{lang["name"]} {lang["pct"]:.0f}%'
        out.append(f'<text x="{lx + 14}" y="156" font-family="{MONO}" font-size="10.5" '
                   f'fill="{c["dim"]}">{esc(label)}</text>')
        lx += 26 + len(label) * 6.4
    return svg(W, h, frame(c, W, h, "s") + "".join(out))


def suite(d, c):
    rows = d["repos"][:5]
    h = 74 + len(rows) * 56
    out = [f'<text x="46" y="46" font-family="{MONO}" font-size="10" letter-spacing="2" '
           f'fill="{c["dim"]}">REEDY LAB — SHIPPING</text>']
    for i, r in enumerate(rows):
        y = 74 + i * 56
        out.append(f'<rect x="34" y="{y}" width="{W - 68}" height="46" rx="8" '
                   f'fill="{c["surface"]}" stroke="{c["border"]}"/>')
        out.append(f'<rect x="34" y="{y}" width="3" height="46" rx="1.5" '
                   f'fill="{c["accent"]}" opacity=".8"/>')
        out.append(f'<text x="52" y="{y + 21}" font-family="{MONO}" font-size="14" '
                   f'font-weight="600" fill="{c["text"]}">{esc(r["name"])}</text>')
        desc = (r["description"] or "")[:74]
        out.append(f'<text x="52" y="{y + 38}" font-family="{SANS}" font-size="11.5" '
                   f'fill="{c["dim"]}">{esc(desc)}</text>')
        lang = (r["primaryLanguage"] or {}).get("name", "")
        if lang:
            out.append(f'<text x="{W - 128}" y="{y + 29}" text-anchor="end" '
                       f'font-family="{MONO}" font-size="11" fill="{c["dim"]}">{esc(lang)}</text>')
        out.append(f'<path d="M{W - 96} {y + 21} l3.1 6.3 6.9 1-5 4.9 1.2 6.9-6.2-3.3'
                   f'-6.2 3.3 1.2-6.9-5-4.9 6.9-1z" fill="{c["warn"]}" opacity=".9"/>')
        out.append(f'<text x="{W - 52}" y="{y + 29}" font-family="{MONO}" font-size="13" '
                   f'font-weight="600" fill="{c["text"]}">{r["stargazerCount"]}</text>')
    return svg(W, h, frame(c, W, h, "p") + "".join(out))


# ---------------------------------------------------------------- main

def main():
    d = fetch()
    ASSETS.mkdir(exist_ok=True)
    written = {}
    for theme, c in THEMES.items():
        for name, fn in (("hero", hero), ("stats", stats), ("suite", suite)):
            content = fn(d, c)
            path = ASSETS / f"{name}-{theme}.svg"
            path.write_text(content)
            written[path.name] = content

    stamp = hashlib.sha256("".join(sorted(written)).encode()
                           + "".join(written[k] for k in sorted(written)).encode()
                           ).hexdigest()[:8]
    readme = ROOT / "README.md"
    text = readme.read_text()
    text = re.sub(r"(assets/[a-z]+-(?:dark|light)\.svg)\?v=[0-9a-f]+", rf"\1?v={stamp}", text)
    text = re.sub(r"(<!-- updated: )[^>]*( -->)", rf"\g<1>{d['updated']}\g<2>", text)
    readme.write_text(text)
    print(f"rendered {len(written)} cards · v={stamp} · phase={d['phase']} "
          f"(sun {d['sun_elevation']}°) · {d['contributions']} contributions · "
          f"{d['stars']} stars")


if __name__ == "__main__":
    main()
