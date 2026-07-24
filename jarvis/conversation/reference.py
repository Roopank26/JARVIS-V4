"""
Reference Resolution for JARVIS.
Resolves pronouns and short references like:
  it, this, that, the previous one, yesterday's project, the last document,
  same folder, same browser, etc.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_PRONOUNS = {"it", "this", "that", "these", "those", "them", "him", "her", "us", "we"}
_ORDINAL_TOKENS = re.compile(
    r"^(?:the\s+)?(?:previous|last|current|next|recent|latest|same)\s+(?:one|document|file|project|folder|repo|repository|browser|window|app|application|build|test|task|note|summary|result|answer|response|version|branch|server|screen|terminal|editor)$",
    re.IGNORECASE,
)
_TIME_TOKENS = re.compile(
    r"^(?:(?:yesterday|today|tomorrow)(?:'s)?\s+.*?)$",
    re.IGNORECASE,
)


def classify_token(token: str) -> str | None:
    stripped = token.strip()
    if stripped.lower() in _PRONOUNS:
        return "pronoun"
    if _ORDINAL_TOKENS.match(stripped):
        return "ordinal"
    if _TIME_TOKENS.match(stripped):
        return "temporal"
    return None


def resolve_token(token: str, context: Any, history: Any) -> str | None:
    kind = classify_token(token)
    if kind == "pronoun":
        return _resolve_pronoun(token, context, history)
    if kind == "ordinal":
        return _resolve_ordinal(token, context, history)
    if kind == "temporal":
        return _resolve_temporal(token, context, history)
    return None


def _resolve_pronoun(pronoun: str, context: Any, history: Any) -> str | None:
    p = pronoun.lower()
    if p in {"it", "this"}:
        topic = getattr(context, "get_topic", lambda: None)()
        if topic:
            return topic
        last_user = getattr(context, "get_last_user_message", lambda: None)()
        if last_user:
            return last_user.content
        return None
    if p == "that":
        last_user = getattr(context, "get_last_user_message", lambda: None)()
        if last_user:
            return last_user.content
        return None
    if p == "them":
        topic = getattr(context, "get_topic", lambda: None)()
        if topic:
            return topic
        return None
    return None


def _resolve_ordinal(token: str, context: Any, history: Any) -> str | None:
    lowered = token.lower()
    recent_user = getattr(history, "get_recent_user_messages", lambda n: [])(8)
    recent_assistant = getattr(history, "get_recent_assistant_messages", lambda n: [])(8)
    all_recent = list(recent_user) + list(recent_assistant)

    if "project" in lowered or "repo" in lowered:
        for m in reversed(all_recent):
            text = m.content.lower()
            if "project" in text or "repo" in text or "repository" in text:
                words = text.split()
                for w in words:
                    if w.lower() not in {"project", "repository", "the", "my", "our", "a", "an"}:
                        return w
        topic = getattr(context, "get_topic", lambda: None)()
        if topic:
            return topic
        return None

    if "document" in lowered or "note" in lowered or "file" in lowered:
        for m in reversed(all_recent):
            text = m.content.lower()
            if any(k in text for k in ["document", "note", "file", "pdf", "summarize", "ingest"]):
                for w in m.content.split():
                    if w.lower() not in {"the", "my", "a", "an", "document", "note", "file", "summarize", "ingest"}:
                        return w
        return None

    if "folder" in lowered or "directory" in lowered:
        topic = getattr(context, "get_topic", lambda: None)()
        if topic and ("folder" in topic.lower() or "directory" in topic.lower() or "/" in topic):
            return topic
        return None

    if "browser" in lowered or "window" in lowered or "app" in lowered or "application" in lowered:
        tool = getattr(context, "get_active_tool", lambda: None)()
        if tool:
            return tool
        topic = getattr(context, "get_topic", lambda: None)()
        if topic:
            return topic
        return None

    if "build" in lowered or "test" in lowered:
        topic = getattr(context, "get_topic", lambda: None)()
        if topic:
            return topic
        return None

    return None


def _resolve_temporal(token: str, context: Any, history: Any) -> str | None:
    lowered = token.lower()
    topic = getattr(context, "get_topic", lambda: None)()
    if topic:
        return f"{topic} ({lowered})"
    return None


def expand_token(token: str, context: Any, history: Any) -> str | None:
    resolved = resolve_token(token, context, history)
    if resolved:
        return resolved
    return None
