#!/usr/bin/env python3
"""
Enhanced MeshAdmin Performance Analytics Dashboard with ML Integration

This is an enhanced version of the Performance Dashboard that integrates
advanced machine learning analytics, predictive insights, and intelligent
monitoring capabilities.

Features:
- Real-time performance monitoring (Network Flow Master & Load Balancer Pro)
- Advanced ML-powered analytics and predictions
- Intelligent anomaly detection and alerts
- Capacity planning recommendations
- Interactive visualization with predictive charts
- Correlation analysis between applications
- Automated optimization suggestions
"""

import sys
import os
import time
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor

# Add project directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# Try to import our custom modules
try:
    from dashboard import (
        PerformanceAnalyticsDashboard,
        ApplicationIntegration,
        create_analytics_dashboard
    )
    DASHBOARD_AVAILABLE = True
except ImportError:
    print("⚠️ Base dashboard not available")
    DASHBOARD_AVAILABLE = False

try:
    # Try to import from both locations
    sys.path.insert(0, os.path.join(current_dir, 'advanced-analytics'))
    from dashboard_integration import (
        AdvancedAnalyticsDashboard,
        create_advanced_analytics_dashboard
    )
    ML_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML integration not available: {e}")
    ML_INTEGRATION_AVAILABLE = False

try:
    from llm_integration import (
        PerformanceAnalyticsLLM,
        create_llm_integration,
        LLMConfig
    )
    LLM_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LLM integration not available: {e}")
    LLM_INTEGRATION_AVAILABLE = False

# External dependencies
try:
    import flask
    from flask import Flask, render_template_string, jsonify, request, Response
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    print("⚠️ Flask not available for web interface")
    FLASK_AVAILABLE = False

try:
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots
    import plotly.utils
    PLOTLY_AVAILABLE = True
except ImportError:
    print("⚠️ Plotly not available")
    PLOTLY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced-dashboard")

# =============================================================================
# Enhanced Dashboard Configuration
# =============================================================================

@dataclass
class DashboardConfig:
    """Configuration for the Enhanced Dashboard"""
    port: int = 8080
    host: str = "0.0.0.0"
    update_interval: int = 30
    ml_enabled: bool = True
    auto_refresh: bool = True
    alert_thresholds: Dict[str, float] = None
    capacity_warning_threshold: float = 0.8
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'response_time': 500.0,
                'error_rate': 0.05,
                'packet_rate': 10000.0,
                'connection_count': 1000
            }

# =============================================================================
# Enhanced Performance Dashboard
# =============================================================================

class EnhancedPerformanceDashboard:
    """
    Enhanced Performance Analytics Dashboard with ML Integration
    
    Combines real-time monitoring with advanced ML analytics for comprehensive
    performance insights and predictive capabilities.
    """
    
    def __init__(self, config: DashboardConfig = None):
        self.config = config or DashboardConfig()
        self.is_running = False
        self.update_thread = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize components
        self.base_dashboard: Optional[PerformanceAnalyticsDashboard] = None
        self.ml_dashboard: Optional[AdvancedAnalyticsDashboard] = None
        self.llm_analytics: Optional[Any] = None
        self.flask_app: Optional[Flask] = None
        
        # Data storage
        self.current_data = {}
        self.ml_insights = {}
        self.alerts = []
        self.suggestions = []
        self.predictive_charts = {}
        
        # Initialize base dashboard
        if DASHBOARD_AVAILABLE:
            dashboard_config = {
                'update_interval': self.config.update_interval,
                'buffer_size': 1000
            }
            self.base_dashboard = create_analytics_dashboard(dashboard_config)
        
        # Initialize ML dashboard if enabled
        if self.config.ml_enabled and ML_INTEGRATION_AVAILABLE:
            ml_config = {
                'update_interval': self.config.update_interval,
                'prediction_horizon': 3600,
                'anomaly_sensitivity': 'medium'
            }
            self.ml_dashboard = create_advanced_analytics_dashboard(ml_config)
        
        # Initialize LLM integration if available
        if LLM_INTEGRATION_AVAILABLE:
            llm_config = LLMConfig(
                models_path="/Users/cnelson/models",
                default_model="llama-3.2-8b"  # Updated to match available models
            )
            self.llm_analytics = create_llm_integration(llm_config)
        
        # Initialize Flask app
        if FLASK_AVAILABLE:
            self._setup_flask_app()
        
        logger.info("🚀 Enhanced Performance Dashboard initialized")
    
    def start(self) -> None:
        """Start the enhanced dashboard"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start base dashboard
        if self.base_dashboard:
            self.base_dashboard.start()
        
        # Start ML dashboard
        if self.ml_dashboard:
            self.ml_dashboard.start()
        
        # Start update thread
        if self.config.auto_refresh:
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
        
        logger.info("✅ Enhanced Performance Dashboard started")
        
        # Start Flask server if available
        if self.flask_app and FLASK_AVAILABLE:
            logger.info(f"🌐 Web interface available at http://{self.config.host}:{self.config.port}")
            self.flask_app.run(
                host=self.config.host,
                port=self.config.port,
                debug=False,
                threaded=True
            )
    
    def stop(self) -> None:
        """Stop the enhanced dashboard"""
        self.is_running = False
        
        if self.base_dashboard:
            self.base_dashboard.stop()
        
        if self.ml_dashboard:
            self.ml_dashboard.stop()
        
        self.executor.shutdown(wait=True)
        logger.info("🛑 Enhanced Performance Dashboard stopped")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        # If no data is available, provide mock data for UI testing
        if not self.current_data:
            self.current_data = self._generate_mock_data()
        
        if not self.ml_insights:
            self.ml_insights = self._generate_mock_ml_insights()
        
        if not self.alerts:
            self.alerts = self._generate_mock_alerts()
        
        if not self.suggestions:
            self.suggestions = self._generate_mock_suggestions()
        
        data = {
            'timestamp': time.time(),
            'status': 'running' if self.is_running else 'stopped',
            'base_available': self.base_dashboard is not None,
            'ml_available': self.ml_dashboard is not None,
            'current_data': self.current_data,
            'ml_insights': self.ml_insights,
            'alerts': self.alerts,
            'suggestions': self.suggestions,
            'predictive_charts': self.predictive_charts,
            'config': asdict(self.config)
        }
        
        return data
    
    def force_update(self) -> None:
        """Force an immediate update of all data"""
        self._update_data()
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _update_loop(self) -> None:
        """Main update loop for real-time data"""
        logger.info("🔄 Starting update loop")
        
        while self.is_running:
            try:
                self._update_data()
                time.sleep(self.config.update_interval)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(5)  # Short delay on error
    
    def _update_data(self) -> None:
        """Update all dashboard data"""
        try:
            # Update base dashboard data
            if self.base_dashboard:
                self.current_data = self.base_dashboard.get_current_metrics()
                
                # Feed data to ML dashboard
                if self.ml_dashboard:
                    self.ml_dashboard.process_dashboard_metrics(self.current_data)
            
            # Update ML insights
            if self.ml_dashboard:
                self.ml_insights = self.ml_dashboard.get_ml_insights()
                self.alerts = self.ml_dashboard.get_intelligent_alerts()
                self.suggestions = self.ml_dashboard.get_optimization_suggestions()
                
                # Update predictive charts
                if PLOTLY_AVAILABLE:
                    self.predictive_charts = self.ml_dashboard.get_predictive_charts()
            
            logger.debug("📊 Dashboard data updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating dashboard data: {e}")
    
    def _setup_flask_app(self) -> None:
        """Setup Flask web application"""
        self.flask_app = Flask(__name__)
        CORS(self.flask_app)
        
        # Static file serving
        @self.flask_app.route('/static/<path:filename>')
        def static_files(filename):
            import os
            from flask import send_from_directory
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            return send_from_directory(static_dir, filename)
        
        # Main dashboard route
        @self.flask_app.route('/')
        def dashboard():
            return render_template_string(self._get_dashboard_template())
        
        # API endpoints
        @self.flask_app.route('/api/data')
        def api_data():
            return jsonify(self.get_dashboard_data())
        
        @self.flask_app.route('/api/update', methods=['POST'])
        def api_update():
            self.force_update()
            return jsonify({'status': 'updated'})
        
        @self.flask_app.route('/api/insights')
        def api_insights():
            return jsonify(self.ml_insights)
        
        @self.flask_app.route('/api/alerts')
        def api_alerts():
            return jsonify(self.alerts)
        
        @self.flask_app.route('/api/suggestions')
        def api_suggestions():
            return jsonify(self.suggestions)
        
        @self.flask_app.route('/api/charts')
        def api_charts():
            return jsonify(self.predictive_charts)
        
        # LLM Model Management APIs
        @self.flask_app.route('/api/llm/status')
        def api_llm_status():
            if self.llm_analytics:
                return jsonify(self.llm_analytics.get_model_status())
            return jsonify({'available': False, 'message': 'LLM integration not available'})
        
        @self.flask_app.route('/api/llm/models')
        def api_llm_models():
            if self.llm_analytics:
                return jsonify(self.llm_analytics.llm.list_available_models())
            return jsonify([])
        
        @self.flask_app.route('/api/llm/load', methods=['POST'])
        def api_llm_load():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            data = request.get_json()
            model_name = data.get('model_name')
            
            # Check if this is an SSE-enabled request
            if request.args.get('sse') == 'true':
                return jsonify({'success': True, 'streaming': True, 'message': 'Use /api/llm/load_stream for progress updates'})
            
            try:
                success = self.llm_analytics.llm.load_model(model_name)
                return jsonify({
                    'success': success,
                    'message': f'Model {model_name} loaded successfully' if success else f'Failed to load model {model_name}'
                })
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.flask_app.route('/api/llm/load_stream')
        def api_llm_load_stream():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            model_name = request.args.get('model')
            if not model_name:
                return jsonify({'success': False, 'message': 'Model name is required'})
            
            def generate_progress():
                import time
                import json
                
                try:
                    # Send initial connection status
                    yield f"data: {json.dumps({'stage': 'connecting', 'pct': 0, 'message': 'Establishing connection...'})}\n\n"
                    time.sleep(0.5)
                    
                    # Simulate model loading stages with progress
                    stages = [
                        {'stage': 'initializing', 'pct': 10, 'message': 'Initializing model loader...'},
                        {'stage': 'loading', 'pct': 25, 'message': 'Loading model file...'},
                        {'stage': 'parsing', 'pct': 45, 'message': 'Parsing model structure...'},
                        {'stage': 'quantizing', 'pct': 70, 'message': 'Applying quantization...'},
                        {'stage': 'optimizing', 'pct': 85, 'message': 'Optimizing for inference...'},
                        {'stage': 'finalizing', 'pct': 95, 'message': 'Finalizing setup...'}
                    ]
                    
                    for stage_info in stages:
                        yield f"data: {json.dumps(stage_info)}\n\n"
                        time.sleep(1)  # Simulate processing time
                    
                    # Attempt actual model loading
                    try:
                        success = self.llm_analytics.llm.load_model(model_name)
                        
                        if success:
                            yield f"data: {json.dumps({
                                'stage': 'complete',
                                'pct': 100,
                                'message': f'Model {model_name} loaded successfully',
                                'complete': True
                            })}\n\n"
                        else:
                            yield f"data: {json.dumps({
                                'error': f'Failed to load model {model_name}. Check model file and configuration.',
                                'stage': 'error',
                                'pct': 0
                            })}\n\n"
                    
                    except Exception as load_error:
                        # Handle specific error types
                        error_message = str(load_error)
                        
                        if "out of memory" in error_message.lower() or "oom" in error_message.lower():
                            yield f"data: {json.dumps({'error': 'OOM on GPU - Model too large for available GPU memory'})}\n\n"
                        elif "not found" in error_message.lower():
                            yield f"data: {json.dumps({'error': f'Model file not found: {model_name}'})}\n\n"
                        elif "permission" in error_message.lower():
                            yield f"data: {json.dumps({'error': 'Permission denied accessing model file'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'error': f'Failed to load model: {error_message}'})}\n\n"
                
                except Exception as e:
                    yield f"data: {json.dumps({'error': f'Streaming error: {str(e)}'})}\n\n"
            
            return Response(
                generate_progress(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'  # Disable nginx buffering
                }
            )
        
        @self.flask_app.route('/api/llm/unload', methods=['POST'])
        def api_llm_unload():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            try:
                self.llm_analytics.llm.model = None
                self.llm_analytics.llm.model_loaded = False
                return jsonify({'success': True, 'message': 'Model unloaded successfully'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.flask_app.route('/api/llm/config', methods=['GET', 'POST'])
        def api_llm_config():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            if request.method == 'GET':
                return jsonify({
                    'models_path': self.llm_analytics.config.models_path,
                    'default_model': self.llm_analytics.config.default_model,
                    'max_tokens': self.llm_analytics.config.max_tokens,
                    'temperature': self.llm_analytics.config.temperature,
                    'context_window': self.llm_analytics.config.context_window,
                    'enable_gpu': self.llm_analytics.config.enable_gpu
                })
            
            elif request.method == 'POST':
                data = request.get_json()
                try:
                    # Update configuration
                    if 'models_path' in data:
                        old_path = self.llm_analytics.config.models_path
                        self.llm_analytics.config.models_path = data['models_path']
                        # Rescan models if path changed
                        if old_path != data['models_path']:
                            self.llm_analytics.llm.config.models_path = data['models_path']
                            self.llm_analytics.llm._scan_available_models()
                    
                    if 'default_model' in data:
                        self.llm_analytics.config.default_model = data['default_model']
                    if 'max_tokens' in data:
                        self.llm_analytics.config.max_tokens = int(data['max_tokens'])
                    if 'temperature' in data:
                        self.llm_analytics.config.temperature = float(data['temperature'])
                    if 'context_window' in data:
                        self.llm_analytics.config.context_window = int(data['context_window'])
                    if 'enable_gpu' in data:
                        self.llm_analytics.config.enable_gpu = bool(data['enable_gpu'])
                    
                    return jsonify({'success': True, 'message': 'Configuration updated successfully'})
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)})
        
        @self.flask_app.route('/api/llm/delete', methods=['POST'])
        def api_llm_delete():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            data = request.get_json()
            model_path = data.get('model_path')
            
            if not model_path:
                return jsonify({'success': False, 'message': 'Model path is required'})
            
            try:
                import os
                if os.path.exists(model_path):
                    os.remove(model_path)
                    # Rescan models after deletion
                    self.llm_analytics.llm._scan_available_models()
                    return jsonify({'success': True, 'message': 'Model deleted successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Model file not found'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Error deleting model: {str(e)}'})
        
        @self.flask_app.route('/api/llm/upload', methods=['POST'])
        def api_llm_upload():
            if not self.llm_analytics:
                return jsonify({'success': False, 'message': 'LLM integration not available'})
            
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file provided'})
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'})
            
            try:
                import os
                # Save uploaded file to models directory
                filename = file.filename
                filepath = os.path.join(self.llm_analytics.config.models_path, filename)
                
                # Create directory if it doesn't exist
                os.makedirs(self.llm_analytics.config.models_path, exist_ok=True)
                
                file.save(filepath)
                
                # Rescan models after upload
                self.llm_analytics.llm._scan_available_models()
                
                return jsonify({
                    'success': True, 
                    'message': f'Model {filename} uploaded successfully',
                    'path': filepath
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Error uploading model: {str(e)}'})
        
        logger.info("🌐 Flask web interface configured")
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock data for UI testing"""
        import random
        return {
            'performance_summary': {
                'total_network_flows': random.randint(1000, 2000),
                'packet_rate': f"{random.randint(2000000, 3000000):,}",
                'total_lb_connections': random.randint(200, 400),
                'average_response_time': f"{random.randint(100, 200):.2f}",
                'error_rate': random.uniform(0.01, 0.05),
                'health_score': random.uniform(0.95, 1.0)
            }
        }
    
    def _generate_mock_ml_insights(self) -> Dict[str, Any]:
        """Generate mock ML insights for UI testing"""
        import random
        return {
            'available': True,
            'ml_status': {
                'models_trained': True,
                'metrics_analyzed': random.randint(20, 50),
                'last_updated': datetime.now().isoformat()
            },
            'anomalies': {
                'count': random.randint(0, 3),
                'critical_count': random.randint(0, 1)
            },
            'predictions': {
                'count': random.randint(0, 5)
            },
            'recommendations': {
                'count': random.randint(0, 3)
            }
        }
    
    def _generate_mock_alerts(self) -> List[Dict[str, Any]]:
        """Generate mock alerts for UI testing"""
        import random
        alerts = []
        if random.random() > 0.7:  # 30% chance of having alerts
            alerts.append({
                'title': 'High Response Time Detected',
                'message': 'Average response time has increased by 25% in the last 10 minutes',
                'severity': 'medium',
                'type': 'performance',
                'confidence': 0.85,
                'timestamp': time.time()
            })
        return alerts
    
    def _generate_mock_suggestions(self) -> List[Dict[str, Any]]:
        """Generate mock suggestions for UI testing"""
        return [
            {
                'title': 'Load Balancer Optimization',
                'description': 'Consider adjusting load balancing algorithm for better performance',
                'priority': 'medium',
                'category': 'performance',
                'actions': [
                    'Review current load balancing configuration',
                    'Consider implementing weighted round-robin',
                    'Monitor backend server performance'
                ]
            }
        ]
    
    def _get_dashboard_template(self) -> str:
        """Get the HTML template for the dashboard"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MeshAdmin Enhanced Performance Analytics</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Tab System CSS -->
    <link rel="stylesheet" href="/static/css/tabs.css">
    <link rel="stylesheet" href="/static/css/llm-progress.css">
    <script src="/static/js/tabs.js"></script>
    <style>
        :root {
            --primary-bg: #000000;
            --secondary-bg: #1a1a1a;
            --card-bg: #1a1a1a;
            --bg-color: #1a1a1a;
            --primary-text: #ffffff;
            --text-color: #e0e0e0;
            --text-secondary: #b0b0b0;
            --border-color: #3d3d3d;
            --accent-color: #FF4444;
            --accent-color-light: #FF6666;
            --success-color: #00b894;
            --warning-color: #fdcb6e;
            --error-color: #e84393;
            --critical-color: #FF3333;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.3s ease;
        }
        .header {
            background: #000;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .full-width {
            grid-column: 1 / -1;
        }
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            border: 1px solid var(--border-color);
            color: var(--primary-text);
        }
        .card h3 {
            color: var(--accent-color);
            margin-top: 0;
            text-shadow: 0 0 10px rgba(255, 68, 68, 0.3);
            font-weight: 600;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin: 8px 0;
            background: var(--bg-color);
            border-radius: 8px;
            border-left: 4px solid var(--accent-color);
            color: var(--text-color);
            transition: all 0.2s ease;
        }
        .metric:hover {
            background: var(--border-color);
            transform: translateX(2px);
        }
        .metric.warning {
            border-left-color: var(--warning-color);
        }
        .metric.critical {
            border-left-color: var(--critical-color);
        }
        .alert {
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            color: var(--text-color);
            border-left: 4px solid;
            background: var(--card-bg);
            transition: all 0.2s ease;
        }
        .alert:hover {
            transform: translateX(2px);
        }
        .alert.critical {
            border-left-color: var(--critical-color);
            background: rgba(214, 48, 49, 0.1);
        }
        .alert.high {
            border-left-color: var(--error-color);
            background: rgba(232, 67, 147, 0.1);
        }
        .alert.medium {
            border-left-color: var(--warning-color);
            background: rgba(253, 203, 110, 0.1);
        }
        .alert.low {
            border-left-color: var(--success-color);
            background: rgba(0, 184, 148, 0.1);
        }
        .suggestion {
            padding: 16px;
            margin: 12px 0;
            border-radius: 8px;
            border-left: 4px solid var(--accent-color-light);
            background: var(--card-bg);
            color: var(--text-color);
            transition: all 0.2s ease;
        }
        .suggestion:hover {
            background: var(--border-color);
            transform: translateX(2px);
        }
        .suggestion h4 {
            color: var(--accent-color-light);
            margin-top: 0;
        }
        .chart-container {
            height: 400px;
            margin: 20px 0;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 8px rgba(255,255,255,0.3);
        }
        .status-running {
            background-color: var(--success-color);
            box-shadow: 0 0 8px var(--success-color);
        }
        .status-stopped {
            background-color: var(--critical-color);
            box-shadow: 0 0 8px var(--critical-color);
        }
        .refresh-btn {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            margin: 10px 5px;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(139, 0, 0, 0.3);
        }
        .refresh-btn:hover {
            background: var(--accent-color-light);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(197, 0, 0, 0.4);
        }
        
        /* Dark mode for Plotly charts */
        .chart-container {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 10px;
            margin: 20px 0;
        }
        
        /* LLM Model Management Styles */
        .model-select-container {
            margin: 15px 0;
        }
        
        .model-select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
            margin-bottom: 15px;
        }
        
        .model-select:focus {
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px rgba(255, 68, 68, 0.2);
        }
        
        .model-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .model-info {
            font-size: 12px;
            color: var(--text-secondary);
            margin-left: 10px;
            flex: 1;
        }
        
        .model-btn {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s ease;
        }
        
        .model-btn:hover {
            background: var(--accent-color-light);
            transform: translateY(-1px);
        }
        
        .model-btn.danger {
            background: var(--critical-color);
        }
        
        .model-btn.danger:hover {
            background: #b71c1c;
        }
        
        .model-btn.success {
            background: var(--success-color);
        }
        
        .form-group {
            margin: 15px 0;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: var(--text-color);
            font-weight: 500;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px rgba(139, 0, 0, 0.2);
        }
        
        .config-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .upload-area {
            border: 2px dashed var(--border-color);
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: var(--accent-color);
            background: rgba(139, 0, 0, 0.05);
        }
        
        .upload-area.dragover {
            border-color: var(--success-color);
            background: rgba(0, 184, 148, 0.1);
        }
        
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status-loaded {
            background: rgba(0, 184, 148, 0.2);
            color: var(--success-color);
        }
        
        .status-available {
            background: rgba(255, 68, 68, 0.2);
            color: var(--accent-color);
            text-shadow: 0 0 6px rgba(255, 68, 68, 0.5);
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
        }
        
        .modal-content {
            background-color: var(--card-bg);
            margin: 5% auto;
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            width: 80%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .close {
            color: var(--text-secondary);
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover {
            color: var(--text-color);
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            
            .model-actions {
                flex-direction: column;
                align-items: stretch;
            }
            
            .model-info {
                margin-left: 0;
                margin-top: 10px;
                text-align: center;
            }
            
            .config-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* Contrast outline helper class for QA */
        .contrast-outline {
            outline: 2px dashed #00ff00 !important;
            outline-offset: 2px;
        }
        
        .contrast-outline::after {
            content: 'CONTRAST CHECK';
            position: absolute;
            top: -20px;
            left: 0;
            background: #00ff00;
            color: #000;
            font-size: 10px;
            padding: 2px 4px;
            font-weight: bold;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <!-- Dashboard Header -->
    <header class="header" role="banner">
        <div class="container-fluid">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                <div style="flex: 2;">
                    <h1 style="margin: 0;">🚀 MeshAdmin Enhanced Performance Analytics</h1>
                    <p style="margin: 5px 0 0 0;">Real-time monitoring with ML-powered insights and predictions</p>
                </div>
                <div style="flex: 1; text-align: right;">
                    <div style="display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap;">
                        <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
                        <button class="refresh-btn" onclick="toggleAutoRefresh()" id="autoRefreshBtn">⏸️ Pause Auto-refresh</button>
                        <button class="refresh-btn" data-flyout="llm-config-flyout">⚙️ LLM Config</button>
                        <button class="refresh-btn" data-flyout="llm-upload-flyout">📤 Upload</button>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <main class="container-fluid" role="main">
        <!-- Tab Navigation -->
        <nav class="tab-navigation" role="navigation" aria-label="Dashboard sections">
            <ul class="tab-nav" role="tablist">
                <li class="tab-nav-item">
                    <button class="tab-nav-link" data-tab="system-status" role="tab" aria-selected="false" tabindex="0" aria-controls="system-status">
                        <i class="fas fa-server" aria-hidden="true"></i>System Status
                    </button>
                </li>
                <li class="tab-nav-item">
                    <button class="tab-nav-link" data-tab="performance-summary" role="tab" aria-selected="false" tabindex="-1" aria-controls="performance-summary">
                        <i class="fas fa-chart-bar" aria-hidden="true"></i>Performance Summary
                    </button>
                </li>
                <li class="tab-nav-item">
                    <button class="tab-nav-link" data-tab="ml-insights" role="tab" aria-selected="false" tabindex="-1" aria-controls="ml-insights">
                        <i class="fas fa-brain" aria-hidden="true"></i>ML Insights
                    </button>
                </li>
                <li class="tab-nav-item">
                    <button class="tab-nav-link" data-tab="llm-management" role="tab" aria-selected="false" tabindex="-1" aria-controls="llm-management">
                        <i class="fas fa-robot" aria-hidden="true"></i>LLM Management
                    </button>
                </li>
            </ul>
        </nav>

        <!-- Tab Content -->
        <div class="tab-content">
            <!-- System Status Tab -->
            <section id="system-status" class="tab-pane" role="tabpanel" aria-labelledby="system-status-tab">
                <div class="tab-section">
                    <header class="tab-actions">
                        <h2><i class="fas fa-server me-2" aria-hidden="true"></i>System Status Overview</h2>
                        <p class="text-muted">Monitor the health and status of all system components</p>
                    </header>
                    
                    <div class="container">
                        <div class="card">
                            <h3>📊 System Status</h3>
                            <div id="systemStatus">
                                <div class="metric">
                                    <span>Dashboard Status</span>
                                    <span><span class="status-indicator" id="statusIndicator"></span><span id="statusText">Loading...</span></span>
                                </div>
                                <div class="metric">
                                    <span>ML Analytics</span>
                                    <span id="mlStatus">Loading...</span>
                                </div>
                                <div class="metric">
                                    <span>Last Updated</span>
                                    <span id="lastUpdated">Loading...</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3>🚨 Recent Alerts</h3>
                            <div id="alertsContainer">
                                Loading alerts...
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Performance Summary Tab -->
            <section id="performance-summary" class="tab-pane" role="tabpanel">
                <div class="tab-section">
                    <header class="tab-actions">
                        <h2><i class="fas fa-chart-bar me-2"></i>Performance Summary</h2>
                        <p class="text-muted">Comprehensive performance metrics and trends analysis</p>
                    </header>
                    
                    <div class="container">
                        <div class="card">
                            <h3>⚡ Performance Summary</h3>
                            <div id="performanceSummary">
                                Loading performance data...
                            </div>
                        </div>
                        
                        <div class="card full-width">
                            <h3>📈 Predictive Analytics</h3>
                            <div id="predictiveCharts">
                                <div class="chart-container" id="anomalyChart"></div>
                                <div class="chart-container" id="predictionChart"></div>
                                <div class="chart-container" id="capacityChart"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- ML Insights Tab -->
            <section id="ml-insights" class="tab-pane" role="tabpanel">
                <div class="tab-section">
                    <header class="tab-actions">
                        <h2><i class="fas fa-brain me-2"></i>ML Insights</h2>
                        <p class="text-muted">Advanced correlation analysis and machine learning insights</p>
                    </header>
                    
                    <div class="container">
                        <div class="card">
                            <h3>🧠 ML Insights</h3>
                            <div id="mlInsights">
                                Loading ML insights...
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3>💡 Optimization Suggestions</h3>
                            <div id="suggestionsContainer">
                                Loading suggestions...
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- LLM Management Tab -->
            <section id="llm-management" class="tab-pane" role="tabpanel">
                <div class="tab-section">
                    <header class="tab-actions">
                        <h2><i class="fas fa-robot me-2"></i>LLM Management</h2>
                        <p class="text-muted">Configure and manage Large Language Models for enhanced analytics</p>
                        <button class="refresh-btn" data-flyout="llm-config-flyout">⚙️ Configure LLM</button>
                        <button class="refresh-btn" data-flyout="llm-upload-flyout">📤 Upload Model</button>
                    </header>
                    
                    <div class="container">
                        <div class="card full-width">
                            <h3>🤖 LLM Model Management</h3>
                            <div id="llmManagement">
                                <div style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center;">
                                    <button class="refresh-btn" onclick="loadLLMStatus()">🔄 Refresh Models</button>
                                    <span id="llmStatusText" style="color: var(--text-secondary);">Loading LLM status...</span>
                                </div>
                                
                                <!-- Model Selection Dropdown -->
                                <div class="model-select-container">
                                    <label for="modelSelect" style="display: block; margin-bottom: 5px; color: var(--text-color); font-weight: 500;">Select Model:</label>
                                    <select id="modelSelect" style="width: 100%; padding: 10px 12px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-color); color: var(--text-color); font-size: 14px; margin-bottom: 15px;">
                                        <option value="">Loading models...</option>
                                    </select>
                                    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                                        <button class="model-btn success" onclick="loadSelectedModel()" id="loadSelectedBtn">📥 Load Selected</button>
                                        <button class="model-btn" onclick="unloadModel()" id="unloadSelectedBtn">📤 Unload Current</button>
                                        <button class="model-btn danger" onclick="deleteSelectedModel()" id="deleteSelectedBtn">🗑️ Delete Selected</button>
                                        <span id="modelInfo" style="font-size: 12px; color: var(--text-secondary); margin-left: 10px; flex: 1;">Select a model to see details</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </main>

    <!-- LLM Configuration Flyout -->
    <div id="llm-config-flyout" class="flyout-modal">
        <div class="flyout-header">
            <h3 class="flyout-title">LLM Configuration</h3>
            <button class="flyout-close" aria-label="Close">&times;</button>
        </div>
        <div class="flyout-body">
            <form id="llm-config-form">
                <div class="form-group">
                    <label for="flyout-models-path">Models Directory:</label>
                    <input type="text" id="flyout-models-path" placeholder="/Volumes/Seagate-5TB/models">
                </div>
                
                <div class="form-group">
                    <label for="flyout-default-model">Default Model:</label>
                    <select id="flyout-default-model" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-color); color: var(--text-color); font-size: 14px;">
                        <option value="">Select default model...</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="flyout-max-tokens">Max Tokens:</label>
                    <input type="number" id="flyout-max-tokens" min="1" max="8192" value="2048">
                </div>
                
                <div class="form-group">
                    <label for="flyout-temperature">Temperature:</label>
                    <input type="number" id="flyout-temperature" min="0" max="2" step="0.1" value="0.7">
                </div>
                
                <div class="form-group">
                    <label for="flyout-context-window">Context Window:</label>
                    <input type="number" id="flyout-context-window" min="512" max="32768" value="4096">
                </div>
                
                <div class="form-group">
                    <label for="flyout-enable-gpu">Enable GPU:</label>
                    <select id="flyout-enable-gpu">
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
            </form>
        </div>
        <div class="flyout-footer">
            <button type="button" class="refresh-btn flyout-close">Cancel</button>
            <button type="submit" form="llm-config-form" class="refresh-btn" onclick="saveFlyoutConfig()">Save Configuration</button>
        </div>
    </div>

    <!-- LLM Upload Flyout -->
    <div id="llm-upload-flyout" class="flyout-modal">
        <div class="flyout-header">
            <h3 class="flyout-title">Upload LLM Model</h3>
            <button class="flyout-close" aria-label="Close">&times;</button>
        </div>
        <div class="flyout-body">
            <form id="llm-upload-form">
                <div class="upload-area" id="flyoutUploadArea" onclick="document.getElementById('flyoutFileInput').click()">
                    <p>📁 Click to select model file or drag and drop</p>
                    <p style="color: var(--text-secondary); font-size: 12px;">Supported formats: .gguf, .bin, .safetensors, .pt, .pth</p>
                    <input type="file" id="flyoutFileInput" style="display: none;" accept=".gguf,.bin,.safetensors,.pt,.pth" onchange="uploadFlyoutModel()">
                </div>
                
                <div id="flyoutFilePreview" style="margin-top: 15px;"></div>
                
                <div class="form-group">
                    <label for="flyout-model-name">Model Name:</label>
                    <input type="text" id="flyout-model-name" placeholder="Enter a name for this model" required>
                </div>
                
                <div class="form-group">
                    <label for="flyout-model-description">Description:</label>
                    <textarea id="flyout-model-description" rows="3" placeholder="Describe this model and its capabilities..." style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-color); color: var(--text-color); font-size: 14px; resize: vertical;"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="flyout-model-type">Model Type:</label>
                    <select id="flyout-model-type" required>
                        <option value="">Select model type...</option>
                        <option value="text-generation">Text Generation</option>
                        <option value="classification">Classification</option>
                        <option value="embedding">Embedding</option>
                        <option value="chat">Chat</option>
                    </select>
                </div>
                
                <div id="flyoutUploadProgress" style="display: none; margin-top: 15px;">
                    <label>Upload Progress:</label>
                    <div style="background: var(--border-color); border-radius: 4px; overflow: hidden; margin-top: 5px;">
                        <div id="flyoutProgressBar" style="height: 20px; background: var(--accent-color); width: 0%; transition: width 0.3s ease;"></div>
                    </div>
                    <p id="flyoutUploadStatus" style="margin-top: 10px; color: var(--text-secondary);">Uploading...</p>
                </div>
            </form>
        </div>
        <div class="flyout-footer">
            <button type="button" class="refresh-btn flyout-close">Cancel</button>
            <button type="submit" form="llm-upload-form" class="refresh-btn" onclick="uploadFlyoutModel()">Upload Model</button>
        </div>
    </div>

    <!-- Configuration Modal -->
    <div id="configModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('configModal')">&times;</span>
            <h3>🤖 LLM Configuration</h3>
            <form id="configForm">
                <div class="config-grid">
                    <div class="form-group">
                        <label for="modelsPath">Models Directory:</label>
                        <input type="text" id="modelsPath" placeholder="/Volumes/Seagate-5TB/models">
                    </div>
                    <div class="form-group">
                        <label for="defaultModel">Default Model:</label>
                        <select id="defaultModel" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-color); color: var(--text-color); font-size: 14px;">
                            <option value="">Select default model...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="maxTokens">Max Tokens:</label>
                        <input type="number" id="maxTokens" min="1" max="8192" value="2048">
                    </div>
                    <div class="form-group">
                        <label for="temperature">Temperature:</label>
                        <input type="number" id="temperature" min="0" max="2" step="0.1" value="0.7">
                    </div>
                    <div class="form-group">
                        <label for="contextWindow">Context Window:</label>
                        <input type="number" id="contextWindow" min="512" max="32768" value="4096">
                    </div>
                    <div class="form-group">
                        <label for="enableGpu">Enable GPU:</label>
                        <select id="enableGpu">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <button type="button" class="refresh-btn" onclick="saveConfig()">💾 Save Configuration</button>
                    <button type="button" class="refresh-btn" onclick="closeModal('configModal')">❌ Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Upload Modal -->
    <div id="uploadModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('uploadModal')">&times;</span>
            <h3>📤 Upload Model</h3>
            <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
                <p>📁 Click to select model file or drag and drop</p>
                <p style="color: var(--text-secondary); font-size: 12px;">Supported formats: .gguf, .bin, .safetensors, .pt, .pth</p>
                <input type="file" id="fileInput" style="display: none;" accept=".gguf,.bin,.safetensors,.pt,.pth" onchange="uploadModel()">
            </div>
            <div id="uploadProgress" style="display: none; margin-top: 15px;">
                <div style="background: var(--border-color); border-radius: 4px; overflow: hidden;">
                    <div id="progressBar" style="height: 20px; background: var(--accent-color); width: 0%; transition: width 0.3s ease;"></div>
                </div>
                <p id="uploadStatus" style="margin-top: 10px; color: var(--text-secondary);">Uploading...</p>
            </div>
        </div>
    </div>

    <script>
        let autoRefresh = true;
        let refreshInterval;

        function refreshData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    updateDashboard(data);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        function updateDashboard(data) {
            // Update system status
            const statusIndicator = document.getElementById('statusIndicator');
            const statusText = document.getElementById('statusText');
            
            if (data.status === 'running') {
                statusIndicator.className = 'status-indicator status-running';
                statusText.textContent = 'Running';
            } else {
                statusIndicator.className = 'status-indicator status-stopped';
                statusText.textContent = 'Stopped';
            }

            document.getElementById('mlStatus').textContent = data.ml_available ? '✅ Available' : '❌ Not Available';
            document.getElementById('lastUpdated').textContent = new Date(data.timestamp * 1000).toLocaleTimeString();

            // Update performance summary
            updatePerformanceSummary(data.current_data);

            // Update ML insights
            updateMLInsights(data.ml_insights);

            // Update alerts
            updateAlerts(data.alerts);

            // Update suggestions
            updateSuggestions(data.suggestions);

            // Update charts
            updateCharts(data.predictive_charts);
        }

        function updatePerformanceSummary(data) {
            const container = document.getElementById('performanceSummary');
            if (!data || !data.performance_summary) {
                container.innerHTML = '<p>No performance data available</p>';
                return;
            }

            const summary = data.performance_summary;
            container.innerHTML = `
                <div class="metric">
                    <span>Network Flows</span>
                    <span>${summary.total_network_flows || 'N/A'}</span>
                </div>
                <div class="metric">
                    <span>Packet Rate</span>
                    <span>${summary.packet_rate || 'N/A'} pps</span>
                </div>
                <div class="metric">
                    <span>LB Connections</span>
                    <span>${summary.total_lb_connections || 'N/A'}</span>
                </div>
                <div class="metric">
                    <span>Response Time</span>
                    <span>${summary.average_response_time || 'N/A'} ms</span>
                </div>
                <div class="metric">
                    <span>Error Rate</span>
                    <span>${((summary.error_rate || 0) * 100).toFixed(2)}%</span>
                </div>
                <div class="metric">
                    <span>Health Score</span>
                    <span>${((summary.health_score || 0) * 100).toFixed(1)}%</span>
                </div>
            `;
        }

        function updateMLInsights(insights) {
            const container = document.getElementById('mlInsights');
            if (!insights || !insights.available) {
                container.innerHTML = '<p>ML insights not available</p>';
                return;
            }

            container.innerHTML = `
                <div class="metric">
                    <span>Models Trained</span>
                    <span>${insights.ml_status.models_trained ? '✅' : '❌'}</span>
                </div>
                <div class="metric">
                    <span>Metrics Analyzed</span>
                    <span>${insights.ml_status.metrics_analyzed}</span>
                </div>
                <div class="metric">
                    <span>Recent Anomalies</span>
                    <span>${insights.anomalies.count} (${insights.anomalies.critical_count} critical)</span>
                </div>
                <div class="metric">
                    <span>Active Predictions</span>
                    <span>${insights.predictions.count}</span>
                </div>
                <div class="metric">
                    <span>Capacity Recommendations</span>
                    <span>${insights.recommendations.count}</span>
                </div>
            `;
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alertsContainer');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p>✅ No active alerts</p>';
                return;
            }

            container.innerHTML = alerts.slice(0, 5).map(alert => `
                <div class="alert ${alert.severity}">
                    <strong>${alert.title}</strong><br>
                    ${alert.message}
                    <br><small>Type: ${alert.type} | Confidence: ${(alert.confidence * 100).toFixed(1)}%</small>
                </div>
            `).join('');
        }

        function updateSuggestions(suggestions) {
            const container = document.getElementById('suggestionsContainer');
            if (!suggestions || suggestions.length === 0) {
                container.innerHTML = '<p>💡 No optimization suggestions available</p>';
                return;
            }

            container.innerHTML = suggestions.slice(0, 3).map(suggestion => `
                <div class="suggestion">
                    <h4>${suggestion.title} (${suggestion.priority})</h4>
                    <p>${suggestion.description}</p>
                    <ul>
                        ${suggestion.actions.map(action => `<li>${action}</li>`).join('')}
                    </ul>
                </div>
            `).join('');
        }

        function updateCharts(charts) {
            if (!charts) return;

            // Update anomaly chart
            if (charts.anomaly_timeline) {
                try {
                    const chartData = JSON.parse(charts.anomaly_timeline);
                    Plotly.newPlot('anomalyChart', chartData.data, chartData.layout);
                } catch (e) {
                    document.getElementById('anomalyChart').innerHTML = '<p>Error loading anomaly chart</p>';
                }
            }

            // Update prediction chart
            if (charts.performance_predictions) {
                try {
                    const chartData = JSON.parse(charts.performance_predictions);
                    Plotly.newPlot('predictionChart', chartData.data, chartData.layout);
                } catch (e) {
                    document.getElementById('predictionChart').innerHTML = '<p>Error loading prediction chart</p>';
                }
            }

            // Update capacity chart
            if (charts.capacity_forecast) {
                try {
                    const chartData = JSON.parse(charts.capacity_forecast);
                    Plotly.newPlot('capacityChart', chartData.data, chartData.layout);
                } catch (e) {
                    document.getElementById('capacityChart').innerHTML = '<p>Error loading capacity chart</p>';
                }
            }
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = document.getElementById('autoRefreshBtn');
            
            if (autoRefresh) {
                btn.textContent = '⏸️ Pause Auto-refresh';
                startAutoRefresh();
            } else {
                btn.textContent = '▶️ Start Auto-refresh';
                clearInterval(refreshInterval);
            }
        }

        function startAutoRefresh() {
            refreshInterval = setInterval(refreshData, 30000); // 30 seconds
        }

        // Note: loadModel and unloadModel functions are provided by llm.js
        function loadLLMStatus() {
            fetch('/api/llm/status')
                .then(response => response.json())
                .then(data => {
                    const statusText = document.getElementById('llmStatusText');
                    if (data.available) {
                        statusText.innerHTML = `🤖 LLM Available - ${data.available_models} models found`;
                        loadLLMModels();
                    } else if (data.model_list && data.model_list.length > 0) {
                        // Models found but library not available
                        statusText.innerHTML = `⚠️ LLM Library Missing - ${data.model_list.length} models found (install llama-cpp-python, transformers, etc.)`;
                        loadLLMModels();
                    } else {
                        statusText.innerHTML = `❌ LLM Not Available - ${data.message || 'No models found'}`;
                        document.getElementById('modelSelect').innerHTML = '<option value="">LLM integration not available</option>';
                    }
                })
                .catch(error => {
                    console.error('Error loading LLM status:', error);
                    document.getElementById('llmStatusText').innerHTML = '❌ Error loading LLM status';
                });
        }

        function loadLLMModels() {
            fetch('/api/llm/models')
                .then(response => response.json())
                .then(models => {
                    updateModelGrid(models);
                })
                .catch(error => {
                    console.error('Error loading models:', error);
                    document.getElementById('modelSelect').innerHTML = '<option value="">Error loading models</option>';
                });
        }

        function updateModelGrid(models) {
            const select = document.getElementById('modelSelect');
            const modelInfo = document.getElementById('modelInfo');
            
            if (!models || models.length === 0) {
                select.innerHTML = '<option value="">No models available</option>';
                modelInfo.textContent = 'No models found in the configured directory';
                return;
            }

            // Check current loaded model
            fetch('/api/llm/status')
                .then(response => response.json())
                .then(status => {
                    const loadedModel = status.model_loaded;
                    
                    // Update select dropdown
                    select.innerHTML = '<option value="">Select a model...</option>' + 
                        models.map(model => {
                            const isLoaded = loadedModel && status.current_model === model.name;
                            const displayName = model.display_name || model.name;
                            const statusText = isLoaded ? ' (LOADED)' : '';
                            return `<option value="${model.name}" data-size="${model.size_mb}" data-format="${model.format}" data-path="${model.path}" ${isLoaded ? 'selected' : ''}>${displayName} - ${model.size_mb}MB${statusText}</option>`;
                        }).join('');
                    
                    // Update model info based on current selection
                    updateModelInfo();
                    
                    // Add event listener for selection changes
                    select.onchange = updateModelInfo;
                })
                .catch(error => {
                    console.error('Error checking model status:', error);
                    select.innerHTML = '<option value="">Error loading models</option>';
                });
        }
        
        function updateModelInfo() {
            const select = document.getElementById('modelSelect');
            const modelInfo = document.getElementById('modelInfo');
            const selectedOption = select.options[select.selectedIndex];
            
            if (!selectedOption || !selectedOption.value) {
                modelInfo.textContent = 'Select a model to see details';
                return;
            }
            
            const size = selectedOption.getAttribute('data-size');
            const format = selectedOption.getAttribute('data-format');
            const isLoaded = selectedOption.textContent.includes('(LOADED)');
            
            modelInfo.innerHTML = `Size: ${size} MB | Format: ${format.toUpperCase()}${isLoaded ? ' | <span style="color: var(--success-color);">Currently Loaded</span>' : ''}`;
        }

        // Load selected model from dropdown
        function loadSelectedModel() {
            const select = document.getElementById('modelSelect');
            const modelName = select.value;
            
            if (!modelName) {
                alert('Please select a model to load');
                return;
            }
            
            loadModel(modelName);
        }
        
        // Delete selected model from dropdown
        function deleteSelectedModel() {
            const select = document.getElementById('modelSelect');
            const selectedOption = select.options[select.selectedIndex];
            
            if (!selectedOption || !selectedOption.value) {
                alert('Please select a model to delete');
                return;
            }
            
            const modelName = selectedOption.value;
            const modelPath = selectedOption.getAttribute('data-path');
            
            deleteModel(modelPath, modelName);
        }
        
        // Note: loadModel and unloadModel functions are now provided by the enhanced llm.js module
        // which includes real-time progress feedback via Server-Sent Events

        function deleteModel(modelPath, modelName) {
            if (!confirm(`Are you sure you want to delete ${modelName}?\nThis action cannot be undone.`)) {
                return;
            }

            fetch('/api/llm/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model_path: modelPath})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`✅ ${data.message}`);
                    loadLLMModels(); // Refresh model grid
                } else {
                    alert(`❌ ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error deleting model:', error);
                alert('❌ Error deleting model');
            });
        }

        function showConfigModal() {
            // Load current configuration and available models
            Promise.all([
                fetch('/api/llm/config').then(r => r.json()),
                fetch('/api/llm/models').then(r => r.json())
            ])
            .then(([config, models]) => {
                document.getElementById('modelsPath').value = config.models_path || '';
                document.getElementById('maxTokens').value = config.max_tokens || 2048;
                document.getElementById('temperature').value = config.temperature || 0.7;
                document.getElementById('contextWindow').value = config.context_window || 4096;
                document.getElementById('enableGpu').value = config.enable_gpu ? 'true' : 'false';
                
                // Populate default model dropdown
                const defaultModelSelect = document.getElementById('defaultModel');
                defaultModelSelect.innerHTML = '<option value="">Select default model...</option>';
                
                if (models && models.length > 0) {
                    defaultModelSelect.innerHTML += models.map(model => {
                        const displayName = model.display_name || model.name;
                        const isSelected = config.default_model === model.name;
                        return `<option value="${model.name}" ${isSelected ? 'selected' : ''}>${displayName}</option>`;
                    }).join('');
                }
                
                document.getElementById('configModal').style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading config:', error);
                alert('❌ Error loading configuration');
            });
        }

        function saveConfig() {
            const config = {
                models_path: document.getElementById('modelsPath').value,
                default_model: document.getElementById('defaultModel').value,
                max_tokens: parseInt(document.getElementById('maxTokens').value),
                temperature: parseFloat(document.getElementById('temperature').value),
                context_window: parseInt(document.getElementById('contextWindow').value),
                enable_gpu: document.getElementById('enableGpu').value === 'true'
            };

            fetch('/api/llm/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`✅ ${data.message}`);
                    closeModal('configModal');
                    loadLLMStatus(); // Refresh models if path changed
                } else {
                    alert(`❌ ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error saving config:', error);
                alert('❌ Error saving configuration');
            });
        }

        function showUploadModal() {
            document.getElementById('uploadModal').style.display = 'block';
            document.getElementById('uploadProgress').style.display = 'none';
        }

        function uploadModel() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file to upload');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Show progress
            document.getElementById('uploadProgress').style.display = 'block';
            document.getElementById('uploadStatus').textContent = 'Uploading...';
            
            fetch('/api/llm/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('progressBar').style.width = '100%';
                    document.getElementById('uploadStatus').textContent = `✅ ${data.message}`;
                    setTimeout(() => {
                        closeModal('uploadModal');
                        loadLLMModels(); // Refresh model grid
                    }, 2000);
                } else {
                    document.getElementById('uploadStatus').textContent = `❌ ${data.message}`;
                }
            })
            .catch(error => {
                console.error('Error uploading model:', error);
                document.getElementById('uploadStatus').textContent = '❌ Upload failed';
            });
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }

        // Add drag and drop support for upload
        document.addEventListener('DOMContentLoaded', function() {
            const uploadArea = document.getElementById('uploadArea');
            
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    document.getElementById('fileInput').files = files;
                    uploadModel();
                }
            });
        });

        // Flyout modal functions
        function saveFlyoutConfig() {
            const config = {
                models_path: document.getElementById('flyout-models-path').value,
                default_model: document.getElementById('flyout-default-model').value,
                max_tokens: parseInt(document.getElementById('flyout-max-tokens').value),
                temperature: parseFloat(document.getElementById('flyout-temperature').value),
                context_window: parseInt(document.getElementById('flyout-context-window').value),
                enable_gpu: document.getElementById('flyout-enable-gpu').value === 'true'
            };

            fetch('/api/llm/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`✅ ${data.message}`);
                    loadLLMStatus(); // Refresh models if path changed
                } else {
                    alert(`❌ ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error saving config:', error);
                alert('❌ Error saving configuration');
            });
        }

        function uploadFlyoutModel() {
            const fileInput = document.getElementById('flyoutFileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file to upload');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Show progress
            document.getElementById('flyoutUploadProgress').style.display = 'block';
            document.getElementById('flyoutUploadStatus').textContent = 'Uploading...';
            
            fetch('/api/llm/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('flyoutProgressBar').style.width = '100%';
                    document.getElementById('flyoutUploadStatus').textContent = `✅ ${data.message}`;
                    setTimeout(() => {
                        loadLLMModels(); // Refresh model grid
                    }, 2000);
                } else {
                    document.getElementById('flyoutUploadStatus').textContent = `❌ ${data.message}`;
                }
            })
            .catch(error => {
                console.error('Error uploading model:', error);
                document.getElementById('flyoutUploadStatus').textContent = '❌ Upload failed';
            });
        }

        // Tab System Implementation
        function initTabSystem() {
            const tabLinks = document.querySelectorAll('.tab-nav-link');
            const tabPanes = document.querySelectorAll('.tab-pane');
            
            // Set first tab as active by default
            if (tabLinks.length > 0 && tabPanes.length > 0) {
                tabLinks[0].classList.add('active');
                tabPanes[0].classList.add('active');
            }
            
            // Add click event listeners to tab links
            tabLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // Remove active class from all tabs and panes
                    tabLinks.forEach(l => l.classList.remove('active'));
                    tabPanes.forEach(p => p.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    this.classList.add('active');
                    
                    // Show corresponding pane
                    const targetId = this.getAttribute('data-tab');
                    const targetPane = document.getElementById(targetId);
                    if (targetPane) {
                        targetPane.classList.add('active');
                    }
                });
            });
            
            // Handle flyout buttons
            const flyoutButtons = document.querySelectorAll('[data-flyout]');
            flyoutButtons.forEach(button => {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    const flyoutId = this.getAttribute('data-flyout');
                    const flyout = document.getElementById(flyoutId);
                    if (flyout) {
                        // Create backdrop if it doesn't exist
                        let backdrop = document.querySelector('.flyout-backdrop');
                        if (!backdrop) {
                            backdrop = document.createElement('div');
                            backdrop.className = 'flyout-backdrop';
                            document.body.appendChild(backdrop);
                        }
                        
                        // Show backdrop and flyout
                        backdrop.classList.add('show');
                        flyout.classList.add('show');
                        
                        // Add close event to backdrop
                        backdrop.onclick = () => closeFlyout();
                    }
                });
            });
            
            // Handle flyout close buttons
            document.querySelectorAll('.flyout-close').forEach(button => {
                button.addEventListener('click', closeFlyout);
            });
            
            // ESC key closes flyout
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    closeFlyout();
                }
            });
        }
        
        function closeFlyout() {
            document.querySelectorAll('.flyout-modal').forEach(flyout => {
                flyout.classList.remove('show');
            });
            const backdrop = document.querySelector('.flyout-backdrop');
            if (backdrop) {
                backdrop.classList.remove('show');
            }
        }
        
        // Initialize everything when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            initTabSystem();
        });
        
        // Initialize dashboard and LLM management
        refreshData();
        startAutoRefresh();
        loadLLMStatus();
    </script>
    
    <!-- Bootstrap JS (required for tab system) -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """

# =============================================================================
# Factory Functions
# =============================================================================

def create_enhanced_dashboard(config: DashboardConfig = None) -> EnhancedPerformanceDashboard:
    """Factory function to create Enhanced Performance Dashboard"""
    return EnhancedPerformanceDashboard(config)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point"""
    print("🚀 Enhanced MeshAdmin Performance Analytics Dashboard")
    print("=" * 60)
    
    # Check dependencies
    print("📋 Checking dependencies...")
    print(f"  Base Dashboard: {'✅' if DASHBOARD_AVAILABLE else '❌'}")
    print(f"  ML Integration: {'✅' if ML_INTEGRATION_AVAILABLE else '❌'}")
    print(f"  Flask Web UI: {'✅' if FLASK_AVAILABLE else '❌'}")
    print(f"  Plotly Charts: {'✅' if PLOTLY_AVAILABLE else '❌'}")
    
    if not any([DASHBOARD_AVAILABLE, ML_INTEGRATION_AVAILABLE, FLASK_AVAILABLE]):
        print("\n❌ Insufficient dependencies to run enhanced dashboard")
        print("Please install required components first")
        return
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8080))
    
    # Create and configure dashboard
    config = DashboardConfig(
        port=port,
        host="0.0.0.0",
        update_interval=30,
        ml_enabled=ML_INTEGRATION_AVAILABLE,
        auto_refresh=True
    )
    
    dashboard = create_enhanced_dashboard(config)
    
    print(f"\n🌐 Starting Enhanced Dashboard on http://{config.host}:{config.port}")
    print("Press Ctrl+C to stop")
    
    try:
        dashboard.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping Enhanced Dashboard...")
        dashboard.stop()
    except Exception as e:
        print(f"\n❌ Error running dashboard: {e}")
        dashboard.stop()

if __name__ == "__main__":
    main()

