"""
keyboards.py - All InlineKeyboardMarkup builders for the bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import chunks


# ── User Keyboards ────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Browse Categories", callback_data="browse")],
        [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("ℹ️ Help / Support", callback_data="help")],
    ])


def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"🏷️ {cat['name']} ({cat['price']:.0f}₹ each)", callback_data=f"cat_{cat['id']}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def quantity_kb(cat_id: int) -> InlineKeyboardMarkup:
    quantities = [1, 2, 5, 10]
    rows = list(chunks(
        [InlineKeyboardButton(str(q), callback_data=f"qty_{cat_id}_{q}") for q in quantities],
        2
    ))
    rows.append([InlineKeyboardButton("✏️ Custom Quantity", callback_data=f"qty_custom_{cat_id}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="browse")])
    return InlineKeyboardMarkup(rows)


def payment_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Upload Payment Screenshot", callback_data=f"upload_ss_{order_id}")],
        [InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_{order_id}")],
    ])


def after_ss_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_{order_id}")],
    ])


def my_orders_kb(orders: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"#{o['order_id']} — {o['status'].upper()}",
            callback_data=f"view_order_{o['order_id']}"
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def channel_gate_kb(channel: str) -> InlineKeyboardMarkup:
    """Shown to users who haven't joined the required channel yet."""
    # Build the join URL — works for @username and numeric IDs
    if channel.startswith("@"):
        join_url = f"https://t.me/{channel.lstrip('@')}"
    else:
        # Numeric channel ID — we can only link if it has an invite link; fall back gracefully
        join_url = f"https://t.me/joinchat"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=join_url)],
        [InlineKeyboardButton("✅ I've Joined – Verify", callback_data="verify_join")],
    ])


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ])


# ── Admin Keyboards ───────────────────────────────────────────────────────────

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Category Management", callback_data="adm_categories")],
        [InlineKeyboardButton("📦 Stock Management", callback_data="adm_stock")],
        [InlineKeyboardButton("💰 Pricing", callback_data="adm_pricing")],
        [InlineKeyboardButton("💳 Payment Settings", callback_data="adm_payment")],
        [InlineKeyboardButton("📊 Analytics & Reports", callback_data="adm_analytics")],
        [InlineKeyboardButton("📋 Pending Orders", callback_data="adm_pending")],
        [InlineKeyboardButton("👥 User Management", callback_data="adm_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔒 Channel Gate", callback_data="adm_channel")],
        [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="adm_maintenance")],
        [InlineKeyboardButton("💾 Backup Database", callback_data="adm_backup")],
    ])


def admin_categories_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Category", callback_data="adm_add_cat")],
        [InlineKeyboardButton("✏️ Edit Category", callback_data="adm_edit_cat")],
        [InlineKeyboardButton("🗑️ Delete Category", callback_data="adm_del_cat")],
        [InlineKeyboardButton("📋 List Categories", callback_data="adm_list_cats")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])


def admin_stock_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Add Stock (bulk)", callback_data="adm_add_stock")],
        [InlineKeyboardButton("📊 View Stock Levels", callback_data="adm_view_stock")],
        [InlineKeyboardButton("⚙️ Manual Adjust", callback_data="adm_manual_stock")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])


def admin_payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Upload QR Code", callback_data="adm_upload_qr")],
        [InlineKeyboardButton("🔗 Set UPI ID", callback_data="adm_set_upi")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])


def admin_analytics_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Total Sales", callback_data="adm_total_sales")],
        [InlineKeyboardButton("👤 Total Users", callback_data="adm_total_users")],
        [InlineKeyboardButton("📋 Transaction Log", callback_data="adm_txn_log")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Ban User", callback_data="adm_ban")],
        [InlineKeyboardButton("✅ Unban User", callback_data="adm_unban")],
        [InlineKeyboardButton("📊 User Stats", callback_data="adm_user_stats")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")],
    ])


def approve_reject_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}"),
        ]
    ])


def select_category_kb(categories: list[dict], prefix: str, back: str = "admin") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(cat["name"], callback_data=f"{prefix}{cat['id']}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=back)])
    return InlineKeyboardMarkup(buttons)


def back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")]
    ])


def confirm_delete_kb(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_del_cat_{cat_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="adm_categories"),
        ]
    ])
