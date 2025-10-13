#!/bin/bash
# Multi-Screen Client Custom Systemd Service Installer

echo "🔧 Multi-Screen Client Custom Service Installer"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    echo "   Run: sudo ./install_custom_services.sh"
    exit 1
fi

# Get current user and home directory
USER="client3"
HOME_DIR="/home/client3"
SERVICE_DIR="$HOME_DIR/Multiscreen/client"

echo "📋 Service Configuration:"
echo "   User: $USER"
echo "   Home: $HOME_DIR"
echo "   Service Directory: $SERVICE_DIR"
echo ""

# Check if service files exist
if [ ! -f "run_client.sh" ] || [ ! -x "run_client.sh" ]; then
    echo "❌ run_client.sh not found or not executable"
    echo "   Make sure run_client.sh exists and has execute permissions"
    exit 1
fi

# Function to create a service file
create_service() {
    local service_num=$1
    local hostname=$2
    local display_name=$3
    local monitor=$4
    local server_url=$5
    
    local service_file="/etc/systemd/system/multiscreen-client-${service_num}.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Multi-Screen Client ${service_num} (${hostname})
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${SERVICE_DIR}
Environment=DISPLAY=:0
ExecStart=${SERVICE_DIR}/run_client.sh --server ${server_url} --hostname ${hostname} --display-name "${display_name}" --monitor ${monitor} --no-hotkeys
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=${SERVICE_DIR}

[Install]
WantedBy=graphical.target
EOF

    echo "✅ Created service: multiscreen-client-${service_num}.service"
    echo "   Hostname: ${hostname}"
    echo "   Display Name: ${display_name}"
    echo "   Monitor: ${monitor}"
    echo "   Server: ${server_url}"
    echo ""
}

# Interactive setup
echo "🎯 Interactive Service Setup"
echo "============================"
echo ""

# Get server URL
read -p "Enter server URL (default: http://128.205.220.234:5000): " SERVER_URL
SERVER_URL=${SERVER_URL:-"http://128.205.220.234:5000"}

echo ""
echo "📺 Screen Configuration"
echo "======================="
echo ""

# Get number of screens
while true; do
    read -p "How many screens do you want to configure? (1-4): " NUM_SCREENS
    if [[ "$NUM_SCREENS" =~ ^[1-4]$ ]]; then
        break
    else
        echo "❌ Please enter a number between 1 and 4"
    fi
done

echo ""
echo "🖥️  Screen Details"
echo "=================="
echo ""

# Arrays to store screen information
declare -a HOSTNAMES
declare -a DISPLAY_NAMES
declare -a MONITORS

# Get details for each screen
for ((i=1; i<=NUM_SCREENS; i++)); do
    echo "Screen $i Configuration:"
    echo "----------------------"
    
    # Get hostname
    read -p "  Hostname for screen $i (e.g., UB_3S_$i): " HOSTNAME
    HOSTNAME=${HOSTNAME:-"UB_3S_$i"}
    HOSTNAMES[$i]=$HOSTNAME
    
    # Get display name
    read -p "  Display name for screen $i (e.g., \"Monitor $i\"): " DISPLAY_NAME
    DISPLAY_NAME=${DISPLAY_NAME:-"Monitor $i"}
    DISPLAY_NAMES[$i]=$DISPLAY_NAME
    
    # Get monitor number
    while true; do
        read -p "  Monitor number for screen $i (0-3, 0=left, 1=right, 2=far-right, 3=bottom): " MONITOR
        if [[ "$MONITOR" =~ ^[0-3]$ ]]; then
            break
        else
            echo "    ❌ Please enter a number between 0 and 3"
        fi
    done
    MONITORS[$i]=$MONITOR
    
    echo ""
done

# Summary
echo "📋 Configuration Summary"
echo "========================"
echo "Server URL: $SERVER_URL"
echo "Number of screens: $NUM_SCREENS"
echo ""
for ((i=1; i<=NUM_SCREENS; i++)); do
    echo "Screen $i:"
    echo "  Hostname: ${HOSTNAMES[$i]}"
    echo "  Display Name: ${DISPLAY_NAMES[$i]}"
    echo "  Monitor: ${MONITORS[$i]}"
done
echo ""

# Confirm
read -p "Create these services? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Installation cancelled"
    exit 1
fi

echo ""
echo "📦 Creating services..."

# Create services
for ((i=1; i<=NUM_SCREENS; i++)); do
    create_service $i "${HOSTNAMES[$i]}" "${DISPLAY_NAMES[$i]}" "${MONITORS[$i]}" "$SERVER_URL"
done

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

echo ""
echo "🎯 Service Management Commands"
echo "=============================="
echo ""

# Generate management commands
for ((i=1; i<=NUM_SCREENS; i++)); do
    echo "Screen $i (${HOSTNAMES[$i]}):"
    echo "  Start:   sudo systemctl start multiscreen-client-$i"
    echo "  Stop:    sudo systemctl stop multiscreen-client-$i"
    echo "  Status:  sudo systemctl status multiscreen-client-$i"
    echo "  Logs:    sudo journalctl -u multiscreen-client-$i -f"
    echo ""
done

echo "All screens:"
echo "  Start all:   for i in {1..$NUM_SCREENS}; do sudo systemctl start multiscreen-client-\$i; done"
echo "  Stop all:    for i in {1..$NUM_SCREENS}; do sudo systemctl stop multiscreen-client-\$i; done"
echo "  Status all:  for i in {1..$NUM_SCREENS}; do sudo systemctl status multiscreen-client-\$i; done"
echo ""

# Ask if user wants to start the services now
read -p "🚀 Do you want to start all services now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting all services..."
    for ((i=1; i<=NUM_SCREENS; i++)); do
        echo "Starting multiscreen-client-$i..."
        systemctl start multiscreen-client-$i
    done
    
    echo ""
    echo "Checking status..."
    for ((i=1; i<=NUM_SCREENS; i++)); do
        echo "=== multiscreen-client-$i ==="
        systemctl status multiscreen-client-$i --no-pager
        echo ""
    done
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "💡 Tips:"
echo "   - Services will restart automatically if they crash"
echo "   - Check logs if you have issues: sudo journalctl -u multiscreen-client-1 -f"
echo "   - Enable auto-start if you want them to start on boot: sudo systemctl enable multiscreen-client-1"
echo "   - Edit service files in /etc/systemd/system/ to modify configuration"



