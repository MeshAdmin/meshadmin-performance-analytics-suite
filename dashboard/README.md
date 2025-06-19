# MeshAdmin Performance Analytics Dashboard

## Overview

The MeshAdmin Performance Analytics Dashboard provides centralized monitoring and correlation analysis for the MeshAdmin Performance Analytics Suite. It offers real-time visualization of metrics from both Network Flow Master and Load Balancer Pro applications, along with advanced correlation analysis capabilities.

## Features

### 🔍 Real-time Monitoring
- **Application Health Status**: Monitor the health of Network Flow Master and Load Balancer Pro
- **Performance Metrics**: Track key performance indicators across both applications
- **Analytics Engine Integration**: Connect to the centralized analytics engine for advanced analysis

### 📊 Data Visualization
- **Network Flow Charts**: Visualize network traffic patterns and packet rates
- **Load Balancer Charts**: Monitor response times and connection metrics
- **Correlation Analysis**: View cross-application performance correlations
- **Performance Overview**: Health score gauges and trend indicators

### 🚨 Alerting & Insights
- **Real-time Alerts**: Automatic alerts for performance thresholds
- **Trend Analysis**: Track performance trends over time
- **Correlation Insights**: AI-powered insights into application relationships
- **Recommendations**: Performance optimization suggestions

### ⚙️ Configuration
- **Adjustable Refresh Intervals**: Customize data collection frequency
- **Correlation Windows**: Configure analysis time windows
- **Alert Thresholds**: Set custom performance thresholds

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Performance Analytics Dashboard                          │
│                            (Port 3000)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Performance     │    │ Flask Web       │    │ Chart           │          │
│  │ Monitor         │    │ Interface       │    │ Generation      │          │
│  │                 │    │                 │    │                 │          │
│  │ • Data Collection│    │ • Dashboard UI  │    │ • Plotly Charts │          │
│  │ • Correlation   │    │ • API Endpoints │    │ • Real-time Data│          │
│  │ • Alerting      │    │ • Settings      │    │ • Visualization │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
│           │                       │                       │                 │
└───────────┼───────────────────────┼───────────────────────┼─────────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐    ┌──────────────────────┐    ┌─────────────────┐
    │ Analytics    │    │ External Apps        │    │ Browser         │
    │ Engine       │    │                      │    │ Dashboard       │
    │              │    │ • Network Flow       │    │                 │
    │ • Data Store │    │   Master (Port 8000) │    │ • Interactive   │
    │ • Correlation│    │ • Load Balancer      │    │   Charts        │
    │ • Analysis   │    │   Pro (Port 5000)    │    │ • Real-time     │
    │              │    │                      │    │   Updates       │
    └──────────────┘    └──────────────────────┘    └─────────────────┘
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- Network Flow Master application
- Load Balancer Pro application
- Analytics Engine (optional, for advanced features)

### Dependencies Installation

```bash
cd dashboard
pip install -r requirements.txt
```

### Required Dependencies
- Flask >= 2.0.0
- Flask-WTF >= 1.0.0
- WTForms >= 3.0.0
- plotly >= 5.0.0
- requests >= 2.25.0

### Optional Dependencies (for enhanced analytics)
- pandas >= 1.3.0
- numpy >= 1.20.0
- scikit-learn >= 1.0.0
- scipy >= 1.7.0

## Configuration

### Application URLs

The dashboard is configured to monitor applications at these default URLs:

```python
DASHBOARD_CONFIG = {
    'apps': {
        'network_flow_master': {
            'url': 'http://localhost:8000',
            'api_endpoint': '/api/flows/summary',
            'health_endpoint': '/health'
        },
        'load_balancer_pro': {
            'url': 'http://localhost:5000',
            'api_endpoint': '/api/stats',
            'health_endpoint': '/api/stats'
        }
    }
}
```

### Alert Thresholds

Default performance alert thresholds:

```python
'alerts': {
    'response_time_threshold': 1000,  # ms
    'error_rate_threshold': 0.05,     # 5%
    'connection_threshold': 1000,     # connections
    'packet_rate_threshold': 10000    # packets/sec
}
```

### Monitoring Intervals

```python
'refresh_interval': 30,        # seconds (data collection)
'correlation_window': 3600,    # seconds (1 hour analysis window)
'max_data_points': 100,        # maximum stored data points
```

## Usage

### Starting the Dashboard

1. **Start the monitored applications first:**
   ```bash
   # Terminal 1: Start Network Flow Master
   cd ../apps/network-flow-master
   python app.py

   # Terminal 2: Start Load Balancer Pro  
   cd ../apps/load-balancer-pro
   python app.py
   ```

2. **Start the dashboard:**
   ```bash
   cd dashboard
   python performance_dashboard.py
   ```

3. **Access the dashboard:**
   - Open your browser to: `http://localhost:3000`

### Testing the Installation

Run the comprehensive test suite:

```bash
python test_dashboard.py
```

Expected output:
```
🎉 ALL TESTS PASSED! Performance dashboard is ready for use.
```

## Dashboard Interface

### Main Dashboard View

The dashboard is organized into several sections:

#### 1. Status Row
- **Monitor Status**: Dashboard monitoring state
- **Network Flow**: Network Flow Master application health
- **Load Balancer**: Load Balancer Pro application health  
- **Analytics Engine**: Analytics engine availability

#### 2. Performance Summary
- **Network Flows**: Total network flows processed
- **Connections**: Load balancer connections
- **Response Time**: Average response time (ms)
- **Packet Rate**: Packets per second
- **Health Score**: Overall system health percentage
- **Correlation**: Cross-application correlation score

#### 3. Visualization Charts
- **Network Flow Chart**: Real-time network traffic patterns
- **Load Balancer Chart**: Response times and connection metrics
- **Correlation Chart**: Cross-application correlation over time
- **Performance Overview**: Health score gauge

#### 4. Alerts & Insights
- **Recent Alerts**: Performance warnings and errors
- **Correlation Insights**: AI-powered analysis results
- **Recommendations**: Performance optimization suggestions

### Controls

- **Start/Stop Monitor**: Control dashboard monitoring
- **Refresh**: Manual data refresh
- **Analyze**: Trigger correlation analysis
- **Settings**: Configure thresholds and intervals

## API Endpoints

The dashboard provides several API endpoints for programmatic access:

### Dashboard Data
```
GET /api/dashboard/data
```
Returns complete dashboard data including metrics, alerts, and status.

### Charts Data
```
GET /api/dashboard/charts  
```
Returns JSON data for all dashboard charts.

### Trigger Correlation
```
GET /api/dashboard/correlation
```
Triggers correlation analysis and returns results.

### Monitor Controls
```
GET /start_monitor    # Start performance monitoring
GET /stop_monitor     # Stop performance monitoring
```

## Troubleshooting

### Common Issues

#### 1. Applications Not Reachable
**Symptom**: Dashboard shows "unreachable" status for applications
**Solution**: 
- Ensure Network Flow Master is running on port 8000
- Ensure Load Balancer Pro is running on port 5000
- Check firewall settings
- Verify application health endpoints

#### 2. No Charts Displaying
**Symptom**: Charts show "No data available"
**Solution**:
- Wait for data collection (30-second intervals)
- Check that monitored applications are running
- Verify applications are generating metrics

#### 3. Analytics Engine Unavailable
**Symptom**: "Analytics engine not available" warnings
**Solution**:
- This is normal if analytics engine is not configured
- Dashboard will work in limited mode
- Advanced correlation features will be disabled

#### 4. Template Errors
**Symptom**: HTTP 500 errors on dashboard pages
**Solution**:
- Check browser console for JavaScript errors
- Verify all template dependencies are installed
- Restart the dashboard application

### Debug Mode

Run the dashboard in debug mode for detailed error information:

```bash
export FLASK_DEBUG=1
python performance_dashboard.py
```

### Log Files

Dashboard logs are output to the console with detailed timestamps:

```
2025-06-18 19:54:16,147 - performance-dashboard - INFO - 🚀 Performance Monitor initialized
2025-06-18 19:54:16,147 - performance-dashboard - INFO - ✅ Performance Monitor started
```

## Performance Considerations

### Resource Usage
- **Memory**: ~50-100MB typical usage
- **CPU**: Low impact, periodic data collection
- **Network**: Regular HTTP requests to monitored applications

### Scaling
- Dashboard can monitor applications on different hosts
- Supports horizontal scaling with load balancing
- Data retention managed automatically (24-hour window)

### Optimization Tips
- Adjust refresh intervals based on requirements
- Limit max_data_points for memory efficiency
- Use analytics engine for advanced features only when needed

## Development

### Architecture Components

1. **PerformanceMonitor Class**: Core monitoring logic
2. **Flask Application**: Web interface and API
3. **Chart Generation**: Plotly visualization
4. **Template Engine**: Jinja2 HTML templates

### Adding New Metrics

To add monitoring for additional applications:

1. **Update Configuration**:
   ```python
   DASHBOARD_CONFIG['apps']['new_app'] = {
       'name': 'New Application',
       'url': 'http://localhost:PORT',
       'api_endpoint': '/api/metrics',
       'health_endpoint': '/health'
   }
   ```

2. **Extend Metrics Collection**:
   - Modify `_collect_app_metrics()` method
   - Add new chart generation methods
   - Update template for new metrics display

### Custom Correlation Analysis

The correlation analysis can be extended with custom algorithms:

```python
def _analyze_cross_app_correlation(self, time_range):
    # Custom correlation logic here
    # Access metrics via self.metrics_history
    # Return correlation results
```

## Contributing

To contribute to the dashboard development:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `python test_dashboard.py`
5. Submit a pull request

## Security Considerations

- Dashboard runs on localhost by default (production deployment requires security review)
- No authentication implemented (add authentication for production use)
- API endpoints are open (consider API key authentication)
- Consider HTTPS for production deployments

## License

This dashboard is part of the MeshAdmin Performance Analytics Suite. See the main project LICENSE file for details.

---

## Quick Start Summary

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start monitored apps**: Network Flow Master + Load Balancer Pro
3. **Start dashboard**: `python performance_dashboard.py`
4. **Open browser**: `http://localhost:3000`
5. **Run tests**: `python test_dashboard.py`

For support, refer to the troubleshooting section or check the application logs for detailed error information.

