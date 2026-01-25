# EmberOS

**An AI-native layer for Arch Linux that transforms your system into an agentic OS where every interaction flows through an intelligent, private AI agent.**

> **Note:** EmberOS is not an application—it is an AI-native layer of the operating system itself. Every decision is logged and explainable, and no data ever leaves your machine.

---

## 🌟 Features

- **Native OS Integration** - Not an app you "run"—it's always there, like a system daemon
- **Dual Interface Equality** - GUI and Terminal are equally powerful, connected to the same brain
- **Visual Excellence** - GUI matches premium commercial apps with glassmorphism design
- **Terminal Power** - CLI competes with tools like fzf, ripgrep, and tmux
- **Privacy by Design** - 100% local. No telemetry. No cloud. Your data stays yours
- **Complete CRUD Operations** - Full Create, Read, Update, Delete for files, notes, and tasks
- **Interrupt & Rollback** - Stop tasks mid-execution and undo operations with snapshots
- **Context-Aware** - Understands your active window, clipboard, and recent history

---

## 🚀 Quick Start

### Prerequisites

- **Arch Linux** (or Arch-based distribution)
- **Python 3.11+** (3.12 recommended for full features)
- **8GB+ RAM** (16GB recommended)
- **~10GB disk space** (for model + application files)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/emberos/emberos
cd emberos

# 2. Run installer
./install.sh

# 3. Download LLM model (manual step required)
huggingface-cli download unsloth/Qwen2.5-VL-7B-Instruct-GGUF \
  Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \
  --local-dir /usr/local/share/ember/models

# 4. Enable and start services
systemctl --user enable --now ember-llm
systemctl --user enable --now emberd

# 5. Launch EmberOS
ember-ui  # GUI
# or
ember     # CLI
```

📖 **For detailed installation instructions:** See [INSTALL.md](INSTALL.md)

📚 **For usage guide and examples:** See [USER_GUIDE.md](USER_GUIDE.md)

---

## 📋 Table of Contents

- [Usage](#-usage)
- [Architecture](#-architecture)
- [Complete Functionality](#-complete-functionality)
- [Tools & CRUD Operations](#-tools--crud-operations)
- [Workflow Pipeline](#-workflow-pipeline)
- [Task Control](#-task-control)
- [Configuration](#-configuration)
- [Security](#-security)
- [Development](#-development)
- [License](#-license)

---

## 🎯 Usage

### Terminal Interface (CLI)

```bash
$ ember

╭─────────────────────────────────────────────────────────────╮
│  EmberOS Terminal v1.0 · Connected · Qwen2.5-VL-7B          │
╰─────────────────────────────────────────────────────────────╯

ember> find my budget spreadsheet

🔍 Searching ~/Documents...

Found 2 files:
  • 2024_budget.xlsx (245 KB) - ~/Documents/Finance/
  • Q4_financials.xlsx (1.2 MB) - ~/Documents/Work/
```

**Built-in Commands:**
- `:help` - Show help
- `:status` - Show system status
- `:tools` - List available tools
- `:quit` - Exit EmberOS

### Graphical Interface (GUI)

```bash
ember-ui
```

Or find **EmberOS** in your application menu.

**GUI Features:**
- Chat interface with message bubbles
- File attachment support (📎 button)
- Interrupt button (⏸) to stop running tasks
- Rollback button (↩) to undo operations
- Context ribbon showing active window, clipboard
- Status ticker with system information

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                       │
│  ┌───────────────┐        ┌──────────────────────┐     │
│  │  CLI (REPL)   │        │   GUI (PyQt6)        │     │
│  │  • Commands   │        │   • Chat Area        │     │
│  │  • History    │        │   • File Attachments │     │
│  │  • Piping     │        │   • Interrupt/Rollback│    │
│  └───────┬───────┘        └──────────┬───────────┘     │
└──────────┼────────────────────────────┼─────────────────┘
           │         D-Bus IPC          │
           ▼                            ▼
┌──────────────────────────────────────────────────────────┐
│              EMBEROS DAEMON (emberd)                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         WORKFLOW ORCHESTRATOR                      │ │
│  │                                                    │ │
│  │  1. Context Gathering (window, clipboard, memory) │ │
│  │  2. LLM Planning (JSON with reasoning)            │ │
│  │  3. Permission Checking (path + operation)        │ │
│  │  4. User Confirmation (if risky)                  │ │
│  │  5. Snapshot Creation (automatic backups)         │ │
│  │  6. Tool Execution (sequential with chaining)     │ │
│  │  7. Result Synthesis (LLM response)               │ │
│  │  8. Memory Storage (SQLite + ChromaDB)            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Components:                                             │
│  • LLM Orchestrator (llama.cpp on port 11434)           │
│  • Tool Registry (FileSystem, Notes, System, Apps)      │
│  • Memory Engine (SQLite + ChromaDB vector search)      │
│  • Task Manager (snapshots + rollback)                  │
│  • Context Monitor (X11/Wayland integration)            │
└──────────────────────────────────────────────────────────┘
```

### Data Flow: User Request → Response

```
User Input: "Find my budget spreadsheet"
    ↓
1. CONTEXT GATHERING
   • Active window: Firefox
   • CWD: /home/user/Documents
   • Recent memory: user mentioned budget yesterday
    ↓
2. LLM PLANNING
   • Generates JSON plan with reasoning
   • Selects tools: filesystem.search
   • Determines risk level: LOW
    ↓
3. PERMISSION CHECK
   • Tool: filesystem.search (READ) ✓
   • Path: /home/user ✓ allowed
   • No confirmation needed
    ↓
4. TOOL EXECUTION
   • filesystem.search(query="budget", extensions=[".xlsx", ".ods"])
   • Found: 2 files
    ↓
5. RESULT SYNTHESIS
   • LLM generates user-friendly response
    ↓
6. MEMORY STORAGE
   • Saves conversation to SQLite
   • Adds embeddings to ChromaDB
    ↓
Response: "I found your budget spreadsheet at:
          /home/user/Documents/2024_budget.xlsx"
```

---

## ✅ Complete Functionality

### CRUD Operations - Files

| Operation | Tool | Description |
|-----------|------|-------------|
| **CREATE** | `filesystem.write` | Create/write files with content |
| | `filesystem.create_directory` | Create directories |
| **READ** | `filesystem.read` | Read file contents |
| | `filesystem.search` | Search files by name/content |
| | `filesystem.list` | List directory contents |
| | `filesystem.info` | Get file metadata |
| **UPDATE** | `filesystem.move` | Move/rename files |
| | `filesystem.copy` | Copy files/directories |
| | `filesystem.organize` | Organize files by type |
| **DELETE** | `filesystem.delete` | Delete files (with confirmation + snapshot) |

### CRUD Operations - Notes

| Operation | Tool | Description |
|-----------|------|-------------|
| **CREATE** | `notes.create` | Create new note with title, content, tags |
| **READ** | `notes.get` | Get note by ID |
| | `notes.list` | List all notes with filtering |
| | `notes.search` | Search notes (keyword + semantic) |
| **UPDATE** | `notes.update` | Update existing note |
| **DELETE** | `notes.delete` | Delete note permanently |

### System Tools

- **`system.info`** - Get system information (OS, CPU, RAM, disk)
- **`system.processes`** - List running processes
- **`system.disk_usage`** - Get disk usage statistics
- **`system.execute`** - Run shell commands (sandboxed)
- **`system.clipboard`** - Read/write clipboard
- **`system.notify`** - Send desktop notifications

### Application Tools

- **`applications.launch`** - Launch applications by name
- **`applications.open_file`** - Open file with default app
- **`applications.list`** - List installed applications

---

## 🔄 Workflow Pipeline

EmberOS implements a complete 8-step workflow for every user request:

### 1. Context Gathering
- Active window/application (via X11/Wayland)
- Current working directory
- Clipboard contents
- Recent conversation history (last 5 exchanges)
- Attached file metadata

### 2. LLM Planning
- Receives user message + full context + available tools
- Generates JSON execution plan with reasoning
- Creates multi-step plan with tool calls
- Determines risk level & confirmation requirements

**Example Plan:**
```json
{
  "reasoning": "User wants spreadsheet file. Search filesystem for 'budget' with spreadsheet extensions.",
  "plan": [{
    "tool": "filesystem.search",
    "args": {
      "query": "budget",
      "extensions": [".xlsx", ".ods", ".csv"],
      "path": "/home/user"
    }
  }],
  "requires_confirmation": false,
  "risk_level": "low"
}
```

### 3. Permission Checking
- Validates tool permissions against config
- Checks file path access rights
- Evaluates operation risk level
- Blocks unauthorized operations

**Risk Levels:**
- **LOW:** Read operations (no confirmation)
- **MEDIUM:** Write operations (confirmation required)
- **HIGH:** Delete, system commands (confirmation + snapshot)

### 4. User Confirmation (if risky)
Shows preview of operation for destructive actions:
- File deletion
- File moves
- Bulk operations (50+ files)
- System commands

### 5. Snapshot Creation
**Automatic backups before:**
- File deletions
- File moves/renames
- File overwrites
- Bulk operations

**Storage:** `~/.local/share/ember/backups/`
**Retention:** 7 days (configurable)

### 6. Tool Execution
- Executes tools sequentially
- Resolves `$result[N]` references between steps
- Monitors for interruption requests
- Logs each operation result

### 7. Result Synthesis
LLM generates human-friendly response from results:
- Summarizes what was accomplished
- Highlights key findings
- Mentions any issues encountered
- Suggests follow-up actions

### 8. Memory Storage
- Stores conversation in SQLite
- Adds to vector database (semantic search)
- Updates user patterns
- Enables future context recall

---

## 🎮 Task Control

### Interrupt Functionality

**Button:** ⏸ **Interrupt**

**Enabled When:** Task is currently running

**What It Does:**
1. Sets interrupt flag on active task
2. Gracefully stops current tool execution
3. Prevents subsequent steps from running
4. Returns partial results
5. Keeps completed snapshots for rollback

**Example:**
```
User: "Organize my entire home directory"
Agent: Starting...
[User clicks Interrupt after 2 minutes]
Result: Organized 500 files, stopped before completing
Snapshots: 5 restore points created
```

### Rollback Functionality

**Button:** ↩ **Rollback**

**Enabled When:** Task completed and snapshots exist

**What It Does:**
1. Restores files from most recent snapshot
2. Reverses filesystem changes
3. Puts system back to pre-operation state
4. Maintains snapshot chain for multiple rollbacks

**Snapshot System:**
- Automatically created before destructive operations
- Full file backups with metadata
- Multiple rollback points supported
- Can rollback multiple times

**Example:**
```
User: "Delete all .tmp files in Downloads"
Plan: Find 23 files → Delete
Snapshot: Created backup of all 23 files
Execution: 23 files deleted
[User realizes mistake]
[Clicks Rollback]
Result: All 23 files restored from snapshot
```

**What Can Be Rolled Back:**
- ✅ File deletions → Files restored
- ✅ File moves → Moved back to original location
- ✅ File overwrites → Original content restored
- ✅ Directory changes → Full tree restored
- ❌ External commands (can't undo)
- ❌ Network requests (can't undo)

---

## ⚙️ Configuration

### System Configuration

**Location:** `~/.config/ember/emberos.toml`

```toml
[llm]
server_url = "http://127.0.0.1:11434"
default_model = "qwen2.5-vl-7b-instruct-q4_k_m.gguf"
context_size = 8192
temperature = 0.1

[gui]
theme = "dark"  # or "light"
opacity = 0.95
window_width = 800
window_height = 600
font_size = 11

[permissions]
filesystem_read_allowed = [
    "~/Documents",
    "~/Downloads",
    "~/Pictures",
    "~/Videos",
    "/tmp"
]

filesystem_read_blocked = [
    "~/.ssh",
    "~/.gnupg"
]

filesystem_write_allowed = [
    "~/Documents",
    "~/Downloads"
]

require_confirmation_threshold = 50  # files

[memory]
sqlite_path = "~/.local/share/ember/ember.db"
vector_store_path = "~/.local/share/ember/vectors"
max_conversations = 10000
```

---

## 🔐 Security

EmberOS is designed with security in mind:

### Sandboxed Execution
- Tools run with restricted permissions
- Timeout enforcement (60s default)
- Memory limits (512MB per tool)
- CPU time limits

### Path Filtering
- Configurable allowed/blocked paths
- Whitelist: `~/Documents`, `~/Downloads`, etc.
- Blacklist: `~/.ssh`, `~/.gnupg`, `/etc`, `/sys`

### Confirmation Prompts
- Destructive operations require confirmation
- Shows preview of changes
- Risk assessment displayed

### Audit Logging
- All actions are logged
- Conversation history stored
- Tool execution tracked

### Privacy
- **No network by default** - Network access disabled unless enabled
- **Local only** - No telemetry, no cloud services
- **100% local** - All data stays on your machine
- **No data collection** - EmberOS never phones home

---

## 🛠️ Development

### Creating Custom Tools

Create a new tool in `~/.local/share/ember/tools/`:

```python
from emberos.tools.base import BaseTool, ToolManifest, ToolParameter, ToolResult
from emberos.tools.registry import register_tool

@register_tool
class MyTool(BaseTool):
    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="custom.mytool",
            description="My custom tool",
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input value",
                    required=True
                )
            ],
            permissions=["custom:execute"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict) -> ToolResult:
        input_value = params["input"]
        # Your tool logic here
        result = f"Processed: {input_value}"
        
        return ToolResult(
            success=True,
            data={"result": result}
        )
```

### API Usage

```python
from emberos.cli.client import EmberClient

async def main():
    client = EmberClient()
    await client.connect()
    
    result = await client.process_command("find my documents")
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 📊 Performance & Limits

### Execution Limits

- **Tool Timeout:** 60 seconds (configurable)
- **Memory Limit:** 512 MB per tool
- **Max Concurrent Tools:** 5
- **File Reading:** 100 KB default (safety limit)

### Snapshot Limits

- **Max File Size:** 100 MB per file
- **Max Total:** 1 GB per snapshot
- **Retention:** 7 days (auto-cleanup)

### Model Requirements

| Model Quantization | Size | RAM Required | Speed |
|-------------------|------|--------------|-------|
| Q2_K | ~2.5GB | 4GB+ | Fastest |
| Q4_K_M (recommended) | ~4.5GB | 8GB+ | Fast |
| Q5_K_M | ~5.5GB | 10GB+ | Medium |
| Q8_0 | ~8GB | 16GB+ | Slower |

---

## 📚 Documentation

- **[INSTALL.md](INSTALL.md)** - Complete installation guide for Arch Linux
- **[USER_GUIDE.md](USER_GUIDE.md)** - User manual with examples and workflows

---

## 📄 License

EmberOS is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See the LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

- **Report bugs:** https://github.com/emberos/emberos/issues
- **Submit PRs:** https://github.com/emberos/emberos/pulls
- **Discussions:** https://github.com/emberos/emberos/discussions

---

## 🙏 Acknowledgments

EmberOS is built on the shoulders of giants:

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Local LLM inference
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) - Vision-language model

---

## 🎯 Project Status

**Current Version:** 1.0.0

**Status:** Production Ready ✅

**What's Working:**
- ✅ Complete CRUD operations (Files, Notes, Tasks)
- ✅ Full workflow pipeline (8 steps)
- ✅ Interrupt & rollback functionality
- ✅ File attachments
- ✅ Context gathering
- ✅ LLM planning
- ✅ Permission system
- ✅ Memory storage (SQLite + ChromaDB)
- ✅ GUI & CLI interfaces
- ✅ Systemd service integration
- ✅ D-Bus IPC

**Coming Soon:**
- Vision analysis (image understanding)
- Calendar integration
- Email drafting
- Code generation
- Web search
- Custom workflows

---

**🔥 EmberOS - Your local, private, intelligent companion for Linux**

