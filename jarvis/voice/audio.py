"""
Voice I/O for JARVIS - Speech-to-Text and Text-to-Speech.
Provides voice command input and voice response output.
"""

import asyncio
import contextlib
import io
import logging
import os
import tempfile
import threading
import wave
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration."""

    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    input_device: int | None = None
    output_device: int | None = None
    silence_threshold: float = 500.0
    silence_duration: float = 1.5
    # Provider settings
    use_whisper: bool = True  # Use Whisper if available
    whisper_model: str = "base"  # tiny, base, small, medium, large
    use_gtts: bool = True  # Use gTTS for TTS if available


def check_audio_availability() -> dict:
    """Check which audio components are available."""
    status = {
        "microphone": False,
        "sounddevice": False,
        "whisper": False,
        "gtts": False,
        "pyttsx3": False,
        "fish_audio": False,
        "can_listen": False,
        "can_speak": False,
    }

    # Check sounddevice
    try:
        import sounddevice as sd

        status["sounddevice"] = True
        # Check if microphone is available
        try:
            devices = sd.query_devices()
            if devices:
                status["microphone"] = True
        except Exception:
            pass
    except ImportError:
        logger.debug("sounddevice not installed")

    # Check Whisper
    try:
        import importlib.util

        if importlib.util.find_spec("whisper") is not None:
            status["whisper"] = True
            status["can_listen"] = status["sounddevice"]
        else:
            logger.debug("whisper not installed")
    except ImportError:
        logger.debug("whisper not installed")

    # Check gTTS
    try:
        import importlib.util

        if importlib.util.find_spec("gtts") is not None:
            status["gtts"] = True
            status["can_speak"] = True
        else:
            logger.debug("gTTS not installed")
    except ImportError:
        logger.debug("gTTS not installed")

    # Check pyttsx3 (offline TTS)
    try:
        import importlib.util

        if importlib.util.find_spec("pyttsx3") is not None:
            status["pyttsx3"] = True
            if not status["can_speak"]:
                status["can_speak"] = True
        else:
            logger.debug("pyttsx3 not installed")
    except ImportError:
        logger.debug("pyttsx3 not installed")

    # Check Fish Audio
    try:
        status["fish_audio"] = bool(
            os.environ.get("FISH_AUDIO_API_KEY") and os.environ.get("FISH_AUDIO_VOICE_ID")
        )
        if status["fish_audio"] and not status["can_speak"]:
            status["can_speak"] = True
    except Exception:
        pass

    return status


class SpeechToText:
    """
    Speech-to-text using WebRTC VAD for voice activity detection
    and Whisper for transcription.
    """

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()
        self._is_listening = False
        self._vad_enabled = True
        self._audio_buffer: list = []
        self._silence_frames = 0
        self._speech_frames = 0
        self._whisper_model = None
        self._availability = check_audio_availability()

        # Initialize Whisper if available
        if self._availability["whisper"]:
            self._init_whisper()

    def _init_whisper(self):
        """Initialize Whisper model."""
        try:
            import whisper

            logger.info(f"Loading Whisper model: {self.config.whisper_model}")
            self._whisper_model = whisper.load_model(self.config.whisper_model)
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.warning(f"Failed to load Whisper: {e}")
            self._whisper_model = None

    async def listen(self, timeout: float = 10.0) -> str | None:
        """
        Listen for speech and return transcribed text.
        Uses WebRTC VAD for voice activity detection.
        """
        try:
            import numpy as np
            import sounddevice as sd

            self._is_listening = True
            self._audio_buffer = []
            self._silence_frames = 0
            self._speech_frames = 0

            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"[STT] Status: {status}")

                audio_data = indata.flatten()
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

                # Voice activity detection
                if rms > (self.config.silence_threshold / 32768.0):
                    self._speech_frames += 1
                    self._silence_frames = 0
                    self._audio_buffer.append(audio_data.tobytes())
                else:
                    if self._speech_frames > 10:
                        self._silence_frames += 1
                        self._audio_buffer.append(audio_data.tobytes())
                        # Check if silence duration exceeded
                        if self._silence_frames > (
                            self.config.silence_duration
                            * self.config.sample_rate
                            / self.config.chunk_size
                        ):
                            self._is_listening = False
                    else:
                        self._audio_buffer = []
                        self._speech_frames = 0

            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=self.config.chunk_size,
                device=self.config.input_device,
                callback=audio_callback,
            )

            with stream:
                start_time = asyncio.get_event_loop().time()
                while self._is_listening:
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        break
                    await asyncio.sleep(0.05)

            if len(self._audio_buffer) > 10:
                audio_bytes = b"".join(self._audio_buffer)
                return await self._transcribe(audio_bytes)

        except ImportError:
            print("[STT] sounddevice not available")
            return None
        except Exception as e:
            print(f"[STT] Listen error: {e}")
        finally:
            self._is_listening = False

        return None

    async def _transcribe(self, audio_data: bytes) -> str | None:
        """Transcribe audio using Whisper or Google Speech Recognition."""
        # Try Whisper first (offline, local)
        if self._whisper_model:
            try:
                import numpy as np

                # Convert bytes to numpy array
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Transcribe with Whisper
                result = self._whisper_model.transcribe(audio_np, fp16=False)
                text = result["text"].strip()

                if text:
                    logger.info(f"Whisper transcription: {text[:50]}...")
                    return text

            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")

        # Fallback to Google Speech Recognition
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            # Convert raw audio to AudioData
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(self._create_wav(audio_data))
                wav_path = f.name

            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)

            # Try Google Speech Recognition
            try:
                text = recognizer.recognize_google(audio)
                logger.info(f"Google STT transcription: {text[:50]}...")
                return text
            except sr.UnknownValueError:
                logger.warning("[STT] Could not understand audio")
            except sr.RequestError as e:
                logger.warning(f"[STT] Google API error: {e}")
                # Fallback to offline recognizer
                try:
                    text = recognizer.recognize_sphinx(audio)
                    return text
                except sr.UnknownValueError:
                    pass

            Path(wav_path).unlink(missing_ok=True)

        except ImportError:
            logger.warning("[STT] speech_recognition not available")
        except Exception as e:
            logger.warning(f"[STT] Transcribe error: {e}")

        return None

    def _create_wav(self, audio_data: bytes) -> bytes:
        """Create WAV file from raw audio data."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(audio_data)
        return buffer.getvalue()

    async def transcribe_file(self, audio_path: str) -> str | None:
        """Transcribe an audio file."""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)

            text = recognizer.recognize_google(audio)
            return text

        except ImportError:
            print("[STT] speech_recognition not available")
        except Exception as e:
            print(f"[STT] File transcribe error: {e}")

        return None

    def stop(self):
        """Stop listening."""
        self._is_listening = False


class TextToSpeech:
    """
    Text-to-speech using gTTS or pyttsx3.
    Supports multiple TTS engines.
    """

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()
        self._is_playing = False
        self._engine = "gtts"  # Default to Google TTS
        self._voice = None
        self._rate = 150  # Words per minute
        self._volume = 1.0

    @property
    def engine(self) -> str:
        return self._engine

    @engine.setter
    def engine(self, value: str):
        """Set TTS engine: 'gtts', 'pyttsx3', 'edge', or 'fish_audio'"""
        if value in ["gtts", "pyttsx3", "edge", "fish_audio"]:
            self._engine = value
        else:
            print(f"[TTS] Unknown engine '{value}', using 'gtts'")
            self._engine = "gtts"

    async def speak(self, text: str, blocking: bool = True) -> bytes | None:
        """
        Convert text to speech and play it.
        Returns audio bytes if blocking=False.
        """
        if not text:
            return None

        try:
            if self._engine == "fish_audio":
                return await self._speak_fish_audio(text)
            if self._engine == "gtts":
                return await self._speak_gtts(text)
            elif self._engine == "pyttsx3":
                return await self._speak_pyttsx3(text)
            elif self._engine == "edge":
                return await self._speak_edge(text)

        except Exception as e:
            print(f"[TTS] Speak error: {e}")

        return None

    async def _speak_fish_audio(self, text: str) -> bytes | None:
        """Fish Audio TTS implementation."""
        try:
            from jarvis.voice.fish_audio_tts import FishAudioConfig, FishAudioTTS

            config = FishAudioConfig.from_env()
            if not config.is_configured():
                print("[TTS] Fish Audio not configured (missing API key or voice ID)")
                return None

            tts = FishAudioTTS(config)
            result = await tts.initialize()
            if not result.success:
                print(f"[TTS] Fish Audio initialization failed: {result.error}")
                return None

            audio = await tts.speak(text)
            if audio:
                await self._play_wav(audio)
            return audio

        except ImportError:
            print("[TTS] Fish Audio provider not available")
        except Exception as e:
            print(f"[TTS] Fish Audio error: {e}")

        return None

    async def _speak_gtts(self, text: str) -> bytes | None:
        """Google TTS implementation."""
        try:
            from gtts import gTTS

            mp3_buffer = io.BytesIO()
            tts = gTTS(text=text, lang="en", slow=False)
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)

            # Convert MP3 to WAV for playback
            from pydub import AudioSegment

            audio = AudioSegment.from_mp3(mp3_buffer)
            audio = audio.set_frame_rate(self.config.sample_rate)
            audio = audio.set_channels(self.config.channels)

            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            await self._play_wav(wav_buffer.read())
            return wav_buffer.getvalue()

        except ImportError:
            print("[TTS] gTTS or pydub not available")
            # Fallback to direct MP3 playback
            await self._speak_simple(text)
        except Exception as e:
            print(f"[TTS] gTTS error: {e}")

        return None

    async def _speak_pyttsx3(self, text: str) -> bytes | None:
        """pyttsx3 offline TTS implementation."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)

            # Save to buffer
            engine.save_to_file(text, "temp_audio.wav")
            engine.runAndWait()

            with open("temp_audio.wav", "rb") as f:
                audio_data = f.read()

            Path("temp_audio.wav").unlink(missing_ok=True)

            await self._play_wav(audio_data)
            return audio_data

        except ImportError:
            print("[TTS] pyttsx3 not available")
        except Exception as e:
            print(f"[TTS] pyttsx3 error: {e}")

        return None

    async def _speak_edge(self, text: str) -> bytes | None:
        """Microsoft Edge TTS implementation."""
        try:
            from edge_tts import Communicate

            mp3_buffer = io.BytesIO()
            communicate = Communicate(text, voice="en-US-JennyNeural")
            await communicate.stream_to_file(mp3_buffer)
            mp3_buffer.seek(0)

            # Convert to WAV
            from pydub import AudioSegment

            audio = AudioSegment.from_mp3(mp3_buffer)
            audio = audio.set_frame_rate(self.config.sample_rate)

            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            await self._play_wav(wav_buffer.read())
            return wav_buffer.getvalue()

        except ImportError:
            print("[TTS] edge-tts not available")
        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}")

        return None

    async def _speak_simple(self, text: str):
        """Simple TTS using OS default (no audio output in container)."""
        try:
            from gtts import gTTS

            tts = gTTS(text=text, lang="en")
            tts.save("/tmp/tts_output.mp3")
            print(f"[TTS] Saved to /tmp/tts_output.mp3: {text[:50]}...")
        except Exception:
            print(f"[TTS] {text}")

    async def _play_wav(self, audio_data: bytes):
        """Play WAV audio data."""
        try:
            import numpy as np
            import sounddevice as sd

            buffer = io.BytesIO(audio_data)
            with wave.open(buffer, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                audio_array = np.frombuffer(frames, dtype=np.int16)

            sd.play(audio_array, self.config.sample_rate)
            sd.wait()

        except ImportError:
            print("[TTS] sounddevice not available for playback")
        except Exception as e:
            print(f"[TTS] Play error: {e}")

    async def speak_async(self, text: str) -> asyncio.Task:
        """Speak text asynchronously (non-blocking)."""
        return asyncio.create_task(self.speak(text, blocking=False))

    def set_voice(self, voice_id: str):
        """Set the voice ID for pyttsx3."""
        self._voice = voice_id

    def set_rate(self, rate: int):
        """Set speech rate (words per minute)."""
        self._rate = max(50, min(300, rate))

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))


class VoiceAssistant:
    """
    Combined voice input/output for JARVIS.
    Handles wake word detection, speech recognition, and response synthesis.
    """

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()
        self.stt = SpeechToText(config)
        self.tts = TextToSpeech(config)
        self._is_active = False
        self._wake_word = "jarvis"
        self._callback: Callable[[str], Awaitable[str]] | None = None

    async def start(self, callback: Callable[[str], Awaitable[str]]):
        """
        Start the voice assistant.
        Continuously listens for commands and responds.
        """
        self._callback = callback
        self._is_active = True

        print(f"[Voice] Assistant started (wake word: '{self._wake_word}')")

        while self._is_active:
            try:
                # Listen for speech
                text = await self.stt.listen(timeout=10.0)

                if text:
                    print(f"[Voice] Heard: {text}")

                    # Check for wake word
                    if self._wake_word.lower() in text.lower():
                        # Remove wake word from command
                        command = text.lower().replace(self._wake_word.lower(), "").strip()
                        if command and self._callback:
                            # Process command
                            response = await self._callback(command)
                            await self.tts.speak(response)

            except Exception as e:
                print(f"[Voice] Error: {e}")
                await asyncio.sleep(1)

        print("[Voice] Assistant stopped")

    def stop(self):
        """Stop the voice assistant."""
        self._is_active = False
        self.stt.stop()

    def set_wake_word(self, wake_word: str):
        """Set the wake word."""
        self._wake_word = wake_word

    async def process_command(self, text: str) -> str:
        """Process a text command (non-voice input)."""
        if self._callback:
            return await self._callback(text)
        return "Voice callback not configured"


class AudioManager:
    """
    Manages audio input and output for JARVIS.
    Uses sounddevice for cross-platform audio.
    """

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()
        self._input_stream = None
        self._output_stream = None
        self._is_recording = False
        self._is_playing = False
        self._input_queue: asyncio.Queue = asyncio.Queue()
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._audio_lock = threading.Lock()
        self.stt = SpeechToText(config)
        self.tts = TextToSpeech(config)

    async def start_input(self):
        """Start the audio input stream."""
        try:
            import sounddevice as sd

            def input_callback(indata, frames, time_info, status):
                if status:
                    print(f"[Audio] Input status: {status}")
                with self._audio_lock:
                    if self._is_recording:
                        self._input_queue.put_nowait(indata.tobytes())

            self._input_stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=self.config.chunk_size,
                device=self.config.input_device,
                callback=input_callback,
            )

            with self._audio_lock:
                self._is_recording = True

            self._input_stream.start()
            print(f"[Audio] Input started: {self.config.sample_rate}Hz, {self.config.channels}ch")

        except ImportError:
            print("[Audio] sounddevice not available, voice input disabled")
        except Exception as e:
            print(f"[Audio] Input error: {e}")

    async def stop_input(self):
        """Stop the audio input stream."""
        with self._audio_lock:
            self._is_recording = False

        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception as e:
                print(f"[Audio] Input stop error: {e}")
            self._input_stream = None

    async def start_output(self):
        """Start the audio output stream."""
        try:
            import sounddevice as sd

            self._output_stream = sd.RawOutputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=self.config.chunk_size,
                device=self.config.output_device,
            )

            with self._audio_lock:
                self._is_playing = True

            self._output_stream.start()
            print(f"[Audio] Output started: {self.config.sample_rate}Hz, {self.config.channels}ch")

        except ImportError:
            print("[Audio] sounddevice not available, voice output disabled")
        except Exception as e:
            print(f"[Audio] Output error: {e}")

    async def stop_output(self):
        """Stop the audio output stream."""
        with self._audio_lock:
            self._is_playing = False

        if self._output_stream:
            try:
                self._output_stream.stop()
                self._output_stream.close()
            except Exception as e:
                print(f"[Audio] Output stop error: {e}")
            self._output_stream = None

    async def get_input_audio(self) -> bytes | None:
        """Get audio data from the input queue."""
        try:
            return await asyncio.wait_for(self._input_queue.get(), timeout=0.1)
        except TimeoutError:
            return None

    async def play_audio(self, audio_data: bytes):
        """Play audio data."""
        if self._output_stream:
            try:
                await asyncio.to_thread(self._output_stream.write, audio_data)
            except Exception as e:
                print(f"[Audio] Play error: {e}")

    def get_available_devices(self) -> dict:
        """Get available audio devices."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            return {
                "inputs": [d for d in devices if d["max_input_channels"] > 0],
                "outputs": [d for d in devices if d["max_output_channels"] > 0],
            }
        except ImportError:
            return {"inputs": [], "outputs": []}
        except Exception as e:
            print(f"[Audio] Device query error: {e}")
            return {"inputs": [], "outputs": []}

    @property
    def is_recording(self) -> bool:
        with self._audio_lock:
            return self._is_recording

    @property
    def is_playing(self) -> bool:
        with self._audio_lock:
            return self._is_playing


class AudioLoopback:
    """
    Simple audio loopback for testing.
    Reads from input and writes to output.
    """

    def __init__(self, audio_manager: AudioManager):
        self.audio = audio_manager
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start the loopback."""
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Stop the loopback."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self):
        """Main loopback loop."""
        while self._running:
            audio = await self.audio.get_input_audio()
            if audio:
                await self.audio.play_audio(audio)
            else:
                await asyncio.sleep(0.01)
