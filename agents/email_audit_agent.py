import logging
import os
from pathlib import Path

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior Email Marketing Strategist auditing email flows for Lazy Sun — vintage/heritage menswear, Portland ME.

SKILL FOUNDATION (emails + copywriting + cro):

AUDIT SCOPE — 5 core flows:
1. Welcome Series (post-signup)
2. Abandoned Cart
3. Post-Purchase (order confirmation + follow-up)
4. Win-Back (60+ day inactive)
5. Browse Abandonment

For each flow, evaluate:
- Does it exist? (YES / MISSING / PARTIAL)
- Subject line quality (clear, specific, not spammy)
- Preview text (extends subject, doesn't repeat it)
- Email count and timing (appropriate for flow type)
- CTA clarity (one primary action, action-oriented button text)
- Tone alignment (LazySun: specific, unhurried, story-first)
- Mobile optimization (short paragraphs, 1 CTA, 600px width)

KISS client update format: each finding gets a 1-sentence summary that Lebron can paste to Jordan in Slack/Telegram without jargon.

OUTPUT FORMAT:

**Flow Audit Table**
| Flow | Status | Subject Quality | Timing | CTA | Tone | Mobile |
|------|--------|----------------|--------|-----|------|--------|
| Welcome | | | | | | |
| Abandoned Cart | | | | | | |
| Post-Purchase | | | | | | |
| Win-Back | | | | | | |
| Browse Abandon | | | | | | |

**Top 5 Findings** (ranked by revenue impact)
1. [Finding] — [Jordan update: one-sentence plain English summary]
2. ...

**Quick Wins** (implement within 1 week)
- [Actionable item]

**Longer-Term** (2–4 weeks)
- [Actionable item]

**Missing Flows** (not yet built)
- [Flow name] — [estimated revenue impact, e.g. "Abandoned cart recovers 5-15% of lost sales on average"]

---
Reply `/log` to save this to knowledge base"""


class EmailAuditAgent:

    def _load_context(self) -> str:
        parts = []
        if _PM_PATH.exists():
            parts.append(_PM_PATH.read_text(encoding="utf-8")[:1200])
        kb = build_knowledge_context()
        if kb:
            parts.append(f"=== Knowledge Base ===\n{kb}")
        return "\n\n".join(parts)

    async def audit(self, flow_info: str, ai) -> str:
        context = self._load_context()

        prompt = f"""EMAIL FLOW INFO (what you know about their current setup):
{flow_info}

BRAND CONTEXT:
{context}

Audit all 5 flows. Include the Jordan-update sentence for each top finding."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=1200, prefer="gemini")

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
