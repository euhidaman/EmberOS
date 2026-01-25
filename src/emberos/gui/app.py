"""
EmberOS GUI Application.
"""

from __future__ import annotations

import sys
import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QFontDatabase, QPalette, QColor

from emberos.core.config import EmberConfig
from emberos.gui.main_window import EmberMainWindow

logger = logging.getLogger(__name__)


class EmberApplication(QApplication):
    """
    Main application class for EmberOS GUI.

    Handles:
    - Application initialization
    - Theme/styling setup
    - Event loop integration with asyncio
    """

    def __init__(self, argv: list[str]):
        super().__init__(argv)

        self.config = EmberConfig.from_env()
        self.main_window: Optional[EmberMainWindow] = None
        self._async_timer: Optional[QTimer] = None
        self._current_theme = self.config.gui.theme  # Track current theme

        # Setup application properties
        self.setApplicationName("EmberOS")
        self.setApplicationDisplayName("EmberOS")
        self.setOrganizationName("EmberOS")
        self.setOrganizationDomain("emberos.org")

        # Setup styling
        self._setup_fonts()
        self.apply_theme(self._current_theme)

        # Setup async event loop integration
        self._setup_async_loop()

    def _setup_fonts(self) -> None:
        """Setup application fonts."""
        # Try to load custom fonts
        font_families = ["Inter", "SF Pro Display", "Segoe UI", "Roboto", "system-ui"]

        # PyQt6 API: get list of available font families
        available_families = QFontDatabase.families()

        for family in font_families:
            if family in available_families:
                font = QFont(family, self.config.gui.font_size)
                self.setFont(font)
                break
        else:
            # Fallback to default with size
            font = self.font()
            font.setPointSize(self.config.gui.font_size)
            self.setFont(font)

    def _setup_palette(self, theme: str = "dark") -> None:
        """Setup application color palette based on theme."""
        palette = QPalette()

        if theme == "dark":
            # Dark theme colors
            palette.setColor(QPalette.ColorRole.Window, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0fa"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#242430"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2a38"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f0fa"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#f0f0fa"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#2a2a38"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f0fa"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#ff6b35"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#ff6b35"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        else:  # light theme
            # Light theme colors
            palette.setColor(QPalette.ColorRole.Window, QColor("#f5f5fa"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#e8e8f0"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#e8e8f0"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1a1a24"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#ff6b35"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#ff6b35"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))

        self.setPalette(palette)

    def _setup_stylesheet(self, theme: str = "dark") -> None:
        """Setup application stylesheet based on theme."""

        # Theme-specific colors
        if theme == "dark":
            bg_color = "rgba(26, 26, 36, 0.95)"
            text_color = "#f0f0fa"
            input_bg = "rgba(36, 36, 48, 0.8)"
            dim_text = "#a0a0b0"
            secondary_bg = "rgba(60, 60, 80, 0.8)"
            scrollbar_bg = "rgba(36, 36, 48, 0.5)"
            container_bg = "rgba(26, 26, 36, 0.95)"
            border_color = "rgba(255, 107, 53, 0.2)"
        else:  # light
            bg_color = "rgba(245, 245, 250, 0.95)"
            text_color = "#1a1a24"
            input_bg = "rgba(255, 255, 255, 0.9)"
            dim_text = "#606070"
            secondary_bg = "rgba(232, 232, 240, 0.8)"
            scrollbar_bg = "rgba(200, 200, 210, 0.5)"
            container_bg = "rgba(245, 245, 250, 0.95)"
            border_color = "rgba(255, 107, 53, 0.3)"

        stylesheet = f"""
        /* Global styles */
        QWidget {{
            background-color: transparent;
            color: {text_color};
            font-family: "Inter", "SF Pro Display", "Segoe UI", sans-serif;
        }}
        
        QMainWindow {{
            background-color: {bg_color};
        }}
        
        QFrame#mainContainer {{
            background-color: {container_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
        }}
        
        /* Scroll bars */
        QScrollBar:vertical {{
            background: {scrollbar_bg};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:vertical {{
            background: rgba(255, 107, 53, 0.5);
            min-height: 30px;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: rgba(255, 107, 53, 0.8);
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar:horizontal {{
            background: {scrollbar_bg};
            height: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: rgba(255, 107, 53, 0.5);
            min-width: 30px;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: rgba(255, 107, 53, 0.8);
        }}
        
        /* Text inputs */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {input_bg};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 8px 12px;
            color: {text_color};
            selection-background-color: rgba(255, 107, 53, 0.5);
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid rgba(255, 107, 53, 0.6);
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: rgba(255, 107, 53, 0.8);
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            color: white;
            font-weight: 600;
        }}
        
        QPushButton:hover {{
            background-color: rgba(255, 107, 53, 1.0);
        }}
        
        QPushButton:pressed {{
            background-color: rgba(247, 147, 30, 1.0);
        }}
        
        QPushButton:disabled {{
            background-color: rgba(100, 100, 100, 0.5);
            color: rgba(240, 240, 250, 0.5);
        }}
        
        QPushButton#secondaryButton {{
            background-color: {secondary_bg};
        }}
        
        QPushButton#secondaryButton:hover {{
            background-color: rgba(80, 80, 100, 0.8);
        }}
        
        /* Labels */
        QLabel {{
            color: {text_color};
            background: transparent;
        }}
        
        QLabel#dimLabel {{
            color: {dim_text};
        }}
        
        /* Tool tips */
        QToolTip {{
            background-color: rgba(26, 26, 36, 0.95);
            border: 1px solid rgba(255, 107, 53, 0.3);
            border-radius: 4px;
            padding: 4px 8px;
            color: #f0f0fa;
        }}
        
        /* Menus */
        QMenu {{
            background-color: rgba(26, 26, 36, 0.95);
            border: 1px solid rgba(255, 107, 53, 0.2);
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: rgba(255, 107, 53, 0.3);
        }}
        
        /* Combo boxes */
        QComboBox {{
            background-color: rgba(36, 36, 48, 0.8);
            border: 1px solid rgba(255, 107, 53, 0.2);
            border-radius: 6px;
            padding: 6px 12px;
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: rgba(255, 107, 53, 0.4);
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: rgba(26, 26, 36, 0.95);
            border: 1px solid rgba(255, 107, 53, 0.2);
            border-radius: 6px;
            selection-background-color: rgba(255, 107, 53, 0.3);
        }}
        
        /* Progress bars */
        QProgressBar {{
            background-color: rgba(36, 36, 48, 0.8);
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: rgba(255, 107, 53, 0.8);
            border-radius: 4px;
        }}
        
        /* Tab widget */
        QTabWidget::pane {{
            border: 1px solid rgba(255, 107, 53, 0.2);
            border-radius: 8px;
            background-color: rgba(26, 26, 36, 0.5);
        }}
        
        QTabBar::tab {{
            background-color: rgba(36, 36, 48, 0.5);
            border: none;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: rgba(255, 107, 53, 0.3);
        }}
        
        QTabBar::tab:hover {{
            background-color: rgba(255, 107, 53, 0.2);
        }}
        """

        self.setStyleSheet(stylesheet)

    def _setup_async_loop(self) -> None:
        """Setup asyncio integration with Qt event loop."""
        # Create a timer to periodically run the asyncio event loop
        self._async_timer = QTimer()
        self._async_timer.timeout.connect(self._process_async_events)
        self._async_timer.start(10)  # 10ms interval

    def _process_async_events(self) -> None:
        """Process pending asyncio events."""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(0))
        except Exception:
            pass

    def apply_theme(self, theme: str) -> None:
        """Apply a theme (dark or light) to the application."""
        self._current_theme = theme
        self._setup_palette(theme)
        self._setup_stylesheet(theme)

        # Notify main window to update if it exists
        if self.main_window:
            self.main_window.on_theme_changed(theme)

    def toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.apply_theme(new_theme)

        # Save preference to config
        self.config.gui.theme = new_theme
        # TODO: Save to config file

    @property
    def current_theme(self) -> str:
        """Get the current theme."""
        return self._current_theme

    def run(self) -> int:
        """Run the application."""
        # Create main window
        self.main_window = EmberMainWindow(self.config)
        self.main_window.show()

        # Run event loop
        return self.exec()


def run_app() -> int:
    """Run the EmberOS GUI application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create and run application
    app = EmberApplication(sys.argv)
    return app.run()
