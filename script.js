let data = { albums: [], featured: null };
let currentList = [];
let currentIndex = 0;
const exifCache = new Map();
const exifRawCache = new Map();

const homeView = document.getElementById('home-view');
const heroSection = document.getElementById('hero-section');
const heroFrame = document.getElementById('hero-frame');
const heroImage = document.getElementById('hero-image');
const heroSidebarTitle = document.getElementById('hero-sidebar-title');
const heroSidebarCaption = document.getElementById('hero-sidebar-caption');
const heroMetaCamera = document.getElementById('hero-meta-camera');
const heroMetaLens = document.getElementById('hero-meta-lens');
const heroMetaExposure = document.getElementById('hero-meta-exposure');
const heroMetaIso = document.getElementById('hero-meta-iso');
const heroExpandBtn = document.getElementById('hero-expand-btn');

const albumsSection = document.getElementById('albums-section');
const favoritesSection = document.getElementById('favorites-section');
const albumsGrid = document.getElementById('albums-grid');
const favoritesGrid = document.getElementById('favorites-grid');

const albumView = document.getElementById('album-view');
const albumGrid = document.getElementById('album-grid');
const albumTitleEl = document.getElementById('album-title');

const emptyState = document.getElementById('empty-state');
const lightbox = document.getElementById('lightbox');
const lbImage = document.getElementById('lb-image');
const lbCaption = document.getElementById('lb-caption');
const lbExif = document.getElementById('lb-exif');
const lbClose = document.getElementById('lb-close');
const lbPrev = document.getElementById('lb-prev');
const lbNext = document.getElementById('lb-next');

fetch('albums.json')
  .then((res) => {
    if (!res.ok) throw new Error('albums.json not found');
    return res.json();
  })
  .then((payload) => {
    let dirs = [];
    if (Array.isArray(payload)) {
      dirs = payload;
      data.featured = null;
    } else if (payload && typeof payload === 'object') {
      dirs = payload.albums || [];
      data.featured = payload.featured || null;
    }

    return Promise.all(
      dirs.map((dir) =>
        loadAlbum(dir).catch((err) => {
          console.warn('Skipping album directory:', dir, err);
          return null;
        })
      )
    );
  })
  .then((albums) => {
    data.albums = albums.filter(Boolean);
    if (data.albums.length === 0 && !data.featured) {
      emptyState.textContent = 'No albums loaded. Check folder names in /images.';
      emptyState.hidden = false;
      return;
    }
    updateStatsLine();
    route();
  })
  .catch((err) => {
    console.error('Could not load albums.json:', err);
    emptyState.textContent = 'Could not load albums.json. Check browser console.';
    emptyState.hidden = false;
  });

function loadAlbum(dir) {
  const base = 'images/' + dir + '/';
  return fetch(base + 'album.json')
    .then((res) => {
      if (!res.ok) throw new Error('album.json not found at ' + base + 'album.json');
      return res.json();
    })
    .then((album) => {
      const photos = (album.photos || []).map((p) => Object.assign({}, p, {
        file: base + p.file,
        thumb: base + 'thumbnails/' + p.file,
        albumTitle: album.title || dir
      }));
      const coverFile = album.cover ? base + album.cover : (photos[0] && photos[0].file) || '';
      const coverThumb = album.cover ? base + 'thumbnails/' + album.cover : (photos[0] && photos[0].thumb) || '';
      return {
        id: dir,
        title: album.title || dir,
        cover: coverFile,
        coverThumb: coverThumb,
        photos: photos
      };
    });
}

window.addEventListener('hashchange', route);

function updateStatsLine() {
  const statsEl = document.getElementById('stats-line');
  if (!statsEl) return;
  const albumCount = (data.albums || []).length;
  const photoCount = (data.albums || []).reduce((sum, a) => sum + (a.photos ? a.photos.length : 0), 0);
  if (!albumCount && !photoCount) {
    statsEl.hidden = true;
    return;
  }
  const albumText = albumCount + (albumCount === 1 ? ' album' : ' albums');
  const photoText = photoCount + (photoCount === 1 ? ' photo' : ' photos');
  statsEl.textContent = `${albumText} · ${photoText}`;
  statsEl.hidden = false;
}

function route() {
  const hash = location.hash;
  if (hash.startsWith('#album/')) {
    const id = decodeURIComponent(hash.slice('#album/'.length));
    const album = data.albums.find((a) => a.id === id);
    if (album) {
      showAlbum(album);
      return;
    }
  }
  showHome();
}

function showHome() {
  albumView.hidden = true;
  homeView.hidden = false;
  document.title = 'Lee\'s Photography';
  renderHome();
}

function showAlbum(album) {
  homeView.hidden = true;
  albumView.hidden = false;
  document.title = album.title + ' — Lee\'s Photography';
  albumTitleEl.textContent = album.title;
  renderAlbumGrid(album);
}

function sortPhotos(list) {
  return list.slice().sort((a, b) => {
    const aMarked = a.favorite === true || typeof a.order === 'number';
    const bMarked = b.favorite === true || typeof b.order === 'number';
    if (aMarked !== bMarked) return aMarked ? -1 : 1;
    if (aMarked) {
      const ao = typeof a.order === 'number' ? a.order : Number.MAX_SAFE_INTEGER;
      const bo = typeof b.order === 'number' ? b.order : Number.MAX_SAFE_INTEGER;
      return ao - bo;
    }
    return 0;
  });
}

function getFavorites() {
  const favorites = [];
  (data.albums || []).forEach((album) => {
    (album.photos || []).forEach((photo) => {
      if (photo.favorite) favorites.push(photo);
    });
  });
  return sortPhotos(favorites);
}

// Full raw EXIF parsing helper
async function parseRawExif(filePath) {
  if (exifRawCache.has(filePath)) {
    return exifRawCache.get(filePath);
  }

  if (typeof window.exifr === 'undefined') return null;

  try {
    let tags = await window.exifr.parse(filePath, [
      'Make',
      'Model',
      'LensModel',
      'FocalLength',
      'FNumber',
      'ExposureTime',
      'ISO'
    ]).catch(() => null);

    if (!tags) {
      const response = await fetch(filePath, { headers: { Range: 'bytes=0-65535' } }).catch(() => null);
      if (response && (response.status === 200 || response.status === 206)) {
        const buffer = await response.arrayBuffer();
        tags = await window.exifr.parse(buffer, [
          'Make',
          'Model',
          'LensModel',
          'FocalLength',
          'FNumber',
          'ExposureTime',
          'ISO'
        ]).catch(() => null);
      }
    }

    exifRawCache.set(filePath, tags || null);
    return tags;
  } catch (err) {
    exifRawCache.set(filePath, null);
    return null;
  }
}

async function getPhotoMeta(photo) {
  if (exifCache.has(photo.file)) {
    return exifCache.get(photo.file);
  }

  const tags = await parseRawExif(photo.file);
  if (tags) {
    const parts = [];
    const camera = tags.Model || tags.Make;
    if (camera) parts.push(camera);
    if (tags.FocalLength) parts.push(`${Math.round(tags.FocalLength)}mm`);
    if (tags.FNumber) parts.push(`ƒ/${tags.FNumber}`);
    if (tags.ExposureTime) {
      const shutter = tags.ExposureTime >= 1
        ? `${tags.ExposureTime}s`
        : `1/${Math.round(1 / tags.ExposureTime)}s`;
      parts.push(shutter);
    }
    if (tags.ISO) parts.push(`ISO ${tags.ISO}`);

    if (parts.length > 0) {
      const formatted = parts.join(' · ');
      exifCache.set(photo.file, formatted);
      return formatted;
    }
  }

  if (photo.meta || photo.camera) {
    return photo.meta || photo.camera;
  }

  exifCache.set(photo.file, '');
  return '';
}

const MASONRY_ROW_UNIT = 4;
const MASONRY_GAP = 16;

function applyMasonrySpan(item, img) {
  const columnWidth = item.getBoundingClientRect().width;
  if (!columnWidth || !img.naturalWidth) return;
  const scaledHeight = (img.naturalHeight / img.naturalWidth) * columnWidth;
  const span = Math.ceil((scaledHeight + MASONRY_GAP) / (MASONRY_ROW_UNIT + MASONRY_GAP));
  item.style.gridRowEnd = 'span ' + span;
}

function setUpMasonryTile(item, img) {
  function measure() {
    requestAnimationFrame(() => applyMasonrySpan(item, img));
  }
  if (img.complete && img.naturalWidth) {
    measure();
  } else {
    img.addEventListener('load', measure);
  }
}

let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    document.querySelectorAll('.photo-grid .gallery-item').forEach((item) => {
      const img = item.querySelector('img');
      if (img && img.naturalWidth) applyMasonrySpan(item, img);
    });
  }, 100);
});

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { rootMargin: '0px 0px -40px 0px', threshold: 0.05 });

function loadWithFallback(img, primarySrc, fallbackSrc) {
  img.src = primarySrc;
  if (!fallbackSrc || fallbackSrc === primarySrc) return;
  img.addEventListener('error', function onError() {
    img.removeEventListener('error', onError);
    img.src = fallbackSrc;
  });
}

function renderHome() {
  revealObserver.disconnect();
  albumsGrid.innerHTML = '';
  favoritesGrid.innerHTML = '';
  emptyState.hidden = true;

  const albums = data.albums || [];
  const favorites = getFavorites();

  albumsSection.hidden = albums.length === 0;
  favoritesSection.hidden = favorites.length === 0;

  const heroTarget = data.featured || favorites[0] || (albums[0] && albums[0].photos[0]);
  if (heroTarget) {
    heroImage.src = heroTarget.file;
    heroSection.hidden = false;

    const openHero = () => openLightbox([heroTarget], 0);
    heroFrame.onclick = openHero;
    if (heroExpandBtn) heroExpandBtn.onclick = openHero;

    // Sidebar text & EXIF population
    if (heroSidebarTitle) {
      heroSidebarTitle.textContent = heroTarget.caption || heroTarget.albumTitle || 'Selected Work';
    }
    if (heroSidebarCaption) {
      if (heroTarget.description) {
        heroSidebarCaption.textContent = heroTarget.description;
        heroSidebarCaption.hidden = false;
      } else {
        heroSidebarCaption.textContent = '';
        heroSidebarCaption.hidden = true;
      }
    }

    parseRawExif(heroTarget.file).then((tags) => {
      if (tags) {
        if (heroMetaCamera) heroMetaCamera.textContent = tags.Model || tags.Make || 'Nikon Digital';
        if (heroMetaLens) {
          const fl = tags.FocalLength ? `${Math.round(tags.FocalLength)}mm` : '';
          const fn = tags.FNumber ? `ƒ/${tags.FNumber}` : '';
          heroMetaLens.textContent = [fl, fn].filter(Boolean).join(' ') || (tags.LensModel || 'Prime');
        }
        if (heroMetaExposure) {
          if (tags.ExposureTime) {
            const shutter = tags.ExposureTime >= 1 ? `${tags.ExposureTime}s` : `1/${Math.round(1 / tags.ExposureTime)}s`;
            heroMetaExposure.textContent = shutter;
          }
        }
        if (heroMetaIso) {
          if (tags.ISO) heroMetaIso.textContent = `ISO ${tags.ISO}`;
        }
      }
    });
  } else {
    heroSection.hidden = true;
  }

  albums.forEach((album, index) => {
    const item = document.createElement('a');
    item.className = 'gallery-item album-item is-visible';
    item.href = '#album/' + encodeURIComponent(album.id);

    const img = document.createElement('img');
    img.alt = album.title;
    img.loading = 'lazy';
    loadWithFallback(img, album.coverThumb, album.cover);
    item.appendChild(img);

    const label = document.createElement('div');
    label.className = 'item-caption';
    const count = album.photos.length;
    const countLabel = count === 1 ? '1 photo' : `${count} photos`;
    label.innerHTML = `
      <span style="font-family: var(--mono-font); font-size: 0.65rem; color: rgba(255,255,255,0.4); letter-spacing: 0.15em; margin-bottom: 0.25rem;">ROLL // ${String(index + 1).padStart(2, '0')}</span>
      <span class="album-name">${album.title}</span>
      <span class="album-count">${countLabel}</span>
    `;
    item.appendChild(label);
    albumsGrid.appendChild(item);
  });

  favorites.forEach((photo, index) => {
    favoritesGrid.appendChild(createPhotoTile(photo, index, favorites));
  });
}

function renderAlbumGrid(album) {
  revealObserver.disconnect();
  albumGrid.innerHTML = '';
  const photos = sortPhotos(album.photos || []);
  photos.forEach((photo, index) => {
    albumGrid.appendChild(createPhotoTile(photo, index, photos));
  });
}

function createPhotoTile(photo, index, list) {
  const item = document.createElement('div');
  item.className = 'gallery-item';
  item.tabIndex = 0;
  item.setAttribute('role', 'button');
  item.setAttribute('aria-label', photo.caption || 'Photo ' + (index + 1));
  
  item.style.transitionDelay = `${Math.min(index * 35, 300)}ms`;
  revealObserver.observe(item);

  const img = document.createElement('img');
  img.alt = photo.caption || '';
  img.loading = 'lazy';
  loadWithFallback(img, photo.thumb, photo.file);
  setUpMasonryTile(item, img);
  item.appendChild(img);

  const overlay = document.createElement('div');
  overlay.className = 'item-overlay';

  const topBox = document.createElement('div');
  topBox.className = 'overlay-top';
  topBox.innerHTML = `<span class="overlay-frame-num">&#9650; ${String(index + 1).padStart(2, '0')}A</span>`;
  overlay.appendChild(topBox);

  const bottomBox = document.createElement('div');
  bottomBox.className = 'overlay-bottom';

  const metaEl = document.createElement('div');
  metaEl.className = 'overlay-meta';
  bottomBox.appendChild(metaEl);

  if (photo.caption) {
    const captionEl = document.createElement('div');
    captionEl.className = 'overlay-caption';
    captionEl.textContent = photo.caption;
    bottomBox.appendChild(captionEl);
  }

  getPhotoMeta(photo).then((metaString) => {
    if (metaString) metaEl.textContent = metaString;
  });

  overlay.appendChild(bottomBox);
  item.appendChild(overlay);

  const open = () => openLightbox(list, index);
  item.addEventListener('click', open);
  item.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open();
    }
  });

  return item;
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
  lbImage.src = photo.file;
  lbImage.alt = photo.caption || '';
  lbCaption.textContent = photo.caption || '';
  lbExif.textContent = '';

  const metaString = await getPhotoMeta(photo);
  lbExif.textContent = metaString || '';
}

function showNext() {
  currentIndex = (currentIndex + 1) % currentList.length;
  showCurrent();
}

function showPrev() {
  currentIndex = (currentIndex - 1 + currentList.length) % currentList.length;
  showCurrent();
}

lbClose.addEventListener('click', closeLightbox);
lbNext.addEventListener('click', showNext);
lbPrev.addEventListener('click', showPrev);

lightbox.addEventListener('click', (e) => {
  if (e.target === lightbox) closeLightbox();
});

document.addEventListener('keydown', (e) => {
  if (lightbox.hidden) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowRight') showNext();
  if (e.key === 'ArrowLeft') showPrev();
});

// Smooth anchor navigation supporting hash-routed views
document.querySelectorAll('.header-nav a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener('click', (e) => {
    const targetId = anchor.getAttribute('href').slice(1);
    if (!albumView.hidden) {
      location.hash = '';
      setTimeout(() => {
        const el = document.getElementById(targetId);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 50);
    }
  });
});