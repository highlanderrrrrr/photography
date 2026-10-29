// ============================================================
// Lee Sagi — Photography
//
// albums.json
//   "albums":   album folders under images/, in menu order
//   "homepage": the Work page, one "album/file" per line, in display order
// images/<album>/album.json
//   title, cover, and photos: {"file", "caption"?, "w"?, "h"?}
//   w/h (pixel size) let rows lay out before images load; without them
//   the row is laid out again once the photo arrives.
// Each photo can have up to three sizes, all with the same file name:
//   thumbnails/<file>  ~800px   small tiles
//   large/<file>       1600px   big tiles
//   <file>             original lightbox
// A missing size falls back to the next larger one.
// ============================================================

let albums = [];
let homepage = [];
let currentList = [];
let currentIndex = 0;
const exifCache = new Map();

const views = {
  work: document.getElementById('work-view'),
  collections: document.getElementById('collections-view'),
  album: document.getElementById('album-view'),
  about: document.getElementById('about-view'),
  contact: document.getElementById('contact-view')
};
const homeStrips = document.getElementById('home-strips');
const albumStrips = document.getElementById('album-strips');
const albumTitleEl = document.getElementById('album-title');
const collectionsGrid = document.getElementById('collections-grid');
const emptyState = document.getElementById('empty-state');

const lightbox = document.getElementById('lightbox');
const lbImage = document.getElementById('lb-image');
const lbCaption = document.getElementById('lb-caption');
const lbExif = document.getElementById('lb-exif');

// ---------- Loading ----------

fetch('albums.json')
  .then((res) => {
    if (!res.ok) throw new Error('albums.json not found');
    return res.json();
  })
  .then((payload) => {
    const dirs = Array.isArray(payload) ? payload : (payload.albums || []);
    return Promise.all(dirs.map((dir) => loadAlbum(dir).catch((err) => {
      console.warn('Skipping album', dir, err);
      return null;
    }))).then((loaded) => {
      albums = loaded.filter(Boolean);
      homepage = resolveHomepage(Array.isArray(payload) ? null : payload.homepage);
      route();
    });
  })
  .catch((err) => {
    console.error(err);
    emptyState.textContent = 'Could not load albums.json. Check the browser console.';
    emptyState.hidden = false;
  });

function loadAlbum(dir) {
  const base = 'images/' + dir + '/';
  return fetch(base + 'album.json')
    .then((res) => {
      if (!res.ok) throw new Error('album.json not found in ' + base);
      return res.json();
    })
    .then((album) => {
      const photos = (album.photos || []).map((p) => ({
        key: dir + '/' + p.file,
        file: base + p.file,
        large: base + 'large/' + p.file,
        thumb: base + 'thumbnails/' + p.file,
        caption: p.caption || '',
        favorite: p.favorite === true,
        ratio: p.w && p.h ? p.w / p.h : 0,
        albumTitle: album.title || dir
      }));
      const cover = photos.find((p) => album.cover && p.key === dir + '/' + album.cover) || photos[0];
      return { id: dir, title: album.title || dir, cover, photos };
    });
}

// "homepage" lists photos as "album/file". Unknown entries are skipped with a
// console warning. Without a list, photos marked "favorite" are used instead.
function resolveHomepage(list) {
  const byKey = new Map();
  albums.forEach((a) => a.photos.forEach((p) => byKey.set(p.key, p)));
  if (Array.isArray(list) && list.length) {
    return list.map((key) => {
      const p = byKey.get(key);
      if (!p) console.warn('homepage: no photo named', key);
      return p;
    }).filter(Boolean);
  }
  const favorites = [];
  albums.forEach((a) => a.photos.forEach((p) => { if (p.favorite) favorites.push(p); }));
  return favorites;
}

// ---------- Routing ----------

window.addEventListener('hashchange', route);

function route() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, ''));
  let view = 'work';
  let album = null;
  if (hash.startsWith('album/')) {
    album = albums.find((a) => a.id === hash.slice(6));
    view = album ? 'album' : 'collections';
  } else if (views[hash]) {
    view = hash;
  }

  Object.entries(views).forEach(([name, el]) => { el.hidden = name !== view; });
  document.querySelectorAll('nav a[data-view]').forEach((a) => {
    const active = a.dataset.view === view || (view === 'album' && a.dataset.view === 'collections');
    if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });

  if (view === 'work') {
    document.title = 'Lee Sagi — Photography';
    if (!homeStrips.childElementCount) buildStrips(homeStrips, homepage);
    layoutStrips(homeStrips);
  } else if (view === 'collections') {
    document.title = 'Collections — Lee Sagi';
    if (!collectionsGrid.childElementCount) buildCollections();
  } else if (view === 'album') {
    document.title = album.title + ' — Lee Sagi';
    albumTitleEl.textContent = album.title;
    if (albumStrips.dataset.album !== album.id) {
      albumStrips.dataset.album = album.id;
      buildStrips(albumStrips, album.photos);
    }
    layoutStrips(albumStrips);
  } else {
    document.title = view.charAt(0).toUpperCase() + view.slice(1) + ' — Lee Sagi';
  }
  window.scrollTo(0, 0);
}

// ---------- Collections ----------

function buildCollections() {
  albums.forEach((album) => {
    const a = document.createElement('a');
    a.className = 'collection';
    a.href = '#album/' + encodeURIComponent(album.id);
    const img = document.createElement('img');
    img.alt = '';
    img.loading = 'lazy';
    if (album.cover) setSource(img, [album.cover.large, album.cover.file]);
    const name = document.createElement('span');
    name.className = 'collection-name';
    name.textContent = album.title;
    const count = document.createElement('span');
    count.className = 'collection-count';
    count.textContent = album.photos.length + (album.photos.length === 1 ? ' photo' : ' photos');
    a.append(img, name, count);
    collectionsGrid.appendChild(a);
  });
}

// ---------- Photo rows ----------

function buildStrips(container, photos) {
  container.innerHTML = '';
  photos.forEach((photo, index) => {
    const tile = document.createElement('button');
    tile.type = 'button';
    tile.className = 'tile';
    tile.setAttribute('aria-label', photo.caption ? 'Open: ' + photo.caption : 'Open photo ' + (index + 1));
    tile.style.setProperty('--ar', photo.ratio || 1.5);
    tile.photo = photo;

    const img = document.createElement('img');
    img.alt = photo.caption || '';
    img.decoding = 'async';
    if (index < 3) { img.loading = 'eager'; img.fetchPriority = 'high'; } else { img.loading = 'lazy'; }
    if (!photo.ratio) {
      // No w/h in album.json: lay the row out again once the real shape is known.
      img.addEventListener('load', () => {
        if (!img.naturalWidth) return;
        photo.ratio = img.naturalWidth / img.naturalHeight;
        tile.style.setProperty('--ar', photo.ratio);
        layoutStrips(container);
      }, { once: true });
    }
    tile.appendChild(img);
    tile.addEventListener('click', () => openLightbox(photos, index));
    container.appendChild(tile);
  });
}

// Splits photos into rows that exactly fill the width. Breaks are chosen so
// rows stay near the target height, rows with a vertical photo may run taller
// (so it isn't squeezed), and three photos per row is preferred.
function layoutStrips(container) {
  if (!container || container.offsetParent === null) return;
  const tiles = Array.from(container.children);
  if (!tiles.length) return;
  const ar = tiles.map((t) => t.photo.ratio || 1.5);
  const W = container.getBoundingClientRect().width - 1;
  const gap = parseFloat(getComputedStyle(container).columnGap) || 0;
  const wide = W > 700;
  // Above phone width the row height scales with the page (460px at a 1354px grid),
  // so a narrower window shows the same rows, just smaller.
  const target = wide ? W * (460 / 1354) : parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--row'));
  const preferThree = wide ? Math.pow(target * 0.9, 2) : 0;

  const n = ar.length;
  const best = new Array(n + 1).fill(Infinity);
  const cut = new Array(n + 1).fill(0);
  best[0] = 0;
  for (let j = 1; j <= n; j++) {
    let sum = 0;
    for (let i = j - 1; i >= 0; i--) {
      sum += ar[i];
      const k = j - i;
      const h = (W - gap * (k - 1)) / sum;
      if (h < target * 0.45) break;
      let tall = 0;
      for (let x = i; x < j; x++) if (ar[x] < 1) tall++;
      const goal = tall ? target * 1.45 : target;
      let cost = best[i] + Math.pow(h - goal, 2);
      for (let x = i; x < j; x++) if (ar[x] < 1 && ar[x] * h < W * 0.26) cost += Math.pow(W * 0.26 - ar[x] * h, 2) * 4;
      if (k !== 3) cost += preferThree;
      if (cost < best[j]) { best[j] = cost; cut[j] = i; }
    }
  }
  const rows = [];
  for (let j = n; j > 0; j = cut[j]) rows.unshift([cut[j], j]);

  const dpr = window.devicePixelRatio || 1;
  rows.forEach(([i, j]) => {
    let sum = 0;
    for (let x = i; x < j; x++) sum += ar[x];
    const h = (W - gap * (j - i - 1)) / sum;
    for (let x = i; x < j; x++) {
      const w = ar[x] * h;
      tiles[x].style.width = w + 'px';
      tiles[x].style.height = h + 'px';
      pickSize(tiles[x].querySelector('img'), tiles[x].photo, Math.max(w, h) * dpr);
    }
  });
}

// Smallest file that's sharp at this tile size; only ever upgrades.
function pickSize(img, photo, neededPx) {
  const level = neededPx <= 760 ? 0 : 1;
  if (img.dataset.level !== undefined && Number(img.dataset.level) >= level) return;
  img.dataset.level = level;
  setSource(img, level === 0 ? [photo.thumb, photo.large, photo.file] : [photo.large, photo.file]);
}

function setSource(img, candidates) {
  let i = 0;
  img.onerror = () => { i += 1; if (i < candidates.length) img.src = candidates[i]; };
  img.src = candidates[0];
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { layoutStrips(homeStrips); layoutStrips(albumStrips); }, 80);
});

// ---------- Lightbox ----------

async function getPhotoMeta(photo) {
  if (exifCache.has(photo.file)) return exifCache.get(photo.file);
  let text = '';
  if (window.exifr) {
    const tags = await window.exifr.parse(photo.file, ['Make', 'Model', 'FocalLength', 'FNumber', 'ExposureTime', 'ISO']).catch(() => null);
    if (tags) {
      const parts = [];
      const camera = tags.Model || tags.Make;
      if (camera) parts.push(camera);
      if (tags.FocalLength) parts.push(Math.round(tags.FocalLength) + 'mm');
      if (tags.FNumber) parts.push('ƒ/' + tags.FNumber);
      if (tags.ExposureTime) parts.push(tags.ExposureTime >= 1 ? tags.ExposureTime + 's' : '1/' + Math.round(1 / tags.ExposureTime) + 's');
      if (tags.ISO) parts.push('ISO ' + tags.ISO);
      text = parts.join(' · ');
    }
  }
  exifCache.set(photo.file, text);
  return text;
}

function openLightbox(list, index) {
  currentList = list;
  currentIndex = index;
  showCurrent();
  lightbox.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  lightbox.hidden = true;
  document.body.style.overflow = '';
}

async function showCurrent() {
  const photo = currentList[currentIndex];
  lbImage.alt = photo.caption || '';
  setSource(lbImage, [photo.file, photo.large]);
  lbCaption.textContent = photo.caption || '';
  lbExif.textContent = '';
  const next = currentList[(currentIndex + 1) % currentList.length];
  if (next) { const pre = new Image(); pre.src = next.file; }
  const meta = await getPhotoMeta(photo);
  if (currentList[currentIndex] === photo) lbExif.textContent = meta;
}

function showNext() { currentIndex = (currentIndex + 1) % currentList.length; showCurrent(); }
function showPrev() { currentIndex = (currentIndex - 1 + currentList.length) % currentList.length; showCurrent(); }

document.getElementById('lb-close').addEventListener('click', closeLightbox);
document.getElementById('lb-next').addEventListener('click', showNext);
document.getElementById('lb-prev').addEventListener('click', showPrev);
lightbox.addEventListener('click', (e) => { if (e.target === lightbox) closeLightbox(); });

document.addEventListener('keydown', (e) => {
  if (lightbox.hidden) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowRight') showNext();
  if (e.key === 'ArrowLeft') showPrev();
});

// Swipe on touch screens
let touchX = 0;
let touchY = 0;
lightbox.addEventListener('touchstart', (e) => {
  if (e.touches.length !== 1) return;
  touchX = e.touches[0].clientX;
  touchY = e.touches[0].clientY;
}, { passive: true });
lightbox.addEventListener('touchend', (e) => {
  const t = e.changedTouches[0];
  if (!t) return;
  const dx = t.clientX - touchX;
  const dy = t.clientY - touchY;
  if (Math.abs(dx) < 45 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
  if (dx < 0) showNext(); else showPrev();
}, { passive: true });

document.getElementById('year').textContent = new Date().getFullYear();
