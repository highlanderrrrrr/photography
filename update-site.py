#!/usr/bin/env python3
"""Update leesagi.com after adding or changing photos. Run from the website folder:

    python3 update-site.py

What it does, for every photo in images/<album>/ and images/outings/<name>/:
  1. Keeps the GPS location (for the "View on map" link), except for photos taken
     within 1 mile of a place listed in private-places.txt, which lose it.
     No private-places.txt at all = GPS is removed from every photo, to be safe.
  2. Shrinks the main file to 2400px on the long side if it's bigger.
  3. Makes the two smaller copies the site uses:
       large/       1600px, for big tiles
       thumbnails/   800px, for small tiles
  4. Adds new photos to that album's album.json (at the end), with their size.
     Photos you deleted from the folder are removed from album.json too.
     For images/outings/<name>/, it does the same to outings/<name>/outing.txt.
  5. Runs build-seo.py, which rebuilds the album pages, Outings pages,
     sitemap.xml, robots.txt and llms.txt.

Nothing happens to a photo that's already done, so it's safe to run any time.

One-time setup on a new computer:  python3 -m pip install --user Pillow
"""
import json
import math
import os
import subprocess
import sys

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow isn't installed. Run this once:  python3 -m pip install --user Pillow")

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(ROOT, "images")
EXTS = (".jpg", ".jpeg")
MAIN_PX, LARGE_PX, THUMB_PX = 2400, 1600, 800
GPS_TAG, ORIENTATION_TAG = 0x8825, 0x0112
PRIVATE_FILE = os.path.join(ROOT, "private-places.txt")
PRIVATE_RADIUS_M = 1609.344  # 1 mile


# ---------- private places: never published, see .gitignore ----------

def load_private_places():
    """Read private-places.txt: one place per line, "name: latitude, longitude".
    Returns a list of (lat, lon), or None if the file doesn't exist."""
    if not os.path.isfile(PRIVATE_FILE):
        return None
    places = []
    with open(PRIVATE_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            nums = line.split(":", 1)[-1].replace(",", " ").split()
            try:
                places.append((float(nums[0]), float(nums[1])))
            except (ValueError, IndexError):
                print(f"  warning: private-places.txt: can't read the line \"{line}\" (use name: latitude, longitude)")
    return places


def check_private_file_not_published():
    try:
        tracked = subprocess.run(["git", "ls-files", "private-places.txt"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except OSError:
        return
    if tracked:
        print("  WARNING: private-places.txt is in git and will be uploaded. Run:  git rm --cached private-places.txt")


def gps_of(exif):
    """(lat, lon) from a Pillow Exif, or None."""
    g = exif.get_ifd(GPS_TAG)
    try:
        def deg(v):
            return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat = deg(g[2]) * (-1 if str(g.get(1, "N")).upper().startswith("S") else 1)
        lon = deg(g[4]) * (-1 if str(g.get(3, "E")).upper().startswith("W") else 1)
        return lat, lon
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return None


def distance_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def gps_must_go(path, places):
    """Why this photo's GPS has to be removed, or None if it may stay."""
    with Image.open(path) as im:
        exif = im.getexif()
        if GPS_TAG not in exif:
            return None
        if places is None:
            return "no private-places.txt"
        where = gps_of(exif)
    if where is None:
        return None
    if any(distance_m(where, p) <= PRIVATE_RADIUS_M for p in places):
        return "near a private place"
    return None


# ---------- EXIF: drop GPS without recompressing the photo ----------

def _segments(data):
    """Yield (start, end, marker) for each JPEG header segment before the image data."""
    i = 2
    while i < len(data) - 4 and data[i] == 0xFF:
        marker = data[i + 1]
        if marker == 0xDA:  # start of image data
            return
        length = int.from_bytes(data[i + 2:i + 4], "big")
        yield i, i + 2 + length, marker
        i += 2 + length


def strip_gps(path):
    """Remove the GPS block from a JPEG in place. Returns True if it had one."""
    with Image.open(path) as im:
        exif = im.getexif()
        if GPS_TAG not in exif:
            return False
        exif.get_ifd(0x8769)  # load the camera-settings block so it's written back
        del exif[GPS_TAG]
        new_exif = exif.tobytes()
    with open(path, "rb") as f:
        data = f.read()
    for start, end, marker in _segments(data):
        if marker == 0xE1 and data[start + 4:start + 10] == b"Exif\x00\x00":
            payload = new_exif if new_exif.startswith(b"Exif") else b"Exif\x00\x00" + new_exif
            segment = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
            with open(path, "wb") as f:
                f.write(data[:start] + segment + data[end:])
            return True
    return False


def exif_for_resize(im):
    """The photo's EXIF with orientation reset; GPS stays if the photo still has it."""
    exif = im.getexif()
    exif.get_ifd(0x8769)
    if GPS_TAG in exif:
        exif.get_ifd(GPS_TAG)
    if ORIENTATION_TAG in exif:
        exif[ORIENTATION_TAG] = 1
    return exif.tobytes()


# ---------- sizes ----------

def save_resized(im, path, px, quality, exif=None, icc=None):
    copy = im.copy()
    copy.thumbnail((px, px), Image.LANCZOS)
    kwargs = {"quality": quality, "optimize": True, "progressive": True}
    if exif:
        kwargs["exif"] = exif
    if icc:
        kwargs["icc_profile"] = icc
    copy.convert("RGB").save(path, "JPEG", **kwargs)


def process_folder(folder, places):
    """Handle every photo in one folder. Returns {file: (w, h)} for the photos found."""
    found = {}
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not (os.path.isfile(path) and name.lower().endswith(EXTS)):
            continue
        notes = []
        why = gps_must_go(path, places)
        if why and strip_gps(path):
            notes.append(f"removed GPS ({why})")
        with Image.open(path) as im:
            icc = im.info.get("icc_profile")
            needs_turn = im.getexif().get(ORIENTATION_TAG, 1) not in (1, None)
            if max(im.size) > MAIN_PX or needs_turn:
                upright = ImageOps.exif_transpose(im)
                exif = exif_for_resize(im)
                tmp = path + ".tmp"
                save_resized(upright, tmp, MAIN_PX, 90, exif, icc)
                os.replace(tmp, path)
                notes.append(f"shrunk to {MAIN_PX}px")
        with Image.open(path) as im:
            im.load()
            size = im.size
            for sub, px, q in (("large", LARGE_PX, 82), ("thumbnails", THUMB_PX, 80)):
                out = os.path.join(folder, sub, name)
                if os.path.exists(out):
                    if strip_gps(out):
                        notes.append(f"removed GPS from {sub}")
                    continue
                os.makedirs(os.path.dirname(out), exist_ok=True)
                save_resized(im, out, px, q, icc=icc)
                notes.append(f"made {sub}")
        found[name] = size
        if notes:
            print(f"  {os.path.relpath(path, ROOT)}: {', '.join(notes)}")
    return found


# ---------- album.json ----------

def dump_album(album):
    """One photo per line, like the hand-written files."""
    lines = ["{"]
    for key, value in album.items():
        if key != "photos":
            lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
    lines.append('  "photos": [')
    lines.append(",\n".join("    " + json.dumps(p, ensure_ascii=False) for p in album.get("photos", [])))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def update_album(folder, found):
    path = os.path.join(folder, "album.json")
    with open(path, encoding="utf-8") as f:
        album = json.load(f)
    photos = album.setdefault("photos", [])
    listed = {p["file"] for p in photos}
    changed = False
    kept = []
    for p in photos:
        if p["file"] not in found:
            print(f"  {os.path.basename(folder)}/album.json: removed {p['file']} (file is gone)")
            changed = True
            continue
        w, h = found[p["file"]]
        if (p.get("w"), p.get("h")) != (w, h):
            p["w"], p["h"] = w, h
            changed = True
        kept.append(p)
    for name, (w, h) in found.items():
        if name not in listed:
            kept.append({"file": name, "w": w, "h": h})
            print(f"  {os.path.basename(folder)}/album.json: added {name} (add a caption there if you like)")
            changed = True
    album["photos"] = kept
    if album.get("cover") and album["cover"] not in found and kept:
        album["cover"] = kept[0]["file"]
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(dump_album(album))


# ---------- outing.txt ----------

def is_photo_line(line):
    return bool(line) and ":" not in line.split("/")[0]


def photo_facts(folder, files):
    """Earliest date and a gear line ("Nikon D7500, 18-200mm") from the photos' EXIF."""
    import re
    days, cameras, lenses = [], [], []
    for name in files:
        try:
            with Image.open(os.path.join(folder, name)) as im:
                exif = im.getexif()
                sub = exif.get_ifd(0x8769)
        except OSError:
            continue
        stamp = str(sub.get(36867) or exif.get(306) or "")
        if len(stamp) >= 10:
            days.append(stamp[:10].replace(":", "-"))
        model = str(exif.get(0x0110) or "").strip()
        if model:
            model = " ".join(w.capitalize() if w.isalpha() and w.isupper() else w for w in model.split())
            if model not in cameras:
                cameras.append(model)
        lens = str(sub.get(0xA434) or "")
        m = re.search(r"(\d+(?:-\d+)?)mm", lens)
        if m:
            short = m.group(0) if "-" in m.group(1) else (m.group(0) + (" " + re.search(r"f/[\d.]+", lens).group(0) if re.search(r"f/[\d.]+", lens) else ""))
            if short not in lenses:
                lenses.append(short)
    gear = ", ".join(x for x in [" + ".join(cameras), " + ".join(lenses)] if x)
    return (min(days) if days else ""), gear


def create_outing(name, found):
    """A new folder in images/outings/ gets its outings/<name>/outing.txt started automatically."""
    date_iso, gear = photo_facts(os.path.join(IMAGES, "outings", name), list(found))
    title = " ".join(w.capitalize() for w in name.replace("_", "-").split("-") if w)
    os.makedirs(os.path.join(ROOT, "outings", name), exist_ok=True)
    with open(os.path.join(ROOT, "outings", name, "outing.txt"), "w", encoding="utf-8") as f:
        f.write(f"title: {title}\n"
                f"date: {date_iso}\n"
                f"gear: {gear}\n"
                f"summary: \n"
                f"cover: \n"
                f"light: \n"
                f"where: \n"
                f"frames: \n"
                f"photos:\n"
                f"---\n")
    print(f"  started outings/{name}/outing.txt (title, date and gear filled in from the photos; edit them as you like)")


def sync_outing(name, found):
    """Make outings/<name>/outing.txt list every photo in images/outings/<name>/.
    New photos are added at the end of the photos list; lines for deleted photos are removed.
    Album photos (the-streets/... and so on) are left alone."""
    path = os.path.join(ROOT, "outings", name, "outing.txt")
    if not os.path.isfile(path):
        create_outing(name, found)
    with open(path, encoding="utf-8") as f:
        lines = f.read().replace("\r\n", "\n").split("\n")
    prefix = f"outings/{name}/"
    end = lines.index("---") if "---" in lines else len(lines)
    start = next((i for i in range(end) if lines[i].strip().lower().startswith("photos:")), None)
    if start is None:
        lines.insert(end, "photos:")
        start, end = end, end + 1
    # the photos list runs from start+1 until the next "key:" line or the ---
    stop = start + 1
    while stop < end and (not lines[stop].strip() or is_photo_line(lines[stop].strip())):
        stop += 1
    listed, changed, block = set(), False, []
    for line in lines[start + 1:stop]:
        key = line.strip().partition(" | ")[0].strip()
        if key.startswith(prefix) and key[len(prefix):] not in found:
            print(f"  outings/{name}/outing.txt: removed {key} (file is gone)")
            changed = True
            continue
        listed.add(key)
        block.append(line)
    while block and not block[-1].strip():
        block.pop()
    for file in found:
        if prefix + file not in listed:
            block.append(prefix + file)
            print(f"  outings/{name}/outing.txt: added {prefix + file} (add \" | Title - comment\" if you like)")
            changed = True
    if changed:
        lines[start + 1:stop] = block
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def main():
    with open(os.path.join(ROOT, "albums.json"), encoding="utf-8") as f:
        albums = json.load(f).get("albums", [])
    places = load_private_places()
    check_private_file_not_published()
    if places is None:
        print("No private-places.txt, so GPS is removed from every photo (no map links).")
    print("Checking photos...")
    for album in albums:
        folder = os.path.join(IMAGES, album)
        if os.path.isdir(folder):
            update_album(folder, process_folder(folder, places))
    outings = os.path.join(IMAGES, "outings")
    if os.path.isdir(outings):
        for name in sorted(os.listdir(outings)):
            if os.path.isdir(os.path.join(outings, name)):
                sync_outing(name, process_folder(os.path.join(outings, name), places))
    print("Rebuilding pages...")
    subprocess.run([sys.executable, os.path.join(ROOT, "build-seo.py")], check=True)
    print("All done. Preview, then commit and push.")


# ---------- preview: python3 update-site.py --preview ----------

def watched_state():
    """Modification times of everything that changes the pages."""
    state = {}
    for base in ("outings", "images"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames[:] = [d for d in dirnames if d not in ("large", "thumbnails")]
            for n in filenames:
                if n.endswith((".txt", ".json", ".jpg", ".jpeg", ".JPG", ".JPEG")):
                    p = os.path.join(dirpath, n)
                    try:
                        state[p] = os.path.getmtime(p)
                    except OSError:
                        pass
    for n in ("albums.json", "private-places.txt"):
        p = os.path.join(ROOT, n)
        if os.path.exists(p):
            state[p] = os.path.getmtime(p)
    return state


def newest_outing():
    folder = os.path.join(ROOT, "outings")
    names = [n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n, "outing.txt"))] if os.path.isdir(folder) else []
    if not names:
        return "/"
    def latest(n):
        times = [os.path.getmtime(os.path.join(folder, n, "outing.txt"))]
        img = os.path.join(IMAGES, "outings", n)
        if os.path.isdir(img):
            times += [os.path.getmtime(os.path.join(img, f)) for f in os.listdir(img)]
        return max(times)
    return f"/outings/{max(names, key=latest)}/"


def preview():
    import functools
    import http.server
    import threading
    import time
    import webbrowser
    main()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=ROOT)
    server = None
    for port in range(8000, 8011):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    if not server:
        sys.exit("Couldn't start the preview: ports 8000-8010 are busy.")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://localhost:{server.server_port}{newest_outing()}"
    print(f"\nPreview: {url}")
    print("Edit and save; the pages rebuild by themselves. Press Cmd+Shift+R in Chrome to see changes.")
    print("Press Ctrl+C here when you're done.\n")
    webbrowser.open(url)
    state = watched_state()
    try:
        while True:
            time.sleep(1)
            now = watched_state()
            if now != state:
                time.sleep(0.5)  # let the save finish
                print(time.strftime("%H:%M:%S"), "change seen, rebuilding...")
                try:
                    main()
                except Exception as e:
                    print("  rebuild failed:", e)
                state = watched_state()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nPreview stopped. Next: git add -A, git commit -m \"...\", git push")


if __name__ == "__main__":
    if "--preview" in sys.argv[1:]:
        preview()
    else:
        main()
