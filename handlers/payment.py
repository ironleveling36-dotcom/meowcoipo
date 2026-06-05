"""
handlers/payment.py - Payment flow: quantity selection → QR → paid → admin approval
"""

import logging
import os
from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

import messages
import keyboards
from database import Database
from utils import generate_order_id, format_invoice, format_admin_notification, safe_int
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# ConversationHandler states
CUSTOM_QTY = 1
UPLOAD_SS = 2


# ── Quantity Selection ────────────────────────────────────────────────────────

async def cbq_quantity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle preset quantity buttons like qty_{cat_id}_{qty}"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    cat_id = int(parts[1])
    qty = int(parts[2])
    await _process_quantity(query, ctx, cat_id, qty)


async def cbq_custom_quantity_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Start custom quantity conversation."""
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("qty_custom_")[1])
    ctx.user_data["pending_cat_id"] = cat_id

    await query.edit_message_text(
        "✏️ *Enter Custom Quantity*\n\n"
        "Please type the number of items you want to buy.\n"
        "_(Send a number between 1 and 100)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return CUSTOM_QTY


async def receive_custom_qty(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cat_id = ctx.user_data.get("pending_cat_id")
    if not cat_id:
        await update.message.reply_text("❌ Session expired. Please start again with /start")
        return ConversationHandler.END

    qty = safe_int(update.message.text.strip())
    if not qty or qty < 1 or qty > 100:
        await update.message.reply_text(
            "❌ Please enter a number between 1 and 100."
        )
        return CUSTOM_QTY

    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    if not cat:
        await update.message.reply_text("❌ Category not found.")
        return ConversationHandler.END

    stock = await db.stock_count(cat_id)
    if qty > stock:
        await update.message.reply_text(
            f"❌ Not enough stock. Only *{stock}* items available.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return CUSTOM_QTY

    ctx.user_data.pop("pending_cat_id", None)
    await _create_and_send_payment_from_message(update, ctx, cat, qty)
    return ConversationHandler.END


async def _process_quantity(query, ctx, cat_id: int, qty: int):
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    if not cat:
        await query.answer("Category not found!", show_alert=True)
        return

    stock = await db.stock_count(cat_id)
    if qty > stock:
        await query.edit_message_text(
            f"❌ *Not enough stock!*\n\nOnly *{stock}* items available for *{cat['name']}*.\n"
            f"Please choose a smaller quantity.",
            reply_markup=keyboards.quantity_kb(cat_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await _create_and_send_payment_from_callback(query, ctx, cat, qty)


async def _create_and_send_payment_from_callback(query, ctx, cat: dict, qty: int):
    """Send payment details after a callback query (quantity button press)."""
    db = await Database.get_instance()
    user = query.from_user
    amount = cat["price"] * qty
    order_id = generate_order_id()

    await db.create_order(order_id, user.id, cat["id"], qty, amount)
    await db.log_transaction(order_id, user.id, "ORDER_CREATED", str(user.id))

    upi_id = await db.get_setting("upi_id") or "yourname@upi"
    qr_path = await db.get_setting("qr_path") or "data/qr_code.jpg"

    invoice_text = format_invoice(
        order_id, user.username or "", user.full_name,
        cat["name"], qty, cat["price"], amount
    )
    payment_text = messages.payment_instructions(order_id, amount, upi_id, qty, cat["name"])
    full_text = invoice_text + "\n" + payment_text

    try:
        if os.path.exists(qr_path):
            # Delete the old inline-keyboard message first, then send photo
            try:
                await query.edit_message_text("⏳ Preparing your order...")
            except BadRequest:
                pass
            with open(qr_path, "rb") as qr_file:
                await ctx.bot.send_photo(
                    chat_id=user.id,
                    photo=InputFile(qr_file),
                    caption=full_text,
                    reply_markup=keyboards.payment_kb(order_id),
                    parse_mode=ParseMode.MARKDOWN,
                )
        else:
            await query.edit_message_text(
                full_text,
                reply_markup=keyboards.payment_kb(order_id),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error("Error sending payment details: %s", e)
        try:
            await ctx.bot.send_message(
                chat_id=user.id,
                text=full_text,
                reply_markup=keyboards.payment_kb(order_id),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e2:
            logger.error("Fallback send also failed: %s", e2)


async def _create_and_send_payment_from_message(update: Update, ctx, cat: dict, qty: int):
    """Send payment details in response to a text message (custom qty flow)."""
    db = await Database.get_instance()
    user = update.effective_user
    amount = cat["price"] * qty
    order_id = generate_order_id()

    await db.create_order(order_id, user.id, cat["id"], qty, amount)
    await db.log_transaction(order_id, user.id, "ORDER_CREATED", str(user.id))

    upi_id = await db.get_setting("upi_id") or "yourname@upi"
    qr_path = await db.get_setting("qr_path") or "data/qr_code.jpg"

    invoice_text = format_invoice(
        order_id, user.username or "", user.full_name,
        cat["name"], qty, cat["price"], amount
    )
    payment_text = messages.payment_instructions(order_id, amount, upi_id, qty, cat["name"])
    full_text = invoice_text + "\n" + payment_text

    try:
        if os.path.exists(qr_path):
            with open(qr_path, "rb") as qr_file:
                await update.message.reply_photo(
                    photo=InputFile(qr_file),
                    caption=full_text,
                    reply_markup=keyboards.payment_kb(order_id),
                    parse_mode=ParseMode.MARKDOWN,
                )
        else:
            await update.message.reply_text(
                full_text,
                reply_markup=keyboards.payment_kb(order_id),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error("Error sending payment details: %s", e)


# ── Payment Screenshot Upload ─────────────────────────────────────────────────

async def cbq_upload_ss(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("upload_ss_")[1]
    ctx.user_data["ss_order_id"] = order_id

    # Disable the button row to prevent double-click
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass

    await ctx.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            "📸 *Upload Payment Screenshot*\n\n"
            f"Order: `{order_id}`\n\n"
            "Please send a screenshot / photo of your payment now.\n"
            "_You can cancel by typing /start_"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )
    return UPLOAD_SS


async def receive_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    order_id = ctx.user_data.get("ss_order_id")
    if not order_id:
        await update.message.reply_text("❌ No active order found. Please start again.")
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send an *image* (photo) of your payment.\n"
            "Use your camera or gallery.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return UPLOAD_SS

    file_id = update.message.photo[-1].file_id
    db = await Database.get_instance()

    order = await db.get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return ConversationHandler.END

    if order["status"] != "pending":
        await update.message.reply_text("⚠️ This order has already been processed.")
        return ConversationHandler.END

    await db.update_order_status(order_id, "pending", screenshot=file_id)
    ctx.user_data.pop("ss_order_id", None)

    await update.message.reply_text(
        f"✅ Screenshot saved for order `{order_id}`!\n\n"
        "Now click the button below to submit your payment for admin review.",
        reply_markup=keyboards.after_ss_kb(order_id),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Paid Button ────────────────────────────────────────────────────────────────

async def cbq_paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Payment submitted! Awaiting admin approval.")
    order_id = query.data.split("paid_")[1]
    user = query.from_user

    db = await Database.get_instance()
    order = await db.get_order(order_id)

    if not order:
        try:
            await query.edit_message_text("❌ Order not found.")
        except BadRequest:
            pass
        return

    if order["user_id"] != user.id:
        await query.answer("Unauthorized!", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer("This order has already been processed.", show_alert=True)
        return

    await db.log_transaction(order_id, user.id, "PAYMENT_SUBMITTED", str(user.id))

    cat = await db.get_category(order["category_id"])
    notif_text = format_admin_notification(
        order_id,
        user.id,
        user.username or "",
        user.full_name,
        cat["name"] if cat else "N/A",
        order["quantity"],
        order["amount"],
    )

    # Notify all admins
    for admin_id in ADMIN_IDS:
        try:
            screenshot = order.get("screenshot")
            if screenshot:
                await ctx.bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot,
                    caption=notif_text,
                    reply_markup=keyboards.approve_reject_kb(order_id),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await ctx.bot.send_message(
                    chat_id=admin_id,
                    text=notif_text,
                    reply_markup=keyboards.approve_reject_kb(order_id),
                    parse_mode=ParseMode.MARKDOWN,
                )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)

    # Update the user-facing message
    awaiting_text = messages.awaiting_approval()
    try:
        # Try editing caption (if it's a photo message)
        await query.edit_message_caption(
            caption=awaiting_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except BadRequest:
        try:
            # Fall back to editing text
            await query.edit_message_text(
                awaiting_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest:
            # Can't edit (e.g. message too old) — send a new one
            await ctx.bot.send_message(
                chat_id=user.id,
                text=awaiting_text,
                parse_mode=ParseMode.MARKDOWN,
            )


# ── Cancel Order ───────────────────────────────────────────────────────────────

async def cbq_cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("cancel_")[1]
    user = query.from_user

    db = await Database.get_instance()
    order = await db.get_order(order_id)

    if not order or order["user_id"] != user.id:
        await query.answer("Order not found!", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer("Order already processed.", show_alert=True)
        return

    await db.update_order_status(order_id, "cancelled")
    await db.log_transaction(order_id, user.id, "ORDER_CANCELLED", str(user.id))

    cancelled_text = messages.order_cancelled_msg(order_id)
    try:
        await query.edit_message_caption(
            caption=cancelled_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except BadRequest:
        try:
            await query.edit_message_text(
                cancelled_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest:
            await ctx.bot.send_message(
                chat_id=user.id,
                text=cancelled_text,
                parse_mode=ParseMode.MARKDOWN,
            )


# ── Register ───────────────────────────────────────────────────────────────────

def register_payment_handlers(app):
    # Custom quantity conversation
    custom_qty_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cbq_custom_quantity_start, pattern=r"^qty_custom_\d+$")
        ],
        states={
            CUSTOM_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_qty)]
        },
        fallbacks=[],
        per_chat=True,
        per_user=True,
    )

    # Screenshot upload conversation
    ss_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cbq_upload_ss, pattern=r"^upload_ss_ORD-\w+-\w+$")
        ],
        states={
            UPLOAD_SS: [MessageHandler(filters.PHOTO, receive_screenshot)]
        },
        fallbacks=[],
        per_chat=True,
        per_user=True,
    )

    app.add_handler(custom_qty_conv)
    app.add_handler(ss_conv)

    app.add_handler(CallbackQueryHandler(cbq_quantity, pattern=r"^qty_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(cbq_paid, pattern=r"^paid_ORD-\w+-\w+$"))
    app.add_handler(CallbackQueryHandler(cbq_cancel_order, pattern=r"^cancel_ORD-\w+-\w+$"))
