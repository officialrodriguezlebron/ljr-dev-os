import base64
import logging
import os
from pathlib import Path

import httpx

from core.knowledge_client import build_knowledge_context

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_PM_PATH = _VA_WORK_PATH / ".agents" / "product-marketing.md"

_SYSTEM = """You are a Senior Ecommerce Photo Editor reviewing product photography for Lazy Sun — vintage/heritage menswear, Portland ME.

EVALUATION CRITERIA (score each 1–5, then give overall verdict):

1. Background compliance — pure white (RGB 255,255,255) for hero shots; lifestyle appropriate for brand
2. Lighting quality — even, no harsh shadows, no blown highlights, shows texture accurately
3. Product size in frame — 70–85% frame fill for hero shots
4. Angle/composition — clean, professional, shows key details
5. Texture/material visibility — heritage buyer needs to see construction quality

VERDICTS:
- PASS: Ready for Shopify/TikTok. Ship it.
- NEEDS REVISION: List specific fixes with tool-specific instructions (Canva / Photoshop / Photopea)
- FAIL: Fundamental issue (wrong product, severe color cast, unusable quality). Do not publish.

TOOL-SPECIFIC FIX INSTRUCTIONS (use the right tool for each fix):
- Background removal/white: Canva → Edit photo → Background remover, OR Photoshop → Select Subject, then fill; OR Photopea (free Photoshop clone — same workflow as Photoshop)
- Brightness/exposure: Canva → Adjust → Brightness slider; Photoshop/Photopea → Image → Adjustments → Curves
- Color cast: Photoshop/Photopea → Image → Adjustments → Color Balance or Camera Raw Filter
- Crop/resize: Any tool — Shopify hero needs 1:1 (2048×2048px recommended)
- Sharpening: Photoshop/Photopea → Filter → Sharpen → Unsharp Mask

OUTPUT FORMAT:
Score Sheet:
| Criterion | Score (1–5) | Notes |
|-----------|-------------|-------|
| Background | | |
| Lighting | | |
| Frame fill | | |
| Composition | | |
| Texture visibility | | |

Overall: [PASS / NEEDS REVISION / FAIL]

[If NEEDS REVISION or FAIL]:
Fixes required:
1. [Fix — Tool: specific tool steps]
2. ...

Priority: [which fix matters most]

---
Reply `/log` to save this to knowledge base"""


class PhotoQaAgent:

    def _load_context(self) -> str:
        kb = build_knowledge_context()
        return f"=== Knowledge Base ===\n{kb}" if kb else ""

    async def review_from_url(self, image_url: str, context_note: str, ai) -> str:
        """Download image from URL and send to Gemini vision for review."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(image_url, follow_redirects=True)
                resp.raise_for_status()
            image_bytes = resp.content
            mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        except Exception as e:
            return f"❌ Could not download image from that URL: {e}\nTry a direct image link (ending in .jpg, .png, etc.)"

        return await self._review(image_bytes, mime_type, context_note, ai)

    async def review_from_bytes(self, image_bytes: bytes, mime_type: str, context_note: str, ai) -> str:
        """Review image from raw bytes (Telegram photo download)."""
        return await self._review(image_bytes, mime_type, context_note, ai)

    async def _review(self, image_bytes: bytes, mime_type: str, context_note: str, ai) -> str:
        kb = self._load_context()
        prompt = f"""Review this product photo for Lazy Sun ecommerce use.

Context: {context_note or "No additional context provided."}

{kb}

Apply all evaluation criteria and provide the score sheet + verdict + tool-specific fixes if needed."""

        try:
            result = await ai.gemini_vision(_SYSTEM, prompt, image_bytes, mime_type)
        except Exception as e:
            logger.warning(f"photo_qa: gemini_vision failed: {e}")
            return f"❌ Vision review failed: {e}\nMake sure GEMINI_API_KEY or GOOGLE_API_KEY is set in .env"

        if "/log" not in result:
            result += "\n\n---\nReply `/log` to save this to knowledge base"

        return result
