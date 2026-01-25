# EmberOS Installation Guide for Arch Linux

Complete step-by-step installation instructions for EmberOS on Arch Linux systems.

---

## Prerequisites

Before installing EmberOS, ensure you have:

- **Arch Linux** (or an Arch-based distribution like EndeavourOS, Manjaro)
- **Python 3.11+**
- **8GB+ RAM** (16GB recommended for smooth LLM inference)
- **~10GB disk space** (for model + application files)
- **AUR helper** (yay or paru recommended)

---

## Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/emberos/emberos
cd emberos
```

---

## Step 2: Install System Dependencies

```bash
sudo pacman -S --needed python python-pip python-virtualenv python-pyqt6 sqlite xclip xdotool wmctrl libnotify dbus
```

---

## Step 3: Install llama.cpp (Required for LLM Inference)

EmberOS uses llama.cpp to run the LLM locally. Choose one of these options:

### Option A: Install from AUR (Recommended)

```bash
# Using yay
yay -S llama.cpp

# OR using paru
paru -S llama.cpp
```

### Option B: Build from Source

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j$(nproc)
sudo cp llama-server /usr/bin/
cd ..
```

---

## Step 4: Create Required Directories

```bash
mkdir -p ~/.local/share/ember/{tools,vectors,backups}
mkdir -p ~/.config/ember
mkdir -p ~/.cache/ember/logs
sudo mkdir -p /usr/local/share/ember/models
sudo chown $USER:$USER /usr/local/share/ember/models
```

---

## Step 5: Download the LLM Model (Manual Download Required)

> ⚠️ **IMPORTANT:** EmberOS does NOT automatically download the model. You must do this manually.

The recommended model is **Qwen2.5-VL-7B-Instruct** with Q4_K_M quantization (~4.5GB).

### Option A: Using Hugging Face CLI

```bash
# Install huggingface-cli if not already installed
pip install --user huggingface-hub

# Download the model
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-GGUF qwen2.5-vl-7b-instruct-q4_k_m.gguf --local-dir /usr/local/share/ember/models
```

### Option B: Manual Download from Hugging Face

1. Visit: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-GGUF/tree/main
2. Download the `qwen2.5-vl-7b-instruct-q4_k_m.gguf` file
3. Move it to `/usr/local/share/ember/models/`

```bash
mv ~/Downloads/qwen2.5-vl-7b-instruct-q4_k_m.gguf /usr/local/share/ember/models/
```

---

## Step 6: Run the Installation Script

```bash
cd ~/emberos
chmod +x install.sh
./install.sh
```

This script will:
- Verify system dependencies
- Install the EmberOS Python package
- Copy configuration files
- Set up systemd services
- Install D-Bus service
- Create desktop entry

---

## Step 7: Manual Installation (If Script Fails)

If the install script doesn't work, you can install manually:

### Install Python Package

```bash
cd ~/emberos
pip install --user -e .
```

### Copy Configuration

```bash
cp configs/emberos.toml ~/.config/ember/
```

### Install Systemd Services

```bash
mkdir -p ~/.config/systemd/user
cp packaging/emberd.service ~/.config/systemd/user/
cp packaging/ember-llm.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

### Install D-Bus Service

```bash
mkdir -p ~/.local/share/dbus-1/services
cp packaging/org.ember.Agent.service ~/.local/share/dbus-1/services/
```

### Install Desktop Entry

```bash
mkdir -p ~/.local/share/applications
cp packaging/emberos.desktop ~/.local/share/applications/

mkdir -p ~/.local/share/icons/hicolor/256x256/apps
cp assets/zevion-logo.png ~/.local/share/icons/hicolor/256x256/apps/emberos.png
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
```

---

## Step 8: Configure Model Path (If Different)

If your model file has a different name, edit the service file:

```bash
# Check what model file you have
ls /usr/local/share/ember/models/

# Edit the service file to match your model filename
nano ~/.config/systemd/user/ember-llm.service
```

Change this line to match your model:
```ini
--model /usr/local/share/ember/models/YOUR_MODEL_NAME.gguf
```

After editing, reload systemd:
```bash
systemctl --user daemon-reload
```

---

## Step 9: Enable and Start Services

```bash
# Enable and start the LLM server
systemctl --user enable --now ember-llm

# Check if LLM server is running
systemctl --user status ember-llm

# Enable and start the EmberOS daemon
systemctl --user enable --now emberd

# Check if daemon is running
systemctl --user status emberd
```

---

## Step 10: Launch EmberOS

### Terminal Interface (CLI)

```bash
ember
```

### Graphical Interface (GUI)

```bash
ember-ui
```

Or find **EmberOS** in your application menu.

---

## Verify Installation

Run these commands to verify everything is working:

```bash
# Check services status
systemctl --user status ember-llm
systemctl --user status emberd

# Test CLI
ember --help

# Check if model is loaded (in ember REPL)
ember
# Then type: :status
```

---

## Troubleshooting

### LLM Server Won't Start

1. Check if the model file exists:
   ```bash
   ls -la /usr/local/share/ember/models/
   ```

2. Check service logs:
   ```bash
   journalctl --user -u ember-llm -f
   ```

3. Verify llama-server is installed:
   ```bash
   which llama-server
   ```

### Daemon Won't Connect

1. Check if LLM server is running first:
   ```bash
   systemctl --user status ember-llm
   ```

2. Check daemon logs:
   ```bash
   journalctl --user -u emberd -f
   ```

3. Ensure D-Bus is running:
   ```bash
   systemctl --user status dbus
   ```

### Permission Errors

1. Ensure model directory is owned by your user:
   ```bash
   sudo chown -R $USER:$USER /usr/local/share/ember/models
   ```

2. Check that all directories exist:
   ```bash
   ls -la ~/.local/share/ember/
   ls -la ~/.config/ember/
   ls -la ~/.cache/ember/
   ```

---

## GPU Acceleration (Optional)

To enable GPU acceleration, edit the ember-llm service:

```bash
nano ~/.config/systemd/user/ember-llm.service
```

Change `--n-gpu-layers 0` to a higher number (e.g., `--n-gpu-layers 35`):

```ini
ExecStart=/usr/bin/llama-server \
    --model /usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf \
    --host 127.0.0.1 \
    --port 8080 \
    --ctx-size 8192 \
    --threads 4 \
    --n-gpu-layers 35
```

**Requirements for GPU:**
- NVIDIA: Install `cuda` and build llama.cpp with CUDA support
- AMD: Install ROCm and build llama.cpp with ROCm support

Reload and restart:
```bash
systemctl --user daemon-reload
systemctl --user restart ember-llm
```

---

## Quick Reference

| Component | Auto-installed? | Notes |
|-----------|----------------|-------|
| System packages (pacman) | ✅ Yes | Via install.sh |
| Python dependencies | ✅ Yes | Via pip |
| llama.cpp | ❌ No | Install from AUR manually |
| LLM Model (~4-8GB) | ❌ No | Download manually |
| Systemd services | ✅ Yes | Via install.sh |
| Configuration | ✅ Yes | Via install.sh |

---

## Uninstall

To remove EmberOS:

```bash
# Stop and disable services
systemctl --user disable --now emberd
systemctl --user disable --now ember-llm

# Remove files
rm -rf ~/.local/share/ember
rm -rf ~/.config/ember
rm -rf ~/.cache/ember
rm ~/.config/systemd/user/ember*.service
rm ~/.local/share/dbus-1/services/org.ember.Agent.service
rm ~/.local/share/applications/emberos.desktop

# Uninstall Python package
pip uninstall emberos

# Optionally remove models
sudo rm -rf /usr/local/share/ember
```

---

## Support

- **Documentation:** https://docs.emberos.org
- **Issues:** https://github.com/emberos/emberos/issues
- **Discussions:** https://github.com/emberos/emberos/discussions

