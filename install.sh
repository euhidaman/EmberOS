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

# Check Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python -c "import sys; print(sys.version_info.minor)")

echo -e "${BLUE}Detected Python version: ${PYTHON_VERSION}${NC}"

# Determine which Python to use for venv
PYTHON_CMD="python"

if [ "$PYTHON_MINOR" -ge 14 ]; then
    echo -e "${YELLOW}⚠ Python 3.14+ detected. Some dependencies (onnxruntime/chromadb) may not be available.${NC}"

    # Check if Python 3.12 is available
    if command -v python3.12 &> /dev/null; then
        echo -e "${GREEN}Python 3.12 found! Using it for better compatibility.${NC}"
        PYTHON_CMD="python3.12"
    else
        echo -e "${YELLOW}Python 3.12 not found. Trying to install...${NC}"

        # Try official package first (python3.12)
        if sudo pacman -S --needed --noconfirm python3.12 2>/dev/null; then
            echo -e "${GREEN}Python 3.12 installed successfully!${NC}"
            PYTHON_CMD="python3.12"
        # Try AUR package if official not found (python312)
        elif command -v yay &> /dev/null && yay -S --needed --noconfirm python312 2>/dev/null; then
            echo -e "${GREEN}Python 3.12 installed from AUR!${NC}"
            PYTHON_CMD="python3.12"
        else
            echo -e "${YELLOW}Could not install Python 3.12 automatically.${NC}"
            echo "EmberOS will work but without vector search (ChromaDB)."
            echo ""
            echo "To install Python 3.12 manually:"
            echo "  sudo pacman -S python3.12  # or"
            echo "  yay -S python312            # from AUR"
            echo ""
        fi
    fi
fi

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
    echo "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv "$VENV_DIR"
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

    # Install LLM manager script
    if [ -f "$SCRIPT_DIR/packaging/ember-llm-manager.sh" ]; then
        sudo cp "$SCRIPT_DIR/packaging/ember-llm-manager.sh" /usr/local/bin/ember-llm-manager
        sudo chmod +x /usr/local/bin/ember-llm-manager
    fi
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
echo -e "${BLUE}Step 9: Checking for LLM models...${NC}"

# Check VLM model
if [ ! -f "$MODEL_DIR/qwen2.5-vl-7b-instruct-q4_k_m.gguf" ]; then
    echo -e "${YELLOW}⚠ Vision model not found in $MODEL_DIR${NC}"
    echo ""
    echo "Vision Model (for image/PDF tasks):"
    echo "  Qwen2.5-VL-7B-Instruct (Q4_K_M) - ~4GB"
    echo ""
    echo "Download:"
    echo "  huggingface-cli download unsloth/Qwen2.5-VL-7B-Instruct-GGUF \\"
    echo "    Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \\"
    echo "    --local-dir $MODEL_DIR \\"
    echo "    --local-dir-use-symlinks False"
    echo "  sudo mv $MODEL_DIR/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf $MODEL_DIR/qwen2.5-vl-7b-instruct-q4_k_m.gguf"
    echo ""
else
    echo -e "${GREEN}✓ Vision model found${NC}"
fi

# Check BitNet model directory
if [ ! -d "$MODEL_DIR/bitnet" ]; then
    echo -e "${YELLOW}⚠ BitNet model not found in $MODEL_DIR/bitnet${NC}"
    echo ""
    echo "Text Model (fast, lightweight for text-only tasks):"
    echo "  BitNet b1.58 - Microsoft's 1-bit LLM"
    echo ""
    echo "This will be downloaded and built automatically."
    echo ""
else
    echo -e "${GREEN}✓ BitNet model found${NC}"
fi

# Check for llama.cpp
echo ""
echo -e "${BLUE}Step 10: Checking for llama.cpp...${NC}"

if ! command -v llama-server &> /dev/null; then
    echo -e "${YELLOW}⚠ llama.cpp not found${NC}"
    echo ""
    echo "llama.cpp (for Vision model):"
    echo "  Install: yay -S llama.cpp"
    echo ""
else
    echo -e "${GREEN}✓ llama.cpp found: $(which llama-server)${NC}"
fi

# Check/Setup BitNet
echo ""
echo -e "${BLUE}Step 11: Setting up BitNet...${NC}"

BITNET_DIR="$HOME/.local/share/bitnet"
BITNET_SERVER="/usr/local/bin/bitnet-server"

if [ -d "../BitNet" ]; then
    BITNET_SOURCE="$(cd ../BitNet && pwd)"
    echo "Found BitNet source at: $BITNET_SOURCE"

    if [ ! -f "$BITNET_SERVER" ]; then
        echo "Building BitNet server..."

        # Install BitNet dependencies
        if ! command -v cmake &> /dev/null; then
            echo "Installing cmake..."
            sudo pacman -S --needed --noconfirm cmake
        fi

        # Build BitNet
        cd "$BITNET_SOURCE"

        # Run setup to download model if needed
        if [ ! -d "models/bitnet-b1.58-2B-4T" ]; then
            echo "Downloading Microsoft BitNet 2B model..."
            python setup_env.py --hf-repo microsoft/bitnet-b1.58-2B-4T -q i2_s
        fi

        # Copy built server
        if [ -f "build/bin/llama-server" ]; then
            echo "Installing BitNet server..."
            sudo cp build/bin/llama-server "$BITNET_SERVER"
            sudo chmod +x "$BITNET_SERVER"

            # Copy model to ember directory
            sudo mkdir -p "$MODEL_DIR/bitnet"
            sudo cp models/bitnet-b1.58-2B-4T/ggml-model-i2_s.gguf "$MODEL_DIR/bitnet/"

            echo -e "${GREEN}✓ BitNet installed successfully${NC}"
        else
            echo -e "${YELLOW}⚠ BitNet build failed. Text-only speedup unavailable.${NC}"
            echo "EmberOS will use the vision model for all tasks."
        fi

        cd "$SCRIPT_DIR"
    else
        echo -e "${GREEN}✓ BitNet server already installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ BitNet source not found at ../BitNet${NC}"
    echo ""
    echo "To install BitNet for faster text inference:"
    echo "  1. Clone: git clone https://github.com/microsoft/BitNet ../BitNet"
    echo "  2. Run: cd ../BitNet && python setup_env.py --hf-repo microsoft/bitnet-b1.58-2B-4T -q i2_s"
    echo "  3. Re-run this installer"
    echo ""
    echo "EmberOS will work without BitNet (using vision model for all tasks)."
fi

# Done
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  EmberOS installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Ensure you have the models:"
echo "     - BitNet (fast text):  $MODEL_DIR/bitnet/ggml-model-i2_s.gguf"
echo "     - Qwen2.5-VL (vision): $MODEL_DIR/qwen2.5-vl-7b-instruct-q4_k_m.gguf"
echo ""
echo "  2. Start the services:"
echo -e "     ${BLUE}systemctl --user enable --now ember-llm${NC}     # Both models (ports 8080 + 11434)"
echo -e "     ${BLUE}systemctl --user enable --now emberd${NC}        # EmberOS daemon"
echo ""
echo "  3. Check service status:"
echo -e "     ${BLUE}systemctl --user status ember-llm emberd${NC}"
echo ""
echo "  4. Launch EmberOS:"
echo -e "     GUI:  ${BLUE}ember-ui${NC}"
echo -e "     CLI:  ${BLUE}ember${NC}"
echo ""
echo "  5. Try it out:"
echo -e "     ${BLUE}ember${NC}"
echo "     ember> create a budget spreadsheet"
echo "     ember> organize ~/Downloads"
echo ""
echo "Model Architecture:"
echo "  • Single service manages both models"
echo "  • BitNet (port 8080) handles fast text-only tasks (3-5x faster)"
echo "  • Qwen2.5-VL (port 11434) handles images, PDFs, screenshots"
echo "  • EmberOS automatically routes requests to the right model"
echo ""
echo "Documentation: https://docs.emberos.org"
echo "Report issues: https://github.com/emberos/emberos/issues"
echo ""

