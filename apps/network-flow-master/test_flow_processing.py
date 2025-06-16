"""
Unit tests for flow processing functionality
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import datetime
from flow_processor import FlowProcessor
from flow_forwarder import FlowForwarder
from models import FlowData, Device, ForwardTarget

class TestFlowProcessor(unittest.TestCase):
    """Test the flow processor"""

    def setUp(self):
        """Set up test environment"""
        self.processor = FlowProcessor()
        
        # Sample flow data
        self.sample_netflow = {
            'src_ip': '192.168.1.1',
            'dst_ip': '8.8.8.8',
            'src_port': 12345,
            'dst_port': 53,
            'protocol': 17,
            'bytes': 500,
            'packets': 5,
            'timestamp': datetime.datetime.utcnow(),
            'flow_type': 'netflow5',
            'tos': 0,
            'tcp_flags': 0,
            'duration': 1.5
        }
        
        self.sample_sflow = {
            'src_ip': '192.168.1.2',
            'dst_ip': '1.1.1.1',
            'src_port': 54321,
            'dst_port': 443,
            'protocol': 6,
            'bytes': 1500,
            'packets': 10,
            'timestamp': datetime.datetime.utcnow(),
            'flow_type': 'sflow5',
            'tos': 0,
            'tcp_flags': 16,  # ACK flag
            'duration': 2.0
        }

    @patch('flow_processor.db')
    def test_process_netflow(self, mock_db):
        """Test processing NetFlow data"""
        # Mock device lookup
        mock_device = MagicMock()
        mock_device.id = 1
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_device
        
        # Call process_flow
        result = self.processor.process_flow(self.sample_netflow, '10.0.0.1')
        
        # Verify result
        self.assertTrue(result)
        
        # Verify database operations
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
        
        # Check that we passed in a FlowData object
        flow_data = mock_db.session.add.call_args[0][0]
        self.assertIsInstance(flow_data, FlowData)
        self.assertEqual(flow_data.src_ip, '192.168.1.1')
        self.assertEqual(flow_data.dst_ip, '8.8.8.8')
        self.assertEqual(flow_data.src_port, 12345)
        self.assertEqual(flow_data.dst_port, 53)
        self.assertEqual(flow_data.protocol, 17)
        self.assertEqual(flow_data.bytes, 500)
        self.assertEqual(flow_data.packets, 5)
        self.assertEqual(flow_data.device_id, 1)
        self.assertEqual(flow_data.flow_type, 'netflow5')

    @patch('flow_processor.db')
    def test_process_sflow(self, mock_db):
        """Test processing sFlow data"""
        # Mock device lookup
        mock_device = MagicMock()
        mock_device.id = 2
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_device
        
        # Call process_flow
        result = self.processor.process_flow(self.sample_sflow, '10.0.0.2')
        
        # Verify result
        self.assertTrue(result)
        
        # Verify database operations
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
        
        # Check that we passed in a FlowData object
        flow_data = mock_db.session.add.call_args[0][0]
        self.assertIsInstance(flow_data, FlowData)
        self.assertEqual(flow_data.src_ip, '192.168.1.2')
        self.assertEqual(flow_data.dst_ip, '1.1.1.1')
        self.assertEqual(flow_data.src_port, 54321)
        self.assertEqual(flow_data.dst_port, 443)
        self.assertEqual(flow_data.protocol, 6)
        self.assertEqual(flow_data.bytes, 1500)
        self.assertEqual(flow_data.packets, 10)
        self.assertEqual(flow_data.device_id, 2)
        self.assertEqual(flow_data.flow_type, 'sflow5')
        self.assertEqual(flow_data.tcp_flags, 16)

    @patch('flow_processor.db')
    def test_create_or_update_device(self, mock_db):
        """Test device creation/update"""
        # Mock device lookup (not found)
        mock_db.session.query.return_value.filter.return_value.first.return_value = None
        
        # Call create_or_update_device
        device_id = self.processor.create_or_update_device('10.0.0.1', 'netflow', '5')
        
        # Verify database operations
        self.assertEqual(mock_db.session.add.call_count, 1)
        self.assertEqual(mock_db.session.commit.call_count, 1)
        
        # Check that we passed in a Device object
        device = mock_db.session.add.call_args[0][0]
        self.assertIsInstance(device, Device)
        self.assertEqual(device.ip_address, '10.0.0.1')
        self.assertEqual(device.flow_type, 'netflow')
        self.assertEqual(device.flow_version, '5')
        
        # Now test update (device found)
        mock_device = MagicMock()
        mock_device.id = 1
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_device
        
        # Call again, should update existing device
        device_id = self.processor.create_or_update_device('10.0.0.1', 'netflow', '5')
        
        # Verify we updated the last_seen field
        self.assertIsNotNone(mock_device.last_seen)
        
        # Should be the same device ID
        self.assertEqual(device_id, 1)

class TestFlowForwarder(unittest.TestCase):
    """Test the flow forwarder"""

    def setUp(self):
        """Set up test environment"""
        # Mock the database session
        with patch('flow_forwarder.db'):
            self.forwarder = FlowForwarder()
        
        # Sample flow data
        self.sample_flow = {
            'src_ip': '192.168.1.1',
            'dst_ip': '8.8.8.8',
            'src_port': 12345,
            'dst_port': 53,
            'protocol': 17,
            'bytes': 500,
            'packets': 5,
            'timestamp': datetime.datetime.utcnow(),
            'flow_type': 'netflow5',
            'tos': 0,
            'tcp_flags': 0,
            'duration': 1.5
        }
        
        # Create raw data
        self.raw_data = b'\x00\x05\x00\x01\x12\x34\x56\x78'

    def test_ip_matches_filter(self):
        """Test IP filter matching"""
        # Test exact match
        self.assertTrue(self.forwarder._ip_matches_filter('192.168.1.1', '192.168.1.1'))
        
        # Test CIDR match
        self.assertTrue(self.forwarder._ip_matches_filter('192.168.1.5', '192.168.1.0/24'))
        
        # Test no match
        self.assertFalse(self.forwarder._ip_matches_filter('10.0.0.1', '192.168.1.0/24'))
        
        # Test empty filter (matches anything)
        self.assertTrue(self.forwarder._ip_matches_filter('192.168.1.1', ''))
        self.assertTrue(self.forwarder._ip_matches_filter('192.168.1.1', None))

    def test_protocol_matches_filter(self):
        """Test protocol filter matching"""
        # Test exact match (number)
        self.assertTrue(self.forwarder._protocol_matches_filter(17, '17'))
        
        # Test protocol name match
        self.assertTrue(self.forwarder._protocol_matches_filter(17, 'UDP'))
        self.assertTrue(self.forwarder._protocol_matches_filter(6, 'TCP'))
        
        # Test comma-separated list
        self.assertTrue(self.forwarder._protocol_matches_filter(17, 'TCP,UDP,ICMP'))
        
        # Test no match
        self.assertFalse(self.forwarder._protocol_matches_filter(1, 'TCP,UDP'))
        
        # Test empty filter (matches anything)
        self.assertTrue(self.forwarder._protocol_matches_filter(17, ''))
        self.assertTrue(self.forwarder._protocol_matches_filter(17, None))

    @patch('flow_forwarder.db')
    def test_forward_flow(self, mock_db):
        """Test flow forwarding"""
        # Create mock flow data
        flow_data = MagicMock()
        flow_data.src_ip = '192.168.1.1'
        flow_data.dst_ip = '8.8.8.8'
        flow_data.protocol = 17
        flow_data.flow_type = 'netflow5'
        
        # Create mock targets
        target1 = ForwardTarget(
            id=1,
            name='Target1',
            ip_address='10.0.0.100',
            port=2055,
            protocol='udp',
            flow_type='netflow',
            flow_version='5',
            active=True,
            filter_src_ip='192.168.1.0/24',
            filter_dst_ip='',
            filter_protocol=''
        )
        
        target2 = ForwardTarget(
            id=2,
            name='Target2',
            ip_address='10.0.0.101',
            port=2055,
            protocol='udp',
            flow_type='netflow',
            flow_version='5',
            active=True,
            filter_src_ip='10.0.0.0/8',  # won't match
            filter_dst_ip='',
            filter_protocol=''
        )
        
        # Mock db query to return our targets
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = [target1, target2]
        
        # Mock flow_matches_target
        with patch.object(self.forwarder, '_flow_matches_target') as mock_match:
            # First target matches, second doesn't
            mock_match.side_effect = [True, False]
            
            # Mock socket
            with patch('socket.socket') as mock_socket:
                mock_socket_instance = MagicMock()
                mock_socket.return_value = mock_socket_instance
                
                # Call forward_flow
                self.forwarder.forward_flow(flow_data, self.raw_data)
                
                # Process the queue
                self.forwarder._forward_flows()
                
                # Verify we checked both targets
                self.assertEqual(mock_match.call_count, 2)
                
                # Verify we created one socket (for the matching target)
                self.assertEqual(mock_socket.call_count, 1)
                
                # Verify we sent the raw data
                mock_socket_instance.sendto.assert_called_once_with(self.raw_data, ('10.0.0.100', 2055))

if __name__ == '__main__':
    unittest.main()
