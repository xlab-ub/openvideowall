# Multi-Screen Client Monitor Assignment

## Overview

The Multi-Screen Client has been enhanced with intelligent monitor assignment functionality that automatically assigns clients to monitors 1 or 2 based on hostname patterns and prevents multiple clients from using the same monitor.

## Key Features

### ✅ Automatic Monitor Assignment
- **Hostname-based assignment**: Clients are automatically assigned to monitors based on their hostname
  - Hostnames containing '1', 'left', or 'monitor1' → Monitor 1 (left)
  - Hostnames containing '2', 'right', or 'monitor2' → Monitor 2 (right)
  - Other hostnames → Monitor 1 (default)

### ✅ Overlap Prevention
- **Monitor availability checking**: Detects which monitors are available using `xrandr`
- **Usage detection**: Checks if monitors are already in use by other clients
- **Automatic fallback**: If preferred monitor is busy, automatically tries the alternative

### ✅ Persistent Window Positioning
- **Continuous monitoring**: Background thread continuously monitors window positions
- **Automatic repositioning**: Windows are automatically moved back to their assigned monitor if moved
- **Multiple positioning attempts**: Uses multiple timing strategies to ensure proper positioning

### ✅ Smart Monitor Detection
- **xrandr integration**: Uses `xrandr --listmonitors` to detect available monitors
- **Fallback detection**: If xrandr fails, assumes monitors 0 and 1 are available
- **Position validation**: Validates that windows are positioned on the correct monitor

## Usage Examples

### Auto-Assignment (Recommended)
```bash
# Client 1 - automatically assigned to Monitor 1
python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-1 --display-name "Monitor 1"

# Client 2 - automatically assigned to Monitor 2  
python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-2 --display-name "Monitor 2"

# Left monitor client
python3 client.py --server http://192.168.1.100:5000 \
  --hostname left-monitor --display-name "Left Display"

# Right monitor client
python3 client.py --server http://192.168.1.100:5000 \
  --hostname right-display --display-name "Right Display"
```

### Manual Assignment
```bash
# Force specific monitor assignment
python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-3 --display-name "Monitor 1" --monitor 0

python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-4 --display-name "Monitor 2" --monitor 1
```

## Technical Implementation

### Monitor Assignment Logic
1. **Pattern Matching**: Analyzes hostname for monitor indicators
2. **Availability Check**: Verifies monitor is available and not in use
3. **Fallback Strategy**: Tries alternative monitors if preferred is busy
4. **Position Assignment**: Sets monitor position coordinates

### Window Positioning
1. **Initial Positioning**: Multiple timed attempts to position window after startup
2. **Continuous Monitoring**: Background thread checks position every 5 seconds
3. **Automatic Correction**: Repositions window if it moves off assigned monitor
4. **Tool Integration**: Uses `wmctrl` and `xdotool` for window management

### Monitor Detection
1. **xrandr Query**: Uses `/usr/bin/xrandr --listmonitors` to detect available monitors
2. **Pattern Matching**: Identifies active monitors by resolution patterns
3. **Fallback Detection**: Assumes monitors 0 and 1 if detection fails
4. **Position Mapping**: Maps detected monitors to coordinate positions

## Monitor Positions

The client uses the following monitor positions (4K setup):
- **Monitor 1 (left)**: (0, 0) - HDMI-1
- **Monitor 2 (right)**: (3840, 0) - HDMI-2  
- **Monitor 3 (far-right)**: (7680, 0) - HDMI-3
- **Monitor 4 (bottom-left)**: (0, 2160) - HDMI-4

## Dependencies

- `wmctrl`: Window management and positioning
- `xdotool`: Alternative window management tool
- `xrandr`: Monitor detection (part of x11-xserver-utils)

Install with:
```bash
sudo apt install wmctrl xdotool x11-xserver-utils
```

## Testing

Run the demo script to test monitor assignment:
```bash
python3 demo_monitor_assignment.py
```

Run the test script to verify functionality:
```bash
python3 test_monitor_assignment.py
```

## Hotkeys

The client supports hotkeys for manual monitor switching:
- `Ctrl+M` or `Ctrl+Right`: Move to next monitor
- `Ctrl+Left`: Move to previous monitor
- `Ctrl+1-4`: Move to specific monitor
- `Ctrl+H`: Show help

## Error Handling

- **Monitor detection failure**: Falls back to assuming monitors 0 and 1 are available
- **Window positioning failure**: Logs errors but continues operation
- **Tool unavailability**: Provides helpful error messages for missing dependencies
- **Monitor busy**: Automatically tries alternative monitors

## Benefits

1. **No Manual Configuration**: Clients automatically find available monitors
2. **No Overlap**: Multiple clients can't accidentally use the same monitor
3. **Persistent Positioning**: Windows stay on their assigned monitor
4. **Easy Deployment**: Just use descriptive hostnames for automatic assignment
5. **Fallback Support**: Graceful handling of detection failures and busy monitors

This enhancement makes the Multi-Screen Client much more user-friendly and prevents common issues with multiple client instances competing for the same monitor space.




