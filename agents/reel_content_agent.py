import logging
import os
from pathlib import Path

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior Short-Form Video Strategist scripting Reels/TikToks for Lazy Sun — vintage/heritage menswear, Portland ME.

SKILL FOUNDATION (social short-form video + copywriting):
- 3-second rule: visual hook + verbal hook + text overlay all hit in the first second
- LazySun tone: specific, unhurried, peer-level — the shop has a POV, it's not performing nostalgia
- NEVER use: luxury, premium, elevated, curated. Say the specific thing instead.
- Target length: 15–30 seconds for product (Reels) / 30–60 seconds for story/process (TikTok)
- Pacing: 1 new visual or text overlay every 3–5 seconds
- CapCut instructions: be explicit — font, placement, timing, B-roll moment
- Captions: MAX 2 lines on screen, 3–5 words per line, bold sans-serif, keyword highlighted in accent color
- Sound: specify whether trending audio / original audio / VO fits better

OUTPUT FORMAT:

**Concept** (1 sentence)

**Hook** (first 3 seconds)
- Visual: [what camera sees]
- Verbal/VO: [exact words if spoken]
- Text overlay: [exact text, font style, placement]

**Structure** (second-by-second breakdown)
| Time | Visual | VO/Audio | Text Overlay |
|------|--------|----------|--------------|
| 0–3s | | | |
| 3–8s | | | |
...

**CapCut Edit Instructions**
1. [Specific step — e.g., "Cut clip at 3.2s to match beat drop"]
2. ...

**Caption** (for post — under 150 chars + hashtags on new line)

**Sound Recommendation**
[Trending audio suggestion OR original audio OR VO — and why]

**B-roll needed**
- [Shot list: what to film]

---
Reply `/log` to save this to knowledge base"""


class ReelContentAgent:

    def _load_context(self) -> str:
        parts = []
        if _PM_PATH.exists():
            parts.append(_PM_PATH.read_text(encoding="utf-8")[:1200])
        kb = build_knowledge_context()
        if kb:
            parts.append(f"=== Knowledge Base ===\n{kb}")
        return "\n\n".join(parts)

    async def write_reel(self, brief: str, ai) -> str:
        context = self._load_context()

        prompt = f"""REEL BRIEF:
{brief}

BRAND CONTEXT:
{context}

Script the full reel with CapCut instructions. Never use luxury/premium/elevated."""

        result = await ai.chat(_SYSTEM, prompt, max_tokens=1000, prefer="groq")

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
