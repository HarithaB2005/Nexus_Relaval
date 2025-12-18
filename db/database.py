# db/database.py
import asyncpg
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global pool variable
DB_POOL: Optional[asyncpg.Pool] = None

async def startup_db_pool():
    """Initializes the database connection pool on FastAPI startup."""
    global DB_POOL
    try:
        # Get connection string securely from environment variables
        DB_URL = os.getenv("DATABASE_URL")
        if not DB_URL:
            logging.error("DATABASE_URL not set. Database initialization failed.")
            return
        else:
            logging.info("DATABASE_URL found in environment (hidden). Proceeding to initialize DB pool.")

        # Create a pool of connections for efficient management
        DB_POOL = await asyncpg.create_pool(
            DB_URL,
            min_size=5,
            max_size=20
        )
        logging.info("PostgreSQL connection pool established successfully.")
        
        # --- CRITICAL: Ensure the table exists on startup (Mock Migration) ---
        async with DB_POOL.acquire() as connection:
            await connection.execute("""
            CREATE TABLE IF NOT EXISTS client_credentials (
                client_id UUID PRIMARY KEY,
                client_name VARCHAR(255) NOT NULL,
                client_email VARCHAR(255) UNIQUE NOT NULL,
                api_key_hash VARCHAR(64) UNIQUE NOT NULL,
                status VARCHAR(50) DEFAULT 'active',
                usage_limits JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                last_access TIMESTAMP WITHOUT TIME ZONE
            );
            """)
            logging.info("Client credentials table verified.")

            # Ensure `last_access` column exists (older DBs may lack it)
            try:
                await connection.execute("ALTER TABLE client_credentials ADD COLUMN IF NOT EXISTS last_access TIMESTAMP WITHOUT TIME ZONE;")
                logging.info("Ensured 'last_access' column exists on client_credentials.")
            except Exception:
                logging.exception("Failed to ensure last_access column; continuing.")

            # Migration: If older deployments stored hashes in `hashed_api_key`, migrate them to `api_key_hash`.
            try:
                col_exists = await connection.fetchval(
                    "SELECT 1 FROM information_schema.columns WHERE table_name='client_credentials' AND column_name='hashed_api_key'"
                )
                api_col_exists = await connection.fetchval(
                    "SELECT 1 FROM information_schema.columns WHERE table_name='client_credentials' AND column_name='api_key_hash'"
                )
                if col_exists and not api_col_exists:
                    # Add api_key_hash column, copy data, keep old column for safety
                    await connection.execute("ALTER TABLE client_credentials ADD COLUMN IF NOT EXISTS api_key_hash VARCHAR(64);")
                    await connection.execute("UPDATE client_credentials SET api_key_hash = hashed_api_key WHERE api_key_hash IS NULL;")
                    logging.info("Migrated hashed_api_key -> api_key_hash for existing rows.")
            except Exception:
                logging.exception("Database migration check failed; continuing startup.")
            
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        # In a real system, you might raise an exception to halt startup
        
async def shutdown_db_pool():
    """Closes the connection pool on FastAPI shutdown."""
    global DB_POOL
    if DB_POOL:
        await DB_POOL.close()
        logging.info("PostgreSQL connection pool closed.")

def get_db_pool() -> asyncpg.Pool:
    """Provides the active pool instance, typically used by dependencies."""
    if DB_POOL is None:
        raise Exception("Database pool not initialized.")
    return DB_POOL