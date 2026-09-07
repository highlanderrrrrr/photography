#!/usr/bin/env python3
"""
Scans each album folder listed in albums.json and adds any photo files
found there but not yet listed in that album's album.json, as plain
{"file": "..."} entries — no favorite/order/caption. Existing entries
(with captions, favorite, order) are left untouched.

Run this after dropping new photos into an album folder, before testing
or deploying.

Usage:
    python3 sync-albums.py
"""
import json
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".svg", ".webp"}


def dump_album(album: dict) -> str:
    """Serialize with one photo per line, matching the hand-written style —
    json.dump's default indent spreads every field across its own line,
    which gets unreadable fast."""
    photos = album.get("photos", [])
    other_fields = {k: v for k, v in album.items() if k != "photos"}

    lines = ["{"]
    for key, value in other_fields.items():
        lines.append(f'  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},')

    lines.append('  "photos": [')
    photo_lines = [
        "    " + json.dumps(p, ensure_ascii=False) for p in photos
    ]
    lines.append(",\n".join(photo_lines))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def sync_album(album_dir: Path):
    album_json_path = album_dir / "album.json"
    if not album_json_path.exists():
        print(f"  skip {album_dir.name}: no album.json found")
        return

    with open(album_json_path) as f:
        album = json.load(f)

    photos = album.setdefault("photos", [])
    listed_files = {p.get("file") for p in photos}

    found_files = sorted(
        p.name for p in album_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    added = []
    for filename in found_files:
        if filename not in listed_files:
            photos.append({"file": filename})
            added.append(filename)

    if added:
        with open(album_json_path, "w") as f:
            f.write(dump_album(album))
        print(f"  {album_dir.name}: added {len(added)} photo(s) — {', '.join(added)}")
    else:
        print(f"  {album_dir.name}: nothing new")


def main():
    root = Path(__file__).parent
    albums_json_path = root / "albums.json"

    if not albums_json_path.exists():
        print("albums.json not found — run this from the project root.")
        return

    with open(albums_json_path) as f:
        album_dirs = json.load(f)

    print(f"Syncing {len(album_dirs)} album(s)...")
    for dir_name in album_dirs:
        sync_album(root / "images" / dir_name)


if __name__ == "__main__":
    main()
