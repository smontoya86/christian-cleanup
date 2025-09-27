# RunPod Configuration Guide

## Overview
The intelligent LLM router is now configured to use:
- **RunPod** (Priority 1): Llama 3.1:70b for high-performance analysis
- **Ollama** (Priority 2): Llama 3.1:8b for local fallback

## RunPod Setup

### 1. Create RunPod Instance
1. Go to [RunPod.io](https://runpod.io)
2. Create a new serverless endpoint or pod
3. Use a Llama 3.1:70b template (e.g., `runpod/llama-3.1-70b-instruct`)
4. Note your endpoint URL

### 2. Environment Variables
Add these to your `.env` file:

```bash
# RunPod Configuration
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/openai/v1
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_MODEL=llama3.1:70b

# Ollama Configuration (already working)
OLLAMA_MODEL=llama3.1:8b
```

### 3. Current Status
- ✅ **Ollama**: Working with Llama 3.1:8b at `http://llm:8000`
- 📝 **RunPod**: Stubbed - will activate when `RUNPOD_ENDPOINT` is set

### 4. Router Behavior
1. **If RunPod is configured and healthy**: Uses Llama 3.1:70b for better analysis quality
2. **If RunPod is unavailable**: Automatically falls back to local Ollama Llama 3.1:8b
3. **Health checks**: Runs every 5 minutes to detect provider availability

### 5. Testing
Once configured, you can check the router status at:
```
GET /api/llm/status
```

And force a specific provider (admin only):
```
POST /api/llm/force-provider
{
  "provider": "runpod"
}
```

## Benefits
- **High Performance**: 70b model for complex theological analysis
- **Reliability**: Local fallback ensures service continuity
- **Cost Efficiency**: Only uses RunPod when needed
- **Automatic Switching**: No manual intervention required
