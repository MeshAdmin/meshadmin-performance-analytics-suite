#!/usr/bin/env python3
"""
Configuration validation system for FlowVision
"""

import os
import json
import logging
from typing import Dict, Any, Union, List, Optional
from dataclasses import dataclass
from enum import Enum
import ipaddress
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when configuration validation fails"""
    pass

class ConfigType(Enum):
    """Configuration value types"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    PORT = "port"
    PATH = "path"
    LIST = "list"

@dataclass
class ConfigField:
    """Configuration field definition with validation rules"""
    name: str
    config_type: ConfigType
    default: Any = None
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    env_var: Optional[str] = None
    description: str = ""
    
    def __post_init__(self):
        """Set default environment variable name if not provided"""
        if self.env_var is None:
            self.env_var = self.name.upper()

class ConfigValidator:
    """Main configuration validator class"""
    
    def __init__(self):
        self.schema = self._define_schema()
        self.validation_errors = []
    
    def _define_schema(self) -> Dict[str, ConfigField]:
        """Define the configuration schema with all fields and validation rules"""
        return {
            # Network settings
            'netflow_port': ConfigField(
                name='netflow_port',
                config_type=ConfigType.PORT,
                default=2055,
                min_value=1,
                max_value=65535,
                description="Port number for NetFlow collector"
            ),
            'sflow_port': ConfigField(
                name='sflow_port',
                config_type=ConfigType.PORT,
                default=6343,
                min_value=1,
                max_value=65535,
                description="Port number for sFlow collector"
            ),
            'max_packet_size': ConfigField(
                name='max_packet_size',
                config_type=ConfigType.INTEGER,
                default=8192,
                min_value=512,
                max_value=65536,
                description="Maximum packet size in bytes"
            ),
            'buffer_size': ConfigField(
                name='buffer_size',
                config_type=ConfigType.INTEGER,
                default=10000,
                min_value=100,
                max_value=1000000,
                description="Buffer size for packet processing"
            ),
            
            # Storage settings
            'max_flows_stored': ConfigField(
                name='max_flows_stored',
                config_type=ConfigType.INTEGER,
                default=1000000,
                min_value=1000,
                max_value=100000000,
                description="Maximum number of flows to store"
            ),
            'flow_retention_days': ConfigField(
                name='flow_retention_days',
                config_type=ConfigType.INTEGER,
                default=7,
                min_value=1,
                max_value=365,
                description="Number of days to retain flow data"
            ),
            'use_external_storage': ConfigField(
                name='use_external_storage',
                config_type=ConfigType.BOOLEAN,
                default=False,
                description="Enable external storage (MinIO)"
            ),
            'minio_endpoint': ConfigField(
                name='minio_endpoint',
                config_type=ConfigType.STRING,
                default='minio:9000',
                pattern=r'^[a-zA-Z0-9.-]+:[0-9]+$',
                description="MinIO endpoint address"
            ),
            'minio_bucket': ConfigField(
                name='minio_bucket',
                config_type=ConfigType.STRING,
                default='flowvision-bucket',
                description="MinIO bucket name"
            ),
            
            # Analysis settings
            'anomaly_detection_threshold': ConfigField(
                name='anomaly_detection_threshold',
                config_type=ConfigType.FLOAT,
                default=0.05,
                min_value=0.001,
                max_value=1.0,
                description="Threshold for anomaly detection (0.0-1.0)"
            ),
            'min_flows_for_analysis': ConfigField(
                name='min_flows_for_analysis',
                config_type=ConfigType.INTEGER,
                default=10,
                min_value=1,
                max_value=10000,
                description="Minimum flows required for analysis"
            ),
            
            # Logging settings
            'log_level': ConfigField(
                name='log_level',
                config_type=ConfigType.STRING,
                default='INFO',
                allowed_values=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                description="Application log level"
            ),
            'log_dir': ConfigField(
                name='log_dir',
                config_type=ConfigType.PATH,
                default='logs',
                description="Directory for log files"
            ),
            
            # Upload settings
            'upload_folder': ConfigField(
                name='upload_folder',
                config_type=ConfigType.PATH,
                default='uploads/mibs',
                description="Directory for uploaded files"
            ),
            'max_upload_size': ConfigField(
                name='max_upload_size',
                config_type=ConfigType.INTEGER,
                default=16 * 1024 * 1024,  # 16MB
                min_value=1024,  # 1KB
                max_value=100 * 1024 * 1024,  # 100MB
                description="Maximum upload file size in bytes"
            ),
            'allowed_extensions': ConfigField(
                name='allowed_extensions',
                config_type=ConfigType.LIST,
                default=['mib', 'txt', 'xml'],
                description="Allowed file extensions for uploads"
            )
        }
    
    def _validate_type(self, field: ConfigField, value: Any) -> Any:
        """Validate and convert value to the correct type"""
        if value is None:
            if field.required:
                raise ValidationError(f"Required field '{field.name}' is missing")
            return field.default
        
        if field.config_type == ConfigType.INTEGER:
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError(f"Field '{field.name}' must be an integer")
            elif not isinstance(value, int):
                raise ValidationError(f"Field '{field.name}' must be an integer")
        
        elif field.config_type == ConfigType.FLOAT:
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    raise ValidationError(f"Field '{field.name}' must be a float")
            elif not isinstance(value, (int, float)):
                raise ValidationError(f"Field '{field.name}' must be a float")
            value = float(value)
        
        elif field.config_type == ConfigType.BOOLEAN:
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes', 'on')
            elif not isinstance(value, bool):
                raise ValidationError(f"Field '{field.name}' must be a boolean")
        
        elif field.config_type == ConfigType.STRING:
            if not isinstance(value, str):
                value = str(value)
        
        elif field.config_type == ConfigType.PORT:
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError(f"Field '{field.name}' must be a valid port number")
            if not isinstance(value, int) or not (1 <= value <= 65535):
                raise ValidationError(f"Field '{field.name}' must be a port number (1-65535)")
        
        elif field.config_type == ConfigType.PATH:
            if not isinstance(value, str):
                value = str(value)
            # Validate path format but don't require it to exist
            try:
                Path(value)
            except Exception:
                raise ValidationError(f"Field '{field.name}' must be a valid path")
        
        elif field.config_type == ConfigType.LIST:
            if isinstance(value, str):
                # Try to parse as JSON, fallback to comma-separated
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = [item.strip() for item in value.split(',') if item.strip()]
            elif not isinstance(value, list):
                raise ValidationError(f"Field '{field.name}' must be a list")
        
        return value
    
    def _validate_constraints(self, field: ConfigField, value: Any) -> None:
        """Validate field constraints (ranges, patterns, etc.)"""
        if value is None:
            return
        
        # Check numeric ranges
        if field.min_value is not None and isinstance(value, (int, float)):
            if value < field.min_value:
                raise ValidationError(f"Field '{field.name}' must be >= {field.min_value}")
        
        if field.max_value is not None and isinstance(value, (int, float)):
            if value > field.max_value:
                raise ValidationError(f"Field '{field.name}' must be <= {field.max_value}")
        
        # Check allowed values
        if field.allowed_values is not None:
            if value not in field.allowed_values:
                raise ValidationError(f"Field '{field.name}' must be one of: {field.allowed_values}")
        
        # Check pattern
        if field.pattern is not None and isinstance(value, str):
            if not re.match(field.pattern, value):
                raise ValidationError(f"Field '{field.name}' does not match required pattern")
    
    def validate_field(self, field_name: str, value: Any) -> Any:
        """Validate a single configuration field"""
        if field_name not in self.schema:
            raise ValidationError(f"Unknown configuration field: {field_name}")
        
        field = self.schema[field_name]
        
        # Type validation and conversion
        validated_value = self._validate_type(field, value)
        
        # Constraint validation
        self._validate_constraints(field, validated_value)
        
        return validated_value
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete configuration dictionary"""
        validated_config = {}
        self.validation_errors = []
        
        for field_name, field in self.schema.items():
            value = config.get(field_name)
            try:
                validated_config[field_name] = self.validate_field(field_name, value)
            except ValidationError as e:
                self.validation_errors.append(str(e))
        
        if self.validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(self.validation_errors)
            raise ValidationError(error_msg)
        
        return validated_config
    
    def load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        for field_name, field in self.schema.items():
            env_value = os.environ.get(field.env_var)
            if env_value is not None:
                try:
                    config[field_name] = self.validate_field(field_name, env_value)
                except ValidationError as e:
                    self.validation_errors.append(f"Environment variable {field.env_var}: {str(e)}")
            else:
                config[field_name] = field.default
        
        return config

# Global validator instance
_validator = ConfigValidator()

def validate_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration dictionary"""
    global _validator
    return _validator.validate_config(config)

def load_from_environment() -> Dict[str, Any]:
    """Load and validate configuration from environment variables"""
    global _validator
    return _validator.load_from_env()

def get_config_schema() -> Dict[str, ConfigField]:
    """Get the configuration schema"""
    global _validator
    return _validator.schema

if __name__ == '__main__':
    # Test the configuration validator
    print("FlowVision Configuration Validator Test")
    print("=" * 50)
    
    # Test validation of current config.py values
    test_config = {
        'netflow_port': 2055,
        'sflow_port': 6343,
        'max_packet_size': 8192,
        'buffer_size': 10000,
        'max_flows_stored': 1000000,
        'flow_retention_days': 7,
        'use_external_storage': False,
        'minio_endpoint': 'minio:9000',
        'minio_bucket': 'flowvision-bucket',
        'log_level': 'INFO'
    }
    
    try:
        validated_config = validate_configuration(test_config)
        print("✅ Configuration validation passed!")
        print(f"Validated {len(validated_config)} configuration fields")
    except ValidationError as e:
        print("❌ Configuration validation failed:")
        print(str(e))
    
    # Test invalid configuration
    print("\nTesting invalid configuration:")
    invalid_config = {
        'netflow_port': 70000,  # Invalid port
        'sflow_port': 'invalid',  # Invalid type
        'max_packet_size': -1,  # Invalid range
        'log_level': 'INVALID'  # Invalid value
    }
    
    try:
        validate_configuration(invalid_config)
        print("❌ Should have failed validation")
    except ValidationError as e:
        print("✅ Correctly caught validation errors:")
        for error in str(e).split('\n')[1:]:  # Skip first line
            if error.strip():
                print(f"  - {error.strip()}")
    
    print("\nConfiguration validation system ready!") 