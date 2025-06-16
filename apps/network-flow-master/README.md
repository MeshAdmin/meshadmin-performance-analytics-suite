# FlowVision - NetFlow/sFlow Analyzer

FlowVision is a cutting-edge NetFlow/sFlow analytics platform that transforms complex network data into actionable insights through intelligent processing and visualization.

## Key Features

- **Multi-Protocol Support**: Automatically detects and processes NetFlow v5/v9/IPFIX and sFlow v5
- **High-Performance Flow Processing**: Optimized for handling ~500GB of daily ingest volume
- **Advanced Flow Forwarding**: Acts as a flow collector and relay with filtering capabilities
- **AI-Powered Insights**: Anomaly detection, traffic pattern analysis, and network behavior classification
- **MIB Management**: Upload, parse, and extract device information from MIB files
- **Flow Simulation**: Generate test flow data for development and testing
- **Role-Based Access Control**: Control access to device data based on user roles
- **Containerized Deployment**: Designed to run in a Docker environment

## Architecture

FlowVision is built with a modular architecture separating flow receiving, processing, simulation, and forwarding components:

- **Flow Receiver**: Listens for NetFlow and sFlow packets on configurable ports
- **Flow Processor**: Processes, validates, and stores flow data
- **Flow Forwarder**: Forwards flows to other collectors based on filtering rules
- **Flow Simulator**: Generates test flow data for development and testing
- **AI Insights**: Advanced analytics engine for detecting anomalies and patterns
- **MIB Parser**: Parses and extracts device information from MIB files
- **Web Interface**: Flask-based web application for visualization and management

## Technology Stack

- **Backend**: Python 3.11+
- **Web Framework**: Flask
- **Database**: PostgreSQL
- **Authentication**: Flask-Login
- **Data Processing**: NumPy, pandas, scikit-learn
- **Visualization**: Chart.js
- **External Storage**: MinIO (optional)
- **Container Orchestration**: Docker & Docker Compose
- **Flow Processing**: Custom high-performance NetFlow/sFlow parsers

## Configuration

The application can be configured through environment variables:

- **DATABASE_URL**: PostgreSQL connection string
- **SESSION_SECRET**: Secret key for session management
- **FLOW_RETENTION_DAYS**: Number of days to retain flow data (default: 7)
- **NETFLOW_PORT**: Port to listen for NetFlow data (default: 2055)
- **SFLOW_PORT**: Port to listen for sFlow data (default: 6343)
- **USE_EXTERNAL_STORAGE**: Use MinIO for external storage (default: false)
- **MINIO_ENDPOINT**: MinIO server endpoint
- **MINIO_ACCESS_KEY**: MinIO access key
- **MINIO_SECRET_KEY**: MinIO secret key
- **MINIO_BUCKET**: MinIO bucket name (default: r369-bucket)
- **MINIO_SECURE**: Use HTTPS for MinIO (default: false)

## API Documentation

FlowVision provides a comprehensive API for integration with other systems. The API documentation is available at `/api_docs` in the web interface.

## Security Features

- TLS support for secure communication
- Role-based access control
- Advanced authentication system
- Secure flow forwarding with filtering
- Compliance with security standards (SOCS 2, PCI-DSS, HIPAA)

## Development

### Setting Up Development Environment

1. Clone the repository
2. Create a virtual environment and install dependencies
3. Set up PostgreSQL database
4. Run tests:

```
python run_tests.py
```

### Running the Application in Development Mode

```
python main.py
```

## License

Copyright © 2025 FlowVision. All rights reserved.
