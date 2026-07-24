# JARVIS Architecture — Phase 2 Evolution

This document preserves the existing JARVIS architecture and maps every Phase 2 enhancement to concrete integration points. The goal is evolution, not replacement.

---

## 1. Current JARVIS Architecture

### 1.1 Core Loop

```
User Input
    │
    ▼
┌─────────────────┐
│ Intent Router   │  Pattern-based + LLM classification
└────────┬────────┘
         │
   ┌─────┴────┬────────┬────────┬────────┬────────┬────────┐
   ▼          ▼        ▼        ▼        ▼        ▼
Profile   Memory    RAG    Research  Desktop  Tools
   │          │        │        │        │        │
   └────┬─────┴────────┴────────┴────────┴────────┘
         │
         ▼
   ┌────────────┐
   │   Agent    │  Planner → Executor → Response
   └─────┬──────┘
         │
   ┌────┴────┐
   ▼         ▼
Memory   Tools
```

### 1.2 Core Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `JarvisAgent` | `jarvis/core/agent.py` | Intent routing, orchestration |
| `Planner` | `jarvis/core/planner.py` | LLM-driven plan generation |
| `Executor` | `jarvis/core/executor.py` | Plan execution with retry |
| `ProviderManager` | `jarvis/core/provider_manager.py` | Priority-based LLM fallback |
| `EventBus` | `jarvis/events.py` | Pub/sub for UI/backend decoupling |
| `MemoryManager` | `jarvis/memory/memory_manager.py` | Session + long-term JSON memory |
| `EnhancedMemoryManager` | `jarvis/memory/enhanced.py` | Memory + user profile |
| `ToolRegistry` | `jarvis/tools/registry.py` | Extensible tool discovery/execution |
| `RAGSystem` | `jarvis/rag/` | Document ingestion + semantic search |
| `VoiceEngine` | `jarvis/voice/` | STT/TTS/wake-word pipeline |
| `Orchestrator` | `jarvis/orchestrator.py` | Streaming + visible reasoning stages |
| `PluginManager` | `jarvis/plugins/` | Hot-loadable plugins |

### 1.3 Key Patterns

- **Async-first**: Heavy use of `asyncio` throughout the stack
- **Intent classification**: Regex + LLM hybrid routing in `JarvisAgent`
- **Provider fallback**: Priority-based chain (`local` → `cloud` → `fallback`)
- **Tool registry**: Central `ToolRegistry` with permissions, execution, callbacks
- **Event-driven UI**: `EventBus` decouples backend logic from Web UI

---

## 2. Gap Analysis

This section maps every requested Phase 2 component to JARVIS's existing systems.

### 2.1 Master Agent (JARVIS Core)

**Request:** A single Master Agent that all UIs talk to; user never contacts internal agents directly.

**Current state:** `jarvis/core/agent.py`'s `JarvisAgent` already acts as the central orchestrator, but:
- Voice, Desktop UI, Web UI, and CLI initialize and call it independently
- Some flows bypass `JarvisAgent` and call planners/executors directly
- No single public entry enforces the requested flow

**Enhancement path:**
1. Formalize `JarvisAgent` as the sole process request path.
2. Wrap all other entrypoints (`voice/`, `desktop/`, `ui/`, `__main__.py`) in a facade that delegates to `JarvisAgent.process()`.
3. Add a `Goal` object passed through the pipeline so memory/planner/executor share context.
4. Surface progress/errors through the existing `EventBus`.

**Risk:** Medium. Some advanced flows (background tasks, proactive monitor) currently operate semi-independently and must remain nested inside the Master Agent's orchestration.

**Complexity:** Low–Medium (facade `+` goal plumbing)

### 2.2 Capability Discovery Service

**Request:** Dynamic inventory of providers/models/tools/hardware before planning.

**Current state:** None. Capability knowledge is implicit:
- `ProviderManager` knows providers/models when initialized
- `ToolRegistry` knows tools when registered
- Hardware checks exist in `jarvis doctor` but not programmatically

**Enhancement path:**
1. Add `CapabilityDiscovery` module under `jarvis/core/`.
2. Surface providers, tools, plugins, OS, CUDA, Ollama/LM Studio, running services, browser state.
3. Inject capability snapshot into planning context.
4. Reuse existing `ProviderManager.list_models()` and `ToolRegistry.list_tools()`.

**Risk:** Low. Discovery is read-only and additive.

**Complexity:** Medium (needs hardware/OS introspection heuristics)

### 2.3 Dynamic Agent Registry

**Request:** Agents dynamically registered, lazily loaded, with health/version/dependencies — never hardcoded.

**Current state:** `ToolRegistry` exists for tools, but agents are not first-class:
- Some "agents" are classes like `ResearchAgent`, `VSCodeBridge` instantiated inline
- No central registry

**Enhancement path:**
1. Create `AgentRegistry` mirroring `ToolRegistry`:
   - `register(agent_cls, metadata)`
   - `get(name)`
   - `list_available()`
2. Move `ResearchAgent`, `VSCodeBridge`, future agents into the registry.
3. Lazy-load heavy modules (`importlib` + entrypoints).
4. Health check callback per agent.

**Risk:** Medium. Existing code instantiates agents directly; refactor requires care.

**Complexity:** Medium

### 2.4 Shared Context Bus

**Request:** Structured context exchange (task/goal/context/memory/progress/errors/plans/results).

**Current state:** `EventBus` emits typed events, but:
- No structured task/goal envelope
- Main memory is JSON/file based; not real-time shareable across agents

**Enhancement path:**
1. Extend `JarvisEvent.data` schema with optional `task_id`, `goal_id`, `context`, `memory_slice`.
2. Add `ContextBus` facade on top of `EventBus`:
   - `publish_task(task_id, ctx)`
   - `publish_result(task_id, result)`
   - `subscribe_goal(goal_id, handler)`
3. Reduce redundant LLM calls by caching memory slices on the bus.

**Risk:** Low. Extends `EventBus`; backward compatible.

**Complexity:** Medium

### 2.5 Goal Memory

**Request:** Track current goal, subgoals, priorities, dependencies, completion estimates.

**Current state:** `MemoryManager` stores facts/conversations/preferences/projects.

**Enhancement path:**
1. Extend `MemoryManager` persistence schema in `~/.jarvis/memory/long_term.json` with a `goals` section.
2. Add `GoalMemory` layer with CRUD for:
   - `current_goal`
   - `subgoals[]`
   - `priority`
   - `dependencies[]`
   - `status` (active/blocked/completed)
3. Expose `get_current_goal_context()` for planner/executor prompts.

**Risk:** Low. Schema extension is additive.

**Complexity:** Low–Medium

### 2.6 Reflection Loop

**Request:** Post-task analysis → lessons learned → memory update → future recommendations.

**Current state:** `PersonalityManager` and daily assistant exist but not per-task reflection.

**Enhancement path:**
1. Add `ReflectionEngine`:
   - Auto-invoked after `Executor` completes or fails.
   - Prompts LLM with outcome + plan + tool results + user feedback.
   - Stores `LessonsLearned` entries in `MemoryManager`.
2. Hook into `EventBus`:
   - Emit `REFLECTION` event after each task.
   - Forward recommendations to proactive suggestions.

**Risk:** Low. Triggered after completion; no blocking path.

**Complexity:** Medium (prompt engineering + persistence)

### 2.7 Long Running Task Engine

**Request:** Background tasks (research, monitoring, downloads) with pause/resume/cancel/progress/notifications/recovery.

**Current state:** `BackgroundIntelligence` exists, but it's scheduler-style (intervals).

**Enhancement path:**
1. Create `LongRunningTaskEngine`:
   - `TaskHandle` with `pause()`, `resume()`, `cancel()`, `progress()`
   - Persist state to `~/.jarvis/tasks/` for recovery.
   - Emit `EventType.TASK` + `BACKGROUND_COMPLETE` events.
2. Integrate with JARVIS Core so `Executor` can delegate to async tasks.

**Risk:** Medium. Persistence/recovery across process restarts is non-trivial.

**Complexity:** Medium–High

### 2.8 Knowledge Graph

**Request:** Relationship-based memory (User → Projects → Goals → Agents → Providers → Tools → Documents).

**Current state:** Linear JSON memory + ChromaDB semantic search.

**Enhancement path:**
1. Optional `knowledge_graph.json` in `~/.jarvis/memory/`.
2. Nodes: entity types. Edges: typed relationships.
3. Hybrid search:
   - Semantic via ChromaDB (existing)
   - Graph traversal via simple adjacency + query matching
4. Add `to_prompt_context()` enrichment using graph edges.

**Risk:** Low. Optional layer; existing memory continues to work unchanged.

**Complexity:** Medium

### 2.9 AI OS Dashboard

**Request:** Internal dashboard showing agents, tasks, goals, memory, providers, plugins, logs, health.

**Current state:** `ui/` has a web UI; `metrics.py`, `diagnostics.py`, `status` events exist.

**Enhancement path:**
1. Add `dashboard/` module generating a snapshot object:
   - `AgentRegistry` state
   - `LongRunningTaskEngine` state
   - `GoalMemory` state
   - `MemoryManager` stats
   - `ProviderManager` health
   - `CapabilityDiscovery` results
2. Expose via existing Web UI endpoints + `EventType.STATUS`.

**Risk:** Low. Read-only aggregation.

**Complexity:** Low–Medium

### 2.10 Intelligent Reasoning Pipeline

**Request:** Replace simple request-response with multi-stage intent detection → capability discovery → memory recall → goal analysis → planning → agent selection → tool selection → execution → self-review → reflection → memory update → response generation.

**Current state:** Already close:
- Intent Router exists
- Planner + Executor exist
- Memory recall exists
- EventBus exists

**Gaps:** Capability discovery, agent selection, self-review, goal awareness, reflection.

**Enhancement path:**
1. Add `ReasoningPipeline`:
   - `detect_intent()`
   - `discover_capabilities()`
   - `recall_memory()`
   - `analyze_goal()`
   - `create_plan()` (existing)
   - `select_agent()` (new)
   - `select_tools()` (existing)
   - `execute()` (existing)
   - `self_review()`
   - `reflect()` (new)
   - `update_memory()`
   - `generate_response()`
2. Each stage emits `EventType.STAGE` for observability.
3. Stages are pluggable; new stages can be added via plugins.

**Risk:** Low. Composes existing components; no breaking changes.

**Complexity:** Medium–High (prompt/stage orchestration)

---

## 3. Preserved Existing Architecture

The following systems are explicitly preserved and enhanced, never replaced:

| System | Preservation Strategy |
|--------|----------------------|
| Provider Manager | Add discovery hooks; keep priority fallback |
| Planner | Add context/goal input; keep JSON plan output |
| Executor | Add long-running + interrupt hooks; keep retry |
| EventBus | Extend schema; keep sync pub/sub |
| Memory | Add goals/knowledge graph; keep session/long-term/semantic |
| SQLite | Add new tables/goals; keep existing schemas |
| ChromaDB | Add graph-augmented queries; keep vector search |
| Voice Engine | Add goal context; keep wake-word/STT/TTS |
| Plugin System | Add agent/tool discovery; keep lifecycle hooks |
| RAG | Add graph enrichment; keep ingestion/search |
| Desktop UI | Add dashboard panel; keep existing UX |
| Web UI | Add dashboard APIs; keep streaming/events |
| ToolRegistry | Add lazy loading/health; keep registration API |
| AgentOrchestrator | Add goal/task orchestration; keep composition |
| Existing APIs | Add new endpoints only; keep `/api/v1` compatibility |

---

## 4. Implementation Roadmap

### Phase 2.0 — Foundation

1. **Master Agent Facade**
   - Enforce `JarvisAgent` as single entry point internally.
   - Add `Goal` data model and thread it through planner/executor.

2. **Capability Discovery Service**
   - Introspect providers, tools, hardware, services.
   - Add to planner context.

3. **Goal Memory**
   - Extend memory schema with goals.
   - Add `GoalMemory` reader/writer.

### Phase 2.1 — Registry & Context

4. **Dynamic Agent Registry**
   - Mirror `ToolRegistry` for agents.
   - Migrate `ResearchAgent`, `VSCodeBridge` into registry.

5. **Shared Context Bus**
   - Add task/goal envelopes to `EventBus`.
   - Publish/subscribe by `task_id`/`goal_id`.

6. **Intelligent Reasoning Pipeline**
   - Build staged pipeline (intent → goal → plan → execute → review → reflect).

### Phase 2.2 — Intelligence & Persistence

7. **Reflection Loop**
   - Post-task analysis + lesson persistence.

8. **Knowledge Graph**
   - Add graph layer to memory; hybrid search.

9. **Long Running Task Engine**
   - Background tasks with pause/resume/cancel + persistence.

### Phase 2.3 — Visibility & Polish

10. **AI OS Dashboard**
    - Aggregate module states into a single view.
    - Web UI + optional terminal dashboard.

---

## 5. Integration Points

| New Component | Integrates With | Integration Type |
|---------------|----------------|------------------|
| Master Agent | `JarvisAgent`, all UIs | Facade + Goal plumbing |
| Capability Discovery | `ProviderManager`, `ToolRegistry` | Read-only snapshot |
| Agent Registry | `PluginManager`, existing agents | Registration + lazy loading |
| Context Bus | `EventBus` | Schema extension |
| Goal Memory | `MemoryManager` | Schema extension |
| Reflection Engine | `Executor`, `MemoryManager`, `EventBus` | Post-hook + emit events |
| Task Engine | `Executor`, `EventBus` | Delegation + persistence |
| Knowledge Graph | `MemoryManager`, ChromaDB | Optional layer |
| Dashboard | `EventBus`, all modules | Read-only aggregation |
| Reasoning Pipeline | Planner, Executor, Registry, Context Bus | Orchestration facade |

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Breaking backward compatibility | Medium | High | Keep existing APIs stable; add new endpoints |
| Performance regressions | Medium | Medium | Benchmark before/after each phase |
| State management complexity | Medium | High | Globally-scoped bus + immutable snapshots |
| Dependency drift | Low | Medium | Pin new deps; prefer stdlib where possible |
| Test coverage gaps | Medium | Medium | Add tests per phase; validate with existing suite |

---

## 7. Complexity Estimates

| Component | Complexity | Effort |
|-----------|-----------|--------|
| Master Agent | Low–Medium | 2–3 days |
| Capability Discovery | Medium | 2–3 days |
| Agent Registry | Medium | 2–3 days |
| Context Bus | Medium | 2–3 days |
| Goal Memory | Low–Medium | 1–2 days |
| Reflection Engine | Medium | 2–4 days |
| Task Engine | Medium–High | 3–5 days |
| Knowledge Graph | Medium | 2–3 days |
| Dashboard | Low–Medium | 1–2 days |
| Reasoning Pipeline | Medium–High | 3–5 days |

---

## 8. Recommended Implementation Order

1. `Goal Memory`
2. `Master Agent`
3. `Capability Discovery`
4. `Agent Registry`
5. `Context Bus`
6. `Reasoning Pipeline`
7. `Reflection Engine`
8. `Task Engine`
9. `Knowledge Graph`
10. `Dashboard`

Rationale: data models first (`Goal Memory`), then routing (`Master Agent`, `Capability Discovery`), then registry/context, then higher-order intelligence.

---

## 9. Design Principles

1. **Never break existing APIs.** Enhance in place.
2. **Make new features opt-in/default-hidden.** Disable features through config when needed.
3. **Prefer composition over inheritance.** Reuse existing components through facades and event hooks.
4. **Prefer async and events.** Keep the async-first posture.
5. **Keep the backend independent of the UI.** The event bus is the contract.
6. **Minimize new dependencies.** Use stdlib + existing deps where possible.
7. **Every change must be testable.**
8. **Document architectural decisions inline in code and in `CHANGELOG.md`.**
