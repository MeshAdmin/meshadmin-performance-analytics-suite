from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from functools import wraps
from datetime import datetime, timedelta
import json
import random

from app import db, csrf
from models import Dashboard, Widget, Log, Metric, Alert, AlertSeverity

api_bp = Blueprint('api', __name__)

# Exempt API routes from CSRF protection when using token authentication
@api_bp.after_request
def set_csrf_token(response):
    response.set_cookie('csrf_token', generate_csrf())
    return response

def api_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for API token in request
        token = request.headers.get('X-API-Token')
        if token:
            # Validate token (implement this part as needed)
            pass
        elif not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/health')
def health_check():
    """API endpoint for health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })

@api_bp.route('/dashboards/<int:dashboard_id>/data')
@login_required
def get_dashboard_data(dashboard_id):
    """Get data for all widgets in a dashboard"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check access
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    # Get time range parameters
    time_range = request.args.get('time_range', '24h')
    now = datetime.utcnow()
    
    if time_range == 'custom':
        # Parse custom time range
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        if start_time and end_time:
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            # Default to last 24 hours
            end_time = now
            start_time = end_time - timedelta(hours=24)
    else:
        # Parse standard time ranges
        end_time = now
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = end_time - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = end_time - timedelta(days=days)
        else:
            # Default to 24 hours
            start_time = end_time - timedelta(hours=24)
    
    # Get widgets for this dashboard
    widgets = Widget.query.filter_by(dashboard_id=dashboard_id).all()
    
    # Get data for each widget
    widgets_data = []
    
    for widget in widgets:
        widget_data = {
            'id': widget.id,
            'name': widget.name,
            'type': widget.widget_type,
            'data_source': widget.data_source.value,
            'position_x': widget.position_x,
            'position_y': widget.position_y,
            'width': widget.width,
            'height': widget.height,
            'configuration': json.loads(widget.configuration),
            'data': get_widget_data(widget, start_time, end_time)
        }
        widgets_data.append(widget_data)
    
    # Get summary data for the dashboard
    summary = get_summary_data(start_time, end_time)
    
    return jsonify({
        'dashboard_id': dashboard_id,
        'widgets': widgets_data,
        'summary': summary,
        'time_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        }
    })

def get_widget_data(widget, start_time, end_time):
    """Get sample data for a specific widget"""
    widget_type = widget.widget_type
    widget_config = json.loads(widget.configuration)
    
    # Based on widget type, return appropriate data structure
    if widget_type == 'line-chart':
        return get_line_chart_data(widget, start_time, end_time)
    elif widget_type == 'bar-chart':
        return get_bar_chart_data(widget, start_time, end_time)
    elif widget_type == 'pie-chart':
        return get_pie_chart_data(widget, start_time, end_time)
    elif widget_type == 'gauge':
        return get_gauge_data(widget, start_time, end_time)
    elif widget_type == 'stat':
        return get_stat_data(widget, start_time, end_time)
    elif widget_type == 'table':
        return get_table_data(widget, start_time, end_time)
    elif widget_type == 'alert-list':
        return get_alerts_data(widget, start_time, end_time)
    
    # Default empty response
    return {'data': []}

def get_line_chart_data(widget, start_time, end_time):
    """Generate sample line chart data"""
    # Calculate number of points based on time range
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600
    
    if hours <= 24:
        # Hourly data points
        points = int(hours) + 1
        interval = timedelta(hours=1)
        format_str = '%H:%M'
    elif hours <= 168:  # 7 days
        # Daily data points
        points = int(hours / 24) + 1
        interval = timedelta(days=1)
        format_str = '%m/%d'
    else:
        # Weekly data points
        points = min(20, int(hours / 168) + 1)
        interval = timedelta(days=7)
        format_str = '%m/%d'
    
    # Generate time points
    time_points = []
    current_time = start_time
    for _ in range(points):
        time_points.append(current_time.strftime(format_str))
        current_time += interval
    
    # For log volume, generate random data that increases over time
    if widget.data_source.value == 'SYSLOG' and widget.name == 'Log Volume':
        base_value = 300
        values = []
        for i in range(points):
            # Generate increasing values with some randomness
            value = base_value + (i * 20) + random.randint(-50, 100)
            values.append(max(0, value))  # Ensure no negative values
        
        return {
            'time_points': time_points,
            'values': values
        }
    
    # For other metrics, generate random data
    values = []
    for _ in range(points):
        values.append(random.randint(10, 1000))
    
    return {
        'time_points': time_points,
        'values': values
    }

def get_bar_chart_data(widget, start_time, end_time):
    """Generate sample bar chart data"""
    # Similar structure to line chart
    return get_line_chart_data(widget, start_time, end_time)

def get_pie_chart_data(widget, start_time, end_time):
    """Generate sample pie chart data"""
    data_source = widget.data_source.value
    
    if data_source == 'SYSLOG':
        labels = ['Error', 'Warning', 'Info', 'Debug']
        values = [random.randint(5, 30), random.randint(20, 60), 
                  random.randint(100, 300), random.randint(50, 200)]
    elif data_source == 'SNMP':
        labels = ['Critical', 'Major', 'Minor', 'Warning', 'Normal']
        values = [random.randint(1, 10), random.randint(5, 20), 
                  random.randint(10, 30), random.randint(20, 50), 
                  random.randint(100, 300)]
    else:
        # Generic data
        labels = ['Type A', 'Type B', 'Type C', 'Type D']
        values = [random.randint(10, 100), random.randint(20, 100), 
                  random.randint(30, 100), random.randint(40, 100)]
    
    return {
        'labels': labels,
        'values': values
    }

def get_gauge_data(widget, start_time, end_time):
    """Generate sample gauge data"""
    # For different metrics, use different ranges
    if widget.data_source.value == 'SYSLOG':
        value = random.randint(60, 95)
        min_val = 0
        max_val = 100
        thresholds = [
            {'value': 80, 'color': 'green'},
            {'value': 90, 'color': 'yellow'},
            {'value': 95, 'color': 'red'}
        ]
    elif widget.data_source.value == 'SNMP':
        value = random.randint(20, 80)
        min_val = 0
        max_val = 100
        thresholds = [
            {'value': 30, 'color': 'green'},
            {'value': 60, 'color': 'yellow'},
            {'value': 80, 'color': 'red'}
        ]
    else:
        value = random.randint(0, 100)
        min_val = 0
        max_val = 100
        thresholds = [
            {'value': 33, 'color': 'green'},
            {'value': 66, 'color': 'yellow'},
            {'value': 100, 'color': 'red'}
        ]
    
    return {
        'value': value,
        'min': min_val,
        'max': max_val,
        'thresholds': thresholds,
        'unit': '%'
    }

def get_stat_data(widget, start_time, end_time):
    """Generate sample statistics data"""
    stats = []
    
    if widget.data_source.value == 'SYSLOG':
        stats.append({
            'title': 'Total Logs',
            'value': random.randint(1000, 10000),
            'change': random.randint(-20, 50),
            'icon': 'fa-file-alt'
        })
        stats.append({
            'title': 'Errors',
            'value': random.randint(10, 500),
            'change': random.randint(-30, 30),
            'icon': 'fa-exclamation-circle'
        })
        stats.append({
            'title': 'Warnings',
            'value': random.randint(100, 1000),
            'change': random.randint(-10, 40),
            'icon': 'fa-exclamation-triangle'
        })
    elif widget.data_source.value == 'SNMP':
        stats.append({
            'title': 'Traps',
            'value': random.randint(50, 1000),
            'change': random.randint(-15, 25),
            'icon': 'fa-network-wired'
        })
        stats.append({
            'title': 'Critical Alerts',
            'value': random.randint(0, 20),
            'change': random.randint(-5, 15),
            'icon': 'fa-bell'
        })
    else:
        stats.append({
            'title': 'Devices',
            'value': random.randint(10, 200),
            'change': random.randint(-5, 10),
            'icon': 'fa-server'
        })
        stats.append({
            'title': 'Metrics',
            'value': random.randint(500, 5000),
            'change': random.randint(-10, 30),
            'icon': 'fa-chart-line'
        })
    
    return {'stats': stats}

def get_table_data(widget, start_time, end_time):
    """Generate sample table data"""
    columns = []
    rows = []
    
    if widget.data_source.value == 'SYSLOG':
        columns = ['Timestamp', 'Device', 'Severity', 'Message']
        severities = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
        devices = ['Router-1', 'Switch-3', 'Firewall-2', 'Server-5', 'Core-Switch']
        
        for _ in range(10):
            timestamp = (start_time + timedelta(seconds=random.randint(0, int((end_time - start_time).total_seconds())))).strftime('%Y-%m-%d %H:%M:%S')
            device = random.choice(devices)
            severity = random.choice(severities)
            message = f"Sample log message for {device}"
            
            rows.append([timestamp, device, severity, message])
    
    elif widget.data_source.value == 'SNMP':
        columns = ['Timestamp', 'Device', 'OID', 'Value']
        devices = ['Router-1', 'Switch-3', 'Firewall-2', 'Server-5', 'Core-Switch']
        oids = ['.1.3.6.1.2.1.1.3.0', '.1.3.6.1.2.1.1.5.0', '.1.3.6.1.2.1.4.3.0', '.1.3.6.1.2.1.4.10.0']
        
        for _ in range(10):
            timestamp = (start_time + timedelta(seconds=random.randint(0, int((end_time - start_time).total_seconds())))).strftime('%Y-%m-%d %H:%M:%S')
            device = random.choice(devices)
            oid = random.choice(oids)
            value = str(random.randint(1, 1000))
            
            rows.append([timestamp, device, oid, value])
    
    else:
        columns = ['ID', 'Name', 'Type', 'Value']
        for i in range(10):
            rows.append([
                str(i + 1),
                f"Item {i+1}",
                random.choice(['Type A', 'Type B', 'Type C']),
                str(random.randint(1, 1000))
            ])
    
    return {
        'columns': columns,
        'rows': rows
    }

def get_alerts_data(widget, start_time, end_time):
    """Generate sample alerts data"""
    alerts = []
    severities = list(AlertSeverity)
    
    # Get actual alerts from database if any
    db_alerts = Alert.query.filter(
        Alert.timestamp.between(start_time, end_time)
    ).order_by(Alert.timestamp.desc()).limit(10).all()
    
    if db_alerts:
        for alert in db_alerts:
            alerts.append({
                'id': alert.id,
                'timestamp': alert.timestamp.isoformat(),
                'severity': alert.severity.value,
                'message': alert.message,
                'acknowledged': alert.acknowledged,
                'resolved': alert.resolved
            })
    else:
        # Generate sample alerts
        devices = ['Router-1', 'Switch-3', 'Firewall-2', 'Server-5', 'Core-Switch']
        alert_messages = [
            'High CPU utilization detected',
            'Memory usage exceeded threshold',
            'Interface down',
            'Disk space warning',
            'Authentication failure',
            'SNMP trap received',
            'Service stopped',
            'Network connectivity issue'
        ]
        
        for i in range(10):
            timestamp = (end_time - timedelta(minutes=random.randint(1, int((end_time - start_time).total_seconds() / 60)))).isoformat()
            severity = random.choice(severities)
            device = random.choice(devices)
            message = f"{random.choice(alert_messages)} on {device}"
            
            alerts.append({
                'id': i + 1,
                'timestamp': timestamp,
                'severity': severity.value,
                'message': message,
                'acknowledged': random.random() > 0.6,
                'resolved': random.random() > 0.8
            })
    
    return {'alerts': alerts}

def get_summary_data(start_time, end_time):
    """Get summary statistics for the dashboard"""
    # For now, return basic stats
    return {
        'total_logs': random.randint(1000, 10000),
        'total_metrics': random.randint(5000, 50000),
        'active_alerts': random.randint(1, 20),
        'devices_count': random.randint(10, 100)
    }