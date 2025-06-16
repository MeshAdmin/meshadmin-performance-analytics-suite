# NetFlow/sFlow Collector Configuration
import os

# Receiver settings
NETFLOW_PORT = 2055
SFLOW_PORT = 6343
MAX_PACKET_SIZE = 8192
BUFFER_SIZE = 10000

# Forwarder settings
DEFAULT_FORWARD_PORT = 9996

# Simulator settings
DEFAULT_SIMULATION_PORT = 9995
DEFAULT_PACKETS_PER_SECOND = 100
DEFAULT_SIMULATION_DURATION = 60  # seconds

# Storage settings
MAX_FLOWS_STORED = 1000000  # Maximum number of flows to keep in database
FLOW_RETENTION_DAYS = 7  # Number of days to keep flow data

# Minio settings
USE_EXTERNAL_STORAGE = os.environ.get('USE_EXTERNAL_STORAGE', 'false').lower() == 'true'
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'minio:9000')
MINIO_BUCKET = os.environ.get('MINIO_BUCKET', 'r369-bucket')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', '')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', '')
MINIO_SECURE = os.environ.get('MINIO_SECURE', 'false').lower() == 'true'

# MIB settings
UPLOAD_FOLDER = "uploads/mibs"
MAX_UPLOAD_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {"mib", "txt", "xml"}

# Analysis settings
ANOMALY_DETECTION_THRESHOLD = 0.05  # 5% of flows considered anomalous
MIN_FLOWS_FOR_ANALYSIS = 10  # Minimum number of flows needed for analysis
