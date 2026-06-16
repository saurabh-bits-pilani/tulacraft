# Brief 7 — PWA Setup

## Tasks

1. `app/static/manifest.json` — name Tulacraft, short_name Tula,
   theme_color #2D6A4F, background_color #ffffff, display standalone,
   icons at 192/512.
2. `app/static/sw.js` — cache core assets on install, serve from cache
   when offline, network-first for API calls.
3. `base.html` — manifest link tag + service worker registration.
4. Install prompt logic — show "Add to Home Screen" banner after 2nd
   visit; visit count in localStorage; dismiss saves preference.
5. Audit seller-facing buttons — minimum 48 px touch target.
6. Camera capture button on product image upload.

## Branch
`feature/pwa` (off `main`)

## Test
Serve app, open on Android Chrome, confirm manifest loads, install
prompt appears.

## Implementation notes / decisions

- **Manifest already exists** (created during brief 1 rebrand) — this
  brief updates the existing file with the brief's specified values
  (short_name `Tula`, theme `#2D6A4F`, background `#ffffff`). Icons at
  192 + 512 already present in `app/static/icons/`.
- **Service worker scope**: a SW served from `/static/sw.js` is scoped
  to `/static/*` by default, which makes it useless for caching app
  routes. Solution: add a Flask route `GET /sw.js` that serves the
  static file from origin root → SW controls the whole origin.
- **`theme-color` meta tag** in `base.html` is currently `#6f42c1` from
  brief 1; updated to `#2D6A4F` to match the new manifest.
- **Install prompt**: capture `beforeinstallprompt` event AND maintain
  a localStorage visit counter. Banner appears when:
  - second-or-later visit
  - install prompt is available (deferred event captured)
  - user hasn't previously dismissed
  Dismiss writes `pwa_install_dismissed=true` to localStorage.
- **Touch targets**: add global CSS `.btn { min-height: 48px }` plus
  `.btn-sm { min-height: 44px }` (Apple HIG minimum), guarded inside
  `@media (pointer: coarse)` so desktop pointer users keep tighter
  buttons. Applies to both buyer and seller sides for consistency.
- **Camera capture**: add a separate "Take Photo" button alongside
  the existing gallery picker. Uses a hidden `<input type="file"
  accept="image/*" capture="environment">` so existing multi-photo
  picker behaviour is preserved.
- **Cache versioning**: SW uses a `CACHE_NAME` const so a bump
  invalidates old caches on next install.
