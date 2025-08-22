#!/usr/bin/env python3
"""
MeshAdmin Performance Analytics Suite - Unified Startup Script
============================================================

This script starts the complete Performance Analytics Suite with unified MPTCP
kernel integration, including all applications and analytics engines.

Features:
- Unified MPTCP kernel integration
- All suite applications (Observability Dashboard, Network Flow Master, Load Balancer Pro)
- Advanced ML analytics engine
- Cross-application correlation analysis
- Real-time metrics collection and analysis
- Automatic application registration with MeshAdminPortal
"""

import sys
import os
import time
import logging
import threading
import signal
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

# Performance Analytics Suite Integration
try:
    from pathways_integration import PerformanceAnalyticsSuiteIntegration, start_integration, stop_integration
    PATHWAYS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Pathways integration not available: {e}")
    PATHWAYS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_analytics_suite.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("suite-startup")

class PerformanceAnalyticsSuiteManager:
    """
    Manager for the complete Performance Analytics Suite
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.running = False
        self.processes: Dict[str, subprocess.Popen] = {}
        self.integration: Optional[PerformanceAnalyticsSuiteIntegration] = None
        
        # Application configurations
        self.applications = {
            'observability-dashboard': {
                'name': 'Observability Dashboard',
                'path': 'apps/observability-dashboard',
                'script': 'app.py',
                'port': 5551,
                'env': {
                    'FLASK_ENV': 'production',
                    'FLASK_APP': 'app.py',
                    'PORT': '5551'
                }
            },
            'network-flow-master': {
                'name': 'Network Flow Master',
                'path': 'apps/network-flow-master',
                'script': 'app.py',
                'port': 5552,
                'env': {
                    'FLASK_ENV': 'production',
                    'FLASK_APP': 'app.py',
                    'PORT': '5552'
                }
            },
            'load-balancer-pro': {
                'name': 'Load Balancer Pro',
                'path': 'apps/load-balancer-pro',
                'script': 'app.py',
                'port': 5553,
                'env': {
                    'FLASK_ENV': 'production',
                    'FLASK_APP': 'app.py',
                    'PORT': '5553'
                }
            }
        }
        
        # Integration config
        self.integration_config = {
            'collection_interval': self.config.get('collection_interval', 15.0),
            'analytics_interval': self.config.get('analytics_interval', 30.0),
            'ml_update_interval': self.config.get('ml_update_interval', 300.0),
            'max_history': self.config.get('max_history', 2000),
            'portal_url': self.config.get('portal_url', 'http://localhost:3000'),
            'anomaly_sensitivity': self.config.get('anomaly_sensitivity', 0.8)
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self) -> bool:
        """Start the complete Performance Analytics Suite"""
        if self.running:
            logger.warning("Performance Analytics Suite already running")
            return True
        
        logger.info("🚀 Starting MeshAdmin Performance Analytics Suite...")
        logger.info("=" * 80)
        
        try:
            # 1. Start pathways integration first
            if not self._start_pathways_integration():
                logger.error("Failed to start pathways integration")
                return False
            
            # 2. Start individual applications
            if not self._start_applications():
                logger.error("Failed to start applications")
                self._stop_pathways_integration()
                return False
            
            # 3. Register applications with integration
            self._register_applications()
            
            # 4. Register suite with MeshAdminPortal
            self._register_with_portal()
            
            # 5. Start monitoring thread
            self._start_monitoring()
            
            self.running = True
            
            logger.info("✅ Performance Analytics Suite started successfully!")
            logger.info(f"🔗 Observability Dashboard: http://localhost:5551")
            logger.info(f"🌊 Network Flow Master: http://localhost:5552")
            logger.info(f"⚖️ Load Balancer Pro: http://localhost:5553")
            logger.info(f"📊 Unified Analytics: Available via API endpoints")
            
            if PATHWAYS_AVAILABLE and self.integration:
                logger.info(f"🔧 MPTCP Kernel Integration: {'Connected' if self.integration.kernel_interface.connected else 'Standalone'}")
            
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Performance Analytics Suite: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Stop the complete Performance Analytics Suite"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping MeshAdmin Performance Analytics Suite...")
        
        # Stop applications
        self._stop_applications()
        
        # Stop pathways integration
        self._stop_pathways_integration()
        
        self.running = False
        logger.info("✅ Performance Analytics Suite stopped")
    
    def status(self) -> Dict[str, Any]:
        """Get comprehensive status of the suite"""
        status = {
            'suite_running': self.running,
            'timestamp': time.time(),
            'applications': {},
            'pathways_integration': {
                'available': PATHWAYS_AVAILABLE,
                'running': False,
                'kernel_connected': False
            }
        }
        
        # Check application status
        for app_id, app_config in self.applications.items():
            process = self.processes.get(app_id)
            if process:
                status['applications'][app_id] = {
                    'name': app_config['name'],
                    'running': process.poll() is None,
                    'port': app_config['port'],
                    'pid': process.pid if process.poll() is None else None
                }
            else:
                status['applications'][app_id] = {
                    'name': app_config['name'],
                    'running': False,
                    'port': app_config['port'],
                    'pid': None
                }
        
        # Check pathways integration status
        if PATHWAYS_AVAILABLE and self.integration:
            status['pathways_integration'] = {
                'available': True,
                'running': self.integration.is_running,
                'kernel_connected': self.integration.kernel_interface.connected,
                'applications_registered': len(self.integration.registered_applications),
                'metrics_collected': len(self.integration.metrics_history)
            }
        
        return status
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics from the suite"""
        if not PATHWAYS_AVAILABLE or not self.integration:
            return {
                'error': 'Pathways integration not available',
                'timestamp': time.time()
            }
        
        try:
            return self.integration.get_comprehensive_metrics()
        except Exception as e:
            logger.error(f"Error getting comprehensive metrics: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _start_pathways_integration(self) -> bool:
        """Start the pathways integration"""
        if not PATHWAYS_AVAILABLE:
            logger.warning("⚠️ Pathways integration not available - running in standalone mode")
            return True
        
        try:
            logger.info("🔧 Starting pathways integration...")
            
            success = start_integration(self.integration_config)
            
            if success:
                from pathways_integration import get_integration
                self.integration = get_integration()
                logger.info("✅ Pathways integration started successfully")
                return True
            else:
                logger.error("❌ Failed to start pathways integration")
                return False
                
        except Exception as e:
            logger.error(f"Error starting pathways integration: {e}")
            return False
    
    def _stop_pathways_integration(self) -> None:
        """Stop the pathways integration"""
        if PATHWAYS_AVAILABLE:
            try:
                logger.info("🛑 Stopping pathways integration...")
                stop_integration()
                logger.info("✅ Pathways integration stopped")
            except Exception as e:
                logger.error(f"Error stopping pathways integration: {e}")
    
    def _start_applications(self) -> bool:
        """Start all suite applications"""
        logger.info("🚀 Starting suite applications...")
        
        for app_id, app_config in self.applications.items():
            if not self._start_application(app_id, app_config):
                logger.error(f"Failed to start {app_config['name']}")
                return False
        
        # Wait for applications to initialize
        logger.info("⏳ Waiting for applications to initialize...")
        time.sleep(5)
        
        return True
    
    def _start_application(self, app_id: str, app_config: Dict[str, Any]) -> bool:
        """Start a single application"""
        try:
            app_path = Path(app_config['path'])
            script_path = app_path / app_config['script']
            
            if not script_path.exists():
                logger.error(f"Application script not found: {script_path}")
                return False
            
            # Prepare environment
            env = os.environ.copy()
            env.update(app_config.get('env', {}))
            
            # Start process
            logger.info(f"🔄 Starting {app_config['name']} on port {app_config['port']}")
            
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(app_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes[app_id] = process
            
            # Quick health check
            time.sleep(2)
            if process.poll() is not None:
                logger.error(f"Application {app_config['name']} failed to start")
                return False
            
            logger.info(f"✅ {app_config['name']} started successfully (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Error starting {app_config['name']}: {e}")
            return False
    
    def _stop_applications(self) -> None:
        """Stop all suite applications"""
        logger.info("🛑 Stopping suite applications...")
        
        for app_id, process in self.processes.items():
            app_config = self.applications[app_id]
            
            try:
                if process.poll() is None:  # Process is running
                    logger.info(f"🛑 Stopping {app_config['name']}")
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                        logger.info(f"✅ {app_config['name']} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"⚠️ Force killing {app_config['name']}")
                        process.kill()
                        process.wait()
            
            except Exception as e:
                logger.error(f"Error stopping {app_config['name']}: {e}")
        
        self.processes.clear()
    
    def _register_applications(self) -> None:
        """Register applications with pathways integration"""
        if not PATHWAYS_AVAILABLE or not self.integration:
            return
        
        logger.info("📋 Registering applications with pathways integration...")
        
        for app_id, app_config in self.applications.items():
            try:
                registration_config = {
                    'port': app_config['port'],
                    'type': 'flask_app',
                    'metrics_endpoint': f"http://localhost:{app_config['port']}/api/analytics/status"
                }
                
                success = self.integration.register_application(app_id, registration_config)
                
                if success:
                    logger.info(f"✅ Registered {app_config['name']} with pathways integration")
                else:
                    logger.warning(f"⚠️ Failed to register {app_config['name']}")
                    
            except Exception as e:
                logger.error(f"Error registering {app_config['name']}: {e}")
    
    def _register_with_portal(self) -> None:
        """Register the suite with MeshAdminPortal"""
        try:
            import requests
            
            portal_url = self.integration_config.get('portal_url', 'http://localhost:3000')
            
            registration_data = {
                'name': 'Performance Analytics Suite',
                'status': 'running',
                'port': 5551,  # Main observability dashboard port
                'lastHealthCheck': time.time(),
                'metadata': {
                    'type': 'analytics_suite',
                    'applications': list(self.applications.keys()),
                    'pathways_integrated': PATHWAYS_AVAILABLE and self.integration is not None
                }
            }
            
            response = requests.post(
                f"{portal_url}/api/mptcp/applications/register",
                json=registration_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Registered Performance Analytics Suite with MeshAdminPortal")
            else:
                logger.warning(f"⚠️ Failed to register with MeshAdminPortal: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Could not register with MeshAdminPortal: {e}")
    
    def _start_monitoring(self) -> None:
        """Start monitoring thread for application health"""
        def monitor():
            while self.running:
                try:
                    # Check application health
                    for app_id, process in self.processes.items():
                        if process.poll() is not None:  # Process has stopped
                            app_config = self.applications[app_id]
                            logger.warning(f"⚠️ {app_config['name']} has stopped unexpectedly")
                    
                    # Sleep for monitoring interval
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in monitoring thread: {e}")
                    time.sleep(60)  # Wait longer on errors
        
        monitoring_thread = threading.Thread(target=monitor, daemon=True)
        monitoring_thread.start()
        logger.info("✅ Application monitoring started")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point"""
    print("🚀 MeshAdmin Performance Analytics Suite")
    print("=" * 80)
    print("Advanced MPTCP Performance Analytics with Unified Kernel Integration")
    print("=" * 80)
    
    # Configuration
    config = {
        'collection_interval': 15.0,  # 15 seconds
        'analytics_interval': 30.0,   # 30 seconds
        'ml_update_interval': 300.0,  # 5 minutes
        'max_history': 2000,
        'portal_url': os.getenv('MESHADMIN_PORTAL_URL', 'http://localhost:3000'),
        'anomaly_sensitivity': 0.8
    }
    
    # Create and start suite manager
    suite_manager = PerformanceAnalyticsSuiteManager(config)
    
    if suite_manager.start():
        try:
            # Keep running until interrupted
            while suite_manager.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            suite_manager.stop()
    else:
        logger.error("Failed to start Performance Analytics Suite")
        sys.exit(1)

if __name__ == "__main__":
    main() 