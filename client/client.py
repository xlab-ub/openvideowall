#!/usr/bin/env python3
"""
Unified Multi-Screen Client for Video Wall Systems
Simple, reliable client for multi-screen video streaming
"""
import argparse
import requests
import time
import logging
import subprocess
import sys
import os
import json
import signal
import atexit
import threading
import socket
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


class UnifiedMultiScreenClient:
    """
    Unified Multi-Screen Client for Video Wall Systems
    Simple and reliable client for multi-screen video streaming
    """
    
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None, 
                 force_ffplay: bool = False, initial_monitor: int = None, enable_hotkeys: bool = False):
        """
        Initialize the multi-screen client
        
        Args:
            server_url: Server URL (e.g., "http://192.168.1.100:5000")
            hostname: Unique client identifier
            display_name: Friendly display name
            force_ffplay: Force use of ffplay instead of smart selection
            initial_monitor: Monitor index to start on (0-based, None for auto-assignment)
            enable_hotkeys: Enable hotkey window manager (default: False)
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or socket.gethostname()
        self.display_name = display_name or f"Display-{self.hostname}"
        self.force_ffplay = force_ffplay
        self.enable_hotkeys = enable_hotkeys
        
        # Window management
        self.window_manager = None
        self.monitor_positions = [
            (0, 0),      # Monitor 1 (left) - HDMI-2
            (3840, 0),   # Monitor 2 (right) - HDMI-1
            (7680, 0),   # Monitor 3 (if available)
            (0, 2160),   # Monitor 4 (bottom-left)
        ]
        
        # Fallback monitoring
        self.last_correct_position_time = time.time()
        self.position_check_interval = 60  # Check every 60 seconds
        self.max_wrong_position_time = 120  # Reposition if wrong for 120 seconds
        self.fallback_monitor_thread = None
        self.last_fullscreen_attempt = 0
        self.fullscreen_cooldown = 30  # Don't try fullscreen more than once every 30 seconds
        
        # Configure logging first
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
        # Auto-assign monitor if not specified
        if initial_monitor is None:
            self.current_monitor = self._auto_assign_monitor()
        else:
            self.current_monitor = initial_monitor
        
        # Stream management
        self.current_stream_url = None
        self.current_stream_version = None
        self.current_player_type = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5
        self.max_retries = 60
        self._shutdown_event = threading.Event()
        
        # Client state
        self.registered = False
        self.assignment_status = "waiting_for_assignment"
        
        # Server-assigned client ID (set after registration)
        self._server_client_id = None
        
        # Extract server IP for stream URL fixing
        parsed_url = urlparse(self.server_url)
        self.server_ip = parsed_url.hostname or "127.0.0.1"
        
        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        atexit.register(self._emergency_cleanup)
        
        # Find player executable
        self.player_executable = self._find_player_executable()
    
    @property
    def client_id(self) -> str:
        """Generate unique client ID using hostname and IP address"""
        # Use server-assigned client ID if available, otherwise generate one
        if self._server_client_id:
            return self._server_client_id
        
        try:
            local_ip = self._get_local_ip_address()
            return f"{self.hostname}_{local_ip}"
        except Exception:
            # Fallback to hostname if IP detection fails
            return self.hostname
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _find_player_executable(self) -> Optional[str]:
        """Find the C++ player executable"""
        if self.force_ffplay:
            self.logger.info("Forcing ffplay usage (--force-ffplay specified)")
            return None
        
        search_paths = [
            Path(__file__).parent / "multi-screen" / "cmake-build-debug" / "player" / "player",
            Path(__file__).parent / "cmake-build-debug" / "player" / "player", 
            Path(__file__).parent / "build" / "player" / "player",
            Path(__file__).parent / "player" / "player",
            Path("./multi-screen/cmake-build-debug/player/player"),
            Path("./cmake-build-debug/player/player"),
            Path("./build/player/player"),
            Path("./player/player")
        ]
        
        for player_path in search_paths:
            if player_path.exists() and os.access(player_path, os.X_OK):
                self.logger.info(f"Found C++ player: {player_path}")
                return str(player_path.absolute())
        
        self.logger.warning("C++ player not found, will use ffplay fallback")
        return None
    
    def _get_local_ip_address(self) -> str:
        """Get the local IP address for unique client identification"""
        try:
            # Try to get the IP address that would be used to connect to the server
            # This helps distinguish between multiple terminal instances on the same machine
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.server_ip, 80))  # Connect to server IP
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            self.logger.warning(f"Could not determine local IP address: {e}")
            # Fallback: try to get any non-loopback IP
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip.startswith('127.'):
                    # If it's loopback, try alternative method
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))  # Connect to external IP
                    local_ip = s.getsockname()[0]
                    s.close()
                return local_ip
            except Exception:
                # Final fallback: use loopback IP
                return "127.0.0.1"
    
    def _detect_available_monitors(self) -> list:
        """Detect which monitors are actually available"""
        available_monitors = []
        
        try:
            # Use xrandr to detect available monitors
            result = subprocess.run(['/usr/bin/xrandr', '--listmonitors'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if 'HDMI' in line or 'DP' in line or 'eDP' in line:
                        # Extract monitor info - look for position info
                        parts = line.split()
                        for part in parts:
                            if '/' in part and 'x' in part:
                                # Found resolution info, this monitor is active
                                monitor_index = len(available_monitors)
                                if monitor_index < len(self.monitor_positions):
                                    available_monitors.append(monitor_index)
                                break
        except Exception as e:
            self.logger.warning(f"Could not detect monitors with xrandr: {e}")
        
        # Fallback: assume monitors 0 and 1 are available if detection fails
        if not available_monitors:
            available_monitors = [0, 1]
            self.logger.info("Monitor detection failed, assuming monitors 0 and 1 are available")
        
        return available_monitors
    
    def _check_monitor_availability(self, monitor_index: int) -> bool:
        """Check if a specific monitor is available and not in use by another client"""
        try:
            # Check if monitor is in available monitors list
            available_monitors = self._detect_available_monitors()
            if monitor_index not in available_monitors:
                self.logger.info(f"Monitor {monitor_index + 1} not in available monitors list")
                return False
            
            # Check if another client is already using this monitor
            result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
            if result.returncode == 0:
                x, y = self.monitor_positions[monitor_index]
                
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    # Only check windows from OTHER clients (not this one)
                    if "Multi-Screen Client" in line and "Window Manager" not in line and self.display_name not in line:
                        # Extract window position from wmctrl -lG output
                        # Format: WindowID Desktop X Y Width Height Hostname Title
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                window_x = int(parts[2])
                                window_y = int(parts[3])
                                # Check if window is positioned on this monitor
                                if abs(window_x - x) < 200 and abs(window_y - y) < 200:
                                    self.logger.info(f"Monitor {monitor_index + 1} is already in use by another client at ({window_x}, {window_y})")
                                    return False
                            except (ValueError, IndexError):
                                continue
            
            self.logger.info(f"Monitor {monitor_index + 1} is available")
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not check monitor availability: {e}")
            return True  # Assume available if check fails
    
    def _auto_assign_monitor(self) -> int:
        """Automatically assign a monitor based on hostname and availability"""
        # Try to assign monitor based on hostname pattern
        hostname_lower = self.hostname.lower()
        
        # Check for common patterns in hostname
        if '1' in hostname_lower or 'left' in hostname_lower or 'monitor1' in hostname_lower:
            preferred_monitor = 0  # Monitor 1
        elif '2' in hostname_lower or 'right' in hostname_lower or 'monitor2' in hostname_lower:
            preferred_monitor = 1  # Monitor 2
        else:
            # Default to monitor 1 if no pattern matches
            preferred_monitor = 0
        
        # Check if preferred monitor is available
        if self._check_monitor_availability(preferred_monitor):
            self.logger.info(f"Auto-assigned to Monitor {preferred_monitor + 1} based on hostname pattern")
            return preferred_monitor
        
        # Try the other monitor (1 or 2)
        alternative_monitor = 1 if preferred_monitor == 0 else 0
        if self._check_monitor_availability(alternative_monitor):
            self.logger.info(f"Preferred monitor {preferred_monitor + 1} in use, assigned to Monitor {alternative_monitor + 1}")
            return alternative_monitor
        
        # If both monitors 1 and 2 are busy, try monitor 3
        if self._check_monitor_availability(2):
            self.logger.warning(f"Monitors 1 and 2 are busy, assigned to Monitor 3")
            return 2
        
        # Last resort: use monitor 1 anyway (will overlap but at least works)
        self.logger.warning(f"All monitors appear busy, using Monitor 1 (may overlap)")
        return 0
    
    def create_window_manager(self):
        """Create a hidden window manager for hotkey handling"""
        try:
            self.window_manager = tk.Tk()
            self.window_manager.withdraw()  # Hide the window
            self.window_manager.title("Multi-Screen Client Window Manager")
            
            # Bind hotkeys
            self.window_manager.bind('<Control-m>', self.move_to_next_monitor)
            self.window_manager.bind('<Control-Left>', self.move_to_previous_monitor)
            self.window_manager.bind('<Control-Right>', self.move_to_next_monitor)
            self.window_manager.bind('<Control-1>', lambda e: self.move_to_monitor(0))
            self.window_manager.bind('<Control-2>', lambda e: self.move_to_monitor(1))
            self.window_manager.bind('<Control-3>', lambda e: self.move_to_monitor(2))
            self.window_manager.bind('<Control-4>', lambda e: self.move_to_monitor(3))
            self.window_manager.bind('<Control-h>', self.show_help)
            
            # Keep window hidden and not focusable
            self.window_manager.attributes('-topmost', False)
            # Don't force focus to keep it hidden
            
            print(f"Window Manager Started")
            print(f"   Hotkeys:")
            print(f"     Ctrl+M or Ctrl+Right: Move to next monitor")
            print(f"     Ctrl+Left: Move to previous monitor")
            print(f"     Ctrl+1-4: Move to specific monitor")
            print(f"     Ctrl+H: Show help")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to create window manager: {e}")
            return False
    
    def move_to_monitor(self, monitor_index: int):
        """Move the fullscreen window to a specific monitor"""
        if not self.player_process or self.player_process.poll() is not None:
            return
        
        if monitor_index >= len(self.monitor_positions):
            print(f"Monitor {monitor_index + 1} not available")
            return
        
        x, y = self.monitor_positions[monitor_index]
        self.current_monitor = monitor_index
        
        try:
            # First, try to move windows by current player PID (most reliable)
            pid_windows = self._find_player_window_ids()
            if pid_windows:
                for wid in pid_windows:
                    # Move to position
                    subprocess.run(['wmctrl', '-ir', wid, '-e', f'0,{x},{y},-1,-1'])
                    # Simple fullscreen enforcement
                    subprocess.run(['wmctrl', '-ir', wid, '-b', 'add,fullscreen'], capture_output=True)
                print(f"Moved player window(s) to Monitor {monitor_index + 1} (x={x}, y={y}) and set fullscreen")
                return
            
            # Use wmctrl to move the window (works with Wayland/XWayland)
            window_title = f"Multi-Screen Client - {self.display_name}"
            
            # Find the window by title, prioritizing video windows
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                # Look for windows, prioritizing video windows over manager windows
                video_windows = []
                manager_windows = []
                
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                        
                    # Skip the Window Manager window
                    if "Window Manager" in line:
                        manager_windows.append(line)
                        continue
                        
                    # Check if this matches our window title
                    if window_title in line:
                        video_windows.append(line)
                
                # Try to move video windows first
                for line in video_windows:
                    window_id = line.split()[0]
                    # Move to position
                    subprocess.run(['wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'])
                    # Simple fullscreen enforcement
                    subprocess.run(['wmctrl', '-ir', window_id, '-b', 'add,fullscreen'], capture_output=True)
                    print(f"Moved video window to Monitor {monitor_index + 1} (x={x}, y={y}) and set fullscreen")
                    return
                
                # If no video windows found, try manager windows as fallback
                if not video_windows and manager_windows:
                    for line in manager_windows:
                        window_id = line.split()[0]
                        subprocess.run(['wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'])
                        subprocess.run(['wmctrl', '-ir', window_id, '-b', 'add,fullscreen'])
                        subprocess.run(['xdotool', 'windowactivate', '--sync', window_id, 'key', 'f'], capture_output=True)
                        print(f"Moved manager window to Monitor {monitor_index + 1} (x={x}, y={y}) and forced fullscreen")
                        return
            
            # Fallback: try xdotool if wmctrl doesn't work
            subprocess.run(['xdotool', 'search', '--name', window_title, 'windowmove', str(x), str(y)])
            print(f"Moved to Monitor {monitor_index + 1} (x={x}, y={y})")
            
        except FileNotFoundError:
            print(f"Window management tools not found. Install with:")
            print(f"   sudo apt install wmctrl xdotool")
        except Exception as e:
            self.logger.error(f"Failed to move window: {e}")
    
    def move_to_next_monitor(self, event=None):
        """Move to the next monitor"""
        next_monitor = (self.current_monitor + 1) % len(self.monitor_positions)
        self.move_to_monitor(next_monitor)
    
    def move_to_previous_monitor(self, event=None):
        """Move to the previous monitor"""
        prev_monitor = (self.current_monitor - 1) % len(self.monitor_positions)
        self.move_to_monitor(prev_monitor)
    
    def _position_window_on_monitor(self):
        """Position the video window on the correct monitor after it starts"""
        if not self.player_process or self.player_process.poll() is not None:
            print(f"   Skipping window positioning - player not running")
            return
        
        try:
            x, y = self.monitor_positions[self.current_monitor]
            print(f"   🎯 Checking window position on Monitor {self.current_monitor + 1} (x={x}, y={y})")
            
            # First check if window is already positioned correctly
            pid_windows = self._find_player_window_ids()
            if pid_windows:
                for wid in pid_windows:
                    result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if wid in line:
                                parts = line.split()
                                if len(parts) >= 6:
                                    current_x, current_y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                                    # Check if already positioned correctly and fullscreen
                                    positioned_ok = abs(current_x - x) < 100 and abs(current_y - y) < 100
                                    fullscreen_ok = w >= 1900 and h >= 1000
                                    
                                    if positioned_ok and fullscreen_ok:
                                        print(f"   ✅ Window already correctly positioned and fullscreen")
                                        return
                                    elif positioned_ok and not fullscreen_ok:
                                        print(f"   🔧 Window positioned correctly but not fullscreen, fixing...")
                                        subprocess.run(['xdotool', 'windowactivate', '--sync', wid, 'key', 'f'], capture_output=True)
                                        return
                                    else:
                                        print(f"   🔧 Window needs positioning: current=({current_x},{current_y}) target=({x},{y})")
                                        break
            
            # If we get here, window needs positioning
            for attempt in range(5):
                time.sleep(2)
                
                print(f"   🔄 Attempt {attempt + 1}/5: Looking for windows...")
                
                # Get list of windows
                result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"   ❌ Could not list windows: {result.stderr}")
                    continue
                
                # Find THIS client's windows only (by display name)
                windows_found = []
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    # Only match windows that contain this client's display name
                    if "Multi-Screen Client" in line and "Window Manager" not in line and self.display_name in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            windows_found.append({
                                'id': parts[0],
                                'x': int(parts[2]),
                                'y': int(parts[3]),
                                'line': line
                            })
                
                if not windows_found:
                    print(f"   No Multi-Screen Client windows found yet...")
                    continue
                
                # Try to move each window
                for window in windows_found:
                    print(f"   Found window: {window['line']}")
                    print(f"   Current position: ({window['x']}, {window['y']})")
                    
                    # Check if already in correct position
                    if abs(window['x'] - x) < 100 and abs(window['y'] - y) < 100:
                        print(f"   ✅ Window already in correct position!")
                        # Force fullscreen mode using safe method
                        self._safe_force_fullscreen("already positioned")
                        return
                    
                    # Move window
                    print(f"   Moving window {window['id']} to ({x}, {y})")
                    move_result = subprocess.run([
                        'wmctrl', '-ir', window['id'], '-e', f'0,{x},{y},-1,-1'
                    ], capture_output=True, text=True)
                    
                    if move_result.returncode == 0:
                        print(f"   ✅ Window moved successfully!")
                        
                        # Verify position
                        time.sleep(1)
                        verify_result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
                        if verify_result.returncode == 0:
                            for verify_line in verify_result.stdout.split('\n'):
                                if window['id'] in verify_line:
                                    verify_parts = verify_line.split()
                                    if len(verify_parts) >= 6:
                                        verify_x = int(verify_parts[2])
                                        verify_y = int(verify_parts[3])
                                        print(f"   New position: ({verify_x}, {verify_y})")
                                        if abs(verify_x - x) < 100 and abs(verify_y - y) < 100:
                                            print(f"   ✅ Successfully positioned on Monitor {self.current_monitor + 1}!")
                                            # Force fullscreen mode using safe method
                                            self._safe_force_fullscreen("successfully positioned")
                                            return
                                        else:
                                            print(f"   ⚠️  Position not correct: expected ({x}, {y}), got ({verify_x}, {verify_y})")
                        return
                    else:
                        print(f"   ❌ Failed to move window: {move_result.stderr}")
            
            print(f"   ❌ Could not position window after 10 attempts")
            
        except Exception as e:
            self.logger.error(f"Failed to position window: {e}")
    
    def _start_window_positioning_monitor(self):
        """Start a background thread to continuously monitor and reposition windows"""
        def positioning_monitor():
            # Wait 10 seconds before starting continuous monitoring
            # This gives the initial positioning attempts time to work
            if self._shutdown_event.wait(timeout=10):
                return
                
            while self.running and not self._shutdown_event.is_set():
                try:
                    # Check every 15 seconds if window is still on correct monitor
                    if self._shutdown_event.wait(timeout=15):
                        break
                    
                    if self.player_process and self.player_process.poll() is None:
                        self._ensure_window_position()
                        
                except Exception as e:
                    self.logger.debug(f"Window positioning monitor error: {e}")
        
        positioning_thread = threading.Thread(target=positioning_monitor, daemon=True)
        positioning_thread.start()
    
    def _ensure_window_position(self):
        """Ensure the window is still positioned on the correct monitor"""
        try:
            x, y = self.monitor_positions[self.current_monitor]
            window_title = f"Multi-Screen Client - {self.display_name}"
            
            # Check if THIS client's window is on correct monitor
            result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    # Only check THIS client's windows
                    if "Multi-Screen Client" in line and "Window Manager" not in line and self.display_name in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                window_x = int(parts[2])
                                window_y = int(parts[3])
                                # Check if window is positioned on correct monitor
                                # Use a larger tolerance to avoid constant repositioning
                                if abs(window_x - x) > 200 or abs(window_y - y) > 200:
                                    # Window is not on correct monitor, reposition it
                                    window_id = parts[0]
                                    print(f"   🔄 Repositioning window from ({window_x}, {window_y}) to ({x}, {y})")
                                    move_result = subprocess.run([
                                        'wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'
                                    ], capture_output=True, text=True)
                                    
                                    if move_result.returncode == 0:
                                        self.logger.info(f"Repositioned window to Monitor {self.current_monitor + 1}")
                                    else:
                                        self.logger.debug(f"Failed to reposition window: {move_result.stderr}")
                                    break
                                else:
                                    # Window is in correct position, no need to move
                                    self.logger.debug(f"Window already positioned correctly at ({window_x}, {window_y})")
                                    # Ensure fullscreen mode is active using safe method
                                    self._safe_force_fullscreen("continuous monitoring")
                            except (ValueError, IndexError):
                                continue
                                
        except Exception as e:
            self.logger.debug(f"Window position check failed: {e}")
    
    def _start_fallback_monitor(self):
        """Start the fallback monitoring thread"""
        if self.fallback_monitor_thread and self.fallback_monitor_thread.is_alive():
            return
            
        def fallback_monitor():
            """Continuously monitor window position and reposition if needed"""
            while self.running and not self._shutdown_event.is_set():
                try:
                    time.sleep(self.position_check_interval)
                    
                    if not self.player_process or self.player_process.poll() is not None:
                        continue
                    
                    # Check if window is in correct position
                    if self._is_window_in_correct_position():
                        self.last_correct_position_time = time.time()
                        self.logger.debug("Window position check: ✅ Correct position")
                    else:
                        wrong_position_time = time.time() - self.last_correct_position_time
                        self.logger.warning(f"Window position check: ❌ Wrong position for {wrong_position_time:.1f}s")
                        
                        if wrong_position_time >= self.max_wrong_position_time:
                            self.logger.warning(f"🔄 FALLBACK: Repositioning window after {wrong_position_time:.1f}s in wrong position")
                            self._emergency_reposition()
                            self.last_correct_position_time = time.time()
                            
                except Exception as e:
                    self.logger.error(f"Fallback monitor error: {e}")
                    time.sleep(10)  # Wait longer on error
        
        self.fallback_monitor_thread = threading.Thread(target=fallback_monitor, daemon=True)
        self.fallback_monitor_thread.start()
        self.logger.info("Fallback monitor started (checks every 60s, repositions after 120s)")
    
    def _is_window_in_correct_position(self):
        """Check if the window is in the correct position"""
        try:
            x, y = self.monitor_positions[self.current_monitor]
            
            # Get list of windows
            result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True, env={'DISPLAY': ':0'})
            if result.returncode != 0:
                return False
            
            # Find this client's window
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                if "Multi-Screen Client" in line and "Window Manager" not in line and self.display_name in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        window_x = int(parts[2])
                        window_y = int(parts[3])
                        
                        # Check if position is correct (with tolerance)
                        if abs(window_x - x) <= 200 and abs(window_y - y) <= 200:
                            return True
            return False
            
        except Exception as e:
            self.logger.debug(f"Position check failed: {e}")
            return False
    
    def _safe_force_fullscreen(self, reason="positioning"):
        """Safely force fullscreen with cooldown to prevent interference"""
        current_time = time.time()
        if current_time - self.last_fullscreen_attempt < self.fullscreen_cooldown:
            self.logger.debug(f"Skipping fullscreen attempt (cooldown): {reason}")
            return False
            
        try:
            # Method 1: Try wmctrl fullscreen
            result1 = subprocess.run(['wmctrl', '-r', f'Multi-Screen Client - {self.display_name}', '-b', 'add,fullscreen'], 
                                   check=False, capture_output=True, env={'DISPLAY': ':0'})
            
            # Method 2: Try xdotool to send ffplay's fullscreen toggle ('f')
            result2 = subprocess.run(['xdotool', 'search', '--name', f'Multi-Screen Client - {self.display_name}', 'windowactivate', '--sync', 'key', 'f'], 
                                   check=False, capture_output=True, env={'DISPLAY': ':0'})
            
            # Method 3: Try to maximize and then fullscreen
            subprocess.run(['wmctrl', '-r', f'Multi-Screen Client - {self.display_name}', '-b', 'add,maximized_vert,maximized_horz'], 
                         check=False, capture_output=True, env={'DISPLAY': ':0'})
            
            self.last_fullscreen_attempt = current_time
            self.logger.info(f"✅ Forced fullscreen mode (multiple methods) - {reason}")
            return True
        except Exception as e:
            self.logger.warning(f"⚠️  Could not force fullscreen ({reason}): {e}")
            return False

    def _emergency_reposition(self):
        """Emergency repositioning when window is in wrong position for too long"""
        try:
            self.logger.warning("🚨 EMERGENCY REPOSITION: Forcing window to correct monitor")
            
            # Force reposition using the existing method
            self._position_window_on_monitor()
            
            # Also try to force fullscreen using safe method
            self._safe_force_fullscreen("emergency reposition")
                
        except Exception as e:
            self.logger.error(f"Emergency reposition failed: {e}")
    
    def show_help(self, event=None):
        """Show hotkey help"""
        help_text = """
Multi-Screen Client Hotkeys:

Ctrl+M or Ctrl+Right: Move to next monitor
Ctrl+Left: Move to previous monitor
Ctrl+1: Move to Monitor 1 (left)
Ctrl+2: Move to Monitor 2 (right)
Ctrl+3: Move to Monitor 3 (if available)
Ctrl+4: Move to Monitor 4 (bottom-left)
Ctrl+H: Show this help

Note: Make sure the client window has focus for hotkeys to work.
        """
        messagebox.showinfo("Multi-Screen Client Help", help_text)
    

    
    def detect_sei_in_stream(self, stream_url: str, timeout: int = 10) -> bool:
        """
        Detect if the stream contains SEI metadata by analyzing the first few seconds
        """
        try:
            print(f" Analyzing stream for SEI metadata...")
            print(f"   Stream URL: {stream_url}")
            
            # Use ffprobe to analyze the stream for a short duration
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "frame=pkt_data",
                "-of", "csv=p=0",
                "-read_intervals", f"%+#10",  # Read first 10 frames
                "-timeout", str(timeout * 1000000),  # Convert to microseconds
                stream_url
            ]
            
            self.logger.debug(f"SEI detection command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                # Check if we got any frame data
                if stdout and len(stdout.strip()) > 0:
                    # Look for patterns that might indicate SEI data
                    sei_patterns = [
                        "681d5c8f-80cd-4847-930a-99b9484b4a32",  # OpenVideoWalls UUID
                        "00000000000000000000000000000000",      # Static SEI pattern
                    ]
                    
                    for pattern in sei_patterns:
                        if pattern.lower() in stdout.lower():
                            print(f" SEI metadata detected (pattern: {pattern[:16]}...)")
                            return True
                    
                    # Alternative: Check stderr for SEI-related messages
                    if stderr:
                        sei_indicators = ["sei", "user_data", "h264_metadata"]
                        for indicator in sei_indicators:
                            if indicator.lower() in stderr.lower():
                                print(f" SEI indicators found in stream analysis")
                                return True
                    
                    print(f" No SEI metadata detected - standard stream")
                    return False
                else:
                    print(f"  Could not analyze stream data")
                    return False
                    
            except subprocess.TimeoutExpired:
                print(f"  Stream analysis timeout - assuming no SEI")
                process.kill()
                return False
                
        except FileNotFoundError:
            self.logger.warning("ffprobe not found - cannot detect SEI, assuming no SEI")
            return False
        except Exception as e:
            self.logger.warning(f"SEI detection failed: {e} - assuming no SEI")
            return False
    
    def choose_optimal_player(self, stream_url: str) -> Tuple[str, str]:
        """Choose the optimal player based on stream characteristics"""
        # If forced to use ffplay, don't bother detecting
        if self.force_ffplay:
            return "ffplay", "Forced ffplay mode (--force-ffplay)"
        
        # If C++ player not available, use ffplay
        if not self.player_executable or not os.path.exists(self.player_executable):
            return "ffplay", "C++ player not available"
        
        # Detect SEI metadata in the stream
        has_sei = self.detect_sei_in_stream(stream_url)
        
        if has_sei:
            return "cpp_player", "SEI metadata detected - using C++ player for synchronization"
        else:
            return "ffplay", "No SEI metadata - using ffplay for standard playback"
    
    def register(self) -> bool:
        """Register client with server"""
        try:
            print(f"\n{'='*80}")
            print(f" STARTING MULTI-SCREEN CLIENT REGISTRATION")
            print(f"   Client: {self.hostname}")
            print(f"   Local IP: {self._get_local_ip_address()}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Server IP: {self.server_ip}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            
            registration_start = time.time()
            registration_start_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(registration_start))[:-3]
            print(f"   Start Time: {registration_start_formatted} UTC")
            print(f"{'='*80}")
            
            # Create platform string indicating player capability
            if self.force_ffplay:
                player_type = "ffplay_only"
            elif not self.player_executable:
                player_type = "ffplay_fb"  # fallback
            else:
                player_type = "smart_sel"  # smart selection
            
            # Get local IP address for unique client identification
            local_ip = self._get_local_ip_address()
            
            registration_data = {
                "hostname": self.hostname,
                "ip_address": local_ip,  # Include IP address for unique client ID
                "display_name": self.display_name,
                "platform": f"multiscreen_{player_type}"  # Indicate multi-screen capability
            }
            
            print(f"\n Sending registration request...")
            request_sent_time = time.time()
            
            # Try new registration endpoint first, fallback to legacy
            try:
                print(f" Trying new endpoint: {self.server_url}/api/clients/register")
                print(f" Registration data: {json.dumps(registration_data, indent=2)}")
                response = requests.post(
                    f"{self.server_url}/api/clients/register",
                    json=registration_data,
                    timeout=10
                )
                endpoint_used = "new (/api/clients/register)"
                print(f" New endpoint succeeded with status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                # Fallback to legacy endpoint (simplified data)
                print(f" New endpoint failed with RequestException: {e}")
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                legacy_data = {
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"multiscreen_{player_type}"
                }
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=legacy_data,
                    timeout=10
                )
                endpoint_used = "legacy (/register_client)"
            except Exception as e:
                # Catch any other exceptions
                print(f" New endpoint failed with unexpected error: {e}")
                print(f" Error type: {type(e).__name__}")
                import traceback
                print(f" Traceback: {traceback.format_exc()}")
                # Fallback to legacy endpoint (simplified data)
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                legacy_data = {
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"multiscreen_{player_type}"
                }
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=legacy_data,
                    timeout=10
                )
                endpoint_used = "legacy (/register_client)"
            
            response_received_time = time.time()
            network_delay_ms = (response_received_time - request_sent_time) * 1000
            
            print(f" Response received in {network_delay_ms:.1f}ms using {endpoint_used}")
            
            if response.status_code in [200, 202]:
                result = response.json()
                if result.get("success", True):  # Legacy endpoint doesn't have 'success' field
                    registration_end = time.time()
                    total_time_ms = (registration_end - registration_start) * 1000
                    
                    print(f"\n REGISTRATION SUCCESSFUL!")
                    print(f"   Client ID: {result.get('client_id', self.client_id)}")
                    print(f"   Status: {result.get('status', 'registered')}")
                    if 'server_time' in result:
                        print(f"   Server Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result['server_time']))}")
                    print(f"   Total Registration Time: {total_time_ms:.1f}ms")
                    
                    self.registered = True
                    self.assignment_status = result.get('status', 'waiting_for_assignment')
                    self._server_client_id = result.get('client_id') # Store server-assigned ID
                    
                    # Initialize heartbeat tracking
                    self.last_heartbeat = time.time()
                    
                    # Show next steps
                    next_steps = result.get('next_steps', [
                        "Wait for admin to assign you to a group",
                        "Admin will use the web interface to make assignments",
                        "Client will automatically start playing when streaming begins"
                    ])
                    print(f"\n Next Steps:")
                    for step in next_steps:
                        print(f"    {step}")
                    
                    print(f"{'='*80}")
                    return True
                else:
                    print(f" Registration failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f" Registration failed with HTTP status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f" Registration error: {e}")
            self.logger.error(f"Registration error: {e}")
            return False
    
    def wait_for_assignment(self) -> bool:
        """Wait for admin to assign this client to a group and stream"""
        retry_count = 0
        
        print(f"\n Waiting for assignment from admin...")
        print(f"   Admin needs to:")
        print(f"   1. Assign this client to a group")
        print(f"   2. Assign this client to a specific stream/screen")
        print(f"   3. Start streaming for the group")
        print(f"   (Check the web interface at {self.server_url})")
        
        while self.running and not self._shutdown_event.is_set() and retry_count < self.max_retries:
            try:
                # Use new endpoint if available, fallback to legacy
                try:
                    response = requests.post(
                        f"{self.server_url}/api/clients/wait_for_assignment",
                        json={"client_id": self.client_id},
                        timeout=10
                    )
                except requests.exceptions.RequestException:
                    # Fallback to legacy endpoint
                    response = requests.post(
                        f"{self.server_url}/wait_for_stream",
                        json={"client_id": self.client_id},
                        timeout=10
                    )
                
                if response.status_code not in [200, 202]:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                status = data.get('status')
                message = data.get('message', '')
                
                # Update heartbeat since we're actively communicating with server
                self.last_heartbeat = time.time()
                
                self.logger.debug(f"Server response: status={status}")
                
                if status == "ready_to_play":
                    # Stream is ready!
                    original_stream_url = data.get('stream_url')
                    self.current_stream_url = self.fix_stream_url(original_stream_url)
                    
                    # Handle stream version
                    server_version = data.get('stream_version')
                    if server_version is not None:
                        self.current_stream_version = server_version
                    else:
                        if self.current_stream_version is None:
                            self.current_stream_version = int(time.time())
                    
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    
                    print(f"\n ASSIGNMENT COMPLETE!")
                    print(f"   Group: {group_name}")
                    print(f"   Stream: {stream_assignment}")
                    print(f"   Assignment Type: {data.get('assignment_status', 'unknown')}")
                    if data.get('screen_number') is not None:
                        print(f"   Screen Number: {data.get('screen_number')}")
                    print(f"   Stream URL: {self.current_stream_url}")
                    print(f"   Stream Version: {self.current_stream_version}")
                    return True
                
                elif status in ["waiting_for_group_assignment", "waiting_for_stream_assignment"]:
                    print(f" {message}")
                    retry_count = 0  # Don't count as failure
                
                elif status == "waiting_for_streaming":
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    print(f" {message}")
                    print(f"   Assigned to: {group_name}/{stream_assignment}")
                    print(f"   Waiting for admin to start streaming...")
                    retry_count = 0
                
                elif status == "group_not_found":
                    # The group might exist but Docker discovery is failing
                    # Keep waiting instead of giving up
                    group_id = data.get('group_id')
                    if retry_count % 6 == 0:
                        print(f"  Group validation failed, but continuing (Docker discovery issue)")
                        print(f"   Group ID: {group_id}")
                        print(f"   Will retry...")
                    # Don't print error every time
                    retry_count += 1
                    # Continue waiting instead of returning error
                
                elif status == "not_registered":
                    print(f" {message}")
                    print(f"   Client may have been removed from server")
                    return False
                
                else:
                    print(f"  Unexpected status: {status} - {message}")
                    retry_count += 1
                
                # Interruptible sleep
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    print(f"   Shutdown requested during wait")
                    return False
                
            except Exception as e:
                print(f"  Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval * 2):
                    print(f"   Shutdown requested during error wait")
                    return False
        
        if retry_count >= self.max_retries:
            print(f" Max retries reached, giving up")
            return False
        
        return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to server to keep connection alive"""
        try:
            response = requests.post(
                f"{self.server_url}/api/clients/heartbeat",
                json={
                    "client_id": self.client_id
                },
                timeout=10
            )
            data = response.json()
            
            if data.get("success", False):
                print(f" Heartbeat sent successfully")
                return True
            else:
                print(f" Heartbeat failed: {data.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
                print(f" Heartbeat request failed: {e}")
                return False
    
    def fix_stream_url(self, stream_url: str) -> str:
        """Fix stream URL to use server IP instead of localhost"""
        if not stream_url:
            return stream_url
            
        if "127.0.0.1" in stream_url:
            fixed_url = stream_url.replace("127.0.0.1", self.server_ip)
            self.logger.info(f"Fixed stream URL: 127.0.0.1  {self.server_ip}")
            return fixed_url
        elif "localhost" in stream_url:
            fixed_url = stream_url.replace("localhost", self.server_ip)
            self.logger.info(f"Fixed stream URL: localhost  {self.server_ip}")
            return fixed_url
        else:
            return stream_url
    
    def play_stream(self) -> bool:
        """Start playing the assigned stream with optimal player selection"""
        if not self.current_stream_url:
            self.logger.error("No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            # Choose the optimal player for this stream
            player_type, reason = self.choose_optimal_player(self.current_stream_url)
            self.current_player_type = player_type
            
            print(f"\n SMART PLAYER SELECTION")
            print(f"   Selected: {player_type.upper()}")
            print(f"   Reason: {reason}")
            print(f"   Stream URL: {self.current_stream_url}")
            
            if player_type == "cpp_player":
                return self._play_with_cpp_player()
            else:
                return self._play_with_ffplay()
                    
        except Exception as e:
            self.logger.error(f"Player error: {e}")
            return False
    
    def _play_with_cpp_player(self) -> bool:
        """Start playing with the built C++ player (for SEI streams)"""
        try:
            print(f"\n STARTING C++ PLAYER (SEI MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: SEI timestamp processing")
            
            env = os.environ.copy()
            cmd = [self.player_executable, self.current_stream_url]
            
            self.player_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=os.path.dirname(self.player_executable),
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor C++ player output with SEI-specific logging
            def monitor_cpp_output():
                try:
                    for line in iter(self.player_process.stdout.readline, ''):
                        if line.strip():
                            line_clean = line.strip()
                            if "SEI" in line_clean or "timestamp" in line_clean.lower():
                                self.logger.info(f" SEI: {line_clean}")
                            elif "TELEMETRY:" in line_clean:
                                self.logger.info(f" {line_clean}")
                            elif "ERROR" in line_clean.upper():
                                self.logger.error(f" {line_clean}")
                            elif "WARNING" in line_clean.upper():
                                self.logger.warning(f" {line_clean}")
                            else:
                                self.logger.debug(f" {line_clean}")
                except Exception as e:
                    self.logger.error(f"Error monitoring C++ output: {e}")
                finally:
                    if self.player_process and self.player_process.stdout:
                        self.player_process.stdout.close()
            
            output_thread = threading.Thread(target=monitor_cpp_output, daemon=True)
            output_thread.start()
            
            print(f"   Player PID: {self.player_process.pid}")
            print(f"   Status: Playing with SEI processing")
            self.logger.info(f"C++ Player started for SEI stream")
            
            # Position window on the correct monitor after a delay (multiple attempts)
            threading.Timer(2.0, self._position_window_on_monitor).start()   # First attempt
            threading.Timer(5.0, self._position_window_on_monitor).start()   # Second attempt
            threading.Timer(10.0, self._position_window_on_monitor).start()  # Third attempt
            
            # Start fallback monitoring after initial positioning
            threading.Timer(15.0, self._start_fallback_monitor).start()
            
            # Continuous window positioning monitor disabled to prevent repositioning
            # self._start_window_positioning_monitor()
            
            return True
            
        except Exception as e:
            self.logger.error(f"C++ Player error: {e}")
            return False
    
    def _have_window_tools(self) -> bool:
        """Check if wmctrl and xdotool are available for window control"""
        try:
            wmctrl_ok = subprocess.run(["which", "wmctrl"], capture_output=True).returncode == 0
            xdotool_ok = subprocess.run(["which", "xdotool"], capture_output=True).returncode == 0
            return wmctrl_ok and xdotool_ok
        except Exception:
            return False

    def _find_player_window_ids(self) -> list:
        """Find window IDs owned by the current player process (ffplay or C++)."""
        try:
            if not self.player_process or not self.player_process.pid:
                return []
            pid_str = str(self.player_process.pid)
            result = subprocess.run(['wmctrl', '-lp'], capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout:
                return []
            window_ids = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] == pid_str:
                    window_ids.append(parts[0])
            return window_ids
        except Exception:
            return []

    def _ensure_window_visible(self):
        """Force the ffplay/player window to map and raise so it's visible."""
        try:
            # Wait for window to appear (by PID or title)
            for i in range(10):
                pid_windows = self._find_player_window_ids()
                if pid_windows:
                    for wid in pid_windows:
                        subprocess.run(['xdotool', 'windowmap', wid], capture_output=True)
                        subprocess.run(['xdotool', 'windowactivate', '--sync', wid], capture_output=True)
                    print(f"   ✅ Window(s) mapped and raised")
                    return
                time.sleep(0.5)
            # Fallback: try by title
            window_title = f"Multi-Screen Client - {self.display_name}"
            subprocess.run(['xdotool', 'search', '--name', window_title, 'windowmap', 'windowactivate', '--sync'], capture_output=True)
            print(f"   ⚠️  Raised window by title")
        except Exception as e:
            self.logger.debug(f"Could not force window visible: {e}")

    def _get_monitor_resolution(self, monitor_index):
        """Get the resolution of the specified monitor."""
        try:
            result = subprocess.run(['xrandr', '--current'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if ' connected' in line and not 'disconnected' in line:
                        # Extract resolution from line like "HDMI-1 connected 1920x1080+0+0"
                        parts = line.split()
                        for part in parts:
                            if 'x' in part and '+' in part:
                                res = part.split('+')[0]
                                if 'x' in res:
                                    w, h = res.split('x')
                                    return int(w), int(h)
            return 1920, 1080  # Default fallback
        except:
            return 1920, 1080

    def _force_immediate_fullscreen(self):
        """Force fullscreen immediately after window positioning"""
        try:
            if not self.player_process or self.player_process.poll() is not None:
                return
                
            print(f"   🎯 FORCING IMMEDIATE FULLSCREEN")
            pid_windows = self._find_player_window_ids()
            if pid_windows:
                for wid in pid_windows:
                    print(f"   Activating window {wid} and sending fullscreen key")
                    # Multiple methods to ensure fullscreen
                    subprocess.run(['xdotool', 'windowactivate', '--sync', wid], capture_output=True)
                    time.sleep(0.5)
                    subprocess.run(['xdotool', 'key', 'f'], capture_output=True)
                    time.sleep(0.5)
                    subprocess.run(['wmctrl', '-ir', wid, '-b', 'add,fullscreen'], capture_output=True)
                    print(f"   ✅ Applied fullscreen to window {wid}")
        except Exception as e:
            self.logger.error(f"Immediate fullscreen failed: {e}")

    def _enforce_fullscreen_periodic(self):
        """Periodically enforce fullscreen mode only if needed."""
        try:
            if not self.player_process or self.player_process.poll() is not None:
                return
                
            pid_windows = self._find_player_window_ids()
            if pid_windows:
                needs_fix = False
                target_x, target_y = self.monitor_positions[self.current_monitor]
                target_w, target_h = self._get_monitor_resolution(self.current_monitor)
                
                for wid in pid_windows:
                    # Check current window state first
                    result = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if wid in line:
                                parts = line.split()
                                if len(parts) >= 6:
                                    x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                                    
                                    # Check if positioned correctly (within 100px tolerance)
                                    positioned_ok = abs(x - target_x) < 100 and abs(y - target_y) < 100
                                    # Check if fullscreen with correct resolution
                                    fullscreen_ok = w >= target_w - 50 and h >= target_h - 50
                                    
                                    if not positioned_ok or not fullscreen_ok:
                                        needs_fix = True
                                        print(f"   🔧 Window needs fix: pos_ok={positioned_ok}, fs_ok={fullscreen_ok} (current: {w}x{h}, target: {target_w}x{target_h})")
                                        
                                        # Fix positioning if needed
                                        if not positioned_ok:
                                            subprocess.run(['wmctrl', '-ir', wid, '-e', f'0,{target_x},{target_y},-1,-1'], capture_output=True)
                                        
                                        # Fix fullscreen if needed
                                        if not fullscreen_ok:
                                            subprocess.run(['xdotool', 'windowactivate', '--sync', wid, 'key', 'f'], capture_output=True)
                                    else:
                                        print(f"   ✅ Window is correctly positioned and fullscreen ({w}x{h})")
                                    break
                
                # Only schedule next check if we needed to fix something
                if needs_fix:
                    threading.Timer(5.0, self._enforce_fullscreen_periodic).start()
                else:
                    # If everything is good, check again in 15 seconds
                    threading.Timer(15.0, self._enforce_fullscreen_periodic).start()
        except Exception as e:
            self.logger.debug(f"Fullscreen enforcement failed: {e}")

    def _play_with_ffplay(self) -> bool:
        """Start playing with ffplay (for standard streams without SEI)"""
        try:
            print(f"\n STARTING FFPLAY (STANDARD MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: Standard video playback")
            
            # Force SDL to create a window immediately with proper resolution
            env = os.environ.copy()
            env['SDL_VIDEODRIVER'] = 'x11'  # Force X11 even on Wayland for window control
            env['DISPLAY'] = env.get('DISPLAY', ':0')
            env['SDL_VIDEO_WINDOW_POS'] = '0,0'  # Force window position
            env['SDL_VIDEO_CENTERED'] = '0'  # Don't center window
            
            cmd = [
                "ffplay",
                "-fs",  # Always start fullscreen
                "-x", "1920",  # Force width
                "-y", "1080",  # Force height
                "-an",  # Disable audio to avoid PulseAudio issues
                "-fflags", "nobuffer",
                "-flags", "low_delay", 
                "-framedrop",
                "-strict", "experimental",
                "-window_title", f"Multi-Screen Client - {self.display_name}",
                "-autoexit",
                "-loglevel", "warning",
                self.current_stream_url
            ]
            
            self.player_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env
            )
            
            # Monitor ffplay output (less verbose than C++ player)
            def monitor_ffplay_output():
                try:
                    for line in iter(self.player_process.stderr.readline, ''):
                        if line.strip():
                            line_clean = line.strip()
                            # Show ALL ffplay output for debugging
                            print(f"FFPLAY: {line_clean}")
                            if "error" in line_clean.lower():
                                self.logger.error(f" {line_clean}")
                            elif "warning" in line_clean.lower():
                                self.logger.warning(f" {line_clean}")
                            else:
                                self.logger.debug(f" {line_clean}")
                except Exception as e:
                    self.logger.debug(f"Error monitoring ffplay output: {e}")
            
            output_thread = threading.Thread(target=monitor_ffplay_output, daemon=True)
            output_thread.start()
            
            print(f"   Player PID: {self.player_process.pid}")
            print(f"   Status: Playing standard stream")
            print(f"   Command: {' '.join(cmd)}")
            self.logger.info(f"ffplay started for standard stream")
            
            # Wait a bit for window to appear, then force map/raise it
            time.sleep(3)
            self._ensure_window_visible()
            
            # Position window on the correct monitor after ensuring visibility
            # Only try once, and only if needed
            threading.Timer(5.0, self._position_window_on_monitor).start()
            
            # Force fullscreen immediately after a short delay
            threading.Timer(8.0, self._force_immediate_fullscreen).start()
            
            # Start fallback monitoring after initial positioning
            threading.Timer(15.0, self._start_fallback_monitor).start()
            
            # Enable periodic fullscreen enforcement to ensure windows stay fullscreen
            threading.Timer(3.0, self._enforce_fullscreen_periodic).start()
            
            # Continuous window positioning monitor disabled to prevent repositioning
            # self._start_window_positioning_monitor()
            
            return True
            
        except Exception as e:
            self.logger.error(f"ffplay error: {e}")
            return False
    
    def monitor_player(self) -> str:
        """Monitor the player process and check for stream changes"""
        if not self.player_process:
            return 'error'
        
        # Determine current player type for display
        player_display_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
        
        print(f"\n MONITORING {player_display_name.upper()}")
        print(f"   PID: {self.player_process.pid}")
        print(f"   Stream: {self.current_stream_url}")
        print(f"   Player Type: {self.current_player_type}")
        
        last_stream_check = time.time()
        stream_check_interval = 10
        last_health_report = time.time()
        health_report_interval = 30
        
        while self.running and not self._shutdown_event.is_set() and self.player_process.poll() is None:
            current_time = time.time()
            
            # Handle window manager events
            if self.window_manager:
                try:
                    self.window_manager.update()
                except tk.TclError:
                    # Window manager closed
                    break
            
            # Check for stream changes
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    print(f" Stream change detected, will restart with optimal player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                print(f" {player_display_name} health: PID={self.player_process.pid}, "
                      f"Running {int(current_time - last_health_report)}s")
                last_health_report = current_time
            
            # Check for shutdown
            if self._shutdown_event.wait(timeout=1):
                print(f" Shutdown requested during monitoring")
                self.stop_stream()
                return 'user_exit'
        
        # Player has stopped
        if self._shutdown_event.is_set() or not self.running:
            return 'user_exit'
        
        exit_code = self.player_process.returncode if self.player_process else -1
        
        print(f"\n PLAYER STOPPED - DEBUG INFO:")
        print(f"   Player: {player_display_name}")
        print(f"   Exit Code: {exit_code}")
        print(f"   Stream URL: {self.current_stream_url}")
        print(f"   Stream Version: {self.current_stream_version}")
        
        if exit_code == 0:
            print(f" {player_display_name} ended normally")
            return 'stream_ended'
        elif exit_code == 1:
            print(f"  {player_display_name} connection lost or stream unavailable")
            return 'connection_lost'
        else:
            print(f" {player_display_name} exited with error code: {exit_code}")
            return 'error'
    
    def _check_for_stream_change(self) -> bool:
        """Check if the stream URL or version has changed on the server"""
        try:
            # FIXED: Don't call wait_for_assignment() here as it creates an infinite loop
            # Instead, just check if we still have a valid stream URL
            if not self.current_stream_url:
                self.logger.info("No current stream URL - need to restart")
                return True
            
            # For now, assume stream is still valid if we have a URL
            # In the future, we could add a lightweight health check endpoint
            # that doesn't trigger the assignment flow
            return False
            
        except Exception as e:
            self.logger.debug(f"Stream change check failed: {e}")
            return False
    
    def stop_stream(self):
        """Stop the player with comprehensive cleanup"""
        if self.player_process:
            try:
                pid = self.player_process.pid
                player_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
                print(f" Stopping {player_name} (PID: {pid})")
                
                # Graceful termination
                self.player_process.terminate()
                
                try:
                    self.player_process.wait(timeout=3)
                    print(f" {player_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"  Force killing {player_name}")
                    self.player_process.kill()
                    
                    try:
                        self.player_process.wait(timeout=2)
                        print(f" {player_name} force-killed")
                    except subprocess.TimeoutExpired:
                        print(f" {player_name} unresponsive")
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (OSError, ProcessLookupError):
                            pass
                
            except (OSError, ProcessLookupError):
                print(f" Player process already terminated")
            except Exception as e:
                self.logger.error(f"Error stopping player: {e}")
            finally:
                self.player_process = None
                self.current_player_type = None
    
    def shutdown(self):
        """Initiate graceful shutdown"""
        if not self.running:
            return
        
        print(f"\n INITIATING GRACEFUL SHUTDOWN")
        self.running = False
        self._shutdown_event.set()
        
        # Stop fallback monitor
        if self.fallback_monitor_thread and self.fallback_monitor_thread.is_alive():
            self.logger.info("Stopping fallback monitor...")
        
        # Stop components
        self.stop_stream()
        
        # Clean up window manager
        if self.window_manager:
            try:
                self.window_manager.destroy()
            except:
                pass
            self.window_manager = None
        
        print(f" Shutdown complete")
    
    def _emergency_cleanup(self):
        """Emergency cleanup for atexit"""
        if self.running:
            self.shutdown()
    
    def run(self):
        """Main execution flow"""
        try:
            print(f"\n{'='*80}")
            print(f" UNIFIED MULTI-SCREEN CLIENT")
            print(f"   Hostname: {self.hostname}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            print(f"   C++ Player: {'Available' if self.player_executable else 'Not found'}")
            print(f"{'='*80}")
            
            # Step 1: Register with server
            if not self.register():
                print(f" Registration failed - exiting")
                return
            
            # Step 1.5: Create window manager for hotkeys (if enabled)
            if self.enable_hotkeys:
                self.create_window_manager()
            
            # Step 2: Main loop - wait for assignment and play streams
            while self.running and not self._shutdown_event.is_set():
                # Send periodic heartbeat to keep connection alive
                if hasattr(self, 'last_heartbeat') and (time.time() - self.last_heartbeat) > 30:
                    self.send_heartbeat()
                    self.last_heartbeat = time.time()
                elif not hasattr(self, 'last_heartbeat'):
                    self.last_heartbeat = time.time()
                
                # Wait for stream assignment
                if self.wait_for_assignment():
                    if self._shutdown_event.is_set():
                        break
                        
                    # Play the assigned stream
                    if self.play_stream():
                        # Monitor the player
                        stop_reason = self.monitor_player()
                        
                        if stop_reason == 'user_exit':
                            print(f" User requested exit")
                            break
                        elif stop_reason == 'stream_changed':
                            print(f" Stream changed, restarting...")
                            continue
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            print(f" Stream stopped ({stop_reason}), waiting for new assignment...")
                            print(f" Client will stay connected and wait for new stream...")
                            self.current_stream_url = None
                            self.current_stream_version = None
                            self.current_player_type = None
                            # Clear any existing player process
                            if self.player_process:
                                self.player_process = None
                            continue
                        else:
                            print(f"  Unexpected stop reason: {stop_reason}")
                            print(f"  Treating as stream end, will wait for new assignment...")
                            self.current_stream_url = None
                            self.current_stream_version = None
                            self.current_player_type = None
                            if self.player_process:
                                self.player_process = None
                            continue
                    else:
                        print(f" Failed to start player, retrying in 10 seconds...")
                        if self._shutdown_event.wait(timeout=10):
                            break
                else:
                    print(f" Assignment failed, retrying in 10 seconds...")
                    if self._shutdown_event.wait(timeout=10):
                        break
                        
        except Exception as e:
            print(f" Fatal error: {e}")
            self.logger.error(f"Fatal error in main loop: {e}")
            print(f" Attempting to recover and continue...")
            # Try to recover instead of shutting down
            try:
                time.sleep(5)  # Wait a bit before retrying
                print(f" Retrying main loop...")
                # Don't call shutdown, just continue
            except Exception as recovery_error:
                print(f" Recovery failed: {recovery_error}")
                print(f"\n MULTI-SCREEN CLIENT SHUTDOWN")
                self.shutdown()
        finally:
            if not self.running:
                print(f"\n MULTI-SCREEN CLIENT SHUTDOWN")
                self.shutdown()


def main():
    """Main entry point for the multi-screen client"""
    parser = argparse.ArgumentParser(
        prog='client.py',
        description="""
 Unified Multi-Screen Client for Video Wall Systems

A simple and reliable client for multi-screen video streaming that supports
automatic player selection with intelligent monitor assignment.

Features:
   Automatic server registration with unique client identification
   Smart player selection (C++ player for SEI streams, ffplay fallback)
   Automatic monitor assignment based on hostname and availability
   Prevents multiple clients from using the same monitor
   Movable fullscreen windows with hotkeys
   Uses system default display (DISPLAY=:0.0)
   Automatic reconnection and error recovery
   Support for multiple instances on the same device
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 BASIC USAGE EXAMPLES:

  Standard usage:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Monitor 1"

  Multiple clients on same device:
    # Client 1:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Client 1"

    # Client 2:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 --display-name "Client 2"

  Note: Uses system default display (DISPLAY=:0.0)

  ADVANCED OPTIONS:

  Force ffplay for all streams (disable smart selection):
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --force-ffplay

  Multi-monitor setup with auto-assignment:
    # Auto-assign monitors based on hostname (recommended)
    DISPLAY=:0 python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Monitor 1" &
    
    DISPLAY=:0 python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-2 --display-name "Monitor 2" &
    
    # Manual monitor assignment (if needed)
    DISPLAY=:0 python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Monitor 1" --monitor 0 &
    
    # Use hotkeys to move between monitors:
    # Ctrl+M or Ctrl+Right: Next monitor
    # Ctrl+Left: Previous monitor
    # Ctrl+1-4: Specific monitor

  Debug mode with detailed logging:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --debug

 DEPLOYMENT EXAMPLES:

  Systemd service for Client 1:
    ExecStart=/usr/bin/python3 client.py \\
      --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 \\
      --display-name "Client 1"

  Systemd service for Client 2:
    ExecStart=/usr/bin/python3 client.py \\
      --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 \\
      --display-name "Client 2"

 SETUP PROCESS:

  1. Ensure ffmpeg/ffplay is installed:
     sudo apt install ffmpeg

  2. Start client:
     python3 client.py --server http://YOUR_SERVER_IP:5000 \\
       --hostname client-1 --display-name "Screen 1"

  3. Use web interface to assign clients to groups and start streaming



 TROUBLESHOOTING:

  Check display configuration:
    xrandr --listmonitors

  Test display:
    xeyes &

  View client logs:
    python3 client.py --server http://YOUR_SERVER_IP:5000 \\
      --hostname client-1 --display-name "Screen 1" --debug

For more information, visit: https://github.com/your-repo/openvideowalls
        """
    )
    
    # Required arguments group
    required_group = parser.add_argument_group(' Required Arguments')
    required_group.add_argument('--server', 
                               required=True,
                               metavar='URL',
                               help='Server URL - Example: http://192.168.1.100:5000')
    required_group.add_argument('--hostname', 
                               required=True,
                               metavar='NAME',
                               help='Client hostname - Example: rpi-client-1')
    required_group.add_argument('--display-name', 
                               required=True,
                               metavar='NAME',
                               help='Display name for admin interface - Example: "Monitor 1"')
    
    # Optional arguments group
    optional_group = parser.add_argument_group('  Optional Arguments')
    optional_group.add_argument('--force-ffplay', 
                               action='store_true',
                               help='Force use of ffplay for all streams (disable smart C++/ffplay selection)')

    optional_group.add_argument('--monitor', 
                               type=int, 
                               default=None,
                               help='Monitor index to start on (0-based: 0=left, 1=right, 2=far-right, 3=bottom). If not specified, auto-assigns based on hostname and availability.')

    optional_group.add_argument('--debug', 
                               action='store_true',
                               help='Enable debug logging (includes SEI detection details)')

    optional_group.add_argument('--no-hotkeys', 
                               action='store_true',
                               help='Disable hotkey window manager (prevents gray boxes from appearing)')

    optional_group.add_argument('--version', 
                               action='version', 
                               version=' Unified Multi-Screen Client v3.0')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate server URL
    if not args.server.startswith(('http://', 'https://')):
        print(" Error: Server URL must start with http:// or https://")
        print("   Example: --server http://192.168.1.100:5000")
        print("   Example: --server https://videowall.example.com:5000")
        sys.exit(1)
    

    
    # Validate hostname (basic check)
    if not args.hostname.strip():
        print(" Error: Hostname cannot be empty")
        print("   Example: --hostname rpi-client-1")
        sys.exit(1)
    
    # Validate display name (basic check)
    if not args.display_name.strip():
        print(" Error: Display name cannot be empty")
        print("   Example: --display-name \"Monitor 1\"")
        sys.exit(1)
    
    # Validate monitor index (if specified)
    if args.monitor is not None and (args.monitor < 0 or args.monitor > 3):
        print(" Error: Monitor index must be between 0 and 3")
        print("   0 = Monitor 1 (left)")
        print("   1 = Monitor 2 (right)")
        print("   2 = Monitor 3 (far-right)")
        print("   3 = Monitor 4 (bottom)")
        print("   Or omit --monitor for auto-assignment")
        sys.exit(1)
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print(" Debug logging enabled")
    
    # Create and run client
    try:
        client = UnifiedMultiScreenClient(
            server_url=args.server,
            hostname=args.hostname,
            display_name=args.display_name,
            force_ffplay=args.force_ffplay,
            initial_monitor=args.monitor,
            enable_hotkeys=not args.no_hotkeys
        )
        
        print(" Starting Unified Multi-Screen Client...")
        print("   Press Ctrl+C to stop gracefully")
        
        client.run()
        
    except KeyboardInterrupt:
        print("\n  Keyboard interrupt received")
    except Exception as e:
        print(f"\n Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()