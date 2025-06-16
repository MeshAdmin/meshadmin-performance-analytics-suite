import socket
import struct
import random
import time
import ipaddress
import logging
import threading
import json
from datetime import datetime, timedelta
from app import db, app
from models import SimulationConfig, FlowTemplate
from config import DEFAULT_SIMULATION_PORT

logger = logging.getLogger(__name__)

class FlowSimulator:
    """
    Simulates NetFlow and sFlow traffic for testing and demonstration
    """
    
    def __init__(self):
        """Initialize the flow simulator"""
        self.running_simulations = {}
        self.lock = threading.Lock()
    
    def start_simulation(self, simulation_id):
        """
        Start a simulation based on a configuration
        
        Args:
            simulation_id (int): ID of the simulation configuration
        """
        sim_config = None
        try:
            # Use application context for database access
            with app.app_context():
                # Get the simulation configuration
                sim_config = SimulationConfig.query.get(simulation_id)
                if not sim_config:
                    logger.error(f"Simulation config not found: {simulation_id}")
                    return
            
                # Create the appropriate simulator based on flow type
                if sim_config.flow_type.lower() == 'netflow':
                    if sim_config.flow_version == '5':
                        simulator = NetFlowV5Simulator(sim_config)
                    elif sim_config.flow_version == '9':
                        simulator = NetFlowV9Simulator(sim_config)
                    else:
                        logger.error(f"Unsupported NetFlow version: {sim_config.flow_version}")
                        self._update_simulation_status(sim_config, 'error', 'Unsupported NetFlow version')
                        return
                elif sim_config.flow_type.lower() == 'sflow':
                    if sim_config.flow_version in ['4', '5']:
                        simulator = SFlowSimulator(sim_config)
                    else:
                        logger.error(f"Unsupported sFlow version: {sim_config.flow_version}")
                        self._update_simulation_status(sim_config, 'error', 'Unsupported sFlow version')
                        return
                else:
                    logger.error(f"Unsupported flow type: {sim_config.flow_type}")
                    self._update_simulation_status(sim_config, 'error', 'Unsupported flow type')
                    return
                
                # Store the simulator and start it
                with self.lock:
                    self.running_simulations[simulation_id] = simulator
                
                # Start the simulation in a new thread
                thread = threading.Thread(target=self._run_simulation, args=(simulation_id,))
                thread.daemon = True
                thread.start()
                
                logger.info(f"Started simulation {simulation_id}")
            
        except Exception as e:
            logger.error(f"Error starting simulation {simulation_id}: {str(e)}")
            if sim_config:
                with app.app_context():
                    self._update_simulation_status(sim_config, 'error', str(e))
    
    def _run_simulation(self, simulation_id):
        """
        Run a simulation
        
        Args:
            simulation_id (int): ID of the simulation configuration
        """
        sim_config = None
        try:
            with app.app_context():
                sim_config = SimulationConfig.query.get(simulation_id)
                if not sim_config:
                    logger.error(f"Simulation config not found: {simulation_id}")
                    return
            
                # Get the simulator
                with self.lock:
                    simulator = self.running_simulations.get(simulation_id)
                
                if not simulator:
                    logger.error(f"Simulator not found for simulation {simulation_id}")
                    return
                
                # Update simulation status
                self._update_simulation_status(sim_config, 'running')
                
                # Run the simulator
                simulator.run()
                
                # Mark simulation as completed
                self._update_simulation_status(sim_config, 'completed')
            
        except Exception as e:
            logger.error(f"Error running simulation {simulation_id}: {str(e)}")
            if sim_config:
                with app.app_context():
                    self._update_simulation_status(sim_config, 'error', str(e))
        
        # Clean up
        with self.lock:
            if simulation_id in self.running_simulations:
                del self.running_simulations[simulation_id]
    
    def stop_simulation(self, simulation_id):
        """
        Stop a running simulation
        
        Args:
            simulation_id (int): ID of the simulation to stop
        """
        with self.lock:
            simulator = self.running_simulations.get(simulation_id)
            if simulator:
                simulator.stop()
                del self.running_simulations[simulation_id]
                
                # Update simulation status
                with app.app_context():
                    sim_config = SimulationConfig.query.get(simulation_id)
                    if sim_config:
                        self._update_simulation_status(sim_config, 'stopped')
                
                logger.info(f"Stopped simulation {simulation_id}")
            else:
                logger.warning(f"Simulation {simulation_id} not found or already stopped")
    
    def _update_simulation_status(self, sim_config, status, error_message=None):
        """
        Update the status of a simulation
        
        Args:
            sim_config (SimulationConfig): Simulation configuration
            status (str): New status
            error_message (str, optional): Error message if status is 'error'
        """
        sim_config.status = status
        
        if status in ['completed', 'stopped', 'error']:
            sim_config.end_time = datetime.utcnow()
        
        if error_message:
            sim_config.error_message = error_message
        
        db.session.commit()
    
    def get_simulation_status(self, simulation_id):
        """
        Get the status of a simulation
        
        Args:
            simulation_id (int): ID of the simulation
        
        Returns:
            dict: Simulation status information
        """
        with app.app_context():
            sim_config = SimulationConfig.query.get(simulation_id)
            if not sim_config:
                return {'error': 'Simulation not found'}
            
            is_running = simulation_id in self.running_simulations
            
            return {
                'id': sim_config.id,
                'status': sim_config.status,
                'flow_type': sim_config.flow_type,
                'flow_version': sim_config.flow_version,
                'start_time': sim_config.start_time.isoformat() if sim_config.start_time else None,
                'end_time': sim_config.end_time.isoformat() if sim_config.end_time else None,
                'is_running': is_running,
                'error_message': sim_config.error_message
            }
    
    def get_all_simulations(self):
        """
        Get status of all simulations
        
        Returns:
            list: List of simulation statuses
        """
        with app.app_context():
            simulations = SimulationConfig.query.all()
            return [self.get_simulation_status(sim.id) for sim in simulations]


class BaseFlowSimulator:
    """Base class for flow simulators"""
    
    def __init__(self, sim_config):
        """
        Initialize the base flow simulator
        
        Args:
            sim_config (SimulationConfig): Simulation configuration
        """
        self.sim_config = sim_config
        self.running = False
        self.target_ip = '127.0.0.1'  # Default to localhost
        self.target_port = DEFAULT_SIMULATION_PORT
        self.packets_per_second = sim_config.packets_per_second
        self.duration = sim_config.duration
        self.start_time = datetime.utcnow()
        
        # Load template data if available
        self.template_data = {}
        if sim_config.template_id:
            with app.app_context():
                template = FlowTemplate.query.get(sim_config.template_id)
                if template:
                    try:
                        self.template_data = json.loads(template.template_data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid template data: {template.template_data}")
                        self.template_data = {}
    
    def run(self):
        """Run the simulation"""
        self.running = True
        self.start_time = datetime.utcnow()
        
        # Create a UDP socket for sending flows
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Calculate how many packets to send and at what interval
        total_packets = self.packets_per_second * self.duration
        interval = 1.0 / self.packets_per_second if self.packets_per_second > 0 else 0
        
        packets_sent = 0
        start = time.time()
        
        logger.info(f"Starting flow simulation: {self.sim_config.flow_type} v{self.sim_config.flow_version}")
        logger.info(f"Target: {self.target_ip}:{self.target_port}")
        logger.info(f"Rate: {self.packets_per_second} packets/sec for {self.duration} seconds")
        
        while self.running and (time.time() - start) < self.duration and packets_sent < total_packets:
            # Generate and send a flow packet
            packet = self.generate_packet()
            if packet:
                sock.sendto(packet, (self.target_ip, self.target_port))
                packets_sent += 1
            
            # Sleep to maintain the desired packet rate
            time.sleep(interval)
        
        sock.close()
        self.running = False
        
        logger.info(f"Flow simulation completed. Sent {packets_sent} packets in {time.time() - start:.2f} seconds.")
    
    def stop(self):
        """Stop the simulation"""
        self.running = False
    
    def generate_packet(self):
        """
        Generate a flow packet
        
        Returns:
            bytes: Generated packet data
        """
        # Implement in subclasses
        raise NotImplementedError("Subclasses must implement generate_packet")
    
    def generate_random_ip(self):
        """
        Generate a random IP address
        
        Returns:
            str: Random IP address
        """
        return str(ipaddress.IPv4Address(random.randint(0, 2**32 - 1)))
    
    def generate_random_port(self):
        """
        Generate a random port number
        
        Returns:
            int: Random port number
        """
        return random.randint(1024, 65535)


class NetFlowV5Simulator(BaseFlowSimulator):
    """NetFlow v5 simulator"""
    
    def generate_packet(self):
        """
        Generate a NetFlow v5 packet
        
        Returns:
            bytes: NetFlow v5 packet data
        """
        # NetFlow v5 header (24 bytes)
        version = 5
        count = random.randint(1, 30)  # Number of flow records
        sys_uptime = random.randint(0, 2**32 - 1)
        unix_secs = int(time.time())
        unix_nsecs = random.randint(0, 2**32 - 1)
        flow_sequence = random.randint(0, 2**32 - 1)
        engine_type = 0
        engine_id = 0
        sampling_interval = 0
        
        header = struct.pack(
            '!HHIIIIBB',
            version,
            count,
            sys_uptime,
            unix_secs,
            unix_nsecs,
            flow_sequence,
            engine_type,
            engine_id
        ) + struct.pack('!H', sampling_interval)
        
        # Generate flow records
        records = b''
        for _ in range(count):
            # Use template data if available, otherwise generate random
            if self.template_data and 'records' in self.template_data:
                template_record = random.choice(self.template_data['records'])
                src_addr = template_record.get('src_ip', self.generate_random_ip())
                dst_addr = template_record.get('dst_ip', self.generate_random_ip())
                next_hop = template_record.get('next_hop', '0.0.0.0')
                input_if = template_record.get('input_if', random.randint(0, 2**16 - 1))
                output_if = template_record.get('output_if', random.randint(0, 2**16 - 1))
                packets = template_record.get('packets', random.randint(1, 1000))
                bytes_value = template_record.get('bytes', random.randint(40, 1500) * packets)
                first_time = template_record.get('first_time', sys_uptime - random.randint(1000, 10000))
                last_time = template_record.get('last_time', sys_uptime)
                src_port = template_record.get('src_port', self.generate_random_port())
                dst_port = template_record.get('dst_port', self.generate_random_port())
                tcp_flags = template_record.get('tcp_flags', random.randint(0, 255))
                protocol = template_record.get('protocol', random.choice([6, 17]))  # TCP or UDP
                tos = template_record.get('tos', 0)
                src_as = template_record.get('src_as', 0)
                dst_as = template_record.get('dst_as', 0)
                src_mask = template_record.get('src_mask', 24)
                dst_mask = template_record.get('dst_mask', 24)
            else:
                src_addr = self.generate_random_ip()
                dst_addr = self.generate_random_ip()
                next_hop = '0.0.0.0'
                input_if = random.randint(0, 2**16 - 1)
                output_if = random.randint(0, 2**16 - 1)
                packets = random.randint(1, 1000)
                bytes_value = random.randint(40, 1500) * packets
                first_time = sys_uptime - random.randint(1000, 10000)
                last_time = sys_uptime
                src_port = self.generate_random_port()
                dst_port = self.generate_random_port()
                tcp_flags = random.randint(0, 255)
                protocol = random.choice([6, 17])  # TCP or UDP
                tos = 0
                src_as = 0
                dst_as = 0
                src_mask = 24
                dst_mask = 24
            
            # Convert IP addresses to bytes
            src_addr_bytes = socket.inet_aton(src_addr)
            dst_addr_bytes = socket.inet_aton(dst_addr)
            next_hop_bytes = socket.inet_aton(next_hop)
            
            # Pack the record (48 bytes)
            record = (
                src_addr_bytes +
                dst_addr_bytes +
                next_hop_bytes +
                struct.pack('!H', input_if) +
                struct.pack('!H', output_if) +
                struct.pack('!I', packets) +
                struct.pack('!I', bytes_value) +
                struct.pack('!I', first_time) +
                struct.pack('!I', last_time) +
                struct.pack('!H', src_port) +
                struct.pack('!H', dst_port) +
                b'\x00' +  # padding
                struct.pack('!B', tcp_flags) +
                struct.pack('!B', protocol) +
                struct.pack('!B', tos) +
                struct.pack('!H', src_as) +
                struct.pack('!H', dst_as) +
                struct.pack('!B', src_mask) +
                struct.pack('!B', dst_mask) +
                b'\x00\x00'  # padding
            )
            
            records += record
        
        # Combine header and records
        return header + records


class NetFlowV9Simulator(BaseFlowSimulator):
    """NetFlow v9 simulator"""
    
    def __init__(self, sim_config):
        super().__init__(sim_config)
        self.template_id = 256
        self.flow_sequence = 0
    
    def generate_packet(self):
        """
        Generate a NetFlow v9 packet
        
        Returns:
            bytes: NetFlow v9 packet data
        """
        # NetFlow v9 header (20 bytes)
        version = 9
        count = 2  # Template set + data set
        sys_uptime = random.randint(0, 2**32 - 1)
        unix_secs = int(time.time())
        self.flow_sequence += 1
        source_id = 0
        
        header = struct.pack(
            '!HHIIII',
            version,
            count,
            sys_uptime,
            unix_secs,
            self.flow_sequence,
            source_id
        )
        
        # Template set header (4 bytes)
        template_set_id = 0
        template_set_length = 4 + 4 + (4 * 15)  # header + template header + 15 fields
        template_set_header = struct.pack('!HH', template_set_id, template_set_length)
        
        # Template record
        template_header = struct.pack('!HH', self.template_id, 15)  # template ID and field count
        
        # Template fields
        template_fields = b''
        for field_type, field_length in [
            (1, 4),    # IN_BYTES
            (2, 4),    # IN_PKTS
            (4, 1),    # PROTOCOL
            (5, 1),    # TOS
            (6, 1),    # TCP_FLAGS
            (7, 2),    # L4_SRC_PORT
            (8, 4),    # IPV4_SRC_ADDR
            (9, 1),    # SRC_MASK
            (10, 2),   # INPUT_SNMP
            (11, 2),   # L4_DST_PORT
            (12, 4),   # IPV4_DST_ADDR
            (13, 1),   # DST_MASK
            (14, 2),   # OUTPUT_SNMP
            (15, 4),   # IPV4_NEXT_HOP
            (21, 4)    # LAST_SWITCHED
        ]:
            template_fields += struct.pack('!HH', field_type, field_length)
        
        template_set = template_set_header + template_header + template_fields
        
        # Data set header
        data_set_id = self.template_id
        
        # Generate flow records
        records = b''
        flow_count = random.randint(1, 20)
        for _ in range(flow_count):
            # Use template data if available, otherwise generate random
            if self.template_data and 'records' in self.template_data:
                template_record = random.choice(self.template_data['records'])
                in_bytes = template_record.get('bytes', random.randint(40, 1500))
                in_pkts = template_record.get('packets', random.randint(1, 100))
                protocol = template_record.get('protocol', random.choice([6, 17]))
                tos = template_record.get('tos', 0)
                tcp_flags = template_record.get('tcp_flags', random.randint(0, 255))
                src_port = template_record.get('src_port', self.generate_random_port())
                src_addr = template_record.get('src_ip', self.generate_random_ip())
                src_mask = template_record.get('src_mask', 24)
                input_if = template_record.get('input_if', random.randint(0, 2**16 - 1))
                dst_port = template_record.get('dst_port', self.generate_random_port())
                dst_addr = template_record.get('dst_ip', self.generate_random_ip())
                dst_mask = template_record.get('dst_mask', 24)
                output_if = template_record.get('output_if', random.randint(0, 2**16 - 1))
                next_hop = template_record.get('next_hop', '0.0.0.0')
                last_switched = template_record.get('last_time', sys_uptime)
            else:
                in_bytes = random.randint(40, 1500)
                in_pkts = random.randint(1, 100)
                protocol = random.choice([6, 17])
                tos = 0
                tcp_flags = random.randint(0, 255)
                src_port = self.generate_random_port()
                src_addr = self.generate_random_ip()
                src_mask = 24
                input_if = random.randint(0, 2**16 - 1)
                dst_port = self.generate_random_port()
                dst_addr = self.generate_random_ip()
                dst_mask = 24
                output_if = random.randint(0, 2**16 - 1)
                next_hop = '0.0.0.0'
                last_switched = sys_uptime
            
            # Convert IP addresses to bytes
            src_addr_bytes = socket.inet_aton(src_addr)
            dst_addr_bytes = socket.inet_aton(dst_addr)
            next_hop_bytes = socket.inet_aton(next_hop)
            
            # Pack the record
            record = (
                struct.pack('!I', in_bytes) +
                struct.pack('!I', in_pkts) +
                struct.pack('!B', protocol) +
                struct.pack('!B', tos) +
                struct.pack('!B', tcp_flags) +
                struct.pack('!H', src_port) +
                src_addr_bytes +
                struct.pack('!B', src_mask) +
                struct.pack('!H', input_if) +
                struct.pack('!H', dst_port) +
                dst_addr_bytes +
                struct.pack('!B', dst_mask) +
                struct.pack('!H', output_if) +
                next_hop_bytes +
                struct.pack('!I', last_switched)
            )
            
            records += record
        
        # Calculate data set length
        record_length = 4 + 4 + 1 + 1 + 1 + 2 + 4 + 1 + 2 + 2 + 4 + 1 + 2 + 4 + 4  # sum of field lengths
        data_set_length = 4 + (flow_count * record_length)  # header + records
        data_set_header = struct.pack('!HH', data_set_id, data_set_length)
        
        data_set = data_set_header + records
        
        # Combine header, template set, and data set
        return header + template_set + data_set


class SFlowSimulator(BaseFlowSimulator):
    """sFlow simulator (v4 and v5)"""
    
    def generate_packet(self):
        """
        Generate an sFlow packet
        
        Returns:
            bytes: sFlow packet data
        """
        # sFlow header
        version = int(self.sim_config.flow_version)
        ip_version = 1  # IPv4
        agent_ip = socket.inet_aton('192.168.1.1')  # Example agent IP
        sub_agent_id = 0
        sequence_number = random.randint(0, 2**32 - 1)
        uptime = random.randint(0, 2**32 - 1)
        num_samples = 1
        
        header = struct.pack(
            '!IIIIII',
            version,
            ip_version,
            0,  # Agent IP (high bytes for IPv6, zeros for IPv4)
            int.from_bytes(agent_ip, byteorder='big'),  # Agent IP (low bytes)
            sub_agent_id,
            sequence_number,
        ) + struct.pack('!II', uptime, num_samples)
        
        # Sample header
        sample_type = 1  # Flow sample
        sample_data_length = 64  # Simplified estimate
        sample_header = struct.pack('!II', sample_type, sample_data_length)
        
        # Sample data
        sequence_number = random.randint(0, 2**32 - 1)
        source_id = random.randint(0, 2**32 - 1)
        sampling_rate = 1000
        sample_pool = random.randint(0, 2**32 - 1)
        drops = 0
        input_if = random.randint(0, 2**32 - 1)
        output_if = random.randint(0, 2**32 - 1)
        flow_records = 1
        
        sample_data = struct.pack(
            '!IIIIIIII',
            sequence_number,
            source_id,
            sampling_rate,
            sample_pool,
            drops,
            input_if,
            output_if,
            flow_records
        )
        
        # Flow record header
        flow_format = 1  # Raw packet flow
        flow_data_length = 32  # Simplified estimate
        flow_record_header = struct.pack('!II', flow_format, flow_data_length)
        
        # Flow data
        protocol = random.choice([6, 17])  # TCP or UDP
        frame_length = random.randint(64, 1500)
        stripped = 0
        header_size = 14 + 20 + (20 if protocol == 6 else 8)  # Ethernet + IP + TCP/UDP
        
        flow_data = struct.pack('!III', protocol, frame_length, stripped)
        
        # Header data (simplified Ethernet + IP + TCP/UDP packet)
        src_mac = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55])
        dst_mac = bytes([0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB])
        ethertype = struct.pack('!H', 0x0800)  # IPv4
        
        # IP header
        ip_header = bytes([0x45, 0x00])  # Version 4, IHL 5, TOS 0
        ip_length = struct.pack('!H', 40 if protocol == 6 else 28)  # 20 IP + (20 TCP or 8 UDP)
        ip_id = struct.pack('!H', random.randint(0, 2**16 - 1))
        ip_flags = struct.pack('!H', 0)
        ip_ttl = 64
        ip_proto = protocol
        ip_checksum = 0
        src_ip = socket.inet_aton(self.generate_random_ip())
        dst_ip = socket.inet_aton(self.generate_random_ip())
        
        # Transport header (TCP or UDP)
        src_port = self.generate_random_port()
        dst_port = self.generate_random_port()
        if protocol == 6:  # TCP
            seq_num = random.randint(0, 2**32 - 1)
            ack_num = random.randint(0, 2**32 - 1)
            flags = random.randint(0, 2**8 - 1)
            window = random.randint(0, 2**16 - 1)
            checksum = 0
            urgent = 0
            transport_header = (
                struct.pack('!H', src_port) +
                struct.pack('!H', dst_port) +
                struct.pack('!I', seq_num) +
                struct.pack('!I', ack_num) +
                struct.pack('!B', (5 << 4)) +  # Data offset 5, reserved bits 0
                struct.pack('!B', flags) +
                struct.pack('!H', window) +
                struct.pack('!H', checksum) +
                struct.pack('!H', urgent)
            )
        else:  # UDP
            udp_length = struct.pack('!H', 8)  # UDP header only
            checksum = 0
            transport_header = (
                struct.pack('!H', src_port) +
                struct.pack('!H', dst_port) +
                udp_length +
                struct.pack('!H', checksum)
            )
        
        # Combine Ethernet, IP, and Transport headers
        header_data = src_mac + dst_mac + ethertype
        header_data += ip_header + ip_length + ip_id + ip_flags
        header_data += bytes([ip_ttl, ip_proto]) + struct.pack('!H', ip_checksum)
        header_data += src_ip + dst_ip
        header_data += transport_header
        
        # Ensure header_data is at least header_size bytes
        if len(header_data) < header_size:
            header_data += b'\x00' * (header_size - len(header_data))
        
        flow_data += struct.pack('!I', len(header_data)) + header_data
        
        # Combine all parts
        flow_record = flow_record_header + flow_data
        sample = sample_header + sample_data + flow_record
        
        return header + sample
