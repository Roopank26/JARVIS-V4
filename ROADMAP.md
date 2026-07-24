# JARVIS V5 — Permanent Improvement Log

This file is the single source of truth for JARVIS evolution. Every discovered issue, friction point, or improvement opportunity is recorded here with root cause, impact, priority, proposed solution, and status.

Update this file continuously. Nothing should be forgotten.

---

## How to Use This Log

When you discover a problem during daily use:

1. Add it to the appropriate section below
2. Fill in: Description / Root Cause / Impact / Priority / Possible Solution / Status
3. Work on high-priority items first
4. Mark Status as: `open` → `in_progress` → `done` → `wontfix`

---

## Bugs

| # | Description | Root Cause | Impact | Priority | Possible Solution | Status |
|---|-------------|------------|--------|----------|-------------------|--------|
| 1 | Voice wake-word sometimes misses activation during noisy background | OpenWakeWord threshold not adaptive | User has to repeat command; trust degrades | High | Add adaptive threshold based on ambient noise level | open |
| 2 | Long-term memory JSON write can fail silently on disk full | No exception surfacing | Memory updates lost; no data corruption | Medium | Add retry with backoff + write-ahead temp file | open |
| 3 | Asyncio loop conflicts between Tkinter desktop UI and async backend | Desktop UI runs blocking mainloop | Voice/coding sessions stall when UI is open | High | Run Tkinter in dedicated thread with async bridge | open |
| 4 | Ollama provider fails to detect local model after restart | Provider init cached before Ollama boots | User must restart JARVIS after Ollama | Medium | Add health-check hook on each provider call | open |
| 5 | RAG ingestion crashes on corrupted PDF Page X of Y meta | PyPDF2 raises on some malformed PDFs | Document never indexed | Medium | Wrap page parse in try/except and skip bad pages | open |
| 6 | Memory search returns stale results after workspace refresh | ChromaDB collection not re-queried | Proactive suggestions reference deleted projects | Low | Invalidate Chroma cache on workspace change event | open |
| 7 | `jarvis doctor` exits non-zero on missing optional GPU | Exits early on optional dependency check | CI/pipeline scripts fail unnecessarily | Low | Make GPU check advisory, not fatal | open |

---

## Performance

| # | Description | Root Cause | Impact | Priority | Possible Solution | Status |
|---|-------------|------------|--------|----------|-------------------|--------|
| 1 | Cold startup takes >3s on Windows | Multiple sequential subsystem inits | User waits before first command | High | Parallelize subsystem init; lazy-load non-critical modules | open |
| 2 | Provider fallback chain adds 2-5s latency | Sequential health checks before each request | Response feels sluggish | High | Pre-warm provider availability in background; cache health | open |
| 3 | Long-term memory JSON load scales linearly | Full file read + json.load on every init | Slower as memory grows | Medium | Switch to append-only JSONL + periodic compaction | open |
| 4 | Voice latency from STT→TTS >1.5s | Whisper + LLM + gTTS chained synchronously | Conversation feels unnatural | Medium | Stream STT results; cache TTS for common phrases | open |
| 5 | RAG retrieval takes >800ms for small corpora | ChromaDB cold start + embedding overhead | Delays context-aware responses | Medium | Keep warm embedding model in memory; pre-compute at ingest | open |
| 6 | Desktop UI redraws on every EventBus message | No event throttling | CPU spike, UI jitter | Medium | Throttle STATUS events to 4Hz; batch RENDER events | open |
| 7 | Multiple redundant LLM calls per request | No query-result caching at orchestrator level | Token waste, latency, cost | High | Add LRU cache for semantically equivalent prompts | open |

---

## Missing Features

| # | Description | Reason Missing | Impact | Priority | Possible Solution | Status |
|---|-------------|----------------|--------|----------|-------------------|--------|
| 1 | Real daily Morning Brief with calendar, weather, GitHub, email, tasks | Prototype exists but not wired to real APIs | User manually checks each source | High | Wire scheduled fetch into `DailyAssistant`; render as structured text | open |
| 2 | Real Evening Summary with completed tasks, pending work, tomorrows priorities | Skeleton exists; needs real data aggregation | User does manual end-of-day review | High | Aggregate scheduler + memory + git status at configurable time | open |
| 3 | GitHub issue/PR awareness in workspace | No GitHub API integration | User switches to browser for PR status | High | Add GitHub API provider; inject into workspace awareness | open |
| 4 | Windows-native file operations (explorer integration, jump lists) | Cross-platform focus limited Windows UX | Extra steps for common file tasks | Medium | Add Windows-specific shell handlers using `pywin32` | open |
| 5 | Resume improvement mode — paste resume, get line-by-line feedback | No document-mode conversation | Manual resume editing | Medium | Add multi-turn document review agent | open |
| 6 | PDF reading + summarizationMode | RAG exists but no chat-over-pdf UX | User must manually extract text | Medium | Add `PDFChat` agent that indexes and answers over PDF | open |
| 7 | Terminal command safety layer (restricted mode for unfamiliar commands) | No sandboxing or review step | Risk of destructive commands | Medium | Add approval gate for commands not in user history | open |
| 8 | Clipboard history + context aware paste | No clipboard monitoring | Lost copied content between sessions | Low | Optional clipboard daemon with memory tagging | open |

---

## UX Improvements

| # | Description | Root Cause | Impact | Priority | Possible Solution | Status |
|---|-------------|------------|--------|----------|-------------------|--------|
| 1 | No visible progress indicator for long-running tasks | Executor runs silently until done | User unsure if JARVIS is stuck | High | Emit TASK_PROGRESS events every 5s; show in UI | open |
| 2 | Error messages are raw tracebacks | No error formatting layer | User sees scary Python stack traces | High | Add sanitized error formatter with recovery hints | open |
| 3 | Voice feedback absent during long tasks | No TTS progress events | User thinks voice failed | Medium | Emit periodic voice status updates | open |
| 4 | Desktop window always on top blocks other apps | Desktop config hardcoded to always-on-top | User must minimize to work elsewhere | Medium | Make always-on-top optional; default to normal window | open |
| 5 | No keyboard shortcut cheatsheet in desktop UI | Shortcuts exist but not discoverable | User learns slowly | Low | Add `Ctrl+/` hints overlay | open |
| 6 | Chat UI scroll resets on new message | No anchor-based scroll behavior | User loses reading position | Low | Maintain scroll anchor on append | open |

---

## AI Improvements

| # | Description | Root Cause | Impact | Priority | Possible Solution | Status |
|---|-------------|------------|--------|----------|-------------------|--------|
| 1 | Context window not managed; old messages silently dropped | MemoryManager has no rolling summary | Long sessions lose early context | High | Auto-summarize messages older than N tokens into memory | open |
| 2 | No persistent user preferences for tone, verbosity, style | PersonalityManager not actively used | Responses feel inconsistent | Medium | Explicit preference model loaded into system prompt | open |
| 3 | Provider selection is static priority-based, not context-aware | ProviderManager ignores task type | Expensive cloud model used for simple query | Medium | Route simple tasks to fast/cheap models; complex to reasoning models | open |
| 4 | No automatic task decomposition for complex requests | Planner prompt doesn't emphasize breaking down | Complex tasks fail or produce partial results | Medium | Add decompose-first rule to planner prompt | open |
| 5 | Memory retrieval is keyword-based only | No semantic reranking | Misses relevant memories with different wording | Medium | Rerank memory results with cross-encoder | open |
| 6 | No automatic citation in RAG responses | RAG returns chunks without attribution | User cannot verify facts | Medium | Include source + page in every RAG chunk response | open |

---

## Automation Ideas

| # | Description | Friction Point | Priority | Possible Solution | Status |
|---|-------------|----------------|----------|-------------------|--------|
| 1 | Morning Brief: weather, calendar, GitHub, email, tasks, research updates | Manual checking of 5+ sources | High | Scheduled agent that fetches all sources and prints concise brief | open |
| 2 | Coding Session: git status, changed files, TODOs, test failures, open issues | Context switching before coding | High | Workspace hook that auto-surfaces project state on session start | open |
| 3 | Study Session: notes, PDFs, flashcards, research queue | Manual file hunting | Medium | Study mode that opens relevant docs and creates flashcard prompts | open |
| 4 | Evening Summary: completed, pending, tomorrow priorities, lessons learned | Manual end-of-day reflection | High | Scheduled aggregation of daily tasks + memory + git log | open |
| 5 | Auto-commit helper: stage + commit with conventional message after tests pass | Manual git workflow | Medium | Post-test hook that opens commit dialog | open |
| 6 | Auto-backup memory + config before provider updates | Risk of config corruption | Low | Pre-update backup to `~/.jarvis/backups/` | open |
| 7 | Smart notification triage: summarize unread, prioritize by project | Notification overload | Medium | Periodic digest of notifications tagged by project relevance | open |

---

## Future Research

| # | Area | Question | Priority | Approach | Status |
|---|------|----------|----------|----------|--------|
| 1 | Local semantic reranking | Can a small local cross-encoder improve memory retrieval without API cost? | Medium | Benchmark `cross-encoder/ms-marco-MiniLM-L-6-v2` on memory queries | open |
| 2 | Voice interruption | Can we detect mid-sentence interruption to cancel TTS? | Low | Monitor audio input during playback; crossfade on detection | open |
| 3 | Predictive task execution | Can JARVIS run predictively useful background tasks based on patterns? | Low | Log task patterns; pre-warm likely next context | open |
| 4 | Multi-modal memory | Can screenshots + OCR enhance memory recall? | Low | Add periodic screenshot→OCR→memory pipeline | open |
| 5 | Planner self-correction | Can the planner detect its own failed assumptions and replan? | Medium | Post-failure analysis feeding back into planning prompt | open |

---

## Completed

| Date | Item | Section | Note |
|------|------|---------|-------|
| 2026-07-23 | Phase 1: "Perfect the Foundation" | Architecture / Testing / Monitoring | Eliminated duplicate/unused modules (planner_v2.py, intelligent.py, diagnostics.py, orchestration/engine.py), consolidated orchestration to MasterAgent wrapper, rewrote failing tests for new imports, created unified HealthMonitor with auto-recovery + tracemalloc memory leak detection + SystemResourceMonitor integration for resource-aware pause/resume, fixed 200+ ruff lint issues across jarvis/ source, registered all background services with explicit memory thresholds, 627 tests passing, 0 lint errors in jarvis/ |
| 2026-07-24 | Reasoning & Memory hardening | Core / Intelligence | Fixed orchestrator executor API mismatch (added `Executor.execute_step`), re-enabled memory fact extraction in `_extract_memory_facts`, made `ProviderManager.get_best_model_for_task` task-aware, added rolling context-window summarization in `SessionMemory` to preserve early conversation context, 735 tests passing, ruff clean, improved system-prompt context injection |

---

## Maintenance

- Review this log at least once per week.
- Convert `open` bugs/features into code changes during active sessions.
- Close stale items after 30 days of no activity with a brief reason.
- Keep descriptions user-focused, not implementation-focused.
