"""
JARVIS Capability Router — Semantic Selection Authority
=========================================================
Single responsibility: Semantic capability matching and selection engine.

Features:
- Semantic & Intent Capability Matching: matches user intent prompts
  (e.g., "Paint me a cyberpunk city" -> generate_image, "Design a wallpaper" -> generate_image, "Read this PDF" -> speak/read_file)
  using token similarity and rich metadata scoring.
- Queries CapabilityDiscovery for the authoritative CapabilityCatalog.
- Provider-agnostic: NEVER knows specific provider backends (ComfyUI, Groq, etc.).
- Records observability metrics (Capability match latency).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from jarvis.core.capability_discovery import (
    CapabilityCatalog,
    CapabilityDiscovery,
    CapabilityInfo,
)
from jarvis.core.observability import get_observability

logger = logging.getLogger(__name__)


# Semantic Intent Concept Map for lightweight semantic matching
_SEMANTIC_CONCEPT_MAP: dict[str, list[str]] = {
    "generate_image": [
        "paint", "drawing", "illustration", "wallpaper", "cyberpunk", "logo",
        "art", "picture", "photo", "sketch", "portrait", "render", "design",
        "image", "visualize", "poster", "artwork", "avatar", "canvas",
    ],
    "speak": [
        "voice", "speak", "aloud", "read", "say", "talk", "hear", "listen",
        "audio", "sound", "tell", "tts", "speech", "recite", "pronounce",
    ],
    "open_camera": [
        "camera", "webcam", "photo", "snap", "picture", "selfie", "capture", "look", "see",
    ],
    "take_screenshot": [
        "screenshot", "screen", "capture", "desktop", "display", "monitor",
    ],
    "search_web": [
        "search", "web", "find", "google", "look up", "news", "articles", "information",
    ],
    "read_file": [
        "file", "document", "pdf", "read", "open", "contents", "text", "lines",
    ],
}


@dataclass
class CapabilityMatch:
    """A capability matched to user intent with confidence score."""

    capability: CapabilityInfo
    confidence: float  # 0.0 - 1.0
    matched_keywords: list[str] = field(default_factory=list)
    semantic_score: float = 0.0


class CapabilityRouter:
    """
    Pure Capability Selection Engine.
    """

    def __init__(self, discovery: CapabilityDiscovery | None = None) -> None:
        self.discovery = discovery or CapabilityDiscovery()
        self._observability = get_observability()

    def set_tool_registry(self, registry) -> None:
        self.discovery.set_tool_registry(registry)

    def set_plugin_manager(self, manager) -> None:
        self.discovery.set_plugin_manager(manager)

    def set_provider_manager(self, manager) -> None:
        self.discovery.set_provider_manager(manager)

    def discover_all(self) -> list[CapabilityInfo]:
        return self.discovery.discover_catalog().capabilities

    def get_catalog(self) -> CapabilityCatalog:
        return self.discovery.discover_catalog()

    def route_intent(
        self, intent_text: str, max_results: int = 5
    ) -> list[CapabilityMatch]:
        """
        Match intent text against CapabilityCatalog using semantic & metadata scoring.
        """
        start_ts = time.time()
        logger.debug("[CapabilityRouter] Routing intent: %r", intent_text)
        catalog = self.get_catalog()
        matches: list[CapabilityMatch] = []

        text_lower = intent_text.lower()
        tokens = set(text_lower.replace("-", " ").split())

        for cap in catalog.get_available():
            matched_kws = [kw for kw in cap.keywords if kw.lower() in text_lower or kw.lower() in tokens]
            matched_aliases = [a for a in cap.aliases if a.lower() in text_lower]

            # Semantic concept similarity match
            semantic_concepts = _SEMANTIC_CONCEPT_MAP.get(cap.name, [])
            semantic_hits = [c for c in semantic_concepts if c in text_lower or c in tokens]

            if not matched_kws and not matched_aliases and not semantic_hits:
                continue

            # Compute hybrid score
            kw_score = len(matched_kws) * 0.25
            alias_score = len(matched_aliases) * 0.35
            semantic_score = len(semantic_hits) * 0.40
            name_hits = sum(1 for w in cap.name.replace("_", " ").split() if w.lower() in text_lower)
            name_score = name_hits * 0.30

            total_score = (kw_score + alias_score + semantic_score + name_score) * (cap.priority / 100.0)
            total_score = min(total_score, 1.0)

            all_matched = list({*matched_kws, *matched_aliases, *semantic_hits})
            matches.append(CapabilityMatch(
                capability=cap,
                confidence=total_score,
                matched_keywords=all_matched,
                semantic_score=semantic_score,
            ))

        matches.sort(key=lambda m: m.confidence, reverse=True)
        result = matches[:max_results]

        latency_ms = (time.time() - start_ts) * 1000.0
        top_cap_name = result[0].capability.name if result else "none"
        self._observability.record_capability_match(top_cap_name, latency_ms)

        if result:
            logger.info(
                "[Capability Router] Matched capability: %s (confidence=%.2f, keywords=%s)",
                result[0].capability.name,
                result[0].confidence,
                result[0].matched_keywords,
            )
        else:
            logger.debug("[Capability Router] No capability matched intent: %r", intent_text)

        return result

    def find_capabilities_for_intent(
        self, intent_text: str, max_results: int = 5
    ) -> list[CapabilityMatch]:
        return self.route_intent(intent_text, max_results=max_results)

    def find_capability_by_name(self, name: str) -> CapabilityInfo | None:
        return self.get_catalog().find_by_name(name)

    def find_tool_by_name(self, name: str) -> CapabilityInfo | None:
        return self.find_capability_by_name(name)

    def has_capability(self, name: str) -> bool:
        cap = self.find_capability_by_name(name)
        return cap is not None and cap.availability

    def build_capabilities_prompt(self) -> str:
        catalog = self.get_catalog()
        caps = catalog.capabilities
        if not caps:
            return "(no capabilities registered)"

        lines: list[str] = []
        by_category: dict[str, list[CapabilityInfo]] = {}
        for cap in caps:
            by_category.setdefault(cap.category, []).append(cap)

        order = [
            "voice", "media", "web", "file", "system", "memory",
            "terminal", "communication", "plugin", "mcp", "provider", "general",
        ]
        sorted_cats = sorted(
            by_category.keys(),
            key=lambda c: order.index(c) if c in order else len(order),
        )

        for cat in sorted_cats:
            cat_caps = by_category[cat]
            lines.append(f"\n[{cat.upper()}]")
            for cap in cat_caps:
                lines.append(cap.to_prompt_line())

        return "\n".join(lines)

    def print_startup_report(self) -> None:
        catalog = self.get_catalog()
        caps = catalog.capabilities
        available = catalog.get_available()
        unavailable = [c for c in caps if not c.availability]

        print("\n" + "=" * 45)
        print("  JARVIS Capability Discovery")
        print("=" * 45)

        for cap in sorted(available, key=lambda c: c.category):
            print(f"  [+] {cap.name:<28} [{cap.category}] (v{cap.version})")

        if unavailable:
            print("\n  Unavailable:")
            for cap in unavailable:
                print(f"  [-] {cap.name:<28} [{cap.category}]")

        print("-" * 45)
        print(f"  Total capabilities: {len(caps)} ({len(available)} available)")
        print("=" * 45 + "\n")


_router: CapabilityRouter | None = None


def get_capability_router() -> CapabilityRouter:
    global _router
    if _router is None:
        _router = CapabilityRouter()
    return _router
