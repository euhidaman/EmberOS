"""
EmberOS Main Window.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QColor, QFont, QAction, QCloseEvent

from emberos.core.config import EmberConfig, GUIConfig
from emberos.core.constants import EMBER_ORANGE, APP_NAME
from emberos.gui.widgets.chat import ChatWidget
from emberos.gui.widgets.input_deck import InputDeck
from emberos.gui.widgets.context_ribbon import ContextRibbon
from emberos.gui.widgets.status_ticker import StatusTicker
from emberos.gui.widgets.title_bar import TitleBar

# Platform-aware client import
import sys
if sys.platform == 'win32':
    from emberos.cli.windows_client import WindowsEmberClient as EmberClient
else:
    from emberos.cli.client import EmberClient

logger = logging.getLogger(__name__)


class EmberMainWindow(QMainWindow):
    """
    Main window for EmberOS GUI.

    Features:
    - Custom frameless window with glassmorphism
    - Chat interface with message bubbles
    - Context ribbon showing system state
    - Input deck with multiline support
    - Status ticker with live updates
    """

    # Signals
    command_submitted = pyqtSignal(str)

    def __init__(self, config: EmberConfig):
        super().__init__()

        self.config = config
        self.gui_config = config.gui
        self._client = EmberClient()
        self._connected = False

        # Window setup
        self._setup_window()
        self._setup_tray()
        self._create_ui()
        self._connect_signals()

        # Start background tasks
        self._start_background_tasks()

        # Connect to daemon
        self._connect_to_daemon()

    def _setup_window(self) -> None:
        """Setup window properties."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(600, 500)
        self.resize(
            self.gui_config.window_width,
            self.gui_config.window_height
        )

        # Enable translucency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set window flags for frameless window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )

        # Set window opacity
        self.setWindowOpacity(self.gui_config.opacity)

        # Always on top if configured
        if self.gui_config.always_on_top:
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

        # Enable mouse tracking for the window
        self.setMouseTracking(True)

    def _setup_tray(self) -> None:
        """Setup system tray icon."""
        if not self.gui_config.show_in_tray:
            return

        self.tray_icon = QSystemTrayIcon(self)
        # TODO: Set actual icon
        # self.tray_icon.setIcon(QIcon(":/icons/ember.png"))

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_ui(self) -> None:
        """Create the UI layout."""
        # Main container with glassmorphism effect
        self.container = QFrame()
        self.container.setObjectName("mainContainer")
        self.container.setStyleSheet("""
            QFrame#mainContainer {
                background-color: rgba(26, 26, 36, 0.95);
                border: 1px solid rgba(255, 107, 53, 0.2);
                border-radius: 12px;
            }
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        # Main layout
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Context ribbon (collapsible)
        self.context_ribbon = ContextRibbon()
        main_layout.addWidget(self.context_ribbon)

        # Chat area
        self.chat_widget = ChatWidget()
        main_layout.addWidget(self.chat_widget, 1)  # Stretch

        # Input deck
        self.input_deck = InputDeck()
        main_layout.addWidget(self.input_deck)

        # Status ticker
        self.status_ticker = StatusTicker()
        main_layout.addWidget(self.status_ticker)

        # Set central widget
        self.setCentralWidget(self.container)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Title bar
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.theme_toggle_clicked.connect(self._on_theme_toggle)

        # Input deck
        self.input_deck.message_submitted.connect(self._on_message_submitted)
        self.input_deck.cancel_clicked.connect(self._on_cancel_clicked)
        self.input_deck.interrupt_requested.connect(self._on_interrupt_requested)
        self.input_deck.rollback_requested.connect(self._on_rollback_requested)

        # Initialize theme button state
        app = QApplication.instance()
        if hasattr(app, 'current_theme'):
            self.title_bar.update_theme_button(app.current_theme)

    def _start_background_tasks(self) -> None:
        """Start background update tasks."""
        # Status update timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(2000)  # Every 2 seconds

        # Context update timer
        self._context_timer = QTimer()
        self._context_timer.timeout.connect(self._update_context)
        self._context_timer.start(500)  # Every 500ms

    def _toggle_maximize(self) -> None:
        """Toggle maximized state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def _on_message_submitted(self, message: str) -> None:
        """Handle submitted message."""
        # Add user message to chat
        self.chat_widget.add_user_message(message)

        # Show typing indicator
        self.chat_widget.show_typing_indicator()

        # Process command using thread to avoid blocking GUI
        import threading
        thread = threading.Thread(target=self._run_command_in_thread, args=(message,))
        thread.daemon = True
        thread.start()

    def _run_command_in_thread(self, message: str) -> None:
        """Run command processing in a separate thread."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._process_command(message))
        finally:
            loop.close()

        # Use QTimer to update GUI from main thread
        QTimer.singleShot(0, lambda: self._handle_command_result(result))


    async def _process_command(self, message: str) -> dict:
        """Process a command through the daemon. Returns result dict."""
        try:
            if not self._connected:
                return {
                    "success": False,
                    "error_type": "not_connected",
                    "response": (
                        "⚠️ Not connected to EmberOS daemon.\n\n"
                        "Please ensure the daemon is running:\n"
                        "  systemctl --user status emberd\n\n"
                        "Try restarting it:\n"
                        "  systemctl --user restart emberd"
                    )
                }

            # Send command to daemon - now returns full result
            result = await self._client.process_command(message)
            self._current_task_id = result.get("task_id")

            return result

        except ConnectionError as e:
            return {
                "success": False,
                "error_type": "connection_error",
                "response": (
                    f"❌ Connection Error: {e}\n\n"
                    "The daemon may not be running. Check with:\n"
                    "  systemctl --user status emberd"
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error_type": "error",
                "response": f"❌ Error processing command: {e}"
            }

    def _handle_command_result(self, result: dict) -> None:
        """Handle command result in main GUI thread."""
        self.chat_widget.hide_typing_indicator()
        self.input_deck.set_task_running(False)

        if not result:
            self.chat_widget.add_agent_message("❌ No response received", is_error=True)
            return

        response = result.get("response", "Task completed.")
        is_error = not result.get("success", True) or result.get("error_type")

        # Check if confirmation is required
        if result.get("status") == "awaiting_confirmation":
            confirmation_msg = result.get("plan", {}).get("confirmation_message", "Proceed with this action?")
            risk_level = result.get("plan", {}).get("risk_level", "medium")
            self.chat_widget.add_agent_message(
                f"⚠️ **Confirmation Required** (Risk: {risk_level})\n\n"
                f"{confirmation_msg}\n\n"
                "This action requires your confirmation."
            )
            return

        self.chat_widget.add_agent_message(response, is_error=is_error)

        # Update rollback availability
        if result.get("snapshots"):
            self.input_deck.set_rollback_available(True)


    def _connect_to_daemon(self) -> None:
        """Connect to the daemon asynchronously using a thread."""
        import threading
        thread = threading.Thread(target=self._connect_daemon_thread)
        thread.daemon = True
        thread.start()

    def _connect_daemon_thread(self) -> None:
        """Run daemon connection in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_daemon_async())
        finally:
            loop.close()

    async def _connect_daemon_async(self) -> None:
        """Async daemon connection."""
        try:
            self._connected = await self._client.connect()

            if self._connected:
                # Use QTimer to update GUI from main thread
                QTimer.singleShot(0, lambda: self.status_ticker.update_connection_status(True))
                # Setup callbacks for daemon events
                self._client.on("progress", self._on_task_progress)
                self._client.on("completed", self._on_task_completed)
                self._client.on("failed", self._on_task_failed)
            else:
                QTimer.singleShot(0, lambda: self.status_ticker.update_connection_status(False))

        except Exception as e:
            self._connected = False
            QTimer.singleShot(0, lambda: self.status_ticker.update_connection_status(False))
            logger.error(f"Failed to connect to daemon: {e}")

    def _on_task_progress(self, update) -> None:
        """Handle task progress updates."""
        message = update.data.get("message", "Processing...")
        # Use thread-safe way to update GUI
        QTimer.singleShot(0, lambda: self.chat_widget.add_system_message(f"⚙️ {message}"))

    def _on_task_completed(self, update) -> None:
        """Handle task completion - store result for polling."""
        task_id = update.task_id
        if not hasattr(self, '_task_results'):
            self._task_results = {}

        self._task_results[task_id] = {
            "success": True,
            "response": update.data.get("response", "Task completed."),
            "plan": update.data.get("plan"),
            "results": update.data.get("results"),
            "snapshots": update.data.get("snapshots"),
            "status": "completed"
        }

    def _on_task_failed(self, update) -> None:
        """Handle task failure - store result for polling."""
        task_id = update.task_id
        if not hasattr(self, '_task_results'):
            self._task_results = {}

        self._task_results[task_id] = {
            "success": False,
            "error_type": update.data.get("error_type", "error"),
            "response": f"❌ Task failed: {update.data.get('error', 'Unknown error')}",
            "status": "failed"
        }

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        # TODO: Cancel current task
        pass

    def _on_interrupt_requested(self) -> None:
        """Handle interrupt button click."""
        if self._connected and hasattr(self, '_current_task_id'):
            QTimer.singleShot(0, lambda: self._schedule_interrupt())
        else:
            self.chat_widget.add_system_message("⚠️ No active task to interrupt")

    def _schedule_interrupt(self) -> None:
        """Schedule task interruption."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        task = loop.create_task(self._interrupt_task_async())
        if not hasattr(self, '_pending_tasks'):
            self._pending_tasks = set()
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _interrupt_task_async(self) -> None:
        """Async task interruption."""
        try:
            if hasattr(self, '_current_task_id'):
                await self._client.cancel_task(self._current_task_id)
                self.chat_widget.add_system_message("⏸ Task interrupted")
                self.input_deck.set_task_running(False)
        except Exception as e:
            self.chat_widget.add_agent_message(f"❌ Failed to interrupt task: {e}", is_error=True)

    def _on_rollback_requested(self) -> None:
        """Handle rollback button click."""
        if self._connected and hasattr(self, '_current_task_id'):
            QTimer.singleShot(0, lambda: self._schedule_rollback())
        else:
            self.chat_widget.add_system_message("⚠️ No snapshots available for rollback")

    def _schedule_rollback(self) -> None:
        """Schedule rollback operation."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        task = loop.create_task(self._rollback_task_async())
        if not hasattr(self, '_pending_tasks'):
            self._pending_tasks = set()
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _rollback_task_async(self) -> None:
        """Async rollback operation."""
        try:
            # TODO: Implement rollback via daemon API once available
            # For now, show a message
            self.chat_widget.add_system_message(
                "↩ Rollback requested\n"
                "Note: Rollback API integration pending in daemon"
            )
            self.input_deck.set_rollback_available(False)
        except Exception as e:
            self.chat_widget.add_agent_message(f"❌ Failed to rollback: {e}", is_error=True)

    def _on_theme_toggle(self) -> None:
        """Handle theme toggle button click."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if hasattr(app, 'toggle_theme'):
            app.toggle_theme()

    def on_theme_changed(self, theme: str) -> None:
        """Called when application theme changes."""
        # Update title bar theme button
        self.title_bar.update_theme_button(theme)

        # Update container stylesheet
        if theme == "dark":
            container_bg = "rgba(26, 26, 36, 0.95)"
            border_color = "rgba(255, 107, 53, 0.2)"
        else:
            container_bg = "rgba(245, 245, 250, 0.95)"
            border_color = "rgba(255, 107, 53, 0.3)"

        self.container.setStyleSheet(f"""
            QFrame#mainContainer {{
                background-color: {container_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)

    def _update_status(self) -> None:
        """Update status ticker."""
        # TODO: Get real status from daemon
        self.status_ticker.update_status(
            connected=True,
            model_name="Qwen2.5-VL-7B",
            memory_gb=4.2,
            cpu_percent=12,
            task_count=0
        )

    def _update_context(self) -> None:
        """Update context ribbon."""
        # TODO: Get real context from daemon
        pass

    # ============ Window Events ============

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close."""
        if self.gui_config.show_in_tray:
            # Hide to tray instead of closing
            event.ignore()
            self.hide()
        else:
            event.accept()


