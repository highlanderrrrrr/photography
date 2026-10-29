#!/usr/bin/env python3
"""Make leesagi.com readable by search engines and AI assistants.

Run this after you add photos or change captions:
    python3 build-seo.py

It reads albums.json and images/<album>/album.json and rewrites:
  - albums/<album>/index.html  plain pages, one per album, with every photo and caption
  - sitemap.xml                list of pages and photos for Google and Bing
  - robots.txt                 lets every crawler in, points to the sitemap
  - llms.txt                   short text summary of the site for AI assistants
  - index.html                 only the parts between the "seo" markers
  - outings/index.html         the Outings list, newest first
  - outings/<name>/index.html  one page per outing, from outings/<name>/outing.txt
  - outings/outings.json       which outing each photo belongs to (for the link in the viewer)

An outing.txt looks like this (edit the text freely, keep the "key: value" lines and the ---):
    title: Oakland Chinatown - Murals, Vendors and the Produce Market
    date: 2026-10-26
    gear: Nikon D7500, 18-200mm
    summary: One or two sentences for the Outings list.
    photos:
    the-streets/2026-10-26-oakland-china-town-53.jpg
    outings/oakland-chinatown/storefront.jpg | Asian Branch - Morning outside the library.
    ---
    First paragraph.

    Second paragraph.
Photos are paths under images/, in the order they should appear. Album photos use their
album caption; for outing-only photos add " | Title - comment" after the path.
Usually run through update-site.py, which also prepares the photos.
"""
import html
import json
import os
import re
from datetime import date, datetime

SITE = "https://leesagi.com"
NAME = "Lee Sagi"
ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today().isoformat()
ABOUT = ("I photograph what I run into. Backcountry tracks and desert camps, the streets near home, "
         "people I know, and more. No rime or reason, just photos I like.")
FACTS = "Based in the East Bay, California. Shoots on a Nikon D7500. Mostly black and white, street."
SAME_AS = [
    "https://www.instagram.com/btbw666/",
    "https://www.threads.com/@btbw666",
    "https://www.youtube.com/@OverlandOutAndAbout",
]


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def esc(s):
    return html.escape(s or "", quote=True)


def img_url(folder, file, size="large"):
    sub = f"{size}/" if size else ""
    if size and not os.path.exists(os.path.join(ROOT, "images", folder, size, file)):
        sub = ""
    return f"/images/{folder}/{sub}{file}"


def split_caption(caption):
    if not caption:
        return "", ""
    if " - " in caption:
        t, c = caption.split(" - ", 1)
        return t.strip(), c.strip()
    return caption.strip(), ""


cfg = load("albums.json")
albums = []
for folder in cfg["albums"]:
    a = load(f"images/{folder}/album.json")
    albums.append({"folder": folder, "title": a.get("title", folder), "cover": a.get("cover"),
                   "photos": a.get("photos", [])})

person = {"@type": "Person", "@id": f"{SITE}/#lee", "name": NAME, "url": f"{SITE}/",
          "description": ABOUT, "jobTitle": "Photographer",
          "homeLocation": {"@type": "Place", "name": "East Bay, California"}, "sameAs": SAME_AS}

# ---------- album pages ----------
PAGE_CSS = """
:root{--bg:#000;--fg:#f2f1ee;--muted:#8f8d89;--line:#222}
*{box-sizing:border-box}html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Source Serif 4",Georgia,"Times New Roman",serif;font-size:18px;line-height:1.5}
a{color:inherit}
.wrap{max-width:1100px;margin:0 auto;padding:28px max(20px,env(safe-area-inset-right)) 64px max(20px,env(safe-area-inset-left))}
header{display:flex;flex-wrap:wrap;gap:12px 28px;justify-content:space-between;align-items:baseline;margin-bottom:48px}
header .name{font-size:22px;text-decoration:none}
nav{display:flex;flex-wrap:wrap;gap:18px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px}
nav a{text-decoration:none;color:var(--muted)}nav a:hover{color:var(--fg)}
h1{font-weight:400;font-size:clamp(30px,5vw,44px);margin:0 0 8px}
.intro{color:var(--muted);margin:0 0 40px;font-size:16px}
figure{margin:0 0 56px}
figure img{display:block;width:100%;height:auto;max-height:88vh;object-fit:contain;background:#0a0a0a}
figcaption{margin-top:12px;font-size:17px}
figcaption b{font-weight:600}
.more{border-top:1px solid var(--line);padding-top:24px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;color:var(--muted)}
.more a{margin-right:16px}
footer{margin-top:48px;color:var(--muted);font-size:14px}
"""

for i, a in enumerate(albums):
    folder, title = a["folder"], a["title"]
    url = f"{SITE}/albums/{folder}/"
    figs, images_ld = [], []
    for p in a["photos"]:
        t, c = split_caption(p.get("caption"))
        alt = p.get("caption") or f"{title} photograph by {NAME}"
        w, h = p.get("w"), p.get("h")
        size = f' width="{w}" height="{h}"' if w and h else ""
        cap = ""
        if t or c:
            cap = "<figcaption>" + (f"<b>{esc(t)}</b>" if t else "") + (f" &middot; {esc(c)}" if c else "") + "</figcaption>"
        figs.append(f'<figure><img src="{esc(img_url(folder, p["file"]))}" alt="{esc(alt)}"{size} loading="lazy">{cap}</figure>')
        images_ld.append({"@type": "ImageObject", "contentUrl": SITE + img_url(folder, p["file"], None),
                          "thumbnailUrl": SITE + img_url(folder, p["file"]),
                          "name": t or title, "caption": p.get("caption") or "",
                          "creator": {"@id": f"{SITE}/#lee"}, "creditText": NAME,
                          "copyrightNotice": f"© {NAME}"})
    others = " ".join(f'<a href="/albums/{o["folder"]}/">{esc(o["title"])}</a>' for o in albums if o is not a)
    ld = {"@context": "https://schema.org", "@graph": [
        person,
        {"@type": "ImageGallery", "name": f"{title} by {NAME}", "url": url,
         "author": {"@id": f"{SITE}/#lee"}, "image": images_ld}]}
    desc = f"{title}: {len(a['photos'])} photographs by {NAME}, East Bay, California."
    cover = a["cover"] or (a["photos"][0]["file"] if a["photos"] else "")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | {NAME} Photography</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME} Photography">
<meta property="og:title" content="{esc(title)} | {NAME} Photography">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}{esc(img_url(folder, cover))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<div class="wrap">
<header><a class="name" href="/">{NAME}</a>
<nav aria-label="Main"><a href="/">Work</a><a href="/#collections">Collections</a><a href="/outings/">Outings</a><a href="/#about">About</a><a href="/#contact">Contact</a></nav></header>
<main>
<h1>{esc(title)}</h1>
<p class="intro">{len(a['photos'])} photographs. <a href="/#album/{folder}">Open in the full-screen viewer</a></p>
{chr(10).join(figs)}
</main>
<p class="more">More collections: {others}</p>
<footer>&copy; {date.today().year} {NAME}</footer>
</div>
</body>
</html>
"""
    write(f"albums/{folder}/index.html", page)

# ---------- outings ----------
def read_outing(folder):
    with open(os.path.join(ROOT, "outings", folder, "outing.txt"), encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n")
    head, _, body = raw.partition("\n---\n")
    meta, photos, in_photos = {}, [], False
    for line in head.split("\n"):
        line = line.strip()
        if not line:
            continue
        if in_photos and ":" not in line.split("/")[0]:
            key, _, cap = line.partition(" | ")
            photos.append((key.strip(), cap.strip()))
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        in_photos = key == "photos"
        if not in_photos:
            meta[key] = value.strip()
    paras = [" ".join(p.split()) for p in body.strip().split("\n\n") if p.strip()]
    return {"folder": folder, "title": meta.get("title", folder), "date": meta.get("date", ""),
            "gear": meta.get("gear", ""), "summary": meta.get("summary", ""), "photos": photos, "paras": paras,
            "meta": meta, "body": body, "raw": raw}


def nice_date(iso):
    try:
        d = date.fromisoformat(iso)
        return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")
    except ValueError:
        return iso


captions = {}
sizes = {}
for a in albums:
    for p in a["photos"]:
        key = f"{a['folder']}/{p['file']}"
        captions[key] = p.get("caption") or ""
        sizes[key] = (p.get("w"), p.get("h"))


def photo_info(key, caption=""):
    w, h = sizes.get(key, (None, None))
    if not w:
        try:
            from PIL import Image
            with Image.open(os.path.join(ROOT, "images", key)) as im:
                w, h = im.size
        except Exception:
            w, h = None, None
    return {"key": key, "caption": caption or captions.get(key, ""), "w": w, "h": h}


def gps_for(key):
    """(lat, lon) from a photo's GPS, or None. Photos near private places have none (update-site.py)."""
    try:
        from PIL import Image
        with Image.open(os.path.join(ROOT, "images", key)) as im:
            g = im.getexif().get_ifd(0x8825)
        deg = lambda v: float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat = deg(g[2]) * (-1 if str(g.get(1, "N")).upper().startswith("S") else 1)
        lon = deg(g[4]) * (-1 if str(g.get(3, "E")).upper().startswith("W") else 1)
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None


LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4"


def large_url(key):
    folder, _, file = key.rpartition("/")
    return img_url(folder, file)


outings = []
outings_dir = os.path.join(ROOT, "outings")
if os.path.isdir(outings_dir):
    for folder in sorted(os.listdir(outings_dir)):
        if os.path.isfile(os.path.join(outings_dir, folder, "outing.txt")):
            o = read_outing(folder)
            missing = [k for k, _ in o["photos"] if not os.path.exists(os.path.join(ROOT, "images", k))]
            for k in missing:
                print(f"  warning: outing {folder}: no image at images/{k} (skipped)")
            o["photos"] = [photo_info(k, c) for k, c in o["photos"] if k not in missing]
            outings.append(o)
outings.sort(key=lambda o: o["date"], reverse=True)

with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
    _idx = f.read()
_m = re.search(r'<header class="site-header">.*?</header>', _idx, flags=re.S)
site_header = _m.group(0) if _m else ""
site_header = re.sub(r'href="#"', 'href="/"', site_header)
site_header = re.sub(r'href="#', 'href="/#', site_header)
site_header = site_header.replace('<a href="/outings/">Outings</a>', '<a href="/outings/" aria-current="page">Outings</a>')
_lb = re.search(r'<div id="lightbox".*?\n  </div>\n', _idx, flags=re.S)
lightbox_html = _lb.group(0) if _lb else ""
_v = re.search(r'style\.css\?v=(\d+)', _idx)
css_v = _v.group(1) if _v else "1"
_v = re.search(r'script\.js\?v=(\d+)', _idx)
js_v = _v.group(1) if _v else "1"

GOAT = """  <script>
    window.goatcounter = { no_onload: true };
    window.addEventListener('load', function () {
      if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: location.pathname });
    });
  </script>
  <script data-goatcounter="https://leesagi.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>"""


def outing_shell(title, desc, url, image, ld, main, extra_body=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{NAME} Photography">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}{esc(image)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/style.css?v={css_v}">
  <script src="https://cdn.jsdelivr.net/npm/exifr/dist/full.umd.js"></script>
  <link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96" />
  <link rel="icon" type="image/svg+xml" href="/favicon/favicon.svg" />
  <link rel="shortcut icon" href="/favicon/favicon.ico" />
  <link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon.png" />
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
  <div class="wrap">
    {site_header}

    <main>
{main}
    </main>

    <footer class="site-footer"><span>{NAME}</span><span>&copy; <span id="year">{date.today().year}</span></span></footer>
  </div>
{extra_body}
{GOAT}
</body>
</html>
"""


SECTION_GAP_MIN = 20   # a new time section starts after this many minutes without a photo, or on a new day
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def capture_time(key):
    """When the photo was taken (camera clock), or None."""
    try:
        from PIL import Image
        with Image.open(os.path.join(ROOT, "images", key)) as im:
            stamp = im.getexif().get_ifd(0x8769).get(36867) or im.getexif().get(306)
        return datetime.strptime(str(stamp).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def clock(t):
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'a.m.' if t.hour < 12 else 'p.m.'}"


def time_range(a, b):
    if (a.hour, a.minute) == (b.hour, b.minute):
        return clock(a)
    if (a.hour < 12) == (b.hour < 12):
        return f"{clock(a).rsplit(' ', 1)[0]} – {clock(b)}"
    return f"{clock(a)} – {clock(b)}"


def short_day(t):
    return t.strftime("%a, %b ") + str(t.day)


HEADER_RE = re.compile(r"^##\s*(?:(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<day>\d{1,2}),?\s*)?"
                       r"(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ap>[aApP])?\.?\s*[mM]?\.?\s*(?:\|\s*(?P<label>.*))?$")


def split_body(body):
    """Outing text -> (intro paragraphs, [{time-line pieces, line, paragraphs}])."""
    intro, blocks, cur = [], [], None
    for chunk in re.split(r"\n(?=##)", "\n" + body.strip()):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        first, _, rest = chunk.partition("\n")
        m = HEADER_RE.match(first.strip()) if first.strip().startswith("##") else None
        paras = [" ".join(p.split()) for p in (rest if m else chunk).strip().split("\n\n") if p.strip()]
        if m:
            blocks.append({"m": m, "line": first.strip(), "paras": paras})
        elif blocks:
            blocks[-1]["paras"] += paras
        else:
            intro += paras
    return intro, blocks


def header_time(m, trip_day):
    h, mi = int(m["h"]), int(m["m"])
    ap = (m["ap"] or "").lower()
    if ap == "p" and h < 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    d = trip_day
    if m["mon"] and m["mon"].title()[:3] in MONTHS:
        d = d.replace(month=MONTHS.index(m["mon"].title()[:3]) + 1, day=int(m["day"]))
    return d.replace(hour=h, minute=mi, second=0)


def make_sections(photos):
    """Group photos (already in time order) into sections at gaps of SECTION_GAP_MIN or a new day."""
    timed = [p for p in photos if p.get("t")]
    sections = []
    for p in timed:
        s = sections[-1] if sections else None
        if s and p["t"].date() == s["end"].date() and (p["t"] - s["end"]).total_seconds() <= SECTION_GAP_MIN * 60:
            s["photos"].append(p)
            s["end"] = p["t"]
        else:
            sections.append({"start": p["t"], "end": p["t"], "photos": [p]})
    untimed = [p for p in photos if not p.get("t")]
    if untimed:
        sections.append({"start": None, "end": None, "photos": untimed})
    return sections


def add_missing_time_lines(folder, raw, sections, multi_day):
    """Write a "## time" line into outing.txt for each section that has none, so Lee can type under it."""
    head, sep, body = raw.partition("\n---\n")
    if not sep:
        return
    new = [s for s in sections if s["start"] and not s.get("blocks")]
    if not new:
        return
    def line(s):
        day = f"{s['start'].strftime('%b')} {s['start'].day}, " if multi_day else ""
        return f"## {day}{clock(s['start'])}"
    # Keep everything Lee wrote; add the new lines in time order among the existing ones.
    intro_part = body
    m = re.search(r"(?m)^##", body)
    if m:
        intro_part, rest = body[:m.start()], body[m.start():]
        existing = [c.strip("\n") for c in re.split(r"\n(?=##)", "\n" + rest) if c.strip()]
    else:
        existing = []
    trip_day = sections[0]["start"]
    items = []
    for c in existing:
        hm = HEADER_RE.match(c.split("\n", 1)[0].strip())
        items.append((header_time(hm, trip_day) if hm else datetime.max, c))
    for s in new:
        items.append((s["start"], line(s)))
        print(f"  outings/{folder}/outing.txt: added the time line \"{line(s)}\" (write about that part under it)")
    items.sort(key=lambda x: x[0])
    times = "\n\n".join(c for _, c in items)
    body = (intro_part.strip("\n") + "\n\n" + times if intro_part.strip() else times) + "\n"
    with open(os.path.join(ROOT, "outings", folder, "outing.txt"), "w", encoding="utf-8") as f:
        f.write(head + sep + body)


def tile_html(p, n):
    w = round(300 * (p["w"] / p["h"])) if p.get("w") and p.get("h") else 300
    title = p["caption"].split(" - ")[0] if p["caption"] else ""
    return (f'              <figure class="sfig" style="width:{w}px">'
            f'<a class="tile" href="{esc(large_url(p["key"]))}"><img src="{esc(large_url(p["key"]))}" alt="{esc(p["caption"])}" loading="lazy"></a>'
            f'<figcaption><em>{n:02d}</em>{esc(title)}</figcaption></figure>')


photo_outings = {}
for o in outings:
    url = f"{SITE}/outings/{o['folder']}/"
    short = o["title"].split(" - ")[0].strip()
    for p in o["photos"]:
        photo_outings.setdefault(p["key"], {"url": f"/outings/{o['folder']}/", "short": short})
    for p in o["photos"]:
        p["t"] = capture_time(p["key"])
        where = gps_for(p["key"])
        if where:
            p["lat"], p["lon"] = where
    keys = [p["key"] for p in o["photos"]]
    cover_key = o["meta"].get("cover", "").strip()
    if cover_key not in keys:
        cover_key = keys[0] if keys else ""
    cover = next((p for p in o["photos"] if p["key"] == cover_key), None)
    body_photos = sorted([p for p in o["photos"] if p is not cover],
                         key=lambda p: (p["t"] is None, p["t"] or datetime.min))
    timed_all = [p["t"] for p in o["photos"] if p.get("t")]
    trip_day = min(timed_all) if timed_all else datetime(2000, 1, 1)
    multi_day = len({t.date() for t in timed_all}) > 1
    sections = make_sections(body_photos)
    # Match each "## time" line Lee wrote to the section it falls in (10 minutes of slack either side).
    intro, blocks = split_body(o["body"])
    loose = []
    for b in blocks:
        t = header_time(b["m"], trip_day)
        home = next((s for s in sections if s["start"] and
                     s["start"].timestamp() - 600 <= t.timestamp() <= s["end"].timestamp() + 600), None)
        if home:
            home.setdefault("blocks", []).append(b)
        else:
            loose.append({"start": t, "end": t, "photos": [], "blocks": [b]})
    add_missing_time_lines(o["folder"], o["raw"], sections, multi_day)
    sections = sorted(sections + loose, key=lambda s: (s["start"] is None, s["start"] or datetime.min))

    # Display order for the full-screen viewer: cover first, then every section's photos.
    shown = ([cover] if cover else []) + [p for s in sections for p in s["photos"]]
    for i, p in enumerate(shown):
        p["n"] = i
    out, n = [], 0
    for s in sections:
        label = next((b["m"]["label"] for b in s.get("blocks", []) if b["m"]["label"]), "")
        if s["start"]:
            stamp = time_range(s["start"], s["end"])
            if multi_day:
                stamp = f"{short_day(s['start'])} · {stamp}"
        else:
            stamp = "More photos"
        text = [para for b in s.get("blocks", []) for para in b["paras"]]
        empty = "" if text else " empty"
        out.append(f'        <section class="o-sec{empty}" data-stamp="{esc(stamp)}">')
        out.append(f'          <div class="o-stamp">{esc(stamp)}' + (f'<small>{esc(label)}</small>' if label else "") + '</div>')
        out.append('          <div class="o-body">')
        out += [f"            <p>{esc(t)}</p>" for t in text]
        if s["photos"]:
            start = s["photos"][0]["n"]
            tiles = []
            for p in s["photos"]:
                n += 1
                tiles.append(tile_html(p, n))
            out.append(f'            <div class="sec-strip" data-start="{start}" aria-label="Photographs">\n' + "\n".join(tiles) + "\n            </div>")
        out.append("          </div>")
        out.append("        </section>")
    located = sum(1 for p in shown if "lat" in p)
    has_map = located >= 2
    map_html = ('        <figure class="outing-map">\n'
                '          <div id="outing-map" class="map" role="region" aria-label="Map of where the photos were taken"></div>\n'
                f'          <figcaption>Where I stopped. {located} of {len(shown)} photos have a location; tap a pin to see it.</figcaption>\n'
                '        </figure>') if has_map else ""

    # Facts panel: worked out from the photos, plus the optional lines in outing.txt.
    meta = o["meta"]
    facts = []
    if o["date"]:
        try:
            d = date.fromisoformat(o["date"])
            facts.append(("Date", d.strftime("%a, %b ") + str(d.day) + d.strftime(", %Y")))
        except ValueError:
            facts.append(("Date", o["date"]))
    if timed_all and not multi_day:
        facts.append(("Hours", time_range(min(timed_all), max(timed_all))))
    elif multi_day:
        facts.append(("Days", f"{short_day(min(timed_all))} – {short_day(max(timed_all))}"))
    if meta.get("light"):
        facts.append(("Light", meta["light"]))
    if o["gear"]:
        facts.append(("Gear", o["gear"]))
    count = f"{len(shown)} photo{'s' if len(shown) != 1 else ''}"
    facts.append(("Frames", f"{meta['frames']} shot · {len(shown)} here" if meta.get("frames") else count))
    if meta.get("where"):
        facts.append(("Where", meta["where"]))
    facts_html = "\n".join(f'              <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in facts)
    cover_html = (f'          <a class="o-cover-img tile" href="{esc(large_url(cover["key"]))}" data-n="0">'
                  f'<img src="{esc(large_url(cover["key"]))}" alt="{esc(cover["caption"])}"></a>') if cover else ""
    eyebrow = f"Outing · {meta['where']}" if meta.get("where") else "Outing"
    intro_html = "\n".join(f"          <p>{esc(t)}</p>" for t in intro)
    main = f"""      <article class="o-page">
        <a class="back o-back" href="/outings/">&larr; Outings</a>
        <header class="o-cover">
{cover_html}
          <div class="o-cover-text">
            <span class="o-eyebrow">{esc(eyebrow)}</span>
            <h1>{esc(o['title'])}</h1>
            {f'<p class="o-dek">{esc(o["summary"])}</p>' if o["summary"] else ''}
            <dl class="o-facts">
{facts_html}
            </dl>
          </div>
        </header>
        <div class="o-intro outing-text">
{intro_html}
        </div>
{map_html}
{chr(10).join(out)}
        <p class="outing-foot"><a href="/outings/">&larr; All outings</a></p>
      </article>"""
    data = {"photos": [{k: v for k, v in p.items() if k not in ("t", "n")} for p in shown]}
    leaflet = (f'  <link rel="stylesheet" href="{LEAFLET}/leaflet.min.css">\n'
               f'  <script src="{LEAFLET}/leaflet.min.js"></script>\n') if has_map else ""
    extra = (f"\n  {lightbox_html}\n  <script type=\"application/json\" id=\"outing-data\">{json.dumps(data, ensure_ascii=False)}</script>\n"
             f"{leaflet}  <script src=\"/script.js?v={js_v}\"></script>")
    ld = {"@context": "https://schema.org", "@graph": [person, {
        "@type": "Article", "headline": o["title"], "url": url, "datePublished": o["date"],
        "author": {"@id": f"{SITE}/#lee"}, "description": o["summary"],
        "image": [{"@type": "ImageObject", "contentUrl": f"{SITE}/images/{p['key']}", "caption": p["caption"],
                   "creator": {"@id": f"{SITE}/#lee"}, "creditText": NAME, "copyrightNotice": f"© {NAME}"} for p in shown]}]}
    o["cover_url"] = large_url(cover["key"]) if cover else "/logo.png"
    o["cover_caption"] = cover["caption"] if cover else ""
    page = outing_shell(f"{o['title']} | {NAME} Photography", o["summary"], url, o["cover_url"], ld, main, extra)
    # The tiles above are plain links so the page reads without JavaScript; script.js lays them out in rows.
    write(f"outings/{o['folder']}/index.html", page)

if outings or os.path.isdir(outings_dir):
    rows = []
    for o in outings:
        cover = o.get("cover_url", "/logo.png")
        n = len(o["photos"])
        rows.append(f"""        <a class="outing-row" href="/outings/{o['folder']}/">
          <img src="{esc(cover)}" alt="{esc(o.get('cover_caption', ''))}" loading="lazy">
          <div>
            <h2>{esc(o['title'])}</h2>
            <p class="outing-date">{esc(nice_date(o['date']))} · {n} photograph{'s' if n != 1 else ''}</p>
            <p class="lead">{esc(o['summary'])}</p>
            <span class="go">Read the outing &rarr;</span>
          </div>
        </a>""")
    main = f"""      <h1 class="page-title">Outings</h1>
      <div class="outing-list">
{chr(10).join(rows)}
      </div>"""
    ld = {"@context": "https://schema.org", "@graph": [person, {
        "@type": "CollectionPage", "name": f"Outings | {NAME} Photography", "url": f"{SITE}/outings/",
        "hasPart": [{"@type": "Article", "headline": o["title"], "url": f"{SITE}/outings/{o['folder']}/"} for o in outings]}]}
    first = outings[0].get("cover_url", "/logo.png") if outings else "/logo.png"
    write("outings/index.html", outing_shell(f"Outings | {NAME} Photography",
          f"Photo outings by {NAME} around the East Bay and the Peninsula: where I went, what the light did, and the photos that held up.",
          f"{SITE}/outings/", first, ld, main, f'\n  <script>document.getElementById("year").textContent = new Date().getFullYear();</script>'))
    write("outings/outings.json", json.dumps(photo_outings, ensure_ascii=False, indent=1) + "\n")

# ---------- sitemap ----------
urls = [f"""  <url>
    <loc>{SITE}/</loc>
    <lastmod>{TODAY}</lastmod>
  </url>"""]
for a in albums:
    imgs = "\n".join(f"""    <image:image><image:loc>{SITE}{esc(img_url(a['folder'], p['file'], None))}</image:loc></image:image>"""
                     for p in a["photos"])
    urls.append(f"""  <url>
    <loc>{SITE}/albums/{a['folder']}/</loc>
    <lastmod>{TODAY}</lastmod>
{imgs}
  </url>""")
if outings:
    urls.append(f"""  <url>
    <loc>{SITE}/outings/</loc>
    <lastmod>{TODAY}</lastmod>
  </url>""")
for o in outings:
    imgs = "\n".join(f"""    <image:image><image:loc>{SITE}/images/{esc(p['key'])}</image:loc></image:image>""" for p in o["photos"])
    urls.append(f"""  <url>
    <loc>{SITE}/outings/{o['folder']}/</loc>
    <lastmod>{TODAY}</lastmod>
{imgs}
  </url>""")
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
      'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(urls) + "\n</urlset>\n")

# ---------- robots.txt ----------
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")

# ---------- llms.txt ----------
lines = [f"# {NAME} Photography", "", f"> Photographs by {NAME}. {FACTS}", "", ABOUT, "",
         f"Instagram: {SAME_AS[0]}", f"Threads: {SAME_AS[1]}", f"YouTube (Overland Out & About): {SAME_AS[2]}",
         "Contact: harbor.lens.studio@gmail.com", "", "## Collections", ""]
for a in albums:
    lines.append(f"- [{a['title']}]({SITE}/albums/{a['folder']}/): {len(a['photos'])} photographs")
if outings:
    lines += ["", "## Outings", ""]
    for o in outings:
        lines.append(f"- [{o['title']}]({SITE}/outings/{o['folder']}/) ({o['date']}): {o['summary']}")
for a in albums:
    lines += ["", f"## {a['title']}", ""]
    for p in a["photos"]:
        lines.append(f"- [{p.get('caption') or p['file']}]({SITE}{img_url(a['folder'], p['file'])})")
write("llms.txt", "\n".join(lines) + "\n")

# ---------- index.html ----------
home_ld = {"@context": "https://schema.org", "@graph": [
    person,
    {"@type": "WebSite", "@id": f"{SITE}/#site", "name": f"{NAME} Photography", "url": f"{SITE}/",
     "author": {"@id": f"{SITE}/#lee"}},
    {"@type": "CollectionPage", "name": f"{NAME} Photography", "url": f"{SITE}/",
     "about": {"@id": f"{SITE}/#lee"},
     "hasPart": [{"@type": "ImageGallery", "name": a["title"], "url": f"{SITE}/albums/{a['folder']}/"} for a in albums]}]}
head_block = (f'<!-- seo:head:start (made by build-seo.py, do not edit by hand) -->\n'
              f'  <link rel="canonical" href="{SITE}/">\n'
              f'  <style>.static-index{{display:none}}</style>\n'
              f'  <script type="application/ld+json">{json.dumps(home_ld, ensure_ascii=False)}</script>\n'
              f'  <!-- seo:head:end -->')

parts = []
for a in albums:
    items = "".join(f"<li>{esc(p.get('caption') or p['file'])}</li>" for p in a["photos"])
    parts.append(f'<h3><a href="/albums/{a["folder"]}/">{esc(a["title"])}</a></h3><ul>{items}</ul>')
body_block = (f'<!-- seo:body:start (made by build-seo.py, do not edit by hand) -->\n'
              f'      <div id="static-index" class="static-index">'
              f'<h2>{NAME} Photography</h2><p>{esc(ABOUT)} {esc(FACTS)}</p>'
              f'<p>Collections, each with every photo and its caption:</p>{"".join(parts)}</div>\n'
              f'      <script>(function(){{var s=document.getElementById("static-index");if(s)s.remove();}})();</script>\n'
              f'      <!-- seo:body:end -->')

idx_path = os.path.join(ROOT, "index.html")
with open(idx_path, encoding="utf-8") as f:
    idx = f.read()
if "<!-- seo:head:start" in idx:
    idx = re.sub(r"<!-- seo:head:start.*?<!-- seo:head:end -->", lambda m: head_block, idx, flags=re.S)
else:
    idx = idx.replace("</head>", "  " + head_block + "\n</head>", 1)
if "<!-- seo:body:start" in idx:
    idx = re.sub(r"<!-- seo:body:start.*?<!-- seo:body:end -->", lambda m: body_block, idx, flags=re.S)
else:
    idx = idx.replace("</main>", "  " + body_block + "\n    </main>", 1)
with open(idx_path, "w", encoding="utf-8") as f:
    f.write(idx)

print(f"Done: {len(albums)} album pages, {len(outings)} outing pages, sitemap.xml, robots.txt, llms.txt, index.html updated.")
