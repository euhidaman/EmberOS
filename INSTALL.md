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

> **Note:** Modern Arch Linux uses PEP 668 which prevents direct pip installs. The installer now uses a virtual environment automatically.

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

The recommended model is **Qwen2.5-VL-7B-Instruct** with Q4_K_M quantization (~4-5GB).

### Option A: Unsloth GGUF (Recommended)

Unsloth provides optimized, high-quality GGUF conversions.

```bash
# Install huggingface-cli if not already installed
pip install --user huggingface-hub

# Download from Unsloth (recommended)
huggingface-cli download unsloth/Qwen2.5-VL-7B-Instruct-GGUF Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf --local-dir /usr/local/share/ember/models
```

**Direct link:** https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF

### Option B: PatataAliena Q4_K_M GGUF

Alternative community conversion with Q4_K_M quantization.

```bash
# Download from PatataAliena
huggingface-cli download PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF qwen2.5-vl-7b-instruct-q4_k_m.gguf --local-dir /usr/local/share/ember/models
```

**Direct link:** https://huggingface.co/PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF

### Option C: Manual Download

1. Visit one of the links above
2. Download the `.gguf` file (Q4_K_M recommended, ~4-5GB)
3. Move it to the models directory:

```bash
mv ~/Downloads/*.gguf /usr/local/share/ember/models/
```

### Available Quantizations (Unsloth)

| Quantization | Size | Quality | Speed | Recommended For |
|--------------|------|---------|-------|-----------------|
| Q2_K | ~2.5GB | Lower | Fastest | Low RAM systems |
| Q4_K_M | ~4.5GB | Good | Fast | **Most users** |
| Q5_K_M | ~5.5GB | Better | Medium | Better quality |
| Q8_0 | ~8GB | Best | Slower | High RAM systems |

> 💡 **Tip:** Q4_K_M offers the best balance between quality and performance for most systems.

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

### Create Virtual Environment and Install Python Package

```bash
cd ~/emberos

# Create virtual environment
python -m venv ~/.local/share/ember/venv

# Activate it
source ~/.local/share/ember/venv/bin/activate

# Install EmberOS
pip install -e .

# Deactivate when done
deactivate
```

### Create CLI Wrapper Scripts

```bash
mkdir -p ~/.local/bin

# Create ember wrapper
cat > ~/.local/bin/ember << 'EOF'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/ember" "$@"
EOF
chmod +x ~/.local/bin/ember

# Create ember-ui wrapper
cat > ~/.local/bin/ember-ui << 'EOF'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/ember-ui" "$@"
EOF
chmod +x ~/.local/bin/ember-ui

# Create emberd wrapper
cat > ~/.local/bin/emberd << 'EOF'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/emberd" "$@"
EOF
chmod +x ~/.local/bin/emberd
```

### Add ~/.local/bin to PATH (if not already)

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload:

```bash
source ~/.bashrc  # or source ~/.zshrc
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

The model filename varies depending on where you downloaded it from:

| Source | Filename |
|--------|----------|
| Unsloth | `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` |
| PatataAliena | `qwen2.5-vl-7b-instruct-q4_k_m.gguf` |

Check what model file you have:

```bash
ls /usr/local/share/ember/models/
```

Edit the service file to match your model filename:

```bash
nano ~/.config/systemd/user/ember-llm.service
```

Change the `--model` line to match your file:

```ini
# For Unsloth download:
--model /usr/local/share/ember/models/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf

# OR for PatataAliena download:
--model /usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf
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

# Remove CLI wrapper scripts
rm -f ~/.local/bin/ember ~/.local/bin/ember-ui ~/.local/bin/emberd

# Remove files (includes virtual environment)
rm -rf ~/.local/share/ember
rm -rf ~/.config/ember
rm -rf ~/.cache/ember
rm -f ~/.config/systemd/user/ember*.service
rm -f ~/.local/share/dbus-1/services/org.ember.Agent.service
rm -f ~/.local/share/applications/emberos.desktop
rm -f ~/.local/share/icons/hicolor/256x256/apps/emberos.png

# Reload systemd
systemctl --user daemon-reload

# Optionally remove models
sudo rm -rf /usr/local/share/ember
```

---

## Support

- **Documentation:** https://docs.emberos.org
- **Issues:** https://github.com/emberos/emberos/issues
- **Discussions:** https://github.com/emberos/emberos/discussions

