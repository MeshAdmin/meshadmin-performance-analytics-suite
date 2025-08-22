#!/usr/bin/env python3
"""
Observability Dashboard - Unified MPTCP Kernel API Routes
========================================================

This module provides Flask API routes for accessing unified MPTCP kernel
metrics and analytics through the Performance Analytics Suite integration.
"""

import sys
import os
import time
import logging
from flask import Flask, jsonify, request
from typing import Dict, Any, Optional

# Add pathways integration to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from pathways_integration import get_integration, PerformanceAnalyticsSuiteIntegration
    PATHWAYS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Pathways integration not available: {e}")
    PATHWAYS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ObservabilityPathwaysAPI:
    """
    API interface for accessing unified MPTCP kernel data through observability dashboard
    """
    
    def __init__(self, app: Flask, integration: Optional[PerformanceAnalyticsSuiteIntegration] = None):
        self.app = app
        self.integration = integration or (get_integration() if PATHWAYS_AVAILABLE else None)
        self.setup_routes()
    
    def setup_routes(self) -> None:
        """Setup API routes for pathways integration"""
        
        @self.app.route('/api/pathways/status')
        def pathways_status():
            """Get pathways integration status"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'available': False,
                        'message': 'Pathways integration not available'
                    }), 503
                
                status = {
                    'success': True,
                    'available': True,
                    'running': self.integration.is_running,
                    'kernel_connected': self.integration.kernel_interface.connected,
                    'applications_registered': len(self.integration.registered_applications),
                    'metrics_collected': len(self.integration.metrics_history),
                    'last_updated': time.time()
                }
                
                return jsonify(status)
                
            except Exception as e:
                logger.error(f"Error getting pathways status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/metrics/comprehensive')
        def comprehensive_metrics():
            """Get comprehensive MPTCP metrics from unified kernel"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                metrics = self.integration.get_comprehensive_metrics()
                
                return jsonify({
                    'success': True,
                    'data': metrics,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting comprehensive metrics: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/dashboard')
        def dashboard_data():
            """Get optimized dashboard data"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                dashboard_data = self.integration.get_performance_dashboard_data()
                
                return jsonify({
                    'success': True,
                    'data': dashboard_data,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting dashboard data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/optimization', methods=['POST'])
        def trigger_optimization():
            """Trigger comprehensive optimization analysis"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                optimization_result = self.integration.trigger_optimization_analysis()
                
                return jsonify({
                    'success': True,
                    'data': optimization_result,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error triggering optimization: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/kernel/overview')
        def kernel_overview():
            """Get unified MPTCP kernel overview"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                overview = self.integration.kernel_interface.get_system_overview()
                
                return jsonify({
                    'success': True,
                    'data': overview,
                    'connected': self.integration.kernel_interface.connected,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting kernel overview: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/kernel/connections')
        def kernel_connections():
            """Get MPTCP connection metrics from kernel"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                connections = self.integration.kernel_interface.get_connection_metrics()
                
                return jsonify({
                    'success': True,
                    'data': connections,
                    'connected': self.integration.kernel_interface.connected,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting kernel connections: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/kernel/paths')
        def kernel_paths():
            """Get MPTCP path statistics from kernel"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                paths = self.integration.kernel_interface.get_path_statistics()
                
                return jsonify({
                    'success': True,
                    'data': paths,
                    'connected': self.integration.kernel_interface.connected,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting kernel paths: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/analytics/summary')
        def analytics_summary():
            """Get analytics engine summary"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                summary = self.integration._get_analytics_summary()
                
                return jsonify({
                    'success': True,
                    'data': summary,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting analytics summary: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/ml/insights')
        def ml_insights():
            """Get ML-driven insights"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                insights = self.integration._get_ml_insights()
                
                return jsonify({
                    'success': True,
                    'data': insights,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting ML insights: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/applications')
        def registered_applications():
            """Get registered applications status"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                apps_status = self.integration._get_application_status_summary()
                
                return jsonify({
                    'success': True,
                    'data': apps_status,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error getting applications status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/applications/register', methods=['POST'])
        def register_application():
            """Register a new application for monitoring"""
            try:
                if not self.integration:
                    return jsonify({
                        'success': False,
                        'error': 'Pathways integration not available'
                    }), 503
                
                data = request.get_json()
                if not data or 'name' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Application name required'
                    }), 400
                
                app_name = data['name']
                app_config = data.get('config', {})
                
                success = self.integration.register_application(app_name, app_config)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Application {app_name} registered successfully',
                        'timestamp': time.time()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to register application {app_name}'
                    }), 500
                
            except Exception as e:
                logger.error(f"Error registering application: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/metrics/stream')
        def metrics_stream():
            """Stream real-time metrics (Server-Sent Events)"""
            try:
                if not self.integration:
                    return "data: {\"error\": \"Pathways integration not available\"}\n\n", 503
                
                def generate():
                    while True:
                        try:
                            # Get latest metrics
                            metrics = self.integration.get_comprehensive_metrics()
                            dashboard_data = self.integration.get_performance_dashboard_data()
                            
                            # Combine data
                            stream_data = {
                                'type': 'metrics_update',
                                'timestamp': time.time(),
                                'metrics': metrics,
                                'dashboard': dashboard_data
                            }
                            
                            yield f"data: {jsonify(stream_data).get_data(as_text=True)}\n\n"
                            time.sleep(5)  # Update every 5 seconds
                            
                        except Exception as e:
                            logger.error(f"Error in metrics stream: {e}")
                            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                            time.sleep(10)  # Wait longer on errors
                
                return self.app.response_class(
                    generate(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*'
                    }
                )
                
            except Exception as e:
                logger.error(f"Error setting up metrics stream: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pathways/health')
        def health_check():
            """Health check endpoint"""
            try:
                health_status = {
                    'service': 'observability-dashboard-pathways-api',
                    'status': 'healthy',
                    'timestamp': time.time(),
                    'pathways_available': PATHWAYS_AVAILABLE,
                    'integration_running': self.integration.is_running if self.integration else False,
                    'kernel_connected': self.integration.kernel_interface.connected if self.integration else False,
                    'version': '1.0.0'
                }
                
                # Determine overall health
                if not PATHWAYS_AVAILABLE or not self.integration:
                    health_status['status'] = 'degraded'
                elif not self.integration.is_running:
                    health_status['status'] = 'warning'
                elif not self.integration.kernel_interface.connected:
                    health_status['status'] = 'warning'
                
                status_code = 200 if health_status['status'] == 'healthy' else 503
                
                return jsonify(health_status), status_code
                
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                return jsonify({
                    'service': 'observability-dashboard-pathways-api',
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }), 500

def setup_pathways_routes(app: Flask, integration: Optional[PerformanceAnalyticsSuiteIntegration] = None) -> ObservabilityPathwaysAPI:
    """
    Setup pathways API routes for Flask application
    
    Args:
        app: Flask application instance
        integration: Optional pathways integration instance
    
    Returns:
        ObservabilityPathwaysAPI instance
    """
    
    api = ObservabilityPathwaysAPI(app, integration)
    
    # Add CORS headers for API routes
    @app.after_request
    def after_request(response):
        if request.path.startswith('/api/pathways/'):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    logger.info("✅ Pathways API routes setup complete")
    return api

if __name__ == "__main__":
    # Test the API routes
    app = Flask(__name__)
    
    # Setup routes
    setup_pathways_routes(app)
    
    print("🧪 Testing Pathways API routes...")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('pathways'):
            print(f"  {rule.methods} {rule.rule}")
    
    # Run test server
    app.run(debug=False, port=5555) 