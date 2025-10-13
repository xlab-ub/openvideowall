#!/usr/bin/env python3
"""
Quick test to verify the simplified window positioning
"""

import subprocess
import time
import sys
import os

def quick_test():
    """Quick test of window positioning"""
    
    print("🧪 Quick Window Positioning Test")
    print("=" * 40)
    
    # Check current windows
    print("\n📋 Current Multi-Screen Client windows:")
    result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
    if result.returncode == 0:
        found_windows = []
        for line in result.stdout.split('\n'):
            if line.strip() and "Multi-Screen Client" in line and "Window Manager" not in line:
                parts = line.split()
                if len(parts) >= 6:
                    found_windows.append({
                        'id': parts[0],
                        'x': int(parts[2]),
                        'y': int(parts[3]),
                        'title': ' '.join(parts[7:])
                    })
        
        if found_windows:
            for i, win in enumerate(found_windows):
                monitor = "Monitor 1" if win['x'] < 2000 else "Monitor 2"
                print(f"   Window {i+1}: {win['title']} at ({win['x']}, {win['y']}) - {monitor}")
        else:
            print("   No Multi-Screen Client windows found")
    else:
        print(f"   ❌ Could not list windows: {result.stderr}")
        return
    
    if not found_windows:
        print("\n❌ No windows to test with. Start a client first.")
        return
    
    # Test moving a window
    window = found_windows[0]
    print(f"\n🎯 Testing with window: {window['title']}")
    print(f"   Current position: ({window['x']}, {window['y']})")
    
    # Try to move to Monitor 1 (0, 0)
    target_x, target_y = 0, 0
    print(f"   Moving to Monitor 1: ({target_x}, {target_y})")
    
    move_result = subprocess.run([
        'wmctrl', '-ir', window['id'], '-e', f'0,{target_x},{target_y},-1,-1'
    ], capture_output=True, text=True)
    
    print(f"   wmctrl result: return_code={move_result.returncode}")
    if move_result.stderr:
        print(f"   stderr: {move_result.stderr}")
    
    if move_result.returncode == 0:
        print("   ✅ Move command succeeded")
        
        # Check new position
        time.sleep(1)
        verify_result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
        if verify_result.returncode == 0:
            for line in verify_result.stdout.split('\n'):
                if window['id'] in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        new_x = int(parts[2])
                        new_y = int(parts[3])
                        print(f"   New position: ({new_x}, {new_y})")
                        
                        if abs(new_x - target_x) < 100 and abs(new_y - target_y) < 100:
                            print("   ✅ SUCCESS: Window positioned correctly!")
                        else:
                            print(f"   ❌ FAILED: Expected ({target_x}, {target_y}), got ({new_x}, {new_y})")
                    break
    else:
        print("   ❌ Move command failed")
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    quick_test()




