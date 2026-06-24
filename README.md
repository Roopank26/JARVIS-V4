# JARVIS - Just A Rather Very Intelligent System

A cross-platform personal AI assistant combining the best features from Mark-XXXIX-OR and Claude Code.

## Features

- **Voice I/O**: Real-time voice input and output support
- **Memory System**: Session memory + persistent long-term storage
- **Tool System**: Extensible tool registry with permissions
- **File Management**: Read, write, search, and organize files
- **Terminal Execution**: Run shell commands and scripts
- **System Control**: System information, clipboard, environment variables
- **Planning**: LLM-driven multi-step task planning
- **Error Recovery**: Automatic retry and replanning on failure

## AI Provider

JARVIS uses **Groq** for fast LLM inference by default. Free tier available.

### Getting a Groq API Key

1. Go to: https://console.groq.com/keys
2. Sign up for a free account
3. Create an API key
4. Copy the key (starts with `gsk_`)

## Installation

### Prerequisites

- Python 3.11+
- pip
- Groq API key (free at https://console.groq.com)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Roopank26/JARVIS-V4.git
cd JARVIS-V4
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure API key:
```bash
mkdir -p ~/.jarvis
echo '{"groq_api_key": "gsk_your_key_here"}' > ~/.jarvis/api_keys.json
```

Or use environment variable:
```bash
export GROQ_API_KEY=gsk_your_key_here
```

## Usage

### Command Line

```bash
# Run JARVIS with interactive CLI
python -m jarvis

# Or with API key as argument
python -m jarvis your-api-key
```

### Python API

```python
from jarvis.core.agent import create_jarvis
from jarvis.memory.memory_manager import MemoryManager
from jarvis.tools.registry import get_registry

# Create JARVIS
jarvis = create_jarvis(api_key="your-api-key")

# Process a query
response = await jarvis.process("What files are in my home directory?")
print(response)

# Execute a task
result = await jarvis.execute_task("Create a file called hello.py with hello world")
print(result)

# Remember something
jarvis.remember("name", "John", "identity")

# Recall from memory
memories = jarvis.recall("name")
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Components

### Core (`jarvis/core/`)
- **agent.py**: Main JARVIS agent orchestration
- **planner.py**: LLM-driven plan generation
- **executor.py**: Plan execution with error recovery
- **config.py**: Configuration management

### Memory (`jarvis/memory/`)
- **session.py**: In-memory conversation history
- **long_term.py**: Persistent JSON storage
- **memory_manager.py**: Unified memory API

### Tools (`jarvis/tools/`)
- **file_tools.py**: File operations
- **terminal_tools.py**: Shell commands
- **system_tools.py**: System control

### Voice (`jarvis/voice/`)
- **audio.py**: Audio capture/playback

### Vision (`jarvis/vision/`)
- **screen.py**: Screen capture
- **camera.py**: Webcam capture

### API (`jarvis/api/`)
- **gemini.py**: Gemini API client

### UI (`jarvis/ui/`)
- **cli.py**: Terminal interface

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Create/write files |
| `list_directory` | List directory contents |
| `find_files` | Search for files |
| `delete_file` | Delete files |
| `disk_usage` | Get disk usage |
| `bash` | Execute shell commands |
| `run_script` | Run script files |
| `get_system_info` | Get system information |
| `open_app` | Open applications/URLs |
| `get_environment` | Get environment variables |
| `get_clipboard` | Get clipboard contents |
| `set_clipboard` | Set clipboard contents |

## Commands

In the CLI, you can use these direct commands:

- `help` - Show help message
- `tools` - List available tools
- `status` - Show agent status
- `memory` - Show stored memory
- `clear` - Clear the screen
- `exit` / `quit` - Exit JARVIS

## Configuration

Configuration is stored in `~/.jarvis/`:

- `config.json` - Main settings
- `api_keys.json` - API keys
- `memory/long_term.json` - Persistent memory

### Configuration Options

```json
{
    "model": "gemini-2.0-flash",
    "voice_enabled": true,
    "language": "en",
    "max_retries": 3,
    "max_replans": 2,
    "memory_max_chars": 2200
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
JARVIS/
├── jarvis/           # Main package
│   ├── core/         # Core engine
│   ├── memory/       # Memory systems
│   ├── tools/        # Tool registry
│   ├── voice/        # Voice I/O
│   ├── vision/       # Vision modules
│   ├── api/          # API clients
│   ├── ui/           # User interfaces
│   └── utils/        # Utilities
├── config/          # Configuration
├── memory/          # Memory storage
├── tests/           # Test suite
└── docs/            # Documentation
```

## License

MIT License

## Credits

- Mark-XXXIX-OR: https://github.com/FatihMakes/Mark-XXXIX-OR
- Claude Code: https://github.com/Kuberwastaken/claude-code
