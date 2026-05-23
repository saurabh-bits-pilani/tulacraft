# Brief 6 — Social Media Post Generator

Already partially built (marketing-text generator with Elegant/Casual/Teen
tones). This brief adds platform-specific multi-output posts.

## Tasks

1. One click generates: Instagram caption + Facebook post + hashtags
2. Three tone options: Elegant / Casual / Gen Z
3. Enforce character limits: Instagram 2200 chars, Twitter 280 chars
4. If seller language is Indian — generate post in seller's language via
   Sarvam translation
5. If non-Indian — generate via Gemma in that language
6. Copy to clipboard button for each generated post
7. Show character count live as post is generated

## Branch
`feature/social-posts` (stacked on `feature/sarvam-languages`)

## Test
Generate Instagram post for pottery product in Hindi — confirm correct
language and under 2200 chars.

## Implementation notes / decisions

- **Output set** (chose option B from clarifying question): generate
  Instagram + Facebook + **Twitter** + hashtags. Twitter included
  because the brief specifies a 280-char limit, which would be dead
  text otherwise.
- **New module** `app/services/social_posts.py`:
  - One Gemma call returns JSON with all four outputs in the source
    language.
  - If target language differs from source: translate each output via
    `translation.translate_one` (Sarvam for Indian, Gemma otherwise).
  - Twitter post is hard-truncated to 280 chars as a safety net.
- **Existing marketing-text generator stays untouched** — it produces
  single-text marketing copy, a different use case. The new social
  posts feature lives as a separate section on the form.
- **UI**: rename the existing "Teen" tone label to "Gen Z" only within
  the new social-posts section (don't disturb the existing marketing
  buttons).
- **Char count**: rendered live next to each output card.
- **Copy**: per-output button using `navigator.clipboard`.
