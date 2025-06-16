import logging
import threading
import time
import json
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import db
from models import AlertRule, Alert, AlertSeverity, Log, Metric
from config import Config

logger = logging.getLogger(__name__)

def start():
    """Start the alert manager service"""
    logger.info("Starting alert manager service...")
    
    # Create a function to check alert rules periodically
    def check_alert_rules_periodically():
        logger.info("Alert manager running")
        while True:
            try:
                # Check all active alert rules
                check_alert_rules()
                
                # Wait before next check
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in alert manager: {e}")
                time.sleep(60)  # Wait before retrying
    
    # Start the manager in a background thread
    manager_thread = threading.Thread(target=check_alert_rules_periodically, daemon=True)
    manager_thread.start()
    
    logger.info("Alert manager service started")

def check_alert_rules():
    """Check all active alert rules against current data"""
    try:
        # Get all enabled alert rules
        rules = AlertRule.query.filter_by(enabled=True).all()
        
        for rule in rules:
            # Skip rules that are in cooldown
            last_alert = Alert.query.filter_by(alert_rule_id=rule.id, resolved=False).order_by(Alert.timestamp.desc()).first()
            if last_alert and (datetime.utcnow() - last_alert.timestamp).total_seconds() < (rule.cooldown_minutes * 60):
                continue
                
            # Check rule conditions
            triggered, details = evaluate_rule_condition(rule)
            
            if triggered:
                # Create new alert
                alert = Alert(
                    timestamp=datetime.utcnow(),
                    severity=rule.severity,
                    message=f"{rule.name} - {rule.description}",
                    details=details,
                    acknowledged=False,
                    resolved=False,
                    alert_rule_id=rule.id
                )
                
                db.session.add(alert)
                db.session.commit()
                
                logger.info(f"Alert created: {rule.name}, ID: {alert.id}")
                
                # Send notifications
                channels = rule.get_notification_channels()
                if channels:
                    send_alert_notification(alert.id, channels)
    except Exception as e:
        logger.error(f"Error checking alert rules: {e}")
        db.session.rollback()

def evaluate_rule_condition(rule):
    """Evaluate a rule's condition against current data
    
    Returns:
        tuple: (triggered, details) where triggered is a boolean indicating if the rule was triggered,
               and details is a string with more information
    """
    try:
        # Parse the condition string
        conditions = json.loads(rule.condition) if isinstance(rule.condition, str) else rule.condition
        
        # Different evaluation logic based on data source
        if rule.data_source.name == "SYSLOG":
            return evaluate_syslog_condition(conditions)
        elif rule.data_source.name == "SNMP":
            return evaluate_snmp_condition(conditions)
        elif rule.data_source.name in ["NETFLOW", "SFLOW"]:
            return evaluate_flow_condition(conditions, rule.data_source.name)
        elif rule.data_source.name == "WINDOWS_EVENTS":
            return evaluate_windows_events_condition(conditions)
        elif rule.data_source.name == "OTEL":
            return evaluate_otel_condition(conditions)
        else:
            logger.warning(f"Unknown data source type for rule: {rule.name}")
            return False, "Unknown data source type"
    except Exception as e:
        logger.error(f"Error evaluating rule condition: {e}")
        return False, f"Error: {str(e)}"

def evaluate_syslog_condition(conditions):
    """Evaluate syslog-specific conditions"""
    # Get time window
    time_window = conditions.get("time_window", 5)  # Default 5 minutes
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    # Build the query
    query = Log.query.filter(
        Log.source_type == "SYSLOG",
        Log.timestamp >= start_time
    )
    
    # Add message pattern if specified
    if "message_pattern" in conditions:
        query = query.filter(Log.message.like(f"%{conditions['message_pattern']}%"))
    
    # Add severity if specified
    if "severity" in conditions:
        query = query.filter(Log.severity == conditions["severity"])
    
    # Add threshold condition
    threshold = conditions.get("threshold", 1)
    count = query.count()
    
    # Check if threshold is met
    if count >= threshold:
        return True, f"Found {count} matching logs in the last {time_window} minutes"
    else:
        return False, f"Found {count} matching logs, threshold is {threshold}"

def evaluate_snmp_condition(conditions):
    """Evaluate SNMP-specific conditions"""
    # Similar to syslog but for SNMP traps
    time_window = conditions.get("time_window", 5)
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    query = Log.query.filter(
        Log.source_type == "SNMP",
        Log.timestamp >= start_time
    )
    
    if "trap_type" in conditions:
        query = query.filter(Log.message.like(f"%{conditions['trap_type']}%"))
    
    if "severity" in conditions:
        query = query.filter(Log.severity == conditions["severity"])
    
    threshold = conditions.get("threshold", 1)
    count = query.count()
    
    if count >= threshold:
        return True, f"Found {count} matching SNMP traps in the last {time_window} minutes"
    else:
        return False, f"Found {count} matching SNMP traps, threshold is {threshold}"

def evaluate_flow_condition(conditions, flow_type):
    """Evaluate NetFlow/sFlow-specific conditions"""
    # For network flow metrics like bandwidth usage, etc.
    time_window = conditions.get("time_window", 5)
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    query = Metric.query.filter(
        Metric.source_type == flow_type,
        Metric.timestamp >= start_time
    )
    
    if "metric_name" in conditions:
        query = query.filter(Metric.name == conditions["metric_name"])
    
    # Get metrics and check against threshold
    metrics = query.all()
    
    if not metrics:
        return False, f"No matching {flow_type} metrics found"
    
    # Calculate average value
    avg_value = sum(m.value for m in metrics) / len(metrics)
    
    # Check threshold type and value
    threshold_type = conditions.get("threshold_type", ">")
    threshold_value = conditions.get("threshold_value", 0)
    
    if threshold_type == ">" and avg_value > threshold_value:
        return True, f"Average value {avg_value} > {threshold_value}"
    elif threshold_type == ">=" and avg_value >= threshold_value:
        return True, f"Average value {avg_value} >= {threshold_value}"
    elif threshold_type == "<" and avg_value < threshold_value:
        return True, f"Average value {avg_value} < {threshold_value}"
    elif threshold_type == "<=" and avg_value <= threshold_value:
        return True, f"Average value {avg_value} <= {threshold_value}"
    elif threshold_type == "==" and avg_value == threshold_value:
        return True, f"Average value {avg_value} == {threshold_value}"
    else:
        return False, f"Condition not met: {avg_value} {threshold_type} {threshold_value}"

def evaluate_windows_events_condition(conditions):
    """Evaluate Windows Events-specific conditions"""
    # Similar to syslog but for Windows Events
    time_window = conditions.get("time_window", 5)
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    query = Log.query.filter(
        Log.source_type == "WINDOWS_EVENTS",
        Log.timestamp >= start_time
    )
    
    if "event_id" in conditions:
        query = query.filter(Log.message.like(f"%EventID: {conditions['event_id']}%"))
    
    if "severity" in conditions:
        query = query.filter(Log.severity == conditions["severity"])
    
    threshold = conditions.get("threshold", 1)
    count = query.count()
    
    if count >= threshold:
        return True, f"Found {count} matching Windows events in the last {time_window} minutes"
    else:
        return False, f"Found {count} matching Windows events, threshold is {threshold}"

def evaluate_otel_condition(conditions):
    """Evaluate OpenTelemetry-specific conditions"""
    # For OTEL metrics and traces
    if conditions.get("data_type", "metric") == "metric":
        return evaluate_otel_metric_condition(conditions)
    else:
        return evaluate_otel_trace_condition(conditions)

def evaluate_otel_metric_condition(conditions):
    """Evaluate OTEL metric conditions"""
    time_window = conditions.get("time_window", 5)
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    query = Metric.query.filter(
        Metric.source_type == "OTEL",
        Metric.timestamp >= start_time
    )
    
    if "metric_name" in conditions:
        query = query.filter(Metric.name == conditions["metric_name"])
    
    metrics = query.all()
    
    if not metrics:
        return False, "No matching OTEL metrics found"
    
    avg_value = sum(m.value for m in metrics) / len(metrics)
    
    threshold_type = conditions.get("threshold_type", ">")
    threshold_value = conditions.get("threshold_value", 0)
    
    if threshold_type == ">" and avg_value > threshold_value:
        return True, f"Average value {avg_value} > {threshold_value}"
    elif threshold_type == ">=" and avg_value >= threshold_value:
        return True, f"Average value {avg_value} >= {threshold_value}"
    elif threshold_type == "<" and avg_value < threshold_value:
        return True, f"Average value {avg_value} < {threshold_value}"
    elif threshold_type == "<=" and avg_value <= threshold_value:
        return True, f"Average value {avg_value} <= {threshold_value}"
    elif threshold_type == "==" and avg_value == threshold_value:
        return True, f"Average value {avg_value} == {threshold_value}"
    else:
        return False, f"Condition not met: {avg_value} {threshold_type} {threshold_value}"

def evaluate_otel_trace_condition(conditions):
    """Evaluate OTEL trace conditions"""
    time_window = conditions.get("time_window", 5)
    start_time = datetime.utcnow() - timedelta(minutes=time_window)
    
    query = Log.query.filter(
        Log.source_type == "OTEL",
        Log.timestamp >= start_time,
        Log.message.like("Trace:%")
    )
    
    if "span_name" in conditions:
        query = query.filter(Log.message.like(f"%{conditions['span_name']}%"))
    
    if "error" in conditions and conditions["error"]:
        query = query.filter(Log.severity == "error")
    
    threshold = conditions.get("threshold", 1)
    count = query.count()
    
    if count >= threshold:
        return True, f"Found {count} matching OTEL traces in the last {time_window} minutes"
    else:
        return False, f"Found {count} matching OTEL traces, threshold is {threshold}"

def send_alert_notification(alert_id, channels):
    """Send notification for an alert through the configured channels"""
    try:
        # Get the alert details
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert not found: {alert_id}")
            return
        
        alert_text = (
            f"ALERT: {alert.message}\n"
            f"Severity: {alert.severity.name}\n"
            f"Time: {alert.timestamp}\n"
            f"Details: {alert.details}"
        )
        
        # Send notifications through each channel
        for channel in channels:
            channel_type = channel.get("type")
            
            if channel_type == "email":
                send_email_notification(channel, alert_text, alert)
            elif channel_type == "slack":
                send_slack_notification(channel, alert_text, alert)
            elif channel_type == "pagerduty":
                send_pagerduty_notification(channel, alert_text, alert)
            else:
                logger.warning(f"Unknown notification channel type: {channel_type}")
    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")

def send_email_notification(channel, alert_text, alert):
    """Send an email notification"""
    try:
        recipients = channel.get("recipients", [])
        if not recipients:
            logger.warning("No email recipients specified")
            return
        
        # Configure email
        msg = MIMEMultipart()
        msg["From"] = Config.SMTP_FROM_EMAIL
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = f"Alert: {alert.message} [{alert.severity.name}]"
        
        # Add body
        msg.attach(MIMEText(alert_text, "plain"))
        
        # Connect to SMTP server
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        
        # Login if credentials are provided
        if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email notification sent for alert {alert.id} to {len(recipients)} recipients")
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")

def send_slack_notification(channel, alert_text, alert):
    """Send a Slack notification"""
    try:
        webhook_url = Config.SLACK_WEBHOOK_URL
        if not webhook_url:
            logger.warning("No Slack webhook URL configured")
            return
        
        # Color based on severity
        color = "#ff0000"  # Default to red
        if alert.severity == AlertSeverity.WARNING:
            color = "#ffcc00"
        elif alert.severity == AlertSeverity.INFO:
            color = "#0099cc"
        
        # Create payload
        payload = {
            "attachments": [
                {
                    "fallback": alert.message,
                    "color": color,
                    "title": f"Alert: {alert.message}",
                    "text": alert_text,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.name,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
            logger.warning(f"Slack API returned error: {response.status_code}, {response.text}")
        else:
            logger.info(f"Slack notification sent for alert {alert.id}")
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")

def send_pagerduty_notification(channel, alert_text, alert):
    """Send a PagerDuty notification"""
    try:
        service_key = Config.PAGERDUTY_SERVICE_KEY
        if not service_key:
            logger.warning("No PagerDuty service key configured")
            return
        
        # Map severity
        severity = "info"
        if alert.severity == AlertSeverity.WARNING:
            severity = "warning"
        elif alert.severity == AlertSeverity.ERROR:
            severity = "error"
        elif alert.severity == AlertSeverity.CRITICAL:
            severity = "critical"
        
        # Create payload
        payload = {
            "routing_key": service_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.message,
                "source": "Observability Dashboard",
                "severity": severity,
                "custom_details": {
                    "details": alert.details,
                    "alert_id": alert.id
                }
            }
        }
        
        # Send to PagerDuty
        response = requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 202:
            logger.warning(f"PagerDuty API returned error: {response.status_code}, {response.text}")
        else:
            logger.info(f"PagerDuty notification sent for alert {alert.id}")
    except Exception as e:
        logger.error(f"Error sending PagerDuty notification: {e}")