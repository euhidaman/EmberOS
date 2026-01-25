"""
Task Execution Manager with Rollback Support for EmberOS.

Handles task execution with:
- State snapshots before operations
- Interrupt/cancel support
- Rollback to previous states
- Transaction-like behavior
"""

from __future__ import annotations

import asyncio
import logging
import json
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class StateSnapshot:
    """Snapshot of system state before an operation."""
    snapshot_id: str
    timestamp: datetime
    operation_type: str  # move, delete, write, etc.
    affected_paths: list[str] = field(default_factory=list)
    backup_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> StateSnapshot:
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class TaskExecution:
    """Represents a task execution with rollback capability."""
    task_id: str
    user_message: str
    plan: Any
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    snapshots: list[StateSnapshot] = field(default_factory=list)
    completed_steps: list[int] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    error: Optional[str] = None
    can_rollback: bool = True
    interrupt_requested: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["start_time"] = self.start_time.isoformat() if self.start_time else None
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        data["snapshots"] = [s.to_dict() for s in self.snapshots]
        return data


class TaskExecutionManager:
    """
    Manages task execution with rollback support.

    Features:
    - Creates state snapshots before destructive operations
    - Supports task interruption
    - Can rollback to any snapshot point
    - Maintains execution history
    """

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._active_tasks: dict[str, TaskExecution] = {}
        self._task_history: dict[str, TaskExecution] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def create_task(self, task_id: str, user_message: str, plan: Any) -> TaskExecution:
        """Create a new task execution."""
        task = TaskExecution(
            task_id=task_id,
            user_message=user_message,
            plan=plan,
            start_time=datetime.now()
        )

        self._active_tasks[task_id] = task
        self._cancel_events[task_id] = asyncio.Event()

        return task

    async def create_snapshot(
        self,
        task_id: str,
        operation_type: str,
        affected_paths: list[str],
        metadata: Optional[dict] = None
    ) -> Optional[StateSnapshot]:
        """
        Create a snapshot before a destructive operation.

        Args:
            task_id: Task identifier
            operation_type: Type of operation (move, delete, write, etc.)
            affected_paths: Paths that will be affected
            metadata: Additional metadata

        Returns:
            StateSnapshot if successful, None otherwise
        """
        task = self._active_tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None

        snapshot_id = f"{task_id}_{len(task.snapshots)}"
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            affected_paths=affected_paths,
            metadata=metadata or {}
        )

        # Backup affected files/directories
        backup_data = {}
        for path_str in affected_paths:
            path = Path(path_str).expanduser().resolve()

            if not path.exists():
                continue

            try:
                # Create backup path
                backup_path = self.backup_dir / snapshot_id / path.name

                if path.is_file():
                    # Backup file
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, backup_path)
                    backup_data[str(path)] = {
                        "type": "file",
                        "backup": str(backup_path),
                        "size": path.stat().st_size,
                        "mtime": path.stat().st_mtime
                    }

                elif path.is_dir():
                    # Backup directory (full copy)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(path, backup_path, dirs_exist_ok=True)
                    backup_data[str(path)] = {
                        "type": "directory",
                        "backup": str(backup_path)
                    }

            except Exception as e:
                logger.error(f"Failed to backup {path}: {e}")
                # Continue with other paths

        snapshot.backup_data = backup_data

        # Save snapshot metadata
        snapshot_meta_path = self.backup_dir / f"{snapshot_id}.json"
        with open(snapshot_meta_path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        task.snapshots.append(snapshot)
        logger.info(f"Created snapshot {snapshot_id} for task {task_id}")

        return snapshot

    async def rollback_to_snapshot(
        self,
        task_id: str,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """
        Rollback to a specific snapshot or the last one.

        Args:
            task_id: Task identifier
            snapshot_id: Specific snapshot to rollback to, or None for last

        Returns:
            True if rollback successful
        """
        task = self._active_tasks.get(task_id) or self._task_history.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False

        if not task.snapshots:
            logger.warning(f"No snapshots available for task {task_id}")
            return False

        # Find snapshot to rollback to
        snapshot = None
        snapshot_index = -1

        if snapshot_id:
            for i, s in enumerate(task.snapshots):
                if s.snapshot_id == snapshot_id:
                    snapshot = s
                    snapshot_index = i
                    break
        else:
            # Use last snapshot
            snapshot = task.snapshots[-1]
            snapshot_index = len(task.snapshots) - 1

        if not snapshot:
            logger.error(f"Snapshot {snapshot_id} not found")
            return False

        logger.info(f"Rolling back task {task_id} to snapshot {snapshot.snapshot_id}")

        # Restore backed up files
        try:
            for original_path, backup_info in snapshot.backup_data.items():
                original = Path(original_path)
                backup = Path(backup_info["backup"])

                if not backup.exists():
                    logger.warning(f"Backup not found: {backup}")
                    continue

                # Remove current file/dir if exists
                if original.exists():
                    if original.is_dir():
                        shutil.rmtree(original)
                    else:
                        original.unlink()

                # Restore from backup
                if backup_info["type"] == "file":
                    original.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, original)
                elif backup_info["type"] == "directory":
                    shutil.copytree(backup, original, dirs_exist_ok=True)

                logger.info(f"Restored {original_path}")

            # Remove snapshots after this one
            task.snapshots = task.snapshots[:snapshot_index + 1]
            task.status = TaskStatus.ROLLED_BACK

            logger.info(f"Successfully rolled back task {task_id}")
            return True

        except Exception as e:
            logger.exception(f"Error during rollback: {e}")
            return False

    def request_interrupt(self, task_id: str) -> bool:
        """Request task interruption."""
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            task.interrupt_requested = True
            self._cancel_events[task_id].set()
            logger.info(f"Interrupt requested for task {task_id}")
            return True
        return False

    def is_interrupted(self, task_id: str) -> bool:
        """Check if task has been interrupted."""
        task = self._active_tasks.get(task_id)
        return task.interrupt_requested if task else False

    async def wait_or_interrupt(self, task_id: str, delay: float = 0.1) -> bool:
        """
        Wait briefly and check if interrupted.

        Returns:
            True if should continue, False if interrupted
        """
        if task_id not in self._cancel_events:
            return True

        try:
            await asyncio.wait_for(
                self._cancel_events[task_id].wait(),
                timeout=delay
            )
            return False  # Interrupted
        except asyncio.TimeoutError:
            return True  # Not interrupted, continue

    def mark_step_complete(self, task_id: str, step_index: int, result: Any) -> None:
        """Mark a step as completed."""
        task = self._active_tasks.get(task_id)
        if task:
            task.completed_steps.append(step_index)
            task.results.append(result)

    def complete_task(self, task_id: str) -> None:
        """Mark task as completed."""
        task = self._active_tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            self._task_history[task_id] = task
            del self._active_tasks[task_id]
            if task_id in self._cancel_events:
                del self._cancel_events[task_id]

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        task = self._active_tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            task.end_time = datetime.now()
            self._task_history[task_id] = task
            del self._active_tasks[task_id]
            if task_id in self._cancel_events:
                del self._cancel_events[task_id]

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task."""
        task = self._active_tasks.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            task.end_time = datetime.now()
            self._task_history[task_id] = task
            del self._active_tasks[task_id]
            if task_id in self._cancel_events:
                del self._cancel_events[task_id]

    def get_task(self, task_id: str) -> Optional[TaskExecution]:
        """Get task by ID."""
        return self._active_tasks.get(task_id) or self._task_history.get(task_id)

    def get_active_tasks(self) -> list[TaskExecution]:
        """Get all active tasks."""
        return list(self._active_tasks.values())

    def get_task_history(self, limit: int = 50) -> list[TaskExecution]:
        """Get task history."""
        tasks = sorted(
            self._task_history.values(),
            key=lambda t: t.start_time or datetime.min,
            reverse=True
        )
        return tasks[:limit]

    def cleanup_old_backups(self, days: int = 7) -> None:
        """Clean up backups older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 86400)

        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                if backup_dir.stat().st_mtime < cutoff:
                    try:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Cleaned up old backup: {backup_dir}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {backup_dir}: {e}")

