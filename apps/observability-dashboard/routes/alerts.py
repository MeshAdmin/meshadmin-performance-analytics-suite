from datetime import datetime, timedelta
import json

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from models import AlertRule, Alert, AlertSeverity, DataSourceType

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/')
@login_required
def index():
    """Show the alerts dashboard"""
    # Get time range from request (default to 24h)
    time_range = request.args.get('time_range', '24h')
    
    # Calculate start time based on time range
    now = datetime.utcnow()
    if time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:  # Default to 24h
        start_time = now - timedelta(days=1)
    
    # Get alerts for the current user's organization
    user_org_ids = [org.id for org in current_user.organizations]
    alerts = Alert.query.join(AlertRule).filter(
        AlertRule.organization_id.in_(user_org_ids),
        Alert.timestamp >= start_time
    ).order_by(desc(Alert.timestamp)).all()
    
    # Get recent alerts (last 10)
    recent_alerts = alerts[:10] if alerts else []
    
    # Get alert rules for the current user's organization
    alert_rules = AlertRule.query.filter(
        AlertRule.organization_id.in_(user_org_ids)
    ).order_by(AlertRule.name).all()
    
    return render_template(
        'alerts_dashboard.html', 
        alerts=alerts,
        recent_alerts=recent_alerts,
        alert_rules=alert_rules,
        time_range=time_range,
        format_condition=format_conditions
    )

@alerts_bp.route('/rules')
@login_required
def rules():
    """Show alert rules management page"""
    # Get alert rules for the current user's organization
    user_org_ids = [org.id for org in current_user.organizations]
    alert_rules = AlertRule.query.filter(
        AlertRule.organization_id.in_(user_org_ids)
    ).order_by(AlertRule.name).all()
    
    return render_template(
        'alert_rules.html', 
        alert_rules=alert_rules,
        format_condition=format_conditions
    )

@alerts_bp.route('/history')
@login_required
def history():
    """Show alert history page"""
    # Get alerts for the current user's organization
    user_org_ids = [org.id for org in current_user.organizations]
    alerts = Alert.query.join(AlertRule).filter(
        AlertRule.organization_id.in_(user_org_ids)
    ).order_by(desc(Alert.timestamp)).all()
    
    return render_template('alert_history.html', alerts=alerts)

@alerts_bp.route('/api/alert_rules', methods=['GET'])
@login_required
def api_get_alert_rules():
    """API endpoint to get all alert rules"""
    user_org_ids = [org.id for org in current_user.organizations]
    rules = AlertRule.query.filter(
        AlertRule.organization_id.in_(user_org_ids)
    ).order_by(AlertRule.name).all()
    
    rules_data = [
        {
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'data_source': rule.data_source.value,
            'severity': rule.severity.value,
            'enabled': rule.enabled,
            'condition': parse_conditions(rule.condition),
            'cooldown_minutes': rule.cooldown_minutes,
            'notification_channels': json.loads(rule.notification_channels) if rule.notification_channels else [],
            'created_at': rule.created_at.isoformat(),
            'updated_at': rule.updated_at.isoformat() if rule.updated_at else None
        }
        for rule in rules
    ]
    
    return jsonify(rules=rules_data)

@alerts_bp.route('/api/alert_rules', methods=['POST'])
@login_required
def api_create_alert_rule():
    """API endpoint to create a new alert rule"""
    data = request.json
    
    # Validate required fields
    if not data.get('name') or not data.get('data_source') or not data.get('severity'):
        return jsonify(error='Missing required fields'), 400
    
    # Get the current user's primary organization
    if not current_user.organizations:
        return jsonify(error='User does not belong to any organization'), 400
    
    organization_id = current_user.organizations[0].id
    
    # Create new alert rule
    rule = AlertRule(
        name=data['name'],
        description=data.get('description', ''),
        data_source=DataSourceType(data['data_source']),
        condition=json.dumps(data['condition']),
        severity=AlertSeverity(data['severity']),
        enabled=data.get('enabled', True),
        cooldown_minutes=data.get('cooldown_minutes', 15),
        notification_channels=json.dumps(data.get('notification_channels', [])),
        organization_id=organization_id
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify(
        id=rule.id,
        name=rule.name,
        message='Alert rule created successfully'
    ), 201

@alerts_bp.route('/api/alert_rules/<int:rule_id>', methods=['GET'])
@login_required
def api_get_alert_rule(rule_id):
    """API endpoint to get a specific alert rule"""
    user_org_ids = [org.id for org in current_user.organizations]
    rule = AlertRule.query.filter(
        AlertRule.id == rule_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not rule:
        return jsonify(error='Alert rule not found'), 404
    
    rule_data = {
        'id': rule.id,
        'name': rule.name,
        'description': rule.description,
        'data_source': rule.data_source.value,
        'severity': rule.severity.value,
        'enabled': rule.enabled,
        'condition': parse_conditions(rule.condition),
        'cooldown_minutes': rule.cooldown_minutes,
        'notification_channels': json.loads(rule.notification_channels) if rule.notification_channels else [],
        'created_at': rule.created_at.isoformat(),
        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None
    }
    
    return jsonify(rule_data)

@alerts_bp.route('/api/alert_rules/<int:rule_id>', methods=['PUT'])
@login_required
def api_update_alert_rule(rule_id):
    """API endpoint to update an alert rule"""
    user_org_ids = [org.id for org in current_user.organizations]
    rule = AlertRule.query.filter(
        AlertRule.id == rule_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not rule:
        return jsonify(error='Alert rule not found'), 404
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        rule.name = data['name']
    if 'description' in data:
        rule.description = data['description']
    if 'data_source' in data:
        rule.data_source = DataSourceType(data['data_source'])
    if 'condition' in data:
        rule.condition = json.dumps(data['condition'])
    if 'severity' in data:
        rule.severity = AlertSeverity(data['severity'])
    if 'enabled' in data:
        rule.enabled = data['enabled']
    if 'cooldown_minutes' in data:
        rule.cooldown_minutes = data['cooldown_minutes']
    if 'notification_channels' in data:
        rule.notification_channels = json.dumps(data['notification_channels'])
    
    # Update timestamp
    rule.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(
        id=rule.id,
        name=rule.name,
        message='Alert rule updated successfully'
    )

@alerts_bp.route('/api/alert_rules/<int:rule_id>', methods=['DELETE'])
@login_required
def api_delete_alert_rule(rule_id):
    """API endpoint to delete an alert rule"""
    user_org_ids = [org.id for org in current_user.organizations]
    rule = AlertRule.query.filter(
        AlertRule.id == rule_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not rule:
        return jsonify(error='Alert rule not found'), 404
    
    # Store the name for response
    rule_name = rule.name
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify(
        id=rule_id,
        name=rule_name,
        message='Alert rule deleted successfully'
    )

@alerts_bp.route('/api/alert_rules/<int:rule_id>/status', methods=['PUT'])
@login_required
def api_update_rule_status(rule_id):
    """API endpoint to update an alert rule's enabled status"""
    user_org_ids = [org.id for org in current_user.organizations]
    rule = AlertRule.query.filter(
        AlertRule.id == rule_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not rule:
        return jsonify(error='Alert rule not found'), 404
    
    data = request.json
    if 'enabled' not in data:
        return jsonify(error='Missing enabled status'), 400
    
    rule.enabled = data['enabled']
    rule.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(
        id=rule.id,
        name=rule.name,
        enabled=rule.enabled,
        message=f'Alert rule {"enabled" if rule.enabled else "disabled"}'
    )

@alerts_bp.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def api_acknowledge_alert(alert_id):
    """API endpoint to acknowledge an alert"""
    user_org_ids = [org.id for org in current_user.organizations]
    alert = Alert.query.join(AlertRule).filter(
        Alert.id == alert_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not alert:
        return jsonify(error='Alert not found'), 404
    
    # Set acknowledged flag and user
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.user_id = current_user.id
    
    db.session.commit()
    
    return jsonify(
        id=alert.id,
        acknowledged=alert.acknowledged,
        acknowledged_at=alert.acknowledged_at.isoformat(),
        message='Alert acknowledged'
    )

@alerts_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def api_resolve_alert(alert_id):
    """API endpoint to resolve an alert"""
    user_org_ids = [org.id for org in current_user.organizations]
    alert = Alert.query.join(AlertRule).filter(
        Alert.id == alert_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not alert:
        return jsonify(error='Alert not found'), 404
    
    # Set resolved flag and user
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.user_id = current_user.id
    
    # If not acknowledged, also acknowledge it
    if not alert.acknowledged:
        alert.acknowledged = True
        alert.acknowledged_at = alert.resolved_at
    
    db.session.commit()
    
    return jsonify(
        id=alert.id,
        resolved=alert.resolved,
        resolved_at=alert.resolved_at.isoformat(),
        message='Alert resolved'
    )

@alerts_bp.route('/api/alerts/bulk_acknowledge', methods=['POST'])
@login_required
def api_bulk_acknowledge():
    """API endpoint to acknowledge multiple alerts"""
    data = request.json
    if not data or 'alert_ids' not in data or not data['alert_ids']:
        return jsonify(error='No alert IDs provided'), 400
    
    alert_ids = data['alert_ids']
    user_org_ids = [org.id for org in current_user.organizations]
    
    # Query alerts that belong to user's organizations
    alerts = Alert.query.join(AlertRule).filter(
        Alert.id.in_(alert_ids),
        AlertRule.organization_id.in_(user_org_ids),
        Alert.acknowledged == False
    ).all()
    
    # Acknowledge each alert
    now = datetime.utcnow()
    acknowledged_count = 0
    
    for alert in alerts:
        alert.acknowledged = True
        alert.acknowledged_at = now
        alert.user_id = current_user.id
        acknowledged_count += 1
    
    db.session.commit()
    
    return jsonify(
        acknowledged_count=acknowledged_count,
        message=f'{acknowledged_count} alerts acknowledged'
    )

@alerts_bp.route('/api/alerts/bulk_resolve', methods=['POST'])
@login_required
def api_bulk_resolve():
    """API endpoint to resolve multiple alerts"""
    data = request.json
    if not data or 'alert_ids' not in data or not data['alert_ids']:
        return jsonify(error='No alert IDs provided'), 400
    
    alert_ids = data['alert_ids']
    user_org_ids = [org.id for org in current_user.organizations]
    
    # Query alerts that belong to user's organizations
    alerts = Alert.query.join(AlertRule).filter(
        Alert.id.in_(alert_ids),
        AlertRule.organization_id.in_(user_org_ids),
        Alert.resolved == False
    ).all()
    
    # Resolve each alert
    now = datetime.utcnow()
    resolved_count = 0
    
    for alert in alerts:
        alert.resolved = True
        alert.resolved_at = now
        alert.user_id = current_user.id
        
        # If not acknowledged, also acknowledge it
        if not alert.acknowledged:
            alert.acknowledged = True
            alert.acknowledged_at = now
        
        resolved_count += 1
    
    db.session.commit()
    
    return jsonify(
        resolved_count=resolved_count,
        message=f'{resolved_count} alerts resolved'
    )

@alerts_bp.route('/api/alerts/notification_settings', methods=['PUT'])
@login_required
def api_update_notification_settings():
    """API endpoint to update user notification settings"""
    data = request.json
    
    # Here you would typically update the user's notification settings in the database
    # For now, we just return success
    
    return jsonify(
        success=True,
        message='Notification settings updated'
    )

@alerts_bp.route('/api/alerts/check', methods=['GET'])
@login_required
def api_check_alerts():
    """API endpoint to check for new alerts since a given timestamp"""
    since_str = request.args.get('since', '')
    
    try:
        since = datetime.fromisoformat(since_str.replace('Z', '+00:00'))
    except ValueError:
        # Default to 1 hour ago if invalid timestamp
        since = datetime.utcnow() - timedelta(hours=1)
    
    user_org_ids = [org.id for org in current_user.organizations]
    new_alerts = Alert.query.join(AlertRule).filter(
        AlertRule.organization_id.in_(user_org_ids),
        Alert.timestamp > since
    ).order_by(desc(Alert.timestamp)).all()
    
    alerts_data = [
        {
            'id': alert.id,
            'timestamp': alert.timestamp.isoformat(),
            'severity': alert.severity.value,
            'message': alert.message,
            'rule_name': alert.alert_rule.name if alert.alert_rule else 'System',
            'rule_id': alert.alert_rule_id
        }
        for alert in new_alerts
    ]
    
    return jsonify(
        count=len(alerts_data),
        alerts=alerts_data
    )

@alerts_bp.route('/api/alerts', methods=['GET'])
@login_required
def api_get_alerts():
    """API endpoint to get alerts with optional filtering"""
    # Parse filter parameters
    severity = request.args.get('severity')
    status = request.args.get('status')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    limit = request.args.get('limit', type=int, default=100)
    
    # Build query
    user_org_ids = [org.id for org in current_user.organizations]
    query = Alert.query.join(AlertRule).filter(
        AlertRule.organization_id.in_(user_org_ids)
    )
    
    # Apply filters
    if severity:
        query = query.filter(Alert.severity == AlertSeverity(severity))
    
    if status:
        if status == 'active':
            query = query.filter(Alert.acknowledged == False, Alert.resolved == False)
        elif status == 'acknowledged':
            query = query.filter(Alert.acknowledged == True, Alert.resolved == False)
        elif status == 'resolved':
            query = query.filter(Alert.resolved == True)
    
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            query = query.filter(Alert.timestamp >= start_time)
        except ValueError:
            pass
    
    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            query = query.filter(Alert.timestamp <= end_time)
        except ValueError:
            pass
    
    # Get results
    alerts = query.order_by(desc(Alert.timestamp)).limit(limit).all()
    
    alerts_data = [
        {
            'id': alert.id,
            'timestamp': alert.timestamp.isoformat(),
            'severity': alert.severity.value,
            'message': alert.message,
            'details': alert.details,
            'rule_name': alert.alert_rule.name if alert.alert_rule else 'System',
            'rule_id': alert.alert_rule_id,
            'acknowledged': alert.acknowledged,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            'resolved': alert.resolved,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
        for alert in alerts
    ]
    
    return jsonify(
        count=len(alerts_data),
        alerts=alerts_data
    )

@alerts_bp.route('/api/alerts/<int:alert_id>', methods=['GET'])
@login_required
def api_get_alert(alert_id):
    """API endpoint to get a specific alert"""
    user_org_ids = [org.id for org in current_user.organizations]
    alert = Alert.query.join(AlertRule).filter(
        Alert.id == alert_id,
        AlertRule.organization_id.in_(user_org_ids)
    ).first()
    
    if not alert:
        return jsonify(error='Alert not found'), 404
    
    alert_data = {
        'id': alert.id,
        'timestamp': alert.timestamp.isoformat(),
        'severity': alert.severity.value,
        'message': alert.message,
        'details': alert.details,
        'rule_name': alert.alert_rule.name if alert.alert_rule else 'System',
        'rule_id': alert.alert_rule_id,
        'acknowledged': alert.acknowledged,
        'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        'resolved': alert.resolved,
        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
    }
    
    return jsonify(alert_data)

def format_conditions(condition_str):
    """Format conditions array into a string representation"""
    try:
        condition_obj = json.loads(condition_str)
        logic = condition_obj.get('logic', 'AND')
        conditions = condition_obj.get('conditions', [])
        
        condition_texts = []
        for cond in conditions:
            field = cond.get('field', '')
            operator = cond.get('operator', 'eq')
            value = cond.get('value', '')
            
            op_text = {
                'eq': 'equals',
                'neq': 'not equals',
                'gt': 'greater than',
                'lt': 'less than',
                'gte': 'greater than or equal',
                'lte': 'less than or equal',
                'contains': 'contains',
                'not_contains': 'does not contain',
                'regex': 'matches regex'
            }.get(operator, operator)
            
            condition_texts.append(f"{field} {op_text} '{value}'")
        
        if not condition_texts:
            return 'No conditions'
        
        if len(condition_texts) == 1:
            return condition_texts[0]
        
        return f"{' {logic} '.join(condition_texts)}"
    except (json.JSONDecodeError, AttributeError, TypeError):
        return condition_str

def parse_conditions(condition_str):
    """Parse condition string back into an array of conditions"""
    try:
        return json.loads(condition_str)
    except (json.JSONDecodeError, TypeError):
        # Return a default structure
        return {
            'logic': 'AND',
            'conditions': []
        }

def get_user_notification_settings():
    """Get the current user's notification settings"""
    # Here you would typically get the user's notification settings from the database
    # For now, we return default settings
    return {
        'browser': True,
        'desktop': False,
        'email': True
    }