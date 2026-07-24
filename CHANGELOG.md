# Changelog

All notable changes to JARVIS-V4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-18

### Production Ready
- Runtime validation completed successfully
- 362 tests passing (6 skipped)
- No import cycles
- No Unicode issues
- Logging standardized across all modules
- Exception handling improved with typed exceptions
- Duplicate code removed
- Dead code removed
- Imports cleaned and organized

### Features
- Multi-provider LLM support: Groq (primary), Ollama (local), Gemini (fallback)
- Voice I/O: Wake-word detection, STT (Whisper/faster-whisper), TTS (Piper/Edge-TTS/pyttsx3/gTTS)
- Persistent memory: Session memory, long-term JSON storage, semantic memory, user profiles
- Extensible tool registry with permission levels and async execution
- File management, terminal execution, desktop automation
- LLM-driven multi-step task planning with automatic replanning
- RAG: Document ingestion (PDF, DOCX, HTML), semantic search, study assistant
- Research agent: Web research with multi-source monitoring and citation
- Coding agent: Repository indexing, AST analysis, security scanning
- Plugin system: Hot-loadable plugins with intent/tool/memory hooks
- Scheduler: Cron-like scheduled tasks and daily summaries
- System tray: Background desktop mode with tray icon
- Diagnostics: `jarvis doctor` comprehensive system health checks

### Architecture
- Centralized agent orchestration with intent classification
- Async-first design throughout
- Lazy imports to prevent circular dependencies
- Configuration management via `~/.jarvis/`
- Extensible provider manager for LLM backends

### Bug Fixes
- Fixed encoding issues for Windows console output
- Fixed audio device detection and calibration
- Fixed voice runtime initialization race conditions
- Fixed memory formatting for prompt injection prevention
- Fixed RAG search relevance scoring

### Performance
- Optimized tool registry lookup
- Reduced memory footprint of session history
- Improved RAG chunking performance
- Cached audio device queries

### Documentation
- Professional README with badges, TOC, examples, FAQ
- Consolidated architecture and audit documentation
- Added contribution guide and troubleshooting section

### Packaging
- Added `pyproject.toml` with modern Python packaging
- Added entry points: `jarvis` and `jarvis-doctor`
- Added optional dependency groups: `dev`, `voice`, `local-ai`, `rag`, `all`
- Added MIT License

### CI/CD
- Added GitHub Actions workflow for testing, linting, and import validation

## [2.1.0] - 2026-07-24

### Fixed
- Fixed critical `orchestrator.py` API mismatch: plan steps were routed through `executor.execute(tool, params)` which collided with the planner/executor contract (`execute(goal, context)`). Added a dedicated `Executor.execute_step()` primitive and wired the orchestrator to use it.
- Re-enabled `agent.py._extract_memory_facts()`: it now actually extracts profile facts from user input and captures explicit `remember`/`note` commands instead of returning an empty list.
- Made `ProviderManager.get_best_model_for_task()` task-aware: heavier reasoning tasks now prefer larger/task models when available; simple tasks prefer smaller/faster models.

### Improved
- Added rolling context-window management in `SessionMemory`: older turns are summarized into a `_rolling_summary` string before they are retired, so long conversations retain earlier context in the system prompt.
- Agent system prompt now injects the rolling summary alongside long-term memory and active goal.

### Verification
- `ruff check jarvis/` passes with zero errors.
- Full test suite: 735 passed, 8 skipped.

### Added
- Persistent conversation context across turns with state tracking
- Intelligent follow-up understanding for pronouns and references (`it`, `this`, `that`, `the previous one`, `yesterday's project`, etc.)
- Conversation memory with automatic fact extraction and long-term storage
- Task interruption support via `request_interrupt()` / `clear_interrupt()` on the agent and executor cancel flag
- Proactive assistant monitoring rules for repository indexing, tests, builds, and research completions
- Smart notification manager with levels: `info`, `success`, `warning`, `reminder`, `background`
- Notification grouping, dismissal, timestamps, and non-intrusive toast events
- Desktop automation extensions: `minimize_window`, `maximize_window`, `open_folder`, `search_files`, `switch_window`
- Workspace awareness: current repository, active branch, recent files, running servers, editor, prompt context injection
- Daily assistant mode with morning briefing, development status, and evening summary routines
- Background intelligence loop with low-priority housekeeping tasks
- Personality manager with concise natural-language response templates
- Adaptive suggestion engine with behavior pattern tracking
- Voice + desktop synchronization through event bus (`WORKFLOW`, `INTERRUPT`, `CONTEXT_RESET`, `BACKGROUND_COMPLETE` events)

### Changed
- Bumped version to `2.0.0`
- Agent `process()` now maintains conversation context, resolves references, and emits structured intent routing through `_process_with_intent()`
- Orchestrator wires proactive monitor, notification manager, and workspace awareness at initialization
- All new modules are optional imports with graceful fallback in `jarvis/__init__.py`

### Tests
- Added `tests/test_phase2_features.py` with 30+ new tests covering conversation context, reference resolution, notifications, proactive monitor, workspace awareness, daily assistant, background intelligence, personality, agent interrupts, and desktop extensions
- Full suite: 520+ tests passing, 0 failures
