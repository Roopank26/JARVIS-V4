# JARVIS Voice Setup Script - Windows PowerShell
# Run as Administrator for full functionality

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS Voice Setup - Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -NoNewline
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version
    Write-Host " OK ($pythonVersion)" -ForegroundColor Green
} else {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Upgrade pip
Write-Host "Upgrading pip..." -NoNewline
python -m pip install --upgrade pip --quiet 2>$null
Write-Host " OK" -ForegroundColor Green

# Install voice dependencies
Write-Host ""
Write-Host "Installing voice dependencies..." -ForegroundColor Cyan

$voicePackages = @(
    "faster-whisper>=1.0.0",
    "openwakeword>=0.2.0",
    "sounddevice>=0.4.6",
    "numpy>=1.24.0",
    "onnxruntime>=1.16.0"
)

foreach ($package in $voicePackages) {
    Write-Host "  Installing $package..." -NoNewline
    pip install $package --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAILED" -ForegroundColor Yellow
    }
}

# Install PyAudio (Windows binary)
Write-Host "  Installing PyAudio..." -NoNewline
pip install PyAudio --quiet 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED (may need Visual C++ build tools)" -ForegroundColor Yellow
}

# Download Piper TTS (optional)
Write-Host ""
Write-Host "Piper TTS Setup (Optional)..." -ForegroundColor Cyan
Write-Host "  Download from: https://github.com/rhasspy/piper" -ForegroundColor Gray
Write-Host "  Install to: C:\tools\piper" -ForegroundColor Gray

# Create config directory
Write-Host ""
Write-Host "Creating configuration..." -NoNewline
$configDir = "$env:USERPROFILE\.jarvis"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}
Copy-Item "voice_config.json" -Destination "$configDir\voice_config.json" -Force -ErrorAction SilentlyContinue
Write-Host " OK" -ForegroundColor Green

# Test audio devices
Write-Host ""
Write-Host "Testing audio devices..." -ForegroundColor Cyan
python -c "import sounddevice; print(sounddevice.query_devices())" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  No audio devices found" -ForegroundColor Yellow
    Write-Host "  Check microphone permissions in Windows Settings" -ForegroundColor Gray
}

# Create models directory
Write-Host ""
Write-Host "Creating models directory..." -NoNewline
$modelsDir = "$configDir\models"
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}
Write-Host " OK" -ForegroundColor Green

# Download wake word model (optional)
Write-Host ""
Write-Host "Wake Word Model Download (Optional)..." -ForegroundColor Cyan
$wwModel = "$modelsDir\jarvis-onnx.onnx"
if (-not (Test-Path $wwModel)) {
    Write-Host "  Run: python -m openwakeword.tools.download_model --output $modelsDir" -ForegroundColor Gray
    Write-Host "  Or download from: https://github.com/collabora/OpenWakeWord" -ForegroundColor Gray
}

# Test voice runtime
Write-Host ""
Write-Host "Testing voice runtime..." -ForegroundColor Cyan
python -c "
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
"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Voice Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To start JARVIS with voice:" -ForegroundColor White
    Write-Host "  python -m jarvis.cli --voice" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To test voice status:" -ForegroundColor White
    Write-Host "  python -c 'from jarvis.voice.voice_runtime import *; print(get_voice_runtime().format_status())'" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Setup Complete with Warnings" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Some components may need manual installation" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Download Ollama models: ollama pull qwen3:8b" -ForegroundColor Gray
Write-Host "  2. Download DeepSeek: ollama pull deepseek-r1:8b" -ForegroundColor Gray
Write-Host "  3. Test: python verify_local_ai.py" -ForegroundColor Gray
Write-Host "  4. Run: python -m jarvis.cli" -ForegroundColor Gray
