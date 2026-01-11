# Production Deployment Checklist

**Before deploying to production, verify all these items.**

## 1. Environment Variables (REQUIRED)

Create a `.env` file in the project root with:

```bash
# Database (MUST CHANGE from defaults)
DATABASE_URL=postgresql://user:password@your-db-host:5432/nexusai
POSTGRES_DB=nexusai
POSTGRES_USER=nexusai
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE

# Security (GENERATE NEW KEY)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# API Keys (Choose at least one LLM provider)
GROQ_API_KEY=your-groq-key-here
GEMINI_API_KEY=your-gemini-key-here

# CORS (Set to your production domain)
ALLOWED_ORIGINS=https://yourdomain.com

# Optional
RATE_LIMIT_PER_MIN=120
REQUEST_COST_PER_1K_TOKENS=0.002
VIP_PLAN_LIMIT=10000
```

## 2. Database Setup

```bash
# Run migrations AFTER database is accessible
docker exec nexus-backend python -m alembic upgrade head
# OR manually execute:
psql -U $POSTGRES_USER -d $POSTGRES_DB < backend/db/migrations/2025-12-28_add_vip_and_usage_fields.sql
psql -U $POSTGRES_USER -d $POSTGRES_DB < backend/db/migrations/2025-12-29_add_billing_and_usage_tracking.sql
psql -U $POSTGRES_USER -d $POSTGRES_DB < backend/db/migrations/2026-01-09_add_audit_and_privacy.sql
```

## 3. Secrets Verification

- [ ] `.env` file is in `.gitignore` (it is — verified)
- [ ] No hardcoded API keys in code (checked — only example uses env vars)
- [ ] SECRET_KEY is 32+ characters
- [ ] Database password is strong (16+ chars, mixed case, numbers, symbols)
- [ ] ALLOWED_ORIGINS points to your domain (not `*` or localhost)

## 4. Docker Deployment

```bash
# Build images
docker-compose build

# Run with production .env
docker-compose --env-file .env up -d

# Verify services are healthy
docker-compose ps
docker logs nexus-backend
docker logs nexus-frontend
```

## 5. Health Checks

```bash
# Check backend
curl http://localhost:8000/docs

# Check frontend
curl http://localhost:5173

# Check database connection
docker exec nexus-db pg_isready -U $POSTGRES_USER
```

## 6. Database Backups

- [ ] Configure automatic PostgreSQL backups
- [ ] Test backup/restore process
- [ ] Document recovery procedure
- [ ] Set backup retention (7-30 days recommended)

## 7. HTTPS/TLS Setup

- [ ] Configure reverse proxy (Nginx, AWS ALB, etc.)
- [ ] Install SSL certificate (Let's Encrypt recommended)
- [ ] Set `ALLOWED_ORIGINS` to HTTPS domain
- [ ] Redirect HTTP → HTTPS

## 8. Monitoring & Logging

- [ ] Set up log aggregation (CloudWatch, DataDog, etc.)
- [ ] Configure uptime monitoring
- [ ] Set up alerts for:
  - Backend HTTP 5xx errors
  - Database connection failures
  - API response time > 2s
  - High rate limit hits

## 9. Rate Limiting & Usage Tracking

- [ ] Test rate limiting: `for i in {1..130}; do curl http://localhost:8000/generate; done`
  - Expected: first 120 succeed, rest get 429
- [ ] Verify usage is logged to database
- [ ] Test billing calculations

## 10. Security Audit (Before Public Launch)

```bash
# Check for hardcoded secrets
git log -p --all -S "sk_" --exclude-dir=node_modules

# Check dependencies for CVEs
pip-audit -r backend/requirements.txt

# Verify .gitignore covers all secrets
grep "\.env\|auth.json\|\.key\|\.pem" .gitignore
```

## 11. Load Testing

```bash
# Test with concurrent requests
ab -n 1000 -c 50 http://localhost:8000/metrics
```

## 12. Rollback Plan

- [ ] Document rollback procedure
- [ ] Keep previous database backup accessible
- [ ] Have previous docker image tag available
- [ ] Test rollback process in staging first

## ✅ Final Checks

- [ ] All environment variables set
- [ ] Database migrations applied successfully
- [ ] No error logs on startup
- [ ] Users can register → login → call `/generate`
- [ ] API keys work for external clients
- [ ] Audit logs are being recorded
- [ ] Billing/usage is tracking correctly

---

## 13. Three Killer Features Deployment (NEW - January 12, 2026)

### 13.1 Registry of Truth (Governance Dashboard)

```bash
# Apply new migration
psql -U $POSTGRES_USER -d $POSTGRES_DB < backend/db/migrations/2026-01-12_governance_and_privacy.sql

# Verify tables
psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'governance_%';"
```

**Checklist:**
- [ ] governance_audit_events table created
- [ ] governance_saved_errors table created
- [ ] governance_summary table created
- [ ] GET /api/v1/audit/events endpoint works
- [ ] GET /api/v1/audit/summary endpoint works
- [ ] GET /api/v1/audit/saved-errors endpoint works

### 13.2 Privacy-by-Design (Data Sovereignty)

```bash
# Migration includes these tables:
# - data_retention_policies
# - local_inference_deployments
# - request_processing_log
# And columns: data_retention_mode, privacy_settings, local_inference_* fields
```

**Checklist:**
- [ ] client_credentials has privacy columns
- [ ] GET /api/v1/privacy/settings endpoint works
- [ ] POST /api/v1/privacy/settings endpoint works
- [ ] Can enable ZDR mode
- [ ] Can enable Local Inference mode

### 13.3 5-Minute SDK

```bash
# Publish to PyPI
cd nexus-releval-sdk
python setup.py sdist bdist_wheel
twine upload dist/*

# Test installation
pip install nexus-releval
python -c "import nexus_releval; client = nexus_releval.Client(api_key='test'); print('✓ SDK works')"
```

**Checklist:**
- [ ] SDK installs via pip
- [ ] Client imports successfully
- [ ] verify() method works
- [ ] get_audit_log() method works
- [ ] enable_zero_data_retention() method works

### 13.4 Documentation

- [ ] QUICK_START.md published to docs
- [ ] FEATURES.md published to docs
- [ ] THREE_FEATURES_QUICK_REFERENCE.md published to docs
- [ ] API docs updated with new endpoints
- [ ] Sales team has closing statements

---

## 14. Final Integration Tests

```bash
# Test 1: Create request and verify governance logging
curl -X POST http://localhost:8000/api/v1/generate-prompt \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'

# Test 2: Check governance dashboard
curl http://localhost:8000/api/v1/audit/summary \
  -H "Authorization: Bearer TOKEN"

# Test 3: Toggle privacy settings
curl -X POST http://localhost:8000/api/v1/privacy/settings \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data_retention_mode": "zero-retention"}'

# Test 4: SDK quick start
python -c "
import nexus_releval
client = nexus_releval.Client(api_key='YOUR_KEY')
result = client.verify('Test prompt')
print('✓ SDK integration works')
"
```

**Checklist:**
- [ ] Governance logging captured
- [ ] Audit summary returns data
- [ ] Privacy settings can be toggled
- [ ] SDK integration works end-to-end

---

**Status:** Ready for production ✅

Once all checks pass, you're safe to deploy!

**New in this deployment:**
✅ Registry of Truth (Governance Dashboard)
✅ Privacy-by-Design (Data Sovereignty)
✅ 5-Minute Quickstart SDK

**References:**
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)
- [FEATURES.md](FEATURES.md)
- [THREE_FEATURES_QUICK_REFERENCE.md](THREE_FEATURES_QUICK_REFERENCE.md)

