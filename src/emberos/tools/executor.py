"""
Tool Executor for EmberOS.

Handles sandboxed execution of tools with resource limits.
"""

from __future__ import annotations

import asyncio
import logging
import resource
import signal
import sys
from typing import Any, Optional
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from emberos.tools.base import BaseTool, ToolResult, ToolManifest

logger = logging.getLogger(__name__)


class ExecutionContext:
    """Context for tool execution."""

    def __init__(
        self,
        timeout: int = 60,
        max_memory_mb: int = 512,
        max_cpu_time: int = 60
    ):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @property
    def duration_ms(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return 0


class ToolExecutor:
    """
    Executes tools with sandboxing and resource limits.

    Features:
    - Timeout enforcement
    - Memory limits (Linux only)
    - CPU time limits (Linux only)
    - Graceful cancellation
    """

    def __init__(
        self,
        default_timeout: int = 60,
        max_memory_mb: int = 512,
        max_concurrent: int = 5
    ):
        self.default_timeout = default_timeout
        self.max_memory_mb = max_memory_mb
        self.max_concurrent = max_concurrent

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._process_pool: Optional[ProcessPoolExecutor] = None

    async def start(self) -> None:
        """Start the executor."""
        self._process_pool = ProcessPoolExecutor(max_workers=self.max_concurrent)

    async def stop(self) -> None:
        """Stop the executor and cancel all tasks."""
        # Cancel active tasks
        for task_id, task in self._active_tasks.items():
            task.cancel()

        self._active_tasks.clear()

        # Shutdown process pool
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
            self._process_pool = None

    async def execute(
        self,
        tool: BaseTool,
        params: dict[str, Any],
        task_id: Optional[str] = None
    ) -> ToolResult:
        """
        Execute a tool with sandboxing.

        Args:
            tool: Tool instance to execute
            params: Execution parameters
            task_id: Optional task identifier for tracking

        Returns:
            ToolResult with execution outcome
        """
        manifest = tool.manifest
        timeout = manifest.timeout or self.default_timeout

        context = ExecutionContext(
            timeout=timeout,
            max_memory_mb=self.max_memory_mb
        )

        async with self._semaphore:
            context.start_time = datetime.now()

            try:
                # Create execution task
                exec_task = asyncio.create_task(tool.execute(params))

                if task_id:
                    self._active_tasks[task_id] = exec_task

                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(exec_task, timeout=timeout)

                    context.end_time = datetime.now()

                    if isinstance(result, ToolResult):
                        result.duration_ms = context.duration_ms
                        return result

                    return ToolResult(
                        success=True,
                        data=result,
                        duration_ms=context.duration_ms
                    )

                except asyncio.TimeoutError:
                    context.end_time = datetime.now()
                    return ToolResult(
                        success=False,
                        error=f"Tool execution timed out after {timeout}s",
                        error_type="TimeoutError",
                        duration_ms=context.duration_ms
                    )

                except asyncio.CancelledError:
                    context.end_time = datetime.now()
                    return ToolResult(
                        success=False,
                        error="Tool execution was cancelled",
                        error_type="CancelledError",
                        duration_ms=context.duration_ms
                    )

            except Exception as e:
                context.end_time = datetime.now()
                logger.exception(f"Tool execution error: {e}")
                return ToolResult(
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=context.duration_ms
                )

            finally:
                if task_id and task_id in self._active_tasks:
                    del self._active_tasks[task_id]

    async def execute_isolated(
        self,
        tool: BaseTool,
        params: dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool in an isolated subprocess.

        Use for untrusted or potentially dangerous tools.
        """
        if not self._process_pool:
            await self.start()

        manifest = tool.manifest
        timeout = manifest.timeout or self.default_timeout

        context = ExecutionContext(timeout=timeout)
        context.start_time = datetime.now()

        try:
            loop = asyncio.get_event_loop()

            # Run in process pool
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._process_pool,
                    partial(_isolated_execute, tool.__class__, params, self.max_memory_mb)
                ),
                timeout=timeout
            )

            context.end_time = datetime.now()

            if isinstance(result, dict):
                return ToolResult(
                    success=result.get("success", False),
                    data=result.get("data"),
                    error=result.get("error"),
                    error_type=result.get("error_type"),
                    duration_ms=context.duration_ms
                )

            return ToolResult(
                success=True,
                data=result,
                duration_ms=context.duration_ms
            )

        except asyncio.TimeoutError:
            context.end_time = datetime.now()
            return ToolResult(
                success=False,
                error=f"Isolated execution timed out after {timeout}s",
                error_type="TimeoutError",
                duration_ms=context.duration_ms
            )
        except Exception as e:
            context.end_time = datetime.now()
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=context.duration_ms
            )

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()
            return True
        return False

    @property
    def active_count(self) -> int:
        """Get number of active executions."""
        return len(self._active_tasks)


def _isolated_execute(tool_class: type, params: dict, max_memory_mb: int) -> dict:
    """
    Execute tool in isolated process.

    This function runs in a separate process for isolation.
    """
    # Set resource limits (Linux only)
    try:
        # Memory limit
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_mb * 1024 * 1024, hard))

        # CPU time limit
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        resource.setrlimit(resource.RLIMIT_CPU, (60, hard))
    except (AttributeError, ValueError):
        # Resource limits not available on this platform
        pass

    try:
        # Create tool instance and execute
        tool = tool_class()

        # Run async in sync context
        import asyncio
        result = asyncio.run(tool.execute(params))

        if isinstance(result, ToolResult):
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "error_type": result.error_type
            }

        return {"success": True, "data": result}

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

