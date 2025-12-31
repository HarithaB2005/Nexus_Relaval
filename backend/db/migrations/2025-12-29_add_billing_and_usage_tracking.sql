-- Migration: Add Real Billing & Usage Tracking Tables
-- Date: 2025-12-29
-- Purpose: Replace mock data with proper database-backed usage and billing tracking

-- Real Usage Tracking Table (replaces mock data endpoints)
CREATE TABLE IF NOT EXISTS usage_tracking (
    id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    requests_count INTEGER DEFAULT 0,
    tokens_count INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 4) DEFAULT 0.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Billing Plans Table (tracks customer subscription plans)
CREATE TABLE IF NOT EXISTS billing_plans (
    id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    price_monthly DECIMAL(10, 2) DEFAULT 0.00,
    billing_cycle_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    is_vip BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invoices Table (stores billing invoices for customers)
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR(100) PRIMARY KEY,
    client_id TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    amount_usd DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    pdf_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_usage_tracking_client_date 
ON usage_tracking(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_billing_plans_client 
ON billing_plans(client_id, status);

CREATE INDEX IF NOT EXISTS idx_invoices_client_date 
ON invoices(client_id, invoice_date DESC);

-- Seed data: Add default plans for existing users
INSERT INTO billing_plans (client_id, plan_name, price_monthly, billing_cycle_date, status, is_vip)
SELECT 
    client_id::TEXT,
    CASE 
        WHEN is_admin THEN 'Enterprise'
        ELSE 'Free'
    END as plan_name,
    CASE 
        WHEN is_admin THEN 99.00
        ELSE 0.00
    END as price_monthly,
    DATE_TRUNC('month', NOW()) + INTERVAL '30 days' as billing_cycle_date,
    'active' as status,
    COALESCE((usage_limits->>'is_vip')::boolean, FALSE) as is_vip
FROM client_credentials
WHERE client_id::TEXT NOT IN (SELECT DISTINCT client_id FROM billing_plans)
ON CONFLICT DO NOTHING;

-- Add sample usage data for demo purposes (last 7 days)
INSERT INTO usage_tracking (client_id, requests_count, tokens_count, cost_usd, created_at)
SELECT 
    cc.client_id::TEXT,
    (RANDOM() * 100)::INTEGER,
    (RANDOM() * 10000)::INTEGER,
    (RANDOM() * 0.5)::DECIMAL,
    NOW() - (INTERVAL '1 day' * i)
FROM client_credentials cc
CROSS JOIN LATERAL generate_series(0, 6) as i
WHERE (cc.client_id::TEXT || NOW()::DATE - (INTERVAL '1 day' * i)::DATE) NOT IN (
    SELECT client_id || created_at::DATE FROM usage_tracking
)
ON CONFLICT DO NOTHING;

-- Add sample invoices for demo purposes
INSERT INTO invoices (invoice_id, client_id, invoice_date, amount_usd, status, pdf_url)
SELECT 
    'inv_' || TO_CHAR(DATE_TRUNC('month', NOW() - (INTERVAL '1 month' * i)), 'YYYYMM') || '_' || SUBSTRING(cc.client_id::TEXT, 1, 8),
    cc.client_id::TEXT,
    (DATE_TRUNC('month', NOW() - (INTERVAL '1 month' * i)))::DATE,
    COALESCE((bp.price_monthly), 0),
    'paid',
    NULL
FROM client_credentials cc
LEFT JOIN billing_plans bp ON cc.client_id::TEXT = bp.client_id AND bp.status = 'active'
CROSS JOIN LATERAL generate_series(0, 2) as i
WHERE bp.is_vip OR bp.price_monthly > 0
ON CONFLICT (invoice_id) DO NOTHING;
