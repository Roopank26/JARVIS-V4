# JARVIS-V4

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-362%20passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-production%20ready-success.svg)]()

**Just A Rather Very Intelligent System** — A cross-platform personal AI assistant with voice, vision, desktop automation, persistent memory, RAG, and multi-provider LLM support.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Providers](#api-providers)
- [Voice Setup](#voice-setup)
- [RAG Setup](#rag-setup)
- [Memory System](#memory-system)
- [Plugin System](#plugin-system)
- [Usage Examples](#usage-examples)
- [CLI Usage](#cli-usage)
- [Desktop Usage](#desktop-usage)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Performance Highlights](#performance-highlights)
- [Release Notes](#release-notes)
- [Future Roadmap](#future-roadmap)
- [Contribution Guide](#contribution-guide)
- [License](#license)
- [Credits](#credits)

---

## Features

| Category | Capabilities |
|----------|-------------|
| **Multi-Provider LLM** | Groq (primary), Ollama (local), Gemini (fallback) |
| **Voice I/O** | Wake-word detection, STT (Whisper/faster-whisper), TTS (Piper/Edge-TTS/pyttsx3/gTTS) |
| **Memory** | Session memory, long-term JSON storage, semantic memory, user profiles, self-improvement logs |
| **Tools** | Extensible tool registry with permission levels and async execution |
| **File Management** | Read, write, search, delete, disk usage |
| **Terminal** | Run shell commands with sandboxing |
| **Desktop Automation** | Window management, clipboard, app launching, Windows service support |
| **Planning** | LLM-driven multi-step task planning with automatic replanning |
| **Error Recovery** | Retry logic with backoff and fallback strategies |
| **RAG** | Document ingestion (PDF, DOCX, HTML), semantic search, study assistant |
| **Research** | Web research with multi-source monitoring and citation |
| **Coding** | Repository indexing, AST analysis, security scanning |
| **Plugins** | Hot-loadable plugins with intent/tool/memory hooks |
| **Scheduler** | Cron-like scheduled tasks and daily summaries |
| **System Tray** | Background desktop mode with tray icon |
| **Diagnostics** | `jarvis doctor` — comprehensive system health checks |

---

## Screenshots

<!-- Add screenshots here -->
<p align="center">
  <img src="resources/jarvis.png" alt="JARVIS Desktop" width="400">
  <br>
  <em>JARVIS Desktop Assistant</em>
</p>

---

## Project Structure

```
JARVIS-V4/
├── jarvis/                        # Main package
│   ├── __main__.py                # CLI entry point (incl. `ui` command)
│   ├── events.py                  # Event bus + reasoning-stage definitions
│   ├── errors.py                  # Friendly error mapping
│   ├── orchestor.py              # Premium orchestration (stages, streaming, planning)
│   ├── tasks/                     # Background task manager
│   ├── tools_library.py          # Dynamic tool discovery / Tool Library
│   ├── palette.py                 # Command palette search index
│   ├── suggestions.py             # Smart proactive suggestions
│   ├── activity.py                # Activity center
│   ├── metrics.py                 # Live dashboard metrics
│   ├── core/                      # Core agent, planner, executor, config
│   ├── api/                       # LLM providers (Groq, Ollama, Gemini)
│   ├── tools/                     # Tool framework & implementations
│   ├── memory/                    # Session, long-term, semantic, user profile
│   ├── voice/                     # STT/TTS, wake word, voice runtime
│   ├── vision/                    # Screenshot, OCR, camera
│   ├── desktop/                   # Desktop assistant, automation, tray, Windows service
│   ├── ui/                        # CLI and premium desktop (web) UI
│   ├── agents/                    # Multi-agent orchestration
│   ├── research/                  # Web research agent
│   ├── coding/                    # Code analysis, repo indexing, security
│   ├── rag/                       # Document processing, RAG system
│   ├── plugins/                   # Plugin system
│   ├── services/                  # Scheduler, daemon
│   ├── integrations/              # VS Code integration
│   ├── repo/                      # Repository analyzer, AST, security scanner
│   ├── utils/                     # Logging, diagnostics, exceptions, lifecycle
│   └── diagnostics.py             # System health checks (jarvis doctor)
├── tests/                         # Test suite (362 tests)
├── resources/                     # Assets (icons, etc.)
├── memory/                        # User memory data (long_term.json)
├── archive/                       # Archived prototype (pre-V4)
├── requirements.txt               # Python dependencies
├── setup_voice.sh / .ps1          # Voice setup scripts
├── pyproject.toml                 # Package configuration
├── LICENSE                        # MIT License
├── CHANGELOG.md                   # Version history
└── README.md                      # This file
```

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

### Core Components

- **Agent** (`jarvis/core/agent.py`): Central orchestrator with intent classification, routing, and response sanitization
- **Planner** (`jarvis/core/planner.py`): LLM-driven multi-step task planning
- **Executor** (`jarvis/core/executor.py`): Tool execution with retry, replanning, and error recovery
- **Memory** (`jarvis/memory/`): Multi-tier memory (session, long-term, semantic, user profile)
- **Tools** (`jarvis/tools/`): Extensible registry with permission levels (ReadOnly, Write, Destructive)
- **Voice** (`jarvis/voice/`): Wake-word → STT → Intent → Agent → TTS pipeline
- **RAG** (`jarvis/rag/`): Document ingestion, chunking, vector search, study assistant

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip
- Groq API key (free at https://console.groq.com) OR Ollama (local)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install JARVIS in editable mode
pip install -e .

# Configure API key
mkdir -p ~/.jarvis
echo '{"groq_api_key": "gsk_your_key_here"}' > ~/.jarvis/api_keys.json
```

### Windows

```powershell
# Clone
git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4

# Virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install
pip install -r requirements.txt
pip install -e .

# Config
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.jarvis"
Set-Content -Path "$env:USERPROFILE\.jarvis\api_keys.json" -Value '{"groq_api_key": "gsk_your_key_here"}'
```

### Linux/macOS

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get install -y portaudio19-dev ffmpeg

# Clone and install
git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Configuration

Configuration is stored in `~/.jarvis/`:

- `config.json` - Main settings
- `api_keys.json` - API keys
- `memory/long_term.json` - Persistent memory

### Configuration Options

```json
{
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "live_model": "llama-3.3-70b-versatile",
    "voice_enabled": true,
    "language": "en",
    "voice_name": "Charon",
    "audio_sample_rate": 16000,
    "audio_channels": 1,
    "chunk_size": 1024,
    "max_retries": 3,
    "max_replans": 2,
    "memory_max_chars": 2200,
    "memory_max_value_length": 380
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `JARVIS_API_KEY` | Default API key (overrides config) |
| `GROQ_API_KEY` | Groq API key |
| `OLLAMA_HOST` | Ollama server address (default: `http://localhost:11434`) |

---

## API Providers

JARVIS supports multiple LLM providers with automatic fallback:

| Provider | Backend | Notes |
|----------|---------|-------|
| Groq | `groq` | Default, fast inference. Free tier available. |
| Ollama | `ollama` | Local models, runs at `http://localhost:11434` |
| Gemini | `gemini` | Legacy fallback |

### Provider Priority

1. **Ollama** (Local) - Fastest, private
2. **Groq** (Cloud) - Fast inference, free tier
3. **Gemini** (Legacy) - Fallback option

---

## Voice Setup

JARVIS supports multiple voice engines with graceful fallbacks.

### Setup Voice (Linux/macOS)

```bash
chmod +x setup_voice.sh
./setup_voice.sh
```

### Setup Voice (Windows)

```powershell
.\setup_voice.ps1
```

### Voice Engines

| Engine | Type | Quality | Speed |
|--------|------|---------|-------|
| Piper TTS | Local | High | Fast |
| Edge-TTS | Cloud | High | Fast |
| pyttsx3 | Local | Medium | Medium |
| gTTS | Cloud | Medium | Medium |

### Wake Word

- **OpenWakeWord**: Local wake-word detection (requires `openwakeword`)
- **Fallback**: Audio threshold-based activation

### Test Voice

```bash
# Run diagnostics
python -m jarvis doctor

# Test microphone
python -m jarvis diagnostics
```

---

## RAG Setup

JARVIS includes a built-in Retrieval-Augmented Generation system for document understanding.

### Supported Formats

- PDF (via PyPDF2)
- DOCX (via python-docx)
- HTML (via BeautifulSoup)
- Plain text

### Usage

```
You: ingest pdf notes.pdf
You: summarize this document
You: search my knowledge base for machine learning
You: generate important questions from my notes
```

### Configuration

RAG data is stored in `~/.jarvis/rag/`. No external database required for basic usage. For advanced semantic search, install `chromadb` and `sentence-transformers`.

---

## Memory System

JARVIS uses a multi-tier memory architecture:

```
Memory System
├── Session Memory (in-memory, current conversation)
├── Long-term Memory (JSON file, persistent facts)
├── Semantic Memory (embedding-based search)
├── User Profile (identity, preferences, projects)
└── Self-Improvement Logs (learning from interactions)
```

### Memory Commands

```
You: my name is John
You: remember that I like coffee
You: what is my name?
You: summarize me
You: forget my name
```

### Categories

- **Identity**: Name, age, occupation
- **Preferences**: Likes, dislikes, settings
- **Projects**: Active projects, goals
- **Facts**: General knowledge about the user
- **Conversations**: Important conversation snippets

---

## Plugin System

JARVIS supports hot-loadable plugins with hooks for intents, tools, and memory.

### Plugin Types

| Type | Hook | Purpose |
|------|------|---------|
| `IntentPlugin` | `on_intent` | Modify intent classification |
| `ToolPlugin` | `on_tool_execute` | Wrap or extend tool execution |
| `MemoryPlugin` | `on_memory_store` | Filter or enrich memory storage |

### Installing Plugins

Drop plugin directories into `jarvis/plugins/` or specify a custom directory when initializing the plugin manager.

---

## Usage Examples

### Python API

```python
import asyncio
from jarvis.core.agent import create_jarvis

async def main():
    jarvis = create_jarvis(api_key="your-api-key")
    
    response = await jarvis.process("What files are in my home directory?")
    print(response)
    
    result = await jarvis.execute_task("Create a file called hello.py with hello world")
    print(result)

asyncio.run(main())
```

### Research Example

```python
from jarvis.research.research_agent import get_research_agent

agent = get_research_agent()
result = await agent.research("latest AI trends")
print(result.summary)
for source in result.sources:
    print(f"- {source.title}: {source.url}")
```

### RAG Example

```python
from jarvis.rag.rag_system import get_rag_system

rag = get_rag_system()
await rag.initialize()
await rag.ingest_document("path/to/notes.pdf")
results = await rag.search("machine learning concepts")
```

---

## CLI Usage

### Commands

| Command | Description |
|---------|-------------|
| `help` | Show help message |
| `tools` | List available tools |
| `status` | Show agent status |
| `memory` | Show stored memory |
| `clear` | Clear the screen |
| `exit` / `quit` | Exit JARVIS |

### Running

```bash
# Interactive CLI
python -m jarvis

# With API key argument (insecure, use env var instead)
python -m jarvis your-api-key

# Recommended: use environment variable
export JARVIS_API_KEY=gsk_your_key_here
python -m jarvis
```

---

## Desktop Usage

```bash
# Run desktop assistant
python -m jarvis.desktop run
```

Features:
- Persistent background assistant
- Wake-word activation ("Hey Jarvis")
- System tray icon (enabled via config)
- Daily summaries
- Scheduled tasks

---

## Premium Desktop UI (Web)

A polished, local-first desktop experience is available on top of the existing
backend. It preserves every backend system (multi-agent, memory, RAG, plugins,
voice, providers, diagnostics, scheduling) and only enhances the *experience*.

```bash
# Launch the premium web UI (served on 127.0.0.1:8742)
python -m jarvis ui
```

Then open **http://127.0.0.1:8742** in your browser.

### What it adds

- **Visible reasoning stages** — Thinking → Planning → Selecting tools → Executing → Observing → Generating → Complete, shown as a live status pill row.
- **Streaming responses** — token-by-token answers over a WebSocket (falls back to the existing non-streaming path when the provider has no stream).
- **Autonomous planning** — multi-step requests (research, report, repo indexing) generate a visible plan and execute it step by step, with automatic one-shot retry of failed steps.
- **Dashboard** — live CPU/RAM, provider, model, voice status, memory status, and internet status.
- **Tool Library** — auto-discovered tools from the registry and plugins, with search, category filter, favorites, and recently-used.
- **Command palette** — `Ctrl+Shift+P` (or the ⌘ button) to search commands, agents, plugins, files, models, memory, settings, and history from one place.
- **Background tasks** — long-running jobs run in a queue with progress, ETA, and pause/resume/cancel; surfaced in a Task Manager view.
- **Workflow timeline** — every request emits a timeline of its stages, plan, and tool steps.
- **Activity center** — categorized history of voice commands, chat, tools, plans, tasks, plugins, and errors.
- **Smart suggestions** — proactive, context-aware nudges (e.g. uncommitted git changes, new PDFs to summarize).
- **Friendly errors** — raw failures are translated to a reason + suggested fix + retry, without exposing internals.
- **UI polish** — dark/light themes, animated transitions, toast notifications, typing indicators, skeleton/loading states.

### Architecture notes

The UI is a thin composition layer (`jarvis.ui.app.JarvisApp`) over the existing
backend. New modules stay separate:

| Module | Responsibility |
|--------|----------------|
| `jarvis/events.py` | Event bus + reasoning-stage definitions |
| `jarvis/orchestrator.py` | Reasoning stages, streaming, autonomous planning (wraps `core/agent`) |
| `jarvis/tasks/` | Background task queue/manager |
| `jarvis/tools_library.py` | Dynamic tool discovery + Tool Library |
| `jarvis/palette.py` | Command palette search index |
| `jarvis/suggestions.py` | Smart suggestions |
| `jarvis/activity.py` | Activity center |
| `jarvis/metrics.py` | Live dashboard metrics |
| `jarvis/errors.py` | Friendly error mapping |
| `jarvis/ui/server.py` + `jarvis/ui/static/` | Local web SPA + JSON/WS API |

No backend modules (`core/`, `voice/`, `memory/`, `plugins/`, `rag/`,
`providers/`, `diagnostics/`, `scheduler/`) were modified — the UI only
composes and observes them via their existing public interfaces.

---

## Diagnostics

```bash
# Run diagnostics
python -m jarvis.diagnostics
```

Checks:
- Python, Git, FFmpeg
- Ollama, Whisper, Piper, OpenWakeWord
- Microphone, Speaker
- GPU, CPU, Memory, Disk
- Internet connectivity

---

## Troubleshooting

### Import Errors

```bash
pip install -r requirements.txt
```

### Audio Issues

```bash
# Test audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### API Key Issues

1. Verify key in `~/.jarvis/api_keys.json`
2. Check internet connectivity
3. Verify quota on provider dashboard

### Voice Not Working

1. Run `python -m jarvis doctor`
2. Check microphone permissions
3. Install optional voice deps: `pip install faster-whisper openwakeword piper-tts`

---

## Testing

```bash
# Run full test suite
pytest tests/ -q

# Run with coverage
pytest tests/ --cov=jarvis --cov-report=html

# Run specific test file
pytest tests/test_memory.py -v
```

### Test Status

- **362 tests passing** (6 skipped)
- **16 test files** covering core, memory, tools, voice, RAG, desktop, research, and more

---

## Performance Highlights

| Metric | Value |
|--------|-------|
| Test suite runtime | ~22s |
| Total tests | 362 passing, 6 skipped |
| Import time | <1s |
| Memory footprint | ~50MB base |
| Tool registry lookup | O(1) |

---

## Release Notes

### v1.0.0 (2026-07-18)

**Production Ready**
- Runtime validation completed successfully
- 362 tests passing (6 skipped)
- No import cycles, no Unicode issues
- Logging standardized, exception handling improved
- Duplicate code and dead code removed

**Features**
- Multi-provider LLM: Groq, Ollama, Gemini
- Voice I/O with wake-word detection
- Persistent memory with semantic search
- RAG with PDF/DOCX/HTML support
- Research agent with multi-source monitoring
- Coding agent with AST analysis
- Desktop automation framework
- Plugin system with hot-loading
- System tray background mode
- Comprehensive diagnostics

**Packaging**
- Added `pyproject.toml`
- Added entry points (`jarvis`, `jarvis-doctor`)
- Added optional dependency groups
- Added MIT License

---

## Future Roadmap

| Milestone | Features |
|-----------|----------|
| **v1.1** | Improved voice wake-word accuracy, better RAG chunking |
| **v1.2** | Docker container, VS Code extension marketplace |
| **v1.3** | Multi-agent coordinator, remote sessions |
| **v2.0** | GUI mode, plugin marketplace, self-improvement engine |

---

## Contribution Guide

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Style

```bash
# Format code
black jarvis/ tests/

# Lint
ruff check jarvis/ tests/
```

### Testing

```bash
pytest tests/ -q
```

All tests must pass before merging.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Credits

- **Mark-XXXIX-OR** — https://github.com/FatihMakes/Mark-XXXIX-OR
- **Claude Code** — https://github.com/Kuberwastaken/claude-code
- **Groq** — Fast LLM inference
- **Ollama** — Local LLM runtime
