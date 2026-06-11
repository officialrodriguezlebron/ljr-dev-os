import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from agents.supervisor import SupervisorAgent
from core.groq_client import AIClient

load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

supervisor = SupervisorAgent()
OWNER_ID = int(os.getenv("OWNER_TELEGRAM_ID", "0"))
_ai = AIClient()

logger.info("=" * 60)
logger.info("  LJR.devOS — Lebron's AI Operating System")
logger.info("=" * 60)
logger.info(f"  AI: {_ai.get_status()}")
logger.info(f"  Owner ID: {OWNER_ID}")
sheets_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")
sheets_ok = os.path.exists(sheets_path)
logger.info(f"  Sheets: {'✅ credentials found' if sheets_ok else '❌ ' + sheets_path + ' missing'}")
logger.info("=" * 60)


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if OWNER_ID and update.effective_user.id != OWNER_ID:
            logger.warning(
                f"Unauthorized access attempt: user_id={update.effective_user.id} "
                f"username=@{update.effective_user.username}"
            )
            await update.message.reply_text("❌ Unauthorized.")
            return
        await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


@owner_only
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.message.text.split()[0].lstrip("/").lower()
    args = " ".join(update.message.text.split()[1:])

    await update.message.chat.send_action("typing")
    response = await supervisor.route(command, args)

    # Telegram max message length is 4096
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(
                response[i : i + 4000],
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(response, parse_mode="Markdown")


@owner_only
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    try:
        if len(text) > 100:
            # Long text = assume it's a job post for KYN
            await update.message.chat.send_action("typing")
            response = await supervisor.route("kyn", text)
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "Send a command or paste a job post for instant KYN scoring.\n/help for all commands."
            )
    except Exception as e:
        logger.error(f"handle_text error: {e}", exc_info=True)
        await update.message.reply_text("❌ Something went wrong. Check logs.")


def build_app() -> Application:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN not set in .env")

    app = Application.builder().token(token).build()

    commands = [
        "overview", "applications", "today", "free", "schedule",
        "kyn", "analyze", "apply", "followup", "track", "stats",
        "me", "projects", "update", "done",
        "skills", "gaps",
        "learn", "roadmap", "log", "logshow",
        "plan", "next", "morning", "weekplan", "sprint",
        "idea", "ideas",
        "start", "help",
    ]

    for cmd in commands:
        app.add_handler(CommandHandler(cmd, handle_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


if __name__ == "__main__":
    import asyncio
    # Python 3.12+ no longer auto-creates an event loop — set one explicitly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Starting LJR.devOS bot...")
    app = build_app()
    logger.info("Bot running. Send /start on Telegram.")
    app.run_polling(drop_pending_updates=True)
