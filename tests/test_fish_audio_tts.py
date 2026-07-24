"""
Tests for Fish Audio TTS Provider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.voice.fish_audio_tts import (
    FishAudioConfig,
    FishAudioTTS,
    TTSProvider,
)
from jarvis.voice.voice_runtime import VoiceComponentStatus


class TestFishAudioConfig:
    """Tests for FishAudioConfig."""

    def test_from_env_reads_variables(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
        monkeypatch.setenv("FISH_AUDIO_VOICE_ID", "test-voice")
        config = FishAudioConfig.from_env()
        assert config.api_key == "test-key"
        assert config.voice_id == "test-voice"

    def test_from_env_defaults_empty(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("FISH_AUDIO_API_KEY", raising=False)
        monkeypatch.delenv("FISH_AUDIO_VOICE_ID", raising=False)
        config = FishAudioConfig.from_env()
        assert config.api_key == ""
        assert config.voice_id == ""

    def test_is_configured_true(self):
        config = FishAudioConfig(api_key="key", voice_id="voice")
        assert config.is_configured() is True

    def test_is_configured_false_no_key(self):
        config = FishAudioConfig(api_key="", voice_id="voice")
        assert config.is_configured() is False

    def test_is_configured_false_no_voice(self):
        config = FishAudioConfig(api_key="key", voice_id="")
        assert config.is_configured() is False

    def test_validate_speed_out_of_range(self):
        config = FishAudioConfig(api_key="key", voice_id="voice", speed=3.0)
        error = config.validate()
        assert "Speed" in error

    def test_validate_volume_out_of_range(self):
        config = FishAudioConfig(api_key="key", voice_id="voice", volume=1.5)
        error = config.validate()
        assert "Volume" in error

    def test_validate_valid(self):
        config = FishAudioConfig(api_key="key", voice_id="voice")
        assert config.validate() is None


class TestFishAudioTTS:
    """Tests for FishAudioTTS."""

    def setup_method(self):
        self.config = FishAudioConfig(api_key="test-key", voice_id="test-voice")
        self.tts = FishAudioTTS(self.config)

    def test_init(self):
        assert self.tts.status == VoiceComponentStatus.NOT_INITIALIZED
        assert self.tts.config.api_key == "test-key"
        assert self.tts.config.voice_id == "test-voice"

    def test_init_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("FISH_AUDIO_API_KEY", "env-key")
        monkeypatch.setenv("FISH_AUDIO_VOICE_ID", "env-voice")
        tts = FishAudioTTS()
        assert tts.config.api_key == "env-key"
        assert tts.config.voice_id == "env-voice"

    @pytest.mark.asyncio
    async def test_initialize_fails_without_aiohttp(self):
        with patch.dict("sys.modules", {"aiohttp": None}):
            tts = FishAudioTTS(self.config)
            result = await tts.initialize()
            assert result.success is False
            assert tts.status == VoiceComponentStatus.DISABLED

    @pytest.mark.asyncio
    async def test_initialize_validates_config(self):
        bad_config = FishAudioConfig(api_key="", voice_id="")
        tts = FishAudioTTS(bad_config)
        result = await tts.initialize()
        assert result.success is False
        assert tts.status == VoiceComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_speak_returns_none_when_not_ready(self):
        audio = await self.tts.speak("hello")
        assert audio is None

    @pytest.mark.asyncio
    async def test_speak_returns_none_for_empty_text(self):
        self.tts.status = VoiceComponentStatus.READY
        audio = await self.tts.speak("")
        assert audio is None

    @pytest.mark.asyncio
    async def test_synthesize_stream_empty_when_not_ready(self):
        chunks = []
        async for chunk in self.tts.synthesize_stream("hello"):
            chunks.append(chunk)
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_get_status_returns_dict(self):
        status = self.tts.get_status()
        assert isinstance(status, dict)
        assert status["provider"] == "fish_audio"
        assert status["model"] == "s2.1-pro"

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self):
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        self.tts._session = mock_session
        self.tts.status = VoiceComponentStatus.READY
        await self.tts.shutdown()
        assert self.tts._session is None
        assert self.tts.status == VoiceComponentStatus.NOT_INITIALIZED

    @pytest.mark.asyncio
    async def test_test_connection_not_configured(self):
        bad_config = FishAudioConfig(api_key="", voice_id="")
        tts = FishAudioTTS(bad_config)
        result = await tts.test_connection()
        assert result["connected"] is False
        assert "Not configured" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_health_check_failure(self):
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = AsyncMock(side_effect=RuntimeError("network error"))
        self.tts._session = mock_session
        healthy = await self.tts._check_health()
        assert healthy is False


class TestFishAudioTTSErrorHandling:
    """Tests for Fish Audio error handling."""

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        config = FishAudioConfig(api_key="invalid-key", voice_id="test-voice")
        tts = FishAudioTTS(config)
        tts.status = VoiceComponentStatus.READY
        with patch.object(tts, "_synthesize", side_effect=PermissionError("Invalid API key")):
            audio = await tts.speak("test")
        assert audio is None
        assert tts._failure_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        config = FishAudioConfig(api_key="test-key", voice_id="test-voice")
        tts = FishAudioTTS(config)
        tts.status = VoiceComponentStatus.READY
        with patch.object(tts, "_synthesize", side_effect=RuntimeError("Rate limit exceeded")):
            audio = await tts.speak("test")
        assert audio is None
        assert tts._failure_count == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        config = FishAudioConfig(api_key="test-key", voice_id="test-voice")
        tts = FishAudioTTS(config)
        tts.status = VoiceComponentStatus.READY
        with patch.object(tts, "_synthesize", side_effect=TimeoutError("Request timed out")):
            audio = await tts.speak("test")
        assert audio is None
        assert tts._failure_count == 1


class TestTTSProvider:
    """Tests for TTSProvider enum."""

    def test_local_value(self):
        assert TTSProvider.LOCAL == "local"

    def test_fish_audio_value(self):
        assert TTSProvider.FISH_AUDIO == "fish_audio"

    def test_values(self):
        assert list(TTSProvider) == [TTSProvider.LOCAL, TTSProvider.FISH_AUDIO]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
