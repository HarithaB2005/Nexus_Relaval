# agents.py (FINAL UNIFIED CODE - Updated with Cognitive Altitude)

import time
import asyncio
import re
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
    classify_prompt
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
    user_context: str = "general"
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
        user_context=user_context
    )

    return await call_llm(planner_prompt, is_meta_prompt=True)


# ==========================================================
# ==================== EXECUTOR ============================
# ==========================================================

async def execute_optimized_prompt(optimized_prompt: str, abstract_task: str, document_context: Optional[str] = None) -> str:
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
    executor_instruction = f"""{optimized_prompt}{context_section}

CRITICAL OUTPUT RULES:
- Output ONLY the final deliverable
- If DOCUMENT REFERENCE provided above, you MUST use that specific content in your response
- NO meta-commentary ("This email is...", "Here's the code...")
- NO explanations or analysis
- If email: start with "Subject:" immediately
- If code: use fenced code block only
- NO suggestions or numbered lists after the deliverable
"""
    return await call_llm(executor_instruction, is_meta_prompt=False)



# ==========================================================
# ====================== MAIN WORKFLOW =====================
# ==========================================================

async def apo_workflow(
    abstract_task: str,
    full_context_history: List[Dict[str, Any]], 
    document_context: Optional[str] = None,
    max_iterations: int = 3,
    quality_threshold: float = 0.97,
    continuation_state: Optional[Dict[str, Any]] = None
) -> dict:

    start_time = time.time()
    executor_output = ""
    current_prompt = "Error during workflow initialization."
    critic_score = 0.0
    
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
        # * [ENHANCED] Classifier now returns tone, user context, complexity, and HIDDEN PROBLEMS
        # Use task WITH date context for accuracy
        classification = await classify_prompt(abstract_task_with_date, full_context_history) 
        detected_type = classification.get("type")
        sub_intents = classification.get("sub_intents", [])
        altitude = classification.get("altitude", "generic")
        conversation_tone = classification.get("conversation_tone", "formal")
        user_context = classification.get("user_context", "general")
        complexity_score = classification.get("complexity_score", 0.5)
        burnout_signal = classification.get("burnout_signal", 0.0)
        hidden_problem = classification.get("hidden_problem")
        
        results["detected_altitude"] = altitude
        results["conversation_tone"] = conversation_tone
        results["user_context"] = user_context
        
        # Extract multi-dimensional intent data
        sincerity_polarity = classification.get("sincerity_polarity", "utility")
        intelligence_altitude = classification.get("intelligence_altitude", "layman")
        hidden_goal = classification.get("hidden_goal")
        confidence_score = classification.get("confidence_score", 0.8)
        vagueness_score = classification.get("vagueness_score", 0.0)

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
        )

        if needs_clarification:
            msg, options = _build_clarifier(abstract_task)
            results["role_selected"] = "Clarifier"
            results["optimized_prompt"] = "Clarification requested due to ambiguity/mixed intent."
            results["final_output"] = msg
            results["clarifier_options"] = options
            results["output_type"] = "text"
            results["iterations"] = 0
            results["critic_score"] = 1.0
            results["execution_time_seconds"] = round(time.time() - start_time, 2)
            return results

        # * [PATHFINDER] Prefer for broad queries when user is new or no prefs
        # Ensures generic prompts like "What is AI/ML?" ask for direction first
        if (
            (broad_trigger and (user_is_new or no_prior_prefs or vagueness_score > 0.5 or confidence_score < 0.7))
            or ((confidence_score < 0.35) and (vagueness_score > 0.6 or bool(hidden_problem)))
        ):
            from util import build_pathfinder_prompt
            # Use original task (without date context) for pathfinder display
            pathfinder_response = build_pathfinder_prompt(abstract_task, confidence_score, hidden_goal)
            results["role_selected"] = "Pathfinder"
            results["final_output"] = pathfinder_response
            results["output_type"] = "pathfinder"
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
            user_context=user_context_augmented
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
                document_context=document_context
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
                document_context=document_context
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
            "confidence_score": round(confidence_score, 2)
        }

    except Exception as e:
        results["final_output"] = f"Workflow Error: {e}"
        results["role_selected"] = "Failure Mode"

    results["execution_time_seconds"] = round(time.time() - start_time, 2)
    return results