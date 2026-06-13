import datetime
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

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

# ConversationHandler states for /apply confirm gate
AWAITING_CONFIRM = 0
AWAITING_EDIT = 1


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if OWNER_ID and update.effective_user.id != OWNER_ID:
            logger.warning(
                f"Unauthorized access attempt: user_id={update.effective_user.id} "
                f"username=@{update.effective_user.username}"
            )
            await update.message.reply_text("❌ Unauthorized.")
            return ConversationHandler.END
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


@owner_only
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.message.text.split()[0].lstrip("/").lower()
    args = " ".join(update.message.text.split()[1:])

    await update.message.chat.send_action("typing")
    response = await supervisor.route(command, args)

    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(
                response[i : i + 4000],
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(response, parse_mode="Markdown")


@owner_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram photo upload → photo_qa_agent review."""
    await update.message.chat.send_action("typing")
    try:
        photo = update.message.photo[-1]  # Largest available size
        caption = update.message.caption or ""

        tg_file = await context.bot.get_file(photo.file_id)
        image_bytes = await tg_file.download_as_bytearray()

        response = await supervisor.photo_qa.review_from_bytes(
            bytes(image_bytes), "image/jpeg", caption, supervisor.ai
        )
        supervisor._last_output = {"agent": "photo_qa", "request": caption or "uploaded photo", "output": response}

        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i : i + 4000], parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"handle_photo error: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Photo review failed. Make sure GOOGLE_API_KEY is set in .env (Gemini vision required)."
        )


@owner_only
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    try:
        if len(text) > 100:
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


# ── /apply ConversationHandler ────────────────────────────────────────────────

@owner_only
async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = " ".join(update.message.text.split()[1:]).strip()
    if not args:
        await update.message.reply_text(
            "Usage: `/apply [url or job post text]`\n"
            "Tip: `/analyze` auto-logs without a confirm gate.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.chat.send_action("typing")

    from core.url_fetcher import detect_platform, fetch_job_post, is_fetch_error, is_url

    if is_url(args):
        platform = detect_platform(args)
        fetched = await fetch_job_post(args)
        if is_fetch_error(fetched):
            from core.url_fetcher import fetch_error_message
            await update.message.reply_text(f"❌ {fetch_error_message(fetched)}")
            return ConversationHandler.END
        job_text = fetched
    else:
        platform = "manual"
        job_text = args

    if len(job_text) < 50:
        await update.message.reply_text("Job post too short — paste the full text or a valid URL.")
        return ConversationHandler.END

    pkg = await supervisor.career.analyze_job(job_text)
    employer, role = supervisor.career.extract_employer_role(job_text)

    context.user_data["apply_pkg"] = pkg
    context.user_data["apply_employer"] = employer
    context.user_data["apply_role"] = role
    context.user_data["apply_platform"] = platform

    response = pkg.format_telegram()
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i : i + 4000], parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")

    await update.message.reply_text("*Apply?* Reply `YES` / `NO` / `EDIT`", parse_mode="Markdown")
    return AWAITING_CONFIRM


async def apply_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().upper()
    pkg = context.user_data.get("apply_pkg")
    employer = context.user_data.get("apply_employer", "Unknown")
    role = context.user_data.get("apply_role", "Unknown")
    platform = context.user_data.get("apply_platform", "direct")
    today = datetime.date.today()

    if not pkg:
        await update.message.reply_text("Session expired. Run /apply again.")
        return ConversationHandler.END

    if text == "YES":
        try:
            supervisor.sheets.append_row("APPLICATIONS", {
                "Date": today.isoformat(),
                "Platform": platform,
                "Employer": employer,
                "Role": role,
                "KYN Score": str(pkg.kyn.score),
                "Status": "applied",
                "Notes": pkg.kyn.verdict,
                "Follow-up Date": (today + datetime.timedelta(days=5)).isoformat(),
                "Replied": "No",
                "Offer": "",
            })
            await update.message.reply_text(
                f"✅ Logged: *{employer}* — {role} → `applied`", parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Sheets error: {e}\nManually track with /track.")
        context.user_data.clear()
        return ConversationHandler.END

    if text == "NO":
        try:
            supervisor.sheets.append_row("APPLICATIONS", {
                "Date": today.isoformat(),
                "Platform": platform,
                "Employer": employer,
                "Role": role,
                "KYN Score": str(pkg.kyn.score),
                "Status": "skipped",
                "Notes": "user skipped",
                "Follow-up Date": "",
                "Replied": "No",
                "Offer": "",
            })
        except Exception:
            pass
        await update.message.reply_text(
            f"Skipped *{employer}* — {role}. Logged as `skipped`.", parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    if text == "EDIT":
        await update.message.reply_text("Send your edited cover letter:")
        return AWAITING_EDIT

    await update.message.reply_text("Reply `YES`, `NO`, or `EDIT`", parse_mode="Markdown")
    return AWAITING_CONFIRM


async def apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pkg = context.user_data.get("apply_pkg")
    employer = context.user_data.get("apply_employer", "Unknown")
    role = context.user_data.get("apply_role", "Unknown")
    platform = context.user_data.get("apply_platform", "direct")
    today = datetime.date.today()

    try:
        supervisor.sheets.append_row("APPLICATIONS", {
            "Date": today.isoformat(),
            "Platform": platform,
            "Employer": employer,
            "Role": role,
            "KYN Score": str(pkg.kyn.score if pkg else ""),
            "Status": "applied",
            "Notes": "edited cover letter",
            "Follow-up Date": (today + datetime.timedelta(days=5)).isoformat(),
            "Replied": "No",
            "Offer": "",
        })
        await update.message.reply_text(
            f"✅ Logged with edited cover letter: *{employer}* — {role}", parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Sheets error: {e}\nManually track with /track.")

    context.user_data.clear()
    return ConversationHandler.END


async def apply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def apply_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pkg = context.user_data.get("apply_pkg")
    employer = context.user_data.get("apply_employer", "Unknown")
    role = context.user_data.get("apply_role", "Unknown")
    platform = context.user_data.get("apply_platform", "direct")
    today = datetime.date.today()

    if pkg:
        try:
            supervisor.sheets.append_row("APPLICATIONS", {
                "Date": today.isoformat(),
                "Platform": platform,
                "Employer": employer,
                "Role": role,
                "KYN Score": str(pkg.kyn.score),
                "Status": "pending-decision",
                "Notes": "no reply to confirm gate",
                "Follow-up Date": "",
                "Replied": "No",
                "Offer": "",
            })
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


# ── App builder ───────────────────────────────────────────────────────────────

def build_app() -> Application:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN not set in .env")

    app = Application.builder().token(token).build()

    # /apply ConversationHandler — must be added before generic CommandHandlers
    apply_handler = ConversationHandler(
        entry_points=[CommandHandler("apply", apply_start)],
        states={
            AWAITING_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_confirm)],
            AWAITING_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_edit)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, apply_timeout)],
        },
        fallbacks=[CommandHandler("cancel", apply_cancel)],
        conversation_timeout=600,  # 10 minutes — log as pending-decision on timeout
        per_user=True,
        per_chat=True,
    )
    app.add_handler(apply_handler)

    # All other commands route through handle_command → supervisor.route()
    commands = [
        "overview", "applications",
        "today", "adjust", "free", "schedule",
        "reply",
        "kyn", "analyze", "followup", "track", "stats",
        "me", "projects", "update", "done",
        "skills", "gaps",
        "learn", "roadmap", "log", "logshow",
        "plan", "next", "morning", "weekplan", "sprint",
        "idea", "ideas",
        # Phase 7 — ecommerce AI team
        "pdp", "photoreview", "tiktok", "meta", "contentcal", "emailaudit", "reel",
        # Time tracking
        "toggl", "hours", "togglreport",
        # Knowledge loop
        "feedback",
        "start", "help",
    ]

    for cmd in commands:
        app.add_handler(CommandHandler(cmd, handle_command))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Starting LJR.devOS bot...")
    app = build_app()
    logger.info("Bot running. Send /start on Telegram.")
    app.run_polling(drop_pending_updates=True)
