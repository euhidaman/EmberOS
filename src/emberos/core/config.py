"""
Configuration management for EmberOS.
"""

from __future__ import annotations

import os
import toml
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

from emberos.core.constants import (
    CONFIG_DIR,
    DATA_DIR,
    CACHE_DIR,
    DEFAULT_LLM_SERVER_URL,
    DEFAULT_CONTEXT_SIZE,
    DEFAULT_TEMPERATURE,
    DEFAULT_MODEL,
    MODEL_DIR,
)


class LLMConfig(BaseModel):
    """LLM server configuration."""
    server_url: str = DEFAULT_LLM_SERVER_URL
    model_path: str = str(MODEL_DIR / DEFAULT_MODEL)
    context_size: int = DEFAULT_CONTEXT_SIZE
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    timeout: int = 120


class GUIConfig(BaseModel):
    """GUI configuration."""
    theme: str = "dark"
    opacity: float = 0.95
    blur_radius: int = 20
    window_width: int = 800
    window_height: int = 700
    always_on_top: bool = False
    start_minimized: bool = False
    show_in_tray: bool = True
    animation_enabled: bool = True
    font_family: str = "Inter, SF Pro Display, system-ui"
    font_size: int = 14


class CLIConfig(BaseModel):
    """CLI configuration."""
    color_enabled: bool = True
    syntax_highlighting: bool = True
    history_size: int = 1000
    prompt_style: str = "default"
    show_stats: bool = True
    autocomplete: bool = True
    multiline_mode: bool = True


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    sqlite_path: str = str(DATA_DIR / "ember.db")
    vector_db_path: str = str(DATA_DIR / "vectors")
    embedding_model: str = "all-MiniLM-L6-v2"
    max_conversation_history: int = 100
    consolidation_interval: int = 3600  # seconds
    auto_backup: bool = True
    backup_interval: int = 86400  # daily


class PermissionsConfig(BaseModel):
    """Permission system configuration."""
    filesystem_read_allowed: list[str] = Field(default_factory=lambda: ["~/*", "/tmp/*"])
    filesystem_read_blocked: list[str] = Field(default_factory=lambda: ["~/.ssh/*", "~/.gnupg/*"])
    filesystem_write_allowed: list[str] = Field(default_factory=lambda: ["~/Documents/*", "~/Downloads/*"])
    max_file_size_mb: int = 100
    require_confirmation_destructive: bool = True
    network_enabled: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)


class DaemonConfig(BaseModel):
    """Daemon configuration."""
    log_level: str = "INFO"
    log_file: Optional[str] = None
    pid_file: str = str(CACHE_DIR / "emberd.pid")
    socket_path: str = str(CACHE_DIR / "emberd.sock")
    max_concurrent_tasks: int = 5
    task_timeout: int = 120
    context_update_interval: float = 0.5  # seconds


class EmberConfig(BaseModel):
    """Main configuration for EmberOS."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    gui: GUIConfig = Field(default_factory=GUIConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    daemon: DaemonConfig = Field(default_factory=DaemonConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> EmberConfig:
        """Load configuration from file."""
        if config_path is None:
            config_path = CONFIG_DIR / "emberos.toml"

        if config_path.exists():
            with open(config_path, "r") as f:
                data = toml.load(f)
            return cls(**data)

        return cls()

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if config_path is None:
            config_path = CONFIG_DIR / "emberos.toml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            toml.dump(self.model_dump(), f)

    @classmethod
    def from_env(cls) -> EmberConfig:
        """Load configuration with environment variable overrides."""
        config = cls.load()

        # Environment overrides
        env_mappings = {
            "EMBER_MODEL": ("llm", "model_path"),
            "EMBER_TEMPERATURE": ("llm", "temperature"),
            "EMBER_TIMEOUT": ("llm", "timeout"),
            "EMBER_LOG_LEVEL": ("daemon", "log_level"),
            "EMBER_CONTEXT_SIZE": ("llm", "context_size"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                section_obj = getattr(config, section)
                field_info = section_obj.model_fields.get(key)
                if field_info:
                    # Convert to appropriate type
                    field_type = field_info.annotation
                    if field_type == float:
                        value = float(value)
                    elif field_type == int:
                        value = int(value)
                    elif field_type == bool:
                        value = value.lower() in ("true", "1", "yes")
                    setattr(section_obj, key, value)

        return config


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    directories = [
        DATA_DIR,
        CONFIG_DIR,
        CACHE_DIR,
        DATA_DIR / "tools",
        DATA_DIR / "vectors",
        DATA_DIR / "backups",
        CACHE_DIR / "logs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_default_config_content() -> str:
    """Get default configuration file content."""
    return '''# EmberOS Configuration
# Documentation: https://docs.emberos.org/config

[llm]
server_url = "http://127.0.0.1:8080"
context_size = 8192
temperature = 0.1
max_tokens = 2048
timeout = 120

[gui]
theme = "dark"
opacity = 0.95
blur_radius = 20
window_width = 800
window_height = 700
always_on_top = false
show_in_tray = true
animation_enabled = true
font_size = 14

[cli]
color_enabled = true
syntax_highlighting = true
history_size = 1000
autocomplete = true

[memory]
embedding_model = "all-MiniLM-L6-v2"
max_conversation_history = 100
auto_backup = true
backup_interval = 86400

[permissions]
filesystem_read_allowed = ["~/*", "/tmp/*"]
filesystem_read_blocked = ["~/.ssh/*", "~/.gnupg/*"]
filesystem_write_allowed = ["~/Documents/*", "~/Downloads/*"]
max_file_size_mb = 100
require_confirmation_destructive = true
network_enabled = false

[daemon]
log_level = "INFO"
max_concurrent_tasks = 5
task_timeout = 120
'''

