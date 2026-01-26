"""
Build script for EmberOS Windows Installer EXE.

Run this to create a standalone installer executable.
Requires PyInstaller: pip install pyinstaller
"""

import subprocess
import sys
import os
from pathlib import Path

def build_installer():
    """Build the EmberOS Windows installer executable."""

    # Get paths
    script_dir = Path(__file__).parent
    installer_script = script_dir / "windows_installer.py"
    assets_dir = script_dir.parent / "assets"
    icon_path = assets_dir / "ember.ico"

    # Check if PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "EmberOS-Setup",
        "--add-data", f"{script_dir.parent / 'src'};src",
        "--add-data", f"{script_dir.parent / 'pyproject.toml'};.",
    ]

    # Add icon if exists
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    # Add the main script
    cmd.append(str(installer_script))

    print("Building EmberOS installer...")
    print(f"Command: {' '.join(cmd)}")

    # Run PyInstaller
    result = subprocess.run(cmd, cwd=str(script_dir))

    if result.returncode == 0:
        exe_path = script_dir / "dist" / "EmberOS-Setup.exe"
        print(f"\n✅ Build successful!")
        print(f"   Installer location: {exe_path}")
    else:
        print(f"\n❌ Build failed with code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build_installer()

