"""
Tool Card Widget for EmberOS GUI.

Displays tool execution status with expandable details.
"""

from __future__ import annotations

from typing import Optional, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont

from emberos.core.constants import EMBER_ORANGE


class ToolCard(QFrame):
    """
    Card showing tool execution status.

    States:
    - Running: Pulsing orange border, animated progress
    - Success: Green border, checkmark
    - Error: Red border, error details
    """

    # Signals
    rerun_clicked = pyqtSignal(str)  # tool_name
    copy_clicked = pyqtSignal(str)   # result

    def __init__(
        self,
        tool_name: str,
        params: Optional[dict] = None,
        icon: str = "🔧"
    ):
        super().__init__()

        self.tool_name = tool_name
        self.params = params or {}
        self.icon = icon
        self._expanded = False
        self._state = "running"
        self._result = None
        self._error = None
        self._duration_ms = 0

        self._collapsed_height = 64
        self._expanded_height = 180

        self._setup_ui()
        self._set_state("running")

    def _setup_ui(self) -> None:
        """Setup the tool card UI."""
        self.setObjectName("toolCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self._collapsed_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        # Icon and name
        self.icon_label = QLabel(self.icon)
        self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        header.addWidget(self.icon_label)

        self.name_label = QLabel(self.tool_name)
        self.name_label.setStyleSheet("font-weight: 600; background: transparent;")
        header.addWidget(self.name_label)

        header.addStretch()

        # Status text
        self.status_label = QLabel("Running...")
        self.status_label.setStyleSheet("color: #a0a0b0; background: transparent;")
        header.addWidget(self.status_label)

        # Duration
        self.duration_label = QLabel("")
        self.duration_label.setStyleSheet("color: #808090; background: transparent;")
        header.addWidget(self.duration_label)

        main_layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.progress_bar.setFixedHeight(4)
        main_layout.addWidget(self.progress_bar)

        # Expanded content (initially hidden)
        self.details_widget = QWidget()
        self.details_widget.setVisible(False)
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.setSpacing(4)

        # Parameters
        self.params_label = QLabel("Parameters:")
        self.params_label.setStyleSheet("color: #a0a0b0; font-size: 11px; background: transparent;")
        details_layout.addWidget(self.params_label)

        self.params_content = QLabel(self._format_params())
        self.params_content.setStyleSheet("color: #808090; font-size: 11px; background: transparent; margin-left: 8px;")
        self.params_content.setWordWrap(True)
        details_layout.addWidget(self.params_content)

        # Result/Error
        self.result_label = QLabel("Result:")
        self.result_label.setStyleSheet("color: #a0a0b0; font-size: 11px; background: transparent;")
        details_layout.addWidget(self.result_label)

        self.result_content = QLabel("—")
        self.result_content.setStyleSheet("color: #f0f0fa; font-size: 11px; background: transparent; margin-left: 8px;")
        self.result_content.setWordWrap(True)
        details_layout.addWidget(self.result_content)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.rerun_btn = QPushButton("↻ Rerun")
        self.rerun_btn.setObjectName("secondaryButton")
        self.rerun_btn.setFixedHeight(28)
        self.rerun_btn.clicked.connect(lambda: self.rerun_clicked.emit(self.tool_name))
        btn_layout.addWidget(self.rerun_btn)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setObjectName("secondaryButton")
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.clicked.connect(self._copy_result)
        btn_layout.addWidget(self.copy_btn)

        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)

        main_layout.addWidget(self.details_widget)

    def _format_params(self) -> str:
        """Format parameters for display."""
        if not self.params:
            return "(none)"

        lines = []
        for key, value in self.params.items():
            val_str = str(value)
            if len(val_str) > 50:
                val_str = val_str[:50] + "..."
            lines.append(f"{key}: {val_str}")

        return "\n".join(lines)

    def _set_state(self, state: str) -> None:
        """Set the card state."""
        self._state = state

        if state == "running":
            self.setStyleSheet(f"""
                QFrame#toolCard {{
                    background-color: rgba(36, 36, 48, 0.9);
                    border: 1px solid {EMBER_ORANGE};
                    border-radius: 8px;
                }}
            """)
            self.status_label.setText("Running...")
            self.progress_bar.setMaximum(0)
            self.progress_bar.show()

        elif state == "success":
            self.setStyleSheet("""
                QFrame#toolCard {
                    background-color: rgba(36, 36, 48, 0.9);
                    border: 1px solid #4caf50;
                    border-radius: 8px;
                }
            """)
            self.status_label.setText("✓ Complete")
            self.status_label.setStyleSheet("color: #4caf50; background: transparent;")
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(100)
            self.progress_bar.hide()

        elif state == "error":
            self.setStyleSheet("""
                QFrame#toolCard {
                    background-color: rgba(36, 36, 48, 0.9);
                    border: 1px solid #f44336;
                    border-radius: 8px;
                }
            """)
            self.status_label.setText("✗ Error")
            self.status_label.setStyleSheet("color: #f44336; background: transparent;")
            self.progress_bar.hide()

    def mousePressEvent(self, event) -> None:
        """Toggle expansion on click."""
        self._toggle_expanded()

    def _toggle_expanded(self) -> None:
        """Toggle expanded state."""
        self._expanded = not self._expanded

        # Animate height
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if self._expanded:
            anim.setStartValue(self._collapsed_height)
            anim.setEndValue(self._expanded_height)
            self.details_widget.setVisible(True)
        else:
            anim.setStartValue(self._expanded_height)
            anim.setEndValue(self._collapsed_height)

        anim.finished.connect(lambda: self.details_widget.setVisible(self._expanded))
        anim.start()

        self._height_anim = anim

    def set_result(self, result: Any, duration_ms: int = 0) -> None:
        """Set successful result."""
        self._result = result
        self._duration_ms = duration_ms

        self._set_state("success")
        self.duration_label.setText(f"⏱️ {duration_ms/1000:.1f}s")

        # Format result
        result_str = str(result)
        if len(result_str) > 200:
            result_str = result_str[:200] + "..."
        self.result_content.setText(result_str)
        self.result_label.setText("Result:")

    def set_error(self, error: str, duration_ms: int = 0) -> None:
        """Set error result."""
        self._error = error
        self._duration_ms = duration_ms

        self._set_state("error")
        self.duration_label.setText(f"⏱️ {duration_ms/1000:.1f}s")

        self.result_content.setText(error)
        self.result_content.setStyleSheet("color: #f44336; font-size: 11px; background: transparent; margin-left: 8px;")
        self.result_label.setText("Error:")

    def _copy_result(self) -> None:
        """Copy result to clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if self._result:
            clipboard.setText(str(self._result))
        elif self._error:
            clipboard.setText(self._error)

        self.copy_clicked.emit(str(self._result or self._error))

