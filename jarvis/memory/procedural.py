"""
JARVIS Procedural Memory — Stores HOW to perform tasks (skills).

A skill is a reusable procedure extracted from successful episodes.
Skills persist across sessions and improve with use.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillStep:
    """A single step in a skill."""
    order: int
    action: str
    tool: str = ""
    parameters_template: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    optional: bool = False
    failure_action: str = ""  # what to do if this step fails


@dataclass
class Skill:
    """A learned, reusable procedure."""
    id: str
    name: str
    purpose: str
    steps: list[SkillStep] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    expected_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    recovery_strategies: list[str] = field(default_factory=list)
    confidence: float = 0.5
    success_count: int = 0
    failure_count: int = 0
    total_uses: int = 0
    version: int = 1
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    provenance: list[str] = field(default_factory=list)  # episode IDs
    tags: set[str] = field(default_factory=set)
    immutable: bool = False  # security-critical skills cannot be auto-modified

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "purpose": self.purpose,
            "steps": [
                {"order": s.order, "action": s.action, "tool": s.tool,
                 "parameters_template": s.parameters_template,
                 "description": s.description, "optional": s.optional,
                 "failure_action": s.failure_action}
                for s in self.steps
            ],
            "prerequisites": self.prerequisites,
            "expected_inputs": self.expected_inputs,
            "expected_outputs": self.expected_outputs,
            "tools_required": self.tools_required,
            "failure_conditions": self.failure_conditions,
            "recovery_strategies": self.recovery_strategies,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_uses": self.total_uses,
            "version": self.version,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "provenance": self.provenance,
            "tags": list(self.tags),
            "immutable": self.immutable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skill:
        steps = [
            SkillStep(
                order=s.get("order", 0),
                action=s.get("action", ""),
                tool=s.get("tool", ""),
                parameters_template=s.get("parameters_template", {}),
                description=s.get("description", ""),
                optional=s.get("optional", False),
                failure_action=s.get("failure_action", ""),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            purpose=data.get("purpose", ""),
            steps=steps,
            prerequisites=data.get("prerequisites", []),
            expected_inputs=data.get("expected_inputs", []),
            expected_outputs=data.get("expected_outputs", []),
            tools_required=data.get("tools_required", []),
            failure_conditions=data.get("failure_conditions", []),
            recovery_strategies=data.get("recovery_strategies", []),
            confidence=data.get("confidence", 0.5),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            total_uses=data.get("total_uses", 0),
            version=data.get("version", 1),
            created_at=data.get("created_at", 0),
            last_used=data.get("last_used", 0),
            provenance=data.get("provenance", []),
            tags=set(data.get("tags", [])),
            immutable=data.get("immutable", False),
        )

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_uses, 1)

    def record_use(self, success: bool):
        self.total_uses += 1
        self.last_used = time.time()
        if success:
            self.success_count += 1
            # Bounded confidence increase
            self.confidence = min(0.95, self.confidence + 0.02 * (1 - self.confidence))
        else:
            self.failure_count += 1
            self.confidence = max(0.1, self.confidence - 0.05)


class ProceduralMemory:
    """
    Stores and retrieves learned skills.
    
    Supports:
    - Skill discovery by goal/tags
    - Prerequisite validation
    - Confidence-based ranking
    - Skill versioning
    - Persistence
    """

    CONFIDENCE_PROMOTION_THRESHOLD = 0.7
    MAX_SKILLS = 200

    def __init__(self, storage_path: Path | None = None):
        self._path = storage_path or Path.home() / ".jarvis" / "memory" / "skills.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                for s_data in data.get("skills", []):
                    skill = Skill.from_dict(s_data)
                    self._skills[skill.id] = skill
                    self._index_skill(skill)
                logger.info(f"Loaded {len(self._skills)} skills")
            except Exception as e:
                logger.warning(f"Failed to load skills: {e}")

    def _save(self):
        try:
            with open(self._path, "w") as f:
                json.dump(
                    {"skills": [s.to_dict() for s in self._skills.values()]},
                    f, indent=1,
                )
        except OSError as e:
            logger.error(f"Failed to save skills: {e}")

    def _generate_id(self, name: str) -> str:
        return hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:10]

    def _index_skill(self, skill: Skill):
        for tag in skill.tags:
            normalized = tag.lower()
            self._tag_index.setdefault(normalized, [])
            if skill.id not in self._tag_index[normalized]:
                self._tag_index[normalized].append(skill.id)
        # Also index by name words
        for word in skill.name.lower().split():
            if len(word) >= 3:
                self._tag_index.setdefault(word, [])
                if skill.id not in self._tag_index[word]:
                    self._tag_index[word].append(skill.id)

    def create_skill(
        self,
        name: str,
        purpose: str,
        steps: list[SkillStep],
        tools_required: list[str] | None = None,
        tags: set[str] | None = None,
        provenance: list[str] | None = None,
        confidence: float = 0.5,
        immutable: bool = False,
    ) -> Skill:
        """Create and store a new skill."""
        skill = Skill(
            id=self._generate_id(name),
            name=name,
            purpose=purpose,
            steps=steps,
            tools_required=tools_required or [],
            tags=tags or set(),
            provenance=provenance or [],
            confidence=confidence,
            immutable=immutable,
        )
        self._skills[skill.id] = skill
        self._index_skill(skill)
        self._save()
        return skill

    def discover(self, goal: str, limit: int = 5) -> list[Skill]:
        """Find skills that match a goal.

        Scoring priorities (highest to lowest):
          1. Exact tag match for a highly distinctive tag (few skills share it)
          2. Multiple matching tags
          3. Single generic tag match

        Distinctiveness is measured by how few skills share a tag.
        Tags shared by very few skills get a large bonus so that an exact
        distinctive match is never crowded out by generic matches.
        """
        words = set(goal.lower().split())
        candidates: dict[str, float] = {}

        for word in words:
            if len(word) < 3:
                continue
            if word not in self._tag_index:
                continue
            matching_sids = self._tag_index[word]
            # Distinctiveness bonus: fewer skills sharing the tag → higher bonus.
            #   1 skill  → +10
            #   2-5      → +5
            #   6-20     → +2
            #   21+      → +1
            n = len(matching_sids)
            if n <= 1:
                tag_score = 10.0
            elif n <= 5:
                tag_score = 5.0
            elif n <= 20:
                tag_score = 2.0
            else:
                tag_score = 1.0
            for sid in matching_sids:
                candidates[sid] = candidates.get(sid, 0.0) + tag_score

        if not candidates:
            # Fallback: scan all skills by purpose text
            for sid, skill in self._skills.items():
                if any(w in skill.purpose.lower() for w in words):
                    candidates[sid] = 1.0

        # Sort by score descending, then by skill name for determinism
        results = []
        for sid, _score in sorted(
            candidates.items(),
            key=lambda x: (-x[1], self._skills[x[0]].name if x[0] in self._skills else ""),
        ):
            if sid in self._skills:
                results.append(self._skills[sid])
            if len(results) >= limit:
                break

        return results

    def get_skill(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    def update_skill(self, skill_id: str, success: bool, episode_id: str = ""):
        """Update skill confidence based on outcome."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.record_use(success)
        if episode_id and episode_id not in skill.provenance:
            skill.provenance.append(episode_id)
        self._save()

    def get_promotable_skills(self) -> list[Skill]:
        """Get skills with confidence above promotion threshold."""
        return [
            s for s in self._skills.values()
            if s.confidence >= self.CONFIDENCE_PROMOTION_THRESHOLD
            and s.total_uses >= 3
            and not s.immutable
        ]

    def rollback_skill(self, skill_id: str) -> bool:
        """Roll back a skill's confidence on repeated failures."""
        skill = self._skills.get(skill_id)
        if not skill or skill.immutable:
            return False
        skill.confidence = max(0.1, skill.confidence - 0.2)
        skill.version += 1
        self._save()
        return True

    def get_stats(self) -> dict[str, Any]:
        total_uses = sum(s.total_uses for s in self._skills.values())
        return {
            "total_skills": len(self._skills),
            "total_uses": total_uses,
            "avg_confidence": (
                sum(s.confidence for s in self._skills.values()) / max(len(self._skills), 1)
            ),
            "promotable": len(self.get_promotable_skills()),
        }
