"""
Windows HTTP Server for EmberOS Daemon.

Provides REST API for Windows since D-Bus is not available.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from aiohttp import web

if TYPE_CHECKING:
    from emberos.daemon.service import EmberDaemon

logger = logging.getLogger(__name__)


class WindowsHTTPServer:
    """
    HTTP REST server for EmberOS on Windows.

    Provides endpoints for:
    - /health - Health check
    - /api/status - Daemon status
    - /api/command - Process commands
    - /api/tool - Execute tools
    - /api/tools - List tools
    - /api/context - Get context
    - /api/memory - Memory operations
    - /api/config - Configuration
    """

    DEFAULT_PORT = 38888

    def __init__(self, daemon: 'EmberDaemon', port: int = None):
        self.daemon = daemon
        self.port = port or self.DEFAULT_PORT
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def start(self) -> None:
        """Start the HTTP server."""
        logger.info(f"Starting Windows HTTP server on port {self.port}...")

        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, '127.0.0.1', self.port)
        await self._site.start()

        logger.info(f"HTTP server started at http://127.0.0.1:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        logger.info("Stopping HTTP server...")

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        logger.info("HTTP server stopped")

    def _setup_routes(self) -> None:
        """Setup API routes."""
        self._app.router.add_get('/health', self._health)
        self._app.router.add_get('/api/status', self._get_status)
        self._app.router.add_post('/api/command', self._process_command)
        self._app.router.add_post('/api/tool', self._execute_tool)
        self._app.router.add_get('/api/tools', self._list_tools)
        self._app.router.add_get('/api/tools/{tool_name}', self._get_tool_schema)
        self._app.router.add_get('/api/context', self._get_context)
        self._app.router.add_get('/api/memory/search', self._search_memory)
        self._app.router.add_get('/api/config', self._get_config)
        self._app.router.add_get('/api/config/{section}', self._get_config_section)
        self._app.router.add_put('/api/config/{section}/{key}', self._set_config)
        self._app.router.add_post('/api/task/{task_id}/confirm', self._confirm_action)
        self._app.router.add_post('/api/task/{task_id}/cancel', self._cancel_task)

    async def _health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "ok"})

    async def _get_status(self, request: web.Request) -> web.Response:
        """Get daemon status."""
        llm_connected = False
        model_name = "Unknown"

        if self.daemon.llm:
            llm_connected = self.daemon.llm._vision_connected or self.daemon.llm._text_connected
            model_name = self.daemon.llm._vision_model_name or self.daemon.llm._text_model_name or "Unknown"

        return web.json_response({
            "version": "1.0.0",
            "running": self.daemon._running,
            "llm_connected": llm_connected,
            "model_name": model_name,
            "active_tasks": len(self.daemon._tasks),
            "uptime_seconds": (datetime.now() - self.daemon._start_time).total_seconds() if self.daemon._start_time else 0
        })

    async def _process_command(self, request: web.Request) -> web.Response:
        """Process a natural language command."""
        try:
            data = await request.json()
            message = data.get("message", "")

            if not message:
                return web.json_response(
                    {"error": "Message is required"},
                    status=400
                )

            # Process command through daemon
            result = await self.daemon.process_command(message)
            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return web.json_response(
                {"error": str(e), "success": False},
                status=500
            )

    async def _execute_tool(self, request: web.Request) -> web.Response:
        """Execute a tool directly."""
        try:
            data = await request.json()
            tool_name = data.get("tool")
            params = data.get("params", {})

            if not tool_name:
                return web.json_response(
                    {"error": "Tool name is required"},
                    status=400
                )

            # Execute tool
            result = await self.daemon.tool_registry.execute(tool_name, params)
            return web.json_response({
                "success": result.success,
                "data": result.data,
                "error": result.error
            })

        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return web.json_response(
                {"error": str(e), "success": False},
                status=500
            )

    async def _list_tools(self, request: web.Request) -> web.Response:
        """List available tools."""
        tools = self.daemon.tool_registry.list_tools() if self.daemon.tool_registry else []
        return web.json_response({"tools": tools})

    async def _get_tool_schema(self, request: web.Request) -> web.Response:
        """Get tool schema."""
        tool_name = request.match_info['tool_name']

        if not self.daemon.tool_registry:
            return web.json_response({"error": "Tool registry not available"}, status=500)

        schema = self.daemon.tool_registry.get_tool_schema(tool_name)
        if schema:
            return web.json_response(schema)

        return web.json_response({"error": f"Tool not found: {tool_name}"}, status=404)

    async def _get_context(self, request: web.Request) -> web.Response:
        """Get current context."""
        if self.daemon.context_monitor:
            ctx = self.daemon.context_monitor.get_current_context()
            return web.json_response(ctx)
        return web.json_response({})

    async def _search_memory(self, request: web.Request) -> web.Response:
        """Search memory."""
        query = request.query.get("query", "")
        limit = int(request.query.get("limit", "10"))

        if not query:
            return web.json_response({"results": []})

        if self.daemon.memory:
            results = await self.daemon.memory.search(query, limit=limit)
            return web.json_response({"results": results})

        return web.json_response({"results": []})

    async def _get_config(self, request: web.Request) -> web.Response:
        """Get all configuration."""
        return web.json_response(self.daemon.config.to_dict())

    async def _get_config_section(self, request: web.Request) -> web.Response:
        """Get configuration section."""
        section = request.match_info['section']
        config_dict = self.daemon.config.to_dict()

        if section in config_dict:
            return web.json_response(config_dict[section])

        return web.json_response({"error": f"Section not found: {section}"}, status=404)

    async def _set_config(self, request: web.Request) -> web.Response:
        """Set configuration value."""
        section = request.match_info['section']
        key = request.match_info['key']

        try:
            data = await request.json()
            value = data.get("value")

            # TODO: Implement config update
            return web.json_response({"success": True})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _confirm_action(self, request: web.Request) -> web.Response:
        """Confirm or reject a pending action."""
        task_id = request.match_info['task_id']

        try:
            data = await request.json()
            confirmed = data.get("confirmed", False)

            result = await self.daemon.confirm_task(task_id, confirmed)
            return web.json_response(result)

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _cancel_task(self, request: web.Request) -> web.Response:
        """Cancel a running task."""
        task_id = request.match_info['task_id']

        try:
            result = await self.daemon.cancel_task(task_id)
            return web.json_response(result)

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

