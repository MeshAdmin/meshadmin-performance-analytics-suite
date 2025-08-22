#!/usr/bin/env python3
"""
MeshAdmin Performance Analytics Dashboard

This module provides the base Performance Analytics Dashboard for monitoring
Network Flow Master and Load Balancer Pro applications in the MeshAdmin suite.

Features:
- Real-time performance monitoring
- Application status tracking  
- Data correlation and analysis
- Interactive visualization
- Alert system
- Web-based dashboard interface
"""

import sys
import os
import time
import json
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor

# Standard libraries for data handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots
    import plotly.utils
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("performance-dashboard")

# =============================================================================
# Application Integration Classes
# =============================================================================

@dataclass
class ApplicationMetrics:
    """Container for application performance metrics"""
    timestamp: float
    app_id: str
    status: str
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_io: float = 0.0
    custom_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}

class ApplicationIntegration:
    """Base class for integrating with MeshAdmin applications"""
    
    def __init__(self, app_id: str, app_path: str = None):
        self.app_id = app_id
        self.app_path = app_path
        self.is_running = False
        self.last_metrics = None
        self.metrics_history = []
        self.max_history = 1000
        
    def start_monitoring(self) -> None:
        """Start monitoring this application"""
        self.is_running = True
        logger.info(f"Started monitoring {self.app_id}")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring this application"""
        self.is_running = False
        logger.info(f"Stopped monitoring {self.app_id}")
    
    def get_current_metrics(self) -> ApplicationMetrics:
        """Get current metrics for this application"""
        current_time = time.time()
        
        # Get basic system metrics
        cpu_usage = 0.0
        memory_usage = 0.0
        network_io = 0.0
        
        if PSUTIL_AVAILABLE:
            try:
                # Try to find the application process
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                    if self.app_id.lower() in proc.info['name'].lower():
                        cpu_usage = proc.info['cpu_percent'] or 0.0
                        memory_info = proc.info['memory_info']
                        if memory_info:
                            memory_usage = memory_info.rss / 1024 / 1024  # MB
                        break
            except Exception as e:
                logger.debug(f"Error getting system metrics for {self.app_id}: {e}")
        
        # Create metrics object
        metrics = ApplicationMetrics(
            timestamp=current_time,
            app_id=self.app_id,
            status='running' if self.is_running else 'stopped',
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            network_io=network_io,
            custom_metrics=self._get_custom_metrics()
        )
        
        # Store in history
        self.last_metrics = metrics
        self.metrics_history.append(metrics)
        
        # Trim history if needed
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        return metrics
    
    def _get_custom_metrics(self) -> Dict[str, Any]:
        """Override this method to provide application-specific metrics"""
        return {}
    
    def get_metrics_history(self, hours: float = 1.0) -> List[ApplicationMetrics]:
        """Get metrics history for the specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

class NetworkFlowMasterIntegration(ApplicationIntegration):
    """Integration for Network Flow Master application"""
    
    def __init__(self):
        super().__init__("network_flow_master", "apps/network-flow-master")
    
    def _get_custom_metrics(self) -> Dict[str, Any]:
        """Get Network Flow Master specific metrics"""
        try:
            # Simulate Network Flow Master metrics
            # In real implementation, this would query the actual application
            return {
                'total_flows': 1200 + int(time.time() % 300),  # Simulated varying flow count
                'packet_rate': 2000.0 + (time.time() % 100) * 10,  # Simulated packet rate
                'active_connections': 150 + int(time.time() % 50),
                'bandwidth_utilization': min(0.95, 0.3 + (time.time() % 100) / 200),
                'flow_classification_accuracy': 0.95 + (time.time() % 10) / 200
            }
        except Exception as e:
            logger.error(f"Error getting Network Flow Master metrics: {e}")
            return {}

class LoadBalancerProIntegration(ApplicationIntegration):
    """Integration for Load Balancer Pro application"""
    
    def __init__(self):
        super().__init__("load_balancer_pro", "apps/load-balancer-pro")
    
    def _get_custom_metrics(self) -> Dict[str, Any]:
        """Get Load Balancer Pro specific metrics"""
        try:
            # Simulate Load Balancer Pro metrics
            # In real implementation, this would query the actual application
            base_response_time = 120.0
            time_factor = (time.time() % 300) / 300  # 5-minute cycle
            
            return {
                'total_connections': 200 + int(time.time() % 100),
                'active_backends': 4,
                'response_time': base_response_time + time_factor * 30,  # 120-150ms range
                'error_rate': max(0.0, 0.02 + (time.time() % 100 - 50) / 10000),  # 0-4% range
                'health_score': min(1.0, 0.85 + (100 - time.time() % 100) / 200),  # 0.85-1.0 range
                'backend_distribution': {
                    'backend_1': 0.25,
                    'backend_2': 0.25, 
                    'backend_3': 0.25,
                    'backend_4': 0.25
                }
            }
        except Exception as e:
            logger.error(f"Error getting Load Balancer Pro metrics: {e}")
            return {}

# =============================================================================
# Performance Analytics Dashboard
# =============================================================================

class PerformanceAnalyticsDashboard:
    """
    Main Performance Analytics Dashboard for MeshAdmin applications
    
    Provides real-time monitoring, correlation analysis, and visualization
    for Network Flow Master and Load Balancer Pro.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_running = False
        self.update_thread = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Configuration
        self.update_interval = self.config.get('update_interval', 30)  # seconds
        self.buffer_size = self.config.get('buffer_size', 1000)
        self.correlation_window = self.config.get('correlation_window', 300)  # 5 minutes
        
        # Application integrations
        self.applications = {
            'network_flow_master': NetworkFlowMasterIntegration(),
            'load_balancer_pro': LoadBalancerProIntegration()
        }
        
        # Data storage
        self.current_metrics = {}
        self.performance_summary = {}
        self.correlation_data = {}
        self.alerts = []
        
        logger.info("📊 Performance Analytics Dashboard initialized")
    
    def start(self) -> None:
        """Start the dashboard monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start application monitoring
        for app in self.applications.values():
            app.start_monitoring()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info("✅ Performance Analytics Dashboard started")
    
    def stop(self) -> None:
        """Stop the dashboard monitoring"""
        self.is_running = False
        
        # Stop application monitoring
        for app in self.applications.values():
            app.stop_monitoring()
        
        self.executor.shutdown(wait=True)
        logger.info("🛑 Performance Analytics Dashboard stopped")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics from all monitored applications"""
        return {
            'timestamp': time.time(),
            'current_metrics': self.current_metrics,
            'performance_summary': self.performance_summary,
            'correlation_data': self.correlation_data,
            'alerts': self.alerts,
            'applications': list(self.applications.keys())
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all applications"""
        return self.performance_summary
    
    def get_correlation_analysis(self) -> Dict[str, Any]:
        """Get correlation analysis between applications"""
        return self.correlation_data
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts"""
        return self.alerts
    
    def generate_report(self, hours: float = 24.0) -> Dict[str, Any]:
        """Generate a performance report for the specified time period"""
        report = {
            'timestamp': time.time(),
            'period_hours': hours,
            'applications': {},
            'summary': {},
            'recommendations': []
        }
        
        # Collect data for each application
        for app_id, app in self.applications.items():
            history = app.get_metrics_history(hours)
            if history:
                app_report = self._analyze_application_performance(app_id, history)
                report['applications'][app_id] = app_report
        
        # Generate overall summary
        report['summary'] = self._generate_summary_analysis(report['applications'])
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _update_loop(self) -> None:
        """Main update loop for dashboard metrics"""
        logger.info("🔄 Starting dashboard update loop")
        
        while self.is_running:
            try:
                self._update_metrics()
                self._update_performance_summary()
                self._update_correlation_analysis()
                self._check_alerts()
                
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(5)  # Short delay on error
    
    def _update_metrics(self) -> None:
        """Update current metrics from all applications"""
        for app_id, app in self.applications.items():
            try:
                metrics = app.get_current_metrics()
                self.current_metrics[app_id] = {
                    'timestamp': metrics.timestamp,
                    'status': metrics.status,
                    'data': asdict(metrics)
                }
            except Exception as e:
                logger.error(f"Error updating metrics for {app_id}: {e}")
    
    def _update_performance_summary(self) -> None:
        """Update performance summary"""
        try:
            summary = {
                'total_applications': len(self.applications),
                'running_applications': sum(1 for m in self.current_metrics.values() if m.get('status') == 'running'),
                'last_updated': time.time()
            }
            
            # Network Flow Master summary
            nfm_metrics = self.current_metrics.get('network_flow_master', {}).get('data', {})
            if nfm_metrics and nfm_metrics.get('custom_metrics'):
                nfm_custom = nfm_metrics['custom_metrics']
                summary.update({
                    'total_network_flows': nfm_custom.get('total_flows', 0),
                    'packet_rate': nfm_custom.get('packet_rate', 0.0),
                    'bandwidth_utilization': nfm_custom.get('bandwidth_utilization', 0.0)
                })
            
            # Load Balancer Pro summary
            lbp_metrics = self.current_metrics.get('load_balancer_pro', {}).get('data', {})
            if lbp_metrics and lbp_metrics.get('custom_metrics'):
                lbp_custom = lbp_metrics['custom_metrics']
                summary.update({
                    'total_lb_connections': lbp_custom.get('total_connections', 0),
                    'average_response_time': lbp_custom.get('response_time', 0.0),
                    'error_rate': lbp_custom.get('error_rate', 0.0),
                    'health_score': lbp_custom.get('health_score', 0.0)
                })
            
            self.performance_summary = summary
            
        except Exception as e:
            logger.error(f"Error updating performance summary: {e}")
    
    def _update_correlation_analysis(self) -> None:
        """Update correlation analysis between applications"""
        try:
            if len(self.current_metrics) < 2:
                return
            
            # Simple correlation analysis
            correlation = {
                'timestamp': time.time(),
                'relationships': []
            }
            
            # Analyze relationship between network flows and load balancer connections
            nfm_data = self.current_metrics.get('network_flow_master', {}).get('data', {})
            lbp_data = self.current_metrics.get('load_balancer_pro', {}).get('data', {})
            
            if nfm_data and lbp_data:
                nfm_custom = nfm_data.get('custom_metrics', {})
                lbp_custom = lbp_data.get('custom_metrics', {})
                
                # Calculate simple correlation metrics
                flow_count = nfm_custom.get('total_flows', 0)
                connection_count = lbp_custom.get('total_connections', 0)
                
                if flow_count > 0 and connection_count > 0:
                    ratio = connection_count / flow_count
                    correlation['relationships'].append({
                        'type': 'flow_to_connection_ratio',
                        'value': ratio,
                        'description': f'Load balancer handles {ratio:.2f} connections per network flow'
                    })
                
                # Response time vs packet rate correlation
                response_time = lbp_custom.get('response_time', 0)
                packet_rate = nfm_custom.get('packet_rate', 0)
                
                if response_time > 0 and packet_rate > 0:
                    correlation['relationships'].append({
                        'type': 'response_time_packet_rate',
                        'response_time': response_time,
                        'packet_rate': packet_rate,
                        'description': f'Response time: {response_time:.1f}ms at {packet_rate:.0f} pps'
                    })
            
            self.correlation_data = correlation
            
        except Exception as e:
            logger.error(f"Error updating correlation analysis: {e}")
    
    def _check_alerts(self) -> None:
        """Check for alert conditions"""
        try:
            alerts = []
            current_time = time.time()
            
            # Check Load Balancer Pro alerts
            lbp_data = self.current_metrics.get('load_balancer_pro', {}).get('data', {})
            if lbp_data and lbp_data.get('custom_metrics'):
                lbp_custom = lbp_data['custom_metrics']
                
                # High response time alert
                response_time = lbp_custom.get('response_time', 0)
                if response_time > 150:  # 150ms threshold
                    alerts.append({
                        'timestamp': current_time,
                        'severity': 'warning' if response_time < 200 else 'critical',
                        'source': 'load_balancer_pro',
                        'type': 'response_time',
                        'message': f'High response time: {response_time:.1f}ms',
                        'value': response_time,
                        'threshold': 150
                    })
                
                # High error rate alert
                error_rate = lbp_custom.get('error_rate', 0)
                if error_rate > 0.05:  # 5% threshold
                    alerts.append({
                        'timestamp': current_time,
                        'severity': 'warning' if error_rate < 0.1 else 'critical',
                        'source': 'load_balancer_pro',
                        'type': 'error_rate',
                        'message': f'High error rate: {error_rate*100:.1f}%',
                        'value': error_rate,
                        'threshold': 0.05
                    })
                
                # Low health score alert
                health_score = lbp_custom.get('health_score', 1.0)
                if health_score < 0.9:  # 90% threshold
                    alerts.append({
                        'timestamp': current_time,
                        'severity': 'warning' if health_score > 0.8 else 'critical',
                        'source': 'load_balancer_pro',
                        'type': 'health_score',
                        'message': f'Low health score: {health_score*100:.1f}%',
                        'value': health_score,
                        'threshold': 0.9
                    })
            
            # Check Network Flow Master alerts
            nfm_data = self.current_metrics.get('network_flow_master', {}).get('data', {})
            if nfm_data and nfm_data.get('custom_metrics'):
                nfm_custom = nfm_data['custom_metrics']
                
                # High bandwidth utilization alert
                bandwidth_util = nfm_custom.get('bandwidth_utilization', 0)
                if bandwidth_util > 0.8:  # 80% threshold
                    alerts.append({
                        'timestamp': current_time,
                        'severity': 'warning' if bandwidth_util < 0.9 else 'critical',
                        'source': 'network_flow_master',
                        'type': 'bandwidth_utilization',
                        'message': f'High bandwidth utilization: {bandwidth_util*100:.1f}%',
                        'value': bandwidth_util,
                        'threshold': 0.8
                    })
            
            # Filter out old alerts and add new ones
            cutoff_time = current_time - 3600  # Keep alerts for 1 hour
            old_alerts = [a for a in self.alerts if a['timestamp'] >= cutoff_time]
            self.alerts = old_alerts + alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _analyze_application_performance(self, app_id: str, history: List[ApplicationMetrics]) -> Dict[str, Any]:
        """Analyze performance for a specific application"""
        if not history:
            return {}
        
        analysis = {
            'app_id': app_id,
            'period_start': history[0].timestamp,
            'period_end': history[-1].timestamp,
            'total_samples': len(history),
            'metrics': {}
        }
        
        # Analyze different metrics
        if history[0].custom_metrics:
            for metric_name in history[0].custom_metrics.keys():
                values = [getattr(m.custom_metrics, metric_name, 0) for m in history if hasattr(m.custom_metrics, metric_name)]
                if values:
                    analysis['metrics'][metric_name] = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'latest': values[-1]
                    }
        
        return analysis
    
    def _generate_summary_analysis(self, app_reports: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall summary analysis"""
        summary = {
            'total_applications': len(app_reports),
            'analysis_timestamp': time.time(),
            'overall_health': 'good',  # Default
            'key_insights': []
        }
        
        # Analyze trends and generate insights
        for app_id, report in app_reports.items():
            metrics = report.get('metrics', {})
            
            # Check for concerning trends
            if app_id == 'load_balancer_pro':
                response_time = metrics.get('response_time', {})
                if response_time and response_time.get('avg', 0) > 150:
                    summary['key_insights'].append(f"Load Balancer response time averaging {response_time['avg']:.1f}ms")
                    if summary['overall_health'] == 'good':
                        summary['overall_health'] = 'warning'
        
        return summary
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Analyze load balancer performance
        lbp_report = report['applications'].get('load_balancer_pro', {})
        if lbp_report:
            metrics = lbp_report.get('metrics', {})
            
            # Response time recommendations
            response_time = metrics.get('response_time', {})
            if response_time and response_time.get('avg', 0) > 150:
                recommendations.append({
                    'category': 'performance',
                    'priority': 'high' if response_time['avg'] > 200 else 'medium',
                    'title': 'Optimize Load Balancer Response Time',
                    'description': f"Average response time is {response_time['avg']:.1f}ms. Consider optimizing backend performance or adding more servers.",
                    'metrics': response_time
                })
            
            # Error rate recommendations
            error_rate = metrics.get('error_rate', {})
            if error_rate and error_rate.get('avg', 0) > 0.05:
                recommendations.append({
                    'category': 'reliability',
                    'priority': 'high',
                    'title': 'Reduce Error Rate',
                    'description': f"Error rate is {error_rate['avg']*100:.1f}%. Investigate backend health and connection issues.",
                    'metrics': error_rate
                })
        
        return recommendations

# =============================================================================
# Factory Functions
# =============================================================================

def create_analytics_dashboard(config: Dict[str, Any] = None) -> PerformanceAnalyticsDashboard:
    """Factory function to create a Performance Analytics Dashboard"""
    return PerformanceAnalyticsDashboard(config)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point for testing the dashboard"""
    print("📊 MeshAdmin Performance Analytics Dashboard")
    print("=" * 50)
    
    # Create and start dashboard
    dashboard = create_analytics_dashboard({
        'update_interval': 10,  # 10 seconds for testing
        'buffer_size': 100
    })
    
    dashboard.start()
    
    try:
        # Monitor for a short period
        for i in range(6):  # 1 minute of monitoring
            time.sleep(10)
            
            # Get current metrics
            current_data = dashboard.get_current_metrics()
            print(f"\n📊 Update {i+1}:")
            print(f"  Running applications: {current_data['performance_summary'].get('running_applications', 0)}")
            
            # Show performance summary
            summary = current_data['performance_summary']
            if 'total_network_flows' in summary:
                print(f"  Network flows: {summary['total_network_flows']}")
            if 'total_lb_connections' in summary:
                print(f"  LB connections: {summary['total_lb_connections']}")
                print(f"  Response time: {summary.get('average_response_time', 0):.1f}ms")
            
            # Show alerts
            alerts = current_data.get('alerts', [])
            if alerts:
                recent_alerts = [a for a in alerts if time.time() - a['timestamp'] < 60]
                if recent_alerts:
                    print(f"  🚨 Recent alerts: {len(recent_alerts)}")
        
        # Generate final report
        print("\n📋 Generating performance report...")
        report = dashboard.generate_report(hours=1.0)
        
        print(f"Report Summary:")
        print(f"  Applications analyzed: {len(report['applications'])}")
        print(f"  Overall health: {report['summary'].get('overall_health', 'unknown')}")
        print(f"  Recommendations: {len(report['recommendations'])}")
        
        if report['recommendations']:
            print("\n💡 Top Recommendations:")
            for rec in report['recommendations'][:3]:
                print(f"  - {rec['title']} ({rec['priority']} priority)")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping dashboard...")
    
    finally:
        dashboard.stop()
        print("✅ Dashboard stopped")

if __name__ == "__main__":
    main()

