"""
Windows IPC Client for EmberOS.

Uses named pipes and HTTP for communication on Windows since D-Bus is not available.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class TaskUpdate:
    """Update from a running task."""
    task_id: str
    event_type: str
    data: dict


class WindowsEmberClient:
    """
    Windows client for connecting to the EmberOS daemon.

    Uses HTTP REST API instead of D-Bus for Windows compatibility.
    """

    # Default daemon port
    DAEMON_PORT = 38888

    def __init__(self, host: str = "127.0.0.1", port: int = None):
        self.host = host
        self.port = port or self.DAEMON_PORT
        self._base_url = f"http://{self.host}:{self.port}"
        self.session: Optional[aiohttp.ClientSession] = None
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
            timeout = aiohttp.ClientTimeout(total=5)
            self.session = aiohttp.ClientSession(timeout=timeout)

            # Check health endpoint
            async with self.session.get(f"{self._base_url}/health") as resp:
                if resp.status == 200:
                    self._connected = True
                    logger.info("Connected to EmberOS daemon (Windows mode)")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to daemon: {e}")
            self._connected = False

            if self.session:
                await self.session.close()
                self.session = None

        return False

    async def disconnect(self) -> None:
        """Disconnect from the daemon."""
        if self.session:
            await self.session.close()
            self.session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to daemon."""
        return self._connected

    def on(self, event_type: str, callback: Callable[[TaskUpdate], None]):
        """Register a callback for an event type."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)

    def off(self, event_type: str, callback: Callable[[TaskUpdate], None]):
        """Unregister a callback."""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def _notify(self, event_type: str, update: TaskUpdate):
        """Notify registered callbacks."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make a request to the daemon."""
        if not self._connected or not self.session:
            raise ConnectionError("Not connected to daemon")

        url = f"{self._base_url}{endpoint}"

        async with self.session.request(method, url, **kwargs) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Request failed: {resp.status} - {error_text}")

            return await resp.json()

    async def process_command(self, message: str) -> dict:
        """Process a natural language command."""
        return await self._request("POST", "/api/command", json={"message": message})

    async def execute_tool(self, tool_name: str, params: dict) -> dict:
        """Execute a tool directly."""
        return await self._request("POST", "/api/tool", json={
            "tool": tool_name,
            "params": params
        })

    async def confirm_action(self, task_id: str, confirmed: bool) -> dict:
        """Confirm or reject a pending action."""
        return await self._request("POST", f"/api/task/{task_id}/confirm", json={
            "confirmed": confirmed
        })

    async def cancel_task(self, task_id: str) -> dict:
        """Cancel a running task."""
        return await self._request("POST", f"/api/task/{task_id}/cancel")

    async def get_status(self) -> dict:
        """Get daemon status."""
        return await self._request("GET", "/api/status")

    async def get_context(self) -> dict:
        """Get current context."""
        return await self._request("GET", "/api/context")

    async def list_tools(self) -> list[dict]:
        """List available tools."""
        result = await self._request("GET", "/api/tools")
        return result.get("tools", [])

    async def get_tool_schema(self, tool_name: str) -> dict:
        """Get tool schema."""
        return await self._request("GET", f"/api/tools/{tool_name}")

    async def search_memory(self, query: str, limit: int = 10) -> list[dict]:
        """Search memory."""
        result = await self._request("GET", "/api/memory/search", params={
            "query": query,
            "limit": limit
        })
        return result.get("results", [])

    async def get_config(self, section: str = "") -> dict:
        """Get configuration."""
        endpoint = f"/api/config/{section}" if section else "/api/config"
        return await self._request("GET", endpoint)

    async def set_config(self, section: str, key: str, value: str) -> dict:
        """Set configuration value."""
        return await self._request("PUT", f"/api/config/{section}/{key}", json={
            "value": value
        })

    async def get_version(self) -> str:
        """Get EmberOS version."""
        status = await self.get_status()
        return status.get("version", "1.0.0")

    async def is_llm_connected(self) -> bool:
        """Check if LLM server is connected."""
        status = await self.get_status()
        return status.get("llm_connected", False)

    async def get_model_name(self) -> str:
        """Get current model name."""
        status = await self.get_status()
        return status.get("model_name", "Unknown")

    async def get_active_task_count(self) -> int:
        """Get number of active tasks."""
        status = await self.get_status()
        return status.get("active_tasks", 0)


def get_ember_client():
    """Get the appropriate client for the current platform."""
    import sys
    if sys.platform == 'win32':
        return WindowsEmberClient()
    else:
        from emberos.cli.client import EmberClient
        return EmberClient()

