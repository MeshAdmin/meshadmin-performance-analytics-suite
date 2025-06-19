# MeshAdmin Developer Dashboard

## Overview
The MeshAdmin Developer Dashboard is a unified control panel for managing all development services and applications during software development cycles. It provides a clean, dark-themed web interface running on port 5555 that helps developers efficiently manage their entire MeshAdmin service portfolio.

## Features

### 🎯 **Unified Service Management**
- **Start/Stop/Restart** all MeshAdmin services with one-click controls
- **Real-time Status Monitoring** with visual indicators (Running, Stopped, Unresponsive)
- **Port Management** - Change service ports dynamically and restart services
- **Quick Access Links** - Direct "Open" buttons to running service web interfaces

### 📊 **System Monitoring**
- **Live System Stats** - CPU load, memory usage, and system load average
- **Service Overview** - Running vs total services count
- **Auto-refresh** - Status updates every 5 seconds automatically

### 📋 **Service Logs**
- **Real-time Log Viewing** - View the last 50 log entries for any service
- **Modal Log Viewer** - Clean interface for browsing service output
- **Automatic Log Collection** - Logs are captured when services start

### 🎨 **Developer-Focused UI**
- **Dark Theme** - Easy on the eyes during long development sessions
- **Responsive Design** - Works on desktop and mobile devices
- **High Contrast** - Improved readability and visual feedback
- **Intuitive Controls** - Clear status badges and button feedback

## Managed Services

The dashboard can control the following MeshAdmin services:

| Service | Default Port | Description |
|---------|-------------|-------------|
| **Enhanced Dashboard** | 8080 | Main performance analytics dashboard with ML/LLM integration |
| **Load Balancer Pro** | 5000 | Advanced load balancing and traffic management |
| **Network Flow Master** | 5001 | Network traffic analysis and monitoring |
| **Observability Dashboard** | 8081 | System monitoring and observability metrics |

## Quick Start

### Method 1: Direct Python
```bash
# Navigate to the project directory
cd "/Users/cnelson/Dev/MeshAdmin Dev/Applications/meshadmin-performance-analytics-suite"

# Start the dashboard
python3 dev_dashboard.py
```

### Method 2: Using the Startup Script
```bash
# Make the script executable (first time only)
chmod +x start_dev_dashboard.sh

# Start the dashboard
./start_dev_dashboard.sh
```

### Method 3: Background Mode
```bash
# Start in background mode
python3 dev_dashboard.py &

# To stop later, find and kill the process
ps aux | grep dev_dashboard
kill [PID]
```

## Usage Guide

### 🚀 **Starting Services**
1. Open http://localhost:5555 in your browser
2. Find the service card you want to start
3. Optionally change the port number in the input field
4. Click the **▶ Start** button
5. The status badge will update to show "Running" when ready
6. Use the **🌐 Open** button to access the service's web interface

### ⏹ **Stopping Services**
1. Find the running service (green "Running" badge)
2. Click the **⏹ Stop** button
3. The service will gracefully shutdown and status will update to "Stopped"

### 🔄 **Restarting Services**
1. Click the **🔄 Restart** button on any service
2. The service will stop, then start again on the specified port
3. Useful for applying configuration changes or clearing memory

### 📋 **Viewing Logs**
1. Click the **📋 Logs** button for any service
2. A modal will open showing recent log entries
3. Logs are automatically collected and limited to the last 100 entries
4. Click "Close" or click outside the modal to dismiss

### 🔄 **Manual Refresh**
- The dashboard auto-refreshes every 5 seconds
- Click the circular **🔄** button (bottom-right) for manual refresh
- System stats and service statuses are updated in real-time

## Benefits for Development

### ⚡ **Efficiency**
- **No Terminal Juggling** - Manage all services from one web interface
- **Quick Testing** - Start/stop services and jump to their URLs instantly
- **Port Flexibility** - Change ports on-the-fly for testing different configurations

### 🛡️ **Reliability**
- **Graceful Shutdown** - Services are properly terminated when stopped
- **Health Monitoring** - Responsive status checks ensure services are actually working
- **Process Management** - Automatic cleanup of dead processes

### 🎯 **Development Workflow**
- **All-in-One View** - See which services are running at a glance
- **Resource Monitoring** - Keep an eye on system load and memory usage
- **Log Debugging** - Quickly access service logs without terminal commands

## Advanced Features

### Service Health Checks
The dashboard performs health checks by hitting each service's status endpoint:
- **Enhanced Dashboard**: `/api/status` on port 8080
- **Load Balancer Pro**: `/api/health` on port 5000  
- **Network Flow Master**: `/api/status` on port 5001
- **Observability Dashboard**: `/health` on port 8081

### Automatic Process Management
- **Process Tracking** - Uses PIDs to track running services
- **Cleanup on Exit** - Pressing Ctrl+C stops all managed services
- **Port Conflict Detection** - Prevents starting services on occupied ports

### Log Collection
- **Real-time Capture** - Service stdout is captured in background threads
- **Memory Efficient** - Only the last 100 log entries are retained per service
- **Thread-safe** - Concurrent log collection doesn't interfere with service operation

## Troubleshooting

### Port Already in Use
If you get "Port already in use" errors:
```bash
# Check what's using the port
lsof -i :5555

# Kill the process if needed
kill [PID]
```

### Service Won't Start
1. Check the **📋 Logs** for error messages
2. Verify the service script exists and is executable
3. Ensure all dependencies are installed in the virtual environment
4. Try starting the service manually from terminal for detailed error output

### Dashboard Not Accessible
1. Verify the dashboard is running: `ps aux | grep dev_dashboard`
2. Check if port 5555 is blocked by firewall
3. Try accessing via `http://127.0.0.1:5555` instead of `localhost`

### Services Show as Unresponsive
1. Services may take a few seconds to fully start up
2. Check if the service's status endpoint is working manually
3. Some services may not have health check endpoints implemented

## Files

- **`dev_dashboard.py`** - Main dashboard application
- **`start_dev_dashboard.sh`** - Convenience startup script
- **`DEV_DASHBOARD_README.md`** - This documentation

## Development Notes

The developer dashboard is built using:
- **Flask** - Lightweight Python web framework
- **psutil** - System and process utilities
- **requests** - HTTP client for health checks
- **Vanilla JavaScript** - No frontend frameworks for simplicity
- **CSS Grid/Flexbox** - Responsive layout system

The dashboard is designed to be:
- **Lightweight** - Minimal dependencies and resource usage
- **Self-contained** - No external dependencies beyond Python packages
- **Maintainable** - Clean, well-documented code structure
- **Extensible** - Easy to add new services to the registry

## Security Considerations

⚠️ **Important**: This dashboard is intended for development use only:
- Services are started with development configurations
- No authentication or authorization controls
- Flask development server (not production-ready)
- Process management requires system-level permissions

**Do not use in production environments.**

---

**Access the dashboard**: http://localhost:5555

**Need help?** Check the logs or review this documentation.

**Ready to develop?** Start your services and begin building! 🚀

