"""
EmberOS - An AI-native layer for Arch Linux

EmberOS transforms Arch Linux into an agentic OS where every interaction,
whether through a beautiful GUI or powerful terminal, flows through an
intelligent, private AI agent.
"""

__version__ = "1.0.0"
__author__ = "EmberOS Team"

from emberos.core.config import EmberConfig
from emberos.core.constants import (
    APP_NAME,
    APP_ID,
    DBUS_NAME,
    DBUS_PATH,
)

__all__ = [
    "__version__",
    "EmberConfig",
    "APP_NAME",
    "APP_ID",
    "DBUS_NAME",
    "DBUS_PATH",
]

