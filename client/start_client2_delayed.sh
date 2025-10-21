#!/bin/bash
# Delayed startup script for Multi-Screen Client 2

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env file..."
    source .env
fi

# Environment variables for Client 2 (must be set in .env file or environment)
# CLIENT2_SERVER_URL, CLIENT2_HOSTNAME, CLIENT2_DISPLAY_NAME, CLIENT2_MONITOR_INDEX, CLIENT2_MONITOR_LOCATION, CLIENT2_STARTUP_DELAY

echo "🕐 Waiting $CLIENT2_STARTUP_DELAY seconds before starting Client 2..."
sleep $CLIENT2_STARTUP_DELAY

echo "🚀 Starting Multi-Screen Client 2 (direct python)..."
echo "   Server: $CLIENT2_SERVER_URL"
echo "   Hostname: $CLIENT2_HOSTNAME"
echo "   Display: $CLIENT2_DISPLAY_NAME"
echo "   Monitor: $CLIENT2_MONITOR_INDEX ($CLIENT2_MONITOR_LOCATION)"
cd "$(dirname "$0")"

# Ensure X/xdotool environment
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:$PATH"

# Wait until X socket and runtime dir exist
for i in $(seq 1 20); do
    if [ -S /tmp/.X11-unix/X0 ] && [ -d "$XDG_RUNTIME_DIR" ]; then
        break
    fi
    sleep 1
done
exec python3 client.py --server "$CLIENT2_SERVER_URL" --hostname "$CLIENT2_HOSTNAME" --display-name "$CLIENT2_DISPLAY_NAME" --monitor "$CLIENT2_MONITOR_INDEX"
