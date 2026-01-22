"""
Command Handler for EmberOS CLI.

Handles built-in commands (prefixed with :) and provides command completion.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.tree import Tree

from emberos.core.constants import EMBER_ORANGE


@dataclass
class Command:
    """Definition of a built-in command."""
    name: str
    description: str
    usage: str
    handler: Callable
    aliases: list[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CommandHandler:
    """
    Handles built-in CLI commands.

    Commands are prefixed with : (e.g., :help, :status, :tools)
    """

    def __init__(self, client, console: Console):
        self.client = client
        self.console = console
        self._commands: dict[str, Command] = {}
        self._register_commands()

    def _register_commands(self):
        """Register all built-in commands."""
        commands = [
            Command(
                name="help",
                description="Show help information",
                usage=":help [command]",
                handler=self._cmd_help,
                aliases=["h", "?"]
            ),
            Command(
                name="status",
                description="Show system status",
                usage=":status",
                handler=self._cmd_status,
                aliases=["s"]
            ),
            Command(
                name="tools",
                description="List available tools",
                usage=":tools [category]",
                handler=self._cmd_tools,
                aliases=["t"]
            ),
            Command(
                name="history",
                description="Show command history",
                usage=":history [n]",
                handler=self._cmd_history,
                aliases=["hist"]
            ),
            Command(
                name="config",
                description="View or set configuration",
                usage=":config [get|set] [section] [key] [value]",
                handler=self._cmd_config,
                aliases=["cfg"]
            ),
            Command(
                name="context",
                description="Show current context",
                usage=":context",
                handler=self._cmd_context,
                aliases=["ctx"]
            ),
            Command(
                name="clear",
                description="Clear the screen",
                usage=":clear",
                handler=self._cmd_clear,
                aliases=["cls"]
            ),
            Command(
                name="quit",
                description="Exit EmberOS CLI",
                usage=":quit",
                handler=self._cmd_quit,
                aliases=["exit", "q"]
            ),
        ]

        for cmd in commands:
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd

    def is_command(self, text: str) -> bool:
        """Check if text is a built-in command."""
        return text.strip().startswith(":")

    async def execute(self, text: str) -> bool:
        """
        Execute a command.

        Returns True if REPL should continue, False to exit.
        """
        parts = text.strip()[1:].split()  # Remove : prefix
        if not parts:
            return True

        cmd_name = parts[0].lower()
        args = parts[1:]

        if cmd_name not in self._commands:
            self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
            self.console.print("Type :help for available commands")
            return True

        cmd = self._commands[cmd_name]
        return await cmd.handler(args)

    def get_completions(self, text: str) -> list[str]:
        """Get command completions."""
        if not text.startswith(":"):
            return []

        prefix = text[1:].lower()
        completions = []

        for name, cmd in self._commands.items():
            if name.startswith(prefix) and name == cmd.name:  # Only main name, not aliases
                completions.append(f":{name}")

        return completions

    # ============ Command Handlers ============

    async def _cmd_help(self, args: list[str]) -> bool:
        """Show help information."""
        if args:
            # Help for specific command
            cmd_name = args[0].lower()
            if cmd_name in self._commands:
                cmd = self._commands[cmd_name]
                self.console.print(Panel(
                    f"[bold]{cmd.name}[/bold]\n\n"
                    f"{cmd.description}\n\n"
                    f"[dim]Usage:[/dim] {cmd.usage}\n"
                    f"[dim]Aliases:[/dim] {', '.join(cmd.aliases) if cmd.aliases else 'none'}",
                    title="Command Help",
                    border_style="blue"
                ))
            else:
                self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
        else:
            # General help
            table = Table(title="EmberOS Commands", border_style="blue")
            table.add_column("Command", style="cyan")
            table.add_column("Description")
            table.add_column("Aliases", style="dim")

            seen = set()
            for name, cmd in sorted(self._commands.items()):
                if cmd.name not in seen:
                    seen.add(cmd.name)
                    table.add_row(
                        f":{cmd.name}",
                        cmd.description,
                        ", ".join(cmd.aliases) if cmd.aliases else ""
                    )

            self.console.print(table)
            self.console.print("\n[dim]Type :help <command> for detailed help[/dim]")

        return True

    async def _cmd_status(self, args: list[str]) -> bool:
        """Show system status."""
        try:
            status = await self.client.get_status()

            # Build status display
            lines = []

            # Daemon status
            daemon_status = "● Running" if status.get("running") else "○ Stopped"
            daemon_color = "green" if status.get("running") else "red"
            lines.append(f"[bold]Daemon:[/bold]     [{daemon_color}]{daemon_status}[/{daemon_color}]")

            if status.get("uptime_seconds"):
                hours = status["uptime_seconds"] / 3600
                lines.append(f"[bold]Uptime:[/bold]     {hours:.1f} hours")

            # LLM status
            llm_status = "● Connected" if status.get("llm_connected") else "○ Disconnected"
            llm_color = "green" if status.get("llm_connected") else "yellow"
            lines.append(f"[bold]LLM Server:[/bold] [{llm_color}]{llm_status}[/{llm_color}]")

            if status.get("model_name"):
                lines.append(f"[bold]Model:[/bold]      {status['model_name']}")

            # Tasks
            lines.append(f"[bold]Active Tasks:[/bold] {status.get('active_tasks', 0)}")
            lines.append(f"[bold]Tools Loaded:[/bold] {status.get('tools_loaded', 0)}")

            self.console.print(Panel(
                "\n".join(lines),
                title="EmberOS Status",
                border_style=EMBER_ORANGE
            ))

        except Exception as e:
            self.console.print(f"[red]Error getting status: {e}[/red]")

        return True

    async def _cmd_tools(self, args: list[str]) -> bool:
        """List available tools."""
        try:
            tools = await self.client.list_tools()

            # Filter by category if specified
            category_filter = args[0].lower() if args else None

            if category_filter:
                tools = [t for t in tools if t.get("category", "").lower() == category_filter]

            if not tools:
                self.console.print("[yellow]No tools found[/yellow]")
                return True

            # Group by category
            by_category = {}
            for tool in tools:
                cat = tool.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(tool)

            for category, cat_tools in sorted(by_category.items()):
                table = Table(title=f"{category.title()} Tools", border_style="blue")
                table.add_column("Tool", style="cyan")
                table.add_column("Description")
                table.add_column("Risk", style="dim")

                for tool in cat_tools:
                    risk = tool.get("risk_level", "low")
                    risk_style = {"low": "green", "medium": "yellow", "high": "red"}.get(risk, "white")

                    table.add_row(
                        f"{tool.get('icon', '🔧')} {tool['name']}",
                        tool.get("description", "")[:50],
                        f"[{risk_style}]{risk}[/{risk_style}]"
                    )

                self.console.print(table)
                self.console.print()

        except Exception as e:
            self.console.print(f"[red]Error listing tools: {e}[/red]")

        return True

    async def _cmd_history(self, args: list[str]) -> bool:
        """Show command history."""
        limit = int(args[0]) if args else 20

        # This would need to be implemented with actual history storage
        self.console.print("[dim]Command history not yet implemented[/dim]")
        return True

    async def _cmd_config(self, args: list[str]) -> bool:
        """View or set configuration."""
        try:
            if not args or args[0] == "get":
                section = args[1] if len(args) > 1 else ""
                config = await self.client.get_config(section)

                syntax = Syntax(
                    str(config),
                    "python",
                    theme="monokai",
                    line_numbers=False
                )
                self.console.print(Panel(syntax, title="Configuration", border_style="blue"))

            elif args[0] == "set" and len(args) >= 4:
                section, key, value = args[1], args[2], args[3]
                result = await self.client.set_config(section, key, value)

                if result.get("success"):
                    self.console.print(f"[green]✓ Set {section}.{key} = {value}[/green]")
                else:
                    self.console.print(f"[red]✗ Failed: {result.get('error')}[/red]")
            else:
                self.console.print("Usage: :config [get|set] [section] [key] [value]")

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

        return True

    async def _cmd_context(self, args: list[str]) -> bool:
        """Show current context."""
        try:
            context = await self.client.get_context()

            tree = Tree("[bold]Current Context[/bold]")

            if context.get("active_window"):
                tree.add(f"🪟 Window: {context['active_window']}")
            if context.get("active_window_title"):
                tree.add(f"   Title: {context['active_window_title']}")
            if context.get("clipboard_text"):
                clip_preview = context['clipboard_text'][:50]
                tree.add(f"📋 Clipboard: {clip_preview}...")
            if context.get("selected_files"):
                files_node = tree.add("📁 Selected Files")
                for f in context['selected_files'][:5]:
                    files_node.add(f)
            if context.get("working_directory"):
                tree.add(f"📂 Working Dir: {context['working_directory']}")

            self.console.print(Panel(tree, border_style=EMBER_ORANGE))

        except Exception as e:
            self.console.print(f"[red]Error getting context: {e}[/red]")

        return True

    async def _cmd_clear(self, args: list[str]) -> bool:
        """Clear the screen."""
        self.console.clear()
        return True

    async def _cmd_quit(self, args: list[str]) -> bool:
        """Exit the REPL."""
        self.console.print("[dim]Goodbye![/dim]")
        return False

