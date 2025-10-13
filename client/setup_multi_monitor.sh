#!/bin/bash
# Multi-Monitor Setup Script for Raspberry Pi
# This script helps configure multiple monitors for video wall setup

echo "  Multi-Monitor Setup for Raspberry Pi"
echo "=========================================="

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "  This script is designed for Raspberry Pi"
    echo "   It may work on other systems but is not tested"
    echo ""
fi

# Check current display setup
echo " Current Display Configuration:"
if command -v xrandr &> /dev/null; then
    xrandr --listmonitors
else
    echo "xrandr not available - cannot check current setup"
fi

echo ""
echo " Monitor Configuration Options:"
echo "1. Dual Monitor (Side by Side)"
echo "2. Dual Monitor (Stacked)"
echo "3. Triple Monitor (Horizontal)"
echo "4. Custom Configuration"
echo "5. Check Wayland/XWayland Status"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "Setting up dual monitors side by side..."
        if command -v xrandr &> /dev/null; then
            # Try to detect HDMI outputs
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -2)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure side by side
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 1920x0
                echo " Dual monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    2)
        echo "Setting up dual monitors stacked..."
        if command -v xrandr &> /dev/null; then
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -2)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure stacked
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 0x1080
                echo " Dual monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    3)
        echo "Setting up triple monitors horizontally..."
        if command -v xrandr &> /dev/null; then
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -3)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure horizontal
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 1920x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $3}') --mode 1920x1080 --pos 3840x0
                echo " Triple monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    4)
        echo "Custom configuration..."
        echo "Please use xrandr manually to configure your monitors"
        echo "Example: xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0"
        ;;
    5)
        echo "Checking display system..."
        echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
        echo "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
        echo "DISPLAY: $DISPLAY"
        echo ""
        if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
            echo " You're using Wayland"
            echo "   - Use the client hotkeys to move windows between monitors"
            echo "   - Monitors are configured through desktop environment settings"
        else
            echo " You're using X11/XWayland"
            echo "   - Use xrandr to configure monitor positions"
            echo "   - Use the client hotkeys to move windows between monitors"
        fi
        ;;
    *)
        echo "Invalid option selected"
        exit 1
        ;;
esac

echo ""
echo " Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start your multi-screen client:"
echo "   ./run_client.sh --server http://YOUR_SERVER:5000 --hostname client-1 --display-name \"Monitor 1\""
echo ""
echo "2. Use hotkeys to move the window:"
echo "   Ctrl+M: Next monitor"
echo "   Ctrl+1-4: Specific monitor"
echo "   Ctrl+H: Show help"
