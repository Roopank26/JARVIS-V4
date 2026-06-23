# JARVIS Architecture Document

> **Project:** JARVIS - Just A Rather Very Intelligent System  
> **Version:** 1.0.0  
> **Date:** 2026-06-23  
> **Sources:** Mark-XXXIX-OR (https://github.com/FatihMakes/Mark-XXXIX-OR) & Claude Code (https://github.com/Kuberwastaken/claude-code)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Repository Analysis](#2-repository-analysis)
3. [Component Classification](#3-component-classification)
4. [JARVIS Architecture](#4-jarvis-architecture)
5. [Migration Plan](#5-migration-plan)
6. [Folder Structure](#6-folder-structure)
7. [Implementation Phases](#7-implementation-phases)

---

## 1. Executive Summary

JARVIS is designed as a cross-platform personal AI assistant combining the best features from two source repositories:

| Feature | Mark-XXXIX-OR | Claude Code | JARVIS Target |
|---------|---------------|-------------|---------------|
| Voice I/O | ✅ Native Gemini Live | ❌ CLI only | ✅ Full voice |
| Desktop Control | ✅ Comprehensive | ❌ None | ✅ Core modules |
| Agent System | ✅ Planner + Executor | ✅ QueryEngine + Tools | ✅ Hybrid |
| Memory | ✅ JSON-based long-term | ✅ Session + memdir | ✅ Persistent |
| Tool System | ✅ 16 action modules | ✅ 40+ typed tools | ✅ Modular |
| Planning | ✅ LLM-based planning | ❌ Implicit | ✅ LLM-driven |
| CLI/UI | ❌ Tkinter GUI | ✅ Terminal TUI | ✅ Both |
| Multi-Agent | ❌ Single agent | ✅ Coordinator/Swarm | ✅ Foundation |

---

## 2. Repository Analysis

### 2.1 Mark-XXXIX-OR Analysis

#### Overview
- **Language:** Python 3.11+
- **Framework:** Custom voice-native with Gemini Live
- **Strengths:** Real-time voice I/O, desktop automation, memory system
- **Target:** Windows-centric personal assistant

#### Key Modules

| Module | Location | Purpose | Reusability |
|--------|----------|---------|-------------|
| **Voice System** | `main.py` (lines 250-370) | Real-time audio capture/playback via sounddevice | ⭐⭐⭐ REUSE |
| **Screen Processor** | `actions/screen_processor.py` | Vision via mss + Gemini Live | ⭐⭐⭐ REUSE |
| **Memory Manager** | `memory/memory_manager.py` | JSON-based long-term memory | ⭐⭐⭐ REUSE |
| **Agent Executor** | `agent/executor.py` | Step-by-step task execution | ⭐⭐ MODIFY |
| **Planner** | `agent/planner.py` | LLM-driven plan generation | ⭐⭐ MODIFY |
| **Error Handler** | `agent/error_handler.py` | Recovery strategies | ⭐⭐ REUSE |
| **Tool Actions** | `actions/*.py` | Desktop automation | ⭐⭐⭐ REUSE |

#### Architecture Pattern
```
User Voice → Audio Queue → Gemini Live API → Tool Calls → Actions → TTS Output
                 ↓
           Memory System
```

### 2.2 Claude Code Analysis

#### Overview
- **Language:** TypeScript/React + Rust (in progress)
- **Framework:** Custom Ink (React TUI) + Claude API
- **Strengths:** Tool system, permission model, multi-agent, extensibility
- **Target:** CLI coding assistant

#### Key Subsystems

| Subsystem | Location | Purpose | Reusability |
|-----------|----------|---------|-------------|
| **QueryEngine** | `src/QueryEngine.ts` | Turn execution loop | ⭐⭐ ADAPT |
| **Tool Framework** | `src/Tool.ts` | Typed tool base class | ⭐⭐⭐ ADAPT |
| **Commands** | `src/commands/` | 87 slash commands | ⭐⭐ ADAPT |
| **Permission System** | `src/Tool.ts` | Permission tiers | ⭐⭐⭐ ADAPT |
| **Memory Dir** | `src/memdir/` | Markdown-based memory | ⭐⭐ REUSE |
| **Bridge Protocol** | `src/bridge/` | Remote sessions | ⭐⭐ FUTURE |
| **Agent System** | `src/tools/AgentTool.ts` | Multi-agent orchestration | ⭐⭐⭐ ADAPT |

#### Architecture Pattern
```
Terminal Input → Command Dispatch → QueryEngine → Claude API → Tool Execution
                        ↓                    ↓
                  Command Registry      History + Memory
```

---

## 3. Component Classification

### 3.1 Voice Modules

| Component | Source | Status | Action |
|-----------|--------|--------|--------|
| Audio Capture (sounddevice) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Audio Playback | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Speech-to-Text (Gemini Live) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Text-to-Speech (Gemini Live) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Voice Config/UI | Both | ⚠️ Mixed | REWRITE |
| Push-to-talk | Claude Code | ⭐ Ref | ADAPT |

**JARVIS Implementation:** Adopt Mark-XXXIX-OR's native audio pipeline, enhance with Claude Code's voice toggle patterns.

### 3.2 Vision Modules

| Component | Source | Status | Action |
|-----------|--------|--------|--------|
| Screen Capture (mss) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Camera Capture (OpenCV) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Image Processing | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Vision Analysis (Gemini) | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Visual Feedback | Mark-XXXIX-OR | ✅ Mature | REUSE |

**JARVIS Implementation:** Direct adoption of Mark-XXXIX-OR's screen_processor module.

### 3.3 Desktop Automation Modules

| Component | Source | Status | Action |
|-----------|--------|--------|--------|
| Open App | Mark-XXXIX-OR | ✅ Mature | REUSE |
| File Controller | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Computer Settings | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Desktop Control | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Computer Control | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Browser Control | Mark-XXXIX-OR | ✅ Mature | REUSE |
| Code Helper | Mark-XXXIX-OR | ⚠️ Basic | ENHANCE |
| Bash/Terminal | Claude Code | ✅ Excellent | ADAPT |

**JARVIS Implementation:** Combine Mark-XXXIX-OR's action modules with Claude Code's bash tool implementation.

### 3.4 Agent Architecture

| Component | Source | Pattern | Action |
|-----------|--------|---------|--------|
| Single Agent (Loop) | Mark-XXXIX-OR | Sequential steps | ADAPT |
| Planner Module | Mark-XXXIX-OR | LLM-driven | ADAPT |
| Executor Module | Mark-XXXIX-OR | Tool-based | ADAPT |
| Error Handler | Mark-XXXIX-OR | Recovery | REUSE |
| Multi-Agent | Claude Code | Coordinator/Swarm | ADAPT |
| Query Engine | Claude Code | Turn-based | ADAPT |

**JARVIS Implementation:** 
- Core: Mark-XXXIX-OR's planner-executor pattern
- Extensions: Claude Code's multi-agent concepts (future)

```
┌─────────────────────────────────────────────────────────────┐
│                        JARVIS Core                          │
├─────────────────────────────────────────────────────────────┤
│  User Input → Planner → Executor → Tool Calls → Response     │
│       ↓              ↓         ↓                           │
│    Memory       Error Handler   ↓                           │
│                             Actions                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Memory Systems

| Component | Source | Type | Action |
|-----------|--------|------|--------|
| Session Memory | Claude Code | In-memory | REUSE |
| Long-term Memory | Mark-XXXIX-OR | JSON file | REUSE |
| Memory Dir | Claude Code | Markdown | ADAPT |
| Auto-dream | Claude Code | Consolidation | ADAPT |

**JARVIS Implementation:**
```python
Memory System:
├── Session Memory (Claude Code pattern)
│   └── In-memory with history
├── Long-term Memory (Mark-XXXIX-OR pattern)
│   └── JSON with categories: identity, preferences, projects, etc.
└── Context Memory
    └── Relevance-scored context injection
```

### 3.6 Tool Systems

| Tool Category | Source | Count | Action |
|--------------|--------|-------|--------|
| File Operations | Both | 8 | MERGE |
| Web Operations | Both | 4 | MERGE |
| System Control | Mark-XXXIX-OR | 6 | REUSE |
| Code/Dev | Both | 4 | MERGE |
| Communication | Mark-XXXIX-OR | 3 | REUSE |
| Media | Mark-XXXIX-OR | 2 | REUSE |
| Advanced | Claude Code | 15+ | ADAPT |

**JARVIS Tool Registry:**
```
File Tools:
├── read_file    - Read file contents
├── write_file   - Write/create files
├── edit_file    - Modify existing files
├── list_dir     - Directory listing
├── find_files   - File search
└── disk_usage   - Storage analysis

System Tools:
├── bash         - Terminal commands
├── open_app     - Launch applications
├── computer     - System settings/control
└── clipboard    - Copy/paste

Web Tools:
├── web_search   - Search engine
├── web_fetch    - Page content
└── browser      - Browser automation

Communication:
├── send_message - WhatsApp/Telegram
├── reminder     - Scheduled alerts
└── email        - Email operations

Media:
├── screenshot   - Screen capture
├── camera       - Webcam access
└── youtube      - Video control

Development:
├── code_helper  - Code generation
├── run_code     - Code execution
└── git          - Version control
```

### 3.7 Planning Systems

| Component | Source | Approach | Action |
|-----------|--------|----------|--------|
| LLM Planner | Mark-XXXIX-OR | Gemini + JSON | ADAPT |
| Replanner | Mark-XXXIX-OR | Recovery | ADAPT |
| Step Validator | Mark-XXXIX-OR | Tool mapping | REUSE |
| Plan Mode | Claude Code | User approval | ADAPT |

**JARVIS Planner:**
```
Input: User goal
  ↓
LLM generates plan (JSON steps)
  ↓
Validate steps → Execute → Monitor
  ↓
Error? → Analyze → Replan → Retry
  ↓
Success → Summarize → Output
```

---

## 4. JARVIS Architecture

### 4.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Voice I/O   │  │ Terminal    │  │ GUI (Optional)          │  │
│  │ (sounddevice)│ │ (Rich CLI)  │  │ (Web/Tkinter)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                         CORE ENGINE                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    JARVIS Agent                              ││
│  │  ┌───────────┐  ┌────────────┐  ┌──────────────────────┐  ││
│  │  │  Planner  │→ │  Executor   │→ │   Response Handler    │  ││
│  │  └───────────┘  └────────────┘  └──────────────────────┘  ││
│  │        ↓              ↓                    ↓               ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │              Tool Registry                           │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────┐              ┌─────────────────────────┐   │
│  │    Memory       │              │    Permission Manager   │   │
│  │    System       │              │    (Claude Code style)   │   │
│  └─────────────────┘              └─────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                         ACTION LAYER                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐   │
│  │  File    │ │  System  │ │   Web    │ │   Communication   │   │
│  │  Tools   │ │  Control │ │  Tools   │ │      Tools        │   │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Components

#### 4.2.1 Voice Module (`jarvis/voice/`)
- **Input:** Microphone stream (sounddevice)
- **Output:** Speaker stream (sounddevice)
- **API:** Gemini Live (realtime audio)
- **Fallback:** Text input mode

#### 4.2.2 Vision Module (`jarvis/vision/`)
- **Screen Capture:** mss library
- **Camera Capture:** OpenCV
- **Analysis:** Gemini Vision API

#### 4.2.3 Memory Module (`jarvis/memory/`)
```python
class MemorySystem:
    session: SessionMemory      # In-memory, current conversation
    long_term: LongTermMemory   # JSON file, persistent facts
    context: ContextMemory       # Relevance-scored context
    
    def remember(key, value, category)
    def recall(query) -> list
    def forget(key, category)
    def format_for_prompt() -> str
```

#### 4.2.4 Tool System (`jarvis/tools/`)
```python
class Tool(ABC):
    name: str
    description: str
    input_schema: Schema
    
    async def execute(input, context) -> ToolResult
    def validate_permission(context) -> PermissionResult
```

#### 4.2.5 Planner (`jarvis/planner/`)
```python
async def create_plan(goal: str, context: str = "") -> Plan:
    # LLM generates step sequence
    # Validates tool availability
    # Returns structured plan

async def replan(goal, completed, failed, error) -> Plan:
    # Recovery planning on failure
```

#### 4.2.6 Executor (`jarvis/executor/`)
```python
class Executor:
    max_retries: int = 3
    max_replans: int = 2
    
    async def execute(goal, speak_callback=None):
        # Execute plan steps
        # Handle errors
        # Replan on failure
        # Summarize results
```

### 4.3 Permission Model (Adapted from Claude Code)

| Level | Operations | Prompt |
|-------|------------|--------|
| Automatic | Read queries, info | None |
| Ask Once | Write operations, net | Per-session |
| Ask Always | Delete, destructive | Every time |
| Deny | Blocked patterns | Blocked |

---

## 5. Migration Plan

### 5.1 Reuse (Direct Adoption)

| Component | Source File | Target | Rationale |
|-----------|-------------|--------|-----------|
| Voice I/O | `main.py` (250-370) | `voice/audio.py` | Proven real-time audio |
| Screen Capture | `screen_processor.py` | `vision/screen.py` | Robust mss implementation |
| Memory Manager | `memory_manager.py` | `memory/long_term.py` | Complete memory system |
| Error Handler | `error_handler.py` | `executor/recovery.py` | Mature error handling |
| Open App | `actions/open_app.py` | `tools/system.py` | Cross-platform support |
| Web Search | `actions/web_search.py` | `tools/web.py` | DuckDuckGo integration |
| File Controller | `actions/file_controller.py` | `tools/files.py` | Comprehensive file ops |
| Computer Settings | `actions/computer_settings.py` | `tools/system.py` | System control |
| Desktop Control | `actions/desktop.py` | `tools/desktop.py` | Desktop automation |
| Browser Control | `actions/browser_control.py` | `tools/browser.py` | Playwright-based |
| Send Message | `actions/send_message.py` | `tools/communication.py` | WhatsApp/Telegram |
| Reminder | `actions/reminder.py` | `tools/communication.py` | Task scheduling |
| Weather Report | `actions/weather_report.py` | `tools/web.py` | Weather info |
| Youtube Control | `actions/youtube_video.py` | `tools/media.py` | Video control |
| Flight Finder | `actions/flight_finder.py` | `tools/web.py` | Flight search |

### 5.2 Modify (Adaptation Required)

| Component | Source | Changes | Effort |
|-----------|--------|---------|--------|
| Planner | `planner.py` | Update tool registry, add context | Medium |
| Executor | `executor.py` | Async refactor, add callbacks | Medium |
| Tool Base | `Tool.ts` | TypeScript → Python, add schemas | Medium |
| Permission System | `Tool.ts` | Port permission tiers | Medium |
| Commands | `commands.ts` | Convert to Python CLI | Low |
| Memory Dir | `memdir/` | Markdown → JSON hybrid | Low |

### 5.3 Discard

| Component | Source | Reason |
|-----------|--------|--------|
| Tkinter UI | `ui.py` | Replace with modern CLI |
| OpenRouter Client | `or_client.py` | Use direct API |
| Windows-specific | Various | Cross-platform rewrite |
| Game Updater | `actions/game_updater.py` | Low utility |
| Code Helper | `actions/code_helper.py` | Basic, replace with better |
| Dev Agent | `actions/dev_agent.py` | Merge into core executor |
| File Processor | `actions/file_processor.py` | Redundant with file_controller |

### 5.4 Future (Phase 2+)

| Component | Source | Notes |
|-----------|--------|-------|
| Multi-Agent | Claude Code | Coordinator/Swarm patterns |
| Bridge Protocol | Claude Code | Remote sessions |
| Plugin System | Claude Code | Extensibility |
| IDE Integration | Claude Code | VS Code/JetBrains |

---

## 6. Folder Structure

```
JARVIS/
├── ARCHITECTURE.md              # This document
├── README.md                    # Project overview
├── SETUP.md                     # Installation guide
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project config
│
├── jarvis/                      # Main package
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   │
│   ├── core/                    # Core engine
│   │   ├── __init__.py
│   │   ├── agent.py             # Main agent loop
│   │   ├── planner.py           # Plan generation
│   │   ├── executor.py          # Plan execution
│   │   ├── recovery.py          # Error handling
│   │   └── config.py            # Configuration
│   │
│   ├── voice/                   # Voice I/O
│   │   ├── __init__.py
│   │   ├── audio.py             # Audio capture/playback
│   │   ├── speech.py            # STT/TTS via Gemini
│   │   └── voice_manager.py     # Voice session management
│   │
│   ├── vision/                  # Visual input
│   │   ├── __init__.py
│   │   ├── screen.py            # Screen capture
│   │   ├── camera.py            # Webcam capture
│   │   └── analyzer.py          # Vision analysis
│   │
│   ├── memory/                  # Memory systems
│   │   ├── __init__.py
│   │   ├── base.py              # Memory base class
│   │   ├── session.py           # Session memory
│   │   ├── long_term.py         # Persistent memory
│   │   ├── context.py           # Context injection
│   │   └── memory_manager.py    # Unified memory API
│   │
│   ├── tools/                   # Tool registry
│   │   ├── __init__.py
│   │   ├── base.py              # Tool base class
│   │   ├── registry.py          # Tool registry
│   │   ├── permissions.py       # Permission system
│   │   │
│   │   ├── file_tools.py        # File operations
│   │   ├── system_tools.py      # System control
│   │   ├── web_tools.py         # Web operations
│   │   ├── terminal_tools.py    # Bash/CLI
│   │   ├── communication_tools.py  # Messaging
│   │   └── media_tools.py       # Media operations
│   │
│   ├── ui/                      # User interfaces
│   │   ├── __init__.py
│   │   ├── cli.py               # Terminal CLI
│   │   ├── console.py           # Rich console output
│   │   └── status.py            # Status indicators
│   │
│   ├── api/                     # API integrations
│   │   ├── __init__.py
│   │   ├── gemini.py            # Gemini API client
│   │   └── config_loader.py     # API key management
│   │
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── logging.py           # Logging setup
│       ├── platform.py          # Platform detection
│       └── paths.py             # Path helpers
│
├── config/                      # Configuration files
│   ├── api_keys.json           # API keys (gitignored)
│   └── settings.json           # User settings
│
├── memory/                      # Memory storage
│   └── long_term.json         # Persistent memory file
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_memory.py
│   ├── test_tools.py
│   ├── test_planner.py
│   └── test_executor.py
│
├── docs/                        # Documentation
│   ├── TOOLS.md                 # Tool reference
│   ├── MEMORY.md                # Memory system docs
│   └── CLI.md                   # CLI usage guide
│
└── scripts/                     # Utility scripts
    ├── setup.sh                 # Linux/macOS setup
    └── setup.bat               # Windows setup
```

---

## 7. Implementation Phases

### Phase 1: Core Foundation (This Implementation)

**Goal:** First working JARVIS with voice, memory, and core tools.

| Task | Components | Status |
|------|------------|--------|
| 1.1 Project scaffold | Folder structure, config | ⬜ |
| 1.2 Memory system | Session + long-term memory | ⬜ |
| 1.3 Tool base class | Registry + permissions | ⬜ |
| 1.4 Core tools | File, terminal, system | ⬜ |
| 1.5 Voice I/O | Audio capture/playback | ⬜ |
| 1.6 Planner | LLM-driven plan generation | ⬜ |
| 1.7 Executor | Step execution + error handling | ⬜ |
| 1.8 CLI interface | Terminal UI | ⬜ |
| 1.9 Integration | Voice + tools + memory | ⬜ |
| 1.10 Documentation | README, setup guide | ⬜ |

### Phase 2: Enhanced Features

| Task | Components |
|------|------------|
| 2.1 Vision module | Screen + camera capture |
| 2.2 Web tools | Search, fetch, browser |
| 2.3 Communication | Messaging, reminders |
| 2.4 Permission UI | Interactive permission prompts |
| 2.5 History | Session persistence |

### Phase 3: Advanced Capabilities

| Task | Components |
|------|------------|
| 3.1 Multi-agent | Coordinator pattern |
| 3.2 Plugin system | Extensibility framework |
| 3.3 Remote sessions | Bridge protocol |
| 3.4 IDE integration | VS Code/JetBrains |

---

## Appendix A: Key Differences from Source Repos

### Mark-XXXIX-OR → JARVIS

| Original | JARVIS Change |
|----------|---------------|
| Windows-only actions | Cross-platform abstraction |
| Tkinter GUI | Modern CLI (Rich) |
| Single-threaded audio | Async audio pipeline |
| Gemini-only | Configurable LLM backend |
| Implicit permissions | Explicit permission system |

### Claude Code → JARVIS

| Original | JARVIS Change |
|----------|---------------|
| CLI-only | Voice-enabled |
| No persistent memory | Full memory system |
| No desktop control | System automation |
| TypeScript | Python |
| Complex tool system | Simplified for desktop |

---

## Appendix B: Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Audio | sounddevice, numpy |
| Vision | mss, opencv-python, PIL |
| LLM | google-genai (Gemini) |
| Terminal UI | rich, prompt_toolkit |
| File Ops | pathlib, shutil |
| Web | requests, beautifulsoup4 |
| Automation | pyautogui, pyperclip |
| Browser | playwright |

---

*Document Version: 1.0.0*  
*Generated: 2026-06-23*
