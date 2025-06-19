"""
MPTCP Performance Analytics Engine - Python Bridge
==================================================

This module provides a Python interface to the TypeScript analytics engine,
enabling seamless integration with Flask applications like Network Flow Master,
Load Balancer Pro, and Observability Dashboard.
"""

import json
import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Core Data Structures
# =============================================================================

@dataclass
class MetricPoint:
    """Individual metric measurement point"""
    timestamp: float
    value: float
    tags: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class FlowMetrics:
    """Flow metrics from any source application"""
    source: str  # 'network-flow-master' | 'load-balancer-pro' | 'observability-dashboard'
    type: str    # 'netflow' | 'sflow' | 'load-balancing' | 'system' | 'custom'
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    metrics: Optional[Dict[str, List[MetricPoint]]] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())

@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all sources"""
    timestamp: float
    total_packets_per_second: float = 0.0
    total_connections: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    cache_efficiency: float = 0.0
    source_breakdown: Optional[Dict[str, Dict[str, float]]] = None
    
    def __post_init__(self):
        if self.source_breakdown is None:
            self.source_breakdown = {}

@dataclass
class AnomalyAlert:
    """Anomaly detection alert"""
    id: str
    type: str
    severity: str  # 'low' | 'medium' | 'high' | 'critical'
    description: str
    timestamp: float
    source: str
    device_id: Optional[str] = None

# =============================================================================
# Analytics Engine Python Implementation
# =============================================================================

class AnalyticsEngine:
    """
    Python implementation of the analytics engine for Flask integration
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_running = False
        self.metrics_store: Dict[str, List[FlowMetrics]] = defaultdict(list)
        self.processors: Dict[str, 'MetricProcessor'] = {}
        self.pipelines: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Setup default processors
        self._setup_default_processors()
        
        # Metrics history management
        self.max_history = self.config.get('max_metrics_history', 1000)
        self.processing_interval = self.config.get('processing_interval', 5.0)  # seconds
    
    def start(self) -> None:
        """Start the analytics engine"""
        if self.is_running:
            raise RuntimeError("Analytics engine is already running")
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self._emit_event('started', {'timestamp': time.time()})
        logger.info("✅ Analytics Engine started")
    
    def stop(self) -> None:
        """Stop the analytics engine"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        self._emit_event('stopped', {'timestamp': time.time()})
        logger.info("🛑 Analytics Engine stopped")
    
    def ingest_metrics(self, metrics: FlowMetrics) -> str:
        """
        Ingest metrics from any source application
        
        Args:
            metrics: FlowMetrics object containing the data
            
        Returns:
            Session ID for tracking
        """
        source = metrics.source
        
        # Store metrics by source
        self.metrics_store[source].append(metrics)
        
        # Maintain history limit
        if len(self.metrics_store[source]) > self.max_history:
            self.metrics_store[source] = self.metrics_store[source][-self.max_history:]
        
        # Emit ingestion event
        self._emit_event('metrics:ingested', {
            'id': metrics.session_id,
            'source': source,
            'timestamp': time.time(),
            'metrics_count': len(metrics.metrics) if metrics.metrics else 0
        })
        
        return metrics.session_id
    
    def get_metrics(self, source: str, time_range: Optional[Dict[str, float]] = None) -> List[FlowMetrics]:
        """
        Get metrics for a specific source
        
        Args:
            source: Source application name
            time_range: Optional dict with 'start' and 'end' timestamps
            
        Returns:
            List of FlowMetrics
        """
        source_metrics = self.metrics_store.get(source, [])
        
        if not time_range:
            return source_metrics
        
        # Filter by time range
        filtered = []
        for metric in source_metrics:
            if metric.metrics:
                # Get latest timestamp from any metric in the set
                latest_time = max(
                    max(point.timestamp for point in points) 
                    for points in metric.metrics.values() 
                    if points
                )
                
                if time_range['start'] <= latest_time <= time_range['end']:
                    filtered.append(metric)
        
        return filtered
    
    def get_aggregated_metrics(self, time_range: Dict[str, float]) -> AggregatedMetrics:
        """
        Get aggregated metrics across all sources
        
        Args:
            time_range: Dict with 'start' and 'end' timestamps
            
        Returns:
            AggregatedMetrics object
        """
        aggregated = AggregatedMetrics(timestamp=time.time())
        
        # Process each source
        for source, metrics_list in self.metrics_store.items():
            filtered_metrics = self.get_metrics(source, time_range)
            
            if filtered_metrics:
                source_stats = self._calculate_source_metrics(filtered_metrics)
                aggregated.source_breakdown[source] = source_stats
                
                # Add to totals
                aggregated.total_packets_per_second += source_stats.get('packets_per_second', 0)
                aggregated.total_connections += int(source_stats.get('connections', 0))
        
        return aggregated
    
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler"""
        self.event_handlers[event].append(handler)
    
    def create_pipeline(self, name: str, input_sources: List[str], 
                       processors: List[Dict[str, Any]], output_targets: List[str]) -> str:
        """Create a processing pipeline"""
        pipeline_id = str(uuid.uuid4())
        
        pipeline = {
            'id': pipeline_id,
            'name': name,
            'input_sources': input_sources,
            'processors': processors,
            'output_targets': output_targets,
            'enabled': True
        }
        
        self.pipelines[pipeline_id] = pipeline
        self._emit_event('pipeline:created', pipeline)
        
        return pipeline_id
    
    # =========================================================================
    # Integration Methods for Flask Applications
    # =========================================================================
    
    def ingest_from_enhanced_processor(self, processor_metrics: Dict[str, Any]) -> str:
        """
        Ingest metrics from Enhanced Flow Processor
        
        Args:
            processor_metrics: Metrics dict from get_performance_metrics()
            
        Returns:
            Session ID
        """
        metrics = FlowMetrics(
            source='network-flow-master',
            type='netflow',
            metrics={
                'packets_per_second': [MetricPoint(
                    timestamp=time.time(),
                    value=processor_metrics.get('packets_per_second', 0)
                )],
                'cache_hit_ratio': [MetricPoint(
                    timestamp=time.time(),
                    value=processor_metrics.get('cache_hit_ratio', 0)
                )],
                'connections_active': [MetricPoint(
                    timestamp=time.time(),
                    value=processor_metrics.get('flows_stored', 0)
                )],
                'memory_usage': [MetricPoint(
                    timestamp=time.time(),
                    value=processor_metrics.get('memory_usage_mb', 0)
                )]
            }
        )
        
        return self.ingest_metrics(metrics)
    
    def ingest_from_load_balancer(self, lb_stats: Dict[str, Any]) -> str:
        """
        Ingest metrics from Load Balancer Pro
        
        Args:
            lb_stats: Statistics from LoadBalancer.get_statistics()
            
        Returns:
            Session ID
        """
        metrics = FlowMetrics(
            source='load-balancer-pro',
            type='load-balancing',
            metrics={
                'connections_active': [MetricPoint(
                    timestamp=time.time(),
                    value=lb_stats.get('active_connections', 0)
                )],
                'response_time': [MetricPoint(
                    timestamp=time.time(),
                    value=lb_stats.get('average_response_time', 0)
                )],
                'error_rate': [MetricPoint(
                    timestamp=time.time(),
                    value=lb_stats.get('error_rate', 0)
                )],
                'bytes_per_second': [MetricPoint(
                    timestamp=time.time(),
                    value=lb_stats.get('bytes_sent', 0) + lb_stats.get('bytes_received', 0)
                )]
            }
        )
        
        return self.ingest_metrics(metrics)
    
    def ingest_from_observability_dashboard(self, dashboard_metrics: Dict[str, Any]) -> str:
        """
        Ingest metrics from Observability Dashboard
        
        Args:
            dashboard_metrics: Various system and application metrics
            
        Returns:
            Session ID
        """
        metrics = FlowMetrics(
            source='observability-dashboard',
            type='system',
            metrics={}
        )
        
        # Convert dashboard metrics to standardized format
        for key, value in dashboard_metrics.items():
            if isinstance(value, (int, float)):
                metrics.metrics[key] = [MetricPoint(
                    timestamp=time.time(),
                    value=float(value)
                )]
        
        return self.ingest_metrics(metrics)
    
    def get_real_time_summary(self) -> Dict[str, Any]:
        """
        Get real-time summary for dashboard display
        
        Returns:
            Summary metrics dict
        """
        now = time.time()
        last_5_min = now - 300  # 5 minutes ago
        
        aggregated = self.get_aggregated_metrics({
            'start': last_5_min,
            'end': now
        })
        
        return {
            'timestamp': aggregated.timestamp,
            'total_packets_per_second': aggregated.total_packets_per_second,
            'total_connections': aggregated.total_connections,
            'average_response_time': aggregated.average_response_time,
            'error_rate': aggregated.error_rate,
            'cache_efficiency': aggregated.cache_efficiency,
            'sources_active': len([s for s in aggregated.source_breakdown.keys() 
                                 if aggregated.source_breakdown[s]]),
            'source_breakdown': aggregated.source_breakdown
        }
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _setup_default_processors(self) -> None:
        """Setup default metric processors"""
        self.processors['correlation'] = CorrelationProcessor()
        self.processors['anomaly'] = AnomalyDetectionProcessor()
        self.processors['aggregation'] = AggregationProcessor()
    
    def _processing_loop(self) -> None:
        """Main processing loop running in background thread"""
        while not self.stop_event.wait(self.processing_interval):
            try:
                self._process_pipelines()
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self._emit_event('error', {
                    'type': 'processing_error',
                    'error': str(e),
                    'timestamp': time.time()
                })
    
    def _process_pipelines(self) -> None:
        """Process all enabled pipelines"""
        for pipeline_id, pipeline in self.pipelines.items():
            if not pipeline.get('enabled', True):
                continue
            
            try:
                self._execute_pipeline(pipeline)
            except Exception as e:
                self._emit_event('error', {
                    'type': 'pipeline_error',
                    'pipeline_id': pipeline_id,
                    'error': str(e),
                    'timestamp': time.time()
                })
    
    def _execute_pipeline(self, pipeline: Dict[str, Any]) -> None:
        """Execute a single pipeline"""
        # Get input data
        input_data = []
        for source in pipeline['input_sources']:
            input_data.extend(self.metrics_store.get(source, []))
        
        if not input_data:
            return
        
        # Process through pipeline processors
        processed_data = input_data
        for processor_config in pipeline['processors']:
            processor_type = processor_config['type']
            processor = self.processors.get(processor_type)
            
            if processor:
                processed_data = processor.process(processed_data, processor_config.get('config', {}))
        
        # Emit results
        self._emit_event('pipeline:processed', {
            'pipeline_id': pipeline['id'],
            'data': processed_data,
            'timestamp': time.time()
        })
    
    def _calculate_source_metrics(self, metrics_list: List[FlowMetrics]) -> Dict[str, float]:
        """Calculate aggregated metrics for a source"""
        if not metrics_list:
            return {}
        
        # Get the latest metrics
        latest = metrics_list[-1]
        
        result = {}
        if latest.metrics:
            for metric_name, points in latest.metrics.items():
                if points:
                    latest_point = points[-1]
                    result[metric_name] = latest_point.value
        
        return result
    
    def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to registered handlers"""
        for handler in self.event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")

# =============================================================================
# Metric Processors
# =============================================================================

class MetricProcessor(ABC):
    """Abstract base class for metric processors"""
    
    @abstractmethod
    def process(self, data: List[FlowMetrics], config: Dict[str, Any]) -> Any:
        """Process metrics data"""
        pass

class CorrelationProcessor(MetricProcessor):
    """Correlate metrics across different sources"""
    
    def process(self, data: List[FlowMetrics], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        correlations = []
        
        # Group by source
        by_source = defaultdict(list)
        for metrics in data:
            by_source[metrics.source].append(metrics)
        
        # Find correlations between network flow and load balancer
        if 'network-flow-master' in by_source and 'load-balancer-pro' in by_source:
            network_metrics = by_source['network-flow-master']
            lb_metrics = by_source['load-balancer-pro']
            
            correlation_score = self._calculate_correlation(network_metrics, lb_metrics)
            
            correlations.append({
                'id': str(uuid.uuid4()),
                'type': 'network_lb_correlation',
                'correlation_score': correlation_score,
                'timestamp': time.time(),
                'sources': ['network-flow-master', 'load-balancer-pro']
            })
        
        return correlations
    
    def _calculate_correlation(self, metrics_a: List[FlowMetrics], 
                             metrics_b: List[FlowMetrics]) -> float:
        """Calculate correlation between two metric sets"""
        # Simplified correlation - in practice would use statistical methods
        return 0.75  # Mock correlation score

class AnomalyDetectionProcessor(MetricProcessor):
    """Detect anomalies in metric data"""
    
    def process(self, data: List[FlowMetrics], config: Dict[str, Any]) -> List[AnomalyAlert]:
        anomalies = []
        
        for metrics in data:
            if not metrics.metrics:
                continue
            
            # Check packet rate anomalies
            if 'packets_per_second' in metrics.metrics:
                packet_points = metrics.metrics['packets_per_second']
                
                if len(packet_points) >= 5:
                    recent = packet_points[-5:]
                    avg = sum(p.value for p in recent) / len(recent)
                    latest = recent[-1].value
                    
                    if abs(latest - avg) > avg * 0.5:  # 50% deviation
                        anomalies.append(AnomalyAlert(
                            id=str(uuid.uuid4()),
                            type='packet_rate_anomaly',
                            severity='high' if latest > avg * 1.5 else 'medium',
                            description=f"Packet rate anomaly: {latest:.2f} pps (avg: {avg:.2f} pps)",
                            timestamp=time.time(),
                            source=metrics.source,
                            device_id=metrics.device_id
                        ))
        
        return anomalies

class AggregationProcessor(MetricProcessor):
    """Aggregate metrics over time windows"""
    
    def process(self, data: List[FlowMetrics], config: Dict[str, Any]) -> AggregatedMetrics:
        aggregated = AggregatedMetrics(timestamp=time.time())
        
        # Group by source and aggregate
        by_source = defaultdict(list)
        for metrics in data:
            by_source[metrics.source].append(metrics)
        
        for source, metrics_list in by_source.items():
            source_metrics = self._aggregate_source(metrics_list)
            aggregated.source_breakdown[source] = source_metrics
            
            # Add to totals
            aggregated.total_packets_per_second += source_metrics.get('packets_per_second', 0)
            aggregated.total_connections += int(source_metrics.get('connections', 0))
        
        return aggregated
    
    def _aggregate_source(self, metrics_list: List[FlowMetrics]) -> Dict[str, float]:
        """Aggregate metrics for a single source"""
        if not metrics_list:
            return {}
        
        # Simple aggregation - take latest values
        latest = metrics_list[-1]
        result = {}
        
        if latest.metrics:
            for metric_name, points in latest.metrics.items():
                if points:
                    result[metric_name] = points[-1].value
        
        return result

# =============================================================================
# Factory Function
# =============================================================================

def create_analytics_engine(config: Optional[Dict[str, Any]] = None) -> AnalyticsEngine:
    """
    Create a new analytics engine instance
    
    Args:
        config: Optional configuration dict
        
    Returns:
        AnalyticsEngine instance
    """
    default_config = {
        'processing_interval': 5.0,  # seconds
        'max_metrics_history': 1000,
        'enabled_processors': ['correlation', 'anomaly', 'aggregation']
    }
    
    if config:
        default_config.update(config)
    
    return AnalyticsEngine(default_config)

# =============================================================================
# Flask Integration Helpers
# =============================================================================

def create_flask_analytics_integration(app, analytics_engine: AnalyticsEngine):
    """
    Create Flask integration for analytics engine
    
    Args:
        app: Flask application instance
        analytics_engine: AnalyticsEngine instance
    """
    
    @app.route('/api/analytics/metrics')
    def get_analytics_metrics():
        """Get current analytics metrics"""
        return analytics_engine.get_real_time_summary()
    
    @app.route('/api/analytics/metrics/<source>')
    def get_source_metrics(source: str):
        """Get metrics for a specific source"""
        time_range = {
            'start': time.time() - 3600,  # Last hour
            'end': time.time()
        }
        metrics = analytics_engine.get_metrics(source, time_range)
        
        return {
            'source': source,
            'metrics_count': len(metrics),
            'latest_metrics': [asdict(m) for m in metrics[-10:]]  # Last 10
        }
    
    @app.route('/api/analytics/aggregated')
    def get_aggregated_metrics():
        """Get aggregated metrics across all sources"""
        time_range = {
            'start': time.time() - 3600,  # Last hour
            'end': time.time()
        }
        aggregated = analytics_engine.get_aggregated_metrics(time_range)
        return asdict(aggregated)
    
    # Start the analytics engine
    analytics_engine.start()
    
    return analytics_engine

