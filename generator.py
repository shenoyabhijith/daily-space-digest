#!/usr/bin/env python3
"""
Daily space HTML digest — now with GitHub Pages auto-push.

Builds a light-theme HTML file featuring planets/moons/asteroids/comets from the Solar
System, with composition facts, NASA/JPL imagery, an APOD side quest, and source links.
Auto-commits and pushes to GitHub Pages.

Standalone — needs only Python 3.10+ stdlib. No pip packages required.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ── CONFIGURABLE ────────────────────────────────────────────────────────
OUT_DIR = Path(os.environ.get("SPACE_DIGEST_OUT_DIR", str(Path.home() / "space-digest")))
ARCHIVE_DIR = OUT_DIR / "archive"
ASSET_DIR = OUT_DIR / "assets"
NASA_APOD = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY&thumbs=true"
NASA_IMAGES = "https://images-api.nasa.gov/search"
JPL_SBDB = "https://ssd-api.jpl.nasa.gov/sbdb.api"
GIT_REMOTE = "https://github.com/shenoyabhijith/daily-space-digest.git"
GIT_BRANCH = "main"
SITE_URL = "https://shenoyabhijith.github.io/daily-space-digest/"
# ────────────────────────────────────────────────────────────────────────

TOPICS = [
    {"name": "Mercury", "kind": "planet", "subtitle": "The iron-hearted speedster baked by the Sun",
     "query": "Mercury planet surface NASA MESSENGER",
     "composition": "A huge iron-rich metallic core, a thin silicate mantle, and a rocky crust. Mercury is unusually dense for its size, which is why scientists often describe it as a world with an oversized metal heart.",
     "fascination": "Mercury has no real atmosphere to move heat around, so its dayside can roast while its nightside plunges into deep cold. It is both scorched and frozen — sometimes on the same long solar day.",
     "numbers": [("Diameter", "4,879 km"), ("Day", "58.6 Earth days"), ("Year", "88 Earth days"), ("Mean density", "5.43 g/cm³")],
     "sources": [("NASA Solar System — Mercury", "https://science.nasa.gov/mercury/"), ("NASA NSSDC Mercury Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/mercuryfact.html"), ("NASA MESSENGER", "https://science.nasa.gov/mission/messenger/")]},
    {"name": "Venus", "kind": "planet", "subtitle": "Earth's evil twin with clouds of acid",
     "query": "Venus clouds surface radar NASA Magellan",
     "composition": "A rocky silicate planet with an iron core, wrapped in a crushing carbon-dioxide atmosphere and sulfuric-acid cloud layers.",
     "fascination": "Venus is not the closest planet to the Sun, but it is the hottest planet because its thick CO₂ atmosphere traps heat in a runaway greenhouse. Its surface pressure feels like being nearly a kilometer underwater on Earth.",
     "numbers": [("Diameter", "12,104 km"), ("Surface pressure", "~92 Earth atmospheres"), ("Surface temperature", "~465°C"), ("Atmosphere", "~96.5% CO₂")],
     "sources": [("NASA Solar System — Venus", "https://science.nasa.gov/venus/"), ("NASA NSSDC Venus Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/venusfact.html"), ("ISRO Shukrayaan", "https://www.isro.gov.in/")]},
    {"name": "Mars", "kind": "planet", "subtitle": "The rusty archive of a wetter world",
     "query": "Mars surface rover NASA Perseverance Curiosity Jezero crater",
     "composition": "Basaltic rock rich in iron-bearing minerals; iron oxides give Mars its red color. Its thin atmosphere is mostly carbon dioxide, with dust that can spread planet-wide.",
     "fascination": "Mars is a crime scene for planetary scientists: dry river valleys, lake beds, clays, and minerals all hint that liquid water once shaped the planet. The question is whether chemistry ever crossed into biology.",
     "numbers": [("Diameter", "6,779 km"), ("Day", "24.6 hours"), ("Atmosphere", "~95% CO₂"), ("Gravity", "0.38 g")],
     "sources": [("NASA Solar System — Mars", "https://science.nasa.gov/mars/"), ("NASA NSSDC Mars Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html"), ("ISRO MOM", "https://www.isro.gov.in/MarsOrbiterMissionSpacecraft.html")]},
    {"name": "Jupiter", "kind": "planet", "subtitle": "A failed-star-sized storm machine",
     "query": "Jupiter Juno spacecraft NASA Great Red Spot",
     "composition": "Mostly hydrogen and helium, likely surrounding deeper layers of metallic hydrogen and a diluted heavy-element core. Its colorful bands are clouds of ammonia, water, and other compounds.",
     "fascination": "Jupiter is so massive it acts like the Solar System's gravitational bouncer. Its storms are not weather in the Earth sense — they are continent-sized fluid dynamics experiments powered by rotation and internal heat.",
     "numbers": [("Diameter", "139,820 km"), ("Mass", "318 Earths"), ("Day", "~9.9 hours"), ("Great Red Spot", "larger than Earth")],
     "sources": [("NASA Solar System — Jupiter", "https://science.nasa.gov/jupiter/"), ("NASA NSSDC Jupiter Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/jupiterfact.html"), ("NASA Juno", "https://science.nasa.gov/mission/juno/")]},
    {"name": "Saturn", "kind": "planet", "subtitle": "The ringed giant made mostly of light gases",
     "query": "Saturn rings Cassini NASA",
     "composition": "Mostly hydrogen and helium. The rings are mostly water-ice particles mixed with dust and rocky material, ranging from grains to house-sized chunks.",
     "fascination": "Saturn's rings look permanent, but they may be temporary on cosmic timescales. We might be living in the lucky era when the Solar System's most photogenic jewelry is still bright and wide.",
     "numbers": [("Diameter", "116,460 km"), ("Density", "0.69 g/cm³"), ("Main rings", "mostly water ice"), ("Known moons", "100+")],
     "sources": [("NASA Solar System — Saturn", "https://science.nasa.gov/saturn/"), ("NASA NSSDC Saturn Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/saturnfact.html"), ("NASA Cassini", "https://science.nasa.gov/mission/cassini/")]},
    {"name": "Uranus", "kind": "planet", "subtitle": "The sideways ice giant",
     "query": "Uranus Voyager 2 NASA ice giant rings",
     "composition": "Hydrogen and helium atmosphere above an interior rich in water, ammonia, and methane ices. Methane absorbs red light, giving Uranus its blue-green color.",
     "fascination": "Uranus rotates on its side, as if a planet-sized collision knocked it over. Its seasons are extreme: each pole can face decades of sunlight followed by decades of darkness.",
     "numbers": [("Diameter", "50,724 km"), ("Axial tilt", "~98°"), ("Year", "84 Earth years"), ("Color source", "methane")],
     "sources": [("NASA Solar System — Uranus", "https://science.nasa.gov/uranus/"), ("NASA NSSDC Uranus Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/uranusfact.html")]},
    {"name": "Neptune", "kind": "planet", "subtitle": "The blue world with supersonic winds",
     "query": "Neptune Voyager 2 NASA dark spot",
     "composition": "Hydrogen, helium, methane atmosphere over an ice-rich mantle of water, ammonia, and methane around a rocky core.",
     "fascination": "Neptune receives very little sunlight, yet it has some of the fastest winds in the Solar System. Something inside this cold blue planet is still powering wild weather.",
     "numbers": [("Diameter", "49,244 km"), ("Year", "165 Earth years"), ("Winds", "up to ~2,000 km/h"), ("Color source", "methane + haze")],
     "sources": [("NASA Solar System — Neptune", "https://science.nasa.gov/neptune/"), ("NASA NSSDC Neptune Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/neptunefact.html")]},
    {"name": "Moon", "kind": "moon", "subtitle": "Earth's impact-scarred memory stone",
     "query": "Moon surface NASA Artemis LRO craters",
     "composition": "Silicate crust and mantle with basaltic maria, anorthosite highlands, and a small metallic core. Lunar regolith is pulverized rock made by billions of years of impacts.",
     "fascination": "The Moon is not just pretty — it is a frozen record of early Solar System violence. Without wind and rain, ancient craters remain like footprints in stone.",
     "numbers": [("Diameter", "3,475 km"), ("Gravity", "0.16 g"), ("Average distance", "384,400 km"), ("Surface", "regolith + basalt + anorthosite")],
     "sources": [("NASA Moon", "https://science.nasa.gov/moon/"), ("NASA NSSDC Moon Fact Sheet", "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html"), ("ISRO Chandrayaan-3", "https://www.isro.gov.in/Chandrayaan3_New.html")]},
    {"name": "Asteroid Bennu", "kind": "asteroid", "subtitle": "A carbon-rich rubble pile older than Earth",
     "query": "asteroid Bennu OSIRIS-REx NASA sample carbon water minerals",
     "composition": "A primitive carbon-rich asteroid containing hydrated minerals and organic-bearing material. Bennu is a rubble pile: a loose gravitational heap rather than one solid rock.",
     "fascination": "Bennu is valuable because it preserved ingredients from the dawn of the Solar System. OSIRIS-REx brought a sample home, giving scientists a clean look at material older than planets.",
     "numbers": [("Diameter", "~492 m"), ("Type", "B-type carbonaceous"), ("Structure", "rubble pile"), ("Sample return", "OSIRIS-REx, 2023")],
     "jpl": "101955",
     "sources": [("NASA OSIRIS-REx", "https://science.nasa.gov/mission/osiris-rex/"), ("NASA Bennu", "https://science.nasa.gov/solar-system/asteroids/101955-bennu/"), ("JPL SBDB", "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=101955")]},
    {"name": "Asteroid Psyche", "kind": "asteroid", "subtitle": "A possible metal-rich planetary core exposed in space",
     "query": "asteroid Psyche NASA mission metal rich asteroid",
     "composition": "Likely metal-rich, with iron-nickel material mixed with silicates. Scientists study it as a possible remnant of a planetesimal core or a complex metal-rock body.",
     "fascination": "Psyche may let us inspect material similar to the hidden cores of rocky planets — without drilling through a planet. It is like finding a planetary engine block floating between Mars and Jupiter.",
     "numbers": [("Diameter", "~226 km"), ("Region", "main asteroid belt"), ("Possible material", "iron-nickel + silicate"), ("NASA mission", "Psyche")],
     "jpl": "16",
     "sources": [("NASA Psyche mission", "https://science.nasa.gov/mission/psyche/"), ("NASA Psyche asteroid", "https://science.nasa.gov/solar-system/asteroids/16-psyche/"), ("JPL SBDB", "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=16")]},
    {"name": "Comet 67P", "kind": "comet", "subtitle": "A dark icy time capsule with cliffs and jets",
     "query": "Comet 67P Rosetta ESA NASA jets nucleus",
     "composition": "A porous mixture of water ice, dust, organic-rich dark material, and volatile compounds. Sunlight warms the nucleus and drives gas/dust jets that form the coma and tails.",
     "fascination": "Comets are messy refrigerators from the early Solar System. 67P looks like a rubber duck, but its jets, pits, and cliffs tell a story of ancient ice slowly waking near the Sun.",
     "numbers": [("Nucleus", "~4 km wide"), ("Type", "Jupiter-family comet"), ("Surface", "dark organic-rich dust"), ("Visited by", "Rosetta/Philae")],
     "sources": [("NASA comet science", "https://science.nasa.gov/solar-system/comets/"), ("ESA Rosetta", "https://www.esa.int/Science_Exploration/Space_Science/Rosetta")]},
]

def fetch_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SpaceDigest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def try_fetch_json(url: str) -> dict | None:
    try: return fetch_json(url)
    except Exception: return None

def pick_topic(today: dt.date) -> dict:
    return TOPICS[int(today.strftime("%Y%m%d")) % len(TOPICS)]

def nasa_image(query: str) -> dict:
    params = urllib.parse.urlencode({"q": query, "media_type": "image", "page_size": 8})
    data = try_fetch_json(f"{NASA_IMAGES}?{params}") or {}
    for item in data.get("collection", {}).get("items", []):
        links, meta = item.get("links") or [], (item.get("data") or [{}])[0]
        href = next((l.get("href") for l in links if l.get("href")), None)
        if href:
            return {"url": href, "title": meta.get("title") or query,
                    "description": re.sub(r"\s+", " ", meta.get("description", "")).strip()[:450],
                    "source": "NASA Images", "source_url": "https://images.nasa.gov/search-results?q=" + urllib.parse.quote(query)}
    return {}

def apod() -> dict:
    data = try_fetch_json(NASA_APOD) or {}
    url = data.get("hdurl") or data.get("url") or data.get("thumbnail_url") or ""
    if url:
        return {"url": url, "title": data.get("title", "NASA APOD"),
                "explanation": re.sub(r"\s+", " ", data.get("explanation", "")).strip()[:650],
                "date": data.get("date", ""), "source_url": "https://apod.nasa.gov/apod/"}
    return {}

def jpl_small_body(des: str | None) -> list[tuple[str, str]]:
    if not des: return []
    data = try_fetch_json(f"{JPL_SBDB}?{urllib.parse.urlencode({'sstr': des, 'phys-par': '1'})}") or {}
    obj, orbit = data.get("object", {}), data.get("orbit", {})
    phys = {p.get("name"): p.get("value") for p in data.get("phys_par", []) if isinstance(p, dict)}
    rows = []
    if obj.get("fullname"): rows.append(("JPL designation", str(obj["fullname"]).strip()))
    if orbit.get("class", {}).get("name"): rows.append(("Orbit class", orbit["class"]["name"]))
    if phys.get("diameter"): rows.append(("JPL diameter", f"{phys['diameter']} km"))
    if phys.get("rot_per"): rows.append(("Rotation period", f"{phys['rot_per']} h"))
    return rows[:4]

def esc(x): return html.escape(str(x), quote=True)

def build_html(topic, image, apod_data, today: dt.date) -> str:
    name = topic["name"]
    nums = list(topic.get("numbers", [])) + jpl_small_body(topic.get("jpl"))
    hero = image.get("url") or apod_data.get("url") or ""
    hero_desc = image.get("description") or apod_data.get("explanation") or "NASA imagery."
    apod_block = f"""\n<section class="apod card"><div class="eyebrow">NASA APOD</div><h2>{esc(apod_data['title'])}</h2><p>{esc(apod_data['explanation'])}</p><a class="button ghost" href="{esc(apod_data['source_url'])}">Open NASA APOD</a></section>\n""" if apod_data else ""
    fact_cards = "\n".join(f'<div class="stat"><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k, v in nums)
    hue = int(hashlib.sha256(name.encode()).hexdigest()[:2], 16) % 360
    sources = "\n".join(f'<li><a href="{esc(u)}">{esc(l)}</a></li>' for l, u in topic.get("sources", []))
    if image.get("source_url"): sources += f'\n<li><a href="{esc(image["source_url"])}">{esc(image.get("source", "NASA Images"))}</a></li>'
    if apod_data.get("source_url"): sources += f'\n<li><a href="{esc(apod_data["source_url"])}">NASA APOD</a></li>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Space Field Note — {esc(name)}</title>
<style>:root{{--h:{hue};--ink:#101828;--muted:#667085;--paper:#fffaf0;--line:#eadfc9;--accent:hsl(var(--h),82%,42%);--accent2:hsl(calc(var(--h)+42),80%,50%)}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:var(--ink);background:radial-gradient(circle at top left,hsl(var(--h),90%,92%),transparent 32rem),linear-gradient(135deg,#fffdf7,#f5f7fb 55%,#eef6ff)}}
.wrap{{max-width:1120px;margin:0 auto;padding:34px 22px 60px}}.mast{{display:flex;gap:18px;align-items:center;margin-bottom:24px}}
.badge{{width:58px;height:58px;border-radius:19px;display:grid;place-items:center;color:#fff;font-size:30px;background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 18px 40px rgba(16,24,40,.18)}}
.kicker{{color:var(--accent);font-weight:800;letter-spacing:.16em;text-transform:uppercase;font-size:12px}}
h1{{font-size:clamp(42px,8vw,88px);line-height:.9;margin:8px 0 12px;letter-spacing:-.07em}}
.subtitle{{font-size:clamp(20px,3vw,34px);color:#344054;margin:0}}
.hero{{margin-top:28px;display:grid;grid-template-columns:1.25fr .75fr;gap:22px;align-items:stretch}}
.image-card,.card{{border:1px solid rgba(16,24,40,.10);background:rgba(255,255,255,.78);backdrop-filter:blur(14px);border-radius:32px;overflow:hidden;box-shadow:0 20px 50px rgba(16,24,40,.10)}}
.image-card img{{display:block;width:100%;height:520px;object-fit:cover;background:#111827}}
.caption{{padding:18px 22px;color:var(--muted);font-size:14px}}.card{{padding:26px}}
.eyebrow{{color:var(--accent);font-weight:900;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}
h2{{font-size:30px;letter-spacing:-.03em;margin:8px 0 12px}}p{{font-size:17px;line-height:1.65}}
.stats{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}}
.stat{{padding:14px;background:#fff;border:1px solid var(--line);border-radius:18px}}
.stat span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;font-weight:800}}
.stat strong{{display:block;margin-top:4px;font-size:18px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}}
.composition{{border-left:8px solid var(--accent)}}
.spark{{font-size:20px;padding:18px;border-radius:22px;background:linear-gradient(135deg,hsl(var(--h),92%,94%),#fff);border:1px solid var(--line)}}
.sources ul{{margin:12px 0 0;padding-left:20px}}a{{color:var(--accent);font-weight:800}}
.footer{{margin-top:28px;color:var(--muted);font-size:13px}}
@media(max-width:820px){{.hero,.grid{{grid-template-columns:1fr}}.image-card img{{height:360px}}.stats{{grid-template-columns:1fr}}}}
</style></head><body><main class="wrap">
<header class="mast"><div class="badge">☄️</div><div><div class="kicker">Daily Space Field Note</div><h1>{esc(name)}</h1><p class="subtitle">{esc(topic['subtitle'])}</p></div></header>
<section class="hero"><div class="image-card">{f'<img src="{esc(hero)}" alt="{esc(name)}">' if hero else ''}<div class="caption"><strong>{esc(image.get("title") or apod_data.get("title") or name)}</strong><br>{esc(hero_desc)}</div></div>
<aside class="card"><div class="eyebrow">Quick scan</div><h2>What is it made of?</h2><p>{esc(topic['composition'])}</p><div class="stats">{fact_cards}</div></aside></section>
<section class="grid"><article class="card composition"><div class="eyebrow">Why it's fascinating</div><h2>The hook</h2><div class="spark">{esc(topic['fascination'])}</div></article>
<article class="card"><div class="eyebrow">Imagine this</div><h2>A tiny thought experiment</h2><p>{esc(_imagination(topic))}</p></article></section>
{apod_block}
<section class="sources card"><div class="eyebrow">Source trail</div><h2>References</h2><ul>{sources}</ul></section>
<div class="footer">Generated by Astronomy Daily Digest. <a href="{SITE_URL}">View all</a></div>
</main></body></html>"""

def _imagination(topic) -> str:
    kind, name = topic.get("kind"), topic.get("name")
    prompts = {"planet": f"Stand above {name} with a transparent science visor. The colors are not just scenery — they are chemistry.",
               "moon": f"Imagine scooping a handful of dust on {name}. Every grain is a smashed fragment of ancient impacts.",
               "asteroid": f"If you could float beside {name}, you would be inspecting leftover construction material from the Solar System's beginning.",
               "comet": f"Approach {name} as sunlight hits it. Ice turns to gas, dust lifts, and a sleeping fossil draws a tail across space."}
    return prompts.get(kind, f"Picture {name} not as a distant dot, but as a physical place made of chemistry, gravity, and time.")

def _run_cmd(args: list[str], cwd: Path, timeout: int = 15, check: bool = True) -> None:
    result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")

def push_to_github(out_dir: Path) -> bool:
    try:
        if not (out_dir / ".git").exists():
            _run_cmd(["git", "init"], cwd=out_dir)
            _run_cmd(["git", "branch", "-m", GIT_BRANCH], cwd=out_dir)
            _run_cmd(["git", "remote", "add", "origin", GIT_REMOTE], cwd=out_dir)
        _run_cmd(["git", "config", "user.email", "shenoyabhijith@users.noreply.github.com"], cwd=out_dir)
        _run_cmd(["git", "config", "user.name", "shenoyabhijith"], cwd=out_dir)
        _run_cmd(["git", "add", "-A"], cwd=out_dir)
        today = dt.datetime.now(dt.UTC).strftime("%B %d, %Y")
        _run_cmd(["git", "commit", "-m", f"☄️ Space Field Note — {today}"], cwd=out_dir, check=False)
        # Get token from gh CLI
        try:
            token = subprocess.run(["/opt/data/bin/gh", "auth", "token"], capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            token = ""
        if token:
            remote_url = GIT_REMOTE.replace("https://", f"https://x-access-token:{token}@")
            _run_cmd(["git", "remote", "set-url", "origin", remote_url], cwd=out_dir)
        _run_cmd(["git", "push", "origin", GIT_BRANCH], cwd=out_dir, timeout=30)
        return True
    except Exception as exc:
        print(f"[space-digest] GitHub push failed: {exc}", file=__import__("sys").stderr)
        return False

def build_index(out_dir: Path, archive_dir: Path) -> None:
    """Generate archive index.html listing all space field notes."""
    articles = []
    for f in sorted(archive_dir.glob("*.html"), reverse=True):
        html = f.read_text(encoding="utf-8")
        title = ""
        m = re.search(r'<h1>([^<]+)</h1>', html)
        if m: title = m.group(1)
        excerpt = ""
        m = re.search(r'<div class="caption"><strong>([^<]+)', html)
        if m: excerpt = m.group(1)[:150]
        articles.append({"title": title or f.name.replace(".html","").replace("space-field-note-",""), "file": f.name, "excerpt": excerpt})

    cards = "\n".join(
        f'<a href="archive/{a["file"]}" class="card"><h3>{esc(a["title"])}</h3><p>{esc(a["excerpt"])}</p></a>'
        for a in articles
    )
    index = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>☄️ Daily Space Field Notes</title>
<style>:root{{--ink:#101828;--muted:#667085;--line:#d0d5dd;--accent:#2563eb;--accent2:#7c3aed}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--ink);background:linear-gradient(180deg,#f8fafc,#eef2ff)}}
.wrap{{max-width:800px;margin:0 auto;padding:40px 22px;text-align:center}}
h1{{font-size:clamp(32px,5vw,48px);margin:8px 0}}
.sub{{color:var(--muted);font-size:18px}}
.cta{{margin:16px 0}}.cta a{{display:inline-block;padding:10px 24px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-radius:999px;font-size:16px;font-weight:700;text-decoration:none}}
.card{{display:block;padding:16px 20px;margin:12px 0;background:#fff;border:1px solid var(--line);border-radius:16px;text-decoration:none;color:var(--ink);text-align:left;transition:.15s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,0,0,.08)}}
.card h3{{margin:0 0 4px;font-size:18px}}.card p{{margin:0;font-size:14px;color:var(--muted)}}
.footer{{margin-top:32px;color:var(--muted);font-size:13px}}
</style></head><body><div class="wrap">
<h1>☄️ Daily Space Field Notes</h1>
<p class="sub">Planets, moons, asteroids &amp; comets — one Solar System body every day</p>
<div class="cta"><a href="latest.html">📖 Read Today's Field Note</a></div>
<h2 style="margin-top:32px">📚 Archive — {len(articles)} Notes</h2>
{cards}
<div class="footer"><p>☄️ NASA/JPL imagery · <a href="https://github.com/shenoyabhijith/daily-space-digest">GitHub</a></p></div>
</div></body></html>"""
    (out_dir / "index.html").write_text(index, encoding="utf-8")

def main() -> int:
    today = dt.datetime.now(dt.UTC).date()
    topic = pick_topic(today)
    image = nasa_image(topic["query"])
    apod_data = apod()
    html_text = build_html(topic, image, apod_data, today)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic["name"].lower()).strip("-")
    html_path = ARCHIVE_DIR / f"space-field-note-{today.isoformat()}-{slug}.html"
    (OUT_DIR / "latest.html").write_text(html_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    build_index(OUT_DIR, ARCHIVE_DIR)
    push_to_github(OUT_DIR)
    print(f"🌐 {SITE_URL}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
