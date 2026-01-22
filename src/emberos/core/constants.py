"""
Core constants for EmberOS.
"""

import os
from pathlib import Path

# Application identity
APP_NAME = "EmberOS"
APP_ID = "org.emberos.EmberOS"
APP_VERSION = "1.0.0"

# D-Bus configuration
DBUS_NAME = "org.ember.Agent"
DBUS_PATH = "/org/ember/Agent"
DBUS_INTERFACE = "org.ember.Agent"

# Directory paths
if os.environ.get("EMBER_DEV_MODE"):
    DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
    CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
    CACHE_DIR = Path(__file__).parent.parent.parent.parent / "cache"
else:
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ember"
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ember"
    CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ember"

# System paths
SYSTEM_DATA_DIR = Path("/usr/local/share/ember")
SYSTEM_CONFIG_DIR = Path("/etc/ember")
MODEL_DIR = SYSTEM_DATA_DIR / "models"
TOOLS_DIR = DATA_DIR / "tools"

# Database paths
DB_PATH = DATA_DIR / "ember.db"
VECTOR_DB_PATH = DATA_DIR / "vectors"

# Default model configuration
DEFAULT_MODEL = "qwen2.5-vl-7b-instruct-q4_k_m.gguf"
DEFAULT_LLM_SERVER_URL = "http://127.0.0.1:8080"
DEFAULT_CONTEXT_SIZE = 8192
DEFAULT_TEMPERATURE = 0.1

# UI Constants
EMBER_ORANGE = "#ff6b35"
EMBER_ORANGE_LIGHT = "#f7931e"
EMBER_DARK_BG = "#1a1a24"
EMBER_DARK_BG_LIGHT = "#242430"
EMBER_TEXT_PRIMARY = "#f0f0fa"
EMBER_TEXT_SECONDARY = "#a0a0b0"
EMBER_SUCCESS = "#4caf50"
EMBER_WARNING = "#ffc107"
EMBER_ERROR = "#f44336"

# Animation timings (ms)
ANIM_FAST = 100
ANIM_NORMAL = 200
ANIM_SLOW = 300
ANIM_SPRING = 250

# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_PERMISSION_DENIED = 3
EXIT_TIMEOUT = 4
EXIT_LLM_UNAVAILABLE = 5
EXIT_USER_CANCELLED = 6
EXIT_CONFIG_ERROR = 7
EXIT_TOOL_ERROR = 8
EXIT_MEMORY_FULL = 9
EXIT_VALIDATION_ERROR = 10

# Limits
MAX_CONTEXT_TOKENS = 16384
MAX_FILE_SIZE_MB = 100
MAX_HISTORY_ITEMS = 1000
MAX_CONCURRENT_TOOLS = 5
DEFAULT_TIMEOUT_SECONDS = 120

