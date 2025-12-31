import asyncpg
import uuid
import hashlib
import secrets
import logging
import json
from typing import Dict, Any, Optional
from passlib.context import CryptContext

# Password hashing configuration
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
logger = logging.getLogger("Nexus-KeyManager")

# ==========================================================
# ==================== KEY UTILITIES =======================
# ==========================================================

def generate_raw_api_key() -> str:
    """Generates a secure, prefix-based raw API key."""
    return f"relevo_sk_{secrets.token_hex(16)}"

def generate_api_key_hash(key: str) -> str:
    """Creates a SHA-256 hash of the API key for secure storage."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

# ==========================================================
# ==================== AUTH & REGISTRATION =================
# ==========================================================

async def register_new_user(email: str, password: str, name: str, db_pool) -> Optional[Dict[str, Any]]:
    """Registers a user and initializes enterprise fields."""
    hashed_pass = pwd_context.hash(password)
    client_id = str(uuid.uuid4())
    initial_raw = generate_raw_api_key()
    initial_hash = generate_api_key_hash(initial_raw)
    
    default_limits = {
        "current_usage": 0, 
        "billing_active": False, 
        "is_vip": False
    }
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval("SELECT client_id FROM client_credentials WHERE client_email = $1", email)
            if exists: 
                return None
            
            res = await conn.fetchrow(
                """INSERT INTO client_credentials 
                   (client_id, client_name, client_email, password_hash, status, is_admin, usage_limits, plan_limit) 
                   VALUES ($1, $2, $3, $4, 'active', FALSE, $5::jsonb, 50) 
                   RETURNING client_id, client_name, client_email, is_admin, usage_limits, plan_limit""",
                client_id, name, email, hashed_pass, json.dumps(default_limits)
            )
            
            await conn.execute(
                "INSERT INTO api_keys (key_id, client_id, api_key_hash, revoked) VALUES ($1, $2, $3, FALSE)",
                str(uuid.uuid4()), client_id, initial_hash
            )
            
            if res:
                data = dict(res)
                data['raw_key'] = initial_raw
                if isinstance(data['usage_limits'], str):
                    data['usage_limits'] = json.loads(data['usage_limits'])
                return data
    return None

async def authenticate_user(email: str, password: str, db_pool) -> Optional[Dict[str, Any]]:
    """Authenticates and parses JSONB for the response."""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            """SELECT client_id, client_name, client_email, password_hash, is_admin, usage_limits, plan_limit 
               FROM client_credentials WHERE client_email = $1""", 
            email
        )
        if user and pwd_context.verify(password, user['password_hash']):
            u_dict = dict(user)
            u_dict.pop('password_hash')
            if isinstance(u_dict['usage_limits'], str):
                u_dict['usage_limits'] = json.loads(u_dict['usage_limits'])
            return u_dict
    return None

# ==========================================================
# ==================== USAGE & LIMITS ======================
# ==========================================================

async def increment_usage_count(client_id: str, db_pool, tokens_used: int = 0, cost_usd: float = 0.0):
    """Records usage in both new tracking table (primary) and legacy JSONB (backward compat)."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # 1. Write to new usage_tracking table (primary tracking system)
            try:
                await conn.execute(
                    """
                    INSERT INTO usage_tracking (client_id, requests_count, tokens_count, cost_usd)
                    VALUES ($1, 1, $2, $3)
                    """,
                    client_id, tokens_used, cost_usd
                )
            except Exception as e:
                logger.warning(f"Failed to insert into usage_tracking: {e}")
            
            # 2. Keep JSONB update for backward compatibility with existing code
            try:
                await conn.execute(
                    """
                    UPDATE client_credentials 
                    SET usage_limits = usage_limits || jsonb_build_object(
                        'current_usage', to_jsonb(COALESCE((usage_limits->>'current_usage')::int, 0) + 1),
                        'tokens_used',  to_jsonb(COALESCE((usage_limits->>'tokens_used')::bigint, 0) + $2),
                        'cost_usd',     to_jsonb(COALESCE((usage_limits->>'cost_usd')::numeric, 0) + $3)
                    )
                    WHERE client_id = $1
                    """,
                    client_id, tokens_used, cost_usd
                )
            except Exception as e:
                logger.warning(f"Failed to update client_credentials usage_limits: {e}")

async def grant_vip_access(client_id: str, db_pool):
    """Force-injects is_vip status."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """UPDATE client_credentials 
               SET usage_limits = usage_limits || '{"is_vip": true}'::jsonb
               WHERE client_id = $1""", 
            client_id
        )

# ==========================================================
# ==================== KEY MANAGEMENT ======================
# ==========================================================

async def create_new_api_key(client_id: str, db_pool) -> Dict[str, str]:
    """Generates and stores a new API key."""
    raw = generate_raw_api_key()
    hashed = generate_api_key_hash(raw)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (key_id, client_id, api_key_hash, revoked) VALUES ($1, $2, $3, FALSE)",
            str(uuid.uuid4()), client_id, hashed
        )
    return {"raw_key": raw}

async def validate_api_key(api_key: str, db_pool) -> Optional[Dict[str, Any]]:
    """Validates key and returns associated client context."""
    h = generate_api_key_hash(api_key)
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            """SELECT u.client_id, u.is_admin, u.client_email, u.usage_limits, u.plan_limit 
               FROM client_credentials u 
               JOIN api_keys k ON u.client_id = k.client_id
               WHERE k.api_key_hash = $1 AND k.revoked = FALSE AND u.status = 'active'""", 
            h
        )
        if user:
            u_dict = dict(user)
            if isinstance(u_dict['usage_limits'], str):
                u_dict['usage_limits'] = json.loads(u_dict['usage_limits'])
            return u_dict
    return None