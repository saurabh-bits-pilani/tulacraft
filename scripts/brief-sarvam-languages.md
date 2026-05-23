# Brief 3 — Sarvam Indian Language Integration

`SARVAM_API_KEY` is already in `.env`.

## Tasks

1. Add `sarvamai` to `requirements.txt`.
2. Create `app/services/sarvam_service.py` with:
   - `translate_text(text, target_lang_code)`
   - `transcribe_voice(audio_bytes, lang_code)`
3. Update translation route — if target language is Indian use Sarvam,
   else use Gemma.
4. Indian language codes:
   `hi-IN, bn-IN, mr-IN, ta-IN, te-IN, gu-IN, kn-IN, ml-IN, pa-IN, or-IN, ur-IN`

## Branch
`feature/sarvam-languages`

## Test
Translate a product description to Hindi and Tamil; confirm output is correct.

## Implementation notes

- `sarvamai==0.1.28` introspected: client is `SarvamAI(api_subscription_key=...)`.
- Translate: `client.text.translate(input=..., source_language_code='auto'|<code>, target_language_code=<code>)`
  returns `TranslationResponse(translated_text=...)`.
- STT: `client.speech_to_text.transcribe(file=(filename, bytes, mime), model='saarika:v2.5', language_code=<code>)`
  returns `SpeechToTextResponse(transcript=...)`.
- **Odia code mismatch**: brief says `or-IN`; Sarvam wire format is `od-IN`.
  Service accepts `or` / `or-IN` from callers and maps to `od-IN` over the wire.
- Codebase stores 2-letter codes (`hi`, `bn`, ...); Sarvam needs `xx-IN`.
  The mapping table lives in `sarvam_service.py`.
- Dispatcher `app/services/translation.py` routes per-language:
  Indian → Sarvam; everything else → Gemma. Bulk multi-language calls
  partition the language list and merge results.
