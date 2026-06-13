import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_BRAIN_PATH = Path(os.getenv("BRAIN_PATH", r"C:\Users\HomePC\ljr-brain"))
_PEOPLE_DIR = _BRAIN_PATH / "wiki" / "people"
_HOT_PATH = _BRAIN_PATH / "wiki" / "hot.md"
_LAZYSUN_PATH = _BRAIN_PATH / "wiki" / "projects" / "lazysun.md"

_SYSTEM = """You are drafting message replies for Lebron Rodriguez — Filipino freelance Shopify developer and eCommerce VA doing a trial with LazySun (started June 15, $400/mo, 20hrs/week).

Voice rules (non-negotiable across all variants):
- No filler openers ("Hope this finds you well", "Just checking in", "Great question")
- No em dashes
- First sentence does something — no warm-up phrase
- Peer-level tone — Lebron is a business partner, not a subordinate
- Under 100 words per variant unless the situation genuinely requires more
- Match the message's energy: casual if they're casual, direct if they're direct

Output EXACTLY this format — no deviation:
Context read: [who this is and what they're asking, 1 sentence]

A — Direct:
[reply, ready to send as-is]

B — Clarifying:
[reply that asks exactly one question, no more]

C — Warm-professional:
[reply with slightly more relational tone, use when early in engagement or after a gap]

Recommend: [which variant and exactly why, 1 sentence]

---
Log this in wiki/people/[sender-name].md? (yes/no)"""


class ReplyAgent:

    def _get_context(self, message: str) -> str:
        msg_lower = message.lower()
        parts = []

        candidates = []
        if "jordan" in msg_lower:
            candidates.append(("jordan-haddadi", "Jordan"))
        if "mark" in msg_lower and "marketing" not in msg_lower and "bookmark" not in msg_lower:
            candidates.append(("mark", "Mark"))

        for slug, _ in candidates:
            path = _PEOPLE_DIR / f"{slug}.md"
            if path.exists():
                parts.append(f"=== wiki/people/{slug}.md ===\n{path.read_text(encoding='utf-8')}")

        # Include LazySun project context when client is involved
        if candidates and _LAZYSUN_PATH.exists():
            content = _LAZYSUN_PATH.read_text(encoding="utf-8")
            # First 600 chars covers status + what I'm doing sections
            parts.append(f"=== wiki/projects/lazysun.md (summary) ===\n{content[:600]}")

        if not parts:
            parts.append("No wiki context found for this sender — use tone cues from the message only.")

        return "\n\n".join(parts)

    def _detect_sender_slug(self, message: str) -> str:
        msg_lower = message.lower()
        if "jordan" in msg_lower:
            return "jordan-haddadi"
        if "mark" in msg_lower and "marketing" not in msg_lower and "bookmark" not in msg_lower:
            return "mark"
        return "unknown"

    async def draft_reply(self, message: str, ai) -> str:
        people_ctx = self._get_context(message)
        hot_ctx = _HOT_PATH.read_text(encoding="utf-8") if _HOT_PATH.exists() else ""

        prompt = f"""MESSAGE TO REPLY TO:
{message}

WIKI CONTEXT ABOUT SENDER:
{people_ctx}

CURRENT SITUATION (hot.md):
{hot_ctx}

Draft 3 reply variants following the format in your system instructions."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=600)

        # Append log prompt if the AI dropped it
        if "Log this" not in result:
            slug = self._detect_sender_slug(message)
            result += f"\n\n---\nLog this in wiki/people/{slug}.md? (yes/no)"

        return result
