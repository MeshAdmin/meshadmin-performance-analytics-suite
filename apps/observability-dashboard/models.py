from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum
import json

# Enum definitions
class AlertSeverity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class DataSourceType(enum.Enum):
    SYSLOG = "syslog"
    SNMP = "snmp"
    NETFLOW = "netflow"
    SFLOW = "sflow"
    WINDOWS_EVENTS = "windows_events"
    OTEL = "otel"

# User-related models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    preferences = db.Column(db.Text, default='{"theme": "dark"}')
    
    # Relationships
    organizations = db.relationship('Organization', secondary='user_organization_link', back_populates='users')
    dashboards = db.relationship('Dashboard', back_populates='user')
    reports = db.relationship('Report', back_populates='user')
    alerts = db.relationship('Alert', back_populates='user')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_preferences(self):
        if self.preferences:
            return json.loads(self.preferences)
        return {"theme": "dark"}
    
    def set_preferences(self, preferences):
        self.preferences = json.dumps(preferences)
        
    def update_last_login(self):
        self.last_login = datetime.utcnow()

# Organization models (for MSP structure)
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_msp = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settings = db.Column(db.Text, default='{}')
    
    # Relationships
    users = db.relationship('User', secondary='user_organization_link', back_populates='organizations')
    sites = db.relationship('Site', back_populates='organization')
    dashboards = db.relationship('Dashboard', back_populates='organization')
    reports = db.relationship('Report', back_populates='organization')
    alert_rules = db.relationship('AlertRule', back_populates='organization')

# User-Organization link
user_organization_link = db.Table('user_organization_link',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organization.id'), primary_key=True)
)

# Site model (represents a customer site/location)
class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(256))
    contact_info = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    
    # Relationships
    organization = db.relationship('Organization', back_populates='sites')
    devices = db.relationship('Device', back_populates='site')
    
# Device model
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    device_type = db.Column(db.String(64))
    os_type = db.Column(db.String(64))
    os_version = db.Column(db.String(64))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    
    # Relationships
    site = db.relationship('Site', back_populates='devices')
    logs = db.relationship('Log', back_populates='device')
    metrics = db.relationship('Metric', back_populates='device')

# Data models
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    source_type = db.Column(db.Enum(DataSourceType), nullable=False)
    severity = db.Column(db.String(64))
    message = db.Column(db.Text, nullable=False)
    raw_data = db.Column(db.Text)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    
    # Relationships
    device = db.relationship('Device', back_populates='logs')

class Metric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    source_type = db.Column(db.Enum(DataSourceType), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    
    # Relationships
    device = db.relationship('Device', back_populates='metrics')

# Dashboard models
class Dashboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    layout = db.Column(db.Text, nullable=False, default='[]')  # JSON string for layout
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    # Relationships
    user = db.relationship('User', back_populates='dashboards')
    organization = db.relationship('Organization', back_populates='dashboards')
    widgets = db.relationship('Widget', back_populates='dashboard')
    
    def get_layout(self):
        return json.loads(self.layout)
    
    def set_layout(self, layout_data):
        self.layout = json.dumps(layout_data)

class Widget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    widget_type = db.Column(db.String(64), nullable=False)
    data_source = db.Column(db.Enum(DataSourceType), nullable=False)
    configuration = db.Column(db.Text, nullable=False)  # JSON string for config
    position_x = db.Column(db.Integer, default=0)
    position_y = db.Column(db.Integer, default=0)
    width = db.Column(db.Integer, default=1)
    height = db.Column(db.Integer, default=1)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboard.id'), nullable=False)
    
    # Relationships
    dashboard = db.relationship('Dashboard', back_populates='widgets')
    
    def get_configuration(self):
        return json.loads(self.configuration)
    
    def set_configuration(self, config_data):
        self.configuration = json.dumps(config_data)

# Report models
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    query = db.Column(db.Text, nullable=False)
    schedule = db.Column(db.String(64))  # Cron-style schedule
    format = db.Column(db.String(64), default='pdf')
    parameters = db.Column(db.Text)  # JSON string for parameters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    # Relationships
    user = db.relationship('User', back_populates='reports')
    organization = db.relationship('Organization', back_populates='reports')
    report_runs = db.relationship('ReportRun', back_populates='report')
    
    def get_parameters(self):
        if self.parameters:
            return json.loads(self.parameters)
        return {}
    
    def set_parameters(self, param_data):
        self.parameters = json.dumps(param_data)

class ReportRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), default='pending')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    file_path = db.Column(db.String(256))
    error_message = db.Column(db.Text)
    parameters_used = db.Column(db.Text)  # JSON string of parameters used
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)
    
    # Relationships
    report = db.relationship('Report', back_populates='report_runs')

# Alert models
class AlertRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    data_source = db.Column(db.Enum(DataSourceType), nullable=False)
    condition = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    enabled = db.Column(db.Boolean, default=True)
    cooldown_minutes = db.Column(db.Integer, default=15)
    notification_channels = db.Column(db.Text)  # JSON string for notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    # Relationships
    organization = db.relationship('Organization', back_populates='alert_rules')
    alerts = db.relationship('Alert', back_populates='alert_rule')
    
    def get_notification_channels(self):
        if self.notification_channels:
            return json.loads(self.notification_channels)
        return []
    
    def set_notification_channels(self, channels):
        self.notification_channels = json.dumps(channels)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    severity = db.Column(db.Enum(AlertSeverity), nullable=False)
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    alert_rule_id = db.Column(db.Integer, db.ForeignKey('alert_rule.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    alert_rule = db.relationship('AlertRule', back_populates='alerts')
    user = db.relationship('User', back_populates='alerts')

# User session and authentication models
class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(128), nullable=False, unique=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User')

class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    token_hash = db.Column(db.String(256), nullable=False)
    permissions = db.Column(db.Text)  # JSON string for permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User')
