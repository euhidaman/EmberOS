"""
Complete Workflow Orchestrator for EmberOS.

Implements the full workflow:
1. Context gathering
2. Planning with LLM
3. Permission checking
4. User confirmation for risky operations
5. Execution with rollback support
6. Result synthesis
7. Memory storage
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from emberos.daemon.planner import AgentPlanner, ExecutionPlan, ToolResult
from emberos.daemon.task_manager import TaskExecutionManager, TaskStatus
from emberos.daemon.context_monitor import ContextMonitor
from emberos.tools.registry import ToolRegistry
from emberos.memory.engine import MemoryEngine

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates complete task workflows from user input to execution.

    Workflow steps:
    1. USER INPUT → Context Gatherer
    2. CONTEXT + INPUT → LLM (Planning)
    3. PLAN → Permission Checker
    4. If risky → User Confirmation
    5. EXECUTE with snapshots
    6. RESULTS → LLM (Synthesis)
    7. RESPONSE + RESULTS → Memory
    """

    def __init__(
        self,
        planner: AgentPlanner,
        tool_registry: ToolRegistry,
        context_monitor: ContextMonitor,
        memory_engine: MemoryEngine,
        task_manager: TaskExecutionManager
    ):
        self.planner = planner
        self.tool_registry = tool_registry
        self.context_monitor = context_monitor
        self.memory = memory_engine
        self.task_manager = task_manager

        # Callbacks for UI updates
        self._on_status_update: Optional[Callable] = None
        self._on_confirmation_needed: Optional[Callable] = None
        self._on_tool_progress: Optional[Callable] = None

    def set_status_callback(self, callback: Callable) -> None:
        """Set callback for status updates."""
        self._on_status_update = callback

    def set_confirmation_callback(self, callback: Callable) -> None:
        """Set callback for confirmation requests."""
        self._on_confirmation_needed = callback

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for tool progress updates."""
        self._on_tool_progress = callback

    async def process_request(
        self,
        user_message: str,
        attached_files: Optional[list[str]] = None,
        task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Process a complete user request through the workflow.

        Args:
            user_message: Natural language request from user
            attached_files: Optional list of file paths
            task_id: Optional task ID (generated if not provided)

        Returns:
            Dict with response, results, and metadata
        """
        task_id = task_id or str(uuid.uuid4())

        logger.info(f"Processing request (task {task_id}): {user_message[:100]}")

        # Step 1: Gather Context
        self._emit_status(task_id, "Gathering context...")
        context = await self._gather_context(attached_files)

        # Step 2: Create Execution Plan
        self._emit_status(task_id, "Planning actions...")
        plan = await self.planner.create_plan(user_message, context)

        if not plan.steps:
            # No tools needed, direct LLM response
            response = await self.planner.synthesize_response(
                user_message, plan, []
            )
            return {
                "task_id": task_id,
                "response": response,
                "plan": plan.to_dict(),
                "results": [],
                "status": "completed"
            }

        # Create task execution
        task = self.task_manager.create_task(task_id, user_message, plan)

        # Step 3: Permission Checking & Confirmation
        if plan.requires_confirmation:
            self._emit_status(task_id, "Awaiting user confirmation...")

            # Request confirmation from UI
            if self._on_confirmation_needed:
                await self._on_confirmation_needed(task_id, {
                    "message": plan.confirmation_message or "Proceed with this action?",
                    "plan": plan.to_dict(),
                    "risk_level": plan.risk_level
                })

            # Return early, execution will resume on confirm_task()
            return {
                "task_id": task_id,
                "status": "awaiting_confirmation",
                "plan": plan.to_dict()
            }

        # Step 4: Execute Plan
        return await self._execute_task(task_id, task, plan, user_message, context)

    async def confirm_task(self, task_id: str) -> dict[str, Any]:
        """
        Confirm and execute a task that required confirmation.

        Args:
            task_id: Task identifier

        Returns:
            Execution results
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return {
                "task_id": task_id,
                "error": "Task not found",
                "status": "error"
            }

        return await self._execute_task(
            task_id,
            task,
            task.plan,
            task.user_message,
            await self._gather_context()
        )

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running or pending task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully
        """
        self.task_manager.request_interrupt(task_id)
        self.task_manager.cancel_task(task_id)
        self._emit_status(task_id, "Task cancelled")
        return True

    async def rollback_task(
        self,
        task_id: str,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """
        Rollback a task to a previous state.

        Args:
            task_id: Task identifier
            snapshot_id: Specific snapshot to rollback to (or last if None)

        Returns:
            True if rollback successful
        """
        self._emit_status(task_id, "Rolling back...")

        success = await self.task_manager.rollback_to_snapshot(task_id, snapshot_id)

        if success:
            self._emit_status(task_id, "Rollback completed")
        else:
            self._emit_status(task_id, "Rollback failed")

        return success

    async def _gather_context(
        self,
        attached_files: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Gather current system context.

        Returns context including:
        - Active window/application
        - Current directory
        - Clipboard contents
        - Recent memory
        - Attached files (if any)
        """
        context = {}

        # Get system context from monitor
        sys_context = self.context_monitor.get_context()
        if sys_context:
            context.update({
                "active_window": sys_context.get("active_window"),
                "current_directory": sys_context.get("cwd"),
                "clipboard": sys_context.get("clipboard"),
            })

        # Get recent conversations from memory
        recent_convs = await self.memory.get_recent_conversations(limit=5)
        if recent_convs:
            context["recent_context"] = [
                {
                    "user": c.get("user_message", ""),
                    "agent": c.get("agent_response", "")[:200]  # Truncate
                }
                for c in recent_convs
            ]

        # Add attached files
        if attached_files:
            context["attached_files"] = []
            for file_path in attached_files:
                path = Path(file_path)
                if path.exists():
                    context["attached_files"].append({
                        "path": str(path),
                        "name": path.name,
                        "size": path.stat().st_size,
                        "type": path.suffix
                    })

        return context

    async def _execute_task(
        self,
        task_id: str,
        task: Any,
        plan: ExecutionPlan,
        user_message: str,
        context: dict
    ) -> dict[str, Any]:
        """Execute a task with full workflow."""
        self._emit_status(task_id, "Executing...")

        results = []
        step_results = {}

        try:
            # Execute each step in the plan
            for i, step in enumerate(plan.steps):
                # Check for interruption
                if self.task_manager.is_interrupted(task_id):
                    logger.info(f"Task {task_id} interrupted at step {i}")
                    self.task_manager.cancel_task(task_id)
                    return {
                        "task_id": task_id,
                        "status": "cancelled",
                        "completed_steps": i,
                        "results": results
                    }

                # Create snapshot before destructive operations
                destructive_ops = ["delete", "move", "write"]
                if any(op in step.tool for op in destructive_ops):
                    affected_paths = self._extract_affected_paths(step.args)
                    await self.task_manager.create_snapshot(
                        task_id,
                        step.tool,
                        affected_paths,
                        {"step_index": i, "step_description": step.description}
                    )

                # Emit progress
                self._emit_progress(
                    task_id,
                    step.tool,
                    i + 1,
                    len(plan.steps),
                    f"Executing {step.tool}..."
                )

                # Resolve any $result references in args
                resolved_args = self._resolve_args(step.args, step_results)

                # Execute tool
                start_time = datetime.now()

                try:
                    result = await self.tool_registry.execute(step.tool, resolved_args)

                    duration_ms = int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    )

                    tool_result = ToolResult(
                        tool=step.tool,
                        success=True,
                        result=result,
                        duration_ms=duration_ms
                    )

                    step_results[i] = result
                    results.append(tool_result)

                    self.task_manager.mark_step_complete(task_id, i, tool_result)

                except Exception as e:
                    logger.exception(f"Error executing {step.tool}: {e}")

                    duration_ms = int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    )

                    tool_result = ToolResult(
                        tool=step.tool,
                        success=False,
                        result=None,
                        error=str(e),
                        duration_ms=duration_ms
                    )
                    results.append(tool_result)

                    # Decide whether to continue or abort
                    # For now, continue with remaining steps

            # Step 5: Synthesize Response
            self._emit_status(task_id, "Generating response...")
            response = await self.planner.synthesize_response(
                user_message, plan, results
            )

            # Step 6: Store in Memory
            await self.memory.store_conversation(
                user_message=user_message,
                agent_response=response,
                plan=plan,
                results=results,
                context=context,
                success=all(r.success for r in results)
            )

            # Mark task complete
            self.task_manager.complete_task(task_id)

            return {
                "task_id": task_id,
                "response": response,
                "plan": plan.to_dict(),
                "results": [r.to_dict() for r in results],
                "status": "completed",
                "snapshots": [s.to_dict() for s in task.snapshots]
            }

        except Exception as e:
            logger.exception(f"Error in task execution: {e}")

            self.task_manager.fail_task(task_id, str(e))

            return {
                "task_id": task_id,
                "error": str(e),
                "status": "failed",
                "completed_steps": len(results),
                "results": [r.to_dict() for r in results]
            }

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

    def _extract_affected_paths(self, args: dict) -> list[str]:
        """Extract file paths that will be affected by an operation."""
        paths = []

        # Common parameter names for paths
        path_keys = ["path", "source", "destination", "file", "directory"]

        for key, value in args.items():
            if key in path_keys and isinstance(value, str):
                paths.append(value)
            elif isinstance(value, list):
                # Handle lists of paths
                paths.extend([str(v) for v in value if isinstance(v, str)])

        return paths

    def _emit_status(self, task_id: str, status: str) -> None:
        """Emit status update to UI."""
        if self._on_status_update:
            try:
                asyncio.create_task(
                    self._on_status_update(task_id, {"status": status})
                )
            except Exception as e:
                logger.error(f"Error emitting status: {e}")

    def _emit_progress(
        self,
        task_id: str,
        tool: str,
        step: int,
        total: int,
        message: str
    ) -> None:
        """Emit progress update to UI."""
        if self._on_tool_progress:
            try:
                asyncio.create_task(
                    self._on_tool_progress(task_id, {
                        "tool": tool,
                        "step": step,
                        "total": total,
                        "message": message,
                        "progress": step / total
                    })
                )
            except Exception as e:
                logger.error(f"Error emitting progress: {e}")

