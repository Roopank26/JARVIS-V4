"""
Real Voice Runtime for JARVIS.
Implements complete voice pipeline with faster-whisper, Piper TTS, and OpenWakeWord.
"""

import asyncio
import logging
import os
import json
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceComponentStatus(Enum):
    """Status of voice components."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ComponentInitResult:
    """Result of component initialization."""
    success: bool
    status: VoiceComponentStatus
    message: str = ""
    error: Optional[str] = None
    
    @classmethod
    def ok(cls, status: VoiceComponentStatus = VoiceComponentStatus.READY, message: str = "") -> "ComponentInitResult":
        return cls(success=True, status=status, message=message)
    
    @classmethod
    def fail(cls, error: str, status: VoiceComponentStatus = VoiceComponentStatus.ERROR) -> "ComponentInitResult":
        return cls(success=False, status=status, message="", error=error)


@dataclass
class VoiceInitResult:
    """Result of voice runtime initialization."""
    wake_word: ComponentInitResult
    stt: ComponentInitResult
    tts: ComponentInitResult
    ready: bool = False
    
    @classmethod
    def from_components(cls, wake_word, stt, tts) -> "VoiceInitResult":
        """Create from component instances."""
        results = cls(
            wake_word=ComponentInitResult.ok() if (wake_word and wake_word.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
            stt=ComponentInitResult.ok() if (stt and stt.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
            tts=ComponentInitResult.ok() if (tts and tts.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
        )
        results.ready = all([results.wake_word.success, results.stt.success, results.tts.success])
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "wake_word": {"status": self.wake_word.status.value, "success": self.wake_word.success, "error": self.wake_word.error},
            "stt": {"status": self.stt.status.value, "success": self.stt.success, "error": self.stt.error},
            "tts": {"status": self.tts.status.value, "success": self.tts.success, "error": self.tts.error},
            "ready": self.ready
        }


@dataclass
class VoiceConfig:
    """Voice configuration."""
    # STT settings
    stt_model: str = "base"  # tiny, base, small, medium, large
    stt_language: str = "en"
    stt_device: str = "auto"  # auto, cpu, cuda
    
    # TTS settings
    tts_model: str = "en_US-lessac-medium"
    tts_voice: str = "en_US-lessac-medium.onnx"
    tts_speaker: int = 0
    
    # Wake word settings
    wake_word: str = "jarvis"
    wake_word_threshold: float = 0.5
    wake_word_model: str = "jarvis-onnx"  # or 'tiny' for faster-wer
    
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    
    # Runtime settings
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    phrase_threshold: float = 0.3
    non_speech_threshold: float = 0.2
    
    @classmethod
    def from_file(cls, path: str) -> "VoiceConfig":
        """Load config from JSON file."""
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class VoiceComponent:
    """Base class for voice components."""
    
    def __init__(self, name: str):
        self.name = name
        self.status = VoiceComponentStatus.NOT_INITIALIZED
        self.error_message: Optional[str] = None
        self._instance = None
    
    async def initialize(self) -> ComponentInitResult:
        """Initialize the component. Subclasses must implement this."""
        self.status = VoiceComponentStatus.INITIALIZING
        raise NotImplementedError("Subclasses must implement initialize()")
    
    async def shutdown(self) -> None:
        """Shutdown the component."""
        self._instance = None
        self.status = VoiceComponentStatus.NOT_INITIALIZED


class FasterWhisperSTT(VoiceComponent):
    """Speech-to-Text using faster-whisper."""
    
    def __init__(self, config: VoiceConfig):
        super().__init__("STT")
        self.config = config
        self._instance = None
        self._model = None
    
    async def initialize(self) -> ComponentInitResult:
        """Initialize faster-whisper model."""
        self.status = VoiceComponentStatus.INITIALIZING
        
        try:
            from faster_whisper import WhisperModel
            
            # Determine compute type
            compute_type = "int8"  # Good balance of speed and accuracy
            if self.config.stt_device == "cuda":
                try:
                    import torch
                    if torch.cuda.is_available():
                        compute_type = "float16"
                except ImportError:
                    pass
            
            logger.info(f"Loading faster-whisper {self.config.stt_model}...")
            self._model = WhisperModel(
                self.config.stt_model,
                device=self.config.stt_device,
                compute_type=compute_type
            )
            self.status = VoiceComponentStatus.READY
            logger.info("STT initialized successfully")
            return ComponentInitResult.ok(
                status=VoiceComponentStatus.READY,
                message=f"Model '{self.config.stt_model}' loaded"
            )
            
        except ImportError as e:
            self.status = VoiceComponentStatus.DISABLED
            self.error_message = f"faster-whisper not installed: {e}"
            logger.warning(f"STT disabled: {e}")
            return ComponentInitResult.fail(
                str(e),
                status=VoiceComponentStatus.DISABLED
            )
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.error(f"STT initialization failed: {e}")
            return ComponentInitResult.fail(str(e))
    
    async def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file."""
        if self.status != VoiceComponentStatus.READY or not self._model:
            return None
        
        try:
            segments, _ = self._model.transcribe(
                audio_path,
                language=self.config.stt_language,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            text = " ".join([seg.text for seg in segments])
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def transcribe_bytes(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio from bytes."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(audio_data)
            f.flush()
            text = await self.transcribe(f.name)
            Path(f.name).unlink(missing_ok=True)
            return text


class PiperTTS(VoiceComponent):
    """Text-to-Speech using Piper."""
    
    def __init__(self, config: VoiceConfig):
        super().__init__("TTS")
        self.config = config
        self._session = None
    
    async def initialize(self) -> ComponentInitResult:
        """Initialize Piper TTS."""
        self.status = VoiceComponentStatus.INITIALIZING
        
        try:
            import piper_pb2
            import grpc
            
            # Piper server address (default)
            server = os.environ.get("PIPPER_SERVER", "localhost:50000")
            
            self._channel = grpc.aio.insecure_channel(server)
            self._session = piper_pb2_grpc.PiperSessionStub(self._channel)
            
            # Test connection
            await asyncio.wait_for(
                self._session.IsReady(piper_pb2.Void()),
                timeout=5.0
            )
            
            self.status = VoiceComponentStatus.READY
            logger.info("TTS initialized successfully")
            return ComponentInitResult.ok(
                status=VoiceComponentStatus.READY,
                message="Connected to Piper TTS server"
            )
            
        except ImportError:
            # Fallback to command-line piper
            self._command_mode = True
            self.status = VoiceComponentStatus.READY
            logger.info("TTS initialized (command mode)")
            return ComponentInitResult.ok(
                status=VoiceComponentStatus.READY,
                message="Using command-line Piper"
            )
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.warning(f"TTS initialization failed: {e}")
            return ComponentInitResult.fail(str(e))
    
    async def speak(self, text: str) -> Optional[bytes]:
        """Convert text to speech and return audio bytes."""
        if self.status != VoiceComponentStatus.READY:
            return None
        
        try:
            if hasattr(self, '_command_mode') and self._command_mode:
                return await self._speak_command(text)
            
            import piper_pb2
            request = piper_pb2.SynthesisRequest(
                text=text,
                speaker_id=self.config.tts_speaker
            )
            
            audio_chunks = []
            async for resp in self._session.Synthesize(request):
                if resp.audio.HasField('audio'):
                    audio_chunks.append(resp.audio.audio)
            
            return b''.join(audio_chunks) if audio_chunks else None
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    async def _speak_command(self, text: str) -> Optional[bytes]:
        """Fallback to command-line Piper."""
        try:
            import subprocess
            
            result = subprocess.run(
                ["piper", "--model", self.config.tts_model, "--output-raw"],
                input=text.encode(),
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None
    
    async def speak_to_file(self, text: str, output_path: str) -> bool:
        """Convert text to speech and save to file."""
        audio = await self.speak(text)
        if audio:
            with open(output_path, 'wb') as f:
                f.write(audio)
            return True
        return False
    
    async def shutdown(self) -> None:
        """Shutdown TTS."""
        if hasattr(self, '_channel'):
            await self._channel.close()
        await super().shutdown()


class OpenWakeWord(VoiceComponent):
    """Wake word detection using OpenWakeWord."""
    
    def __init__(self, config: VoiceConfig):
        super().__init__("Wake Word")
        self.config = config
        self._predictor = None
        self._running = False
    
    async def initialize(self) -> ComponentInitResult:
        """Initialize OpenWakeWord model."""
        self.status = VoiceComponentStatus.INITIALIZING
        
        try:
            import numpy as np
            try:
                from openwakeword import WakeWordClassifier
                self._framework = "openwakeword"
                logger.info("Using OpenWakeWord framework")
            except ImportError:
                # Fallback to simpler VAD-based wake word
                self._framework = "vad"
                logger.info("Using VAD-based wake word detection")
                self.status = VoiceComponentStatus.READY
                return ComponentInitResult.ok(
                    status=VoiceComponentStatus.READY,
                    message="Using VAD-based wake word detection"
                )
            
            # Initialize model
            self._predictor = WakeWordClassifier(
                verbose=False,
                inference_framework="onnx"
            )
            
            # Add custom wake word model if exists
            model_path = Path("models") / f"{self.config.wake_word_model}.onnx"
            if model_path.exists():
                self._predictor.add_model(str(model_path))
            else:
                # Use built-in model
                self._predictor.add_model("jarvis")
            
            self.status = VoiceComponentStatus.READY
            logger.info("Wake word detection initialized")
            return ComponentInitResult.ok(
                status=VoiceComponentStatus.READY,
                message=f"Wake word '{self.config.wake_word}' ready"
            )
            
        except ImportError:
            self.status = VoiceComponentStatus.DISABLED
            self.error_message = "openwakeword not installed"
            logger.warning("Wake word disabled (use 'pip install openwakeword')")
            return ComponentInitResult.fail(
                "openwakeword not installed",
                status=VoiceComponentStatus.DISABLED
            )
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.error(f"Wake word initialization failed: {e}")
            return ComponentInitResult.fail(str(e))
    
    async def detect(self, audio_chunk: bytes) -> bool:
        """Detect wake word in audio chunk."""
        if self.status != VoiceComponentStatus.READY:
            return False
        
        if self._framework == "vad":
            return await self._detect_vad(audio_chunk)
        
        try:
            import numpy as np
            audio = np.frombuffer(audio_chunk, dtype=np.int16)
            
            predictions = self._predictor.predict(audio)
            for model_name, score in predictions.items():
                if score > self.config.wake_word_threshold:
                    logger.info(f"Wake word detected: {model_name} ({score:.2f})")
                    return True
            return False
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            return False
    
    async def _detect_vad(self, audio_chunk: bytes) -> bool:
        """Fallback VAD-based detection."""
        import numpy as np
        
        audio = np.frombuffer(audio_chunk, dtype=np.int16)
        energy = np.sqrt(np.mean(audio.astype(float) ** 2))
        
        # Simple energy-based detection
        return energy > 1000  # Adjust threshold as needed
    
    async def shutdown(self) -> None:
        """Shutdown wake word detection."""
        self._running = False
        await super().shutdown()


class VoiceRuntime:
    """
    Complete voice runtime for JARVIS.
    
    Pipeline:
    Wake Word → STT → Intent → Agent → TTS
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        
        # Components
        self.wake_word: Optional[OpenWakeWord] = None
        self.stt: Optional[FasterWhisperSTT] = None
        self.tts: Optional[PiperTTS] = None
        
        # Runtime state
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.on_wake_word: Optional[Callable] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
    
    async def initialize(self) -> VoiceInitResult:
        """Initialize all voice components."""
        # Initialize wake word
        self.wake_word = OpenWakeWord(self.config)
        wake_result = await self.wake_word.initialize()
        
        # Initialize STT
        self.stt = FasterWhisperSTT(self.config)
        stt_result = await self.stt.initialize()
        
        # Initialize TTS
        self.tts = PiperTTS(self.config)
        tts_result = await self.tts.initialize()
        
        # Build VoiceInitResult from individual results
        result = VoiceInitResult(
            wake_word=wake_result,
            stt=stt_result,
            tts=tts_result,
            ready=wake_result.success and stt_result.success and tts_result.success
        )
        
        return result
    
    async def shutdown(self) -> None:
        """Shutdown all voice components."""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.wake_word:
            await self.wake_word.shutdown()
        if self.stt:
            await self.stt.shutdown()
        if self.tts:
            await self.tts.shutdown()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all components."""
        return {
            "wake_word": {
                "status": self.wake_word.status.value if self.wake_word else "not_initialized",
                "error": self.wake_word.error_message if self.wake_word else None
            },
            "stt": {
                "status": self.stt.status.value if self.stt else "not_initialized",
                "model": self.config.stt_model,
                "error": self.stt.error_message if self.stt else None
            },
            "tts": {
                "status": self.tts.status.value if self.tts else "not_initialized",
                "model": self.config.tts_model,
                "error": self.tts.error_message if self.tts else None
            },
            "ready": all([
                self.wake_word.status == VoiceComponentStatus.READY if self.wake_word else True,
                self.stt.status == VoiceComponentStatus.READY if self.stt else True,
                self.tts.status == VoiceComponentStatus.READY if self.tts else True,
            ])
        }
    
    def format_status(self) -> str:
        """Format status for display."""
        status = self.get_status()
        lines = ["[Voice Status]", "=" * 40]
        
        for component in ["wake_word", "stt", "tts"]:
            info = status[component]
            name = component.replace("_", " ").title()
            icon = "✓" if "ready" in info["status"] else "✗" if "error" in info["status"] else "○"
            lines.append(f"{icon} {name}: {info['status']}")
            if info.get("model"):
                lines.append(f"   Model: {info['model']}")
        
        return "\n".join(lines)
    
    async def listen_once(self, timeout: float = 10.0) -> Optional[str]:
        """Listen for one voice command and return transcription."""
        if not self.stt or self.stt.status != VoiceComponentStatus.READY:
            return None
        
        try:
            import sounddevice as sd
            import numpy as np
            
            logger.info("Listening...")
            
            audio_data = []
            speaking = False
            silence_frames = 0
            
            def callback(indata, frames, time_info, status):
                nonlocal speaking, silence_frames
                
                if status:
                    logger.warning(f"Audio status: {status}")
                
                audio = indata.flatten()
                audio_data.append(audio.tobytes())
                
                # Simple VAD
                energy = np.sqrt(np.mean(audio.astype(float) ** 2))
                if energy > 500:
                    speaking = True
                    silence_frames = 0
                elif speaking:
                    silence_frames += 1
                    if silence_frames > 30:  # ~1 second of silence
                        raise StopIteration
            
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=1024,
                callback=callback
            )
            
            with stream:
                await asyncio.wait_for(asyncio.sleep(timeout), timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.debug("Listen timeout")
            return None
        except StopIteration:
            pass
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return None
        
        if audio_data:
            audio_bytes = b''.join(audio_data)
            return await self.stt.transcribe_bytes(audio_bytes)
        
        return None
    
    async def speak(self, text: str) -> bool:
        """Speak text using TTS."""
        if not self.tts or self.tts.status != VoiceComponentStatus.READY:
            return False
        
        audio = await self.tts.speak(text)
        if audio:
            try:
                import sounddevice as sd
                import numpy as np
                
                # Play audio
                audio_array = np.frombuffer(audio, dtype=np.int16)
                sd.play(audio_array, samplerate=22050)
                sd.wait()
                return True
            except Exception as e:
                logger.error(f"TTS playback error: {e}")
        
        return False


# Global runtime instance
_voice_runtime: Optional[VoiceRuntime] = None


def get_voice_runtime(config: Optional[VoiceConfig] = None) -> VoiceRuntime:
    """Get or create global voice runtime."""
    global _voice_runtime
    if _voice_runtime is None:
        _voice_runtime = VoiceRuntime(config)
    return _voice_runtime


async def initialize_voice(config_path: Optional[str] = None) -> VoiceRuntime:
    """Initialize voice runtime with config."""
    global _voice_runtime
    
    config = VoiceConfig()
    if config_path and Path(config_path).exists():
        config = VoiceConfig.from_file(config_path)
    
    _voice_runtime = VoiceRuntime(config)
    await _voice_runtime.initialize()
    
    return _voice_runtime
