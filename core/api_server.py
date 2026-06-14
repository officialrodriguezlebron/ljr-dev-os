"""
LJR.devOS HTTP API — exposes supervisor.route() over HTTP so iPhone
Shortcuts (or any HTTP client) can call any bot command directly.

Standalone:  uvicorn core.api_server:app --host 0.0.0.0 --port 8000
Combined:    python core/run_all.py  (shares supervisor with Telegram bot)
"""
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
    command: str  # e.g. "/pdp" or "/tiktok Sonny Hat" (full string) or just "today"
    args: str = ""  # optional — split here if command already contains args


class CommandResponse(BaseModel):
    output: str


@app.post("/run", response_model=CommandResponse)
async def run_command(req: CommandRequest, x_api_key: str | None = Header(None)):
    """
    Execute any LJR.devOS command. Supports two calling styles:

    Style A — split:  {"command": "/pdp", "args": "Sonny Corduroy Hat Moss Green"}
    Style B — full:   {"command": "/tiktok Sonny Hat", "args": ""}

    Both produce the same result.
    """
    _verify_key(x_api_key)

    # Merge and re-split so both calling styles work identically
    full = f"{req.command} {req.args}".strip()
    parts = full.split(None, 1)
    command = parts[0].lstrip("/").lower()
    args = parts[1] if len(parts) > 1 else ""

    result = await _get_supervisor().route(command, args)
    return CommandResponse(output=result)


@app.get("/health")
async def health():
    sv = _get_supervisor()
    ai_status = sv.ai.get_status() if hasattr(sv, "ai") else "unknown"
    return {"status": "ok", "ai": ai_status}
