# 🚂 Railway Deployment Guide

Complete step-by-step guide to deploy your Telegram Coupon Bot on Railway.

---

## Prerequisites

- GitHub account
- Railway account ([railway.app](https://railway.app))
- Your bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot))

---

## Step 1 — Push Code to GitHub

```bash
# Initialize git repo
cd telegram-coupon-bot
git init
git add .
git commit -m "Initial commit — Telegram Coupon Bot"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/telegram-coupon-bot.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Click **Deploy from GitHub repo**
3. Authorize Railway to access your GitHub
4. Select your `telegram-coupon-bot` repository
5. Railway will detect it's a Python project automatically

---

## Step 3 — Set Environment Variables

In your Railway project dashboard:

1. Click on your service → **Variables** tab
2. Add the following:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | `your_bot_token_from_botfather` |
| `ADMIN_IDS` | `123456789` (your Telegram user ID) |
| `UPI_ID` | `yourname@upi` |
| `WEBHOOK_URL` | _(fill after Step 4)_ |
| `BOT_NAME` | `CouponBot` |
| `CURRENCY_SYMBOL` | `₹` |
| `LOG_LEVEL` | `INFO` |

> ⚠️ `PORT` is automatically set by Railway — do NOT set it manually.

---

## Step 4 — Get Your Railway Domain

1. In Railway dashboard → **Settings** tab
2. Under **Networking** → click **Generate Domain**
3. You'll get a URL like: `https://my-app.up.railway.app`
4. Copy this URL → go back to **Variables**
5. Set `WEBHOOK_URL` = `https://my-app.up.railway.app`

---

## Step 5 — Deploy

Railway auto-deploys when you push to GitHub.

To trigger manual deploy:
1. Railway dashboard → **Deployments** tab
2. Click **Deploy** (or push a new commit)

---

## Step 6 — Verify Deployment

1. Open Railway logs → **View Logs**
2. You should see:
   ```
   ✅ Bot initialized and ready.
   Starting in WEBHOOK mode on port XXXX
   ```
3. Open Telegram → find your bot → send `/start`
4. Bot should respond immediately ✅

---

## 📦 File Roles for Railway

| File | Purpose |
|---|---|
| `Procfile` | Tells Railway: `python main.py` |
| `runtime.txt` | Pins Python 3.11 |
| `requirements.txt` | Installs dependencies |
| `railway.json` | Build + restart policy config |
| `main.py` | Auto-detects Railway → uses webhook mode |

---

## 🔄 How Webhook Mode Works

When `WEBHOOK_URL` is set:
- Bot registers a webhook at `https://your-domain.up.railway.app/webhook/{BOT_TOKEN}`
- Telegram pushes updates directly to your Railway app
- No polling loop needed — zero wasted resources ✅

When `WEBHOOK_URL` is empty (local dev):
- Bot uses long polling
- Works without any domain or HTTPS

---

## 💾 Data Persistence on Railway

> ⚠️ Railway's ephemeral filesystem resets on redeploy.

**For production with persistent data, add a Railway Volume:**

1. Railway dashboard → your service → **Volumes** tab
2. Click **Add Volume** → Mount Path: `/app/data`
3. Railway will preserve `data/` across deploys

Alternatively, migrate to **Railway's PostgreSQL plugin** or use **MongoDB Atlas** (free tier).

---

## 🔁 Auto-Deploy on Push

Railway automatically redeploys every time you `git push`:

```bash
# Make changes, then:
git add .
git commit -m "Updated pricing"
git push
# → Railway auto-deploys within ~60 seconds ✅
```

---

## 🐛 Common Issues

| Issue | Fix |
|---|---|
| Webhook not working | Make sure `WEBHOOK_URL` has no trailing slash |
| Bot not starting | Check logs for missing env vars |
| `PORT` error | Don't set PORT manually — Railway sets it |
| Data wiped on redeploy | Add a Railway Volume (see above) |
| Bot responds twice | Make sure `drop_pending_updates=True` in polling (already set) |

---

## 📊 Monitoring

- **Logs**: Railway dashboard → Logs tab (real-time)
- **Metrics**: Railway dashboard → Metrics tab (CPU/Memory)
- **Bot logs**: Also saved to `logs/bot.log` in container

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Railway project created from GitHub repo
- [ ] `BOT_TOKEN` set in Railway variables
- [ ] `ADMIN_IDS` set (your Telegram user ID)
- [ ] `UPI_ID` set
- [ ] Railway domain generated
- [ ] `WEBHOOK_URL` set to Railway domain
- [ ] Deployment successful (green in Railway)
- [ ] `/start` works in Telegram
- [ ] `/admin` shows admin panel
