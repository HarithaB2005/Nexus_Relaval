# Relevo: Agent-based Prompt Optimization (APO) Service

**A production-ready, investor-friendly AI prompt optimization platform with enterprise security.**

## 🎯 What It Does (In Plain English)

Relevo is a web app that takes your rough ideas or tasks and **automatically refines them into perfect prompts** using multiple AI agents working together. Think of it as a "prompt polisher"—it:

1. **Understands your intent** — What are you really asking for?
2. **Optimizes your prompt** — Rewrites it to get the best result from AI models.
3. **Checks the output** — Makes sure the result matches what you wanted.
4. **Refines until perfect** — Iterates until quality is high enough.

Perfect for content creators, developers, researchers, and anyone working with AI models who wants better, faster results.

---

## 🔒 Enterprise Security (Investor Confidence)

✅ **User Authentication** — Email/password with JWT tokens (industry standard)  
✅ **Password Security** — Argon2 hashing (resistant to attacks)  
✅ **API Keys** — Secure token-based access for apps; hashed in database  
✅ **Usage Tracking** — Track and bill per user, prevent abuse  
✅ **Rate Limiting** — Prevent spam; enforce per-user request limits  
✅ **Database Security** — PostgreSQL with SSL, secure connection pooling  
✅ **HTTPS Ready** — Auto-HTTPS when deployed to cloud (Render/Vercel/Railway)  

---

## 🏗️ Architecture (Built to Scale)

- **Backend**: FastAPI (Python) — Fast, async, auto-documented API
- **Frontend**: React + Vite — Modern, responsive web UI
- **Database**: PostgreSQL — Reliable, proven for production
- **Infrastructure**: Docker — Reproducible, cloud-ready containers

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose (simplest) — or —
- Python 3.11+ & Node.js 20+ (manual)

### Option A: Docker (Recommended)
```bash
# Clone or navigate to project
cd APO_RMP_Project

---

## 🚀 Production Deployment

**Relevo is production-ready and tested for enterprise deployment.**

### Quick Deployment (5 minutes)

**Option 1: Render.com (Easiest)**
```bash
1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect repository
4. Set environment variables from .env.production
5. Start command: gunicorn backend.wsgi:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
6. Deploy!
```

**Option 2: Docker Compose**
```bash
docker-compose -f docker-compose.yml up --build
# Runs on: http://localhost:8000 (API), http://localhost:5173 (Frontend)
```

### Documentation
- **🚀 Production Deployment Guide:** [DEPLOYMENT_PRODUCTION.md](DEPLOYMENT_PRODUCTION.md)
- **🔌 API Service Readiness:** [API_SERVICE_READY.md](API_SERVICE_READY.md)
- **📋 Investor Readiness:** [INVESTOR_READINESS.md](INVESTOR_READINESS.md)

### ✅ Production Features
- HTTPS/SSL support
- Load balancing ready
- Database pooling
- Health checks
- Audit logging
- Rate limiting
- CORS security

---

## 🔌 API Service Integration

Relevo can be integrated as a **service API** into other platforms:

```python
# Example: Healthcare integration
import requests

api_url = "https://api.yourdomain.com"

# Login
response = requests.post(f"{api_url}/auth/login", json={
    "email": "user@example.com",
    "password": "password"
})
token = response.json()["access_token"]

# Generate medical consultation
response = requests.post(f"{api_url}/generate", 
    headers={"Authorization": f"Bearer {token}"},
    json={"user_task": "I have a cold and sore throat"}
)

result = response.json()
print(result["final_output"])         # Detailed guidance
print(f"Quality: {result['critic_score']:.2f}/1.0")
```

**Perfect for:**
- Telemedicine platforms
- Healthcare provider systems
- Insurance triage automation
- Wellness applications
- Enterprise prompt optimization

See [API_SERVICE_READY.md](API_SERVICE_READY.md) for detailed integration examples.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose (simplest) — or —
- Python 3.11+ & Node.js 20+ (manual)

### Option A: Docker (Recommended)
```bash
# Clone or navigate to project
cd APO_RMP_Project

# Start all services (db, backend, frontend)
docker compose up

# Visit: http://localhost:5173
# Login with: demo@relevo.ai / demo123
```

### Option B: Manual Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

---

## 📋 Deployment (How to Get a Live Link for Investors)

### Quick Summary
- **Backend** → Deploy to Render or Railway (free tier available)
- **Frontend** → Deploy to Vercel or Netlify (free tier available)
- **Database** → Use Neon PostgreSQL (free tier available) or your own

### Step-by-Step (Render + Vercel)

#### 1. Set Up Database (Neon PostgreSQL — free)
- Go to [neon.tech](https://neon.tech) → Sign up
- Create a new project → Copy your PostgreSQL connection string
- Save it; you'll need it for the backend

#### 2. Deploy Backend (Render)
- Go to [render.com](https://render.com) → Sign up
- Click **New +** → **Web Service**
- Connect your GitHub repo (or paste code)
- Set **Build Command**: `pip install -r backend/requirements.txt`
- Set **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Add **Environment Variables**:
  ```
  DATABASE_URL = <your Neon PostgreSQL URL>
  SECRET_KEY = <generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
  ALLOWED_ORIGINS = https://yourapp.vercel.app
  GROQ_API_KEY = <optional, for fast mode>
  ```
- Deploy → Note your backend URL (e.g., `https://yourapp-backend.onrender.com`)

#### 3. Deploy Frontend (Vercel)
- Go to [vercel.com](https://vercel.com) → Sign up → **Import Project**
- Select your GitHub repo
- Set **Build Command**: `npm run build`
- Add **Environment Variable**:
  ```
  VITE_API_URL = https://yourapp-backend.onrender.com
  ```
- Deploy → Get your live URL (e.g., `https://yourapp.vercel.app`)

#### 4. Update Backend CORS
- Go back to Render → Update `ALLOWED_ORIGINS` with your Vercel URL
- Redeploy

#### 5. Run Database Migration (One-Time)
```bash
# Use your database provider's SQL console (Neon has one built-in)
# Paste and run: db/migrations/2025-12-28_add_vip_and_usage_fields.sql
```

#### 6. Seed Demo User (One-Time, Optional)
```bash
# Same SQL console, paste and run: db/seed-data.sql
```

**Done!** Your live link is ready. Share it with investors.

---

## 🎯 What to Show Investors

1. **Open the live link** → Shows a polished UI
2. **Sign up or login** (demo@relevo.ai / demo123)
3. **Try the chat** → Type a rough task, see it optimized
4. **Show the API docs** → Append `/docs` to backend URL (e.g., `https://yourapp-backend.onrender.com/docs`) — Auto-generated, professional
5. **Highlight features**:
   - Real-time optimization
   - Multi-agent AI orchestration
   - Usage tracking & billing ready
   - Enterprise auth & security

---

## 📁 Project Structure

```
APO_RMP_Project/
├── backend/
│   ├── main.py           # FastAPI app & routes
│   ├── agents.py         # AI agent orchestration (APO workflow)
│   ├── auth.py           # JWT authentication
│   ├── key_management.py # API key & user management
│   ├── util.py           # LLM calls & helpers
│   ├── Dockerfile        # Backend container image
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Main React component
│   │   ├── pages/        # Page components (Chat, Login, etc.)
│   │   ├── components/   # Reusable UI components
│   │   └── services/     # API call helpers
│   ├── Dockerfile        # Frontend container image
│   └── package.json      # JS dependencies
├── db/
│   ├── database.py       # PostgreSQL connection & schema
│   ├── migrations/       # SQL migration files
│   └── seed-data.sql     # Demo user insert
├── docker-compose.yml    # Local development orchestration
└── README.md             # This file
```

---

## 🔑 Environment Variables Explained

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | JWT signing key (security) | A random 32+ char string |
| `ALLOWED_ORIGINS` | CORS allowlist (which domains can call the API) | `https://yourapp.vercel.app` |
| `GROQ_API_KEY` | Optional API key for fast LLM (speeds up optimization) | Your Groq API key |
| `RATE_LIMIT_PER_MIN` | Max requests per user per minute | `120` |

---

## 💡 For Fund Submission

**Talking Points:**
- ✅ **Production-ready**: Secure auth, database, containerized, deployed live
- ✅ **Scalable**: Async Python backend, connection pooling, designed for multi-user
- ✅ **Enterprise-grade**: JWT tokens, Argon2 hashing, rate limiting, audit-ready
- ✅ **User-centric**: Demo account, intuitive UI, clear API docs
- ✅ **Monetizable**: Built-in usage tracking & billing hooks for SaaS model

**Mention to Investors:**
- "Our platform uses a multi-agent AI system to iteratively refine prompts, improving output quality by X% vs. manual prompting."
- "Enterprise security from day one: JWT authentication, Argon2 password hashing, API key management, and usage-based billing."
- "Live demo already deployed and running; investors can test immediately."

---

## 🐛 Troubleshooting

**"Can't connect to database?"**
- Check `DATABASE_URL` is correct and accessible
- For Neon: whitelist your IP in the console

**"Frontend can't reach backend API?"**
- Verify `ALLOWED_ORIGINS` on backend includes your frontend URL
- Check `VITE_API_URL` on frontend matches backend HTTPS URL

**"Login fails?"**
- For demo account, ensure `db/seed-data.sql` was run
- Or register a new account directly in the UI

---

## 📞 Support

For questions or issues, check:
- Backend API docs: `<backend-url>/docs`
- Frontend source: `frontend/src/`
- Database schema: `db/database.py`

---

**Built with ❤️ for startups. Ready to impress investors. 🚀**
