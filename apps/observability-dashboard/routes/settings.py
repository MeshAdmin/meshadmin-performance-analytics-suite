from flask import Blueprint, render_template, request, jsonify, abort, flash, redirect, url_for
from flask_login import login_required, current_user
import json
from datetime import datetime, timedelta
import os
from werkzeug.security import check_password_hash

from models import User, Organization, Dashboard, UserSession, ApiToken
from app import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def index():
    """Show the settings dashboard"""
    # Get user's dashboards for default selection
    dashboards = Dashboard.query.filter(
        (Dashboard.user_id == current_user.id) | 
        (Dashboard.organization_id.in_([org.id for org in current_user.organizations]))
    ).all()
    
    # Get user preferences
    preferences = current_user.get_preferences()
    default_dashboard_id = preferences.get('default_dashboard')
    
    # Get active sessions
    active_sessions = get_active_sessions()
    
    # Get API tokens
    api_tokens = get_api_tokens()
    
    # Get notification settings
    notification_settings = get_notification_settings()
    
    # Get data retention settings
    data_retention = get_data_retention_settings()
    
    # Get collector settings
    collector_settings = get_collector_settings()
    
    # Get integrations
    integrations = get_integrations()
    
    return render_template(
        'settings.html',
        dashboards=dashboards,
        default_dashboard_id=default_dashboard_id,
        active_sessions=active_sessions,
        api_tokens=api_tokens,
        notification_settings=notification_settings,
        data_retention=data_retention,
        collector_settings=collector_settings,
        integrations=integrations
    )

@settings_bp.route('/settings/profile')
@login_required
def profile():
    """Show profile settings page"""
    return render_template('profile.html')

@settings_bp.route('/settings/notifications')
@login_required
def notifications():
    """Show notification settings page"""
    notification_settings = get_notification_settings()
    return render_template('notification_settings.html', notification_settings=notification_settings)

@settings_bp.route('/settings/security')
@login_required
def security():
    """Show security settings page"""
    active_sessions = get_active_sessions()
    return render_template('security_settings.html', active_sessions=active_sessions)

@settings_bp.route('/api/users/profile', methods=['PUT'])
@login_required
def api_update_profile():
    """API endpoint to update user profile"""
    data = request.json
    
    # Update basic profile fields
    if 'username' in data and data['username'] != current_user.username:
        # Check if username is already taken
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400
        current_user.username = data['username']
    
    if 'email' in data and data['email'] != current_user.email:
        # Check if email is already taken
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already taken'}), 400
        current_user.email = data['email']
    
    if 'full_name' in data:
        current_user.full_name = data['full_name']
    
    if 'job_title' in data:
        current_user.job_title = data['job_title']
    
    if 'timezone' in data:
        preferences = current_user.get_preferences()
        preferences['timezone'] = data['timezone']
        current_user.set_preferences(preferences)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully'
    })

@settings_bp.route('/api/users/password', methods=['PUT'])
@login_required
def api_update_password():
    """API endpoint to update user password"""
    data = request.json
    
    # Verify current password
    if not check_password_hash(current_user.password_hash, data.get('current_password')):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Update password
    current_user.set_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Password updated successfully'
    })

@settings_bp.route('/api/users/preferences', methods=['POST'])
@login_required
def api_update_preferences():
    """API endpoint to update user preferences"""
    data = request.json
    
    # Get current preferences
    preferences = current_user.get_preferences()
    
    # Update theme if provided
    if 'theme' in data:
        preferences['theme'] = data['theme']
    
    # Update default dashboard if provided
    if 'default_dashboard' in data:
        preferences['default_dashboard'] = data['default_dashboard']
    
    # Update sidebar preference if provided
    if 'sidebar_collapsed' in data:
        preferences['sidebar_collapsed'] = data['sidebar_collapsed']
    
    # Save preferences
    current_user.set_preferences(preferences)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Preferences updated successfully'
    })

@settings_bp.route('/api/tokens', methods=['POST'])
@login_required
def api_create_token():
    """API endpoint to create an API token"""
    data = request.json
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Token name is required'}), 400
    
    permissions = data.get('permissions', {})
    expiry = data.get('expiry')
    
    # Calculate expiration date
    expires_at = None
    if expiry and expiry != 'never':
        days = int(expiry)
        expires_at = datetime.utcnow() + timedelta(days=days)
    
    # Create token (in a real implementation, this would be more sophisticated)
    import secrets
    token_value = secrets.token_hex(32)
    
    # Create token record
    from models import ApiToken
    token = ApiToken(
        user_id=current_user.id,
        name=name,
        token_hash=token_value,  # In a real impl, this would be hashed
        permissions=json.dumps(permissions),
        expires_at=expires_at
    )
    
    db.session.add(token)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'token': token_value,
        'message': 'Token created successfully'
    })

@settings_bp.route('/api/tokens/<int:token_id>', methods=['DELETE'])
@login_required
def api_delete_token(token_id):
    """API endpoint to delete an API token"""
    from models import ApiToken
    token = ApiToken.query.get_or_404(token_id)
    
    # Ensure the token belongs to the current user
    if token.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    db.session.delete(token)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Token deleted successfully'
    })

@settings_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def api_terminate_session(session_id):
    """API endpoint to terminate a user session"""
    session = UserSession.query.get_or_404(session_id)
    
    # Ensure the session belongs to the current user
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Delete the session
    db.session.delete(session)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Session terminated successfully'
    })

@settings_bp.route('/api/sessions/terminate-all', methods=['POST'])
@login_required
def api_terminate_all_sessions():
    """API endpoint to terminate all sessions except the current one"""
    current_session_id = request.cookies.get('session_id')
    
    # Delete all sessions except the current one
    UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.id != current_session_id
    ).delete()
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'All other sessions terminated successfully'
    })

@settings_bp.route('/api/data/retention', methods=['POST'])
@login_required
def api_update_data_retention():
    """API endpoint to update data retention settings"""
    # Verify admin access
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    
    # Get organization settings
    organizations = current_user.organizations
    if not organizations:
        return jsonify({'error': 'No organization found'}), 400
    
    organization = organizations[0]
    
    # Get current settings
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Update retention settings
    settings['data_retention'] = {
        'logs': data.get('logs', 30),
        'metrics': data.get('metrics', 30),
        'alerts': data.get('alerts', 90),
        'reports': data.get('reports', 90)
    }
    
    # Save settings
    organization.settings = json.dumps(settings)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Data retention settings updated successfully'
    })

@settings_bp.route('/api/data/export', methods=['POST'])
@login_required
def api_export_data():
    """API endpoint to export user data"""
    data = request.json
    
    # Determine what to export
    export_dashboards = data.get('dashboards', True)
    export_reports = data.get('reports', True)
    export_alerts = data.get('alerts', True)
    export_settings = data.get('settings', True)
    
    # Build export data
    export_data = {
        'username': current_user.username,
        'email': current_user.email,
        'exported_at': datetime.utcnow().isoformat()
    }
    
    # Add dashboard data if requested
    if export_dashboards:
        dashboards = Dashboard.query.filter_by(user_id=current_user.id).all()
        export_data['dashboards'] = []
        
        for dashboard in dashboards:
            dashboard_data = {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'layout': json.loads(dashboard.layout) if dashboard.layout else [],
                'created_at': dashboard.created_at.isoformat(),
                'updated_at': dashboard.updated_at.isoformat()
            }
            
            # Add widgets
            dashboard_data['widgets'] = []
            for widget in dashboard.widgets:
                widget_data = {
                    'name': widget.name,
                    'type': widget.widget_type,
                    'data_source': widget.data_source.value,
                    'configuration': widget.get_configuration(),
                    'position': {
                        'x': widget.position_x,
                        'y': widget.position_y
                    },
                    'size': {
                        'width': widget.width,
                        'height': widget.height
                    }
                }
                dashboard_data['widgets'].append(widget_data)
            
            export_data['dashboards'].append(dashboard_data)
    
    # Add reports data if requested
    if export_reports:
        from models import Report
        reports = Report.query.filter_by(user_id=current_user.id).all()
        export_data['reports'] = []
        
        for report in reports:
            report_data = {
                'id': report.id,
                'name': report.name,
                'description': report.description,
                'format': report.format,
                'sections': json.loads(report.sections) if report.sections else [],
                'parameters': json.loads(report.parameters) if report.parameters else [],
                'schedule': report.schedule,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat()
            }
            export_data['reports'].append(report_data)
    
    # Add alert rules if requested
    if export_alerts:
        from models import AlertRule
        alert_rules = AlertRule.query.filter(
            AlertRule.organization_id.in_([org.id for org in current_user.organizations])
        ).all()
        
        export_data['alert_rules'] = []
        for rule in alert_rules:
            rule_data = {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'data_source': rule.data_source.value,
                'condition': rule.condition,
                'severity': rule.severity.value,
                'enabled': rule.enabled,
                'cooldown_minutes': rule.cooldown_minutes,
                'notification_channels': rule.get_notification_channels(),
                'created_at': rule.created_at.isoformat(),
                'updated_at': rule.updated_at.isoformat()
            }
            export_data['alert_rules'].append(rule_data)
    
    # Add settings if requested
    if export_settings:
        export_data['preferences'] = current_user.get_preferences()
    
    return jsonify(export_data)

@settings_bp.route('/api/data/cleanup', methods=['POST'])
@login_required
def api_cleanup_data():
    """API endpoint to clean up data"""
    # Verify admin access
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    data_type = data.get('type')
    
    if data_type == 'logs':
        from models import Log
        Log.query.delete()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'All logs have been deleted'
        })
    
    elif data_type == 'metrics':
        from models import Metric
        Metric.query.delete()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'All metrics have been deleted'
        })
    
    elif data_type == 'alerts':
        from models import Alert
        Alert.query.delete()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'All alerts have been deleted'
        })
    
    else:
        return jsonify({'error': 'Invalid data type'}), 400

@settings_bp.route('/api/collectors/<string:collector>', methods=['PUT'])
@login_required
def api_update_collector(collector):
    """API endpoint to update collector settings"""
    # Verify admin access
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    
    # Get organization settings
    organizations = current_user.organizations
    if not organizations:
        return jsonify({'error': 'No organization found'}), 400
    
    organization = organizations[0]
    
    # Get current settings
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Initialize collectors if not present
    if 'collectors' not in settings:
        settings['collectors'] = {}
    
    # Update collector settings
    if collector not in settings['collectors']:
        settings['collectors'][collector] = {}
    
    # Update enabled status
    if 'enabled' in data:
        settings['collectors'][collector]['enabled'] = data['enabled']
    
    # Update port if provided
    if 'port' in data:
        settings['collectors'][collector]['port'] = data['port']
    
    # Update any other collector-specific settings
    for key, value in data.items():
        if key not in ['enabled', 'port']:
            settings['collectors'][collector][key] = value
    
    # Save settings
    organization.settings = json.dumps(settings)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'{collector} collector settings updated successfully'
    })

@settings_bp.route('/api/integrations/<string:service>', methods=['POST'])
@login_required
def api_connect_integration(service):
    """API endpoint to connect an integration"""
    data = request.json
    
    # Get organization settings
    organizations = current_user.organizations
    if not organizations:
        return jsonify({'error': 'No organization found'}), 400
    
    organization = organizations[0]
    
    # Get current settings
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Initialize integrations if not present
    if 'integrations' not in settings:
        settings['integrations'] = {}
    
    # Update integration settings
    if service not in settings['integrations']:
        settings['integrations'][service] = {}
    
    # Update service-specific settings
    if service == 'slack':
        settings['integrations'][service] = {
            'webhook_url': data.get('webhook_url'),
            'channel': data.get('channel'),
            'workspace': data.get('workspace', 'Unknown')
        }
    elif service == 'pagerduty':
        settings['integrations'][service] = {
            'api_key': data.get('api_key'),
            'service_key': data.get('service_key'),
            'account': data.get('account', 'Unknown')
        }
    elif service == 'teams':
        settings['integrations'][service] = {
            'webhook_url': data.get('webhook_url'),
            'team': data.get('team', 'Unknown')
        }
    else:
        # Generic handling for other services
        for key, value in data.items():
            settings['integrations'][service][key] = value
    
    # Save settings
    organization.settings = json.dumps(settings)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'{service} integration connected successfully'
    })

@settings_bp.route('/api/integrations/<string:service>', methods=['DELETE'])
@login_required
def api_disconnect_integration(service):
    """API endpoint to disconnect an integration"""
    # Get organization settings
    organizations = current_user.organizations
    if not organizations:
        return jsonify({'error': 'No organization found'}), 400
    
    organization = organizations[0]
    
    # Get current settings
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Check if integrations exist
    if 'integrations' not in settings or service not in settings['integrations']:
        return jsonify({'error': 'Integration not found'}), 404
    
    # Remove the integration
    del settings['integrations'][service]
    
    # Save settings
    organization.settings = json.dumps(settings)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'{service} integration disconnected successfully'
    })

def get_active_sessions():
    """Get the current user's active sessions"""
    # Query actual UserSession records
    db_sessions = UserSession.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(UserSession.last_active.desc()).all()
    
    sessions = []
    current_session_id = request.cookies.get('session_id')
    
    for session in db_sessions:
        # Parse user agent
        user_agent = session.user_agent or "Unknown"
        device = "Desktop"
        if "Mobile" in user_agent:
            device = "Mobile Device"
        elif "Tablet" in user_agent:
            device = "Tablet"
        
        sessions.append({
            'id': session.id,
            'device': device,
            'location': 'Unknown',  # Would require IP geolocation service
            'ip_address': session.ip_address,
            'user_agent': user_agent,
            'last_active': session.last_active,
            'current': str(session.session_id) == current_session_id
        })
    
    # If no sessions found, create a placeholder for current session
    if not sessions:
        sessions.append({
            'id': '1',
            'device': 'Current Browser',
        'location': 'New York, USA',
        'ip_address': '192.168.1.100',
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        'last_active': datetime.utcnow() - timedelta(days=1),
        'current': False
    })
    
    return sessions

def get_api_tokens():
    """Get the current user's API tokens"""
    # Query actual ApiToken records
    db_tokens = ApiToken.query.filter_by(
        user_id=current_user.id
    ).order_by(ApiToken.created_at.desc()).all()
    
    tokens = []
    
    for token in db_tokens:
        # Parse permissions
        permissions = json.loads(token.permissions) if token.permissions else {
            'read': True,
            'write': False,
            'delete': False
        }
        
        tokens.append({
            'id': token.id,
            'name': token.name,
            'created_at': token.created_at,
            'expires_at': token.expires_at,
            'last_used_at': token.last_used,
            'permissions': permissions
        })
    
    # If no tokens found (for new users), return empty list
    return tokens

def get_notification_settings():
    """Get the current user's notification settings"""
    preferences = current_user.get_preferences()
    notifications = preferences.get('notifications', {})
    
    # Default settings if not set
    if not notifications:
        notifications = {
            'email': True,
            'slack': False,
            'pagerduty': False,
            'webhook': False,
            'desktop': True,
            'email_alerts': True,
            'email_reports': True,
            'email_system': True,
            'app_alerts': True,
            'app_reports': True,
            'app_system': True,
            'desktop_alerts': True
        }
    
    return notifications

def get_data_retention_settings():
    """Get organization data retention settings"""
    organizations = current_user.organizations
    if not organizations:
        # Default retention settings
        return {
            'logs': 30,
            'metrics': 30,
            'alerts': 90,
            'reports': 90
        }
    
    organization = organizations[0]
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Get retention settings or use defaults
    retention = settings.get('data_retention', {})
    return {
        'logs': retention.get('logs', 30),
        'metrics': retention.get('metrics', 30),
        'alerts': retention.get('alerts', 90),
        'reports': retention.get('reports', 90)
    }

def get_collector_settings():
    """Get organization collector settings"""
    organizations = current_user.organizations
    if not organizations:
        # Default collector settings
        return {
            'syslog': {'enabled': True, 'port': 514},
            'snmp': {'enabled': True, 'port': 162},
            'netflow': {'enabled': True, 'port': 2055},
            'sflow': {'enabled': True, 'port': 6343},
            'windows_events': {'enabled': True, 'port': 3268},
            'otel': {'enabled': True, 'port': 4317}
        }
    
    organization = organizations[0]
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Get collector settings or use defaults
    collectors = settings.get('collectors', {})
    
    defaults = {
        'syslog': {'enabled': True, 'port': 514},
        'snmp': {'enabled': True, 'port': 162},
        'netflow': {'enabled': True, 'port': 2055},
        'sflow': {'enabled': True, 'port': 6343},
        'windows_events': {'enabled': True, 'port': 3268},
        'otel': {'enabled': True, 'port': 4317}
    }
    
    # Merge defaults with actual settings
    result = {}
    for collector, default in defaults.items():
        if collector in collectors:
            result[collector] = {**default, **collectors[collector]}
        else:
            result[collector] = default
    
    return result

def get_integrations():
    """Get organization integrations"""
    organizations = current_user.organizations
    if not organizations:
        return {}
    
    organization = organizations[0]
    settings = json.loads(organization.settings) if organization.settings else {}
    
    # Get integrations or return empty dict
    return settings.get('integrations', {})
