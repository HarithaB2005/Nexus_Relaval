import hashlib
import logging
import os
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db.database import get_db_pool 

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-very-secret-key-replace-me":
    raise ValueError(
        "CRITICAL: SECRET_KEY environment variable not set or is placeholder. "
        "Set a strong 32+ character random key via environment variables. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 8 * 60  # 8 hours - standard enterprise session timeout (was 24h) 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_user_by_email(email: str, db_pool: asyncpg.Pool) -> Optional[Dict[str, Any]]:
    """Fetches user with full enterprise context for usage validation."""
    try:
        async with db_pool.acquire() as connection:
            user_data = await connection.fetchrow(
                """
                SELECT client_id, client_email, client_name, status, is_admin, usage_limits, plan_limit,
                       clarifier_count_last_5, last_5_request_types
                FROM client_credentials 
                WHERE client_email = $1 AND status = 'active'
                """, 
                email
            )
            if not user_data:
                return None
            
            u_dict = dict(user_data)
            # Ensure usage_limits is always a dictionary
            if isinstance(u_dict.get("usage_limits"), str):
                u_dict["usage_limits"] = json.loads(u_dict["usage_limits"])
            if isinstance(u_dict.get("last_5_request_types"), str):
                try:
                    u_dict["last_5_request_types"] = json.loads(u_dict["last_5_request_types"])
                except Exception:
                    u_dict["last_5_request_types"] = []
            return u_dict
    except Exception as e:
        logging.error(f"Authentication DB Error: {e}")
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db_pool: asyncpg.Pool = Depends(get_db_pool)):
    """FastAPI Dependency for protected routes."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(email, db_pool)
    if user is None:
        raise credentials_exception
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)