"""
handlers/admin.py - Complete admin control panel handlers
"""

import logging
import os
from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CommandHandler,
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
from utils import is_admin, format_delivery, safe_float, safe_int

logger = logging.getLogger(__name__)

# ── Conversation States ────────────────────────────────────────────────────────
(
    ADD_CAT_NAME, ADD_CAT_PRICE,
    EDIT_CAT_NAME, EDIT_CAT_PRICE,
    ADD_STOCK_ITEMS,
    SET_PRICE_VALUE,
    UPLOAD_QR,
    SET_UPI,
    BROADCAST_MSG,
    MANUAL_STOCK_DELTA,
    REJECT_REASON,
    BAN_UID, UNBAN_UID,
    SET_CHANNEL,
) = range(14)


# ── Guard ──────────────────────────────────────────────────────────────────────

def admin_only(func):
    """Decorator — silently rejects non-admin callers."""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Admin only!", show_alert=True)
            else:
                await update.message.reply_text("❌ You are not authorised.")
            return ConversationHandler.END
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _safe_edit(query, text: str, reply_markup=None):
    """Edit message text, ignoring 'message is not modified' errors."""
    try:
        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


# ── Admin Panel Entry ──────────────────────────────────────────────────────────

@admin_only
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        messages.admin_welcome(),
        reply_markup=keyboards.admin_panel_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )


@admin_only
async def cbq_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, messages.admin_welcome(), keyboards.admin_panel_kb())


# ── Categories ─────────────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_categories(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "📂 *Category Management*", keyboards.admin_categories_kb())


@admin_only
async def cbq_adm_list_cats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories(active_only=False)

    if not cats:
        text = "📂 *No categories found.*"
    else:
        lines = []
        for c in cats:
            stock = await db.stock_count(c["id"])
            status = "✅" if c["is_active"] else "❌"
            lines.append(
                f"{status} `{c['id']}` | *{c['name']}* | ₹{c['price']} | Stock: {stock}"
            )
        text = "📂 *All Categories:*\n\n" + "\n".join(lines)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_categories")]])
    await _safe_edit(query, text, kb)


# ── Add Category Conversation ──────────────────────────────────────────────────

@admin_only
async def cbq_add_cat_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "➕ *Add New Category*\n\nEnter the category name:")
    return ADD_CAT_NAME


async def add_cat_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Name cannot be empty.")
        return ADD_CAT_NAME
    ctx.user_data["new_cat_name"] = name
    await update.message.reply_text(
        f"✅ Name: *{name}*\n\nNow enter the price per item (e.g. `5` or `49.99`):",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADD_CAT_PRICE


async def add_cat_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    price = safe_float(update.message.text.strip())
    if price is None or price <= 0:
        await update.message.reply_text("❌ Invalid price. Enter a positive number (e.g. `5`):")
        return ADD_CAT_PRICE

    name = ctx.user_data.pop("new_cat_name", "")
    db = await Database.get_instance()
    try:
        cat_id = await db.add_category(name, price)
        await update.message.reply_text(
            f"✅ Category *{name}* added (ID: {cat_id}) at ₹{price:.2f} per item!",
            reply_markup=keyboards.admin_categories_kb(),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {e}\n\nCategory name may already exist.",
            reply_markup=keyboards.admin_categories_kb(),
        )
    return ConversationHandler.END


# ── Edit Category ──────────────────────────────────────────────────────────────

@admin_only
async def cbq_edit_cat_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories()
    if not cats:
        await _safe_edit(query, "No active categories available.", keyboards.back_to_admin_kb())
        return ConversationHandler.END
    await _safe_edit(
        query,
        "✏️ *Edit Category* — Select one:",
        keyboards.select_category_kb(cats, "edit_cat_pick_", "adm_categories"),
    )
    return EDIT_CAT_NAME


async def edit_cat_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("edit_cat_pick_")[1])
    ctx.user_data["edit_cat_id"] = cat_id
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    await _safe_edit(
        query,
        f"✏️ Editing: *{cat['name']}*\n\n"
        f"Enter new name (or `-` to keep *{cat['name']}*):",
    )
    return EDIT_CAT_NAME


async def edit_cat_name_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    ctx.user_data["edit_cat_new_name"] = None if val == "-" else val
    await update.message.reply_text(
        "Enter new price per item (or `-` to keep current):"
    )
    return EDIT_CAT_PRICE


async def edit_cat_price_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    cat_id = ctx.user_data.pop("edit_cat_id", None)
    new_name = ctx.user_data.pop("edit_cat_new_name", None)

    if val == "-":
        new_price = None
    else:
        new_price = safe_float(val)
        if new_price is None or new_price <= 0:
            await update.message.reply_text("❌ Invalid price. Operation cancelled.")
            return ConversationHandler.END

    db = await Database.get_instance()
    await db.update_category(cat_id, name=new_name, price=new_price)
    cat = await db.get_category(cat_id)
    await update.message.reply_text(
        f"✅ Category updated!\n\n*Name:* {cat['name']}\n*Price:* ₹{cat['price']:.2f}",
        reply_markup=keyboards.admin_categories_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Delete Category ────────────────────────────────────────────────────────────

@admin_only
async def cbq_del_cat_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories()
    if not cats:
        await _safe_edit(query, "No active categories.", keyboards.back_to_admin_kb())
        return
    await _safe_edit(
        query,
        "🗑️ *Delete Category* — Select one:",
        keyboards.select_category_kb(cats, "del_cat_pick_", "adm_categories"),
    )


async def cbq_del_cat_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("del_cat_pick_")[1])
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    await _safe_edit(
        query,
        f"⚠️ Delete *{cat['name']}*?\n_(Stock items are preserved)_",
        keyboards.confirm_delete_kb(cat_id),
    )


async def cbq_confirm_del_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("confirm_del_cat_")[1])
    db = await Database.get_instance()
    await db.delete_category(cat_id)
    await _safe_edit(
        query,
        "✅ Category hidden from users (soft-deleted).",
        keyboards.back_to_admin_kb(),
    )


# ── Stock Management ───────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_stock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "📦 *Stock Management*", keyboards.admin_stock_kb())


@admin_only
async def cbq_add_stock_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories()
    if not cats:
        await _safe_edit(query, "No active categories.", keyboards.back_to_admin_kb())
        return ConversationHandler.END
    await _safe_edit(
        query,
        "📥 *Add Stock* — Select category:",
        keyboards.select_category_kb(cats, "add_stock_cat_", "adm_stock"),
    )
    return ADD_STOCK_ITEMS


async def add_stock_cat_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("add_stock_cat_")[1])
    ctx.user_data["add_stock_cat_id"] = cat_id
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    await _safe_edit(
        query,
        f"📥 *Adding stock to: {cat['name']}*\n\n"
        "Send all items one per line:\n\n"
        "`CODE1234\nCODE5678\nCODE9012`\n\n"
        "_Paste as many as you like._",
    )
    return ADD_STOCK_ITEMS


async def add_stock_items_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cat_id = ctx.user_data.pop("add_stock_cat_id", None)
    if not cat_id:
        await update.message.reply_text("❌ Session expired. Please try again.")
        return ConversationHandler.END

    raw_lines = update.message.text.split("\n")
    items = [line.strip() for line in raw_lines if line.strip()]
    if not items:
        await update.message.reply_text("❌ No valid items found. Try again:")
        ctx.user_data["add_stock_cat_id"] = cat_id
        return ADD_STOCK_ITEMS

    db = await Database.get_instance()
    await db.add_stock_items(cat_id, items)
    stock = await db.stock_count(cat_id)
    cat = await db.get_category(cat_id)
    await update.message.reply_text(
        f"✅ Added *{len(items)}* items to *{cat['name']}*.\n📦 Total stock now: *{stock}*",
        reply_markup=keyboards.admin_stock_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


@admin_only
async def cbq_view_stock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    summary = await db.stock_summary()

    if not summary:
        text = "📊 No stock data available."
    else:
        lines = ["📊 *Stock Summary:*\n"]
        for row in summary:
            bar = "🟢" if row["available"] > 0 else "🔴"
            lines.append(
                f"{bar} *{row['name']}*\n"
                f"   Available: `{row['available']}` | Sold: `{row['sold']}` | "
                f"Price: ₹{row['price']:.2f}"
            )
        text = "\n".join(lines)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_stock")]])
    await _safe_edit(query, text, kb)


@admin_only
async def cbq_manual_stock_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories()
    if not cats:
        await _safe_edit(query, "No active categories.", keyboards.back_to_admin_kb())
        return ConversationHandler.END
    await _safe_edit(
        query,
        "⚙️ *Manual Stock Adjustment* — Select category:",
        keyboards.select_category_kb(cats, "manual_stock_cat_", "adm_stock"),
    )
    return MANUAL_STOCK_DELTA


async def manual_stock_cat_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("manual_stock_cat_")[1])
    ctx.user_data["manual_stock_cat"] = cat_id
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    stock = await db.stock_count(cat_id)
    await _safe_edit(
        query,
        f"⚙️ *{cat['name']}* — Current stock: `{stock}`\n\n"
        "Enter adjustment:\n"
        "• `+10` to add 10\n"
        "• `-5` to remove 5",
    )
    return MANUAL_STOCK_DELTA


async def manual_stock_delta_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cat_id = ctx.user_data.pop("manual_stock_cat", None)
    if not cat_id:
        await update.message.reply_text("❌ Session expired.")
        return ConversationHandler.END

    val = update.message.text.strip()
    delta = safe_int(val)
    if delta is None:
        await update.message.reply_text("❌ Invalid value. Use e.g. `+10` or `-5`.")
        return ConversationHandler.END

    db = await Database.get_instance()
    await db.manual_adjust_stock(cat_id, delta)
    cat = await db.get_category(cat_id)
    stock = await db.stock_count(cat_id)
    await update.message.reply_text(
        f"✅ Adjusted by `{delta:+d}`.\n📦 *{cat['name']}* → `{stock}` items.",
        reply_markup=keyboards.admin_stock_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Pricing ────────────────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_pricing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    cats = await db.get_categories()
    if not cats:
        await _safe_edit(query, "No active categories.", keyboards.back_to_admin_kb())
        return ConversationHandler.END
    await _safe_edit(
        query,
        "💰 *Set Price* — Select category:",
        keyboards.select_category_kb(cats, "set_price_cat_", "admin"),
    )
    return SET_PRICE_VALUE


async def set_price_cat_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("set_price_cat_")[1])
    ctx.user_data["set_price_cat"] = cat_id
    db = await Database.get_instance()
    cat = await db.get_category(cat_id)
    await _safe_edit(
        query,
        f"💰 *{cat['name']}*\n\nCurrent price: ₹{cat['price']:.2f}\n\nEnter new price:",
    )
    return SET_PRICE_VALUE


async def set_price_value_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cat_id = ctx.user_data.pop("set_price_cat", None)
    price = safe_float(update.message.text.strip())
    if price is None or price <= 0:
        await update.message.reply_text("❌ Invalid price. Please enter a positive number.")
        return ConversationHandler.END
    db = await Database.get_instance()
    await db.update_category(cat_id, price=price)
    cat = await db.get_category(cat_id)
    await update.message.reply_text(
        f"✅ *{cat['name']}* price updated to ₹{price:.2f}",
        reply_markup=keyboards.back_to_admin_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Payment Settings ───────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "💳 *Payment Settings*", keyboards.admin_payment_kb())


@admin_only
async def cbq_upload_qr_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "📷 *Upload QR Code*\n\nSend your QR code image now:")
    return UPLOAD_QR


async def receive_qr_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a photo/image of your QR code.")
        return UPLOAD_QR

    os.makedirs("data", exist_ok=True)
    file = await update.message.photo[-1].get_file()
    await file.download_to_drive("data/qr_code.jpg")

    db = await Database.get_instance()
    await db.set_setting("qr_path", "data/qr_code.jpg")
    await update.message.reply_text(
        "✅ QR code updated successfully!",
        reply_markup=keyboards.admin_payment_kb(),
    )
    return ConversationHandler.END


@admin_only
async def cbq_set_upi_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    current = await db.get_setting("upi_id") or "not set"
    await _safe_edit(
        query,
        f"🔗 *Set UPI ID*\n\nCurrent: `{current}`\n\nEnter new UPI ID:",
    )
    return SET_UPI


async def set_upi_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    upi = update.message.text.strip()
    if not upi:
        await update.message.reply_text("❌ UPI ID cannot be empty.")
        return SET_UPI
    db = await Database.get_instance()
    await db.set_setting("upi_id", upi)
    await update.message.reply_text(
        f"✅ UPI ID updated to: `{upi}`",
        reply_markup=keyboards.admin_payment_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Approve / Reject Orders ───────────────────────────────────────────────────

@admin_only
async def cbq_approve_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Processing approval...")
    order_id = query.data.split("approve_")[1]
    db = await Database.get_instance()

    order = await db.get_order(order_id)
    if not order:
        await _safe_edit(query, "❌ Order not found.", keyboards.back_to_admin_kb())
        return

    if order["status"] != "pending":
        await query.answer("Order already processed!", show_alert=True)
        return

    # Reserve stock
    items = await db.reserve_stock(order["category_id"], order["quantity"])
    if len(items) < order["quantity"]:
        await _safe_edit(
            query,
            f"❌ *Not enough stock!*\n\n"
            f"Available: {len(items)} | Required: {order['quantity']}\n\n"
            f"Please add more stock and try again.",
            keyboards.back_to_admin_kb(),
        )
        return

    # Mark items sold and link to order
    stock_ids = [item["id"] for item in items]
    await db.mark_sold(stock_ids)
    await db.add_order_items(order_id, stock_ids)
    await db.update_order_status(order_id, "approved")
    await db.log_transaction(
        order_id, order["user_id"], "ORDER_APPROVED", str(query.from_user.id)
    )

    cat = await db.get_category(order["category_id"])
    item_texts = [item["item"] for item in items]
    delivery_msg = format_delivery(
        item_texts, cat["name"] if cat else "N/A", order_id
    )

    # Deliver to user
    try:
        await ctx.bot.send_message(
            chat_id=order["user_id"],
            text=delivery_msg,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("Could not deliver to user %s: %s", order["user_id"], e)

    # Update admin-side message
    approved_text = (
        f"✅ *APPROVED* — Order `{order_id}`\n\n"
        f"📦 {order['quantity']} items delivered to user `{order['user_id']}`."
    )
    try:
        await query.edit_message_caption(
            caption=approved_text, parse_mode=ParseMode.MARKDOWN
        )
    except BadRequest:
        try:
            await query.edit_message_text(
                approved_text, parse_mode=ParseMode.MARKDOWN
            )
        except BadRequest:
            pass


@admin_only
async def cbq_reject_order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("reject_")[1]
    ctx.user_data["reject_order_id"] = order_id
    await _safe_edit(
        query,
        f"❌ *Reject Order* `{order_id}`\n\nEnter the reason for rejection:",
    )
    return REJECT_REASON


async def reject_reason_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    order_id = ctx.user_data.pop("reject_order_id", None)
    if not order_id:
        await update.message.reply_text("❌ Session expired.")
        return ConversationHandler.END

    db = await Database.get_instance()
    order = await db.get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return ConversationHandler.END

    await db.update_order_status(order_id, "rejected", reject_reason=reason)
    await db.log_transaction(
        order_id, order["user_id"], "ORDER_REJECTED", str(update.effective_user.id)
    )

    # Notify user
    try:
        await ctx.bot.send_message(
            chat_id=order["user_id"],
            text=messages.order_rejected_msg(order_id, reason),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("Could not notify user %s of rejection: %s", order["user_id"], e)

    await update.message.reply_text(
        f"✅ Order `{order_id}` rejected.\nUser has been notified.",
        reply_markup=keyboards.back_to_admin_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Pending Orders ─────────────────────────────────────────────────────────────

@admin_only
async def cbq_pending_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    orders = await db.get_pending_orders()

    if not orders:
        await _safe_edit(
            query, "📋 *No pending orders.*", keyboards.back_to_admin_kb()
        )
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for o in orders:
        name = o.get("username") or o.get("full_name") or str(o["user_id"])
        label = f"{o['order_id']} | {name} | ₹{o['amount']:.0f}"
        buttons.append([
            InlineKeyboardButton(f"✅ {label}", callback_data=f"approve_{o['order_id']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{o['order_id']}"),
        ])
    buttons.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")])

    await _safe_edit(
        query,
        f"📋 *Pending Orders ({len(orders)}):*\n\nTap ✅ to approve or ❌ to reject.",
        InlineKeyboardMarkup(buttons),
    )


# ── Analytics ──────────────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_analytics(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "📊 *Analytics & Reports*", keyboards.admin_analytics_kb())


@admin_only
async def cbq_total_sales(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    sales = await db.total_sales()
    orders = await db.total_orders()
    await _safe_edit(
        query,
        f"📈 *Sales Report*\n\n💰 Total Revenue: ₹{sales:,.2f}\n📦 Total Orders: {orders}",
        keyboards.admin_analytics_kb(),
    )


@admin_only
async def cbq_total_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    total = await db.count_users()
    banned_row = await db.fetchone("SELECT COUNT(*) as c FROM users WHERE is_banned=1")
    banned = banned_row["c"] if banned_row else 0
    await _safe_edit(
        query,
        f"👥 *User Stats*\n\n👤 Total Users : {total + banned}\n✅ Active : {total}\n🔨 Banned : {banned}",
        keyboards.admin_analytics_kb(),
    )


@admin_only
async def cbq_txn_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    txns = await db.get_transactions(limit=15)

    if not txns:
        text = "📋 No transactions recorded yet."
    else:
        lines = ["📋 *Recent Transactions (last 15):*\n"]
        for t in txns:
            lines.append(
                f"`{t['ts'][:16]}` | `{t['action']}` | `{t['order_id']}`"
            )
        text = "\n".join(lines)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_analytics")]])
    await _safe_edit(query, text, kb)


# ── User Management ────────────────────────────────────────────────────────────

@admin_only
async def cbq_adm_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "👥 *User Management*", keyboards.admin_users_kb())


@admin_only
async def cbq_user_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    active = await db.count_users()
    banned_row = await db.fetchone("SELECT COUNT(*) as c FROM users WHERE is_banned=1")
    banned = banned_row["c"] if banned_row else 0
    await _safe_edit(
        query,
        f"👤 *Detailed User Stats*\n\n"
        f"Total Registered : {active + banned}\n"
        f"Active Users     : {active}\n"
        f"Banned Users     : {banned}",
        keyboards.admin_users_kb(),
    )


@admin_only
async def cbq_ban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "🔨 Enter the *User ID* to ban:\n\n_(e.g. `123456789`)_")
    return BAN_UID


async def ban_uid_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = safe_int(update.message.text.strip())
    if not uid:
        await update.message.reply_text("❌ Invalid user ID. Enter a numeric ID:")
        return BAN_UID
    db = await Database.get_instance()
    await db.ban_user(uid)
    await update.message.reply_text(
        f"✅ User `{uid}` has been banned.",
        reply_markup=keyboards.admin_users_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


@admin_only
async def cbq_unban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, "✅ Enter the *User ID* to unban:\n\n_(e.g. `123456789`)_")
    return UNBAN_UID


async def unban_uid_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = safe_int(update.message.text.strip())
    if not uid:
        await update.message.reply_text("❌ Invalid user ID.")
        return UNBAN_UID
    db = await Database.get_instance()
    await db.unban_user(uid)
    await update.message.reply_text(
        f"✅ User `{uid}` has been unbanned.",
        reply_markup=keyboards.admin_users_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Broadcast ──────────────────────────────────────────────────────────────────

@admin_only
async def cbq_broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    count = await db.count_users()
    await _safe_edit(
        query,
        f"📢 *Broadcast Message*\n\n"
        f"Will be sent to *{count}* active users.\n\n"
        "Type your message now:",
    )
    return BROADCAST_MSG


async def broadcast_msg_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Message is empty.")
        return BROADCAST_MSG

    db = await Database.get_instance()
    users = await db.get_all_users()

    success, fail = 0, 0
    for user in users:
        try:
            await ctx.bot.send_message(
                chat_id=user["user_id"],
                text=f"📢 *Announcement:*\n\n{text}",
                parse_mode=ParseMode.MARKDOWN,
            )
            success += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"📢 *Broadcast Complete!*\n\n✅ Sent: {success}\n❌ Failed: {fail}",
        reply_markup=keyboards.back_to_admin_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Maintenance ────────────────────────────────────────────────────────────────

@admin_only
async def cbq_maintenance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    current = await db.get_setting("maintenance")
    new_val = "false" if current == "true" else "true"
    await db.set_setting("maintenance", new_val)
    if new_val == "true":
        status = "🔴 *ON* — Users will see maintenance message"
    else:
        status = "🟢 *OFF* — Bot is live for users"
    await _safe_edit(
        query,
        f"🔧 *Maintenance Mode: {status}*",
        keyboards.back_to_admin_kb(),
    )


# ── Backup ─────────────────────────────────────────────────────────────────────

@admin_only
async def cbq_backup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Creating backup...")
    db = await Database.get_instance()
    try:
        backup_path = await db.backup()
        with open(backup_path, "rb") as f:
            await ctx.bot.send_document(
                chat_id=query.from_user.id,
                document=InputFile(f, filename=os.path.basename(backup_path)),
                caption=f"💾 Database backup\n🕒 {os.path.basename(backup_path)}",
            )
        await _safe_edit(query, "✅ Backup sent to you!", keyboards.back_to_admin_kb())
    except Exception as e:
        logger.error("Backup failed: %s", e)
        await _safe_edit(
            query,
            f"❌ Backup failed: {e}",
            keyboards.back_to_admin_kb(),
        )


# ── Channel Gate Management ────────────────────────────────────────────────────

@admin_only
async def cbq_adm_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show current channel gate setting with set / clear options."""
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    current = await db.get_setting("required_channel") or ""
    if current:
        status = f"🟢 *Active* — `{current}`"
    else:
        status = "🔴 *Disabled* — No channel required"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Set Channel", callback_data="adm_set_channel")],
        [InlineKeyboardButton("🗑️ Remove Channel Gate", callback_data="adm_clear_channel")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])
    await _safe_edit(
        query,
        f"📢 *Channel Gate*\n\nStatus: {status}\n\n"
        f"When a channel is set, users must join it before accessing the bot.\n"
        f"Admins always bypass the gate.",
        kb,
    )


@admin_only
async def cbq_set_channel_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit(
        query,
        "📢 *Set Required Channel*\n\n"
        "Send the channel username or ID:\n\n"
        "• Username: `@mychannel`\n"
        "• Numeric ID: `-1001234567890`\n\n"
        "⚠️ Make sure the bot is an *admin* in that channel so it can verify membership.",
    )
    return SET_CHANNEL


async def set_channel_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    if not val:
        await update.message.reply_text("❌ Value cannot be empty.")
        return SET_CHANNEL

    # Basic validation
    if not (val.startswith("@") or val.lstrip("-").isdigit()):
        await update.message.reply_text(
            "❌ Invalid format.\n\nUse `@username` or a numeric ID like `-1001234567890`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return SET_CHANNEL

    db = await Database.get_instance()
    await db.set_setting("required_channel", val)
    await update.message.reply_text(
        f"✅ Required channel set to `{val}`\n\n"
        f"Users who are not members will now see a join prompt on `/start`.",
        reply_markup=keyboards.back_to_admin_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


@admin_only
async def cbq_clear_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = await Database.get_instance()
    await db.set_setting("required_channel", "")
    await _safe_edit(
        query,
        "✅ Channel gate *disabled*.\n\nAll users can now access the bot freely.",
        keyboards.back_to_admin_kb(),
    )


# ── Register All Admin Handlers ────────────────────────────────────────────────

def register_admin_handlers(app):
    # ── Plain callback handlers (no conversation state needed)
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(cbq_admin,            pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_categories,   pattern="^adm_categories$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_list_cats,    pattern="^adm_list_cats$"))
    app.add_handler(CallbackQueryHandler(cbq_del_cat_start,    pattern="^adm_del_cat$"))
    app.add_handler(CallbackQueryHandler(cbq_del_cat_pick,     pattern=r"^del_cat_pick_\d+$"))
    app.add_handler(CallbackQueryHandler(cbq_confirm_del_cat,  pattern=r"^confirm_del_cat_\d+$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_stock,        pattern="^adm_stock$"))
    app.add_handler(CallbackQueryHandler(cbq_view_stock,       pattern="^adm_view_stock$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_payment,      pattern="^adm_payment$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_analytics,    pattern="^adm_analytics$"))
    app.add_handler(CallbackQueryHandler(cbq_total_sales,      pattern="^adm_total_sales$"))
    app.add_handler(CallbackQueryHandler(cbq_total_users,      pattern="^adm_total_users$"))
    app.add_handler(CallbackQueryHandler(cbq_txn_log,          pattern="^adm_txn_log$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_users,        pattern="^adm_users$"))
    app.add_handler(CallbackQueryHandler(cbq_user_stats,       pattern="^adm_user_stats$"))
    app.add_handler(CallbackQueryHandler(cbq_pending_orders,   pattern="^adm_pending$"))
    app.add_handler(CallbackQueryHandler(cbq_approve_order,    pattern=r"^approve_ORD-\w+-\w+$"))
    app.add_handler(CallbackQueryHandler(cbq_maintenance,      pattern="^adm_maintenance$"))
    app.add_handler(CallbackQueryHandler(cbq_backup,           pattern="^adm_backup$"))
    app.add_handler(CallbackQueryHandler(cbq_adm_channel,      pattern="^adm_channel$"))
    app.add_handler(CallbackQueryHandler(cbq_clear_channel,    pattern="^adm_clear_channel$"))

    # ── Add Category Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_add_cat_start, pattern="^adm_add_cat$")],
        states={
            ADD_CAT_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_name)],
            ADD_CAT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_price)],
        },
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Edit Category Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_edit_cat_start, pattern="^adm_edit_cat$")],
        states={
            EDIT_CAT_NAME: [
                CallbackQueryHandler(edit_cat_pick, pattern=r"^edit_cat_pick_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_cat_name_input),
            ],
            EDIT_CAT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_cat_price_input)],
        },
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Add Stock Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_add_stock_start, pattern="^adm_add_stock$")],
        states={
            ADD_STOCK_ITEMS: [
                CallbackQueryHandler(add_stock_cat_pick, pattern=r"^add_stock_cat_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_stock_items_input),
            ],
        },
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Set Price Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_adm_pricing, pattern="^adm_pricing$")],
        states={
            SET_PRICE_VALUE: [
                CallbackQueryHandler(set_price_cat_pick, pattern=r"^set_price_cat_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_price_value_input),
            ],
        },
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Upload QR Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_upload_qr_start, pattern="^adm_upload_qr$")],
        states={UPLOAD_QR: [MessageHandler(filters.PHOTO, receive_qr_code)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Set UPI Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_set_upi_start, pattern="^adm_set_upi$")],
        states={SET_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_upi_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Broadcast Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_broadcast_start, pattern="^adm_broadcast$")],
        states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Manual Stock Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_manual_stock_start, pattern="^adm_manual_stock$")],
        states={
            MANUAL_STOCK_DELTA: [
                CallbackQueryHandler(manual_stock_cat_pick, pattern=r"^manual_stock_cat_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_stock_delta_input),
            ],
        },
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Reject Reason Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_reject_order_start, pattern=r"^reject_ORD-\w+-\w+$")],
        states={REJECT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, reject_reason_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Ban User Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_ban_start, pattern="^adm_ban$")],
        states={BAN_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_uid_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Unban User Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_unban_start, pattern="^adm_unban$")],
        states={UNBAN_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_uid_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))

    # ── Set Required Channel Conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cbq_set_channel_start, pattern="^adm_set_channel$")],
        states={SET_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_channel_input)]},
        fallbacks=[CommandHandler("admin", cmd_admin)],
        per_chat=True, per_user=True,
    ))
