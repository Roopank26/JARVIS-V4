# JARVIS Migration Plan

> **From:** Mark-XXXIX-OR & Claude Code  
> **To:** JARVIS v1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Component Migration Matrix](#component-migration-matrix)
3. [Reuse: Direct Adoption](#reuse-direct-adoption)
4. [Modify: Adaptation Required](#modify-adaptation-required)
5. [Discard: Not Included](#discard-not-included)
6. [Future Phases](#future-phases)

---

## Overview

This document details the migration decisions for building JARVIS from the analyzed source repositories:

- **Mark-XXXIX-OR**: Python-based voice assistant with Gemini Live
- **Claude Code**: TypeScript CLI coding assistant with Claude API

### Migration Strategy

| Category | Count | Description |
|----------|-------|-------------|
| **Reuse** | 18 | Direct code adoption with minimal changes |
| **Modify** | 6 | Significant adaptation required |
| **Discard** | 8 | Not suitable for JARVIS |
| **Future** | 5 | Deferred to later phases |

---

## Component Migration Matrix

### Voice Modules

| Component | Source | Original File | Action | Effort |
|-----------|--------|---------------|--------|--------|
| Audio Capture | Mark-XXXIX-OR | main.py (250-370) | **REUSE** | Low |
| Audio Playback | Mark-XXXIX-OR | main.py (250-370) | **REUSE** | Low |
| STT (Gemini Live) | Mark-XXXIX-OR | main.py | **REUSE** | Low |
| TTS (Gemini Live) | Mark-XXXIX-OR | main.py | **REUSE** | Low |
| Voice Config UI | Both | Mixed | **DISCARD** | - |
| Push-to-talk | Claude Code | voice/ | **MODIFY** | Medium |

**Decision Rationale:** Mark-XXXIX-OR's voice system is proven and production-ready. We adopt it directly and enhance with Claude Code's voice toggle patterns.

### Vision Modules

| Component | Source | Original File | Action | Effort |
|-----------|--------|---------------|--------|--------|
| Screen Capture | Mark-XXXIX-OR | screen_processor.py | **REUSE** | Low |
| Camera Capture | Mark-XXXIX-OR | screen_processor.py | **REUSE** | Low |
| Image Processing | Mark-XXXIX-OR | screen_processor.py | **REUSE** | Low |
| Vision Analysis | Mark-XXXIX-OR | screen_processor.py | **REUSE** | Low |
| Visual Feedback | Mark-XXXIX-OR | screen_processor.py | **REUSE** | Low |

**Decision Rationale:** Complete adoption of Mark-XXXIX-OR's vision module. Robust implementation with mss + OpenCV + Gemini Vision.

### Desktop Automation Modules

| Component | Source | Original File | Action | Effort |
|-----------|--------|---------------|--------|--------|
| Open App | Mark-XXXIX-OR | open_app.py | **REUSE** | Low |
| File Controller | Mark-XXXIX-OR | file_controller.py | **REUSE** | Medium |
| Computer Settings | Mark-XXXIX-OR | computer_settings.py | **REUSE** | Low |
| Desktop Control | Mark-XXXIX-OR | desktop.py | **REUSE** | Low |
| Computer Control | Mark-XXXIX-OR | computer_control.py | **REUSE** | Low |
| Browser Control | Mark-XXXIX-OR | browser_control.py | **REUSE** | Medium |
| Code Helper | Mark-XXXIX-OR | code_helper.py | **DISCARD** | - |
| Bash/Terminal | Claude Code | BashTool | **MODIFY** | Medium |
| Windows-specific | Various | Mixed | **MODIFY** | High |

**Decision Rationale:** Most Mark-XXXIX-OR action modules are reusable. Claude Code's BashTool provides better shell handling patterns to adapt.

### Agent Architecture

| Component | Source | Original File | Action | Effort |
|-----------|--------|---------------|--------|--------|
| Agent Loop | Mark-XXXIX-OR | main.py | **MODIFY** | Medium |
| Planner | Mark-XXXIX-OR | planner.py | **MODIFY** | Medium |
| Executor | Mark-XXXIX-OR | executor.py | **MODIFY** | Medium |
| Error Handler | Mark-XXXIX-OR | error_handler.py | **REUSE** | Low |
| Multi-Agent | Claude Code | AgentTool.ts | **FUTURE** | - |
| Query Engine | Claude Code | QueryEngine.ts | **MODIFY** | High |

**Decision Rationale:** Mark-XXXIX-OR's planner-executor pattern is core to JARVIS. Adaptation includes async support and enhanced error recovery.

### Memory Systems

| Component | Source | Original File | Action | Effort |
|-----------|--------|---------------|--------|--------|
| Session Memory | Claude Code | session.ts | **MODIFY** | Medium |
| Long-term Memory | Mark-XXXIX-OR | memory_manager.py | **REUSE** | Low |
| Memory Dir | Claude Code | memdir/ | **FUTURE** | - |
| Auto-dream | Claude Code | autoDream/ | **FUTURE** | - |
| Memory Extraction | Mark-XXXIX-OR | memory_manager.py | **REUSE** | Low |

**Decision Rationale:** Hybrid approach - adopt Mark-XXXIX-OR's proven JSON-based long-term memory with Claude Code's session memory patterns.

### Tool Systems

| Tool | Source | Action | Effort |
|------|--------|--------|--------|
| read_file | New | **CREATE** | Low |
| write_file | New | **CREATE** | Low |
| list_directory | New | **CREATE** | Low |
| find_files | New | **CREATE** | Low |
| delete_file | New | **CREATE** | Low |
| disk_usage | New | **CREATE** | Low |
| bash | Claude Code | **MODIFY** | Medium |
| run_script | Claude Code | **MODIFY** | Medium |
| get_system_info | Mark-XXXIX-OR | **REUSE** | Low |
| open_app | Mark-XXXIX-OR | **REUSE** | Low |
| get_environment | Claude Code | **CREATE** | Low |
| get_clipboard | Mark-XXXIX-OR | **REUSE** | Low |
| set_clipboard | Mark-XXXIX-OR | **REUSE** | Low |
| web_search | Mark-XXXIX-OR | **REUSE** | Medium |
| send_message | Mark-XXXIX-OR | **REUSE** | Medium |
| reminder | Mark-XXXIX-OR | **REUSE** | Medium |
| weather_report | Mark-XXXIX-OR | **REUSE** | Medium |
| youtube_video | Mark-XXXIX-OR | **REUSE** | Medium |
| flight_finder | Mark-XXXIX-OR | **DISCARD** | - |
| game_updater | Mark-XXXIX-OR | **DISCARD** | - |

**Decision Rationale:** Core file/terminal/system tools created as new Python implementations. Advanced tools adopted from Mark-XXXIX-OR.

### Planning Systems

| Component | Source | Action | Effort |
|-----------|--------|--------|--------|
| LLM Planner | Mark-XXXIX-OR | **MODIFY** | Medium |
| Replanner | Mark-XXXIX-OR | **MODIFY** | Medium |
| Step Validator | Mark-XXXIX-OR | **REUSE** | Low |
| Plan Mode | Claude Code | **MODIFY** | Medium |

**Decision Rationale:** Core planner from Mark-XXXIX-OR adapted with Claude Code's permission-aware planning patterns.

---

## Reuse: Direct Adoption

The following components are adopted with minimal changes:

### 1. Voice System (Mark-XXXIX-OR)

**Location:** `jarvis/voice/audio.py`

**Components:**
- Audio capture using sounddevice
- Audio playback using sounddevice
- Real-time audio streaming
- Microphone selection

**Changes:** None (direct adoption)

### 2. Screen Processor (Mark-XXXIX-OR)

**Location:** `jarvis/vision/screen.py`, `jarvis/vision/camera.py`

**Components:**
- Screen capture with mss
- Camera capture with OpenCV
- Image compression and optimization
- Gemini Vision integration

**Changes:** None (direct adoption)

### 3. Memory Manager (Mark-XXXIX-OR)

**Location:** `jarvis/memory/long_term.py`

**Components:**
- JSON-based persistent storage
- Category-based organization
- Memory extraction from conversations
- Automatic trimming

**Changes:** None (direct adoption)

### 4. Error Handler (Mark-XXXIX-OR)

**Location:** `jarvis/core/recovery.py`

**Components:**
- Error analysis
- Recovery strategy generation
- Fix suggestion

**Changes:** None (direct adoption)

### 5. Action Modules (Mark-XXXIX-OR)

| Module | Target | Changes |
|--------|--------|---------|
| open_app | `tools/system_tools.py` | Cross-platform abstraction |
| web_search | `tools/web_tools.py` | Generalize search |
| file_controller | `tools/file_tools.py` | Split into multiple tools |
| computer_settings | `tools/system_tools.py` | Merge into system |
| desktop | `tools/desktop_tools.py` | Cross-platform |
| computer_control | `tools/control_tools.py` | Cross-platform |
| browser_control | `tools/browser_tools.py` | Playwright integration |
| send_message | `tools/communication.py` | WhatsApp/Telegram |
| reminder | `tools/communication.py` | Task scheduling |
| weather_report | `tools/web_tools.py` | Weather API |
| youtube_video | `tools/media_tools.py` | Video control |

**Changes:** Cross-platform generalization, integration into tool registry

---

## Modify: Adaptation Required

### 1. Planner (Mark-XXXIX-OR → JARVIS)

**Original:** `agent/planner.py`  
**Target:** `core/planner.py`

**Required Changes:**
- Convert to async/await
- Update tool registry
- Add context injection
- Improve plan validation

**Effort:** Medium

### 2. Executor (Mark-XXXIX-OR → JARVIS)

**Original:** `agent/executor.py`  
**Target:** `core/executor.py`

**Required Changes:**
- Convert to async/await
- Integrate with tool registry
- Enhanced error recovery
- Add progress callbacks

**Effort:** Medium

### 3. Session Memory (Claude Code → JARVIS)

**Original:** `session.ts`  
**Target:** `memory/session.py`

**Required Changes:**
- Convert from TypeScript to Python
- Adapt to our memory base classes
- Keep message structure similar
- Add token estimation

**Effort:** Medium

### 4. Bash Tool (Claude Code → JARVIS)

**Original:** `BashTool.ts`  
**Target:** `tools/terminal_tools.py`

**Required Changes:**
- Convert from TypeScript to Python
- Add permission checking
- Add shell detection
- Handle dangerous commands

**Effort:** Medium

### 5. Tool Registry (Claude Code → JARVIS)

**Original:** `Tool.ts` + `tools.ts`  
**Target:** `tools/base.py` + `tools/registry.py`

**Required Changes:**
- Convert from TypeScript to Python
- Simplify permission system
- Remove TypeScript-specific features
- Keep permission levels

**Effort:** Medium

### 6. Main Agent (Mark-XXXIX-OR + Claude Code → JARVIS)

**Original:** `main.py` + `main.tsx`  
**Target:** `core/agent.py`

**Required Changes:**
- Combine voice loop + query engine
- Add memory integration
- Add tool registry integration
- Add speak callbacks

**Effort:** Medium

---

## Discard: Not Included

The following components are intentionally not included:

### 1. Tkinter UI

**Source:** Mark-XXXIX-OR (`ui.py`)

**Reason:** JARVIS uses a modern CLI interface (Rich + prompt_toolkit) instead of Tkinter.

**Alternative:** Use `jarvis/ui/cli.py`

### 2. OpenRouter Client

**Source:** Mark-XXXIX-OR (`or_client.py`)

**Reason:** Use direct Gemini API. OpenRouter adds unnecessary complexity.

**Alternative:** Use `jarvis/api/gemini.py`

### 3. Windows-Specific Code

**Source:** Various (`comtypes`, `winreg`, `pycaw`, `win10toast`)

**Reason:** JARVIS targets cross-platform. Windows-specific code removed.

**Alternative:** Cross-platform abstractions in tools

### 4. Game Updater

**Source:** Mark-XXXIX-OR (`game_updater.py`)

**Reason:** Low utility, Steam/Epic API specific. Not core to JARVIS.

**Alternative:** N/A

### 5. Basic Code Helper

**Source:** Mark-XXXIX-OR (`code_helper.py`)

**Reason:** Basic functionality. Replaced by better bash + script execution.

**Alternative:** `bash` and `run_script` tools

### 6. Dev Agent

**Source:** Mark-XXXIX-OR (`dev_agent.py`)

**Reason:** Overlaps with core executor. Merged into planner/executor.

**Alternative:** `core/planner.py` + `core/executor.py`

### 7. File Processor

**Source:** Mark-XXXIX-OR (`file_processor.py`)

**Reason:** Redundant with file_controller. Simpler tools replace it.

**Alternative:** `read_file`, `write_file` tools

### 8. Claude Code's Complex Tool System

**Source:** Claude Code (40+ TypeScript tools)

**Reason:** TypeScript-specific (schemas, permissions, rendering). Too complex for initial implementation.

**Alternative:** Simplified Python tool base class

---

## Future Phases

The following are deferred to future JARVIS versions:

### Phase 2: Enhanced Features

| Component | Source | Description |
|----------|--------|-------------|
| Multi-Agent | Claude Code | Coordinator/Swarm patterns |
| Memory Dir | Claude Code | Markdown-based long-term |
| Auto-dream | Claude Code | Memory consolidation |
| Plugin System | Claude Code | Extensibility |
| IDE Integration | Claude Code | VS Code/JetBrains |

### Phase 3: Advanced Capabilities

| Component | Source | Description |
|----------|--------|-------------|
| Bridge Protocol | Claude Code | Remote sessions |
| Team Memory | Claude Code | Multi-user support |
| Voice Native | Mark-XXXIX-OR | Full Gemini Live integration |

---

## Implementation Status

### Phase 1 Complete (v1.0.0)

| Category | Items | Status |
|----------|-------|--------|
| Voice Modules | 4 | ✅ Complete |
| Vision Modules | 5 | ✅ Complete |
| Desktop Tools | 6 | ✅ Complete |
| Agent Architecture | 4 | ✅ Complete |
| Memory Systems | 3 | ✅ Complete |
| Tool System | 13 | ✅ Complete |
| Planning Systems | 4 | ✅ Complete |

### Phase 2 Pending

| Category | Items | Status |
|----------|-------|--------|
| Multi-Agent | 1 | ⬜ Pending |
| Memory Extensions | 2 | ⬜ Pending |
| Plugin System | 1 | ⬜ Pending |
| IDE Integration | 1 | ⬜ Pending |

### Phase 3 Pending

| Category | Items | Status |
|----------|-------|--------|
| Bridge Protocol | 1 | ⬜ Pending |
| Team Memory | 1 | ⬜ Pending |
| Voice Native | 1 | ⬜ Pending |

---

## Notes

1. **API Keys:** Both Mark-XXXIX-OR and Claude Code use external APIs. JARVIS supports Gemini API directly.

2. **Language Differences:** Claude Code is TypeScript, Mark-XXXIX-OR is Python. JARVIS is Python for easier desktop integration.

3. **Cross-Platform:** Mark-XXXIX-OR is Windows-focused. JARVIS targets Linux, macOS, and Windows.

4. **Voice vs CLI:** Claude Code is CLI-only. JARVIS combines CLI with voice capabilities from Mark-XXXIX-OR.

---

*Document Version: 1.0.0*  
*Generated: 2026-06-23*
