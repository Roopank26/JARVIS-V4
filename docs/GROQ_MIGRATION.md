# Groq Migration Guide

**Date:** 2024-06-23  
**Migration:** Gemini → Groq

## Summary

JARVIS has been migrated from Google's Gemini API to Groq for faster, more cost-effective LLM inference while maintaining full backward compatibility.

## Why Groq?

| Feature | Gemini | Groq |
|---------|--------|------|
| Speed | ~5-10s | ~0.5-1s |
| Free Tier | Limited | Generous |
| API Stability | Good | Excellent |
| Setup | Complex | Simple |

## Files Modified

| File | Changes |
|------|---------|
| `jarvis/api/gemini.py` | Complete rewrite with Groq SDK |
| `jarvis/api/__init__.py` | Added GroqClient export |
| `jarvis/core/agent.py` | Changed default backend |
| `jarvis/core/config.py` | Updated default model |
| `requirements.txt` | Replaced google-genai with groq |
| `README.md` | Updated API key instructions |

## API Key Configuration

### Option 1: Environment Variable

```bash
export GROQ_API_KEY=gsk_your_key_here
```

### Option 2: Config File

```bash
mkdir -p ~/.jarvis
echo '{"groq_api_key": "gsk_your_key_here"}' > ~/.jarvis/api_keys.json
```

### Legacy Support

Existing `gemini_api_key` in config will still work as fallback.

## Model Changes

| Before | After |
|--------|-------|
| `gemini-2.0-flash` | `llama-3.3-70b-versatile` |

Groq models available:
- `llama-3.3-70b-versatile` (default, recommended)
- `llama-3.1-8b-instant`
- `mixtral-8x7b-32768`
- `gemma2-9b-it`

## Backward Compatibility

All existing code continues to work:

```python
# Old code still works
from jarvis.api import GeminiClient
client = GeminiClient()  # Now uses Groq internally

# New code
from jarvis.api import GroqClient
client = GroqClient()

# Simple client
from jarvis.api import SimpleLLMClient
client = SimpleLLMClient(backend="groq")
```

## Getting a Groq API Key

1. Visit: https://console.groq.com/keys
2. Create account (free)
3. Generate API key
4. Key format: `gsk_...`

## Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Test API manually
python -c "
from jarvis.api import SimpleLLMClient
import asyncio
async def test():
    client = SimpleLLMClient()
    result = await client.generate('Say hello')
    print(result)
asyncio.run(test())
"
```

## Troubleshooting

### "API client not available"

1. Check API key is set:
   ```bash
   echo $GROQ_API_KEY
   ```

2. Verify config file:
   ```bash
   cat ~/.jarvis/api_keys.json
   ```

3. Test SDK:
   ```bash
   python -c "from groq import Groq; print('OK')"
   ```

### Rate Limit Errors

Groq free tier has rate limits. If you hit them:
- Wait 1 minute between requests
- Consider upgrading to paid tier

## Remaining Gemini References

The following files contain legacy Gemini references (for backward compatibility only):

| File | Reference | Purpose |
|------|-----------|---------|
| `jarvis/core/agent.py` | `set_api_key("gemini", ...)` | Legacy config key |
| `jarvis/core/config.py` | `get_api_key(provider="gemini")` | Fallback support |

These are harmless and do not affect functionality.

## Rollback (If Needed)

To revert to Gemini:

```python
# Use Gemini backend explicitly
client = SimpleLLMClient(backend="gemini", api_key="your-gemini-key")
```

Note: Gemini integration requires `google-genai` package.
