# Nexus Releval Python SDK

Official Python SDK for the Nexus Releval AI Auditor API - 5-minute integration for AI safety and quality verification.

## 🚀 Quick Start

### Installation

```bash
pip install nexus-releval
```

### 5-Minute Example

```python
from nexus_releval import Auditor

# Initialize with your API key
auditor = Auditor(api_key="relevo_sk_your_key_here")

# Verify medical content
result = auditor.verify("Patient has chest pain, should take aspirin immediately")

if result["safe"] and result["score"] >= 0.94:
    print(f"✓ Safe: {result['response']}")
    print(f"Quality Score: {result['score']:.2f}")
else:
    print(f"✗ Unsafe: {result['warnings']}")
```

## 📚 Usage

### Simple Chat

```python
from nexus_releval import NexusClient

client = NexusClient(api_key="relevo_sk_abc123")
response = client.chat("What are symptoms of the flu?")
print(response)
```

### Advanced Verification

```python
from nexus_releval import Auditor

auditor = Auditor(api_key="relevo_sk_abc123")

# Verify with context
result = auditor.verify(
    content="Prescribe 500mg ibuprofen for fever",
    context="Patient is 35 years old, no allergies, no existing conditions",
    min_score=0.95
)

print(f"Safe: {result['safe']}")
print(f"Score: {result['score']}")
print(f"Response: {result['response']}")
```

### Batch Processing

```python
contents = [
    "Take 2 aspirin for headache",
    "Invest 100% in cryptocurrency",
    "Normal blood pressure is 120/80"
]

results = auditor.batch_verify(contents)

for i, r in enumerate(results):
    print(f"Content {i+1}: Safe={r['safe']}, Score={r['score']:.2f}")
```

### Conversation History

```python
messages = [
    {"role": "user", "content": "I have a fever"},
    {"role": "assistant", "content": "What's your temperature?"},
    {"role": "user", "content": "101.5°F"}
]

result = client.generate(messages=messages, quality_threshold=0.92)
print(result["final_output"])
```

## 🔑 Authentication

Get your API key from the [Nexus Releval Dashboard](http://localhost:8000):

1. Register at `/auth/register`
2. Login to get JWT token
3. Generate API key from dashboard
4. Use in SDK: `Auditor(api_key="relevo_sk_...")`

## 📊 API Reference

### `Auditor` Class

High-level client for content verification.

#### `verify(content, context=None, min_score=0.94)`
Verify content safety and quality.

**Returns:**
```python
{
    "safe": bool,           # True if score >= min_score
    "score": float,         # Quality score (0.0-1.0)
    "response": str,        # AI-generated response
    "warnings": List[str],  # Quality warnings
    "iterations": int,      # Optimization loops used
    "execution_time": float # Time in seconds
}
```

#### `batch_verify(contents, **kwargs)`
Verify multiple contents at once.

### `NexusClient` Class

Low-level API client.

#### `generate(messages, max_iterations=3, quality_threshold=0.9, document_context=None)`
Generate AI response with quality auditing.

#### `chat(message, **kwargs)`
Simple single-message interface.

#### `get_usage()`
Get account usage statistics.

#### `health_check()`
Check API availability.

## 🏥 Use Cases

### Medical Consultancy
```python
result = auditor.verify("Patient presents with chest pain and shortness of breath")
if result["safe"]:
    print(result["response"])  # Medical-grade advice
```

### Financial Compliance
```python
result = auditor.verify("Recommend diversified portfolio with 60/40 stock/bond split")
# Ensures no hallucinated financial advice
```

### Legal Document Review
```python
result = auditor.verify(
    content="Draft employment contract clause",
    min_score=0.96  # Higher threshold for legal
)
```

## ⚙️ Configuration

```python
client = Auditor(
    api_key="relevo_sk_abc123",
    base_url="https://api.nexusreleval.com",  # Production URL
    timeout=30  # Request timeout in seconds
)
```

## 🔒 Security

- All requests use HTTPS in production
- API keys are never logged or stored
- Zero data retention mode available (enterprise)

## 📈 Rate Limits

- Free tier: 50 requests/month
- Pro tier: 1,000 requests/month
- Enterprise: Custom limits

Check usage: `client.get_usage()`

## 🐛 Error Handling

```python
try:
    result = auditor.verify("content")
except TimeoutError:
    print("Request timed out")
except Exception as e:
    print(f"Error: {e}")
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Support

- Documentation: https://docs.nexusreleval.com
- Email: support@nexusreleval.com
- Issues: https://github.com/nexusreleval/python-sdk/issues
