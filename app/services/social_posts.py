"""Social media post generator: Instagram + Facebook + Twitter + hashtags.

Strategy:
- One Gemma call returns a JSON object with all four outputs in the
  source language (richer prompt-following).
- If the target language differs, each output is translated via the
  translation dispatcher (Sarvam for Indian languages, Gemma otherwise).
- Twitter is hard-truncated to 280 chars as a safety net even if Gemma
  ignored the limit in the prompt.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.services import gemma, translation

logger = logging.getLogger(__name__)

INSTAGRAM_LIMIT = 2200
FACEBOOK_LIMIT = 63206  # FB's actual hard cap, but we still aim shorter via the prompt
TWITTER_LIMIT = 280
HASHTAGS_LIMIT = 500  # soft cap for the hashtag string

TONES = ("elegant", "casual", "gen_z")

# Section keys returned by the service (also keys in the Gemma JSON response).
SECTIONS = ("instagram", "facebook", "twitter", "hashtags")


@dataclass(frozen=True)
class SocialPost:
    instagram: str
    facebook: str
    twitter: str
    hashtags: str
    language: str

    def to_dict(self) -> dict:
        return {
            "instagram": self.instagram,
            "facebook": self.facebook,
            "twitter": self.twitter,
            "hashtags": self.hashtags,
            "language": self.language,
            "char_counts": {
                "instagram": len(self.instagram),
                "facebook": len(self.facebook),
                "twitter": len(self.twitter),
                "hashtags": len(self.hashtags),
            },
            "limits": {
                "instagram": INSTAGRAM_LIMIT,
                "twitter": TWITTER_LIMIT,
            },
        }


def generate_posts(description: str, tone: str, target_language: str, source_language: str = "en") -> SocialPost:
    if not description or not description.strip():
        raise ValueError("description is required")
    if tone not in TONES:
        raise ValueError(f"tone must be one of {TONES}")

    raw = _ask_gemma(description, tone, source_language)
    source_posts = _parse_response(raw)

    if target_language and target_language != source_language:
        translated: dict[str, str] = {}
        for section in SECTIONS:
            text = source_posts.get(section, "")
            if not text:
                translated[section] = ""
                continue
            try:
                translated[section] = translation.translate_one(text, target_language, source_language)
            except Exception as exc:
                logger.warning("translate_one failed for %s/%s: %s", section, target_language, exc)
                translated[section] = text
        posts = translated
        out_lang = target_language
    else:
        posts = source_posts
        out_lang = source_language

    return SocialPost(
        instagram=_cap(posts.get("instagram", ""), INSTAGRAM_LIMIT),
        facebook=_cap(posts.get("facebook", ""), FACEBOOK_LIMIT),
        twitter=_cap(posts.get("twitter", ""), TWITTER_LIMIT),
        hashtags=_cap(posts.get("hashtags", ""), HASHTAGS_LIMIT),
        language=out_lang,
    )


def _tone_hint(tone: str) -> str:
    if tone == "elegant":
        return "Tone: formal, warm, respectful. Highlight craftsmanship and the feeling of owning this piece."
    if tone == "casual":
        return "Tone: friendly, conversational, approachable — like a knowledgeable friend recommending the product."
    return "Tone: Gen Z energy — punchy, authentic, share-worthy. Include 1-2 relevant emojis."


def _ask_gemma(description: str, tone: str, source_language: str) -> str:
    tone_hint = _tone_hint(tone)
    prompt = f"""You are a social-media copywriter for a handmade artisan product.
Write platform-specific posts in language '{source_language}'.

Product: {description}

{tone_hint}

Return ONLY a JSON object — no markdown fences, no commentary. Use this exact shape:

{{
  "instagram": "<engaging caption, max {INSTAGRAM_LIMIT} chars, use line breaks, end with 3-5 emojis>",
  "facebook":  "<conversational post, 400-1200 chars, slightly longer than IG, no hashtags inside body>",
  "twitter":   "<punchy single tweet, MAX {TWITTER_LIMIT} chars including spaces, include 1-2 hashtags>",
  "hashtags":  "<10-15 relevant hashtags as a single line, space-separated, each starting with #>"
}}

Rules:
- Every value is a plain string. No nested objects, no arrays.
- Do not echo back the product description verbatim — rewrite for impact.
- Twitter MUST be under {TWITTER_LIMIT} characters.
"""
    return gemma._call(prompt, max_tokens=1024)


def _parse_response(raw: str) -> dict[str, str]:
    cleaned = raw.strip()
    for prefix in ("```json", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    cleaned = cleaned.rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError(f"Gemma response missing JSON object: {raw[:200]}")
    data = json.loads(cleaned[start:end])

    out: dict[str, str] = {}
    for section in SECTIONS:
        value = data.get(section, "")
        if not isinstance(value, str):
            # Coerce odd shapes (e.g. arrays of hashtags) into strings.
            if isinstance(value, list):
                value = " ".join(str(v) for v in value)
            else:
                value = str(value or "")
        out[section] = value.strip()
    return out


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1].rstrip() + "…"
