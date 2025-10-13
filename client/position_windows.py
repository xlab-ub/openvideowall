#!/usr/bin/env python3
"""
Simple script to position client windows on the correct monitors
Usage: python3 position_windows.py [monitor_number]
"""

import subprocess
import sys
import os

def position_windows(monitor=1):
    """Position all Multi-Screen Client windows on the specified monitor"""
    
    # Monitor positions for 4K setup
    monitor_positions = [
        (0, 0),      # Monitor 1 (left) - HDMI-1
        (3840, 0),   # Monitor 2 (right) - HDMI-2
        (7680, 0),   # Monitor 3 (if available)
        (0, 2160),   # Monitor 4 (bottom-left)
    ]
    
    if monitor < 1 or monitor > 4:
        print(f"❌ Monitor number must be between 1 and 4, got {monitor}")
        return False
    
    x, y = monitor_positions[monitor - 1]
    
    try:
        # Get list of windows
        result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ wmctrl not available. Make sure DISPLAY=:0 is set")
            return False
        
        # Find Multi-Screen Client windows
        client_windows = []
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            if "Multi-Screen Client" in line and "Window Manager" not in line:
                client_windows.append(line)
        
        if not client_windows:
            print("❌ No Multi-Screen Client windows found")
            return False
        
        # Position each window
        for window_line in client_windows:
            window_id = window_line.split()[0]
            window_title = window_line.split(None, 3)[-1]  # Get the title part
            
            # Move window to new position
            move_result = subprocess.run([
                'wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'
            ], capture_output=True, text=True)
            
            if move_result.returncode == 0:
                print(f"✅ Positioned '{window_title}' on Monitor {monitor} (x={x}, y={y})")
            else:
                print(f"❌ Failed to position '{window_title}': {move_result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        try:
            monitor = int(sys.argv[1])
        except ValueError:
            print("❌ Monitor number must be an integer")
            sys.exit(1)
    else:
        monitor = 1  # Default to Monitor 1
    
    print(f"🎯 Positioning Multi-Screen Client windows on Monitor {monitor}...")
    success = position_windows(monitor)
    
    if success:
        print("✅ Window positioning complete!")
    else:
        print("❌ Window positioning failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
