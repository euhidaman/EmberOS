"""
D-Bus Client for EmberOS CLI.

Connects to the emberd daemon for command execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass

from dbus_next.aio import MessageBus
from dbus_next import BusType, Variant

from emberos.core.constants import DBUS_NAME, DBUS_PATH, DBUS_INTERFACE

logger = logging.getLogger(__name__)


@dataclass
class TaskUpdate:
    """Update from a running task."""
    task_id: str
    event_type: str  # progress, completed, failed, confirmation_required
    data: dict


class EmberClient:
    """
    D-Bus client for connecting to the EmberOS daemon.

    Provides async methods for:
    - Processing commands
    - Executing tools
    - Managing tasks
    - Querying status
    """

    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.proxy = None
        self.interface = None
        self._connected = False
        self._callbacks: dict[str, list[Callable]] = {
            "progress": [],
            "completed": [],
            "failed": [],
            "confirmation": [],
            "context_changed": [],
        }

    async def connect(self) -> bool:
        """Connect to the EmberOS daemon."""
        try:
            self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

            introspection = await self.bus.introspect(DBUS_NAME, DBUS_PATH)
            self.proxy = self.bus.get_proxy_object(DBUS_NAME, DBUS_PATH, introspection)
            self.interface = self.proxy.get_interface(DBUS_INTERFACE)

            # Setup signal handlers
            self.interface.on_task_progress(self._on_task_progress)
            self.interface.on_task_completed(self._on_task_completed)
            self.interface.on_task_failed(self._on_task_failed)
            self.interface.on_confirmation_required(self._on_confirmation_required)
            self.interface.on_context_changed(self._on_context_changed)

            self._connected = True
            logger.info("Connected to EmberOS daemon")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to daemon: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the daemon."""
        if self.bus:
            self.bus.disconnect()
            self.bus = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to daemon."""
        return self._connected

    # ============ Signal Handlers ============

    def _on_task_progress(self, task_id: str, stage: str, message: str):
        """Handle task progress signal."""
        update = TaskUpdate(
            task_id=task_id,
            event_type="progress",
            data={"stage": stage, "message": message}
        )
        self._notify("progress", update)

    def _on_task_completed(self, task_id: str, result_json: str):
        """Handle task completed signal."""
        update = TaskUpdate(
            task_id=task_id,
            event_type="completed",
            data=json.loads(result_json)
        )
        self._notify("completed", update)

    def _on_task_failed(self, task_id: str, error_json: str):
        """Handle task failed signal."""
        update = TaskUpdate(
            task_id=task_id,
            event_type="failed",
            data=json.loads(error_json)
        )
        self._notify("failed", update)

    def _on_confirmation_required(self, task_id: str, plan_json: str):
        """Handle confirmation required signal."""
        update = TaskUpdate(
            task_id=task_id,
            event_type="confirmation",
            data=json.loads(plan_json)
        )
        self._notify("confirmation", update)

    def _on_context_changed(self, context_json: str):
        """Handle context changed signal."""
        update = TaskUpdate(
            task_id="",
            event_type="context_changed",
            data=json.loads(context_json)
        )
        self._notify("context_changed", update)

    def _notify(self, event_type: str, update: TaskUpdate):
        """Notify registered callbacks."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def on(self, event_type: str, callback: Callable[[TaskUpdate], None]):
        """Register a callback for an event type."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)

    def off(self, event_type: str, callback: Callable[[TaskUpdate], None]):
        """Unregister a callback."""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    # ============ Commands ============

    async def process_command(self, message: str) -> dict:
        """
        Process a natural language command.

        Returns initial response with task_id.
        """
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_process_command(message)
        return json.loads(result)

    async def execute_tool(self, tool_name: str, params: dict) -> dict:
        """Execute a tool directly."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_execute_tool(tool_name, json.dumps(params))
        return json.loads(result)

    async def confirm_action(self, task_id: str, confirmed: bool) -> dict:
        """Confirm or reject a pending action."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_confirm_action(task_id, confirmed)
        return json.loads(result)

    async def cancel_task(self, task_id: str) -> dict:
        """Cancel a running task."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_cancel_task(task_id)
        return json.loads(result)

    async def get_status(self) -> dict:
        """Get daemon status."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_get_status()
        return json.loads(result)

    async def get_context(self) -> dict:
        """Get current context."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_get_context()
        return json.loads(result)

    async def list_tools(self) -> list[dict]:
        """List available tools."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_list_tools()
        return json.loads(result)

    async def get_tool_schema(self, tool_name: str) -> dict:
        """Get tool schema."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_get_tool_schema(tool_name)
        return json.loads(result)

    async def search_memory(self, query: str, limit: int = 10) -> list[dict]:
        """Search memory."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_search_memory(query, limit)
        return json.loads(result)

    async def get_config(self, section: str = "") -> dict:
        """Get configuration."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_get_config(section)
        return json.loads(result)

    async def set_config(self, section: str, key: str, value: str) -> dict:
        """Set configuration value."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")

        result = await self.interface.call_set_config(section, key, value)
        return json.loads(result)

    # ============ Properties ============

    async def get_version(self) -> str:
        """Get EmberOS version."""
        if not self._connected:
            raise ConnectionError("Not connected to daemon")
        return await self.interface.get_version()

    async def is_llm_connected(self) -> bool:
        """Check if LLM server is connected."""
        if not self._connected:
            return False
        return await self.interface.get_is_connected()

    async def get_model_name(self) -> str:
        """Get current model name."""
        if not self._connected:
            return "Unknown"
        return await self.interface.get_model_name()

    async def get_active_task_count(self) -> int:
        """Get number of active tasks."""
        if not self._connected:
            return 0
        return await self.interface.get_active_task_count()


class OfflineClient:
    """
    Offline client that executes tools directly without daemon.

    Used when daemon is not available.
    """

    def __init__(self):
        self._tool_registry = None

    async def initialize(self):
        """Initialize offline mode."""
        from emberos.tools.registry import ToolRegistry
        self._tool_registry = ToolRegistry()
        await self._tool_registry.load_tools()

    @property
    def is_connected(self) -> bool:
        return False

    async def execute_tool(self, tool_name: str, params: dict) -> dict:
        """Execute a tool directly."""
        if self._tool_registry is None:
            await self.initialize()

        result = await self._tool_registry.execute(tool_name, params)
        return {"success": True, "result": result}

    async def list_tools(self) -> list[dict]:
        """List available tools."""
        if self._tool_registry is None:
            await self.initialize()

        return self._tool_registry.list_tools()

    async def get_status(self) -> dict:
        """Get status (offline mode)."""
        return {
            "running": False,
            "mode": "offline",
            "llm_connected": False,
            "tools_loaded": self._tool_registry.tool_count if self._tool_registry else 0
        }

