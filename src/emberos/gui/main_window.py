"""
EmberOS Main Window.
"""

from __future__ import annotations

import asyncio
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
        self._client = None

        # Window setup
        self._setup_window()
        self._setup_tray()
        self._create_ui()
        self._connect_signals()

        # Start background tasks
        self._start_background_tasks()

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

        # Process command asynchronously using QTimer
        # This avoids the "no running event loop" error
        QTimer.singleShot(0, lambda: self._schedule_command(message))

    def _schedule_command(self, message: str) -> None:
        """Schedule command processing."""
        # Get the event loop from the application
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create task
        task = loop.create_task(self._process_command(message))

        # Store task reference to prevent garbage collection
        if not hasattr(self, '_pending_tasks'):
            self._pending_tasks = set()
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _process_command(self, message: str) -> None:
        """Process a command through the daemon."""
        try:
            # TODO: Connect to daemon client
            # For now, simulate response
            await asyncio.sleep(1)

            self.chat_widget.hide_typing_indicator()
            self.chat_widget.add_agent_message(
                f"I received your message: \"{message}\"\n\n"
                "The daemon connection is not yet implemented in the GUI."
            )

        except Exception as e:
            self.chat_widget.hide_typing_indicator()
            self.chat_widget.add_agent_message(
                f"Error processing command: {e}",
                is_error=True
            )

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        # TODO: Cancel current task
        pass

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


