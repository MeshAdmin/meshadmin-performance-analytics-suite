#!/usr/bin/env python3
"""
Advanced Analytics Dashboard Integration

This module integrates the ML Analytics Engine with the Performance Dashboard,
providing real-time intelligent insights, predictive analytics, and automated
recommendations.

Features:
- Real-time anomaly detection integration
- Performance prediction dashboard widgets
- Capacity planning recommendations
- ML-powered alerts and insights
- Predictive charts and visualizations
"""

import sys
import os
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

try:
    from ml_analytics_engine import (
        MLAnalyticsEngine, 
        PerformanceMetric, 
        create_ml_analytics_engine,
        ML_AVAILABLE
    )
    ML_ENGINE_AVAILABLE = True
except ImportError:
    print("⚠️ ML Analytics Engine not available")
    ML_ENGINE_AVAILABLE = False

try:
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots
    import plotly.utils
    PLOTLY_AVAILABLE = True
except ImportError:
    print("⚠️ Plotly not available for chart generation")
    PLOTLY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ml-dashboard-integration")

# =============================================================================
# Advanced Analytics Dashboard Integration
# =============================================================================

class AdvancedAnalyticsDashboard:
    """
    Advanced Analytics Dashboard Integration
    
    Provides ML-powered insights and predictions for the Performance Dashboard
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.ml_engine: Optional[MLAnalyticsEngine] = None
        self.is_running = False
        
        # Configuration
        self.update_interval = self.config.get('update_interval', 30)  # seconds
        self.prediction_horizon = self.config.get('prediction_horizon', 3600)  # 1 hour
        self.anomaly_sensitivity = self.config.get('anomaly_sensitivity', 'medium')
        
        # Initialize ML engine if available
        if ML_ENGINE_AVAILABLE:
            ml_config = {
                'buffer_size': self.config.get('buffer_size', 1000),
                'train_threshold': self.config.get('train_threshold', 100),
                'model_update_interval': self.config.get('model_update_interval', 1800),
                'prediction_horizon': self.prediction_horizon
            }
            self.ml_engine = create_ml_analytics_engine(ml_config)
        
        logger.info("🧠 Advanced Analytics Dashboard Integration initialized")
    
    def start(self) -> None:
        """Start the advanced analytics integration"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Try to load existing models
        if self.ml_engine:
            self.ml_engine.load_models()
        
        logger.info("✅ Advanced Analytics Dashboard Integration started")
    
    def stop(self) -> None:
        """Stop the advanced analytics integration"""
        self.is_running = False
        logger.info("🛑 Advanced Analytics Dashboard Integration stopped")
    
    def process_dashboard_metrics(self, dashboard_data: Dict[str, Any]) -> None:
        """Process metrics from the dashboard and feed to ML engine"""
        if not self.ml_engine or not self.is_running:
            return
        
        try:
            # Extract metrics from dashboard data
            metrics = self._extract_metrics_from_dashboard(dashboard_data)
            
            if metrics:
                # Feed metrics to ML engine
                self.ml_engine.ingest_metrics(metrics)
                logger.debug(f"Processed {len(metrics)} metrics for ML analysis")
        
        except Exception as e:
            logger.error(f"Error processing dashboard metrics: {e}")
    
    def get_ml_insights(self) -> Dict[str, Any]:
        """Get ML-powered insights for the dashboard"""
        if not self.ml_engine:
            return {
                'available': False,
                'message': 'ML Analytics not available'
            }
        
        try:
            # Get analysis summary
            summary = self.ml_engine.get_analysis_summary()
            
            # Get recent anomalies
            anomalies = self.ml_engine.get_recent_anomalies(hours=1.0)
            
            # Get predictions
            predictions = self.ml_engine.get_predictions()
            
            # Get capacity recommendations
            recommendations = self.ml_engine.get_capacity_recommendations()
            
            # Create insights response
            insights = {
                'available': True,
                'timestamp': time.time(),
                'summary': summary,
                'anomalies': {
                    'recent': anomalies,
                    'count': len(anomalies),
                    'critical_count': len([a for a in anomalies if a['severity'] == 'critical'])
                },
                'predictions': {
                    'active': predictions,
                    'count': len(predictions),
                    'next_hour': [p for p in predictions if p['time_to_prediction'] <= 3600]
                },
                'recommendations': {
                    'capacity': recommendations,
                    'urgent': [r for r in recommendations if r['urgency'] in ['high', 'critical']],
                    'count': len(recommendations)
                },
                'ml_status': {
                    'models_trained': summary.get('models_trained', False),
                    'metrics_analyzed': summary.get('metrics_analyzed', 0),
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting ML insights: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def get_predictive_charts(self) -> Dict[str, Any]:
        """Generate predictive charts for the dashboard"""
        if not PLOTLY_AVAILABLE or not self.ml_engine:
            return {}
        
        try:
            charts = {}
            
            # Anomaly Detection Chart
            charts['anomaly_timeline'] = self._create_anomaly_timeline_chart()
            
            # Prediction Charts
            charts['performance_predictions'] = self._create_prediction_chart()
            
            # Capacity Planning Chart
            charts['capacity_forecast'] = self._create_capacity_forecast_chart()
            
            # ML Model Performance Chart
            charts['model_performance'] = self._create_model_performance_chart()
            
            return charts
            
        except Exception as e:
            logger.error(f"Error creating predictive charts: {e}")
            return {'error': str(e)}
    
    def get_intelligent_alerts(self) -> List[Dict[str, Any]]:
        """Get intelligent alerts based on ML analysis"""
        if not self.ml_engine:
            return []
        
        try:
            alerts = []
            
            # Anomaly-based alerts
            anomalies = self.ml_engine.get_recent_anomalies(hours=1.0)
            for anomaly in anomalies:
                if anomaly['severity'] in ['high', 'critical']:
                    alerts.append({
                        'type': 'anomaly',
                        'severity': anomaly['severity'],
                        'title': f"Performance Anomaly Detected",
                        'message': anomaly['description'],
                        'timestamp': anomaly['timestamp'],
                        'confidence': anomaly['confidence'],
                        'source': anomaly['source'],
                        'metric': anomaly['metric_name']
                    })
            
            # Prediction-based alerts
            predictions = self.ml_engine.get_predictions()
            for pred in predictions:
                if pred['time_to_prediction'] <= 1800:  # Next 30 minutes
                    # Check if prediction indicates potential issues
                    if (pred['metric_name'] == 'response_time' and pred['predicted_value'] > 500) or \
                       (pred['metric_name'] == 'error_rate' and pred['predicted_value'] > 0.05):
                        alerts.append({
                            'type': 'prediction',
                            'severity': 'medium',
                            'title': f"Performance Degradation Predicted",
                            'message': f"{pred['metric_name']} predicted to reach {pred['predicted_value']:.2f} in {pred['time_to_prediction']/60:.1f} minutes",
                            'timestamp': time.time(),
                            'confidence': pred['model_accuracy'],
                            'metric': pred['metric_name'],
                            'prediction_time': pred['target_time']
                        })
            
            # Capacity-based alerts
            recommendations = self.ml_engine.get_capacity_recommendations()
            for rec in recommendations:
                if rec['urgency'] in ['high', 'critical']:
                    alerts.append({
                        'type': 'capacity',
                        'severity': rec['urgency'],
                        'title': f"Capacity Warning: {rec['component']}",
                        'message': rec['recommendation'],
                        'timestamp': time.time(),
                        'component': rec['component'],
                        'utilization': rec['current_utilization'],
                        'time_to_limit': rec.get('estimated_time_to_limit')
                    })
            
            # Sort by severity and timestamp
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            alerts.sort(key=lambda x: (severity_order.get(x['severity'], 4), -x['timestamp']))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating intelligent alerts: {e}")
            return []
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get AI-powered optimization suggestions"""
        if not self.ml_engine:
            return []
        
        try:
            suggestions = []
            
            # Get current analysis
            summary = self.ml_engine.get_analysis_summary()
            recommendations = self.ml_engine.get_capacity_recommendations()
            
            # Performance optimization suggestions
            model_perf = summary.get('model_performance', {})
            
            if model_perf.get('response_time_mse', 0) > 1000:
                suggestions.append({
                    'category': 'performance',
                    'priority': 'high',
                    'title': 'Response Time Optimization',
                    'description': 'High response time variance detected. Consider load balancer configuration tuning.',
                    'actions': [
                        'Review backend server performance',
                        'Adjust load balancing algorithm',
                        'Consider adding more backend servers'
                    ]
                })
            
            if model_perf.get('packet_rate_mse', 0) > 100000:
                suggestions.append({
                    'category': 'network',
                    'priority': 'medium',
                    'title': 'Network Traffic Optimization',
                    'description': 'Irregular network traffic patterns detected. Network optimization may be needed.',
                    'actions': [
                        'Analyze network flow patterns',
                        'Optimize routing configurations',
                        'Consider traffic shaping policies'
                    ]
                })
            
            # Capacity optimization suggestions
            for rec in recommendations:
                if rec['urgency'] in ['medium', 'high', 'critical']:
                    suggestions.append({
                        'category': 'capacity',
                        'priority': rec['urgency'],
                        'title': f"Capacity Planning: {rec['component']}",
                        'description': rec['recommendation'],
                        'actions': [
                            'Monitor resource utilization trends',
                            'Plan capacity expansion',
                            'Consider auto-scaling solutions'
                        ],
                        'component': rec['component'],
                        'utilization': rec['current_utilization']
                    })
            
            # Model training suggestions
            if summary.get('metrics_analyzed', 0) > 500 and not summary.get('models_trained', False):
                suggestions.append({
                    'category': 'ml',
                    'priority': 'low',
                    'title': 'ML Model Training',
                    'description': 'Sufficient data available for improved ML model training.',
                    'actions': [
                        'Retrain ML models with latest data',
                        'Tune model hyperparameters',
                        'Evaluate model performance'
                    ]
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            return []
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _extract_metrics_from_dashboard(self, dashboard_data: Dict[str, Any]) -> List[PerformanceMetric]:
        """Extract performance metrics from dashboard data"""
        metrics = []
        timestamp = time.time()
        
        try:
            # Extract from performance summary
            perf_summary = dashboard_data.get('performance_summary', {})
            
            if perf_summary:
                # Network Flow Master metrics
                if 'total_network_flows' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='network_flow_master',
                        metric_name='total_flows',
                        value=float(perf_summary['total_network_flows'])
                    ))
                
                if 'packet_rate' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='network_flow_master',
                        metric_name='packet_rate',
                        value=float(perf_summary['packet_rate'])
                    ))
                
                # Load Balancer Pro metrics
                if 'total_lb_connections' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='load_balancer_pro',
                        metric_name='connection_count',
                        value=float(perf_summary['total_lb_connections'])
                    ))
                
                if 'average_response_time' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='load_balancer_pro',
                        metric_name='response_time',
                        value=float(perf_summary['average_response_time'])
                    ))
                
                if 'error_rate' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='load_balancer_pro',
                        metric_name='error_rate',
                        value=float(perf_summary['error_rate'])
                    ))
                
                if 'health_score' in perf_summary:
                    metrics.append(PerformanceMetric(
                        timestamp=timestamp,
                        source='load_balancer_pro',
                        metric_name='health_score',
                        value=float(perf_summary['health_score'])
                    ))
            
            # Extract from current metrics if available
            current_metrics = dashboard_data.get('current_metrics', {})
            
            for app_id, app_metrics in current_metrics.items():
                if isinstance(app_metrics, dict) and 'data' in app_metrics:
                    app_data = app_metrics['data']
                    
                    # Extract numeric metrics
                    for key, value in app_data.items():
                        if isinstance(value, (int, float)):
                            metrics.append(PerformanceMetric(
                                timestamp=timestamp,
                                source=app_id,
                                metric_name=key,
                                value=float(value)
                            ))
        
        except Exception as e:
            logger.error(f"Error extracting metrics: {e}")
        
        return metrics
    
    def _create_anomaly_timeline_chart(self) -> str:
        """Create anomaly timeline visualization"""
        try:
            anomalies = self.ml_engine.get_recent_anomalies(hours=24)
            
            if not anomalies:
                return self._create_empty_chart("No anomalies detected in the last 24 hours")
            
            # Prepare data
            timestamps = [datetime.fromtimestamp(a['timestamp']) for a in anomalies]
            severities = [a['severity'] for a in anomalies]
            confidences = [a['confidence'] for a in anomalies]
            descriptions = [a['description'] for a in anomalies]
            
            # Color mapping for severities
            color_map = {
                'low': '#28a745',
                'medium': '#ffc107',
                'high': '#ff7f0e',
                'critical': '#dc3545'
            }
            
            colors = [color_map.get(sev, '#6c757d') for sev in severities]
            
            # Create scatter plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=confidences,
                mode='markers+text',
                marker=dict(
                    size=[c*20 + 10 for c in confidences],  # Size based on confidence
                    color=colors,
                    opacity=0.7
                ),
                text=[desc[:30] + '...' if len(desc) > 30 else desc for desc in descriptions],
                textposition="top center",
                name="Anomalies",
                hovertemplate="<b>%{text}</b><br>Confidence: %{y:.2f}<br>Time: %{x}<extra></extra>"
            ))
            
            fig.update_layout(
                title='Anomaly Detection Timeline (24 Hours)',
                xaxis_title='Time',
                yaxis_title='Confidence Score',
                height=300,
                showlegend=False
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating anomaly timeline: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_prediction_chart(self) -> str:
        """Create performance prediction visualization"""
        try:
            predictions = self.ml_engine.get_predictions()
            
            if not predictions:
                return self._create_empty_chart("No predictions available")
            
            # Group predictions by metric
            metrics_data = {}
            for pred in predictions:
                metric = pred['metric_name']
                if metric not in metrics_data:
                    metrics_data[metric] = []
                metrics_data[metric].append(pred)
            
            fig = make_subplots(
                rows=len(metrics_data), cols=1,
                subplot_titles=list(metrics_data.keys()),
                vertical_spacing=0.1
            )
            
            row = 1
            for metric, preds in metrics_data.items():
                # Sort by prediction time
                preds.sort(key=lambda x: x['target_time'])
                
                times = [datetime.fromtimestamp(p['target_time']) for p in preds]
                values = [p['predicted_value'] for p in preds]
                lower_bounds = [p['confidence_interval'][0] for p in preds]
                upper_bounds = [p['confidence_interval'][1] for p in preds]
                
                # Add prediction line
                fig.add_trace(go.Scatter(
                    x=times,
                    y=values,
                    mode='lines+markers',
                    name=f'{metric} prediction',
                    line=dict(color='blue')
                ), row=row, col=1)
                
                # Add confidence interval
                fig.add_trace(go.Scatter(
                    x=times + times[::-1],
                    y=upper_bounds + lower_bounds[::-1],
                    fill='toself',
                    fillcolor='rgba(0,100,80,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name=f'{metric} confidence',
                    showlegend=False
                ), row=row, col=1)
                
                row += 1
            
            fig.update_layout(
                title='Performance Predictions',
                height=300 * len(metrics_data),
                showlegend=True
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating prediction chart: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_capacity_forecast_chart(self) -> str:
        """Create capacity forecasting chart"""
        try:
            recommendations = self.ml_engine.get_capacity_recommendations()
            
            if not recommendations:
                return self._create_empty_chart("No capacity recommendations available")
            
            # Prepare data
            components = [r['component'] for r in recommendations]
            utilizations = [r['current_utilization'] * 100 for r in recommendations]  # Convert to percentage
            predicted_peaks = [r['predicted_peak'] for r in recommendations]
            urgencies = [r['urgency'] for r in recommendations]
            
            # Color mapping for urgencies
            color_map = {
                'low': '#28a745',
                'medium': '#ffc107',
                'high': '#ff7f0e',
                'critical': '#dc3545'
            }
            
            colors = [color_map.get(urgency, '#6c757d') for urgency in urgencies]
            
            fig = go.Figure()
            
            # Current utilization bars
            fig.add_trace(go.Bar(
                x=components,
                y=utilizations,
                name='Current Utilization (%)',
                marker_color=colors,
                opacity=0.7
            ))
            
            # Add capacity limit line at 100%
            fig.add_hline(y=100, line_dash="dash", line_color="red", 
                         annotation_text="Capacity Limit")
            
            # Add warning zone at 80%
            fig.add_hline(y=80, line_dash="dot", line_color="orange", 
                         annotation_text="Warning Zone")
            
            fig.update_layout(
                title='Capacity Utilization Forecast',
                xaxis_title='Components',
                yaxis_title='Utilization (%)',
                height=300,
                yaxis=dict(range=[0, 120])
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating capacity forecast: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_model_performance_chart(self) -> str:
        """Create ML model performance chart"""
        try:
            summary = self.ml_engine.get_analysis_summary()
            model_perf = summary.get('model_performance', {})
            
            if not model_perf:
                return self._create_empty_chart("No model performance data available")
            
            # Extract MSE values for different metrics
            metrics = []
            mse_values = []
            
            for key, value in model_perf.items():
                if key.endswith('_mse') and isinstance(value, (int, float)):
                    metric_name = key.replace('_mse', '')
                    metrics.append(metric_name)
                    mse_values.append(value)
            
            if not metrics:
                return self._create_empty_chart("No MSE data available")
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=metrics,
                y=mse_values,
                name='Mean Squared Error',
                marker_color='lightblue'
            ))
            
            fig.update_layout(
                title='ML Model Performance (Lower MSE = Better)',
                xaxis_title='Metrics',
                yaxis_title='Mean Squared Error',
                height=300
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating model performance chart: {e}")
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
# Factory Function
# =============================================================================

def create_advanced_analytics_dashboard(config: Dict[str, Any] = None) -> AdvancedAnalyticsDashboard:
    """Factory function to create Advanced Analytics Dashboard"""
    return AdvancedAnalyticsDashboard(config)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point for testing"""
    print("🧠 Advanced Analytics Dashboard Integration")
    print("=" * 50)
    
    if not ML_ENGINE_AVAILABLE:
        print("❌ ML Analytics Engine not available")
        return
    
    # Create dashboard integration
    dashboard = create_advanced_analytics_dashboard()
    dashboard.start()
    
    # Test with sample data
    sample_dashboard_data = {
        'performance_summary': {
            'total_network_flows': 1500,
            'packet_rate': 2500.0,
            'total_lb_connections': 150,
            'average_response_time': 125.5,
            'error_rate': 0.02,
            'health_score': 0.95
        }
    }
    
    # Process metrics
    print("📊 Processing sample dashboard metrics...")
    dashboard.process_dashboard_metrics(sample_dashboard_data)
    
    # Get insights
    print("🔍 Getting ML insights...")
    insights = dashboard.get_ml_insights()
    
    print("ML Insights Summary:")
    if insights['available']:
        print(f"  Models trained: {insights['ml_status']['models_trained']}")
        print(f"  Metrics analyzed: {insights['ml_status']['metrics_analyzed']}")
        print(f"  Recent anomalies: {insights['anomalies']['count']}")
        print(f"  Active predictions: {insights['predictions']['count']}")
        print(f"  Capacity recommendations: {insights['recommendations']['count']}")
    else:
        print(f"  Status: {insights.get('message', 'Not available')}")
    
    # Get intelligent alerts
    alerts = dashboard.get_intelligent_alerts()
    if alerts:
        print(f"\n🚨 Intelligent Alerts ({len(alerts)} found):")
        for alert in alerts[:3]:
            print(f"  - {alert['title']} ({alert['severity']})")
    
    # Get optimization suggestions
    suggestions = dashboard.get_optimization_suggestions()
    if suggestions:
        print(f"\n💡 Optimization Suggestions ({len(suggestions)} found):")
        for suggestion in suggestions[:3]:
            print(f"  - {suggestion['title']} ({suggestion['priority']})")
    
    dashboard.stop()
    print("\n✅ Advanced Analytics Dashboard Integration test complete!")

if __name__ == "__main__":
    main()

