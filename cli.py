# cli.py
import asyncio
import sys
from agents import apo_workflow

def main():
    """
    Handles command-line input and runs the asynchronous workflow, then prints the results.
    """
    print("==============================================")
    print(" 💡 Universal Optimization Agent (CLI Mode) ")
    print("==============================================")
    print("Enter any vague or general request (finish with Ctrl+D [Linux/Mac] or Ctrl+Z then Enter [Windows]):")
    
    # Read multiline input from standard input until EOF
    lines = sys.stdin.readlines()
    abstract_task = ''.join(lines).strip()

    if not abstract_task:
        print("No task entered. Exiting.")
        return

    print("\n--- Running Optimization Workflow ---\n")
    results = None
    try:
        # Run the main asynchronous workflow and capture the results dictionary
        results = asyncio.run(apo_workflow(abstract_task))
        
        # --- Print Results ---
        if results:
            print("==============================================")
            print(f"| Role Selected: {results.get('role_selected', 'N/A')}")
            print(f"| Cycle Time:    {results.get('execution_time_seconds', 0):.2f} s")
            print(f"| Critic Score:  {results.get('critic_score', 'N/A')}")
            print(f"| Iterations:    {results.get('iterations', 0)}")
            print("==============================================")
            
            # Optimized Prompt
            print("\n>>> 1. Optimized Prompt:")
            print("----------------------------------------------")
            print(results.get('optimized_prompt', 'Optimization failed to generate a prompt.'))
            print("----------------------------------------------")

            # Final Output
            print("\n>>> 2. Final AI Output:")
            print(f"[Type: {results.get('output_type', 'text').upper()}]")
            print("----------------------------------------------")
            print(results.get('final_output', 'Agent failed to produce a final output.'))
            print("----------------------------------------------")

            # Critic History (for debugging/metrics)
            critic_comments = results.get("critic_comments", [])
            if critic_comments:
                print("\n>>> 3. Critic History:")
                for comment in critic_comments:
                    print(f"- Iteration {comment['iteration']} (Score: {comment['score']}): {comment['comment']}")
                print("----------------------------------------------")
        else:
            print("Workflow completed, but no results were returned.")

    except ImportError as e:
        print(f"\n--- Dependency Error ---")
        print(f"Failed to run due to missing dependency: {e}")
        print("Please ensure 'groq' and 'ollama' libraries are installed if you intend to use them.")
    except Exception as e:
        print(f"\n--- An unexpected error occurred ---")
        print(e)
        if results and results.get('final_output'):
             print(f"Partial result/Error output: {results['final_output']}")

if __name__ == "__main__":
    main()