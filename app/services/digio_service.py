"""Digio KYC service for PAN and GST verification.

PII rules (enforced):
- Full ID numbers (PAN, GSTIN, Aadhaar) NEVER appear in log lines.
- Full numbers flow only in-memory through the Digio request body.
- Callers persist only the masked tail via `mask_id()`.

Sandbox base URL: https://ext.digio.in:444
Production base URL: https://api.digio.in (set DIGIO_BASE_URL accordingly)

NOTE: Endpoint paths are the documented Digio v3 paths, but should be
re-validated against the current Digio docs the first time real sandbox
credentials are used.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")

# Digio v3 KYC endpoints. Re-verify against current Digio docs before
# going live; if Digio updates a path, change here only.
_PAN_PATH = "/v3/client/kyc/pan_basic/{client_ref_id}"
_GST_PATH = "/v3/client/kyc/business_data/gstin_search/{client_ref_id}"

_REQUEST_TIMEOUT_SECONDS = 15


class DigioNotConfiguredError(RuntimeError):
    """Raised when DIGIO_* env vars are missing."""


class DigioVerificationError(RuntimeError):
    """Raised when the Digio API returns a non-success response."""


def mask_id(value: str, keep: int = 4) -> str:
    """Return a string with all but the last `keep` chars masked as 'X'."""
    if not value:
        return ""
    value = value.strip()
    if len(value) <= keep:
        return "X" * len(value)
    return ("X" * (len(value) - keep)) + value[-keep:]


def is_valid_pan(pan: str) -> bool:
    return bool(pan and PAN_REGEX.match(pan.strip().upper()))


def is_valid_gstin(gstin: str) -> bool:
    return bool(gstin and GSTIN_REGEX.match(gstin.strip().upper()))


def verify_pan(pan_number: str) -> dict:
    """Verify a PAN with Digio. Returns `{valid: bool, name: str}`.

    Raises:
        ValueError: if the PAN format is invalid.
        DigioNotConfiguredError: if Digio env vars are missing.
        DigioVerificationError: if Digio returns a non-success response.
    """
    pan = (pan_number or "").strip().upper()
    if not is_valid_pan(pan):
        raise ValueError("PAN must match 5 letters + 4 digits + 1 letter")

    response = _post(
        _PAN_PATH.format(client_ref_id=_new_client_ref_id()),
        body={"id_no": pan},
    )

    valid = _is_success(response)
    name = _extract_name(response)
    return {"valid": bool(valid), "name": name or ""}


def verify_gst(gstin: str) -> dict:
    """Verify a GSTIN with Digio. Returns `{valid: bool, business_name: str}`.

    Raises:
        ValueError: if GSTIN format is invalid.
        DigioNotConfiguredError: if Digio env vars are missing.
        DigioVerificationError: if Digio returns a non-success response.
    """
    cleaned = (gstin or "").strip().upper()
    if not is_valid_gstin(cleaned):
        raise ValueError("GSTIN must be a valid 15-character identifier")

    response = _post(
        _GST_PATH.format(client_ref_id=_new_client_ref_id()),
        body={"gstin": cleaned},
    )

    valid = _is_success(response)
    business_name = _extract_business_name(response)
    return {"valid": bool(valid), "business_name": business_name or ""}


# -- internals ----------------------------------------------------------------


def _new_client_ref_id() -> str:
    """Generate a short opaque ref id for Digio request correlation."""
    return f"tula-{uuid.uuid4().hex[:16]}"


def _get_config() -> tuple[str, str, str]:
    base = os.getenv("DIGIO_BASE_URL", "").rstrip("/")
    client_id = os.getenv("DIGIO_CLIENT_ID", "")
    client_secret = os.getenv("DIGIO_CLIENT_SECRET", "")
    if not (base and client_id and client_secret):
        raise DigioNotConfiguredError(
            "DIGIO_BASE_URL, DIGIO_CLIENT_ID, and DIGIO_CLIENT_SECRET must be set"
        )
    return base, client_id, client_secret


def _post(path: str, body: dict) -> dict:
    """Authenticated POST to Digio. NEVER logs the request body."""
    base, client_id, client_secret = _get_config()
    url = f"{base}{path}"
    # IMPORTANT: do NOT log `body` — it contains full PAN / GSTIN / Aadhaar.
    logger.info("digio request: %s", path)
    resp = requests.post(
        url,
        json=body,
        auth=(client_id, client_secret),
        timeout=_REQUEST_TIMEOUT_SECONDS,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        data = resp.json()
    except ValueError as exc:
        raise DigioVerificationError(f"non-JSON response (HTTP {resp.status_code})") from exc

    if resp.status_code >= 400:
        # Log status only, never the response body (may echo the input).
        logger.warning("digio %s -> HTTP %s", path, resp.status_code)
        raise DigioVerificationError(f"HTTP {resp.status_code}")

    return data


def _is_success(response: dict) -> bool:
    """Digio responses use `status` or `status_code` to signal outcome."""
    status = (response.get("status") or response.get("status_code") or "").lower()
    if status in ("success", "approved", "verified", "valid", "200"):
        return True
    return bool(response.get("valid") is True)


def _extract_name(response: dict) -> Optional[str]:
    # Digio commonly returns `id_data.name` or `name`.
    id_data = response.get("id_data") or {}
    return id_data.get("name") or response.get("name")


def _extract_business_name(response: dict) -> Optional[str]:
    # Digio GST commonly returns `business_data.legal_name_of_business` or `business_name`.
    business_data = response.get("business_data") or {}
    return (
        business_data.get("legal_name_of_business")
        or business_data.get("trade_name_of_business")
        or response.get("business_name")
        or response.get("legal_name")
    )
