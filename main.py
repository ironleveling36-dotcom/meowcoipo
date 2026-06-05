"""
main.py - Entry point for the Telegram Coupon & Account Selling Bot
Supports both polling (local dev) and webhook mode (Railway / production).
"""

import asyncio
import logging
import os
import sys
import warnings

# ── Suppress known harmless PTB warnings about per_message ───────────────────
from telegram.warnings import PTBUserWarning
warnings.filterwarnings(
    "ignore",
    message=r".*per_message=False.*",
    category=PTBUserWarning,
)

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from config import (
    BOT_TOKEN,
    WEBHOOK_URL,
    PORT,
    LOG_LEVEL,
)
from database import Database
from handlers.user import register_user_handlers
from handlers.payment import register_payment_handlers
from handlers.admin import register_admin_handlers

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ── post_init callback ─────────────────────────────────────────────────────────

async def _post_init(app: Application) -> None:
    """Called once after the Application is initialised but before polling/webhook starts."""
    os.makedirs("data", exist_ok=True)
    await Database.get_instance()   # warm up / create tables
    commands = [
        BotCommand("start", "🏠 Start the bot"),
        BotCommand("admin", "🛠️ Admin panel (admins only)"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✅ Bot initialised — commands set, database ready.")


# ── Application Setup ──────────────────────────────────────────────────────────

def build_app() -> Application:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set. Check your .env file or Railway variables.")
        sys.exit(1)

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(_post_init)      # ← correct PTB 21 builder pattern
        .build()
    )

    # Register all handlers  (ConversationHandlers must come before plain CBQ handlers)
    register_admin_handlers(app)
    register_payment_handlers(app)
    register_user_handlers(app)

    return app


# ── Run ────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    app = build_app()

    if WEBHOOK_URL:
        # ── Webhook mode (Railway / production)
        webhook_path = f"/webhook/{BOT_TOKEN}"
        full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{webhook_path}"
        logger.info("Starting in WEBHOOK mode — port %s → %s", PORT, full_webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=full_webhook_url,
        )
    else:
        # ── Polling mode (local development)
        logger.info("Starting in POLLING mode (local dev).")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
