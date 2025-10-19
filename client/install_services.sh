#!/bin/bash
# Multi-Screen Client Systemd Service Installer

echo "🔧 Installing Multi-Screen Client Systemd Services"
echo "=================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user, not as root"
    echo "   The services will run as your user account"
    exit 1
fi

# Get current user and home directory
USER=$(whoami)
HOME_DIR=$(eval echo ~$USER)
SERVICE_DIR="$HOME_DIR/Multiscreen/client"

echo "📋 Service Configuration:"
echo "   User: $USER"
echo "   Home: $HOME_DIR"
echo "   Service Directory: $SERVICE_DIR"
echo ""

# Check if service files exist
if [ ! -f "multiscreen-client-1.service" ] || [ ! -f "multiscreen-client-2.service" ]; then
    echo "❌ Service files not found in current directory"
    echo "   Make sure you're in the client directory with the .service files"
    exit 1
fi

# Check if run_client.sh exists and is executable
if [ ! -f "run_client.sh" ] || [ ! -x "run_client.sh" ]; then
    echo "❌ run_client.sh not found or not executable"
    echo "   Make sure run_client.sh exists and has execute permissions"
    exit 1
fi

echo "📦 Installing services..."

# Copy service files to systemd user directory
mkdir -p ~/.config/systemd/user
cp multiscreen-client-1.service ~/.config/systemd/user/
# cp multiscreen-client-2.service ~/.config/systemd/user/

# Update service files with correct paths
sed -i "s|/home/$USER|$HOME_DIR|g" ~/.config/systemd/user/multiscreen-client-1.service
sed -i "s|$USER|$HOME_DIR|g" ~/.config/systemd/user/multiscreen-client-1.service
# secondary client based on bool
if [ "$SECONDARY_CLIENT" = true ]; then
    sed -i "s|/home/$USER|$HOME_DIR|g" ~/.config/systemd/user/multiscreen-client-2.service
    sed -i "s|$USER|$HOME_DIR|g" ~/.config/systemd/user/multiscreen-client-2.service
fi

echo "✅ Service files installed to ~/.config/systemd/user/"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl --user daemon-reload

echo ""
echo "🎯 Service Management Commands:"
echo "==============================="
echo ""
echo "Start services:"
echo "  systemctl --user start multiscreen-client-1"
echo "  systemctl --user start multiscreen-client-2"
echo ""
echo "Stop services:"
echo "  systemctl --user stop multiscreen-client-1"
echo "  systemctl --user stop multiscreen-client-2"
echo ""
echo "Check status:"
echo "  systemctl --user status multiscreen-client-1"
echo "  systemctl --user status multiscreen-client-2"
echo ""
echo "View logs:"
echo "  journalctl --user -u multiscreen-client-1 -f"
echo "  journalctl --user -u multiscreen-client-2 -f"
echo ""
echo "Enable auto-start (start on boot):"
echo "  systemctl --user enable multiscreen-client-1"
echo "  systemctl --user enable multiscreen-client-2"
echo ""
echo "Disable auto-start:"
echo "  systemctl --user disable multiscreen-client-1"
echo "  systemctl --user disable multiscreen-client-2"
echo ""

# Ask if user wants to start the services now
read -p "🚀 Do you want to start the services now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting services..."
    systemctl --user start multiscreen-client-1
    # systemctl --user start multiscreen-client-2
    
    echo "Checking status..."
    systemctl --user status multiscreen-client-1 --no-pager
    # systemctl --user status multiscreen-client-2 --no-pager
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "💡 Tips:"
echo "   - Services will restart automatically if they crash"
echo "   - Check logs if you have issues: journalctl --user -u multiscreen-client-1 -f"
echo "   - Enable auto-start if you want them to start on boot"



