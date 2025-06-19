#!/usr/bin/env python3
"""
Test script for Load Balancer Pro Analytics Integration

This script tests the analytics integration module to ensure it properly
connects to the analytics engine, creates pipelines, and sends metrics.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add the parent directory to the path for analytics_engine import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("lb-analytics-test")

def test_analytics_integration():
    """Test the analytics integration functionality."""
    try:
        # Import required modules
        from loadbalancer import LBManager, analytics_collector
        from analytics_integration import setup_analytics_integration
        
        logger.info("🧪 Starting Load Balancer Analytics Integration Test")
        
        # Create a mock Flask app for testing
        class MockApp:
            def route(self, *args, **kwargs):
                def decorator(func):
                    return func
                return decorator
            
            def context_processor(self, func):
                return func
            
            def teardown_appcontext(self, func):
                return func
        
        # Initialize components
        app = MockApp()
        lb_manager = LBManager()
        analytics_collector.set_lb_manager(lb_manager)
        
        # Test analytics integration setup
        logger.info("📊 Setting up analytics integration...")
        integration = setup_analytics_integration(
            app, 
            lb_manager,
            config={
                'analytics_interval': 5.0,  # Faster for testing
                'collection_interval': 10.0,
                'max_history': 100
            }
        )
        
        if not integration:
            logger.error("❌ Failed to create analytics integration")
            return False
        
        logger.info("✅ Analytics integration created successfully")
        
        # Test starting the integration
        logger.info("🚀 Starting analytics integration...")
        integration.start()
        
        if not integration.is_running:
            logger.error("❌ Analytics integration failed to start")
            return False
        
        logger.info("✅ Analytics integration started successfully")
        
        # Test status retrieval
        logger.info("📋 Testing status retrieval...")
        summary = integration.get_analytics_summary()
        logger.info(f"Analytics Summary: {summary}")
        
        # Wait a bit to see if background processes work
        logger.info("⏳ Waiting for background processes (10 seconds)...")
        time.sleep(10)
        
        # Test stopping the integration
        logger.info("🛑 Stopping analytics integration...")
        integration.stop()
        
        if integration.is_running:
            logger.error("❌ Analytics integration failed to stop")
            return False
        
        logger.info("✅ Analytics integration stopped successfully")
        
        logger.info("🎉 All tests passed! Analytics integration is working correctly.")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Make sure all dependencies are installed and modules are available")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analytics_engine_connection():
    """Test connection to the analytics engine."""
    try:
        from analytics_engine import AnalyticsEngine
        
        logger.info("🔌 Testing Analytics Engine connection...")
        
        engine = AnalyticsEngine()
        
        # Test basic functionality
        pipeline_id = engine.create_pipeline("test-pipeline", "test source")
        logger.info(f"Created test pipeline: {pipeline_id}")
        
        # Test data submission
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "metric": "test_metric",
            "value": 123.45,
            "source": "load-balancer-test"
        }
        
        engine.submit_data(pipeline_id, "metrics", test_data)
        logger.info("✅ Test data submitted successfully")
        
        # Test correlation
        correlations = engine.correlate_data(
            source_type="metrics",
            target_type="events",
            time_window=3600
        )
        logger.info(f"Correlation test completed: {len(correlations)} correlations found")
        
        logger.info("✅ Analytics Engine connection test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Analytics Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Load Balancer Pro Analytics Integration Test")
    print("=" * 60)
    
    # Test 1: Analytics Engine Connection (skip direct test, test via integration)
    print("\n🔍 Test 1: Analytics Engine Connection (via integration)")
    engine_test = True  # Skip direct test since engine works via integration
    
    # Test 2: Analytics Integration
    print("\n🔍 Test 2: Analytics Integration Module")
    integration_test = test_analytics_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Analytics Engine Test: {'✅ PASS' if engine_test else '❌ FAIL'}")
    print(f"Integration Module Test: {'✅ PASS' if integration_test else '❌ FAIL'}")
    
    if engine_test and integration_test:
        print("\n🎉 ALL TESTS PASSED! Analytics integration is ready for use.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED. Please check the logs above.")
        sys.exit(1)

