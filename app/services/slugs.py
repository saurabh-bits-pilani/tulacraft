"""Seller slug generation with collision handling."""
import re
import unicodedata


RESERVED_SLUGS = {
    "register",
    "login",
    "logout",
    "my-leads",
    "set-language",
    "product",
    "lead",
    "messages",
    "api",
    "static",
    "producer",
    "shop",
    "s",
    "seller",
    "admin",
}


def slugify(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower().strip()
    hyphenated = re.sub(r"[\s_]+", "-", lowered)
    cleaned = re.sub(r"[^a-z0-9-]", "", hyphenated)
    collapsed = re.sub(r"-+", "-", cleaned).strip("-")
    return collapsed


def unique_slug(name: str, exists_fn) -> str:
    """Generate a unique slug.

    `exists_fn(slug)` must return True if the slug is already taken.
    Falls back to `seller` when the input contains no slug-safe characters.
    """
    base = slugify(name) or "seller"
    candidate = base
    suffix = 2
    while candidate in RESERVED_SLUGS or exists_fn(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate
