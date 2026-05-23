"""Price suggestion via Gemma: Budget / Standard / Premium tiers."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from app.services import gemma, exchange_rate

logger = logging.getLogger(__name__)

TIER_ORDER = ("budget", "standard", "premium")


@dataclass(frozen=True)
class PriceTier:
    tier: str
    price_inr: float
    price_usd: Optional[float]
    reason: str

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "price_inr": self.price_inr,
            "price_usd": self.price_usd,
            "reason": self.reason,
        }


def suggest_prices(material_cost_inr: float, hours_spent: float, craft_category: str) -> list[PriceTier]:
    raw = _ask_gemma(material_cost_inr, hours_spent, craft_category)
    parsed = _parse_response(raw)
    return [_attach_usd(t) for t in parsed]


def _ask_gemma(material_cost_inr: float, hours_spent: float, craft_category: str) -> str:
    prompt = f"""You are a pricing advisor for Indian artisan crafts.
Suggest three price points (in INR) for a handmade item with these inputs.

Material cost: ₹{material_cost_inr:.2f}
Hours of work: {hours_spent}
Craft category: {craft_category}

Return ONLY a JSON object — no markdown, no commentary. Use this exact shape:

{{
  "budget":   {{"price_inr": <number>, "reason": "<one short sentence>"}},
  "standard": {{"price_inr": <number>, "reason": "<one short sentence>"}},
  "premium":  {{"price_inr": <number>, "reason": "<one short sentence>"}}
}}

Rules:
- Each price must be a positive number, no currency symbol.
- Budget < Standard < Premium.
- All three must exceed the material cost.
- Reasons must be one short sentence, under 20 words.
"""
    return gemma._call(prompt, max_tokens=512)


def _parse_response(raw: str) -> list[PriceTier]:
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
    tiers: list[PriceTier] = []
    for name in TIER_ORDER:
        entry = data.get(name)
        if not entry or "price_inr" not in entry or "reason" not in entry:
            raise ValueError(f"Gemma response missing tier {name!r}: {data}")
        price = float(entry["price_inr"])
        if price <= 0:
            raise ValueError(f"Tier {name!r} has non-positive price: {price}")
        tiers.append(
            PriceTier(
                tier=name,
                price_inr=round(price, 2),
                price_usd=None,
                reason=str(entry["reason"]).strip(),
            )
        )
    return tiers


def _attach_usd(tier: PriceTier) -> PriceTier:
    usd = exchange_rate.inr_to_usd(tier.price_inr)
    return PriceTier(
        tier=tier.tier,
        price_inr=tier.price_inr,
        price_usd=usd,
        reason=tier.reason,
    )
