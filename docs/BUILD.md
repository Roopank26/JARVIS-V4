# JARVIS Desktop - Build Guide

## Quick Build

### Windows
```cmd
build.bat
```

### Linux/macOS
```bash
chmod +x build.sh
./build.sh
```

## Build Output

After successful build:
```
dist/JARVIS.exe    # Single executable (Windows)
dist/JARVIS        # Single executable (Linux/macOS)
```

## Build Options

### Clean Build
```cmd
build.bat -clean    # Windows
./build.sh -clean  # Linux/macOS
```

## Installation

### Windows - Quick Install
```cmd
startup.bat install
```

This creates:
- Desktop shortcut
- Start Menu shortcut
- Auto-start on boot

### Uninstall
```cmd
startup.bat uninstall
```

## Building from Source

### Prerequisites
- Python 3.10+
- pip

### Steps

1. **Clone repository**
   ```bash
   git clone <repo>
   cd JARVIS
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller pystray pillow psutil
   ```

3. **Build executable**
   ```cmd
   build.bat
   ```

## PyInstaller Configuration

The `JARVIS.spec` file configures the build:

- **Single file**: All dependencies bundled
- **No console**: Runs as GUI application
- **Hidden imports**: All JARVIS modules included

## Creating Windows Installer

For a distributable installer:

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Open `installer.iss`
3. Compile with `iscc installer.iss`

Output: `installer/JARVIS-Setup-3.0.0.exe`

## Auto-Start Configuration

The executable supports these arguments:
```
JARVIS.exe              # Start normally
JARVIS.exe --hidden     # Start minimized to tray
JARVIS.exe --console    # Start with console (debug)
```

Registry key for auto-start:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Value: JARVIS = "<path>\JARVIS.exe" --hidden
```

## System Requirements

- Windows 10/11 (x64)
- Linux (x64)
- macOS 10.15+ (x64, ARM64)

## Troubleshooting

### Build Fails
- Ensure Python 3.10+ is installed
- Run `pip install -r requirements.txt`
- Check for antivirus blocking

### Executable Won't Start
- Run with `--console` flag to see errors
- Check Windows Event Viewer
- Verify all DLLs are bundled

### Icon Missing
Run icon generator:
```bash
python create_icon.py
```
