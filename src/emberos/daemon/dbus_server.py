"""
D-Bus Server for EmberOS Daemon.

Exposes the org.ember.Agent interface for IPC communication between
the daemon and GUI/CLI clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, signal, dbus_property
from dbus_next import Variant, BusType

from emberos.core.constants import DBUS_NAME, DBUS_PATH, DBUS_INTERFACE

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    result: Any
    error: Optional[str]
    duration_ms: int
    timestamp: str


@dataclass
class ContextSnapshot:
    """Current system context snapshot."""
    active_window: str
    active_window_title: str
    selected_files: list[str]
    clipboard_text: str
    clipboard_type: str
    timestamp: str


class EmberAgentInterface(ServiceInterface):
    """
    D-Bus interface for EmberOS Agent.

    Provides methods for:
    - Processing natural language commands
    - Executing tools
    - Managing memory
    - Querying system status
    """

    def __init__(self, daemon: Any):
        super().__init__(DBUS_INTERFACE)
        self.daemon = daemon
        self._current_task_id: Optional[str] = None
        self._task_counter = 0

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        return f"task_{self._task_counter}_{int(datetime.now().timestamp())}"

    # ============ Methods ============

    @method()
    async def ProcessCommand(self, message: 's') -> 's':
        """
        Process a natural language command.

        Args:
            message: Natural language command from user

        Returns:
            JSON response with task_id and initial status
        """
        task_id = self._generate_task_id()
        self._current_task_id = task_id

        logger.info(f"Processing command: {message[:100]}...")

        # Start processing in background
        asyncio.create_task(self._process_command_async(task_id, message))

        return json.dumps({
            "task_id": task_id,
            "status": "processing",
            "message": "Command received, processing..."
        })

    async def _process_command_async(self, task_id: str, message: str) -> None:
        """Process command asynchronously."""
        start_time = datetime.now()

        try:
            # Get context snapshot
            context = await self.daemon.context_monitor.get_snapshot()

            # Emit progress
            self.TaskProgress(task_id, "planning", "Building execution plan...")

            # Generate plan
            plan = await self.daemon.planner.create_plan(message, context)

            # Check if confirmation required
            if plan.requires_confirmation:
                self.ConfirmationRequired(
                    task_id,
                    json.dumps({
                        "plan": plan.to_dict(),
                        "message": plan.confirmation_message
                    })
                )
                return

            # Execute plan
            self.TaskProgress(task_id, "executing", "Executing plan...")
            results = await self.daemon.execute_plan(plan)

            # Synthesize response
            self.TaskProgress(task_id, "synthesizing", "Generating response...")
            response = await self.daemon.planner.synthesize_response(message, plan, results)

            # Store in memory
            await self.daemon.memory.store_conversation(message, response, plan, results)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.TaskCompleted(task_id, json.dumps({
                "success": True,
                "response": response,
                "plan": plan.to_dict(),
                "results": [r.to_dict() if hasattr(r, 'to_dict') else r for r in results],
                "duration_ms": duration_ms
            }))

        except Exception as e:
            logger.exception(f"Error processing command: {e}")
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.TaskFailed(task_id, json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms
            }))

    @method()
    async def ExecuteTool(self, tool_name: 's', params_json: 's') -> 's':
        """
        Execute a specific tool directly.

        Args:
            tool_name: Name of the tool to execute
            params_json: JSON string of parameters

        Returns:
            JSON response with result
        """
        try:
            params = json.loads(params_json)
            result = await self.daemon.tool_registry.execute(tool_name, params)
            return json.dumps({
                "success": True,
                "result": result
            })
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @method()
    async def ConfirmAction(self, task_id: 's', confirmed: 'b') -> 's':
        """
        Confirm or reject a pending action.

        Args:
            task_id: The task ID requiring confirmation
            confirmed: Whether user confirmed the action

        Returns:
            JSON response with status
        """
        if confirmed:
            await self.daemon.resume_confirmed_task(task_id)
            return json.dumps({"status": "resumed"})
        else:
            await self.daemon.cancel_task(task_id)
            return json.dumps({"status": "cancelled"})

    @method()
    async def CancelTask(self, task_id: 's') -> 's':
        """Cancel a running task."""
        await self.daemon.cancel_task(task_id)
        return json.dumps({"status": "cancelled"})

    @method()
    def GetStatus(self) -> 's':
        """Get daemon status."""
        status = self.daemon.get_status()
        return json.dumps(status)

    @method()
    def GetContext(self) -> 's':
        """Get current context snapshot."""
        context = self.daemon.context_monitor.get_snapshot_sync()
        return json.dumps(asdict(context) if context else {})

    @method()
    def ListTools(self) -> 's':
        """List all available tools."""
        tools = self.daemon.tool_registry.list_tools()
        return json.dumps(tools)

    @method()
    def GetToolSchema(self, tool_name: 's') -> 's':
        """Get schema for a specific tool."""
        schema = self.daemon.tool_registry.get_schema(tool_name)
        return json.dumps(schema) if schema else "{}"

    @method()
    async def SearchMemory(self, query: 's', limit: 'i') -> 's':
        """Search conversation memory."""
        results = await self.daemon.memory.search(query, limit)
        return json.dumps(results)

    @method()
    def GetConfig(self, section: 's') -> 's':
        """Get configuration section."""
        config = self.daemon.config
        if section and hasattr(config, section):
            section_config = getattr(config, section)
            return json.dumps(section_config.model_dump())
        return json.dumps(config.model_dump())

    @method()
    def SetConfig(self, section: 's', key: 's', value: 's') -> 's':
        """Set a configuration value."""
        try:
            self.daemon.set_config(section, key, value)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # ============ Signals ============

    @signal()
    def TaskProgress(self, task_id: 's', stage: 's', message: 's') -> '':
        """Emitted when task makes progress."""
        pass

    @signal()
    def TaskCompleted(self, task_id: 's', result_json: 's') -> '':
        """Emitted when task completes successfully."""
        pass

    @signal()
    def TaskFailed(self, task_id: 's', error_json: 's') -> '':
        """Emitted when task fails."""
        pass

    @signal()
    def ConfirmationRequired(self, task_id: 's', plan_json: 's') -> '':
        """Emitted when user confirmation is required."""
        pass

    @signal()
    def ContextChanged(self, context_json: 's') -> '':
        """Emitted when system context changes."""
        pass

    @signal()
    def ToolExecutionStarted(self, tool_name: 's', params_json: 's') -> '':
        """Emitted when a tool starts executing."""
        pass

    @signal()
    def ToolExecutionCompleted(self, tool_name: 's', result_json: 's') -> '':
        """Emitted when a tool completes execution."""
        pass

    # ============ Properties ============

    @dbus_property()
    def Version(self) -> 's':
        """EmberOS version."""
        from emberos import __version__
        return __version__

    @dbus_property()
    def IsConnected(self) -> 'b':
        """Whether LLM server is connected."""
        return self.daemon.llm.is_connected

    @dbus_property()
    def ModelName(self) -> 's':
        """Current model name."""
        return self.daemon.llm.model_name or "Unknown"

    @dbus_property()
    def ActiveTaskCount(self) -> 'i':
        """Number of active tasks."""
        return self.daemon.active_task_count


class EmberDBusServer:
    """
    D-Bus server manager for EmberOS daemon.

    Handles connection to session bus and interface registration.
    """

    def __init__(self, daemon: Any):
        self.daemon = daemon
        self.bus: Optional[MessageBus] = None
        self.interface: Optional[EmberAgentInterface] = None
        self._running = False

    async def start(self) -> None:
        """Start the D-Bus server."""
        logger.info("Starting D-Bus server...")

        try:
            # Connect to session bus
            self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

            # Create and export interface
            self.interface = EmberAgentInterface(self.daemon)
            self.bus.export(DBUS_PATH, self.interface)

            # Request name
            await self.bus.request_name(DBUS_NAME)

            self._running = True
            logger.info(f"D-Bus server started: {DBUS_NAME} at {DBUS_PATH}")

        except Exception as e:
            logger.error(f"Failed to start D-Bus server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the D-Bus server."""
        logger.info("Stopping D-Bus server...")
        self._running = False

        if self.bus:
            self.bus.disconnect()
            self.bus = None

    def emit_context_changed(self, context: ContextSnapshot) -> None:
        """Emit context changed signal."""
        if self.interface:
            self.interface.ContextChanged(json.dumps(asdict(context)))

    def emit_tool_started(self, tool_name: str, params: dict) -> None:
        """Emit tool execution started signal."""
        if self.interface:
            self.interface.ToolExecutionStarted(tool_name, json.dumps(params))

    def emit_tool_completed(self, tool_name: str, result: Any) -> None:
        """Emit tool execution completed signal."""
        if self.interface:
            self.interface.ToolExecutionCompleted(tool_name, json.dumps(result))

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

