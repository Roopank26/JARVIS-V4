"""
Long-term memory system for JARVIS - persistent JSON storage.
Adapted from Mark-XXXIX-OR's memory_manager.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from jarvis.memory.knowledge_graph import KnowledgeGraph


class LongTermMemory:
    """
    Persistent long-term memory storage.
    Stores personal facts, preferences, projects, etc.
    """

    MAX_VALUE_LENGTH = 380
    MEMORY_MAX_CHARS = 2200

    def __init__(self, memory_path: Path | None = None, knowledge_graph: KnowledgeGraph | None = None):
        if memory_path is None:
            base_dir = self._get_base_dir()
            memory_dir = base_dir / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            self.memory_path = memory_dir / "long_term.json"
        else:
            self.memory_path = memory_path

        self._lock = Lock()
        self._knowledge_graph = knowledge_graph
        self._load_or_initialize()

    def _get_base_dir(self) -> Path:
        """Get the base directory for JARVIS config."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent.parent

    def _empty_memory(self) -> dict:
        """Return the empty memory structure."""
        return {
            "identity": {},
            "preferences": {},
            "projects": {},
            "relationships": {},
            "wishes": {},
            "notes": {},
            "goals": {},
        }

    def _load_or_initialize(self):
        """Load existing memory or initialize new."""
        if not self.memory_path.exists():
            self._memory = self._empty_memory()
            self._save()
            return

        with self._lock:
            try:
                with open(self.memory_path, encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    # Ensure all required categories exist
                    base = self._empty_memory()
                    for key in base:
                        if key not in data:
                            data[key] = {}
                    self._memory = data
                else:
                    self._memory = self._empty_memory()
            except Exception as e:
                print(f"[Memory] Load error: {e}")
                self._memory = self._empty_memory()

    @property
    def memories(self) -> dict:
        """Expose stored memory dict (backward compatibility)."""
        return self._memory

    def load(self) -> dict:
        """Load and return the full memory."""
        with self._lock:
            return self._memory.copy()

    def _save(self):
        """Save memory to disk."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        # Trim to limit before saving
        memory = self._trim_to_limit(self._memory)

        with self._lock, open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)

    def _all_entries(self, memory: dict) -> list:
        """Get all memory entries sorted by update time."""
        entries = []
        for category, items in memory.items():
            if not isinstance(items, dict):
                continue
            for key, entry in items.items():
                if isinstance(entry, dict) and "value" in entry:
                    entries.append((category, key, entry))

        # Sort by timestamp (oldest first)
        entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
        return entries

    def _trim_to_limit(self, memory: dict) -> dict:
        """Trim memory if it exceeds the size limit."""
        serialized = json.dumps(memory, ensure_ascii=False)
        if len(serialized) <= self.MEMORY_MAX_CHARS:
            return memory

        entries = self._all_entries(memory)

        for category, key, _ in entries:
            if len(json.dumps(memory, ensure_ascii=False)) <= self.MEMORY_MAX_CHARS:
                break
            del memory[category][key]
            print(f"[Memory] Trimmed {category}/{key}")

        return memory

    def _truncate_value(self, val: str) -> str:
        """Truncate a value if it exceeds the max length."""
        if isinstance(val, str) and len(val) > self.MAX_VALUE_LENGTH:
            return val[: self.MAX_VALUE_LENGTH].rstrip() + "…"
        return val

    def remember(self, key: str, value: Any, category: str = "notes") -> bool:
        """
        Store a value in long-term memory.

        Args:
            key: The key to store under
            value: The value to store
            category: Memory category (identity, preferences, projects, etc.)

        Returns:
            True if memory was updated, False otherwise
        """
        valid_categories = {
            "identity",
            "preferences",
            "projects",
            "relationships",
            "wishes",
            "notes",
        }
        if category not in valid_categories:
            category = "notes"

        # Ensure category exists
        if category not in self._memory:
            self._memory[category] = {}

        # Truncate and store
        truncated_value = self._truncate_value(str(value))
        entry = {"value": truncated_value, "updated": datetime.now().strftime("%Y-%m-%d")}

        existing = self._memory[category].get(key, {})
        if not isinstance(existing, dict) or existing.get("value") != truncated_value:
            self._memory[category][key] = entry
            self._save()
            return True

        return False

    def recall(self, query: str, knowledge_graph: KnowledgeGraph | None = None) -> list:
        """
        Recall memories matching a query.
        Simple keyword matching for now.
        """
        results = []
        query_lower = query.lower()

        for category, items in self._memory.items():
            if not isinstance(items, dict):
                continue
            for key, entry in items.items():
                if isinstance(entry, dict):
                    value = entry.get("value", "")
                    if query_lower in key.lower() or query_lower in value.lower():
                        results.append(
                            {
                                "key": key,
                                "value": value,
                                "category": category,
                                "updated": entry.get("updated", ""),
                            }
                        )

        graph = knowledge_graph or self._knowledge_graph
        if graph is not None:
            try:
                graph_results = graph.search(query, limit=10)
                for gr in graph_results:
                    data = gr.get("data", {})
                    label = data.get("label", "")
                    node_type = data.get("type", "")
                    props = data.get("properties", {})
                    text_blob = f"{label} {node_type} {json.dumps(props)}".lower()
                    if query_lower in text_blob:
                        results.append(
                            {
                                "key": data.get("id", label),
                                "value": label,
                                "category": f"graph:{node_type}",
                                "updated": "",
                                "source": "knowledge_graph",
                            }
                        )
            except Exception:
                pass

        seen = set()
        deduped = []
        for r in results:
            k = (r.get("key"), r.get("category"))
            if k not in seen:
                seen.add(k)
                deduped.append(r)
        return deduped

    def semantic_search(self, query: str, limit: int = 5) -> list:
        """
        Semantic search using embeddings (if available) or keyword matching.

        Args:
            query: Natural language query
            limit: Maximum results to return

        Returns:
            List of relevant memory entries
        """
        # Try semantic embeddings if available
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer

            # Load model
            if not hasattr(self, "_embedding_model"):
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

            query_embedding = self._embedding_model.encode([query])[0]

            # Get embeddings for all entries
            entries = []
            embeddings = []

            for category, items in self._memory.items():
                if not isinstance(items, dict):
                    continue
                for key, entry in items.items():
                    if isinstance(entry, dict):
                        text = f"{key} {entry.get('value', '')}"
                        entries.append(
                            {
                                "key": key,
                                "value": entry.get("value", ""),
                                "category": category,
                                "updated": entry.get("updated", ""),
                            }
                        )
                        embeddings.append(self._embedding_model.encode([text])[0])

            # Calculate similarities
            results = []
            for i, emb in enumerate(embeddings):
                sim = np.dot(query_embedding, emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(emb)
                )
                results.append((entries[i], sim))

            # Sort and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            return [r[0] for r in results[:limit]]

        except ImportError:
            # Fallback to keyword search
            return self.recall(query)[:limit]

    def forget(self, key: str, category: str = "notes") -> bool:
        """
        Remove a key from memory.

        Returns:
            True if key was found and removed, False otherwise
        """
        if category not in self._memory:
            return False

        if key in self._memory[category]:
            del self._memory[category][key]
            self._save()
            return True

        return False

    def get_category(self, category: str) -> dict[str, Any]:
        """Get all entries in a category."""
        return self._memory.get(category, {}).copy()

    def get_identity(self) -> dict[str, Any]:
        """Get identity information."""
        return self.get_category("identity")

    def get_preferences(self) -> dict[str, Any]:
        """Get user preferences."""
        return self.get_category("preferences")

    def get_projects(self) -> dict[str, Any]:
        """Get user projects."""
        return self.get_category("projects")

    def _goal_to_dict(self, goal: dict) -> dict:
        if isinstance(goal, dict):
            return goal
        return {"value": str(goal), "updated": datetime.now().strftime("%Y-%m-%d")}

    def save_goal(
        self,
        key: str,
        value: Any,
        status: str = "active",
        priority: str = "medium",
        dependencies: str = "",
        estimated_completion: str = "",
        subgoals: str = "",
    ) -> bool:
        category = "goals"
        if category not in self._memory:
            self._memory[category] = {}

        entry = self._goal_to_dict(value)
        entry.update({
            "status": status,
            "priority": priority,
            "dependencies": dependencies,
            "estimated_completion": estimated_completion,
            "subgoals": subgoals,
            "updated": datetime.now().strftime("%Y-%m-%d"),
        })

        existing = self._memory[category].get(key, {})
        serialized = json.dumps(entry, ensure_ascii=False)
        existing_serialized = json.dumps(existing, ensure_ascii=False)
        if existing.get("value") == entry["value"] and existing.get("status") == status and existing_serialized == serialized:
            return False

        self._memory[category][key] = entry
        self._save()
        return True

    def get_goal(self, key: str, category: str = "goals") -> dict[str, Any] | None:
        goal = self.get_category(category).get(key)
        if goal is None:
            return None
        if isinstance(goal, dict) and "value" in goal:
            return goal
        return {"value": str(goal), "updated": ""}

    def get_goals(self) -> dict[str, Any]:
        """Get all goals."""
        return self.get_category("goals")

    def get_goals_by_status(self, status: str) -> list[dict[str, Any]]:
        goals = self.get_category("goals")
        return [
            {"key": key, **entry}
            for key, entry in goals.items()
            if isinstance(entry, dict) and entry.get("status", "active") == status
        ]

    def get_current_goal(self) -> dict[str, Any] | None:
        goals = self.get_category("goals")
        for key, entry in goals.items():
            if isinstance(entry, dict) and entry.get("status", "active") == "active":
                return {"key": key, **entry}
        return None

    def update_goal_status(self, key: str, status: str, category: str = "goals") -> bool:
        if category not in self._memory:
            return False
        if key not in self._memory[category]:
            return False
        entry = self._memory[category][key]
        if isinstance(entry, dict):
            entry["status"] = status
            entry["updated"] = datetime.now().strftime("%Y-%m-%d")
            self._save()
            return True
        return False

    def remove_goal(self, key: str, category: str = "goals") -> bool:
        return self.forget(key, category)

    def format_for_prompt(self, memory: dict | None = None) -> str:
        """
        Format memory for inclusion in a prompt.
        Adapted from Mark-XXXIX-OR's format_memory_for_prompt.
        """
        if memory is None:
            memory = self._memory.copy()

        lines = []

        # Identity
        identity = memory.get("identity", {})
        id_fields = ["name", "age", "birthday", "city", "job", "language", "school"]
        for field in id_fields:
            entry = identity.get(field)
            if entry:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"{field.title()}: {val}")
        for key, entry in identity.items():
            if key in id_fields:
                continue
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{key.replace('_', ' ').title()}: {val}")

        # Preferences
        prefs = memory.get("preferences", {})
        if prefs:
            lines.append("")
            lines.append("Preferences:")
            for key, entry in list(prefs.items())[:15]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        # Projects
        projects = memory.get("projects", {})
        if projects:
            lines.append("")
            lines.append("Active Projects / Goals:")
            for key, entry in list(projects.items())[:8]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        # Relationships
        rels = memory.get("relationships", {})
        if rels:
            lines.append("")
            lines.append("People in their life:")
            for key, entry in list(rels.items())[:10]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        if not lines:
            return ""

        header = "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally]\n"
        result = header + "\n".join(lines)

        if len(result) > 2000:
            result = result[:1997] + "…"

        return result + "\n"

    def format_goals_for_prompt(self) -> str:
        goals = self.get_category("goals")
        if not goals:
            return ""
        lines = ["Current Goals:"]
        for key, entry in list(goals.items())[:10]:
            if not isinstance(entry, dict):
                continue
            status = entry.get("status", "active")
            if status == "completed":
                continue
            val = entry.get("value", "")
            priority = entry.get("priority", "medium")
            deps = entry.get("dependencies", "")
            parts = [f"  - {key.replace('_', ' ').title()}: {val} [{priority}]"]
            if deps:
                parts.append(f"    Depends on: {deps}")
            lines.extend(parts)
        if len(lines) <= 1:
            return ""
        return "\n".join(lines) + "\n"

    def clear(self):
        """Clear all long-term memory."""
        self._memory = self._empty_memory()
        self._save()
