"""
Nexus Releval SDK Client
Simple, production-ready client for AI auditing and prompt optimization

Quick Start (3 lines of code):
    import nexus_releval
    client = nexus_releval.Client(api_key="relevo_sk_your_key")
    result = client.verify("Your prompt here...")
"""

import requests
from typing import List, Dict, Any, Optional, Union
import time


class Client:
    """Nexus Releval API Client - Simple interface for AI auditing"""
    
    def __init__(
        self, 
        api_key: str,
        base_url: str = "https://api.nexus-releval.com",
        timeout: int = 30
    ):
        """
        Initialize Nexus Releval client.
        
        Args:
            api_key: Your Nexus Releval API key (get from dashboard)
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds (default: 30)
        
        Example:
            >>> client = Client(api_key="relevo_sk_abc123")
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Internal request handler with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method, url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {endpoint} timed out after {self.timeout}s")
        
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            raise Exception(f"API Error ({e.response.status_code if e.response else 'Unknown'}): {error_detail}")
        
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    # =============================================
    # CORE API METHODS
    # =============================================
    
    def verify(self, prompt: str, document_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify and optimize a prompt using the APO (Agent-based Prompt Optimization) workflow.
        This is the main method you'll use - ultra-simple interface.
        
        Args:
            prompt: The prompt/task to verify and optimize
            document_context: Optional document text to include for context
        
        Returns:
            Dictionary with:
                - final_output: The optimized response
                - critic_score: Quality score (0.0-1.0)
                - iterations: Number of optimization iterations
                - output_type: Type of output generated
        
        Example:
            >>> result = client.verify("Write a safe medical recommendation")
            >>> print(result['final_output'])
            >>> print(f"Quality score: {result['critic_score']}")
        """
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "document_context": document_context,
            "max_iterations": 3,
            "quality_threshold": 0.9
        }
        
        return self._request("POST", "/api/v1/generate-prompt", json=payload)
    
    def verify_batch(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """
        Verify multiple prompts in a batch.
        
        Args:
            prompts: List of prompts to verify
        
        Returns:
            List of verification results
        """
        results = []
        for prompt in prompts:
            try:
                result = self.verify(prompt)
                results.append({"prompt": prompt, "result": result, "status": "success"})
            except Exception as e:
                results.append({"prompt": prompt, "error": str(e), "status": "failed"})
        
        return results
    
    def optimize(
        self,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        document_context: Optional[str] = None,
        max_iterations: int = 3,
        quality_threshold: float = 0.9
    ) -> Dict[str, Any]:
        """
        Run full APO optimization workflow with conversation context.
        
        Args:
            prompt: The user prompt
            messages: Conversation history (list of {"role": "...", "content": "..."})
            document_context: Reference document text
            max_iterations: Maximum optimization iterations (1-5)
            quality_threshold: Minimum quality score (0.0-1.0)
        
        Returns:
            Full optimization result with quality metrics
        """
        if not messages:
            messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "messages": messages,
            "document_context": document_context,
            "max_iterations": max_iterations,
            "quality_threshold": quality_threshold
        }
        
        return self._request("POST", "/api/v1/generate-prompt", json=payload)
    
    def get_audit_log(self, days: int = 30) -> Dict[str, Any]:
        """
        Get your governance audit log (Registry of Truth).
        
        Args:
            days: Number of days of history to retrieve
        
        Returns:
            Dictionary with:
                - total_rejections: Number of times outputs were rejected
                - hallucinations_blocked: Count of detected hallucinations
                - quality_issues_found: Count of quality problems caught
                - saved_errors: List of recurring error patterns caught
        """
        return self._request("GET", f"/api/v1/audit/summary?days={days}")
    
    def get_saved_errors(self) -> List[Dict[str, Any]]:
        """
        Get "Saved Errors" - the recurring issues your system has blocked.
        
        Returns:
            List of error patterns with:
                - description: What the error was
                - impact: 'critical', 'high', 'medium', or 'low'
                - blocked_count: How many times it was caught
        """
        result = self._request("GET", "/api/v1/audit/events?event_type=quality_reject&limit=100")
        return result.get("events", [])
    
    def get_governance_dashboard(self) -> Dict[str, Any]:
        """
        Get full governance dashboard data (Registry of Truth).
        
        Returns:
            Complete governance metrics including:
                - total_events: Total audit events
                - hallucinations_blocked: Count of hallucinations caught
                - quality_issues_found: Count of quality problems
                - events_by_severity: Breakdown by severity level
                - saved_errors_count: Number of recurring error patterns
        """
        return self._request("GET", "/api/v1/audit/summary")
    
    # =============================================
    # PRIVACY-BY-DESIGN API METHODS
    # =============================================
    
    def enable_zero_data_retention(self) -> Dict[str, Any]:
        """
        Enable Zero-Data-Retention (ZDR) mode.
        
        In ZDR mode:
        - Requests are processed in volatile memory only
        - No persistent logs are created
        - Data is "forgotten" immediately after response
        
        Perfect for: HIPAA, GDPR, banking, classified data
        
        Returns:
            Configuration confirmation
        """
        return self._request(
            "POST",
            "/api/v1/privacy/settings",
            json={
                "data_retention_mode": "zero-retention",
                "log_usage": False,
                "log_inputs": False,
                "log_outputs": False
            }
        )
    
    def enable_local_inference(self, inference_url: str) -> Dict[str, Any]:
        """
        Enable Local Inference Support - run the auditor on your own servers.
        
        In Local Inference mode:
        - Your data never leaves your infrastructure
        - You run the Nexus auditor on your own servers
        - You get all governance benefits without cloud processing
        
        Args:
            inference_url: URL of your local Nexus Releval Auditor deployment
        
        Returns:
            Deployment configuration
        
        Example:
            >>> client.enable_local_inference("https://auditor.internal.mycompany.com")
        """
        return self._request(
            "POST",
            "/api/v1/privacy/settings",
            json={
                "data_retention_mode": "local-inference-only",
                "local_inference_enabled": True,
                "local_inference_api_url": inference_url
            }
        )
    
    def get_privacy_settings(self) -> Dict[str, Any]:
        """Get current privacy configuration"""
        return self._request("GET", "/api/v1/privacy/settings")
    
    # =============================================
    # UTILITY METHODS
    # =============================================
    
    def health_check(self) -> Dict[str, str]:
        """
        Check if the API is reachable.
        
        Returns:
            {"status": "ok"} if healthy
        """
        return self._request("GET", "/api/health")
    
    def set_timeout(self, timeout: int) -> None:
        """Update request timeout"""
        self.timeout = timeout
    
    def set_base_url(self, base_url: str) -> None:
        """Update base URL"""
        self.base_url = base_url.rstrip("/")


# =============================================
# BACKWARD COMPATIBILITY
# =============================================
class NexusClient(Client):
    """Alias for backward compatibility"""
    pass

    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_iterations: int = 3,
        quality_threshold: float = 0.9,
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response with quality auditing.
        
        Args:
            messages: Conversation history [{"role": "user", "content": "..."}]
            max_iterations: Max optimization loops (1-5)
            quality_threshold: Min quality score (0.0-1.0)
            document_context: Optional document text for context
        
        Returns:
            Dict with final_output, critic_score, iterations, etc.
        
        Example:
            >>> result = client.generate(
            ...     messages=[{"role": "user", "content": "Patient has chest pain"}]
            ... )
            >>> print(result["final_output"])
        """
        payload = {
            "messages": messages,
            "max_iterations": max_iterations,
            "quality_threshold": quality_threshold
        }
        
        if document_context:
            payload["document_context"] = document_context
        
        return self._request("POST", "/api/v1/generate-prompt", json=payload)
    
    def chat(self, message: str, **kwargs) -> str:
        """
        Simple chat interface (single message).
        
        Args:
            message: User message
            **kwargs: Additional arguments for generate()
        
        Returns:
            AI response text
        
        Example:
            >>> response = client.chat("What are symptoms of flu?")
            >>> print(response)
        """
        result = self.generate(
            messages=[{"role": "user", "content": message}],
            **kwargs
        )
        return result.get("final_output", "")
    
    def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics for your account"""
        return self._request("GET", "/usage/summary")
    
    def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


class Auditor(NexusClient):
    """
    High-level auditor client with safety verification.
    Use this for medical/financial/legal content validation.
    """
    
    def verify(
        self, 
        content: str,
        context: Optional[str] = None,
        min_score: float = 0.94
    ) -> Dict[str, Any]:
        """
        Verify content safety and quality with AI auditing.
        
        Args:
            content: Content to verify (medical advice, financial info, etc.)
            context: Optional background context
            min_score: Minimum acceptable quality score (default: 0.94)
        
        Returns:
            {
                "safe": bool,
                "score": float,
                "response": str,
                "warnings": List[str]
            }
        
        Example:
            >>> auditor = Auditor(api_key="relevo_sk_abc123")
            >>> result = auditor.verify("Patient has chest pain, take aspirin")
            >>> if result["safe"] and result["score"] >= 0.94:
            ...     print(result["response"])
        """
        start_time = time.time()
        
        result = self.generate(
            messages=[{"role": "user", "content": content}],
            document_context=context,
            quality_threshold=min_score,
            max_iterations=3
        )
        
        score = result.get("critic_score", 0.0)
        is_safe = score >= min_score
        warnings = []
        
        # Extract warnings from critic comments
        for comment in result.get("critic_comments", []):
            if comment.get("score", 1.0) < min_score:
                warnings.append(comment.get("comments", "Quality below threshold"))
        
        return {
            "safe": is_safe,
            "score": score,
            "response": result.get("final_output", ""),
            "warnings": warnings,
            "iterations": result.get("iterations", 1),
            "execution_time": time.time() - start_time
        }
    
    def batch_verify(
        self,
        contents: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Verify multiple pieces of content.
        
        Args:
            contents: List of content strings to verify
            **kwargs: Arguments passed to verify()
        
        Returns:
            List of verification results
        
        Example:
            >>> results = auditor.batch_verify([
            ...     "Take 500mg aspirin for headache",
            ...     "Invest all savings in crypto"
            ... ])
            >>> for r in results:
            ...     print(f"Safe: {r['safe']}, Score: {r['score']}")
        """
        return [self.verify(content, **kwargs) for content in contents]
