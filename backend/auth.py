# /backend/auth.py (FINAL, COMPLETE CODE FOR JWT + API KEY UTILITIES)

import hashlib
from typing import Optional, Dict, Any
from db.database import get_db_pool 
import asyncpg 
import logging
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Use environment variables for production security!
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-secret-key-replace-me") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

# Instantiate OAuth2 scheme for dependency injection
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Define the password hashing scheme (Must match key_management.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- JWT Token Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Database Helper Functions ---

async def get_user_by_email(email: str, db_pool: asyncpg.Pool) -> Optional[Dict[str, Any]]:
    """Fetches full user data from DB using email (used during token validation)."""
    try:
        async with db_pool.acquire() as connection:
            user_data = await connection.fetchrow(
                """
                SELECT client_id, client_email, client_name, status
                FROM client_credentials 
                WHERE client_email = $1 AND status = 'active'
                """, 
                email
            )
            return dict(user_data) if user_data else None
    except Exception:
        return None

# --- FastAPI Dependency for Protected Routes (JWT) ---

async def get_current_user(token: str = Depends(oauth2_scheme), db_pool: asyncpg.Pool = Depends(get_db_pool)):
    """
    Validates JWT and returns the current user's data (JWT PROTECTION).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Decode and verify the JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # 'sub' field holds the user email
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. Fetch user data from DB using email
    user = await get_user_by_email(email, db_pool)
    if user is None:
        raise credentials_exception
    return user


# --- API Key Utility Functions (Used by key_management.py and/or external API calls) ---

def hash_key_sha256(key: str) -> str:
    """Hashes the plain API key using SHA-256 for secure comparison (Must match key_management.py)."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

async def is_valid_api_key(key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validates the plain key by hashing it and checking against the HASHED key in the DB."""
    if not key:
        return None

    key_hash_to_check = hash_key_sha256(key)
    
    try:
        pool = get_db_pool()
        async with pool.acquire() as connection:
            # Look up api_keys table and join to client_credentials
            # NOTE: Assuming your DB schema is updated to use api_keys table for keys
            row = await connection.fetchrow(
                """
                SELECT c.client_id, c.client_name, c.client_email, c.status
                FROM client_credentials c
                WHERE c.api_key_hash = $1 AND c.status = 'active'
                """,
                key_hash_to_check,
            )
            if row:
                # Update last_access (optional but good practice)
                await connection.execute("UPDATE client_credentials SET last_access = NOW() WHERE client_id = $1", row['client_id'])
                return dict(row)
            
    except Exception:
        logging.exception("Error during API key validation.")
        return None
    return None

# --- MOCK RATE LIMITING (Can be kept as a placeholder) ---
async def check_usage_limits(client_data: Dict[str, Any]) -> bool:
    """MOCK: Checks if the client has exceeded usage limits."""
    client_id = client_data.get('client_id', '')
    if client_id.endswith('0'):
         return False # Limit exceeded
    return True # Limit OK

# --- Dependency for External API Key Protection (If needed outside the main app) ---
async def api_key_auth_dependency(x_apo_key: Optional[str] = Depends(is_valid_api_key)):
    """
    FastAPI dependency that validates the API key and enforces limits.
    """
    if not x_apo_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid X-APO-Key header."
        )

    # --- DEPLOYMENT STEP: RATE LIMIT CHECK ---
    if not await check_usage_limits(x_apo_key):
         raise HTTPException(
             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
             detail="Too Many Requests: Usage limit exceeded. Please upgrade your plan."
         )

    # Returns the client data if successful
    return x_apo_key