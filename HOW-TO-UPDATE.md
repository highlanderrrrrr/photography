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

## Write or edit an outing
Each outing is a folder in `outings/` with one file you edit: `outing.txt`.

    title: Oakland Chinatown - Murals, Vendors and the Produce Market
    date: 2026-10-26
    gear: Nikon D7500, 18-200mm
    summary: One or two sentences for the Outings list.
    photos:
    the-streets/2026-10-26-oakland-china-town-53.jpg
    outings/oakland-chinatown-murals-vendors-produce-market/library.jpg | Asian Branch - Morning outside the library.
    ---
    First paragraph.

    Second paragraph.

- `photos:` lists files under `images/`, in display order. The first one is the cover.
- A photo that's already in an album: list it as `<album>/<file>`. No copy needed.
- An outing-only photo (context shot): drop it in `images/outings/<outing-name>/`
  (same folder name as in `outings/`) and run `python3 update-site.py`. It's added to
  `photos:` automatically, at the end. Move the line to reorder, and add
  ` | Title - comment` after it for a caption. Delete the file and its line goes too.
- New outing: copy an existing outing folder, rename it (the name becomes the web
  address, e.g. `leesagi.com/outings/oakland-chinatown-murals-vendors-produce-market/`),
  and edit its `outing.txt`.
- Then run `python3 update-site.py`

## Preview, commit, push
1. `python3 -m http.server 8000`, open http://localhost:8000, look around
2. Ctrl+C to stop it
3. `git add -A`
4. `git commit -m "what changed"`
5. `git push`

## Undo everything since a tag
`git revert --no-edit <tag>..HEAD` then `git push`
Tags: `pre-cleanup-2026-10-28`, `pre-redesign-2026-10-28`, `pre-outings-2026-10-29`
