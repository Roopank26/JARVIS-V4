# JARVIS Desktop Assistant - Roadmap

**Version:** 3.0.0  
**Status:** IN PROGRESS  
**Target:** Production Desktop Assistant

---

## Vision

JARVIS v3.0 transforms from a prototype into a persistent desktop assistant that runs continuously in the background, learning from interactions, proactively assisting with tasks, and seamlessly integrating with the developer's workflow.

---

## Implementation Status

### Completed (v3.0 Foundation)
- Plugin architecture (`jarvis/plugins/base.py`)
- Wake word detection (`jarvis/voice/wake_word.py`)
- Task scheduler (`jarvis/services/scheduler.py`)
- Project memory (`jarvis/memory/project.py`)
- Voice state machine

### In Progress
- Background service mode
- Continuous listening
- System tray integration

### Planned (v3.1+)
- Local knowledge base (ChromaDB)
- VS Code extension
- Daily summaries
- Self-improvement logs
- Desktop notifications
- File system watcher

---

## Feature Specifications

### 1. Wake Word Detection - DONE
Wake word engine for continuous "Jarvis" detection with voice activity detection.

### 2. Plugin Architecture - DONE
Extensible plugin system for custom commands and integrations.

### 3. Task Scheduler - DONE
Cron-like scheduling for recurring tasks and reminders.

### 4. Project Memory - DONE
Per-project context tracking with Git integration.

### 5. Background Service (TODO)
Persistent daemon with autostart and crash recovery.

### 6. VS Code Integration (TODO)
Two-way communication for enhanced developer experience.

---

## File Structure

```
JARVIS/
├── jarvis/
│   ├── core/              # Agent, planner, executor
│   ├── voice/
│   │   ├── audio.py      # STT/TTS
│   │   └── wake_word.py  # Wake word (DONE)
│   ├── memory/
│   │   ├── session.py
│   │   ├── long_term.py
│   │   └── project.py    # (DONE)
│   ├── services/
│   │   ├── scheduler.py  # (DONE)
│   │   └── notifier.py   # (TODO)
│   ├── plugins/
│   │   ├── base.py       # (DONE)
│   │   └── manager.py    # (TODO)
│   └── integrations/
│       └── vscode.py      # (TODO)
├── tests/
│   └── test_desktop.py   # (DONE)
└── docs/
```

---

## Dependencies

```txt
# New for v3.0
croniter>=1.4.0          # Cron parsing
porcupine>=2.0.0        # Wake word (optional)

# Future
chromadb>=0.4.0          # Knowledge base
sentence-transformers>=2.2.0
watchdog>=3.0.0         # File watcher
plyer>=2.0.0            # Notifications
```

---

## Next Steps

1. Implement background service (systemd/LaunchAgent)
2. Add system tray integration
3. Implement continuous listening loop
4. Create VS Code extension bridge
5. Add ChromaDB knowledge base

---

*Last updated: 2026-06-23*
