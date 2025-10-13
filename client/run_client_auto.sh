#!/bin/bash

# Auto-positioning client runner
# Usage: ./run_client_auto.sh [monitor_number] [other_client_args...]

# Default values
MONITOR=0
SERVER="http://128.205.220.234:5000"
HOSTNAME="client-auto"
DISPLAY_NAME="Auto Client"

# Parse arguments
if [ $# -gt 0 ]; then
    MONITOR=$1
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER="$2"
            shift 2
            ;;
        --hostname)
            HOSTNAME="$2"
            shift 2
            ;;
        --display-name)
            DISPLAY_NAME="$2"
            shift 2
            ;;
        *)
            # Pass through other arguments
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

echo "🚀 Starting Multi-Screen Client with auto-positioning..."
echo "   Monitor: $MONITOR"
echo "   Server: $SERVER"
echo "   Hostname: $HOSTNAME"
echo "   Display Name: $DISPLAY_NAME"

# Start the client in the background
DISPLAY=:0 nohup python3 client.py \
    --server "$SERVER" \
    --hostname "$HOSTNAME" \
    --display-name "$DISPLAY_NAME" \
    --monitor "$MONITOR" \
    $EXTRA_ARGS > "client_${HOSTNAME}.log" 2>&1 &

CLIENT_PID=$!
echo "   Client PID: $CLIENT_PID"
echo "   Log file: client_${HOSTNAME}.log"

# Wait a bit for the client to start
sleep 5

# Try to position the window automatically
echo "🎯 Attempting automatic window positioning..."
DISPLAY=:0 python3 position_windows.py $((MONITOR + 1))

echo "✅ Client started! Check the log file for details."
echo "   To stop: kill $CLIENT_PID"
echo "   To reposition: DISPLAY=:0 python3 position_windows.py $((MONITOR + 1))"
