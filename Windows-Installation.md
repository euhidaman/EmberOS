# EmberOS Windows Installation Guide

This guide covers installing and running EmberOS on Windows 10/11.

## System Requirements

- Windows 10 (version 1903+) or Windows 11
- 8GB RAM minimum (16GB recommended for vision model)
- 10GB free disk space for models
- Internet connection (for downloading models)

## One-Click Installation (Recommended)

### Just Double-Click to Install!

1. Download or clone the EmberOS repository
2. **Double-click `EmberOS-Install.bat`**
3. Follow the on-screen prompts

**That's it!** The installer automatically:
- ✅ Installs Python 3.12 (if not found)
- ✅ Installs llama.cpp (if not found)
- ✅ Creates virtual environment
- ✅ Installs EmberOS with all dependencies
- ✅ Creates Start Menu shortcut
- ✅ Adds EmberOS to PATH
- ✅ Optionally downloads AI models

### What You'll See:

```
╔══════════════════════════════════════════════════════════════╗
║  EmberOS Windows Installer v1.0.0                            ║
║  ================================                            ║
║                                                              ║
║  [Step 1/6] Checking for Python...                          ║
║    [OK] Found Python 3.12                                   ║
║                                                              ║
║  [Step 2/6] Checking for llama.cpp...                       ║
║    Installing llama.cpp...                                  ║
║    [OK] llama.cpp installed                                 ║
║                                                              ║
║  [Step 3/6] Creating directories...                         ║
║    [OK] Directories created                                 ║
║                                                              ║
║  [Step 4/6] Setting up EmberOS...                           ║
║    [OK] EmberOS installed                                   ║
║                                                              ║
║  [Step 5/6] Creating launchers and shortcuts...             ║
║    [OK] Launchers and shortcuts created                     ║
║                                                              ║
║  [Step 6/6] AI Models Setup                                 ║
║    Would you like to download the AI models now? (Y/N):     ║
╚══════════════════════════════════════════════════════════════╝
```

## Alternative Installation Methods

### Option 1: PowerShell Script (More Options)

```powershell
# Clone and run
git clone https://github.com/emberos/emberos
cd emberos
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install_windows.ps1 -InstallPython -InstallLlamaCpp
```

### Option 2: Build GUI Installer EXE

If you want a traditional GUI wizard installer:

```powershell
pip install pyinstaller PyQt6
python installer/build_installer.py
# Run: installer/dist/EmberOS-Setup.exe
```

## After Installation

### Starting EmberOS

Open a **new** terminal (Command Prompt or PowerShell) and run:

```cmd
:: Start the AI servers (run once, keeps running in background)
ember-llm

:: Start the EmberOS daemon
emberd

:: Launch the GUI
ember-ui
```

Or simply use the **Start Menu → EmberOS** shortcut!

### Quick Test

```cmd
ember --help
```

### Step 2: Install llama.cpp

**Option A: Using the Installer Script**
```powershell
.\install_windows.ps1 -InstallLlamaCpp
```

**Option B: Download Pre-built**
1. Go to https://github.com/ggerganov/llama.cpp/releases
2. Download the latest Windows release (e.g., `llama-bXXXX-bin-win-avx2-x64.zip`)
3. Extract to `C:\llama.cpp\`
4. Add to PATH:
   ```powershell
   [Environment]::SetEnvironmentVariable("PATH", "$env:PATH;C:\llama.cpp", "User")
   ```

**Option C: Use Winget**
```powershell
winget install llama.cpp
```

### Step 3: Run the Installer

Open PowerShell in the EmberOS directory and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install_windows.ps1
```

The installer will:
- Create a virtual environment
- Install all Python dependencies
- Download the LLM models (~6GB total)
- Create Start Menu shortcuts
- Configure auto-start (optional)

### Step 4: Start EmberOS

After installation, restart your terminal, then:

```powershell
# Start the LLM servers (run in background)
ember-llm

# Start the EmberOS daemon
emberd

# Launch the GUI (or use Start Menu)
ember-ui
```

## Advanced: Manual Installation Without Scripts

If you prefer complete manual control:

### 1. Create Virtual Environment

```powershell
cd D:\BabyLM\EmberOS
python -m venv $env:LOCALAPPDATA\EmberOS\venv
$env:LOCALAPPDATA\EmberOS\venv\Scripts\Activate.ps1
pip install --upgrade pip
```

### 2. Install EmberOS Package

```powershell
pip install -e .[documents]
```

### 3. Download Models

```powershell
# Vision model (~5GB)
huggingface-cli download PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF qwen2.5-vl-7b-instruct-q4_k_m.gguf --local-dir $env:LOCALAPPDATA\EmberOS\models

# BitNet text model (~1.2GB)
huggingface-cli download microsoft/bitnet-b1.58-2B-4T-gguf ggml-model-i2_s.gguf --local-dir $env:LOCALAPPDATA\EmberOS\models\bitnet
```

### 4. Start LLM Servers Manually

Terminal 1 - Vision Model:
```powershell
llama-server --model $env:LOCALAPPDATA\EmberOS\models\qwen2.5-vl-7b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 11434 --ctx-size 8192 --threads 4
```

Terminal 2 - BitNet Model:
```powershell
llama-server --model $env:LOCALAPPDATA\EmberOS\models\bitnet\ggml-model-i2_s.gguf --host 127.0.0.1 --port 38080 --ctx-size 4096 --threads 4
```

### 5. Start Daemon and GUI

Terminal 3:
```powershell
$env:LOCALAPPDATA\EmberOS\venv\Scripts\Activate.ps1
emberd
```

Terminal 4:
```powershell
$env:LOCALAPPDATA\EmberOS\venv\Scripts\Activate.ps1
ember-ui
```

## Configuration

Configuration file location: `%APPDATA%\EmberOS\emberos.toml`

Key settings:

```toml
[llm]
timeout = 120
text_port = 38080    # BitNet text model
vision_port = 11434  # Qwen2.5-VL vision model

[gui]
theme = "dark"       # or "light"
opacity = 0.95
window_width = 900
window_height = 700
always_on_top = false
show_in_tray = true
```

## File Locations

| Item | Location |
|------|----------|
| Installation | `%LOCALAPPDATA%\EmberOS\` |
| Configuration | `%APPDATA%\EmberOS\emberos.toml` |
| Models | `%LOCALAPPDATA%\EmberOS\models\` |
| Logs | `%LOCALAPPDATA%\EmberOS\logs\` |
| Database | `%LOCALAPPDATA%\EmberOS\ember.db` |
| Vectors | `%LOCALAPPDATA%\EmberOS\vectors\` |

## Usage Examples

### Create Documents

```
Create a budget spreadsheet with columns for Date, Description, Amount, Category
```

```
Write a formal letter to HR requesting vacation time
```

```
Create a markdown file with meeting notes from today
```

### Read Documents

```
Summarize this PDF [drag and drop file]
```

```
What's in my Downloads folder?
```

```
Read and explain the contents of report.docx
```

### File Operations

```
Organize my Downloads folder by file type
```

```
Find all PDF files in Documents
```

```
Search for files containing "budget" in my home directory
```

## Troubleshooting

### "llama-server not found"

Ensure llama.cpp is installed and in your PATH:
```powershell
where llama-server
```

If not found, add it:
```powershell
[Environment]::SetEnvironmentVariable("PATH", "$env:PATH;C:\path\to\llama.cpp", "User")
```

### "Connection refused" errors

Check if the LLM servers are running:
```powershell
curl http://127.0.0.1:11434/health
curl http://127.0.0.1:38080/health
```

### "Python not found"

Ensure Python is in PATH:
```powershell
python --version
```

If not working, reinstall Python with "Add to PATH" checked.

### GUI doesn't start

Try running from command line to see errors:
```powershell
$env:LOCALAPPDATA\EmberOS\venv\Scripts\python.exe -m emberos.gui
```

### Performance Issues

1. Reduce context size:
   ```powershell
   llama-server --ctx-size 4096 ...  # instead of 8192
   ```

2. Use fewer threads:
   ```powershell
   llama-server --threads 2 ...
   ```

3. Use only the BitNet model for faster responses (text-only tasks)

## Uninstallation

1. Remove files:
   ```powershell
   Remove-Item -Recurse -Force $env:LOCALAPPDATA\EmberOS
   Remove-Item -Recurse -Force $env:APPDATA\EmberOS
   ```

2. Remove from PATH (via System Properties > Environment Variables)

3. Remove Start Menu shortcut:
   ```powershell
   Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EmberOS.lnk"
   ```

4. Remove scheduled task:
   ```powershell
   schtasks /Delete /TN "EmberOS\EmberDaemon" /F
   ```

## GPU Acceleration (Optional)

For NVIDIA GPUs:

1. Install CUDA Toolkit
2. Download llama.cpp with CUDA support
3. Start with GPU layers:
   ```powershell
   llama-server --model ... --n-gpu-layers 35
   ```

For AMD GPUs:

1. Install ROCm
2. Download llama.cpp with ROCm support
3. Start with GPU layers:
   ```powershell
   llama-server --model ... --n-gpu-layers 35
   ```

## Support

- GitHub Issues: https://github.com/emberos/emberos/issues
- Documentation: https://docs.emberos.org

