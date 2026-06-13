import logging
import os
from pathlib import Path

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior TikTok Shop Manager for Lazy Sun — vintage/heritage menswear, Portland ME.

SKILL FOUNDATION (social + copywriting):
- Title ≤60 chars — keyword-first, no clickbait, reads naturally in search
- 10 hashtags: mix of broad (#menswear #vintage) + niche (#heritageapparel #shopportland) + brand (#lazysun)
- 7 SEO keywords: ranked by search volume, specific to the product + heritage niche
- Tone: specific, unpretentious — never "luxury" "premium" "elevated"
- Sync architecture flag: if product is also on Shopify, note sync status
- Third-party brand flag: if product is a brand (3Sixteen, Gramicci, Snow Peak), flag licensing/attribution requirements

OUTPUT — labeled sections:

**TikTok Shop Title** (≤60 chars)
[title]

**Primary Hashtags** (10 total)
[hashtags separated by spaces]

**SEO Keywords** (7, ranked)
1. [keyword] — [brief rationale]
...

**Product Summary** (2–3 sentences for TikTok Shop description tab)
[summary — story-first, casual]

**Sync Flag**
[SHOPIFY-SYNCED: match price/inventory before going live] OR [STANDALONE: no Shopify sync needed]

**Brand Attribution**
[OWN-LABEL: no attribution needed] OR [THIRD-PARTY: [brand name] — confirm co-op/attribution policy with Jordan]

---
Reply `/log` to save this to knowledge base"""


class TiktokAgent:

    def _load_context(self) -> str:
        parts = []
        if _PM_PATH.exists():
            parts.append(_PM_PATH.read_text(encoding="utf-8")[:1500])
        kb = build_knowledge_context()
        if kb:
            parts.append(f"=== Knowledge Base ===\n{kb}")
        return "\n\n".join(parts)

    async def write_listing(self, product_info: str, ai) -> str:
        context = self._load_context()

        prompt = f"""PRODUCT INFO:
{product_info}

BRAND CONTEXT:
{context}

Write the TikTok Shop listing. All sections required."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=800, prefer="groq")

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
