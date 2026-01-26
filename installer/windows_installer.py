"""
EmberOS Windows Installer GUI

A graphical installer for EmberOS on Windows 10/11.
Creates an executable installer with checkboxes and proper permissions.
"""

import os
import sys
import subprocess
import threading
import tempfile
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

# PyQt6 for GUI
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QProgressBar, QTextEdit, QPushButton,
    QFileDialog, QLineEdit, QGroupBox, QRadioButton, QMessageBox,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor


# ==================== Configuration ====================

EMBER_VERSION = "1.0.0"
PYTHON_VERSION = "3.12.8"
# Use embedded Python for fully self-contained installation
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
LLAMA_CPP_URL = "https://github.com/ggerganov/llama.cpp/releases/download/b4598/llama-b4598-bin-win-avx2-x64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# Model URLs
VISION_MODEL_REPO = "PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF"
VISION_MODEL_FILE = "qwen2.5-vl-7b-instruct-q4_k_m.gguf"
BITNET_MODEL_REPO = "microsoft/bitnet-b1.58-2B-4T-gguf"
BITNET_MODEL_FILE = "ggml-model-i2_s.gguf"

# Default paths
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'EmberOS')
DEFAULT_MODEL_DIR = os.path.join(DEFAULT_INSTALL_DIR, 'models')


# ==================== Worker Thread ====================

class InstallWorker(QThread):
    """Background worker for installation tasks."""

    progress = pyqtSignal(int, str)  # percentage, message
    log = pyqtSignal(str)  # log message
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            total_steps = self._count_steps()
            current_step = 0

            # Step 1: Install Python if needed
            if self.config.get('install_python'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Installing Python...")
                if not self._install_python():
                    self.finished.emit(False, "Failed to install Python")
                    return

            if self._cancelled:
                return

            # Step 2: Install llama.cpp if needed
            if self.config.get('install_llama'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Installing llama.cpp...")
                if not self._install_llama_cpp():
                    self.finished.emit(False, "Failed to install llama.cpp")
                    return

            if self._cancelled:
                return

            # Step 3: Create directories
            current_step += 1
            self.progress.emit(int(current_step / total_steps * 100), "Creating directories...")
            self._create_directories()

            if self._cancelled:
                return

            # Step 4: Create virtual environment
            current_step += 1
            self.progress.emit(int(current_step / total_steps * 100), "Creating Python virtual environment...")
            if not self._create_venv():
                self.finished.emit(False, "Failed to create virtual environment")
                return

            if self._cancelled:
                return

            # Step 5: Install EmberOS package
            current_step += 1
            self.progress.emit(int(current_step / total_steps * 100), "Installing EmberOS package...")
            if not self._install_emberos():
                self.finished.emit(False, "Failed to install EmberOS package")
                return

            if self._cancelled:
                return

            # Step 6: Download models if requested
            if self.config.get('download_vision_model'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Downloading vision model (~5GB)...")
                if not self._download_vision_model():
                    self.log.emit("Warning: Failed to download vision model")

            if self._cancelled:
                return

            if self.config.get('download_bitnet_model'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Downloading BitNet model (~1.2GB)...")
                if not self._download_bitnet_model():
                    self.log.emit("Warning: Failed to download BitNet model")

            if self._cancelled:
                return

            # Step 7: Create shortcuts
            if self.config.get('create_shortcuts'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Creating shortcuts...")
                self._create_shortcuts()

            if self._cancelled:
                return

            # Step 8: Configure auto-start
            if self.config.get('auto_start'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Configuring auto-start...")
                self._configure_autostart()

            # Step 9: Add to PATH
            if self.config.get('add_to_path'):
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100), "Adding to PATH...")
                self._add_to_path()

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, "EmberOS installed successfully!")

        except Exception as e:
            self.finished.emit(False, f"Installation failed: {str(e)}")

    def _count_steps(self) -> int:
        steps = 4  # directories, venv, package, config
        if self.config.get('install_python'):
            steps += 1
        if self.config.get('install_llama'):
            steps += 1
        if self.config.get('download_vision_model'):
            steps += 1
        if self.config.get('download_bitnet_model'):
            steps += 1
        if self.config.get('create_shortcuts'):
            steps += 1
        if self.config.get('auto_start'):
            steps += 1
        if self.config.get('add_to_path'):
            steps += 1
        return steps

    def _install_python(self) -> bool:
        self.log.emit("Downloading Python embeddable package...")
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        python_dir = os.path.join(install_dir, 'python')
        python_zip = os.path.join(tempfile.gettempdir(), "python-embed.zip")

        try:
            # Download embedded Python
            urllib.request.urlretrieve(PYTHON_URL, python_zip)
            self.log.emit("Extracting Python...")

            # Create directory and extract
            os.makedirs(python_dir, exist_ok=True)
            with zipfile.ZipFile(python_zip, 'r') as zip_ref:
                zip_ref.extractall(python_dir)

            os.remove(python_zip)

            # Enable pip support by modifying ._pth file
            self.log.emit("Configuring Python...")
            pth_file = os.path.join(python_dir, 'python312._pth')
            if os.path.exists(pth_file):
                with open(pth_file, 'r') as f:
                    content = f.read()
                content = content.replace('#import site', 'import site')
                with open(pth_file, 'w') as f:
                    f.write(content)

            # Download and install pip
            self.log.emit("Installing pip...")
            get_pip = os.path.join(tempfile.gettempdir(), "get-pip.py")
            urllib.request.urlretrieve(GET_PIP_URL, get_pip)

            python_exe = os.path.join(python_dir, 'python.exe')
            result = subprocess.run([python_exe, get_pip, '--no-warn-script-location'],
                                  capture_output=True, timeout=300)

            os.remove(get_pip)

            if result.returncode == 0:
                self.log.emit("Python embedded package installed successfully!")
                return True
            else:
                self.log.emit(f"pip installation had issues: {result.stderr.decode()}")
                return False

        except Exception as e:
            self.log.emit(f"Error installing Python: {e}")
            return False

    def _install_llama_cpp(self) -> bool:
        self.log.emit("Downloading llama.cpp...")
        zip_path = os.path.join(tempfile.gettempdir(), "llama-cpp.zip")
        llama_dir = self.config.get('llama_path', 'C:\\llama.cpp')

        try:
            urllib.request.urlretrieve(LLAMA_CPP_URL, zip_path)
            self.log.emit(f"Extracting to {llama_dir}...")

            if os.path.exists(llama_dir):
                shutil.rmtree(llama_dir)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(llama_dir)

            os.remove(zip_path)

            # Add to PATH
            self._add_to_user_path(llama_dir)

            self.log.emit("llama.cpp installed successfully!")
            return True
        except Exception as e:
            self.log.emit(f"Error installing llama.cpp: {e}")
            return False

    def _create_directories(self):
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        dirs = [
            install_dir,
            os.path.join(install_dir, 'tools'),
            os.path.join(install_dir, 'vectors'),
            os.path.join(install_dir, 'backups'),
            os.path.join(install_dir, 'logs'),
            os.path.join(install_dir, 'models'),
            os.path.join(install_dir, 'models', 'bitnet'),
            os.path.join(os.environ.get('APPDATA', ''), 'EmberOS'),
        ]

        for d in dirs:
            os.makedirs(d, exist_ok=True)
            self.log.emit(f"Created: {d}")

    def _create_venv(self) -> bool:
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        venv_dir = os.path.join(install_dir, 'venv')
        python_dir = os.path.join(install_dir, 'python')
        python_exe = os.path.join(python_dir, 'python.exe')
        pip_exe = os.path.join(python_dir, 'Scripts', 'pip.exe')

        try:
            # If we installed our own Python, use it
            if os.path.exists(python_exe):
                self.log.emit(f"Using EmberOS Python: {python_exe}")

                # Install virtualenv first (embedded Python doesn't have venv module)
                self.log.emit("Installing virtualenv...")
                subprocess.run([pip_exe, 'install', 'virtualenv', '-q'],
                             capture_output=True, timeout=300)

                # Create venv using virtualenv
                self.log.emit("Creating virtual environment...")
                result = subprocess.run([python_exe, '-m', 'virtualenv', venv_dir, '-q'],
                                      capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    self.log.emit(f"virtualenv creation failed: {result.stderr}")
                    # Try alternative: copy Python directory
                    self.log.emit("Trying alternative method...")
                    shutil.copytree(python_dir, venv_dir, dirs_exist_ok=True)
            else:
                # Find system Python
                python_cmd = self._find_python()
                if not python_cmd:
                    self.log.emit("Python not found!")
                    return False

                self.log.emit(f"Using system Python: {python_cmd}")

                # Try standard venv first
                result = subprocess.run([python_cmd, '-m', 'venv', venv_dir],
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    # Try virtualenv as fallback
                    self.log.emit("Standard venv failed, trying virtualenv...")
                    subprocess.run([python_cmd, '-m', 'pip', 'install', 'virtualenv', '-q'],
                                 capture_output=True)
                    result = subprocess.run([python_cmd, '-m', 'virtualenv', venv_dir],
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        self.log.emit(f"venv creation failed: {result.stderr}")
                        return False

            # Verify venv was created
            venv_python = os.path.join(venv_dir, 'Scripts', 'python.exe')
            if not os.path.exists(venv_python):
                self.log.emit("Virtual environment creation failed!")
                return False

            # Upgrade pip in venv
            venv_pip = os.path.join(venv_dir, 'Scripts', 'pip.exe')
            if os.path.exists(venv_pip):
                subprocess.run([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip', '-q'],
                             capture_output=True, timeout=300)

            self.log.emit("Virtual environment created!")
            return True
        except Exception as e:
            self.log.emit(f"Error creating venv: {e}")
            return False

    def _install_emberos(self) -> bool:
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        source_dir = self.config.get('source_dir', os.getcwd())
        pip_path = os.path.join(install_dir, 'venv', 'Scripts', 'pip.exe')

        try:
            # Install EmberOS with documents support
            self.log.emit("Installing EmberOS package (this may take a few minutes)...")
            result = subprocess.run(
                [pip_path, 'install', '-e', f'{source_dir}[documents]'],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                self.log.emit(f"pip install failed: {result.stderr}")
                return False

            self.log.emit("EmberOS package installed!")
            return True
        except Exception as e:
            self.log.emit(f"Error installing EmberOS: {e}")
            return False

    def _download_vision_model(self) -> bool:
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        model_dir = os.path.join(install_dir, 'models')
        pip_path = os.path.join(install_dir, 'venv', 'Scripts', 'pip.exe')
        python_path = os.path.join(install_dir, 'venv', 'Scripts', 'python.exe')

        try:
            # Ensure huggingface_hub is installed
            subprocess.run([pip_path, 'install', 'huggingface_hub'], capture_output=True)

            # Download model
            self.log.emit(f"Downloading {VISION_MODEL_FILE}...")
            result = subprocess.run([
                python_path, '-c',
                f'''
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="{VISION_MODEL_REPO}",
    filename="{VISION_MODEL_FILE}",
    local_dir=r"{model_dir}"
)
print("Download complete!")
'''
            ], capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                self.log.emit("Vision model downloaded!")
                return True
            else:
                self.log.emit(f"Download failed: {result.stderr}")
                return False
        except Exception as e:
            self.log.emit(f"Error downloading vision model: {e}")
            return False

    def _download_bitnet_model(self) -> bool:
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        model_dir = os.path.join(install_dir, 'models', 'bitnet')
        python_path = os.path.join(install_dir, 'venv', 'Scripts', 'python.exe')

        try:
            self.log.emit(f"Downloading {BITNET_MODEL_FILE}...")
            result = subprocess.run([
                python_path, '-c',
                f'''
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="{BITNET_MODEL_REPO}",
    filename="{BITNET_MODEL_FILE}",
    local_dir=r"{model_dir}"
)
print("Download complete!")
'''
            ], capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                self.log.emit("BitNet model downloaded!")
                return True
            else:
                self.log.emit(f"Download failed: {result.stderr}")
                return False
        except Exception as e:
            self.log.emit(f"Error downloading BitNet model: {e}")
            return False

    def _create_shortcuts(self):
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        venv_scripts = os.path.join(install_dir, 'venv', 'Scripts')

        # Create batch files
        batch_files = {
            'ember.cmd': f'@echo off\n"{venv_scripts}\\python.exe" -m emberos.cli %*',
            'ember-ui.cmd': f'@echo off\n"{venv_scripts}\\pythonw.exe" -m emberos.gui %*',
            'emberd.cmd': f'@echo off\n"{venv_scripts}\\python.exe" -m emberos.daemon %*',
            'ember-llm.cmd': self._get_llm_manager_script(install_dir),
        }

        for name, content in batch_files.items():
            path = os.path.join(install_dir, name)
            with open(path, 'w') as f:
                f.write(content)
            self.log.emit(f"Created: {name}")

        # Create Start Menu shortcut
        try:
            self._create_start_menu_shortcut(install_dir)
            self.log.emit("Start Menu shortcut created!")
        except Exception as e:
            self.log.emit(f"Could not create Start Menu shortcut: {e}")

    def _get_llm_manager_script(self, install_dir: str) -> str:
        model_dir = os.path.join(install_dir, 'models')
        return f'''@echo off
setlocal

set VISION_MODEL="{model_dir}\\{VISION_MODEL_FILE}"
set BITNET_MODEL="{model_dir}\\bitnet\\{BITNET_MODEL_FILE}"

echo Starting EmberOS LLM servers...

if exist %VISION_MODEL% (
    echo Starting Vision model on port 11434...
    start "EmberOS-Vision" /min llama-server --model %VISION_MODEL% --host 127.0.0.1 --port 11434 --ctx-size 8192 --threads 4
) else (
    echo Vision model not found at %VISION_MODEL%
)

if exist %BITNET_MODEL% (
    echo Starting BitNet model on port 38080...
    start "EmberOS-BitNet" /min llama-server --model %BITNET_MODEL% --host 127.0.0.1 --port 38080 --ctx-size 4096 --threads 4
) else (
    echo BitNet model not found at %BITNET_MODEL%
)

echo LLM servers started!
echo   Vision: port 11434
echo   BitNet: port 38080
'''

    def _create_start_menu_shortcut(self, install_dir: str):
        import winreg

        start_menu = os.path.join(
            os.environ.get('APPDATA', ''),
            'Microsoft', 'Windows', 'Start Menu', 'Programs'
        )

        # Create shortcut using PowerShell
        shortcut_path = os.path.join(start_menu, 'EmberOS.lnk')
        target_path = os.path.join(install_dir, 'ember-ui.cmd')

        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
$Shortcut.WorkingDirectory = "{install_dir}"
$Shortcut.Description = "EmberOS - AI-Native Desktop Assistant"
$Shortcut.Save()
'''
        subprocess.run(['powershell', '-Command', ps_script], capture_output=True)

    def _configure_autostart(self):
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)

        # Create scheduled task for LLM servers
        task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><Delay>PT30S</Delay></LogonTrigger>
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
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>{install_dir}\\ember-llm.cmd</Command>
      <WorkingDirectory>{install_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

        task_file = os.path.join(install_dir, 'ember-autostart.xml')
        with open(task_file, 'w', encoding='utf-16') as f:
            f.write(task_xml)

        try:
            subprocess.run([
                'schtasks', '/Create', '/TN', 'EmberOS\\LLMServers',
                '/XML', task_file, '/F'
            ], capture_output=True)
            self.log.emit("Auto-start configured!")
        except Exception as e:
            self.log.emit(f"Could not configure auto-start: {e}")

    def _add_to_path(self):
        install_dir = self.config.get('install_dir', DEFAULT_INSTALL_DIR)
        self._add_to_user_path(install_dir)
        self.log.emit(f"Added {install_dir} to PATH")

    def _add_to_user_path(self, path: str):
        import winreg

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Environment',
                0,
                winreg.KEY_ALL_ACCESS
            )

            try:
                current_path, _ = winreg.QueryValueEx(key, 'PATH')
            except WindowsError:
                current_path = ''

            if path.lower() not in current_path.lower():
                new_path = f"{path};{current_path}" if current_path else path
                winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)

            winreg.CloseKey(key)

            # Notify system of environment change
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")

        except Exception as e:
            self.log.emit(f"Could not update PATH: {e}")

    def _find_python(self) -> Optional[str]:
        for cmd in ['python', 'python3', 'py']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0 and 'Python 3' in result.stdout:
                    version = result.stdout.strip().split()[1]
                    major, minor = map(int, version.split('.')[:2])
                    if major == 3 and minor >= 11:
                        return cmd
            except:
                pass
        return None


# ==================== Wizard Pages ====================

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to EmberOS")
        self.setSubTitle("AI-Native Desktop Assistant for Windows")

        layout = QVBoxLayout(self)

        # Logo placeholder
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                color: #ff6b35;
                padding: 20px;
            }
        """)
        logo_label.setText("🔥 EmberOS")
        layout.addWidget(logo_label)

        # Description
        desc = QLabel(
            f"<p style='font-size: 14px;'>Version {EMBER_VERSION}</p>"
            "<p>EmberOS transforms your Windows desktop into an AI-native environment "
            "where every interaction flows through an intelligent, private AI agent.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Dual AI models for fast and accurate responses</li>"
            "<li>Complete document creation and reading</li>"
            "<li>File organization and search</li>"
            "<li>100% local and private - no cloud required</li>"
            "</ul>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()


class PrerequisitesPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Prerequisites")
        self.setSubTitle("Check and install required components")

        layout = QVBoxLayout(self)

        # Python
        python_group = QGroupBox("Python 3.11+")
        python_layout = QVBoxLayout(python_group)

        self.python_status = QLabel("Checking...")
        python_layout.addWidget(self.python_status)

        self.install_python = QCheckBox("Install Python 3.12 (if not found)")
        self.install_python.setChecked(True)
        self.registerField("install_python", self.install_python)
        python_layout.addWidget(self.install_python)

        layout.addWidget(python_group)

        # llama.cpp
        llama_group = QGroupBox("llama.cpp (LLM Server)")
        llama_layout = QVBoxLayout(llama_group)

        self.llama_status = QLabel("Checking...")
        llama_layout.addWidget(self.llama_status)

        self.install_llama = QCheckBox("Install llama.cpp (if not found)")
        self.install_llama.setChecked(True)
        self.registerField("install_llama", self.install_llama)
        llama_layout.addWidget(self.install_llama)

        layout.addWidget(llama_group)

        layout.addStretch()

        # Check prerequisites when page is shown
        QTimer.singleShot(100, self._check_prerequisites)

    def _check_prerequisites(self):
        # Check Python
        python_found = False
        for cmd in ['python', 'python3', 'py']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0 and 'Python 3' in result.stdout:
                    version = result.stdout.strip()
                    major, minor = map(int, version.split()[1].split('.')[:2])
                    if major == 3 and minor >= 11:
                        self.python_status.setText(f"✅ Found: {version}")
                        self.python_status.setStyleSheet("color: green;")
                        self.install_python.setChecked(False)
                        self.install_python.setEnabled(False)
                        python_found = True
                        break
            except:
                pass

        if not python_found:
            self.python_status.setText("❌ Not found (will be installed)")
            self.python_status.setStyleSheet("color: red;")

        # Check llama.cpp
        llama_path = shutil.which('llama-server')
        if llama_path:
            self.llama_status.setText(f"✅ Found: {llama_path}")
            self.llama_status.setStyleSheet("color: green;")
            self.install_llama.setChecked(False)
            self.install_llama.setEnabled(False)
        else:
            self.llama_status.setText("❌ Not found (will be installed)")
            self.llama_status.setStyleSheet("color: red;")


class InstallLocationPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Location")
        self.setSubTitle("Choose where to install EmberOS")

        layout = QVBoxLayout(self)

        # Install directory
        dir_group = QGroupBox("Installation Directory")
        dir_layout = QHBoxLayout(dir_group)

        self.install_dir = QLineEdit(DEFAULT_INSTALL_DIR)
        self.registerField("install_dir", self.install_dir)
        dir_layout.addWidget(self.install_dir)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        dir_layout.addWidget(browse_btn)

        layout.addWidget(dir_group)

        # Space required
        space_label = QLabel(
            "<p><b>Disk space required:</b></p>"
            "<ul>"
            "<li>EmberOS application: ~500 MB</li>"
            "<li>Vision model (optional): ~5 GB</li>"
            "<li>BitNet model (optional): ~1.2 GB</li>"
            "</ul>"
            "<p><b>Total: up to 7 GB</b></p>"
        )
        layout.addWidget(space_label)

        layout.addStretch()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder")
        if folder:
            self.install_dir.setText(folder)


class ComponentsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Components")
        self.setSubTitle("Select components to install")

        layout = QVBoxLayout(self)

        # AI Models
        models_group = QGroupBox("AI Models")
        models_layout = QVBoxLayout(models_group)

        self.vision_model = QCheckBox("Qwen2.5-VL Vision Model (~5 GB)")
        self.vision_model.setToolTip("Required for image analysis, PDF reading, screenshots")
        self.vision_model.setChecked(True)
        self.registerField("download_vision_model", self.vision_model)
        models_layout.addWidget(self.vision_model)

        self.bitnet_model = QCheckBox("BitNet Text Model (~1.2 GB)")
        self.bitnet_model.setToolTip("Fast text-only model for quick responses")
        self.bitnet_model.setChecked(True)
        self.registerField("download_bitnet_model", self.bitnet_model)
        models_layout.addWidget(self.bitnet_model)

        models_note = QLabel("<i>Models can be downloaded later if you skip them now.</i>")
        models_note.setStyleSheet("color: gray;")
        models_layout.addWidget(models_note)

        layout.addWidget(models_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.create_shortcuts = QCheckBox("Create Start Menu shortcut")
        self.create_shortcuts.setChecked(True)
        self.registerField("create_shortcuts", self.create_shortcuts)
        options_layout.addWidget(self.create_shortcuts)

        self.add_to_path = QCheckBox("Add EmberOS to PATH")
        self.add_to_path.setChecked(True)
        self.registerField("add_to_path", self.add_to_path)
        options_layout.addWidget(self.add_to_path)

        self.auto_start = QCheckBox("Start LLM servers on login")
        self.auto_start.setChecked(False)
        self.registerField("auto_start", self.auto_start)
        options_layout.addWidget(self.auto_start)

        layout.addWidget(options_group)

        layout.addStretch()


class InstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing")
        self.setSubTitle("Please wait while EmberOS is being installed...")

        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Preparing installation...")
        layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        self.worker = None
        self._complete = False

    def initializePage(self):
        # Gather configuration
        config = {
            'install_python': self.field("install_python"),
            'install_llama': self.field("install_llama"),
            'install_dir': self.field("install_dir"),
            'download_vision_model': self.field("download_vision_model"),
            'download_bitnet_model': self.field("download_bitnet_model"),
            'create_shortcuts': self.field("create_shortcuts"),
            'add_to_path': self.field("add_to_path"),
            'auto_start': self.field("auto_start"),
            'source_dir': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        }

        # Start installation
        self.worker = InstallWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_log(self, message: str):
        self.log_text.append(message)

    def _on_finished(self, success: bool, message: str):
        self._complete = True
        if success:
            self.status_label.setText("✅ " + message)
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("❌ " + message)
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

        self.completeChanged.emit()

    def isComplete(self):
        return self._complete


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Complete")
        self.setSubTitle("EmberOS has been installed successfully!")

        layout = QVBoxLayout(self)

        success_label = QLabel(
            "<h2 style='color: #ff6b35;'>🎉 Welcome to EmberOS!</h2>"
            "<p>Installation completed successfully.</p>"
        )
        layout.addWidget(success_label)

        # Next steps
        steps = QLabel(
            "<p><b>Next steps:</b></p>"
            "<ol>"
            "<li>Restart your terminal (for PATH changes)</li>"
            "<li>Run <code>ember-llm</code> to start the AI servers</li>"
            "<li>Run <code>emberd</code> to start the daemon</li>"
            "<li>Run <code>ember-ui</code> or use Start Menu to launch the GUI</li>"
            "</ol>"
            "<p><b>Quick commands:</b></p>"
            "<ul>"
            "<li><code>ember-ui</code> - Launch graphical interface</li>"
            "<li><code>ember</code> - Launch terminal interface</li>"
            "<li><code>ember --help</code> - Show help</li>"
            "</ul>"
        )
        steps.setWordWrap(True)
        layout.addWidget(steps)

        self.launch_checkbox = QCheckBox("Launch EmberOS now")
        self.launch_checkbox.setChecked(True)
        layout.addWidget(self.launch_checkbox)

        layout.addStretch()


# ==================== Main Installer Wizard ====================

class EmberOSInstaller(QWizard):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"EmberOS Installer v{EMBER_VERSION}")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 500)

        # Set style
        self.setStyleSheet("""
            QWizard {
                background-color: #1a1a24;
            }
            QWizardPage {
                background-color: #1a1a24;
                color: #f0f0fa;
            }
            QLabel {
                color: #f0f0fa;
            }
            QGroupBox {
                color: #f0f0fa;
                border: 1px solid #ff6b35;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #ff6b35;
            }
            QCheckBox {
                color: #f0f0fa;
            }
            QLineEdit {
                background-color: #242430;
                color: #f0f0fa;
                border: 1px solid #ff6b35;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ff8c5a;
            }
            QProgressBar {
                border: 1px solid #ff6b35;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #ff6b35;
            }
            QTextEdit {
                background-color: #242430;
                color: #a0a0b0;
                border: 1px solid #3a3a4a;
                border-radius: 4px;
            }
        """)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(PrerequisitesPage())
        self.addPage(InstallLocationPage())
        self.addPage(ComponentsPage())
        self.addPage(InstallPage())
        self.addPage(FinishPage())

    def done(self, result):
        if result == QWizard.DialogCode.Accepted:
            # Check if user wants to launch
            finish_page = self.page(5)
            if hasattr(finish_page, 'launch_checkbox') and finish_page.launch_checkbox.isChecked():
                install_dir = self.field("install_dir")
                ember_ui = os.path.join(install_dir, 'ember-ui.cmd')
                if os.path.exists(ember_ui):
                    subprocess.Popen([ember_ui], shell=True)

        super().done(result)


def main():
    app = QApplication(sys.argv)

    # Set application info
    app.setApplicationName("EmberOS Installer")
    app.setApplicationVersion(EMBER_VERSION)

    # Create and show wizard
    wizard = EmberOSInstaller()
    wizard.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

