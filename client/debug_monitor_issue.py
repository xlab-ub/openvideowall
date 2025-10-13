#!/usr/bin/env python3
"""
Debug script to investigate monitor assignment issues
"""

import subprocess
import sys
import os

def debug_monitor_issue():
    """Debug why multiple clients end up on the same monitor"""
    
    print("🔍 Debugging Monitor Assignment Issue")
    print("=" * 50)
    
    # Check wmctrl output format
    print("\n📋 Current wmctrl output:")
    try:
        result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
        if result.returncode == 0:
            print("wmctrl -l output:")
            for i, line in enumerate(result.stdout.split('\n')):
                if line.strip():
                    print(f"  {i}: {line}")
                    parts = line.split()
                    if len(parts) >= 4:
                        print(f"      Parts: {parts}")
                        print(f"      Window ID: {parts[0]}")
                        print(f"      Desktop: {parts[1]}")
                        print(f"      Position: {parts[2]}x{parts[3]}")
                        print(f"      Title: {' '.join(parts[4:])}")
        else:
            print(f"wmctrl failed with return code: {result.returncode}")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running wmctrl: {e}")
    
    # Check xrandr output
    print("\n📺 xrandr monitor detection:")
    try:
        result = subprocess.run(['/usr/bin/xrandr', '--listmonitors'], capture_output=True, text=True)
        if result.returncode == 0:
            print("xrandr --listmonitors output:")
            print(result.stdout)
        else:
            print(f"xrandr failed with return code: {result.returncode}")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running xrandr: {e}")
    
    # Test monitor position checking
    print("\n🎯 Testing monitor position checking:")
    monitor_positions = [
        (0, 0),      # Monitor 1 (left)
        (3840, 0),   # Monitor 2 (right)
        (7680, 0),   # Monitor 3 (far-right)
        (0, 2160),   # Monitor 4 (bottom-left)
    ]
    
    for i, (x, y) in enumerate(monitor_positions):
        print(f"\nMonitor {i + 1} position: ({x}, {y})")
        
        # Check if any windows are near this position
        try:
            result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
            if result.returncode == 0:
                windows_on_monitor = []
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    if "Multi-Screen Client" in line and "Window Manager" not in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                window_x = int(parts[2])
                                window_y = int(parts[3])
                                distance = ((window_x - x) ** 2 + (window_y - y) ** 2) ** 0.5
                                if distance < 100:
                                    windows_on_monitor.append({
                                        'line': line,
                                        'x': window_x,
                                        'y': window_y,
                                        'distance': distance
                                    })
                            except (ValueError, IndexError):
                                continue
                
                if windows_on_monitor:
                    print(f"  Found {len(windows_on_monitor)} windows on this monitor:")
                    for win in windows_on_monitor:
                        print(f"    {win['line']}")
                        print(f"    Position: ({win['x']}, {win['y']}), Distance: {win['distance']:.1f}")
                else:
                    print(f"  No windows found on this monitor")
            else:
                print(f"  wmctrl failed")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test window positioning
    print("\n🪟 Testing window positioning:")
    try:
        # Find a test window
        result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
        if result.returncode == 0:
            test_windows = []
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                if "Multi-Screen Client" in line and "Window Manager" not in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        test_windows.append(parts[0])
                        break
            
            if test_windows:
                window_id = test_windows[0]
                print(f"Testing with window ID: {window_id}")
                
                # Try to move to Monitor 2
                x, y = monitor_positions[1]  # Monitor 2
                print(f"Moving to Monitor 2 position: ({x}, {y})")
                
                move_result = subprocess.run([
                    'wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'
                ], capture_output=True, text=True)
                
                if move_result.returncode == 0:
                    print("✅ Window moved successfully")
                    
                    # Check new position
                    time.sleep(1)
                    result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if window_id in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    new_x = int(parts[2])
                                    new_y = int(parts[3])
                                    print(f"New position: ({new_x}, {new_y})")
                                    distance = ((new_x - x) ** 2 + (new_y - y) ** 2) ** 0.5
                                    print(f"Distance from target: {distance:.1f}")
                                break
                else:
                    print(f"❌ Failed to move window: {move_result.stderr}")
            else:
                print("No test windows found")
        else:
            print("Could not list windows")
    except Exception as e:
        print(f"Error testing window positioning: {e}")

if __name__ == "__main__":
    debug_monitor_issue()
