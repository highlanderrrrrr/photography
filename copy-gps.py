#!/usr/bin/env python3
"""Copy GPS locations from your original camera JPEGs into photos already on the site.

    python3 copy-gps.py "<folder with the originals>" "<site photo folder>"

Example:
    python3 copy-gps.py "/Volumes/SSD/Photography/2026-10-26-oakland-china-town" images/outings/oakland-chinatown-murals-vendors-produce-market

Photos are matched by file name (the site photo 2026-10-26-oakland-china-town-17.jpg takes
the GPS from the original with that same name). The photo itself isn't recompressed.
Afterwards run  python3 update-site.py  as usual; it still removes GPS from anything
within 1 mile of a place in private-places.txt.
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow isn't installed. Run this once:  python3 -m pip install --user Pillow")

GPS_TAG = 0x8825
EXTS = (".jpg", ".jpeg")


def segments(data):
    i = 2
    while i < len(data) - 4 and data[i] == 0xFF:
        marker = data[i + 1]
        if marker == 0xDA:
            return
        length = int.from_bytes(data[i + 2:i + 4], "big")
        yield i, i + 2 + length, marker
        i += 2 + length


def write_exif(path, exif_bytes):
    """Replace (or add) the EXIF block of a JPEG without touching the image data."""
    payload = exif_bytes if exif_bytes.startswith(b"Exif") else b"Exif\x00\x00" + exif_bytes
    segment = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
    with open(path, "rb") as f:
        data = f.read()
    for start, end, marker in segments(data):
        if marker == 0xE1 and data[start + 4:start + 10] == b"Exif\x00\x00":
            data = data[:start] + segment + data[end:]
            break
    else:
        data = data[:2] + segment + data[2:]
    with open(path, "wb") as f:
        f.write(data)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source, target = sys.argv[1], sys.argv[2]
    for folder in (source, target):
        if not os.path.isdir(folder):
            sys.exit(f"Can't find the folder: {folder}")
    originals = {n.lower(): os.path.join(source, n) for n in os.listdir(source)}
    copied = missing = no_gps = 0
    for name in sorted(os.listdir(target)):
        path = os.path.join(target, name)
        if not (os.path.isfile(path) and name.lower().endswith(EXTS)):
            continue
        original = originals.get(name.lower())
        if not original:
            print(f"  {name}: no original with this name, skipped")
            missing += 1
            continue
        with Image.open(original) as im:
            gps = dict(im.getexif().get_ifd(GPS_TAG))
        if not gps.get(2) or not gps.get(4):
            print(f"  {name}: the original has no GPS, skipped")
            no_gps += 1
            continue
        with Image.open(path) as im:
            exif = im.getexif()
            exif.get_ifd(0x8769)
            exif.get_ifd(GPS_TAG).update(gps)
            new_exif = exif.tobytes()
        write_exif(path, new_exif)
        print(f"  {name}: GPS copied")
        copied += 1
    print(f"Done: {copied} copied, {no_gps} originals without GPS, {missing} without an original.")
    print("Now run:  python3 update-site.py")


if __name__ == "__main__":
    main()
