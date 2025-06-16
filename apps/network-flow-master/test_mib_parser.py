"""
Unit tests for MIB parser functionality
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from mib_parser import MIBParser, DeviceInfoExtractor

class TestMIBParser(unittest.TestCase):
    """Test the MIB parser"""

    def setUp(self):
        """Set up test environment"""
        # Create MIB parser instance
        self.parser = MIBParser()
        
        # Sample MIB content
        self.sample_mib = """
-- Sample Cisco MIB for testing
CISCO-FLOW-MONITOR-MIB DEFINITIONS ::= BEGIN

IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, Integer32, Unsigned32, Counter64
        FROM SNMPv2-SMI
    MODULE-COMPLIANCE, OBJECT-GROUP
        FROM SNMPv2-CONF
    SnmpAdminString
        FROM SNMP-FRAMEWORK-MIB
    InetAddressType, InetAddress, InetPortNumber
        FROM INET-ADDRESS-MIB
    ciscoMgmt
        FROM CISCO-SMI;

ciscoFlowMonitorMIB MODULE-IDENTITY
    LAST-UPDATED    "200708210000Z"
    ORGANIZATION    "Cisco Systems, Inc."
    CONTACT-INFO
        "Cisco Systems
        Customer Service

        Postal: 170 W Tasman Drive
        San Jose, CA  95134
        USA

        Tel: +1 800 553-NETS

        E-mail: cs-snmp@cisco.com"
    DESCRIPTION
        "This MIB module defines objects that describe flow monitoring."
    REVISION        "200708210000Z"
    DESCRIPTION
        "Initial version of this MIB module."
    ::= { ciscoMgmt 590 }

-- FlowMonitor Table

cfmFlowMonitorTable OBJECT-TYPE
    SYNTAX      SEQUENCE OF CfmFlowMonitorEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
        "This table lists flow monitors configured on the device."
    ::= { cfmFlowMonitor 1 }

cfmFlowMonitorEntry OBJECT-TYPE
    SYNTAX      CfmFlowMonitorEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
        "An entry describes a flow monitor."
    INDEX { cfmFlowMonitorId }
    ::= { cfmFlowMonitorTable 1 }

CfmFlowMonitorEntry ::= SEQUENCE {
    cfmFlowMonitorId                 Unsigned32,
    cfmFlowMonitorName               SnmpAdminString,
    cfmFlowMonitorDescription        SnmpAdminString,
    cfmFlowMonitorActivateTime       TimeTicks,
    cfmFlowMonitorInactiveTimeout    Unsigned32,
    cfmFlowMonitorActiveTimeout      Unsigned32
}

cfmFlowMonitorId OBJECT-TYPE
    SYNTAX      Unsigned32 (1..4294967295)
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
        "This object indicates the flow monitor identifier."
    ::= { cfmFlowMonitorEntry 1 }

cfmFlowMonitorName OBJECT-TYPE
    SYNTAX      SnmpAdminString
    MAX-ACCESS  read-only
    STATUS      current
    DESCRIPTION
        "This object indicates the name assigned to the flow monitor."
    ::= { cfmFlowMonitorEntry 2 }

END
        """

    @patch('builtins.open', new_callable=mock_open)
    def test_parse_mib(self, mock_file):
        """Test MIB parsing"""
        # Set up mock file
        mock_file.return_value.read.return_value = self.sample_mib
        
        # Parse MIB
        result = self.parser.parse_mib('test.mib')
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['mib_name'], 'CISCO-FLOW-MONITOR-MIB')
        self.assertIn('tables', result)
        self.assertIn('scalars', result)
        
        # Check that we found the table
        self.assertIn('cfmFlowMonitorTable', result['tables'])
        
        # Check organization
        self.assertEqual(result['organization'], 'Cisco Systems, Inc.')
        
        # Check contact info
        self.assertIn('Cisco Systems', result['contact_info'])
        
        # Check that it identified as a Cisco MIB
        self.assertEqual(result['vendor'], 'Cisco')

    @patch('builtins.open', new_callable=mock_open)
    def test_extract_device_info(self, mock_file):
        """Test device info extraction"""
        # Create extractor instance
        extractor = DeviceInfoExtractor()
        
        # Set up mock file
        mock_file.return_value.read.return_value = self.sample_mib
        
        # Mock the parser
        with patch.object(extractor, '_parser', MagicMock()) as mock_parser:
            # Mock parse_mib to return our desired data
            mock_parser.parse_mib.return_value = {
                'success': True,
                'mib_name': 'CISCO-FLOW-MONITOR-MIB',
                'organization': 'Cisco Systems, Inc.',
                'vendor': 'Cisco',
                'contact_info': 'Customer Service Postal: 170 W Tasman Drive San Jose, CA 95134 USA',
                'tables': {
                    'cfmFlowMonitorTable': {
                        'description': 'This table lists flow monitors configured on the device.'
                    }
                }
            }
            
            # Extract device info
            result = extractor.extract_device_info('test.mib')
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertEqual(result['vendor'], 'Cisco')
            self.assertEqual(result['device_type'], 'Flow Monitor')
            self.assertIn('flow', result['capabilities'])
            self.assertIn('monitor', result['capabilities'])

    def test_guess_vendor(self):
        """Test vendor guessing"""
        # Test Cisco identification
        self.assertEqual(self.parser._guess_vendor('CISCO-FLOW-MONITOR-MIB'), 'Cisco')
        self.assertEqual(self.parser._guess_vendor('Cisco Systems'), 'Cisco')
        
        # Test Juniper identification
        self.assertEqual(self.parser._guess_vendor('JUNIPER-FLOW-MONITORING-MIB'), 'Juniper')
        self.assertEqual(self.parser._guess_vendor('Juniper Networks'), 'Juniper')
        
        # Test HP identification
        self.assertEqual(self.parser._guess_vendor('HP-ICF-IPCONFIG'), 'HP')
        self.assertEqual(self.parser._guess_vendor('Hewlett-Packard'), 'HP')
        
        # Test unknown vendor
        self.assertEqual(self.parser._guess_vendor('UNKNOWN-VENDOR-MIB'), 'Unknown')

    def test_find_flow_related_objects(self):
        """Test flow-related object identification"""
        # Create a sample MIB structure
        mib_structure = {
            'tables': {
                'cfmFlowMonitorTable': {
                    'description': 'This table lists flow monitors configured on the device.'
                },
                'ipNetToMediaTable': {
                    'description': 'ARP translation table'
                }
            },
            'scalars': {
                'flowEnabled': {
                    'description': 'Indicates if flow monitoring is enabled'
                },
                'systemName': {
                    'description': 'The system name'
                }
            }
        }
        
        # Find flow-related objects
        flow_objects = self.parser._find_flow_related_objects(mib_structure)
        
        # Verify result
        self.assertEqual(len(flow_objects), 2)
        self.assertIn('cfmFlowMonitorTable', flow_objects)
        self.assertIn('flowEnabled', flow_objects)
        self.assertNotIn('ipNetToMediaTable', flow_objects)
        self.assertNotIn('systemName', flow_objects)

if __name__ == '__main__':
    unittest.main()
