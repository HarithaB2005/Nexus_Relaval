# Nexus Relaval - Full System Logic (Backend + Frontend)

This document describes how the backend and frontend work, based on the current code. It covers the core workflow, agents, and how Groq/Ollama/Gemini are selected.

## Backend Overview

The backend is a FastAPI service that exposes:
- JWT-protected user endpoints at /generate and /auth/*
- API key protected endpoints at /api/v1/generate-prompt
- Usage, billing, and file upload endpoints
- A 4-agent APO workflow (Classifier -> Planner -> Executor -> Critic)

Key modules:
- backend/main.py: FastAPI app, routes, auth, rate limits, usage/billing
- backend/agents.py: APO orchestration and decision logic
- backend/util.py: LLM calls, classifier, planner prompt construction, critic
- backend/auth.py: JWT handling and user lookup
- backend/key_management.py: registration, API key creation, usage tracking
- backend/db/database.py: DB pool and schema initialization
- backend/file_upload_endpoints.py: helper endpoints for PDF/video (main uses PDF)
- backend/wsgi.py: production entry for gunicorn

## Backend: main.py (API entry points)

### Environment and startup
- Loads .env from backend/.env and validates required vars (DATABASE_URL, SECRET_KEY).
- Adds a request middleware that creates X-Request-ID and X-Response-Time headers, plus basic security headers.
- Starts and stops the asyncpg connection pool on startup/shutdown.

### Request metrics and token estimation
- request_metrics is an in-memory dictionary with total_requests, total_errors, and route_counts.
- The middleware increments total_requests and per-path route_counts on every request, increments total_errors on unhandled exceptions.
- estimate_tokens uses a simple character count heuristic (sum of content length / 4, minimum 1). It is only used for cost/usage tracking, not for LLM limits.

### Rate limiter (in-memory)
- RATE_LIMIT_PER_MIN comes from env (default 120).
- _rate_buckets holds per-minute counters keyed by client email or client_id.
- _allow_request creates or increments a minute bucket and allows up to RATE_LIMIT_PER_MIN requests per minute.
- This limiter is process-local and resets on server restart.

### Pydantic models
- Message: role, content
- APORequest: messages, document_context, max_iterations, quality_threshold
- Token and UserRegistration for auth
- APOResponse: complete response structure (final_output, optimized_prompt, scores, metadata, clarifier options, etc.)

### Auth endpoints
- /auth/register: register user and return JWT.
- /auth/login: OAuth2 password flow; returns JWT and user info.
- /auth/me: returns current user from JWT.

### API key authentication dependency
- get_api_user extracts the Bearer token from the Authorization header.
- validate_api_key checks hash against api_keys, verifies non-revoked, and returns user context.
- If the token is invalid, it returns 401 with WWW-Authenticate: Bearer.

### APO workflow endpoints
- /generate (JWT-protected):
  1) Validates user and rate limit
  2) Estimates tokens and cost
  3) Calls apo_workflow with history and optional document_context
  4) Updates usage tracking and clarifier fatigue counters

- /api/v1/generate-prompt (API key):
  Same flow, but user context comes from API key instead of JWT.

### Continuation endpoint
- /api/optimize/continue accepts messages, continuation_state, and additional_iterations.
- It reconstructs the latest user task from history and resumes apo_workflow with continuation_state.
- It uses a lower quality_threshold (0.95) and allows more iterations.
- It runs the same usage/clarifier counters as the normal endpoints.

### Usage and billing endpoints
- /usage/summary and /usage/history: read from usage_tracking
- /billing/plan and /billing/invoices: read from billing_plans and invoices

### Health and metrics endpoints
- / returns a basic health payload with the API version.
- /metrics returns the in-memory request_metrics dictionary.

### PDF upload
- /upload/pdf: accepts PDF, extracts text with PyPDF2, returns extracted_text
- The extracted text is intended for document_context input to the workflow

## Backend: agents.py (APO orchestration)

### The 4-agent pipeline
1) Classifier (LLM-0): classify_prompt
2) Validation gate (LLM-0b): validate_intent_context
3) CSA logic: clarify/pathfinder/rejection intelligence
4) Planner (LLM-1): build optimized prompt
5) Executor (LLM-2): generate final output
6) Critic (LLM-3): score and iterate if needed

### Key logic and flow
- Classification runs on abstract_task_with_date (adds current date).
- Validation checks if the request is actionable without guessing.
- Clarifier/Pathfinder decisions:
  - Uses ambiguity and validation signals
  - Can offer focus options for broad questions
  - Rejection intelligence triggers when the user rejects prior output

### Internal helpers in agents.py (what they do)
- _rephrase_similarity uses SequenceMatcher on the last two user messages to detect rewording.
- _has_rejection scans explicit negative cues but ignores pure domain names (software engineering, psychology, etc).
- _is_rejection_after_response enforces the exact pattern user -> assistant -> user with rejection cues.
- _is_domain_selection recognizes a user selecting one of the six domain lenses.
- _is_clarification_refiner detects short clarifier phrases like "personal thinking" and merges them into the original question.
- _is_paradox_request matches contradiction patterns (explain without explaining, define without defining).
- _extract_final_content_and_type strips meta text and pulls code blocks when present, returning (content, type).

### Iteration and scoring
- Executor output is scored by Critic
- If score below threshold, Critic can suggest a revised prompt and re-run
- The best output is returned when thresholds are not met

### Clarifier vs Pathfinder vs Rejection intelligence
- needs_clarification is true if vagueness is high, LLM confidence is low for a question, or validation asks for clarification.
- If paradox is detected, clarification and pathfinder are both disabled.
- Rejection intelligence is triggered when explicit or implicit rejection is detected and the rephrase is not clearly better.
- Rejection returns a clarifier with domain lenses that are filtered for relevance, and includes hypotheses in metadata.
- Pathfinder is preferred for broad or underspecified requests, especially for new users with no preferences.

### Preference inference and detail level
- _infer_preferences scans recent messages for hints like academic, plain, examples, business impact, maximize quality.
- If academic preference is found, altitude is elevated to academic.
- detail_level becomes brief if the user asks for brevity or the tone is casual and complexity is low.
- detail_level becomes detailed if user asks for steps or if document_context is present.

### Code-only enforcement
- strict_code_only is true when sub_intents include wants_only_code or the user explicitly asks for only code.
- When strict_code_only is true, the executor prompt is prefixed with a hard rule to return only fenced code.

### Output
- Returns final_output (deliverable), optimized_prompt (planner output), and metadata
- Includes clarifier/pathfinder options and intent metadata when relevant

### Critic loop control
- should_skip_critic is true for casual low-complexity or simple question tasks, which returns a single executor pass.
- should_full_loop is true for production tasks with higher complexity or security signals.
- force_max_quality overrides skip and forces a longer loop with a high threshold (0.999).
- The loop tracks best_score and best_output, and returns the best output if thresholds are not reached.
- If the critic fails, the system either returns a paradox fallback or a clarifier about re-running.

## Backend: util.py (LLM, classifier, planner, critic)

### LLM selection (Gemini -> Groq -> Ollama)
- call_llm():
  1) Try Gemini (if GEMINI_API_KEY is set)
  2) Else try Groq (if GROQ_API_KEY is set)
  3) Else fallback to local Ollama

Why:
- Gemini is preferred for longer, higher-quality responses
- Groq is fast when configured
- Ollama provides local fallback if no API keys

### Video grounding helper
- get_video_context_via_search uses Gemini with google_search tool to summarize a video URL in 3 sentences.
- If Gemini errors, it returns a fixed fallback message.

### Classifier (LLM-0)
- classify_prompt builds a structured JSON classification:
  - type (code_request, question, generic, etc.)
  - sub_intents (prompt_optimization, wants_only_code, etc.)
  - confidence, vagueness, ambiguity
  - altitude (academic, production, etc.)
  - tone and context

- It calls the LLM, then normalizes fields.
- The output drives the workflow decisions in agents.py.

#### Classifier normalization details
- All numeric fields are clamped to 0.0 to 1.0 with defaults if missing.
- pathfinder_trigger and needs_clarification default to true when ambiguity is high.
- Consultative tone override sets conversation_tone to empathetic and forces clarifier for personal disclosure.
- Paradox detection adds sub_intents and disables clarification and pathfinder.

#### Heuristic ambiguity
- heuristic_ambiguity uses short length, broad terms, vague terms, and question marks.
- The heuristic is used as fallback when LLM output is missing or malformed.

#### Classifier decision logic (what triggers what)
- **Heuristic ambiguity**: short or broad prompts ("what is", "explain", "overview") raise ambiguity.
- **Prompt-optimization request**: if the *current* message contains both "optimiz" and "prompt", it tags `type=meta_instruction` and `sub_intents=[prompt_optimization]`, and disables clarifiers for that request.
- **Code task detection**: if the request mentions code-like verbs (write/implement/compute/check/return) plus math-ish terms (square, integer, numbers), it is forced to `code_request` even if the LLM labeled it generic/question.
- **Academic default for simple code**: short, low-complexity code requests default to `altitude=academic` to avoid overproduction features.
- **Consultative tone override**: if the user shares personal concerns or uncertainty, tone is forced to empathetic and clarifier is enabled.
- **Paradox detection**: contradictory prompts ("explain without explaining") are tagged with `paradox_prompt` and bypass clarifiers/pathfinder.

#### How "generic" vs "code_request" behaves
- If the request is clearly a code task (even if phrased casually), it becomes `code_request` and skips clarifiers.
- If it is genuinely broad or conceptual (e.g., "what is AI"), it stays generic/question and can trigger pathfinder.

### Planner (LLM-1)
- build_meta_instruction builds an optimized prompt from:
  - detected_type
  - altitude
  - sub_intents
  - conversation tone
  - document context and history

- It emits a single optimized prompt as plain text.

#### Two planner builders in util.py
- util.py defines build_meta_instruction twice. The later definition overrides the earlier one at runtime.
- The active planner builder (later definition) uses history injection, altitude/tone hints, and a global code/non-code policy block.
- The earlier definition is still in the file and may be legacy; only the last one is actually used.

#### Planner input fields (how each is produced)
- detected_type
  - Source: `classify_prompt()` in util.py.
  - The classifier LLM emits `type` (e.g., code_request, question, generic, academic_essay).
  - If the LLM output is missing or invalid, the system falls back to a heuristic ambiguity score and keeps `type=generic`.
  - This field controls which rubric block the planner inserts (code/academic/business/paradox).

- altitude
  - Source: `classify_prompt()` returns `altitude` (academic/production/enterprise/generic).
  - If the classifier doesn’t supply it, it defaults to `generic`.
  - In agents.py, if the user expresses academic preference (detected in recent history), altitude is elevated to `academic`.
  - This field adds altitude-specific tone hints to the planner prompt.

- sub_intents
  - Source: `classify_prompt()` returns a list of sub intents (wants_only_code, prompt_optimization, wants_comparison, paradox_prompt).
  - Agents can append sub intents (e.g., paradox_prompt) based on additional checks.
  - The planner includes these as SPECIAL CONSTRAINTS to force behavior (e.g., code-only output).

- conversation tone
  - Source: `classify_prompt()` returns `conversation_tone` (formal/casual/empathetic).
  - A consultative tone override triggers when the classifier detects personal concern/uncertainty.
  - Planner uses this to add empathetic/consultative rubric blocks.

- document context and history
  - History: last 4 messages are formatted into a short context block.
  - Document context: if the API request includes `document_context`, it is injected into the prompt with an explicit instruction to use it.
  - This ensures the optimizer and executor are aware of prior messages and any uploaded document content.

#### Planner prompt construction (exact behavior)
- Includes recent conversation history (last 4 messages) into a short context block.
- Builds a rubric block depending on `detected_type`:
  - code_request: clean, idiomatic code + error handling + best practices
  - academic_essay: formal tone + intro/body/conclusion
  - email/report: concise, professional, action-oriented
- Adds consultative rubric when tone is empathetic (validation, reassurance, red flags).
- Adds paradox rubric and paradox output format when `paradox_prompt` is present.
- Adds a SPECIAL CONSTRAINTS line if sub_intents exist.
- Forces the planner to output ONLY the optimized prompt (no meta-commentary).

#### Planner default code rules (current code)
- Always injects a generic code standards block for any code-related task:
  - Human-friendly input prompts
  - Basic error handling and edge cases
  - Readable variable names and a key inline comment
  - Sample output (bonus)
  - “Least time and space complexity”
  - “Shouldn’t make things complex”
  This is why even simple code questions can get extra I/O and validation unless the task is explicitly framed as function-only.

#### Planner history formatting helper
- _format_history_for_planner transforms message history into a single block with Role and Content, excluding the latest user message.
- That history is inserted into the combined target_code context for the planner.

#### Professionalization helper
- _professionalize_outcome_phrase rewrites "shortlist" phrasing into a more formal target outcome, and varies it by detected_type.

### Executor (LLM-2) - Final Output
- Runs the optimized prompt with strict output rules.
- If document context is provided, it must be used.
- Uses detail-level controls (brief, standard, detailed).

#### Executor prompt rules (exact behavior)
- Injects document context under a DOCUMENT REFERENCE block when present.
- Adds strict output rules:
  - Output ONLY the deliverable
  - No explanations, no analysis
  - If code: fenced code block only
  - No numbered lists after deliverable
- Adds brief/detailed detail rules based on detail_level.

### Critic (LLM-3)
- critic_evaluate compares final output against original user task.
- It uses additional rubrics for academic or paradox tasks.
- Returns a score and optionally a revised prompt.

#### Critic prompt details (exact behavior)
- Always compares FINAL OUTPUT to ORIGINAL USER TASK.
- Adds academic rubric when altitude is academic.
- Adds paradox rubric for paradox tasks.
- Returns JSON: score, suggested_prompt, role, comments.
- If critic fails or returns 0.0, the system falls back to clarifier or paradox fallback.

#### Critic academic and paradox rubrics
- Academic rubric demands formal definition, contrast with adjacent concepts, objective, domain examples, and limitations.
- Paradox rubric rewards indirect explanation and penalizes explicit definitions or step lists.

## Backend: auth.py

- Uses JWT (HS256) with SECRET_KEY from env.
- get_current_user decodes token and fetches user from DB.
- get_user_by_email reads client_credentials and normalizes JSONB fields.

### JWT specifics
- SECRET_KEY is required and validated at import time; the service refuses to start with a placeholder.
- ACCESS_TOKEN_EXPIRE_MINUTES is set to 8 hours.
- create_access_token injects exp and signs with HS256.

## Backend: key_management.py

- Password hashing with argon2
- register_new_user inserts client_credentials and initial API key
- authenticate_user verifies password and returns user profile
- validate_api_key validates Bearer token via api_keys table
- increment_usage_count updates usage_tracking and usage_limits JSONB
- update_clarifier_fatigue increments or decrements clarifier_count_last_5
- update_last_request_types appends last request types to JSONB list
- get_silent_misalignment_rate computes misalignment rate from usage_tracking

### Internal helpers
- generate_raw_api_key uses a relevo_sk_ prefix and secrets.token_hex.
- generate_api_key_hash uses SHA-256 for storage and comparisons.

### Usage tracking details
- increment_usage_count writes to usage_tracking and mirrors counts into usage_limits JSONB for backward compatibility.
- update_last_request_types appends to last_5_request_types and trims to the last 5.
- update_clarifier_fatigue applies a bounded delta using GREATEST to avoid negative counts.

## Backend: database.py

- Creates asyncpg pool and core tables if missing:
  - client_credentials
  - api_keys
  - usage_tracking
  - billing_plans
  - invoices
- Adds indexes for usage and billing queries

### Connection retry behavior
- startup_db_pool retries up to 5 times with exponential backoff starting at 2 seconds.
- A TypeError in create_pool arguments is treated as a fatal coding error (no retries).
- The pool uses min_size=10, max_size=30, command_timeout=60, timeout=30.

### Schema details
- client_credentials includes usage_limits JSONB and plan_limit.
- usage_tracking stores client_id as text and per-request counts with cost_usd.
- billing_plans and invoices are separate tables with timestamps and statuses.

## Backend: file_upload_endpoints.py

- Helper implementations for PDF/video upload
- main.py uses a built-in PDF upload route with PyPDF2

### PDF helper behavior
- upload_pdf validates auth, file size (10 MB), and content_type.
- It reads all pages with PyPDF2 and returns extracted_text capped at 50k characters.
- It returns an explicit note telling callers to use extracted_text as document_context.

### Video helper behavior
- upload_video saves the file to backend/uploads with a UUID filename.
- It returns a video_ref_url intended for later retrieval by get_video.
- get_video enforces auth and returns a FileResponse with a guessed mime type.

## Backend: wsgi.py

- Gunicorn entry for production, imports main.app

## Backend: db/generator.py (admin utility)

- Standalone CLI script to generate a client API key and store its hash.
- generate_random_key uses a client-specific prefix and token_urlsafe(32).
- hash_key uses SHA-256; it matches the auth hash scheme.
- create_new_client_key inserts into client_credentials with client_id and api_key_hash.
- It is designed for one-off admin use and requires DATABASE_URL.

## Frontend Overview

Frontend is a React app (Vite) with routes:
- /login, /register (public)
- /dashboard, /chat, /usage, /billing (protected)

Key files:
- frontend/src/App.jsx: routing
- frontend/src/main.jsx: React root
- frontend/src/services/api.js: API calls for JWT or API key
- frontend/src/components/*: auth, chat UI, prompt display
- frontend/src/pages/*: screens for auth, chat, usage, billing

## Frontend: Auth and API

### AuthProvider.jsx
- Stores JWT in localStorage
- Sets axios default Authorization header
- refreshUser calls /auth/me
- Interceptor logs out on 401

### services/api.js
- registerClient: /auth/register
- generateContent: /generate (JWT)
- generateWithApiKey: /api/v1/generate-prompt

## Frontend: Chat experience

### ChatWindow.jsx
- Renders messages with role labels and styles
- Shows optimized prompt preview and full prompt toggle
- Displays clarifier/pathfinder options and allows selection
- Shows continuation prompt for low-quality outputs

### HistoryPanel.jsx
- Holds document context text
- Allows PDF upload
- Sets max iteration count

### TextInput.jsx
- Text input + send button
- Handles Enter key and loading state

## Frontend: Pages

- LoginPage/RegisterPage: Auth flow, create or log in
- DashboardPage: API key generation, usage stats, VIP status
- ChatPage/UsagePage/BillingPage/NotFoundPage: route containers and content

## Client Example

client.py shows a Streamlit demo that:
- Sends chat messages to /api/v1/generate-prompt
- Displays final_output and quality score

## How Groq and Ollama are used

- If GEMINI_API_KEY is set: Gemini is used first.
- Else if GROQ_API_KEY is set: Groq is used for both planner and executor.
- Else Ollama is used as the local fallback.

This applies to all LLM calls in the workflow (Classifier, Planner, Executor, Critic).
