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
exec DISPLAY=:0 python3 client.py --server "$CLIENT1_SERVER_URL" --hostname "$CLIENT1_HOSTNAME" --display-name "$CLIENT1_DISPLAY_NAME" --monitor 3
