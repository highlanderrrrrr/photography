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
from datetime import date

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
            "gear": meta.get("gear", ""), "summary": meta.get("summary", ""), "photos": photos, "paras": paras}


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


photo_outings = {}
for o in outings:
    url = f"{SITE}/outings/{o['folder']}/"
    short = o["title"].split(" - ")[0].strip()
    for p in o["photos"]:
        photo_outings.setdefault(p["key"], {"url": f"/outings/{o['folder']}/", "short": short})
    paras = "\n".join(f"          <p>{esc(t)}</p>" for t in o["paras"])
    tiles = "\n".join(
        f'          <a class="tile" href="{esc(large_url(p["key"]))}" style="width:{round(300 * (p["w"] / p["h"])) if p["w"] else 300}px;height:300px">'
        f'<img src="{esc(large_url(p["key"]))}" alt="{esc(p["caption"])}" loading="lazy"></a>'
        for p in o["photos"])
    main = f"""      <article>
        <header class="outing-head">
          <a class="back" href="/outings/">&larr; Outings</a>
          <h1>{esc(o['title'])}</h1>
          <p class="outing-date">{esc(nice_date(o['date']))}{' · ' + esc(o['gear']) if o['gear'] else ''}</p>
        </header>
        <div class="outing-text">
{paras}
        </div>
        <div id="outing-strips" class="strips" aria-label="Photographs">
{tiles}
        </div>
        <p class="outing-foot"><a href="/outings/">&larr; All outings</a></p>
      </article>"""
    data = {"photos": o["photos"]}
    extra = (f"\n  {lightbox_html}\n  <script type=\"application/json\" id=\"outing-data\">{json.dumps(data, ensure_ascii=False)}</script>\n"
             f"  <script src=\"/script.js?v={js_v}\"></script>")
    ld = {"@context": "https://schema.org", "@graph": [person, {
        "@type": "Article", "headline": o["title"], "url": url, "datePublished": o["date"],
        "author": {"@id": f"{SITE}/#lee"}, "description": o["summary"],
        "image": [{"@type": "ImageObject", "contentUrl": f"{SITE}/images/{p['key']}", "caption": p["caption"],
                   "creator": {"@id": f"{SITE}/#lee"}, "creditText": NAME, "copyrightNotice": f"© {NAME}"} for p in o["photos"]]}]}
    cover = large_url(o["photos"][0]["key"]) if o["photos"] else "/logo.png"
    page = outing_shell(f"{o['title']} | {NAME} Photography", o["summary"], url, cover, ld, main, extra)
    # The tiles above are plain links so the page reads without JavaScript; script.js rebuilds them as the photo rows.
    write(f"outings/{o['folder']}/index.html", page)

if outings or os.path.isdir(outings_dir):
    rows = []
    for o in outings:
        cover = large_url(o["photos"][0]["key"]) if o["photos"] else "/logo.png"
        n = len(o["photos"])
        rows.append(f"""        <a class="outing-row" href="/outings/{o['folder']}/">
          <img src="{esc(cover)}" alt="{esc(o['photos'][0]['caption'] if o['photos'] else '')}" loading="lazy">
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
    first = large_url(outings[0]["photos"][0]["key"]) if outings and outings[0]["photos"] else "/logo.png"
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
