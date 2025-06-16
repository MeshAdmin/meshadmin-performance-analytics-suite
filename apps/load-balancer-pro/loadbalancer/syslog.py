"""
Syslog forwarding module for the load balancer.
This module handles sending logs to external syslog servers.
"""

import socket
import logging
import threading
import time
import queue
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer.syslog")

class LogLevel(Enum):
    """Enum for syslog log levels."""
    DEBUG = 7
    INFO = 6
    NOTICE = 5
    WARNING = 4
    ERROR = 3
    CRITICAL = 2
    ALERT = 1
    EMERGENCY = 0
    
    @staticmethod
    def from_string(level_str: str) -> 'LogLevel':
        """Convert string level to enum."""
        mapping = {
            "debug": LogLevel.DEBUG,
            "informational": LogLevel.INFO,
            "notice": LogLevel.NOTICE,
            "warning": LogLevel.WARNING,
            "error": LogLevel.ERROR,
            "critical": LogLevel.CRITICAL,
            "alert": LogLevel.ALERT,
            "emergency": LogLevel.EMERGENCY
        }
        return mapping.get(level_str.lower(), LogLevel.INFO)
    
    @property
    def description(self) -> str:
        """Get description for UI display."""
        descriptions = {
            LogLevel.DEBUG: "Debug - Detailed debugging information",
            LogLevel.INFO: "Informational - Normal operational messages",
            LogLevel.NOTICE: "Notice - Normal but significant events",
            LogLevel.WARNING: "Warning - Potential issues that aren't errors",
            LogLevel.ERROR: "Error - Error conditions",
            LogLevel.CRITICAL: "Critical - Critical conditions",
            LogLevel.ALERT: "Alert - Immediate action required",
            LogLevel.EMERGENCY: "Emergency - System is unusable"
        }
        return descriptions[self]

class SyslogForwarder:
    """Handles forwarding logs to external syslog servers."""
    
    def __init__(self):
        self._enabled = False
        self._host = "127.0.0.1"
        self._port = 1514
        self._protocol = "udp"  # "tcp" or "udp"
        self._min_level = LogLevel.WARNING  # Default to WARNING level
        self._facility = 16  # local0
        self._hostname = socket.gethostname()
        self._app_name = "loadbalancer"
        self._lock = threading.RLock()
        self._log_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        
    def start(self) -> None:
        """Start the syslog forwarder."""
        with self._lock:
            if self._enabled and not self._worker_thread:
                self._stop_event.clear()
                self._worker_thread = threading.Thread(
                    target=self._log_sender_loop,
                    daemon=True
                )
                self._worker_thread.start()
                logger.info(f"Syslog forwarder started - forwarding to {self._host}:{self._port}/{self._protocol}")
    
    def stop(self) -> None:
        """Stop the syslog forwarder."""
        with self._lock:
            if self._worker_thread:
                self._stop_event.set()
                self._worker_thread.join(timeout=2.0)
                self._worker_thread = None
                logger.info("Syslog forwarder stopped")
    
    def configure(self, enabled: bool = False, host: str = "127.0.0.1", 
                 port: int = 1514, protocol: str = "udp", 
                 min_level: LogLevel = LogLevel.WARNING) -> None:
        """Configure the syslog forwarder."""
        with self._lock:
            was_enabled = self._enabled
            
            self._enabled = enabled
            self._host = host
            self._port = port
            self._protocol = protocol.lower()
            self._min_level = min_level
            
            # If enabled status changed, start or stop accordingly
            if was_enabled and not self._enabled:
                self.stop()
            elif not was_enabled and self._enabled:
                self.start()
            
            logger.info(f"Syslog forwarder configured: enabled={enabled}, host={host}, port={port}, protocol={protocol}, min_level={min_level.name}")
    
    def is_enabled(self) -> bool:
        """Check if forwarding is enabled."""
        with self._lock:
            return self._enabled
    
    def get_config(self) -> Dict:
        """Get current configuration."""
        with self._lock:
            return {
                "enabled": self._enabled,
                "host": self._host,
                "port": self._port,
                "protocol": self._protocol,
                "min_level": self._min_level.name,
                "min_level_value": self._min_level.value
            }
    
    def forward(self, level: LogLevel, message: str) -> None:
        """Forward a log message if it meets the minimum level."""
        with self._lock:
            if not self._enabled or level.value > self._min_level.value:
                return
            
            self._log_queue.put((level, message))
    
    def _log_sender_loop(self) -> None:
        """Background thread for sending logs."""
        sock = None
        try:
            if self._protocol == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:  # tcp
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self._host, self._port))
            
            while not self._stop_event.is_set():
                try:
                    # Get a log message from the queue with timeout
                    try:
                        level, message = self._log_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    # Format syslog message according to RFC 5424
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    pri = (self._facility * 8) + level.value
                    syslog_msg = f"<{pri}>{timestamp} {self._hostname} {self._app_name} - - - {message}"
                    
                    # Send the message
                    if self._protocol == "udp":
                        sock.sendto(syslog_msg.encode(), (self._host, self._port))
                    else:  # tcp
                        sock.sendall(syslog_msg.encode() + b'\n')
                    
                    # Mark task as done
                    self._log_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Error sending syslog message: {e}")
                    
                    # Try to reconnect if using TCP and connection lost
                    if self._protocol == "tcp" and isinstance(e, (ConnectionRefusedError, BrokenPipeError)):
                        try:
                            sock.close()
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.connect((self._host, self._port))
                        except Exception as connect_err:
                            logger.error(f"Failed to reconnect to syslog server: {connect_err}")
                            time.sleep(5)  # Wait before retry
                
        except Exception as e:
            logger.error(f"Error in syslog sender: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

# Global instance
syslog_forwarder = SyslogForwarder()

def log_debug(message: str) -> None:
    """Log a debug message."""
    logger.debug(message)
    syslog_forwarder.forward(LogLevel.DEBUG, message)

def log_info(message: str) -> None:
    """Log an info message."""
    logger.info(message)
    syslog_forwarder.forward(LogLevel.INFO, message)

def log_warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)
    syslog_forwarder.forward(LogLevel.WARNING, message)

def log_error(message: str) -> None:
    """Log an error message."""
    logger.error(message)
    syslog_forwarder.forward(LogLevel.ERROR, message)

def log_critical(message: str) -> None:
    """Log a critical message."""
    logger.critical(message)
    syslog_forwarder.forward(LogLevel.CRITICAL, message)