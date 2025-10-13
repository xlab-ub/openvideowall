#!/usr/bin/env python3
"""
Demo script showing the monitor assignment functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import UnifiedMultiScreenClient

def demo_monitor_assignment():
    """Demonstrate the monitor assignment functionality"""
    
    print("🎯 Multi-Screen Client Monitor Assignment Demo")
    print("=" * 60)
    
    # Test different hostname patterns
    test_cases = [
        ("client-1", "Monitor 1"),
        ("client-2", "Monitor 2"), 
        ("left-monitor", "Left Monitor"),
        ("right-display", "Right Display"),
        ("monitor1", "Monitor 1"),
        ("monitor2", "Monitor 2"),
        ("generic-client", "Generic Client"),
    ]
    
    print("\n📋 Testing Auto-Assignment Logic:")
    print("-" * 40)
    
    for hostname, display_name in test_cases:
        print(f"\n🔍 Testing hostname: '{hostname}'")
        
        # Create a client instance (without actually connecting to server)
        try:
            client = UnifiedMultiScreenClient(
                server_url="http://localhost:5000",  # Dummy URL
                hostname=hostname,
                display_name=display_name,
                force_ffplay=True  # Use ffplay to avoid C++ player dependency
            )
            
            print(f"   ✅ Assigned to Monitor {client.current_monitor + 1}")
            print(f"   📍 Position: {client.monitor_positions[client.current_monitor]}")
            
            # Test monitor availability checking
            available = client._check_monitor_availability(client.current_monitor)
            print(f"   🖥️  Monitor available: {'Yes' if available else 'No'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n🎯 Key Features:")
    print("-" * 20)
    print("✅ Automatic monitor assignment based on hostname patterns")
    print("✅ Prevents multiple clients from using the same monitor")
    print("✅ Fallback to alternative monitors if preferred is busy")
    print("✅ Continuous window positioning monitoring")
    print("✅ Hotkey support for manual monitor switching")
    
    print("\n🚀 Usage Examples:")
    print("-" * 20)
    print("# Auto-assign based on hostname:")
    print("python3 client.py --server http://192.168.1.100:5000 \\")
    print("  --hostname client-1 --display-name \"Monitor 1\"")
    print()
    print("python3 client.py --server http://192.168.1.100:5000 \\")
    print("  --hostname client-2 --display-name \"Monitor 2\"")
    print()
    print("# Manual assignment:")
    print("python3 client.py --server http://192.168.1.100:5000 \\")
    print("  --hostname client-3 --display-name \"Monitor 1\" --monitor 0")
    
    print("\n✨ Demo completed!")

if __name__ == "__main__":
    demo_monitor_assignment()




