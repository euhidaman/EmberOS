"""
EmberOS GUI - Beautiful desktop interface for EmberOS.

A PyQt6-based GUI with glassmorphism design, dock integration,
and premium visual aesthetics.
"""

from emberos.gui.main_window import EmberMainWindow
from emberos.gui.app import EmberApplication

__all__ = ["EmberMainWindow", "EmberApplication", "main"]


def main():
    """Main entry point for ember-ui."""
    import sys
    from emberos.gui.app import run_app
    sys.exit(run_app())

