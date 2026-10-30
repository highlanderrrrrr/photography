# How to update leesagi.com

Everything runs from the website folder in Terminal:
`cd "/Users/lee/Google Drive Sync/Photography Website"`

## Add a photo to an album
1. Export from RapidRAW as JPEG, any size (the script shrinks it).
2. Drop it into `images/<album>/` (the-streets, faces, birds, land-and-sky, misc).
3. Run `python3 update-site.py`
4. Optional: open `images/<album>/album.json` and add a caption to the new line:
   `"caption": "Title - comment",` then run `python3 update-site.py` again.
5. Optional: to show it on the homepage, add `"<album>/<file>"` to the `homepage` list in `albums.json`.
6. Preview, commit and push (below).

`update-site.py` removes GPS location, shrinks the file to 2400px, makes the
`large/` and `thumbnails/` copies, updates album.json and rebuilds all pages.
Never edit `large/`, `thumbnails/`, `albums/`, `outings/*/index.html`,
`sitemap.xml` or `llms.txt` by hand; the scripts rewrite them.

## Remove a photo
Delete the file from `images/<album>/`, then run `python3 update-site.py`.
(Delete its copies in `large/` and `thumbnails/` too, to keep the folder clean.)

## New outing (the easy way)
1. Make a folder `images/outings/<name>/` (the name becomes the web address, e.g.
   `redwood-city-farmers-market`) and drop in the photos you picked.
2. Run `python3 update-site.py --preview`
   - It starts `outings/<name>/outing.txt` for you (title, date and gear from the photos),
     splits the photos into time sections (a new section after 20+ minutes without a photo,
     or a new day), adds a `## 8:47 a.m.` line for each section, and opens the page in Chrome.
   - Sections without text show a dim "Write about ... here" note. Only you see it, in preview.
3. Open `outings/<name>/outing.txt`, fill in title, summary, cover (best photo, e.g.
   `outings/<name>/<file>.jpg`), light, where, frames (optional), write the intro under `---`
   and the text for each time under its `##` line. Save; the page rebuilds. Cmd+Shift+R in Chrome.
   - `## 9:38 a.m. | Produce District` adds a small name under the time.
4. Ctrl+C in Terminal, then `git add -A`, `git commit -m "..."`, `git push`.

## outing.txt reference
    title: Oakland Chinatown - Murals, Vendors and the Produce Market
    date: 2026-10-26
    gear: Nikon D7500, 18-200mm
    summary: One or two sentences for the cover and the Outings list.
    cover: the-streets/2026-10-26-oakland-china-town-53.jpg
    light: Low, hard sun
    where: Oakland Chinatown and the Produce District
    frames: 105
    photos:
    the-streets/2026-10-26-oakland-china-town-53.jpg
    outings/oakland-chinatown-murals-vendors-produce-market/2026-10-26-oakland-china-town-17.jpg | Two Glances - comment
    ---
    Intro paragraphs (no time).

    ## 8:47 a.m. | Webster Street
    Text for that part of the day.

- Photos are placed by the time they were taken, not by their order in `photos:`.
  The cover is shown on top and not repeated below.
- Photos in `images/outings/<name>/` are added to `photos:` automatically. Album photos
  (`the-streets/...`) can be listed too.
- Rows: three photos fill the width; one or two are centered at the same height.
- Several paragraphs under one `##` time line: the photos are spread between them, in time
  order, in whole rows of three (text, photos, text, photos...). Keep the intro to 2-3 sentences
  so photos start near the top.

## Map links (GPS)
Photos keep their GPS location, and the full-screen viewer shows "View on map" for them.
Photos taken within 1 mile of a place in `private-places.txt` lose their GPS automatically.

- `private-places.txt` lives only on this Mac. It is never uploaded (it's in `.gitignore`).
  One place per line: `home: 37.6..., -122.0...` (right-click a spot in Google Maps to copy its numbers).
- No `private-places.txt` at all = GPS is removed from every photo, to be safe.
- To give photos already on the site their GPS back from the camera originals:
  `python3 copy-gps.py "<originals folder>" images/<album or outings/name>` then `python3 update-site.py`

## Preview, commit, push
1. `python3 -m http.server 8000`, open http://localhost:8000, look around
2. Ctrl+C to stop it
3. `git add -A`
4. `git commit -m "what changed"`
5. `git push`

## Undo everything since a tag
`git revert --no-edit <tag>..HEAD` then `git push`
Tags: `pre-cleanup-2026-10-28`, `pre-redesign-2026-10-28`, `pre-outings-2026-10-29`
