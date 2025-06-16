from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user
import json
from datetime import datetime, timedelta
import math
import random

from app import db
from models import Dashboard, Widget, Organization, Log, Metric, Device, Site

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Show default dashboard or first available dashboard"""
    # Try to find the default dashboard
    default_dashboard = Dashboard.query.filter_by(
        user_id=current_user.id, 
        is_default=True
    ).first()
    
    # If no default, get the first dashboard for this user
    if not default_dashboard:
        default_dashboard = Dashboard.query.filter_by(
            user_id=current_user.id
        ).first()
    
    # If user has no dashboards, get a shared dashboard from their organization
    if not default_dashboard:
        orgs = current_user.organizations
        for org in orgs:
            default_dashboard = Dashboard.query.filter_by(
                organization_id=org.id,
                is_default=True
            ).first()
            if default_dashboard:
                break
    
    # If still no dashboard, create a default one
    if not default_dashboard:
        default_dashboard = create_default_dashboard()
    
    # Get all dashboards available to the user
    dashboards = get_available_dashboards()
    
    # Get organizations for the dashboard selector
    organizations = current_user.organizations
    
    return render_template('dashboard.html',
                          dashboard=default_dashboard,
                          dashboards=dashboards,
                          organizations=organizations)

@dashboard_bp.route('/<int:dashboard_id>')
@login_required
def show(dashboard_id):
    """Show a specific dashboard"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check access to the dashboard
    if dashboard.user_id and dashboard.user_id != current_user.id:
        # Check if it's an organizational dashboard
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            abort(403)
    
    # Get all dashboards available to the user
    dashboards = get_available_dashboards()
    
    # Get organizations for the dashboard selector
    organizations = current_user.organizations
    
    return render_template('dashboard.html',
                          dashboard=dashboard,
                          dashboards=dashboards,
                          organizations=organizations)

@dashboard_bp.route('/api/dashboards', methods=['POST'])
@login_required
def api_create_dashboard():
    """API endpoint to create a new dashboard"""
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Dashboard name is required'}), 400
    
    # Create dashboard
    dashboard = Dashboard(
        name=data.get('name'),
        description=data.get('description', ''),
        layout=json.dumps([]),  # Start with empty layout
        is_default=data.get('is_default', False),
        user_id=current_user.id,
        organization_id=data.get('organization_id')
    )
    
    # If setting as default, unset any existing default dashboards
    if dashboard.is_default:
        if dashboard.organization_id:
            Dashboard.query.filter_by(
                organization_id=dashboard.organization_id,
                is_default=True
            ).update({'is_default': False})
        else:
            Dashboard.query.filter_by(
                user_id=current_user.id,
                is_default=True
            ).update({'is_default': False})
    
    db.session.add(dashboard)
    db.session.commit()
    
    return jsonify({
        'id': dashboard.id,
        'name': dashboard.name,
        'status': 'created'
    })

@dashboard_bp.route('/api/dashboards/<int:dashboard_id>', methods=['PUT'])
@login_required
def api_update_dashboard(dashboard_id):
    """API endpoint to update a dashboard"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check access
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        dashboard.name = data['name']
    
    if 'description' in data:
        dashboard.description = data['description']
    
    if 'is_default' in data and data['is_default']:
        # Unset any existing default dashboards
        if dashboard.organization_id:
            Dashboard.query.filter_by(
                organization_id=dashboard.organization_id,
                is_default=True
            ).update({'is_default': False})
        else:
            Dashboard.query.filter_by(
                user_id=current_user.id,
                is_default=True
            ).update({'is_default': False})
        
        dashboard.is_default = True
    
    if 'organization_id' in data:
        dashboard.organization_id = data['organization_id']
    
    dashboard.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'id': dashboard.id,
        'name': dashboard.name,
        'status': 'updated'
    })

@dashboard_bp.route('/api/dashboards/<int:dashboard_id>', methods=['DELETE'])
@login_required
def api_delete_dashboard(dashboard_id):
    """API endpoint to delete a dashboard"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check access
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    # Get dashboard info for response
    dashboard_name = dashboard.name
    
    # Delete associated widgets first
    Widget.query.filter_by(dashboard_id=dashboard_id).delete()
    
    # Delete the dashboard
    db.session.delete(dashboard)
    db.session.commit()
    
    return jsonify({
        'status': 'deleted',
        'message': f'Dashboard {dashboard_name} deleted successfully'
    })

@dashboard_bp.route('/api/dashboards/<int:dashboard_id>/layout', methods=['PUT'])
@login_required
def save_dashboard_layout(dashboard_id):
    """Save dashboard layout"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check access
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update the layout
    if 'layout' in data:
        dashboard.layout = json.dumps(data['layout'])
        dashboard.updated_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'id': dashboard.id,
        'status': 'layout_updated'
    })

@dashboard_bp.route('/api/dashboards/<int:dashboard_id>/data')
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

@dashboard_bp.route('/api/widgets', methods=['POST'])
@login_required
def api_create_widget():
    """API endpoint to create a new widget"""
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Widget name is required'}), 400
        
    if not data.get('widget_type'):
        return jsonify({'error': 'Widget type is required'}), 400
        
    if not data.get('data_source'):
        return jsonify({'error': 'Data source is required'}), 400
        
    if not data.get('dashboard_id'):
        return jsonify({'error': 'Dashboard ID is required'}), 400
    
    # Check access to dashboard
    dashboard_id = data.get('dashboard_id')
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    # Parse size
    size = data.get('size', '1x1').split('x')
    width = int(size[0])
    height = int(size[1]) if len(size) > 1 else 1
    
    # Create widget
    widget = Widget(
        name=data.get('name'),
        widget_type=data.get('widget_type'),
        data_source=data.get('data_source'),
        configuration=json.dumps(data.get('configuration', {})),
        position_x=data.get('position_x', 0),
        position_y=data.get('position_y', 0),
        width=width,
        height=height,
        dashboard_id=dashboard_id
    )
    
    db.session.add(widget)
    db.session.commit()
    
    return jsonify({
        'id': widget.id,
        'name': widget.name,
        'status': 'created'
    })

@dashboard_bp.route('/api/widgets/<int:widget_id>', methods=['PUT'])
@login_required
def api_update_widget(widget_id):
    """API endpoint to update a widget"""
    widget = Widget.query.get_or_404(widget_id)
    
    # Check access to dashboard
    dashboard = Dashboard.query.get_or_404(widget.dashboard_id)
    
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        widget.name = data['name']
    
    if 'widget_type' in data:
        widget.widget_type = data['widget_type']
    
    if 'data_source' in data:
        widget.data_source = data['data_source']
    
    if 'configuration' in data:
        widget.configuration = json.dumps(data['configuration'])
    
    if 'position_x' in data:
        widget.position_x = data['position_x']
    
    if 'position_y' in data:
        widget.position_y = data['position_y']
    
    if 'size' in data:
        size = data['size'].split('x')
        widget.width = int(size[0])
        widget.height = int(size[1]) if len(size) > 1 else 1
    
    db.session.commit()
    
    return jsonify({
        'id': widget.id,
        'name': widget.name,
        'status': 'updated'
    })

@dashboard_bp.route('/api/widgets/<int:widget_id>', methods=['DELETE'])
@login_required
def api_delete_widget(widget_id):
    """API endpoint to delete a widget"""
    widget = Widget.query.get_or_404(widget_id)
    
    # Check access to dashboard
    dashboard = Dashboard.query.get_or_404(widget.dashboard_id)
    
    if dashboard.user_id and dashboard.user_id != current_user.id:
        if not dashboard.organization_id or dashboard.organization not in current_user.organizations:
            return jsonify({'error': 'Permission denied'}), 403
    
    # Get widget info for response
    widget_name = widget.name
    
    # Delete the widget
    db.session.delete(widget)
    db.session.commit()
    
    return jsonify({
        'status': 'deleted',
        'message': f'Widget {widget_name} deleted successfully'
    })

# Helper functions
def get_available_dashboards():
    """Get all dashboards available to the current user"""
    # Get user's personal dashboards
    user_dashboards = Dashboard.query.filter_by(user_id=current_user.id).all()
    
    # Get dashboards from user's organizations
    org_dashboards = []
    for org in current_user.organizations:
        org_dash = Dashboard.query.filter_by(organization_id=org.id).all()
        org_dashboards.extend(org_dash)
    
    # Combine and remove duplicates
    all_dashboards = user_dashboards + [d for d in org_dashboards if d not in user_dashboards]
    
    return all_dashboards

def create_default_dashboard():
    """Create a default dashboard for a new user"""
    dashboard = Dashboard(
        name="Main Dashboard",
        description="Default dashboard with system overview",
        layout=json.dumps([]),
        is_default=True,
        user_id=current_user.id
    )
    
    db.session.add(dashboard)
    db.session.commit()
    
    # Create some default widgets
    widgets = [
        {
            'name': 'System Overview',
            'widget_type': 'stat',
            'data_source': 'SYSLOG',
            'configuration': json.dumps({}),
            'position_x': 0,
            'position_y': 0,
            'width': 2,
            'height': 1,
            'dashboard_id': dashboard.id
        },
        {
            'name': 'Log Volume',
            'widget_type': 'line-chart',
            'data_source': 'SYSLOG',
            'configuration': json.dumps({
                'metric': 'count',
                'group_by': 'hour'
            }),
            'position_x': 0,
            'position_y': 1,
            'width': 2,
            'height': 1,
            'dashboard_id': dashboard.id
        },
        {
            'name': 'Recent Alerts',
            'widget_type': 'alert-list',
            'data_source': 'SYSLOG',
            'configuration': json.dumps({
                'limit': 10,
                'severity': ['ERROR', 'CRITICAL']
            }),
            'position_x': 2,
            'position_y': 0,
            'width': 1,
            'height': 2,
            'dashboard_id': dashboard.id
        }
    ]
    
    for widget_data in widgets:
        widget = Widget(**widget_data)
        db.session.add(widget)
    
    db.session.commit()
    return dashboard

def get_widget_data(widget, start_time, end_time):
    """Get data for a specific widget based on its type and data source"""
    widget_config = json.loads(widget.configuration)
    
    # Route to appropriate data fetcher based on data source
    if widget.data_source.value == 'SYSLOG':
        return get_syslog_data(widget_config, start_time, end_time)
    elif widget.data_source.value == 'SNMP':
        return get_snmp_data(widget_config, start_time, end_time)
    elif widget.data_source.value == 'NETFLOW':
        return get_netflow_data(widget_config, start_time, end_time, widget.widget_type)
    elif widget.data_source.value == 'SFLOW':
        return get_sflow_data(widget_config, start_time, end_time, widget.widget_type)
    elif widget.data_source.value == 'WINDOWS_EVENTS':
        return get_windows_events_data(widget_config, start_time, end_time)
    elif widget.data_source.value == 'OTEL':
        return get_otel_data(widget_config, start_time, end_time, widget.widget_type)
    
    # For specific widget types with custom data sources
    if widget.widget_type == 'alert-list':
        return get_alerts_data(widget_config, start_time, end_time)
    elif widget.widget_type in ['line-chart', 'bar-chart', 'gauge']:
        return get_performance_data(widget_config, start_time, end_time, widget.widget_type)
    
    # Default empty response
    return {'data': []}

def get_summary_data(start_time, end_time):
    """Get summary statistics for the dashboard"""
    # Organizations user has access to
    orgs = current_user.organizations
    org_ids = [org.id for org in orgs]
    
    # Sites for these organizations
    sites = Site.query.filter(Site.organization_id.in_(org_ids)).all()
    site_ids = [site.id for site in sites]
    
    # Devices for these sites
    devices = Device.query.filter(Device.site_id.in_(site_ids)).all()
    device_ids = [device.id for device in devices]
    
    # Count logs in this period
    log_count = Log.query.filter(
        Log.device_id.in_(device_ids),
        Log.timestamp >= start_time,
        Log.timestamp <= end_time
    ).count()
    
    # Count metrics in this period
    metric_count = Metric.query.filter(
        Metric.device_id.in_(device_ids),
        Metric.timestamp >= start_time,
        Metric.timestamp <= end_time
    ).count()
    
    # Get distribution of log severity
    severity_counts = {}
    for severity in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        count = Log.query.filter(
            Log.device_id.in_(device_ids),
            Log.timestamp >= start_time,
            Log.timestamp <= end_time,
            Log.severity == severity
        ).count()
        severity_counts[severity] = count
    
    # Get active device count
    active_device_count = len(device_ids)
    
    return {
        'total_logs': log_count,
        'total_metrics': metric_count,
        'severity_distribution': severity_counts,
        'active_devices': active_device_count,
        'total_organizations': len(org_ids),
        'total_sites': len(site_ids),
    }

# Data source specific data fetchers
def get_syslog_data(config, start_time, end_time):
    """Get syslog data for widgets"""
    # TODO: Implement real data fetching from database
    # For now, return sample data
    hours = int((end_time - start_time).total_seconds() / 3600) + 1
    
    if hours > 168:  # More than 7 days, group by day
        interval = 24
        group_by = "day"
    elif hours > 72:  # More than 3 days, group by 4 hours
        interval = 4
        group_by = "4-hour"
    else:
        interval = 1
        group_by = "hour"
    
    time_points = []
    values = []
    
    current = start_time
    while current <= end_time:
        time_points.append(current.strftime('%Y-%m-%d %H:%M'))
        values.append(random.randint(5, 50))
        current += timedelta(hours=interval)
    
    return {
        'time_points': time_points,
        'values': values,
        'group_by': group_by
    }

def get_snmp_data(config, start_time, end_time):
    """Get SNMP trap data for widgets"""
    # Sample SNMP trap categories
    categories = ['linkDown', 'linkUp', 'authenticationFailure', 'coldStart', 'warmStart', 'other']
    data = []
    
    for category in categories:
        data.append({
            'category': category,
            'count': random.randint(1, 20)
        })
    
    return {
        'categories': categories,
        'data': data
    }

def get_netflow_data(config, start_time, end_time, widget_type):
    """Get NetFlow data for widgets"""
    if widget_type in ['line-chart', 'bar-chart']:
        # For time series charts
        hours = int((end_time - start_time).total_seconds() / 3600) + 1
        
        time_points = []
        values = []
        
        current = start_time
        while current <= end_time:
            time_points.append(current.strftime('%Y-%m-%d %H:%M'))
            values.append(random.randint(100000, 5000000))  # bytes
            current += timedelta(hours=1)
        
        return {
            'time_points': time_points,
            'values': values,
            'unit': 'bytes'
        }
    elif widget_type == 'pie-chart':
        # For protocol distribution
        protocols = ['HTTP', 'HTTPS', 'DNS', 'SMTP', 'FTP', 'SSH', 'OTHER']
        values = [random.randint(5, 30) for _ in protocols]
        
        return {
            'labels': protocols,
            'values': values
        }
    
    return {'data': []}

def get_sflow_data(config, start_time, end_time, widget_type):
    """Get sFlow data for widgets"""
    # Similar to NetFlow but with different sample data
    if widget_type in ['line-chart', 'bar-chart']:
        # For time series charts
        hours = int((end_time - start_time).total_seconds() / 3600) + 1
        
        time_points = []
        in_values = []
        out_values = []
        
        current = start_time
        while current <= end_time:
            time_points.append(current.strftime('%Y-%m-%d %H:%M'))
            in_values.append(random.randint(200000, 8000000))  # bytes in
            out_values.append(random.randint(100000, 4000000))  # bytes out
            current += timedelta(hours=1)
        
        return {
            'time_points': time_points,
            'datasets': [
                {'label': 'Bytes In', 'values': in_values},
                {'label': 'Bytes Out', 'values': out_values}
            ],
            'unit': 'bytes'
        }
    
    return {'data': []}

def get_windows_events_data(config, start_time, end_time):
    """Get Windows Events data for widgets"""
    # Sample event types
    event_types = ['System', 'Security', 'Application', 'Setup']
    data = []
    
    for event_type in event_types:
        data.append({
            'type': event_type,
            'count': random.randint(10, 100)
        })
    
    return {
        'event_types': event_types,
        'data': data
    }

def get_otel_data(config, start_time, end_time, widget_type):
    """Get OpenTelemetry data for widgets"""
    if widget_type in ['line-chart', 'bar-chart']:
        # For time series charts
        hours = int((end_time - start_time).total_seconds() / 3600) + 1
        
        time_points = []
        response_times = []
        error_rates = []
        
        current = start_time
        while current <= end_time:
            time_points.append(current.strftime('%Y-%m-%d %H:%M'))
            response_times.append(random.randint(50, 500))  # ms
            error_rates.append(random.uniform(0, 5))  # percentage
            current += timedelta(hours=1)
        
        return {
            'time_points': time_points,
            'datasets': [
                {'label': 'Response Time (ms)', 'values': response_times},
                {'label': 'Error Rate (%)', 'values': error_rates}
            ]
        }
    elif widget_type == 'gauge':
        # For service health gauge
        return {
            'value': random.randint(70, 100),  # percentage
            'min': 0,
            'max': 100,
            'thresholds': [
                {'value': 60, 'color': 'red'},
                {'value': 80, 'color': 'yellow'},
                {'value': 90, 'color': 'green'}
            ]
        }
    
    return {'data': []}

def get_alerts_data(config, start_time, end_time):
    """Get alerts data for widgets"""
    # Sample alert data
    severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    messages = [
        'High CPU utilization detected',
        'Memory usage exceeds threshold',
        'Disk space is running low',
        'Network interface is down',
        'Service is not responding',
        'Authentication failure detected',
        'Database connection error',
        'Unexpected application restart'
    ]
    
    alerts = []
    
    for _ in range(min(10, config.get('limit', 10))):
        timestamp = start_time + timedelta(
            seconds=random.randint(0, int((end_time - start_time).total_seconds()))
        )
        severity = random.choice(severities)
        
        # If config specifies severity filter
        if 'severity' in config and severity not in config['severity']:
            # Skip if doesn't match filter
            continue
            
        alerts.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'severity': severity,
            'message': random.choice(messages),
            'source': random.choice(['syslog', 'snmp', 'netflow', 'windows_events', 'otel'])
        })
    
    # Sort by timestamp (newest first)
    alerts.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {
        'alerts': alerts
    }

def get_performance_data(config, start_time, end_time, widget_type):
    """Get performance metrics data for widgets"""
    if widget_type in ['line-chart', 'bar-chart']:
        # For time series charts
        hours = int((end_time - start_time).total_seconds() / 3600) + 1
        
        time_points = []
        values = []
        
        current = start_time
        while current <= end_time:
            time_points.append(current.strftime('%Y-%m-%d %H:%M'))
            if config.get('metric') == 'cpu':
                values.append(random.randint(5, 95))  # percentage
            elif config.get('metric') == 'memory':
                values.append(random.randint(20, 80))  # percentage
            elif config.get('metric') == 'network':
                values.append(random.randint(100, 5000))  # Kbps
            elif config.get('metric') == 'disk':
                values.append(random.randint(30, 90))  # percentage
            else:
                values.append(random.randint(1, 100))
            
            current += timedelta(hours=1)
        
        return {
            'time_points': time_points,
            'values': values,
            'metric': config.get('metric', 'unknown')
        }
    elif widget_type == 'gauge':
        # For gauge widgets
        if config.get('metric') == 'cpu':
            value = random.randint(5, 95)
        elif config.get('metric') == 'memory':
            value = random.randint(20, 80)
        elif config.get('metric') == 'disk':
            value = random.randint(30, 90)
        else:
            value = random.randint(1, 100)
            
        return {
            'value': value,
            'min': 0,
            'max': 100,
            'thresholds': [
                {'value': 80, 'color': 'red'},
                {'value': 60, 'color': 'yellow'},
                {'value': 0, 'color': 'green'}
            ]
        }
    
    return {'data': []}