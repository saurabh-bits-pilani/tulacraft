"""Translation router: dispatches per-language to Sarvam (Indian) or Gemma."""
from __future__ import annotations

import logging
from typing import Optional

from app.services import gemma, sarvam_service

logger = logging.getLogger(__name__)


def translate_one(
    text: str,
    lang: str,
    source_language: str = "en",
    max_tokens: int = 1024,
) -> str:
    """Translate a single string. Indian languages go to Sarvam, else Gemma.

    Falls back to Gemma if Sarvam raises — the caller still gets a translation.
    """
    if not text:
        return text

    if sarvam_service.is_indian_language(lang):
        try:
            return sarvam_service.translate_text(text, lang, source_language)
        except Exception as exc:
            logger.warning("Sarvam translate failed for %s, falling back to Gemma: %s", lang, exc)

    return gemma.translate_one(text, lang, source_language, max_tokens=max_tokens)


def translate(
    text: str,
    target_languages: list[str],
    source_language: str = "en",
) -> dict[str, str]:
    """Bulk translate: partition languages by provider, merge results."""
    if not text or not target_languages:
        return {}

    indian = [l for l in target_languages if sarvam_service.is_indian_language(l)]
    others = [l for l in target_languages if not sarvam_service.is_indian_language(l)]

    results: dict[str, str] = {}

    if others:
        try:
            results.update(gemma.translate(text, others, source_language))
        except Exception as exc:
            logger.warning("Gemma bulk translate failed: %s", exc)
            for lang in others:
                try:
                    results[lang] = gemma.translate_one(text, lang, source_language)
                except Exception:
                    results[lang] = text

    for lang in indian:
        try:
            results[lang] = sarvam_service.translate_text(text, lang, source_language)
        except Exception as exc:
            logger.warning("Sarvam translate failed for %s, falling back to Gemma: %s", lang, exc)
            try:
                results[lang] = gemma.translate_one(text, lang, source_language)
            except Exception:
                results[lang] = text

    return results
