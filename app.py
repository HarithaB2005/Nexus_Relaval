# app_groq_ui.py (Enterprise Console UI with API Key Mock)

import streamlit as st
import asyncio
import time
from typing import List, Dict, Any

# Import the core APO Agent logic
try:
    from agents import apo_workflow
except ImportError:
    st.error("Error: Could not import 'apo_workflow' from agents.py.")
    st.stop()

# --- Initialize Session State for History and Setup ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'workflow_running' not in st.session_state:
    st.session_state.workflow_running = False
if 'api_key_status' not in st.session_state:
    st.session_state.api_key_status = "None Created"
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Playground"


# --- Core Workflow Runner (unchanged from previous version) ---
async def run_workflow_async(user_task, max_iters, quality_thresh):
    """Wrapper to call the asynchronous apo_workflow."""
    # (Implementation remains the same as previously defined)
    full_context_history = st.session_state.history
    user_msg_dict = {"role": "user", "content": user_task}
    full_context_history.append(user_msg_dict)
    
    try:
        results = await apo_workflow(
            abstract_task=user_task,
            full_context_history=full_context_history,
            document_context=None,
            video_url=None,
            max_iterations=max_iters,
            quality_threshold=quality_thresh
        )
        st.session_state.history.append({"role": "assistant", "content": results['final_output']})
        return results
    except Exception as e:
        st.error(f"Execution Error: {e}")
        return {"final_output": f"CRITICAL WORKFLOW FAILURE: {e}", "critic_score": 0.0, "critic_comments": [], "execution_time_seconds": 0}


# --- UI Page Definitions ---

def playground_page():
    """Renders the main agent execution interface."""
    
    st.title("⚡ Playground")
    st.markdown("Run your task with the **APO Agent Orchestrator** and monitor the refinement loop.")
    
    # Configuration Column (Mimics the controls sidebar of LLM platforms)
    with st.sidebar:
        st.header("⚙️ Model Configuration")
        st.selectbox("Model Selector", ["APO Agent Orchestrator v1"], index=0)
        
        st.markdown("#### **APO Refinement Parameters**")
        max_iterations = st.number_input(
            "Max Refinement Iterations",
            min_value=1, max_value=5, value=3,
        )
        quality_threshold = st.slider(
            "Quality Threshold (Compliance)",
            min_value=0.7, max_value=1.0, value=0.97, step=0.01,
        )
        st.markdown("---")
        if st.button("Clear Conversation"):
            st.session_state.history = []
            st.experimental_rerun()
            
    
    # Input/Output Split
    col_input, col_output = st.columns(2)

    with col_input:
        st.subheader("User Input")
        user_task = st.text_area(
            "Enter your task/prompt:",
            height=300,
            placeholder="e.g., Generate a Python script with 10 classes to manage customer orders and inventory..."
        )
        
        execute_button = st.button("🚀 Run Orchestrator", disabled=st.session_state.workflow_running, use_container_width=True)

    with col_output:
        st.subheader("Agent Response")
        final_output_placeholder = st.empty()


    # Execution Logic
    if execute_button and user_task:
        st.session_state.start_time = time.time()
        st.session_state.workflow_running = True
        final_output_placeholder.markdown("### Running...")
        
        with st.spinner("Executing Multi-Agent Workflow..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            final_results = loop.run_until_complete(
                run_workflow_async(user_task, max_iterations, quality_threshold)
            )
            
        st.session_state.workflow_running = False
        
        # Display Results
        with col_output:
            final_output_placeholder.code(final_results['final_output'], language=final_results.get('output_type', 'text'))
            
            st.markdown("#### **Performance & Metrics**")
            col_perf1, col_perf2, col_perf3 = st.columns(3)
            col_perf1.metric("Execution Time", f"{final_results.get('execution_time_seconds', 0.0):.2f}s")
            col_perf2.metric("Final Score", f"{final_results.get('critic_score', 0.0):.2f}")
            col_perf3.metric("Iterations Used", final_results.get('iterations', 1))

        # Audit Trail
        st.markdown("---")
        with st.expander("🔍 Agent Audit Trail (Planner & Critic Logs)"):
            st.markdown("#### **LLM-1 (Planner) Optimized Prompt**")
            st.code(final_results['optimized_prompt'])
            
            st.markdown("#### **LLM-3 (Critic) Review**")
            if final_results.get('critic_comments'):
                for comment in final_results['critic_comments']:
                    status = "✅ PASS" if comment['score'] >= quality_threshold else "⚠️ FAIL"
                    st.info(f"**Iteration {comment['iteration']} | Score: {comment['score']:.2f} {status}**\n\n> {comment['comment']}")
            else:
                st.warning("No critique comments available.")

    elif execute_button and not user_task:
        st.warning("Please enter a task.")

def api_keys_page():
    """Renders the simulated API Key management page."""
    
    st.title("🔑 API Keys")
    st.markdown("Manage your project API keys for external access to the APO Agent Orchestrator.")
    st.markdown("---")
    
    st.markdown("### **Generate New Key**")
    
    key_name = st.text_input(
        "Key Name", 
        placeholder="e.g., production-app-key"
    )
    
    col_create, col_status = st.columns([1, 2])
    
    if col_create.button("Create API Key"):
        if key_name:
            # Simulate key generation (transient display)
            generated_key = f"gsk_apo_{hash(key_name + str(time.time()))}"[:25] + "..."
            st.session_state.api_key_status = f"Key created successfully: **{generated_key}**"
            st.warning("⚠️ **IMPORTANT:** Copy this key now! You cannot view it again.")
        else:
            st.error("Please enter a key name.")
            
    col_status.metric("API Key Status", st.session_state.api_key_status)

    st.markdown("---")
    st.markdown("### **Existing Keys**")
    
    # Mock table data structure similar to Groq's console
    mock_keys = {
        "Name": ["dev-testing-key", "website-app-key"],
        "Created": ["2025-11-01", "2025-12-01"],
        "Last Used": ["2025-12-12 10:30", "2025-12-05 08:00"],
        "Status": ["Active", "Active"],
        "Usage (24hrs)": ["150 requests", "3,200 requests"]
    }
    st.dataframe(mock_keys, use_container_width=True)
    st.caption("Only team owners or users with the developer role may create or manage API keys.")

# --- Main Application Logic ---

st.set_page_config(
    page_title="APO Enterprise Console",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Top Navigation (Mimicking the console navbar)
st.sidebar.header("APO Console")
selected_page = st.sidebar.radio(
    "Navigation", 
    ["Playground", "API Keys", "Usage Dashboard (Mock)"],
    index=0
)

# 2. Page Router
if selected_page == "Playground":
    playground_page()
elif selected_page == "API Keys":
    api_keys_page()
else:
    st.title("📈 Usage Dashboard (Mock)")
    st.info("This is where charts and usage data would be displayed in an enterprise console.")

st.markdown("---")
st.caption("UI designed to mimic enterprise LLM consoles (Groq/OpenAI).")
