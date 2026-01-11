-- Migration: 2026-01-12 - Add Registry of Truth (Governance Dashboard) and Privacy-by-Design
-- This migration adds tables for:
-- 1. Registry of Truth: Track all auditor rejections and quality issues
-- 2. Privacy Controls: Data retention modes and local inference support
-- 3. Data retention policies for compliance

-- =====================================================
-- REGISTRY OF TRUTH (Governance Dashboard)
-- =====================================================
CREATE TABLE IF NOT EXISTS governance_audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'hallucination_blocked', 'quality_reject', 'safety_violation', 'rate_limit', etc.
    severity VARCHAR(20) NOT NULL, -- 'critical', 'high', 'medium', 'low'
    reason TEXT NOT NULL,
    input_preview TEXT,
    output_preview TEXT,
    blocked_content TEXT,
    
    -- Additional metadata for the dashboard
    metric_value NUMERIC(10, 4), -- e.g., quality score, logic gap percentage
    metric_name VARCHAR(100), -- e.g., 'quality_score', 'logic_gap_percentage'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_date DATE DEFAULT CURRENT_DATE,
    INDEX idx_governance_client_date (client_id, created_at DESC),
    INDEX idx_governance_type_date (event_type, created_at DESC),
    INDEX idx_governance_severity (severity)
);

-- Saved Errors Table - aggregated view for dashboard
CREATE TABLE IF NOT EXISTS governance_saved_errors (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    error_category VARCHAR(100) NOT NULL, -- 'medical_dosage', 'financial_logic', 'legal_risk', etc.
    error_description TEXT NOT NULL,
    impact_level VARCHAR(20), -- 'critical', 'high', 'medium', 'low'
    times_blocked INTEGER DEFAULT 1,
    first_detected TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_detected TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_saved_errors_client (client_id),
    INDEX idx_saved_errors_category (error_category)
);

-- Governance Dashboard Summary View (aggregates by domain)
CREATE TABLE IF NOT EXISTS governance_summary (
    summary_id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    summary_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    total_requests INTEGER DEFAULT 0,
    total_rejections INTEGER DEFAULT 0,
    hallucinations_blocked INTEGER DEFAULT 0,
    quality_issues_found INTEGER DEFAULT 0,
    safety_violations_detected INTEGER DEFAULT 0,
    
    avg_quality_score NUMERIC(5, 3),
    risk_score NUMERIC(5, 3), -- 0-1.0, higher = more risk mitigated
    
    UNIQUE(client_id, summary_date),
    INDEX idx_governance_summary_client_date (client_id, summary_date DESC)
);

-- =====================================================
-- PRIVACY-BY-DESIGN (Data Sovereignty)
-- =====================================================

-- Extend client_credentials with privacy controls
ALTER TABLE client_credentials 
ADD COLUMN IF NOT EXISTS data_retention_mode VARCHAR(50) DEFAULT 'standard', -- 'standard', 'zero-retention', 'local-inference-only'
ADD COLUMN IF NOT EXISTS privacy_settings JSONB DEFAULT '{"log_usage": true, "log_inputs": false, "log_outputs": false, "encryption_at_rest": true}'::jsonb,
ADD COLUMN IF NOT EXISTS local_inference_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS local_inference_api_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS zero_data_retention_enabled BOOLEAN DEFAULT FALSE;

-- Data Retention Policy Table
CREATE TABLE IF NOT EXISTS data_retention_policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    policy_name VARCHAR(100) NOT NULL,
    retention_days INTEGER DEFAULT 30, -- days before deletion (0 = immediate, -1 = forever)
    applies_to VARCHAR(100) NOT NULL, -- 'request_logs', 'inference_results', 'audit_logs', 'user_data'
    deletion_schedule VARCHAR(50) DEFAULT 'immediate', -- 'immediate', 'daily', 'weekly', 'monthly'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_retention_policies_client (client_id),
    INDEX idx_retention_policies_active (is_active)
);

-- Local Inference Deployment Table
CREATE TABLE IF NOT EXISTS local_inference_deployments (
    deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    deployment_name VARCHAR(255) NOT NULL,
    deployment_url VARCHAR(500) NOT NULL,
    api_key_hash VARCHAR(64), -- hash of the local deployment's API key
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'paused'
    last_healthcheck TIMESTAMP WITH TIME ZONE,
    healthcheck_status VARCHAR(20) DEFAULT 'unknown', -- 'healthy', 'degraded', 'offline'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_local_inference_client_status (client_id, status),
    INDEX idx_local_inference_healthcheck (last_healthcheck DESC)
);

-- Request Processing Mode Log - track where requests are processed
CREATE TABLE IF NOT EXISTS request_processing_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    request_id UUID,
    processing_mode VARCHAR(50) NOT NULL, -- 'standard', 'zero-retention', 'local-inference'
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_retained BOOLEAN, -- true if data was persisted, false if volatile memory only
    retention_days INTEGER,
    
    INDEX idx_processing_log_client_date (client_id, processed_at DESC),
    INDEX idx_processing_log_mode (processing_mode)
);

-- =====================================================
-- AUDIT INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_governance_audit_client_type ON governance_audit_events(client_id, event_type);
CREATE INDEX IF NOT EXISTS idx_governance_audit_severity_date ON governance_audit_events(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_retention_active ON data_retention_policies(client_id, is_active);
CREATE INDEX IF NOT EXISTS idx_local_inference_status ON local_inference_deployments(client_id, status);

-- =====================================================
-- GRANT PERMISSIONS (if multi-user)
-- =====================================================
-- Uncomment if using separate DB users:
-- GRANT SELECT, INSERT ON governance_audit_events TO app_user;
-- GRANT SELECT, INSERT ON governance_saved_errors TO app_user;
-- GRANT SELECT, INSERT, UPDATE ON data_retention_policies TO app_user;
-- GRANT SELECT, INSERT, UPDATE ON local_inference_deployments TO app_user;
