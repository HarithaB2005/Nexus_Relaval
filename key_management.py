# /backend/key_management.py (FINAL, COMPLETE and CORRECTED)

import asyncpg
from typing import Dict, Any, Optional
from passlib.context import CryptContext
import uuid
import hashlib
# REMOVED: from passlib.exc import InvalidSecretError 

# Define the password hashing scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Password Hashing Functions ---
def _truncate_password(password: str) -> str:
    """Helper to truncate password to 72 bytes for bcrypt."""
    truncated_password = password.encode('utf-8')[:72]
    # Decode back to string (passlib expects a string/text input)
    return truncated_password.decode('utf-8', 'ignore')

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt. 
    CRITICAL FIX: Truncates password to 72 bytes to prevent ValueError.
    """
    truncated_password_str = _truncate_password(password)
    return pwd_context.hash(truncated_password_str)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    CRITICAL FIX: Truncates plain_password for verification consistency.
    """
    truncated_password_str = _truncate_password(plain_password)

    try:
        return pwd_context.verify(truncated_password_str, hashed_password)
    except Exception:
        # Catch unexpected errors during verification
        return False

# --- API Key Hashing ---
def generate_raw_api_key() -> str:
    """Generates a secure, 32-character hexadecimal API key with a prefix."""
    import secrets
    KEY_PREFIX = "apo_sk_" 
    return f"{KEY_PREFIX}{secrets.token_hex(16)}"

def generate_api_key_hash(key: str) -> str:
    """Hashes a raw API key using SHA-256 for storage."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

# --- Registration Function (Uses Email/Password) ---
async def register_new_user(email: str, password: str, name: str, db_pool) -> Optional[Dict[str, Any]]:
    """Registers a new user with hashed password."""
    hashed_pass = hash_password(password) 
    client_id = str(uuid.uuid4())
    
    try:
        async with db_pool.acquire() as connection:
            # 1. Check if email already exists
            existing_user = await connection.fetchval(
                "SELECT client_id FROM client_credentials WHERE client_email = $1", 
                email
            )
            if existing_user:
                return None 

            # 2. Insert new user with hashed password (Requires 'password_hash' column)
            result = await connection.fetchrow(
                """
                INSERT INTO client_credentials (client_id, client_name, client_email, password_hash, status)
                VALUES ($1, $2, $3, $4, 'active')
                RETURNING client_id, client_name, client_email;
                """,
                client_id, name, email, hashed_pass
            )
            return dict(result) if result else None
            
    except Exception as e:
        print(f"Database error during registration: {e}")
        return None

# --- Authentication Function (Uses Email/Password) ---
async def authenticate_user(email: str, password: str, db_pool) -> Optional[Dict[str, Any]]:
    """Authenticates user using email and password."""
    try:
        async with db_pool.acquire() as connection:
            # 1. Fetch user data and password hash by email
            user_data = await connection.fetchrow(
                """
                SELECT client_id, client_email, password_hash, client_name, status
                FROM client_credentials 
                WHERE client_email = $1 AND status = 'active'
                """, 
                email
            )
            
            if user_data:
                # 2. Verify the provided password against the stored hash
                if verify_password(password, user_data['password_hash']): 
                    user_dict = dict(user_data)
                    del user_dict['password_hash'] 
                    return user_dict
                    
    except Exception as e:
        print(f"Database error during authentication: {e}")
        
    return None

# --- Function for Dashboard API Key Generation (Needs DB Pool) ---
async def create_new_api_key(client_id: str, db_pool) -> Dict[str, str]:
    """Generates a new API key for an existing client and updates the DB."""
    raw_key = generate_raw_api_key()
    hashed_key = generate_api_key_hash(raw_key)

    sql = """
    UPDATE client_credentials 
    SET api_key_hash = $2, last_access = NOW()
    WHERE client_id = $1;
    """
    async with db_pool.acquire() as connection:
        await connection.execute(sql, client_id, hashed_key)

    return {"raw_key": raw_key}

# --- API Key Validation Function (NEW) ---
async def validate_api_key(api_key: str, db_pool) -> Optional[Dict[str, Any]]:
    """
    Validates a raw API key against the stored hash in the database.
    Returns user data if valid, None otherwise.
    """
    # 1. Generate the hash of the incoming key
    incoming_key_hash = generate_api_key_hash(api_key)

    try:
        async with db_pool.acquire() as connection:
            # 2. Look up user by the hashed key
            user_data = await connection.fetchrow(
                """
                SELECT client_id, client_name, client_email
                FROM client_credentials 
                WHERE api_key_hash = $1 AND status = 'active'
                """, 
                incoming_key_hash
            )
            
            # 3. If found, update last_access and return user info
            if user_data:
                await connection.execute(
                    "UPDATE client_credentials SET last_access = NOW() WHERE client_id = $1",
                    user_data['client_id']
                )
                return dict(user_data)
            
    except Exception as e:
        print(f"Database error during API key validation: {e}")
        
    return None