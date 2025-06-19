from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional
import threading
import json
import time
import os
import logging
from datetime import datetime
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Import our load balancer modules
from loadbalancer import (
    LBManager, 
    StatsCollector, 
    GLOBAL_SHUTDOWN_EVENT, 
    create_test_servers,
    test_client, 
    load_test, 
    syslog_forwarder,
    LogLevel,
    analytics_collector
)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer-web")

# Create a singleton for our load balancer
lb_manager = LBManager()
test_server_threads = None
test_server_ports = None

# Initialize analytics collector
analytics_collector.set_lb_manager(lb_manager)

# Initialize Analytics Integration
lb_analytics_integration = None
try:
    from analytics_integration import setup_analytics_integration
    lb_analytics_integration = setup_analytics_integration(
        app, 
        lb_manager,
        config={
            'analytics_interval': 15.0,  # 15 seconds
            'collection_interval': 20.0,  # 20 seconds
            'max_history': 300
        }
    )
    if lb_analytics_integration:
        lb_analytics_integration.start()
        logger.info("✅ Load Balancer Analytics Integration initialized")
except ImportError as e:
    logger.warning(f"Analytics integration not available: {e}")
    lb_analytics_integration = None
except Exception as e:
    logger.error(f"Error initializing analytics integration: {e}")
    lb_analytics_integration = None

# Store test client results in a global variable
test_client_results = []

# Form for configuring the load balancer
class LoadBalancerForm(FlaskForm):
    port = IntegerField('Listen Port', validators=[DataRequired(), NumberRange(min=1024, max=65535)], default=8080)
    backends = TextAreaField('Backend Servers (host:port, one per line)', 
                           validators=[DataRequired()], 
                           default='127.0.0.1:8081\n127.0.0.1:8082')
    
    # Load balancing algorithm options
    algorithm = SelectField('Load Balancing Algorithm', 
                         choices=[
                             ('round_robin', 'Round Robin'),
                             ('least_connections', 'Least Connections'),
                             ('weighted_round_robin', 'Weighted Round Robin'),
                             ('random', 'Random'),
                             ('ip_hash', 'IP Hash')
                         ], 
                         default='round_robin')
    
    # Health check options
    enable_health_checks = BooleanField('Enable Health Checks', default=True)
    health_check_interval = IntegerField('Health Check Interval (seconds)', 
                                     validators=[Optional(), NumberRange(min=1, max=60)], 
                                     default=10)
    health_check_timeout = IntegerField('Health Check Timeout (seconds)', 
                                    validators=[Optional(), NumberRange(min=1, max=10)], 
                                    default=2)
    unhealthy_threshold = IntegerField('Unhealthy Threshold', 
                                   validators=[Optional(), NumberRange(min=1, max=10)], 
                                   default=3,
                                   description="Number of consecutive failures before marking a backend as unhealthy")
    healthy_threshold = IntegerField('Healthy Threshold', 
                                 validators=[Optional(), NumberRange(min=1, max=10)], 
                                 default=2,
                                 description="Number of consecutive successes before marking a backend as healthy again")
    
    submit = SubmitField('Start')

class TestClientForm(FlaskForm):
    message = StringField('Test Message', validators=[DataRequired()], default='Hello from test client')
    num_messages = IntegerField('Number of Messages', validators=[DataRequired(), NumberRange(min=1, max=10)], default=3)
    submit = SubmitField('Send Test Messages')

class LoadTestForm(FlaskForm):
    num_clients = IntegerField('Number of Clients', validators=[DataRequired(), NumberRange(min=1, max=20)], default=5)
    messages_per_client = IntegerField('Messages Per Client', validators=[DataRequired(), NumberRange(min=1, max=10)], default=3)
    submit = SubmitField('Run Load Test')

@app.route('/')
def index():
    """Home page with load balancer configuration."""
    start_form = LoadBalancerForm()
    test_form = TestClientForm()
    load_test_form = LoadTestForm()
    
    # Get stats for display
    stats = lb_manager.get_statistics()
    if stats["start_time"]:
        uptime = datetime.now() - stats["start_time"]
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    else:
        uptime_str = "Not running"
    
    # Format data transferred
    total_bytes = stats["bytes_sent"] + stats["bytes_received"]
    if total_bytes < 1024:
        data_str = f"{total_bytes} B"
    elif total_bytes < 1024 * 1024:
        data_str = f"{total_bytes / 1024:.2f} KB"
    else:
        data_str = f"{total_bytes / (1024 * 1024):.2f} MB"
    
    # For the connections table
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    
    # Get connection history
    history = stats.get("connection_history", [])
    
    return render_template('index.html', 
                          form=start_form,
                          test_form=test_form,
                          load_test_form=load_test_form,
                          is_running=lb_manager.is_running(),
                          stats=stats,
                          uptime=uptime_str,
                          data_transferred=data_str,
                          connections=connections,
                          history=history,
                          client_results=test_client_results)

@app.route('/start', methods=['POST'])
def start():
    """Start the load balancer."""
    form = LoadBalancerForm()
    if form.validate_on_submit():
        port = form.port.data
        backends_text = form.backends.data
        backends = [line.strip() for line in backends_text.split('\n') if line.strip()]
        
        if not backends:
            return jsonify({"status": "error", "message": "No backends specified"})
        
        try:
            # Set the load balancing algorithm
            algorithm = form.algorithm.data
            lb_manager.set_algorithm(algorithm)
            
            # Configure health checks
            enable_health_checks = form.enable_health_checks.data
            health_check_interval = form.health_check_interval.data or 10
            health_check_timeout = form.health_check_timeout.data or 2
            unhealthy_threshold = form.unhealthy_threshold.data or 3
            healthy_threshold = form.healthy_threshold.data or 2
            
            lb_manager.set_health_check_config(
                interval=health_check_interval,
                timeout=health_check_timeout,
                path="/",  # Default path for health check
                unhealthy_threshold=unhealthy_threshold,
                healthy_threshold=healthy_threshold,
                enabled=enable_health_checks
            )
            
            # Configure syslog forwarding if enabled
            enable_syslog = request.form.get('enable_syslog') == 'on'
            if enable_syslog:
                syslog_host = request.form.get('syslog_host', '127.0.0.1')
                syslog_port = int(request.form.get('syslog_port', 1514))
                syslog_protocol = request.form.get('syslog_protocol', 'udp')
                syslog_level = request.form.get('syslog_level', 'warning')
                
                # Configure the syslog forwarder
                syslog_forwarder.configure(
                    enabled=True,
                    host=syslog_host,
                    port=syslog_port,
                    protocol=syslog_protocol,
                    min_level=LogLevel.from_string(syslog_level)
                )
            else:
                # Disable syslog forwarding
                syslog_forwarder.configure(enabled=False)
            
            # Start the analytics collector
            analytics_collector.start()
            
            # Start the load balancer
            lb_manager.start_listener(port, backends)
            
            return redirect(url_for('index'))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return redirect(url_for('index'))

@app.route('/stop')
def stop():
    """Stop the load balancer."""
    # Stop analytics integration
    if lb_analytics_integration:
        try:
            lb_analytics_integration.stop()
            logger.info("✅ Load Balancer Analytics Integration stopped")
        except Exception as e:
            logger.error(f"Error stopping analytics integration: {e}")
    
    # Stop analytics collector
    analytics_collector.stop()
    
    # Stop syslog forwarder
    syslog_forwarder.stop()
    
    # Stop the load balancer
    lb_manager.stop_listener()
    
    return redirect(url_for('index'))

@app.route('/test-servers/start')
def start_test_servers():
    """Start test backend servers."""
    global test_server_threads, test_server_ports
    if test_server_threads is None:
        test_server_threads, test_server_ports = create_test_servers()
        return jsonify({"status": "success", "message": f"Test servers started on ports {', '.join(map(str, test_server_ports))}"})
    else:
        return jsonify({"status": "error", "message": "Test servers are already running"})

@app.route('/test-servers/stop')
def stop_test_servers():
    """Stop test backend servers."""
    global test_server_threads, test_server_ports
    if test_server_threads is not None:
        GLOBAL_SHUTDOWN_EVENT.set()
        time.sleep(1)  # Give servers time to shut down
        GLOBAL_SHUTDOWN_EVENT.clear()
        test_server_threads = None
        test_server_ports = None
        return jsonify({"status": "success", "message": "Test servers stopped"})
    else:
        return jsonify({"status": "error", "message": "No test servers are running"})

@app.route('/test-client', methods=['POST'])
def run_test_client():
    """Run a test client."""
    global test_client_results
    form = TestClientForm()
    if form.validate_on_submit():
        if not lb_manager.is_running():
            return jsonify({"status": "error", "message": "Load balancer is not running"})
        
        port = request.form.get('lb_port', type=int)
        if port is None:
            port = lb_manager.get_listen_port()
            
        message = form.message.data or "Test message"
        num_messages = form.num_messages.data or 3
        
        # Run test client in a background thread to avoid blocking
        def run_client():
            global test_client_results
            results = test_client(port, message, num_messages)
            test_client_results = results
        
        client_thread = threading.Thread(target=run_client)
        client_thread.daemon = True
        client_thread.start()
        
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/load-test', methods=['POST'])
def run_load_test():
    """Run a load test with multiple clients."""
    global test_client_results
    form = LoadTestForm()
    if form.validate_on_submit():
        if not lb_manager.is_running():
            return jsonify({"status": "error", "message": "Load balancer is not running"})
        
        port = request.form.get('lb_port', type=int)
        if port is None:
            port = lb_manager.get_listen_port()
            
        num_clients = form.num_clients.data or 5
        messages_per_client = form.messages_per_client.data or 3
        
        # Run load test in a background thread
        def run_test():
            global test_client_results
            results = load_test(port, num_clients, messages_per_client)
            test_client_results = results
        
        test_thread = threading.Thread(target=run_test)
        test_thread.daemon = True
        test_thread.start()
        
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/api/stats')
def get_stats():
    """API endpoint to get current stats."""
    stats = lb_manager.get_statistics()
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    
    # Get backend server information including health status
    backend_servers = lb_manager.get_backend_servers()
    
    # Get current algorithm
    algorithm = lb_manager.get_algorithm()
    
    # Get syslog configuration
    syslog_config = syslog_forwarder.get_config()
    
    # Get analytics integration status
    analytics_status = {
        "integration_active": lb_analytics_integration is not None and lb_analytics_integration.is_running(),
        "integration_available": lb_analytics_integration is not None
    }
    
    return jsonify({
        "stats": stats,
        "connections": connections,
        "is_running": lb_manager.is_running(),
        "backend_servers": backend_servers,
        "algorithm": algorithm,
        "syslog": syslog_config,
        "analytics": analytics_status
    })

@app.route('/api/connections')
def get_connections():
    """API endpoint to get current connections."""
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    return jsonify({"connections": connections})

@app.route('/api/client-results')
def get_client_results():
    """API endpoint to get test client results."""
    global test_client_results
    return jsonify({"results": test_client_results})

@app.route('/api/clear-results')
def clear_results():
    """Clear test client results."""
    global test_client_results
    test_client_results = []
    return redirect(url_for('index'))

@app.route('/api/plot/connections')
def plot_connections():
    """Generate a plot of connections over time."""
    # Get connection data
    stats = lb_manager.get_statistics()
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    
    # Simple plot for now - this would be better with time series data
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode = "number",
        value = len(connections),
        title = {"text": "Active Connections"},
        domain = {'row': 0, 'column': 0}
    ))
    
    fig.add_trace(go.Indicator(
        mode = "number",
        value = stats["total_connections"],
        title = {"text": "Total Connections"},
        domain = {'row': 0, 'column': 1}
    ))
    
    fig.update_layout(
        grid = {'rows': 1, 'columns': 2},
        margin=dict(l=20, r=20, t=30, b=20),
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/api/plot/health')
def plot_health():
    """Generate a plot of backend health over time."""
    stats = lb_manager.get_statistics()
    backend_servers = lb_manager.get_backend_servers()
    
    # Create a health dashboard with multiple indicators
    fig = go.Figure()
    
    # Add indicators for each backend server
    total_backends = len(backend_servers)
    if total_backends > 0:
        healthy_backends = sum(1 for backend in backend_servers if backend['healthy'])
        
        # Add health ratio gauge
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=100 * healthy_backends / total_backends,
            title={"text": "Backend Health %"},
            domain={'row': 0, 'column': 0},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#19d3f3"},
                'steps': [
                    {'range': [0, 33], 'color': "#ff0000"},
                    {'range': [33, 66], 'color': "#ffa500"},
                    {'range': [66, 100], 'color': "#00ff00"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ))
        
        # Add individual server status
        for i, backend in enumerate(backend_servers):
            color = "green" if backend['healthy'] else "red"
            symbol = "✓" if backend['healthy'] else "✗"
            response_time = backend['response_time']
            
            # Create text display for server status
            status_text = f"{symbol} {backend['host']}:{backend['port']}  •  {response_time}ms"
            
            # Add text annotation
            fig.add_annotation(
                text=status_text,
                x=0.5,
                y=0.7 - (i * 0.1),
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(
                    family="Arial",
                    size=14,
                    color=color
                )
            )
    else:
        # If no backend servers, show empty message
        fig.add_annotation(
            text="No backend servers configured",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                family="Arial",
                size=14
            )
        )
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/api/plot/analytics')
def plot_analytics():
    """Generate analytics dashboard with historical data."""
    # Get timespan from query parameter (default: 1 hour)
    timespan = request.args.get('timespan', 3600, type=int)
    
    # Create dashboard using the analytics collector
    fig = analytics_collector.create_dashboard(timespan)
    
    # Convert to JSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/api/analytics/status')
def get_analytics_status():
    """Get analytics integration status and metrics."""
    status = {
        "integration_active": lb_analytics_integration is not None and lb_analytics_integration.is_running(),
        "analytics_engine_connected": False,
        "last_sync_time": None,
        "metrics_collected": 0,
        "events_processed": 0,
        "correlation_data_available": False
    }
    
    if lb_analytics_integration:
        try:
            # Get detailed status from the integration
            integration_status = lb_analytics_integration.get_status()
            status.update(integration_status)
        except Exception as e:
            logger.error(f"Error getting analytics integration status: {e}")
            status["error"] = str(e)
    
    return jsonify(status)

@app.route('/api/syslog/config', methods=['POST'])
def update_syslog_config():
    """Update syslog forwarding configuration."""
    try:
        enable_syslog = request.json.get('enabled', False)
        host = request.json.get('host', '127.0.0.1')
        port = request.json.get('port', 1514)
        protocol = request.json.get('protocol', 'udp')
        level = request.json.get('level', 'warning')
        
        # Configure syslog forwarder
        syslog_forwarder.configure(
            enabled=enable_syslog,
            host=host,
            port=port,
            protocol=protocol,
            min_level=LogLevel.from_string(level)
        )
        
        return jsonify({
            "status": "success",
            "message": "Syslog configuration updated",
            "config": syslog_forwarder.get_config()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error updating syslog configuration: {str(e)}"
        })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)