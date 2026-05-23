# Brief 6 — Seller Verification Shield with OTP Flow

## Scope: 6a (this PR)
- Schema for `verification_status` table
- Digio service module: `verify_pan` + `verify_gst` (Aadhaar deferred to 6b)
- Routes: `POST /producer/verify-pan`, `POST /producer/verify-gst`
- `GET /producer/get-verified` page with 4 tier cards + PAN/GST forms
- Producer dashboard shows earned badges + Get-Verified CTA
- `.env.example` additions

## Out of scope (deferred)
- **6b**: Aadhaar OTP flow + Razorpay payment gate + storefront badges on `/shop/<seller_slug>`
- Storefront badges depend on PR #1 (`feature/shop-link`); will land after PR #1 merges

## Decisions confirmed with user
1. Branch off `main` (option b): defer storefront badges to a follow-up.
2. Use **Digio for GST too** (one vendor, one integration). The brief's
   `https://api.gst.gov.in` "free GSTN API" doesn't exist as described.
3. **Proceed mocked**: no Digio sandbox keys yet. Service is structurally
   correct + unit-tested with mocked HTTP; not live-validated against
   Digio. Will need round-trip test after sandbox keys land.
4. **PAN is masked** to last 4 digits — same rule as Aadhaar. Full
   numbers never persisted, never logged.
5. PR split: 6a + 6b.

## PII handling rules
- Full ID number flows only in-memory through the Digio call.
- Stored column `masked_number` holds last 4 digits only.
- No log line ever contains the full number.
- Error responses to the client never echo back the input number.

## Branch
`feature/verification-shield` (off `main`)

## Tests (mocked)
- Valid PAN format -> Digio mock returns `{status: "success", name: ...}` -> row inserted with masked_number, status=verified
- Invalid PAN format -> 400 before any Digio call
- Digio failure -> row inserted with status=failed (or no row, see code)
- Same flow for GST
- `mask_id("ABCDE1234F")` -> `"XXXXXX234F"` (keep last 4)
