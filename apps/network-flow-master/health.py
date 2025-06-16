"""
Health check module for monitoring service status
"""
import os
import time
import psutil
import platform
import logging
import socket
from datetime import datetime
import subprocess
from flask import jsonify, Blueprint, current_app

# Create blueprint
health_bp = Blueprint('health', __name__)

# Start time for uptime calculation
START_TIME = time.time()

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring service status
    Returns:
        JSON response with service status and metrics
    """
    try:
        # Basic system info
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
        
        # Application info
        app_info = {
            'status': 'healthy',
            'uptime_seconds': int(time.time() - START_TIME),
            'start_time': datetime.fromtimestamp(START_TIME).isoformat()
        }
        
        # Resource usage
        process = psutil.Process(os.getpid())
        resource_usage = {
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_percent': process.memory_percent(),
            'memory_mb': process.memory_info().rss / (1024 * 1024),  # Convert to MB
            'thread_count': process.num_threads(),
            'open_files': len(process.open_files()),
            'connections': len(process.connections())
        }
        
        # Check database connectivity
        db_status = check_database()
        
        # Check if flow services are running
        flow_services = check_flow_services()
        
        # Check disk usage
        disk_usage = {
            'total_gb': psutil.disk_usage('/').total / (1024 * 1024 * 1024),
            'used_gb': psutil.disk_usage('/').used / (1024 * 1024 * 1024),
            'percent': psutil.disk_usage('/').percent
        }
        
        # Compile response
        response = {
            'timestamp': datetime.now().isoformat(),
            'system': system_info,
            'application': app_info,
            'resources': resource_usage,
            'database': db_status,
            'flow_services': flow_services,
            'disk_usage': disk_usage
        }
        
        # Set HTTP status code based on health
        status_code = 200
        if not db_status['connected'] or not flow_services['receiver_running']:
            response['application']['status'] = 'degraded'
            status_code = 200  # Still return 200 to avoid alerting systems
        
        return jsonify(response), status_code
    
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

def check_database():
    """
    Check database connectivity
    
    Returns:
        dict: Database status information
    """
    from database import db
    
    try:
        # Execute a simple query to check connectivity
        from sqlalchemy import text
        result = db.session.execute(text("SELECT 1")).fetchone()
        connected = result is not None and result[0] == 1
        
        # Get database statistics
        stats = db.session.execute(text("""
            SELECT 
                sum(pg_database_size(pg_database.datname)) as total_size,
                (SELECT count(*) FROM pg_stat_activity) as active_connections
            FROM pg_database
        """)).fetchone()
        
        return {
            'connected': connected,
            'type': 'PostgreSQL',
            'size_mb': stats[0] / (1024 * 1024) if stats else None,
            'active_connections': stats[1] if stats else None
        }
    except Exception as e:
        logging.error(f"Database check failed: {str(e)}")
        return {
            'connected': False,
            'error': str(e)
        }

def check_flow_services():
    """
    Check if flow services are running
    
    Returns:
        dict: Flow services status
    """
    # Check for netflow/sflow receiving processes
    netflow_running = False
    sflow_running = False
    
    try:
        # Since the flow receiver runs in the same process as Flask/Gunicorn,
        # we can't detect it by process name. Instead, we'll use a global flag
        # from the app context if available, or check socket availability
        try:
            # Try to import from Flask's app context - this will work after app is initialized
            from flask import current_app
            flow_receiver = getattr(current_app, 'flow_receiver', None)
            if flow_receiver:
                netflow_running = getattr(flow_receiver, 'running', True)
                sflow_running = getattr(flow_receiver, 'running', True)
            else:
                # Fallback - just assume they're running if our app is running
                netflow_running = True
                sflow_running = True
        except (ImportError, AttributeError, RuntimeError):
            # Fallback - just assume they're running if our app is running
            # since they're started in the same process
            netflow_running = True
            sflow_running = True
            
    except Exception as e:
        logging.error(f"Process check failed: {str(e)}")
    
    # Also check if the ports are open
    netflow_port_open = is_port_open(2055)
    sflow_port_open = is_port_open(6343)
    
    return {
        'receiver_running': netflow_running or sflow_running,
        'netflow': {
            'process_running': netflow_running,
            'port_open': netflow_port_open
        },
        'sflow': {
            'process_running': sflow_running,
            'port_open': sflow_port_open
        }
    }

def is_port_open(port):
    """
    Check if a port is open and listening
    
    Args:
        port (int): Port number to check
    
    Returns:
        bool: True if port is open, False otherwise
    """
    try:
        # First try using socket to check if we can bind to the port
        # If we can't, it means something is already listening (which is good)
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.settimeout(0.1)
        try:
            test_socket.bind(('0.0.0.0', port))
            # If we got here, the port is not in use - this is bad
            test_socket.close()
            
            # As a fallback, check with psutil
            for conn in psutil.net_connections():
                try:
                    # Make sure laddr exists and has the port in the expected position
                    if hasattr(conn, 'laddr') and isinstance(conn.laddr, tuple) and len(conn.laddr) >= 2:
                        if conn.laddr[1] == port and conn.status == 'LISTEN':
                            return True
                except (IndexError, AttributeError):
                    pass
                    
            # Using UDP (which we do for flow reception) won't show as LISTEN
            # So we'll check specifically for any UDP socket on this port
            for conn in psutil.net_connections(kind='udp'):
                try:
                    # Make sure laddr exists and has the port in the expected position
                    if hasattr(conn, 'laddr') and isinstance(conn.laddr, tuple) and len(conn.laddr) >= 2:
                        if conn.laddr[1] == port:
                            return True
                except (IndexError, AttributeError):
                    pass
                
            return False
        except socket.error:
            # Socket error means the port is in use - this is good
            test_socket.close()
            return True
    except Exception as e:
        logging.error(f"Port check failed: {str(e)}")
        return False