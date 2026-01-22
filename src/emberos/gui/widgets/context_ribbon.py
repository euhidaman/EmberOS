"""
Context Ribbon Widget for EmberOS GUI.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont

from emberos.core.constants import EMBER_ORANGE


class ContextRibbon(QFrame):
    """
    Collapsible context ribbon showing current system context.

    Displays:
    - Selected files count
    - Active window
    - Clipboard preview
    - Current time
    """

    def __init__(self):
        super().__init__()

        self._expanded = False
        self._collapsed_height = 8
        self._expanded_height = 48

        self._setup_ui()

        # Start collapsed
        self.setFixedHeight(self._collapsed_height)

    def _setup_ui(self) -> None:
        """Setup the context ribbon UI."""
        self.setObjectName("contextRibbon")
        self.setStyleSheet(f"""
            QFrame#contextRibbon {{
                background-color: rgba(36, 36, 48, 0.8);
                border-bottom: 1px solid rgba(255, 107, 53, 0.15);
            }}
            QLabel {{
                color: #a0a0b0;
                background: transparent;
            }}
        """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Content layout
        self.content_layout = QHBoxLayout(self)
        self.content_layout.setContentsMargins(16, 8, 16, 8)
        self.content_layout.setSpacing(24)

        # File selection indicator
        self.files_label = QLabel("📁 No files selected")
        self.content_layout.addWidget(self.files_label)

        # Active window indicator
        self.window_label = QLabel("🪟 —")
        self.content_layout.addWidget(self.window_label)

        # Clipboard indicator
        self.clipboard_label = QLabel("📋 —")
        self.clipboard_label.setMaximumWidth(200)
        self.content_layout.addWidget(self.clipboard_label)

        self.content_layout.addStretch()

        # Time
        self.time_label = QLabel("🕐 —")
        self.content_layout.addWidget(self.time_label)

    def mousePressEvent(self, event) -> None:
        """Toggle expansion on click."""
        self.toggle_expanded()

    def toggle_expanded(self) -> None:
        """Toggle between expanded and collapsed states."""
        self._expanded = not self._expanded

        # Animate height change
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if self._expanded:
            anim.setStartValue(self._collapsed_height)
            anim.setEndValue(self._expanded_height)
        else:
            anim.setStartValue(self._expanded_height)
            anim.setEndValue(self._collapsed_height)

        anim.start()

        # Keep reference
        self._height_anim = anim

    def update_context(
        self,
        selected_files: list[str] = None,
        active_window: str = None,
        clipboard_text: str = None,
        current_time: str = None
    ) -> None:
        """Update the context display."""
        if selected_files is not None:
            count = len(selected_files)
            if count == 0:
                self.files_label.setText("📁 No files selected")
            elif count == 1:
                self.files_label.setText(f"📁 1 file selected")
            else:
                self.files_label.setText(f"📁 {count} files selected")

        if active_window is not None:
            if active_window:
                # Truncate long names
                display_name = active_window[:30] + "..." if len(active_window) > 30 else active_window
                self.window_label.setText(f"🪟 {display_name}")
            else:
                self.window_label.setText("🪟 —")

        if clipboard_text is not None:
            if clipboard_text:
                # Truncate and clean
                preview = clipboard_text[:30].replace("\n", " ")
                if len(clipboard_text) > 30:
                    preview += "..."
                self.clipboard_label.setText(f'📋 "{preview}"')
            else:
                self.clipboard_label.setText("📋 —")

        if current_time is not None:
            self.time_label.setText(f"🕐 {current_time}")

    @property
    def is_expanded(self) -> bool:
        """Check if ribbon is expanded."""
        return self._expanded

