"""
EmberOS Platform-Specific Modules.

Provides platform-specific implementations for:
- Service management (systemd on Linux, Task Scheduler on Windows)
- System integration
- Process management
"""

from __future__ import annotations

import sys

# Detect platform
IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')
IS_MACOS = sys.platform == 'darwin'


def get_service_manager():
    """Get the appropriate service manager for the current platform."""
    if IS_WINDOWS:
        from emberos.platform.windows_service import get_service_manager as get_win_manager
        return get_win_manager()
    else:
        # Linux uses systemd - return a compatible interface
        from emberos.platform.linux_service import get_service_manager as get_linux_manager
        return get_linux_manager()


__all__ = [
    'IS_WINDOWS',
    'IS_LINUX',
    'IS_MACOS',
    'get_service_manager',
]

