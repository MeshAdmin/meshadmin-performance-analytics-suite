#!/usr/bin/env python3
"""
Run tests for the FlowVision application.
"""
import unittest
import os
import sys
from tests import FlowVisionTestCase
import test_ai_insights
import test_flow_processing
import test_mib_parser

if __name__ == '__main__':
    # Create a test suite
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite([
        # Main application tests
        loader.loadTestsFromTestCase(FlowVisionTestCase),
        
        # AI insights tests
        loader.loadTestsFromModule(test_ai_insights),
        
        # Flow processing tests
        loader.loadTestsFromModule(test_flow_processing),
        
        # MIB parser tests
        loader.loadTestsFromModule(test_mib_parser)
    ])
    
    # Run the tests and capture the result
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Exit with a non-zero status if tests failed
    sys.exit(not result.wasSuccessful())