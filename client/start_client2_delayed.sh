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

echo "🚀 Starting Multi-Screen Client 2..."
echo "   Server: $CLIENT2_SERVER_URL"
echo "   Hostname: $CLIENT2_HOSTNAME"
echo "   Display: $CLIENT2_DISPLAY_NAME"
echo "   Monitor: $CLIENT2_MONITOR_INDEX ($CLIENT2_MONITOR_LOCATION)"
cd "$(dirname "$0")"
exec ./run_client.sh --server "$CLIENT2_SERVER_URL" --hostname "$CLIENT2_HOSTNAME" --display-name "$CLIENT2_DISPLAY_NAME" --monitor "$CLIENT2_MONITOR_INDEX"
