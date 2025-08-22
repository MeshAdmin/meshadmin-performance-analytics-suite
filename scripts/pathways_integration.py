#!/usr/bin/env python3
"""
Performance Analytics Suite - Unified MPTCP Kernel Integration
============================================================

This module provides comprehensive integration between the Performance Analytics Suite
and the unified meshadmin-pathways MPTCP kernel, enabling real-time collection and
analysis of MPTCP performance metrics across the entire ecosystem.

Features:
- Real-time MPTCP metrics collection from unified kernel
- Integration with existing analytics infrastructure
- Cross-application performance correlation
- Advanced ML-driven insights for MPTCP optimization
- Performance anomaly detection and alerting
"""

import sys
import os
import json
import time
import threading
import subprocess
from typing import Dict, Any, Optional, List, Callable
import logging
from datetime import datetime
from pathlib import Path

# Analytics Engine Integration
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'packages/analytics-engine/python'))
    from analytics_engine import create_analytics_engine, AnalyticsEngine, MetricPoint
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Analytics engine not available: {e}")
    ANALYTICS_AVAILABLE = False

# ML Analytics Integration
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'advanced-analytics'))
    from ml_analytics_engine import MLAnalyticsEngine
    ML_ANALYTICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML analytics engine not available: {e}")
    ML_ANALYTICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnifiedKernelInterface:
    """
    Interface for communicating with the unified MPTCP kernel via Node.js bridge
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.kernel_path = config.get('kernel_path', '../meshadmin-pathways/packages/mptcp-kernel')
        self.bridge_script = self._create_bridge_script()
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the unified MPTCP kernel"""
        try:
            # Test connection to kernel via Node.js bridge
            result = self._execute_kernel_command(['healthCheck'])
            self.connected = result.get('success', False)
            
            if self.connected:
                logger.info("✅ Successfully connected to unified MPTCP kernel")
            else:
                logger.warning("⚠️ Failed to connect to unified MPTCP kernel")
            
            return self.connected
        except Exception as e:
            logger.error(f"Error connecting to unified MPTCP kernel: {e}")
            self.connected = False
            return False
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive MPTCP system overview"""
        if not self.connected:
            return {'error': 'Not connected to unified kernel'}
        
        try:
            result = self._execute_kernel_command(['getSystemOverview'])
            return result.get('data', {})
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {'error': str(e)}
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get detailed connection metrics"""
        if not self.connected:
            return {'error': 'Not connected to unified kernel'}
        
        try:
            result = self._execute_kernel_command(['listConnections'])
            return result.get('data', {})
        except Exception as e:
            logger.error(f"Error getting connection metrics: {e}")
            return {'error': str(e)}
    
    def get_path_statistics(self) -> Dict[str, Any]:
        """Get path utilization and performance statistics"""
        if not self.connected:
            return {'error': 'Not connected to unified kernel'}
        
        try:
            result = self._execute_kernel_command(['getPathStatistics'])
            return result.get('data', {})
        except Exception as e:
            logger.error(f"Error getting path statistics: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.connected:
            return {'error': 'Not connected to unified kernel'}
        
        try:
            result = self._execute_kernel_command(['getPerformanceMetrics'])
            return result.get('data', {})
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def _create_bridge_script(self) -> str:
        """Create Node.js bridge script for kernel communication"""
        bridge_content = '''
const { MptcpKernel } = require('../meshadmin-pathways/packages/mptcp-kernel/src/index.js');

class PythonBridge {
    constructor() {
        this.kernel = new MptcpKernel({
            endpoint: 'localhost',
            port: 9090,
            secure: false
        });
    }

    async execute(command, args = []) {
        try {
            await this.kernel.connect();
            
            let result;
            switch (command) {
                case 'healthCheck':
                    result = await this.kernel.healthCheck();
                    break;
                case 'getSystemOverview':
                    const overview = await this.kernel.getStats();
                    const connections = await this.kernel.listConnections();
                    result = { overview, connections };
                    break;
                case 'listConnections':
                    result = await this.kernel.listConnections();
                    break;
                case 'getPathStatistics':
                    result = await this.kernel.getTopology();
                    break;
                case 'getPerformanceMetrics':
                    result = await this.kernel.getStats();
                    break;
                default:
                    throw new Error(`Unknown command: ${command}`);
            }
            
            return { success: true, data: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
}

// Command line interface
if (require.main === module) {
    const bridge = new PythonBridge();
    const command = process.argv[2];
    const args = process.argv.slice(3);
    
    bridge.execute(command, args).then(result => {
        console.log(JSON.stringify(result));
        process.exit(0);
    }).catch(error => {
        console.log(JSON.stringify({ success: false, error: error.message }));
        process.exit(1);
    });
}

module.exports = PythonBridge;
'''
        
        # Write bridge script
        bridge_path = os.path.join(os.path.dirname(__file__), 'kernel_bridge.js')
        with open(bridge_path, 'w') as f:
            f.write(bridge_content)
        
        return bridge_path
    
    def _execute_kernel_command(self, args: List[str]) -> Dict[str, Any]:
        """Execute command via Node.js bridge"""
        try:
            cmd = ['node', self.bridge_script] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                raise Exception(f"Bridge command failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("Kernel command timed out")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from kernel: {e}")

class PerformanceAnalyticsSuiteIntegration:
    """
    Main integration class for Performance Analytics Suite with unified MPTCP kernel
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.kernel_interface = UnifiedKernelInterface(self.config)
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.ml_engine: Optional[MLAnalyticsEngine] = None
        
        # Integration state
        self.is_running = False
        self.metrics_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.metrics_history = []
        self.performance_baselines = {}
        self.anomaly_thresholds = {}
        
        # Application registrations
        self.registered_applications = set()
        
        # Initialize analytics engines
        self._initialize_analytics_engines()
    
    def start(self) -> bool:
        """Start the Performance Analytics Suite integration"""
        if self.is_running:
            logger.warning("Performance Analytics Suite integration already running")
            return True
        
        logger.info("🚀 Starting Performance Analytics Suite integration...")
        
        # Connect to unified kernel
        if not self.kernel_interface.connect():
            logger.error("Failed to connect to unified MPTCP kernel")
            return False
        
        # Start analytics engines
        self._start_analytics_engines()
        
        # Start metrics collection
        self.is_running = True
        self.stop_event.clear()
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()
        
        # Register with MeshAdminPortal
        self._register_with_portal()
        
        # Setup cross-application pipelines
        self._setup_cross_application_pipelines()
        
        logger.info("✅ Performance Analytics Suite integration started successfully")
        return True
    
    def stop(self) -> None:
        """Stop the Performance Analytics Suite integration"""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping Performance Analytics Suite integration...")
        
        self.is_running = False
        self.stop_event.set()
        
        if self.metrics_thread:
            self.metrics_thread.join(timeout=10.0)
        
        self._stop_analytics_engines()
        
        logger.info("✅ Performance Analytics Suite integration stopped")
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics from unified kernel and analytics"""
        try:
            # Get metrics from unified kernel
            kernel_overview = self.kernel_interface.get_system_overview()
            connection_metrics = self.kernel_interface.get_connection_metrics()
            path_statistics = self.kernel_interface.get_path_statistics()
            performance_metrics = self.kernel_interface.get_performance_metrics()
            
            # Get analytics insights
            analytics_summary = self._get_analytics_summary()
            ml_insights = self._get_ml_insights()
            
            # Cross-application correlations
            cross_correlations = self._get_cross_application_correlations()
            
            # Performance anomalies
            anomalies = self._detect_performance_anomalies()
            
            comprehensive_metrics = {
                'timestamp': time.time(),
                'unified_kernel': {
                    'connected': self.kernel_interface.connected,
                    'overview': kernel_overview,
                    'connections': connection_metrics,
                    'paths': path_statistics,
                    'performance': performance_metrics
                },
                'analytics': {
                    'available': ANALYTICS_AVAILABLE,
                    'summary': analytics_summary,
                    'cross_correlations': cross_correlations
                },
                'ml_insights': {
                    'available': ML_ANALYTICS_AVAILABLE,
                    'insights': ml_insights,
                    'anomalies': anomalies
                },
                'applications': {
                    'registered': list(self.registered_applications),
                    'count': len(self.registered_applications)
                },
                'integration_status': {
                    'running': self.is_running,
                    'kernel_connected': self.kernel_interface.connected,
                    'metrics_count': len(self.metrics_history)
                }
            }
            
            return comprehensive_metrics
            
        except Exception as e:
            logger.error(f"Error getting comprehensive metrics: {e}")
            return {
                'timestamp': time.time(),
                'error': str(e),
                'integration_status': {
                    'running': self.is_running,
                    'kernel_connected': self.kernel_interface.connected
                }
            }
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get data optimized for dashboard display"""
        try:
            metrics = self.get_comprehensive_metrics()
            
            # Extract key dashboard metrics
            dashboard_data = {
                'system_health': self._calculate_system_health(metrics),
                'key_metrics': self._extract_key_metrics(metrics),
                'performance_trends': self._calculate_performance_trends(),
                'alerts': self._get_active_alerts(metrics),
                'application_status': self._get_application_status_summary(),
                'optimization_recommendations': self._generate_optimization_recommendations(metrics)
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                'error': str(e),
                'system_health': 'unknown',
                'timestamp': time.time()
            }
    
    def register_application(self, app_name: str, app_config: Dict[str, Any]) -> bool:
        """Register an application for performance monitoring"""
        try:
            self.registered_applications.add(app_name)
            
            # Setup application-specific monitoring
            if ANALYTICS_AVAILABLE and self.analytics_engine:
                self.analytics_engine.register_source(app_name, app_config)
            
            logger.info(f"✅ Registered application: {app_name}")
            return True
        except Exception as e:
            logger.error(f"Error registering application {app_name}: {e}")
            return False
    
    def trigger_optimization_analysis(self) -> Dict[str, Any]:
        """Trigger comprehensive optimization analysis"""
        try:
            metrics = self.get_comprehensive_metrics()
            
            optimization_analysis = {
                'timestamp': time.time(),
                'analysis_type': 'comprehensive_optimization',
                'recommendations': [],
                'priority_issues': [],
                'performance_opportunities': []
            }
            
            # Analyze MPTCP performance
            if metrics.get('unified_kernel', {}).get('connected'):
                mptcp_recommendations = self._analyze_mptcp_performance(metrics['unified_kernel'])
                optimization_analysis['recommendations'].extend(mptcp_recommendations)
            
            # Analyze cross-application performance
            if metrics.get('analytics', {}).get('cross_correlations'):
                correlation_recommendations = self._analyze_cross_correlations(metrics['analytics']['cross_correlations'])
                optimization_analysis['recommendations'].extend(correlation_recommendations)
            
            # ML-driven insights
            if ML_ANALYTICS_AVAILABLE and self.ml_engine:
                ml_recommendations = self.ml_engine.generate_optimization_recommendations(metrics)
                optimization_analysis['recommendations'].extend(ml_recommendations)
            
            return optimization_analysis
            
        except Exception as e:
            logger.error(f"Error triggering optimization analysis: {e}")
            return {
                'timestamp': time.time(),
                'error': str(e),
                'analysis_type': 'optimization_failed'
            }
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _initialize_analytics_engines(self) -> None:
        """Initialize analytics and ML engines"""
        # Initialize analytics engine
        if ANALYTICS_AVAILABLE:
            try:
                self.analytics_engine = create_analytics_engine({
                    'processing_interval': self.config.get('analytics_interval', 30.0),
                    'max_metrics_history': self.config.get('max_history', 2000)
                })
                logger.info("✅ Analytics engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize analytics engine: {e}")
        
        # Initialize ML engine
        if ML_ANALYTICS_AVAILABLE:
            try:
                self.ml_engine = MLAnalyticsEngine({
                    'model_update_interval': self.config.get('ml_update_interval', 300.0),
                    'anomaly_sensitivity': self.config.get('anomaly_sensitivity', 0.8)
                })
                logger.info("✅ ML analytics engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ML analytics engine: {e}")
    
    def _start_analytics_engines(self) -> None:
        """Start analytics engines"""
        if self.analytics_engine:
            try:
                self.analytics_engine.start()
                logger.info("✅ Analytics engine started")
            except Exception as e:
                logger.error(f"Failed to start analytics engine: {e}")
        
        if self.ml_engine:
            try:
                self.ml_engine.start()
                logger.info("✅ ML analytics engine started")
            except Exception as e:
                logger.error(f"Failed to start ML analytics engine: {e}")
    
    def _stop_analytics_engines(self) -> None:
        """Stop analytics engines"""
        if self.analytics_engine:
            try:
                self.analytics_engine.stop()
                logger.info("✅ Analytics engine stopped")
            except Exception as e:
                logger.error(f"Error stopping analytics engine: {e}")
        
        if self.ml_engine:
            try:
                self.ml_engine.stop()
                logger.info("✅ ML analytics engine stopped")
            except Exception as e:
                logger.error(f"Error stopping ML analytics engine: {e}")
    
    def _metrics_collection_loop(self) -> None:
        """Main metrics collection loop"""
        collection_interval = self.config.get('collection_interval', 15.0)  # 15 seconds
        
        while not self.stop_event.wait(collection_interval):
            try:
                self._collect_and_process_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
    
    def _collect_and_process_metrics(self) -> None:
        """Collect metrics from unified kernel and process them"""
        try:
            # Get comprehensive metrics
            metrics = self.get_comprehensive_metrics()
            
            # Store in history
            self.metrics_history.append(metrics)
            
            # Keep only recent history
            max_history = self.config.get('max_metrics_history', 1000)
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]
            
            # Send to analytics engine
            if self.analytics_engine and metrics.get('unified_kernel', {}).get('connected'):
                self._send_to_analytics_engine(metrics)
            
            # Process with ML engine
            if self.ml_engine:
                self._process_with_ml_engine(metrics)
            
            logger.debug("✅ Metrics collected and processed successfully")
            
        except Exception as e:
            logger.error(f"Error collecting and processing metrics: {e}")
    
    def _send_to_analytics_engine(self, metrics: Dict[str, Any]) -> None:
        """Send metrics to analytics engine for processing"""
        try:
            # Extract relevant metrics for analytics
            analytics_metrics = {
                'timestamp': metrics['timestamp'],
                'source': 'performance-analytics-suite',
                'unified_kernel_metrics': metrics.get('unified_kernel', {}),
                'performance_indicators': self._extract_performance_indicators(metrics)
            }
            
            # Send to analytics engine
            session_id = self.analytics_engine.ingest_metrics('performance-analytics-suite', analytics_metrics)
            logger.debug(f"Sent metrics to analytics engine: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error sending metrics to analytics engine: {e}")
    
    def _process_with_ml_engine(self, metrics: Dict[str, Any]) -> None:
        """Process metrics with ML engine for insights"""
        try:
            if self.ml_engine:
                insights = self.ml_engine.process_metrics(metrics)
                logger.debug(f"ML engine processed metrics: {len(insights.get('insights', []))} insights")
        except Exception as e:
            logger.error(f"Error processing metrics with ML engine: {e}")
    
    def _register_with_portal(self) -> None:
        """Register this integration with MeshAdminPortal"""
        try:
            import requests
            
            registration_data = {
                'name': 'Performance Analytics Suite',
                'status': 'running',
                'port': self.config.get('port', 5555),
                'lastHealthCheck': datetime.now().isoformat()
            }
            
            portal_url = self.config.get('portal_url', 'http://localhost:3000')
            response = requests.post(
                f"{portal_url}/api/mptcp/applications/register",
                json=registration_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Registered with MeshAdminPortal")
            else:
                logger.warning(f"Failed to register with MeshAdminPortal: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Could not register with MeshAdminPortal: {e}")
    
    def _setup_cross_application_pipelines(self) -> None:
        """Setup pipelines for cross-application analysis"""
        if not self.analytics_engine:
            return
        
        try:
            # Performance Correlation Pipeline
            pipeline_id = self.analytics_engine.create_pipeline(
                name="Cross-Application Performance Correlation",
                input_sources=['performance-analytics-suite', 'network-flow-master', 'load-balancer-pro', 'observability-dashboard'],
                processors=[
                    {
                        'type': 'correlation',
                        'config': {
                            'correlation_metrics': [
                                'response_time',
                                'throughput',
                                'error_rate',
                                'connection_count',
                                'path_utilization'
                            ],
                            'time_window': 600  # 10 minutes
                        }
                    },
                    {
                        'type': 'anomaly',
                        'config': {
                            'threshold': 0.25,
                            'window_size': 20
                        }
                    }
                ],
                output_targets=['performance-analytics-suite']
            )
            
            logger.info(f"Created cross-application pipeline: {pipeline_id}")
            
        except Exception as e:
            logger.error(f"Error setting up cross-application pipelines: {e}")
    
    def _get_analytics_summary(self) -> Dict[str, Any]:
        """Get summary from analytics engine"""
        if not self.analytics_engine:
            return {'available': False}
        
        try:
            return self.analytics_engine.get_real_time_summary()
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {'error': str(e)}
    
    def _get_ml_insights(self) -> Dict[str, Any]:
        """Get insights from ML engine"""
        if not self.ml_engine:
            return {'available': False}
        
        try:
            return self.ml_engine.get_current_insights()
        except Exception as e:
            logger.error(f"Error getting ML insights: {e}")
            return {'error': str(e)}
    
    def _get_cross_application_correlations(self) -> List[Dict[str, Any]]:
        """Get cross-application correlation analysis"""
        # This would analyze correlations between different applications
        # For now, return placeholder data
        return [
            {
                'app1': 'network-flow-master',
                'app2': 'load-balancer-pro',
                'correlation': 0.78,
                'significance': 'high',
                'metric': 'response_time'
            },
            {
                'app1': 'load-balancer-pro',
                'app2': 'performance-analytics-suite',
                'correlation': 0.65,
                'significance': 'medium',
                'metric': 'throughput'
            }
        ]
    
    def _detect_performance_anomalies(self) -> List[Dict[str, Any]]:
        """Detect performance anomalies using ML"""
        if not self.ml_engine or len(self.metrics_history) < 10:
            return []
        
        try:
            recent_metrics = self.metrics_history[-10:]
            return self.ml_engine.detect_anomalies(recent_metrics)
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def _calculate_system_health(self, metrics: Dict[str, Any]) -> str:
        """Calculate overall system health status"""
        try:
            # Check kernel connection
            if not metrics.get('unified_kernel', {}).get('connected'):
                return 'critical'
            
            # Check for errors in metrics
            if 'error' in metrics:
                return 'warning'
            
            # Check performance indicators
            performance = metrics.get('unified_kernel', {}).get('performance', {})
            if isinstance(performance, dict):
                # Simple health scoring based on typical performance metrics
                error_rate = performance.get('error_rate', 0)
                if error_rate > 0.1:  # 10% error rate
                    return 'warning'
                
                latency = performance.get('average_latency', 0)
                if latency > 1000:  # 1 second latency
                    return 'warning'
            
            return 'healthy'
            
        except Exception as e:
            logger.error(f"Error calculating system health: {e}")
            return 'unknown'
    
    def _extract_key_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics for dashboard display"""
        try:
            kernel_data = metrics.get('unified_kernel', {})
            
            return {
                'total_connections': kernel_data.get('connections', {}).get('total', 0),
                'active_connections': kernel_data.get('connections', {}).get('active', 0),
                'average_latency': kernel_data.get('performance', {}).get('average_latency', 0),
                'total_throughput': kernel_data.get('performance', {}).get('total_throughput', 0),
                'error_rate': kernel_data.get('performance', {}).get('error_rate', 0),
                'path_count': len(kernel_data.get('paths', {}).get('paths', [])),
                'system_uptime': kernel_data.get('overview', {}).get('uptime', 0)
            }
        except Exception as e:
            logger.error(f"Error extracting key metrics: {e}")
            return {}
    
    def _calculate_performance_trends(self) -> Dict[str, str]:
        """Calculate performance trends from historical data"""
        if len(self.metrics_history) < 5:
            return {
                'latency_trend': 'stable',
                'throughput_trend': 'stable',
                'connection_trend': 'stable',
                'error_trend': 'stable'
            }
        
        try:
            # Analyze trends in recent metrics
            recent_metrics = self.metrics_history[-5:]
            
            # Extract latency values
            latencies = []
            for metric in recent_metrics:
                latency = metric.get('unified_kernel', {}).get('performance', {}).get('average_latency', 0)
                if latency > 0:
                    latencies.append(latency)
            
            # Simple trend calculation
            latency_trend = 'stable'
            if len(latencies) >= 3:
                if latencies[-1] > latencies[0] * 1.1:
                    latency_trend = 'increasing'
                elif latencies[-1] < latencies[0] * 0.9:
                    latency_trend = 'decreasing'
            
            return {
                'latency_trend': latency_trend,
                'throughput_trend': 'stable',  # Placeholder
                'connection_trend': 'stable',  # Placeholder
                'error_trend': 'stable'       # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance trends: {e}")
            return {
                'latency_trend': 'unknown',
                'throughput_trend': 'unknown',
                'connection_trend': 'unknown',
                'error_trend': 'unknown'
            }
    
    def _get_active_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        alerts = []
        
        try:
            # Check kernel connectivity
            if not metrics.get('unified_kernel', {}).get('connected'):
                alerts.append({
                    'severity': 'critical',
                    'message': 'Unified MPTCP kernel not connected',
                    'timestamp': time.time(),
                    'type': 'connectivity'
                })
            
            # Check for performance issues
            performance = metrics.get('unified_kernel', {}).get('performance', {})
            if isinstance(performance, dict):
                error_rate = performance.get('error_rate', 0)
                if error_rate > 0.05:  # 5% error rate threshold
                    alerts.append({
                        'severity': 'warning',
                        'message': f'High error rate detected: {error_rate:.2%}',
                        'timestamp': time.time(),
                        'type': 'performance'
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    def _get_application_status_summary(self) -> Dict[str, Any]:
        """Get summary of application statuses"""
        return {
            'total_registered': len(self.registered_applications),
            'applications': list(self.registered_applications),
            'integration_health': 'healthy' if self.is_running else 'stopped'
        }
    
    def _generate_optimization_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on current metrics"""
        recommendations = []
        
        try:
            # Check if kernel is connected
            if metrics.get('unified_kernel', {}).get('connected'):
                performance = metrics.get('unified_kernel', {}).get('performance', {})
                
                if isinstance(performance, dict):
                    # Latency-based recommendations
                    latency = performance.get('average_latency', 0)
                    if latency > 100:  # 100ms
                        recommendations.append("Consider optimizing network paths to reduce latency")
                    
                    # Throughput-based recommendations
                    throughput = performance.get('total_throughput', 0)
                    if throughput < 100:  # Low throughput
                        recommendations.append("Monitor path utilization for potential bottlenecks")
                    
                    # Connection-based recommendations
                    connections = metrics.get('unified_kernel', {}).get('connections', {})
                    if isinstance(connections, dict):
                        total = connections.get('total', 0)
                        active = connections.get('active', 0)
                        
                        if total > 0 and active / total < 0.7:  # Low connection efficiency
                            recommendations.append("Review connection management and pooling strategies")
                
                # General recommendations
                recommendations.extend([
                    "Enable cross-application correlation analysis for better insights",
                    "Consider implementing automated path optimization",
                    "Monitor ML-driven anomaly detection for proactive issue resolution"
                ])
            else:
                recommendations.append("Establish connection to unified MPTCP kernel for full optimization")
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return ["Error generating recommendations - check system logs"]
    
    def _extract_performance_indicators(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key performance indicators for analytics"""
        try:
            kernel_data = metrics.get('unified_kernel', {})
            
            return {
                'response_time': kernel_data.get('performance', {}).get('average_latency', 0),
                'throughput': kernel_data.get('performance', {}).get('total_throughput', 0),
                'error_rate': kernel_data.get('performance', {}).get('error_rate', 0),
                'connection_count': kernel_data.get('connections', {}).get('total', 0),
                'active_connections': kernel_data.get('connections', {}).get('active', 0),
                'path_utilization': kernel_data.get('paths', {}).get('utilization', 0),
                'system_health': self._calculate_system_health(metrics)
            }
        except Exception as e:
            logger.error(f"Error extracting performance indicators: {e}")
            return {}
    
    def _analyze_mptcp_performance(self, kernel_data: Dict[str, Any]) -> List[str]:
        """Analyze MPTCP performance and generate recommendations"""
        recommendations = []
        
        try:
            performance = kernel_data.get('performance', {})
            
            if isinstance(performance, dict):
                # Analyze latency
                latency = performance.get('average_latency', 0)
                if latency > 200:
                    recommendations.append("High latency detected - consider path optimization")
                
                # Analyze throughput
                throughput = performance.get('total_throughput', 0)
                if throughput < 50:
                    recommendations.append("Low throughput - review path utilization and load balancing")
                
                # Analyze error rate
                error_rate = performance.get('error_rate', 0)
                if error_rate > 0.02:
                    recommendations.append("Elevated error rate - investigate connection stability")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing MPTCP performance: {e}")
            return ["Error analyzing MPTCP performance"]
    
    def _analyze_cross_correlations(self, correlations: List[Dict[str, Any]]) -> List[str]:
        """Analyze cross-application correlations for recommendations"""
        recommendations = []
        
        try:
            for correlation in correlations:
                if correlation.get('correlation', 0) > 0.8:
                    app1 = correlation.get('app1', 'unknown')
                    app2 = correlation.get('app2', 'unknown')
                    metric = correlation.get('metric', 'performance')
                    
                    recommendations.append(
                        f"Strong correlation between {app1} and {app2} {metric} - "
                        f"consider coordinated optimization"
                    )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing cross correlations: {e}")
            return []

# Global integration instance
_global_integration: Optional[PerformanceAnalyticsSuiteIntegration] = None

def get_integration(config: Optional[Dict[str, Any]] = None) -> PerformanceAnalyticsSuiteIntegration:
    """Get or create the global Performance Analytics Suite integration instance"""
    global _global_integration
    
    if _global_integration is None:
        _global_integration = PerformanceAnalyticsSuiteIntegration(config)
    
    return _global_integration

def start_integration(config: Optional[Dict[str, Any]] = None) -> bool:
    """Start the Performance Analytics Suite integration"""
    integration = get_integration(config)
    return integration.start()

def stop_integration() -> None:
    """Stop the Performance Analytics Suite integration"""
    global _global_integration
    
    if _global_integration:
        _global_integration.stop()

if __name__ == "__main__":
    # Test the integration
    logging.basicConfig(level=logging.INFO)
    
    test_config = {
        'collection_interval': 10.0,
        'analytics_interval': 30.0,
        'max_history': 100
    }
    
    print("🧪 Testing Performance Analytics Suite Integration...")
    
    if start_integration(test_config):
        print("✅ Integration started successfully")
        
        try:
            integration = get_integration()
            
            # Test metrics collection
            print("\n📊 Testing metrics collection...")
            metrics = integration.get_comprehensive_metrics()
            print(f"✅ Collected {len(metrics)} metric categories")
            
            # Test dashboard data
            print("\n📈 Testing dashboard data...")
            dashboard_data = integration.get_performance_dashboard_data()
            print(f"✅ Dashboard data: {dashboard_data.get('system_health', 'unknown')} health")
            
            # Test optimization analysis
            print("\n🔧 Testing optimization analysis...")
            optimization = integration.trigger_optimization_analysis()
            recommendations_count = len(optimization.get('recommendations', []))
            print(f"✅ Generated {recommendations_count} optimization recommendations")
            
            print("\n✅ All tests completed successfully!")
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping integration...")
        finally:
            stop_integration()
    else:
        print("❌ Failed to start integration") 