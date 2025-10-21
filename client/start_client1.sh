#!/bin/bash
# Startup script for Multi-Screen Client 1

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env file..."
    source .env
fi

# Environment variables for Client 1 (must be set in .env file or environment)
# CLIENT1_SERVER_URL, CLIENT1_HOSTNAME, CLIENT1_DISPLAY_NAME, CLIENT1_MONITOR_INDEX, CLIENT1_MONITOR_LOCATION

echo "🚀 Starting Multi-Screen Client 1 (direct python)..."
echo "   Server: $CLIENT1_SERVER_URL"
echo "   Hostname: $CLIENT1_HOSTNAME"
echo "   Display: $CLIENT1_DISPLAY_NAME"
echo "   Monitor: 3 (override)"
cd "$(dirname "$0")"

# Ensure X/xdotool environment
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:$PATH"

# Quick check for X socket and runtime dir
if [ ! -S /tmp/.X11-unix/X0 ] || [ ! -d "$XDG_RUNTIME_DIR" ]; then
    echo "   ⚠️  X socket or runtime dir not ready, continuing anyway..."
fi

exec python3 client.py --server "$CLIENT1_SERVER_URL" --hostname "$CLIENT1_HOSTNAME" --display-name "$CLIENT1_DISPLAY_NAME" --monitor 3
