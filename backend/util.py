# util.py (Modified to include abstract_task for the Critic)

import time
import asyncio
import os
import json
import requests
import re
from typing import Dict, Any, List, Optional

# --- Configuration for Hybrid LLM Agent ---

# Groq Configuration (High Speed Mode)
GROQ_MODEL: str = "moonshotai/kimi-k2-instruct-0905"
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
HIGH_SPEED_MODE: bool = bool(GROQ_API_KEY)

# Ollama Configuration (Local Fallback)
OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3")

# Gemini API (video grounding) — set via environment for security
GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# ==========================================================
# ======== PATHFINDER PROMPT BUILDER =======================
# ==========================================================

def build_pathfinder_prompt(abstract_task: str, confidence: float, hidden_goal: Optional[str] = None) -> str:
    """
    Builds a concise, scenario-aware follow-up that helps the user choose a direction
    before we proceed. Returns a plain string intended for immediate display.

    The options are tailored but kept lightweight to avoid analysis paralysis.
    """
    task = (abstract_task or "").strip().lower()
    base_note = "This seems broad. To give the best answer, please choose a focus."

    if re.search(r"\b(what is|define|explain|overview)\b", task):
        options = [
            "plain overview",
            "academic definition",
            "business impact",
            "examples",
            "maximize quality",
        ]
        msg = (
            f"{base_note} Choose one: plain overview, academic definition, business impact, examples, or maximize quality."
        )
    elif re.search(r"\b(how to|steps|guide)\b", task):
        options = ["quick steps", "detailed guide", "best practices", "maximize quality"]
        msg = "Prefer quick steps, a detailed guide, best practices, or maximize quality?"
    elif re.search(r"\b(compare|vs|difference)\b", task):
        options = ["features", "performance", "cost", "use cases", "maximize quality"]
        msg = "Compare by features, performance, cost, use cases, or maximize quality?"
    elif re.search(r"\b(write|draft|email|report|code)\b", task):
        options = ["email", "report", "code", "summary", "maximize quality"]
        msg = "What deliverable should I produce: email, report, code, summary, or maximize quality?"
    else:
        options = ["plain overview", "academic definition", "examples", "business impact", "maximize quality"]
        msg = "Choose a focus: plain overview, academic definition, examples, business impact, or maximize quality."

    hint = "Reply with exactly one option to proceed."
    if hidden_goal:
        hint += f" (Noted hidden goal: {hidden_goal})"
    return f"{msg} {hint}"


# ==========================================================
# ======== META-INSTRUCTION BUILDER (LLM-1 PLANNER) =======
# ==========================================================

def build_meta_instruction(
    task_description: str,
    target_code: str,
    full_context_history: List[Dict[str, Any]],
    detected_type: Optional[str] = None,
    sub_intents: Optional[List[str]] = None,
    altitude: str = "generic",
    conversation_tone: str = "formal",
    user_context: str = "general"
) -> str:
    """
    LLM-1: Builds a comprehensive meta-instruction for the Planner.
    Encodes task type, tone, altitude, and constraints into the prompt.
    """
    # Build conversation context
    context_lines = []
    for msg in full_context_history[-4:]:  # Last 4 messages for conciseness
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:200]  # Truncate for brevity
        context_lines.append(f"{role}: {content}")
    
    conversation_context = "\n".join(context_lines) if context_lines else "Fresh conversation"
    
    # Build rubric based on detected type
    rubric = ""
    if detected_type == "code_request":
        rubric = "\nRUBRIC (Code):\n- Provide clean, idiomatic, well-commented code\n- Include error handling\n- Use best practices for the language"
    elif detected_type == "academic_essay":
        rubric = "\nRUBRIC (Academic):\n- Use formal tone\n- Cite concepts with precision\n- Structure clearly: intro, body, conclusion"
    elif detected_type in ["email", "report"]:
        rubric = "\nRUBRIC (Business):\n- Be concise and professional\n- Action-oriented\n- Clear call-to-action if needed"
    
    # Build sub-intent enforcement
    sub_intent_msg = ""
    if sub_intents:
        sub_intent_msg = f"\nSPECIAL CONSTRAINTS: {', '.join(sub_intents)}"
    
    meta_instruction = f"""You are a professional prompt optimizer. Your task is to improve and refine the user's original request into a perfectly clear, actionable prompt for an AI model.

ORIGINAL REQUEST:
{task_description}

CONTEXT:
- Conversation History: {conversation_context}
- Detected Intent: {detected_type or 'generic'}
- Conversation Tone: {conversation_tone}
- Cognitive Altitude: {altitude}
- User Context: {user_context}

EXTERNAL CONTEXT (if provided):
{target_code if target_code else '(None)'}

YOUR TASK:
1. Identify the core intent and any hidden requirements
2. Refine the request for maximum clarity and actionability
3. If EXTERNAL CONTEXT (documents/videos) is provided above, EXPLICITLY instruct the AI to reference and use that specific content in the response
4. Ensure completeness without over-specification
5. Adapt tone to match: {conversation_tone}
6. Output ONLY the optimized prompt (no meta-commentary)

{rubric}
{sub_intent_msg}

OPTIMIZED PROMPT:"""
    
    return meta_instruction.strip()


# ======== OLLAMA CALL ========

async def _ollama_generate(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        # Use asyncio.to_thread for synchronous requests call
        response = await asyncio.to_thread(
            requests.post, OLLAMA_URL, headers=headers, json=payload, timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip() or "Error: Ollama returned empty response."
    except Exception as e:
        return f"Error: Failed to connect to Ollama: {str(e)}"


# ======== GEMINI / GROQ / OLLAMA HYBRID CALL ========

async def call_llm_with_gemini(prompt_to_send: str, is_meta_prompt: bool = True) -> str:
    """Call Gemini API with better long-form response handling."""
    if not GEMINI_API_KEY:
        return None  # Fallback to other methods
    
    max_output_tokens = 4000 if not is_meta_prompt else 2000
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_to_send}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": max_output_tokens,
        }
    }
    
    headers = {"Content-Type": "application/json"}
    gemini_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    
    for attempt in range(2):
        try:
            response = await asyncio.to_thread(
                requests.post, gemini_url, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0].get("content", {}).get("parts", [])
                if content and len(content) > 0:
                    return content[0].get("text", "").strip()
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            else:
                break
    
    return None

async def call_llm(prompt_to_send: str, is_meta_prompt: bool = True) -> str:
    """Unified LLM call with Gemini -> Groq -> Ollama."""
    max_tokens = 900 if is_meta_prompt else 4000  # Extended max for better long-form response

    # 1. Try Gemini first (best for long-form responses and quality)
    gemini_result = await call_llm_with_gemini(prompt_to_send, is_meta_prompt)
    if gemini_result:
        return gemini_result
    
    # 2. Fallback to Groq if Gemini unavailable
    if HIGH_SPEED_MODE:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt_to_send}],
            "temperature": 0.1,
            "stream": False,
            "max_tokens": max_tokens,
        }

        for attempt in range(2):
            try:
                response = await asyncio.to_thread(
                    requests.post, url, headers=headers, json=payload, timeout=45
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            except Exception:
                if attempt == 0:
                    await asyncio.sleep(2)

    # 3. Final fallback to Ollama
    return await _ollama_generate(prompt_to_send)


# ======== VIDEO GROUNDING USING GEMINI ========

async def get_video_context_via_search(video_url: str) -> str:
    system_prompt = (
        "You are a Video Content Analyst. Use search to identify the video's topic. "
        "Answer in 3 sentences. If nothing is found, reply: 'Video content could not be determined.'"
    )

    payload = {
        "contents": [{"parts": [{"text": f"Summarize the content for: {video_url}"}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    headers = {"Content-Type": "application/json"}

    try:
        # Use asyncio.to_thread for synchronous requests call
        response = await asyncio.to_thread(
            requests.post, GEMINI_API_URL, headers=headers, json=payload, timeout=45
        )
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return content.strip()
    except Exception:
        return "Video content could not be determined."


# ==========================================================
# ======== CLASSIFIER (LLM-0) (UPDATED SIGNATURE) ==========
# ==========================================================

async def classify_prompt(
    user_prompt: str,
    full_context_history: List[Dict[str, Any]] # NEW: Added argument to match agents.py call
) -> Dict[str, Any]:
    """
    LLM-0: Classifies the user's intent to apply specific meta-instructions.
    
    NOTE: While the function now accepts history, we'll keep the prompt simple 
    for now and primarily use it in the Planner for full context.
    """
    # Build a simple history string to include in the classifier prompt
    # Exclude the last message (the current prompt)
    history_string = ""
    if len(full_context_history) > 1:
        history_string = "\n".join([f"({m['role']}): {m['content']}" for m in full_context_history[:-1]])
        history_string = f"PREVIOUS CONTEXT:\n---\n{history_string}\n---\n"

    classifier_prompt = f"""
You are a Prompt Classifier. Analyze the user's instruction and categorize it.
Return ONLY a single, valid JSON object, strictly following this schema:

{{
    "type": "string", // One of: "code_request", "website_request", "software_task", "academic_essay", "personal_advice", "daily_advice", "meta_instruction", "generic", "data_analysis", "other"
    "sub_intents": ["string"], // Examples: "wants_only_code", "needs_firestore", "needs_tailwind", "wants_plagiarism_free", "wants_comparison"
    "confidence": "float", // Confidence score between 0.0 and 1.0
    "reason": "string" // Brief explanation for the classification
}}

{history_string}
USER INSTRUCTION: {user_prompt}
"""
    try:
        raw = await call_llm(classifier_prompt, is_meta_prompt=True)
        # Find the JSON object in the raw response
        json_start = raw.find("{")
        json_text = raw[json_start:]
        return json.loads(json_text)
    except Exception:
        return {"type": "generic", "sub_intents": [], "confidence": 0.5, "reason": "Classification failed"}


# ==========================================================
# ======== CRITIC (LLM-3) (MODIFIED SIGNATURE AND PROMPT) ==
# ==========================================================

async def critic_evaluate(
    original_task: str,  # User's initial instruction
    optimized_prompt: str,
    executor_output: str,
    detected_altitude: Optional[str] = None,
    conversation_tone: Optional[str] = None,
    burnout_signal: Optional[float] = None,
    sincerity_polarity: Optional[str] = None,
    intelligence_altitude: Optional[str] = None,
    hidden_goal: Optional[str] = None,
    iteration: Optional[int] = None
) -> Dict[str, Any]:
    """
    LLM-3: Compares the output against the original intent for quality control.
    The prompt is updated to explicitly include the original task for better compliance checking.
    """
    # Lightly include multi-dimensional context for more reliable scoring
    context_meta = []
    if detected_altitude:
        context_meta.append(f"Altitude: {detected_altitude}")
    if conversation_tone:
        context_meta.append(f"Tone: {conversation_tone}")
    if sincerity_polarity:
        context_meta.append(f"Sincerity: {sincerity_polarity}")
    if intelligence_altitude:
        context_meta.append(f"Intelligence Altitude: {intelligence_altitude}")
    if hidden_goal:
        context_meta.append(f"Hidden Goal: {hidden_goal}")
    if burnout_signal is not None:
        context_meta.append(f"Burnout Signal: {burnout_signal:.2f}")
    if iteration is not None:
        context_meta.append(f"Iteration: {iteration}")

    meta_header = ("\n".join(context_meta)).strip()

    # Academic rubric (conditional)
    academic_rubric = ""
    if (detected_altitude or "").lower() == "academic":
        academic_rubric = (
            "\n\nACADEMIC RUBRIC (apply when answering academically):\n"
            "- Provide a precise formal definition (use notation where appropriate).\n"
            "- Distinguish clearly from adjacent concepts (e.g., ML vs AI vs rule-based).\n"
            "- Mention core objective (risk minimization / generalization) succinctly.\n"
            "- Note assumptions or limitations briefly (no lengthy discourse).\n"
            "- Include representative domains or architectures if relevant (1 short sentence).\n"
        )

    critic_prompt = f"""
You are the Critic Agent. Compare the optimized prompt and the final output with the ORIGINAL USER TASK.
Your goal is to score the output for:
1.  **Completeness:** Does it cover all requirements, including derived (inferred) intent?
2.  **Conciseness:** Is the final output as direct and brief as possible while being complete?
3.  **Accuracy/Compliance:** Is the content/code correct, and does it strictly adhere to all explicit constraints (e.g., character count, specific format, required elements) from the ORIGINAL USER TASK?
{academic_rubric}

Return ONLY a single, valid JSON object, strictly following this schema:

{{
    "score": "float", // Score between 0.0 (Failed) and 1.0 (Perfect). A score < 0.8 triggers a re-try.
    "suggested_prompt": "string", // If score < 0.8, provide a new optimized prompt to fix the issue. Otherwise, keep it the same.
    "role": "string", // e.g., "Critic-Pass", "Critic-Fail"
    "comments": "string" // Brief critique of the output, specifically noting any missed explicit constraints.
}}

{('CONTEXT META:\n' + meta_header + '\n') if meta_header else ''}
ORIGINAL USER TASK: {original_task}
OPTIMIZED PROMPT USED: {optimized_prompt}
FINAL OUTPUT RECEIVED: {executor_output}
"""

    full_prompt = critic_prompt

    try:
        raw = await call_llm(full_prompt, is_meta_prompt=True)
        # Find the JSON object in the raw response
        json_start = raw.find("{")
        json_text = raw[json_start:]
        return json.loads(json_text)
    except Exception:
        # Return a low score to trigger a safe fallback or re-try
        return {"score": 0.0, "suggested_prompt": optimized_prompt, "role": "Critic-Error", "comments": "Critic function failed to process response."}


# ==========================================================
# ======== CORE META-INSTRUCTION (PLANNER) =================
# ==========================================================

def _professionalize_outcome_phrase(phrase: str, detected_type: Optional[str]) -> str:
    low = phrase.lower()
    if "shortlist" in low or "selected" in low:
        if detected_type and detected_type.startswith("code"):
            return "Ensure the solution is competitive and suitable for technical shortlisting."
        if detected_type in ["daily_advice", "personal_advice"]:
            return "Ensure the guidance supports preparation for competitive shortlisting."
        if detected_type in ["website_request", "software_task"]:
            return "Ensure the deliverable is polished and competitive for selection reviews."
        return "Ensure the output meets standards appropriate for competitive shortlisting."
    return phrase

def _format_history_for_planner(history: List[Dict[str, Any]]) -> str:
    """Converts the message list history into a single string for the Planner LLM."""
    if len(history) <= 1:
        return "" # No history to provide beyond the current task
        
    # Exclude the last message, which is the current task already in 'task_description'
    history_string = "\n".join([f"Role: {m['role'].capitalize()}\nContent: {m['content']}" for m in history[:-1]])
    return f"PREVIOUS CONVERSATION HISTORY:\n---\n{history_string}\n---"


def build_meta_instruction(
    task_description: str,
    target_code: str,
    full_context_history: List[Dict[str, Any]], # NEW: Added history argument
    detected_type: Optional[str] = None,
    sub_intents: Optional[List[str]] = None,
    altitude: Optional[str] = None,
    conversation_tone: Optional[str] = None,
    user_context: Optional[str] = None,
) -> str:
    """
    LLM-1: Planner. Builds the meta-instruction for the Executor.
    This function now integrates conversation history for statefulness.
    """
    detected_type = detected_type or "generic"
    sub_intents = sub_intents or []
    altitude = altitude or "generic"
    conversation_tone = conversation_tone or "formal"
    user_context = user_context or "general"

    # Inject History into the context string
    history_context = _format_history_for_planner(full_context_history)

    preserve = []
    if "shortlist" in task_description.lower():
        preserve.append(
            _professionalize_outcome_phrase("help me get shortlisted", detected_type)
        )

    # TYPE-AWARE GUIDANCE
    type_hint = ""
    if detected_type.startswith("code"):
        type_hint = (
            "Prioritize correctness, low time/space complexity, and originality. "
            "Return only code when explicitly required."
        )
    elif detected_type in ["daily_advice", "personal_advice"]:
        type_hint = (
            "Provide clear, practical, realistic suggestions tailored to the user's goals."
        )
    elif detected_type in ["website_request", "software_task"]:
        type_hint = (
            "Favor modern UI/UX, responsive design (using Tailwind CSS classes if applicable), and professionalism. "
            "The optimized prompt should prioritize features that can be implemented in a single, front-end file "
            "(HTML/CSS/JS/React/Angular) to maximize the utility of the first output. Avoid introducing complex external dependencies unless necessary."
        )
    elif detected_type == "meta_instruction":
        type_hint = "Preserve the user's intent exactly; clarify but never alter meaning."

    # ALTITUDE/TONE/CONTEXT HINTS (light-touch defaults to avoid breaking behavior)
    altitude_hint = ""
    if altitude in ["production", "enterprise"]:
        altitude_hint = (
            "Ensure auditability and explicit deliverables. Prefer structured, scannable outputs, "
            "state decisions and action items clearly, and avoid informal commentary."
        )
    elif altitude in ["academic"]:
        altitude_hint = (
            "Use precise terminology and briefly state assumptions. "
            "For academic answers, include: a formal definition (notation acceptable), a concise distinction from adjacent concepts, "
            "the core objective (risk minimization/generalization), one sentence on representative domains/architectures, and a short note on limitations."
        )

    tone_hint = ""
    if conversation_tone == "casual":
        tone_hint = "Use a clear, friendly tone; avoid overly formal phrasing."
    elif conversation_tone == "formal":
        tone_hint = "Use a neutral, professional tone and concise language."

    user_context_hint = ""
    if user_context and user_context != "general":
        user_context_hint = f"Tailor the prompt to the user's context: {user_context}."

    # SUB-INTENTS
    sub_hint = []
    if "wants_only_code" in sub_intents:
        sub_hint.append("The response must contain only the final code.")
    if "wants_plagiarism_free" in sub_intents:
        sub_hint.append("Ensure originality and avoid copied content.")

    # MAIN GUIDANCE TEXT (Neutral Professional Tone)
    guidance = [
        "Rewrite the user's request into a single clear, professional prompt that any AI model can understand perfectly.",
        "Do not change or weaken ANY explicit requirement.",
        "Professionally restate outcome goals (such as competing for shortlisting) in a suitable tone.",
        # --- CRITICAL GENERALIZED INTELLIGENCE INSTRUCTION ---
        "**CRITICAL:** The optimized prompt MUST demonstrate high common-sense intelligence and deep user intent understanding. When the original task is minimal or vague, the prompt must infer and include necessary, professional-grade features (the Minimal Viable Product) that are implicitly required by context. This means always prioritizing user-centric design, security (if data is sensitive), robust error handling, and high-quality aesthetics/presentation.",
        type_hint,
        altitude_hint,
        tone_hint,
        user_context_hint,
    ]

    if preserve:
        guidance.append("Include this requirement: " + "; ".join(preserve))
    if sub_hint:
        guidance.append("Also enforce: " + "; ".join(sub_hint))

    final_instruction = " ".join([g for g in guidance if g])

    # Combine History and other context into target_code
    combined_target_code = target_code
    if history_context:
        combined_target_code = f"{history_context}\n\nEXTERNAL CONTEXT:\n{target_code}"

    return f"""
{final_instruction}
You are a Universal Optimization Agent.
Rewrite the user's request so any AI assistant delivers a result that is simple, clear, and maximally user-friendly.

- For any code-related tasks, your optimized prompt MUST require:
  - Readable code with docstrings (or header comment) summarizing the overall logic.
  - Human-friendly prompt for user input (not raw 'n: ', but e.g. 'Enter N:')
  - Basic error handling for bad/edge-case input (e.g. ValueError, negative, empty)
  - Output that is easy to read and understand even for non-experts (e.g. 'The square of 7 is: 49')
  - Clean, logical variable names, and at least one inline comment explaining the key part.
  - (Bonus) Show a sample output for illustration if helpful.

- For any non-code/general tasks, ALWAYS demand:
  - Clear explanation (as a comment, docstring, or short intro)
  - If advice/instructions, steps must be actionable and immediately usable by most people
  - Never sacrifice clarity, context, or user understanding just for brevity.

**Addition:** Before formatting your answer, always pause to reflect on the user’s actual intent and context:
- If code or technical output is specifically warranted or obviously the best fit, provide it as described above.
- If the prompt is open-ended, general, or only about advice, respond only in human language—clear, actionable statements, not code or technical logic—unless the user’s intent or context changes.
- Use professional judgement, not keyword triggers, to ensure the answer feels natural and goal-oriented for the specific user and their likely scenario.
- If unsure, briefly clarify or offer a menu of helpful next actions instead of assuming their intent.

All output must be the *optimized prompt only*—no meta, no explanations, just the thing to send to the next assistant, which is concise and precise.


Produce a single natural-language optimized prompt (1–2 paragraphs, neutral professional tone)
that ensures ANY AI model can provide the exact correct output in one attempt.

TASK: {task_description}
CONTEXT: {combined_target_code}
""".strip()