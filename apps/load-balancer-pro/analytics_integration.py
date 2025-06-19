"""
Analytics Integration for Load Balancer Pro
===========================================

This module integrates the Load Balancer Pro with the analytics engine,
enabling real-time metrics sharing and cross-application correlation analysis.
"""

import sys
import os
import time
import threading
from typing import Dict, Any, Optional, List
import logging

# Add the analytics engine to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../packages/analytics-engine/python'))

try:
    from analytics_engine import create_analytics_engine, AnalyticsEngine, FlowMetrics, MetricPoint
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Analytics engine not available: {e}")
    ANALYTICS_AVAILABLE = False
    AnalyticsEngine = None

logger = logging.getLogger(__name__)

class LoadBalancerAnalyticsIntegration:
    """
    Integration layer between Load Balancer Pro and Analytics Engine
    """
    
    def __init__(self, lb_manager=None, config: Optional[Dict[str, Any]] = None):
        self.lb_manager = lb_manager
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.config = config or {}
        self.is_running = False
        self.metrics_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.last_stats = {}
        self.performance_history = []
        
        # Configure analytics if available
        if ANALYTICS_AVAILABLE:
            self.analytics_engine = create_analytics_engine({
                'processing_interval': self.config.get('analytics_interval', 15.0),  # 15 seconds
                'max_metrics_history': self.config.get('max_history', 500)
            })
        else:
            logger.warning("Analytics engine not available - load balancer metrics will not be shared")
    
    def start(self) -> None:
        """Start the analytics integration"""
        if not ANALYTICS_AVAILABLE or not self.analytics_engine:
            logger.warning("Cannot start analytics integration - engine not available")
            return
        
        if self.is_running:
            logger.warning("Analytics integration already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start the analytics engine
        self.analytics_engine.start()
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Create correlation pipelines
        self._create_correlation_pipelines()
        
        logger.info("✅ Load Balancer Analytics Integration started")
    
    def stop(self) -> None:
        """Stop the analytics integration"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5.0)
        
        if self.analytics_engine:
            self.analytics_engine.stop()
        
        logger.info("🛑 Load Balancer Analytics Integration stopped")
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary for dashboard display"""
        if not self.analytics_engine:
            return {
                'available': False,
                'message': 'Analytics engine not available'
            }
        
        try:
            summary = self.analytics_engine.get_real_time_summary()
            summary['available'] = True
            
            # Add load balancer specific metrics
            if self.lb_manager:
                lb_stats = self.lb_manager.get_statistics()
                summary['load_balancer'] = {
                    'active_connections': lb_stats.get('active_connections', 0),
                    'total_connections': lb_stats.get('total_connections', 0),
                    'bytes_sent': lb_stats.get('bytes_sent', 0),
                    'bytes_received': lb_stats.get('bytes_received', 0),
                    'average_response_time': self._calculate_average_response_time(),
                    'error_rate': self._calculate_error_rate(),
                    'backend_health': self._get_backend_health_summary()
                }
            
            return summary
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def get_load_balancer_metrics(self) -> Dict[str, Any]:
        """Get detailed load balancer metrics for correlation analysis"""
        if not self.lb_manager:
            return {'error': 'Load balancer manager not available'}
        
        try:
            stats = self.lb_manager.get_statistics()
            connections = self.lb_manager.list_connections()
            
            # Calculate performance metrics
            performance_metrics = {
                'timestamp': time.time(),
                'active_connections': len(connections),
                'total_connections': stats.get('total_connections', 0),
                'requests_per_second': self._calculate_requests_per_second(stats),
                'average_response_time': self._calculate_average_response_time(),
                'error_rate': self._calculate_error_rate(),
                'bytes_per_second': self._calculate_bytes_per_second(stats),
                'backend_health': self._get_detailed_backend_health(),
                'connection_distribution': self._calculate_connection_distribution(connections)
            }
            
            return performance_metrics
        except Exception as e:
            logger.error(f"Error getting load balancer metrics: {e}")
            return {'error': str(e)}
    
    def trigger_correlation_analysis(self) -> Dict[str, Any]:
        """Trigger correlation analysis between load balancer and network flow data"""
        if not self.analytics_engine:
            return {'error': 'Analytics engine not available'}
        
        try:
            # Get recent metrics from both sources
            time_range = {
                'start': time.time() - 3600,  # Last hour
                'end': time.time()
            }
            
            lb_metrics = self.analytics_engine.get_metrics('load-balancer-pro', time_range)
            network_metrics = self.analytics_engine.get_metrics('network-flow-master', time_range)
            
            correlation_results = {
                'timestamp': time.time(),
                'load_balancer_metrics_count': len(lb_metrics),
                'network_flow_metrics_count': len(network_metrics),
                'correlation_available': len(lb_metrics) > 0 and len(network_metrics) > 0,
                'time_range': time_range
            }
            
            if correlation_results['correlation_available']:
                # Calculate correlation metrics
                correlation_results['analysis'] = self._analyze_lb_network_correlation(lb_metrics, network_metrics)
            
            return correlation_results
        except Exception as e:
            logger.error(f"Error triggering correlation analysis: {e}")
            return {'error': str(e)}
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _metrics_collection_loop(self) -> None:
        """Main loop for collecting and sending metrics to analytics engine"""
        collection_interval = self.config.get('collection_interval', 20.0)  # 20 seconds
        
        while not self.stop_event.wait(collection_interval):
            try:
                self._collect_and_send_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
    
    def _collect_and_send_metrics(self) -> None:
        """Collect metrics from load balancer and send to analytics engine"""
        if not self.lb_manager or not self.analytics_engine:
            return
        
        try:
            # Get load balancer statistics
            lb_stats = self.lb_manager.get_statistics()
            
            # Enhanced metrics collection
            enhanced_stats = {
                **lb_stats,
                'requests_per_second': self._calculate_requests_per_second(lb_stats),
                'average_response_time': self._calculate_average_response_time(),
                'error_rate': self._calculate_error_rate(),
                'backend_health_score': self._calculate_backend_health_score()
            }
            
            # Send to analytics engine
            session_id = self.analytics_engine.ingest_from_load_balancer(enhanced_stats)
            
            # Store for trend analysis
            self.last_stats = enhanced_stats
            self.performance_history.append({
                'timestamp': time.time(),
                'stats': enhanced_stats
            })
            
            # Keep only recent history
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            logger.debug(f"Sent load balancer metrics to analytics engine: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error collecting/sending load balancer metrics: {e}")
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for analytics events"""
        if not self.analytics_engine:
            return
        
        # Handle correlation results
        self.analytics_engine.on('pipeline:processed', self._handle_correlation_results)
        
        # Handle anomaly detection
        self.analytics_engine.on('error', self._handle_analytics_error)
    
    def _create_correlation_pipelines(self) -> None:
        """Create processing pipelines for cross-application correlation"""
        if not self.analytics_engine:
            return
        
        try:
            # Load Balancer Performance Analysis Pipeline
            lb_pipeline_id = self.analytics_engine.create_pipeline(
                name="Load Balancer Performance Analysis",
                input_sources=['load-balancer-pro'],
                processors=[
                    {
                        'type': 'anomaly',
                        'config': {
                            'threshold': 0.3,  # 30% deviation
                            'metrics': ['response_time', 'error_rate', 'connections_active'],
                            'window_size': 10
                        }
                    },
                    {
                        'type': 'aggregation',
                        'config': {
                            'interval': 60,  # 1 minute aggregation
                            'functions': ['avg', 'max', 'min', 'count']
                        }
                    }
                ],
                output_targets=['observability-dashboard']
            )
            
            # Cross-Application Correlation Pipeline
            correlation_pipeline_id = self.analytics_engine.create_pipeline(
                name="Network Flow - Load Balancer Correlation",
                input_sources=['network-flow-master', 'load-balancer-pro'],
                processors=[
                    {
                        'type': 'correlation',
                        'config': {
                            'correlation_metrics': [
                                'packets_per_second',
                                'connections_active',
                                'response_time',
                                'error_rate'
                            ],
                            'time_window': 300  # 5 minutes
                        }
                    }
                ],
                output_targets=['observability-dashboard']
            )
            
            logger.info(f"Created analytics pipelines: {lb_pipeline_id}, {correlation_pipeline_id}")
            
        except Exception as e:
            logger.error(f"Error creating correlation pipelines: {e}")
    
    def _handle_correlation_results(self, data: Dict[str, Any]) -> None:
        """Handle correlation analysis results"""
        try:
            pipeline_id = data.get('pipeline_id')
            processed_data = data.get('data')
            
            logger.debug(f"Correlation pipeline {pipeline_id} results: {type(processed_data)}")
            
            # Handle anomaly alerts for load balancer
            if isinstance(processed_data, list):
                for item in processed_data:
                    if isinstance(item, dict) and 'severity' in item:
                        self._handle_load_balancer_alert(item)
        
        except Exception as e:
            logger.error(f"Error handling correlation results: {e}")
    
    def _handle_load_balancer_alert(self, alert: Dict[str, Any]) -> None:
        """Handle load balancer specific alerts"""
        try:
            severity = alert.get('severity', 'medium')
            alert_type = alert.get('type', 'unknown')
            description = alert.get('description', 'Unknown alert')
            
            logger.warning(f"LOAD BALANCER ALERT [{severity.upper()}] {alert_type}: {description}")
            
            # Could integrate with external alerting systems here
            # For example: PagerDuty, Slack, email notifications
            
        except Exception as e:
            logger.error(f"Error handling load balancer alert: {e}")
    
    def _handle_analytics_error(self, error_data: Dict[str, Any]) -> None:
        """Handle errors from analytics engine"""
        error_type = error_data.get('type', 'unknown')
        error_message = error_data.get('error', 'Unknown error')
        
        logger.error(f"Load balancer analytics error [{error_type}]: {error_message}")
    
    def _calculate_requests_per_second(self, stats: Dict[str, Any]) -> float:
        """Calculate requests per second from statistics"""
        if not self.performance_history:
            return 0.0
        
        try:
            current_connections = stats.get('total_connections', 0)
            
            # Find stats from 60 seconds ago
            target_time = time.time() - 60
            previous_stats = None
            
            for entry in reversed(self.performance_history):
                if entry['timestamp'] <= target_time:
                    previous_stats = entry['stats']
                    break
            
            if previous_stats:
                previous_connections = previous_stats.get('total_connections', 0)
                time_diff = 60  # 60 seconds
                
                if time_diff > 0:
                    return max(0, (current_connections - previous_connections) / time_diff)
            
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_average_response_time(self) -> float:
        """Calculate average response time from recent history"""
        if not self.performance_history:
            return 0.0
        
        try:
            # Use last 10 measurements
            recent_entries = self.performance_history[-10:]
            response_times = []
            
            for entry in recent_entries:
                rt = entry['stats'].get('average_response_time', 0)
                if rt > 0:
                    response_times.append(rt)
            
            return sum(response_times) / len(response_times) if response_times else 0.0
        except Exception:
            return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate from load balancer statistics"""
        try:
            if not self.lb_manager:
                return 0.0
            
            # This would depend on how the load balancer tracks errors
            # For now, return a placeholder calculation
            stats = self.lb_manager.get_statistics()
            total_connections = stats.get('total_connections', 0)
            
            # Placeholder error calculation
            # In a real implementation, this would track actual errors
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_bytes_per_second(self, stats: Dict[str, Any]) -> float:
        """Calculate bytes per second throughput"""
        if not self.performance_history:
            return 0.0
        
        try:
            current_bytes = stats.get('bytes_sent', 0) + stats.get('bytes_received', 0)
            
            # Find stats from 60 seconds ago
            target_time = time.time() - 60
            previous_stats = None
            
            for entry in reversed(self.performance_history):
                if entry['timestamp'] <= target_time:
                    previous_stats = entry['stats']
                    break
            
            if previous_stats:
                previous_bytes = previous_stats.get('bytes_sent', 0) + previous_stats.get('bytes_received', 0)
                return max(0, (current_bytes - previous_bytes) / 60)
            
            return 0.0
        except Exception:
            return 0.0
    
    def _get_backend_health_summary(self) -> Dict[str, Any]:
        """Get summary of backend server health"""
        try:
            if not self.lb_manager:
                return {'healthy': 0, 'unhealthy': 0, 'total': 0}
            
            # This would depend on the load balancer's backend health tracking
            # Placeholder implementation
            return {
                'healthy': 2,
                'unhealthy': 0,
                'total': 2,
                'health_score': 1.0
            }
        except Exception:
            return {'healthy': 0, 'unhealthy': 0, 'total': 0}
    
    def _get_detailed_backend_health(self) -> List[Dict[str, Any]]:
        """Get detailed health information for each backend"""
        try:
            # Placeholder implementation
            # In real implementation, this would query actual backend health
            return [
                {
                    'address': '127.0.0.1:8081',
                    'healthy': True,
                    'response_time': 45,
                    'error_count': 0,
                    'last_check': time.time()
                },
                {
                    'address': '127.0.0.1:8082',
                    'healthy': True,
                    'response_time': 38,
                    'error_count': 0,
                    'last_check': time.time()
                }
            ]
        except Exception:
            return []
    
    def _calculate_connection_distribution(self, connections: List) -> Dict[str, int]:
        """Calculate how connections are distributed across backends"""
        try:
            distribution = {}
            for conn in connections:
                backend = getattr(conn, 'backend_address', 'unknown')
                distribution[backend] = distribution.get(backend, 0) + 1
            return distribution
        except Exception:
            return {}
    
    def _calculate_backend_health_score(self) -> float:
        """Calculate overall backend health score (0.0 to 1.0)"""
        try:
            health_summary = self._get_backend_health_summary()
            total = health_summary.get('total', 0)
            healthy = health_summary.get('healthy', 0)
            
            return healthy / total if total > 0 else 1.0
        except Exception:
            return 1.0
    
    def _analyze_lb_network_correlation(self, lb_metrics: List, network_metrics: List) -> Dict[str, Any]:
        """Analyze correlation between load balancer and network flow metrics"""
        try:
            analysis = {
                'correlation_score': 0.0,
                'insights': [],
                'recommendations': []
            }
            
            if len(lb_metrics) > 0 and len(network_metrics) > 0:
                # Simple correlation analysis
                # In production, this would use statistical correlation algorithms
                analysis['correlation_score'] = 0.75  # Placeholder
                
                analysis['insights'] = [
                    "Network flow patterns correlate with load balancer performance",
                    "Peak traffic times show increased response latency",
                    "Backend distribution is balanced during normal operations"
                ]
                
                analysis['recommendations'] = [
                    "Consider scaling backends during peak hours",
                    "Monitor response times during high packet rates",
                    "Implement adaptive load balancing based on network conditions"
                ]
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing correlation: {e}")
            return {'error': str(e)}

# =============================================================================
# Flask Integration Functions
# =============================================================================

def create_analytics_routes(app, integration: LoadBalancerAnalyticsIntegration):
    """
    Create Flask routes for load balancer analytics integration
    
    Args:
        app: Flask application instance
        integration: LoadBalancerAnalyticsIntegration instance
    """
    
    @app.route('/api/analytics/summary')
    def lb_analytics_summary():
        """Get load balancer analytics summary"""
        return integration.get_analytics_summary()
    
    @app.route('/api/analytics/metrics')
    def lb_analytics_metrics():
        """Get detailed load balancer metrics"""
        return integration.get_load_balancer_metrics()
    
    @app.route('/api/analytics/correlation')
    def lb_analytics_correlation():
        """Trigger correlation analysis"""
        return integration.trigger_correlation_analysis()
    
    @app.route('/api/analytics/status')
    def lb_analytics_status():
        """Get analytics integration status"""
        return {
            'available': ANALYTICS_AVAILABLE,
            'running': integration.is_running,
            'engine_running': integration.analytics_engine.is_running if integration.analytics_engine else False,
            'load_balancer_connected': integration.lb_manager is not None
        }

def setup_analytics_integration(app, lb_manager, config: Optional[Dict[str, Any]] = None):
    """
    Setup analytics integration for the Load Balancer Pro Flask app
    
    Args:
        app: Flask application instance
        lb_manager: LBManager instance
        config: Optional configuration
    
    Returns:
        LoadBalancerAnalyticsIntegration instance
    """
    
    # Create integration instance
    integration = LoadBalancerAnalyticsIntegration(lb_manager, config)
    
    # Create routes
    create_analytics_routes(app, integration)
    
    # Add template context processor
    @app.context_processor
    def inject_analytics_status():
        return {
            'analytics_available': ANALYTICS_AVAILABLE,
            'analytics_running': integration.is_running
        }
    
    # Setup shutdown handler
    import atexit
    atexit.register(lambda: integration.stop())
    
    return integration

# =============================================================================
# Utility Functions
# =============================================================================

def get_analytics_dashboard_data(integration: LoadBalancerAnalyticsIntegration) -> Dict[str, Any]:
    """
    Get formatted analytics data for dashboard display
    
    Args:
        integration: LoadBalancerAnalyticsIntegration instance
    
    Returns:
        Formatted dashboard data
    """
    if not integration.analytics_engine:
        return {
            'available': False,
            'message': 'Analytics not available'
        }
    
    try:
        summary = integration.get_analytics_summary()
        metrics = integration.get_load_balancer_metrics()
        
        return {
            'available': True,
            'summary': summary,
            'metrics': metrics,
            'last_updated': time.strftime('%H:%M:%S', time.localtime()),
            'performance_trend': 'stable'  # Could calculate actual trend
        }
    
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }

