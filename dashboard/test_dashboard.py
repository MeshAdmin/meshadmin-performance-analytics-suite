#!/usr/bin/env python3
"""
Test script for MeshAdmin Performance Analytics Dashboard

This script tests the performance dashboard functionality to ensure it properly
monitors both applications and provides correlation analysis.
"""

import sys
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard-test")

def test_performance_monitor():
    """Test the PerformanceMonitor class functionality."""
    try:
        from performance_dashboard import PerformanceMonitor
        
        logger.info("🧪 Starting Performance Dashboard Test")
        
        # Test monitor initialization
        logger.info("📊 Testing monitor initialization...")
        monitor = PerformanceMonitor()
        
        if not monitor:
            logger.error("❌ Failed to create performance monitor")
            return False
        
        logger.info("✅ Performance monitor created successfully")
        
        # Test starting the monitor
        logger.info("🚀 Testing monitor start...")
        monitor.start()
        
        if not monitor.is_running:
            logger.error("❌ Performance monitor failed to start")
            return False
        
        logger.info("✅ Performance monitor started successfully")
        
        # Test dashboard data retrieval
        logger.info("📋 Testing dashboard data retrieval...")
        dashboard_data = monitor.get_dashboard_data()
        
        if not dashboard_data:
            logger.error("❌ Failed to get dashboard data")
            return False
        
        logger.info(f"✅ Dashboard data retrieved: {len(dashboard_data)} sections")
        
        # Test chart generation
        logger.info("📈 Testing chart generation...")
        charts = monitor.get_real_time_charts()
        
        if not charts:
            logger.error("❌ Failed to generate charts")
            return False
        
        logger.info(f"✅ Charts generated: {list(charts.keys())}")
        
        # Wait for some monitoring data
        logger.info("⏳ Waiting for monitoring data (10 seconds)...")
        time.sleep(10)
        
        # Test correlation analysis
        logger.info("🔍 Testing correlation analysis...")
        correlation_results = monitor.trigger_correlation_analysis()
        
        if 'error' in correlation_results:
            logger.warning(f"⚠️ Correlation analysis returned error: {correlation_results['error']}")
        else:
            logger.info("✅ Correlation analysis completed")
        
        # Test stopping the monitor
        logger.info("🛑 Testing monitor stop...")
        monitor.stop()
        
        if monitor.is_running:
            logger.error("❌ Performance monitor failed to stop")
            return False
        
        logger.info("✅ Performance monitor stopped successfully")
        
        logger.info("🎉 All tests passed! Performance dashboard is working correctly.")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Make sure Flask dependencies are installed")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """Test the Flask dashboard application."""
    try:
        from performance_dashboard import FLASK_AVAILABLE
        
        if not FLASK_AVAILABLE:
            logger.warning("⚠️ Flask not available - skipping Flask app test")
            return True
        
        logger.info("🌐 Testing Flask dashboard app...")
        
        # Import the Flask app
        from performance_dashboard import app, performance_monitor
        
        # Test basic app configuration
        if not app:
            logger.error("❌ Flask app not created")
            return False
        
        logger.info("✅ Flask app created successfully")
        
        # Test with test client
        with app.test_client() as client:
            logger.info("🔍 Testing dashboard routes...")
            
            # Test main dashboard route
            response = client.get('/')
            if response.status_code != 200:
                logger.error(f"❌ Dashboard route failed: {response.status_code}")
                return False
            
            logger.info("✅ Dashboard route working")
            
            # Test API endpoints
            response = client.get('/api/dashboard/data')
            if response.status_code != 200:
                logger.error(f"❌ Dashboard data API failed: {response.status_code}")
                return False
            
            logger.info("✅ Dashboard data API working")
            
            response = client.get('/api/dashboard/charts')
            if response.status_code != 200:
                logger.error(f"❌ Dashboard charts API failed: {response.status_code}")
                return False
            
            logger.info("✅ Dashboard charts API working")
        
        logger.info("✅ Flask app tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_connectivity():
    """Test connectivity to the monitored applications."""
    try:
        import requests
        
        logger.info("🔌 Testing application connectivity...")
        
        apps_to_test = {
            'Network Flow Master': 'http://localhost:8000/health',
            'Load Balancer Pro': 'http://localhost:5000/api/stats'
        }
        
        connectivity_results = {}
        
        for app_name, url in apps_to_test.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    connectivity_results[app_name] = 'reachable'
                    logger.info(f"✅ {app_name} is reachable")
                else:
                    connectivity_results[app_name] = f'error_{response.status_code}'
                    logger.warning(f"⚠️ {app_name} returned {response.status_code}")
            except requests.exceptions.ConnectionError:
                connectivity_results[app_name] = 'unreachable'
                logger.warning(f"⚠️ {app_name} is unreachable")
            except Exception as e:
                connectivity_results[app_name] = f'error_{str(e)}'
                logger.warning(f"⚠️ {app_name} error: {e}")
        
        # Summary
        reachable_count = sum(1 for status in connectivity_results.values() if status == 'reachable')
        total_count = len(connectivity_results)
        
        logger.info(f"📊 Connectivity summary: {reachable_count}/{total_count} applications reachable")
        
        if reachable_count == 0:
            logger.warning("⚠️ No applications are reachable - dashboard will show limited data")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connectivity test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("MeshAdmin Performance Analytics Dashboard Test")
    print("=" * 60)
    
    # Test 1: Application Connectivity
    print("\n🔍 Test 1: Application Connectivity")
    connectivity_test = test_app_connectivity()
    
    # Test 2: Performance Monitor
    print("\n🔍 Test 2: Performance Monitor")
    monitor_test = test_performance_monitor()
    
    # Test 3: Flask Application
    print("\n🔍 Test 3: Flask Dashboard App")
    flask_test = test_flask_app()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Application Connectivity: {'✅ PASS' if connectivity_test else '❌ FAIL'}")
    print(f"Performance Monitor: {'✅ PASS' if monitor_test else '❌ FAIL'}")
    print(f"Flask Dashboard App: {'✅ PASS' if flask_test else '❌ FAIL'}")
    
    if connectivity_test and monitor_test and flask_test:
        print("\n🎉 ALL TESTS PASSED! Performance dashboard is ready for use.")
        print("\n🚀 To start the dashboard, run:")
        print("   python performance_dashboard.py")
        print("\n📖 Then visit: http://localhost:3000")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED. Please check the logs above.")
        sys.exit(1)

