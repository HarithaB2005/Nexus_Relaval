-- Migration: Add Audit Events & Privacy Controls
-- Date: 2026-01-09
-- Purpose: Registry of Truth + Privacy-by-Design features

-- 1. AUDIT EVENTS TABLE (Registry of Truth)
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    event_type VARCHAR(100) NOT NULL, -- 'safety_block', 'quality_reject', 'rate_limit', 'validation_error'
    severity VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high', 'critical'
    reason TEXT NOT NULL,
    input_preview TEXT,
    output_preview TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_client_date 
ON audit_events(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_severity 
ON audit_events(severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_type 
ON audit_events(event_type, created_at DESC);

-- 2. ADD PRIVACY CONTROLS TO USERS
ALTER TABLE client_credentials 
ADD COLUMN IF NOT EXISTS data_retention_mode VARCHAR(50) DEFAULT 'standard';
-- Values: 'standard', 'zero-retention', 'anonymous'

ALTER TABLE client_credentials 
ADD COLUMN IF NOT EXISTS privacy_settings JSONB DEFAULT '{"log_usage": true, "log_inputs": false, "log_outputs": false}'::jsonb;

-- 3. AUDIT SUMMARY VIEW
CREATE OR REPLACE VIEW audit_summary AS
SELECT 
    client_id,
    event_type,
    severity,
    COUNT(*) as event_count,
    DATE_TRUNC('day', created_at) as event_date
FROM audit_events
GROUP BY client_id, event_type, severity, DATE_TRUNC('day', created_at);

-- 4. SEED DEMO AUDIT DATA (last 30 days)
INSERT INTO audit_events (client_id, event_type, severity, reason, input_preview, metadata, created_at)
SELECT 
    cc.client_id::TEXT,
    CASE 
        WHEN RANDOM() < 0.3 THEN 'quality_reject'
        WHEN RANDOM() < 0.6 THEN 'safety_block'
        WHEN RANDOM() < 0.85 THEN 'rate_limit'
        ELSE 'validation_error'
    END as event_type,
    CASE 
        WHEN RANDOM() < 0.05 THEN 'critical'
        WHEN RANDOM() < 0.20 THEN 'high'
        WHEN RANDOM() < 0.60 THEN 'medium'
        ELSE 'low'
    END as severity,
    CASE 
        WHEN RANDOM() < 0.3 THEN 'Quality score below threshold (0.85 < 0.90)'
        WHEN RANDOM() < 0.6 THEN 'Content safety filter blocked inappropriate medical advice'
        WHEN RANDOM() < 0.85 THEN 'Rate limit exceeded (120 requests/minute)'
        ELSE 'Invalid request format (missing required field: messages)'
    END as reason,
    'Preview of blocked content...',
    jsonb_build_object(
        'score', ROUND((RANDOM() * 0.3 + 0.6)::numeric, 3),
        'iterations', (RANDOM() * 5)::int + 1,
        'model', 'gpt-4'
    ),
    NOW() - (INTERVAL '1 day' * (RANDOM() * 30)::int + INTERVAL '1 hour' * (RANDOM() * 24)::int)
FROM client_credentials cc
CROSS JOIN LATERAL generate_series(1, (RANDOM() * 15)::int + 5) as i
LIMIT 200
ON CONFLICT DO NOTHING;

COMMENT ON TABLE audit_events IS 'Registry of Truth: Logs all safety/quality rejections for governance';
COMMENT ON COLUMN client_credentials.data_retention_mode IS 'Privacy mode: standard, zero-retention, or anonymous';
COMMENT ON COLUMN client_credentials.privacy_settings IS 'Granular privacy controls (log_usage, log_inputs, log_outputs)';
