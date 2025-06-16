from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from database import db

class Device(db.Model):
    """Model for network devices sending flow data"""
    __tablename__ = 'device'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    device_type = db.Column(db.String(64))
    flow_type = db.Column(db.String(32))  # netflow or sflow
    flow_version = db.Column(db.String(16))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    flow_data = db.relationship('FlowData', backref='device', lazy=True)
    
    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'

class FlowData(db.Model):
    """Model for flow data records"""
    __tablename__ = 'flow_data'
    __table_args__ = (
        db.Index('idx_flow_timestamp', 'timestamp'),
        db.Index('idx_flow_device_timestamp', 'device_id', 'timestamp'),
        db.Index('idx_flow_src_dst', 'src_ip', 'dst_ip')
    )
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    flow_type = db.Column(db.String(32), nullable=False)  # netflow, sflow + version
    src_ip = db.Column(db.String(45), nullable=False)
    dst_ip = db.Column(db.String(45), nullable=False)
    src_port = db.Column(db.Integer)
    dst_port = db.Column(db.Integer)
    protocol = db.Column(db.Integer)
    tos = db.Column(db.Integer)
    bytes = db.Column(db.BigInteger)
    packets = db.Column(db.BigInteger)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data = db.Column(db.Text)  # JSON string of the original flow data
    
    def __repr__(self):
        return f'<FlowData {self.id} {self.src_ip}:{self.src_port} -> {self.dst_ip}:{self.dst_port}>'

class FlowTemplate(db.Model):
    """Model for flow templates used in simulation"""
    __tablename__ = 'flow_template'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    flow_type = db.Column(db.String(32), nullable=False)  # netflow, sflow + version
    template_data = db.Column(db.Text, nullable=False)  # JSON string of template fields
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    simulations = db.relationship('SimulationConfig', backref='template', lazy=True)
    
    def __repr__(self):
        return f'<FlowTemplate {self.name} ({self.flow_type})>'

class SimulationConfig(db.Model):
    """Model for simulation configurations"""
    __tablename__ = 'simulation_config'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('flow_template.id'), nullable=True)
    flow_type = db.Column(db.String(32), nullable=False)
    flow_version = db.Column(db.String(16), nullable=False)
    packets_per_second = db.Column(db.Integer, default=100)
    duration = db.Column(db.Integer, default=60)  # seconds
    status = db.Column(db.String(32), default='pending')  # pending, running, completed, error
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SimulationConfig {self.id} {self.flow_type} {self.status}>'

class ForwardLog(db.Model):
    """
    Model for logging flow forwarding activity
    Records statistics about forwarded flows
    """
    __tablename__ = 'forward_log'
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('forward_target.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Statistics
    success_count = db.Column(db.Integer, default=0)  # Number of successfully forwarded flows
    failure_count = db.Column(db.Integer, default=0)  # Number of failed forwarding attempts
    
    # Flow types
    flow_type = db.Column(db.String(32))  # netflow, sflow
    flow_version = db.Column(db.String(16))
    
    # Error information
    error_message = db.Column(db.String(512))
    
    # Relationship to the target
    target = db.relationship('ForwardTarget', backref=db.backref('logs', lazy=True))
    
    def __repr__(self):
        return f'<ForwardLog {self.id}: {self.target.name if self.target else "Unknown"} - S:{self.success_count}/F:{self.failure_count}>'


class ForwardTarget(db.Model):
    """Model for flow forwarding targets"""
    __tablename__ = 'forward_target'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(16), default='udp')  # udp or tcp
    flow_type = db.Column(db.String(32), nullable=False)  # netflow, sflow + version 
    flow_version = db.Column(db.String(16))
    
    # Basic filtering options
    filter_src_ip = db.Column(db.String(45))  # Filter by source IP (CIDR supported)
    filter_dst_ip = db.Column(db.String(45))  # Filter by destination IP (CIDR supported)
    filter_protocol = db.Column(db.String(64))  # Comma-separated list of protocols
    
    # Advanced filtering options
    filter_src_port_min = db.Column(db.Integer)  # Filter by source port range
    filter_src_port_max = db.Column(db.Integer)
    filter_dst_port_min = db.Column(db.Integer)  # Filter by destination port range
    filter_dst_port_max = db.Column(db.Integer)
    filter_tos = db.Column(db.String(32))  # Type of Service filters (comma-separated)
    filter_bytes_min = db.Column(db.BigInteger)  # Filter by flow size in bytes
    filter_bytes_max = db.Column(db.BigInteger)
    filter_packets_min = db.Column(db.BigInteger)  # Filter by packet count
    filter_packets_max = db.Column(db.BigInteger)
    
    # Additional filter rules in JSON format
    filter_custom_rules = db.Column(db.JSON)  # Custom filtering rules
    
    # Security options
    use_tls = db.Column(db.Boolean, default=False)  # Use TLS for TCP connections
    tls_cert = db.Column(db.String(512))  # Path to certificate
    tls_key = db.Column(db.String(512))  # Path to private key
    
    # Storage options
    store_locally = db.Column(db.Boolean, default=True)  # Store copy in local database
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def has_advanced_filters(self):
        """Check if this target is using any advanced filters"""
        return any([
            self.filter_src_port_min is not None, 
            self.filter_src_port_max is not None,
            self.filter_dst_port_min is not None, 
            self.filter_dst_port_max is not None,
            self.filter_tos is not None,
            self.filter_bytes_min is not None,
            self.filter_bytes_max is not None,
            self.filter_packets_min is not None,
            self.filter_packets_max is not None,
            self.filter_custom_rules is not None
        ])
    
    def __repr__(self):
        return f'<ForwardTarget {self.name} {self.ip_address}:{self.port}>'

class MibFile(db.Model):
    """Model for MIB files uploaded for device-specific analysis"""
    __tablename__ = 'mib_file'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(512), nullable=False)
    device_type = db.Column(db.String(64))
    description = db.Column(db.Text)
    parsed = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MibFile {self.filename}>'

class AnalysisResult(db.Model):
    """Model for AI analysis results"""
    __tablename__ = 'analysis_result'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    analysis_type = db.Column(db.String(64), nullable=False)  # anomaly, traffic_pattern, etc.
    result_data = db.Column(db.Text, nullable=False)  # JSON string of analysis results
    confidence = db.Column(db.Float)  # Confidence score for the analysis
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref='analysis_results')
    
    def __repr__(self):
        return f'<AnalysisResult {self.id} {self.analysis_type}>'
class Permission:
    """Constants for different permission levels"""
    VIEW_FLOW_DATA = 1
    MANAGE_DEVICES = 2
    MANAGE_FORWARD_TARGETS = 4
    MANAGE_SIMULATIONS = 8
    MANAGE_MIBS = 16
    ACCESS_API = 32
    ADMIN = 64

class Role(db.Model):
    """Role model for user permissions"""
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    permissions = db.Column(db.JSON, default={})
    
    # Relationships
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    @staticmethod
    def insert_roles():
        """Create or update predefined roles"""
        roles = {
            'User': [Permission.VIEW_FLOW_DATA],
            'Operator': [Permission.VIEW_FLOW_DATA, Permission.MANAGE_DEVICES, 
                         Permission.MANAGE_FORWARD_TARGETS, Permission.ACCESS_API],
            'Engineer': [Permission.VIEW_FLOW_DATA, Permission.MANAGE_DEVICES, 
                        Permission.MANAGE_FORWARD_TARGETS, Permission.MANAGE_SIMULATIONS, 
                        Permission.MANAGE_MIBS, Permission.ACCESS_API],
            'Administrator': [Permission.VIEW_FLOW_DATA, Permission.MANAGE_DEVICES, 
                             Permission.MANAGE_FORWARD_TARGETS, Permission.MANAGE_SIMULATIONS, 
                             Permission.MANAGE_MIBS, Permission.ACCESS_API, Permission.ADMIN]
        }
        
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            db.session.add(role)
        db.session.commit()
    
    def add_permission(self, perm):
        if self.permissions is None:
            self.permissions = {}
        
        if 'permissions' not in self.permissions:
            self.permissions = {'permissions': []}
            
        if perm not in self.permissions['permissions']:
            self.permissions['permissions'].append(perm)
    
    def remove_permission(self, perm):
        if self.permissions and 'permissions' in self.permissions and perm in self.permissions['permissions']:
            self.permissions['permissions'].remove(perm)
    
    def reset_permissions(self):
        self.permissions = {'permissions': []}
    
    def has_permission(self, perm):
        if self.permissions is None or 'permissions' not in self.permissions:
            return False
        return perm in self.permissions['permissions']
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    """User model with authentication and role-based access control"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(120))
    company = db.Column(db.String(120))
    active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    
    # Relationships
    devices = db.relationship('Device', secondary='user_device', backref='users')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)
    
    @property
    def is_active(self):
        """Check if user is active"""
        return self.active
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def has_permission(self, perm):
        """Check if user has a specific permission"""
        if self.role:
            return self.role.has_permission(perm)
        return False
    
    def is_administrator(self):
        """Check if user is an administrator"""
        return self.has_permission(Permission.ADMIN)
    
    def can_access_device(self, device_id):
        """Check if user can access a specific device"""
        # Administrators can access all devices
        if self.is_administrator():
            return True
        
        # Check if device is in user's device list
        device = Device.query.get(device_id)
        return device in self.devices
    
    def get_accessible_devices(self):
        """Get all devices this user can access"""
        if self.is_administrator():
            return Device.query.all()
        return self.devices
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserDevice(db.Model):
    """Association table for many-to-many relationship between users and devices"""
    __tablename__ = 'user_device'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserDevice {self.user_id}:{self.device_id}>'
