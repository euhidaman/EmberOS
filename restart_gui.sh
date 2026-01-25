#!/bin/bash

# EmberOS GUI Restart Script
# Run this to reload the GUI with code changes

echo "🔥 EmberOS GUI Restart"
echo "====================="

# Kill existing GUI
echo "→ Stopping existing GUI..."
pkill -f ember-ui
sleep 1

# Check if venv exists
if [ ! -d "$HOME/.local/share/ember/venv" ]; then
    echo "❌ Virtual environment not found at ~/.local/share/ember/venv"
    exit 1
fi

# Reinstall in editable mode (picks up code changes)
echo "→ Reinstalling EmberOS package (editable mode)..."
cd ~/EmberOS || cd ~/emberos || cd "$(dirname "$0")"
source ~/.local/share/ember/venv/bin/activate
pip install -e . --quiet
deactivate

echo "→ Starting GUI..."
echo ""

# Start GUI
ember-ui

echo ""
echo "✓ Done!"

