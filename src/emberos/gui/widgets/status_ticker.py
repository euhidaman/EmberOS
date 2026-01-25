"""
Status Ticker Widget for EmberOS GUI.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from emberos.core.constants import EMBER_ORANGE


class StatusIndicator(QLabel):
    """
    Colored status indicator dot.
    """

    def __init__(self, color: str = EMBER_ORANGE):
        super().__init__("●")
        self._color = color
        self._update_style()

    def _update_style(self) -> None:
        """Update the indicator style."""
        self.setStyleSheet(f"color: {self._color}; font-size: 10px;")

    def set_color(self, color: str) -> None:
        """Set the indicator color."""
        self._color = color
        self._update_style()

    def set_connected(self) -> None:
        """Set to connected state (green)."""
        self.set_color(EMBER_ORANGE)

    def set_reconnecting(self) -> None:
        """Set to reconnecting state (yellow)."""
        self.set_color("#ffc107")

    def set_disconnected(self) -> None:
        """Set to disconnected state (red)."""
        self.set_color("#f44336")


class StatusTicker(QFrame):
    """
    Status ticker showing connection status, model info, and resource usage.
    """

    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the status ticker UI."""
        self.setObjectName("statusTicker")
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QFrame#statusTicker {
                background-color: rgba(20, 20, 28, 0.95);
                border-top: 1px solid rgba(255, 107, 53, 0.1);
            }
            QLabel {
                color: #808090;
                font-size: 11px;
                background: transparent;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(16)

        # Connection status
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)

        self.connection_label = QLabel("Connecting...")
        layout.addWidget(self.connection_label)

        # Separator
        layout.addWidget(self._create_separator())

        # Model name
        self.model_label = QLabel("—")
        layout.addWidget(self.model_label)

        # Separator
        layout.addWidget(self._create_separator())

        # Memory usage
        self.memory_label = QLabel("🧠 —")
        layout.addWidget(self.memory_label)

        # CPU usage
        self.cpu_label = QLabel("💻 —")
        layout.addWidget(self.cpu_label)

        layout.addStretch()

        # Task count
        self.tasks_label = QLabel("📊 0 tasks")
        layout.addWidget(self.tasks_label)

    def _create_separator(self) -> QLabel:
        """Create a separator label."""
        sep = QLabel("·")
        sep.setStyleSheet("color: #505060;")
        return sep

    def update_status(
        self,
        connected: bool = None,
        model_name: str = None,
        memory_gb: float = None,
        cpu_percent: float = None,
        task_count: int = None
    ) -> None:
        """Update the status ticker."""
        if connected is not None:
            if connected:
                self.status_indicator.set_connected()
                self.connection_label.setText("Connected")
            else:
                self.status_indicator.set_disconnected()
                self.connection_label.setText("Disconnected")

        if model_name is not None:
            self.model_label.setText(model_name)

        if memory_gb is not None:
            self.memory_label.setText(f"🧠 {memory_gb:.1f}GB")

        if cpu_percent is not None:
            self.cpu_label.setText(f"💻 {cpu_percent:.0f}%")

        if task_count is not None:
            if task_count == 0:
                self.tasks_label.setText("📊 No tasks")
            elif task_count == 1:
                self.tasks_label.setText("📊 1 task")
            else:
                self.tasks_label.setText(f"📊 {task_count} tasks")

    def set_reconnecting(self) -> None:
        """Set to reconnecting state."""
        self.status_indicator.set_reconnecting()
        self.connection_label.setText("Reconnecting...")

    def update_connection_status(self, connected: bool) -> None:
        """Update just the connection status."""
        self.update_status(connected=connected)
