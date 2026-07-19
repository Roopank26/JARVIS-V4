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
