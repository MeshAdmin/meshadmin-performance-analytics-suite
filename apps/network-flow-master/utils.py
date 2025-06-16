import socket
import ipaddress
import logging
from datetime import datetime, timedelta
import os
from flask import flash
from models import FlowData, Device
from app import db

logger = logging.getLogger(__name__)

def is_valid_ip(ip_str):
    """
    Check if a string is a valid IP address
    
    Args:
        ip_str (str): IP address string to check
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def is_valid_port(port):
    """
    Check if a port number is valid
    
    Args:
        port (int): Port number to check
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        port_num = int(port)
        return 0 < port_num < 65536
    except (ValueError, TypeError):
        return False

def get_protocol_name(protocol_number):
    """
    Get the name of a protocol by number
    
    Args:
        protocol_number (int): Protocol number
    
    Returns:
        str: Protocol name
    """
    protocols = {
        1: "ICMP",
        6: "TCP",
        17: "UDP",
        47: "GRE",
        50: "ESP",
        51: "AH",
        58: "IPv6-ICMP",
        89: "OSPF",
        132: "SCTP"
    }
    
    return protocols.get(protocol_number, f"Protocol {protocol_number}")

def format_bytes(num_bytes):
    """
    Format bytes into a human-readable string
    
    Args:
        num_bytes (int): Number of bytes
    
    Returns:
        str: Formatted string (e.g., "1.23 MB")
    """
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{num_bytes / (1024 ** 3):.2f} GB"

def get_time_series_labels(start_time, end_time, interval='1h'):
    """
    Generate time labels for time series data
    
    Args:
        start_time (datetime): Start time
        end_time (datetime): End time
        interval (str): Time interval ('15m', '1h', '1d')
    
    Returns:
        list: List of formatted time labels
    """
    labels = []
    current = start_time
    
    if interval == '15m':
        delta = timedelta(minutes=15)
        fmt = '%H:%M'
    elif interval == '1h':
        delta = timedelta(hours=1)
        fmt = '%H:%M'
    elif interval == '1d':
        delta = timedelta(days=1)
        fmt = '%Y-%m-%d'
    else:
        delta = timedelta(hours=1)
        fmt = '%H:%M'
    
    while current <= end_time:
        labels.append(current.strftime(fmt))
        current += delta
    
    return labels

def cleanup_old_flows():
    """Remove flow data older than the configured retention period"""
    try:
        from config import FLOW_RETENTION_DAYS
        
        cutoff_date = datetime.utcnow() - timedelta(days=FLOW_RETENTION_DAYS)
        count = db.session.query(FlowData).filter(FlowData.timestamp < cutoff_date).delete()
        db.session.commit()
        
        logger.info(f"Cleaned up {count} flow records older than {FLOW_RETENTION_DAYS} days")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up old flows: {str(e)}")
        db.session.rollback()
        return 0

def clear_unused_devices():
    """Remove devices that have no associated flow data"""
    try:
        # Find devices with no associated flows
        devices = Device.query.outerjoin(FlowData).filter(FlowData.id == None).all()
        count = len(devices)
        
        for device in devices:
            db.session.delete(device)
        
        db.session.commit()
        
        logger.info(f"Removed {count} unused device records")
        return count
    except Exception as e:
        logger.error(f"Error clearing unused devices: {str(e)}")
        db.session.rollback()
        return 0

def validate_upload(file, allowed_extensions):
    """
    Validate a file upload
    
    Args:
        file: The uploaded file object
        allowed_extensions (set): Set of allowed file extensions
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not file or file.filename == '':
        flash('No file selected', 'error')
        return False
    
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        flash(f'File type not allowed. Supported types: {", ".join(allowed_extensions)}', 'error')
        return False
    
    return True

def ensure_upload_dir(directory):
    """
    Ensure that an upload directory exists
    
    Args:
        directory (str): Directory path
    """
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        raise
