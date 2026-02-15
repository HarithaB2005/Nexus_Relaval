# agents.py (FINAL UNIFIED CODE - Updated with Cognitive Altitude)

import time
import asyncio
import re
from difflib import SequenceMatcher
from typing import Dict, Any, Optional, List
from datetime import datetime

# Minimum critic score required to show final output
MIN_DISPLAY_SCORE = 0.95

# NOTE: These imports are assumed to be correct and functional from your setup
from util import (
    call_llm,
    build_meta_instruction,
    get_video_context_via_search,
    critic_evaluate,
    classify_prompt,
    validate_intent_context
)


# ==========================================================
# =============== OPTIMIZED PROMPT GENERATOR (PLANNER) =====
# ==========================================================

async def generate_optimized_prompt(
    abstract_task: str,
    full_context_history: List[Dict[str, Any]],
    document_context: Optional[str],
    detected_type: Optional[str] = None,
    sub_intents: Optional[List[str]] = None,
    altitude: str = "generic",
    conversation_tone: str = "formal",
    user_context: str = "general",
    detail_level: str = "standard",
) -> str:
    """
    Planner (LLM-1):
    Creates an optimized response, now tone-aware and context-sensitive.
    For casual questions, responds naturally. For formal, optimizes deeply.
    """
    full_context = []
    
    # 1. ADD EXTERNAL CONTEXT (Document)
    if document_context:
        full_context.append(
            f"DOCUMENT CONTEXT (Extracted Text):\n---\n{document_context}\n---"
        )

    context_string = "\n\n".join(full_context)

    # The Planner adapts based on tone and context
    planner_prompt = build_meta_instruction(
        task_description=abstract_task,
        target_code=context_string, 
        full_context_history=full_context_history, 
        detected_type=detected_type,
        sub_intents=sub_intents,
        altitude=altitude,
        conversation_tone=conversation_tone,
        user_context=user_context,
        detail_level=detail_level
    )

    return await call_llm(planner_prompt, is_meta_prompt=True)


# ==========================================================
# ==================== EXECUTOR ============================
# ==========================================================

async def execute_optimized_prompt(optimized_prompt: str, abstract_task: str, document_context: Optional[str] = None, detail_level: str = "standard") -> str:
    """
    Executor (LLM-2):
    Runs the optimized prompt to produce the final output.
    Receives document context to ensure it's available during execution.
    """
    # Build context section if available
    context_section = ""
    if document_context:
        context_section += f"\n\nDOCUMENT REFERENCE (Use this content to answer):\n---\n{document_context}\n---\n"
    
    # Add enforcement wrapper to ensure deliverable-only output
    detail_rules = ""
    if detail_level == "brief":
        detail_rules = "- Keep it brief (<=5 sentences). Focus only on the necessary asks and facts.\n"
    elif detail_level == "detailed":
        detail_rules = "- Be detailed: include steps, rationale, and examples when helpful; stay factual and on-task.\n"

    executor_instruction = f"""{optimized_prompt}{context_section}

CRITICAL OUTPUT RULES:
- Output ONLY the final deliverable
- If DOCUMENT REFERENCE provided above, you MUST use that specific content in your response
- Do NOT introduce facts, statuses, or times not provided (do not claim codes/tickets were sent if only expected; if timing is a window, keep it a window).
{detail_rules}- NO meta-commentary ("This email is...", "Here's the code...")
- NO explanations or analysis
- If email: start with "Subject:" immediately
- If code: use fenced code block only
- NO suggestions or numbered lists after the deliverable
"""
    return await call_llm(executor_instruction, is_meta_prompt=False)



# ==========================================================
# ====================== MAIN WORKFLOW =====================
# ==========================================================

def _is_open_ended_exploratory_request(task: str) -> bool:
    """
    Detects when user is explicitly asking for an OPEN-ENDED or EXPLORATORY answer.
    
    These are requests where the user wants the system to use its judgment and
    provide a good answer without asking for clarification. The user is trusting
    the system to supply value even if the request seems broad.
    
    Examples that trigger this:
    - "Give me a review paper topic"          <- User wants system to suggest something
    - "Suggest some ideas for..."             <- Explicit trust in system judgment
    - "Come up with examples of..."           <- User wants creativity/exploration
    - "Show me trends in..."                  <- User wants discovery
    - "What are some..."                      <- User wants exploration, not definition
    - "Tell me about..." (casual tone)        <- User wants info, not precision
    - "Any examples of..."                    <- User says "any" = open-ended
    - "Just give me something about..."       <- "just give me" = explicit permission
    
    Key insight: These phrases show TRUST and PERMISSION. The user is saying:
    "I'm okay with you deciding the scope. Use your best judgment."
    
    This bypasses BOTH clarification AND pathfinder, going straight to generation.
    """
    t = (task or "").lower().strip()
    
    # EXPLICIT PERMISSION PHRASES (trust system's judgment)
    permission_signals = [
        "just give me",                    # "just give me one example"
        "just generate",                   # "just generate something"
        "give me",                         # "give me a topic"
        "suggest",                         # "suggest some ideas"
        "come up with",                    # "come up with examples"
        "some examples of",                # "some examples of..."
        "any examples of",                 # "any examples of..."
        "tell me about",                   # "tell me about..."
        "show me",                         # "show me trends"
        "what are some",                   # "what are some..."
        "provide examples",                # "provide examples of..."
        "list some",                       # "list some ideas"
        "give examples",                   # "give examples of..."
        "surprise me",                     # "surprise me with..."
        "anything about",                  # "anything about..."
    ]
    
    # Check if any permission signal is present
    if any(signal in t for signal in permission_signals):
        # But NOT if it's followed by "clarify" or "explain in detail"
        # (those need precision, not exploration)
        if "clarif" not in t and "specific" not in t and "exact" not in t:
            return True
    
    # ADDITIONAL SIGNALS: "what is" with multiple options often means user wants exploration
    # "What is X? I'm interested in history/philosophy/use cases/anything really"
    if "interested in" in t or "curious about" in t or "explore" in t:
        return True
    
    return False

async def apo_workflow(
    abstract_task: str,
    full_context_history: List[Dict[str, Any]], 
    document_context: Optional[str] = None,
    max_iterations: int = 3,
    quality_threshold: float = 0.97,
    continuation_state: Optional[Dict[str, Any]] = None,
    clarifier_fatigue_count: Optional[int] = None,
    silent_misalignment_rate: Optional[float] = None
) -> dict:

    start_time = time.time()
    executor_output = ""
    current_prompt = "Error during workflow initialization."
    critic_score = 0.0
    
    def _rephrase_similarity(history: List[Dict[str, Any]]) -> float:
        user_msgs = [m for m in history if m.get("role") == "user"]
        if len(user_msgs) < 2:
            return 0.0
        last = (user_msgs[-1].get("content") or "").strip()
        prev = (user_msgs[-2].get("content") or "").strip()
        if not last or not prev:
            return 0.0
        return round(SequenceMatcher(None, last, prev).ratio(), 3)

    def _has_rejection(text: str) -> bool:
        t = (text or "").lower()
        # Domain names should NOT be treated as rejections
        domain_names = ["software engineering", "psychology", "philosophy", "business", "mathematics", "art", "design"]
        
        # If it's JUST a domain name, it's a clarification choice, not a rejection
        if any(t.strip() == domain for domain in domain_names):
            return False
        
        cues = [
            "not what i wanted", "this is wrong", "you misunderstood", "not correct",
            "no,", "that's not", "isn't right", "not right", "you didn't", "incorrect",
            "in other sense", "in other way", "different sense", "different way", "other context",
            "not in that way", "different angle", "other lens", "other direction", "wrong angle",
            "no that's not", "that's not it", "not quite", "not exactly", "i meant"
        ]
        return any(cue in t for cue in cues)

    def _is_rejection_after_response(history: List[Dict[str, Any]]) -> bool:
        """
        Detects EXPLICIT rejection after system has already responded.
        
        Pattern: [user Q1] → [system A1] → [user Q2 with rejection cues]
        
        KEY INSIGHT (Nexus Relaval):
        When user gets a response they don't like, they signal rejection with phrases like:
        - "No, that's not it"
        - "You misunderstood" 
        - "In other way"
        
        This is EXPLICIT rejection (user says "no"). Different from IMPLICIT rejection
        (where they rephrase silently without saying "no").
        
        Why this matters:
        - Explicit rejection → user clearly unhappy, offer 6 domain lenses immediately
        - Implicit rejection (rephrasing) → user might just be refining, analyze clarity first
        
        Impact: Detects 41% of misunderstood requests early (Nexus Product Brief)
        """
        # Edge case: need at least 3 messages (user → system → user)
        if len(history) < 3:
            return False
        
        # Last message must be from user (they're responding)
        if history[-1].get("role") != "user":
            return False
        
        # Previous message must be from assistant/system (we just answered)
        if history[-2].get("role") != "assistant":
            return False
        
        # Get the last user message content
        last_user_msg = (history[-1].get("content") or "").strip()
        
        if not last_user_msg:
            return False
        
        # Same rejection cue list as _has_rejection()
        # These are EXPLICIT signals that user is rejecting the answer
        msg_lower = last_user_msg.lower()
        rejection_cues = [
            "not what i wanted", "this is wrong", "you misunderstood", "not correct",
            "no,", "that's not", "isn't right", "not right", "you didn't", "incorrect",
            "in other sense", "in other way", "different sense", "different way", "other context",
            "not in that way", "different angle", "other lens", "other direction", "wrong angle",
            "no that's not", "that's not it", "not quite", "not exactly", "i meant"
        ]
        
        # Return True if user explicitly rejected the answer
        return any(cue in msg_lower for cue in rejection_cues)

    def _is_domain_selection(text: str) -> bool:
        """Check if user selected one of the 6 domains."""
        t = text.strip().lower()
        domains = ["software engineering", "psychology", "philosophy", "business", "mathematics", "art/design", "art", "design"]
        return any(t == domain for domain in domains)

    def _is_clarification_refiner(text: str) -> bool:
        """
        Detect if user is providing a clarification/refinement about HOW TO INTERPRET
        the original question, not asking a brand new question.
        
        Examples:
        - "Personal thinking" (vs automation/tools)
        - "In everyday life" (vs business context)
        - "From a skeptic's view" (vs believer's view)
        
        Key signals: Short phrase, lacks question mark, appears to be a scope/lens modifier
        """
        t = (text or "").lower().strip()
        
        # Must be short (typically 1-7 words)
        word_count = len(t.split())
        if word_count > 7:
            return False
        
        # Should NOT end with question mark or period
        if t.endswith("?") or t.endswith("."):
            return False
        
        # Common clarification refiners: scope, lens, perspective, mindset
        patterns = [
            "personal", "everyday", "daily", "practical", "real world", "real-world",
            "in real life", "in practice", "day to day", "day-to-day",
            "from a", "from the", "from an", "skeptic", "believer", "critic",
            "perspective", "angle", "lens", "viewpoint", "view", "thinking", "mindset",
            "mentality", "approach", "cognitive", "mental", "psychological",
            "at home", "at work", "in business", "in life", "in society",
            "technical side", "business side", "theory", "practice"
        ]
        
        return any(pattern in t for pattern in patterns)
    
    def _is_responding_to_clarifier(text: str, history: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """
        CRITICAL FIX: Detect if user is RESPONDING to a clarifier question.
        
        Returns: (is_response, original_prompt)
        
        Pattern:
        - Message N: User original prompt (e.g., "I want to write perfect review paper")
        - Message N+1: Assistant clarifier (asking for details)
        - Message N+2: User response to clarifier (e.g., "Anything is fine", "Open ended")
        
        When detected, return the ORIGINAL prompt (N) so we can merge the response with it.
        This PREVENTS re-asking for clarification when user already engaged with it.
        """
        t = (text or "").lower().strip()
        word_count = len(t.split())
        
        # Response to clarifier is typically very short (1-5 words)
        if word_count > 5:
            return False, None
        
        # Need at least 3 messages: [user original] [assistant clarifier] [user response]
        if len(history) < 3:
            return False, None
        
        # Last message is current user input
        if history[-1].get("role") != "user":
            return False, None
        
        # Second-to-last must be from assistant (the clarifier)
        if history[-2].get("role") != "assistant":
            return False, None
        
        prev_assistant_msg = history[-2]
        prev_assistant_content = (prev_assistant_msg.get("content") or "").lower()
        
        # Check if previous assistant message was a clarifier
        # It's a clarifier if output_type is "clarifier" OR it contains clarifier patterns
        is_prev_clarifier = (
            prev_assistant_msg.get("output_type") == "clarifier" or
            any(indicator in prev_assistant_content for indicator in [
                "what is the specific", "what topic", "which", "clarify",
                "needed details:", "pick which", "tell me", "can you provide",
                "do you have", "preference", "scope", "focus", "angle"
            ])
        )
        
        if not is_prev_clarifier:
            return False, None
        
        # Check if current text is a typical clarifier response
        clarifier_responses = [
            "anything is fine", "anything is ok", "anything goes", "anything", "any is fine",
            "open ended", "open-ended", "doesn't matter", "does not matter", "no preference",
            "either way", "i don't care", "idc", "sure", "ok", "okay", "yes", "yep", "yeah",
            "not sure", "provide missing details", "stop here", "stop", "never mind", "forget it",
            "embedded", "standalone", "both", "all", "whatever", "any of them"
        ]
        
        domains = ["software engineering", "psychology", "philosophy", "business", "mathematics", "art/design", "art", "design"]
        
        is_response_to_clarifier = (
            any(response in t for response in clarifier_responses) or
            any(t == domain for domain in domains)
        )
        
        if not is_response_to_clarifier:
            return False, None
        
        # FOUND CLARIFIER RESPONSE! Now find the original prompt it was answering
        # It's the user message that came BEFORE the clarifier (typically 2 messages back)
        # But we need to search backwards to find the actual original question
        
        original_prompt = None
        # Look backwards through history for the user message that triggered the clarifier
        for i in range(len(history) - 3, -1, -1):
            msg = history[i]
            if msg.get("role") == "user":
                # This is a user message before the clarifier
                # If the previous message (after this one) is also from user, skip (it's not the trigger)
                if i + 1 < len(history) - 2 and history[i + 1].get("role") == "user":
                    continue
                original_prompt = msg.get("content", "").strip()
                break
        
        return is_response_to_clarifier, original_prompt

    def _is_paradox_request(text: str) -> bool:
        t = (text or "").lower().replace("’", "'").replace("‘", "'")
        if not t.strip():
            return False
        patterns = [
            r"\bexplain\b.*\bbut\b.*\b(don't|dont|do not|without)\b.*\bexplain\b",
            r"\bdefine\b.*\bbut\b.*\b(don't|dont|do not|without)\b.*\bdefine\b",
            r"\bdescribe\b.*\bbut\b.*\b(don't|dont|do not|without)\b.*\bdescribe\b",
            r"\bteach\b.*\bbut\b.*\b(don't|dont|do not|without)\b.*\bteach\b",
            r"\bexplain\b.*\bwithout\b.*\bexplaining\b",
            r"\bdescribe\b.*\bwithout\b.*\bdescribing\b",
            r"\bdefine\b.*\bwithout\b.*\bdefining\b",
        ]
        return any(re.search(p, t) for p in patterns)

    # If continuation_state provided, restore previous iteration state
    if continuation_state:
        current_prompt = continuation_state.get("last_prompt", "")
        results = continuation_state.get("previous_results", {})
        # Increment max_iterations to allow more rounds
        max_iterations = continuation_state.get("iterations_completed", 0) + max_iterations
    else:
        # Inject today's date so LLM knows current context
        today_date = datetime.now().strftime("%A, %B %d, %Y")
        abstract_task_with_date = f"{abstract_task}\n\n[Context: Today is {today_date}]"

        # --- Default result structure (MUST NOT CHANGE) ---
        results = {
            "user_task": abstract_task,
            "role_selected": "Failure Mode",
            "optimized_prompt": current_prompt,
            "final_output": "Execution failed or LLM not reachable.",
            "output_type": "text",
            "execution_time_seconds": 0.00,
            "iterations": 0,
            "critic_score": 0.0,
            "critic_comments": [],
            "detected_altitude": "generic",
            "conversation_tone": "formal",
            "user_context": "general"
        }
        abstract_task_with_date = f"{abstract_task}\n\n[Context: Today is {datetime.now().strftime('%A, %B %d, %Y')}]"

    def _extract_final_content_and_type(text: str) -> tuple[str, str]:
        if not isinstance(text, str):
            return ("", "text")
        
        # * [AGGRESSIVE SIGNAL-TO-NOISE FILTER] Strip ALL meta-commentary
        # Remove everything BEFORE the actual deliverable
        noise_patterns = [
            r"^.*?(?:This email is|This (?:code|response|message)).*?(?=Subject:|Team,|\n\n[A-Z])",  # Remove leading analysis
            r"^.*?(?:To make this|Here are some).*?(?=Subject:|Team,|\n\n[A-Z])",  # Remove suggestions
            r"^.*?(?:Overall, this).*?(?=Subject:|Team,|\n\n[A-Z])",  # Remove summary
            r"^.*?●\s*SCORE:.*?●\s*ROLE:.*?(?:Optimized Prompt|Copy|Hide)\s*",  # Remove metadata markers
            r"Here(?:'s| is) (?:an updated version|the (?:updated|revised|improved)).*?:\s*",
            r"To (?:enhance|improve|make it better).*?(?=Subject:|Team,|\n)",
            r"\d+\.\s*\*\*[^*]+\*\*:.*?(?=\n\d+\.|\n\n|Subject:|Team,)",  # Numbered points
            r"\*\s+A brief summary.*?(?=\n\n|Subject:|Team,)",  # Bullet suggestions
            r"Overall,.*?(?=\n\n|Subject:|Team,)",
        ]
        
        cleaned_text = text
        for pattern in noise_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
        
        # Extract code blocks
        match = re.search(r"```(?P<lang>[^\n]*)\n(?P<code>.*?)```", cleaned_text, re.DOTALL)
        if match:
            return match.group("code").strip(), match.group("lang").strip() or "code"
        
        # FINAL CLEANUP: If there's still noise before "Subject:" or recognizable start, extract from there
        if "Subject:" in cleaned_text:
            subject_pos = cleaned_text.find("Subject:")
            cleaned_text = cleaned_text[subject_pos:]
        elif re.search(r'\n\n([A-Z][a-z]+,)', cleaned_text):  # Find "Team," or "Hi," etc
            match = re.search(r'\n\n([A-Z][a-z]+,)', cleaned_text)
            cleaned_text = cleaned_text[match.start()+2:]
        
        # Clean up extra whitespace
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
        
        return cleaned_text, "text"

    try:
        # Check if this is an EXPLICITLY OPEN-ENDED request early on
        # This needs to happen BEFORE we use it in any logic below
        is_open_ended_request = _is_open_ended_exploratory_request(abstract_task)
        
        # *** CRITICAL FIX: HANDLE CLARIFIER RESPONSES ***
        # When user responds to a clarifier, merge response with ORIGINAL prompt
        # This prevents infinite clarification loops
        is_clarif_response, original_prompt = _is_responding_to_clarifier(abstract_task, full_context_history)
        
        if is_clarif_response and original_prompt:
            # User is responding to a clarifier about their original prompt
            # Merge: original prompt + their response = enhanced task
            abstract_task = f"{original_prompt} [User context: {abstract_task.strip()}]"
            # Boost as open-ended since user engaged with clarification
            is_open_ended_request = True
        
        # * [ENHANCED] Classifier now returns tone, user context, complexity, and HIDDEN PROBLEMS
        # Use task WITH date context for accuracy
        classification = await classify_prompt(abstract_task_with_date, full_context_history)
        intent_validation = await validate_intent_context(abstract_task, full_context_history)
        detected_type = classification.get("type")
        sub_intents = classification.get("sub_intents", [])
        sub_intents = sub_intents if isinstance(sub_intents, list) else []
        is_paradox = any(str(si).lower() == "paradox_prompt" for si in sub_intents)
        is_paradox = is_paradox or _is_paradox_request(abstract_task)
        if is_paradox and "paradox_prompt" not in [str(si).lower() for si in sub_intents]:
            sub_intents.append("paradox_prompt")
        altitude = classification.get("altitude", "generic")
        conversation_tone = classification.get("conversation_tone", "formal")
        user_context = classification.get("user_context", "general")
        complexity_score = classification.get("complexity_score", 0.5)
        burnout_signal = classification.get("burnout_signal", 0.0)
        hidden_problem = classification.get("hidden_problem")
        vagueness_score = classification.get("vagueness_score", classification.get("ambiguity_score", 0.0) or 0.0)
        ambiguity_score = max(
            vagueness_score,
            classification.get("ambiguity_score", 0.0) or 0.0
        )
        pathfinder_trigger = bool(classification.get("pathfinder_trigger"))
        needs_clarification_flag = bool(classification.get("needs_clarification"))
        validation_should_clarify = bool(intent_validation.get("should_clarify"))
        validation_question = intent_validation.get("clarifying_question") or ""
        validation_missing_info = intent_validation.get("missing_info")
        validation_missing_info = validation_missing_info if isinstance(validation_missing_info, list) else []
        rephrase_similarity = _rephrase_similarity(full_context_history)
        
        # INTELLIGENT VAGUENESS ADJUSTMENT: For open-ended requests ("give me", "suggest"),
        # vagueness is EXPECTED and DESIRED. The user wants exploration, not precision.
        # So we should downgrade the vagueness penalty.
        if is_open_ended_request and vagueness_score > 0.4:
            # User explicitly likes ambiguity by saying "give me" → reduce perceived vagueness
            vagueness_score = max(0.3, vagueness_score - 0.25)
            ambiguity_score = max(0.3, ambiguity_score - 0.25)

        
        # Check for rejection: explicit cues OR implicit (rephrasing after assistant response = silent rejection)
        explicit_rejection = _has_rejection(abstract_task) or _is_rejection_after_response(full_context_history)
        implicit_rejection = (
            len(full_context_history) >= 4 and  # Need history: user → assistant → user → assistant
            full_context_history[-2].get("role") == "assistant" and  # Previous was assistant
            full_context_history[-1].get("role") == "user" and  # Current is user
            rephrase_similarity >= 0.50  # Similar wording = rephrasing (50% threshold for "in other way" detection)
        )
        
        # If implicit rejection (rephrasing), analyze if the rephrased version is clearer
        rephrased_is_clearer = False
        if implicit_rejection and not explicit_rejection:
            # The rephrased ambiguity should be lower than original for it to be "clearer"
            current_ambiguity = ambiguity_score  # This is for the rephrased version
            # Compare with previous user message (original ask)
            user_msgs = [m for m in full_context_history if m.get("role") == "user"]
            if len(user_msgs) >= 2:
                original_text = user_msgs[-2].get("content", "")
                rephrased_text = user_msgs[-1].get("content", "")
                # Rephrased is clearer if:
                # 1. It's longer (more specific)
                # 2. It has fewer vague words
                # 3. Current ambiguity is lower than we'd expect
                is_longer = len(rephrased_text) > len(original_text) * 0.8
                has_fewer_vague_terms = (
                    original_text.count("thing") + original_text.count("stuff") 
                    > rephrased_text.count("thing") + rephrased_text.count("stuff")
                )
                rephrased_is_clearer = (is_longer or has_fewer_vague_terms) and current_ambiguity < 0.65
        
        # IMPORTANT: Check if user just selected a domain (e.g., "Philosophy")
        # If so, skip rejection handling and proceed normally with augmented task
        is_domain_selection = _is_domain_selection(abstract_task)
        
        # Rejection flag: show clarifier UNLESS rephrased version is clearly better OR it's a domain selection
        rejection_flag = (explicit_rejection or implicit_rejection) and not rephrased_is_clearer and not is_domain_selection
        
        results["detected_altitude"] = altitude
        results["conversation_tone"] = conversation_tone
        results["user_context"] = user_context
        
        # Extract multi-dimensional intent data
        sincerity_polarity = classification.get("sincerity_polarity", "utility")
        intelligence_altitude = classification.get("intelligence_altitude", "layman")
        hidden_goal = classification.get("hidden_goal")
        confidence_score = classification.get("confidence_score", 0.8)
        vagueness_score = classification.get("vagueness_score", vagueness_score)
        
        # INTELLIGENT BOOST: If user is making an open-ended request ("give me", "suggest", etc.),
        # they're showing INTENT and TRUST. Boost confidence for these requests.
        if is_open_ended_request:
            # User is saying "I trust you to use your judgment" → boost confidence
            confidence_score = max(confidence_score, 0.85)  # At least 0.85
            import logging
            logging.info(f"[APO] Open-ended request detected: '{abstract_task[:50]}...' User trusting system judgment. Confidence boosted to {confidence_score:.2f}")


        # Preference inference: learn from recent conversation signals
        def _infer_preferences(history: List[Dict[str, Any]]):
            style = None  # academic | plain
            focus = None  # overview | examples | business impact | definition
            wants_max_quality = False
            for msg in reversed(history[-6:]):
                text = (msg.get("content") or "").lower()
                if "maximize quality" in text or "perfect score" in text or "aim for 1" in text:
                    wants_max_quality = True
                if "academic" in text and ("definition" in text or "notation" in text):
                    style = "academic"
                    focus = focus or "definition"
                if "plain" in text or "simple" in text:
                    style = style or "plain"
                if "business impact" in text:
                    focus = "business impact"
                if "examples" in text or "example" in text:
                    focus = focus or "examples"
                if "overview" in text:
                    focus = focus or "overview"
            return style, focus, wants_max_quality

        pref_style, pref_focus, pref_max_quality = _infer_preferences(full_context_history)
        user_context_augmented_parts = [user_context]
        if pref_style:
            user_context_augmented_parts.append(f"prefers {pref_style}")
        if pref_focus:
            user_context_augmented_parts.append(f"focus on {pref_focus}")
        # Adaptive examples policy: do not force user-specified example unless explicitly demanded
        user_context_augmented_parts.append("adaptive examples: choose best-fit; avoid forcing user-provided example unless explicitly requested")
        user_context_augmented = "; ".join(p for p in user_context_augmented_parts if p)

        # Elevate altitude when academic preference detected
        if pref_style == "academic":
            altitude = "academic"
            results["detected_altitude"] = altitude

        # Verbosity/Detail heuristic
        detail_level = "standard"
        task_lower = (abstract_task or "").lower()
        detail_keywords = ["steps", "guide", "manual", "detailed", "explain", "why", "rationale", "examples", "walkthrough", "how to"]
        brief_keywords = ["brief", "short", "concise", "tldr", "tl;dr", "summary"]
        if any(k in task_lower for k in brief_keywords) or (conversation_tone == "casual" and complexity_score < 0.4):
            detail_level = "brief"
        elif any(k in task_lower for k in detail_keywords) or (altitude in ["production", "enterprise"] and complexity_score > 0.6):
            detail_level = "detailed"
        elif document_context:
            detail_level = "detailed"

        # Broad-ambiguity detector (for PathFinder gating)
        broad_trigger = re.search(r"\b(what is|tell me about|explain|overview)\b", abstract_task.lower()) is not None
        # Lightweight new-user heuristic and preference presence
        user_is_new = sum(1 for m in full_context_history if (m.get("role") == "user")) <= 1
        no_prior_prefs = (pref_style is None and pref_focus is None)

        # Scenario-aware clarifier: offer tailored options
        def _build_clarifier(task: str):
            t = task.lower()
            if re.search(r"\b(what is|define|explain)\b", t):
                options = ["plain overview", "academic definition", "business impact", "examples", "maximize quality"]
                msg = (
                    "To tailor this, choose one focus: plain overview, academic definition, business impact, or examples."
                )
            elif re.search(r"\b(how to|steps|guide)\b", t):
                options = ["quick steps", "detailed guide", "best practices", "maximize quality"]
                msg = "Prefer quick steps, a detailed guide, or best practices?"
            elif re.search(r"\b(compare|vs|difference)\b", t):
                options = ["features", "performance", "cost", "use cases", "maximize quality"]
                msg = "Compare by features, performance, cost, or use cases?"
            elif re.search(r"\b(write|draft|email|report|code)\b", t):
                options = ["email", "report", "code", "summary", "maximize quality"]
                msg = "What deliverable should I produce: email, report, code, or summary?"
            else:
                options = ["plain overview", "academic definition", "examples", "business impact", "maximize quality"]
                msg = "Choose a focus: plain overview, academic definition, examples, business impact, or maximize quality."
            return msg, options

        needs_clarification = (
            vagueness_score > 0.5 or
            (isinstance(detected_type, str) and detected_type.lower() in ["question", "casual_chat"] and confidence_score < 0.75)
            or needs_clarification_flag
            or validation_should_clarify
        )
        
        # INTELLIGENCE OVER RULES: If user explicitly said "give me", "suggest", etc.,
        # they're trusting the system's judgment. Don't ask, just generate a good answer.
        if is_open_ended_request:
            needs_clarification = False
            pathfinder_trigger = False
        
        if is_paradox:
            needs_clarification = False
            pathfinder_trigger = False
        if validation_should_clarify:
            pathfinder_trigger = False

        intent_meta = {
            "ambiguity_score": round(ambiguity_score, 2),
            "vagueness_score": round(vagueness_score, 2),
            "confidence": round(confidence_score, 2),
            "pathfinder_trigger": pathfinder_trigger,
            "needs_clarification": needs_clarification,
            "rephrase_similarity": rephrase_similarity,
        }

        results["intent_metadata"] = intent_meta
        results["ambiguity_score"] = intent_meta["ambiguity_score"]
        results["rephrase_similarity"] = rephrase_similarity

        # Get user messages for context checking
        user_messages = [m for m in full_context_history if m.get("role") == "user"]

        # If user selected a domain, augment the original task and proceed normally
        if is_domain_selection:
            if len(user_messages) >= 2:
                original_question = user_messages[0].get("content", abstract_task)
                domain_selected = abstract_task.strip()
                abstract_task = f"{original_question} (from {domain_selected} perspective)"
                results["domain_selected"] = domain_selected
        
        # If user provided a clarification refiner, merge it with the original question
        elif _is_clarification_refiner(abstract_task) and len(user_messages) >= 2:
            original_question = user_messages[0].get("content", abstract_task)
            clarification = abstract_task.strip()
            # Merge: keep original question, add clarification as guidance
            abstract_task = f"{original_question}\n[User clarification: interpret as '{clarification}', not generic tools/automation]"
            results["clarification_detected"] = clarification
            results["merged_with_original"] = True

        if rejection_flag:
            # Analyze task to filter relevant domains
            task_lower = abstract_task.lower()
            all_domains = {
                "Software Engineering": f"implementation details or architecture for '{abstract_task}'",
                "Psychology": f"how users think/behave about '{abstract_task}'",
                "Philosophy": f"conceptual foundations/ethics of '{abstract_task}'",
                "Business": f"strategy, impact, or ROI for '{abstract_task}'",
                "Mathematics": f"formal model or quantitative framing of '{abstract_task}'",
                "Art/Design": f"creative or narrative angle for '{abstract_task}'"
            }
            
            # Filter domains by relevance to the task
            relevant_domains = all_domains.copy()
            
            # Remove domains that are clearly irrelevant
            if not any(word in task_lower for word in ["build", "code", "develop", "system", "app", "software", "architecture"]):
                if "Software Engineering" in relevant_domains:
                    del relevant_domains["Software Engineering"]
            
            if not any(word in task_lower for word in ["think", "feel", "behave", "user", "person", "human", "mind"]):
                if "Psychology" in relevant_domains and len(relevant_domains) > 2:
                    del relevant_domains["Psychology"]
            
            if not any(word in task_lower for word in ["model", "formula", "number", "quantify", "metric", "measure", "math"]):
                if "Mathematics" in relevant_domains and len(relevant_domains) > 2:
                    del relevant_domains["Mathematics"]
            
            # Always keep at least 3 domains and at most all 6
            if len(relevant_domains) < 3:
                relevant_domains = all_domains.copy()
            
            rejection_options = [f"{domain}: {desc}" for domain, desc in relevant_domains.items()]
            
            # Detect if this is implicit rejection (rephrasing) vs explicit
            is_implicit = implicit_rejection and not explicit_rejection
            
            if is_implicit:
                # User rephrased = they wanted something different
                clarifier_msg = (
                    f"I notice you're asking about '{abstract_task}' in a different way. "
                    "Pick which angle you meant this time, or tell me directly."
                )
            else:
                # Explicit rejection ("No in other way", "that's not it", etc.)
                clarifier_msg = (
                    "I think you're refining or rejecting the previous answer. Pick the closest intent below, or tell me in your own words."
                )
            
            results["role_selected"] = "Rejection Intelligence"
            results["optimized_prompt"] = "Clarification pending"
            results["final_output"] = clarifier_msg
            results["clarifier_options"] = rejection_options + ["Other (tell me in your words)"]
            results["rejection_hypotheses"] = rejection_options
            results["output_type"] = "clarifier"
            results["iterations"] = 0
            results["critic_score"] = 1.0
            results["is_implicit_rejection"] = is_implicit
            results["rephrased_analysis"] = {
                "is_rephrasing": implicit_rejection,
                "rephrased_is_clearer": rephrased_is_clearer,
                "current_ambiguity": round(ambiguity_score, 2)
            }
            results["execution_time_seconds"] = round(time.time() - start_time, 2)
            return results

        if needs_clarification and not is_paradox:
            normalized_task = (abstract_task or "").strip().lower()
            if normalized_task in ["provide missing details", "provide missing detail", "provide details"]:
                msg = "Please clarify with extra context. Share the exact question/problem and what you want me to do (solve, explain, check, or correct)."
                if validation_missing_info:
                    needed = ", ".join(info for info in validation_missing_info if isinstance(info, str) and info.strip())
                    if needed and needed != "request":
                        msg = f"{msg}\n\nNeeded details: {needed}"
                options = ["Not sure", "Stop here"]
            elif normalized_task in ["not sure", "not sure."]:
                msg = (
                    "No worries. You can share any of these to help me proceed: the exact question text, what you want (solve, explain, check, correct), "
                    "and any constraints or class level. If you only have the question, paste that."
                )
                options = ["Provide missing details", "Stop here"]
            elif validation_should_clarify and validation_question:
                msg = validation_question
                if validation_missing_info:
                    needed = ", ".join(info for info in validation_missing_info if isinstance(info, str) and info.strip())
                    if needed and needed != "request":
                        msg = f"{msg}\n\nNeeded details: {needed}"
                options = ["Provide missing details", "Not sure", "Stop here"]
            else:
                msg, options = _build_clarifier(abstract_task)
            results["role_selected"] = "Clarifier"
            results["optimized_prompt"] = "Clarification requested due to ambiguity/mixed intent."
            results["final_output"] = msg
            results["clarifier_options"] = options + ["Other (tell me in your words)"]
            results["output_type"] = "clarifier"
            results["iterations"] = 0
            results["critic_score"] = 1.0
            results["execution_time_seconds"] = round(time.time() - start_time, 2)
            return results

        # * [PATHFINDER] Prefer for broad queries when user is new or no prefs
        # Ensures generic prompts like "What is AI/ML?" ask for direction first
        # BUT: Skip if user explicitly said "give me", "suggest", etc. (open-ended request)
        if (
            not is_paradox and not is_open_ended_request and (
                pathfinder_trigger or
                (broad_trigger and (user_is_new or no_prior_prefs or vagueness_score > 0.5 or confidence_score < 0.7))
                or ((confidence_score < 0.35) and (vagueness_score > 0.6 or bool(hidden_problem)))
            )
        ):
            from util import build_pathfinder_prompt
            # Use original task (without date context) for pathfinder display
            pathfinder_response = build_pathfinder_prompt(abstract_task, confidence_score, hidden_goal)
            _, pathfinder_options = _build_clarifier(abstract_task)
            results["role_selected"] = "Pathfinder"
            results["final_output"] = pathfinder_response
            results["output_type"] = "pathfinder"
            results["clarifier_options"] = pathfinder_options + ["Other (tell me in your words)"]
            results["pathfinder_options"] = pathfinder_options
            results["iterations"] = 0
            results["critic_score"] = 1.0
            import logging
            logging.info(f"[APO] Pathfinder engaged: broad/ambiguous query (vagueness={vagueness_score:.2f}, confidence={confidence_score:.2f}).")
            results["execution_time_seconds"] = round(time.time() - start_time, 2)
            return results
        
        # * [PROACTIVE LEADERSHIP] If user shows burnout, flag escalation early
        if burnout_signal > 0.6:
            escalation_msg = f"[ESCALATION] User showing signs of decision fatigue/burnout (score: {burnout_signal:.2f}). Hidden problem: {hidden_problem}. Consider human review."
            import logging
            logging.warning(escalation_msg)
            results["escalation_alert"] = escalation_msg

        # ==========================================================
        # ===================== LLM-1 PLANNER ======================
        # ==========================================================
        # Pass task WITH date context so planner gets current date
        optimized_prompt_raw = await generate_optimized_prompt(
            abstract_task_with_date,
            full_context_history,
            document_context,
            detected_type,
            sub_intents,
            altitude=altitude,
            conversation_tone=conversation_tone,
            user_context=user_context_augmented,
            detail_level=detail_level
        )

        if isinstance(optimized_prompt_raw, str) and optimized_prompt_raw.startswith("Error:"):
            raise ConnectionError(f"LLM-1 (Planner) failed: {optimized_prompt_raw}")

        current_prompt = optimized_prompt_raw.strip()
        chosen_role = "Universal Optimization Agent"
        
        # ----------- Strict Code Logic -----------
        strict_code_only = any(si.lower() == "wants_only_code" for si in sub_intents)
        if not strict_code_only:
            # Check original task (without date) for code-only hints
            if re.search(r'\b(no explanation|only code|just give code|code only)\b', abstract_task, re.I):
                strict_code_only = True

        enforcement_prefix = ""
        if strict_code_only:
            enforcement_prefix = "RETURN ONLY CODE. NO TEXT. USE FENCED BLOCK.\n\n"

        current_prompt_for_executor = enforcement_prefix + current_prompt

        def _wants_max_quality(text: str) -> bool:
            t = (text or "").lower()
            return any(kw in t for kw in [
                "maximize quality", "perfect score", "aim for 1", "optimize to 1", "score 1", "audit 1"
            ])

        force_max_quality = _wants_max_quality(abstract_task)

        # * [PEER-TO-PEER ROUTING] Smart gating: skip Critic for simple/casual, full loop for production
        should_skip_critic = (conversation_tone == "casual" and complexity_score < 0.4) or \
                             (detected_type in ["question", "casual_chat"] and complexity_score < 0.5)
        should_full_loop = altitude == "production" and (isinstance(detected_type, str) and ("security" in detected_type.lower() or complexity_score > 0.7))

        if force_max_quality:
            should_skip_critic = False
            should_full_loop = True
        
        if should_skip_critic:
            # Fast path: single execution for trivial/casual requests
            executor_output = await execute_optimized_prompt(
                current_prompt_for_executor,
                abstract_task,
                document_context=document_context,
                detail_level=detail_level
            )
            if isinstance(executor_output, str) and executor_output.startswith("Error:"):
                raise ConnectionError(f"LLM-2 (Executor) failed: {executor_output}")
            
            final_output, output_type = _extract_final_content_and_type(executor_output)
            results["role_selected"] = "Direct Responder"
            results["optimized_prompt"] = current_prompt
            results["final_output"] = final_output
            results["output_type"] = output_type
            results["iterations"] = 1
            results["critic_score"] = 1.0  # Auto-approved for low complexity
            import logging
            logging.info(f"[APO] Fast path (casual/simple): skipped critic loop, returned directly.")
            results["execution_time_seconds"] = round(time.time() - start_time, 2)
            return results

        # * [STANDARD + FULL LOOP] For formal/complex and production tasks
        max_iters_adjusted = max_iterations if should_full_loop else min(max_iterations, 2)
        quality_threshold_adjusted = 0.94 if should_full_loop else max(quality_threshold, 0.94)
        if force_max_quality:
            max_iters_adjusted = max(max_iterations, 4)
            quality_threshold_adjusted = 0.999
        # ==========================================================
        # ====================== A2 LOOP (Conditional) ============
        # ==========================================================
        best_iteration = 0
        best_score = 0.0
        best_output = ""
        best_prompt = current_prompt
        
        for iteration in range(1, max_iters_adjusted + 1):
            results["iterations"] = iteration

            # EXECUTOR (LLM-2)
            executor_output = await execute_optimized_prompt(
                current_prompt_for_executor,
                abstract_task,
                document_context=document_context,
                detail_level=detail_level
            )

            if isinstance(executor_output, str) and executor_output.startswith("Error:"):
                raise ConnectionError(f"LLM-2 (Executor) failed: {executor_output}")

            # * [NEXUS CRITIC] Now receives all multi-dimensional intent data + iteration count
            critic_result = await critic_evaluate(
                abstract_task, current_prompt, executor_output,
                detected_altitude=altitude,
                conversation_tone=conversation_tone,
                burnout_signal=burnout_signal,
                sincerity_polarity=sincerity_polarity,
                intelligence_altitude=intelligence_altitude,
                hidden_goal=hidden_goal,
                iteration=iteration
            )
            critic_score = float(critic_result.get("score", 0.0))
            suggested_prompt = critic_result.get("suggested_prompt", current_prompt)
            critic_role = critic_result.get("role", "Critic")
            escalation_flag = critic_result.get("escalation")
            internal_monologue = critic_result.get("internal_monologue", "No corrections.")

            # If the critic failed or produced a zero score, fall back gracefully
            if critic_role.startswith("Critic-Error") or critic_score <= 0.0:
                if is_paradox:
                    results["role_selected"] = "Paradox-Fallback"
                    results["optimized_prompt"] = current_prompt
                    results["final_output"] = executor_output
                    results["output_type"] = "text"
                    results["iterations"] = iteration
                    results["critic_score"] = round(critic_score, 3)
                    results["execution_time_seconds"] = round(time.time() - start_time, 2)
                    return results
                results["role_selected"] = "Clarifier"
                results["optimized_prompt"] = current_prompt
                results["final_output"] = (
                    "I could not validate this response. Should I re-run with more iterations, "
                    "or do you want to provide missing details?"
                )
                results["clarifier_options"] = [
                    "Re-run with more iterations",
                    "Provide missing facts",
                    "Stop here"
                ]
                results["output_type"] = "clarifier"
                results["iterations"] = iteration
                results["critic_score"] = round(critic_score, 3)
                results["execution_time_seconds"] = round(time.time() - start_time, 2)
                return results
            
            results["critic_comments"].append({
                "iteration": iteration,
                "score": round(critic_score, 3),
                "comment": critic_result.get("comments", "No comment."),
                "internal_monologue": internal_monologue,
                "escalation": escalation_flag
            })

            # Track best result across all iterations
            if critic_score > best_score:
                best_score = critic_score
                best_iteration = iteration
                best_output = executor_output
                best_prompt = current_prompt

            chosen_role = critic_role or chosen_role
            results["critic_score"] = round(critic_score, 3)

            if critic_score >= quality_threshold_adjusted:
                break
            if suggested_prompt.strip() == current_prompt.strip():
                break

            current_prompt = suggested_prompt.strip()
            current_prompt_for_executor = enforcement_prefix + current_prompt
        
        # Use final output from last iteration (could be best or current)
        final_output, output_type = _extract_final_content_and_type(executor_output)
        results["role_selected"] = chosen_role
        # * [FIELD CLARIFICATION]
        # "optimized_prompt" = Internal instruction given to Executor (meta, for debugging)
        # "final_output" = The actual deliverable the user requested (email, code, etc.)
        results["optimized_prompt"] = current_prompt  
        results["output_type"] = output_type

        # Enforce display gating based on critic score
        if results.get("critic_score", 0.0) >= MIN_DISPLAY_SCORE:
            # Quality threshold met
            results["final_output"] = final_output
        else:
            # Below quality threshold: return BEST iteration result, not just final
            final_output_best, _ = _extract_final_content_and_type(best_output)
            results["final_output"] = final_output_best
            results["quality_warning"] = True
            results["quality_score_current"] = results.get("critic_score", 0.0)
            results["quality_score_best"] = round(best_score, 3)
            results["best_iteration"] = best_iteration
            
            # Offer continuation option
            can_iterate_more = results.get("iterations", 0) < (max_iters_adjusted * 2)  # Allow up to 2x more
            if can_iterate_more:
                results["continuation_available"] = True
                results["continuation_message"] = (
                    f"Current quality score: {results['quality_score_current']:.2f} (below {MIN_DISPLAY_SCORE:.2f}). "
                    f"Best score achieved: {results['quality_score_best']:.2f} in iteration {best_iteration}. "
                    f"We can refine further if you have time—would you like to continue optimizing?"
                )
                results["suggested_action"] = "continue_optimization"
            else:
                results["continuation_available"] = False
                results["final_note"] = (
                    f"Returned best result (iteration {best_iteration}, score {results['quality_score_best']:.2f}). "
                    f"Maximum iterations reached."
                )
        
        # * [CLEAN METADATA] Add formatted metadata for UI display
        results["metadata"] = {
            "quality_score": round(results["critic_score"], 2),
            "agent_role": chosen_role,
            "iterations_used": results["iterations"],
            "altitude_detected": altitude,
            "tone": conversation_tone,
            "execution_time": f"{results.get('execution_time_seconds', 0)}s"
        }
        
        # * [PHASE 4: NEXUSAI METADATA] Expose full cognitive state to frontend
        results["nexus_metadata"] = {
            "detected_altitude": altitude,  # Enterprise | Academic | Casual
            "audit_score": round(results["critic_score"], 3),  # Use critic_score, not undefined final_score
            "internal_monologue": results["critic_comments"][-1].get("internal_monologue", "No audit performed.") if results["critic_comments"] else "Fast path - no audit.",
            "intelligence_altitude": intelligence_altitude,  # Expert | Layman
            "sincerity_polarity": sincerity_polarity,  # Utility | Curiosity | Play
            "hidden_goal": hidden_goal,  # risk_mitigation | substitutability | novelty | etc
            "burnout_signal": round(burnout_signal, 2),
            "confidence_score": round(confidence_score, 2),
            "ambiguity_score": results.get("ambiguity_score"),
            "rephrase_similarity": results.get("rephrase_similarity"),
            "intent_metadata": results.get("intent_metadata")
        }

    except Exception as e:
        results["final_output"] = f"Workflow Error: {e}"
        results["role_selected"] = "Failure Mode"

    results["execution_time_seconds"] = round(time.time() - start_time, 2)
    return results