-- Seed Data for Demo/Investor Review
-- Run this ONCE after database initialization to create a demo account

INSERT INTO client_credentials 
  (client_id, client_name, client_email, password_hash, status, is_admin, plan_limit, usage_limits, created_at)
VALUES (
  gen_random_uuid(),
  'Demo User',
  'demo@nexus.ai',
  -- Password: 'demo123' (hashed with Argon2; if you need to update, regenerate the hash)
  '$argon2id$v=19$m=65540,t=3,p=4$salt123456789/salt$hashvalueherexxxxx', 
  'active',
  FALSE,
  1000,
  '{"current_usage":0,"tokens_used":0,"cost_usd":0,"is_vip":false,"vip_limit":10000,"plan_limit":1000}'::jsonb,
  CURRENT_TIMESTAMP
)
ON CONFLICT (client_email) DO NOTHING;

-- Note: To generate a proper Argon2 hash for a custom password, use:
--   python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['argon2']); print(pwd_context.hash('your_password_here'))"
