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

# Check if start scripts exist and are executable
if [ ! -f "start_client1.sh" ] || [ ! -x "start_client1.sh" ]; then
    echo "❌ start_client1.sh not found or not executable"
    echo "   Make sure start_client1.sh exists and has execute permissions"
    exit 1
fi
if [ ! -f "start_client2_delayed.sh" ] || [ ! -x "start_client2_delayed.sh" ]; then
    echo "❌ start_client2_delayed.sh not found or not executable"
    echo "   Make sure start_client2_delayed.sh exists and has execute permissions"
    exit 1
fi

echo "📦 Installing system services..."

# Stop running services first (if they exist)
echo "🛑 Stopping existing services (if running)..."
systemctl stop openvideowall-client-1 2>/dev/null || true
systemctl stop openvideowall-client-2 2>/dev/null || true
systemctl disable openvideowall-client-1 2>/dev/null || true
systemctl disable openvideowall-client-2 2>/dev/null || true
echo "✅ Existing services stopped and disabled"

# Ensure required packages for window control and playback
echo "🔍 Checking required packages (xdotool, wmctrl, ffmpeg)..."
if command -v apt >/dev/null 2>&1; then
    MISSING_PKGS=()
    for pkg in xdotool wmctrl ffmpeg; do
        dpkg -s "$pkg" >/dev/null 2>&1 || MISSING_PKGS+=("$pkg")
    done
    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo "⬇️  Installing: ${MISSING_PKGS[*]}"
        apt update && apt install -y ${MISSING_PKGS[*]}
    else
        echo "✅ Required packages already installed"
    fi
else
    echo "⚠️  Non-Debian system; ensure xdotool, wmctrl, and ffmpeg are installed manually."
fi

# Copy service files to systemd directory (install as openvideowall-*.service)
cp multiscreen-client-1-system.service /etc/systemd/system/openvideowall-client-1.service
cp multiscreen-client-2-system.service /etc/systemd/system/openvideowall-client-2.service

# Inject user and home directory into unit files
sed -i "s|__USER__|$TARGET_USER|g" /etc/systemd/system/openvideowall-client-1.service
sed -i "s|__HOME_DIR__|$HOME_DIR|g" /etc/systemd/system/openvideowall-client-1.service
sed -i "s|__USER__|$TARGET_USER|g" /etc/systemd/system/openvideowall-client-2.service
sed -i "s|__HOME_DIR__|$HOME_DIR|g" /etc/systemd/system/openvideowall-client-2.service

echo "✅ Service files installed to /etc/systemd/system/"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

echo "⚙️ Enabling services to start on boot by default..."
systemctl enable openvideowall-client-1
systemctl enable openvideowall-client-2
echo "✅ Enabled: openvideowall-client-1, openvideowall-client-2"

echo ""
echo "🎯 Service Management Commands:"
echo "==============================="
echo ""
echo "Start services:"
echo "  sudo systemctl start openvideowall-client-1"
echo "  sudo systemctl start openvideowall-client-2"
echo ""
echo "Stop services:"
echo "  sudo systemctl stop openvideowall-client-1"
echo "  sudo systemctl stop openvideowall-client-2"
echo ""
echo "Check status:"
echo "  sudo systemctl status openvideowall-client-1"
echo "  sudo systemctl status openvideowall-client-2"
echo ""
echo "View logs:"
echo "  sudo journalctl -u openvideowall-client-1 -f"
echo "  sudo journalctl -u openvideowall-client-2 -f"
echo ""
echo "Enable auto-start (start on boot):"
echo "  sudo systemctl enable openvideowall-client-1"
echo "  sudo systemctl enable openvideowall-client-2"
echo ""
echo "Disable auto-start:"
echo "  sudo systemctl disable openvideowall-client-1"
echo "  sudo systemctl disable openvideowall-client-2"
echo ""

# Ask if user wants to start the services now
read -p "🚀 Do you want to start the services now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting services..."
    systemctl start openvideowall-client-1
    systemctl start openvideowall-client-2
    
    echo "Checking status..."
    systemctl status openvideowall-client-1 --no-pager
    systemctl status openvideowall-client-2 --no-pager
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "💡 Tips:"
echo "   - Services will restart automatically if they crash"
echo "   - Check logs if you have issues: sudo journalctl -u openvideowall-client-1 -f"
echo "   - Enable auto-start if you want them to start on boot"



