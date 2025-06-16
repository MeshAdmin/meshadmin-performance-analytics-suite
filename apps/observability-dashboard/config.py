import os
from datetime import timedelta

class Config:
    """Application configuration settings"""
    
    # Flask configuration
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_BACKEND', 'redis://localhost:6379/0')
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Collector ports
    SYSLOG_PORT = int(os.environ.get('SYSLOG_PORT', 514))
    SNMP_PORT = int(os.environ.get('SNMP_PORT', 162))
    NETFLOW_PORT = int(os.environ.get('NETFLOW_PORT', 2055))
    SFLOW_PORT = int(os.environ.get('SFLOW_PORT', 6343))
    WINDOWS_EVENTS_PORT = int(os.environ.get('WINDOWS_EVENTS_PORT', 3268))
    OTEL_PORT = int(os.environ.get('OTEL_PORT', 4317))
    
    # Performance settings
    MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', 10000))
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', 30))
    
    # Email notification settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'alerts@observability.com')
    
    # Notification integrations
    SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
    PAGERDUTY_SERVICE_KEY = os.environ.get('PAGERDUTY_SERVICE_KEY', '')
    
    # UI settings
    DEFAULT_THEME = 'dark'
    ALLOWED_THEMES = ['dark', 'light', 'blue', 'green']
    
    # Reports settings
    REPORT_OUTPUT_DIR = os.environ.get('REPORT_OUTPUT_DIR', 'reports')
    
    # Temporary directory
    TEMP_DIR = os.environ.get('TEMP_DIR', '/tmp')