# EmberOS Windows Installation Guide

This guide covers installing and running EmberOS on Windows 10/11.

## System Requirements

- Windows 10 (version 1903+) or Windows 11
- 8GB RAM minimum (16GB recommended for vision model)
- 10GB free disk space for models
- Internet connection (for downloading models)

## Quick Installation (Recommended)

### Option 1: Use the Installer EXE (Easiest)

1. Download `EmberOS-Setup.exe` from the [Releases page](https://github.com/emberos/emberos/releases)
2. Run the installer
3. Follow the wizard:
   - The installer will automatically install Python if not found
   - The installer will automatically install llama.cpp if not found
   - Choose which AI models to download
   - Select installation options (shortcuts, auto-start, etc.)
4. Click "Install" and wait for completion
5. Launch EmberOS from the Start Menu or run `ember-ui`

The installer handles everything automatically:
- ✅ Python 3.12 installation
- ✅ llama.cpp installation  
- ✅ Virtual environment setup
- ✅ AI model downloads
- ✅ Start Menu shortcuts
- ✅ PATH configuration
- ✅ Auto-start setup (optional)

### Option 2: Build the Installer Yourself

If you want to build the installer from source:

```powershell
# Clone the repository
git clone https://github.com/emberos/emberos
cd emberos

# Install PyInstaller
pip install pyinstaller PyQt6

# Build the installer
python installer/build_installer.py

# The installer will be at: installer/dist/EmberOS-Setup.exe
```

### Option 3: PowerShell Script

```powershell
# Clone and run the PowerShell installer
git clone https://github.com/emberos/emberos
cd emberos

# Run installer (will install Python if needed)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install_windows.ps1 -InstallPython -InstallLlamaCpp
```

## Manual Installation

If you prefer manual control, follow these steps:

### Step 1: Install Python

**Option A: Using Winget (Recommended - Automatic)**

Open PowerShell as Administrator and run:
```powershell
# Install Python 3.12 automatically
winget install Python.Python.3.12

# Restart your terminal after installation, then verify:
python --version
```

**Option B: Using the Installer Script**

Our installer can download and install Python for you:
```powershell
# Run with -InstallPython flag
.\install_windows.ps1 -InstallPython
```

**Option C: Manual Download**

1. Download Python 3.12 from https://www.python.org/downloads/
2. During installation, CHECK "Add Python to PATH" ✅
3. Verify installation:
   ```powershell
   python --version
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

