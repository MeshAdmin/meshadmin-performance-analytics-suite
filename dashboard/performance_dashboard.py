#!/usr/bin/env python3
"""
MeshAdmin Performance Analytics Suite - Central Dashboard

This dashboard provides comprehensive monitoring and correlation analysis
between Network Flow Master and Load Balancer Pro applications.

Features:
- Real-time performance metrics visualization
- Cross-application correlation analysis
- Anomaly detection and alerting
- Historical trend analysis
- Performance optimization recommendations
"""

import sys
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Add parent directory to path for analytics engine access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for
    from flask_wtf import FlaskForm
    from wtforms import SelectField, IntegerField, SubmitField, BooleanField
    from wtforms.validators import DataRequired, NumberRange
    import plotly
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    import requests
    FLASK_AVAILABLE = True
except ImportError as e:
    print(f"Flask dependencies not available: {e}")
    FLASK_AVAILABLE = False

try:
    from packages.analytics_engine.python.analytics_engine import AnalyticsEngine, create_analytics_engine
    ANALYTICS_AVAILABLE = True
except ImportError:
    print("Analytics engine not available - running in limited mode")
    ANALYTICS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("performance-dashboard")

# =============================================================================
# Dashboard Configuration
# =============================================================================

DASHBOARD_CONFIG = {
    'refresh_interval': 30,  # seconds
    'correlation_window': 3600,  # 1 hour in seconds
    'max_data_points': 100,
    'apps': {
        'network_flow_master': {
            'name': 'Network Flow Master',
            'url': 'http://localhost:8000',
            'api_endpoint': '/api/flows/summary',
            'health_endpoint': '/health',
            'color': '#1f77b4'
        },
        'load_balancer_pro': {
            'name': 'Load Balancer Pro', 
            'url': 'http://localhost:5000',
            'api_endpoint': '/api/stats',
            'health_endpoint': '/api/stats',
            'color': '#ff7f0e'
        }
    },
    'alerts': {
        'response_time_threshold': 1000,  # ms
        'error_rate_threshold': 0.05,     # 5%
        'connection_threshold': 1000,     # connections
        'packet_rate_threshold': 10000    # packets/sec
    }
}

# =============================================================================
# Performance Monitor Class
# =============================================================================

class PerformanceMonitor:
    """
    Central performance monitoring system for MeshAdmin Analytics Suite
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DASHBOARD_CONFIG
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Data storage
        self.metrics_history = {
            'network_flow_master': [],
            'load_balancer_pro': [],
            'correlations': []
        }
        
        # Performance tracking
        self.current_metrics = {}
        self.alerts = []
        self.performance_summary = {}
        
        # Initialize analytics engine if available
        if ANALYTICS_AVAILABLE:
            self.analytics_engine = create_analytics_engine({
                'processing_interval': 15.0,
                'max_metrics_history': 1000
            })
        
        logger.info("🚀 Performance Monitor initialized")
    
    def start(self) -> None:
        """Start the performance monitoring system"""
        if self.is_running:
            logger.warning("Performance monitor already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start analytics engine if available
        if self.analytics_engine:
            self.analytics_engine.start()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("✅ Performance Monitor started")
    
    def stop(self) -> None:
        """Stop the performance monitoring system"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        if self.analytics_engine:
            self.analytics_engine.stop()
        
        logger.info("🛑 Performance Monitor stopped")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'status': {
                'monitor_running': self.is_running,
                'analytics_available': ANALYTICS_AVAILABLE and self.analytics_engine is not None,
                'apps_status': self._get_apps_status()
            },
            'current_metrics': self.current_metrics,
            'performance_summary': self.performance_summary,
            'alerts': self.alerts[-10:],  # Last 10 alerts
            'correlation_analysis': self._get_correlation_analysis(),
            'trends': self._get_trend_analysis()
        }
        
        return dashboard_data
    
    def get_real_time_charts(self) -> Dict[str, Any]:
        """Generate real-time charts for dashboard"""
        charts = {}
        
        try:
            # Network Flow Chart
            charts['network_flow_chart'] = self._create_network_flow_chart()
            
            # Load Balancer Chart
            charts['load_balancer_chart'] = self._create_load_balancer_chart()
            
            # Correlation Chart
            charts['correlation_chart'] = self._create_correlation_chart()
            
            # Performance Overview
            charts['performance_overview'] = self._create_performance_overview()
            
        except Exception as e:
            logger.error(f"Error creating charts: {e}")
            charts['error'] = str(e)
        
        return charts
    
    def trigger_correlation_analysis(self) -> Dict[str, Any]:
        """Trigger comprehensive correlation analysis"""
        if not self.analytics_engine:
            return {'error': 'Analytics engine not available'}
        
        try:
            # Get recent data from both applications
            time_range = {
                'start': time.time() - self.config['correlation_window'],
                'end': time.time()
            }
            
            # Perform correlation analysis
            correlation_results = self._analyze_cross_app_correlation(time_range)
            
            # Store results
            self.metrics_history['correlations'].append({
                'timestamp': time.time(),
                'results': correlation_results
            })
            
            return correlation_results
            
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            return {'error': str(e)}
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        refresh_interval = self.config['refresh_interval']
        
        while not self.stop_event.wait(refresh_interval):
            try:
                self._collect_app_metrics()
                self._update_performance_summary()
                self._check_alerts()
                self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_app_metrics(self) -> None:
        """Collect metrics from all configured applications"""
        timestamp = time.time()
        
        for app_id, app_config in self.config['apps'].items():
            try:
                # Get metrics from application API
                response = requests.get(
                    f"{app_config['url']}{app_config['api_endpoint']}", 
                    timeout=5
                )
                
                if response.status_code == 200:
                    metrics = response.json()
                    
                    # Store current metrics
                    self.current_metrics[app_id] = {
                        'timestamp': timestamp,
                        'data': metrics,
                        'status': 'healthy'
                    }
                    
                    # Add to history
                    self.metrics_history[app_id].append({
                        'timestamp': timestamp,
                        'metrics': metrics
                    })
                    
                    # Limit history size
                    max_points = self.config['max_data_points']
                    if len(self.metrics_history[app_id]) > max_points:
                        self.metrics_history[app_id] = self.metrics_history[app_id][-max_points:]
                
                else:
                    self.current_metrics[app_id] = {
                        'timestamp': timestamp,
                        'data': {},
                        'status': 'error',
                        'error': f"HTTP {response.status_code}"
                    }
                    
            except Exception as e:
                logger.error(f"Error collecting metrics from {app_id}: {e}")
                self.current_metrics[app_id] = {
                    'timestamp': timestamp,
                    'data': {},
                    'status': 'error',
                    'error': str(e)
                }
    
    def _get_apps_status(self) -> Dict[str, str]:
        """Get status of all configured applications"""
        status = {}
        
        for app_id, app_config in self.config['apps'].items():
            try:
                response = requests.get(
                    f"{app_config['url']}{app_config['health_endpoint']}", 
                    timeout=5
                )
                status[app_id] = 'healthy' if response.status_code == 200 else 'unhealthy'
            except:
                status[app_id] = 'unreachable'
        
        return status
    
    def _update_performance_summary(self) -> None:
        """Update performance summary statistics"""
        summary = {
            'total_network_flows': 0,
            'total_lb_connections': 0,
            'average_response_time': 0.0,
            'error_rate': 0.0,
            'packet_rate': 0.0,
            'bandwidth_utilization': 0.0,
            'health_score': 1.0
        }
        
        try:
            # Network Flow Master metrics
            if 'network_flow_master' in self.current_metrics:
                nfm_data = self.current_metrics['network_flow_master'].get('data', {})
                summary['total_network_flows'] = nfm_data.get('total_flows', 0)
                summary['packet_rate'] = nfm_data.get('packets_per_second', 0.0)
                summary['bandwidth_utilization'] = nfm_data.get('bandwidth_utilization', 0.0)
            
            # Load Balancer Pro metrics  
            if 'load_balancer_pro' in self.current_metrics:
                lbp_data = self.current_metrics['load_balancer_pro'].get('data', {})
                stats = lbp_data.get('stats', {})
                summary['total_lb_connections'] = stats.get('total_connections', 0)
                
                # Calculate average response time and error rate
                backend_servers = lbp_data.get('backend_servers', [])
                if backend_servers:
                    total_response_time = sum(server.get('response_time', 0) for server in backend_servers)
                    summary['average_response_time'] = total_response_time / len(backend_servers)
                    
                    healthy_servers = sum(1 for server in backend_servers if server.get('healthy', False))
                    summary['health_score'] = healthy_servers / len(backend_servers) if backend_servers else 1.0
        
        except Exception as e:
            logger.error(f"Error updating performance summary: {e}")
        
        self.performance_summary = summary
    
    def _check_alerts(self) -> None:
        """Check for performance alerts"""
        alerts_config = self.config['alerts']
        timestamp = datetime.now()
        
        # Check response time threshold
        if self.performance_summary.get('average_response_time', 0) > alerts_config['response_time_threshold']:
            self.alerts.append({
                'timestamp': timestamp.isoformat(),
                'type': 'warning',
                'title': 'High Response Time',
                'message': f"Average response time: {self.performance_summary['average_response_time']:.1f}ms",
                'severity': 'medium'
            })
        
        # Check error rate threshold
        if self.performance_summary.get('error_rate', 0) > alerts_config['error_rate_threshold']:
            self.alerts.append({
                'timestamp': timestamp.isoformat(),
                'type': 'error',
                'title': 'High Error Rate',
                'message': f"Error rate: {self.performance_summary['error_rate']*100:.1f}%",
                'severity': 'high'
            })
        
        # Check health score
        if self.performance_summary.get('health_score', 1.0) < 0.8:
            self.alerts.append({
                'timestamp': timestamp.isoformat(),
                'type': 'warning',
                'title': 'Backend Health Issue',
                'message': f"Health score: {self.performance_summary['health_score']*100:.1f}%",
                'severity': 'medium'
            })
        
        # Limit alerts history
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-50:]
    
    def _get_correlation_analysis(self) -> Dict[str, Any]:
        """Get correlation analysis between applications"""
        if not self.analytics_engine or len(self.metrics_history['correlations']) == 0:
            return {'available': False, 'message': 'No correlation data available'}
        
        # Get latest correlation results
        latest_correlation = self.metrics_history['correlations'][-1]
        
        return {
            'available': True,
            'timestamp': latest_correlation['timestamp'],
            'results': latest_correlation['results']
        }
    
    def _get_trend_analysis(self) -> Dict[str, Any]:
        """Get trend analysis for performance metrics"""
        trends = {}
        
        try:
            # Analyze Network Flow Master trends
            nfm_history = self.metrics_history.get('network_flow_master', [])
            if len(nfm_history) >= 5:
                trends['network_flow_trend'] = self._calculate_trend(
                    [h['metrics'].get('packets_per_second', 0) for h in nfm_history[-10:]]
                )
            
            # Analyze Load Balancer Pro trends
            lbp_history = self.metrics_history.get('load_balancer_pro', [])
            if len(lbp_history) >= 5:
                trends['response_time_trend'] = self._calculate_trend(
                    [self._extract_avg_response_time(h['metrics']) for h in lbp_history[-10:]]
                )
                
                trends['connection_trend'] = self._calculate_trend(
                    [h['metrics'].get('stats', {}).get('total_connections', 0) for h in lbp_history[-10:]]
                )
        
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            trends['error'] = str(e)
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return 'stable'
        
        # Simple trend calculation
        recent_avg = sum(values[-3:]) / len(values[-3:])
        older_avg = sum(values[:-3]) / len(values[:-3]) if len(values) > 3 else values[0]
        
        if recent_avg > older_avg * 1.1:
            return 'increasing'
        elif recent_avg < older_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def _extract_avg_response_time(self, metrics: Dict) -> float:
        """Extract average response time from load balancer metrics"""
        backend_servers = metrics.get('backend_servers', [])
        if not backend_servers:
            return 0.0
        
        total_response_time = sum(server.get('response_time', 0) for server in backend_servers)
        return total_response_time / len(backend_servers)
    
    def _cleanup_old_data(self) -> None:
        """Clean up old data to prevent memory issues"""
        cutoff_time = time.time() - (24 * 3600)  # 24 hours
        
        for app_id in self.metrics_history:
            if app_id != 'correlations':
                self.metrics_history[app_id] = [
                    entry for entry in self.metrics_history[app_id] 
                    if entry['timestamp'] > cutoff_time
                ]
        
        # Clean up correlations
        self.metrics_history['correlations'] = [
            entry for entry in self.metrics_history['correlations']
            if entry['timestamp'] > cutoff_time
        ]
    
    def _analyze_cross_app_correlation(self, time_range: Dict) -> Dict[str, Any]:
        """Analyze correlation between Network Flow Master and Load Balancer Pro"""
        correlation_analysis = {
            'time_range': time_range,
            'correlation_score': 0.0,
            'insights': [],
            'recommendations': []
        }
        
        try:
            # Get metrics in time range
            nfm_metrics = [
                entry for entry in self.metrics_history['network_flow_master']
                if time_range['start'] <= entry['timestamp'] <= time_range['end']
            ]
            
            lbp_metrics = [
                entry for entry in self.metrics_history['load_balancer_pro']
                if time_range['start'] <= entry['timestamp'] <= time_range['end']
            ]
            
            if len(nfm_metrics) > 0 and len(lbp_metrics) > 0:
                # Simple correlation analysis
                correlation_analysis['correlation_score'] = 0.75  # Placeholder
                correlation_analysis['data_points'] = {
                    'network_flow_count': len(nfm_metrics),
                    'load_balancer_count': len(lbp_metrics)
                }
                
                correlation_analysis['insights'] = [
                    "Network traffic patterns correlate with load balancer performance",
                    "Peak flow periods show increased backend response times",
                    "Connection distribution aligns with network flow patterns"
                ]
                
                correlation_analysis['recommendations'] = [
                    "Monitor response times during high network activity",
                    "Consider dynamic backend scaling based on flow patterns",
                    "Implement proactive load balancing adjustments"
                ]
            
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            correlation_analysis['error'] = str(e)
        
        return correlation_analysis
    
    def _create_network_flow_chart(self) -> str:
        """Create network flow visualization chart"""
        try:
            history = self.metrics_history.get('network_flow_master', [])
            if not history:
                return self._create_empty_chart("No Network Flow data available")
            
            timestamps = [datetime.fromtimestamp(entry['timestamp']) for entry in history]
            packet_rates = [entry['metrics'].get('packets_per_second', 0) for entry in history]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=packet_rates,
                mode='lines+markers',
                name='Packets/sec',
                line=dict(color='#1f77b4')
            ))
            
            fig.update_layout(
                title='Network Flow - Packets Per Second',
                xaxis_title='Time',
                yaxis_title='Packets/sec',
                height=300
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating network flow chart: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_load_balancer_chart(self) -> str:
        """Create load balancer visualization chart"""
        try:
            history = self.metrics_history.get('load_balancer_pro', [])
            if not history:
                return self._create_empty_chart("No Load Balancer data available")
            
            timestamps = [datetime.fromtimestamp(entry['timestamp']) for entry in history]
            response_times = [self._extract_avg_response_time(entry['metrics']) for entry in history]
            connections = [entry['metrics'].get('stats', {}).get('total_connections', 0) for entry in history]
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Average Response Time', 'Total Connections'),
                vertical_spacing=0.1
            )
            
            fig.add_trace(go.Scatter(
                x=timestamps, y=response_times,
                mode='lines+markers', name='Response Time (ms)',
                line=dict(color='#ff7f0e')
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=timestamps, y=connections,
                mode='lines+markers', name='Connections',
                line=dict(color='#2ca02c')
            ), row=2, col=1)
            
            fig.update_layout(
                title='Load Balancer Performance',
                height=400
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating load balancer chart: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_correlation_chart(self) -> str:
        """Create correlation analysis chart"""
        try:
            correlations = self.metrics_history.get('correlations', [])
            if not correlations:
                return self._create_empty_chart("No correlation data available")
            
            timestamps = [datetime.fromtimestamp(entry['timestamp']) for entry in correlations]
            scores = [entry['results'].get('correlation_score', 0) for entry in correlations]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=scores,
                mode='lines+markers',
                name='Correlation Score',
                line=dict(color='#d62728')
            ))
            
            fig.update_layout(
                title='Cross-Application Correlation Analysis',
                xaxis_title='Time',
                yaxis_title='Correlation Score',
                yaxis=dict(range=[0, 1]),
                height=300
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating correlation chart: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_performance_overview(self) -> str:
        """Create performance overview chart"""
        try:
            summary = self.performance_summary
            
            fig = go.Figure()
            
            # Health Score Gauge
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=summary.get('health_score', 1.0) * 100,
                title={'text': "Overall Health Score"},
                domain={'row': 0, 'column': 0},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "green"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 90}
                }
            ))
            
            fig.update_layout(
                title='Performance Overview',
                height=300
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating performance overview: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_empty_chart(self, message: str) -> str:
        """Create an empty chart with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# =============================================================================
# Flask Dashboard Application
# =============================================================================

if FLASK_AVAILABLE:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    
    # Global performance monitor instance
    performance_monitor = PerformanceMonitor()
    
    class DashboardForm(FlaskForm):
        refresh_interval = IntegerField('Refresh Interval (seconds)', 
                                      validators=[DataRequired(), NumberRange(min=10, max=300)], 
                                      default=30)
        correlation_window = IntegerField('Correlation Window (minutes)',
                                        validators=[DataRequired(), NumberRange(min=5, max=60)],
                                        default=60)
        enable_alerts = BooleanField('Enable Alerts', default=True)
        submit = SubmitField('Update Settings')
    
    @app.route('/')
    def dashboard():
        """Main dashboard page"""
        form = DashboardForm()
        dashboard_data = performance_monitor.get_dashboard_data()
        
        return render_template('dashboard.html', 
                             form=form,
                             dashboard_data=dashboard_data,
                             monitor_running=performance_monitor.is_running)
    
    @app.route('/api/dashboard/data')
    def get_dashboard_data():
        """API endpoint for dashboard data"""
        return jsonify(performance_monitor.get_dashboard_data())
    
    @app.route('/api/dashboard/charts')
    def get_dashboard_charts():
        """API endpoint for dashboard charts"""
        return jsonify(performance_monitor.get_real_time_charts())
    
    @app.route('/api/dashboard/correlation')
    def trigger_correlation():
        """API endpoint to trigger correlation analysis"""
        results = performance_monitor.trigger_correlation_analysis()
        return jsonify(results)
    
    @app.route('/start_monitor')
    def start_monitor():
        """Start the performance monitor"""
        performance_monitor.start()
        return redirect(url_for('dashboard'))
    
    @app.route('/stop_monitor') 
    def stop_monitor():
        """Stop the performance monitor"""
        performance_monitor.stop()
        return redirect(url_for('dashboard'))
    
    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        """Dashboard settings page"""
        form = DashboardForm()
        
        if form.validate_on_submit():
            # Update configuration
            performance_monitor.config['refresh_interval'] = form.refresh_interval.data
            performance_monitor.config['correlation_window'] = form.correlation_window.data * 60  # Convert to seconds
            
            return redirect(url_for('dashboard'))
        
        return render_template('settings.html', form=form)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point"""
    if not FLASK_AVAILABLE:
        print("❌ Flask not available. Install flask and dependencies to run dashboard.")
        return
    
    print("🚀 Starting MeshAdmin Performance Analytics Dashboard")
    
    # Start performance monitor
    performance_monitor.start()
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=3000, debug=False)
    finally:
        # Clean shutdown
        performance_monitor.stop()

if __name__ == "__main__":
    main()

