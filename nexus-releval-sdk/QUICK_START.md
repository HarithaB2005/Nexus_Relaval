# Nexus Releval SDK - Quick Start Guide

**Get started in 5 minutes with 3 lines of Python code.**

## Installation

```bash
pip install nexus-releval
```

## 3-Line Quick Start

```python
import nexus_releval
client = nexus_releval.Client(api_key="relevo_sk_your_key_here")
result = client.verify("Your prompt here...")
```

## Authentication

Get your API key from the [Nexus Releval Dashboard](https://dashboard.nexus-releval.com)

```python
import nexus_releval

client = nexus_releval.Client(
    api_key="relevo_sk_abc123",  # Your API key
    base_url="https://api.nexus-releval.com"  # Production URL
)
```

## Core Usage

### Verify a Single Prompt

```python
result = client.verify("Write a safe medical dosage recommendation for patient X")

# Access results
print(result['final_output'])  # The optimized response
print(result['critic_score'])  # Quality score (0.0-1.0)
print(result['iterations'])    # Number of optimization passes
```

### Verify Multiple Prompts (Batch)

```python
prompts = [
    "Generate a financial report",
    "Draft a legal contract",
    "Write code for user authentication"
]

results = client.verify_batch(prompts)

for item in results:
    if item['status'] == 'success':
        print(f"✓ {item['prompt']}: Score {item['result']['critic_score']}")
    else:
        print(f"✗ {item['prompt']}: {item['error']}")
```

### Full Optimization with Context

```python
result = client.optimize(
    prompt="Summarize this document",
    document_context="The full text of the document goes here...",
    max_iterations=5,  # More iterations = higher quality
    quality_threshold=0.95  # Minimum acceptable score
)

print(f"Quality Score: {result['critic_score']}")
print(f"Output: {result['final_output']}")
```

## Registry of Truth (Governance Dashboard)

The Registry of Truth is a live feed showing every time your Nexus Auditor has blocked a hallucinated or low-quality response. Perfect for CTOs and Legal teams.

### Get Governance Summary

```python
# Get all governance metrics for the last 30 days
summary = client.get_audit_log(days=30)

print(f"Total Rejections: {summary['total_rejections']}")
print(f"Hallucinations Blocked: {summary['hallucinations_blocked']}")
print(f"Quality Issues Found: {summary['quality_issues_found']}")
print(f"Safety Violations: {summary['safety_violations_detected']}")
print(f"Saved Error Patterns: {summary['saved_errors_count']}")
```

### Get Recurring Error Patterns ("Saved Errors")

```python
# The most valuable insights - recurring issues your system has caught
saved_errors = client.get_saved_errors()

for error in saved_errors:
    print(f"{error['description']}")
    print(f"  Impact: {error['impact']}")
    print(f"  Blocked {error['blocked_count']} times")
    print()

# Example output:
# "Blocked high-risk medical dosage recommendation"
#   Impact: critical
#   Blocked 42 times
```

### Full Governance Dashboard

```python
dashboard = client.get_governance_dashboard()

print(f"Total Audit Events: {dashboard['total_events']}")
print(f"Average Quality Score: {dashboard['avg_quality_score']}")
print(f"Events by Type: {dashboard['events_by_severity']}")
print(f"Critical Events: {dashboard['critical_events']}")
```

## Privacy-by-Design (Data Sovereignty)

Nexus offers two powerful privacy modes to ensure your data never leaves your control.

### Zero-Data-Retention (ZDR) Mode

In ZDR mode, requests are processed in volatile memory and "forgotten" immediately.

```python
# Enable Zero-Data-Retention
client.enable_zero_data_retention()

# Now all requests are processed without persistent logs
result = client.verify("Sensitive information here...")

# Data is never retained - perfect for HIPAA, GDPR, classified data
```

### Local Inference Support

Run the Nexus Auditor on your own infrastructure. Your data never leaves your servers.

```python
# Deploy Nexus Auditor on your servers and enable local inference
client.enable_local_inference(
    inference_url="https://auditor.internal.mycompany.com"
)

# Verify privacy settings
settings = client.get_privacy_settings()
print(settings)
# Output: {
#   "data_retention_mode": "local-inference-only",
#   "local_inference_enabled": True,
#   "local_inference_api_url": "https://auditor.internal.mycompany.com"
# }
```

## Advanced Usage

### Custom Conversation Context

```python
# Include conversation history for better optimization
messages = [
    {"role": "system", "content": "You are a helpful medical advisor"},
    {"role": "user", "content": "What is a safe dosage?"},
    {"role": "assistant", "content": "Here are the guidelines..."},
    {"role": "user", "content": "But what about patients over 65?"}
]

result = client.optimize(
    prompt="Provide a specific recommendation",
    messages=messages
)
```

### Health Check

```python
# Verify the API is healthy
health = client.health_check()
print(health)  # {"status": "ok"}
```

## Error Handling

```python
try:
    result = client.verify("Your prompt")
except TimeoutError:
    print("Request timed out - try again or increase timeout")
except Exception as e:
    print(f"API Error: {e}")
```

## Configuration

```python
import nexus_releval

client = nexus_releval.Client(api_key="relevo_sk_abc123")

# Change timeout (default 30s)
client.set_timeout(60)

# Change API endpoint (for self-hosted)
client.set_base_url("https://nexus.mycompany.com")
```

## Response Format

All methods return dictionaries with the following structure:

```python
{
    "user_task": "The original prompt",
    "role_selected": "The detected role/context",
    "optimized_prompt": "The refined prompt",
    "final_output": "The AI-generated response",
    "output_type": "text|code|email|etc",
    "execution_time_seconds": 2.34,
    "iterations": 3,
    "critic_score": 0.97,
    "critic_comments": [
        {"issue": "description", "severity": "medium"}
    ]
}
```

## Best Practices

1. **Always check the critic_score** - It tells you how confident Nexus is in the output
2. **Use governance dashboard regularly** - Track what your system is catching
3. **Enable ZDR for sensitive data** - Medical, financial, legal, classified data
4. **Batch verify related prompts** - More efficient than individual calls
5. **Monitor saved errors** - They reveal patterns you should address

## Support

- Documentation: https://docs.nexus-releval.com
- API Reference: https://api.nexus-releval.com/docs
- Issues: https://github.com/nexus-releval/sdk-python/issues
- Email: support@nexus-releval.com

## License

MIT License - See LICENSE file for details
