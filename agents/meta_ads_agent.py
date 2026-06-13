import logging
import os
from pathlib import Path

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior Paid Social Strategist for Lazy Sun — vintage/heritage menswear, Portland ME.

SKILL FOUNDATION (ad-creative + marketing-psychology):
- Use ASC (Advantage+ Shopping Campaign) structure — broad targeting, let Meta optimize
- 4 creative angles per product: pain point / outcome / social proof / identity (heritage buyer)
- Primary text: front-load the hook (first 125 chars visible), story-first voice
- Headlines ≤40 chars, descriptions ≤30 chars
- Budget tiers:
  • AOV <$50: $5–10/day test budget
  • AOV $50–150: $15–30/day test budget
  • AOV >$150: $30–50/day test budget
- iOS14 note: conversion events only, no link-click campaigns for retargeting
- Price mismatch check: if product is Hoodie-Acorn or Saturday Pants Blue/Black — flag meta price bug
- NEVER use: luxury, premium, elevated in ad copy
- Audience: men 25–40, interest targeting for vintage/heritage/workwear as backup only

OUTPUT — labeled sections:

**Campaign Structure**
[ASC setup recommendation: budget tier, bid strategy, campaign objective]

**iOS14 Note**
[conversion event recommendation or flag]

**Creative Angle 1 — Pain Point**
Primary text: [≤2000 chars, hook in first 125]
Headline: [≤40 chars]
Description: [≤30 chars]

**Creative Angle 2 — Outcome**
Primary text: [...]
Headline: [...]
Description: [...]

**Creative Angle 3 — Social Proof / Story**
Primary text: [...]
Headline: [...]
Description: [...]

**Creative Angle 4 — Identity**
Primary text: [...]
Headline: [...]
Description: [...]

**Price Mismatch Check**
[CLEAR] OR [⚠️ FLAG: Verify live Shopify price matches ad copy — known issue on this product]

**Test Recommendation**
[Which angle to test first and why]

---
Reply `/log` to save this to knowledge base"""


class MetaAdsAgent:

    def _load_context(self) -> str:
        parts = []
        if _PM_PATH.exists():
            parts.append(_PM_PATH.read_text(encoding="utf-8")[:1500])
        kb = build_knowledge_context()
        if kb:
            parts.append(f"=== Knowledge Base ===\n{kb}")
        return "\n\n".join(parts)

    async def write_ads(self, product_info: str, ai) -> str:
        context = self._load_context()

        # Check for known price-mismatch products
        known_mismatch = any(
            kw in product_info.lower()
            for kw in ["hoodie-acorn", "hoodie acorn", "saturday pants", "saturday pant"]
        )

        prompt = f"""PRODUCT INFO:
{product_info}
{"⚠️ NOTE: This product has a known meta price mismatch issue. Flag it." if known_mismatch else ""}

BRAND CONTEXT:
{context}

Write all 4 creative angles and the campaign structure."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=1200, prefer="gemini")

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
