#!/bin/bash
# Multi-Screen Client Runner Script
# This script runs the multi-screen client with common options

# Default values
SERVER_URL="http://192.168.1.100:5000"
HOSTNAME=""
DISPLAY_NAME=""
FORCE_FFPLAY=""
MONITOR=""
DEBUG=""
NO_HOTKEYS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_URL="$2"
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
        --force-ffplay)
            FORCE_FFPLAY="--force-ffplay"
            shift
            ;;
        --monitor)
            MONITOR="--monitor $2"
            shift 2
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --no-hotkeys)
            NO_HOTKEYS="--no-hotkeys"
            shift
            ;;
        --help)
            echo "Multi-Screen Client Runner"
            echo "Usage: $0 [options]"
            echo ""
            echo "Required Options:"
            echo "  --server URL         : Server URL (default: http://192.168.1.100:5000)"
            echo "  --hostname NAME      : Client hostname (required)"
            echo "  --display-name NAME  : Display name for admin interface (required)"
            echo ""
            echo "Optional Options:"
            echo "  --force-ffplay       : Force use of ffplay instead of smart selection"
            echo "  --monitor INDEX      : Monitor index to start on (0-3: 0=left, 1=right, 2=far-right, 3=bottom)"
            echo "  --debug              : Enable debug logging"
            echo "  --no-hotkeys         : Disable hotkey window manager (prevents gray boxes)"
            echo "  --help               : Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --server http://192.168.1.100:5000 --hostname rpi-client-1 --display-name \"Monitor 1\""
            echo "  $0 --server http://192.168.1.100:5000 --hostname rpi-client-2 --display-name \"Monitor 2\" --monitor 1"
            echo "  $0 --server http://192.168.1.100:5000 --hostname rpi-client-3 --display-name \"Monitor 3\" --monitor 2 --force-ffplay"
            echo ""
            echo "Hotkeys (once running):"
            echo "  Ctrl+M or Ctrl+Right: Move to next monitor"
            echo "  Ctrl+Left: Move to previous monitor"
            echo "  Ctrl+1-4: Move to specific monitor"
            echo "  Ctrl+H: Show help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check required arguments
if [ -z "$HOSTNAME" ] || [ -z "$DISPLAY_NAME" ]; then
    echo "Error: --hostname and --display-name are required"
    echo "Use --help for usage information"
    exit 1
fi

echo "Starting Multi-Screen Client..."
echo "Server: $SERVER_URL"
echo "Hostname: $HOSTNAME"
echo "Display Name: $DISPLAY_NAME"
echo "Force ffplay: $([ -n "$FORCE_FFPLAY" ] && echo "Yes" || echo "No")"
echo "Debug mode: $([ -n "$DEBUG" ] && echo "Yes" || echo "No")"
echo "Hotkeys: $([ -n "$NO_HOTKEYS" ] && echo "Disabled" || echo "Enabled")"
echo ""
echo "Hotkeys:"
echo "  Ctrl+M: Move to next monitor"
echo "  Ctrl+1-4: Move to specific monitor"
echo "  Ctrl+H: Show help"
echo ""

# Run the client
DISPLAY=:0 python3 client.py --server "$SERVER_URL" --hostname "$HOSTNAME" --display-name "$DISPLAY_NAME" $FORCE_FFPLAY $MONITOR $DEBUG $NO_HOTKEYS
