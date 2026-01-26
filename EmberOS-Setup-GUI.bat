@echo off
:: ============================================================
:: EmberOS GUI Installer Launcher
:: ============================================================
:: This script launches the graphical installer for EmberOS.
:: If Python is not available, it will download a portable version.
:: ============================================================

title EmberOS Installer Launcher
color 0E

set "SCRIPT_DIR=%~dp0"
set "INSTALLER_SCRIPT=%SCRIPT_DIR%installer\windows_installer.py"
set "TEMP_PYTHON_DIR=%TEMP%\EmberOS_Portable_Python"

:: Check if the installer script exists
if not exist "%INSTALLER_SCRIPT%" (
    echo ERROR: Installer script not found at %INSTALLER_SCRIPT%
    echo Please ensure you're running this from the EmberOS directory.
    pause
    exit /b 1
)

:: Try to find Python
set "PYTHON_CMD="

:: Check system Python
where python >nul 2>&1
if %errorlevel% == 0 (
    python --version >nul 2>&1
    if %errorlevel% == 0 (
        set "PYTHON_CMD=python"
    )
)

:: Check py launcher
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if %errorlevel% == 0 (
        py --version >nul 2>&1
        if %errorlevel% == 0 (
            set "PYTHON_CMD=py"
        )
    )
)

:: If Python found, check for PyQt6
if defined PYTHON_CMD (
    echo Checking for required packages...
    %PYTHON_CMD% -c "import PyQt6" >nul 2>&1
    if %errorlevel% == 0 (
        echo Launching graphical installer...
        %PYTHON_CMD% "%INSTALLER_SCRIPT%"
        exit /b %errorlevel%
    ) else (
        echo PyQt6 not found. Installing...
        %PYTHON_CMD% -m pip install PyQt6 --user -q
        if %errorlevel% == 0 (
            echo Launching graphical installer...
            %PYTHON_CMD% "%INSTALLER_SCRIPT%"
            exit /b %errorlevel%
        )
    )
)

:: If we get here, we need to download portable Python
echo.
echo Python not found or PyQt6 installation failed.
echo Downloading portable Python to launch the installer...
echo This is temporary and will only be used for the installer GUI.
echo.

:: Create temp directory
if not exist "%TEMP_PYTHON_DIR%" mkdir "%TEMP_PYTHON_DIR%"

:: Download Python embeddable
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
set "PYTHON_ZIP=%TEMP%\python-portable.zip"

echo Downloading Python (this will take a moment)...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing"

if not exist "%PYTHON_ZIP%" (
    echo ERROR: Failed to download Python.
    echo Please install Python manually and try again.
    pause
    exit /b 1
)

echo Extracting Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%TEMP_PYTHON_DIR%' -Force"
del "%PYTHON_ZIP%" 2>nul

:: Configure Python for pip
set "PTH_FILE=%TEMP_PYTHON_DIR%\python312._pth"
if exist "%PTH_FILE%" (
    powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site', 'import site' | Set-Content '%PTH_FILE%'"
)

:: Download and install pip
echo Installing pip...
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "GET_PIP=%TEMP%\get-pip.py"
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%' -UseBasicParsing"

if exist "%GET_PIP%" (
    "%TEMP_PYTHON_DIR%\python.exe" "%GET_PIP%" --no-warn-script-location -q
    del "%GET_PIP%" 2>nul
)

:: Install PyQt6
echo Installing PyQt6 (this may take a minute)...
"%TEMP_PYTHON_DIR%\Scripts\pip.exe" install PyQt6 -q

:: Launch the GUI installer
echo.
echo Launching graphical installer...
"%TEMP_PYTHON_DIR%\python.exe" "%INSTALLER_SCRIPT%"

:: Cleanup temporary Python (optional - keep it for faster subsequent runs)
:: echo Cleaning up temporary files...
:: rmdir /s /q "%TEMP_PYTHON_DIR%" 2>nul

exit /b %errorlevel%

