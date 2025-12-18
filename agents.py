# agents.py (FINAL UNIFIED CODE)

import time
import asyncio
import re
from typing import Dict, Any, Optional, List

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
    video_context_text: Optional[str],
    detected_type: Optional[str] = None,
    sub_intents: Optional[List[str]] = None
) -> str:
    """
    Planner (LLM-1):
    Creates the optimized, natural-language, professional prompt, 
    now aware of the full conversation history.
    """
    full_context = []
    
    # 1. ADD EXTERNAL CONTEXT (Document and Video)
    if document_context:
        full_context.append(
            f"DOCUMENT CONTEXT (Extracted Text):\n---\n{document_context}\n---"
        )

    if video_context_text:
        full_context.append(
            f"VIDEO CONTEXT (Summary from Search):\n---\n{video_context_text}\n---"
        )

    context_string = "\n\n".join(full_context)

    # The Planner uses the combined context (History + Documents/Video)
    # NOTE: The full_context_history is passed directly to build_meta_instruction
    # which is where the history is converted into a structured string for the LLM.
    planner_prompt = build_meta_instruction(
        task_description=abstract_task,
        target_code=context_string, 
        full_context_history=full_context_history, 
        detected_type=detected_type,
        sub_intents=sub_intents
    )

    return await call_llm(planner_prompt, is_meta_prompt=True)


# ==========================================================
# ==================== EXECUTOR ============================
# ==========================================================

async def execute_optimized_prompt(optimized_prompt: str, abstract_task: str) -> str:
    """
    Executor (LLM-2):
    Runs the optimized prompt to produce the final output.
    """
    return await call_llm(optimized_prompt, is_meta_prompt=False)


# ==========================================================
# ====================== MAIN WORKFLOW =====================
# ==========================================================

async def apo_workflow(
    abstract_task: str,
    full_context_history: List[Dict[str, Any]], 
    document_context: Optional[str] = None,
    video_url: Optional[str] = None,
    max_iterations: int = 3,
    quality_threshold: float = 0.97
) -> dict:

    start_time = time.time()
    video_context_text = None
    executor_output = ""
    current_prompt = "Error during workflow initialization."
    critic_score = 0.0

    # ----------- default result structure (MUST NOT CHANGE) -----------
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
    }
    # ----------- structure preserved exactly as required -----------

    # ==========================================================
    # ======== HELPER: EXTRACT CONTENT AND TYPE ================
    # ==========================================================
    def _extract_final_content_and_type(text: str) -> tuple[str, str]:
        """
        Extracts content from a fenced code block if present, or returns the entire text.
        """
        if not isinstance(text, str):
            return ("", "text")
        
        # Regex to find a fenced code block: ```[lang]\n[code]```
        match = re.search(
            r"```(?P<lang>[^\n]*)\n(?P<code>.*?)```",
            text,
            re.DOTALL
        )
        if match:
            return match.group("code").strip(), match.group("lang").strip() or "code"
        
        return text.strip(), "text"

    try:
        # ==========================================================
        # ===================== LLM-0 CLASSIFIER ===================
        # ==========================================================
        # The Classifier must use the history to determine the intent if the abstract_task is vague
        classification = await classify_prompt(abstract_task, full_context_history) 
        detected_type = classification.get("type")
        sub_intents = classification.get("sub_intents", [])

        # ==========================================================
        # ===================== VIDEO CONTEXT ======================
        # ==========================================================
        if video_url and video_url.strip():
            video_context_text = await get_video_context_via_search(video_url)
            if video_context_text.startswith("Video content could not be determined"):
                print("Video context retrieval failed.")

        # ==========================================================
        # ===================== LLM-1 PLANNER ======================
        # ==========================================================
        optimized_prompt_raw = await generate_optimized_prompt(
            abstract_task,
            full_context_history,
            document_context,
            video_context_text,
            detected_type,
            sub_intents
        )

        if isinstance(optimized_prompt_raw, str) and optimized_prompt_raw.startswith("Error:"):
            raise ConnectionError(f"LLM-1 (Planner) failed: {optimized_prompt_raw}")

        current_prompt = optimized_prompt_raw.strip()
        chosen_role = "Universal Optimization Agent"
        
        # ==========================================================
        # =========== STRICT CODE-ONLY ENFORCEMENT LOGIC ===========
        # ==========================================================
        strict_code_only = any(si.lower() == "wants_only_code" for si in sub_intents)

        # Check for inline user requests for code-only output (uses the original abstract_task)
        if not strict_code_only:
            if re.search(
                r'\b(no explanation|only code|just give code|code only)\b',
                abstract_task,
                re.I
            ):
                strict_code_only = True

        enforcement_prefix = ""
        if strict_code_only:
            enforcement_prefix = (
                "IMPORTANT: RETURN ONLY THE FINAL WORKING SOURCE CODE. "
                "NO EXPLANATION OR TEXT. USE A SINGLE FENCED CODE BLOCK.\n\n"
            )

        current_prompt_for_executor = enforcement_prefix + current_prompt


        # ==========================================================
        # ====================== A2 LOOP ===========================
        # ==========================================================
        for iteration in range(1, max_iterations + 1):
            results["iterations"] = iteration

            # EXECUTOR (LLM-2)
            executor_output = await execute_optimized_prompt(
                current_prompt_for_executor,
                abstract_task
            )

            if isinstance(executor_output, str) and executor_output.startswith("Error:"):
                raise ConnectionError(f"LLM-2 (Executor) failed: {executor_output}")

            # CRITIC (LLM-3) - Compares original task, the base optimized prompt, and output
            critic_result = await critic_evaluate(
                abstract_task, current_prompt, executor_output
            )
            critic_score = float(critic_result.get("score", 0.0))
            suggested_prompt = critic_result.get("suggested_prompt", current_prompt)
            critic_role = critic_result.get("role", "Critic")
            
            # Capture Critic Comments for Debugging/Dossier Metrics
            results["critic_comments"].append({
                "iteration": iteration,
                "score": round(critic_score, 3),
                "comment": critic_result.get("comments", "No comment.")
            })

            chosen_role = critic_role or chosen_role
            results["critic_score"] = round(critic_score, 3)

            # ----- success condition -----
            if critic_score >= quality_threshold: # Checks against the new 0.97 threshold
                break

            # ----- if critic gives no real improvement but score is low, stop loop to avoid infinite retries -----
            if suggested_prompt.strip() == current_prompt.strip():
                break

            # ----- update prompt for next iteration -----
            current_prompt = suggested_prompt.strip()
            current_prompt_for_executor = enforcement_prefix + current_prompt
        
        # End of A2 Loop: Final assignment of results
        final_output, output_type = _extract_final_content_and_type(executor_output)

        results["role_selected"] = chosen_role
        results["optimized_prompt"] = current_prompt
        results["final_output"] = final_output
        results["output_type"] = output_type


    # ==========================================================
    # ===================== ERRORS =============================
    # ==========================================================

    except ConnectionError as ce:
        results["final_output"] = f"Connection Error: {str(ce)}"
        results["role_selected"] = "Failure Mode (LLM)"

    except Exception as e:
        results["final_output"] = f"Workflow Error: {e}"
        results["role_selected"] = "Failure Mode (Internal)"

    # ==========================================================
    # ===================== FINAL METRICS ======================
    # ==========================================================
    results["execution_time_seconds"] = round(time.time() - start_time, 2)
    return results