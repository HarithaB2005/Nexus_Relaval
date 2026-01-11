import asyncpg
import os
import asyncio
from typing import Optional
import logging

# Configure professional logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DatabaseEngine")

DB_POOL: Optional[asyncpg.Pool] = None

async def startup_db_pool():
    """
    Initializes the PostgreSQL connection pool with enterprise retry logic
    and verifies schema integrity.
    """
    global DB_POOL
    
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        logger.error("DATABASE_URL environment variable is not set.")
        return

    max_retries = 5
    base_delay = 2 

    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Database... (Attempt {attempt + 1}/{max_retries})")
            
            # 1. Initialize Connection Pool
            # Note: Parameter is 'timeout', not 'connection_timeout'
            DB_POOL = await asyncpg.create_pool(
                DB_URL,
                min_size=10,
                max_size=30,
                command_timeout=60,
                timeout=30  # Correct parameter name for connection timeout
            )
            
            # 2. Verify and Initialize Schema
            async with DB_POOL.acquire() as conn:
                async with conn.transaction():
                    # Main Credentials Table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS client_credentials (
                            client_id UUID PRIMARY KEY,
                            client_name VARCHAR(255) NOT NULL,
                            client_email VARCHAR(255) UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            status VARCHAR(50) DEFAULT 'active',
                            is_admin BOOLEAN DEFAULT FALSE,
                            plan_limit INTEGER DEFAULT 50,
                            usage_limits JSONB DEFAULT '{"current_usage": 0, "billing_active": false, "is_vip": false}'::jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # API Keys Table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS api_keys (
                            key_id UUID PRIMARY KEY,
                            client_id UUID REFERENCES client_credentials(client_id) ON DELETE CASCADE,
                            api_key_hash VARCHAR(64) UNIQUE NOT NULL,
                            revoked BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # Real Usage Tracking Table (replaces mock data)
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS usage_tracking (
                            id SERIAL PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            requests_count INTEGER DEFAULT 0,
                            tokens_count INTEGER DEFAULT 0,
                            cost_usd DECIMAL(10, 4) DEFAULT 0.0000,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # Billing Plans Table
                    await conn.execute("""
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
                    """)
                    
                    # Invoices Table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS invoices (
                            invoice_id VARCHAR(100) PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            invoice_date DATE NOT NULL,
                            amount_usd DECIMAL(10, 2) NOT NULL,
                            status VARCHAR(50) DEFAULT 'pending',
                            pdf_url TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # Create indexes for performance
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_usage_tracking_client_date 
                        ON usage_tracking(client_id, created_at DESC);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_billing_plans_client 
                        ON billing_plans(client_id, status);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_invoices_client_date 
                        ON invoices(client_id, invoice_date DESC);
                    """)
                    
                    # ========================================
                    # REGISTRY OF TRUTH (Governance Dashboard)
                    # ========================================
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS governance_audit_events (
                            event_id UUID PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            event_type VARCHAR(50) NOT NULL,
                            severity VARCHAR(20) NOT NULL,
                            reason TEXT NOT NULL,
                            input_preview TEXT,
                            output_preview TEXT,
                            metric_value NUMERIC(10, 4),
                            metric_name VARCHAR(100),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            created_date DATE DEFAULT CURRENT_DATE
                        );
                    """)
                    
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS governance_saved_errors (
                            error_id UUID PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            error_category VARCHAR(100) NOT NULL,
                            error_description TEXT NOT NULL,
                            impact_level VARCHAR(20),
                            times_blocked INTEGER DEFAULT 1,
                            first_detected TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            last_detected TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    await conn.execute("""
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
                            risk_score NUMERIC(5, 3),
                            UNIQUE(client_id, summary_date)
                        );
                    """)
                    
                    # ========================================
                    # PRIVACY-BY-DESIGN (Data Sovereignty)
                    # ========================================
                    # Add columns to client_credentials if they don't exist
                    try:
                        await conn.execute("""
                            ALTER TABLE client_credentials 
                            ADD COLUMN data_retention_mode VARCHAR(50) DEFAULT 'standard'
                        """)
                    except asyncpg.DuplicateColumnError:
                        pass
                    
                    try:
                        await conn.execute("""
                            ALTER TABLE client_credentials 
                            ADD COLUMN privacy_settings JSONB DEFAULT '{"log_usage": true, "log_inputs": false, "log_outputs": false, "encryption_at_rest": true}'::jsonb
                        """)
                    except asyncpg.DuplicateColumnError:
                        pass
                    
                    try:
                        await conn.execute("""
                            ALTER TABLE client_credentials 
                            ADD COLUMN local_inference_enabled BOOLEAN DEFAULT FALSE
                        """)
                    except asyncpg.DuplicateColumnError:
                        pass
                    
                    try:
                        await conn.execute("""
                            ALTER TABLE client_credentials 
                            ADD COLUMN local_inference_api_url VARCHAR(500)
                        """)
                    except asyncpg.DuplicateColumnError:
                        pass
                    
                    try:
                        await conn.execute("""
                            ALTER TABLE client_credentials 
                            ADD COLUMN zero_data_retention_enabled BOOLEAN DEFAULT FALSE
                        """)
                    except asyncpg.DuplicateColumnError:
                        pass
                    
                    # Data Retention Policies Table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS data_retention_policies (
                            policy_id UUID PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            policy_name VARCHAR(100) NOT NULL,
                            retention_days INTEGER DEFAULT 30,
                            applies_to VARCHAR(100) NOT NULL,
                            deletion_schedule VARCHAR(50) DEFAULT 'immediate',
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # Local Inference Deployments Table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS local_inference_deployments (
                            deployment_id UUID PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            deployment_name VARCHAR(255) NOT NULL,
                            deployment_url VARCHAR(500) NOT NULL,
                            api_key_hash VARCHAR(64),
                            status VARCHAR(50) DEFAULT 'active',
                            last_healthcheck TIMESTAMP WITH TIME ZONE,
                            healthcheck_status VARCHAR(20) DEFAULT 'unknown',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    
                    # Request Processing Mode Log
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS request_processing_log (
                            log_id UUID PRIMARY KEY,
                            client_id TEXT NOT NULL,
                            request_id UUID,
                            processing_mode VARCHAR(50) NOT NULL,
                            processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            data_retained BOOLEAN,
                            retention_days INTEGER
                        );
                    """)
                    
                    # Create indexes for governance and privacy tables
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_governance_audit_client_date 
                        ON governance_audit_events(client_id, created_at DESC);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_saved_errors_client 
                        ON governance_saved_errors(client_id);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_data_retention_active 
                        ON data_retention_policies(client_id, is_active);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_local_inference_status 
                        ON local_inference_deployments(client_id, status);
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_processing_log_client_date 
                        ON request_processing_log(client_id, processed_at DESC);
                    """)
            
            logger.info("Enterprise Database Schema Verified and Pool Initialized.")
            return

        except (OSError, asyncio.TimeoutError, asyncpg.PostgresError) as e:
            logger.warning(f"Database connection attempt failed: {e}")
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying connection in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.critical("Maximum database connection retries reached.")
                raise e
        except TypeError as te:
            # Catching argument errors immediately to prevent useless retries
            logger.critical(f"Coding Standard Error: Invalid argument in create_pool: {te}")
            raise te

async def shutdown_db_pool():
    global DB_POOL
    if DB_POOL:
        await DB_POOL.close()
        logger.info("Database pool closed successfully.")

def get_db_pool() -> asyncpg.Pool:
    if DB_POOL is None:
        raise RuntimeError("Database pool not initialized.")
    return DB_POOL