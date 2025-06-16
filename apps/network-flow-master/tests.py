import unittest
import os
import tempfile
import json
import struct
from datetime import datetime, timedelta
from database import db
from flask import Flask

# Create a test app instance to avoid circular imports
def create_test_app():
    """Create a test Flask app with minimal configuration"""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.secret_key = 'test_secret_key'
    
    # Initialize database
    db.init_app(test_app)
    
    return test_app

class FlowVisionTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a new test environment before each test."""
        self.app = create_test_app()
        self.client = self.app.test_client()
        
        # Create the database and tables
        with self.app.app_context():
            # Import models here to avoid circular imports
            from models import User, Role, Device, FlowData, ForwardTarget, FlowTemplate
            
            db.create_all()
            self._create_test_data()
    
    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_test_data(self):
        """Create test data for the database."""
        from models import User, Role, Device, FlowData, ForwardTarget, FlowTemplate, Permission
        
        # Create roles with proper permissions structure
        admin_role = Role(name='Administrator')
        admin_role.permissions = {'permissions': [Permission.ADMIN, Permission.VIEW_FLOW_DATA, Permission.MANAGE_DEVICES]}
        
        analyst_role = Role(name='Analyst')
        analyst_role.permissions = {'permissions': [Permission.VIEW_FLOW_DATA]}
        
        db.session.add_all([admin_role, analyst_role])
        db.session.commit()
        
        # Create test users
        admin_user = User(username='admin_test', email='admin@test.com', role=admin_role)
        admin_user.set_password('password')
        
        analyst_user = User(username='analyst_test', email='analyst@test.com', role=analyst_role)
        analyst_user.set_password('password')
        
        db.session.add_all([admin_user, analyst_user])
        db.session.commit()
        
        # Create test devices
        device1 = Device(
            name='Router1', 
            ip_address='192.168.1.1', 
            flow_type='netflow', 
            flow_version='5',
            last_seen=datetime.utcnow()
        )
        device2 = Device(
            name='Switch1', 
            ip_address='192.168.1.2', 
            flow_type='sflow', 
            flow_version='5',
            last_seen=datetime.utcnow()
        )
        db.session.add_all([device1, device2])
        db.session.commit()
        
        # Create test flow data
        for i in range(10):
            flow1 = FlowData(
                device_id=device1.id,
                src_ip='10.0.0.1',
                dst_ip='8.8.8.8',
                src_port=12345,
                dst_port=53,
                protocol=17,  # UDP
                bytes=120 + i * 10,
                packets=1 + i,
                timestamp=datetime.utcnow() - timedelta(minutes=i * 5),
                flow_type='netflow5'
            )
            
            flow2 = FlowData(
                device_id=device2.id,
                src_ip='10.0.0.2',
                dst_ip='1.1.1.1',
                src_port=54321,
                dst_port=53,
                protocol=17,  # UDP
                bytes=80 + i * 5,
                packets=1 + i,
                timestamp=datetime.utcnow() - timedelta(minutes=i * 5),
                flow_type='sflow5'
            )
            
            db.session.add_all([flow1, flow2])
        
        # Create test forward target
        target = ForwardTarget(
            name='Test Collector',
            ip_address='10.0.0.100',
            port=2055,
            protocol='udp',
            flow_type='netflow',
            flow_version='5',
            active=True
        )
        db.session.add(target)
        
        # Create test simulation template
        template = FlowTemplate(
            name='Test Template',
            description='Test flow template for DNS traffic',
            flow_type='netflow',
            template_data=json.dumps({
                'src_ip_range': '192.168.0.0/24',
                'dst_ip_range': '8.8.8.0/24',
                'src_port_range': [1024, 65535],
                'dst_port_range': [53, 53],
                'protocol': 17,
                'bytes_range': [60, 120],
                'packets_range': [1, 2]
            })
        )
        db.session.add(template)
        
        db.session.commit()

# Flow Processor Tests
class FlowProcessorTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment for flow processor tests."""
        from flow_processor import FlowProcessor
        self.processor = FlowProcessor()
    
    def test_detect_flow_type(self):
        """Test flow type detection."""
        # Test NetFlow v5 detection
        netflow_v5_header = struct.pack('!H', 5) + b'\x00' * 22  # Version 5 + padding
        flow_type, version = self.processor.detect_flow_type(netflow_v5_header)
        self.assertEqual(flow_type, 'netflow')
        self.assertEqual(version, 5)
        
        # Test NetFlow v9 detection
        netflow_v9_header = struct.pack('!H', 9) + b'\x00' * 18  # Version 9 + padding
        flow_type, version = self.processor.detect_flow_type(netflow_v9_header)
        self.assertEqual(flow_type, 'netflow')
        self.assertEqual(version, 9)
        
        # Test IPFIX detection
        ipfix_header = struct.pack('!H', 10) + b'\x00' * 14  # Version 10 + padding
        flow_type, version = self.processor.detect_flow_type(ipfix_header)
        self.assertEqual(flow_type, 'ipfix')
        self.assertEqual(version, 10)
        
        # Test sFlow v5 detection
        sflow_v5_header = struct.pack('!I', 5) + b'\x00' * 24  # Version 5 + padding
        flow_type, version = self.processor.detect_flow_type(sflow_v5_header)
        self.assertEqual(flow_type, 'sflow')
        self.assertEqual(version, 5)
    
    def test_validate_packet(self):
        """Test packet validation."""
        # Test valid NetFlow v5 packet
        netflow_v5_packet = struct.pack('!HHIII', 5, 1, 1000, 1234567890, 0) + b'\x00' * 56
        is_valid, error = self.processor.validate_packet(netflow_v5_packet, 'netflow', 5)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test invalid packet (too short)
        short_packet = b'\x00' * 10
        is_valid, error = self.processor.validate_packet(short_packet, 'netflow', 5)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        
        # Test invalid packet (empty)
        is_valid, error = self.processor.validate_packet(b'', 'netflow', 5)
        self.assertFalse(is_valid)
        self.assertEqual(error, "Empty packet data")
    
    def test_validate_flow_record(self):
        """Test flow record validation."""
        # Test valid flow record
        valid_flow = {
            'src_ip': '192.168.1.1',
            'dst_ip': '8.8.8.8',
            'src_port': 12345,
            'dst_port': 53,
            'protocol': 17,
            'bytes': 128,
            'packets': 1
        }
        is_valid, errors = self.processor.validate_flow_record(valid_flow)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test invalid flow record (missing required fields)
        invalid_flow = {
            'src_port': 12345,
            'dst_port': 53
        }
        is_valid, errors = self.processor.validate_flow_record(invalid_flow)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Test invalid IP address
        invalid_ip_flow = {
            'src_ip': 'invalid_ip',
            'dst_ip': '8.8.8.8'
        }
        is_valid, errors = self.processor.validate_flow_record(invalid_ip_flow)
        self.assertFalse(is_valid)
        self.assertTrue(any('Invalid source IP' in error for error in errors))
    
    def test_sanitize_flow_record(self):
        """Test flow record sanitization."""
        # Test sanitization with mixed valid/invalid data
        raw_flow = {
            'src_ip': '192.168.1.1',
            'dst_ip': '8.8.8.8',
            'src_port': '12345',  # String that should be converted to int
            'dst_port': 53,
            'protocol': 17,
            'bytes': '128',  # String that should be converted to int
            'packets': 1,
            'invalid_field': None,  # Should be filtered out
            'empty_field': '',  # Should be filtered out
            'negative_port': -1  # Should be filtered out
        }
        
        sanitized = self.processor.sanitize_flow_record(raw_flow)
        
        self.assertEqual(sanitized['src_ip'], '192.168.1.1')
        self.assertEqual(sanitized['dst_ip'], '8.8.8.8')
        self.assertEqual(sanitized['src_port'], 12345)
        self.assertEqual(sanitized['dst_port'], 53)
        self.assertEqual(sanitized['bytes'], 128)
        self.assertNotIn('invalid_field', sanitized)
        self.assertNotIn('empty_field', sanitized)
        self.assertNotIn('negative_port', sanitized)

# Template Manager Tests
class TemplateManagerTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment for template manager tests."""
        from netflow_templates import get_template_manager
        self.template_mgr = get_template_manager()
    
    def test_store_and_retrieve_template(self):
        """Test storing and retrieving NetFlow templates."""
        # Test template storage
        source_id = 12345
        template_id = 256
        fields = [(1, 4), (2, 4), (8, 4), (12, 4)]  # Common NetFlow fields
        
        self.template_mgr.store_template(source_id, template_id, fields)
        
        # Test template retrieval
        template = self.template_mgr.get_template(source_id, template_id)
        
        self.assertIsNotNone(template)
        self.assertEqual(template['template_id'], template_id)
        self.assertEqual(template['fields'], fields)
        self.assertEqual(template['field_count'], 4)
        self.assertEqual(template['record_length'], 16)
    
    def test_template_not_found(self):
        """Test retrieving non-existent template."""
        template = self.template_mgr.get_template(99999, 99999)
        self.assertIsNone(template)

# Integration Tests (require minimal app setup)
class IntegrationTestCase(unittest.TestCase):
    def test_flow_processor_integration(self):
        """Test flow processor with template manager integration."""
        from flow_processor import FlowProcessor
        from netflow_templates import get_template_manager
        
        processor = FlowProcessor()
        template_mgr = get_template_manager()
        
        # Create a simple NetFlow v9 template packet
        source_id = 12345
        template_id = 256
        
        # Store a template first
        fields = [(8, 4), (12, 4), (7, 2), (11, 2), (4, 1), (1, 4), (2, 4)]
        template_mgr.store_template(source_id, template_id, fields)
        
        # Verify the template was stored
        template = template_mgr.get_template(source_id, template_id)
        self.assertIsNotNone(template)
        self.assertEqual(len(template['fields']), 7)
    
    def test_validation_stats(self):
        """Test validation statistics tracking."""
        from flow_processor import FlowProcessor
        
        processor = FlowProcessor()
        
        # Test initial stats
        stats = processor.get_validation_stats()
        self.assertEqual(stats['total_packets'], 0)
        
        # Update stats
        processor.update_validation_stats(True)
        processor.update_validation_stats(False, "Test error")
        processor.update_validation_stats(True)
        
        # Check updated stats
        stats = processor.get_validation_stats()
        self.assertEqual(stats['total_packets'], 3)
        self.assertEqual(stats['valid_packets'], 2)
        self.assertEqual(stats['invalid_packets'], 1)
        self.assertEqual(stats['valid_percentage'], 66.66666666666666)

if __name__ == '__main__':
    # Create a test suite combining all test cases
    test_suite = unittest.TestSuite()
    
    # Add basic tests that don't require full app
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(FlowProcessorTestCase))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TemplateManagerTestCase))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(IntegrationTestCase))
    
    # Add app-based tests (commented out due to circular import issues)
    # test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(FlowVisionTestCase))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)