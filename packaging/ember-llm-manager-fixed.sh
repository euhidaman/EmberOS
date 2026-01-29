#!/bin/bash
#
# EmberOS LLM Manager
# Manages Qwen2.5-VL (vision) model
# (BitNet disabled due to incompatibility)
#

set -e

BITNET_MODEL="/usr/local/share/ember/models/bitnet/ggml-model-i2_s.gguf"
VISION_MODEL="/usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf"
LLAMA_SERVER="/usr/bin/llama-server"

BITNET_PID=""
VISION_PID=""

cleanup() {
    echo "Shutting down LLM servers..."
    if [ -n "$BITNET_PID" ] && kill -0 $BITNET_PID 2>/dev/null; then
        echo "Stopping BitNet (PID $BITNET_PID)..."
        kill $BITNET_PID 2>/dev/null || true
    fi
    if [ -n "$VISION_PID" ] && kill -0 $VISION_PID 2>/dev/null; then
        echo "Stopping Qwen2.5-VL (PID $VISION_PID)..."
        kill $VISION_PID 2>/dev/null || true
    fi
    wait
    exit 0
}

trap cleanup SIGTERM SIGINT EXIT

# Check llama-server exists
if [ ! -x "$LLAMA_SERVER" ]; then
    echo "ERROR: llama-server not found at $LLAMA_SERVER"
    echo "Install with: yay -S llama.cpp"
    exit 1
fi

# BitNet disabled
echo "BitNet text model disabled (incompatible with current llama.cpp)"

# Start Qwen2.5-VL (vision model) on port 11434
if [ -f "$VISION_MODEL" ]; then
    echo "Starting Qwen2.5-VL vision model (port 11434)..."
    "$LLAMA_SERVER" \
        --model "$VISION_MODEL" \
        --host 127.0.0.1 \
        --port 11434 \
        --ctx-size 8192 \
        --threads 4 \
        --n-gpu-layers 0 \
        --log-disable 2>&1 | while IFS= read -r line; do echo "[Qwen2.5-VL] $line"; done &

    VISION_PID=$!
    echo "Qwen2.5-VL started (PID: $VISION_PID)"
    sleep 1

    # Verify it's still running
    if ! kill -0 $VISION_PID 2>/dev/null; then
        echo "WARNING: Qwen2.5-VL failed to start"
        VISION_PID=""
    fi
else
    echo "WARNING: Qwen2.5-VL model not found at $VISION_MODEL"
fi

# Check if at least one model started
if [ -z "$BITNET_PID" ] && [ -z "$VISION_PID" ]; then
    echo "ERROR: No models could be started!"
    exit 1
fi

echo "LLM servers running. Waiting for processes..."
echo "  Qwen2.5-VL: ${VISION_PID:-not running} (port 11434)"

# Wait for all background processes
wait
