#!/bin/bash
#
# EmberOS Installation Script
#
# This script installs EmberOS on Arch Linux systems.
# Run as a regular user (not root).
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

EMBER_VERSION="1.0.0"
EMBER_DIR="$HOME/.local/share/ember"
CONFIG_DIR="$HOME/.config/ember"
CACHE_DIR="$HOME/.cache/ember"
MODEL_DIR="/usr/local/share/ember/models"

# Banner
echo -e "${ORANGE}"
cat << 'EOF'
  ███████ ███    ███ ██████  ███████ ██████   ██████  ███████
  ██      ████  ████ ██   ██ ██      ██   ██ ██    ██ ██
  █████   ██ ████ ██ ██████  █████   ██████  ██    ██ ███████
  ██      ██  ██  ██ ██   ██ ██      ██   ██ ██    ██      ██
  ███████ ██      ██ ██████  ███████ ██   ██  ██████  ███████
EOF
echo -e "${NC}"
echo -e "${BLUE}EmberOS Installer v${EMBER_VERSION}${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root!${NC}"
    echo "Run as a regular user. sudo will be used when needed."
    exit 1
fi

# Check for Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo -e "${YELLOW}Warning: This script is designed for Arch Linux.${NC}"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Step 1: Installing system dependencies...${NC}"

# Install dependencies
sudo pacman -S --needed --noconfirm \
    python \
    python-pip \
    python-virtualenv \
    python-pyqt6 \
    sqlite \
    xclip \
    xdotool \
    wmctrl \
    libnotify \
    dbus

echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "${BLUE}Step 2: Creating directories...${NC}"

# Create directories
mkdir -p "$EMBER_DIR"
mkdir -p "$EMBER_DIR/tools"
mkdir -p "$EMBER_DIR/vectors"
mkdir -p "$EMBER_DIR/backups"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CACHE_DIR"
mkdir -p "$CACHE_DIR/logs"

# Create model directory (requires sudo)
if [ ! -d "$MODEL_DIR" ]; then
    sudo mkdir -p "$MODEL_DIR"
    sudo chown "$USER:$USER" "$MODEL_DIR"
fi

echo -e "${GREEN}✓ Directories created${NC}"

echo -e "${BLUE}Step 3: Installing EmberOS Python package...${NC}"

# Install the package using virtual environment (PEP 668 compliant)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$EMBER_DIR/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python -m venv "$VENV_DIR"
fi

# Activate virtual environment and install
source "$VENV_DIR/bin/activate"

# Upgrade pip in venv
pip install --upgrade pip

if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    # Development install from source
    pip install -e "$SCRIPT_DIR"
else
    # Install from PyPI (when available)
    pip install emberos
fi

deactivate

echo -e "${GREEN}✓ EmberOS package installed (in virtual environment)${NC}"

echo -e "${BLUE}Step 4: Creating CLI wrapper scripts...${NC}"

# Create wrapper scripts in ~/.local/bin for easy CLI access
mkdir -p "$HOME/.local/bin"

# Create ember wrapper
cat > "$HOME/.local/bin/ember" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/ember" "$@"
WRAPPER
chmod +x "$HOME/.local/bin/ember"

# Create ember-ui wrapper
cat > "$HOME/.local/bin/ember-ui" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/ember-ui" "$@"
WRAPPER
chmod +x "$HOME/.local/bin/ember-ui"

# Create emberd wrapper
cat > "$HOME/.local/bin/emberd" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.local/share/ember/venv/bin/emberd" "$@"
WRAPPER
chmod +x "$HOME/.local/bin/emberd"

echo -e "${GREEN}✓ CLI wrapper scripts created${NC}"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}⚠ ~/.local/bin is not in your PATH${NC}"
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo -e "${BLUE}Step 5: Installing configuration...${NC}"

# Copy default config if not exists
if [ ! -f "$CONFIG_DIR/emberos.toml" ]; then
    if [ -f "$SCRIPT_DIR/configs/emberos.toml" ]; then
        cp "$SCRIPT_DIR/configs/emberos.toml" "$CONFIG_DIR/"
    fi
fi

echo -e "${GREEN}✓ Configuration installed${NC}"

echo -e "${BLUE}Step 6: Installing systemd services...${NC}"

# Create user systemd directory
mkdir -p "$HOME/.config/systemd/user"

# Copy service files
if [ -d "$SCRIPT_DIR/packaging" ]; then
    cp "$SCRIPT_DIR/packaging/emberd.service" "$HOME/.config/systemd/user/"
    cp "$SCRIPT_DIR/packaging/ember-llm.service" "$HOME/.config/systemd/user/"
fi

# Reload systemd
systemctl --user daemon-reload

echo -e "${GREEN}✓ Systemd services installed${NC}"

echo -e "${BLUE}Step 7: Installing D-Bus service...${NC}"

# Copy D-Bus service file
mkdir -p "$HOME/.local/share/dbus-1/services"
if [ -f "$SCRIPT_DIR/packaging/org.ember.Agent.service" ]; then
    cp "$SCRIPT_DIR/packaging/org.ember.Agent.service" "$HOME/.local/share/dbus-1/services/"
fi

echo -e "${GREEN}✓ D-Bus service installed${NC}"

echo -e "${BLUE}Step 8: Installing desktop entry and icon...${NC}"

# Install desktop entry
mkdir -p "$HOME/.local/share/applications"
if [ -f "$SCRIPT_DIR/packaging/emberos.desktop" ]; then
    cp "$SCRIPT_DIR/packaging/emberos.desktop" "$HOME/.local/share/applications/"
fi

# Install icon
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
if [ -f "$SCRIPT_DIR/assets/zevion-logo.png" ]; then
    cp "$SCRIPT_DIR/assets/zevion-logo.png" "$HOME/.local/share/icons/hicolor/256x256/apps/emberos.png"
fi

# Also copy to ember data directory for the GUI
mkdir -p "$EMBER_DIR/assets"
if [ -f "$SCRIPT_DIR/assets/zevion-logo.png" ]; then
    cp "$SCRIPT_DIR/assets/zevion-logo.png" "$EMBER_DIR/assets/"
fi

# Update icon cache
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo -e "${GREEN}✓ Desktop entry and icon installed${NC}"

# Check for LLM model
echo ""
echo -e "${BLUE}Step 9: Checking for LLM model...${NC}"

if [ -z "$(ls -A $MODEL_DIR 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠ No LLM model found in $MODEL_DIR${NC}"
    echo ""
    echo "EmberOS requires a local LLM model to function."
    echo "Recommended: Qwen2.5-VL-7B-Instruct (Q4_K_M quantization)"
    echo ""
    echo "Download options:"
    echo "  1. Unsloth (recommended): https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF"
    echo "  2. PatataAliena: https://huggingface.co/PatataAliena/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF"
    echo ""
    echo "Quick download command:"
    echo "  pip install huggingface-hub"
    echo "  huggingface-cli download unsloth/Qwen2.5-VL-7B-Instruct-GGUF Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf --local-dir $MODEL_DIR"
    echo ""
else
    echo -e "${GREEN}✓ LLM model found${NC}"
fi

# Check for llama.cpp
echo ""
echo -e "${BLUE}Step 10: Checking for llama.cpp...${NC}"

if ! command -v llama-server &> /dev/null; then
    echo -e "${YELLOW}⚠ llama.cpp not found${NC}"
    echo ""
    echo "EmberOS uses llama.cpp for local LLM inference."
    echo "Install options:"
    echo "  - AUR: yay -S llama.cpp"
    echo "  - Manual: https://github.com/ggerganov/llama.cpp"
else
    echo -e "${GREEN}✓ llama.cpp found${NC}"
fi

# Done
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  EmberOS installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Ensure you have an LLM model in $MODEL_DIR"
echo ""
echo "  2. Start the services:"
echo -e "     ${BLUE}systemctl --user enable --now ember-llm${NC}"
echo -e "     ${BLUE}systemctl --user enable --now emberd${NC}"
echo ""
echo "  3. Launch EmberOS:"
echo -e "     GUI:  ${BLUE}ember-ui${NC}"
echo -e "     CLI:  ${BLUE}ember${NC}"
echo ""
echo "  4. Try it out:"
echo -e "     ${BLUE}ember${NC}"
echo "     ember> find my documents"
echo "     ember> organize ~/Downloads"
echo ""
echo "Documentation: https://docs.emberos.org"
echo "Report issues: https://github.com/emberos/emberos/issues"
echo ""

