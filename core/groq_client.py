import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"


class AIClient:
    """
    Priority chain:
    1. Groq  — fastest, free, 14400 req/day
    2. Gemini — free, 1500 req/day, Google AI Studio
    3. Claude — premium, only if ANTHROPIC_API_KEY set
    4. Ollama — local fallback, always available, slow
    """

    groq_model = "llama-3.3-70b-versatile"
    gemini_model = "gemini-2.0-flash"
    claude_model = "claude-sonnet-4-6"
    ollama_model = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

    def __init__(self) -> None:
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    async def chat(
        self,
        system: str,
        user: str,
        max_tokens: int = 400,
        prefer: str = "groq",
    ) -> str:
        """
        prefer = "groq" | "gemini" | "claude" | "ollama"
        Falls back down the chain if preferred provider fails or is unconfigured.
        Never fails silently — always returns a string.
        """
        chain = self._build_chain(prefer)
        last_error = ""
        for fn in chain:
            try:
                return await fn(system, user, max_tokens)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{fn.__name__} failed: {e}")
        return f"⚠️ All AI providers failed. Last error: {last_error}\nCheck API keys in .env."

    async def extract_json(self, system: str, user: str) -> dict[str, Any]:
        json_system = system + "\n\nRespond with valid JSON only. No markdown, no explanation."
        raw = await self.groq_chat(json_system, user, max_tokens=600)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Groq JSON parse failed, trying Gemini")
            try:
                raw2 = await self.gemini_chat(json_system, user, max_tokens=600)
                raw2 = raw2.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                return json.loads(raw2)
            except Exception:
                return {}

    async def groq_chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Groq — llama-3.3-70b-versatile — fastest, 14400 req/day free"""
        if not self.groq_key:
            raise ValueError("GROQ_API_KEY not set")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def gemini_chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Gemini 2.0 Flash — free 1500 req/day, good for longer outputs"""
        if not self.gemini_key:
            raise ValueError("GOOGLE_API_KEY / GEMINI_API_KEY not set")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={self.gemini_key}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"parts": [{"text": user}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
                },
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    async def claude_chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Claude Sonnet 4.6 — highest quality, ~$0.003/1K tokens, use sparingly"""
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                CLAUDE_URL,
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.claude_model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()

    async def ollama_chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Ollama local — deepseek-r1:8b — free, always available, 20-60s"""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": f"{system}\n\n{user}",
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()

    def get_available_providers(self) -> list[str]:
        providers = []
        if self.groq_key:
            providers.append("groq")
        if self.gemini_key:
            providers.append("gemini")
        if self.anthropic_key:
            providers.append("claude")
        providers.append("ollama")
        return providers

    def get_status(self) -> str:
        groq = "✅" if self.groq_key else "❌ no key"
        gemini = "✅" if self.gemini_key else "❌ no key"
        claude = "✅" if self.anthropic_key else "❌ no key"
        return f"Groq {groq} | Gemini {gemini} | Claude {claude} | Ollama ✅"

    def _build_chain(self, prefer: str):
        available = {
            "groq": (self.groq_chat, bool(self.groq_key)),
            "gemini": (self.gemini_chat, bool(self.gemini_key)),
            "claude": (self.claude_chat, bool(self.anthropic_key)),
            "ollama": (self.ollama_chat, True),
        }
        chain = []
        # Preferred provider first (if configured)
        if prefer in available and available[prefer][1]:
            chain.append(available[prefer][0])
        # Rest in default order
        for key in ["groq", "gemini", "claude", "ollama"]:
            if key != prefer:
                fn, configured = available[key]
                if configured:
                    chain.append(fn)
        return chain


# Backwards-compatible alias
GroqClient = AIClient
