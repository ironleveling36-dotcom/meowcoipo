"""
config.py - Central configuration for the Telegram Coupon & Account Selling Bot
All sensitive values are loaded from environment variables for Railway / .env support.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot Credentials ──────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# ── Payment ───────────────────────────────────────────────────────────────────
UPI_ID: str = os.getenv("UPI_ID", "yourname@upi")
QR_CODE_PATH: str = os.getenv("QR_CODE_PATH", "data/qr_code.jpg")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "data/bot.db")   # SQLite path

# ── Feature Flags ─────────────────────────────────────────────────────────────
MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

# ── Misc ──────────────────────────────────────────────────────────────────────
BOT_NAME: str = os.getenv("BOT_NAME", "CouponBot")
CURRENCY_SYMBOL: str = os.getenv("CURRENCY_SYMBOL", "₹")
PAYMENT_TIMEOUT_MINUTES: int = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "30"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")   # Set on Railway for webhook mode
PORT: int = int(os.getenv("PORT", "8443"))
