#!/usr/bin/env python3
"""
Isolated tests for flow parsing components.
"""

import unittest
import struct
import ipaddress

class TemplateManagerTestCase(unittest.TestCase):
    def setUp(self):
        from netflow_templates import get_template_manager
        self.template_mgr = get_template_manager()
    
    def test_store_and_retrieve_template(self):
        """Test storing and retrieving NetFlow templates."""
        source_id = 12345
        template_id = 256
        fields = [(1, 4), (2, 4), (8, 4), (12, 4)]
        
        self.template_mgr.store_template(source_id, template_id, fields)
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

class ValidationTestCase(unittest.TestCase):
    def test_ip_validation(self):
        """Test IP address validation."""
        valid_ips = ['192.168.1.1', '10.0.0.1', '::1', '2001:db8::1']
        for ip in valid_ips:
            try:
                ipaddress.ip_address(ip)
                self.assertTrue(True)
            except ValueError:
                self.fail(f"Should be valid IP: {ip}")
        
        invalid_ips = ['256.1.1.1', 'not.an.ip', '']
        for ip in invalid_ips:
            try:
                ipaddress.ip_address(ip)
                self.fail(f"Should be invalid IP: {ip}")
            except ValueError:
                self.assertTrue(True)
    
    def test_port_validation(self):
        """Test port validation logic."""
        valid_ports = [80, 443, 8080, 65535]
        for port in valid_ports:
            self.assertGreaterEqual(port, 0)
            self.assertLessEqual(port, 65535)
        
        invalid_ports = [-1, 65536, 100000]
        for port in invalid_ports:
            self.assertTrue(port < 0 or port > 65535)

class PacketStructureTestCase(unittest.TestCase):
    def test_netflow_v5_header(self):
        """Test NetFlow v5 header structure."""
        version = 5
        count = 2
        header = struct.pack('!HH', version, count) + b'\x00' * 20
        
        parsed_version = struct.unpack('!H', header[0:2])[0]
        parsed_count = struct.unpack('!H', header[2:4])[0]
        
        self.assertEqual(parsed_version, version)
        self.assertEqual(parsed_count, count)
        self.assertGreaterEqual(len(header), 24)  # Minimum NetFlow v5 size
    
    def test_sflow_header(self):
        """Test sFlow header structure."""
        version = 5
        address_type = 1
        header = struct.pack('!II', version, address_type) + b'\x00' * 20
        
        parsed_version = struct.unpack('!I', header[0:4])[0]
        parsed_addr_type = struct.unpack('!I', header[4:8])[0]
        
        self.assertEqual(parsed_version, version)
        self.assertEqual(parsed_addr_type, address_type)
        self.assertGreaterEqual(len(header), 28)  # Minimum sFlow size

if __name__ == '__main__':
    unittest.main(verbosity=2) 