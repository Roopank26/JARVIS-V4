# JARVIS Setup Guide

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- A microphone (for voice features)
- Gemini API key (for AI capabilities)

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd JARVIS
```

### 2. Create a Virtual Environment

Using a virtual environment is recommended to avoid conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### Optional Dependencies

For enhanced functionality:

```bash
# For screen capture
pip install mss Pillow

# For camera capture
pip install opencv-python

# For system automation
pip install pyautogui pyperclip

# For better CLI experience
pip install rich prompt_toolkit
```

### 4. Configure API Keys

#### Gemini API Key

1. Get an API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create the config directory:
```bash
mkdir -p ~/.jarvis
```
3. Create the API keys file:
```bash
# On Linux/macOS:
echo '{"gemini_api_key": "YOUR-API-KEY"}' > ~/.jarvis/api_keys.json

# On Windows (PowerShell):
echo '{"gemini_api_key": "YOUR-API-KEY"}' | Out-File -FilePath "$env:USERPROFILE\.jarvis\api_keys.json"
```

### 5. Verify Installation

Run JARVIS:

```bash
python -m jarvis
```

You should see the JARVIS banner and prompt. Type `help` for available commands.

## Platform-Specific Setup

### Linux

#### Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip portaudio19-dev

# Fedora
sudo dnf install python3-devel portaudio-devel

# Arch
sudo pacman -S python python-pip portaudio
```

#### Audio Permissions

If you encounter audio issues, ensure your user has audio access:
```bash
sudo usermod -a -G audio $USER
```

Log out and back in for changes to take effect.

### macOS

#### Install System Dependencies

```bash
# Using Homebrew
brew install python@3.11 portaudio
```

#### Audio Permissions

Grant microphone access in System Preferences > Security & Privacy > Privacy > Microphone.

### Windows

#### Install System Dependencies

- Install Python from [python.org](https://www.python.org/downloads/)
- Install Visual Studio Build Tools (for compiling packages)

#### Audio

Windows should automatically detect microphones. If not, check:
Settings > System > Sound > Input

## Configuration Files

### Main Configuration (`~/.jarvis/config.json`)

```json
{
    "model": "gemini-2.0-flash",
    "live_model": "models/gemini-2.0-flash",
    "voice_enabled": true,
    "language": "en",
    "audio_sample_rate": 16000,
    "audio_channels": 1,
    "max_retries": 3,
    "max_replans": 2
}
```

### API Keys (`~/.jarvis/api_keys.json`)

```json
{
    "gemini_api_key": "your-api-key"
}
```

### Memory Storage

Long-term memory is stored at:
- `~/.jarvis/memory/long_term.json`

## Troubleshooting

### Import Errors

If you encounter `ModuleNotFoundError`:

```bash
pip install -r requirements.txt
```

### Audio Issues

1. Check if your microphone is working:
```bash
# Linux
pactl list sources

# macOS
system_profiler SPAudioDataType

# Windows
Get-PnpDevice -Class AudioEndpoint
```

2. Test audio with Python:
```python
import sounddevice as sd
print(sd.query_devices())
```

### Permission Errors

On Linux, if you get permission errors accessing `/dev`:
```bash
sudo chmod +rw /dev/snd/*
```

### API Key Issues

If JARVIS can't connect to Gemini:

1. Verify your API key is correct in `~/.jarvis/api_keys.json`
2. Check if you have internet connectivity
3. Verify your API key has not expired or exceeded quotas

## First-Time Usage

1. Start JARVIS:
```bash
python -m jarvis
```

2. Try basic commands:
```
You: hello
You: what files are in the current directory?
You: help
You: tools
```

3. Try a task:
```
You: create a file called test.txt with hello world
```

4. Test memory:
```
You: my name is John
You: remember that I like coffee
You: what is my name?
```

## Uninstall

To remove JARVIS:

```bash
# Remove the installation
rm -rf JARVIS

# Optionally remove configuration
rm -rf ~/.jarvis

# Deactivate virtual environment (if used)
deactivate
```

## Getting Help

- Type `help` in the CLI
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Review the source code in `jarvis/`
