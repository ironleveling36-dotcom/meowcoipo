"""
database.py - SQLite async-compatible wrapper using aiosqlite
All DB interactions go through this module.
"""

import aiosqlite
import logging
import os
import shutil
from datetime import datetime
from typing import Optional

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    joined_at   TEXT    DEFAULT (datetime('now')),
    is_banned   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    UNIQUE NOT NULL,
    price       REAL    NOT NULL DEFAULT 0,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    item        TEXT    NOT NULL,
    is_sold     INTEGER DEFAULT 0,
    sold_at     TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id    TEXT    PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    status      TEXT    DEFAULT 'pending',
    screenshot  TEXT,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now')),
    reject_reason TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT    REFERENCES orders(order_id) ON DELETE CASCADE,
    stock_id    INTEGER REFERENCES stock(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT    PRIMARY KEY,
    value       TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT,
    user_id     INTEGER,
    action      TEXT,
    actor       TEXT,
    ts          TEXT    DEFAULT (datetime('now'))
);
"""

_DEFAULT_SETTINGS = {
    "maintenance":       "false",
    "upi_id":            "yourname@upi",
    "qr_path":           "data/qr_code.jpg",
    "bot_name":          "CouponBot",
    "required_channel":  "",          # e.g. "@mychannel" or "-100123456789"
}


class Database:
    _instance: Optional["Database"] = None

    def __init__(self, db_path: str = DATABASE_URL):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    # ── Singleton ──────────────────────────────────────────────────────────
    @classmethod
    async def get_instance(cls) -> "Database":
        if cls._instance is None or cls._instance._conn is None:
            cls._instance = cls()
            await cls._instance._init()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None

    async def _init(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        await self._seed_settings()
        logger.info("Database initialised at %s", self.db_path)

    async def _seed_settings(self):
        for k, v in _DEFAULT_SETTINGS.items():
            await self._conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v)
            )
        await self._conn.commit()

    # ── Low-level helpers ──────────────────────────────────────────────────
    async def fetchone(self, sql: str, params=()):
        async with self._conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def fetchall(self, sql: str, params=()):
        async with self._conn.execute(sql, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def execute(self, sql: str, params=()):
        await self._conn.execute(sql, params)
        await self._conn.commit()

    async def executemany(self, sql: str, params_list):
        await self._conn.executemany(sql, params_list)
        await self._conn.commit()

    # ── Settings ───────────────────────────────────────────────────────────
    async def get_setting(self, key: str) -> Optional[str]:
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        return row["value"] if row else None

    async def set_setting(self, key: str, value: str):
        await self.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    # ── Users ──────────────────────────────────────────────────────────────
    async def upsert_user(self, user_id: int, username: str, full_name: str):
        await self.execute(
            "INSERT INTO users(user_id, username, full_name) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "username=excluded.username, full_name=excluded.full_name",
            (user_id, username or "", full_name or ""),
        )

    async def get_user(self, user_id: int):
        return await self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def get_all_users(self):
        return await self.fetchall("SELECT * FROM users WHERE is_banned=0")

    async def count_users(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) as c FROM users")
        return row["c"] if row else 0

    async def ban_user(self, user_id: int):
        await self.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))

    async def unban_user(self, user_id: int):
        await self.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))

    async def is_banned(self, user_id: int) -> bool:
        row = await self.fetchone("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
        return bool(row["is_banned"]) if row else False

    # ── Categories ─────────────────────────────────────────────────────────
    async def add_category(self, name: str, price: float) -> int:
        await self._conn.execute(
            "INSERT INTO categories(name, price) VALUES(?,?)", (name, price)
        )
        await self._conn.commit()
        row = await self.fetchone("SELECT id FROM categories WHERE name=?", (name,))
        return row["id"]

    async def get_categories(self, active_only: bool = True):
        if active_only:
            return await self.fetchall(
                "SELECT * FROM categories WHERE is_active=1 ORDER BY name"
            )
        return await self.fetchall("SELECT * FROM categories ORDER BY name")

    async def get_category(self, cat_id: int):
        return await self.fetchone("SELECT * FROM categories WHERE id=?", (cat_id,))

    async def update_category(self, cat_id: int, name: str = None, price: float = None):
        if name is not None:
            await self.execute(
                "UPDATE categories SET name=? WHERE id=?", (name, cat_id)
            )
        if price is not None:
            await self.execute(
                "UPDATE categories SET price=? WHERE id=?", (price, cat_id)
            )

    async def delete_category(self, cat_id: int):
        await self.execute(
            "UPDATE categories SET is_active=0 WHERE id=?", (cat_id,)
        )

    async def stock_count(self, cat_id: int) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) as c FROM stock WHERE category_id=? AND is_sold=0",
            (cat_id,),
        )
        return row["c"] if row else 0

    # ── Stock ──────────────────────────────────────────────────────────────
    async def add_stock_items(self, cat_id: int, items: list):
        clean = [item.strip() for item in items if item.strip()]
        if not clean:
            return
        await self.executemany(
            "INSERT INTO stock(category_id, item) VALUES(?,?)",
            [(cat_id, item) for item in clean],
        )

    async def reserve_stock(self, cat_id: int, quantity: int) -> list:
        """Fetch `quantity` unsold items. Does NOT mark them sold yet."""
        return await self.fetchall(
            "SELECT * FROM stock WHERE category_id=? AND is_sold=0 LIMIT ?",
            (cat_id, quantity),
        )

    async def mark_sold(self, stock_ids: list):
        if not stock_ids:
            return
        now = datetime.utcnow().isoformat()
        await self.executemany(
            "UPDATE stock SET is_sold=1, sold_at=? WHERE id=?",
            [(now, sid) for sid in stock_ids],
        )

    async def manual_adjust_stock(self, cat_id: int, delta: int):
        """Positive delta = add placeholder items; negative = remove unsold items."""
        if delta > 0:
            await self.executemany(
                "INSERT INTO stock(category_id, item) VALUES(?,?)",
                [(cat_id, f"MANUAL-ITEM-{i+1}") for i in range(delta)],
            )
        elif delta < 0:
            rows = await self.fetchall(
                "SELECT id FROM stock WHERE category_id=? AND is_sold=0 LIMIT ?",
                (cat_id, abs(delta)),
            )
            for row in rows:
                await self.execute("DELETE FROM stock WHERE id=?", (row["id"],))

    # ── Orders ─────────────────────────────────────────────────────────────
    async def create_order(
        self,
        order_id: str,
        user_id: int,
        cat_id: int,
        quantity: int,
        amount: float,
    ):
        await self.execute(
            "INSERT INTO orders(order_id, user_id, category_id, quantity, amount) "
            "VALUES(?,?,?,?,?)",
            (order_id, user_id, cat_id, quantity, amount),
        )

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        reject_reason: str = None,
        screenshot: str = None,
    ):
        now = datetime.utcnow().isoformat()
        await self.execute(
            "UPDATE orders SET status=?, reject_reason=?, updated_at=? WHERE order_id=?",
            (status, reject_reason, now, order_id),
        )
        if screenshot:
            await self.execute(
                "UPDATE orders SET screenshot=? WHERE order_id=?",
                (screenshot, order_id),
            )

    async def get_order(self, order_id: str):
        return await self.fetchone(
            "SELECT * FROM orders WHERE order_id=?", (order_id,)
        )

    async def get_pending_orders(self):
        return await self.fetchall(
            """SELECT o.*, u.username, u.full_name, c.name as category_name
               FROM orders o
               JOIN users u ON u.user_id = o.user_id
               JOIN categories c ON c.id = o.category_id
               WHERE o.status = 'pending'
               ORDER BY o.created_at"""
        )

    async def add_order_items(self, order_id: str, stock_ids: list):
        if not stock_ids:
            return
        await self.executemany(
            "INSERT INTO order_items(order_id, stock_id) VALUES(?,?)",
            [(order_id, sid) for sid in stock_ids],
        )

    async def get_order_items(self, order_id: str) -> list:
        rows = await self.fetchall(
            """SELECT s.item FROM order_items oi
               JOIN stock s ON s.id = oi.stock_id
               WHERE oi.order_id = ?""",
            (order_id,),
        )
        return [r["item"] for r in rows]

    # ── Transactions ───────────────────────────────────────────────────────
    async def log_transaction(
        self, order_id: str, user_id: int, action: str, actor: str
    ):
        await self.execute(
            "INSERT INTO transactions(order_id, user_id, action, actor) "
            "VALUES(?,?,?,?)",
            (order_id, user_id, action, actor),
        )

    async def get_transactions(self, limit: int = 50) -> list:
        return await self.fetchall(
            "SELECT * FROM transactions ORDER BY ts DESC LIMIT ?", (limit,)
        )

    # ── Analytics ──────────────────────────────────────────────────────────
    async def total_sales(self) -> float:
        row = await self.fetchone(
            "SELECT COALESCE(SUM(amount), 0) as s FROM orders WHERE status='approved'"
        )
        return row["s"] if row else 0.0

    async def total_orders(self) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) as c FROM orders WHERE status='approved'"
        )
        return row["c"] if row else 0

    async def stock_summary(self) -> list:
        return await self.fetchall(
            """SELECT
                   c.name,
                   c.price,
                   COUNT(CASE WHEN s.is_sold = 0 THEN 1 END) AS available,
                   COUNT(CASE WHEN s.is_sold = 1 THEN 1 END) AS sold
               FROM categories c
               LEFT JOIN stock s ON s.category_id = c.id
               WHERE c.is_active = 1
               GROUP BY c.id
               ORDER BY c.name"""
        )

    # ── Backup ─────────────────────────────────────────────────────────────
    async def backup(self) -> str:
        """Copy the live DB to a timestamped file and return its path."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/backup_{ts}.db"
        os.makedirs("data", exist_ok=True)
        shutil.copy2(self.db_path, backup_path)
        logger.info("Database backed up to %s", backup_path)
        return backup_path

    # ── Lifecycle ──────────────────────────────────────────────────────────
    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
        Database._instance = None
