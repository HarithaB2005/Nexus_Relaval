# NexusAI API Key Usage - Simple Like Groq

**Your API key works exactly like Groq - simple and straightforward.**

## 🔑 How It Works (Just Like Groq)

### 1. **Get API Key**
```bash
# User gets API key from NexusAI dashboard
# Example: api_key_abc123xyz789
```

### 2. **Use API Key (Streamlit Demo)**
```python
# User enters API key in sidebar
api_key = "api_key_abc123xyz789"

# Ask a medical question
question = "I have chest pain, what should I do?"

# Send to API with Bearer token
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

### 3. **Backend Process (Automatic)**
```
Backend receives API key
    ↓
Validates API key (checks if valid & active)
    ↓
Retrieves user from database
    ↓
Runs APO Workflow:
  - Pathfinder (detects broad vs specific)
  - Clarifier (extracts intent & context)
  - Planner (creates plan)
  - Executor (generates response using Groq)
  - Critic (scores quality 0.0-1.0)
    ↓
Increments usage count
    ↓
Returns response with quality score
```

### 4. **Get Response Back**
```json
{
  "final_response": "Medical guidance with specific recommendations...",
  "critic_score": 0.92,
  "num_iterations": 2,
  "active_role": "Emergency Medicine Specialist",
  "tokens_used": 450,
  "cost_usd": "0.00090"
}
```

### 5. **Usage Tracking (Automatic)**
```
Each request:
  ✓ Increments usage counter
  ✓ Records tokens used
  ✓ Calculates cost
  ✓ Checks against plan limit
  ✓ Stores audit trail
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Generate API Key
```bash
# User logs in to NexusAI dashboard
# Clicks "Create API Key"
# Copy: api_key_xxxxxxxxxxxxxxxx
```

### Step 2: Open Streamlit Demo
```bash
streamlit run streamlit_demo.py
```

### Step 3: Enter API Key & Ask Question
1. Paste API key in sidebar (password field)
2. Type medical question
3. Click "Analyze & Compare"
4. See result with quality score & usage tracked ✓

**That's it! No complex setup needed.**

---

## 🔐 What Your API Key Grants

| Feature | Status |
|---------|--------|
| Full APO Workflow Access | ✅ |
| 4-Agent Optimization | ✅ |
| Groq LLM Processing | ✅ |
| Quality Scoring (0.0-1.0) | ✅ |
| Usage Tracking | ✅ |
| Rate Limiting (120 req/min) | ✅ |
| Plan Limits Enforcement | ✅ |
| Audit Trail | ✅ |
| Cost Tracking | ✅ |

---

## 📊 Usage Tracking

### In Streamlit Demo:
```
Session Usage: 3 requests
Total Requests: 3
API Key: api_key_abc***
Timestamp: 14:23:45
Quality Score: 0.92/1.0
```

### In Backend Database:
```sql
-- Automatically tracked
INSERT INTO usage_tracking (
  client_id,
  requests_count,
  tokens_count,
  cost_usd,
  created_at
) VALUES (...)
```

---

## 🎯 Endpoints

### Primary Endpoint (API Key Protected)
```
POST /api/v1/generate-prompt
Authorization: Bearer {api_key}

Request:
{
  "messages": [{"role": "user", "content": "question"}],
  "max_iterations": 3,
  "quality_threshold": 0.85,
  "document_context": null
}

Response:
{
  "final_response": "...",
  "critic_score": 0.92,
  "num_iterations": 2,
  "active_role": "Medical Role"
}
```

---

## ✅ How It's Like Groq

| Aspect | Groq | NexusAI |
|--------|------|---------|
| API Key Auth | ✓ Simple Bearer token | ✓ Simple Bearer token |
| Usage Tracking | ✓ Automatic per request | ✓ Automatic per request |
| Response Time | ✓ Fast (1-5 sec) | ✓ Fast (1-5 sec) |
| Cost Tracking | ✓ Per tokens | ✓ Per tokens + iterations |
| Rate Limiting | ✓ Yes | ✓ Yes (120 req/min) |
| Plan Limits | ✓ Yes | ✓ Yes (respects plan) |
| Audit Trail | ✓ Detailed logs | ✓ Detailed logs |
| Easy Integration | ✓ Very simple | ✓ Very simple |

---

## 🔧 Integration Examples

### Python (Using NexusAI API Key)
```python
import requests

api_key = "api_key_your_key_here"
question = "I have a cold, what should I do?"

response = requests.post(
    "http://localhost:8000/api/v1/generate-prompt",
    json={
        "messages": [{"role": "user", "content": question}],
        "max_iterations": 3,
        "quality_threshold": 0.85
    },
    headers={"Authorization": f"Bearer {api_key}"}
)

data = response.json()
print(f"Response: {data['final_response']}")
print(f"Quality: {data['critic_score']:.2f}/1.0")
print(f"Iterations: {data['num_iterations']}")
```

### JavaScript
```javascript
const apiKey = "api_key_your_key_here";
const question = "I have chest pain";

const response = await fetch(
  "http://localhost:8000/api/v1/generate-prompt",
  {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      messages: [{ role: "user", content: question }],
      max_iterations: 3,
      quality_threshold: 0.85
    })
  }
);

const data = await response.json();
console.log(data.final_response);
console.log(`Quality: ${data.critic_score}/1.0`);
```

### cURL
```bash
curl -X POST http://localhost:8000/api/v1/generate-prompt \
  -H "Authorization: Bearer api_key_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I have a cold"}],
    "max_iterations": 3,
    "quality_threshold": 0.85
  }'
```

---

## 🎯 Simple Flow Diagram

```
┌─────────────────────────────────────────────────┐
│           User (Streamlit Demo)                 │
│  Enter API Key + Medical Question               │
└──────────────────┬──────────────────────────────┘
                   │
                   │ POST /api/v1/generate-prompt
                   │ Authorization: Bearer {api_key}
                   ↓
┌─────────────────────────────────────────────────┐
│          NexusAI Backend (FastAPI)              │
│  ✓ Validate API Key                            │
│  ✓ Check User & Plan Limits                    │
│  ✓ Run APO Workflow (4-agent)                  │
│  ✓ Use Groq for LLM Processing                 │
│  ✓ Score Quality with Critic                   │
│  ✓ Track Usage in Database                     │
└──────────────────┬──────────────────────────────┘
                   │
                   │ Response with:
                   │ - final_response
                   │ - critic_score
                   │ - num_iterations
                   │ - active_role
                   ↓
┌─────────────────────────────────────────────────┐
│           User (Streamlit Demo)                 │
│  See Response + Quality Score + Usage Tracked   │
│  ✓ Usage Count Incremented                     │
│  ✓ Cost Calculated & Stored                    │
│  ✓ Audit Trail Created                         │
└─────────────────────────────────────────────────┘
```

---

## 🚀 That's It!

Your API key works exactly like Groq:
1. **Enter API key** - Simple bearer token auth
2. **Send request** - Question goes to backend
3. **Get response** - Medical guidance with quality score
4. **Usage tracked** - Automatic per request

**No complexity. Just like Groq.** ✅

---

## 📞 Support

- **API Documentation:** See `/docs` endpoint (Swagger UI)
- **Issues:** Check backend logs
- **Rate Limits:** 120 requests/minute per API key
- **Plan Limits:** Checked automatically per request
- **Billing:** Per 1000 tokens used + iterations

---

**Last Updated:** December 30, 2025  
**API Version:** v1  
**Status:** Production Ready ✅
