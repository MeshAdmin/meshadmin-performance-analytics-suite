"""
Analytics Integration for Network Flow Master
=============================================

This module integrates the enhanced flow processor with the analytics engine,
enabling real-time metrics sharing across the MPTCP Performance Analytics Suite.
"""

import sys
import os
import time
import threading
from typing import Dict, Any, Optional
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

class NetworkFlowAnalyticsIntegration:
    """
    Integration layer between Enhanced Flow Processor and Analytics Engine
    """
    
    def __init__(self, enhanced_processor=None, config: Optional[Dict[str, Any]] = None):
        self.enhanced_processor = enhanced_processor
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.config = config or {}
        self.is_running = False
        self.metrics_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Configure analytics if available
        if ANALYTICS_AVAILABLE:
            self.analytics_engine = create_analytics_engine({
                'processing_interval': self.config.get('analytics_interval', 10.0),
                'max_metrics_history': self.config.get('max_history', 500)
            })
        else:
            logger.warning("Analytics engine not available - metrics will not be shared")
    
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
        
        logger.info("✅ Network Flow Analytics Integration started")
    
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
        
        logger.info("🛑 Network Flow Analytics Integration stopped")
    
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
            return summary
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def get_correlation_data(self) -> Dict[str, Any]:
        """Get correlation data between network flows and other sources"""
        if not self.analytics_engine:
            return {'correlations': []}
        
        # Get metrics from the last hour
        time_range = {
            'start': time.time() - 3600,
            'end': time.time()
        }
        
        try:
            network_metrics = self.analytics_engine.get_metrics('network-flow-master', time_range)
            
            return {
                'network_metrics_count': len(network_metrics),
                'time_range': time_range,
                'last_updated': time.time()
            }
        except Exception as e:
            logger.error(f"Error getting correlation data: {e}")
            return {'error': str(e)}
    
    def _metrics_collection_loop(self) -> None:
        """Main loop for collecting and sending metrics to analytics engine"""
        collection_interval = self.config.get('collection_interval', 30.0)  # 30 seconds
        
        while not self.stop_event.wait(collection_interval):
            try:
                self._collect_and_send_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
    
    def _collect_and_send_metrics(self) -> None:
        """Collect metrics from enhanced processor and send to analytics engine"""
        if not self.enhanced_processor or not self.analytics_engine:
            return
        
        try:
            # Get performance metrics from enhanced processor
            processor_metrics = self.enhanced_processor.get_performance_metrics()
            
            # Send to analytics engine
            session_id = self.analytics_engine.ingest_from_enhanced_processor(processor_metrics)
            
            logger.debug(f"Sent metrics to analytics engine: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error collecting/sending metrics: {e}")
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for analytics events"""
        if not self.analytics_engine:
            return
        
        # Handle anomaly detection
        self.analytics_engine.on('pipeline:processed', self._handle_pipeline_results)
        
        # Handle analytics errors
        self.analytics_engine.on('error', self._handle_analytics_error)
    
    def _handle_pipeline_results(self, data: Dict[str, Any]) -> None:
        """Handle results from analytics pipeline processing"""
        try:
            pipeline_id = data.get('pipeline_id')
            processed_data = data.get('data')
            
            logger.debug(f"Pipeline {pipeline_id} processed data: {type(processed_data)}")
            
            # Handle anomaly alerts
            if isinstance(processed_data, list):
                for item in processed_data:
                    if isinstance(item, dict) and item.get('type') == 'packet_rate_anomaly':
                        self._handle_anomaly_alert(item)
        
        except Exception as e:
            logger.error(f"Error handling pipeline results: {e}")
    
    def _handle_anomaly_alert(self, alert: Dict[str, Any]) -> None:
        """Handle anomaly alerts from analytics engine"""
        try:
            severity = alert.get('severity', 'medium')
            description = alert.get('description', 'Unknown anomaly')
            
            logger.warning(f"ANOMALY DETECTED [{severity.upper()}]: {description}")
            
            # You could integrate with alerting systems here
            # For example, send notifications, trigger automated responses, etc.
            
        except Exception as e:
            logger.error(f"Error handling anomaly alert: {e}")
    
    def _handle_analytics_error(self, error_data: Dict[str, Any]) -> None:
        """Handle errors from analytics engine"""
        error_type = error_data.get('type', 'unknown')
        error_message = error_data.get('error', 'Unknown error')
        
        logger.error(f"Analytics engine error [{error_type}]: {error_message}")

# =============================================================================
# Flask Integration Functions
# =============================================================================

def create_analytics_routes(app, integration: NetworkFlowAnalyticsIntegration):
    """
    Create Flask routes for analytics integration
    
    Args:
        app: Flask application instance
        integration: NetworkFlowAnalyticsIntegration instance
    """
    
    @app.route('/api/analytics/summary')
    def analytics_summary():
        """Get analytics summary"""
        return integration.get_analytics_summary()
    
    @app.route('/api/analytics/correlations')
    def analytics_correlations():
        """Get correlation data"""
        return integration.get_correlation_data()
    
    @app.route('/api/analytics/status')
    def analytics_status():
        """Get analytics integration status"""
        return {
            'available': ANALYTICS_AVAILABLE,
            'running': integration.is_running,
            'engine_running': integration.analytics_engine.is_running if integration.analytics_engine else False
        }

def setup_analytics_integration(app, enhanced_processor, config: Optional[Dict[str, Any]] = None):
    """
    Setup analytics integration for the Flask app
    
    Args:
        app: Flask application instance
        enhanced_processor: EnhancedFlowProcessor instance
        config: Optional configuration
    
    Returns:
        NetworkFlowAnalyticsIntegration instance
    """
    
    # Create integration instance
    integration = NetworkFlowAnalyticsIntegration(enhanced_processor, config)
    
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

def get_analytics_metrics_for_display(integration: NetworkFlowAnalyticsIntegration) -> Dict[str, Any]:
    """
    Get formatted analytics metrics for dashboard display
    
    Args:
        integration: NetworkFlowAnalyticsIntegration instance
    
    Returns:
        Formatted metrics dict
    """
    if not integration.analytics_engine:
        return {
            'available': False,
            'message': 'Analytics not available'
        }
    
    try:
        summary = integration.analytics_engine.get_real_time_summary()
        
        return {
            'available': True,
            'total_packets_per_second': f"{summary.get('total_packets_per_second', 0):.1f}",
            'total_connections': f"{summary.get('total_connections', 0):,}",
            'cache_efficiency': f"{summary.get('cache_efficiency', 0):.1%}",
            'sources_active': summary.get('sources_active', 0),
            'last_updated': time.strftime('%H:%M:%S', time.localtime()),
            'source_breakdown': summary.get('source_breakdown', {})
        }
    
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }

def create_sample_analytics_pipeline(integration: NetworkFlowAnalyticsIntegration) -> Optional[str]:
    """
    Create a sample analytics pipeline for demonstration
    
    Args:
        integration: NetworkFlowAnalyticsIntegration instance
    
    Returns:
        Pipeline ID if successful, None otherwise
    """
    if not integration.analytics_engine:
        return None
    
    try:
        pipeline_id = integration.analytics_engine.create_pipeline(
            name="Network Flow Performance Analysis",
            input_sources=['network-flow-master'],
            processors=[
                {
                    'type': 'anomaly',
                    'config': {
                        'threshold': 0.5,
                        'window_size': 10
                    }
                },
                {
                    'type': 'aggregation',
                    'config': {
                        'interval': 60,
                        'functions': ['avg', 'max', 'min']
                    }
                }
            ],
            output_targets=['observability-dashboard']
        )
        
        logger.info(f"Created sample analytics pipeline: {pipeline_id}")
        return pipeline_id
    
    except Exception as e:
        logger.error(f"Error creating sample pipeline: {e}")
        return None

