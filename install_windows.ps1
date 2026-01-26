# EmberOS Windows Installation Script
# PowerShell script for installing EmberOS on Windows 10/11
# Run as Administrator if needed

param(
    [switch]$Force,
    [switch]$SkipModelDownload,
    [string]$ModelPath = ""
)

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

$EMBER_VERSION = "1.0.0"
$EMBER_DIR = "$env:LOCALAPPDATA\EmberOS"
$CONFIG_DIR = "$env:APPDATA\EmberOS"
$MODEL_DIR = "$EMBER_DIR\models"
$VENV_DIR = "$EMBER_DIR\venv"
$LOG_DIR = "$EMBER_DIR\logs"

# Banner
Write-ColorText @"

  ███████ ███    ███ ██████  ███████ ██████   ██████  ███████
  ██      ████  ████ ██   ██ ██      ██   ██ ██    ██ ██
  █████   ██ ████ ██ ██████  █████   ██████  ██    ██ ███████
  ██      ██  ██  ██ ██   ██ ██      ██   ██ ██    ██      ██
  ███████ ██      ██ ██████  ███████ ██   ██  ██████  ███████

"@ -Color DarkYellow

Write-ColorText "EmberOS Windows Installer v$EMBER_VERSION" -Color Cyan
Write-Host ""

# Check if running as Admin for certain operations
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Step 1: Check Prerequisites
Write-ColorText "Step 1: Checking prerequisites..." -Color Cyan

# Check Python
$pythonCmd = $null
$pythonVersion = $null

foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 11) {
                $pythonCmd = $cmd
                $pythonVersion = "$major.$minor"
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-ColorText "ERROR: Python 3.11+ is required but not found!" -Color Red
    Write-Host ""
    Write-Host "Please install Python from: https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

Write-ColorText "  Found Python $pythonVersion ($pythonCmd)" -Color Green

# Check for llama.cpp (optional - can use Ollama or download)
$llamaServer = $null
$llamaPath = Get-Command "llama-server" -ErrorAction SilentlyContinue
if ($llamaPath) {
    $llamaServer = $llamaPath.Source
    Write-ColorText "  Found llama-server: $llamaServer" -Color Green
} else {
    Write-ColorText "  llama-server not found (will check alternatives)" -Color Yellow
}

# Check for Ollama (alternative)
$ollamaPath = Get-Command "ollama" -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-ColorText "  Found Ollama: $($ollamaPath.Source)" -Color Green
}

# Step 2: Create directories
Write-ColorText "Step 2: Creating directories..." -Color Cyan

$dirs = @(
    $EMBER_DIR,
    "$EMBER_DIR\tools",
    "$EMBER_DIR\vectors",
    "$EMBER_DIR\backups",
    $CONFIG_DIR,
    $MODEL_DIR,
    "$MODEL_DIR\bitnet",
    $LOG_DIR
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-ColorText "  Directories created" -Color Green

# Step 3: Create virtual environment
Write-ColorText "Step 3: Setting up Python virtual environment..." -Color Cyan

if (-not (Test-Path $VENV_DIR) -or $Force) {
    Write-Host "  Creating virtual environment..."
    & $pythonCmd -m venv $VENV_DIR
}

# Activate venv and upgrade pip
$venvPython = "$VENV_DIR\Scripts\python.exe"
$venvPip = "$VENV_DIR\Scripts\pip.exe"

Write-Host "  Upgrading pip..."
& $venvPip install --upgrade pip --quiet

Write-ColorText "  Virtual environment ready" -Color Green

# Step 4: Install EmberOS package
Write-ColorText "Step 4: Installing EmberOS package..." -Color Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path "$scriptDir\pyproject.toml") {
    Write-Host "  Installing from source..."
    & $venvPip install -e "$scriptDir[documents]" --quiet
} else {
    Write-ColorText "ERROR: pyproject.toml not found in $scriptDir" -Color Red
    exit 1
}

Write-ColorText "  EmberOS package installed" -Color Green

# Step 5: Create CLI wrapper scripts
Write-ColorText "Step 5: Creating CLI wrapper scripts..." -Color Cyan

# Create ember.cmd
$emberCmd = @"
@echo off
"$VENV_DIR\Scripts\python.exe" -m emberos.cli %*
"@
Set-Content -Path "$EMBER_DIR\ember.cmd" -Value $emberCmd

# Create ember-ui.cmd
$emberUiCmd = @"
@echo off
"$VENV_DIR\Scripts\pythonw.exe" -m emberos.gui %*
"@
Set-Content -Path "$EMBER_DIR\ember-ui.cmd" -Value $emberUiCmd

# Create emberd.cmd (daemon)
$emberdCmd = @"
@echo off
"$VENV_DIR\Scripts\python.exe" -m emberos.daemon %*
"@
Set-Content -Path "$EMBER_DIR\emberd.cmd" -Value $emberdCmd

# Create LLM server manager script
$llmManagerContent = @'
@echo off
setlocal enabledelayedexpansion

set VISION_MODEL="%LOCALAPPDATA%\EmberOS\models\qwen2.5-vl-7b-instruct-q4_k_m.gguf"
set BITNET_MODEL="%LOCALAPPDATA%\EmberOS\models\bitnet\ggml-model-i2_s.gguf"
set LLAMA_SERVER=llama-server

:: Check for llama-server
where llama-server >nul 2>nul
if errorlevel 1 (
    echo ERROR: llama-server not found in PATH
    echo Please install llama.cpp from: https://github.com/ggerganov/llama.cpp/releases
    exit /b 1
)

:: Start Vision model on port 11434
if exist %VISION_MODEL% (
    echo Starting Qwen2.5-VL vision model on port 11434...
    start "EmberOS-Vision" /min llama-server --model %VISION_MODEL% --host 127.0.0.1 --port 11434 --ctx-size 8192 --threads 4 --n-gpu-layers 0
) else (
    echo WARNING: Vision model not found at %VISION_MODEL%
)

:: Start BitNet model on port 38080
if exist %BITNET_MODEL% (
    echo Starting BitNet text model on port 38080...
    start "EmberOS-BitNet" /min llama-server --model %BITNET_MODEL% --host 127.0.0.1 --port 38080 --ctx-size 4096 --threads 4 --n-gpu-layers 0
) else (
    echo WARNING: BitNet model not found at %BITNET_MODEL%
)

echo LLM servers started.
echo   Vision model: port 11434
echo   BitNet model: port 38080
'@
Set-Content -Path "$EMBER_DIR\ember-llm.cmd" -Value $llmManagerContent

Write-ColorText "  CLI scripts created" -Color Green

# Step 6: Add to PATH
Write-ColorText "Step 6: Configuring PATH..." -Color Cyan

$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$EMBER_DIR*") {
    [Environment]::SetEnvironmentVariable("PATH", "$EMBER_DIR;$userPath", "User")
    Write-ColorText "  Added EmberOS to PATH" -Color Green
    Write-ColorText "  NOTE: Please restart your terminal for PATH changes to take effect" -Color Yellow
} else {
    Write-ColorText "  EmberOS already in PATH" -Color Green
}

# Step 7: Install configuration
Write-ColorText "Step 7: Installing configuration..." -Color Cyan

$configContent = @"
# EmberOS Configuration for Windows
[llm]
timeout = 120
max_retries = 3
default_model = "qwen2.5-vl-7b"

# Port configuration (using less common ports)
text_port = 38080
vision_port = 11434

[gui]
theme = "dark"
opacity = 0.95
window_width = 900
window_height = 700
font_size = 11
always_on_top = false
show_in_tray = true
blur_background = true

[memory]
db_path = "$EMBER_DIR\\ember.db"
vector_path = "$EMBER_DIR\\vectors"
max_entries = 10000

[tools]
user_tools_path = "$EMBER_DIR\\tools"
enable_filesystem = true
enable_applications = true
enable_system = true
enable_documents = true

[permissions]
auto_approve_read = true
auto_approve_low_risk = false
"@
$configContent = $configContent -replace '\\', '\\'
Set-Content -Path "$CONFIG_DIR\emberos.toml" -Value $configContent

Write-ColorText "  Configuration installed" -Color Green

# Step 8: Create Windows Task Scheduler tasks (instead of systemd)
Write-ColorText "Step 8: Setting up auto-start (Task Scheduler)..." -Color Cyan

# Create task XML for EmberOS daemon
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$EMBER_DIR\emberd.cmd</Command>
      <WorkingDirectory>$EMBER_DIR</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$taskXmlPath = "$EMBER_DIR\emberd-task.xml"
Set-Content -Path $taskXmlPath -Value $taskXml

# Register task (requires elevation for some options)
try {
    schtasks /Create /TN "EmberOS\EmberDaemon" /XML $taskXmlPath /F 2>$null
    Write-ColorText "  Auto-start task created" -Color Green
} catch {
    Write-ColorText "  Note: Run as Administrator to enable auto-start" -Color Yellow
}

# Step 9: Create Start Menu shortcut
Write-ColorText "Step 9: Creating Start Menu shortcut..." -Color Cyan

$startMenuPath = [Environment]::GetFolderPath('StartMenu')
$shortcutPath = "$startMenuPath\Programs\EmberOS.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "$EMBER_DIR\ember-ui.cmd"
$Shortcut.WorkingDirectory = $EMBER_DIR
$Shortcut.Description = "EmberOS - AI-Native Desktop Assistant"

# Try to set icon if available
$iconPath = "$scriptDir\assets\zevion-logo.png"
if (Test-Path $iconPath) {
    # Note: .lnk files need .ico, not .png - we'll skip for now
}

$Shortcut.Save()
Write-ColorText "  Start Menu shortcut created" -Color Green

# Step 10: Check for models
Write-ColorText "Step 10: Checking for LLM models..." -Color Cyan

$visionModelPath = "$MODEL_DIR\qwen2.5-vl-7b-instruct-q4_k_m.gguf"
$bitnetModelPath = "$MODEL_DIR\bitnet\ggml-model-i2_s.gguf"

$visionFound = Test-Path $visionModelPath
$bitnetFound = Test-Path $bitnetModelPath

if ($visionFound) {
    Write-ColorText "  Vision model found" -Color Green
} else {
    Write-ColorText "  Vision model NOT found" -Color Yellow
}

if ($bitnetFound) {
    Write-ColorText "  BitNet model found" -Color Green
} else {
    Write-ColorText "  BitNet model NOT found" -Color Yellow
}

# Step 11: Download models if needed
if ((-not $visionFound -or -not $bitnetFound) -and -not $SkipModelDownload) {
    Write-ColorText "Step 11: Downloading models..." -Color Cyan

    # Check for huggingface-cli
    $hfCmd = "$VENV_DIR\Scripts\huggingface-cli.exe"
    if (-not (Test-Path $hfCmd)) {
        Write-Host "  Installing huggingface_hub..."
        & $venvPip install huggingface_hub --quiet
    }

    if (-not $visionFound) {
        Write-Host "  Downloading Qwen2.5-VL vision model (~5GB)..."
        Write-Host "    This may take a while..."
        try {
            & $venvPython -c @"
from huggingface_hub import hf_hub_download
import shutil
import os
model_path = hf_hub_download(
    repo_id='PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF',
    filename='qwen2.5-vl-7b-instruct-q4_k_m.gguf',
    local_dir='$($MODEL_DIR -replace '\\', '/')'
)
print(f'Downloaded to: {model_path}')
"@
            Write-ColorText "    Vision model downloaded" -Color Green
        } catch {
            Write-ColorText "    Failed to download vision model: $_" -Color Red
        }
    }

    if (-not $bitnetFound) {
        Write-Host "  Downloading BitNet model (~1.2GB)..."
        try {
            & $venvPython -c @"
from huggingface_hub import hf_hub_download
import shutil
import os
model_path = hf_hub_download(
    repo_id='microsoft/bitnet-b1.58-2B-4T-gguf',
    filename='ggml-model-i2_s.gguf',
    local_dir='$($MODEL_DIR -replace '\\', '/')/bitnet'
)
print(f'Downloaded to: {model_path}')
"@
            Write-ColorText "    BitNet model downloaded" -Color Green
        } catch {
            Write-ColorText "    Failed to download BitNet model: $_" -Color Red
        }
    }
} elseif ($SkipModelDownload) {
    Write-ColorText "Step 11: Skipping model download (--SkipModelDownload)" -Color Yellow
}

# Step 12: Check for llama.cpp
Write-ColorText "Step 12: Checking for llama.cpp..." -Color Cyan

if (-not $llamaServer) {
    Write-ColorText "  llama-server not found!" -Color Yellow
    Write-Host ""
    Write-Host "  To use EmberOS with local models, install llama.cpp:"
    Write-Host "    Option 1: Download from https://github.com/ggerganov/llama.cpp/releases"
    Write-Host "    Option 2: Use Ollama (https://ollama.ai) with OpenAI-compatible endpoint"
    Write-Host "    Option 3: Build from source with CUDA support"
    Write-Host ""
} else {
    Write-ColorText "  llama-server found: $llamaServer" -Color Green
}

# Done!
Write-Host ""
Write-ColorText "═══════════════════════════════════════════════════════" -Color DarkYellow
Write-ColorText "  EmberOS Windows installation complete!" -Color Green
Write-ColorText "═══════════════════════════════════════════════════════" -Color DarkYellow
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. Restart your terminal (for PATH changes)"
Write-Host ""
Write-Host "  2. Start the LLM servers (if you have llama.cpp):"
Write-Host "     ember-llm"
Write-Host ""
Write-Host "  3. Start the EmberOS daemon:"
Write-Host "     emberd"
Write-Host ""
Write-Host "  4. Launch EmberOS:"
Write-Host "     GUI:  ember-ui"
Write-Host "     CLI:  ember"
Write-Host ""
Write-Host "  5. Or use Start Menu -> EmberOS"
Write-Host ""
Write-ColorText "Model locations:" -Color Cyan
Write-Host "  Vision: $MODEL_DIR\qwen2.5-vl-7b-instruct-q4_k_m.gguf"
Write-Host "  BitNet: $MODEL_DIR\bitnet\ggml-model-i2_s.gguf"
Write-Host ""
Write-ColorText "Configuration: $CONFIG_DIR\emberos.toml" -Color Cyan
Write-Host ""
Write-ColorText "For help: ember --help" -Color Cyan
Write-Host ""

