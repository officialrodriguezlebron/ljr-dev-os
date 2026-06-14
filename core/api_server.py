"""
LJR.devOS HTTP API — exposes supervisor.route() over HTTP so iPhone
Shortcuts (or any HTTP client) can call any bot command directly.

Standalone:  uvicorn core.api_server:app --host 0.0.0.0 --port 8000
Combined:    python core/run_all.py  (shares supervisor with Telegram bot)
"""
import asyncio
import logging
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LJR.devOS API",
    description="HTTP interface to LJR.devOS — same routing as Telegram bot",
)

# Populated by run_all.py when running combined; lazy-init otherwise
_supervisor: SupervisorAgent | None = None

API_KEY = os.getenv("LJROS_API_KEY")
if not API_KEY:
    logger.warning("LJROS_API_KEY not set — API is open (set it in .env before exposing to network)")

COMMAND_TIMEOUT = float(os.getenv("LJROS_API_TIMEOUT", "60"))

# Full command list matching supervisor._dispatch() routing table
_COMMANDS = {
    "daily": [
        "/overview", "/today", "/adjust [text]", "/reply [message]",
        "/applications", "/free", "/schedule [N]",
    ],
    "career": [
        "/analyze [url or text]", "/kyn [job post]", "/followup",
        "/stats", "/track [platform] [employer] [role] [kyn] [status]",
    ],
    "profile": [
        "/me", "/projects", "/update [project] [field] [value]",
        "/done [project] [new next task]", "/sprint",
    ],
    "skills": ["/skills", "/gaps"],
    "learning": [
        "/learn [skill]", "/roadmap [weeks]",
        "/log (no args — save last ecommerce output)",
        "/log [skill] [notes]", "/logshow",
    ],
    "planning": [
        "/plan [hours] [energy: high|medium|low]",
        "/next", "/morning", "/weekplan",
    ],
    "build": ["/idea [description]", "/ideas"],
    "ecommerce": [
        "/pdp [product info]", "/photoreview [url] [context]",
        "/tiktok [product info]", "/meta [product info]",
        "/contentcal [brief]", "/emailaudit [flow info]",
        "/reel [brief]", "/feedback [notes]",
    ],
    "time": ["/toggl [desc] [Xmin]", "/hours", "/togglreport"],
    "notes": [
        "/apply is Telegram-only (ConversationHandler with confirm gate)",
        "Photo upload QA is Telegram-only (send photo in chat)",
    ],
}


def _get_supervisor() -> SupervisorAgent:
    global _supervisor
    if _supervisor is None:
        logger.info("API: standalone mode — creating SupervisorAgent...")
        _supervisor = SupervisorAgent()
    return _supervisor


def _verify_key(x_api_key: str | None) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class CommandRequest(BaseModel):
    command: str  # "/pdp", "/tiktok Sonny Hat" (full string), or "today"
    args: str = ""  # optional — merged with command before parsing


class CommandResponse(BaseModel):
    output: str


@app.post("/run", response_model=CommandResponse)
async def run_command(req: CommandRequest, x_api_key: str | None = Header(None)):
    """
    Execute any LJR.devOS command. Supports two calling styles:

    Style A — split:  {"command": "/pdp", "args": "Sonny Corduroy Hat Moss Green"}
    Style B — full:   {"command": "/tiktok Sonny Hat", "args": ""}

    Both produce the same result. Times out after 60s (configurable via LJROS_API_TIMEOUT).
    """
    _verify_key(x_api_key)

    # Merge and re-split so both calling styles work identically
    full = f"{req.command} {req.args}".strip()
    parts = full.split(None, 1)
    command = parts[0].lstrip("/").lower()
    args = parts[1] if len(parts) > 1 else ""

    try:
        result = await asyncio.wait_for(
            _get_supervisor().route(command, args),
            timeout=COMMAND_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Command /{command} timed out after {COMMAND_TIMEOUT:.0f}s — try again or simplify the request",
        )

    return CommandResponse(output=result)


@app.get("/health")
async def health():
    sv = _get_supervisor()
    ai_status = sv.ai.get_status() if hasattr(sv, "ai") else "unknown"
    return {"status": "ok", "ai": ai_status}


@app.get("/commands")
async def list_commands():
    """All available commands grouped by category."""
    return _COMMANDS
