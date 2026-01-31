"""
EmberOS Daemon Service.

Main daemon process that coordinates all EmberOS functionality.
Runs as a systemd user service.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import os
from typing import Any, Optional
from pathlib import Path
from datetime import datetime

from emberos.core.config import EmberConfig, ensure_directories
from emberos.core.constants import CACHE_DIR
from emberos.daemon.llm_orchestrator import LLMOrchestrator
from emberos.daemon.planner import AgentPlanner, ExecutionPlan, ToolResult
from emberos.daemon.context_monitor import ContextMonitor

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

logger = logging.getLogger(__name__)


class EmberDaemon:
    """
    Main EmberOS daemon.

    Coordinates:
    - D-Bus server for IPC
    - LLM orchestration
    - Tool execution
    - Memory management
    - Context monitoring
    """

    def __init__(self, config: Optional[EmberConfig] = None):
        self.config = config or EmberConfig.from_env()

        # Core components
        self.dbus_server: Optional[Any] = None
        self.http_server: Optional[Any] = None  # Windows HTTP server
        self.llm: Optional[LLMOrchestrator] = None
        self.planner: Optional[AgentPlanner] = None
        self.context_monitor: Optional[ContextMonitor] = None
        self.tool_registry: Optional[Any] = None  # Will be ToolRegistry
        self.memory: Optional[Any] = None  # Will be MemoryEngine

        # State
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._pending_confirmations: dict[str, ExecutionPlan] = {}
        self._start_time: Optional[datetime] = None

    async def start(self) -> None:
        """Start the daemon and all components."""
        logger.info("Starting EmberOS daemon...")

        ensure_directories()
        self._start_time = datetime.now()

        # Initialize components
        await self._init_components()

        # Start IPC server based on platform
        if IS_WINDOWS:
            # Windows: Use HTTP REST API
            from emberos.daemon.windows_server import WindowsHTTPServer
            self.http_server = WindowsHTTPServer(self)
            await self.http_server.start()

            # Register context change callback (no-op on Windows for now)
            if self.context_monitor:
                self.context_monitor.register_callback(lambda ctx: None)
        else:
            # Linux: Use D-Bus
            from emberos.daemon.dbus_server import EmberDBusServer
            self.dbus_server = EmberDBusServer(self)
            await self.dbus_server.start()

            # Register context change callback
            if self.context_monitor:
                self.context_monitor.register_callback(
                    lambda ctx: self.dbus_server.emit_context_changed(ctx)
                )

        self._running = True
        logger.info("EmberOS daemon started successfully")

        # Write PID file
        self._write_pid_file()

    async def _init_components(self) -> None:
        """Initialize all daemon components."""
        # Initialize LLM orchestrator
        self.llm = LLMOrchestrator(self.config.llm)
        await self.llm.start()

        # Initialize tool registry
        from emberos.tools.registry import ToolRegistry
        self.tool_registry = ToolRegistry()
        await self.tool_registry.load_tools()

        # Initialize memory engine
        from emberos.memory.engine import MemoryEngine
        self.memory = MemoryEngine(self.config.memory)
        await self.memory.start()

        # Initialize planner
        self.planner = AgentPlanner(self.llm, self.tool_registry)

        # Initialize context monitor
        self.context_monitor = ContextMonitor(
            update_interval=self.config.daemon.context_update_interval
        )
        await self.context_monitor.start()

    async def stop(self) -> None:
        """Stop the daemon and all components."""
        logger.info("Stopping EmberOS daemon...")
        self._running = False

        # Cancel all running tasks
        for task_id, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

        # Stop components
        if self.context_monitor:
            await self.context_monitor.stop()

        if self.memory:
            await self.memory.stop()

        if self.llm:
            await self.llm.stop()

        if self.dbus_server:
            await self.dbus_server.stop()

        if self.http_server:
            await self.http_server.stop()

        # Remove PID file
        self._remove_pid_file()

        logger.info("EmberOS daemon stopped")

    def _emit_signal(self, signal_name: str, *args):
        """Emit a signal safely on both Windows and Linux."""
        if self.dbus_server and hasattr(self.dbus_server, f'emit_{signal_name}'):
            getattr(self.dbus_server, f'emit_{signal_name}')(*args)
        # Windows HTTP server doesn't have signals - uses polling instead

    async def execute_plan(self, plan: ExecutionPlan) -> list[ToolResult]:
        """
        Execute an execution plan.

        Args:
            plan: The plan to execute

        Returns:
            List of results from each tool execution
        """
        results = []
        step_results = {}

        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.tool}")

            # Emit tool started signal
            self._emit_signal('tool_started', step.tool, step.args)

            start_time = datetime.now()

            try:
                # Resolve any $result references in args
                resolved_args = self._resolve_args(step.args, step_results)

                # Execute tool
                result = await self.tool_registry.execute(step.tool, resolved_args)

                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # Check if the tool reported a failure in its result
                tool_success = True
                error_msg = None
                if isinstance(result, dict) and result.get("success") is False:
                    tool_success = False
                    error_msg = result.get("error")

                tool_result = ToolResult(
                    tool=step.tool,
                    success=tool_success,
                    result=result,
                    error=error_msg,
                    duration_ms=duration_ms
                )

                step_results[i] = result
                results.append(tool_result)

                # Emit tool completed signal
                self._emit_signal('tool_completed', step.tool, {
                    "success": tool_success,
                    "result": result,
                    "error": error_msg,
                    "duration_ms": duration_ms
                })

            except Exception as e:
                logger.exception(f"Error executing tool {step.tool}: {e}")
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                tool_result = ToolResult(
                    tool=step.tool,
                    success=False,
                    result=None,
                    error=str(e),
                    duration_ms=duration_ms
                )
                results.append(tool_result)

                # Emit tool completed signal with error
                self._emit_signal('tool_completed', step.tool, {
                    "success": False,
                    "error": str(e),
                    "duration_ms": duration_ms
                })

                # Decide whether to continue or abort
                # For now, continue with remaining steps

        return results

    def _resolve_args(self, args: dict, step_results: dict) -> dict:
        """Resolve $result references in arguments."""
        resolved = {}

        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$result["):
                # Extract index
                import re
                match = re.match(r'\$result\[(\d+)\](?:\.(.+))?', value)
                if match:
                    idx = int(match.group(1))
                    path = match.group(2)

                    if idx in step_results:
                        result = step_results[idx]
                        if path:
                            # Navigate nested path
                            for part in path.split('.'):
                                if isinstance(result, dict):
                                    result = result.get(part)
                                elif hasattr(result, part):
                                    result = getattr(result, part)
                        resolved[key] = result
                    else:
                        resolved[key] = value
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_args(value, step_results)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_args({"v": v}, step_results)["v"]
                    if isinstance(v, (dict, str)) else v
                    for v in value
                ]
            else:
                resolved[key] = value

        return resolved

    async def resume_confirmed_task(self, task_id: str) -> None:
        """Resume a task after user confirmation."""
        if task_id in self._pending_confirmations:
            plan = self._pending_confirmations.pop(task_id)
            asyncio.create_task(self._execute_confirmed_plan(task_id, plan))

    async def _execute_confirmed_plan(self, task_id: str, plan: ExecutionPlan) -> None:
        """Execute a confirmed plan."""
        try:
            results = await self.execute_plan(plan)

            # Synthesize response
            response = await self.planner.synthesize_response(
                "",  # Original message not stored
                plan,
                results
            )

            # Emit task completed signal
            if self.dbus_server and hasattr(self.dbus_server, 'interface'):
                self.dbus_server.interface.TaskCompleted(task_id, {
                    "success": True,
                    "response": response,
                    "results": [r.to_dict() for r in results]
                })

        except Exception as e:
            # Emit task failed signal
            if self.dbus_server and hasattr(self.dbus_server, 'interface'):
                self.dbus_server.interface.TaskFailed(task_id, {
                    "error": str(e)
                })

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a running or pending task."""
        # Remove from pending confirmations
        if task_id in self._pending_confirmations:
            del self._pending_confirmations[task_id]

        # Cancel running task
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            del self._tasks[task_id]

    def get_status(self) -> dict:
        """Get daemon status."""
        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "llm_connected": self.llm.is_connected if self.llm else False,
            "model_name": self.llm.model_name if self.llm else None,
            "active_tasks": len(self._tasks),
            "pending_confirmations": len(self._pending_confirmations),
            "tools_loaded": self.tool_registry.tool_count if self.tool_registry else 0,
            "dbus_running": self.dbus_server.is_running if self.dbus_server else False,
        }

    def set_config(self, section: str, key: str, value: str) -> None:
        """Set a configuration value."""
        if hasattr(self.config, section):
            section_obj = getattr(self.config, section)
            if hasattr(section_obj, key):
                # Convert value to appropriate type
                field_info = section_obj.model_fields.get(key)
                if field_info:
                    field_type = field_info.annotation
                    if field_type == float:
                        value = float(value)
                    elif field_type == int:
                        value = int(value)
                    elif field_type == bool:
                        value = value.lower() in ("true", "1", "yes")
                setattr(section_obj, key, value)

                # Save config
                self.config.save()

    @property
    def active_task_count(self) -> int:
        """Get number of active tasks."""
        return len(self._tasks)

    def _write_pid_file(self) -> None:
        """Write PID file."""
        pid_path = Path(self.config.daemon.pid_file)
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()))

    def _remove_pid_file(self) -> None:
        """Remove PID file."""
        pid_path = Path(self.config.daemon.pid_file)
        if pid_path.exists():
            pid_path.unlink()


async def run_daemon() -> None:
    """Run the EmberOS daemon."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(CACHE_DIR / "logs" / "emberd.log")
        ]
    )

    daemon = EmberDaemon()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await daemon.start()

        # Keep running
        while daemon._running:
            await asyncio.sleep(1)

    except Exception as e:
        logger.exception(f"Daemon error: {e}")
    finally:
        await daemon.stop()


def main() -> None:
    """Main entry point for emberd."""
    ensure_directories()
    asyncio.run(run_daemon())


if __name__ == "__main__":
    main()

