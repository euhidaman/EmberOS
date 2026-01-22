"""
System tools for EmberOS.
"""

from __future__ import annotations

import asyncio
import subprocess
import os
import platform
from typing import Any, Optional
from datetime import datetime

import psutil

from emberos.tools.base import (
    BaseTool, ToolResult, ToolManifest, ToolParameter,
    ToolCategory, RiskLevel
)
from emberos.tools.registry import register_tool


@register_tool
class SystemStatusTool(BaseTool):
    """Get system status and resource usage."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.status",
            description="Get system status including CPU, memory, disk usage",
            category=ToolCategory.SYSTEM,
            icon="📊",
            parameters=[],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk info
            disk = psutil.disk_usage('/')

            # Network info
            net_io = psutil.net_io_counters()

            # System info
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            return ToolResult(
                success=True,
                data={
                    "system": {
                        "platform": platform.system(),
                        "release": platform.release(),
                        "hostname": platform.node(),
                        "uptime_hours": round(uptime.total_seconds() / 3600, 1),
                        "boot_time": boot_time.isoformat()
                    },
                    "cpu": {
                        "percent": cpu_percent,
                        "cores": cpu_count,
                        "frequency_mhz": cpu_freq.current if cpu_freq else None
                    },
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 1),
                        "used_gb": round(memory.used / (1024**3), 1),
                        "available_gb": round(memory.available / (1024**3), 1),
                        "percent": memory.percent
                    },
                    "swap": {
                        "total_gb": round(swap.total / (1024**3), 1),
                        "used_gb": round(swap.used / (1024**3), 1),
                        "percent": swap.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 1),
                        "used_gb": round(disk.used / (1024**3), 1),
                        "free_gb": round(disk.free / (1024**3), 1),
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 1),
                        "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 1)
                    }
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class SystemCommandTool(BaseTool):
    """Execute a system command."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.command",
            description="Execute a shell command",
            category=ToolCategory.SYSTEM,
            icon="💻",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command to execute",
                    required=True
                ),
                ToolParameter(
                    name="timeout",
                    type="int",
                    description="Timeout in seconds",
                    required=False,
                    default=30
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory",
                    required=False
                )
            ],
            permissions=["system:execute"],
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="Execute command: {command}?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        command = params["command"]
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")

        if cwd:
            cwd = os.path.expanduser(cwd)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout}s"
                )

            return ToolResult(
                success=proc.returncode == 0,
                data={
                    "command": command,
                    "return_code": proc.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace')
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class SystemServiceTool(BaseTool):
    """Manage systemd services."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.service",
            description="Manage systemd services",
            category=ToolCategory.SYSTEM,
            icon="⚙️",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="Service name",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: status, start, stop, restart, enable, disable",
                    required=True,
                    choices=["status", "start", "stop", "restart", "enable", "disable"]
                ),
                ToolParameter(
                    name="user",
                    type="bool",
                    description="User service (--user flag)",
                    required=False,
                    default=False
                )
            ],
            permissions=["system:execute"],
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="{action} service {name}?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        name = params["name"]
        action = params["action"]
        user = params.get("user", False)

        try:
            cmd = ["systemctl"]
            if user:
                cmd.append("--user")
            cmd.extend([action, name])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            output = stdout.decode() if stdout else stderr.decode()

            return ToolResult(
                success=proc.returncode == 0,
                data={
                    "service": name,
                    "action": action,
                    "output": output,
                    "return_code": proc.returncode
                }
            )

        except FileNotFoundError:
            return ToolResult(success=False, error="systemctl not found")
        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class SystemPackageTool(BaseTool):
    """Manage Arch Linux packages with pacman."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.package",
            description="Manage packages with pacman",
            category=ToolCategory.SYSTEM,
            icon="📦",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: search, info, list, install, remove",
                    required=True,
                    choices=["search", "info", "list", "install", "remove"]
                ),
                ToolParameter(
                    name="package",
                    type="string",
                    description="Package name",
                    required=False
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=False
                )
            ],
            permissions=["system:execute"],
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="{action} package(s)?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        action = params["action"]
        package = params.get("package")
        query = params.get("query")

        try:
            if action == "search":
                cmd = ["pacman", "-Ss", query or package or ""]
            elif action == "info":
                if not package:
                    return ToolResult(success=False, error="Package name required")
                cmd = ["pacman", "-Si", package]
            elif action == "list":
                cmd = ["pacman", "-Q"]
            elif action == "install":
                if not package:
                    return ToolResult(success=False, error="Package name required")
                cmd = ["sudo", "pacman", "-S", "--noconfirm", package]
            elif action == "remove":
                if not package:
                    return ToolResult(success=False, error="Package name required")
                cmd = ["sudo", "pacman", "-R", "--noconfirm", package]
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            output = stdout.decode() if stdout else ""
            error_output = stderr.decode() if stderr else ""

            return ToolResult(
                success=proc.returncode == 0,
                data={
                    "action": action,
                    "package": package,
                    "output": output,
                    "error": error_output if proc.returncode != 0 else None
                }
            )

        except FileNotFoundError:
            return ToolResult(success=False, error="pacman not found")
        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class SystemNotifyTool(BaseTool):
    """Send desktop notification."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.notify",
            description="Send a desktop notification",
            category=ToolCategory.SYSTEM,
            icon="🔔",
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Notification title",
                    required=True
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Notification message",
                    required=True
                ),
                ToolParameter(
                    name="urgency",
                    type="string",
                    description="Urgency level",
                    required=False,
                    default="normal",
                    choices=["low", "normal", "critical"]
                ),
                ToolParameter(
                    name="icon",
                    type="string",
                    description="Icon name or path",
                    required=False
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        title = params["title"]
        message = params["message"]
        urgency = params.get("urgency", "normal")
        icon = params.get("icon")

        try:
            cmd = ["notify-send", "-u", urgency]
            if icon:
                cmd.extend(["-i", icon])
            cmd.extend([title, message])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                return ToolResult(
                    success=False,
                    error=stderr.decode() if stderr else "Failed to send notification"
                )

            return ToolResult(
                success=True,
                data={
                    "title": title,
                    "message": message,
                    "urgency": urgency
                }
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="notify-send not found. Install with: sudo pacman -S libnotify"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class SystemClipboardTool(BaseTool):
    """Interact with system clipboard."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="system.clipboard",
            description="Read or write to system clipboard",
            category=ToolCategory.SYSTEM,
            icon="📋",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: read or write",
                    required=True,
                    choices=["read", "write"]
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (for write action)",
                    required=False
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        action = params["action"]
        content = params.get("content")

        try:
            if action == "read":
                proc = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard", "-o",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()

                return ToolResult(
                    success=True,
                    data={"content": stdout.decode('utf-8', errors='replace')}
                )

            elif action == "write":
                if not content:
                    return ToolResult(success=False, error="Content required for write")

                proc = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard",
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate(content.encode('utf-8'))

                return ToolResult(
                    success=True,
                    data={"written": True, "length": len(content)}
                )

            return ToolResult(success=False, error=f"Unknown action: {action}")

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="xclip not found. Install with: sudo pacman -S xclip"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

