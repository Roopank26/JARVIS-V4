"""
JARVIS Configuration Management
"""

import json
from pathlib import Path


class Config:
    """Central configuration management for JARVIS."""

    DEFAULT_CONFIG_DIR = Path.home() / ".jarvis"
    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_API_KEYS_FILE = "api_keys.json"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config: dict = {}
        self._api_keys: dict = {}

        self._load_configs()

    def _load_configs(self):
        """Load configuration files."""
        # Load main config
        config_path = self.config_dir / self.DEFAULT_CONFIG_FILE
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                self._config = json.load(f)

        # Load API keys
        api_keys_path = self.config_dir / self.DEFAULT_API_KEYS_FILE
        if api_keys_path.exists():
            with open(api_keys_path, encoding="utf-8") as f:
                self._api_keys = json.load(f)

        # Set defaults for missing values
        self._set_defaults()

    def _set_defaults(self):
        """Set default configuration values."""
        defaults = {
            "voice_enabled": True,
            "language": "en",
            "voice_name": "Charon",
            "audio_sample_rate": 16000,
            "audio_channels": 1,
            "chunk_size": 1024,
            "max_retries": 3,
            "max_replans": 2,
            "memory_max_chars": 2200,
            "memory_max_value_length": 380,
        }

        for key, value in defaults.items():
            if key not in self._config:
                self._config[key] = value

    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value):
        """Set a configuration value."""
        self._config[key] = value
        self._save_config()

    def get_api_key(self, provider: str = "gemini") -> str | None:
        """Get an API key for a provider."""
        return self._api_keys.get(f"{provider}_api_key")

    def set_api_key(self, provider: str, key: str):
        """Set an API key for a provider."""
        self._api_keys[f"{provider}_api_key"] = key
        self._save_api_keys()

    def _save_config(self):
        """Save configuration to file."""
        config_path = self.config_dir / self.DEFAULT_CONFIG_FILE
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def _save_api_keys(self):
        """Save API keys to file."""
        api_keys_path = self.config_dir / self.DEFAULT_API_KEYS_FILE
        with open(api_keys_path, "w", encoding="utf-8") as f:
            json.dump(self._api_keys, f, indent=2)

    @property
    def model(self) -> str:
        return self.get("model", "llama-3.3-70b-versatile")

    @property
    def live_model(self) -> str:
        return self.get("live_model", "llama-3.3-70b-versatile")

    @property
    def voice_enabled(self) -> bool:
        return self.get("voice_enabled", True)

    @property
    def audio_sample_rate(self) -> int:
        return self.get("audio_sample_rate", 16000)

    @property
    def audio_channels(self) -> int:
        return self.get("audio_channels", 1)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(config_dir: Path | None = None) -> Config:
    """Initialize the global configuration."""
    global _config
    _config = Config(config_dir)
    return _config
