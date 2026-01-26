#!/bin/bash
#
# EmberOS LLM Manager
# Manages both BitNet (text) and Qwen2.5-VL (vision) models
#

BITNET_MODEL="/usr/local/share/ember/models/bitnet/ggml-model-i2_s.gguf"
VISION_MODEL="/usr/local/share/ember/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf"

BITNET_SERVER="/usr/local/bin/bitnet-server"
VISION_SERVER="/usr/bin/llama-server"

# Start BitNet (text model) on port 8080
if [ -f "$BITNET_MODEL" ] && [ -x "$BITNET_SERVER" ]; then
    echo "Starting BitNet text model on port 8080..."
    "$BITNET_SERVER" \
        --model "$BITNET_MODEL" \
        --host 127.0.0.1 \
        --port 8080 \
        --ctx-size 4096 \
        --threads 4 \
        --n-gpu-layers 0 \
        --temp 0.1 \
        2>&1 | sed 's/^/[BitNet] /' &

    BITNET_PID=$!
else
    echo "BitNet not available (model or server not found)"
    BITNET_PID=""
fi

# Start Qwen2.5-VL (vision model) on port 11434
if [ -f "$VISION_MODEL" ] && [ -x "$VISION_SERVER" ]; then
    echo "Starting Qwen2.5-VL vision model on port 11434..."
    "$VISION_SERVER" \
        --model "$VISION_MODEL" \
        --host 127.0.0.1 \
        --port 11434 \
        --ctx-size 8192 \
        --threads 4 \
        --n-gpu-layers 0 \
        2>&1 | sed 's/^/[Qwen2.5-VL] /' &

    VISION_PID=$!
else
    echo "Qwen2.5-VL not available (model or server not found)"
    VISION_PID=""
fi

# Wait for any process to exit
wait -n

# If one exits, kill the other
if [ -n "$BITNET_PID" ]; then
    kill $BITNET_PID 2>/dev/null
fi

if [ -n "$VISION_PID" ]; then
    kill $VISION_PID 2>/dev/null
fi

