# Brief 6b — Aadhaar OTP Verification Flow

## Dependency
Stacked on `feature/verification-shield` (PR #5). Depends on
`VerificationStatus` model, `digio_service` module, `mask_id` helper,
and `get_verified.html` template.

## Tasks

1. Add to `app/services/digio_service.py`:
   - `aadhaar_send_otp(aadhaar_number) -> {ref_id: str}`
   - `aadhaar_verify_otp(ref_id, otp) -> {valid: bool, name: str}`
2. Add routes:
   - `POST /producer/aadhaar-send-otp` — validate 12-digit, call
     service, stash `ref_id` in session, return `{ref_id, status}`.
   - `POST /producer/aadhaar-verify-otp` — read `ref_id` from session,
     call service, store masked last 4 in `verification_status`, clear
     session `ref_id` either way.
3. Replace Aadhaar "Coming soon" card in `get_verified.html` with the
   3-step OTP flow (input → OTP field → verify + spinner).
4. `ref_id` lives in Flask session ONLY for the duration of the OTP
   flow. Never persisted to DB.

## Branch
`feature/aadhaar-otp` (off `feature/verification-shield`)

## PII rules (strict)
- Full Aadhaar number: never logged, never persisted, never echoed.
- Flows in-memory only through `digio_service._post` body.
- `masked_number` column gets `XXXXXXXX1234` (last 4 only).
- OTP not logged either.
- Session stores opaque Digio `ref_id` only — not Aadhaar, not OTP.

## Implementation notes
- Verhoeff checksum used as a cheap early-reject for invalid Aadhaar
  formats before the Digio API call.
- Digio endpoint paths (`/v3/client/kyc/aadhaar/...`) are the
  documented v3 paths but should be re-verified once sandbox keys
  arrive.
- Mocked HTTP tests for both routes (success, invalid format, missing
  session ref_id, OTP failure).

## Out of scope (intentionally)
- Rate limiting on `aadhaar-send-otp` (recommend follow-up: cap to
  1 send per 30 s per producer session).
- Razorpay payment gate (still deferred).
- Storefront badge display (still deferred — depends on PR #1).

## Test
- Mocked: send OTP returns ref_id stored in session; verify OTP reads
  ref_id, stores masked tail, returns success.
- Live (when Digio sandbox keys arrive): send OTP to test Aadhaar,
  enter OTP, confirm Aadhaar badge appears on dashboard.
