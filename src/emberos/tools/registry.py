"""
Tool Registry for EmberOS.

Manages tool discovery, registration, and execution.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Any, Callable, Optional, Type
from pathlib import Path
from datetime import datetime

from emberos.tools.base import BaseTool, ToolManifest, ToolResult
from emberos.tools.permissions import PermissionManager
from emberos.core.constants import DATA_DIR

logger = logging.getLogger(__name__)

# Global registry for decorator-based registration
_TOOL_REGISTRY: dict[str, Type[BaseTool]] = {}


def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """
    Decorator to register a tool class.

    Usage:
        @register_tool
        class MyTool(BaseTool):
            ...
    """
    # Create a temporary instance to get the manifest
    try:
        instance = cls()
        name = instance.manifest.name
        _TOOL_REGISTRY[name] = cls
        logger.debug(f"Registered tool: {name}")
    except Exception as e:
        logger.error(f"Failed to register tool {cls.__name__}: {e}")

    return cls


class ToolRegistry:
    """
    Registry for managing EmberOS tools.

    Handles:
    - Tool discovery and loading
    - Tool instantiation
    - Permission checking
    - Execution routing
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._tool_classes: dict[str, Type[BaseTool]] = {}
        self._permission_manager = PermissionManager()
        self._stats: dict[str, dict] = {}

    async def load_tools(self) -> None:
        """Load all available tools."""
        logger.info("Loading tools...")

        # Load built-in tools
        await self._load_builtin_tools()

        # Load decorator-registered tools
        self._load_registered_tools()

        # Load custom tools from user directory
        await self._load_custom_tools()

        logger.info(f"Loaded {len(self._tools)} tools")

    async def _load_builtin_tools(self) -> None:
        """Load built-in tools."""
        builtin_modules = [
            "emberos.tools.builtin.filesystem",
            "emberos.tools.builtin.notes",
            "emberos.tools.builtin.applications",
            "emberos.tools.builtin.system",
        ]

        for module_name in builtin_modules:
            try:
                module = importlib.import_module(module_name)

                # Find all BaseTool subclasses in module
                for name in dir(module):
                    obj = getattr(module, name)
                    if (isinstance(obj, type) and
                        issubclass(obj, BaseTool) and
                        obj is not BaseTool):
                        self._register_tool_class(obj)

            except ImportError as e:
                logger.debug(f"Could not load builtin module {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error loading builtin tools from {module_name}: {e}")

    def _load_registered_tools(self) -> None:
        """Load tools registered via decorator."""
        for name, cls in _TOOL_REGISTRY.items():
            if name not in self._tool_classes:
                self._register_tool_class(cls)

    async def _load_custom_tools(self) -> None:
        """Load custom tools from user tools directory."""
        tools_dir = DATA_DIR / "tools"

        if not tools_dir.exists():
            return

        for tool_dir in tools_dir.iterdir():
            if tool_dir.is_dir() and (tool_dir / "__init__.py").exists():
                try:
                    # Add to path and import
                    import sys
                    if str(tools_dir) not in sys.path:
                        sys.path.insert(0, str(tools_dir))

                    module = importlib.import_module(tool_dir.name)

                    # Find BaseTool subclasses
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (isinstance(obj, type) and
                            issubclass(obj, BaseTool) and
                            obj is not BaseTool):
                            self._register_tool_class(obj)

                except Exception as e:
                    logger.error(f"Error loading custom tool from {tool_dir}: {e}")

    def _register_tool_class(self, cls: Type[BaseTool]) -> None:
        """Register a tool class."""
        try:
            instance = cls()
            name = instance.manifest.name

            self._tool_classes[name] = cls
            self._tools[name] = instance
            self._stats[name] = {
                "call_count": 0,
                "success_count": 0,
                "error_count": 0,
                "total_duration_ms": 0,
                "last_called": None
            }

            logger.debug(f"Registered tool: {name}")

        except Exception as e:
            logger.error(f"Failed to register tool {cls.__name__}: {e}")

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        name = tool.manifest.name
        self._tools[name] = tool
        self._tool_classes[name] = type(tool)
        self._stats[name] = {
            "call_count": 0,
            "success_count": 0,
            "error_count": 0,
            "total_duration_ms": 0,
            "last_called": None
        }

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            del self._tool_classes[name]
            del self._stats[name]

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool instance by name."""
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[dict]:
        """Get tool schema by name."""
        tool = self._tools.get(name)
        if tool:
            return tool.get_schema()
        return None

    def get_all_schemas(self) -> list[dict]:
        """Get schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def list_tools(self) -> list[dict]:
        """List all registered tools."""
        result = []
        for name, tool in self._tools.items():
            manifest = tool.manifest
            result.append({
                "name": name,
                "description": manifest.description,
                "category": manifest.category.value,
                "icon": manifest.icon,
                "risk_level": manifest.risk_level.value,
                "stats": self._stats.get(name, {})
            })
        return result

    async def execute(self, name: str, params: dict[str, Any]) -> Any:
        """
        Execute a tool.

        Args:
            name: Tool name
            params: Parameters for the tool

        Returns:
            Tool execution result
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        # Validate parameters
        is_valid, error = tool.validate(params)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {error}")

        # Check permissions
        if not self._permission_manager.check(tool.manifest, params):
            raise PermissionError(f"Permission denied for tool: {name}")

        # Execute
        start_time = datetime.now()

        try:
            result = await tool.execute(params)

            # Update stats
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_stats(name, True, duration_ms)

            if isinstance(result, ToolResult):
                return result.data if result.success else result
            return result

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_stats(name, False, duration_ms)
            raise

    def _update_stats(self, name: str, success: bool, duration_ms: int) -> None:
        """Update tool execution statistics."""
        if name in self._stats:
            stats = self._stats[name]
            stats["call_count"] += 1
            stats["total_duration_ms"] += duration_ms
            stats["last_called"] = datetime.now().isoformat()

            if success:
                stats["success_count"] += 1
            else:
                stats["error_count"] += 1

    @property
    def tool_count(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def get_tools_by_category(self, category: str) -> list[BaseTool]:
        """Get tools by category."""
        return [
            tool for tool in self._tools.values()
            if tool.manifest.category.value == category
        ]

