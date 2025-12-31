# 🚀 Deployment Checklist & Step-by-Step Guide

## Pre-Deployment Checklist

- [ ] Code pushed to GitHub (or ready to deploy)
- [ ] All environment variables sourced (no hardcoded secrets in code)
- [ ] Database migration file ready (`db/migrations/2025-12-28_add_vip_and_usage_fields.sql`)
- [ ] README.md updated with live links
- [ ] Frontend build tested locally (`npm run build`)
- [ ] Backend tested locally (`uvicorn backend.main:app --reload`)

---

## Step 1: Set Up Production Database (Neon PostgreSQL)

**Why Neon?** — Free tier, managed PostgreSQL, instant backups, no setup required.

### Instructions

1. Go to **[neon.tech](https://neon.tech)**
2. **Sign up** with GitHub or email
3. Create a **new project** (default settings fine)
4. Copy your connection string (looks like):
   ```
   postgresql://user:password@host.neon.tech/dbname?sslmode=require
   ```
5. Save it; you'll paste this into your backend config next

### Run Initial Migration (One-time)

1. In Neon console, open **SQL Editor**
2. Copy and paste contents of `db/migrations/2025-12-28_add_vip_and_usage_fields.sql`
3. Click **Execute**
4. (Optional) Run `db/seed-data.sql` to create demo user

---

## Step 2: Deploy Backend (Render)

**Why Render?** — Free tier, auto-HTTPS, simple env var management, instant deploys.

### Instructions

1. Go to **[render.com](https://render.com)**
2. **Sign up** with GitHub
3. Click **New +** → **Web Service**
4. **Choose deployment method:**
   - If GitHub: Connect repo, select branch
   - If no GitHub: Paste your code manually
5. Fill in:
   - **Name**: `yourapp-backend` (e.g., `relevo-backend`)
   - **Environment**: `Docker`
   - **Build Command**: (leave default)
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
   - **Instance Type**: `Free` (sufficient for demo)

6. **Add Environment Variables** — Click **Advanced** and add:
   ```
   DATABASE_URL = postgresql://...@...neon.tech/...?sslmode=require
   SECRET_KEY = <generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
   ALLOWED_ORIGINS = https://yourapp.vercel.app
   GROQ_API_KEY = <your Groq API key, or leave blank>
   OLLAMA_URL = <optional>
   OLLAMA_MODEL = llama3
   REQUEST_COST_PER_1K_TOKENS = 0.002
   RATE_LIMIT_PER_MIN = 120
   VIP_PLAN_LIMIT = 10000
   ```

7. Click **Create Web Service**
8. **Wait 3-5 minutes** for deploy
9. Copy your backend URL (e.g., `https://relevo-backend.onrender.com`)

---

## Step 3: Deploy Frontend (Vercel)

**Why Vercel?** — Free tier, auto-HTTPS, optimized for React, 1-click deploy.

### Instructions

1. Go to **[vercel.com](https://vercel.com)**
2. **Sign up** with GitHub
3. Click **Add New…** → **Project**
4. **Import your GitHub repo** (or paste code)
5. **Configure:**
   - **Framework**: `Vite`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
6. **Add Environment Variables** (under **Environment Variables**):
   ```
   VITE_API_URL = https://yourapp-backend.onrender.com
   ```
7. Click **Deploy**
8. **Wait 1-2 minutes** for build
9. Copy your frontend URL (e.g., `https://yourapp.vercel.app`)

---

## Step 4: Enable CORS on Backend (Important!)

Now that you have both URLs, update backend CORS to allow only your frontend.

1. Go back to **Render** → **Your backend service**
2. Click **Environment**
3. Update `ALLOWED_ORIGINS`:
   ```
   https://yourapp.vercel.app
   ```
4. Click **Save**
5. Render auto-redeploys (wait 1 minute)

---

## Step 5: Test Your Live App

1. **Open frontend**: `https://yourapp.vercel.app`
2. **You should see**: Login page
3. **Click "Sign Up"** or use demo account:
   - Email: `demo@relevo.ai`
   - Password: `demo123` (if you ran seed-data.sql)
4. **Once logged in**: Try the chat interface
5. **API docs** (for technical investors): `https://yourapp-backend.onrender.com/docs`

---

## Step 6: Share with Investors

**Live Demo Link**: `https://yourapp.vercel.app`

**What to highlight:**
- ✅ **Live and running** — No "under construction"
- ✅ **Professional UI** — Modern, clean, responsive
- ✅ **Enterprise Auth** — Secure login, API keys
- ✅ **Auto-generated API docs** — Append `/docs` to backend URL
- ✅ **Usage tracking** — Built-in analytics hooks
- ✅ **Scalable architecture** — Containerized, cloud-ready

---

## Troubleshooting

### "Backend URL is not reachable"
- Check your Render service is running (green status light)
- Verify `ALLOWED_ORIGINS` on backend includes your Vercel URL
- Wait 2-3 minutes if you just updated env vars (Render takes time to redeploy)

### "Frontend can't load data"
- Open browser DevTools (F12) → **Console**
- Check for CORS errors
- Verify `VITE_API_URL` on Vercel matches your backend URL (with https)
- Test backend directly: `https://yourapp-backend.onrender.com/docs`

### "Login fails"
- Check `SECRET_KEY` is set on backend (not blank)
- Verify database is reachable from backend (test with Neon console)
- Ensure `db/seed-data.sql` was run if using demo user

### "Database connection error"
- Verify `DATABASE_URL` is correct (copy from Neon console)
- Check it has `?sslmode=require` (important for Neon)
- If on corporate network, may need VPN/firewall allowlist

---

## What Happens Behind the Scenes (For Curious Minds)

1. **You visit frontend** → Browser loads React app from Vercel (static HTML/JS)
2. **You login** → Frontend sends email/password to backend API
3. **Backend checks database** → Verifies user in PostgreSQL (via Neon)
4. **Backend sends back JWT token** → Frontend saves in localStorage
5. **You submit a prompt** → Frontend sends to backend with token
6. **Backend calls LLM** → Uses Groq or Ollama to optimize
7. **Backend returns optimized prompt** → Frontend displays result
8. **Usage is tracked** → Database updated with request count & cost

---

## Cost Estimate (Monthly, at free tiers)

| Service | Free Tier | Cost |
|---------|-----------|------|
| Neon (PostgreSQL) | 0.5 GB + 50 GB bandwidth | $0 |
| Render (Backend) | 750 hours/month | $0 |
| Vercel (Frontend) | Unlimited | $0 |
| **Total** | | **$0** (unless you go past free limits) |

---

## Next Steps After Launch

1. **Monitor logs** — Both Render and Vercel have log dashboards; check for errors
2. **Collect investor feedback** — Ask what they liked/disliked
3. **Plan scaling** — Move to paid tiers when you have users (simple slider, no code change)
4. **Add features** — Usage analytics dashboard, custom billing, team management
5. **Security hardening** — Add SSL pinning, rate limiting tuning, audit logging

---

**You're done! 🎉 Share your live link with investors and impress them.** 🚀
