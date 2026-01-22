"""
EmberOS CLI - Terminal interface for EmberOS.

Provides a rich terminal REPL with syntax highlighting, autocomplete,
and beautiful output formatting.
"""

from emberos.cli.repl import EmberREPL
from emberos.cli.client import EmberClient
from emberos.cli.commands import CommandHandler

__all__ = ["EmberREPL", "EmberClient", "CommandHandler", "main"]


def main():
    """Main entry point for the ember CLI."""
    import asyncio
    from emberos.cli.repl import run_repl
    asyncio.run(run_repl())

