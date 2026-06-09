import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class GroqClient:
    model = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    async def chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        try:
            return await self._groq(system, user, max_tokens)
        except Exception as e:
            logger.warning(f"Groq failed: {e} — trying Gemini")
        try:
            return await self._gemini(system, user)
        except Exception as e:
            logger.warning(f"Gemini failed: {e} — trying Ollama")
        return await self._ollama(system, user, max_tokens)

    async def extract_json(self, system: str, user: str) -> dict[str, Any]:
        json_system = system + "\n\nRespond with valid JSON only. No markdown, no explanation."
        raw = await self.chat(json_system, user, max_tokens=600)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    async def _groq(self, system: str, user: str, max_tokens: int) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
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

    async def _gemini(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={self.gemini_key}",
                json={
                    "contents": [{"parts": [{"text": f"{system}\n\n{user}"}]}]
                },
            )
            resp.raise_for_status()
            return (
                resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            )

    async def _ollama(self, system: str, user: str, max_tokens: int) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llama3",
                    "prompt": f"{system}\n\n{user}",
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
