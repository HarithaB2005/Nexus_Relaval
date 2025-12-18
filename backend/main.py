# /backend/main.py (FINAL UNIFIED CODE)

import asyncio
import json
import os 
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header, status, Depends, APIRouter 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta

# --- Database Lifecycle and Authentication Imports ---
from db.database import startup_db_pool, shutdown_db_pool, get_db_pool 
from key_management import (
    register_new_user, 
    authenticate_user,
    create_new_api_key,
    validate_api_key
)
from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user 

# >>> 1. ADD THE APO WORKFLOW IMPORT HERE <<<
from agents import apo_workflow 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# OAuth2 setup (required for the login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ==========================================================
# ======= CORE SETUP: LOAD ENV and DB LIFECYCLE HOOKS ======
# ==========================================================

# Load .env explicitly from the project root
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
logging.info(f"Loaded environment from: {env_path}")

app = FastAPI(
    title="NexusAI: APO (Agent-based Prompt Optimization) Service",
    description="Unified service endpoints for JWT dashboard and external API Key access.",
    version="2.0.0"
)

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
    video_url: Optional[str] = Field(None)
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

origins = ["*"] 

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
    new_user = await register_new_user(user.email, user.password, user.name, db_pool)
    if not new_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
    
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
    user = await authenticate_user(form_data.username, form_data.password, db_pool)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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
    result = await create_new_api_key(str(current_user['client_id']), db_pool)
    return result

# ==========================================================
# ==================== API KEY INTEGRATION =================
# ==========================================================

# --- API Key Security Dependency (Needed for external client access) ---
api_key_scheme = HTTPBearer()

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
    user: Dict[str, Any] = Depends(get_api_user) 
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
    
    try:
        # >>> 2. CALL THE REAL APO WORKFLOW <<<
        results = await apo_workflow(
            full_context_history=full_context_history,
            abstract_task=latest_user_task,
            document_context=request.document_context,
            video_url=request.video_url,
            max_iterations=request.max_iterations,
            quality_threshold=request.quality_threshold
        )
        # >>> END REAL WORKFLOW CALL <<<
        
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


# 5. Main Generation Endpoint (PROTECTED BY JWT)
@app.post(
    "/generate", 
    response_model=APOResponse, 
    summary="Run 4-Agent Optimization Workflow (JWT Protected)"
)
async def generate_optimized_content(
    request: APORequest,
    # This dependency ensures the user is logged in before running the workflow
    current_user: Dict[str, Any] = Depends(get_current_user) 
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
    
    try:
        # >>> 3. CALL THE REAL APO WORKFLOW <<<
        results = await apo_workflow(
            full_context_history=full_context_history,
            abstract_task=latest_user_task,
            document_context=request.document_context,
            video_url=request.video_url,
            max_iterations=request.max_iterations,
            quality_threshold=request.quality_threshold
        )
        # >>> END REAL WORKFLOW CALL <<<
        
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