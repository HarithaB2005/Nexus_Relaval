# /backend/main.py (FINAL UNIFIED CODE)

import asyncio
import json
import os 
import sys
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header, status, Depends, APIRouter, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta, datetime
import uuid
import time
import math
from starlette.requests import Request
from starlette.responses import Response, FileResponse
import mimetypes
import PyPDF2
import io
import PyPDF2

# Ensure project root is on sys.path when running from backend/ so imports like "db" resolve
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load .env before importing modules that validate env on import (e.g., auth)
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info(f"Loaded environment from: {env_path}")

# --- Database Lifecycle and Authentication Imports ---
from db.database import startup_db_pool, shutdown_db_pool, get_db_pool 
from key_management import (
    register_new_user, 
    authenticate_user,
    create_new_api_key,
    validate_api_key,
    increment_usage_count
)
from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user 

# >>> 1. ADD THE APO WORKFLOW IMPORT HERE <<<
from agents import apo_workflow 

# OAuth2 setup (required for the login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ==========================================================
# ======= ENVIRONMENT VALIDATION (STARTUP CHECK) ===========
# ==========================================================

def validate_environment():
    """Validate all critical environment variables at startup."""
    required_vars = ["DATABASE_URL", "SECRET_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise RuntimeError(
            f"CRITICAL: Missing required environment variables: {', '.join(missing)}. "
            f"Set them before starting the app."
        )
    
    # Warn if using weak SECRET_KEY
    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        logging.warning("WARNING: SECRET_KEY is less than 32 characters. Generate a stronger key for production.")

validate_environment()
logging.info("✓ Environment validation passed")

# Billing rate (cost per 1k tokens)
REQUEST_COST_PER_1K_TOKENS: float = float(os.environ.get("REQUEST_COST_PER_1K_TOKENS", "0.002"))

app = FastAPI(
    title="Relevo: APO (Agent-based Prompt Optimization) Service",
    description="Unified service endpoints for JWT dashboard and external API Key access.",
    version="2.0.0"
)

# =====================
# Observability: Request ID + Timing
# =====================
request_metrics = {
    "total_requests": 0,
    "total_errors": 0,
    "route_counts": {}
}

def estimate_tokens(messages: List[Dict[str, Any]]) -> int:
    """Rough token estimate based on message text length (chars / 4)."""
    if not messages:
        return 0
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return max(1, math.ceil(total_chars / 4))

@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    req_id = str(uuid.uuid4())
    start = time.time()
    request_metrics["total_requests"] += 1
    path = request.url.path
    request_metrics["route_counts"][path] = request_metrics["route_counts"].get(path, 0) + 1
    response: Response = Response("Internal server error", status_code=500)
    try:
        response = await call_next(request)
    except Exception:
        request_metrics["total_errors"] += 1
        raise
    finally:
        duration = time.time() - start
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Database Lifecycle Hooks
@app.on_event("startup")
async def startup_event():
    """Initializes the PostgreSQL connection pool."""
    await startup_db_pool()
    logging.info("FastAPI: Database pool initialization attempted.")

@app.on_event("shutdown")
async def shutdown_event():
    """Closes the connection pool."""
    await shutdown_db_pool()
    logging.info("FastAPI: Database pool closed cleanly.")

# ==========================================================
# =================== PYDANTIC MODELS ======================
# ==========================================================

class Message(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'user', 'assistant', or 'system'.")
    content: str = Field(..., description="The message content.")

class APORequest(BaseModel):
    messages: List[Message] = Field(..., description="The conversation history.")
    document_context: Optional[str] = Field(None)
    max_iterations: int = Field(3, ge=1, le=5)
    quality_threshold: float = Field(0.9, ge=0.0, le=1.0)

# NEW: Model for Registration 
class UserRegistration(BaseModel):
    name: str
    email: str
    password: str

# Model for JWT response
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class APOResponse(BaseModel):
    user_task: str
    role_selected: str
    optimized_prompt: str
    final_output: str
    output_type: str
    execution_time_seconds: float
    iterations: int
    critic_score: float
    critic_comments: List[Dict[str, Any]]


# ==========================================================
# ==================== MIDDLEWARE ==========================
# ==========================================================

import os
origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",")] if origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# ===================== AUTH ENDPOINTS =====================
# ==========================================================

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/register", response_model=Token, summary="Register new user (Email/Password)")
async def register(user: UserRegistration, db_pool=Depends(get_db_pool)):
    # Pass arguments in the order expected by key_management.register_new_user
    new_user = await register_new_user(user.email, user.password, user.name, db_pool)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Account already exists with this email. Please login instead."
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user["client_email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": new_user}


@auth_router.post("/login", response_model=Token, summary="Login and get JWT token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db_pool=Depends(get_db_pool)
):
    # Pass arguments in the order expected by key_management.authenticate_user
    user = await authenticate_user(form_data.username, form_data.password, db_pool)
    if not user:
        # Check if email exists to provide better error message
        async with db_pool.acquire() as conn:
            email_exists = await conn.fetchval(
                "SELECT client_id FROM client_credentials WHERE client_email = $1",
                form_data.username
            )
        
        if not email_exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account doesn't exist. Please register first.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Please try again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["client_email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@auth_router.get("/me", summary="Get current logged-in user details")
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

app.include_router(auth_router)


# Endpoint for dashboard: create API key for the logged-in user
@app.post('/client/apikey', summary='Create API key for current user')
async def client_create_apikey(current_user: Dict[str, Any] = Depends(get_current_user), db_pool=Depends(get_db_pool)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    # Pass client_id first, then db_pool (matches create_new_api_key signature)
    result = await create_new_api_key(str(current_user['client_id']), db_pool)
    return result

# =================== REAL USAGE & BILLING ===================
@app.get("/usage/summary", summary="Usage summary - real database tracking")
async def usage_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool=Depends(get_db_pool)
):
    """Returns real usage statistics from database for last 30 days."""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT 
                    COALESCE(SUM(requests_count), 0) as total_requests,
                    COALESCE(SUM(tokens_count), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost
                FROM usage_tracking 
                WHERE client_id = $1::TEXT
                AND created_at >= NOW() - INTERVAL '30 days'
                """,
                str(current_user.get("client_id"))
            )
            return {
                "requests_30d": result["total_requests"] if result else 0,
                "tokens_30d": result["total_tokens"] if result else 0,
                "cost_30d": str(round(float(result["total_cost"] or 0), 4)) if result else "0.0000",
                "plan_limit": current_user.get("plan_limit", 1000),
            }
    except Exception as e:
        logging.warning(f"Usage summary query failed: {e}")
        return {
            "requests_30d": 0,
            "tokens_30d": 0,
            "cost_30d": "0.0000",
            "plan_limit": current_user.get("plan_limit", 1000),
        }


@app.get("/usage/history", summary="Usage history - real database tracking")
async def usage_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool=Depends(get_db_pool)
):
    """Returns daily usage breakdown for last 30 days."""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    DATE(created_at) as usage_date,
                    SUM(requests_count) as requests,
                    SUM(tokens_count) as tokens,
                    SUM(cost_usd) as cost
                FROM usage_tracking
                WHERE client_id = $1::TEXT
                AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at) DESC
                """,
                str(current_user.get("client_id"))
            )
            return [
                {
                    "date": row["usage_date"].isoformat() if row["usage_date"] else "",
                    "requests": row["requests"] or 0,
                    "tokens": row["tokens"] or 0,
                    "cost": round(float(row["cost"] or 0), 4)
                }
                for row in rows
            ] if rows else []
    except Exception as e:
        logging.warning(f"Usage history query failed: {e}")
        return []


@app.get("/billing/plan", summary="Billing plan - real account plan info")
async def billing_plan(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool=Depends(get_db_pool)
):
    """Returns current billing plan and subscription status."""
    try:
        async with db_pool.acquire() as conn:
            plan_info = await conn.fetchrow(
                """
                SELECT plan_name, price_monthly, billing_cycle_date, is_vip
                FROM billing_plans
                WHERE client_id = $1::TEXT AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                str(current_user.get("client_id"))
            )
            if plan_info:
                return {
                    "name": plan_info["plan_name"],
                    "price_monthly": plan_info["price_monthly"],
                    "description": f"Current plan with limit: {current_user.get('plan_limit', 1000)} requests/month",
                    "billing_cycle": plan_info["billing_cycle_date"].isoformat() if plan_info["billing_cycle_date"] else "",
                    "is_vip": plan_info["is_vip"],
                }
        # Fallback if no plan found
        return {
            "name": "Free Tier",
            "price_monthly": 0,
            "description": "Free tier with basic limits.",
            "is_vip": False,
        }
    except Exception as e:
        logging.warning(f"Billing plan query failed: {e}")
        return {
            "name": "Free Tier",
            "price_monthly": 0,
            "description": "Free tier with basic limits.",
            "is_vip": False,
        }


@app.get("/billing/invoices", summary="Billing invoices - real invoice history")
async def billing_invoices(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool=Depends(get_db_pool)
):
    """Returns billing invoices for current user."""
    try:
        async with db_pool.acquire() as conn:
            invoices = await conn.fetch(
                """
                SELECT invoice_id, invoice_date, amount_usd, status, pdf_url
                FROM invoices
                WHERE client_id = $1::TEXT
                ORDER BY invoice_date DESC
                LIMIT 12
                """,
                str(current_user.get("client_id"))
            )
            return [
                {
                    "id": row["invoice_id"],
                    "date": row["invoice_date"].isoformat() if row["invoice_date"] else "",
                    "amount": round(float(row["amount_usd"] or 0), 2),
                    "status": row["status"],
                    "download_url": row["pdf_url"] or f"/api/invoice/{row['invoice_id']}/download"
                }
                for row in invoices
            ] if invoices else []
    except Exception as e:
        logging.warning(f"Invoices query failed: {e}")
        return []

# ==========================================================
# ==================== API KEY INTEGRATION =================
# ==========================================================

# --- API Key Security Dependency (Needed for external client access) ---
api_key_scheme = HTTPBearer()

# =====================
# Simple in-memory rate limiter (per client/key)
# =====================
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
_rate_buckets: Dict[str, Dict[str, Any]] = {}

def _rate_key_for_user(user_ctx: Dict[str, Any]) -> str:
    return f"client:{user_ctx.get('client_email') or user_ctx.get('client_id')}"

def _allow_request(rate_key: str) -> bool:
    now = int(time.time() // 60)  # current minute bucket
    bucket = _rate_buckets.get(rate_key)
    if not bucket or bucket.get("minute") != now:
        _rate_buckets[rate_key] = {"minute": now, "count": 1}
        return True
    if bucket["count"] < RATE_LIMIT_PER_MIN:
        bucket["count"] += 1
        return True
    return False

async def get_api_user(
    api_key_cred: HTTPAuthorizationCredentials = Depends(api_key_scheme), 
    db_pool = Depends(get_db_pool)
):
    """
    FastAPI Dependency to validate the API key from the Authorization header (Bearer token).
    """
    api_key = api_key_cred.credentials
    user = await validate_api_key(api_key, db_pool)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# --- API KEY PROTECTED SERVICE ENDPOINT (NO MOCK) ---
@app.post(
    "/api/v1/generate-prompt", 
    response_model=APOResponse, 
    summary="External API Key Protected Service (Runs APO Workflow)"
)
async def generate_prompt_by_key(
    request: APORequest,
    user: Dict[str, Any] = Depends(get_api_user),
    db_pool = Depends(get_db_pool)
):
    """
    Runs the APO workflow after validating the API Key and returns the optimized output.
    """
    logging.info(f"API Key authenticated request from user: {user.get('client_email', 'Unknown User')}")

    if not request.messages or request.messages[-1].role != 'user':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Input must contain a 'messages' list, with the last message from the 'user'.")
    
    # Extract data for the workflow
    full_context_history = [msg.model_dump() for msg in request.messages]
    latest_user_task = request.messages[-1].content
    tokens_est = estimate_tokens(full_context_history)
    cost_est = (tokens_est / 1000) * REQUEST_COST_PER_1K_TOKENS
    
    # VIP bypass: if is_vip is true, skip all limits
    is_vip = user.get("usage_limits", {}).get("is_vip", False)
    
    # Enforce rate limit and plan limit before running workflow
    try:
        if not is_vip:
            if not _allow_request(_rate_key_for_user(user)):
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

            current_usage = int(user.get("usage_limits", {}).get("current_usage", 0))
            plan_limit = int(user.get("plan_limit", 1000))
            if current_usage >= plan_limit:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Plan limit exceeded")

        # >>> 2. CALL THE REAL APO WORKFLOW <<<
        results = await apo_workflow(
            full_context_history=full_context_history,
            abstract_task=latest_user_task,
            document_context=request.document_context,
            max_iterations=request.max_iterations,
            quality_threshold=request.quality_threshold
        )
        # >>> END REAL WORKFLOW CALL <<<
        
        # Increment usage after successful run
        try:
            await increment_usage_count(str(user.get("client_id")), db_pool, tokens_est, cost_est)
        except Exception:
            pass

        return APOResponse(**results)

    except ValidationError as e:
        logging.error(f"Request validation error (422): {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Request Body: {e.errors()}"
        )
    except Exception as e:
        logging.error(f"Internal APO Workflow Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APO Workflow failed internally. Check server logs for details."
        )


# ==========================================================
# ================== SERVICE ENDPOINTS =====================
# ==========================================================

# 4. Health Check Endpoint (Unprotected)
@app.get("/", summary="Service Health Check")
async def health_check():
    return {"status": "APO Service is operational", "version": app.version}

# 6. Basic metrics endpoint (JSON)
@app.get("/metrics", summary="Basic service metrics")
async def metrics():
    return request_metrics


# 5. Main Generation Endpoint (PROTECTED BY JWT)
@app.post(
    "/generate", 
    response_model=APOResponse, 
    summary="Run 4-Agent Optimization Workflow (JWT Protected)"
)
async def generate_optimized_content(
    request: APORequest,
    # This dependency ensures the user is logged in before running the workflow
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Executes the full APO workflow after validating the JWT token. 
    """
    logging.info(f"Authenticated request from user: {current_user.get('client_email', 'Unknown User')}")

    if not request.messages or request.messages[-1].role != 'user':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Input must contain a 'messages' list, with the last message from the 'user'.")
    
    # Extract data for the workflow
    full_context_history = [msg.model_dump() for msg in request.messages]
    latest_user_task = request.messages[-1].content
    tokens_est = estimate_tokens(full_context_history)
    cost_est = (tokens_est / 1000) * REQUEST_COST_PER_1K_TOKENS
    
    # VIP bypass: if is_vip is true, skip all limits
    is_vip = current_user.get("usage_limits", {}).get("is_vip", False)
    
    # Enforce rate limit and plan limit before running workflow
    try:
        if not is_vip:
            if not _allow_request(_rate_key_for_user(current_user)):
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

            current_usage = int(current_user.get("usage_limits", {}).get("current_usage", 0))
            plan_limit = int(current_user.get("plan_limit", 1000))
            if current_usage >= plan_limit:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Plan limit exceeded")

        # >>> 3. CALL THE REAL APO WORKFLOW <<<
        results = await apo_workflow(
            full_context_history=full_context_history,
            abstract_task=latest_user_task,
            document_context=request.document_context,
            max_iterations=request.max_iterations,
            quality_threshold=request.quality_threshold
        )
        # >>> END REAL WORKFLOW CALL <<<
        
        # Increment usage after successful run
        try:
            await increment_usage_count(str(current_user.get("client_id")), db_pool, tokens_est, cost_est)
        except Exception:
            pass

        return APOResponse(**results)

    except ValidationError as e:
        logging.error(f"Request validation error (422): {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Request Body: {e.errors()}"
        )
    except Exception as e:
        logging.error(f"Internal APO Workflow Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APO Workflow failed internally. Check server logs for details."
        )


# ==========================================================
# ============ CONTINUATION ENDPOINT =======================
# ==========================================================

class ContinueOptimizationRequest(BaseModel):
    messages: List[Message]
    continuation_state: Dict[str, Any]
    additional_iterations: int = Field(3, ge=1, le=5)

@app.post("/api/optimize/continue", response_model=APOResponse, summary="Continue optimizing with more iterations")
async def continue_optimization(
    request: ContinueOptimizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Continue optimization when initial score was below threshold.
    Accepts previous state and runs additional iterations.
    """
    try:
        full_context_history = [m.dict() for m in request.messages]
        latest_user_task = next((msg["content"] for msg in reversed(full_context_history) if msg["role"] == "user"), "")
        
        if not latest_user_task:
            raise HTTPException(status_code=400, detail="No user task found in messages")
        
        # Rate limiting
        if current_user:
            from datetime import datetime
            last_request = current_user.get("last_request_time")
            if last_request:
                elapsed = (datetime.now() - last_request).total_seconds()
                if elapsed < 0.5:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            current_usage = int(current_user.get("usage_limits", {}).get("current_usage", 0))
            plan_limit = int(current_user.get("plan_limit", 1000))
            if current_usage >= plan_limit:
                raise HTTPException(status_code=429, detail="Plan limit exceeded")
        
        # Run continued workflow
        results = await apo_workflow(
            full_context_history=full_context_history,
            abstract_task=latest_user_task,
            document_context=request.continuation_state.get("document_context"),
            max_iterations=request.additional_iterations,
            quality_threshold=0.95,
            continuation_state=request.continuation_state
        )
        
        # Increment usage
        try:
            tokens_est = estimate_tokens(full_context_history)
            cost_est = (tokens_est / 1000) * REQUEST_COST_PER_1K_TOKENS
            await increment_usage_count(str(current_user.get("client_id")), db_pool, tokens_est, cost_est)
        except Exception:
            pass
        
        return APOResponse(**results)
    
    except Exception as e:
        logging.error(f"Continue optimization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# ================== FILE UPLOAD ENDPOINTS =================
# ==========================================================

@app.post("/upload/pdf", summary="Upload PDF and extract text")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_pool=Depends(get_db_pool)
):
    """Upload PDF file and extract text content for use in document_context."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    # Validate file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Validate file type
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Extract text using PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        extracted_text = ""
        
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        if not extracted_text.strip():
            raise ValueError("No text content found in PDF")
        
        logging.info(f"PDF uploaded by {current_user.get('client_email')}: {file.filename} ({len(extracted_text)} chars)")
        
        return {
            "status": "success",
            "filename": file.filename,
            "pages": len(pdf_reader.pages),
            "text_length": len(extracted_text),
            "extracted_text": extracted_text[:50000],  # Return first 50k chars
            "note": "Use 'extracted_text' field as document_context in your APO request"
        }
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF: {str(e)}")


# ==========================================================
# =================== USAGE & BILLING ======================
# ==========================================================

