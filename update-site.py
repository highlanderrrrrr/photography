#!/usr/bin/env python3
"""Update leesagi.com after adding or changing photos. Run from the website folder:

    python3 update-site.py

What it does, for every photo in images/<album>/ and images/outings/<name>/:
  1. Removes GPS location from the file (camera, lens and settings stay).
  2. Shrinks the main file to 2400px on the long side if it's bigger.
  3. Makes the two smaller copies the site uses:
       large/       1600px, for big tiles
       thumbnails/   800px, for small tiles
  4. Adds new photos to that album's album.json (at the end), with their size.
     Photos you deleted from the folder are removed from album.json too.
  5. Runs build-seo.py, which rebuilds the album pages, Outings pages,
     sitemap.xml, robots.txt and llms.txt.

Nothing happens to a photo that's already done, so it's safe to run any time.

One-time setup on a new computer:  python3 -m pip install --user Pillow
"""
import json
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


def exif_without_gps(im):
    exif = im.getexif()
    exif.get_ifd(0x8769)
    if GPS_TAG in exif:
        del exif[GPS_TAG]
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


def process_folder(folder):
    """Handle every photo in one folder. Returns {file: (w, h)} for the photos found."""
    found = {}
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not (os.path.isfile(path) and name.lower().endswith(EXTS)):
            continue
        notes = []
        if strip_gps(path):
            notes.append("removed GPS")
        with Image.open(path) as im:
            icc = im.info.get("icc_profile")
            needs_turn = im.getexif().get(ORIENTATION_TAG, 1) not in (1, None)
            if max(im.size) > MAIN_PX or needs_turn:
                upright = ImageOps.exif_transpose(im)
                exif = exif_without_gps(im)
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


def main():
    with open(os.path.join(ROOT, "albums.json"), encoding="utf-8") as f:
        albums = json.load(f).get("albums", [])
    print("Checking photos...")
    for album in albums:
        folder = os.path.join(IMAGES, album)
        if os.path.isdir(folder):
            update_album(folder, process_folder(folder))
    outings = os.path.join(IMAGES, "outings")
    if os.path.isdir(outings):
        for name in sorted(os.listdir(outings)):
            if os.path.isdir(os.path.join(outings, name)):
                process_folder(os.path.join(outings, name))
    print("Rebuilding pages...")
    subprocess.run([sys.executable, os.path.join(ROOT, "build-seo.py")], check=True)
    print("All done. Preview, then commit and push.")


if __name__ == "__main__":
    main()
