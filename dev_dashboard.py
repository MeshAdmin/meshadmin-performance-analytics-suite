#!/usr/bin/env python3
"""
MeshAdmin Developer Dashboard
Unified control panel for managing all development services and applications.
Runs on port 5555 for easy access during development cycles.
"""

import os
import sys
import json
import time
import psutil
import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
import requests
from urllib.parse import urljoin

app = Flask(__name__)

# Add custom filter for basename
@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path)

# Service registry for known applications
SERVICES = {
    'enhanced_dashboard': {
        'name': 'Enhanced Dashboard',
        'script': './enhanced_dashboard.py',
        'default_port': 8080,
        'description': 'Main performance analytics dashboard with ML/LLM integration',
        'url_path': '/',
        'status_endpoint': '/api/status'
    },
    'load_balancer_pro': {
        'name': 'Load Balancer Pro',
        'script': '/Users/cnelson/Dev/MeshAdmin Dev/MPTCP/LoadBalancerPro/loadbalancer.py',
        'default_port': 5000,
        'description': 'Advanced load balancing and traffic management',
        'url_path': '/',
        'status_endpoint': '/api/health'
    },
    'network_flow_master': {
        'name': 'Network Flow Master', 
        'script': './apps/network-flow-master/app.py',
        'default_port': 5001,
        'description': 'Network traffic analysis and monitoring',
        'url_path': '/',
        'status_endpoint': '/api/status'
    },
    'observability_dashboard': {
        'name': 'Observability Dashboard',
        'script': './apps/observability-dashboard/app.py', 
        'default_port': 8081,
        'description': 'System monitoring and observability metrics',
        'url_path': '/',
        'status_endpoint': '/health'
    }
}

class ServiceManager:
    def __init__(self):
        self.running_services = {}
        self.service_logs = {}
        # Scan for already running services on startup
        self.scan_for_running_services()
    
    def get_service_status(self, service_id):
        """Check if a service is running and responsive"""
        if service_id not in self.running_services:
            return {'status': 'stopped', 'pid': None, 'port': None}
        
        process_info = self.running_services[service_id]
        pid = process_info['pid']
        port = process_info['port']
        
        # Check if process is still alive
        try:
            process = psutil.Process(pid)
            if not process.is_running():
                del self.running_services[service_id]
                return {'status': 'stopped', 'pid': None, 'port': None}
        except psutil.NoSuchProcess:
            del self.running_services[service_id]
            return {'status': 'stopped', 'pid': None, 'port': None}
        
        # Check if service is responsive
        service_config = SERVICES.get(service_id, {})
        status_endpoint = service_config.get('status_endpoint')
        
        if status_endpoint and port:
            try:
                url = f"http://localhost:{port}{status_endpoint}"
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return {'status': 'running', 'pid': pid, 'port': port, 'responsive': True}
                else:
                    return {'status': 'running', 'pid': pid, 'port': port, 'responsive': False}
            except requests.RequestException:
                return {'status': 'running', 'pid': pid, 'port': port, 'responsive': False}
        
        return {'status': 'running', 'pid': pid, 'port': port}
    
    def start_service(self, service_id, port=None):
        """Start a service on specified port"""
        if service_id not in SERVICES:
            return {'success': False, 'error': f'Unknown service: {service_id}'}
        
        service_config = SERVICES[service_id]
        script_path = service_config['script']
        port = port or service_config['default_port']
        
        # Check if port is already in use
        if self.is_port_in_use(port):
            return {'success': False, 'error': f'Port {port} is already in use'}
        
        try:
            # Resolve absolute path to script
            if not os.path.isabs(script_path):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(base_dir, script_path)
            
            # Ensure script exists
            if not os.path.exists(script_path):
                return {'success': False, 'error': f'Script not found: {script_path}'}
            
            # Determine working directory (script's directory)
            script_dir = os.path.dirname(script_path)
            
            # Prepare the command to run the service
            cmd = [sys.executable, os.path.basename(script_path)]
            
            # Set environment variable for port if service supports it
            env = os.environ.copy()
            env['PORT'] = str(port)
            env['FLASK_ENV'] = 'development'
            env['PYTHONPATH'] = f"{script_dir}:{env.get('PYTHONPATH', '')}"
            
            print(f"🚀 Starting {service_config['name']} on port {port}")
            print(f"   Script: {script_path}")
            print(f"   Working dir: {script_dir}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                env=env,
                cwd=script_dir,  # Use script's directory as working directory
                bufsize=0,  # Unbuffered
                text=True   # Text mode for easier log handling
            )
            
            # Store process info
            self.running_services[service_id] = {
                'pid': process.pid,
                'port': port,
                'started_at': datetime.now().isoformat(),
                'process': process
            }
            
            # Start log collection thread
            self.start_log_collection(service_id, process)
            
            return {'success': True, 'pid': process.pid, 'port': port}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_service(self, service_id):
        """Stop a running service"""
        if service_id not in self.running_services:
            return {'success': False, 'error': 'Service not running'}
        
        process_info = self.running_services[service_id]
        pid = process_info['pid']
        
        try:
            # Try graceful shutdown first
            process = psutil.Process(pid)
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown fails
                process.kill()
            
            del self.running_services[service_id]
            return {'success': True}
            
        except psutil.NoSuchProcess:
            del self.running_services[service_id]
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def restart_service(self, service_id, port=None):
        """Restart a service"""
        current_port = None
        if service_id in self.running_services:
            current_port = self.running_services[service_id]['port']
            self.stop_service(service_id)
            time.sleep(1)  # Brief pause
        
        port = port or current_port or SERVICES[service_id]['default_port']
        return self.start_service(service_id, port)
    
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        try:
            # Method 1: Use lsof command (works without special permissions)
            result = subprocess.run(['lsof', '-i', f':{port}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Method 2: Fall back to psutil if available and permitted
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        return False
    
    def start_log_collection(self, service_id, process):
        """Start collecting logs for a service in a separate thread"""
        def collect_logs():
            self.service_logs[service_id] = []
            try:
                for line in iter(process.stdout.readline, ''):
                    if not line:  # End of output
                        break
                    if service_id in self.service_logs:
                        log_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'message': line.strip()
                        }
                        self.service_logs[service_id].append(log_entry)
                        # Keep only last 100 log entries
                        if len(self.service_logs[service_id]) > 100:
                            self.service_logs[service_id].pop(0)
            except Exception as e:
                # Log the error but don't crash the thread
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'message': f'Log collection error: {str(e)}'
                }
                if service_id in self.service_logs:
                    self.service_logs[service_id].append(error_entry)
        
        thread = threading.Thread(target=collect_logs, daemon=True)
        thread.start()
    
    def get_service_logs(self, service_id, last_n=50):
        """Get recent logs for a service"""
        if service_id not in self.running_services:
            return [{
                'timestamp': datetime.now().isoformat(),
                'message': f'Service {service_id} is not running'
            }]
        
        service_info = self.running_services[service_id]
        if service_info.get('process') is None:
            # Pre-existing service - we don't have direct logs
            return [{
                'timestamp': datetime.now().isoformat(),
                'message': f'Service {service_id} was running before dashboard startup - no logs available'
            }]
        
        logs = self.service_logs.get(service_id, [])
        if not logs:
            return [{
                'timestamp': datetime.now().isoformat(),
                'message': f'No logs available yet for {service_id}'
            }]
        
        return logs[-last_n:]
    
    def scan_for_running_services(self):
        """Scan for already running services and register them"""
        print("🔍 Scanning for already running services...")
        
        for service_id, service_config in SERVICES.items():
            port = service_config['default_port']
            
            # Check if the port is in use
            if self.is_port_in_use(port):
                print(f"  • Found service on port {port}, checking if it's {service_config['name']}...")
                
                # Try to find the process using this port
                pid = self.find_process_by_port(port)
                if pid:
                    # Try basic connectivity test - just check if something responds on the main URL
                    try:
                        url = f"http://localhost:{port}/"
                        response = requests.get(url, timeout=2)
                        if response.status_code < 500:  # Any non-server-error response means it's alive
                            print(f"    ✅ Confirmed {service_config['name']} is running (PID: {pid}, HTTP {response.status_code})")
                            
                            # Register this service as running
                            self.running_services[service_id] = {
                                'pid': pid,
                                'port': port,
                                'started_at': 'pre-existing',
                                'process': None  # We don't have the process object for pre-existing services
                            }
                        else:
                            print(f"    ⚠️  Port {port} responded with HTTP {response.status_code}")
                    except requests.RequestException as e:
                        # Even if HTTP fails, if we found a PID on the port, it's probably the right service
                        print(f"    ✅ Assuming {service_config['name']} is running (PID: {pid}, HTTP check failed but port matches)")
                        self.running_services[service_id] = {
                            'pid': pid,
                            'port': port,
                            'started_at': 'pre-existing',
                            'process': None
                        }
                else:
                    print(f"    ❌ Could not find process for port {port}")
            else:
                print(f"  • {service_config['name']} not detected on port {port}")
    
    def find_process_by_port(self, port):
        """Find the PID of the process using a specific port"""
        try:
            # Method 1: Use psutil (might require permissions)
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.pid:
                    return conn.pid
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        # Method 2: Use lsof command as fallback
        try:
            import subprocess
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                if pids and pids[0].isdigit():
                    return int(pids[0])
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return None

# Global service manager instance
service_manager = ServiceManager()

# HTML template for the dev dashboard
DEV_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MeshAdmin Developer Dashboard</title>
    <style>
        :root {
            --primary-bg: #1a1a1a;
            --secondary-bg: #2d2d2d;
            --accent-bg: #3d3d3d;
            --text-primary: #ffffff;
            --text-secondary: #cccccc;
            --text-muted: #999999;
            --success: #00ff88;
            --warning: #ffaa00;
            --error: #ff4444;
            --border: #444444;
            --hover: #404040;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--primary-bg);
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        .header {
            background: var(--secondary-bg);
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 {
            color: var(--success);
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .header p {
            color: var(--text-secondary);
            margin-top: 0.5rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .service-card {
            background: var(--secondary-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .service-card:hover {
            border-color: var(--success);
            transform: translateY(-2px);
        }
        
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .service-name {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status-running {
            background: var(--success);
            color: var(--primary-bg);
        }
        
        .status-stopped {
            background: var(--error);
            color: var(--text-primary);
        }
        
        .status-unresponsive {
            background: var(--warning);
            color: var(--primary-bg);
        }
        
        .service-description {
            color: var(--text-secondary);
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        
        .service-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        
        .detail-item {
            display: flex;
            justify-content: space-between;
        }
        
        .detail-label {
            color: var(--text-muted);
        }
        
        .detail-value {
            color: var(--text-primary);
            font-weight: 500;
        }
        
        .service-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn:hover {
            transform: translateY(-1px);
        }
        
        .btn-start {
            background: var(--success);
            color: var(--primary-bg);
        }
        
        .btn-stop {
            background: var(--error);
            color: var(--text-primary);
        }
        
        .btn-restart {
            background: var(--warning);
            color: var(--primary-bg);
        }
        
        .btn-open {
            background: var(--accent-bg);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .btn-logs {
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid var(--border);
        }
        
        .port-input {
            background: var(--primary-bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.25rem 0.5rem;
            color: var(--text-primary);
            width: 80px;
            font-size: 0.875rem;
        }
        
        .system-stats {
            background: var(--secondary-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--success);
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--success);
            color: var(--primary-bg);
            border: none;
            cursor: pointer;
            font-size: 1.5rem;
            transition: all 0.3s ease;
            z-index: 1000;
        }
        
        .refresh-btn:hover {
            transform: scale(1.1);
        }
        
        .logs-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            z-index: 2000;
        }
        
        .logs-content {
            background: var(--primary-bg);
            margin: 5% auto;
            padding: 2rem;
            width: 80%;
            height: 80%;
            border-radius: 8px;
            overflow-y: auto;
        }
        
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .close-logs {
            background: var(--error);
            color: var(--text-primary);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .log-entries {
            background: var(--secondary-bg);
            padding: 1rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            line-height: 1.4;
            white-space: pre-wrap;
            height: calc(100% - 100px);
            overflow-y: auto;
        }
        
        .log-entry {
            margin-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }
        
        .log-timestamp {
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        
        .log-message {
            color: var(--text-primary);
            margin-top: 0.25rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .services-grid {
                grid-template-columns: 1fr;
            }
            
            .service-actions {
                flex-direction: column;
            }
            
            .logs-content {
                width: 95%;
                height: 90%;
                margin: 2.5% auto;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 MeshAdmin Developer Dashboard</h1>
        <p>Unified control panel for all development services and applications</p>
    </div>
    
    <div class="container">
        <div class="system-stats">
            <h2 style="margin-bottom: 1rem; color: var(--text-primary);">System Overview</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="running-services">0</div>
                    <div class="stat-label">Running Services</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="total-services">{{ services|length }}</div>
                    <div class="stat-label">Total Services</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="system-load">--</div>
                    <div class="stat-label">System Load</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="memory-usage">--</div>
                    <div class="stat-label">Memory Usage</div>
                </div>
            </div>
        </div>
        
        <div class="services-grid">
            {% for service_id, service in services.items() %}
            <div class="service-card" data-service="{{ service_id }}">
                <div class="service-header">
                    <div class="service-name">{{ service.name }}</div>
                    <div class="status-badge status-stopped" id="status-{{ service_id }}">Stopped</div>
                </div>
                
                <div class="service-description">{{ service.description }}</div>
                
                <div class="service-details">
                    <div class="detail-item">
                        <span class="detail-label">Default Port:</span>
                        <span class="detail-value">{{ service.default_port }}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">PID:</span>
                        <span class="detail-value" id="pid-{{ service_id }}">--</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Current Port:</span>
                        <span class="detail-value" id="port-{{ service_id }}">--</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Script:</span>
                        <span class="detail-value">{{ service.script|basename }}</span>
                    </div>
                </div>
                
                <div class="service-actions">
                    <button class="btn btn-start" onclick="startService('{{ service_id }}')">
                        ▶ Start
                    </button>
                    <button class="btn btn-stop" onclick="stopService('{{ service_id }}')">
                        ⏹ Stop
                    </button>
                    <button class="btn btn-restart" onclick="restartService('{{ service_id }}')">
                        🔄 Restart
                    </button>
                    <input type="number" class="port-input" id="port-input-{{ service_id }}" 
                           value="{{ service.default_port }}" min="1000" max="65535">
                    <a class="btn btn-open" id="open-{{ service_id }}" href="#" target="_blank" style="display: none;">
                        🌐 Open
                    </a>
                    <button class="btn btn-logs" onclick="showLogs('{{ service_id }}')">
                        📋 Logs
                    </button>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <button class="refresh-btn" onclick="refreshAll()" title="Refresh Status">
        🔄
    </button>
    
    <!-- Logs Modal -->
    <div class="logs-modal" id="logs-modal">
        <div class="logs-content">
            <div class="logs-header">
                <h3 id="logs-title">Service Logs</h3>
                <button class="close-logs" onclick="closeLogs()">Close</button>
            </div>
            <div class="log-entries" id="log-entries"></div>
        </div>
    </div>
    
    <script>
        // Auto-refresh status every 5 seconds
        setInterval(refreshAll, 5000);
        
        // Initial load
        document.addEventListener('DOMContentLoaded', refreshAll);
        
        async function refreshAll() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                let runningCount = 0;
                
                // Update service statuses
                for (const [serviceId, status] of Object.entries(data.services)) {
                    updateServiceStatus(serviceId, status);
                    if (status.status === 'running') runningCount++;
                }
                
                // Update system stats
                document.getElementById('running-services').textContent = runningCount;
                document.getElementById('system-load').textContent = data.system.load.toFixed(1);
                document.getElementById('memory-usage').textContent = data.system.memory + '%';
                
            } catch (error) {
                console.error('Failed to refresh status:', error);
            }
        }
        
        function updateServiceStatus(serviceId, status) {
            const statusBadge = document.getElementById(`status-${serviceId}`);
            const pidElement = document.getElementById(`pid-${serviceId}`);
            const portElement = document.getElementById(`port-${serviceId}`);
            const openButton = document.getElementById(`open-${serviceId}`);
            
            statusBadge.className = 'status-badge';
            
            if (status.status === 'running') {
                statusBadge.classList.add('status-running');
                statusBadge.textContent = status.responsive ? 'Running' : 'Unresponsive';
                if (!status.responsive) {
                    statusBadge.classList.remove('status-running');
                    statusBadge.classList.add('status-unresponsive');
                }
                
                pidElement.textContent = status.pid;
                portElement.textContent = status.port;
                
                // Update open button
                if (status.port) {
                    openButton.href = `http://localhost:${status.port}`;
                    openButton.style.display = 'inline-flex';
                }
            } else {
                statusBadge.classList.add('status-stopped');
                statusBadge.textContent = 'Stopped';
                pidElement.textContent = '--';
                portElement.textContent = '--';
                openButton.style.display = 'none';
            }
        }
        
        async function startService(serviceId) {
            const portInput = document.getElementById(`port-input-${serviceId}`);
            const port = portInput.value;
            
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service_id: serviceId, port: parseInt(port) })
                });
                
                const result = await response.json();
                if (result.success) {
                    setTimeout(refreshAll, 1000); // Refresh after a delay
                } else {
                    alert(`Failed to start service: ${result.error}`);
                }
            } catch (error) {
                alert(`Error starting service: ${error.message}`);
            }
        }
        
        async function stopService(serviceId) {
            try {
                const response = await fetch('/api/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service_id: serviceId })
                });
                
                const result = await response.json();
                if (result.success) {
                    setTimeout(refreshAll, 1000); // Refresh after a delay
                } else {
                    alert(`Failed to stop service: ${result.error}`);
                }
            } catch (error) {
                alert(`Error stopping service: ${error.message}`);
            }
        }
        
        async function restartService(serviceId) {
            const portInput = document.getElementById(`port-input-${serviceId}`);
            const port = portInput.value;
            
            try {
                const response = await fetch('/api/restart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service_id: serviceId, port: parseInt(port) })
                });
                
                const result = await response.json();
                if (result.success) {
                    setTimeout(refreshAll, 2000); // Refresh after a longer delay for restart
                } else {
                    alert(`Failed to restart service: ${result.error}`);
                }
            } catch (error) {
                alert(`Error restarting service: ${error.message}`);
            }
        }
        
        async function showLogs(serviceId) {
            try {
                const response = await fetch(`/api/logs/${serviceId}`);
                const logs = await response.json();
                
                document.getElementById('logs-title').textContent = `${SERVICES[serviceId]?.name || serviceId} - Logs`;
                
                const logEntries = document.getElementById('log-entries');
                logEntries.innerHTML = '';
                
                if (logs.length === 0) {
                    logEntries.innerHTML = '<div style="color: var(--text-muted);">No logs available</div>';
                } else {
                    logs.forEach(log => {
                        const logDiv = document.createElement('div');
                        logDiv.className = 'log-entry';
                        logDiv.innerHTML = `
                            <div class="log-timestamp">${log.timestamp}</div>
                            <div class="log-message">${log.message}</div>
                        `;
                        logEntries.appendChild(logDiv);
                    });
                    
                    // Scroll to bottom
                    logEntries.scrollTop = logEntries.scrollHeight;
                }
                
                document.getElementById('logs-modal').style.display = 'block';
                
            } catch (error) {
                alert(`Error fetching logs: ${error.message}`);
            }
        }
        
        function closeLogs() {
            document.getElementById('logs-modal').style.display = 'none';
        }
        
        // Close logs modal when clicking outside
        document.getElementById('logs-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLogs();
            }
        });
        
        // Service configurations for frontend use
        const SERVICES = {{ services|tojson }};
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template_string(DEV_DASHBOARD_TEMPLATE, services=SERVICES)

@app.route('/api/status')
def api_status():
    """Get status of all services and system stats"""
    service_statuses = {}
    
    for service_id in SERVICES:
        service_statuses[service_id] = service_manager.get_service_status(service_id)
    
    # Get system stats
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else cpu_percent / 100
    
    return jsonify({
        'services': service_statuses,
        'system': {
            'load': load_avg,
            'memory': memory.percent,
            'cpu': cpu_percent
        }
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start a service"""
    data = request.get_json()
    service_id = data.get('service_id')
    port = data.get('port')
    
    if not service_id:
        return jsonify({'success': False, 'error': 'service_id required'})
    
    result = service_manager.start_service(service_id, port)
    return jsonify(result)

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop a service"""
    data = request.get_json()
    service_id = data.get('service_id')
    
    if not service_id:
        return jsonify({'success': False, 'error': 'service_id required'})
    
    result = service_manager.stop_service(service_id)
    return jsonify(result)

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """Restart a service"""
    data = request.get_json()
    service_id = data.get('service_id')
    port = data.get('port')
    
    if not service_id:
        return jsonify({'success': False, 'error': 'service_id required'})
    
    result = service_manager.restart_service(service_id, port)
    return jsonify(result)

@app.route('/api/logs/<service_id>')
def api_logs(service_id):
    """Get logs for a service"""
    logs = service_manager.get_service_logs(service_id)
    return jsonify(logs)

def cleanup_on_exit():
    """Cleanup function to stop all managed services on exit"""
    print("\nCleaning up managed services...")
    for service_id in list(service_manager.running_services.keys()):
        process_info = service_manager.running_services[service_id]
        # Only stop services that were started by this dashboard (have a process object)
        if process_info.get('process') is not None:
            print(f"Stopping {service_id} (started by dashboard)...")
            service_manager.stop_service(service_id)
        else:
            print(f"Leaving {service_id} running (pre-existing service)...")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    cleanup_on_exit()
    sys.exit(0)

if __name__ == '__main__':
    # Suppress Flask access logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 MeshAdmin Developer Dashboard")
    print("=" * 50)
    print(f"Starting on http://localhost:5555")
    print("This dashboard provides unified control for all development services.")
    print("\nAvailable services:")
    for service_id, service in SERVICES.items():
        print(f"  • {service['name']} (default port: {service['default_port']})")
    print("\nPress Ctrl+C to stop the dashboard and all managed services.")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5555, debug=False, threaded=True)
    finally:
        cleanup_on_exit()

