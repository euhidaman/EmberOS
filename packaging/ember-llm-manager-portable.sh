#!/bin/bash
#
# EmberOS LLM Manager (Fixed Absolute Paths)
#

set -e

PROJECT_DIR="/home/leonardo890229/Desktop/github/EmberOS"

BITNET_MODEL="$PROJECT_DIR/models/bitnet-2b.gguf"
VISION_MODEL="$PROJECT_DIR/models/qwen-vision.gguf"

# System llama-server for Qwen
SYSTEM_LLAMA_SERVER="/usr/bin/llama-server"

# Local BitNet-compatible server
BITNET_SERVER="$PROJECT_DIR/bin/bitnet-server"

BITNET_PID=""
VISION_PID=""

cleanup() {
    echo "Shutting down LLM servers..."
    [ -n "$BITNET_PID" ] && kill $BITNET_PID 2>/dev/null || true
    [ -n "$VISION_PID" ] && kill $VISION_PID 2>/dev/null || true
    wait
    exit 0
}

trap cleanup SIGTERM SIGINT EXIT

# Check exist
if [ ! -x "$BITNET_SERVER" ]; then echo "ERROR: $BITNET_SERVER not found"; exit 1; fi

# Start BitNet (port 38080)
echo "Starting BitNet..."
"$BITNET_SERVER" \
    --model "$BITNET_MODEL" \
    --host 127.0.0.1 \
    --port 38080 \
    --ctx-size 2048 \
    --threads 2 \
    -n 4096 \
    --temp 0.1 \
    --log-disable & 
BITNET_PID=$!

# Start Qwen (port 11434)
echo "Starting Qwen..."
"$SYSTEM_LLAMA_SERVER" \
    --model "$VISION_MODEL" \
    --host 127.0.0.1 \
    --port 11434 \
    --ctx-size 8192 \
    --threads 4 \
    --log-disable & 
VISION_PID=$!

echo "LLM servers running."
wait