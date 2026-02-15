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