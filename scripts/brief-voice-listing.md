# Brief 5 — Voice Product Listing with Sarvam STT

## Tasks

1. On the product listing form, add a microphone button next to the
   product description field.
2. If seller's language is Indian
   (`hi`, `bn`, `mr`, `ta`, `te`, `gu`, `kn`, `ml`, `pa`, `or`, `ur`)
   use Sarvam STT to transcribe.
3. If seller's language is non-Indian — use existing Web Speech API.
4. Create route `POST /producer/transcribe-voice`.
5. Accepts audio blob, returns transcribed text.
6. Transcribed text auto-fills the description field.
7. Show recording indicator while mic is active.

## Branch
`feature/voice-listing` (stacked on `feature/sarvam-languages`)

## Test
Record voice in Hindi, confirm transcribed text appears in description
field.

## Implementation notes

- Mic button already exists on the form (`#startVoice` / `#stopVoice`)
  for the Web Speech API path. Brief 5 augments the existing button so
  it branches by `current_user.language`:
  - Indian → MediaRecorder captures webm/opus, POSTs to backend
  - Non-Indian → existing Web Speech API (unchanged)
- Backend route accepts multipart `audio` file + form `language` field;
  uses `sarvam_service.transcribe_voice` from brief 3.
- Recording indicator: pulsing red dot + elapsed timer next to the mic
  button while recording.
- The Sarvam endpoint accepts webm/opus directly via the
  `input_audio_codec` autodetection in the SDK (the SDK introspection
  in brief 3 showed `webm` is in the accepted codec list).
- Backend exposes a small context helper so the template can ask
  `is_seller_indian`.
