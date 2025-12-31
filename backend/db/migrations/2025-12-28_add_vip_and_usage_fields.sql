-- Migration: Align usage_limits with VIP and usage fields
-- Date: 2025-12-28
-- Purpose: Add vip_limit field, triggers, and indexes for production readiness

BEGIN;

-- Ensure pgcrypto for UUID defaults
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Add updated_at triggers if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.routines WHERE routine_name = 'update_timestamp_column'
    ) THEN
        CREATE OR REPLACE FUNCTION update_timestamp_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE 'plpgsql';
    END IF;
END $$;

-- Add updated_at column to client_credentials if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='client_credentials' AND column_name='updated_at'
    ) THEN
        ALTER TABLE client_credentials ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Add updated_at column to api_keys if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='api_keys' AND column_name='updated_at'
    ) THEN
        ALTER TABLE api_keys ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Drop old triggers if exist and recreate
DROP TRIGGER IF EXISTS trg_update_client ON client_credentials;
CREATE TRIGGER trg_update_client BEFORE UPDATE ON client_credentials FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS trg_update_keys ON api_keys;
CREATE TRIGGER trg_update_keys BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- Gently backfill usage_limits JSONB keys for compatibility
-- Adds keys only when missing; preserves existing values
UPDATE client_credentials
SET usage_limits = usage_limits
    || jsonb_build_object(
        'current_usage', COALESCE((usage_limits->>'current_usage')::int, 0),
        'tokens_used', COALESCE((usage_limits->>'tokens_used')::bigint, 0),
        'cost_usd', COALESCE((usage_limits->>'cost_usd')::numeric, 0),
        'is_vip', COALESCE((usage_limits->>'is_vip')::boolean, FALSE),
        'vip_limit', COALESCE((usage_limits->>'vip_limit')::int, 10000),
        'plan_limit', COALESCE((usage_limits->>'plan_limit')::int, 1000)
    )
WHERE usage_limits IS NOT NULL;

-- If usage_limits is NULL, initialize with sane defaults
UPDATE client_credentials
SET usage_limits = jsonb_build_object(
        'current_usage', 0,
        'tokens_used', 0,
        'cost_usd', 0,
        'is_vip', false,
        'vip_limit', 10000,
        'plan_limit', COALESCE(plan_limit, 1000)
    )
WHERE usage_limits IS NULL;

-- Helpful index for faster API key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (api_key_hash);
CREATE INDEX IF NOT EXISTS idx_client_email ON client_credentials (client_email);

COMMIT;
