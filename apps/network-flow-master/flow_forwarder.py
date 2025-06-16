import socket
import threading
import logging
import time
import queue
import ssl
import ipaddress
import json
from app import db
from models import ForwardTarget, FlowData
import config

logger = logging.getLogger(__name__)

class FlowForwarder:
    """
    Forwards NetFlow and sFlow data to other collectors
    """
    
    def __init__(self):
        """Initialize the flow forwarder"""
        self.running = False
        self.forward_queue = queue.Queue(maxsize=config.BUFFER_SIZE)
        self.targets = {}  # Maps target ID to socket
        self.lock = threading.Lock()
    
    def start(self):
        """Start the flow forwarder service"""
        if self.running:
            logger.warning("Flow forwarder is already running")
            return
        
        self.running = True
        
        # Start thread for forwarding
        thread = threading.Thread(target=self._forward_flows)
        thread.daemon = True
        thread.start()
        
        logger.info("Flow forwarder started")
    
    def stop(self):
        """Stop the flow forwarder service"""
        self.running = False
        
        # Close all target sockets
        with self.lock:
            for target_id, sock in self.targets.items():
                sock.close()
            
            self.targets.clear()
        
        logger.info("Flow forwarder stopped")
    
    def add_target(self, target_id):
        """
        Add a forwarding target
        
        Args:
            target_id (int): ID of the target in the database
        """
        target = ForwardTarget.query.get(target_id)
        if not target:
            logger.error(f"Forward target not found: {target_id}")
            return False
        
        if not target.active:
            logger.warning(f"Forward target {target_id} is inactive")
            return False
        
        # Create a socket for the target
        try:
            if target.protocol.lower() == 'udp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:  # tcp
                # Create base TCP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # If TLS is enabled, wrap the socket
                if target.use_tls:
                    try:
                        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                        
                        # If certificates are provided, use them
                        if target.tls_cert and target.tls_key:
                            context.load_cert_chain(certfile=target.tls_cert, keyfile=target.tls_key)
                        
                        # Wrap the socket with SSL/TLS
                        sock = context.wrap_socket(sock, server_hostname=target.ip_address)
                        logger.info(f"TLS enabled for target {target.name}")
                    except Exception as tls_error:
                        logger.error(f"TLS configuration error for target {target.name}: {str(tls_error)}")
                        return False
                
                # Connect the socket
                sock.connect((target.ip_address, target.port))
            
            with self.lock:
                self.targets[target_id] = sock
            
            protocol_type = "TLS TCP" if target.use_tls else target.protocol.upper()
            logger.info(f"Added forward target {target.name} ({target.ip_address}:{target.port}, {protocol_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding forward target {target_id}: {str(e)}")
            return False
    
    def remove_target(self, target_id):
        """
        Remove a forwarding target
        
        Args:
            target_id (int): ID of the target to remove
        """
        with self.lock:
            if target_id in self.targets:
                self.targets[target_id].close()
                del self.targets[target_id]
                logger.info(f"Removed forward target {target_id}")
                return True
            else:
                logger.warning(f"Forward target {target_id} not found")
                return False
    
    def forward_flow(self, flow_data, raw_data=None):
        """
        Queue a flow for forwarding
        
        Args:
            flow_data (FlowData): Flow data record
            raw_data (bytes): Raw flow packet data (if available)
        """
        if not self.running:
            return False
        
        try:
            # Add to forward queue
            self.forward_queue.put_nowait((flow_data.id, raw_data))
            return True
        except queue.Full:
            logger.warning("Forward queue is full, dropping flow")
            return False
    
    def _forward_flows(self):
        """Process and forward flows from the queue"""
        while self.running:
            try:
                # Get an item from the queue
                try:
                    flow_id, raw_data = self.forward_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Load the flow data
                flow_data = FlowData.query.get(flow_id)
                if not flow_data:
                    logger.warning(f"Flow data not found: {flow_id}")
                    continue
                
                # Forward to matching targets
                with self.lock:
                    for target_id, sock in list(self.targets.items()):
                        target = ForwardTarget.query.get(target_id)
                        if not target or not target.active:
                            # Target was removed or deactivated
                            self.remove_target(target_id)
                            continue
                        
                        # Check if the flow type matches the target
                        if self._flow_matches_target(flow_data, target):
                            self._send_to_target(sock, target, flow_data, raw_data)
                
                self.forward_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error forwarding flow: {str(e)}")
                time.sleep(1)  # Sleep longer on error
    
    def _flow_matches_target(self, flow_data, target):
        """
        Check if a flow matches a target's criteria
        
        Args:
            flow_data (FlowData): Flow data record
            target (ForwardTarget): Forward target
        
        Returns:
            bool: True if the flow matches, False otherwise
        """
        # Check flow type (netflow, sflow)
        if target.flow_type and not flow_data.flow_type.startswith(target.flow_type.lower()):
            return False
        
        # Check flow version
        if target.flow_version and target.flow_version not in flow_data.flow_type:
            return False
        
        # === Basic Filters ===
        
        # Check source IP filter (CIDR supported)
        if target.filter_src_ip and not self._ip_matches_filter(flow_data.src_ip, target.filter_src_ip):
            return False
        
        # Check destination IP filter (CIDR supported)
        if target.filter_dst_ip and not self._ip_matches_filter(flow_data.dst_ip, target.filter_dst_ip):
            return False
        
        # Check protocol filter
        if target.filter_protocol and not self._protocol_matches_filter(flow_data.protocol, target.filter_protocol):
            return False
        
        # === Advanced Filters ===
        
        # Check source port range
        if ((target.filter_src_port_min is not None and flow_data.src_port < target.filter_src_port_min) or
            (target.filter_src_port_max is not None and flow_data.src_port > target.filter_src_port_max)):
            return False
        
        # Check destination port range
        if ((target.filter_dst_port_min is not None and flow_data.dst_port < target.filter_dst_port_min) or
            (target.filter_dst_port_max is not None and flow_data.dst_port > target.filter_dst_port_max)):
            return False
        
        # Check Type of Service (ToS)
        if target.filter_tos and flow_data.tos is not None:
            tos_values = [int(x.strip()) for x in target.filter_tos.split(',') if x.strip().isdigit()]
            if tos_values and flow_data.tos not in tos_values:
                return False
        
        # Check bytes range
        if ((target.filter_bytes_min is not None and flow_data.bytes < target.filter_bytes_min) or
            (target.filter_bytes_max is not None and flow_data.bytes > target.filter_bytes_max)):
            return False
        
        # Check packets range
        if ((target.filter_packets_min is not None and flow_data.packets < target.filter_packets_min) or
            (target.filter_packets_max is not None and flow_data.packets > target.filter_packets_max)):
            return False
        
        # Check custom filter rules (if any)
        if target.filter_custom_rules and not self._check_custom_filter_rules(flow_data, target.filter_custom_rules):
            return False
        
        return True
        
    def _ip_matches_filter(self, ip_address, filter_value):
        """
        Check if an IP address matches a filter value
        
        Args:
            ip_address (str): IP address to check
            filter_value (str): Filter value (IP address or CIDR notation)
        
        Returns:
            bool: True if the IP matches the filter, False otherwise
        """
        try:
            # Check if the filter is a CIDR
            if '/' in filter_value:
                network = ipaddress.ip_network(filter_value, strict=False)
                ip_obj = ipaddress.ip_address(ip_address)
                return ip_obj in network
            else:
                # Direct IP comparison
                return ip_address == filter_value
        except ValueError:
            # If the IP or CIDR is invalid
            logger.warning(f"Invalid IP filter value: {filter_value}")
            return False
            
    def _protocol_matches_filter(self, protocol, filter_value):
        """
        Check if a protocol matches a filter value
        
        Args:
            protocol (int): Protocol number
            filter_value (str): Comma-separated list of protocols (numbers or names)
        
        Returns:
            bool: True if the protocol matches the filter, False otherwise
        """
        # Protocol name to number mapping
        protocol_map = {
            'icmp': 1,
            'tcp': 6,
            'udp': 17,
            'gre': 47,
            'esp': 50,
            'ah': 51,
            'ospf': 89
        }
        
        # Split the filter by commas
        protocol_filters = filter_value.split(',')
        
        # Convert protocol names to numbers
        for p_filter in protocol_filters:
            p_filter = p_filter.strip().lower()
            
            # If it's a name, convert to number
            if p_filter in protocol_map:
                if protocol == protocol_map[p_filter]:
                    return True
            else:
                # Try to convert to int
                try:
                    if protocol == int(p_filter):
                        return True
                except ValueError:
                    continue
        
        return False
        
    def _check_custom_filter_rules(self, flow_data, custom_rules):
        """
        Apply custom filter rules to flow data
        
        Args:
            flow_data (FlowData): Flow data record
            custom_rules (dict): Custom filter rules defined in JSON
        
        Returns:
            bool: True if flow matches all custom rules, False otherwise
        """
        try:
            # If rules is a string (from database), convert to dict
            if isinstance(custom_rules, str):
                import json
                custom_rules = json.loads(custom_rules)
            
            # Check if there are conditions to evaluate
            if 'conditions' not in custom_rules:
                logger.warning("Custom filter rules missing 'conditions' key")
                return True  # No conditions means pass-through
            
            # Determine logical operation for combining conditions
            # Default is AND (all conditions must match)
            operator = custom_rules.get('operator', 'and').lower()
            
            # Convert flow data to a dictionary that can be used for condition matching
            flow_dict = {
                'src_ip': flow_data.src_ip,
                'dst_ip': flow_data.dst_ip,
                'src_port': flow_data.src_port,
                'dst_port': flow_data.dst_port,
                'protocol': flow_data.protocol,
                'tos': flow_data.tos,
                'bytes': flow_data.bytes,
                'packets': flow_data.packets,
                'flow_type': flow_data.flow_type
            }
            
            # Loop through all conditions
            matches = []
            for condition in custom_rules['conditions']:
                if 'field' not in condition or 'operator' not in condition or 'value' not in condition:
                    logger.warning("Custom filter condition missing required keys")
                    continue
                
                field = condition['field']
                cond_op = condition['operator']
                value = condition['value']
                
                # Skip if field not in flow data
                if field not in flow_dict:
                    logger.warning(f"Custom filter field not found: {field}")
                    matches.append(False)
                    continue
                
                # Get the field value from flow data
                flow_value = flow_dict[field]
                
                # Skip if flow value is None and we're not checking for equality
                if flow_value is None and cond_op != 'eq' and cond_op != 'ne':
                    matches.append(False)
                    continue
                
                # Apply the operator
                if cond_op == 'eq':  # Equal
                    matches.append(flow_value == value)
                elif cond_op == 'ne':  # Not equal
                    matches.append(flow_value != value)
                elif cond_op == 'gt':  # Greater than
                    matches.append(flow_value > value)
                elif cond_op == 'lt':  # Less than
                    matches.append(flow_value < value)
                elif cond_op == 'ge':  # Greater than or equal
                    matches.append(flow_value >= value)
                elif cond_op == 'le':  # Less than or equal
                    matches.append(flow_value <= value)
                elif cond_op == 'in':  # In a list of values
                    if isinstance(value, list):
                        matches.append(flow_value in value)
                    else:
                        matches.append(False)
                elif cond_op == 'contains':  # String contains
                    if isinstance(flow_value, str) and isinstance(value, str):
                        matches.append(value in flow_value)
                    else:
                        matches.append(False)
                else:
                    logger.warning(f"Unknown custom filter operator: {cond_op}")
                    matches.append(False)
            
            # If no conditions were actually evaluated, pass through
            if not matches:
                return True
            
            # Apply the logical operator to all condition results
            if operator == 'and':
                return all(matches)
            elif operator == 'or':
                return any(matches)
            elif operator == 'not':
                return not any(matches)
            else:
                logger.warning(f"Unknown logical operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error in custom filter evaluation: {str(e)}")
            return False  # On error, fail safe by not forwarding
    
    def _send_to_target(self, sock, target, flow_data, raw_data):
        """
        Send a flow to a target
        
        Args:
            sock (socket): Socket to use for sending
            target (ForwardTarget): Forward target
            flow_data (FlowData): Flow data record
            raw_data (bytes): Raw flow packet data (if available)
        """
        try:
            # If we have the raw data, use it
            if raw_data:
                if target.protocol.lower() == 'udp':
                    sock.sendto(raw_data, (target.ip_address, target.port))
                else:  # tcp
                    sock.sendall(raw_data)
                
                logger.debug(f"Forwarded raw flow data to {target.name} ({target.ip_address}:{target.port})")
                
                # Log successful forwarding
                self._log_forward_result(target.id, success=True, flow_type=flow_data.flow_type, flow_version=flow_data.flow_version)
                return
            
            # Otherwise, we need to reconstruct the flow
            # This would require knowledge of the specific flow format
            # For now, just log that we don't have raw data
            logger.warning(f"Cannot forward flow {flow_data.id} to {target.name}: No raw data available")
            
            # Log failed forwarding
            self._log_forward_result(target.id, success=False, flow_type=flow_data.flow_type, 
                                    flow_version=flow_data.flow_version, 
                                    error="No raw data available for forwarding")
            
        except Exception as e:
            logger.error(f"Error sending to target {target.name}: {str(e)}")
            
            # Log failed forwarding
            self._log_forward_result(target.id, success=False, flow_type=flow_data.flow_type, 
                                    flow_version=flow_data.flow_version, 
                                    error=str(e))
            
            # If it's a connection error, try to reconnect for TCP
            if target.protocol.lower() == 'tcp':
                try:
                    sock.close()
                    new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    
                    # Apply TLS if configured
                    if target.use_tls:
                        try:
                            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                            
                            # If certificates are provided, use them
                            if target.tls_cert and target.tls_key:
                                context.load_cert_chain(certfile=target.tls_cert, keyfile=target.tls_key)
                            
                            # Wrap the socket with SSL/TLS
                            new_sock = context.wrap_socket(new_sock, server_hostname=target.ip_address)
                            logger.info(f"TLS re-enabled for target {target.name}")
                        except Exception as tls_error:
                            logger.error(f"TLS configuration error during reconnection to {target.name}: {str(tls_error)}")
                            self.remove_target(target.id)
                            return
                    
                    # Connect the socket
                    new_sock.connect((target.ip_address, target.port))
                    
                    with self.lock:
                        self.targets[target.id] = new_sock
                    
                    protocol_type = "TLS TCP" if target.use_tls else "TCP"
                    logger.info(f"Reconnected to target {target.name} using {protocol_type}")
                    
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect to target {target.name}: {str(reconnect_error)}")
                    self.remove_target(target.id)
    
    def _log_forward_result(self, target_id, success=True, flow_type=None, flow_version=None, error=None):
        """
        Log the result of a forwarding attempt
        
        Args:
            target_id (int): ID of the target
            success (bool): Whether the forwarding was successful
            flow_type (str): Type of flow (netflow, sflow)
            flow_version (str): Version of flow
            error (str): Error message if forwarding failed
        """
        try:
            from app import db
            from models import ForwardLog
            from datetime import datetime, timedelta
            
            # Check if there's an existing log entry for this target and period
            # We'll group by hour to avoid creating too many records
            now = datetime.utcnow()
            hour_start = datetime(now.year, now.month, now.day, now.hour)
            
            # Try to find an existing log for this period
            log_entry = ForwardLog.query.filter(
                ForwardLog.target_id == target_id,
                ForwardLog.timestamp >= hour_start,
                ForwardLog.flow_type == flow_type,
                ForwardLog.flow_version == flow_version
            ).first()
            
            if log_entry:
                # Update existing log
                if success:
                    log_entry.success_count += 1
                else:
                    log_entry.failure_count += 1
                    log_entry.error_message = error  # Update with most recent error
            else:
                # Create new log
                log_entry = ForwardLog(
                    target_id=target_id,
                    flow_type=flow_type,
                    flow_version=flow_version,
                    success_count=1 if success else 0,
                    failure_count=0 if success else 1,
                    error_message=error if not success else None
                )
                db.session.add(log_entry)
            
            db.session.commit()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error logging forward result: {str(e)}")
            # Continue without logging stats - this shouldn't disrupt the main flow

    def get_stats(self):
        """
        Get forwarder statistics
        
        Returns:
            dict: Statistics about the forwarder including:
            - running: bool indicating if the forwarder is running
            - queue_size: current size of the forwarding queue
            - queue_capacity: maximum capacity of the forwarding queue
            - active_targets: number of targets with active connections
            - total_targets: total number of targets configured as active
            - forwarded_flows: total number of flows forwarded
            - dropped_flows: total number of flows dropped
        """
        with self.lock:
            active_targets = len(self.targets)
            
        # Get the total counts from the database
        from app import db
        from models import ForwardTarget, ForwardLog
        
        try:
            total_targets = ForwardTarget.query.filter_by(active=True).count()
            
            # Get forwarded and dropped counts from logs (if available)
            forwarded_flows = db.session.query(db.func.sum(ForwardLog.success_count)).scalar() or 0
            dropped_flows = db.session.query(db.func.sum(ForwardLog.failure_count)).scalar() or 0
            
            # Get targets with details
            targets_query = ForwardTarget.query.all()
            targets_detail = []
            
            for target in targets_query:
                target_dict = {
                    'id': target.id,
                    'name': target.name,
                    'address': f"{target.ip_address}:{target.port}",
                    'protocol': target.protocol,
                    'active': target.active,
                    'connected': target.id in self.targets,
                    'use_tls': target.use_tls if hasattr(target, 'use_tls') else False
                }
                targets_detail.append(target_dict)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting forwarder stats from database: {str(e)}")
            total_targets = 0
            forwarded_flows = 0
            dropped_flows = 0
            targets_detail = []
        
        return {
            'running': self.running,
            'queue_size': self.forward_queue.qsize(),
            'queue_capacity': self.forward_queue.maxsize,
            'active_targets': active_targets,
            'total_targets': total_targets,
            'forwarded_flows': forwarded_flows,
            'dropped_flows': dropped_flows,
            'targets': targets_detail
        }
