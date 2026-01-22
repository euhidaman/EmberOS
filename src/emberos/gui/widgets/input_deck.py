"""
Input Deck Widget for EmberOS GUI.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QKeyEvent

from emberos.core.constants import EMBER_ORANGE


class AutoGrowTextEdit(QTextEdit):
    """
    Text edit that auto-grows up to a maximum height.
    """

    def __init__(self, max_lines: int = 5):
        super().__init__()

        self.max_lines = max_lines
        self._min_height = 60
        self._max_height = 150

        # Connect to text changed
        self.textChanged.connect(self._adjust_height)

        # Initial setup
        self.setMinimumHeight(self._min_height)
        self.setMaximumHeight(self._max_height)

    def _adjust_height(self) -> None:
        """Adjust height based on content."""
        doc_height = self.document().size().height()
        margins = self.contentsMargins()
        new_height = int(doc_height + margins.top() + margins.bottom() + 10)

        # Clamp to min/max
        new_height = max(self._min_height, min(new_height, self._max_height))

        self.setMinimumHeight(new_height)


class InputDeck(QFrame):
    """
    Input deck with text input, action buttons, and placeholder rotation.
    """

    # Signals
    message_submitted = pyqtSignal(str)
    cancel_clicked = pyqtSignal()
    execute_clicked = pyqtSignal()

    # Placeholder examples
    PLACEHOLDERS = [
        "What would you like to do?",
        "Find my budget spreadsheet...",
        "Organize downloads by type...",
        "Summarize this document...",
        "Search for files containing...",
        "Launch an application...",
    ]

    def __init__(self):
        super().__init__()

        self._placeholder_index = 0
        self._setup_ui()
        self._setup_placeholder_rotation()

    def _setup_ui(self) -> None:
        """Setup the input deck UI."""
        self.setObjectName("inputDeck")
        self.setStyleSheet("""
            QFrame#inputDeck {
                background-color: rgba(30, 30, 42, 0.95);
                border-top: 1px solid rgba(255, 107, 53, 0.2);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row: attachment buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setToolTip("Attach files")
        self.attach_btn.setObjectName("secondaryButton")
        top_row.addWidget(self.attach_btn)

        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(32, 32)
        self.voice_btn.setToolTip("Voice input")
        self.voice_btn.setObjectName("secondaryButton")
        top_row.addWidget(self.voice_btn)

        top_row.addStretch()
        layout.addLayout(top_row)

        # Text input
        self.text_input = AutoGrowTextEdit(max_lines=5)
        self.text_input.setPlaceholderText(self.PLACEHOLDERS[0])
        self.text_input.installEventFilter(self)
        layout.addWidget(self.text_input)

        # Bottom row: action buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self._on_cancel)
        bottom_row.addWidget(self.cancel_btn)

        bottom_row.addStretch()

        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setObjectName("secondaryButton")
        self.execute_btn.clicked.connect(self._on_execute)
        bottom_row.addWidget(self.execute_btn)

        self.send_btn = QPushButton("Send ⚡")
        self.send_btn.clicked.connect(self._on_send)
        bottom_row.addWidget(self.send_btn)

        layout.addLayout(bottom_row)

    def _setup_placeholder_rotation(self) -> None:
        """Setup placeholder text rotation."""
        self._placeholder_timer = QTimer()
        self._placeholder_timer.timeout.connect(self._rotate_placeholder)
        self._placeholder_timer.start(10000)  # Every 10 seconds

    def _rotate_placeholder(self) -> None:
        """Rotate to next placeholder text."""
        if not self.text_input.toPlainText():  # Only if empty
            self._placeholder_index = (self._placeholder_index + 1) % len(self.PLACEHOLDERS)
            self.text_input.setPlaceholderText(self.PLACEHOLDERS[self._placeholder_index])

    def eventFilter(self, obj, event) -> bool:
        """Handle key events in text input."""
        if obj == self.text_input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Return:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Shift+Enter: new line
                    return False
                else:
                    # Enter: submit
                    self._on_send()
                    return True

        return super().eventFilter(obj, event)

    def _on_send(self) -> None:
        """Handle send button click."""
        text = self.text_input.toPlainText().strip()
        if text:
            self.message_submitted.emit(text)
            self.text_input.clear()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.cancel_clicked.emit()

    def _on_execute(self) -> None:
        """Handle execute button click."""
        self.execute_clicked.emit()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable input."""
        self.text_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.execute_btn.setEnabled(enabled)

    def focus_input(self) -> None:
        """Focus the text input."""
        self.text_input.setFocus()

