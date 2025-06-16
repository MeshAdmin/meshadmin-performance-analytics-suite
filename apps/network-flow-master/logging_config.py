#!/usr/bin/env python3
"""
Comprehensive logging configuration for FlowVision
Provides structured logging, log rotation, performance metrics, and security audit trails.
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading
from contextlib import contextmanager

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': threading.get_ident()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName',
                          'process', 'exc_info', 'exc_text', 'stack_info', 'getMessage']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

class ContextualFilter(logging.Filter):
    """Filter to add contextual information to log records"""
    
    def __init__(self):
        super().__init__()
        self.context = threading.local()
    
    def filter(self, record):
        # Add request context if available
        if hasattr(self.context, 'request_id'):
            record.request_id = self.context.request_id
        if hasattr(self.context, 'user_id'):
            record.user_id = self.context.user_id
        if hasattr(self.context, 'device_ip'):
            record.device_ip = self.context.device_ip
        if hasattr(self.context, 'flow_type'):
            record.flow_type = self.context.flow_type
        
        return True
    
    def set_context(self, **kwargs):
        """Set context variables for current thread"""
        for key, value in kwargs.items():
            setattr(self.context, key, value)
    
    def clear_context(self):
        """Clear all context variables for current thread"""
        for attr in list(vars(self.context).keys()):
            delattr(self.context, attr)

class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self, logger_name: str = 'performance'):
        self.logger = logging.getLogger(logger_name)
        self.timings = {}
    
    def start_timer(self, operation: str, context: Optional[Dict[str, Any]] = None):
        """Start timing an operation"""
        timer_key = f"{operation}_{threading.get_ident()}"
        self.timings[timer_key] = {
            'start_time': datetime.now(timezone.utc),
            'operation': operation,
            'context': context or {}
        }
    
    def end_timer(self, operation: str, additional_context: Optional[Dict[str, Any]] = None):
        """End timing an operation and log the duration"""
        timer_key = f"{operation}_{threading.get_ident()}"
        
        if timer_key not in self.timings:
            self.logger.warning(f"No timer found for operation: {operation}")
            return
        
        timer_data = self.timings.pop(timer_key)
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - timer_data['start_time']).total_seconds() * 1000
        
        context = timer_data['context'].copy()
        if additional_context:
            context.update(additional_context)
        
        self.logger.info(
            f"Operation completed: {operation}",
            extra={
                'operation': operation,
                'duration_ms': round(duration_ms, 2),
                'start_time': timer_data['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                **context
            }
        )
    
    @contextmanager
    def timer(self, operation: str, context: Optional[Dict[str, Any]] = None):
        """Context manager for timing operations"""
        self.start_timer(operation, context)
        try:
            yield
        finally:
            self.end_timer(operation)

class SecurityLogger:
    """Logger for security events and audit trails"""
    
    def __init__(self, logger_name: str = 'security'):
        self.logger = logging.getLogger(logger_name)
    
    def log_authentication(self, username: str, success: bool, ip_address: str, 
                          user_agent: str = None, additional_info: Dict[str, Any] = None):
        """Log authentication attempts"""
        event_type = "authentication_success" if success else "authentication_failure"
        
        log_data = {
            'event_type': event_type,
            'username': username,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'success': success
        }
        
        if additional_info:
            log_data.update(additional_info)
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, f"Authentication attempt: {username}", extra=log_data)
    
    def log_authorization(self, username: str, resource: str, action: str, 
                         granted: bool, ip_address: str = None):
        """Log authorization attempts"""
        event_type = "authorization_granted" if granted else "authorization_denied"
        
        log_data = {
            'event_type': event_type,
            'username': username,
            'resource': resource,
            'action': action,
            'granted': granted,
            'ip_address': ip_address
        }
        
        level = logging.INFO if granted else logging.WARNING
        self.logger.log(level, f"Authorization check: {username} -> {resource}:{action}", 
                       extra=log_data)
    
    def log_flow_event(self, event_type: str, device_ip: str, flow_type: str,
                      packet_count: int = None, error_message: str = None):
        """Log flow processing security events"""
        log_data = {
            'event_type': f"flow_{event_type}",
            'device_ip': device_ip,
            'flow_type': flow_type,
            'packet_count': packet_count
        }
        
        if error_message:
            log_data['error_message'] = error_message
            level = logging.ERROR
        else:
            level = logging.INFO
        
        self.logger.log(level, f"Flow event: {event_type} from {device_ip}", extra=log_data)

class FlowVisionLogger:
    """Main logging configuration class for FlowVision"""
    
    def __init__(self, log_dir: str = 'logs', log_level: str = 'INFO', 
                 enable_json: bool = True, enable_file_rotation: bool = True):
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper())
        self.enable_json = enable_json
        self.enable_file_rotation = enable_file_rotation
        
        # Create logs directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize contextual filter
        self.contextual_filter = ContextualFilter()
        
        # Initialize specialized loggers
        self.performance = PerformanceLogger()
        self.security = SecurityLogger()
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure all logging handlers and formatters"""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(self.log_level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if self.enable_json:
            console_handler.setFormatter(JsonFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        console_handler.addFilter(self.contextual_filter)
        root_logger.addHandler(console_handler)
        
        # Application log file handler
        if self.enable_file_rotation:
            app_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(self.log_dir, 'flowvision.log'),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        else:
            app_file_handler = logging.FileHandler(
                os.path.join(self.log_dir, 'flowvision.log')
            )
        
        if self.enable_json:
            app_file_handler.setFormatter(JsonFormatter())
        else:
            app_file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        app_file_handler.addFilter(self.contextual_filter)
        root_logger.addHandler(app_file_handler)
        
        # Error log file handler (only errors and critical)
        error_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'errors.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(JsonFormatter() if self.enable_json 
                                       else logging.Formatter(
                                           '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                                       ))
        error_file_handler.addFilter(self.contextual_filter)
        root_logger.addHandler(error_file_handler)
        
        # Performance log file handler
        perf_logger = logging.getLogger('performance')
        perf_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'performance.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        perf_handler.setFormatter(JsonFormatter())
        perf_handler.addFilter(self.contextual_filter)
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root logger
        
        # Security log file handler  
        sec_logger = logging.getLogger('security')
        sec_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'security.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        sec_handler.setFormatter(JsonFormatter())
        sec_handler.addFilter(self.contextual_filter)
        sec_logger.addHandler(sec_handler)
        sec_logger.setLevel(logging.INFO)
        sec_logger.propagate = False  # Don't propagate to root logger
        
        # Flow processing log file handler
        flow_logger = logging.getLogger('flow_processor')
        flow_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'flows.log'),
            maxBytes=20*1024*1024,  # 20MB (flows generate lots of logs)
            backupCount=10
        )
        flow_handler.setFormatter(JsonFormatter())
        flow_handler.addFilter(self.contextual_filter)
        flow_logger.addHandler(flow_handler)
        flow_logger.setLevel(logging.INFO)
        flow_logger.propagate = True  # Also send to root logger
    
    def set_context(self, **kwargs):
        """Set logging context for current thread"""
        self.contextual_filter.set_context(**kwargs)
    
    def clear_context(self):
        """Clear logging context for current thread"""
        self.contextual_filter.clear_context()
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary logging context"""
        self.set_context(**kwargs)
        try:
            yield
        finally:
            self.clear_context()

# Global logger instance
_logger_instance = None

def setup_logging(log_dir: str = 'logs', log_level: str = 'INFO', 
                 enable_json: bool = True, enable_file_rotation: bool = True) -> FlowVisionLogger:
    """Setup comprehensive logging configuration"""
    global _logger_instance
    _logger_instance = FlowVisionLogger(log_dir, log_level, enable_json, enable_file_rotation)
    return _logger_instance

def get_logger() -> FlowVisionLogger:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = setup_logging()
    return _logger_instance

def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger"""
    return get_logger().performance

def get_security_logger() -> SecurityLogger:
    """Get the security logger"""
    return get_logger().security

# Convenience functions for common logging operations
def log_flow_packet_received(device_ip: str, flow_type: str, packet_size: int):
    """Log when a flow packet is received"""
    logger = logging.getLogger('flow_processor')
    with get_logger().context(device_ip=device_ip, flow_type=flow_type):
        logger.debug(f"Received {flow_type} packet from {device_ip}",
                    extra={'event_type': 'packet_received', 'packet_size': packet_size,
                          'device_ip': device_ip, 'flow_type': flow_type})

def log_flow_processing_error(device_ip: str, flow_type: str, error: str):
    """Log flow processing errors"""
    logger = logging.getLogger('flow_processor')
    with get_logger().context(device_ip=device_ip, flow_type=flow_type):
        logger.error(f"Flow processing error from {device_ip}: {error}",
                    extra={'event_type': 'processing_error', 'error_message': error,
                          'device_ip': device_ip, 'flow_type': flow_type})

def log_database_operation(operation: str, table: str, duration_ms: float, success: bool):
    """Log database operations"""
    logger = logging.getLogger('database')
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"Database {operation} on {table}",
              extra={
                  'event_type': 'database_operation',
                  'operation': operation,
                  'table': table,
                  'duration_ms': duration_ms,
                  'success': success
              })

if __name__ == '__main__':
    # Test the logging configuration
    main_logger = setup_logging(log_level='DEBUG')
    
    logger = logging.getLogger(__name__)
    
    # Test basic logging
    logger.info("Testing FlowVision logging configuration")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test contextual logging
    with main_logger.context(request_id="test-123", user_id="admin"):
        logger.info("Testing contextual logging")
    
    # Test performance logging
    with main_logger.performance.timer("test_operation", {"param": "value"}):
        import time
        time.sleep(0.1)
    
    # Test security logging
    main_logger.security.log_authentication("testuser", True, "192.168.1.100", "Test-Agent/1.0")
    main_logger.security.log_authorization("testuser", "/api/flows", "read", True, "192.168.1.100")
    
    # Test convenience functions
    log_flow_packet_received("192.168.1.50", "netflow5", 1024)
    log_flow_processing_error("192.168.1.51", "sflow5", "Invalid packet format")
    log_database_operation("SELECT", "flow_data", 25.5, True)
    
    print("\nLogging test completed. Check the logs/ directory for output files.")
    print("Log files created:")
    print("  - logs/flowvision.log (main application log)")
    print("  - logs/errors.log (errors only)")
    print("  - logs/performance.log (performance metrics)")
    print("  - logs/security.log (security events)")
    print("  - logs/flows.log (flow processing events)") 