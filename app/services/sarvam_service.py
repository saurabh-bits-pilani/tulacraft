"""Sarvam AI service for Indian-language translation and speech-to-text.

Codebase-internal language codes are 2-letter (`hi`, `bn`, `ta`, ...).
Sarvam's wire format is BCP-47 (`hi-IN`, `bn-IN`, ...). This module accepts
either form from callers and normalises to Sarvam's format.

Note: ISO-639-1 uses `or` for Odia, but Sarvam's API uses `od-IN`. We accept
both `or` / `or-IN` from callers and map to `od-IN` over the wire.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sarvamai import SarvamAI

logger = logging.getLogger(__name__)

# Internal 2-letter code -> Sarvam BCP-47 code.
_LANG_MAP = {
    "hi": "hi-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "or": "od-IN",  # ISO-639-1 'or' (Odia) -> Sarvam's 'od-IN'
    "ur": "ur-IN",
    "en": "en-IN",
}

# Accept brief's 'or-IN' alias and normalise to Sarvam's 'od-IN'.
_BCP47_ALIAS = {
    "or-IN": "od-IN",
}

INDIAN_LANGUAGE_CODES: frozenset[str] = frozenset(
    list(_LANG_MAP.keys())
    + list(_LANG_MAP.values())
    + list(_BCP47_ALIAS.keys())
)

STT_MODEL = "saarika:v2.5"

_client: Optional[SarvamAI] = None


def _get_client() -> SarvamAI:
    global _client
    if _client is None:
        key = os.getenv("SARVAM_API_KEY")
        if not key:
            raise RuntimeError("SARVAM_API_KEY is not set")
        _client = SarvamAI(api_subscription_key=key)
    return _client


def is_indian_language(code: Optional[str]) -> bool:
    if not code:
        return False
    return code in INDIAN_LANGUAGE_CODES


def to_sarvam_code(code: str) -> str:
    """Normalise any accepted code to Sarvam's BCP-47 wire format."""
    if code in _BCP47_ALIAS:
        return _BCP47_ALIAS[code]
    if code in _LANG_MAP:
        return _LANG_MAP[code]
    # Already a Sarvam-style code (e.g. 'hi-IN').
    return code


def _source_language_code(source: Optional[str]) -> str:
    if not source or source == "auto":
        return "auto"
    if is_indian_language(source):
        return to_sarvam_code(source)
    # Sarvam only accepts Indian BCP-47 codes or 'auto' for source.
    return "auto"


def translate_text(text: str, target_lang_code: str, source_lang_code: str = "auto") -> str:
    """Translate `text` to an Indian language using Sarvam.

    Raises ValueError if `target_lang_code` is not an Indian language.
    On API failure, raises the underlying SDK exception — caller decides
    whether to fall back.
    """
    if not is_indian_language(target_lang_code):
        raise ValueError(f"{target_lang_code!r} is not an Indian language supported by Sarvam")
    if not text:
        return text

    client = _get_client()
    response = client.text.translate(
        input=text,
        source_language_code=_source_language_code(source_lang_code),
        target_language_code=to_sarvam_code(target_lang_code),
    )
    return response.translated_text


def transcribe_voice(
    audio_bytes: bytes,
    lang_code: str,
    filename: str = "audio.wav",
    mime_type: str = "audio/wav",
) -> str:
    """Transcribe audio bytes to text in the given Indian language.

    `lang_code` may be a 2-letter code or BCP-47. Pass `'unknown'` to let
    Sarvam auto-detect. Defaults to wav; pass `mime_type` for other formats.
    """
    if not audio_bytes:
        raise ValueError("audio_bytes is empty")

    if lang_code and lang_code != "unknown":
        if not is_indian_language(lang_code):
            raise ValueError(f"{lang_code!r} is not a Sarvam-supported language")
        wire_lang = to_sarvam_code(lang_code)
    else:
        wire_lang = "unknown"

    client = _get_client()
    response = client.speech_to_text.transcribe(
        file=(filename, audio_bytes, mime_type),
        model=STT_MODEL,
        language_code=wire_lang,
    )
    return response.transcript
