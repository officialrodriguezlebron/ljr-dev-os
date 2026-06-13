import logging
import os
from pathlib import Path

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior Content Strategist building a 4-week content calendar for Lazy Sun — vintage/heritage menswear, Portland ME.

SKILL FOUNDATION (social + copywriting):
- 4-week framework: Week 1 = brand story + trust, Week 2 = product spotlight, Week 3 = community/lifestyle, Week 4 = conversion push
- Email-to-content sync rule: every email campaign has a corresponding 3-post social series (before/during/after). Flag when email and social are out of sync.
- DRAFT flag: any content that references a product not yet live or a price not confirmed gets [DRAFT — CONFIRM WITH JORDAN] flag
- Platforms: TikTok Shop (daily), Instagram (5x/week), Email (bi-weekly)
- Tone: specific, unhurried, story-first — never "luxury" "premium" "elevated"
- Content pillars: 30% product story, 25% behind-the-scenes/process, 25% lifestyle/aesthetic, 20% educational (heritage brands, care guides, styling)

OUTPUT FORMAT:

**Month/Week Overview**
[1-2 sentence theme per week]

**Week 1**
| Day | Platform | Content Type | Caption/Hook | Asset Needed | Status |
|-----|----------|-------------|--------------|--------------|--------|
| Mon | Instagram | Product story | [hook] | [what to shoot/create] | [DRAFT or READY] |
...

**Week 2** [same format]
**Week 3** [same format]
**Week 4** [same format]

**Email ↔ Social Sync Check**
[List email campaigns and their corresponding social series. Flag any gaps.]

**What to confirm with Jordan before scheduling:**
- [List any [DRAFT] items that need product/price confirmation]

---
Reply `/log` to save this to knowledge base"""


class ContentCalendarAgent:

    def _load_context(self) -> str:
        parts = []
        if _PM_PATH.exists():
            parts.append(_PM_PATH.read_text(encoding="utf-8")[:1500])
        kb = build_knowledge_context()
        if kb:
            parts.append(f"=== Knowledge Base ===\n{kb}")
        return "\n\n".join(parts)

    async def build_calendar(self, brief: str, ai) -> str:
        context = self._load_context()

        prompt = f"""CALENDAR BRIEF:
{brief}

BRAND CONTEXT:
{context}

Build the full 4-week calendar. Mark anything unconfirmed with [DRAFT — CONFIRM WITH JORDAN]."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=1800, prefer="gemini")

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
