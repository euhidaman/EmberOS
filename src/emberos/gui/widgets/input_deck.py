"""
Input Deck Widget for EmberOS GUI.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFrame, QSizePolicy, QFileDialog
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
    file_attached = pyqtSignal(list)  # Emits list of file paths
    interrupt_requested = pyqtSignal()  # Interrupt current task
    rollback_requested = pyqtSignal()  # Rollback to previous state

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
        self._attached_files = []  # Track attached files
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

        # Top row: attachment button and file indicator
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.attach_btn = QPushButton("📎 Attach Files")
        self.attach_btn.setFixedHeight(32)
        self.attach_btn.setMinimumWidth(120)
        self.attach_btn.setToolTip("Attach files for analysis (images, documents, etc.)")
        self.attach_btn.setObjectName("secondaryButton")
        self.attach_btn.clicked.connect(self._on_attach_files)
        top_row.addWidget(self.attach_btn)

        # Label showing attached files count
        self.attached_label = QLabel("")
        self.attached_label.setStyleSheet("color: #ff6b35; font-size: 10px;")
        self.attached_label.setVisible(False)
        top_row.addWidget(self.attached_label)

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

        # Left side: control buttons
        self.interrupt_btn = QPushButton("⏸ Interrupt")
        self.interrupt_btn.setObjectName("warningButton")
        self.interrupt_btn.setToolTip("Stop the current task")
        self.interrupt_btn.clicked.connect(self._on_interrupt)
        self.interrupt_btn.setEnabled(False)  # Disabled until task is running
        bottom_row.addWidget(self.interrupt_btn)

        self.rollback_btn = QPushButton("↩ Rollback")
        self.rollback_btn.setObjectName("warningButton")
        self.rollback_btn.setToolTip("Undo the last operation")
        self.rollback_btn.clicked.connect(self._on_rollback)
        self.rollback_btn.setEnabled(False)  # Disabled until rollback is available
        bottom_row.addWidget(self.rollback_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self._on_cancel)
        bottom_row.addWidget(self.cancel_btn)

        bottom_row.addStretch()

        # Right side: execution buttons
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

            # Emit attached files if any
            if self._attached_files:
                self.file_attached.emit(self._attached_files)
                self._clear_attachments()

    def _on_attach_files(self) -> None:
        """Handle attach files button click."""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Attach Files")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # Allow multiple files

        # Set file filters for common types
        file_dialog.setNameFilter(
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;"
            "Documents (*.pdf *.doc *.docx *.txt *.md *.odt);;"
            "Spreadsheets (*.xls *.xlsx *.csv *.ods);;"
            "Code (*.py *.js *.java *.cpp *.c *.h *.rs *.go);;"
            "Archives (*.zip *.tar *.gz *.bz2 *.7z)"
        )

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self._attached_files.extend(selected_files)
                self._update_attachment_display()

    def _update_attachment_display(self) -> None:
        """Update the attachment count label."""
        if self._attached_files:
            count = len(self._attached_files)
            self.attached_label.setText(f"{count} file{'s' if count > 1 else ''} attached")
            self.attached_label.setVisible(True)
            self.attach_btn.setText("📎 Add More")
        else:
            self.attached_label.setVisible(False)
            self.attach_btn.setText("📎 Attach Files")

    def _clear_attachments(self) -> None:
        """Clear all attached files."""
        self._attached_files.clear()
        self._update_attachment_display()

    def get_attached_files(self) -> list[str]:
        """Get list of currently attached files."""
        return self._attached_files.copy()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.cancel_clicked.emit()

    def _on_execute(self) -> None:
        """Handle execute button click."""
        self.execute_clicked.emit()

    def _on_interrupt(self) -> None:
        """Handle interrupt button click."""
        self.interrupt_requested.emit()

    def _on_rollback(self) -> None:
        """Handle rollback button click."""
        self.rollback_requested.emit()

    def set_task_running(self, running: bool) -> None:
        """Update UI based on task running state."""
        self.interrupt_btn.setEnabled(running)
        self.send_btn.setEnabled(not running)
        self.execute_btn.setEnabled(not running)

    def set_rollback_available(self, available: bool) -> None:
        """Update rollback button availability."""
        self.rollback_btn.setEnabled(available)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable input."""
        self.text_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.execute_btn.setEnabled(enabled)

    def focus_input(self) -> None:
        """Focus the text input."""
        self.text_input.setFocus()

