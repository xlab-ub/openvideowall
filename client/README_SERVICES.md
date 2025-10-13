# Multi-Screen Client Systemd Services

This guide explains how to set up and manage Multi-Screen Client services using systemd.

## 📋 Overview

The Multi-Screen Client can be run as systemd services for automatic startup, monitoring, and management. This is ideal for production environments where you need reliable, unattended operation.

## 🚀 Quick Start

### 1. Install Services

```bash
# Navigate to client directory
cd /home/client3/Multiscreen/client

# Install system services (requires sudo)
sudo ./install_system_services.sh
```

### 2. Start Services

```bash
# Start both clients
sudo systemctl start multiscreen-client-1
sudo systemctl start multiscreen-client-2

# Or start individually
sudo systemctl start multiscreen-client-1
sudo systemctl start multiscreen-client-2
```

### 3. Check Status

```bash
# Check service status
sudo systemctl status multiscreen-client-1
sudo systemctl status multiscreen-client-2

# View live logs
sudo journalctl -u multiscreen-client-1 -f
sudo journalctl -u multiscreen-client-2 -f
```

## 🔧 Service Configuration

### Default Configuration

| Service | Hostname | Display Name | Monitor | Server |
|---------|----------|--------------|---------|--------|
| multiscreen-client-1 | UB_3S_1 | UB_3S_1 | 0 (left) | http://128.205.220.234:5000 |
| multiscreen-client-2 | UB_3S_2 | UB_3S_2 | 1 (right) | http://128.205.220.234:5000 |

### Customizing Services

To modify the services for your specific setup:

1. **Edit the service files:**
   ```bash
   sudo nano /etc/systemd/system/multiscreen-client-1.service
   sudo nano /etc/systemd/system/multiscreen-client-2.service
   ```

2. **Modify the ExecStart line:**
   ```ini
   ExecStart=/home/client3/Multiscreen/client/run_client.sh --server YOUR_SERVER_URL --hostname YOUR_HOSTNAME --display-name "YOUR_DISPLAY_NAME" --monitor MONITOR_NUMBER --no-hotkeys
   ```

3. **Reload and restart:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart multiscreen-client-1
   sudo systemctl restart multiscreen-client-2
   ```

## 📊 Service Management Commands

### Basic Operations

```bash
# Start services
sudo systemctl start multiscreen-client-1
sudo systemctl start multiscreen-client-2

# Stop services
sudo systemctl stop multiscreen-client-1
sudo systemctl stop multiscreen-client-2

# Restart services
sudo systemctl restart multiscreen-client-1
sudo systemctl restart multiscreen-client-2

# Check status
sudo systemctl status multiscreen-client-1
sudo systemctl status multiscreen-client-2
```

### Auto-Start Configuration

```bash
# Enable auto-start on boot
sudo systemctl enable multiscreen-client-1
sudo systemctl enable multiscreen-client-2

# Disable auto-start
sudo systemctl disable multiscreen-client-1
sudo systemctl disable multiscreen-client-2

# Check if enabled
sudo systemctl is-enabled multiscreen-client-1
sudo systemctl is-enabled multiscreen-client-2
```

### Logging and Monitoring

```bash
# View recent logs
sudo journalctl -u multiscreen-client-1 --since "1 hour ago"
sudo journalctl -u multiscreen-client-2 --since "1 hour ago"

# Follow live logs
sudo journalctl -u multiscreen-client-1 -f
sudo journalctl -u multiscreen-client-2 -f

# View all logs
sudo journalctl -u multiscreen-client-1
sudo journalctl -u multiscreen-client-2

# Clear logs (if needed)
sudo journalctl --vacuum-time=1d
```

## 🖥️ Multi-Screen Setup

### Monitor Configuration

The services are configured for a dual-monitor setup:

- **Monitor 0 (Left)**: 1920x1080 at position (0, 0)
- **Monitor 1 (Right)**: 1920x1080 at position (3840, 0)

### Adding More Screens

To add additional screens, create new service files:

1. **Copy existing service:**
   ```bash
   sudo cp /etc/systemd/system/multiscreen-client-1.service /etc/systemd/system/multiscreen-client-3.service
   ```

2. **Edit the new service:**
   ```bash
   sudo nano /etc/systemd/system/multiscreen-client-3.service
   ```

3. **Update the configuration:**
   ```ini
   [Unit]
   Description=Multi-Screen Client 3 (UB_3S_3)
   
   [Service]
   ExecStart=/home/client3/Multiscreen/client/run_client.sh --server http://128.205.220.234:5000 --hostname UB_3S_3 --display-name "UB_3S_3" --monitor 2 --no-hotkeys
   ```

4. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable multiscreen-client-3
   sudo systemctl start multiscreen-client-3
   ```

## 🔍 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status for errors
sudo systemctl status multiscreen-client-1

# Check logs for specific errors
sudo journalctl -u multiscreen-client-1 --since "5 minutes ago"
```

#### Display Issues
```bash
# Verify DISPLAY environment
echo $DISPLAY

# Check if X server is running
ps aux | grep X

# Test display access
xrandr --query
```

#### Permission Issues
```bash
# Check file permissions
ls -la /home/client3/Multiscreen/client/run_client.sh
ls -la /home/client3/Multiscreen/client/client.py

# Fix permissions if needed
chmod +x /home/client3/Multiscreen/client/run_client.sh
chmod +x /home/client3/Multiscreen/client/client.py
```

#### Network Issues
```bash
# Test server connectivity
curl -I http://128.205.220.234:5000

# Check network configuration
ip route show
```

### Debug Mode

Enable debug logging for troubleshooting:

1. **Edit service file:**
   ```bash
   sudo nano /etc/systemd/system/multiscreen-client-1.service
   ```

2. **Add --debug flag:**
   ```ini
   ExecStart=/home/client3/Multiscreen/client/run_client.sh --server http://128.205.220.234:5000 --hostname UB_3S_1 --display-name "UB_3S_1" --monitor 0 --no-hotkeys --debug
   ```

3. **Restart service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart multiscreen-client-1
   ```

## 📁 File Locations

### Service Files
- `/etc/systemd/system/multiscreen-client-1.service`
- `/etc/systemd/system/multiscreen-client-2.service`

### Client Files
- `/home/client3/Multiscreen/client/client.py` - Main client application
- `/home/client3/Multiscreen/client/run_client.sh` - Client runner script
- `/home/client3/Multiscreen/client/install_system_services.sh` - Service installer

### Logs
- System logs: `journalctl -u multiscreen-client-1`
- Client logs: Check console output in journalctl

## 🔒 Security Considerations

The services run with the following security settings:
- **User**: Runs as `client3` (not root)
- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Isolated temporary directory
- **ProtectSystem**: Read-only system directories
- **ReadWritePaths**: Limited to client directory only

## 🆘 Support

If you encounter issues:

1. **Check logs first**: `sudo journalctl -u multiscreen-client-1 -f`
2. **Verify configuration**: Check service files and parameters
3. **Test manually**: Run the client manually to isolate issues
4. **Check dependencies**: Ensure all required packages are installed

## 📝 Notes

- Services automatically restart if they crash
- Hotkeys are disabled by default to prevent UI interference
- Monitor assignment is automatic based on hostname patterns
- Services require a graphical session (DISPLAY=:0)



