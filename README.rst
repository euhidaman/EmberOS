========
EmberOS
========

An AI-native layer for Arch Linux that transforms your system into an agentic OS
where every interaction flows through an intelligent, private AI agent.

.. note::
   EmberOS is not an application—it is an AI-native layer of the operating system itself.
   Every decision is logged and explainable, and no data ever leaves your machine.

Features
========

**Native OS Integration**
   Not an app you "run"—it's always there, like a system daemon.

**Dual Interface Equality**
   The GUI and Terminal are equally powerful, connected to the same brain.

**Visual Excellence**
   GUI matches premium commercial apps with glassmorphism design.

**Terminal Power**
   CLI competes with tools like fzf, ripgrep, and tmux.

**Privacy by Design**
   100% local. No telemetry. No cloud. Your data stays yours.

Quick Start
===========

Prerequisites
-------------

- Arch Linux (or Arch-based distribution)
- Python 3.11+
- 8GB+ RAM (16GB recommended)
- llama.cpp for local LLM inference
- A GGUF model (e.g., Qwen2.5-VL-7B-Instruct-Q4_K_M)

Installation
------------

1. Clone the repository::

      git clone https://github.com/emberos/emberos
      cd emberos

2. Run the installer::

      ./install.sh

3. Download an LLM model to ``/usr/local/share/ember/models/``

4. Enable and start the services::

      systemctl --user enable --now ember-llm
      systemctl --user enable --now emberd

5. Launch EmberOS::

      # GUI
      ember-ui

      # Terminal
      ember

Usage
=====

Terminal Interface
------------------

Launch the REPL::

   $ ember

   ╭─────────────────────────────────────────────────────────────╮
   │  EmberOS Terminal v1.0 · Connected · Qwen2.5-VL-7B          │
   ╰─────────────────────────────────────────────────────────────╯

   ember> find my budget spreadsheet

   🔍 Searching ~/Documents...

   Found 2 files:
     • 2024_budget.xlsx (245 KB) - ~/Documents/Finance/
     • Q4_financials.xlsx (1.2 MB) - ~/Documents/Work/

Built-in Commands
~~~~~~~~~~~~~~~~~

Commands prefixed with ``:`` are built-in::

   :help                Show help
   :status              Show system status
   :tools               List available tools
   :config              View/set configuration
   :history             Show command history
   :quit                Exit EmberOS

GUI Interface
-------------

Launch the graphical interface::

   ember-ui

Or find "EmberOS" in your application menu.

The GUI provides:

- Chat interface with message bubbles
- Context ribbon showing active window, clipboard, selected files
- Tool execution cards with progress and results
- Quick action palette (Ctrl+.)

Architecture
============

EmberOS consists of three main components:

**emberd (Daemon)**
   Systemd user service that coordinates all functionality:

   - D-Bus server for IPC (``org.ember.Agent``)
   - LLM orchestrator connecting to llama.cpp
   - Tool registry with permission system
   - Memory engine (SQLite + ChromaDB)
   - Context monitor for system state

**ember-ui (GUI)**
   PyQt6 application with glassmorphism design:

   - Title bar with custom controls
   - Collapsible context ribbon
   - Chat canvas with styled bubbles
   - Tool execution widgets
   - Input deck with auto-grow
   - Status ticker

**ember (CLI)**
   Rich terminal interface:

   - Syntax highlighting
   - Auto-completion
   - Command history
   - Progress displays
   - Pipe integration

Tools
=====

EmberOS includes built-in tools for common tasks:

**Filesystem**
   - ``filesystem.search`` - Search files by name or content
   - ``filesystem.read`` - Read file contents
   - ``filesystem.write`` - Write to files
   - ``filesystem.move`` - Move/rename files
   - ``filesystem.delete`` - Delete files
   - ``filesystem.list`` - List directory contents
   - ``filesystem.organize`` - Organize by file type

**Notes**
   - ``notes.create`` - Create a note
   - ``notes.search`` - Semantic search notes
   - ``notes.update`` - Update a note
   - ``notes.delete`` - Delete a note
   - ``notes.list`` - List all notes

**Applications**
   - ``applications.launch`` - Launch an app
   - ``applications.list`` - List running apps
   - ``applications.close`` - Close an app
   - ``applications.focus`` - Focus a window

**System**
   - ``system.status`` - System resource usage
   - ``system.command`` - Execute shell command
   - ``system.service`` - Manage systemd services
   - ``system.package`` - Manage packages with pacman
   - ``system.notify`` - Send desktop notification
   - ``system.clipboard`` - Read/write clipboard

Configuration
=============

System configuration: ``/etc/ember/emberos.toml``
User configuration: ``~/.config/ember/emberos.toml``

Key settings::

   [llm]
   server_url = "http://127.0.0.1:8080"
   context_size = 8192
   temperature = 0.1

   [permissions]
   filesystem_read_allowed = ["~/*", "/tmp/*"]
   filesystem_read_blocked = ["~/.ssh/*", "~/.gnupg/*"]
   require_confirmation_destructive = true
   network_enabled = false

Security
========

EmberOS is designed with security in mind:

- **Sandboxed execution** - Tools run with restricted permissions
- **Path filtering** - Configurable allowed/blocked paths
- **Confirmation prompts** - Destructive operations require confirmation
- **Audit logging** - All actions are logged
- **No network by default** - Network access is disabled unless explicitly enabled
- **Local only** - No telemetry, no cloud services

Development
===========

Creating Custom Tools
---------------------

Create a new tool in ``~/.local/share/ember/tools/``::

   from emberos.tools.base import BaseTool, ToolManifest, ToolParameter, ToolResult
   from emberos.tools.registry import register_tool

   @register_tool
   class MyTool(BaseTool):
       @property
       def manifest(self) -> ToolManifest:
           return ToolManifest(
               name="custom.mytool",
               description="My custom tool",
               parameters=[
                   ToolParameter(
                       name="input",
                       type="string",
                       description="Input value",
                       required=True
                   )
               ]
           )

       async def execute(self, params: dict) -> ToolResult:
           return ToolResult(success=True, data=f"Result: {params['input']}")

API Usage
---------

Python::

   from emberos.cli.client import EmberClient

   async def main():
       client = EmberClient()
       await client.connect()

       result = await client.process_command("find my documents")
       print(result)

License
=======

EmberOS is licensed under the GNU General Public License v3.0 (GPL-3.0).

See the LICENSE file for details.

Contributing
============

Contributions are welcome! Please see CONTRIBUTING.rst for guidelines.

- Report bugs: https://github.com/emberos/emberos/issues
- Submit PRs: https://github.com/emberos/emberos/pulls
- Discussions: https://github.com/emberos/emberos/discussions

Acknowledgments
===============

EmberOS is built on the shoulders of giants:

- `llama.cpp <https://github.com/ggerganov/llama.cpp>`_ - Local LLM inference
- `PyQt6 <https://www.riverbankcomputing.com/software/pyqt/>`_ - GUI framework
- `Rich <https://github.com/Textualize/rich>`_ - Terminal formatting
- `ChromaDB <https://www.trychroma.com/>`_ - Vector database
- `dbus-next <https://github.com/altdesktop/python-dbus-next>`_ - D-Bus bindings

