#!/bin/bash
# JARVIS Voice Setup Script - Linux/macOS

set -e

echo "========================================"
echo "JARVIS Voice Setup - Linux/macOS"
echo "========================================"
echo ""

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
    echo "OK ($(python3 --version))"
elif command -v python &> /dev/null; then
    PYTHON=python
    echo "OK ($(python --version))"
else
    echo "NOT FOUND"
    echo "Please install Python 3.8+ from python.org"
    exit 1
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
$PYTHON -m pip install --upgrade pip --quiet 2>/dev/null || true
echo "OK"

# Install system dependencies (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Installing system dependencies..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq portaudio19-dev libspeechd1-dev 2>/dev/null || true
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y portaudio-devel 2>/dev/null || true
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm portaudio 2>/dev/null || true
    fi
fi

# Install voice dependencies
echo ""
echo "Installing voice dependencies..."

$PYTHON -m pip install \
    "faster-whisper>=1.0.0" \
    "openwakeword>=0.2.0" \
    "sounddevice>=0.4.6" \
    "numpy>=1.24.0" \
    "onnxruntime>=1.16.0" \
    "pyaudio>=0.2.14" \
    2>/dev/null || true

echo "OK"

# Install Piper TTS (optional)
echo ""
echo "Piper TTS Setup (Optional)..."
echo "  Download from: https://github.com/rhasspy/piper"
echo "  Install to: ~/tools/piper"

# Create config directory
echo ""
echo "Creating configuration..."
CONFIG_DIR="$HOME/.jarvis"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/models"
cp voice_config.json "$CONFIG_DIR/" 2>/dev/null || true
echo "OK"

# Test audio devices
echo ""
echo "Testing audio devices..."
$PYTHON -c "import sounddevice; print(sounddevice.query_devices())" 2>/dev/null || echo "  No audio devices found"

# Download wake word model (optional)
echo ""
echo "Wake Word Model Download (Optional)..."
$PYTHON -m openwakeword.tools.download_model --output "$CONFIG_DIR/models" 2>/dev/null || \
    echo "  Run: python -m openwakeword.tools.download_model"

# Test voice runtime
echo ""
echo "Testing voice runtime..."
$PYTHON -c "
import asyncio
from jarvis.voice.voice_runtime import initialize_voice, VoiceConfig

async def test():
    config = VoiceConfig()
    runtime = await initialize_voice()
    status = runtime.get_status()
    print('  Wake Word:', status['wake_word']['status'])
    print('  STT:', status['stt']['status'])
    print('  TTS:', status['tts']['status'])
    return runtime

runtime = asyncio.run(test())
" 2>/dev/null || echo "  Some components may need manual installation"

echo ""
echo "========================================"
echo "Voice Setup Complete!"
echo "========================================"
echo ""
echo "To start JARVIS with voice:"
echo "  python -m jarvis.cli --voice"
echo ""
echo "To test voice status:"
echo '  python -c "from jarvis.voice.voice_runtime import *; print(get_voice_runtime().format_status())"'
echo ""
echo "Next Steps:"
echo "  1. Download Ollama models: ollama pull qwen3:8b"
echo "  2. Download DeepSeek: ollama pull deepseek-r1:8b"
echo "  3. Test: python verify_local_ai.py"
echo "  4. Run: python -m jarvis.cli"
