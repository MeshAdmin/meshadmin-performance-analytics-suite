import logging
import json
import struct
import socket
from database import db
from datetime import datetime
from storage_manager import get_storage_manager
from netflow_templates import get_template_manager, parse_field_value

logger = logging.getLogger(__name__)

class FlowProcessor:
    """
    Handles the processing of NetFlow and sFlow data
    """
    
    def __init__(self):
        # Use a dictionary to map flow types to their parsers for quick lookup
        self.flow_parsers = {
            'netflow5': self.parse_netflow_v5,
            'netflow9': self.parse_netflow_v9,
            'ipfix': self.parse_ipfix,
            'sflow4': self.parse_sflow_v4,
            'sflow5': self.parse_sflow_v5
        }
        
        # Cache for devices to reduce database lookups
        self.device_cache = {}
        self.device_cache_size = 1000  # Maximum number of devices to cache
        
        # Batch processing variables
        self.flow_batch = []
        self.batch_size = 100  # Number of flows to accumulate before bulk insert
        self.last_batch_time = datetime.utcnow()
        
        # Validation statistics
        self.validation_stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'invalid_packets': 0,
            'validation_errors': {},
            'flow_validation_errors': {}
        }
    
    def process_packet(self, data, addr, port):
        """
        Process a received flow packet with validation and error handling
        
        Args:
            data (bytes): The raw packet data
            addr (tuple): Source address (IP, port)
            port (int): Port the packet was received on
        
        Returns:
            dict: Processed flow data or None if validation fails
        """
        try:
            # Auto-detect flow type and version
            flow_type, flow_version = self.detect_flow_type(data)
            
            # Validate packet before parsing
            is_valid, error_message = self.validate_packet(data, flow_type, flow_version)
            self.update_validation_stats(is_valid, error_message)
            
            if not is_valid:
                logger.warning(f"Invalid packet from {addr[0]}: {error_message}")
                return None
            
            # Call the appropriate parser based on flow type
            parser_key = flow_type.lower() + str(flow_version)
            if parser_key in self.flow_parsers:
                flow_data = self.flow_parsers[parser_key](data)
            else:
                logger.warning(f"Unsupported flow type: {flow_type} v{flow_version}")
                self.update_validation_stats(False, f"Unsupported flow type: {flow_type} v{flow_version}")
                return None
            
            if not flow_data:
                logger.warning(f"Failed to parse {flow_type} v{flow_version} packet from {addr[0]}")
                self.update_validation_stats(False, f"Parse failure: {flow_type} v{flow_version}")
                return None
            
            # Validate and sanitize individual flow records
            if 'flows' in flow_data:
                original_flows = flow_data['flows']
                validated_flows = []
                for flow_record in original_flows:
                    # Sanitize the flow record
                    sanitized_flow = self.sanitize_flow_record(flow_record)
                    
                    # Validate the sanitized flow
                    is_flow_valid, flow_errors = self.validate_flow_record(sanitized_flow)
                    
                    if is_flow_valid:
                        validated_flows.append(sanitized_flow)
                    else:
                        logger.debug(f"Invalid flow record from {addr[0]}: {', '.join(flow_errors)}")
                        # Update flow validation stats
                        for error in flow_errors:
                            error_type = error.split(':')[0]  # Extract error type
                            self.validation_stats['flow_validation_errors'][error_type] = \
                                self.validation_stats['flow_validation_errors'].get(error_type, 0) + 1
                
                flow_data['flows'] = validated_flows
                
                # Log if we filtered out flows
                original_count = len(original_flows)
                valid_count = len(validated_flows)
                if valid_count < original_count:
                    logger.info(f"Filtered {original_count - valid_count} invalid flows from {addr[0]}")
            
            # Get or create device record
            device = self.get_or_create_device(addr[0], flow_type, flow_version)
            
            # Store flow data with raw packet data
            self.store_flow_data(flow_data, device.id, flow_type + str(flow_version), data)
            
            return flow_data
        
        except Exception as e:
            logger.error(f"Error processing flow packet from {addr[0]}: {str(e)}")
            self.update_validation_stats(False, f"Processing error: {str(e)}")
            return None
    
    def detect_flow_type(self, data):
        """
        Auto-detect the flow type and version from raw packet data
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            tuple: (flow_type, flow_version)
        """
        # Check for NetFlow v5 (typically 24-byte header with version field = 5)
        if len(data) >= 24 and int.from_bytes(data[0:2], byteorder='big') == 5:
            return 'netflow', 5
        
        # Check for NetFlow v9 (typically 20-byte header with version field = 9)
        elif len(data) >= 20 and int.from_bytes(data[0:2], byteorder='big') == 9:
            return 'netflow', 9
        
        # Check for IPFIX (typically 16-byte header with version field = 10)
        elif len(data) >= 16 and int.from_bytes(data[0:2], byteorder='big') == 10:
            return 'ipfix', 10
        
        # Check for sFlow v5 (typically 28-byte header with version field = 5)
        elif len(data) >= 28 and int.from_bytes(data[0:4], byteorder='big') == 5:
            return 'sflow', 5
        
        # Check for sFlow v4
        elif len(data) >= 28 and int.from_bytes(data[0:4], byteorder='big') == 4:
            return 'sflow', 4
        
        # Default to unknown - could implement more sophisticated detection
        return 'unknown', 0
    
    def parse_netflow_v5(self, data):
        """
        Parse NetFlow v5 packet
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            dict: Parsed flow data
        """
        # NetFlow v5 header is 24 bytes
        if len(data) < 24:
            logger.warning("NetFlow v5 packet too short")
            return None
        
        # Extract header fields
        version = int.from_bytes(data[0:2], byteorder='big')
        count = int.from_bytes(data[2:4], byteorder='big')
        sys_uptime = int.from_bytes(data[4:8], byteorder='big')
        unix_secs = int.from_bytes(data[8:12], byteorder='big')
        unix_nsecs = int.from_bytes(data[12:16], byteorder='big')
        flow_sequence = int.from_bytes(data[16:20], byteorder='big')
        engine_type = data[20]
        engine_id = data[21]
        sampling_interval = int.from_bytes(data[22:24], byteorder='big')
        
        flows = []
        # Each NetFlow v5 record is 48 bytes
        for i in range(count):
            if len(data) < 24 + (i + 1) * 48:
                break
            
            offset = 24 + i * 48
            record = data[offset:offset + 48]
            
            # Extract record fields
            src_addr = '.'.join(str(record[i]) for i in range(0, 4))
            dst_addr = '.'.join(str(record[i]) for i in range(4, 8))
            next_hop = '.'.join(str(record[i]) for i in range(8, 12))
            input_if = int.from_bytes(record[12:14], byteorder='big')
            output_if = int.from_bytes(record[14:16], byteorder='big')
            packets = int.from_bytes(record[16:20], byteorder='big')
            bytes_value = int.from_bytes(record[20:24], byteorder='big')
            first_time = int.from_bytes(record[24:28], byteorder='big')
            last_time = int.from_bytes(record[28:32], byteorder='big')
            src_port = int.from_bytes(record[32:34], byteorder='big')
            dst_port = int.from_bytes(record[34:36], byteorder='big')
            tcp_flags = record[37]
            protocol = record[38]
            tos = record[39]
            src_as = int.from_bytes(record[40:42], byteorder='big')
            dst_as = int.from_bytes(record[42:44], byteorder='big')
            src_mask = record[44]
            dst_mask = record[45]
            
            flow_data = {
                'src_ip': src_addr,
                'dst_ip': dst_addr,
                'next_hop': next_hop,
                'input_if': input_if,
                'output_if': output_if,
                'packets': packets,
                'bytes': bytes_value,
                'first_time': first_time,
                'last_time': last_time,
                'src_port': src_port,
                'dst_port': dst_port,
                'tcp_flags': tcp_flags,
                'protocol': protocol,
                'tos': tos,
                'src_as': src_as,
                'dst_as': dst_as,
                'src_mask': src_mask,
                'dst_mask': dst_mask,
                'start_time': datetime.fromtimestamp(unix_secs + first_time / 1000),
                'end_time': datetime.fromtimestamp(unix_secs + last_time / 1000)
            }
            
            flows.append(flow_data)
        
        return {
            'version': version,
            'count': count,
            'sys_uptime': sys_uptime,
            'unix_secs': unix_secs,
            'unix_nsecs': unix_nsecs,
            'flow_sequence': flow_sequence,
            'engine_type': engine_type,
            'engine_id': engine_id,
            'sampling_interval': sampling_interval,
            'flows': flows
        }
    
    def parse_netflow_v9(self, data):
        """
        Parse NetFlow v9 packet with proper template management
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            dict: Parsed flow data
        """
        if len(data) < 20:
            logger.warning("NetFlow v9 packet too short")
            return None
        
        # Parse header
        version = int.from_bytes(data[0:2], byteorder='big')
        count = int.from_bytes(data[2:4], byteorder='big')
        sys_uptime = int.from_bytes(data[4:8], byteorder='big')
        unix_secs = int.from_bytes(data[8:12], byteorder='big')
        package_sequence = int.from_bytes(data[12:16], byteorder='big')
        source_id = int.from_bytes(data[16:20], byteorder='big')
        
        template_mgr = get_template_manager()
        flows = []
        offset = 20  # Start after header
        
        # Process flowsets
        for _ in range(count):
            if offset + 4 > len(data):
                break
                
            flowset_id = int.from_bytes(data[offset:offset+2], byteorder='big')
            flowset_length = int.from_bytes(data[offset+2:offset+4], byteorder='big')
            
            if flowset_length < 4 or offset + flowset_length > len(data):
                logger.warning(f"Invalid flowset length: {flowset_length}")
                break
            
            flowset_data = data[offset+4:offset+flowset_length]
            
            if flowset_id == 0:  # Template flowset
                self._parse_netflow_v9_template(flowset_data, source_id, template_mgr)
            elif flowset_id > 255:  # Data flowset
                flows.extend(self._parse_netflow_v9_data(flowset_data, flowset_id, source_id, template_mgr, unix_secs))
            
            offset += flowset_length
        
        return {
            'version': version,
            'count': count,
            'sys_uptime': sys_uptime,
            'unix_secs': unix_secs,
            'package_sequence': package_sequence,
            'source_id': source_id,
            'flows': flows
        }
    
    def _parse_netflow_v9_template(self, data, source_id, template_mgr):
        """Parse NetFlow v9 template flowset"""
        offset = 0
        
        while offset + 4 <= len(data):
            template_id = int.from_bytes(data[offset:offset+2], byteorder='big')
            field_count = int.from_bytes(data[offset+2:offset+4], byteorder='big')
            offset += 4
            
            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break
                    
                field_type = int.from_bytes(data[offset:offset+2], byteorder='big')
                field_length = int.from_bytes(data[offset+2:offset+4], byteorder='big')
                fields.append((field_type, field_length))
                offset += 4
            
            if len(fields) == field_count:
                template_mgr.store_template(source_id, template_id, fields)
                logger.debug(f"Stored NetFlow v9 template {template_id} with {field_count} fields")
    
    def _parse_netflow_v9_data(self, data, template_id, source_id, template_mgr, unix_secs):
        """Parse NetFlow v9 data flowset using template"""
        template = template_mgr.get_template(source_id, template_id)
        if not template:
            logger.warning(f"Template {template_id} not found for source {source_id}")
            return []
        
        flows = []
        offset = 0
        record_length = template['record_length']
        
        while offset + record_length <= len(data):
            flow_record = {}
            field_offset = offset
            
            for field_type, field_length in template['fields']:
                try:
                    field_name, value, field_offset = parse_field_value(field_type, field_length, data, field_offset)
                    if value is not None:
                        flow_record[field_name.lower()] = value
                except Exception as e:
                    logger.warning(f"Error parsing field {field_type}: {str(e)}")
                    field_offset += field_length
            
            if flow_record:
                # Convert to standard flow format
                standardized_flow = self._standardize_netflow_record(flow_record, unix_secs)
                if standardized_flow:
                    flows.append(standardized_flow)
            
            offset += record_length
        
        return flows
    
    def _standardize_netflow_record(self, record, unix_secs):
        """Convert NetFlow v9 record to standardized format"""
        flow = {}
        
        # Map common fields
        field_mapping = {
            'ipv4_src_addr': 'src_ip',
            'ipv6_src_addr': 'src_ip',
            'ipv4_dst_addr': 'dst_ip', 
            'ipv6_dst_addr': 'dst_ip',
            'l4_src_port': 'src_port',
            'l4_dst_port': 'dst_port',
            'protocol': 'protocol',
            'tcp_flags': 'tcp_flags',
            'src_tos': 'tos',
            'in_bytes': 'bytes',
            'in_pkts': 'packets',
            'first_switched': 'first_time',
            'last_switched': 'last_time'
        }
        
        for netflow_field, std_field in field_mapping.items():
            if netflow_field in record:
                flow[std_field] = record[netflow_field]
        
        # Handle timestamps
        if 'flow_start_seconds' in record:
            flow['start_time'] = datetime.fromtimestamp(record['flow_start_seconds'])
        elif 'first_switched' in record:
            flow['start_time'] = datetime.fromtimestamp(unix_secs + record['first_switched'] / 1000)
        
        if 'flow_end_seconds' in record:
            flow['end_time'] = datetime.fromtimestamp(record['flow_end_seconds'])
        elif 'last_switched' in record:
            flow['end_time'] = datetime.fromtimestamp(unix_secs + record['last_switched'] / 1000)
        
        return flow if flow else None
    
    def parse_ipfix(self, data):
        """
        Parse IPFIX packet (similar to NetFlow v9 but with differences)
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            dict: Parsed flow data
        """
        if len(data) < 16:
            logger.warning("IPFIX packet too short")
            return None
        
        # Parse header
        version = int.from_bytes(data[0:2], byteorder='big')
        length = int.from_bytes(data[2:4], byteorder='big')
        export_time = int.from_bytes(data[4:8], byteorder='big')
        sequence_number = int.from_bytes(data[8:12], byteorder='big')
        observation_domain_id = int.from_bytes(data[12:16], byteorder='big')
        
        template_mgr = get_template_manager()
        flows = []
        offset = 16  # Start after header
        
        # Process sets (IPFIX uses "sets" instead of "flowsets")
        while offset + 4 <= len(data):
            set_id = int.from_bytes(data[offset:offset+2], byteorder='big')
            set_length = int.from_bytes(data[offset+2:offset+4], byteorder='big')
            
            if set_length < 4 or offset + set_length > len(data):
                logger.warning(f"Invalid IPFIX set length: {set_length}")
                break
            
            set_data = data[offset+4:offset+set_length]
            
            if set_id == 2:  # Template set
                self._parse_ipfix_template(set_data, observation_domain_id, template_mgr)
            elif set_id > 255:  # Data set
                flows.extend(self._parse_ipfix_data(set_data, set_id, observation_domain_id, template_mgr, export_time))
            
            offset += set_length
        
        return {
            'version': version,
            'length': length,
            'export_time': export_time,
            'sequence_number': sequence_number,
            'observation_domain_id': observation_domain_id,
            'flows': flows
        }
    
    def _parse_ipfix_template(self, data, observation_domain_id, template_mgr):
        """Parse IPFIX template set"""
        offset = 0
        
        while offset + 4 <= len(data):
            template_id = int.from_bytes(data[offset:offset+2], byteorder='big')
            field_count = int.from_bytes(data[offset+2:offset+4], byteorder='big')
            offset += 4
            
            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break
                    
                field_type = int.from_bytes(data[offset:offset+2], byteorder='big')
                field_length = int.from_bytes(data[offset+2:offset+4], byteorder='big')
                fields.append((field_type, field_length))
                offset += 4
            
            if len(fields) == field_count:
                template_mgr.store_template(observation_domain_id, template_id, fields)
                logger.debug(f"Stored IPFIX template {template_id} with {field_count} fields")
    
    def _parse_ipfix_data(self, data, template_id, observation_domain_id, template_mgr, export_time):
        """Parse IPFIX data set using template"""
        template = template_mgr.get_template(observation_domain_id, template_id)
        if not template:
            logger.warning(f"IPFIX template {template_id} not found for observation domain {observation_domain_id}")
            return []
        
        flows = []
        offset = 0
        record_length = template['record_length']
        
        while offset + record_length <= len(data):
            flow_record = {}
            field_offset = offset
            
            for field_type, field_length in template['fields']:
                try:
                    field_name, value, field_offset = parse_field_value(field_type, field_length, data, field_offset)
                    if value is not None:
                        flow_record[field_name.lower()] = value
                except Exception as e:
                    logger.warning(f"Error parsing IPFIX field {field_type}: {str(e)}")
                    field_offset += field_length
            
            if flow_record:
                # Convert to standard flow format (reuse NetFlow standardization)
                standardized_flow = self._standardize_ipfix_record(flow_record, export_time)
                if standardized_flow:
                    flows.append(standardized_flow)
            
            offset += record_length
        
        return flows
    
    def _standardize_ipfix_record(self, record, export_time):
        """Convert IPFIX record to standardized format"""
        # IPFIX uses similar field mapping to NetFlow v9
        return self._standardize_netflow_record(record, export_time)
    
    def parse_sflow_v4(self, data):
        """
        Parse sFlow v4 packet with comprehensive sample record parsing
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            dict: Parsed flow data
        """
        if len(data) < 28:
            logger.warning("sFlow v4 packet too short")
            return None
        
        # Parse sFlow header
        version = int.from_bytes(data[0:4], byteorder='big')
        
        # Address type and agent address
        address_type = int.from_bytes(data[4:8], byteorder='big')
        if address_type == 1:  # IPv4
            agent_address = '.'.join(str(data[i]) for i in range(8, 12))
            offset = 12
        elif address_type == 2:  # IPv6
            agent_address = ':'.join(f'{data[i]:02x}{data[i+1]:02x}' for i in range(8, 24, 2))
            offset = 24
        else:
            logger.warning(f"Unknown sFlow address type: {address_type}")
            return None
        
        sub_agent_id = int.from_bytes(data[offset:offset+4], byteorder='big')
        sequence_number = int.from_bytes(data[offset+4:offset+8], byteorder='big')
        uptime = int.from_bytes(data[offset+8:offset+12], byteorder='big')
        num_samples = int.from_bytes(data[offset+12:offset+16], byteorder='big')
        
        # Parse sample records
        flows = []
        samples = []
        sample_offset = offset + 16
        
        for i in range(num_samples):
            if sample_offset >= len(data):
                break
                
            try:
                sample_data, sample_offset = self._parse_sflow_sample(data, sample_offset, version)
                if sample_data:
                    samples.append(sample_data)
                    # Extract flows from flow samples
                    if sample_data.get('sample_type') == 'flow_sample':
                        flow_records = self._extract_flows_from_sflow_sample(sample_data, uptime)
                        flows.extend(flow_records)
            except Exception as e:
                logger.warning(f"Error parsing sFlow sample {i}: {str(e)}")
                break
        
        return {
            'version': version,
            'address_type': address_type,
            'agent_address': agent_address,
            'sub_agent_id': sub_agent_id,
            'sequence_number': sequence_number,
            'uptime': uptime,
            'num_samples': num_samples,
            'samples': samples,
            'flows': flows
        }
    
    def _parse_sflow_sample(self, data, offset, version):
        """Parse an individual sFlow sample record"""
        if offset + 8 > len(data):
            return None, offset
        
        sample_type = int.from_bytes(data[offset:offset+4], byteorder='big')
        sample_length = int.from_bytes(data[offset+4:offset+8], byteorder='big')
        
        if offset + sample_length > len(data):
            logger.warning(f"sFlow sample extends beyond packet boundary")
            return None, offset + sample_length
        
        sample_data = data[offset+8:offset+sample_length]
        
        # Parse based on sample type
        if sample_type == 1:  # Flow sample
            return self._parse_sflow_flow_sample(sample_data, version), offset + sample_length
        elif sample_type == 2:  # Counter sample
            return self._parse_sflow_counter_sample(sample_data, version), offset + sample_length
        elif sample_type == 3:  # Expanded flow sample (sFlow v5)
            return self._parse_sflow_expanded_flow_sample(sample_data, version), offset + sample_length
        else:
            logger.debug(f"Unknown sFlow sample type: {sample_type}")
            return {
                'sample_type': 'unknown',
                'type_id': sample_type,
                'data': sample_data.hex()
            }, offset + sample_length
    
    def _parse_sflow_flow_sample(self, data, version):
        """Parse sFlow flow sample record"""
        if len(data) < 32:
            return None
        
        offset = 0
        
        # Flow sample header
        sequence_number = int.from_bytes(data[offset:offset+4], byteorder='big')
        source_id = int.from_bytes(data[offset+4:offset+8], byteorder='big')
        sampling_rate = int.from_bytes(data[offset+8:offset+12], byteorder='big')
        sample_pool = int.from_bytes(data[offset+12:offset+16], byteorder='big')
        drops = int.from_bytes(data[offset+16:offset+20], byteorder='big')
        input_if = int.from_bytes(data[offset+20:offset+24], byteorder='big')
        output_if = int.from_bytes(data[offset+24:offset+28], byteorder='big')
        num_flow_records = int.from_bytes(data[offset+28:offset+32], byteorder='big')
        
        offset += 32
        
        # Parse flow records
        flow_records = []
        for i in range(num_flow_records):
            if offset >= len(data):
                break
            try:
                flow_record, offset = self._parse_sflow_flow_record(data, offset)
                if flow_record:
                    flow_records.append(flow_record)
            except Exception as e:
                logger.warning(f"Error parsing sFlow flow record {i}: {str(e)}")
                break
        
        return {
            'sample_type': 'flow_sample',
            'sequence_number': sequence_number,
            'source_id': source_id,
            'sampling_rate': sampling_rate,
            'sample_pool': sample_pool,
            'drops': drops,
            'input_if': input_if,
            'output_if': output_if,
            'flow_records': flow_records
        }
    
    def _parse_sflow_flow_record(self, data, offset):
        """Parse individual flow record within a sample"""
        if offset + 8 > len(data):
            return None, offset
        
        record_type = int.from_bytes(data[offset:offset+4], byteorder='big')
        record_length = int.from_bytes(data[offset+4:offset+8], byteorder='big')
        
        if offset + 8 + record_length > len(data):
            return None, offset + 8 + record_length
        
        record_data = data[offset+8:offset+8+record_length]
        
        # Parse based on record type
        if record_type == 1:  # Raw packet header
            return self._parse_raw_packet_header(record_data), offset + 8 + record_length
        elif record_type == 2:  # Ethernet frame data
            return self._parse_ethernet_frame_data(record_data), offset + 8 + record_length
        elif record_type == 3:  # IPv4 data
            return self._parse_ipv4_data(record_data), offset + 8 + record_length
        elif record_type == 4:  # IPv6 data
            return self._parse_ipv6_data(record_data), offset + 8 + record_length
        else:
            return {
                'record_type': 'unknown',
                'type_id': record_type,
                'data': record_data.hex()
            }, offset + 8 + record_length
    
    def _parse_raw_packet_header(self, data):
        """Parse raw packet header record"""
        if len(data) < 16:
            return None
        
        header_protocol = int.from_bytes(data[0:4], byteorder='big')
        frame_length = int.from_bytes(data[4:8], byteorder='big')
        stripped = int.from_bytes(data[8:12], byteorder='big')
        header_length = int.from_bytes(data[12:16], byteorder='big')
        
        # Extract packet header
        header_data = data[16:16+header_length] if len(data) >= 16+header_length else data[16:]
        
        return {
            'record_type': 'raw_packet_header',
            'header_protocol': header_protocol,
            'frame_length': frame_length,
            'stripped': stripped,
            'header_length': header_length,
            'header_data': header_data
        }
    
    def _parse_ethernet_frame_data(self, data):
        """Parse Ethernet frame data record"""
        if len(data) < 18:
            return None
        
        eth_length = int.from_bytes(data[0:4], byteorder='big')
        src_mac = ':'.join(f'{data[i]:02x}' for i in range(4, 10))
        dst_mac = ':'.join(f'{data[i]:02x}' for i in range(10, 16))
        eth_type = int.from_bytes(data[16:18], byteorder='big')
        
        return {
            'record_type': 'ethernet_frame',
            'eth_length': eth_length,
            'src_mac': src_mac,
            'dst_mac': dst_mac,
            'eth_type': eth_type
        }
    
    def _parse_ipv4_data(self, data):
        """Parse IPv4 data record"""
        if len(data) < 20:
            return None
        
        # IPv4 header fields
        ip_length = int.from_bytes(data[0:4], byteorder='big')
        protocol = data[4]
        tos = data[5]
        ttl = data[6]
        src_ip = '.'.join(str(data[i]) for i in range(8, 12))
        dst_ip = '.'.join(str(data[i]) for i in range(12, 16))
        src_port = int.from_bytes(data[16:18], byteorder='big')
        dst_port = int.from_bytes(data[18:20], byteorder='big')
        tcp_flags = data[20] if len(data) > 20 else 0
        
        return {
            'record_type': 'ipv4_data',
            'ip_length': ip_length,
            'protocol': protocol,
            'tos': tos,
            'ttl': ttl,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port,
            'dst_port': dst_port,
            'tcp_flags': tcp_flags
        }
    
    def _parse_ipv6_data(self, data):
        """Parse IPv6 data record"""
        if len(data) < 40:
            return None
        
        # IPv6 header fields
        ip_length = int.from_bytes(data[0:4], byteorder='big')
        next_header = data[4]
        hop_limit = data[5]
        src_ip = ':'.join(f'{data[i]:02x}{data[i+1]:02x}' for i in range(8, 24, 2))
        dst_ip = ':'.join(f'{data[i]:02x}{data[i+1]:02x}' for i in range(24, 40, 2))
        src_port = int.from_bytes(data[40:42], byteorder='big') if len(data) >= 42 else 0
        dst_port = int.from_bytes(data[42:44], byteorder='big') if len(data) >= 44 else 0
        
        return {
            'record_type': 'ipv6_data',
            'ip_length': ip_length,
            'next_header': next_header,
            'hop_limit': hop_limit,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port,
            'dst_port': dst_port
        }
    
    def _parse_sflow_counter_sample(self, data, version):
        """Parse sFlow counter sample record"""
        if len(data) < 12:
            return None
        
        sequence_number = int.from_bytes(data[0:4], byteorder='big')
        source_id = int.from_bytes(data[4:8], byteorder='big')
        num_counter_records = int.from_bytes(data[8:12], byteorder='big')
        
        return {
            'sample_type': 'counter_sample',
            'sequence_number': sequence_number,
            'source_id': source_id,
            'num_counter_records': num_counter_records
        }
    
    def _parse_sflow_expanded_flow_sample(self, data, version):
        """Parse sFlow expanded flow sample (sFlow v5)"""
        # Similar to flow sample but with additional fields
        return self._parse_sflow_flow_sample(data, version)
    
    def _extract_flows_from_sflow_sample(self, sample, uptime):
        """Extract standardized flow records from sFlow sample"""
        flows = []
        
        if sample.get('sample_type') != 'flow_sample':
            return flows
        
        # Combine information from different flow records in the sample
        flow_record = {
            'input_if': sample.get('input_if'),
            'output_if': sample.get('output_if'),
            'sampling_rate': sample.get('sampling_rate')
        }
        
        # Extract data from flow records
        for record in sample.get('flow_records', []):
            if record.get('record_type') == 'ipv4_data':
                flow_record.update({
                    'src_ip': record.get('src_ip'),
                    'dst_ip': record.get('dst_ip'),
                    'src_port': record.get('src_port'),
                    'dst_port': record.get('dst_port'),
                    'protocol': record.get('protocol'),
                    'tos': record.get('tos'),
                    'tcp_flags': record.get('tcp_flags')
                })
            elif record.get('record_type') == 'ipv6_data':
                flow_record.update({
                    'src_ip': record.get('src_ip'),
                    'dst_ip': record.get('dst_ip'),
                    'src_port': record.get('src_port'),
                    'dst_port': record.get('dst_port'),
                    'protocol': record.get('next_header'),
                })
            elif record.get('record_type') == 'raw_packet_header':
                # Estimate bytes and packets from frame length and sampling rate
                frame_length = record.get('frame_length', 0)
                sampling_rate = sample.get('sampling_rate', 1)
                flow_record.update({
                    'bytes': frame_length * sampling_rate,
                    'packets': sampling_rate,
                    'frame_length': frame_length
                })
        
        # Only create flow if we have essential data
        if flow_record.get('src_ip') and flow_record.get('dst_ip'):
            # Add timestamp
            flow_record['start_time'] = datetime.utcnow()
            flow_record['end_time'] = datetime.utcnow()
            flows.append(flow_record)
        
        return flows
    
    def parse_sflow_v5(self, data):
        """
        Parse sFlow v5 packet with enhanced features over v4
        
        Args:
            data (bytes): The raw packet data
        
        Returns:
            dict: Parsed flow data
        """
        # sFlow v5 has the same basic structure as v4 but with additional features
        # Use v4 parsing as base and add v5 enhancements
        result = self.parse_sflow_v4(data)
        
        if result is None:
            return None
        
        # sFlow v5 specific enhancements
        result['version'] = 5
        
        # Additional parsing for v5-specific sample types and records
        # This includes expanded flow samples, extended data types, etc.
        
        return result
    
    def get_or_create_device(self, ip_address, flow_type, flow_version):
        """
        Get existing device or create a new one, using cache to reduce database lookups
        
        Args:
            ip_address (str): Device IP address
            flow_type (str): Flow type (netflow, sflow)
            flow_version (int): Flow version
        
        Returns:
            Device: Device record
        """
        from models import Device
        
        # Check device cache first to reduce database lookups
        if ip_address in self.device_cache:
            device = self.device_cache[ip_address]
            
            # Only update the last_seen timestamp if it's been more than a minute
            current_time = datetime.utcnow()
            if (current_time - device.last_seen).total_seconds() > 60:
                device.last_seen = current_time
                db.session.add(device)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating device timestamp: {str(e)}")
            
            return device
        
        # Not in cache, query the database
        try:
            device = Device.query.filter_by(ip_address=ip_address).first()
            
            if not device:
                # Create a new device
                device = Device(
                    name=f"Device {ip_address}",
                    ip_address=ip_address,
                    flow_type=flow_type,
                    flow_version=str(flow_version),
                    last_seen=datetime.utcnow()
                )
                db.session.add(device)
                db.session.commit()
            else:
                # Update last seen timestamp
                device.last_seen = datetime.utcnow()
                db.session.commit()
            
            # Add to cache
            self.device_cache[ip_address] = device
            
            # Trim cache if it exceeds the maximum size
            if len(self.device_cache) > self.device_cache_size:
                # Remove oldest accessed devices
                excess = len(self.device_cache) - self.device_cache_size
                oldest_ips = sorted(self.device_cache.keys(), 
                                   key=lambda ip: self.device_cache[ip].last_seen)[:excess]
                for ip in oldest_ips:
                    del self.device_cache[ip]
            
            return device
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating/updating device: {str(e)}")
            
            # Fallback to create a temporary device object without persisting
            return Device(
                name=f"Device {ip_address}",
                ip_address=ip_address,
                flow_type=flow_type,
                flow_version=str(flow_version),
                last_seen=datetime.utcnow(),
                id=-1  # Using -1 to indicate a temporary device
            )
    
    def store_flow_data(self, flow_data, device_id, flow_type_version, raw_data=None):
        """
        Store flow data using the storage manager with batch processing
        
        Args:
            flow_data (dict): Parsed flow data
            device_id (int): Device ID
            flow_type_version (str): Flow type and version (e.g., netflow5)
            raw_data (bytes): Raw flow packet data (if available)
        """
        if not flow_data or 'flows' not in flow_data:
            return
        
        # Get the storage manager
        storage_mgr = get_storage_manager()
        
        # Check if device ID is valid (not a temporary device)
        if device_id < 0:
            logger.warning(f"Skipping flow storage for temporary device (ID: {device_id})")
            return
        
        current_time = datetime.utcnow()
        force_flush = False
        
        # Add flows to batch
        for flow in flow_data.get('flows', []):
            # Add to batch for bulk processing
            self.flow_batch.append({
                'flow_data': flow,
                'device_id': device_id,
                'flow_type': flow_type_version,
                'raw_data': raw_data,
                'timestamp': current_time
            })
        
        # Check if we should process the batch:
        # 1. Batch size threshold reached
        # 2. Time threshold reached (5 seconds since last batch processing)
        if (len(self.flow_batch) >= self.batch_size or 
            (current_time - self.last_batch_time).total_seconds() > 5):
            force_flush = True
        
        # Process the batch if needed
        if force_flush and self.flow_batch:
            try:
                # Process batch with storage manager
                storage_mgr.store_flow_batch(self.flow_batch)
                
                # Clear batch and update timestamp
                self.flow_batch = []
                self.last_batch_time = current_time
                
            except Exception as e:
                logger.error(f"Error processing flow batch: {str(e)}")
                
                # On error, try to process flows individually
                for item in self.flow_batch:
                    try:
                        storage_mgr.store_flow_data(
                            flow_data=item['flow_data'],
                            device_id=item['device_id'],
                            flow_type=item['flow_type'],
                            raw_data=item['raw_data'],
                            store_locally=True
                        )
                    except Exception as inner_e:
                        logger.error(f"Error processing individual flow: {str(inner_e)}")
                
                # Clear batch even if there were errors
                self.flow_batch = []
                self.last_batch_time = current_time
                
    def flush_flow_batch(self):
        """
        Force processing of any pending flows in the batch
        Should be called when shutting down or when idle
        """
        if not self.flow_batch:
            return
            
        try:
            # Get the storage manager
            storage_mgr = get_storage_manager()
            
            # Process batch with storage manager
            storage_mgr.store_flow_batch(self.flow_batch)
            
            # Clear batch and update timestamp
            self.flow_batch = []
            self.last_batch_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error flushing flow batch: {str(e)}")
            
            # On error, try to process flows individually
            for item in self.flow_batch:
                try:
                    storage_mgr.store_flow_data(
                        flow_data=item['flow_data'],
                        device_id=item['device_id'],
                        flow_type=item['flow_type'],
                        raw_data=item['raw_data'],
                        store_locally=True
                    )
                except Exception as inner_e:
                    logger.error(f"Error processing individual flow: {str(inner_e)}")
            
            # Clear batch even if there were errors
            self.flow_batch = []
            self.last_batch_time = datetime.utcnow()
    
    def validate_packet(self, data, flow_type, flow_version):
        """
        Validate packet data before parsing
        
        Args:
            data (bytes): Raw packet data
            flow_type (str): Detected flow type
            flow_version (int): Detected flow version
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Basic packet validation
            if not data or len(data) == 0:
                return False, "Empty packet data"
            
            if len(data) > 65535:  # Maximum UDP packet size
                return False, f"Packet too large: {len(data)} bytes"
            
            # Flow type specific validation
            if flow_type == 'netflow':
                return self._validate_netflow_packet(data, flow_version)
            elif flow_type == 'sflow':
                return self._validate_sflow_packet(data, flow_version)
            elif flow_type == 'ipfix':
                return self._validate_ipfix_packet(data, flow_version)
            else:
                return False, f"Unknown flow type: {flow_type}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _validate_netflow_packet(self, data, version):
        """Validate NetFlow packet structure"""
        if version == 5:
            if len(data) < 24:
                return False, "NetFlow v5 packet too short (minimum 24 bytes)"
            
            # Check version field
            packet_version = int.from_bytes(data[0:2], byteorder='big')
            if packet_version != 5:
                return False, f"Version mismatch: expected 5, got {packet_version}"
            
            # Check count field is reasonable
            count = int.from_bytes(data[2:4], byteorder='big')
            if count > 30:  # NetFlow v5 typically has max 30 records
                return False, f"Too many NetFlow v5 records: {count}"
            
            # Check packet size matches expected size
            expected_size = 24 + (count * 48)
            if len(data) < expected_size:
                return False, f"Packet size mismatch: expected {expected_size}, got {len(data)}"
                
        elif version == 9:
            if len(data) < 20:
                return False, "NetFlow v9 packet too short (minimum 20 bytes)"
            
            # Check version field
            packet_version = int.from_bytes(data[0:2], byteorder='big')
            if packet_version != 9:
                return False, f"Version mismatch: expected 9, got {packet_version}"
            
            # Check count field is reasonable
            count = int.from_bytes(data[2:4], byteorder='big')
            if count > 1000:  # Reasonable upper limit
                return False, f"Too many NetFlow v9 flowsets: {count}"
        
        return True, None
    
    def _validate_sflow_packet(self, data, version):
        """Validate sFlow packet structure"""
        if len(data) < 28:
            return False, f"sFlow v{version} packet too short (minimum 28 bytes)"
        
        # Check version field
        packet_version = int.from_bytes(data[0:4], byteorder='big')
        if packet_version not in [4, 5]:
            return False, f"Invalid sFlow version: {packet_version}"
        
        # Check address type
        address_type = int.from_bytes(data[4:8], byteorder='big')
        if address_type not in [1, 2]:  # IPv4 or IPv6
            return False, f"Invalid sFlow address type: {address_type}"
        
        # Check number of samples is reasonable
        offset = 12 if address_type == 1 else 24
        if len(data) < offset + 16:
            return False, "sFlow packet too short for header"
            
        num_samples = int.from_bytes(data[offset+12:offset+16], byteorder='big')
        if num_samples > 10000:  # Reasonable upper limit
            return False, f"Too many sFlow samples: {num_samples}"
        
        return True, None
    
    def _validate_ipfix_packet(self, data, version):
        """Validate IPFIX packet structure"""
        if len(data) < 16:
            return False, "IPFIX packet too short (minimum 16 bytes)"
        
        # Check version field
        packet_version = int.from_bytes(data[0:2], byteorder='big')
        if packet_version != 10:
            return False, f"Version mismatch: expected 10, got {packet_version}"
        
        # Check packet length field
        length = int.from_bytes(data[2:4], byteorder='big')
        if length != len(data):
            return False, f"Length field mismatch: header says {length}, actual {len(data)}"
        
        return True, None
    
    def validate_flow_record(self, flow_record):
        """
        Validate a parsed flow record
        
        Args:
            flow_record (dict): Parsed flow record
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        # Required fields validation
        required_fields = ['src_ip', 'dst_ip']
        for field in required_fields:
            if field not in flow_record or flow_record[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # IP address validation
        if 'src_ip' in flow_record:
            if not self._validate_ip_address(flow_record['src_ip']):
                errors.append(f"Invalid source IP: {flow_record['src_ip']}")
        
        if 'dst_ip' in flow_record:
            if not self._validate_ip_address(flow_record['dst_ip']):
                errors.append(f"Invalid destination IP: {flow_record['dst_ip']}")
        
        # Port validation
        for port_field in ['src_port', 'dst_port']:
            if port_field in flow_record and flow_record[port_field] is not None:
                port = flow_record[port_field]
                if not isinstance(port, int) or port < 0 or port > 65535:
                    errors.append(f"Invalid {port_field}: {port}")
        
        # Protocol validation
        if 'protocol' in flow_record and flow_record['protocol'] is not None:
            protocol = flow_record['protocol']
            if not isinstance(protocol, int) or protocol < 0 or protocol > 255:
                errors.append(f"Invalid protocol: {protocol}")
        
        # Byte and packet count validation
        for count_field in ['bytes', 'packets']:
            if count_field in flow_record and flow_record[count_field] is not None:
                count = flow_record[count_field]
                if not isinstance(count, int) or count < 0:
                    errors.append(f"Invalid {count_field}: {count}")
                elif count > 1e12:  # Sanity check for extremely large values
                    errors.append(f"Suspiciously large {count_field}: {count}")
        
        # Timestamp validation
        if 'start_time' in flow_record and flow_record['start_time'] is not None:
            if not isinstance(flow_record['start_time'], datetime):
                errors.append("Invalid start_time: not a datetime object")
        
        if 'end_time' in flow_record and flow_record['end_time'] is not None:
            if not isinstance(flow_record['end_time'], datetime):
                errors.append("Invalid end_time: not a datetime object")
        
        # Cross-field validation
        if ('start_time' in flow_record and 'end_time' in flow_record and 
            flow_record['start_time'] is not None and flow_record['end_time'] is not None):
            if flow_record['start_time'] > flow_record['end_time']:
                errors.append("Start time is after end time")
        
        return len(errors) == 0, errors
    
    def _validate_ip_address(self, ip_str):
        """Validate IP address format"""
        try:
            import ipaddress
            ipaddress.ip_address(ip_str)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def sanitize_flow_record(self, flow_record):
        """
        Sanitize and clean flow record data
        
        Args:
            flow_record (dict): Raw flow record
        
        Returns:
            dict: Sanitized flow record
        """
        sanitized = {}
        
        # Copy and validate each field
        for key, value in flow_record.items():
            try:
                if key in ['src_ip', 'dst_ip']:
                    # Clean IP addresses
                    if isinstance(value, str) and self._validate_ip_address(value):
                        sanitized[key] = value.strip()
                
                elif key in ['src_port', 'dst_port']:
                    # Ensure ports are integers in valid range
                    if value is not None:
                        port = int(value)
                        if 0 <= port <= 65535:
                            sanitized[key] = port
                
                elif key in ['protocol', 'tos', 'tcp_flags']:
                    # Ensure protocol fields are valid integers
                    if value is not None:
                        val = int(value)
                        if 0 <= val <= 255:
                            sanitized[key] = val
                
                elif key in ['bytes', 'packets']:
                    # Ensure counters are non-negative integers
                    if value is not None:
                        val = int(value)
                        if val >= 0 and val < 1e15:  # Reasonable upper limit
                            sanitized[key] = val
                
                elif key in ['start_time', 'end_time']:
                    # Ensure timestamps are datetime objects
                    if isinstance(value, datetime):
                        sanitized[key] = value
                
                else:
                    # Copy other fields as-is if they seem reasonable
                    if value is not None and str(value).strip():
                        sanitized[key] = value
                        
            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid field {key}={value}: {str(e)}")
                continue
        
        return sanitized
    
    def update_validation_stats(self, is_valid, error_type=None):
        """Update validation statistics"""
        self.validation_stats['total_packets'] += 1
        
        if is_valid:
            self.validation_stats['valid_packets'] += 1
        else:
            self.validation_stats['invalid_packets'] += 1
            if error_type:
                self.validation_stats['validation_errors'][error_type] = \
                    self.validation_stats['validation_errors'].get(error_type, 0) + 1
    
    def get_validation_stats(self):
        """Get current validation statistics"""
        total = self.validation_stats['total_packets']
        if total == 0:
            return self.validation_stats
        
        stats = self.validation_stats.copy()
        stats['valid_percentage'] = (stats['valid_packets'] / total) * 100
        stats['invalid_percentage'] = (stats['invalid_packets'] / total) * 100
        
        return stats
