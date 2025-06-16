import logging
import os
import json
from pysnmp.smi import builder, view, compiler, rfc1902
from app import db
from models import MibFile

logger = logging.getLogger(__name__)

class MibParser:
    """
    Parses and processes MIB files for device-specific analysis
    """
    
    def __init__(self):
        """Initialize the MIB parser"""
        # Initialize a MIB builder
        self.mib_builder = builder.MibBuilder()
        
        # Initialize MIB view controller
        self.mib_view_controller = view.MibViewController(self.mib_builder)
        
        # Set up compiler
        self.mib_compiler = compiler.MibCompiler(self.mib_builder)
        
        # Load default MIB sources
        default_mibs = os.path.join(os.path.dirname(__file__), 'mibs')
        if os.path.exists(default_mibs):
            self.mib_compiler.addSources(builder.DirMibSource(default_mibs))
        
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'mibs')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Add the uploads directory to the MIB sources
        self.mib_compiler.addSources(builder.DirMibSource(uploads_dir))
    
    def parse_mib_file(self, mib_file_id):
        """
        Parse an uploaded MIB file
        
        Args:
            mib_file_id (int): ID of the MIB file record
        
        Returns:
            dict: Result of the parsing operation
        """
        try:
            # Get the MIB file record
            mib_file = MibFile.query.get(mib_file_id)
            if not mib_file:
                return {'error': f'MIB file record not found: {mib_file_id}'}
            
            # Check if the file exists
            if not os.path.exists(mib_file.path):
                return {'error': f'MIB file not found: {mib_file.path}'}
            
            # Determine the MIB module name from the filename
            mib_module = os.path.splitext(os.path.basename(mib_file.path))[0]
            
            # Compile the MIB file
            self.mib_compiler.addSources(builder.FileSource(mib_file.path))
            compiled_mibs = self.mib_compiler.compile(mib_module)
            
            # Extract information from the compiled MIB
            mib_info = self._extract_mib_info(compiled_mibs)
            
            # Update the MIB file record
            mib_file.parsed = True
            db.session.commit()
            
            return {
                'success': True,
                'mib_module': mib_module,
                'oids': len(mib_info['oids']),
                'mib_info': mib_info
            }
            
        except Exception as e:
            logger.error(f"Error parsing MIB file {mib_file_id}: {str(e)}")
            return {'error': str(e)}
    
    def _extract_mib_info(self, compiled_mibs):
        """
        Extract useful information from compiled MIBs
        
        Args:
            compiled_mibs (list): List of compiled MIB modules
        
        Returns:
            dict: Extracted MIB information
        """
        mib_info = {
            'module_names': compiled_mibs,
            'oids': {},
            'tables': {}
        }
        
        # Iterate through all symbols in the MIB
        for module_name in compiled_mibs:
            mib_symbols = self.mib_builder.mibSymbols[module_name]
            
            for symbol_name, symbol_obj in mib_symbols.items():
                # Skip internal symbols
                if symbol_name.startswith('_'):
                    continue
                
                try:
                    # Get OID for this symbol
                    oid = self.mib_view_controller.getNodeLocation((module_name, symbol_name))
                    
                    # Extract different information based on object type
                    if hasattr(symbol_obj, 'syntax') and hasattr(symbol_obj.syntax, 'clone'):
                        # This is a scalar object
                        oid_info = {
                            'name': symbol_name,
                            'oid': '.'.join([str(x) for x in oid[0]]),
                            'type': str(symbol_obj.syntax.__class__.__name__),
                            'description': getattr(symbol_obj, 'description', ''),
                            'access': getattr(symbol_obj, 'maxAccess', 'unknown')
                        }
                        
                        mib_info['oids'][symbol_name] = oid_info
                    
                    elif hasattr(symbol_obj, 'createRow'):
                        # This is a table
                        table_info = {
                            'name': symbol_name,
                            'oid': '.'.join([str(x) for x in oid[0]]),
                            'description': getattr(symbol_obj, 'description', ''),
                            'columns': {}
                        }
                        
                        # Extract column information if available
                        if hasattr(symbol_obj, 'tableIndex'):
                            table_info['index'] = str(symbol_obj.tableIndex)
                        
                        mib_info['tables'][symbol_name] = table_info
                
                except Exception as e:
                    logger.debug(f"Error extracting info for {module_name}::{symbol_name}: {str(e)}")
        
        return mib_info
    
    def get_compiled_mibs(self):
        """
        Get a list of all compiled MIBs
        
        Returns:
            list: List of compiled MIB modules
        """
        return list(self.mib_builder.mibSymbols.keys())
    
    def lookup_oid(self, oid_string):
        """
        Look up an OID in the loaded MIBs
        
        Args:
            oid_string (str): OID to look up (e.g., '1.3.6.1.2.1.1.1.0')
        
        Returns:
            dict: Information about the OID
        """
        try:
            # Convert string OID to tuple
            oid_tuple = tuple(int(x) for x in oid_string.split('.') if x)
            
            # Look up the OID
            module_name, symbol_name, suffix = self.mib_view_controller.getNodeName(oid_tuple)
            
            # Get the object
            managed_object = self.mib_builder.mibSymbols[module_name][symbol_name]
            
            # Format the result
            result = {
                'module': module_name,
                'name': symbol_name,
                'oid': oid_string,
                'suffix': '.'.join([str(x) for x in suffix]) if suffix else '',
                'type': str(type(managed_object)),
                'description': getattr(managed_object, 'description', '')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error looking up OID {oid_string}: {str(e)}")
            return {
                'error': str(e),
                'oid': oid_string
            }
    
    def extract_device_info_from_mib(self, mib_file_id, device_type=None):
        """
        Extract device-specific information from a MIB file
        
        Args:
            mib_file_id (int): ID of the MIB file record
            device_type (str): Optional device type hint
        
        Returns:
            dict: Device information
        """
        try:
            # Parse the MIB file if not already parsed
            mib_file = MibFile.query.get(mib_file_id)
            if not mib_file:
                return {'error': f'MIB file record not found: {mib_file_id}'}
            
            if not mib_file.parsed:
                parse_result = self.parse_mib_file(mib_file_id)
                if 'error' in parse_result:
                    return parse_result
            
            # Determine the MIB module name from the filename
            mib_module = os.path.splitext(os.path.basename(mib_file.path))[0]
            
            # Extract device information from the MIB
            device_info = {
                'name': mib_module,
                'description': '',
                'oids': {},
                'tables': {},
                'flow_capabilities': [],
                'vendor': None,
                'model': None,
                'os_version': None
            }
            
            # Look for common device information OIDs
            common_oids = [
                '1.3.6.1.2.1.1.1',  # sysDescr
                '1.3.6.1.2.1.1.2',  # sysObjectID
                '1.3.6.1.2.1.1.5',  # sysName
                '1.3.6.1.2.1.1.6',  # sysLocation
                '1.3.6.1.2.1.1.7'   # sysServices
            ]
            
            for oid in common_oids:
                try:
                    oid_info = self.lookup_oid(oid)
                    if 'error' not in oid_info:
                        device_info['oids'][oid] = oid_info
                        
                        # Try to extract more detailed information from sysDescr
                        if oid == '1.3.6.1.2.1.1.1' and oid_info.get('description'):
                            device_info['description'] = oid_info.get('description', '')
                            vendor_info = self._extract_vendor_info(oid_info.get('description', ''))
                            if vendor_info:
                                device_info.update(vendor_info)
                except Exception as e:
                    logger.debug(f"Error looking up OID {oid}: {str(e)}")
            
            # Look for flow-specific OIDs
            self._detect_flow_capabilities(device_info, device_type)
            
            # Update MIB file record with detected info
            if device_info.get('vendor') and not mib_file.device_type:
                mib_file.device_type = device_info['vendor']
                db.session.commit()
                
            return device_info
            
        except Exception as e:
            logger.error(f"Error extracting device info from MIB {mib_file_id}: {str(e)}")
            return {'error': str(e)}
    
    def _extract_vendor_info(self, description):
        """
        Extract vendor information from device description
        
        Args:
            description (str): Device description string
        
        Returns:
            dict: Extracted vendor information
        """
        result = {}
        
        # Common networking equipment vendors
        vendors = [
            'Cisco', 'Juniper', 'Arista', 'Huawei', 'Palo Alto', 'Fortinet',
            'F5', 'CheckPoint', 'HPE', 'Dell', 'Alcatel', 'Nokia', 'Brocade',
            'Extreme', 'Netgear', 'Ubiquiti', 'SonicWall', 'Mikrotik', 'Barracuda'
        ]
        
        description_lower = description.lower()
        
        # Check for vendor names in description
        for vendor in vendors:
            if vendor.lower() in description_lower:
                result['vendor'] = vendor
                break
        
        # Try to extract OS version using common patterns
        import re
        # Version pattern like "Version 12.4(15)T1" or "v3.2.1"
        version_patterns = [
            r'version\s+(\d+[.\d]*(?:\([^\)]+\))?(?:[a-zA-Z]\d*)?)',
            r'v(\d+\.\d+[\.\d]*)',
            r'release\s+(\d+\.\d+[\.\d]*)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, description_lower)
            if match:
                result['os_version'] = match.group(1)
                break
        
        # Try to extract model information
        model_patterns = {
            'cisco': [
                r'(catalyst\s+\d[^\s,]+)',
                r'(ISR\s+\d[^\s,]+)',
                r'(ASR\s+\d[^\s,]+)',
                r'(Nexus\s+\d[^\s,]+)',
                r'(CSR\s+\d[^\s,]+)',
            ],
            'juniper': [
                r'(SRX\s+\d[^\s,]+)',
                r'(MX\s+\d[^\s,]+)',
                r'(EX\s+\d[^\s,]+)',
                r'(QFX\s+\d[^\s,]+)',
                r'(PTX\s+\d[^\s,]+)',
            ],
            'arista': [
                r'(DCS-\d[^\s,]+)',
                r'(7\d\d\d[^\s,]+)',
            ],
            'huawei': [
                r'(USG\s+\d[^\s,]+)',
                r'(S\d\d\d\d[^\s,]+)',
                r'(NE\s+\d[^\s,]+)',
            ]
        }
        
        if result.get('vendor'):
            vendor_lower = result['vendor'].lower()
            if vendor_lower in model_patterns:
                for pattern in model_patterns[vendor_lower]:
                    match = re.search(pattern, description, re.IGNORECASE)
                    if match:
                        result['model'] = match.group(1)
                        break
        
        return result
    
    def _detect_flow_capabilities(self, device_info, device_type=None):
        """
        Detect flow capabilities based on MIB information and device type
        
        Args:
            device_info (dict): Device information dict to update
            device_type (str): Optional device type hint
        """
        # Default capabilities based on device type/vendor
        vendor = (device_info.get('vendor') or device_type or '').lower()
        
        # Flow-related OIDs by vendor
        flow_oids = {
            'cisco': [
                '1.3.6.1.4.1.9.9.387',  # CISCO-NETFLOW-MIB
                '1.3.6.1.4.1.9.9.389',  # CISCO-IP-FLOW-MIB
            ],
            'juniper': [
                '1.3.6.1.4.1.2636.3.39',  # Juniper flow monitoring MIB
                '1.3.6.1.4.1.4300.1',     # sFlow related MIB
            ],
            'huawei': [
                '1.3.6.1.4.1.2011.5.25.31',  # Huawei NetStream MIB
            ],
            'fortinet': [
                '1.3.6.1.4.1.12356.101.4',  # Fortinet flow monitoring
            ],
            'extreme': [
                '1.3.6.1.4.1.1916.1.34',  # Extreme Networks sFlow MIB
            ],
            'hp': [
                '1.3.6.1.4.1.11.2.14.11.5',  # HP Enterprise flow monitoring
            ],
            'arista': [
                '1.3.6.1.4.1.30065.3',  # Arista flow monitoring
            ],
        }
        
        # Check for flow-specific OIDs in the MIB
        # This is a simplified approach - production code would actually inspect the MIB objects
        if vendor in flow_oids:
            for oid_prefix in flow_oids[vendor]:
                try:
                    # Try to look up the OID prefix
                    oid_info = self.lookup_oid(oid_prefix)
                    if 'error' not in oid_info:
                        # Found flow-related MIB - determine capabilities
                        self._add_flow_capabilities(device_info, vendor, oid_prefix)
                except Exception as e:
                    logger.debug(f"Error looking up flow OID {oid_prefix}: {str(e)}")
        
        # Use device type hint if provided and no capabilities detected yet
        if not device_info['flow_capabilities'] and device_type:
            if device_type.lower() in ['cisco', 'ios', 'ios-xe', 'ios-xr', 'nx-os']:
                device_info['flow_capabilities'].extend(['NetFlow v5', 'NetFlow v9', 'IPFIX'])
            elif device_type.lower() in ['juniper', 'junos']:
                device_info['flow_capabilities'].extend(['sFlow v5', 'NetFlow v9'])
            elif device_type.lower() in ['huawei', 'vrp']:
                device_info['flow_capabilities'].extend(['NetStream v5', 'NetStream v9', 'IPFIX'])
            elif device_type.lower() in ['fortinet', 'fortigate']:
                device_info['flow_capabilities'].append('IPFIX')
            elif device_type.lower() in ['extreme', 'exos']:
                device_info['flow_capabilities'].append('sFlow v5')
            elif device_type.lower() in ['hp', 'hpe', 'aruba', 'procurve']:
                device_info['flow_capabilities'].extend(['sFlow v5', 'NetFlow v9'])
            elif device_type.lower() in ['arista', 'eos']:
                device_info['flow_capabilities'].extend(['sFlow v5', 'NetFlow v9'])
    
    def _add_flow_capabilities(self, device_info, vendor, oid_prefix):
        """
        Add flow capabilities based on vendor and OID prefix
        
        Args:
            device_info (dict): Device information to update
            vendor (str): Vendor name
            oid_prefix (str): OID prefix that was found
        """
        # Cisco flow capabilities based on MIB
        if vendor == 'cisco':
            if oid_prefix == '1.3.6.1.4.1.9.9.387':  # CISCO-NETFLOW-MIB
                device_info['flow_capabilities'].extend(['NetFlow v5', 'NetFlow v9'])
            elif oid_prefix == '1.3.6.1.4.1.9.9.389':  # CISCO-IP-FLOW-MIB
                device_info['flow_capabilities'].extend(['NetFlow v9', 'IPFIX'])
        
        # Juniper flow capabilities
        elif vendor == 'juniper':
            if oid_prefix == '1.3.6.1.4.1.2636.3.39':
                device_info['flow_capabilities'].extend(['NetFlow v9', 'IPFIX'])
            elif oid_prefix == '1.3.6.1.4.1.4300.1':
                device_info['flow_capabilities'].append('sFlow v5')
        
        # Huawei NetStream capabilities
        elif vendor == 'huawei' and oid_prefix == '1.3.6.1.4.1.2011.5.25.31':
            device_info['flow_capabilities'].extend(['NetStream v5', 'NetStream v9', 'IPFIX'])
        
        # Default case - make reasonable guesses
        else:
            if 'fortinet' in vendor:
                device_info['flow_capabilities'].append('IPFIX')
            elif vendor in ['extreme', 'hp', 'arista']:
                device_info['flow_capabilities'].append('sFlow v5')
        
        # Remove duplicates
        device_info['flow_capabilities'] = list(set(device_info['flow_capabilities']))
