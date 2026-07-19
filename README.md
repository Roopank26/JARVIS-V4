# JARVIS-V4

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-362%20passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-production%20ready-success.svg)]()

**Just A Rather Very Intelligent System** — A cross-platform personal AI assistant with voice, vision, desktop automation, persistent memory, RAG, and multi-provider LLM support.

---

## Table of Contents

- [Features & Capabilities](#features--capabilities)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running JARVIS](#running-jarvis)
- [Troubleshooting](#troubleshooting)
- [Future Roadmap](#future-roadmap)
- [License](#license)

---

## Features & Capabilities

| Category | Capabilities |
|----------|-------------|
| **Multi-Provider LLM** | Groq (primary), Ollama (local), Gemini (fallback) |
| **Voice I/O** | Wake-word detection, STT (Whisper/faster-whisper), TTS (Piper/Edge-TTS/pyttsx3/gTTS) |
| **Memory** | Session, long-term JSON, semantic search, user profiles, self-improvement logs |
| **RAG** | Document ingestion (PDF, DOCX, HTML), semantic search, study assistant |
| **Research** | Web research with multi-source monitoring and citation |
| **Coding** | Repository indexing, AST analysis, security scanning |
| **Desktop Automation** | Window management, clipboard, app launching, Windows service support |
| **Plugins** | Hot-loadable plugins with intent/tool/memory hooks |
| **Scheduler** | Cron-like scheduled tasks and daily summaries |
| **Diagnostics** | `jarvis doctor` — comprehensive system health checks |

### Voice

Multiple TTS engines with graceful fallbacks:

| Engine | Type | Quality | Speed |
|--------|------|---------|-------|
| Piper TTS | Local | High | Fast |
| Edge-TTS | Cloud | High | Fast |
| pyttsx3 | Local | Medium | Medium |
| gTTS | Cloud | Medium | Medium |

Wake-word detection via OpenWakeWord (local) or audio threshold fallback.

Setup:
```bash
# Linux/macOS
chmod +x setup_voice.sh && ./setup_voice.sh

# Windows
.\setup_voice.ps1
```

### Memory

Multi-tier memory: session (in-memory), long-term JSON, semantic search, user profiles, and self-improvement logs.

Example:
```
You: my name is John
You: remember that I like coffee
You: what is my name?
You: forget my name
```

### RAG

Ingest PDF, DOCX, HTML, and plain text for semantic search and study assistance.

Example:
```
You: ingest pdf notes.pdf
You: summarize this document
You: search my knowledge base for machine learning
```

### Plugins

Hot-loadable plugins with hooks for intents, tools, and memory. Drop plugin directories into `jarvis/plugins/`.

### Coding & Research

- **Coding**: Repository indexing, AST analysis, security scanning.
- **Research**: Multi-source web research with citation.

---

## Screenshots

<!-- Add screenshots here -->
<p align="center">
  <img src="resources/jarvis.png" alt="JARVIS Desktop" width="400">
  <br>
  <em>JARVIS Desktop Assistant</em>
</p>

---

## Architecture

JARVIS uses an **async-first, intent-classification-driven architecture**:

```
User Input
    │
    ▼
┌─────────────────┐
│ Intent Router   │  Pattern-based + LLM classification
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼        ▼
 Profile   Memory    RAG    Research  Desktop  Tools
    │         │        │        │        │        │
    └────┬────┴────────┴────────┴────────┴────────┘
         │
         ▼
   ┌───────────┐
   │   Agent   │  Planner → Executor → Response
   └─────┬─────┘
         │
    ┌────┴────┐
    ▼         ▼
 Memory   Tools
```

**Core components**: `core/agent.py` (orchestrator), `core/planner.py` (LLM-driven planning), `core/executor.py` (tool execution with retry), `memory/` (multi-tier), `tools/` (extensible registry), `voice/` (STT/TTS pipeline), `rag/` (document processing).

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip
- Groq API key (free at https://console.groq.com) OR Ollama (local)

### Windows

```powershell
git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
pip install -e .

New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.jarvis"
Set-Content -Path "$env:USERPROFILE\.jarvis\api_keys.json" -Value '{"groq_api_key": "gsk_your_key_here"}'
```

### Linux/macOS

```bash
sudo apt-get install -y portaudio19-dev ffmpeg

git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Configuration

Configuration lives in `~/.jarvis/`:

- `config.json` — Main settings
- `api_keys.json` — API keys
- `memory/long_term.json` — Persistent memory

### Settings

```json
{
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "voice_enabled": true,
    "language": "en",
    "voice_name": "Charon",
    "audio_sample_rate": 16000,
    "max_retries": 3,
    "max_replans": 2,
    "memory_max_chars": 2200
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `JARVIS_API_KEY` | Default API key (overrides config) |
| `GROQ_API_KEY` | Groq API key |
| `OLLAMA_HOST` | Ollama server address (default: `http://localhost:11434`) |

### API Providers

| Provider | Backend | Notes |
|----------|---------|-------|
| Groq | `groq` | Default, fast inference. Free tier available. |
| Ollama | `ollama` | Local models, runs at `http://localhost:11434` |
| Gemini | `gemini` | Legacy fallback |

Priority: Ollama → Groq → Gemini.

---

## Running JARVIS

### Interactive CLI

```bash
python -m jarvis
```

With API key argument:
```bash
python -m jarvis your-api-key
```

### CLI with Environment Variable

```bash
export JARVIS_API_KEY=gsk_your_key_here
python -m jarvis
```

### Python API

```python
import asyncio
from jarvis.core.agent import create_jarvis

async def main():
    jarvis = create_jarvis(api_key="your-api-key")
    response = await jarvis.process("What files are in my home directory?")
    print(response)

asyncio.run(main())
```

### Desktop Assistant

```bash
python -m jarvis.desktop run
```

Persistent background assistant with wake-word activation, system tray icon, and daily summaries.

### Premium Web UI

```bash
python -m jarvis ui
```

Opens at **http://127.0.0.1:8742**. Adds visible reasoning stages, streaming responses, autonomous planning, live dashboard, command palette, background tasks, activity center, smart suggestions, and dark/light themes.

### Diagnostics

```bash
python -m jarvis doctor
```

Checks Python, Git, FFmpeg, Ollama, Whisper, Piper, OpenWakeWord, audio devices, GPU, CPU, memory, disk, and internet connectivity.

---

## Troubleshooting

### Import Errors

```bash
pip install -r requirements.txt
```

### Audio Issues

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### API Key Issues

1. Verify key in `~/.jarvis/api_keys.json`
2. Check internet connectivity
3. Verify quota on provider dashboard

### Voice Not Working

1. Run `python -m jarvis doctor`
2. Check microphone permissions
3. Install optional deps: `pip install faster-whisper openwakeword piper-tts`

---

## Future Roadmap

| Milestone | Features |
|-----------|----------|
| **v1.1** | Improved voice wake-word accuracy, better RAG chunking |
| **v1.2** | Docker container, VS Code extension marketplace |
| **v1.3** | Multi-agent coordinator, remote sessions |
| **v2.0** | GUI mode, plugin marketplace, self-improvement engine |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
