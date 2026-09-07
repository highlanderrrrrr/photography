# Photo gallery — setup

Plain HTML/CSS/JS. No build step, no dependencies.

## File structure

```
photo-gallery/
├── index.html
├── style.css
├── script.js
├── albums.json              ← just lists album folder names, in display order
├── sync-albums.py
├── README.md
└── images/
    ├── sample-album-two/
    │   ├── album.json       ← this album's title, cover, and photos
    │   ├── photo-c.svg
    │   └── thumbnails/
    │       └── photo-c.svg  ← same filename, smaller/optimized version
    └── sample-album-one/
        ├── album.json
        ├── photo-a.svg
        ├── photo-b.svg
        └── thumbnails/
            └── photo-a.svg  ← photo-b has none — falls back to full-res
```

Each album is self-contained: its own folder, its own `album.json`, its own
photos. `albums.json` at the root only lists which folders exist and in what
order — it never repeats titles or photo lists, so it stays short no matter
how many albums or photos you have.

## 1. Test locally

```
python3 -m http.server 8000
```

Open `http://localhost:8000`. Don't double-click `index.html` directly —
`fetch()` is blocked under `file://`, and it'll silently show a blank page.

After **any** file edit, hard refresh: **Cmd+Shift+R**. Regular reload can
serve a stale cached copy.

## 2. albums.json

A flat array of folder names, in the order you want albums to appear on the
home page:

```json
["yreka-trip", "crater-lake"]
```

That's it. Reordering albums = reordering this array. No separate `order`
field, no titles, nothing else — everything about an album lives in its own
folder.

## 3. Each album's album.json

Lives inside that album's own folder, e.g. `images/yreka-trip/album.json`:

```json
{
  "title": "Yreka Trip",
  "cover": "01.jpg",
  "photos": [
    { "file": "01.jpg", "caption": "Optional", "favorite": true, "order": 1 },
    { "file": "02.jpg" }
  ]
}
```

- File paths (`cover`, each photo's `file`) are relative to this folder —
  just the filename, not `images/yreka-trip/01.jpg`. The app prepends the
  folder path automatically.
- `cover` — optional. Defaults to the first photo if omitted.
- `caption` — optional.
- `favorite: true` — pulls this photo onto the home page's Favorites row,
  in addition to it showing inside this album.
- `order` (on a photo) — controls position within the Favorites row (lower
  = earlier). Also controls position within this album's own grid, same
  rule (lower = earlier).

**Sort order within an album:** any photo with `favorite: true` and/or an
`order` number leads the grid (sorted by `order` where set). Every other
photo — no `favorite`, no `order` — just follows afterward, in whatever
order you listed it. So adding a plain photo you don't want to fuss over is
as simple as:

```json
{ "file": "05.jpg" }
```

No need to touch `favorite` or `order` unless you actually want that photo
prioritized.

## 4. Thumbnails

Every grid tile (favorites, an album's own photos, and album covers) looks
for a same-named file in that photo's `thumbnails/` subfolder first. If it's
not there, the tile falls back to the full-resolution original automatically
— no broken image, just slower to load until you add the thumbnail. The
lightbox (full-size view when you click a photo) always loads the original,
never the thumbnail.

```
images/yreka-trip/01.jpg              ← full resolution
images/yreka-trip/thumbnails/01.jpg   ← same filename, resized/compressed
```

You're resizing these yourself for now — long edge ~2000px, JPEG quality
~80 is a reasonable target for the thumbnail. `album.json` doesn't need any
changes to use this; the app checks the `thumbnails/` folder automatically
based on the filenames already listed there.

## 5. Add a new album

1. Create `images/<album-id>/` — lowercase, hyphens, no spaces (this
   doubles as the URL: `#album/<album-id>`).
2. Export/convert JPEGs into it (not RAW — browsers can't render NEF).
3. Add `album.json` inside that folder, per the format above (or just
   `{"title": "...", "photos": []}` — the sync script below fills in the
   photos).
4. Add the folder name to `albums.json`, wherever you want it to sort.
5. Once you have real albums in, delete `images/sample-album-one/`,
   `images/sample-album-two/`, and their entries in `albums.json`.

## 6. Adding plain photos without writing JSON by hand

Run this after dropping new photos into any album folder, before testing
or deploying:

```
python3 sync-albums.py
```

It scans every album listed in `albums.json`, finds any image file sitting
in that folder that isn't yet in `album.json`, and adds it as a plain
`{"file": "..."}` entry. Existing entries — captions, `favorite`, `order`
— are left untouched, so you can still hand-edit specific photos before or
after running it.

**Why this has to be a script you run, not something the live site does
automatically:** a static site has no way to ask "what files are in this
folder" once it's actually deployed — GitHub Pages, like any static host,
doesn't serve directory listings. A file sitting in the folder but not
listed in `album.json` simply won't appear. This script is what stands in
for that at build time, so you never have to write the JSON entry by hand
for a plain photo — you just have to remember to run it.

**Resizing is still on you for now** (see the Thumbnails section above) —
the mechanism is in place, but nothing generates the resized files
automatically yet. Say the word if you want that automated later.

## 7. Deploy to GitHub Pages

1. Create a repo (`yourusername.github.io` for root domain, or any other
   name for a project site).
2. Push everything at the repo root — `index.html`, `style.css`,
   `script.js`, `albums.json`, `/images` (with each album's folder,
   `album.json`, photos, and `thumbnails/` inside it). `sync-albums.py` is
   a local tool — it doesn't need to be deployed, though there's no harm
   leaving it in the repo.
3. Settings → Pages → source branch `main`, folder `/ (root)`.
4. Live in 1–2 minutes at the URL shown on that settings page. Album pages
   work as direct links too, e.g. `yourusername.github.io/#album/yreka-trip`.
