"""
Chat Widget for EmberOS GUI.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient

from emberos.core.constants import EMBER_ORANGE, EMBER_ORANGE_LIGHT


class MessageBubble(QFrame):
    """
    Chat message bubble with styling based on sender.
    """

    def __init__(
        self,
        message: str,
        is_user: bool = False,
        is_error: bool = False,
        timestamp: Optional[datetime] = None
    ):
        super().__init__()

        self.is_user = is_user
        self.is_error = is_error
        self._message = message
        self.timestamp = timestamp or datetime.now()

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Setup the bubble UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # Message text
        self.message_label = QLabel(self._message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.message_label.setOpenExternalLinks(True)
        layout.addWidget(self.message_label)

        # Timestamp (optional, small)
        self.time_label = QLabel(self.timestamp.strftime("%H:%M"))
        self.time_label.setObjectName("dimLabel")
        font = self.time_label.font()
        font.setPointSize(font.pointSize() - 2)
        self.time_label.setFont(font)
        layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignRight)

        # Size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _apply_style(self) -> None:
        """Apply styling based on message type."""
        if self.is_user:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {EMBER_ORANGE},
                        stop:1 {EMBER_ORANGE_LIGHT}
                    );
                    border-radius: 18px 18px 4px 18px;
                    margin-left: 60px;
                    margin-right: 24px;
                }}
                QLabel {{
                    color: white;
                    background: transparent;
                }}
            """)
        elif self.is_error:
            self.setStyleSheet("""
                MessageBubble {
                    background: rgba(244, 67, 54, 0.2);
                    border: 1px solid rgba(244, 67, 54, 0.5);
                    border-radius: 18px 18px 18px 4px;
                    margin-left: 24px;
                    margin-right: 60px;
                }
                QLabel {
                    color: #f44336;
                    background: transparent;
                }
            """)
        else:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background: rgba(26, 26, 36, 0.95);
                    border: 1px solid rgba(255, 107, 53, 0.15);
                    border-radius: 18px 18px 18px 4px;
                    margin-left: 24px;
                    margin-right: 60px;
                }}
                QLabel {{
                    color: #f0f0fa;
                    background: transparent;
                }}
            """)


class TypingIndicator(QWidget):
    """
    Animated typing indicator (three pulsing dots).
    """

    def __init__(self):
        super().__init__()

        self.setFixedSize(80, 40)
        self._dot_positions = [0.0, 0.0, 0.0]
        self._animation_offset = 0

        # Animation timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def _animate(self) -> None:
        """Animate the dots."""
        import math

        self._animation_offset += 0.15

        for i in range(3):
            phase = self._animation_offset - (i * 0.5)
            self._dot_positions[i] = abs(math.sin(phase)) * 8

        self.update()

    def paintEvent(self, event) -> None:
        """Paint the typing indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw three dots
        dot_radius = 4
        spacing = 16
        start_x = (self.width() - (3 * dot_radius * 2 + 2 * spacing)) / 2

        painter.setBrush(QColor(EMBER_ORANGE))
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(3):
            x = start_x + i * (dot_radius * 2 + spacing) + dot_radius
            y = self.height() / 2 - self._dot_positions[i]
            painter.drawEllipse(int(x - dot_radius), int(y - dot_radius),
                              dot_radius * 2, dot_radius * 2)

    def showEvent(self, event) -> None:
        """Start animation when shown."""
        self._timer.start(50)

    def hideEvent(self, event) -> None:
        """Stop animation when hidden."""
        self._timer.stop()


class ChatWidget(QScrollArea):
    """
    Main chat widget containing message bubbles.
    """

    def __init__(self):
        super().__init__()

        self._setup_ui()
        self._typing_indicator: Optional[TypingIndicator] = None

    def _setup_ui(self) -> None:
        """Setup the chat widget UI."""
        # Scroll area settings
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Container widget
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")

        # Layout for messages
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 16, 0, 16)
        self.layout.setSpacing(8)
        self.layout.addStretch()  # Push messages to bottom

        self.setWidget(self.container)

    def add_user_message(self, message: str) -> MessageBubble:
        """Add a user message to the chat."""
        bubble = MessageBubble(message, is_user=True)
        self._add_bubble(bubble)
        return bubble

    def add_agent_message(self, message: str, is_error: bool = False) -> MessageBubble:
        """Add an agent message to the chat."""
        bubble = MessageBubble(message, is_user=False, is_error=is_error)
        self._add_bubble(bubble)
        return bubble

    def _add_bubble(self, bubble: MessageBubble) -> None:
        """Add a bubble to the chat."""
        # Insert before stretch
        self.layout.insertWidget(self.layout.count() - 1, bubble)

        # Animate appearance
        if True:  # Animation enabled
            effect = QGraphicsOpacityEffect(bubble)
            bubble.setGraphicsEffect(effect)

            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

            # Keep reference to prevent garbage collection
            bubble._fade_anim = anim

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def show_typing_indicator(self) -> None:
        """Show the typing indicator."""
        if self._typing_indicator is None:
            self._typing_indicator = TypingIndicator()

        # Insert before stretch
        self.layout.insertWidget(self.layout.count() - 1, self._typing_indicator)
        self._typing_indicator.show()

        QTimer.singleShot(50, self._scroll_to_bottom)

    def hide_typing_indicator(self) -> None:
        """Hide the typing indicator."""
        if self._typing_indicator:
            self.layout.removeWidget(self._typing_indicator)
            self._typing_indicator.hide()

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat."""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear all messages."""
        while self.layout.count() > 1:  # Keep the stretch
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

