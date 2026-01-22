"""
Context Monitor for EmberOS.

Monitors system context including active window, clipboard, file selection,
and other relevant state that the agent can use for context-aware responses.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any, Callable, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContextSnapshot:
    """Snapshot of current system context."""
    active_window: str = ""
    active_window_title: str = ""
    active_window_class: str = ""
    selected_files: list[str] = field(default_factory=list)
    clipboard_text: str = ""
    clipboard_type: str = "text"  # text, image, files
    working_directory: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class ContextMonitor:
    """
    Monitors system context for the EmberOS agent.

    Tracks:
    - Active window (name, title, class)
    - Clipboard content
    - Selected files (from file managers)
    - Working directory
    """

    def __init__(self, update_interval: float = 0.5):
        self.update_interval = update_interval
        self._current_context = ContextSnapshot()
        self._callbacks: list[Callable[[ContextSnapshot], None]] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # X11 display for context queries
        self._display = None

    async def start(self) -> None:
        """Start the context monitor."""
        logger.info("Starting context monitor...")

        # Try to initialize X11 connection
        try:
            from Xlib import X, display
            self._display = display.Display()
            logger.info("X11 connection established")
        except ImportError:
            logger.warning("python-xlib not available, using fallback methods")
        except Exception as e:
            logger.warning(f"Could not connect to X11: {e}")

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the context monitor."""
        logger.info("Stopping context monitor...")
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if self._display:
            self._display.close()
            self._display = None

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                new_context = await self._capture_context()

                if self._context_changed(new_context):
                    self._current_context = new_context
                    self._notify_callbacks(new_context)

            except Exception as e:
                logger.error(f"Error in context monitor: {e}")

            await asyncio.sleep(self.update_interval)

    async def _capture_context(self) -> ContextSnapshot:
        """Capture current system context."""
        context = ContextSnapshot()

        # Get active window
        window_info = await self._get_active_window()
        context.active_window = window_info.get("name", "")
        context.active_window_title = window_info.get("title", "")
        context.active_window_class = window_info.get("class", "")

        # Get clipboard
        clipboard_info = await self._get_clipboard()
        context.clipboard_text = clipboard_info.get("text", "")
        context.clipboard_type = clipboard_info.get("type", "text")

        # Get selected files (from file manager)
        context.selected_files = await self._get_selected_files()

        # Get working directory (from active terminal)
        context.working_directory = await self._get_working_directory()

        return context

    async def _get_active_window(self) -> dict:
        """Get information about the active window."""
        try:
            if self._display:
                return self._get_active_window_xlib()
            else:
                return await self._get_active_window_xdotool()
        except Exception as e:
            logger.debug(f"Error getting active window: {e}")
            return {}

    def _get_active_window_xlib(self) -> dict:
        """Get active window using Xlib."""
        from Xlib import X

        try:
            root = self._display.screen().root
            window_id = root.get_full_property(
                self._display.intern_atom('_NET_ACTIVE_WINDOW'),
                X.AnyPropertyType
            )

            if window_id is None:
                return {}

            window = self._display.create_resource_object('window', window_id.value[0])

            # Get window name
            name_prop = window.get_full_property(
                self._display.intern_atom('_NET_WM_NAME'),
                X.AnyPropertyType
            )
            name = name_prop.value.decode() if name_prop else ""

            # Get window class
            class_prop = window.get_wm_class()
            window_class = class_prop[1] if class_prop else ""

            # Get title (may be same as name)
            title_prop = window.get_wm_name()
            title = title_prop if title_prop else name

            return {
                "name": window_class or name,
                "title": title,
                "class": window_class
            }

        except Exception as e:
            logger.debug(f"Xlib error: {e}")
            return {}

    async def _get_active_window_xdotool(self) -> dict:
        """Get active window using xdotool (fallback)."""
        try:
            # Get window ID
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "getactivewindow",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            window_id = stdout.decode().strip()

            if not window_id:
                return {}

            # Get window name
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "getwindowname", window_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            title = stdout.decode().strip()

            # Get window class using xprop
            proc = await asyncio.create_subprocess_exec(
                "xprop", "-id", window_id, "WM_CLASS",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            class_line = stdout.decode().strip()

            window_class = ""
            if "=" in class_line:
                parts = class_line.split("=")[1].strip().split(",")
                if len(parts) >= 2:
                    window_class = parts[1].strip().strip('"')

            return {
                "name": window_class or title.split(" - ")[-1] if title else "",
                "title": title,
                "class": window_class
            }

        except FileNotFoundError:
            logger.debug("xdotool not found")
            return {}
        except Exception as e:
            logger.debug(f"xdotool error: {e}")
            return {}

    async def _get_clipboard(self) -> dict:
        """Get clipboard content."""
        try:
            # Try to get text clipboard
            proc = await asyncio.create_subprocess_exec(
                "xclip", "-selection", "clipboard", "-o",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                text = stdout.decode("utf-8", errors="replace")
                # Limit clipboard text length
                if len(text) > 1000:
                    text = text[:1000] + "..."
                return {"text": text, "type": "text"}

        except FileNotFoundError:
            # Try xsel as fallback
            try:
                proc = await asyncio.create_subprocess_exec(
                    "xsel", "--clipboard", "--output",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()

                if proc.returncode == 0:
                    text = stdout.decode("utf-8", errors="replace")
                    if len(text) > 1000:
                        text = text[:1000] + "..."
                    return {"text": text, "type": "text"}

            except FileNotFoundError:
                pass
        except Exception as e:
            logger.debug(f"Clipboard error: {e}")

        return {"text": "", "type": "unknown"}

    async def _get_selected_files(self) -> list[str]:
        """Get selected files from file manager (if available)."""
        # This is tricky as it depends on the file manager
        # Try Nautilus D-Bus interface
        try:
            proc = await asyncio.create_subprocess_exec(
                "dbus-send", "--session", "--print-reply",
                "--dest=org.gnome.Nautilus",
                "/org/gnome/Nautilus",
                "org.gnome.Nautilus.FileOperations.GetClipboardContents",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            # Parse output for file paths
            # This is a simplified implementation

        except Exception:
            pass

        return []

    async def _get_working_directory(self) -> str:
        """Get working directory of active terminal (if applicable)."""
        try:
            # Get active window PID
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "getactivewindow", "getwindowpid",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            pid = stdout.decode().strip()

            if pid:
                # Get CWD from /proc
                import os
                cwd_link = f"/proc/{pid}/cwd"
                if os.path.exists(cwd_link):
                    return os.readlink(cwd_link)

        except Exception as e:
            logger.debug(f"Error getting working directory: {e}")

        return ""

    def _context_changed(self, new_context: ContextSnapshot) -> bool:
        """Check if context has meaningfully changed."""
        old = self._current_context
        return (
            new_context.active_window != old.active_window or
            new_context.active_window_title != old.active_window_title or
            new_context.clipboard_text != old.clipboard_text or
            new_context.selected_files != old.selected_files
        )

    def _notify_callbacks(self, context: ContextSnapshot) -> None:
        """Notify registered callbacks of context change."""
        for callback in self._callbacks:
            try:
                callback(context)
            except Exception as e:
                logger.error(f"Error in context callback: {e}")

    def register_callback(self, callback: Callable[[ContextSnapshot], None]) -> None:
        """Register a callback for context changes."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[ContextSnapshot], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def get_snapshot(self) -> ContextSnapshot:
        """Get fresh context snapshot."""
        return await self._capture_context()

    def get_snapshot_sync(self) -> ContextSnapshot:
        """Get current cached context snapshot (synchronous)."""
        return self._current_context

    @property
    def current_context(self) -> ContextSnapshot:
        """Get current context."""
        return self._current_context

