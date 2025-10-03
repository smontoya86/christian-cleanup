# Environment Setup Notes

## Required Environment Variables

### OpenAI Fine-Tuned Model
```bash
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav
```

This fine-tuned model is required for the biblical discernment analysis system.

**Note**: If `OPENAI_MODEL` is not set, the system will incorrectly try to use Ollama/local LLM, causing analysis failures.

## Recent Fix (2025-10-03)
- Added `OPENAI_MODEL` to `.env` to fix song analysis failures
- Error was: `{"error":{"message":"model is required","type":"api_error"}}`
- Root cause: System defaulting to Ollama instead of OpenAI API

