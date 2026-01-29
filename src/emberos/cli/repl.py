"""
EmberOS REPL - Interactive terminal interface.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.style import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

from emberos.core.constants import (
    EMBER_ORANGE, EMBER_DARK_BG, EMBER_TEXT_PRIMARY,
    DATA_DIR, APP_VERSION
)
from emberos.cli.client import EmberClient, OfflineClient, TaskUpdate
from emberos.cli.commands import CommandHandler

# ASCII Art Banner
BANNER = """
╭─────────────────────────────────────────────────────────────╮
│  ███████ ███    ███ ██████  ███████ ██████        ██████  ███████│
│  ██      ████  ████ ██   ██ ██      ██   ██       ██    ██ ██     │
│  █████   ██ ████ ██ ██████  █████   ██████  █████ ██    ██ ███████│
│  ██      ██  ██  ██ ██   ██ ██      ██   ██       ██    ██      ██│
│  ███████ ██      ██ ██████  ███████ ██   ██        ██████  ███████│
╰─────────────────────────────────────────────────────────────╯"""


class EmberREPL:
    """
    Interactive REPL for EmberOS.

    Features:
    - Rich terminal output with colors and formatting
    - Command history with file persistence
    - Auto-suggestions from history
    - Built-in commands (prefixed with :)
    - Real-time task progress display
    """

    def __init__(self):
        self.console = Console()
        self.client: Optional[EmberClient] = None
        self.offline_client: Optional[OfflineClient] = None
        self.command_handler: Optional[CommandHandler] = None
        self._running = False
        self._current_task_id: Optional[str] = None

        # Prompt styling
        self.prompt_style = PTStyle.from_dict({
            'prompt': f'{EMBER_ORANGE} bold',
            'input': EMBER_TEXT_PRIMARY,
        })

        # History file
        history_file = DATA_DIR / "cli_history"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            style=self.prompt_style,
        )

    async def start(self) -> None:
        """Start the REPL."""
        # Display banner
        self.console.print(f"[{EMBER_ORANGE}]{BANNER}[/{EMBER_ORANGE}]")
        self.console.print()

        # Try to connect to daemon
        self.client = EmberClient()
        connected = await self.client.connect()

        if connected:
            # Get status info
            try:
                tools_count = len(await self.client.list_tools())

                self.console.print(
                    f"  [bold]Ember-OS Terminal[/bold] v{APP_VERSION} · "
                    f"[green]Connected[/green] · "
                    f"{tools_count} tools"
                )
            except Exception:
                self.console.print(
                    f"  [bold]Ember-OS Terminal[/bold] v{APP_VERSION} · "
                    f"[green]Connected[/green]"
                )

            # Setup signal handlers
            self.client.on("progress", self._on_progress)
            self.client.on("completed", self._on_completed)
            self.client.on("failed", self._on_failed)
            self.client.on("confirmation", self._on_confirmation)
        else:
            self.console.print(
                f"  [bold]Ember-OS Terminal[/bold] v{APP_VERSION} · "
                f"[yellow]Offline Mode[/yellow] (daemon not running)"
            )
            self.offline_client = OfflineClient()
            await self.offline_client.initialize()

        self.console.print("  Type [bold]:help[/bold] or press [bold]Ctrl+D[/bold] to exit")
        self.console.print()

        # Initialize command handler
        active_client = self.client if connected else self.offline_client
        self.command_handler = CommandHandler(active_client, self.console)

        self._running = True

    async def stop(self) -> None:
        """Stop the REPL."""
        self._running = False

        if self.client:
            await self.client.disconnect()

    def _get_prompt(self) -> HTML:
        """Get the prompt string."""
        if self.client and self.client.is_connected:
            status_color = EMBER_ORANGE
        else:
            status_color = "yellow"

        return HTML(f'<style fg="{status_color}" bold="true">ember></style> ')

    async def run(self) -> None:
        """Run the REPL loop."""
        await self.start()

        while self._running:
            try:
                # Get input
                text = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.session.prompt(self._get_prompt())
                )

                text = text.strip()
                if not text:
                    continue

                # Handle built-in commands
                if self.command_handler.is_command(text):
                    should_continue = await self.command_handler.execute(text)
                    if not should_continue:
                        break
                    continue

                # Process as natural language command
                await self._process_command(text)

            except KeyboardInterrupt:
                self.console.print("\n[dim]Use :quit to exit[/dim]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

        await self.stop()

    async def _process_command(self, text: str) -> None:
        """Process a natural language command."""
        if self.client and self.client.is_connected:
            await self._process_command_daemon(text)
        else:
            await self._process_command_offline(text)

    async def _process_command_daemon(self, text: str) -> None:
        """Process command through daemon."""
        try:
            # Show processing indicator
            with Progress(
                SpinnerColumn(style=EMBER_ORANGE),
                TextColumn("[bold]Processing...[/bold]"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("processing", total=None)

                # Send command
                result = await self.client.process_command(text)
                self._current_task_id = result.get("task_id")
                
                # Use result immediately if task is already completed (sync call)
                if result.get("status") == "completed" or result.get("success"):
                    update = TaskUpdate(
                        task_id=self._current_task_id,
                        event_type="completed",
                        data=result
                    )
                    self._on_completed(update)
                    return

            # Wait for completion if needed (for async tasks)

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    async def _process_command_offline(self, text: str) -> None:
        """Process command in offline mode (limited functionality)."""
        self.console.print(
            "[yellow]⚠ Offline mode: Natural language processing unavailable[/yellow]"
        )
        self.console.print(
            "[dim]Use direct tool execution or start the daemon with: systemctl --user start emberd[/dim]"
        )

    # ============ Signal Handlers ============

    def _on_progress(self, update: TaskUpdate) -> None:
        """Handle progress updates."""
        if update.task_id != self._current_task_id:
            return

        stage = update.data.get("stage", "")
        message = update.data.get("message", "")

        self.console.print(f"[dim]⟳ {stage}: {message}[/dim]")

    def _on_completed(self, update: TaskUpdate) -> None:
        """Handle task completion."""
        if update.task_id != self._current_task_id:
            return

        data = update.data

        if data.get("success"):
            response = data.get("response", "")
            self.console.print()
            self.console.print(Panel(
                response,
                border_style="green",
                padding=(1, 2)
            ))

            # Show execution summary
            if data.get("results"):
                results = data["results"]
                success_count = sum(1 for r in results if r.get("success", True))
                total = len(results)

                duration = data.get("duration_ms", 0)
                self.console.print(
                    f"[dim]✓ {success_count}/{total} operations · {duration}ms[/dim]"
                )
        else:
            self.console.print(f"[red]✗ Task failed[/red]")

        self.console.print()

    def _on_failed(self, update: TaskUpdate) -> None:
        """Handle task failure."""
        if update.task_id != self._current_task_id:
            return

        error = update.data.get("error", "Unknown error")
        error_type = update.data.get("error_type", "Error")

        self.console.print()
        self.console.print(Panel(
            f"[bold red]{error_type}[/bold red]\n\n{error}",
            title="❌ Error",
            border_style="red"
        ))
        self.console.print()

    def _on_confirmation(self, update: TaskUpdate) -> None:
        """Handle confirmation request."""
        if update.task_id != self._current_task_id:
            return

        plan = update.data.get("plan", {})
        message = update.data.get("message", "Confirm action?")

        # Display plan
        self.console.print()
        self.console.print(Panel(
            self._format_plan(plan),
            title="⚠️ Confirmation Required",
            border_style="yellow"
        ))
        self.console.print()
        self.console.print(f"[bold]{message}[/bold]")

        # Get confirmation
        try:
            response = self.session.prompt(
                HTML('<style fg="yellow" bold="true">[y/N]</style> ')
            )
            confirmed = response.lower() in ("y", "yes")

            # Send confirmation
            asyncio.create_task(
                self.client.confirm_action(update.task_id, confirmed)
            )

        except (KeyboardInterrupt, EOFError):
            asyncio.create_task(
                self.client.confirm_action(update.task_id, False)
            )

    def _format_plan(self, plan: dict) -> str:
        """Format execution plan for display."""
        lines = []

        if plan.get("reasoning"):
            lines.append(f"[bold]Reasoning:[/bold] {plan['reasoning']}")
            lines.append("")

        if plan.get("steps"):
            lines.append("[bold]Steps:[/bold]")
            for i, step in enumerate(plan["steps"], 1):
                tool = step.get("tool", "unknown")
                desc = step.get("description", "")
                lines.append(f"  {i}. {tool}")
                if desc:
                    lines.append(f"     [dim]{desc}[/dim]")

        if plan.get("risk_level"):
            risk = plan["risk_level"]
            risk_style = {"low": "green", "medium": "yellow", "high": "red"}.get(risk, "white")
            lines.append(f"\n[bold]Risk Level:[/bold] [{risk_style}]{risk}[/{risk_style}]")

        return "\n".join(lines)


async def run_repl() -> None:
    """Run the EmberOS REPL."""
    repl = EmberREPL()
    await repl.run()


def main():
    """Main entry point."""
    asyncio.run(run_repl())


if __name__ == "__main__":
    main()

