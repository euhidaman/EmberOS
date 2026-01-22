"""
Tool System for EmberOS.

Provides a plugin architecture for extensible tool execution with
permission management and sandboxing.
"""

from emberos.tools.registry import ToolRegistry, register_tool
from emberos.tools.base import BaseTool, ToolResult, ToolManifest
from emberos.tools.executor import ToolExecutor
from emberos.tools.permissions import PermissionManager

__all__ = [
    "ToolRegistry",
    "register_tool",
    "BaseTool",
    "ToolResult",
    "ToolManifest",
    "ToolExecutor",
    "PermissionManager",
]

