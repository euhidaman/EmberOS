# EmberOS User Guide

**Version 1.0.0** | An AI-powered desktop assistant for Linux

---

## Table of Contents

1. [What is EmberOS?](#what-is-emberos)
2. [Key Features & Capabilities](#key-features--capabilities)
3. [User Interface Overview](#user-interface-overview)
4. [How to Use EmberOS](#how-to-use-emberos)
5. [Workflow Examples](#workflow-examples)
6. [Understanding the UI Elements](#understanding-the-ui-elements)
7. [Commands & Interactions](#commands--interactions)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)

---

## What is EmberOS?

EmberOS is an **AI-powered desktop assistant** that runs entirely on your local machine. It combines a powerful language model (LLM) with system integration to help you accomplish tasks through natural language.

### Core Philosophy

- **Privacy-First:** Everything runs locally - no cloud, no data sharing
- **Context-Aware:** Remembers your conversations and learns your preferences
- **Action-Oriented:** Doesn't just answer questions - actually does things on your system
- **Seamless Integration:** Works with your desktop environment through D-Bus

---

## Key Features & Capabilities

### 🤖 What EmberOS Can Do (Current Version)

#### ✅ **File Management**
- Search for files by name or content
- Organize files (move, copy, rename)
- Create directories
- Read and analyze file contents
- Get file information (size, type, permissions)

**Example Tasks:**
- "Find all PDFs in my Downloads folder"
- "Create a folder called 'Projects 2024' in my Documents"
- "What's inside budget.txt?"

#### ✅ **Note Taking & Memory**
- Create and save notes
- Search through your notes
- Retrieve notes by topic or keyword
- Organize notes with tags

**Example Tasks:**
- "Remember that the meeting is at 3 PM tomorrow"
- "What did I note about the project deadline?"
- "Create a note: grocery list - milk, eggs, bread"

#### ✅ **System Commands**
- Execute shell commands safely
- Check system status
- Monitor processes
- View system information

**Example Tasks:**
- "What's my disk usage?"
- "Show me running Python processes"
- "What's my system uptime?"

#### ✅ **Application Launching**
- Open applications by name
- Launch files with default applications
- Quick access to common programs

**Example Tasks:**
- "Open Firefox"
- "Launch Spotify"
- "Open my budget spreadsheet"

#### ✅ **Conversational AI**
- Natural language understanding
- Context-aware responses
- Multi-turn conversations
- Task planning and execution

**Example Tasks:**
- "Help me organize my Downloads folder by file type"
- "Explain what this Python script does" (after attaching it)
- "What are the best practices for writing clean code?"

---

### 🚧 What EmberOS Will Do Soon

- **Image Analysis:** Vision capabilities with Qwen2.5-VL model
- **Calendar Integration:** Manage events and reminders
- **Email Drafting:** Compose emails with AI assistance
- **Code Generation:** Generate code snippets and scripts
- **Web Search:** Fetch information from the internet
- **System Automation:** Create custom workflows and macros

---

## User Interface Overview

EmberOS has **two interfaces**: CLI (Terminal) and GUI (Graphical).

### GUI (Graphical Interface)

The GUI features a modern, glassmorphic design with dark/light themes.

```
┌─────────────────────────────────────────────┐
│  [Logo] EmberOS  [Theme] [Min] [Max] [Close] │ ← Title Bar
├─────────────────────────────────────────────┤
│ Context Ribbon (system status, active tools)│
├─────────────────────────────────────────────┤
│                                             │
│         Chat Area                           │ ← Conversation
│         (Messages appear here)              │   History
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│ [📎 Attach Files] (2 files attached)       │ ← Attachment Button
│ ┌─────────────────────────────────────────┐ │
│ │ Type your message here...               │ │
│ │                                         │ │ ← Input Box
│ └─────────────────────────────────────────┘ │
│ [⏸ Interrupt] [↩ Rollback] [Cancel] ...   │ ← Task Control
│ ... [Execute]              [Send ⚡]        │   & Action Buttons
├─────────────────────────────────────────────┤
│ Status: Ready • Model: Qwen2.5-VL-7B       │ ← Status Ticker
└─────────────────────────────────────────────┘
```

### CLI (Terminal Interface)

The CLI provides a clean REPL (Read-Eval-Print Loop) interface:

```
  EmberOS Terminal v1.0.0

  Type :help or press Ctrl+D to exit

ember> your command here
```

---

## Understanding the UI Elements

### Title Bar Components

| Element | Description | Action |
|---------|-------------|--------|
| **🔥 Logo** | EmberOS branding | No action (just branding) |
| **Theme** | Toggle appearance | Click to switch Light/Dark mode |
| **Min** | Minimize window | Click to minimize to taskbar |
| **Max** | Maximize/Restore | Click to fullscreen or restore |
| **Close** | Close application | Click to quit EmberOS |

**💡 Tip:** You can **drag the title bar** to move the window, and **double-click** to maximize/restore.

---

### Input Area Components

#### **Top Button (Above Text Box)**

| Button | Icon | Purpose | Status |
|--------|------|---------|--------|
| **Attach Files** | 📎 | Attach documents/images/code for analysis | ✅ Working |

Click the **"📎 Attach Files"** button to open a file picker where you can select one or multiple files to attach to your message. Supported file types include:
- **Images:** PNG, JPG, JPEG, GIF, BMP, SVG
- **Documents:** PDF, DOC, DOCX, TXT, MD, ODT
- **Spreadsheets:** XLS, XLSX, CSV, ODS
- **Code:** PY, JS, JAVA, CPP, C, H, RS, GO
- **Archives:** ZIP, TAR, GZ, BZ2, 7Z
- **All other file types** are also supported

After attaching files:
- A counter will show: "2 files attached"
- The button changes to "📎 Add More" to add additional files
- Files will be sent along with your message when you click "Send ⚡"

**Note:** Voice input feature has been removed. Type your commands in the text box instead.

---

#### **Bottom Buttons (Below Text Box)**

##### **Task Control Buttons (Left Side)**

| Button | Icon | Purpose | When Enabled |
|--------|------|---------|--------------|
| **Interrupt** | ⏸ | Stop current task immediately | Task is running |
| **Rollback** | ↩ | Undo last operation | Snapshots available |
| **Cancel** | Cancel | Cancel pending operation | Always |

**⏸ Interrupt Button:**
- **Purpose:** Gracefully stop a running task
- **When enabled:** A task is currently executing
- **What it does:**
  - Stops current tool execution
  - Prevents subsequent steps from running
  - Returns partial results
  - Preserves snapshots for rollback
- **Use cases:**
  - Stop a long-running search
  - Cancel a slow file operation
  - Halt before destructive operations

**↩ Rollback Button:**
- **Purpose:** Undo the last operation and restore previous state
- **When enabled:** Task completed and snapshots exist
- **What it does:**
  - Restores files from most recent snapshot
  - Reverses filesystem changes
  - Puts system back to pre-operation state
  - Can rollback multiple times if multiple snapshots exist
- **Use cases:**
  - Undo accidental file deletion
  - Revert file moves
  - Restore overwritten files
  - Fix incorrect bulk operations

**How Snapshots Work:**
- Automatically created before:
  - File deletions
  - File moves/renames
  - File overwrites
  - Bulk operations
- Stored in: `~/.local/share/ember/backups/`
- Retention: 7 days (configurable)
- Includes: Full file backups + metadata

**Example Workflow with Rollback:**
```
1. "Delete all .tmp files in Downloads"
   → Snapshot created
   → 23 files deleted
   
2. [Realize mistake]
   
3. Click "↩ Rollback"
   → All 23 files restored
   → Downloads folder back to original state
```

##### **Action Buttons (Right Side)**

| Button | Purpose | When to Use |
|--------|---------|-------------|
| **Execute** | Run a specific command | For direct system commands (advanced) |
| **Send ⚡** | Submit your message | Main button to send messages (or press Enter) |

---

### Chat Area

The main conversation area where:
- **Your messages** appear on the right (or with a "You:" prefix in CLI)
- **EmberOS responses** appear on the left (or with "Agent:" prefix in CLI)
- **System messages** show task progress and results

---

### Context Ribbon (Top)

Shows real-time information:
- **Active application** you're working in
- **Current tools** being used by EmberOS
- **System context** (clipboard, selected files, etc.)

---

### Status Ticker (Bottom)

Displays:
- Connection status (Connected/Disconnected)
- Current LLM model loaded
- Memory usage
- Task count
- CPU usage

---

## How to Use EmberOS

### Starting EmberOS

#### Launch GUI

```bash
ember-ui
```

Or click **EmberOS** in your application menu.

#### Launch CLI

```bash
ember
```

---

### Basic Workflow

1. **Type your request** in natural language
2. **Press Enter** (or click "Send ⚡")
3. **Review the response** in the chat area
4. **Confirm actions** if prompted (for safety)
5. **Continue the conversation** or start a new task

---

### Input Methods

#### GUI Input

- **Type:** Click in the text box and type
- **Multiline:** Press `Shift + Enter` for new lines
- **Submit:** Press `Enter` or click "Send ⚡"
- **Cancel:** Press `Escape` or click "Cancel"

#### CLI Input

- **Type:** Enter commands at the `ember>` prompt
- **Submit:** Press `Enter`
- **Exit:** Press `Ctrl+D` or type `:exit`
- **Help:** Type `:help`

---

### Special CLI Commands

| Command | Description |
|---------|-------------|
| `:help` | Show help message |
| `:status` | Show system and model status |
| `:clear` | Clear screen |
| `:exit` or `:quit` | Exit EmberOS |
| `:theme <dark\|light>` | Change theme |

---

## Workflow Examples

### Example 1: Finding Files

**Task:** Find all Python files modified in the last week

```
You: Find Python files modified in the last 7 days

EmberOS: I'll search for Python files modified recently.
         Found 15 Python files:
         
         1. ~/projects/bot/main.py (modified 2 days ago)
         2. ~/Downloads/script.py (modified 5 days ago)
         ...
         
         Would you like me to organize them or show details?

You: Move them to ~/projects/python-files/

EmberOS: I'll move 15 files to ~/projects/python-files/
         [Creates directory if needed]
         ✓ Moved main.py
         ✓ Moved script.py
         ...
         Done! All 15 files moved successfully.
```

---

### Example 2: Taking Notes

**Task:** Save information for later

```
You: Remember that the password for the WiFi is "GuestNetwork2024"

EmberOS: I've saved that note. You can retrieve it later by asking
         about WiFi passwords or guest network.
         
         Note ID: #1234
         Tags: password, wifi, network

You: What was the WiFi password?

EmberOS: The WiFi password is: GuestNetwork2024
         (From note #1234, saved 5 minutes ago)
```

---

### Example 3: System Commands

**Task:** Check disk space

```
You: How much disk space do I have left?

EmberOS: I'll check your disk usage.
         
         Filesystem      Size  Used  Avail Use%
         /dev/sda1       500G  320G   180G  64%
         /dev/sdb1       1.0T  750G   250G  75%
         
         Your main drive (/dev/sda1) has 180GB available.
```

---

### Example 4: Multi-Step Task

**Task:** Organize downloads by file type

```
You: Organize my Downloads folder by file type

EmberOS: I'll analyze your Downloads folder and create organized 
         subdirectories.
         
         Found:
         - 25 PDFs
         - 18 images (jpg, png)
         - 12 documents (docx, txt)
         - 8 videos (mp4, mkv)
         - 15 archives (zip, tar.gz)
         
         I'll create:
         ~/Downloads/PDFs/
         ~/Downloads/Images/
         ~/Downloads/Documents/
         ~/Downloads/Videos/
         ~/Downloads/Archives/
         
         Proceed? (yes/no)

You: yes

EmberOS: Moving files...
         ✓ Created directories
         ✓ Moved 25 PDFs
         ✓ Moved 18 images
         ✓ Moved 12 documents
         ✓ Moved 8 videos
         ✓ Moved 15 archives
         
         Done! Your Downloads folder is now organized.
```

---

### Example 5: Application Launching

**Task:** Open an application

```
You: Open Firefox

EmberOS: Launching Firefox...
         ✓ Firefox started successfully (PID: 12345)

You: Also open Spotify

EmberOS: Launching Spotify...
         ✓ Spotify started successfully (PID: 12346)
```

---

### Example 6: File Attachment & Analysis

**Task:** Analyze a document or image

```
[Click "📎 Attach Files" button]
[Select: report.pdf, chart.png]

You: Summarize this report and explain the chart

EmberOS: Analyzing attached files...
         
         **report.pdf Summary:**
         This Q4 report shows revenue growth of 23% YoY,
         driven primarily by new product launches. Key highlights:
         - Revenue: $2.3M (↑23%)
         - Customers: 15,000 (↑18%)
         - Retention: 94%
         
         **chart.png Analysis:**
         The bar chart shows monthly revenue trends with a clear
         upward trajectory from September to December, with December
         showing the highest revenue at $680K.
         
         Overall assessment: Strong quarter with positive momentum.
```

---

## Document Creation Guide

### Overview

EmberOS can create professional documents in multiple formats with AI-generated content. Simply describe what you want, and EmberOS will generate the content and save it in your preferred format.

### Supported Formats

| Format | Extension | Use Cases | Features |
|--------|-----------|-----------|----------|
| **Plain Text** | `.txt` | Quick notes, logs, simple lists | Fast, lightweight, universal compatibility |
| **Markdown** | `.md` | Technical docs, README files, formatted notes | Supports headings, code blocks, lists, links |
| **PDF** | `.pdf` | Reports, presentations, formal documents | Professional layout, title formatting, paragraph spacing |
| **Word** | `.docx` | Business docs, proposals, collaborative editing | Microsoft Word compatible, centered titles, justified text |

### How Document Creation Works

#### Step 1: Request a Document

Use natural language to describe what you want:

```
create [format] document about [topic]
```

**Examples:**
- "create pdf document about renewable energy"
- "create a word document about artificial intelligence"
- "make a markdown file about Python programming"
- "generate a txt document about healthy eating"

#### Step 2: Specify Filename and Location

EmberOS will ask for:
1. **Filename:** What to name the file
2. **Location:** Where to save it

**Response format:**
```
filename.ext in Location
```

**Examples:**
- "energy_report.pdf in Documents"
- "ai_guide.docx in Desktop"
- "python_notes.md in ~/projects"
- "health_tips.txt in Downloads"

**Common Locations:**
- `Desktop` → `~/Desktop/`
- `Downloads` → `~/Downloads/`
- `Documents` → `~/Documents/`
- `Pictures`, `Videos`, `Music` → Standard user folders
- Custom paths: Use full path like `~/work/reports`

#### Step 3: Content Generation

EmberOS will:
1. Generate content based on your topic using AI
2. Format it appropriately for the chosen format
3. Save the file to your specified location
4. Show you a preview of the content

### Content Length Control

You can specify how long you want the document to be:

| Length | Words | Use Cases |
|--------|-------|-----------|
| **Short** | ~75 | Summaries, overviews, quick references |
| **Medium** | ~150 | Standard explanations, introductions (default) |
| **Long** | ~300 | Detailed guides, comprehensive articles |

**Examples:**
- "create a **short** pdf about quantum physics"
- "create a **long** word document about climate change"
- "make a **brief** markdown guide about Git"

### Format-Specific Features

#### Plain Text (.txt)
- Simple, universal format
- No special formatting
- Best for: notes, logs, simple lists, code snippets

```
Example output:
Machine learning is a subset of artificial intelligence...
[Plain text continues...]
```

#### Markdown (.md)
- Formatted text with Markdown syntax
- Title as H1 heading (`# Title`)
- Supports: headings, lists, code blocks, links
- Best for: technical documentation, README files, GitHub

```
Example output:
# Python Programming

Python is a high-level programming language...
[Markdown formatting continues...]
```

#### PDF (.pdf)
- Professional document format
- Features:
  - Centered title (18pt, Heading style)
  - Proper paragraph spacing
  - Justified text alignment
  - Page layout with margins
- Best for: reports, presentations, formal documents

```
Example output:
[Centered Title]
Types of Oceans

Oceans cover approximately 71% of Earth's surface...
[Professional PDF formatting]
```

#### Word (.docx)
- Microsoft Word compatible format
- Features:
  - Centered title (Heading 1 style)
  - Justified paragraphs
  - 12pt spacing between paragraphs
  - Professional formatting
- Best for: business documents, proposals, collaborative editing

```
Example output:
[Centered Title]
Artificial Intelligence

Artificial Intelligence refers to computer systems...
[Word document formatting]
```

### Advanced Usage

#### Multiple Documents on Same Topic

Create different formats for the same content:

```
You: create pdf document about machine learning

[Specify filename/location]

You: now create a word version of the same topic

[Specify filename/location]
```

#### Custom Topics with Details

Be specific about what you want covered:

```
"create pdf about types of machine learning algorithms including 
supervised, unsupervised, and reinforcement learning"
```

#### Naming Conventions

Use descriptive filenames:

```
✅ Good:
- "quarterly_sales_report_Q4_2024.pdf"
- "python_beginner_guide.docx"
- "project_proposal_v2.md"

❌ Avoid:
- "document.pdf"
- "file.docx"
- "new file.txt" (spaces cause issues)
```

### Installation Requirements

Document creation requires additional Python libraries:

**Automatically installed** if you used `./install.sh`

**Manual installation** (if needed):
```bash
cd ~/EmberOS
source ~/.local/share/ember/venv/bin/activate
pip install python-docx reportlab
deactivate
systemctl --user restart emberd
```

**Libraries used:**
- `python-docx` → Word (.docx) documents
- `reportlab` → PDF documents
- Built-in Python → TXT and Markdown

### Common Workflows

#### 1. Quick Note
```
create txt document about meeting notes
notes_2024_01_30.txt in Desktop
```

#### 2. Technical Documentation
```
create markdown document about API endpoints
api_documentation.md in ~/projects/docs
```

#### 3. Professional Report
```
create a long pdf document about quarterly performance
Q4_performance_report.pdf in Documents
```

#### 4. Business Proposal
```
create word document about new feature proposal
feature_proposal_v1.docx in ~/work/proposals
```

---

## Commands & Interactions

### Natural Language Commands

EmberOS understands natural language. Here are common patterns:

#### File Operations

```
"Find files named budget in my Documents"
"Delete temporary files in Downloads"
"Create a folder called ProjectX"
"What's inside config.txt?"
"Show me all images in Pictures"
```

#### System Queries

```
"What's my disk usage?"
"How much RAM is available?"
"Show running processes"
"What's my system uptime?"
"Check CPU temperature"
```

#### Notes & Memory

```
"Remember that Sarah's birthday is June 15"
"What did I note about the meeting?"
"Save this: API key is abc123xyz"
"Search my notes for 'password'"
```

#### Application Control

```
"Open Visual Studio Code"
"Launch the browser"
"Start terminal"
"Open calculator"
```

---

## Tips & Best Practices

### 🎯 Getting Better Results

1. **Be Specific:** "Find PDFs in Downloads from last month" is better than "find files"
2. **Use Context:** EmberOS remembers your conversation, so you can refer back
3. **Confirm Actions:** For destructive operations (delete, move), EmberOS will ask for confirmation
4. **Natural Language:** Don't worry about perfect grammar - talk naturally
5. **Document Creation:** 
   - Specify format clearly: "pdf", "word", "markdown", "txt"
   - Control length: Use "short" (75 words), "medium" (150 words), or "long" (300 words)
   - Provide clear topics: "about renewable energy" is better than just "energy"
   - Choose locations wisely: Use common folders (Desktop, Downloads, Documents) or full paths

### 📝 Document Creation Best Practices

1. **Topic Clarity:**
   - ✅ Good: "Create a pdf about types of machine learning algorithms"
   - ❌ Unclear: "Create a document about ML"

2. **Format Selection:**
   - **TXT:** Quick notes, simple lists, plain content
   - **Markdown:** Technical documentation, README files, formatted notes
   - **PDF:** Professional reports, presentations, formal documents
   - **Word:** Business documents, proposals, collaborative editing

3. **Length Guidelines:**
   - **Short (~75 words):** Quick summaries, brief overviews, elevator pitches
   - **Medium (~150 words):** Standard explanations, introductions, descriptions
   - **Long (~300 words):** Detailed guides, comprehensive analyses, full articles

4. **File Naming:**
   - Use descriptive names: "quarterly_report_Q4.pdf" instead of "report.pdf"
   - Avoid spaces in names: Use underscores or hyphens
   - Include version numbers if needed: "proposal_v2.docx"

5. **Location Organization:**
   - **Desktop:** Quick access files, temporary work
   - **Documents:** Permanent storage, organized by project
   - **Downloads:** Files to review or process later
   - Custom folders: Create project-specific directories

### 🔒 Safety Features

- **Permission System:** EmberOS asks before executing potentially dangerous commands
- **Dry Run:** You can preview changes before applying them (use "show me what would happen")
- **Undo Support:** Some operations can be undone (coming soon)
- **Local Only:** Everything stays on your machine

### ⚡ Keyboard Shortcuts (GUI)

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line in input |
| `Escape` | Clear input / Cancel |
| `Ctrl + ,` | Open settings (coming soon) |
| `Ctrl + Q` | Quit application |

### 📋 Using the CLI

**Advantages:**
- Faster for power users
- Works over SSH
- Lower resource usage
- Scriptable

**When to use:**
- Quick queries
- Server management
- Automation scripts
- When GUI is not available

---

## Troubleshooting

### GUI Won't Start

**Problem:** `ember-ui` command not found or window doesn't appear

**Solutions:**

1. Check if services are running:
   ```bash
   systemctl --user status ember-llm
   systemctl --user status emberd
   ```

2. Restart services:
   ```bash
   systemctl --user restart ember-llm
   systemctl --user restart emberd
   ```

3. Reinstall GUI:
   ```bash
   cd ~/EmberOS
   source ~/.local/share/ember/venv/bin/activate
   pip install -e .
   deactivate
   ember-ui
   ```

---

### Window Can't Be Moved (Linux)

**Problem:** Dragging the title bar doesn't move the window

**Solution:**

This is a known issue on some Linux window managers with frameless Qt windows. Try:

1. Restart GUI after pulling latest code:
   ```bash
   cd ~/EmberOS
   git pull
   pkill -f ember-ui
   ember-ui
   ```

2. Use your window manager's move function:
   - **KDE Plasma:** `Alt + F3` → Select "Move" → Use mouse/arrows
   - **KDE Alternative:** Hold `Alt` and drag anywhere on the window
   - **GNOME:** `Super + Click and Drag`
   - **i3/Sway:** `Super + Click and Drag`

3. Maximize the window (it will fit your screen):
   - Double-click the title bar
   - Or click "Max" button

**For KDE Users:**
The `Alt + drag` method works best with KDE Plasma. You can also:
- Right-click title bar → "More Actions" → "Move"
- Use arrow keys after initiating move mode
- Configure window rules in KDE System Settings for EmberOS

---

### EmberOS Says "Daemon Not Running"

**Problem:** CLI or GUI shows "Failed to connect to daemon"

**Solutions:**

1. Start the daemon:
   ```bash
   systemctl --user start emberd
   ```

2. Check logs for errors:
   ```bash
   journalctl --user -u emberd -n 50 --no-pager
   ```

3. Ensure LLM server is running first:
   ```bash
   systemctl --user status ember-llm
   ```

---

### LLM Responses Are Slow

**Problem:** EmberOS takes a long time to respond

**Possible Causes & Solutions:**

1. **CPU-only inference:** Enable GPU acceleration (see INSTALL.md)
2. **Large context:** Restart to clear conversation history
3. **System load:** Close other heavy applications
4. **Model size:** Use a smaller quantization (Q2_K instead of Q4_K_M)

---

### Attach Button Not Working

**Problem:** Clicking "📎 Attach Files" doesn't open file picker

**Solutions:**

1. Restart the GUI:
   ```bash
   pkill -f ember-ui
   ember-ui
   ```

2. Check if you're running the latest version:
   ```bash
   cd ~/EmberOS
   git pull
   source ~/.local/share/ember/venv/bin/activate
   pip install -e .
   deactivate
   ember-ui
   ```

3. If the button is not visible, check your display scaling settings.

---

### Theme Toggle Not Working

**Problem:** Clicking "Theme" button doesn't change appearance

**Solution:**

1. Restart GUI:
   ```bash
   pkill -f ember-ui
   ember-ui
   ```

2. Check if theme is set in config:
   ```bash
   cat ~/.config/ember/emberos.toml | grep theme
   ```

3. Manually set theme in CLI:
   ```bash
   ember
   # Then type: :theme light
   ```

---

### Document Creation Fails

**Problem:** Cannot create PDF or Word documents, getting "library not installed" error

**Solutions:**

1. Install document processing libraries:
   ```bash
   cd ~/EmberOS
   source ~/.local/share/ember/venv/bin/activate
   pip install -e .[documents,vectordb]
   deactivate
   systemctl --user restart emberd
   ```

2. Verify installation:
   ```bash
   source ~/.local/share/ember/venv/bin/activate
   python -c "import docx; import reportlab; print('Libraries installed!')"
   deactivate
   ```

3. If still failing, try reinstalling:
   ```bash
   cd ~/EmberOS
   ./install.sh
   ```

---

### Wrong Document Content

**Problem:** Document created about wrong topic (e.g., asked for "oceans" but got "machine learning")

**Cause:** Old pending state from previous conversation wasn't cleared

**Solution:**

This has been fixed in the latest version. Update EmberOS:
```bash
cd ~/EmberOS
git pull
systemctl --user restart emberd
```

**Workaround:**
- Start a new terminal/GUI session for each document
- Or use different topics in sequence to avoid confusion

---

### File Not Created in Specified Location

**Problem:** Document created in `~/.local/share/ember/` instead of requested location

**Cause:** Target directory is read-only or permission denied

**Solutions:**

1. Check directory permissions:
   ```bash
   ls -ld ~/Downloads ~/Documents ~/Desktop
   ```

2. Update systemd service to allow writes:
   ```bash
   cp ~/EmberOS/packaging/emberd.service ~/.config/systemd/user/emberd.service
   systemctl --user daemon-reload
   systemctl --user restart emberd
   ```

3. Move file manually from fallback location:
   ```bash
   mv ~/.local/share/ember/document.pdf ~/Downloads/
   ```

---

### ChromaDB Warning: "Vector search disabled"

**Problem:** Logs show "ChromaDB not available"

**Explanation:**

You're running Python 3.14, which doesn't have compatible `onnxruntime` yet.

**Impact:**
- Core features work fine
- Only semantic search over notes is disabled

**Solution:**

Use Python 3.12 for full features (see INSTALL.md Step 2.5)

---

## Advanced Usage

### Using EmberOS in Scripts

You can automate tasks by piping to ember:

```bash
echo "Find Python files modified today" | ember
```

### Custom Tools (Coming Soon)

Create your own tools that EmberOS can use:

```bash
~/.local/share/ember/tools/my_custom_tool.py
```

### Configuration

Edit `~/.config/ember/emberos.toml` to customize:

```toml
[gui]
theme = "dark"  # or "light"
opacity = 0.95
window_width = 800
window_height = 600
font_size = 11

[llm]
server_url = "http://127.0.0.1:11434"
default_model = "qwen2.5-vl-7b-instruct-q4_k_m.gguf"
```

---

## What Makes EmberOS Special?

### 🔐 Privacy-First AI

Unlike cloud-based assistants (Alexa, Siri, Google Assistant), EmberOS:
- Runs 100% locally on your machine
- Never sends data to external servers
- No internet required for core functionality
- Your conversations stay private

### 🧠 Context-Aware Intelligence

EmberOS isn't just a chatbot - it understands:
- What you're working on (active window)
- Your file system structure
- Your past conversations
- Your preferences and patterns

### 🛠️ Action-Oriented

Instead of just answering questions, EmberOS:
- Executes system commands
- Manages files and directories
- Launches applications
- Performs multi-step tasks

### 🎨 Beautiful & Modern UI

- Glassmorphic design
- Dark/Light theme support
- Smooth animations
- Responsive layout
- System tray integration

---

## Coming Soon

### Planned Features

- ✅ **Vision Analysis:** Understand images and screenshots
- ✅ **File Attachments:** Drag & drop documents for analysis (NOW AVAILABLE!)
- ✅ **Web Search:** Fetch information from the internet
- ✅ **Calendar Integration:** Manage events and reminders
- ✅ **Email Drafting:** Compose professional emails
- ✅ **Code Generation:** Generate scripts and code snippets
- ✅ **Browser Control:** Automate web browsing tasks
- ✅ **Custom Workflows:** Create macros and automation
- ✅ **Plugin System:** Extend EmberOS with custom tools

---

## Feedback & Support

### Report Issues

Found a bug? Have a feature request?

```bash
# On GitHub
https://github.com/emberos/emberos/issues

# Or check logs
journalctl --user -u emberd -f
```

### Community

- **Discussions:** https://github.com/emberos/emberos/discussions
- **Documentation:** https://docs.emberos.org

---

## Summary: Quick Start

1. **Start EmberOS:** Run `ember-ui` or `ember`
2. **Check status:** Services should show "active (running)"
3. **Type naturally:** "Find my budget spreadsheet"
4. **Press Enter:** EmberOS will respond and take action
5. **Iterate:** Continue the conversation or start a new task

**Most Important Tips:**
- 🗣️ Talk naturally - EmberOS understands context
- 🔄 Use the conversation - refer back to previous messages
- ✅ Review actions - EmberOS asks before doing anything destructive
- 🌓 Toggle theme - Click "Theme" button for Light/Dark mode
- 💾 EmberOS remembers - It learns from your interactions

---

**Enjoy your AI-powered desktop assistant! 🔥**

*EmberOS - Your local, private, intelligent companion for Linux*

