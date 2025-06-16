import socket
import select
import logging
import threading
import time
from collections import deque
from app import db
from flow_processor import FlowProcessor
from config import NETFLOW_PORT, SFLOW_PORT, MAX_PACKET_SIZE, BUFFER_SIZE
import config

logger = logging.getLogger(__name__)

class FlowReceiver:
    """
    Receives NetFlow and sFlow data from network devices
    """
    
    def __init__(self):
        self.running = False
        self.flow_processor = FlowProcessor()
        self.buffer = deque(maxlen=BUFFER_SIZE)
        self.processing_thread = None
        self.receive_threads = []
        self.sockets = {}
        
    def start(self):
        """Start the flow receiver services"""
        if self.running:
            logger.warning("Flow receiver is already running")
            return
        
        self.running = True
        
        # Start a thread for processing the buffer
        self.processing_thread = threading.Thread(target=self._process_buffer)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start receiver threads for NetFlow and sFlow
        self._start_receiver(config.NETFLOW_PORT, 'netflow')
        self._start_receiver(config.SFLOW_PORT, 'sflow')
        
        logger.info(f"Flow receiver started on ports {config.NETFLOW_PORT} (NetFlow) and {config.SFLOW_PORT} (sFlow)")
    
    def stop(self):
        """Stop the flow receiver services"""
        self.running = False
        
        # Close all sockets
        for sock in self.sockets.values():
            sock.close()
        
        # Clear sockets and threads
        self.sockets.clear()
        self.receive_threads.clear()
        
        logger.info("Flow receiver stopped")
    
    def _start_receiver(self, port, flow_type):
        """
        Start a receiver for a specific flow type
        
        Args:
            port (int): Port to listen on
            flow_type (str): Flow type (netflow, sflow)
        """
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind the socket to the port
            sock.bind(('0.0.0.0', port))
            self.sockets[flow_type] = sock
            
            # Start a thread to receive data
            thread = threading.Thread(target=self._receive_data, args=(sock, port, flow_type))
            thread.daemon = True
            thread.start()
            
            self.receive_threads.append(thread)
            logger.info(f"Started {flow_type} receiver on port {port}")
            
        except Exception as e:
            logger.error(f"Error starting {flow_type} receiver on port {port}: {str(e)}")
    
    def _receive_data(self, sock, port, flow_type):
        """
        Receive data from a socket and add it to the buffer
        
        Args:
            sock (socket): Socket to receive from
            port (int): Port the socket is bound to
            flow_type (str): Flow type (netflow, sflow)
        """
        while self.running:
            try:
                # Use select to avoid blocking indefinitely
                ready, _, _ = select.select([sock], [], [], 1.0)
                
                if ready:
                    data, addr = sock.recvfrom(config.MAX_PACKET_SIZE)
                    
                    # Add to buffer for processing
                    self.buffer.append((data, addr, port))
                    
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error receiving {flow_type} data: {str(e)}")
    
    def _process_buffer(self):
        """Process items in the buffer"""
        while self.running:
            try:
                # Process items in the buffer
                while self.buffer and self.running:
                    data, addr, port = self.buffer.popleft()
                    
                    # Process the packet
                    self.flow_processor.process_packet(data, addr, port)
                
                # Sleep a short time if buffer is empty
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error processing flow data: {str(e)}")
                time.sleep(1)  # Sleep longer on error
    
    def get_stats(self):
        """
        Get receiver statistics
        
        Returns:
            dict: Statistics about the receiver
        """
        return {
            'running': self.running,
            'buffer_size': len(self.buffer),
            'buffer_capacity': self.buffer.maxlen,
            'active_sockets': len(self.sockets),
            'ports': {
                'netflow': config.NETFLOW_PORT,
                'sflow': config.SFLOW_PORT
            }
        }
