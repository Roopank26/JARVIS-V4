"""
Voice event helpers for JARVIS.

Provides typed event emission helpers and additional event constants
used across the voice subsystem. All events flow through the central
EventBus defined in ``jarvis.events``.
"""

from __future__ import annotations

from jarvis.events import EventBus, EventType, get_event_bus

# ---------------------------------------------------------------------------
# Additional voice-specific event types that extend the central EventType enum.
# We keep them as string constants rather than adding to the enum to avoid
# touching the shared events module (Feature 1.10).
# ---------------------------------------------------------------------------
VOICE_STARTED = "voice_started"
VOICE_STOPPED = "voice_stopped"
VOICE_INTERRUPTED = "voice_interrupted"
VOICE_RESUMED = "voice_resumed"
USER_STARTED_SPEAKING = "user_started_speaking"
USER_STOPPED_SPEAKING = "user_stopped_speaking"
STT_PARTIAL = "stt_partial"
STT_FINAL = "stt_final"
LLM_STREAM_STARTED = "llm_stream_started"
LLM_STREAM_TOKEN = "llm_stream_token"
LLM_STREAM_FINISHED = "llm_stream_finished"
TTS_STARTED = "tts_started"
TTS_CHUNK = "tts_chunk"
TTS_FINISHED = "tts_finished"
PLAYBACK_STARTED = "playback_started"
PLAYBACK_FINISHED = "playback_finished"
CONVERSATION_TIMEOUT = "conversation_timeout"


def emit_voice_started(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "started",
            "detail": VOICE_STARTED,
        },
    )


def emit_voice_stopped(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "stopped",
            "detail": VOICE_STOPPED,
        },
    )


def emit_voice_interrupted(bus: EventBus | None = None, reason: str = "") -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_INTERRUPT,
        {
            "reason": reason,
        },
    )


def emit_voice_resumed(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "resumed",
            "detail": VOICE_RESUMED,
        },
    )


def emit_user_started_speaking(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "user_speaking",
            "detail": USER_STARTED_SPEAKING,
        },
    )


def emit_user_stopped_speaking(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "user_stopped",
            "detail": USER_STOPPED_SPEAKING,
        },
    )


def emit_stt_partial(bus: EventBus | None = None, text: str = "") -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_TRANSCRIPT,
        {
            "partial": True,
            "text": text,
        },
    )


def emit_stt_final(bus: EventBus | None = None, text: str = "") -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_TRANSCRIPT,
        {
            "partial": False,
            "text": text,
        },
    )


def emit_llm_stream_started(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.TOKEN,
        {
            "detail": LLM_STREAM_STARTED,
        },
    )


def emit_llm_stream_token(bus: EventBus | None = None, token: str = "") -> None:
    (bus or get_event_bus()).emit(
        EventType.TOKEN,
        {
            "detail": LLM_STREAM_TOKEN,
            "token": token,
        },
    )


def emit_llm_stream_finished(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.TOKEN,
        {
            "detail": LLM_STREAM_FINISHED,
        },
    )


def emit_tts_started(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "tts_started",
            "detail": TTS_STARTED,
        },
    )


def emit_tts_chunk(bus: EventBus | None = None, index: int = 0) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "tts_chunk",
            "detail": TTS_CHUNK,
            "chunk": index,
        },
    )


def emit_tts_finished(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "tts_finished",
            "detail": TTS_FINISHED,
        },
    )


def emit_playback_started(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "playback_started",
            "detail": PLAYBACK_STARTED,
        },
    )


def emit_playback_finished(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "playback_finished",
            "detail": PLAYBACK_FINISHED,
        },
    )


def emit_conversation_timeout(bus: EventBus | None = None) -> None:
    (bus or get_event_bus()).emit(
        EventType.VOICE_STATE,
        {
            "state": "conversation_timeout",
            "detail": CONVERSATION_TIMEOUT,
        },
    )
