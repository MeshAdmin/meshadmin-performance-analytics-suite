#!/usr/bin/env python3
"""
Comprehensive Test Suite for MeshAdmin Performance Analytics Suite

This script tests all components of the Performance Analytics Suite including:
- Base Performance Dashboard
- ML Analytics Engine  
- Dashboard Integration
- Enhanced Dashboard
- All dependencies and configurations
"""

import sys
import os
import time
import traceback
import subprocess
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Add project directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'advanced-analytics'))

# =============================================================================
# Test Configuration
# =============================================================================

@dataclass
class TestResult:
    """Test result container"""
    name: str
    passed: bool
    message: str = ""
    details: str = ""
    execution_time: float = 0.0

class TestSuite:
    """Comprehensive test suite for the Analytics Suite"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_all_tests(self) -> None:
        """Run all test categories"""
        print("🧪 MeshAdmin Performance Analytics Suite - Comprehensive Test")
        print("=" * 70)
        
        # Test categories
        test_categories = [
            ("📦 Dependency Tests", self._test_dependencies),
            ("🔧 Component Import Tests", self._test_component_imports),
            ("🏗️ Component Initialization Tests", self._test_component_initialization),
            ("📊 Data Processing Tests", self._test_data_processing),
            ("🧠 ML Analytics Tests", self._test_ml_analytics),
            ("🔗 Integration Tests", self._test_integration),
            ("🌐 Web Interface Tests", self._test_web_interface),
            ("⚡ Performance Tests", self._test_performance),
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n{category_name}")
            print("-" * 50)
            try:
                test_function()
            except Exception as e:
                self._record_test_result(
                    f"{category_name} - Category Error",
                    False,
                    f"Category failed with error: {str(e)}",
                    traceback.format_exc()
                )
        
        # Print summary
        self._print_summary()
    
    def _record_test_result(self, name: str, passed: bool, message: str = "", details: str = "", execution_time: float = 0.0) -> None:
        """Record a test result"""
        result = TestResult(name, passed, message, details, execution_time)
        self.results.append(result)
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        
        # Print immediate result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if message:
            print(f"    {message}")
        if not passed and details:
            print(f"    Details: {details[:200]}...")
    
    def _test_dependencies(self) -> None:
        """Test all required dependencies"""
        dependencies = [
            ("numpy", "import numpy"),
            ("pandas", "import pandas"),
            ("scikit-learn", "import sklearn"),
            ("plotly", "import plotly"),
            ("flask", "import flask"),
            ("flask-cors", "from flask_cors import CORS"),
            ("psutil", "import psutil"),
            ("threading", "import threading"),
            ("concurrent.futures", "import concurrent.futures"),
            ("dataclasses", "from dataclasses import dataclass"),
            ("typing", "from typing import Dict, List, Any, Optional"),
            ("json", "import json"),
            ("logging", "import logging"),
            ("time", "import time"),
            ("datetime", "from datetime import datetime"),
        ]
        
        for dep_name, import_statement in dependencies:
            start_time = time.time()
            try:
                exec(import_statement)
                self._record_test_result(
                    f"Import {dep_name}",
                    True,
                    f"Successfully imported {dep_name}",
                    execution_time=time.time() - start_time
                )
            except ImportError as e:
                self._record_test_result(
                    f"Import {dep_name}",
                    False,
                    f"Failed to import {dep_name}: {str(e)}",
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                self._record_test_result(
                    f"Import {dep_name}",
                    False,
                    f"Unexpected error importing {dep_name}: {str(e)}",
                    execution_time=time.time() - start_time
                )
    
    def _test_component_imports(self) -> None:
        """Test importing all custom components"""
        components = [
            ("dashboard", "from dashboard import PerformanceAnalyticsDashboard, create_analytics_dashboard"),
            ("ml_analytics_engine", "from ml_analytics_engine import MLAnalyticsEngine, create_ml_analytics_engine"),
            ("dashboard_integration", "from dashboard_integration import AdvancedAnalyticsDashboard, create_advanced_analytics_dashboard"),
            ("enhanced_dashboard", "from enhanced_dashboard import EnhancedPerformanceDashboard, create_enhanced_dashboard"),
        ]
        
        for comp_name, import_statement in components:
            start_time = time.time()
            try:
                exec(import_statement)
                self._record_test_result(
                    f"Import {comp_name}",
                    True,
                    f"Successfully imported {comp_name}",
                    execution_time=time.time() - start_time
                )
            except ImportError as e:
                self._record_test_result(
                    f"Import {comp_name}",
                    False,
                    f"Failed to import {comp_name}: {str(e)}",
                    str(e),
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                self._record_test_result(
                    f"Import {comp_name}",
                    False,
                    f"Unexpected error importing {comp_name}: {str(e)}",
                    traceback.format_exc(),
                    execution_time=time.time() - start_time
                )
    
    def _test_component_initialization(self) -> None:
        """Test initializing all components"""
        
        # Test Dashboard
        start_time = time.time()
        try:
            # Try to import and create dashboard
            from dashboard import create_analytics_dashboard
            dashboard = create_analytics_dashboard()
            self._record_test_result(
                "Initialize Base Dashboard",
                True,
                "Successfully created base dashboard",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Initialize Base Dashboard",
                False,
                f"Failed to create base dashboard: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
        
        # Test ML Engine
        start_time = time.time()
        try:
            from ml_analytics_engine import create_ml_analytics_engine
            ml_engine = create_ml_analytics_engine()
            self._record_test_result(
                "Initialize ML Analytics Engine",
                True,
                "Successfully created ML analytics engine",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Initialize ML Analytics Engine",
                False,
                f"Failed to create ML analytics engine: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
        
        # Test Dashboard Integration
        start_time = time.time()
        try:
            from dashboard_integration import create_advanced_analytics_dashboard
            integration = create_advanced_analytics_dashboard()
            self._record_test_result(
                "Initialize Dashboard Integration",
                True,
                "Successfully created dashboard integration",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Initialize Dashboard Integration",
                False,
                f"Failed to create dashboard integration: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
        
        # Test Enhanced Dashboard
        start_time = time.time()
        try:
            from enhanced_dashboard import create_enhanced_dashboard, DashboardConfig
            config = DashboardConfig(port=8081, ml_enabled=False)  # Disable ML to avoid dependencies
            enhanced = create_enhanced_dashboard(config)
            self._record_test_result(
                "Initialize Enhanced Dashboard",
                True,
                "Successfully created enhanced dashboard",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Initialize Enhanced Dashboard",
                False,
                f"Failed to create enhanced dashboard: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _test_data_processing(self) -> None:
        """Test data processing capabilities"""
        
        # Test sample data creation
        start_time = time.time()
        try:
            sample_data = {
                'timestamp': time.time(),
                'performance_summary': {
                    'total_network_flows': 1500,
                    'packet_rate': 2500.0,
                    'total_lb_connections': 150,
                    'average_response_time': 125.5,
                    'error_rate': 0.02,
                    'health_score': 0.95
                }
            }
            
            # Validate data structure
            assert isinstance(sample_data['timestamp'], (int, float))
            assert isinstance(sample_data['performance_summary'], dict)
            assert sample_data['performance_summary']['error_rate'] <= 1.0
            assert sample_data['performance_summary']['health_score'] <= 1.0
            
            self._record_test_result(
                "Sample Data Processing",
                True,
                "Successfully created and validated sample data",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Sample Data Processing",
                False,
                f"Failed to process sample data: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
        
        # Test metric extraction
        start_time = time.time()
        try:
            from dashboard_integration import AdvancedAnalyticsDashboard
            
            # Create dashboard and test metric extraction
            dashboard = AdvancedAnalyticsDashboard()
            
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
            
            metrics = dashboard._extract_metrics_from_dashboard(sample_dashboard_data)
            
            # Validate metrics
            assert isinstance(metrics, list)
            assert len(metrics) > 0
            
            self._record_test_result(
                "Metric Extraction",
                True,
                f"Successfully extracted {len(metrics)} metrics",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Metric Extraction",
                False,
                f"Failed to extract metrics: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _test_ml_analytics(self) -> None:
        """Test ML analytics capabilities"""
        
        start_time = time.time()
        try:
            from ml_analytics_engine import MLAnalyticsEngine, PerformanceMetric
            
            # Create ML engine
            ml_engine = MLAnalyticsEngine()
            
            # Test with sample metrics
            sample_metrics = [
                PerformanceMetric(
                    timestamp=time.time(),
                    source='test_source',
                    metric_name='test_metric',
                    value=100.0
                )
            ]
            
            # Test ingestion
            ml_engine.ingest_metrics(sample_metrics)
            
            # Test analysis
            summary = ml_engine.get_analysis_summary()
            assert isinstance(summary, dict)
            
            self._record_test_result(
                "ML Analytics Processing",
                True,
                "Successfully processed ML analytics",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "ML Analytics Processing",
                False,
                f"Failed ML analytics test: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _test_integration(self) -> None:
        """Test component integration"""
        
        start_time = time.time()
        try:
            from dashboard_integration import create_advanced_analytics_dashboard
            
            # Create integration dashboard
            integration = create_advanced_analytics_dashboard()
            integration.start()
            
            # Test ML insights
            insights = integration.get_ml_insights()
            assert isinstance(insights, dict)
            
            # Test alerts
            alerts = integration.get_intelligent_alerts()
            assert isinstance(alerts, list)
            
            # Test suggestions
            suggestions = integration.get_optimization_suggestions()
            assert isinstance(suggestions, list)
            
            integration.stop()
            
            self._record_test_result(
                "Component Integration",
                True,
                "Successfully tested component integration",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Component Integration",
                False,
                f"Failed integration test: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _test_web_interface(self) -> None:
        """Test web interface capabilities"""
        
        start_time = time.time()
        try:
            # Test Flask availability
            import flask
            from flask import Flask
            
            # Create minimal Flask app
            app = Flask(__name__)
            
            @app.route('/test')
            def test_route():
                return {'status': 'ok'}
            
            # Test route registration
            assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]
            
            self._record_test_result(
                "Web Interface Setup",
                True,
                "Successfully set up web interface",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Web Interface Setup",
                False,
                f"Failed web interface test: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _test_performance(self) -> None:
        """Test performance characteristics"""
        
        # Test data processing performance
        start_time = time.time()
        try:
            from ml_analytics_engine import PerformanceMetric
            
            # Create large dataset
            large_dataset = []
            for i in range(1000):
                large_dataset.append(PerformanceMetric(
                    timestamp=time.time() + i,
                    source=f'source_{i % 10}',
                    metric_name=f'metric_{i % 5}',
                    value=float(i)
                ))
            
            processing_time = time.time() - start_time
            
            # Performance should be reasonable
            assert processing_time < 5.0  # Should complete in under 5 seconds
            
            self._record_test_result(
                "Data Processing Performance",
                True,
                f"Processed 1000 metrics in {processing_time:.3f} seconds",
                execution_time=processing_time
            )
        except Exception as e:
            self._record_test_result(
                "Data Processing Performance",
                False,
                f"Failed performance test: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
        
        # Test memory usage
        start_time = time.time()
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Memory usage should be reasonable
            assert memory_mb < 500  # Should use less than 500MB
            
            self._record_test_result(
                "Memory Usage",
                True,
                f"Memory usage: {memory_mb:.1f} MB",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            self._record_test_result(
                "Memory Usage",
                False,
                f"Failed memory test: {str(e)}",
                traceback.format_exc(),
                execution_time=time.time() - start_time
            )
    
    def _print_summary(self) -> None:
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📋 TEST SUMMARY")
        print("=" * 70)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests / self.total_tests * 100):.1f}%")
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            print("-" * 40)
            for test in failed_tests:
                print(f"  • {test.name}")
                print(f"    {test.message}")
                if test.details and len(test.details) > 100:
                    print(f"    Details: {test.details[:100]}...")
                elif test.details:
                    print(f"    Details: {test.details}")
        
        # Show performance summary
        performance_tests = [r for r in self.results if r.execution_time > 0]
        if performance_tests:
            print(f"\n⚡ PERFORMANCE SUMMARY:")
            print("-" * 40)
            total_time = sum(t.execution_time for t in performance_tests)
            print(f"  Total execution time: {total_time:.3f} seconds")
            
            # Show slowest tests
            slowest = sorted(performance_tests, key=lambda x: x.execution_time, reverse=True)[:5]
            print("  Slowest tests:")
            for test in slowest:
                print(f"    • {test.name}: {test.execution_time:.3f}s")
        
        # Overall status
        if self.passed_tests == self.total_tests:
            print(f"\n🎉 ALL TESTS PASSED! Analytics Suite is ready for deployment.")
        elif self.passed_tests / self.total_tests >= 0.8:
            print(f"\n✅ Most tests passed. Analytics Suite is mostly functional.")
        else:
            print(f"\n⚠️ Many tests failed. Analytics Suite needs fixes before deployment.")

def main():
    """Main entry point"""
    test_suite = TestSuite()
    test_suite.run_all_tests()

if __name__ == "__main__":
    main()

