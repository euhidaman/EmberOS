@echo off
setlocal EnableDelayedExpansion
:: ============================================================
:: EmberOS Windows Installer - One-Click Setup
:: ============================================================
:: Just double-click this file to install EmberOS!
:: No Python or other tools required - everything is automatic.
::
:: FULLY SELF-CONTAINED: EmberOS installs its own Python and
:: llama.cpp in isolated directories. It will NOT interfere with
:: any existing Python, Ollama, or other software on your system.
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

:: ============================================================
:: Set installation directories - ALL SELF-CONTAINED
:: ============================================================
set "EMBER_DIR=%LOCALAPPDATA%\EmberOS"
set "CONFIG_DIR=%APPDATA%\EmberOS"
set "MODEL_DIR=%EMBER_DIR%\models"
set "TEMP_DIR=%TEMP%\EmberOS_Install"

:: EmberOS has its OWN Python - completely isolated
set "EMBER_PYTHON_DIR=%EMBER_DIR%\python"
set "EMBER_PYTHON=%EMBER_PYTHON_DIR%\python.exe"
set "EMBER_PIP=%EMBER_PYTHON_DIR%\Scripts\pip.exe"

:: EmberOS has its OWN llama.cpp - completely isolated
set "EMBER_LLAMA_DIR=%EMBER_DIR%\llama.cpp"

:: Virtual environment inside EmberOS directory
set "VENV_DIR=%EMBER_DIR%\venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: Create temp directory
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 1: Install Embedded Python (Self-Contained)
:: ============================================================
echo [Step 1/6] Setting up isolated Python environment...

:: Check if we already have our own Python installed
if exist "%EMBER_PYTHON%" (
    echo   [OK] EmberOS Python already installed
    goto :python_ok
)

echo   Downloading Python 3.12 (embeddable package)...
echo   This will be installed ONLY for EmberOS, not system-wide.
echo.

:: Download Python embeddable package (completely isolated, no system changes)
set "PYTHON_EMBED_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
set "PYTHON_ZIP=%TEMP_DIR%\python-embed.zip"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing}"

if not exist "%PYTHON_ZIP%" (
    echo   [ERROR] Failed to download Python
    echo   Please check your internet connection and try again.
    pause
    exit /b 1
)

:: Create EmberOS directory and extract Python
echo   Extracting Python to EmberOS directory...
if not exist "%EMBER_DIR%" mkdir "%EMBER_DIR%"
if not exist "%EMBER_PYTHON_DIR%" mkdir "%EMBER_PYTHON_DIR%"

powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%EMBER_PYTHON_DIR%' -Force"
del "%PYTHON_ZIP%" 2>nul

:: Enable pip in embedded Python (modify python312._pth)
echo   Configuring Python for pip support...
set "PTH_FILE=%EMBER_PYTHON_DIR%\python312._pth"
if exist "%PTH_FILE%" (
    :: Uncomment import site to enable pip
    powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site', 'import site' | Set-Content '%PTH_FILE%'"
)

:: Download and install pip
echo   Installing pip (this may take 30-60 seconds)...
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "GET_PIP=%TEMP_DIR%\get-pip.py"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%' -UseBasicParsing}"

if exist "%GET_PIP%" (
    echo   Running pip installer...
    "%EMBER_PYTHON%" "%GET_PIP%" --no-warn-script-location

    if %errorlevel% neq 0 (
        echo   [WARNING] pip installation had issues, trying alternative...
        "%EMBER_PYTHON%" -m ensurepip --default-pip
    )

    del "%GET_PIP%" 2>nul
) else (
    echo   [WARNING] Failed to download get-pip.py, trying alternative...
    "%EMBER_PYTHON%" -m ensurepip --default-pip
)

:: Verify pip installation
echo   Verifying pip installation...
if not exist "%EMBER_PIP%" (
    echo   [WARNING] pip executable not found, trying alternative method...
    "%EMBER_PYTHON%" -m ensurepip --default-pip

    timeout /t 2 >nul

    if not exist "%EMBER_PIP%" (
        echo   [ERROR] Failed to install pip
        echo   This might be due to network issues or Python configuration
        echo   Please check your internet connection and try again
        pause
        exit /b 1
    )
)

echo   Testing pip...
"%EMBER_PYTHON%" -m pip --version
if %errorlevel% neq 0 (
    echo   [ERROR] pip is not working correctly
    pause
    exit /b 1
)

echo   [OK] Isolated Python 3.12 installed for EmberOS

:python_ok
echo.

:: ============================================================
:: STEP 2: Install llama.cpp (Self-Contained)
:: ============================================================
echo [Step 2/6] Setting up isolated llama.cpp...

:: Check if we already have our own llama.cpp installed
if exist "%EMBER_LLAMA_DIR%\llama-server.exe" (
    echo   [OK] EmberOS llama.cpp already installed
    goto :llama_ok
)

echo   Downloading llama.cpp (will be installed ONLY for EmberOS)...

set "LLAMA_URL=https://github.com/ggerganov/llama.cpp/releases/download/b4598/llama-b4598-bin-win-avx2-x64.zip"
set "LLAMA_ZIP=%TEMP_DIR%\llama-cpp.zip"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%LLAMA_URL%' -OutFile '%LLAMA_ZIP%' -UseBasicParsing}"

if not exist "%LLAMA_ZIP%" (
    echo   [WARNING] Failed to download llama.cpp
    echo   You can install it manually later.
    goto :llama_skip
)

echo   Extracting to EmberOS directory...
if exist "%EMBER_LLAMA_DIR%" rmdir /s /q "%EMBER_LLAMA_DIR%"
mkdir "%EMBER_LLAMA_DIR%"
powershell -Command "Expand-Archive -Path '%LLAMA_ZIP%' -DestinationPath '%EMBER_LLAMA_DIR%' -Force"
del "%LLAMA_ZIP%" 2>nul

:: Check if files are in a subdirectory and move them up
for /d %%d in ("%EMBER_LLAMA_DIR%\*") do (
    if exist "%%d\llama-server.exe" (
        move "%%d\*" "%EMBER_LLAMA_DIR%\" >nul 2>&1
        rmdir "%%d" 2>nul
    )
)

echo   [OK] llama.cpp installed for EmberOS (isolated)

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

:: Create venv using virtualenv (embedded Python doesn't have venv module)
if not exist "%VENV_DIR%" (
    echo   Installing virtualenv...
    "%EMBER_PIP%" install virtualenv -q 2>nul

    echo   Creating virtual environment with isolated Python...
    "%EMBER_PYTHON%" -m virtualenv "%VENV_DIR%" -q

    if not exist "%VENV_PYTHON%" (
        echo   [ERROR] Failed to create virtual environment
        echo   Trying alternative method...

        :: Alternative: Use pip directly with --target
        if not exist "%VENV_DIR%" mkdir "%VENV_DIR%"
        if not exist "%VENV_DIR%\Scripts" mkdir "%VENV_DIR%\Scripts"

        :: Copy Python to venv
        xcopy /E /I /Q /Y "%EMBER_PYTHON_DIR%" "%VENV_DIR%" >nul 2>&1

        :: Move to Scripts folder structure
        if not exist "%VENV_DIR%\Scripts\python.exe" (
            copy "%EMBER_PYTHON%" "%VENV_DIR%\Scripts\python.exe" >nul 2>&1
            copy "%EMBER_PYTHON_DIR%\pythonw.exe" "%VENV_DIR%\Scripts\pythonw.exe" >nul 2>&1
            copy "%EMBER_PYTHON_DIR%\python*.dll" "%VENV_DIR%\Scripts\" >nul 2>&1
        )

        if not exist "%VENV_PYTHON%" (
            echo   [ERROR] Failed to create virtual environment
            pause
            exit /b 1
        )
    )
)

:: Ensure pip is available in venv
if not exist "%VENV_PIP%" (
    echo   Setting up pip in virtual environment...
    "%VENV_PYTHON%" -m ensurepip --default-pip 2>nul

    :: If still not available, copy from base Python
    if not exist "%VENV_PIP%" (
        if exist "%EMBER_PIP%" (
            copy "%EMBER_PIP%" "%VENV_PIP%" >nul 2>&1
        )
    )
)

echo   Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip --no-warn-script-location

if %errorlevel% neq 0 (
    echo   [WARNING] pip upgrade had issues, continuing anyway...
)

:: Get the script directory (where EmberOS source is)
set "SCRIPT_DIR=%~dp0"

:: Check if we're in the EmberOS source directory
if exist "%SCRIPT_DIR%pyproject.toml" (
    echo   Installing EmberOS from source (this may take a few minutes)...
    echo   Please wait, this step takes the longest...

    :: First install wheel and setuptools
    echo   Installing build tools...
    "%VENV_PYTHON%" -m pip install wheel setuptools --no-warn-script-location

    :: Try to install with documents support
    echo   Installing EmberOS package...
    "%VENV_PYTHON%" -m pip install -e "%SCRIPT_DIR%[documents]" --no-warn-script-location

    if %errorlevel% neq 0 (
        echo   [WARNING] Full installation had issues, trying basic install...
        "%VENV_PYTHON%" -m pip install -e "%SCRIPT_DIR%" --no-warn-script-location

        if %errorlevel% neq 0 (
            echo   [ERROR] Failed to install EmberOS
            echo   Trying to install core dependencies individually...

            :: Install core dependencies manually
            echo   Installing core packages...
            "%VENV_PYTHON%" -m pip install aiohttp pydantic pyyaml toml PyQt6 rich click aiosqlite psutil watchdog appdirs python-dateutil numpy --no-warn-script-location

            :: Try installing again
            echo   Retrying EmberOS installation...
            "%VENV_PYTHON%" -m pip install -e "%SCRIPT_DIR%" --no-warn-script-location

            if %errorlevel% neq 0 (
                echo   [ERROR] Installation still failed
                echo   You may need to install dependencies manually
                pause
                exit /b 1
            )
        )
    )
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

:: Create ember.cmd - uses our isolated venv Python
(
echo @echo off
echo "%VENV_PYTHON%" -m emberos.cli %%*
) > "%EMBER_DIR%\ember.cmd"

:: Create ember-ui.cmd - uses our isolated venv Python (windowed)
(
echo @echo off
echo start "" "%VENV_DIR%\Scripts\pythonw.exe" -m emberos.gui %%*
) > "%EMBER_DIR%\ember-ui.cmd"

:: Create emberd.cmd - daemon
(
echo @echo off
echo "%VENV_PYTHON%" -m emberos.daemon %%*
) > "%EMBER_DIR%\emberd.cmd"

:: Create ember-llm.cmd - uses our ISOLATED llama.cpp (not system's)
(
echo @echo off
echo setlocal
echo.
echo :: EmberOS LLM Server Manager - Uses ISOLATED llama.cpp
echo set "LLAMA_SERVER=%EMBER_LLAMA_DIR%\llama-server.exe"
echo set "VISION_MODEL=%MODEL_DIR%\qwen2.5-vl-7b-instruct-q4_k_m.gguf"
echo set "BITNET_MODEL=%MODEL_DIR%\bitnet\ggml-model-i2_s.gguf"
echo.
echo if not exist "%%LLAMA_SERVER%%" ^(
echo     echo [ERROR] llama-server not found at %%LLAMA_SERVER%%
echo     echo Please run the EmberOS installer again.
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo Starting EmberOS LLM servers...
echo echo Using isolated llama.cpp from: %%LLAMA_SERVER%%
echo.
echo if exist "%%VISION_MODEL%%" ^(
echo     echo Starting Vision model on port 11434...
echo     start "EmberOS-Vision" /min "%%LLAMA_SERVER%%" --model "%%VISION_MODEL%%" --host 127.0.0.1 --port 11434 --ctx-size 8192 --threads 4
echo ^) else ^(
echo     echo [WARNING] Vision model not found at %%VISION_MODEL%%
echo ^)
echo.
echo if exist "%%BITNET_MODEL%%" ^(
echo     echo Starting BitNet model on port 38080...
echo     start "EmberOS-BitNet" /min "%%LLAMA_SERVER%%" --model "%%BITNET_MODEL%%" --host 127.0.0.1 --port 38080 --ctx-size 4096 --threads 4
echo ^) else ^(
echo     echo [WARNING] BitNet model not found at %%BITNET_MODEL%%
echo ^)
echo.
echo echo.
echo echo LLM servers started!
echo echo   Vision model: port 11434
echo echo   BitNet model: port 38080
) > "%EMBER_DIR%\ember-llm.cmd"

:: Create a model download helper script
(
echo @echo off
echo echo EmberOS Model Downloader
echo echo ========================
echo echo.
echo set /p DL_BITNET="Download BitNet model (~1.2 GB)? (Y/N): "
echo if /i "%%DL_BITNET%%"=="Y" ^(
echo     echo Downloading BitNet model...
echo     "%VENV_PYTHON%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='microsoft/bitnet-b1.58-2B-4T-gguf', filename='ggml-model-i2_s.gguf', local_dir=r'%MODEL_DIR%\bitnet')"
echo ^)
echo set /p DL_VISION="Download Vision model (~5 GB)? (Y/N): "
echo if /i "%%DL_VISION%%"=="Y" ^(
echo     echo Downloading Vision model...
echo     "%VENV_PYTHON%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF', filename='qwen2.5-vl-7b-instruct-q4_k_m.gguf', local_dir=r'%MODEL_DIR%')"
echo ^)
echo echo Done!
echo pause
) > "%EMBER_DIR%\ember-download-models.cmd"

:: Add EmberOS to PATH (only the EmberOS directory, not system Python)
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
    "%VENV_PYTHON%" -m pip install huggingface_hub -q 2>nul

    echo.
    echo   Downloading BitNet model (~1.2 GB)...
    echo   This may take several minutes depending on your internet speed...
    "%VENV_PYTHON%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='microsoft/bitnet-b1.58-2B-4T-gguf', filename='ggml-model-i2_s.gguf', local_dir=r'%MODEL_DIR%\bitnet')"

    echo.
    set /p DOWNLOAD_VISION="Download Vision model too? (~5 GB, takes longer) (Y/N): "
    if /i "!DOWNLOAD_VISION!"=="Y" (
        echo   Downloading Vision model (~5 GB)...
        echo   This may take 10-30 minutes depending on your internet speed...
        "%VENV_PYTHON%" -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF', filename='qwen2.5-vl-7b-instruct-q4_k_m.gguf', local_dir=r'%MODEL_DIR%')"
    )

    echo   [OK] Models downloaded
) else (
    echo   Skipping model download. You can download them later by running:
    echo   %EMBER_DIR%\ember-download-models.cmd
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

