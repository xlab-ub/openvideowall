#!/bin/bash
# Multi-Screen Client Systemd System Service Installer

echo "🔧 Installing Multi-Screen Client System Services"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    echo "   Run: sudo ./install_system_services.sh"
    exit 1
fi

# Get target user and home directory (overridable via flags)
# Defaults: use the invoking sudo user if available, else fallback to current
TARGET_USER_DEFAULT="${SUDO_USER:-$(logname 2>/dev/null || whoami)}"
HOME_DIR_DEFAULT=$(eval echo ~"$TARGET_USER_DEFAULT")

TARGET_USER=""
HOME_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)
            TARGET_USER="$2"
            shift 2
            ;;
        --home_dir|--home-dir)
            HOME_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: sudo ./install_system_services.sh [--user USERNAME] [--home_dir /home/USERNAME]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: sudo ./install_system_services.sh [--user USERNAME] [--home_dir /home/USERNAME]"
            exit 1
            ;;
    esac
done

# Apply defaults if not provided
if [ -z "$TARGET_USER" ]; then
    TARGET_USER="$TARGET_USER_DEFAULT"
fi
if [ -z "$HOME_DIR" ]; then
    HOME_DIR=$(eval echo ~"$TARGET_USER")
fi

SERVICE_DIR="$HOME_DIR/Multiscreen/client"

echo "📋 Service Configuration:"
echo "   User: $TARGET_USER"
echo "   Home: $HOME_DIR"
echo "   Service Directory: $SERVICE_DIR"
echo ""

# Check if service files exist
if [ ! -f "multiscreen-client-1-system.service" ] || [ ! -f "multiscreen-client-2-system.service" ]; then
    echo "❌ System service files not found in current directory"
    echo "   Make sure you're in the client directory with the .service files"
    exit 1
fi

# Check if run_client.sh exists and is executable
if [ ! -f "run_client.sh" ] || [ ! -x "run_client.sh" ]; then
    echo "❌ run_client.sh not found or not executable"
    echo "   Make sure run_client.sh exists and has execute permissions"
    exit 1
fi

echo "📦 Installing system services..."

# Copy service files to systemd directory
cp multiscreen-client-1-system.service /etc/systemd/system/multiscreen-client-1.service
cp multiscreen-client-2-system.service /etc/systemd/system/multiscreen-client-2.service

# Inject user and home directory into unit files
sed -i "s|__USER__|$TARGET_USER|g" /etc/systemd/system/multiscreen-client-1.service
sed -i "s|__HOME_DIR__|$HOME_DIR|g" /etc/systemd/system/multiscreen-client-1.service
sed -i "s|__USER__|$TARGET_USER|g" /etc/systemd/system/multiscreen-client-2.service
sed -i "s|__HOME_DIR__|$HOME_DIR|g" /etc/systemd/system/multiscreen-client-2.service

echo "✅ Service files installed to /etc/systemd/system/"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

echo ""
echo "🎯 Service Management Commands:"
echo "==============================="
echo ""
echo "Start services:"
echo "  sudo systemctl start multiscreen-client-1"
echo "  sudo systemctl start multiscreen-client-2"
echo ""
echo "Stop services:"
echo "  sudo systemctl stop multiscreen-client-1"
echo "  sudo systemctl stop multiscreen-client-2"
echo ""
echo "Check status:"
echo "  sudo systemctl status multiscreen-client-1"
echo "  sudo systemctl status multiscreen-client-2"
echo ""
echo "View logs:"
echo "  sudo journalctl -u multiscreen-client-1 -f"
echo "  sudo journalctl -u multiscreen-client-2 -f"
echo ""
echo "Enable auto-start (start on boot):"
echo "  sudo systemctl enable multiscreen-client-1"
echo "  sudo systemctl enable multiscreen-client-2"
echo ""
echo "Disable auto-start:"
echo "  sudo systemctl disable multiscreen-client-1"
echo "  sudo systemctl disable multiscreen-client-2"
echo ""

# Ask if user wants to start the services now
read -p "🚀 Do you want to start the services now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting services..."
    systemctl start multiscreen-client-1
    systemctl start multiscreen-client-2
    
    echo "Checking status..."
    systemctl status multiscreen-client-1 --no-pager
    systemctl status multiscreen-client-2 --no-pager
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "💡 Tips:"
echo "   - Services will restart automatically if they crash"
echo "   - Check logs if you have issues: sudo journalctl -u multiscreen-client-1 -f"
echo "   - Enable auto-start if you want them to start on boot"



