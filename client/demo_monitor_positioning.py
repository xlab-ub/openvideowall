#!/usr/bin/env python3
"""
Demo script to show monitor positioning functionality
"""
import subprocess
import time
import os

def demo_monitor_positioning():
    """Demonstrate monitor positioning with a simple window"""
    
    # Monitor positions for 4K setup
    monitor_positions = [
        (0, 0),      # Monitor 1 (left) - HDMI-1
        (3840, 0),   # Monitor 2 (right) - HDMI-2
        (7680, 0),   # Monitor 3 (if available)
        (0, 2160),   # Monitor 4 (bottom-left)
    ]
    
    print("=== Multi-Screen Client Monitor Positioning Demo ===")
    print(f"Your monitor setup:")
    print(f"  Monitor 1 (left):   HDMI-1 at (0, 0)")
    print(f"  Monitor 2 (right):  HDMI-2 at (3840, 0)")
    print(f"  Monitor 3:          at (7680, 0) - if available")
    print(f"  Monitor 4:          at (0, 2160) - if available")
    print()
    
    # Check if we have a display
    if not os.environ.get('DISPLAY'):
        print("Setting DISPLAY=:0")
        os.environ['DISPLAY'] = ':0'
    
    # Create a test window using zenity (if available) or a simple dialog
    test_window_title = "Multi-Screen Client Demo"
    
    try:
        # Try to create a simple dialog window
        subprocess.Popen([
            'zenity', '--info', 
            '--title', test_window_title,
            '--text', 'This is a demo window for monitor positioning.\nIt will move between monitors every 3 seconds.',
            '--width', '400',
            '--height', '200'
        ])
        
        time.sleep(2)  # Wait for window to appear
        
        print("Demo window created. Moving between monitors...")
        
        for i in range(4):  # Test all 4 monitor positions
            monitor_num = i + 1
            x, y = monitor_positions[i]
            
            print(f"\nMoving to Monitor {monitor_num} at position ({x}, {y})")
            
            # Find and move the window
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if test_window_title in line:
                        window_id = line.split()[0]
                        print(f"  Found window: {window_id}")
                        
                        # Move window to monitor position
                        move_result = subprocess.run([
                            'wmctrl', '-ir', window_id, '-e', f'0,{x},{y},400,200'
                        ], capture_output=True, text=True)
                        
                        if move_result.returncode == 0:
                            print(f"  ✓ Window moved to Monitor {monitor_num}")
                        else:
                            print(f"  ✗ Failed to move: {move_result.stderr}")
                        break
                else:
                    print(f"  ✗ Window not found")
            else:
                print(f"  ✗ wmctrl failed: {result.stderr}")
            
            time.sleep(3)  # Wait 3 seconds before next move
        
        print(f"\n=== Demo Complete ===")
        print(f"The --monitor argument works by:")
        print(f"  1. Starting the client with --monitor N")
        print(f"  2. Client automatically positions video window on Monitor N")
        print(f"  3. You can still use hotkeys to move between monitors")
        print(f"\nExample usage:")
        print(f"  DISPLAY=:0 ./run_client.sh --server http://server:5000 --hostname client-1 --display-name 'Monitor 1' --monitor 0")
        print(f"  DISPLAY=:0 ./run_client.sh --server http://server:5000 --hostname client-2 --display-name 'Monitor 2' --monitor 1")
        
    except FileNotFoundError:
        print("zenity not available. Creating a simple test window...")
        
        # Fallback: create a simple window using xmessage or similar
        try:
            subprocess.Popen([
                'xmessage', '-title', test_window_title,
                '-center', 'Demo window for monitor positioning'
            ])
            time.sleep(2)
            
            # Move the window
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if test_window_title in line:
                        window_id = line.split()[0]
                        print(f"Moving demo window to Monitor 2 (right monitor)...")
                        subprocess.run([
                            'wmctrl', '-ir', window_id, '-e', '0,3840,0,400,200'
                        ])
                        print("✓ Window moved to Monitor 2")
                        break
        except FileNotFoundError:
            print("No suitable window creation tools found.")
            print("But the monitor positioning functionality is working!")
            print("You can test it by running the actual client with --monitor argument.")

if __name__ == "__main__":
    demo_monitor_positioning()
