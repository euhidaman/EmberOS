"""
Title Bar Widget for EmberOS GUI.
"""

from __future__ import annotations
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QCursor

from emberos.core.constants import EMBER_ORANGE, EMBER_ORANGE_LIGHT, APP_NAME, DATA_DIR


class WindowButton(QPushButton):
    """
    Custom window control button with hover effects.
    """

    def __init__(self, text: str, hover_color: str = "#505060", width: int = 70):
        super().__init__(text)

        self._hover_color = hover_color
        self.setFixedSize(width, 32)
        self._setup_style()

    def _setup_style(self) -> None:
        """Setup button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(42, 42, 56, 0.8);
                border: 1px solid rgba(255, 107, 53, 0.2);
                border-radius: 6px;
                color: #f0f0fa;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {self._hover_color};
                border-color: rgba(255, 107, 53, 0.5);
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 107, 53, 0.6);
            }}
        """)


class EmberLogo(QLabel):
    """
    EmberOS/Zevion logo widget.
    """

    def __init__(self, size: int = 24):
        super().__init__()
        self.setFixedSize(size, size)
        self._size = size
        self._load_logo()

    def _load_logo(self) -> None:
        """Load the Zevion logo image."""
        # Try multiple paths for the logo
        logo_paths = [
            Path(__file__).parent.parent.parent.parent.parent / "assets" / "zevion-logo.png",
            Path("/usr/share/icons/hicolor/256x256/apps/emberos.png"),
            Path("/usr/local/share/ember/assets/zevion-logo.png"),
            DATA_DIR / "assets" / "zevion-logo.png",
        ]

        for logo_path in logo_paths:
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self._size, self._size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.setPixmap(scaled)
                    return

        # Fallback: draw a simple colored circle if logo not found
        self._draw_fallback()

    def _draw_fallback(self) -> None:
        """Draw a fallback logo if image not found."""
        pixmap = QPixmap(self._size, self._size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self._size, self._size)
        gradient.setColorAt(0, QColor(EMBER_ORANGE))
        gradient.setColorAt(1, QColor(EMBER_ORANGE_LIGHT))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
        painter.end()

        self.setPixmap(pixmap)


class TitleBar(QFrame):
    """
    Custom title bar with logo, title, and window controls.
    """

    # Signals
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    theme_toggle_clicked = pyqtSignal()  # New signal for theme toggle

    def __init__(self, parent=None):
        super().__init__(parent)

        self._drag_pos = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the title bar UI."""
        self.setObjectName("titleBar")
        self.setFixedHeight(48)

        # Enable mouse tracking for proper drag handling
        self.setMouseTracking(True)

        self.setStyleSheet("""
            QFrame#titleBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(26, 26, 36, 1),
                    stop:1 rgba(36, 36, 48, 1)
                );
                border-bottom: 1px solid rgba(255, 107, 53, 0.1);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(12)

        # Logo
        self.logo = EmberLogo(24)
        layout.addWidget(self.logo)

        # Title
        self.title_label = QLabel(APP_NAME)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #f0f0fa;
                font-weight: 600;
                font-size: 14px;
                background: transparent;
            }
        """)
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Theme toggle button (wider for icon + text)
        self.theme_btn = WindowButton("Theme", hover_color="#404050", width=90)
        self.theme_btn.setToolTip("Toggle Light/Dark Mode")
        self.theme_btn.clicked.connect(self.theme_toggle_clicked.emit)
        layout.addWidget(self.theme_btn)

        # Window controls
        self.minimize_btn = WindowButton("Min", hover_color="#505060", width=60)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.minimize_btn)

        self.maximize_btn = WindowButton("Max", hover_color="#505060", width=60)
        self.maximize_btn.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(self.maximize_btn)

        self.close_btn = WindowButton("Close", hover_color="#e81123", width=70)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.close_btn)

    def set_title(self, title: str) -> None:
        """Set the title text."""
        self.title_label.setText(title)

    def update_theme_button(self, theme: str) -> None:
        """Update theme button text based on current theme."""
        if theme == "dark":
            self.theme_btn.setText("☀ Light")
            self.theme_btn.setToolTip("Switch to Light Mode")
        else:
            self.theme_btn.setText("☾ Dark")
            self.theme_btn.setToolTip("Switch to Dark Mode")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't start drag if clicking on buttons
            widget = self.childAt(event.pos())
            if widget and isinstance(widget, WindowButton):
                event.ignore()
                return

            # Try native window dragging first (works better on Linux)
            window = self.window()
            if window.windowHandle():
                # Use native system move (better for X11/Wayland)
                window.windowHandle().startSystemMove()
                event.accept()
                return

            # Fallback to manual dragging
            self._drag_pos = event.globalPosition().toPoint() - window.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for window dragging."""
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            # Move the main window manually (fallback method)
            window = self.window()
            window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            # Update cursor based on what we're hovering over
            widget = self.childAt(event.pos())
            if widget and isinstance(widget, WindowButton):
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            # Reset cursor
            widget = self.childAt(event.pos())
            if widget and isinstance(widget, WindowButton):
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click to maximize/restore."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't maximize if clicking on buttons
            widget = self.childAt(event.pos())
            if widget and isinstance(widget, WindowButton):
                event.ignore()
                return

            self.maximize_clicked.emit()
            event.accept()

