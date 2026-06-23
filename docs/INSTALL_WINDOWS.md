# JARVIS Desktop - Windows 11 Installation Guide

## Prerequisites

### System Requirements
- **OS**: Windows 11 (build 22000 or later)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB available space
- **Audio**: Built-in or USB microphone, speakers
- **Network**: Internet connection (for AI features)

### Required Software
1. **Python 3.10 or later** - [Download from python.org](https://www.python.org/downloads/)
2. **Git** - [Download from git-scm.com](https://git-scm.com/download/win)
3. **Visual Studio Build Tools** - For PyAudio dependency

## Installation Steps

### 1. Install Python

1. Download Python 3.11+ from [python.org](https://www.python.org/downloads/windows/)
2. Run the installer
3. **Important**: Check "Add Python to PATH"
4. Click "Install Now"

Verify installation:
```powershell
python --version
pip --version
```

### 2. Install System Dependencies

#### Visual Studio Build Tools
1. Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio)
2. Install with "Desktop development with C++" workload

#### PyAudio (requires compilation)
```powershell
pip install pipwin
pipwin install pyaudio
```

### 3. Clone or Download JARVIS

```powershell
# Clone from GitHub
git clone https://github.com/your-repo/JARVIS.git
cd JARVIS

# Or download and extract ZIP
```

### 4. Install Python Dependencies

```powershell
# Install all dependencies
pip install -r requirements.txt

# Or use the installer script
.\install.bat
```

### 5. Configure Audio (Optional)

Run audio setup to select microphone and speakers:
```powershell
python -m jarvis.desktop audio-setup
```

### 6. Test Installation

```powershell
# Run diagnostic
python -m jarvis.desktop test

# Start in console mode
python -m jarvis.desktop console
```

## Installation Methods

### Method 1: User Installation (Recommended)

Installs for current user only, no admin required:

```powershell
python -m jarvis.desktop install
```

This will:
- Create Start Menu shortcut
- Add to Windows startup (optional)
- Create desktop shortcut (optional)

### Method 2: System-Wide Installation

Requires administrator privileges:

```powershell
# Run PowerShell as Administrator
python -m jarvis.desktop install --system
```

### Method 3: Portable Installation

Run directly without installation:

```powershell
# Just run
python -m jarvis.desktop run

# Or with portable mode
python -m jarvis.desktop run --portable
```

## Configuration

### First-Time Setup

On first run, JARVIS will:
1. Create configuration in `%APPDATA%\JARVIS\`
2. Prompt for wake word selection
3. Test microphone access
4. Configure optional integrations

### Configuration File

Location: `%APPDATA%\JARVIS\config.json`

```json
{
  "wake_word": "jarvis",
  "wake_sensitivity": 0.7,
  "voice": {
    "stt_engine": "google",
    "tts_engine": "edge"
  },
  "auto_start": false,
  "minimize_to_tray": true,
  "data_dir": "%APPDATA%\\JARVIS"
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JARVIS_DATA` | Data directory | `%APPDATA%\JARVIS` |
| `JARVIS_CONFIG` | Config file path | `%APPDATA%\JARVIS\config.json` |
| `JARVIS_LOG` | Log file path | `%APPDATA%\JARVIS\jarvis.log` |
| `GOOGLE_API_KEY` | Google Cloud API key | None |
| `OPENAI_API_KEY` | OpenAI API key | None |

## Windows-Specific Features

### System Tray
JARVIS minimizes to the Windows system tray:
- Left-click: Show/hide window
- Right-click: Context menu
- Double-click: Open main window

### Startup with Windows

Enable auto-start:
```powershell
python -m jarvis.desktop set-startup --enable
```

Disable auto-start:
```powershell
python -m jarvis.desktop set-startup --disable
```

### Windows Notifications

JARVIS uses Windows Toast Notifications for:
- Daily summaries
- Reminders
- Task completions
- Error alerts

### Voice Commands

Use "Hey Jarvis" or "Jarvis" to activate:
```
"Hey Jarvis, what's the weather today?"
"Jarvis, open Visual Studio Code"
"Hey Jarvis, remind me to call mom at 5pm"
```

## Troubleshooting

### Microphone Not Detected

1. Check Privacy Settings:
   - Settings > Privacy > Microphone > Allow apps to access your microphone

2. Run audio diagnostic:
   ```powershell
   python -m jarvis.desktop diagnose audio
   ```

### Installation Fails with pywin32

```powershell
# Install pywin32 manually
pip install pywin32

# Then run post-install
python Scripts/pywin32_postinstall.py -install
```

### Service Won't Start

Check Windows Event Viewer:
1. Open Event Viewer
2. Navigate to Windows Logs > Application
3. Look for "JARVIS" errors

### Audio Quality Issues

1. Set preferred microphone:
   ```powershell
   python -m jarvis.desktop audio-set --microphone "USB Mic"
   ```

2. Adjust noise threshold in config

## Uninstallation

### Standard Uninstall

```powershell
python -m jarvis.desktop uninstall
```

### Complete Removal

```powershell
# Remove application
Remove-Item -Recurse -Force $env:APPDATA\JARVIS

# Remove shortcuts
Remove-Item "$env:USERPROFILE\Desktop\JARVIS.lnk"
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\JARVIS.lnk"

# Remove from startup (if enabled)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v JARVIS /f
```

## Support

- **Issues**: GitHub Issues
- **Documentation**: [docs/README.md](README.md)
- **Discord**: Join our community

## Next Steps

1. [Configuration Guide](CONFIG.md)
2. [Plugin Development](PLUGINS.md)
3. [VS Code Integration](VSCODE.md)
4. [Release Checklist](RELEASE_CHECKLIST.md)
