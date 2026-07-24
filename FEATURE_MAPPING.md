# JARVIS-V4 Feature Mapping & Enhancement Plan

## Existing Architecture

### Core
- `core/agent.py` — Intent-classification-driven agent with 70+ intent types
- `core/planner.py` — LLM-driven plan generation with dynamic tool discovery
- `core/executor.py` — Plan execution with retry, re-plan, and cancellation
- `core/master_agent.py` — Facade wiring Goal context + AGW Director routing
- `core/config.py` — Settings management
- `core/agent_registry.py` — Agent registry
- `core/provider_manager.py` — Multi-provider LLM selection
- `core/provider_health_monitor.py` — Provider health checks
- `core/capability_router.py` — Capability routing
- `core/dashboard.py` — Dashboard metrics
- `core/context_bus.py` — Shared context bus
- `core/observability.py` — Observability layer
- `core/reflection.py` — Self-reflection
- `core/task_engine.py` — Task engine

### AI / AGW Layer
- `agw/orchestrator.py` — AGW orchestrator with Director routing
- `agw/directors.py` — 9 specialized directors
- `agw/project_intelligence.py` — Project intelligence
- `agw/reasoning.py` — AI reasoning engine
- `agw/work_session.py` — Work session management
- `agw/self_improvement.py` — Self-improvement

### Agents
- `agents/multi_agent.py` — Multi-agent orchestration
- `agents/vision_agent.py` — Vision agent (image, OCR, UI analysis)
- `agents/collaboration.py` — Agent collaboration

### Memory
- `memory/memory_manager.py` — Unified memory manager
- `memory/enhanced.py` — Enhanced memory manager
- `memory/session.py` — Session memory
- `memory/long_term.py` — Long-term persistent memory
- `memory/semantic.py` — Semantic search memory
- `memory/knowledge_graph.py` — Knowledge graph
- `memory/knowledge.py` — Local knowledge base (TF-IDF + ChromaDB)
- `memory/user_profile.py` — User profile

### Voice
- `voice/voice_events.py` — Voice event types
- `voice/voice_router.py` — Voice routing
- `voice/voice_runtime.py` — Voice runtime
- `voice/production.py` — Production voice
- `voice/listener.py` — Voice listener
- `voice/streaming_stt.py` — Streaming STT (faster-whisper)
- `voice/streaming_tts.py` — Streaming TTS
- `voice/vad.py` — Voice activity detection
- `voice/wake_word.py` — Wake word detection
- `voice/interrupt_manager.py` — Interrupt/barge-in
- `voice/audio_queue.py` — Audio queue
- `voice/audio.py` — Audio utilities
- `voice/speech_state.py` — Speech state machine

### RAG
- `rag/rag_system.py` — RAG system with document ingestion
- `rag/document_processor.py` — Document processing (chunking)
- `document_processor.py` — Study assistant

### Research
- `research/research_agent.py` — Research agent with web search, monitoring
- `research/pipeline.py` — Research pipeline
- `research/production.py` — Production research

### Tools
- `tools/registry.py` — Tool registry
- `tools/base.py` — Base tool class
- `tools/browser_tools.py` — Browser tools
- `tools/camera_tool.py` — Camera/screenshot tool
- `tools/file_tools.py` — File operations
- `tools/image_gen_tool.py` — Image generation
- `tools/speak_tool.py` — TTS tool
- `tools/system_tools.py` — System info
- `tools/terminal_tools.py` — Terminal execution

### Desktop / Workspace
- `desktop/` — Desktop automation
- `workspace/` — Workspace management

### Coding
- `coding/` — Coding agent, repo analysis

### Web Services
- `api/gemini.py` — LLM client wrapper
- `api/providers.py` — Provider APIs
- `api/os.py` — OS interaction

### Plugins
- `plugins/plugin_manager.py` — Plugin loader
- `plugins/marketplace.py` — Plugin marketplace
- `plugins/base.py` — Base plugin class
- `plugins/example_plugin.py` — Example plugin

### UI
- `ui/app.py` — UI composition root
- `ui/server.py` — aiohttp web server with WebSocket
- `ui/static/index.html` — Glassmorphism SPA with sidebar navigation
- `ui/static/css/` — CSS modules (theme, layout, components, chat, aicore, panels, animations, responsive)
- `ui/static/js/` — JavaScript modules

### Supporting
- `events.py` — Event bus (decoupled pub/sub)
- `activity.py` — Activity center (event history)
- `palette.py` — Command palette
- `tools_library.py` — Dynamic tool discovery
- `skills/manager.py` — Skill manager
- `suggestions.py` — Suggestion engine
- `metrics.py` — Metrics tracking
- `monitoring/` — Monitoring
- `notifications/` — Notifications
- `proactive/` — Proactive features
- `security/` — Security layer
- `integrations/` — External integrations
- `evolution/` — Self-evolution

## Existing Features

| Category | Status | Details |
|----------|--------|---------|
| Multi-Provider LLM | ✅ Complete | Groq, Ollama, Gemini, OpenAI, Anthropic, OpenRouter, LM Studio, AirLLM |
| Voice I/O | ✅ Excellent | Streaming STT (faster-whisper), streaming TTS (Piper/Edge/pyttsx3/gTTS), wake word, VAD, barge-in |
| Memory | ✅ Excellent | Session, long-term JSON, semantic search, user profiles, self-improvement |
| RAG | ✅ Good | Document ingestion (PDF, DOCX, HTML), semantic search, ChromaDB + TF-IDF fallback |
| Research | ✅ Complete | Web search via Tavily/Wikipedia/DDG, monitoring, citation, report generation |
| Coding | ✅ Good | Repo indexing, AST analysis, security scanning |
| Desktop Automation | ✅ Complete | Window management, clipboard, app launching, file reveal |
| Plugins | ✅ Good | Hot-loadable with hooks, marketplace, example plugin |
| Scheduler | ✅ Complete | Cron-like tasks, daily summaries, daily briefing |
| Premium UI | ✅ Complete | Glassmorphism SPA, command palette, timeline, analytics, notifications, settings |
| Diagnostics | ✅ Complete | `jarvis doctor` health checks |
| Multi-Agent | ✅ Complete | AGW with 9 Directors, multi-agent collaboration |
| Vision | ✅ Good | Image understanding, OCR, UI element detection, screenshot analysis |
| Browser | ✅ Good | Selenium-based browser tools |
| PDF | ✅ Basic | Basic PDF ingestion via pypdf2 |
| Agent Skills | ✅ Good | SkillManager with metrics and self-improvement |
| Activity Timeline | ✅ Complete | EventBus-based activity center |
| AI Dashboard | ✅ Complete | Live metrics, status indicators |
| Skills Library | ✅ Good | Auto-discovery from registry + plugins |
| Workspace | ✅ Good | File/folder management |
| GitHub | ✅ Partial | Basic repo analysis in coding module |

## Missing Capabilities / Enhancement Opportunities

| Category | Gap | Recommended Enhancement |
|----------|-----|------------------------|
| **Advanced RAG** | No hybrid search (no simple BM25/BM25-like parallel), no reranking, no exact citations with page numbers, limited chunking strategies | Add BM25 + vector hybrid, cross-encoder reranker, citation tracking per chunk, improved chunking (recursive, semantic) |
| **Vision Agent** | No image comparison, no video analysis, no batch vision | Add compare-images tool, video-frame extraction, batch OCR |
| **Browser Agent** | Limited to Selenium, no smart extraction, no article summarization pipeline | Add playwright alternative, content extraction with readability, article summarization |
| **Coding Agent** | No documentation generation, no test generation, no dependency analysis, no refactoring suggestions | Add AST-based tools for docs/tests/refactoring |
| **Research Agent** | Good but no deep research mode, no multi-doc comparison | Add deep research with iterative refinement, compare across sources |
| **Voice** | No live transcription streaming to UI, no voice profiles | Add voice profile manager, stream transcripts to event bus |
| **PDF Expert** | No table extraction, no PDF comparison, no smart citation | Add table extraction with tabula/plumber, PDF diff, citation metadata |
| **GitHub Agent** | No commit summaries, branch summaries, release notes, issue tracking | Add GitHub API tools for commits, branches, releases, issues |
| **Plugin System** | No sandboxing, no version management, no plugin marketplace browsing | Add plugin versioning, dependency management, sandbox |
| **Activity Timeline** | Good but could show more granular phases | Add more detailed phases (thinking, reading, executing) |
| **AI Dashboard** | Could show CPU, RAM, token usage, provider latency | Add system metrics, provider latency display, token tracking |
| **Skills Library** | Good foundation but limited built-in skills | Add 10+ reusable skills (analyze repo, explain code, summarize PDF, compare files) |
| **Autonomous Tasks** | No autonomous workflow scheduler | Add task pipeline with approval gates |
| **UI** | Could add more Iron Man aesthetic elements | Add more animations, live arc reactor, better status indicators |
| **Provider Manager** | Good but no token usage tracking, no model capability detection | Add token counter, model capability matrix |
| **Workspace Agent** | Basic but no terminal management | Add integrated terminal with safety checks |
| **Notification System** | Basic but no proactive notifications | Add proactive alert system |
| **Security** | Good safety gates but no audit log | Add audit trail for all actions |

## awesome-llm-apps Design Patterns to Adopt

| Pattern | Source App | How to Integrate |
|---------|-----------|------------------|
| Agentic RAG with reasoning | Agentic RAG with Reasoning | Add step-by-step reasoning to RAG queries |
| Hybrid search | Hybrid Search RAG | Combine BM25 + vector, use best of both |
| Multi-agent routing | AG2 Adaptive Research Team | Extend director routing with confidence scores |
| Self-improving skills | Self-Improving Agent Skills | Enhance existing skill optimizer |
| Multi-source research | Deep Research Agent | Add iterative research with source comparison |
| Corrective RAG | CRAG | Add self-grading and retry logic |
| Trust-gated actions | Trust-Gated Multi-Agent | Add hash-chained audit trail (already partially exists) |
| Always-on agents | Always-on HN Briefing | Extend scheduled tasks to proactive monitoring |
| Voice RAG | Voice RAG Agent | Stream RAG results to TTS |
| Generative UI | Generative UI Starter | Add dynamic UI components for reports/plans |

## Implementation Plan (Phased)

### Phase 1: Core Quality + RAG (Weeks 1-3)
- Enhanced RAG: hybrid search, reranking, better citations
- PDF Expert: table extraction, comparison, smart citations
- Provider Manager: token tracking, latency display

### Phase 2: Agent Intelligence (Weeks 4-6)
- GitHub Agent: repo analysis, commits, branches, issues
- Coding Agent: documentation generation, test generation, dependency analysis
- Vision Agent: image comparison, video frames, batch processing

### Phase 3: Orchestration + Skills (Weeks 7-9)
- Skills Library expansion (12+ skills)
- Autonomous Tasks scheduler with approval gates
- Multi-Agent improvements with confidence-based routing

### Phase 4: UI/UX + Polish (Weeks 10-12)
- Dashboard enhancements (CPU, RAM, tokens, latency)
- Activity Timeline granularity
- Plugin system improvements
- UI animations and Iron Man aesthetic touches
