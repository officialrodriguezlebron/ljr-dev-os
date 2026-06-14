"""
Run Telegram bot + HTTP API server in a single process.

Shares one SupervisorAgent between both interfaces so session caches
(_last_output, _last_kyn) work correctly across Telegram and API calls.

Usage:
    python core/run_all.py
"""
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

import uvicorn
import core.api_server as api_server
from core.telegram_bot import build_app, supervisor as tg_supervisor

# Share the Telegram bot's supervisor with the API server so that
# session caches (_last_output, _last_kyn) are the same object
api_server._supervisor = tg_supervisor

log = logging.getLogger(__name__)


async def main() -> None:
    tg_app = build_app()

    config = uvicorn.Config(
        api_server.app,
        host="0.0.0.0",
        port=int(os.getenv("LJROS_API_PORT", "8000")),
        log_level="info",
    )
    server = uvicorn.Server(config)

    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram bot polling + HTTP API on :8000 — both running")

        await server.serve()  # blocks until Ctrl+C

        await tg_app.updater.stop()
        await tg_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
