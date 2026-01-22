"""
Application tools for EmberOS.
"""

from __future__ import annotations

import asyncio
import subprocess
import shutil
from typing import Any, Optional
from datetime import datetime

import psutil

from emberos.tools.base import (
    BaseTool, ToolResult, ToolManifest, ToolParameter,
    ToolCategory, RiskLevel
)
from emberos.tools.registry import register_tool


@register_tool
class AppLaunchTool(BaseTool):
    """Launch an application."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="applications.launch",
            description="Launch an application by name",
            category=ToolCategory.APPLICATIONS,
            icon="🚀",
            parameters=[
                ToolParameter(
                    name="app",
                    type="string",
                    description="Application name or command",
                    required=True
                ),
                ToolParameter(
                    name="args",
                    type="list",
                    description="Command line arguments",
                    required=False,
                    default=[]
                ),
                ToolParameter(
                    name="detach",
                    type="bool",
                    description="Run in background",
                    required=False,
                    default=True
                )
            ],
            permissions=["system:execute"],
            risk_level=RiskLevel.MEDIUM
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        app = params["app"]
        args = params.get("args", [])
        detach = params.get("detach", True)

        try:
            # Find executable
            executable = shutil.which(app)
            if not executable:
                # Try common paths
                common_paths = [
                    f"/usr/bin/{app}",
                    f"/usr/local/bin/{app}",
                    f"/opt/{app}/{app}",
                ]
                for path in common_paths:
                    if shutil.which(path):
                        executable = path
                        break

            if not executable:
                return ToolResult(
                    success=False,
                    error=f"Application not found: {app}"
                )

            # Launch process
            cmd = [executable] + list(args)

            if detach:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                pid = process.pid
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                pid = process.pid

            return ToolResult(
                success=True,
                data={
                    "app": app,
                    "executable": executable,
                    "pid": pid,
                    "detached": detach
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class AppListTool(BaseTool):
    """List running applications."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="applications.list",
            description="List running applications and processes",
            category=ToolCategory.APPLICATIONS,
            icon="📋",
            parameters=[
                ToolParameter(
                    name="filter",
                    type="string",
                    description="Filter by name",
                    required=False
                ),
                ToolParameter(
                    name="sort_by",
                    type="string",
                    description="Sort by: 'name', 'cpu', 'memory', 'pid'",
                    required=False,
                    default="memory",
                    choices=["name", "cpu", "memory", "pid"]
                ),
                ToolParameter(
                    name="limit",
                    type="int",
                    description="Maximum results",
                    required=False,
                    default=20
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        name_filter = params.get("filter", "").lower()
        sort_by = params.get("sort_by", "memory")
        limit = params.get("limit", 20)

        try:
            apps = []

            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'num_threads', 'username']):
                try:
                    info = proc.info
                    name = info['name']

                    if name_filter and name_filter not in name.lower():
                        continue

                    memory_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0

                    apps.append({
                        "pid": info['pid'],
                        "name": name,
                        "cpu_percent": info['cpu_percent'] or 0,
                        "memory_mb": round(memory_mb, 1),
                        "threads": info['num_threads'] or 0,
                        "user": info['username']
                    })

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort
            sort_keys = {
                "name": lambda x: x["name"].lower(),
                "cpu": lambda x: -x["cpu_percent"],
                "memory": lambda x: -x["memory_mb"],
                "pid": lambda x: x["pid"]
            }
            apps.sort(key=sort_keys.get(sort_by, sort_keys["memory"]))

            # Limit
            apps = apps[:limit]

            # Calculate totals
            total_cpu = sum(a["cpu_percent"] for a in apps)
            total_memory = sum(a["memory_mb"] for a in apps)

            return ToolResult(
                success=True,
                data={
                    "apps": apps,
                    "count": len(apps),
                    "total_cpu_percent": round(total_cpu, 1),
                    "total_memory_mb": round(total_memory, 1)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class AppCloseTool(BaseTool):
    """Close an application."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="applications.close",
            description="Close an application by name or PID",
            category=ToolCategory.APPLICATIONS,
            icon="❌",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="Application name",
                    required=False
                ),
                ToolParameter(
                    name="pid",
                    type="int",
                    description="Process ID",
                    required=False
                ),
                ToolParameter(
                    name="force",
                    type="bool",
                    description="Force kill (SIGKILL)",
                    required=False,
                    default=False
                )
            ],
            permissions=["system:execute"],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Close application?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name")
        pid = params.get("pid")
        force = params.get("force", False)

        if not name and not pid:
            return ToolResult(success=False, error="Must specify 'name' or 'pid'")

        try:
            closed = []

            if pid:
                # Close by PID
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()

                    if force:
                        proc.kill()
                    else:
                        proc.terminate()

                    closed.append({"pid": pid, "name": proc_name})

                except psutil.NoSuchProcess:
                    return ToolResult(success=False, error=f"Process not found: {pid}")

            elif name:
                # Close by name
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if name.lower() in proc.info['name'].lower():
                            if force:
                                proc.kill()
                            else:
                                proc.terminate()

                            closed.append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name']
                            })

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if not closed:
                return ToolResult(
                    success=False,
                    error=f"No matching processes found"
                )

            return ToolResult(
                success=True,
                data={
                    "closed": closed,
                    "count": len(closed),
                    "forced": force
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class AppFocusTool(BaseTool):
    """Focus an application window."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="applications.focus",
            description="Focus an application window",
            category=ToolCategory.APPLICATIONS,
            icon="🎯",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="Application or window name",
                    required=True
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        name = params["name"]

        try:
            # Use wmctrl to find and focus window
            proc = await asyncio.create_subprocess_exec(
                "wmctrl", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            windows = stdout.decode().strip().split('\n')

            for window in windows:
                if name.lower() in window.lower():
                    parts = window.split()
                    if parts:
                        window_id = parts[0]

                        # Focus the window
                        await asyncio.create_subprocess_exec(
                            "wmctrl", "-i", "-a", window_id,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )

                        return ToolResult(
                            success=True,
                            data={
                                "window_id": window_id,
                                "window_title": " ".join(parts[4:]) if len(parts) > 4 else ""
                            }
                        )

            return ToolResult(
                success=False,
                error=f"Window not found: {name}"
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="wmctrl not installed. Install with: sudo pacman -S wmctrl"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

