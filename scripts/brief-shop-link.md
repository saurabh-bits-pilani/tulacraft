# Brief 1 — Digital Shop Link

Create a public seller storefront page at `/shop/<seller_slug>`.

## Tasks

1. Add `seller_slug` field to the User model in `app/models.py`
   - Auto-generate from seller name on registration (lowercase, spaces to hyphens)
   - Must be unique

2. Create new route `GET /shop/<seller_slug>` in `app/routes/shop.py`
   - Public — no login required
   - Fetch seller by slug, return 404 if not found
   - Pass seller profile and all their active listings to template

3. Create new template `app/templates/shop/seller_shop.html`
   - Show seller name, bio, profile photo
   - Show all active product listings as cards
   - Mobile-first layout
   - Add Share button that copies URL to clipboard

4. Add share button on existing product cards linking to seller shop

## Branch
`feature/shop-link`

## Test
Register test seller, confirm `/shop/test-seller` loads on mobile Chrome.

## Implementation notes
- "User model" in this codebase = `Producer` (sellers).
- New blueprint `shop_bp` mounted at `/shop`; reserved slugs guard against
  collisions with existing buyer routes (`login`, `register`, `logout`,
  `my-leads`, `set-language`, `product`, `lead`, `messages`).
- `Producer` has no `profile_photo` column; template renders a default
  avatar (initial in a coloured circle). Photo upload is out of scope.
- Slug generation: lowercase + `-` separator + collision suffix `-2`, `-3`, ...
- Schema update via `ALTER TABLE IF NOT EXISTS` + startup backfill loop.
