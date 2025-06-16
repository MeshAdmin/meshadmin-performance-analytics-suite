import logging
import struct
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class NetFlowTemplateManager:
    """
    Manages NetFlow v9 and IPFIX templates for parsing flow records
    """
    
    def __init__(self):
        # Template cache: {source_id: {template_id: template_definition}}
        self.templates = defaultdict(dict)
        
        # Template timeout - templates expire after 30 minutes of no activity
        self.template_timeout = 1800
        
        # Last seen timestamp for each template
        self.template_last_seen = defaultdict(dict)
    
    def store_template(self, source_id, template_id, field_list):
        """
        Store a template definition
        
        Args:
            source_id (int): Source ID from the flow record
            template_id (int): Template ID
            field_list (list): List of field definitions [(field_type, field_length), ...]
        """
        template_def = {
            'template_id': template_id,
            'fields': field_list,
            'field_count': len(field_list),
            'record_length': sum(field[1] for field in field_list),
            'created': datetime.utcnow()
        }
        
        self.templates[source_id][template_id] = template_def
        self.template_last_seen[source_id][template_id] = datetime.utcnow()
        
        logger.debug(f"Stored template {template_id} for source {source_id} with {len(field_list)} fields")
    
    def get_template(self, source_id, template_id):
        """
        Retrieve a template definition
        
        Args:
            source_id (int): Source ID
            template_id (int): Template ID
        
        Returns:
            dict: Template definition or None if not found
        """
        if source_id in self.templates and template_id in self.templates[source_id]:
            # Update last seen timestamp
            self.template_last_seen[source_id][template_id] = datetime.utcnow()
            return self.templates[source_id][template_id]
        
        return None


# NetFlow v9 and IPFIX field definitions
NETFLOW_FIELD_TYPES = {
    1: ('IN_BYTES', 4),           # Incoming counter with length N x 8 bits for bytes
    2: ('IN_PKTS', 4),            # Incoming counter with length N x 8 bits for packets
    4: ('PROTOCOL', 1),           # IP protocol byte
    5: ('SRC_TOS', 1),            # Type of service byte
    6: ('TCP_FLAGS', 1),          # Cumulative OR of TCP flags
    7: ('L4_SRC_PORT', 2),        # TCP/UDP source port number
    8: ('IPV4_SRC_ADDR', 4),      # IPv4 source address
    9: ('SRC_MASK', 1),           # Source subnet mask
    10: ('INPUT_SNMP', 2),        # Input interface index
    11: ('L4_DST_PORT', 2),       # TCP/UDP destination port number
    12: ('IPV4_DST_ADDR', 4),     # IPv4 destination address
    13: ('DST_MASK', 1),          # Destination subnet mask
    14: ('OUTPUT_SNMP', 2),       # Output interface index
    15: ('IPV4_NEXT_HOP', 4),     # IPv4 Next Hop address
    16: ('SRC_AS', 2),            # Source BGP autonomous system number
    17: ('DST_AS', 2),            # Destination BGP autonomous system number
    21: ('LAST_SWITCHED', 4),     # System uptime at which the last packet was switched
    22: ('FIRST_SWITCHED', 4),    # System uptime at which the first packet was switched
    27: ('IPV6_SRC_ADDR', 16),    # IPv6 source address
    28: ('IPV6_DST_ADDR', 16),    # IPv6 destination address
    150: ('FLOW_START_SECONDS', 4),     # Absolute timestamp of start of flow
    151: ('FLOW_END_SECONDS', 4),       # Absolute timestamp of end of flow
    152: ('FLOW_START_MILLISECONDS', 8), # Absolute timestamp of start of flow
    153: ('FLOW_END_MILLISECONDS', 8),   # Absolute timestamp of end of flow
}

def parse_field_value(field_type, field_length, data, offset):
    """
    Parse a field value based on its type and length
    """
    if field_type not in NETFLOW_FIELD_TYPES:
        return f'UNKNOWN_{field_type}', None, offset + field_length
    
    field_name, default_length = NETFLOW_FIELD_TYPES[field_type]
    
    if offset + field_length > len(data):
        raise ValueError(f"Field extends beyond packet boundary")
    
    field_data = data[offset:offset + field_length]
    
    # Parse based on field type
    if field_type in [1, 2]:  # Counter fields
        if field_length == 4:
            value = struct.unpack('!I', field_data)[0]
        elif field_length == 8:
            value = struct.unpack('!Q', field_data)[0]
        else:
            value = int.from_bytes(field_data, byteorder='big')
    
    elif field_type in [4, 5, 6, 9, 13]:  # Single byte fields
        value = field_data[0]
    
    elif field_type in [7, 10, 11, 14, 16, 17]:  # Two byte fields
        if field_length >= 2:
            value = struct.unpack('!H', field_data[:2])[0]
        else:
            value = field_data[0]
    
    elif field_type in [8, 12, 15]:  # IPv4 addresses
        if field_length == 4:
            value = '.'.join(str(b) for b in field_data)
        else:
            value = None
    
    elif field_type in [27, 28]:  # IPv6 addresses
        if field_length == 16:
            value = ':'.join(f'{field_data[i]:02x}{field_data[i+1]:02x}' 
                           for i in range(0, 16, 2))
        else:
            value = None
    
    elif field_type in [21, 22, 150, 151]:  # Uptime/timestamp fields
        if field_length == 4:
            value = struct.unpack('!I', field_data)[0]
        else:
            value = int.from_bytes(field_data, byteorder='big')
    
    elif field_type in [152, 153]:  # Millisecond timestamps
        if field_length == 8:
            value = struct.unpack('!Q', field_data)[0]
        else:
            value = int.from_bytes(field_data, byteorder='big')
    
    else:
        # Default parsing
        if field_length <= 8:
            value = int.from_bytes(field_data, byteorder='big')
        else:
            value = field_data.hex()
    
    return field_name, value, offset + field_length


# Global template manager instance
_template_manager = None

def get_template_manager():
    """Get the global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = NetFlowTemplateManager()
    return _template_manager 