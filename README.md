# 🎫 Telegram Coupon & Account Selling Bot

A fully automated, professional-grade Telegram bot for selling **coupons, gift cards, promo codes, and premium accounts** — with admin control panel, auto stock management, payment verification, and Railway deployment support.

---

## ✨ Features at a Glance

### 👤 User Features
- `/start` → Dynamic category listing with inline buttons
- Quantity picker (1 / 2 / 5 / 10 / Custom)
- Auto price calculation
- Dynamic QR code + UPI payment display
- Payment screenshot upload
- Instant delivery on approval
- Order history with status tracking

### 🛠️ Admin Features
| Feature | Command/Button |
|---|---|
| Admin Panel | `/admin` |
| Add / Edit / Delete Categories | Admin Panel → Category Management |
| Add Bulk Stock | Admin Panel → Stock Management |
| Set / Change Pricing | Admin Panel → Pricing |
| Upload QR Code | Admin Panel → Payment Settings |
| Change UPI ID | Admin Panel → Payment Settings |
| View Pending Orders | Admin Panel → Pending Orders |
| Approve / Reject Payments | Approve/Reject buttons on notification |
| Broadcast Message | Admin Panel → Broadcast |
| View Sales Report | Admin Panel → Analytics |
| View Transaction Logs | Admin Panel → Analytics |
| Ban / Unban Users | Admin Panel → User Management |
| Maintenance Mode Toggle | Admin Panel → Maintenance Mode |
| Database Backup | Admin Panel → Backup |
| Manual Stock Adjust | Admin Panel → Stock Management |

---

## 📁 Project Structure

```
telegram-coupon-bot/
├── main.py                  # Entry point (polling + webhook)
├── config.py                # All settings from env vars
├── database.py              # Async SQLite (aiosqlite) ORM
├── keyboards.py             # All InlineKeyboardMarkup builders
├── messages.py              # Message templates
├── states.py                # ConversationHandler states
├── handlers/
│   ├── __init__.py
│   ├── user.py              # Start, browse, help, my orders
│   ├── payment.py           # Quantity → QR → Paid → Admin notify
│   └── admin.py             # Full admin control panel
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Order ID generator, formatters
├── data/                    # SQLite DB + QR code (auto-created)
├── logs/                    # Log files (auto-created)
├── requirements.txt
├── Procfile
├── runtime.txt
├── railway.json
├── .env.example
└── .gitignore
```

---

## 🚀 Quick Start (Local)

### 1. Clone & setup

```bash
git clone https://github.com/YOUR_USERNAME/telegram-coupon-bot.git
cd telegram-coupon-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env   # Fill in BOT_TOKEN and ADMIN_IDS
```

### 3. Run locally

```bash
python main.py
```

---

## 🚂 Railway Deployment

See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) for the full step-by-step guide.

**Quick summary:**
1. Push code to GitHub
2. Create new Railway project → Deploy from GitHub repo
3. Add environment variables (see `.env.example`)
4. Railway auto-deploys on every push ✅

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | ✅ | Comma-separated Telegram user IDs |
| `UPI_ID` | ✅ | Your UPI payment ID |
| `WEBHOOK_URL` | Railway | Your Railway public domain URL |
| `PORT` | Railway | Auto-set by Railway (default 8443) |
| `DATABASE_URL` | ❌ | SQLite path (default: `data/bot.db`) |
| `BOT_NAME` | ❌ | Display name (default: CouponBot) |
| `CURRENCY_SYMBOL` | ❌ | Currency symbol (default: ₹) |
| `MAINTENANCE_MODE` | ❌ | `true`/`false` (default: false) |
| `LOG_LEVEL` | ❌ | `DEBUG`/`INFO`/`WARNING` (default: INFO) |

---

## 📦 Workflow Diagram

```
User /start
    └→ Browse Categories
         └→ Select Category
              └→ Select Quantity (1/2/5/10/Custom)
                   └→ View Invoice + QR + UPI
                        ├→ Upload Screenshot (optional)
                        └→ Click "I Have Paid"
                             └→ Admin receives notification
                                  ├→ ✅ APPROVE → Stock deducted → Items delivered to user
                                  └→ ❌ REJECT  → User notified with reason
```

---

## 🔒 Security

- Admin-only handlers are protected by `ADMIN_IDS` check on every call
- User IDs are validated on all order operations
- No sensitive data is stored in logs
- `.env` is excluded from Git via `.gitignore`

---

## 📊 Database Schema

| Table | Description |
|---|---|
| `users` | All bot users with ban status |
| `categories` | Product categories with price |
| `stock` | Individual items (codes/accounts) per category |
| `orders` | Purchase orders with status tracking |
| `order_items` | Links orders to specific stock items |
| `transactions` | Full audit log |
| `settings` | Key-value settings (UPI, QR path, etc.) |

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| Bot not responding | Check `BOT_TOKEN` in env |
| Admin panel not showing | Verify your ID is in `ADMIN_IDS` |
| QR code not showing | Upload via Admin → Payment Settings |
| Payment not going through | Check `UPI_ID` setting |
| Railway deploy fails | Check `requirements.txt` versions |

---

## 📄 License

MIT License — free to use, modify, and deploy.
