"""
Self-improvement logging for JARVIS.
Tracks interactions and learns from outcomes.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class Outcome(Enum):
    """Interaction outcome types."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class InteractionLog:
    """A single interaction log entry."""
    timestamp: datetime
    input_text: str
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    response: str = ""
    outcome: Outcome = Outcome.UNKNOWN
    feedback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tools_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["outcome"] = self.outcome.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "InteractionLog":
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["outcome"] = Outcome(data["outcome"])
        return cls(**data)


@dataclass
class LearnedPattern:
    """A learned pattern from interactions."""
    pattern: str
    intent: str
    frequency: int = 1
    success_rate: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["last_seen"] = self.last_seen.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "LearnedPattern":
        data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)


class SelfImprovementLogs:
    """
    Tracks interactions and outcomes for self-improvement.
    Learns user patterns, command frequencies, and success rates.
    """

    def __init__(self, storage_path: Path = None):
        if storage_path is None:
            storage_path = Path.home() / ".jarvis" / "self_improvement.json"

        self.storage_path = storage_path
        self.interactions: List[InteractionLog] = []
        self.patterns: Dict[str, LearnedPattern] = {}
        self._stats: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load data from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                
                self.interactions = [
                    InteractionLog.from_dict(i) 
                    for i in data.get("interactions", [])
                ]
                self.patterns = {
                    k: LearnedPattern.from_dict(v)
                    for k, v in data.get("patterns", {}).items()
                }
                self._stats = data.get("stats", {})
                
                logger.info(f"Loaded {len(self.interactions)} interactions")
            except Exception as e:
                logger.warning(f"Failed to load self-improvement data: {e}")

    def _save(self) -> None:
        """Save data to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "interactions": [i.to_dict() for i in self.interactions],
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "stats": self._stats,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def log_interaction(
        self,
        input_text: str,
        intent: str,
        response: str = "",
        outcome: Outcome = Outcome.UNKNOWN,
        entities: Dict[str, Any] = None,
        tools_used: List[str] = None,
        duration_ms: float = 0.0,
        feedback: str = None,
        **context
    ) -> InteractionLog:
        """
        Log a new interaction.
        
        Args:
            input_text: User input
            intent: Detected intent
            response: JARVIS response
            outcome: Interaction outcome
            entities: Extracted entities
            tools_used: Tools used in this interaction
            duration_ms: Processing duration
            feedback: User feedback (correction/praise)
            **context: Additional context
            
        Returns:
            Created InteractionLog
        """
        log = InteractionLog(
            timestamp=datetime.now(),
            input_text=input_text,
            intent=intent,
            response=response,
            outcome=outcome,
            entities=entities or {},
            tools_used=tools_used or [],
            duration_ms=duration_ms,
            feedback=feedback,
            context=context
        )
        
        self.interactions.append(log)
        
        # Update patterns
        self._update_pattern(input_text, intent, outcome)
        
        # Update statistics
        self._update_stats(log)
        
        # Trim old interactions (keep last 1000)
        if len(self.interactions) > 1000:
            self.interactions = self.interactions[-1000:]
        
        self._save()
        return log

    def _update_pattern(
        self,
        input_text: str,
        intent: str,
        outcome: Outcome
    ) -> None:
        """Update learned patterns."""
        # Create pattern key from words
        words = input_text.lower().split()[:5]
        pattern_key = "_".join(words)
        
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
            
            # Update success rate
            if outcome == Outcome.SUCCESS:
                pattern.success_rate = (
                    pattern.success_rate * (pattern.frequency - 1) + 1.0
                ) / pattern.frequency
            elif outcome == Outcome.FAILED:
                pattern.success_rate = (
                    pattern.success_rate * (pattern.frequency - 1)
                ) / pattern.frequency
            
            # Add example
            if input_text not in pattern.examples:
                pattern.examples.append(input_text)
                if len(pattern.examples) > 10:
                    pattern.examples = pattern.examples[-10:]
        else:
            self.patterns[pattern_key] = LearnedPattern(
                pattern=pattern_key,
                intent=intent,
                frequency=1,
                success_rate=1.0 if outcome == Outcome.SUCCESS else 0.0,
                last_seen=datetime.now(),
                examples=[input_text]
            )

    def _update_stats(self, log: InteractionLog) -> None:
        """Update interaction statistics."""
        today = datetime.now().date().isoformat()
        
        if "daily" not in self._stats:
            self._stats["daily"] = {}
        
        if today not in self._stats["daily"]:
            self._stats["daily"][today] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "intents": Counter()
            }
        
        daily = self._stats["daily"][today]
        daily["total"] += 1
        
        if log.outcome == Outcome.SUCCESS:
            daily["success"] += 1
        elif log.outcome == Outcome.FAILED:
            daily["failed"] += 1
        
        daily["intents"][log.intent] += 1
        
        # Trim old daily stats
        cutoff = (datetime.now() - timedelta(days=30)).date().isoformat()
        self._stats["daily"] = {
            k: v for k, v in self._stats["daily"].items()
            if k >= cutoff
        }

    def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions."""
        recent = self.interactions[-limit:]
        return [i.to_dict() for i in reversed(recent)]

    def get_failed_interactions(self, limit: int = 10) -> List[Dict]:
        """Get failed interactions for analysis."""
        failed = [i for i in self.interactions if i.outcome == Outcome.FAILED]
        return [i.to_dict() for i in reversed(failed[-limit:])]

    def get_intent_stats(self) -> Dict[str, Any]:
        """Get intent statistics."""
        intent_counts = Counter(i.intent for i in self.interactions)
        intent_success = {}
        
        for intent in intent_counts:
            total = sum(1 for i in self.interactions if i.intent == intent)
            successes = sum(1 for i in self.interactions 
                          if i.intent == intent and i.outcome == Outcome.SUCCESS)
            intent_success[intent] = successes / total if total > 0 else 0
        
        return {
            "counts": dict(intent_counts.most_common(20)),
            "success_rates": intent_success
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Get daily statistics."""
        cutoff = (datetime.now() - timedelta(days=days)).date()
        stats = []
        
        for i in range(days):
            date = (cutoff + timedelta(days=i)).isoformat()
            if date in self._stats.get("daily", {}):
                d = self._stats["daily"][date]
                stats.append({
                    "date": date,
                    "total": d["total"],
                    "success": d["success"],
                    "failed": d["failed"],
                    "success_rate": d["success"] / d["total"] if d["total"] > 0 else 0
                })
            else:
                stats.append({
                    "date": date,
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "success_rate": 0
                })
        
        return stats

    def get_patterns(self, min_frequency: int = 2) -> List[Dict]:
        """Get learned patterns."""
        patterns = [
            p.to_dict() for p in self.patterns.values()
            if p.frequency >= min_frequency
        ]
        return sorted(patterns, key=lambda x: x["frequency"], reverse=True)

    def get_common_commands(self, limit: int = 10) -> List[Dict]:
        """Get most common commands."""
        commands = Counter(i.input_text for i in self.interactions)
        return [
            {"command": cmd, "count": count}
            for cmd, count in commands.most_common(limit)
        ]

    def get_tools_usage(self) -> Dict[str, int]:
        """Get tools usage statistics."""
        all_tools = []
        for log in self.interactions:
            all_tools.extend(log.tools_used)
        return dict(Counter(all_tools))

    def get_stats_summary(self) -> Dict:
        """Get comprehensive stats summary."""
        total = len(self.interactions)
        successes = sum(1 for i in self.interactions if i.outcome == Outcome.SUCCESS)
        failures = sum(1 for i in self.interactions if i.outcome == Outcome.FAILED)
        
        return {
            "total_interactions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "unique_patterns": len(self.patterns),
            "top_commands": self.get_common_commands(5),
            "top_intents": list(self.get_intent_stats()["counts"].items())[:5],
            "tools_usage": self.get_tools_usage()
        }

    def export_logs(self, path: Path) -> bool:
        """Export logs to file."""
        try:
            data = {
                "interactions": [i.to_dict() for i in self.interactions],
                "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
                "exported_at": datetime.now().isoformat()
            }
            
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
