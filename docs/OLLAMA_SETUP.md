# Ollama Local AI Setup Guide

JARVIS uses **Ollama** as the primary AI provider for local, fast, and private AI interactions.

## Overview

JARVIS implements a **Local-First AI Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                     JARVIS AI Stack                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   User Query                                                │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────┐                                      │
│   │ Intent Router   │ ─── Classifies query type            │
│   └────────┬────────┘                                      │
│            │                                               │
│            ▼                                               │
│   ┌─────────────────┐     ┌─────────────────────────┐    │
│   │ Model Selector   │────▶│ Reasoning (deepseek-r1) │    │
│   │ (Automatic)      │     │ General (qwen3)         │    │
│   └────────┬────────┘     └─────────────────────────┘    │
│            │                                               │
│            ▼                                               │
│   ┌─────────────────┐     ┌─────────────────────────┐    │
│   │ Provider Manager │────▶│ Ollama (Local) - FIRST   │    │
│   │                  │     │ Groq (Cloud) - FALLBACK │    │
│   └─────────────────┘     └─────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from [ollama.com/download](https://ollama.com/download)

### 2. Verify Installation
```bash
ollama --version
```

### 3. Download Models

JARVIS uses these models by default:

```bash
# General purpose model (default)
ollama pull qwen3:8b

# Reasoning/analysis model
ollama pull deepseek-r1:8b

# Alternative general model
ollama pull llama3.2:3b
```

### 4. Start Ollama Service

```bash
# Start Ollama server (runs on port 11434)
ollama serve

# Or run in background
nohup ollama serve > /dev/null 2>&1 &
```

### 5. Verify Models

```bash
ollama list
```

Expected output:
```
NAME                ID          SIZE      MODIFIED
qwen3:8b            a382b2d2... 4.7GB     2 hours ago
deepseek-r1:8b      6aa5c1d3... 4.6GB     2 hours ago
```

## Commands

### Provider Commands

| Command | Description |
|---------|-------------|
| `provider status` | Show current provider and model |
| `list models` | List available Ollama models |
| `show models` | Same as list models |
| `current model` | Show current model name |
| `switch provider qwen3` | Switch to qwen3:8b model |
| `switch provider deepseek` | Switch to deepseek-r1:8b model |
| `switch provider groq` | Switch to Groq cloud |
| `benchmark models` | Benchmark all available models |
| `compare qwen3 vs deepseek` | Compare two models |

### Examples

```
User: provider status
JARVIS:
[Provider Status]
========================================

OLLAMA:
  Status: ✓ PRIMARY
  Model: qwen3:8b
  Available models:
    • qwen3:8b ← DEFAULT
    • deepseek-r1:8b ← REASONING

GROQ:
  Status: ○ available
  Model: llama-3.3-70b-versatile
```

```
User: switch provider deepseek
JARVIS: Provider switched successfully to deepseek-r1:8b
```

```
User: benchmark models
JARVIS:
[Benchmark Results]
========================================

ollama/qwen3:8b:
  Latency: 2.3s
  Tokens: 45
  Provider: Ollama

ollama/deepseek-r1:8b:
  Latency: 3.1s
  Tokens: 67
  Provider: Ollama
```

## Automatic Model Selection

JARVIS automatically selects the best model for your task:

| Task Type | Keywords | Model |
|-----------|----------|-------|
| General | chat, explain, help | qwen3:8b |
| Reasoning | step by step, solve, calculate, analyze | deepseek-r1:8b |
| Coding | code, function, algorithm | qwen2.5-coder |

### Examples

```
User: Explain neural networks
→ Routes to: qwen3:8b (general explanation)

User: Solve this algorithm problem step by step
→ Routes to: deepseek-r1:8b (reasoning)

User: Write a Python function to sort a list
→ Routes to: qwen3:8b (coding/general)
```

## Offline Mode

When Ollama is unavailable, JARVIS automatically falls back to **Groq Cloud**:

```
[Provider] Ollama: unavailable
[Provider] Falling back to Groq
```

### Groq Fallback

- **Model**: llama-3.3-70b-versatile
- **API Key**: Required in environment or config
- **Internet**: Required for cloud fallback

## Configuration

### Environment Variables

```bash
# Optional: Ollama custom URL
OLLAMA_BASE_URL=http://localhost:11434

# Required for cloud fallback
GROQ_API_KEY=your_groq_api_key
```

### Model Configuration

```python
# In code
from jarvis.api.providers import ProviderManager, ProviderType, LLMConfig

manager = ProviderManager()
config = LLMConfig(
    provider=ProviderType.OLLAMA,
    model="qwen3:8b",
    base_url="http://localhost:11434"
)
```

## Troubleshooting

### Ollama Not Detected

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Verify models
ollama list
```

### Model Not Found

```bash
# Pull the missing model
ollama pull qwen3:8b
ollama pull deepseek-r1:8b

# Verify
ollama list
```

### Connection Errors

1. Check Ollama service: `curl localhost:11434`
2. Restart Ollama: `pkill ollama && ollama serve`
3. Check firewall: Ensure port 11434 is accessible

### Slow Responses

- Use smaller models for faster responses
- Close other resource-intensive applications
- Consider using qwen3:4b instead of qwen3:8b

## Performance Tips

1. **Use Local First**: Ollama responses are faster and free
2. **Choose Right Model**: Use reasoning models only for complex tasks
3. **GPU Acceleration**: Ollama uses GPU automatically if available
4. **Memory**: 8GB RAM minimum, 16GB recommended

## Model Comparison

| Model | Strengths | Best For |
|-------|-----------|----------|
| qwen3:8b | Fast, general purpose | Chat, explanations, coding |
| deepseek-r1:8b | Reasoning, analysis | Algorithms, math, step-by-step |
| llama3.2:3b | Lightweight | Quick responses, low memory |

## API Reference

### ProviderManager Methods

```python
# Initialize
manager = get_provider_manager()
await manager.initialize()

# Get status
status = manager.format_status()
models = manager.format_models()
current = manager.get_current_model()

# Switch models
manager.set_model("qwen3:8b")
manager.set_model("deepseek-r1:8b")

# Auto-select
best_model = manager.get_best_model_for_task("Explain step by step")

# Benchmark
results = await manager.benchmark_models()
```

### Intent Classification

JARVIS classifies queries automatically:

```python
# Patterns detected:
- "provider status" → PROVIDER_QUERY
- "list models" → PROVIDER_QUERY
- "switch to qwen3" → PROVIDER_QUERY
- "benchmark" → PROVIDER_QUERY
- "compare models" → PROVIDER_QUERY
```

## Security & Privacy

- **Local Processing**: All AI runs on your machine
- **No Data Sharing**: Nothing sent to external servers
- **Offline Capable**: Works without internet
- **API Key Protection**: Cloud fallback keys stay local

## Summary

```bash
# Quick Setup
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b
ollama pull deepseek-r1:8b
ollama serve

# Test
python -m jarvis.cli "provider status"
```

---

For more help, see:
- [Ollama Documentation](https://github.com/ollama/ollama)
- [JARVIS GitHub](https://github.com/Roopank26/JARVIS-V4)
