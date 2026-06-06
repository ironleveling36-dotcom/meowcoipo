"""
messages.py - Static and dynamic message templates
"""

from config import BOT_NAME, CURRENCY_SYMBOL


def welcome(full_name: str) -> str:
    return (
        f"👋 *Welcome to {BOT_NAME}!*\n\n"
        f"Hello, {full_name}! 🎉\n\n"
        f"We sell premium coupons, gift cards, promo codes,\n"
        f"and digital accounts at amazing prices.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ Browse our categories to get started!\n"
        f"📦 Fast delivery after payment verification.\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def maintenance() -> str:
    return (
        "🔧 *Bot Under Maintenance*\n\n"
        "We're working hard to improve your experience.\n"
        "Please check back soon! 🙏"
    )


def banned() -> str:
    return (
        "🚫 *Access Denied*\n\n"
        "Your account has been restricted.\n"
        "Contact support if you believe this is an error."
    )


def no_categories() -> str:
    return (
        "😔 *No categories available right now.*\n\n"
        "Please check back later!"
    )


def category_detail(name: str, price: float, stock: int) -> str:
    stock_indicator = "✅ In Stock" if stock > 0 else "❌ Out of Stock"
    return (
        f"🏷️ *{name}*\n\n"
        f"💰 Price: *{CURRENCY_SYMBOL}{price:.2f}* per item\n"
        f"📦 Stock: {stock_indicator} ({stock} available)\n\n"
        f"Select quantity below 👇"
    )


def payment_instructions(
    order_id: str, amount: float, upi_id: str, qty: int, cat_name: str
) -> str:
    return (
        f"💳 *Payment Details*\n\n"
        f"📋 Order ID : `{order_id}`\n"
        f"🛒 Category : {cat_name}\n"
        f"📦 Quantity : {qty}\n"
        f"💰 Amount   : *{CURRENCY_SYMBOL}{amount:.2f}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Pay via UPI:*\n"
        f"📱 UPI ID: `{upi_id}`\n\n"
        f"📸 Scan the QR code above OR transfer manually.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ *Important:*\n"
        f"• After payment, click 📸 *Upload Screenshot* (Faster approval)\n"
        f"• Then click ✅ *I Have Paid*\n"
        f"• Orders expire in 30 minutes\n"
    )


def awaiting_approval() -> str:
    return (
        "⏳ *Payment Submitted!*\n\n"
        "Your payment is being verified by our admin.\n"
        "You will receive your items shortly.\n\n"
        "🕐 Average approval time: 5–15 minutes"
    )


def order_approved_msg(order_id: str, category: str) -> str:
    return (
        f"🎊 *Order Approved!*\n\n"
        f"📋 Order: `{order_id}`\n"
        f"🛒 Category: {category}\n\n"
        f"Your items are below 👇"
    )


def order_rejected_msg(order_id: str, reason: str = None) -> str:
    msg = (
        f"❌ *Order Rejected*\n\n"
        f"📋 Order: `{order_id}`\n\n"
    )
    if reason:
        msg += f"📝 Reason: {reason}\n\n"
    msg += "If you believe this is a mistake, please contact support."
    return msg


def order_cancelled_msg(order_id: str) -> str:
    return (
        f"🚫 *Order Cancelled*\n\n"
        f"📋 Order: `{order_id}`\n\n"
        f"Your order has been cancelled successfully."
    )


def out_of_stock_msg(category: str) -> str:
    return (
        f"😔 *Out of Stock*\n\n"
        f"Sorry, *{category}* is currently out of stock.\n"
        f"Please try another category or check back later!"
    )


def help_msg() -> str:
    return (
        f"ℹ️ *Help & Support*\n\n"
        f"*How to Buy:*\n"
        f"1️⃣ Browse categories\n"
        f"2️⃣ Select quantity\n"
        f"3️⃣ Make UPI payment\n"
        f"4️⃣ Submit payment proof\n"
        f"5️⃣ Receive items instantly after approval\n\n"
        f"*Having issues?*\n"
        f"Contact our admin directly @rockzzz1.\n\n"
        f"*Refund Policy:*\n"
        f"Invalid items will be replaced or refunded."
    )


def channel_gate_msg(channel: str) -> str:
    return (
        f"🔒 *Access Restricted*\n\n"
        f"To use this bot, you must join our channel first.\n\n"
        f"📢 Channel: {channel}\n\n"
        f"👇 Click *Join Channel* below, then tap *I've Joined – Verify* to unlock the bot."
    )


def channel_not_joined_msg() -> str:
    return (
        "❌ *You haven't joined the channel yet!*\n\n"
        "Please join the channel first, then click *I've Joined – Verify*."
    )


def admin_welcome() -> str:
    return (
        "🛠️ *Admin Control Panel*\n\n"
        "Welcome back, Admin! 👋\n\n"
        "Select an option below to manage the bot:"
    )
