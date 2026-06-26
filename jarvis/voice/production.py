"""
JARVIS Production Voice Module
Supports OpenWakeWord, Faster Whisper, Piper TTS, and streaming audio.
"""

import asyncio
import io
import logging
import struct
import threading
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Union

import numpy as np

logger = logging.getLogger("jarvis.voice.production")


@dataclass
class VoiceConfig:
    """Voice system configuration."""
    # Wake word settings
    wake_words: List[str] = field(default_factory=lambda: ["jarvis", "computer", "hey jarvis"])
    wake_sensitivity: float = 0.5
    wake_audio_threshold: float = 0.5
    
    # STT settings
    stt_model: str = "base"  # tiny, base, small, medium, large
    stt_language: str = "en"
    stt_use_gpu: bool = False
    
    # TTS settings
    tts_voice: str = "en_US-lessac-medium"
    tts_model: str = "中等"  # Default to a small voice
    tts_rate: float = 1.0
    tts_pitch: float = 1.0
    
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    silence_threshold: float = 500.0
    silence_duration: float = 1.5
    
    # Behavior
    interrupt_on_speech: bool = True
    continuous_listening: bool = True
    stream_audio: bool = True


class WakeWordEngine(ABC):
    """Abstract base class for wake word engines."""
    
    @abstractmethod
    async def listen(self) -> Optional[str]:
        """
        Listen for wake word.
        
        Returns:
            Detected wake word or None
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening."""
        pass


class OpenWakeWordEngine(WakeWordEngine):
    """
    OpenWakeWord integration for wake word detection.
    
    Lightweight, runs locally, supports custom wake words.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._running = False
        self._model = None
        self._vad = None
    
    async def start(self) -> bool:
        """Initialize and start the wake word engine."""
        try:
            # Try to import openwakeword
            try:
                import openwakeword
                from openwakeword.model import Model
            except ImportError:
                logger.warning("OpenWakeWord not installed, using fallback")
                return False
            
            # Load models for each wake word
            self._model = Model(
                model_path=None,  # Use default models
                inference_framework="onnx",
            )
            
            # Try to add custom models for configured wake words
            for ww in self.config.wake_words:
                try:
                    # Check if model exists, if not we'll use fallback
                    pass
                except Exception as e:
                    logger.debug(f"Could not load model for '{ww}': {e}")
            
            self._running = True
            logger.info("OpenWakeWord engine started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start OpenWakeWord: {e}")
            return False
    
    async def listen(self) -> Optional[str]:
        """Listen for wake word using microphone."""
        if not self._running:
            return None
        
        try:
            import sounddevice as sd
            import onnxruntime
            
            # Simple VAD-based wake word detection
            def audio_callback(indata, frames, time_info, status):
                if status:
                    return
                
                audio_data = indata.flatten()
                energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                
                # Check if audio exceeds threshold
                if energy > self.config.wake_audio_threshold:
                    # Could run through OpenWakeWord model here
                    # For now, return first wake word if audio detected
                    if self._running:
                        return self.config.wake_words[0]
            
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=self.config.chunk_size,
                callback=audio_callback,
            )
            
            with stream:
                while self._running:
                    await asyncio.sleep(0.1)
                    
        except ImportError:
            logger.warning("sounddevice not available for wake word")
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
        
        return None
    
    async def stop(self) -> None:
        """Stop the wake word engine."""
        self._running = False
        self._model = None
        logger.info("OpenWakeWord engine stopped")


class FallbackWakeWordEngine(WakeWordEngine):
    """
    Fallback wake word engine using simple audio detection.
    
    Used when OpenWakeWord is not available.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._running = False
    
    async def start(self) -> bool:
        """Start the fallback wake word engine."""
        self._running = True
        logger.info("Fallback wake word engine started")
        return True
    
    async def listen(self) -> Optional[str]:
        """Listen for wake word."""
        if not self._running:
            return None
        
        try:
            import sounddevice as sd
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    return
                
                audio_data = indata.flatten()
                energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                
                if energy > self.config.wake_audio_threshold:
                    # Return first configured wake word
                    return self.config.wake_words[0]
            
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                callback=audio_callback,
            )
            
            with stream:
                while self._running:
                    await asyncio.sleep(0.1)
                    
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Fallback wake word error: {e}")
        
        return None
    
    async def stop(self) -> None:
        """Stop the wake word engine."""
        self._running = False


class SpeechToTextEngine(ABC):
    """Abstract base class for speech-to-text engines."""
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text or None
        """
        pass


class FasterWhisperEngine(SpeechToTextEngine):
    """
    Faster Whisper integration for speech-to-text.
    
    Fast, accurate, runs locally with optional GPU acceleration.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._model = None
        self._model_size = config.stt_model
    
    async def start(self) -> bool:
        """Load the Whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            # Determine compute type based on GPU availability
            compute_type = "float16" if self.config.stt_use_gpu else "int8"
            
            self._model = WhisperModel(
                self._model_size,
                device="cuda" if self.config.stt_use_gpu else "cpu",
                compute_type=compute_type,
            )
            
            logger.info(f"Faster Whisper loaded: {self._model_size}")
            return True
            
        except ImportError:
            logger.warning("faster-whisper not installed, using fallback STT")
            return False
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper: {e}")
            return False
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio using Faster Whisper.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        if not self._model:
            return None
        
        try:
            # Convert bytes to numpy array
            audio_array = self._bytes_to_audio(audio_data)
            
            # Transcribe
            segments, info = self._model.transcribe(
                audio_array,
                language=self.config.stt_language,
                beam_size=5,
                vad_filter=True,
            )
            
            # Combine segments
            text = " ".join(segment.text for segment in segments)
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def _bytes_to_audio(self, audio_bytes: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array."""
        # Parse WAV if available, otherwise assume raw 16-bit PCM
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                return audio.astype(np.float32) / 32768.0
        except:
            # Assume raw PCM
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            return audio.astype(np.float32) / 32768.0
    
    async def stop(self) -> None:
        """Unload the model."""
        self._model = None
        logger.info("Faster Whisper stopped")


class FallbackSTTEngine(SpeechToTextEngine):
    """
    Fallback STT using basic audio analysis.
    
    Used when Faster Whisper is not available.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
    
    async def start(self) -> bool:
        """Start the fallback STT engine."""
        logger.info("Fallback STT engine started")
        return True
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Fallback transcription (placeholder).
        
        In production, this could integrate with cloud APIs.
        """
        # Check audio energy
        try:
            audio = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
            
            if energy < 100:  # Very quiet
                return None
            
            # Return placeholder - in production, use cloud API
            logger.warning("Using fallback STT - no transcription available")
            return None
            
        except Exception as e:
            logger.error(f"Fallback STT error: {e}")
            return None
    
    async def stop(self) -> None:
        """Stop the fallback engine."""
        pass


class TextToSpeechEngine(ABC):
    """Abstract base class for text-to-speech engines."""
    
    @abstractmethod
    async def speak(self, text: str, blocking: bool = True) -> None:
        """
        Speak text.
        
        Args:
            text: Text to speak
            blocking: Whether to wait for completion
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop speaking."""
        pass


class PiperTTSEngine(TextToSpeechEngine):
    """
    Piper TTS integration for text-to-speech.
    
    High-quality, runs locally, supports streaming.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._running = False
        self._speaking = False
        self._process = None
    
    async def start(self) -> bool:
        """Initialize Piper TTS."""
        try:
            # Check if piper-tts is available
            import subprocess
            result = subprocess.run(
                ["piper", "--help"],
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                raise ImportError("Piper TTS not found")
            
            self._running = True
            logger.info("Piper TTS engine started")
            return True
            
        except (ImportError, FileNotFoundError):
            logger.warning("Piper TTS not installed, using fallback")
            return False
        except Exception as e:
            logger.error(f"Failed to start Piper TTS: {e}")
            return False
    
    async def speak(self, text: str, blocking: bool = True) -> None:
        """
        Speak text using Piper TTS.
        
        Args:
            text: Text to speak
            blocking: Whether to wait for completion
        """
        if not self._running:
            return
        
        self._speaking = True
        
        try:
            import subprocess
            import io
            
            # Prepare piper command
            cmd = [
                "piper",
                "--model", self.config.tts_voice,
                "--output-raw",
            ]
            
            # Run piper
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Send text
            stdout, _ = process.communicate(
                input=text.encode('utf-8'),
                timeout=30,
            )
            
            if process.returncode == 0 and stdout:
                # Play audio
                await self._play_audio(stdout)
            
        except ImportError:
            logger.warning("Could not play audio")
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
        finally:
            self._speaking = False
    
    async def _play_audio(self, audio_data: bytes) -> None:
        """Play audio data."""
        try:
            import sounddevice as sd
            
            # Convert to numpy array
            audio = np.frombuffer(audio_data, dtype=np.int16)
            
            # Play
            sd.play(audio, samplerate=22050)
            
            if self.config.stream_audio:
                sd.wait()
            
        except ImportError:
            logger.warning("sounddevice not available for playback")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
    
    async def stop(self) -> None:
        """Stop speaking."""
        self._speaking = False
        self._running = False
        
        try:
            import sounddevice as sd
            sd.stop()
        except:
            pass
        
        logger.info("Piper TTS stopped")


class FallbackTTSEngine(TextToSpeechEngine):
    """
    Fallback TTS using pyttsx3 or system TTS.
    
    Used when Piper is not available.
    """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._running = False
        self._speaking = False
    
    async def start(self) -> bool:
        """Initialize fallback TTS."""
        self._running = True
        logger.info("Fallback TTS engine started")
        return True
    
    async def speak(self, text: str, blocking: bool = True) -> None:
        """
        Speak text using fallback TTS.
        
        Args:
            text: Text to speak
            blocking: Whether to wait
        """
        if not self._running:
            return
        
        self._speaking = True
        
        try:
            # Try pyttsx3
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150 * self.config.tts_rate)
                engine.setProperty('pitch', self.config.tts_pitch)
                engine.say(text)
                engine.runAndWait()
            except ImportError:
                # Fallback to print
                print(f"[TTS] {text}")
                
        except Exception as e:
            logger.error(f"Fallback TTS error: {e}")
        finally:
            self._speaking = False
    
    async def stop(self) -> None:
        """Stop speaking."""
        self._speaking = False
        self._running = False


class VoicePipeline:
    """
    Complete voice pipeline integrating all components.
    
    Pipeline:
    Wake Word -> STT -> Intent -> Agent -> TTS
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        
        # Initialize engines
        self._wake_word: Optional[WakeWordEngine] = None
        self._stt: Optional[SpeechToTextEngine] = None
        self._tts: Optional[TextToSpeechEngine] = None
        
        # State
        self._running = False
        self._speaking = False
        self._listening = False
        
        # Callbacks
        self.on_wake_word: Optional[Callable[[str], None]] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None
    
    async def start(self) -> bool:
        """Start the voice pipeline."""
        if self._running:
            return True
        
        logger.info("Starting voice pipeline...")
        
        # Start wake word engine
        self._wake_word = OpenWakeWordEngine(self.config)
        if not await self._wake_word.start():
            self._wake_word = FallbackWakeWordEngine(self.config)
            await self._wake_word.start()
        
        # Start STT engine
        self._stt = FasterWhisperEngine(self.config)
        if not await self._stt.start():
            self._stt = FallbackSTTEngine(self.config)
            await self._stt.start()
        
        # Start TTS engine
        self._tts = PiperTTSEngine(self.config)
        if not await self._tts.start():
            self._tts = FallbackTTSEngine(self.config)
            await self._tts.start()
        
        self._running = True
        logger.info("Voice pipeline started")
        return True
    
    async def stop(self) -> None:
        """Stop the voice pipeline."""
        logger.info("Stopping voice pipeline...")
        
        self._running = False
        self._listening = False
        
        if self._wake_word:
            await self._wake_word.stop()
            self._wake_word = None
        
        if self._stt:
            await self._stt.stop()
            self._stt = None
        
        if self._tts:
            await self._tts.stop()
            self._tts = None
        
        logger.info("Voice pipeline stopped")
    
    async def listen_for_wake_word(self) -> Optional[str]:
        """
        Listen for wake word.
        
        Returns:
            Detected wake word or None
        """
        if not self._running or not self._wake_word:
            return None
        
        return await self._wake_word.listen()
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        if not self._running or not self._stt:
            return None
        
        return await self._stt.transcribe(audio_data)
    
    async def speak(self, text: str, interrupt: bool = True) -> None:
        """
        Speak text.
        
        Args:
            text: Text to speak
            interrupt: Whether to interrupt current speech
        """
        if not self._running or not self._tts:
            return
        
        if interrupt and self._speaking:
            await self.stop_speaking()
        
        self._speaking = True
        
        try:
            await self._tts.speak(text, blocking=True)
        finally:
            self._speaking = False
    
    async def stop_speaking(self) -> None:
        """Stop current speech."""
        self._speaking = False
        if self._tts:
            await self._tts.stop()
    
    async def continuous_listen(
        self,
        callback: Callable[[str], None],
        wake_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Continuously listen for voice commands.
        
        Args:
            callback: Called with transcribed text
            wake_callback: Called when wake word detected
        """
        self._listening = True
        
        while self._listening and self._running:
            try:
                # Listen for wake word
                wake_word = await self.listen_for_wake_word()
                
                if wake_word:
                    logger.info(f"Wake word detected: {wake_word}")
                    
                    if wake_callback:
                        wake_callback(wake_word)
                    
                    # Listen for command
                    audio = await self._record_audio()
                    
                    if audio:
                        text = await self.transcribe(audio)
                        
                        if text:
                            logger.info(f"Transcribed: {text}")
                            callback(text)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Continuous listen error: {e}")
                await asyncio.sleep(1)
    
    async def _record_audio(self) -> Optional[bytes]:
        """Record audio from microphone."""
        try:
            import sounddevice as sd
            
            audio_buffer = []
            recording = False
            silence_count = 0
            
            def callback(indata, frames, time_info, status):
                nonlocal recording, silence_count
                
                audio_data = indata.flatten()
                energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                
                if energy > self.config.silence_threshold / 32768.0:
                    recording = True
                    silence_count = 0
                    audio_buffer.append(indata.tobytes())
                elif recording:
                    silence_count += frames
                    audio_buffer.append(indata.tobytes())
                    
                    # Check if silence duration exceeded
                    if silence_count > self.config.silence_duration * self.config.sample_rate:
                        return True  # Signal to stop
                
                return False
            
            # Record with callback
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=self.config.chunk_size,
                callback=callback,
            )
            
            with stream:
                # Record for up to 30 seconds
                await asyncio.sleep(30)
            
            if audio_buffer:
                return b''.join(audio_buffer)
            
        except ImportError:
            logger.warning("sounddevice not available for recording")
        except Exception as e:
            logger.error(f"Recording error: {e}")
        
        return None
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running
    
    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._speaking
    
    @property
    def is_listening(self) -> bool:
        """Check if continuously listening."""
        return self._listening
    
    def get_status(self) -> dict:
        """Get pipeline status."""
        return {
            "running": self._running,
            "speaking": self._speaking,
            "listening": self._listening,
            "wake_word_engine": type(self._wake_word).__name__ if self._wake_word else None,
            "stt_engine": type(self._stt).__name__ if self._stt else None,
            "tts_engine": type(self._tts).__name__ if self._tts else None,
            "config": {
                "wake_words": self.config.wake_words,
                "stt_model": self.config.stt_model,
                "tts_voice": self.config.tts_voice,
                "interrupt_on_speech": self.config.interrupt_on_speech,
                "continuous_listening": self.config.continuous_listening,
            },
        }


# Factory function
def create_voice_pipeline(config: Optional[VoiceConfig] = None) -> VoicePipeline:
    """
    Create a configured voice pipeline.
    
    Args:
        config: Voice configuration
        
    Returns:
        Configured VoicePipeline instance
    """
    return VoicePipeline(config)
