"""
utils/helpers.py - Utility functions shared across the bot
"""

import random
import string
import logging
from datetime import datetime
from typing import Optional

from config import ADMIN_IDS, CURRENCY_SYMBOL

logger = logging.getLogger(__name__)


def generate_order_id() -> str:
    """Generate a unique order ID like ORD-20240524-AB3F."""
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date_part}-{rand_part}"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_currency(amount: float) -> str:
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def format_invoice(
    order_id: str,
    username: str,
    full_name: str,
    category: str,
    quantity: int,
    price_per: float,
    total: float,
) -> str:
    return (
        f"╔══════════════════════════╗\n"
        f"       🧾 ORDER INVOICE\n"
        f"╚══════════════════════════╝\n\n"
        f"📋 Order ID  : `{order_id}`\n"
        f"👤 Name      : {full_name}\n"
        f"🆔 Username  : @{username or 'N/A'}\n\n"
        f"🛒 Category  : {category}\n"
        f"📦 Quantity  : {quantity}\n"
        f"💰 Unit Price: {format_currency(price_per)}\n"
        f"💳 Total     : {format_currency(total)}\n\n"
        f"🕒 Date      : {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
    )


def format_delivery(items: list[str], category: str, order_id: str) -> str:
    items_text = "\n".join(f"  {i+1}. `{item}`" for i, item in enumerate(items))
    return (
        f"✅ *Order Delivered!*\n\n"
        f"📋 Order: `{order_id}`\n"
        f"🛒 Category: {category}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 *Your Items:*\n\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🙏 *Thank you for your purchase!*\n"
        f"📞 Support: Contact admin if any item is invalid."
    )


def format_admin_notification(
    order_id: str,
    user_id: int,
    username: str,
    full_name: str,
    category: str,
    quantity: int,
    amount: float,
) -> str:
    return (
        f"🔔 *NEW PAYMENT NOTIFICATION*\n\n"
        f"📋 Order ID  : `{order_id}`\n"
        f"👤 Name      : {full_name}\n"
        f"🆔 User ID   : `{user_id}`\n"
        f"👥 Username  : @{username or 'N/A'}\n\n"
        f"🛒 Category  : {category}\n"
        f"📦 Quantity  : {quantity}\n"
        f"💰 Amount    : {format_currency(amount)}\n\n"
        f"⏳ *Awaiting your approval...*"
    )


def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def safe_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
