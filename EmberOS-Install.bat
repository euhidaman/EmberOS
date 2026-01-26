@echo off
:: ============================================================
:: EmberOS Windows Installer - One-Click Setup
:: ============================================================
:: Just double-click this file to install EmberOS!
:: No Python or other tools required - everything is automatic.
:: ============================================================

title EmberOS Installer v1.0.0
color 0E

echo.
echo   ███████ ███    ███ ██████  ███████ ██████   ██████  ███████
echo   ██      ████  ████ ██   ██ ██      ██   ██ ██    ██ ██
echo   █████   ██ ████ ██ ██████  █████   ██████  ██    ██ ███████
echo   ██      ██  ██  ██ ██   ██ ██      ██   ██ ██    ██      ██
echo   ███████ ██      ██ ██████  ███████ ██   ██  ██████  ███████
echo.
echo   EmberOS Windows Installer v1.0.0
echo   ================================
echo.
echo   This installer will set up EmberOS on your Windows PC.
echo   Everything is automatic - just follow the prompts!
echo.
pause

:: Check for admin rights (optional, for some features)
net session >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Running with administrator privileges
) else (
    echo   [INFO] Running without admin rights (some features may be limited)
)
echo.

:: Set installation directories
set "EMBER_DIR=%LOCALAPPDATA%\EmberOS"
set "CONFIG_DIR=%APPDATA%\EmberOS"
set "MODEL_DIR=%EMBER_DIR%\models"
set "TEMP_DIR=%TEMP%\EmberOS_Install"

:: Create temp directory
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 1: Check/Install Python
:: ============================================================
echo [Step 1/6] Checking for Python...

where python >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo   Found Python %PYVER%

    :: Check if version is 3.11+
    python -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>nul
    if %errorlevel% == 0 (
        echo   [OK] Python version is compatible
        set "PYTHON_CMD=python"
        goto :python_ok
    ) else (
        echo   [WARNING] Python version too old, need 3.11+
    )
)

echo   Python 3.11+ not found. Installing Python 3.12...
echo.

:: Try winget first
where winget >nul 2>&1
if %errorlevel% == 0 (
    echo   Using winget to install Python...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements -h
    if %errorlevel% == 0 (
        echo   [OK] Python installed via winget
        echo.
        echo   *** IMPORTANT: Please close this window and run the installer again ***
        echo   *** This is needed for Python to be available in PATH ***
        echo.
        pause
        exit /b 0
    )
)

:: Download Python installer
echo   Downloading Python 3.12 installer...
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PYTHON_INSTALLER=%TEMP_DIR%\python-installer.exe"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}"

if not exist "%PYTHON_INSTALLER%" (
    echo   [ERROR] Failed to download Python installer
    echo   Please install Python manually from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Running Python installer (this may take a minute)...
echo   *** IMPORTANT: If a dialog appears, make sure "Add to PATH" is checked! ***
"%PYTHON_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0

if %errorlevel% neq 0 (
    echo   [ERROR] Python installation failed
    pause
    exit /b 1
)

del "%PYTHON_INSTALLER%" 2>nul

echo   [OK] Python installed successfully
echo.
echo   *** IMPORTANT: Please close this window and run the installer again ***
echo   *** This is needed for Python to be available in PATH ***
echo.
pause
exit /b 0

:python_ok
echo.

:: ============================================================
:: STEP 2: Check/Install llama.cpp
:: ============================================================
echo [Step 2/6] Checking for llama.cpp...

where llama-server >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] llama-server found
    goto :llama_ok
)

echo   llama-server not found. Installing llama.cpp...
set "LLAMA_DIR=C:\llama.cpp"
set "LLAMA_URL=https://github.com/ggerganov/llama.cpp/releases/download/b4598/llama-b4598-bin-win-avx2-x64.zip"
set "LLAMA_ZIP=%TEMP_DIR%\llama-cpp.zip"

echo   Downloading llama.cpp...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%LLAMA_URL%' -OutFile '%LLAMA_ZIP%'}"

if not exist "%LLAMA_ZIP%" (
    echo   [WARNING] Failed to download llama.cpp
    echo   You can install it manually later from: https://github.com/ggerganov/llama.cpp/releases
    goto :llama_skip
)

echo   Extracting to %LLAMA_DIR%...
if exist "%LLAMA_DIR%" rmdir /s /q "%LLAMA_DIR%"
powershell -Command "Expand-Archive -Path '%LLAMA_ZIP%' -DestinationPath '%LLAMA_DIR%' -Force"
del "%LLAMA_ZIP%" 2>nul

:: Add to PATH
echo   Adding llama.cpp to PATH...
powershell -Command "[Environment]::SetEnvironmentVariable('PATH', '%LLAMA_DIR%;' + [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')"
set "PATH=%LLAMA_DIR%;%PATH%"

echo   [OK] llama.cpp installed

:llama_ok
:llama_skip
echo.

:: ============================================================
:: STEP 3: Create directories
:: ============================================================
echo [Step 3/6] Creating directories...

if not exist "%EMBER_DIR%" mkdir "%EMBER_DIR%"
if not exist "%EMBER_DIR%\tools" mkdir "%EMBER_DIR%\tools"
if not exist "%EMBER_DIR%\vectors" mkdir "%EMBER_DIR%\vectors"
if not exist "%EMBER_DIR%\backups" mkdir "%EMBER_DIR%\backups"
if not exist "%EMBER_DIR%\logs" mkdir "%EMBER_DIR%\logs"
if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"
if not exist "%MODEL_DIR%\bitnet" mkdir "%MODEL_DIR%\bitnet"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

echo   [OK] Directories created
echo.

:: ============================================================
:: STEP 4: Create virtual environment and install EmberOS
:: ============================================================
echo [Step 4/6] Setting up EmberOS...

set "VENV_DIR=%EMBER_DIR%\venv"
set "PIP=%VENV_DIR%\Scripts\pip.exe"
set "PYTHON_VENV=%VENV_DIR%\Scripts\python.exe"

:: Create venv if needed
if not exist "%VENV_DIR%" (
    echo   Creating virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
)

echo   Upgrading pip...
"%PIP%" install --upgrade pip -q

:: Get the script directory (where EmberOS source is)
set "SCRIPT_DIR=%~dp0"

:: Check if we're in the EmberOS source directory
if exist "%SCRIPT_DIR%pyproject.toml" (
    echo   Installing EmberOS from source...
    "%PIP%" install -e "%SCRIPT_DIR%[documents]" -q
) else (
    echo   [ERROR] EmberOS source not found!
    echo   Please run this installer from the EmberOS directory.
    pause
    exit /b 1
)

echo   [OK] EmberOS installed
echo.

:: ============================================================
:: STEP 5: Create launcher scripts and shortcuts
:: ============================================================
echo [Step 5/6] Creating launchers and shortcuts...

:: Create ember.cmd
(
echo @echo off
echo "%VENV_DIR%\Scripts\python.exe" -m emberos.cli %%*
) > "%EMBER_DIR%\ember.cmd"

:: Create ember-ui.cmd
(
echo @echo off
echo start "" "%VENV_DIR%\Scripts\pythonw.exe" -m emberos.gui %%*
) > "%EMBER_DIR%\ember-ui.cmd"

:: Create emberd.cmd
(
echo @echo off
echo "%VENV_DIR%\Scripts\python.exe" -m emberos.daemon %%*
) > "%EMBER_DIR%\emberd.cmd"

:: Create ember-llm.cmd (LLM server manager)
(
echo @echo off
echo setlocal
echo.
echo set "VISION_MODEL=%MODEL_DIR%\qwen2.5-vl-7b-instruct-q4_k_m.gguf"
echo set "BITNET_MODEL=%MODEL_DIR%\bitnet\ggml-model-i2_s.gguf"
echo.
echo echo Starting EmberOS LLM servers...
echo.
echo if exist "%%VISION_MODEL%%" ^(
echo     echo Starting Vision model on port 11434...
echo     start "EmberOS-Vision" /min llama-server --model "%%VISION_MODEL%%" --host 127.0.0.1 --port 11434 --ctx-size 8192 --threads 4
echo ^) else ^(
echo     echo [WARNING] Vision model not found
echo ^)
echo.
echo if exist "%%BITNET_MODEL%%" ^(
echo     echo Starting BitNet model on port 38080...
echo     start "EmberOS-BitNet" /min llama-server --model "%%BITNET_MODEL%%" --host 127.0.0.1 --port 38080 --ctx-size 4096 --threads 4
echo ^) else ^(
echo     echo [WARNING] BitNet model not found
echo ^)
echo.
echo echo LLM servers started!
) > "%EMBER_DIR%\ember-llm.cmd"

:: Add EmberOS to PATH
echo   Adding EmberOS to PATH...
powershell -Command "[Environment]::SetEnvironmentVariable('PATH', '%EMBER_DIR%;' + [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')"

:: Create Start Menu shortcut
echo   Creating Start Menu shortcut...
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\EmberOS.lnk'); $s.TargetPath = '%EMBER_DIR%\ember-ui.cmd'; $s.WorkingDirectory = '%EMBER_DIR%'; $s.Description = 'EmberOS - AI Desktop Assistant'; $s.Save()"

echo   [OK] Launchers and shortcuts created
echo.

:: ============================================================
:: STEP 6: Download AI Models (Optional)
:: ============================================================
echo [Step 6/6] AI Models Setup
echo.
echo   EmberOS uses two AI models:
echo   - Vision Model (Qwen2.5-VL): ~5 GB - for images, PDFs, screenshots
echo   - BitNet Model: ~1.2 GB - for fast text responses
echo.

set /p DOWNLOAD_MODELS="Would you like to download the AI models now? (Y/N): "
if /i "%DOWNLOAD_MODELS%"=="Y" (
    echo.
    echo   Installing huggingface_hub...
    "%PIP%" install huggingface_hub -q

    echo.
    echo   Downloading BitNet model (~1.2 GB)...
    "%PYTHON_VENV%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='microsoft/bitnet-b1.58-2B-4T-gguf', filename='ggml-model-i2_s.gguf', local_dir=r'%MODEL_DIR%\bitnet')"

    echo.
    set /p DOWNLOAD_VISION="Download Vision model too? (~5 GB, takes longer) (Y/N): "
    if /i "!DOWNLOAD_VISION!"=="Y" (
        echo   Downloading Vision model (~5 GB)...
        "%PYTHON_VENV%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF', filename='qwen2.5-vl-7b-instruct-q4_k_m.gguf', local_dir=r'%MODEL_DIR%')"
    )

    echo   [OK] Models downloaded
) else (
    echo   Skipping model download. You can download them later with:
    echo   ember-download-models
)

:: ============================================================
:: DONE!
:: ============================================================
echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo   EmberOS has been installed successfully!
echo.
echo   To get started:
echo   1. Open a NEW terminal window (for PATH changes)
echo   2. Run: ember-llm     (to start the AI servers)
echo   3. Run: emberd        (to start the daemon)
echo   4. Run: ember-ui      (to launch the GUI)
echo.
echo   Or use the Start Menu shortcut: EmberOS
echo.
echo   Installation location: %EMBER_DIR%
echo   Models location: %MODEL_DIR%
echo.

set /p LAUNCH_NOW="Would you like to launch EmberOS now? (Y/N): "
if /i "%LAUNCH_NOW%"=="Y" (
    echo.
    echo   Starting EmberOS...
    start "" "%EMBER_DIR%\ember-ui.cmd"
)

echo.
echo   Thank you for installing EmberOS!
echo.
pause

