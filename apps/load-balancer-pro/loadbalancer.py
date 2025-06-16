import socket
import threading
import time
import uuid
import logging
import queue
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer")

class ConnectionInfo:
    """Class to store information about active connections."""
    
    def __init__(self, conn_id, source, destination, start_time):
        self.id = conn_id
        self.source = source
        self.destination = destination
        self.start_time = start_time
        self.bytes_sent = 0
        self.bytes_received = 0
        self.active = True
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source": self.source,
            "destination": self.destination,
            "start_time": self.start_time.strftime("%H:%M:%S"),
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "active": self.active
        }
        
    def __str__(self):
        return f"ID:{self.id[:8]} | {self.source} -> {self.destination} | {self.start_time.strftime('%H:%M:%S')}"

class LBManager:
    """Manager class for the load balancer."""
    
    def __init__(self):
        self._active_conns = {}  # Dictionary of active connections
        self._backends = []  # List of backend servers
        self._backend_index = 0  # Current index for round-robin
        self._lock = threading.RLock()  # Lock for thread safety
        self._running = False  # Flag to indicate if the load balancer is running
        self._listener_thread = None  # Thread for accepting connections
        self._stop_event = threading.Event()  # Event to signal stop
        self._statistics = {
            "total_connections": 0,
            "active_connections": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "start_time": None,
            "connection_history": []  # Limited history of connections
        }
    
    def add_connection(self, conn):
        """Add a new connection to the active list."""
        with self._lock:
            self._active_conns[conn.id] = conn
            self._statistics["total_connections"] += 1
            self._statistics["active_connections"] += 1
    
    def remove_connection(self, conn_id):
        """Remove a connection by its ID."""
        with self._lock:
            if conn_id in self._active_conns:
                conn = self._active_conns[conn_id]
                conn.active = False
                
                # Update statistics
                self._statistics["active_connections"] -= 1
                self._statistics["bytes_sent"] += conn.bytes_sent
                self._statistics["bytes_received"] += conn.bytes_received
                
                # Store in history (limit to 100 entries)
                self._statistics["connection_history"].append(conn.to_dict())
                if len(self._statistics["connection_history"]) > 100:
                    self._statistics["connection_history"].pop(0)
                
                # Remove from active connections
                del self._active_conns[conn_id]
    
    def list_connections(self):
        """Return a list of all active connections."""
        with self._lock:
            return list(self._active_conns.values())
    
    def get_statistics(self):
        """Get current statistics."""
        with self._lock:
            stats = self._statistics.copy()
            stats["active_connections"] = len(self._active_conns)
            
            # Calculate uptime if running
            if stats["start_time"]:
                stats["uptime"] = (datetime.now() - stats["start_time"]).total_seconds()
            else:
                stats["uptime"] = 0
                
            return stats
    
    def pick_backend(self):
        """Pick a backend server using round-robin algorithm."""
        with self._lock:
            if not self._backends:
                raise ValueError("No backends available")
            
            backend = self._backends[self._backend_index % len(self._backends)]
            self._backend_index += 1
            
            # Parse host and port
            try:
                host, port = backend.split(":")
                return host, port
            except ValueError:
                raise ValueError(f"Invalid backend format: {backend}")
    
    def start_listener(self, listen_port, backends):
        """Start the load balancer listener."""
        with self._lock:
            if self._running:
                raise RuntimeError("Load balancer is already running")
            
            self._backends = backends
            self._backend_index = 0
            self._running = True
            self._stop_event.clear()
            self._statistics["start_time"] = datetime.now()
            
            self._listener_thread = threading.Thread(
                target=self._listener_loop, 
                args=(listen_port,),
                daemon=True
            )
            self._listener_thread.start()
            logger.info(f"Load balancer listening on port {listen_port}")
            return True
    
    def stop_listener(self):
        """Stop the load balancer."""
        with self._lock:
            if not self._running:
                return False
            
            logger.info("Stopping load balancer...")
            self._stop_event.set()
            self._running = False
            
            # Wait for the listener thread to finish
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=2.0)
            
            # Close all active connections
            for conn_id in list(self._active_conns.keys()):
                self.remove_connection(conn_id)
                
            return True
    
    def is_running(self):
        """Check if the load balancer is running."""
        with self._lock:
            return self._running
    
    def _listener_loop(self, listen_port):
        """Main listener loop to accept connections."""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', listen_port))
            server_socket.settimeout(0.5)  # Set timeout for accept() to allow checking stop_event
            server_socket.listen(5)
            
            while not self._stop_event.is_set():
                try:
                    client_sock, addr = server_socket.accept()
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_sock, addr),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
            
        except Exception as e:
            logger.error(f"Error in listener loop: {e}")
        finally:
            if 'server_socket' in locals():
                server_socket.close()
            self._running = False
    
    def _handle_client(self, client_sock, addr):
        """Handle a client connection."""
        conn_id = str(uuid.uuid4())
        source = f"{addr[0]}:{addr[1]}"
        
        try:
            # Pick a backend
            host, port = self.pick_backend()
            destination = f"{host}:{port}"
            
            # Connect to the backend
            backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_sock.connect((host, int(port)))
            
            # Create connection info
            conn_info = ConnectionInfo(
                conn_id=conn_id,
                source=source,
                destination=destination,
                start_time=datetime.now()
            )
            self.add_connection(conn_info)
            
            # Set up communication threads
            client_to_backend = threading.Thread(
                target=self._forward_data,
                args=(client_sock, backend_sock, conn_info, True),
                daemon=True
            )
            backend_to_client = threading.Thread(
                target=self._forward_data,
                args=(backend_sock, client_sock, conn_info, False),
                daemon=True
            )
            
            client_to_backend.start()
            backend_to_client.start()
            
            # Wait for both threads to complete
            client_to_backend.join()
            backend_to_client.join()
            
        except Exception as e:
            logger.error(f"Error handling client {conn_id}: {e}")
        finally:
            # Clean up
            self.remove_connection(conn_id)
            try:
                client_sock.close()
            except:
                pass
            try:
                if 'backend_sock' in locals():
                    backend_sock.close()
            except:
                pass
    
    def _forward_data(self, src, dst, conn, client_to_backend):
        """Forward data between source and destination sockets."""
        try:
            buffer_size = 8192
            src.settimeout(60.0)  # 60 second timeout
            
            while not self._stop_event.is_set():
                try:
                    data = src.recv(buffer_size)
                    if not data:
                        break
                    
                    dst.sendall(data)
                    
                    # Update statistics
                    if client_to_backend:
                        conn.bytes_sent += len(data)
                    else:
                        conn.bytes_received += len(data)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error forwarding data: {e}")
                    break
        except Exception as e:
            logger.error(f"Error in forward loop: {e}")

# Global event for clean shutdown
GLOBAL_SHUTDOWN_EVENT = threading.Event()

# Create test backend servers for demonstration
def create_test_servers(ports=[8081, 8082]):
    """
    Create simple backend servers for testing.
    Returns the server threads and a list of server ports.
    """
    def handle_client(conn, addr, server_id):
        logger.info(f"Server {server_id}: New connection from {addr}")
        conn.send(f"Hello from backend server {server_id}\n".encode())
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                logger.info(f"Server {server_id} received: {data.decode().strip()}")
                conn.send(f"Server {server_id} echo: {data.decode()}".encode())
        except:
            pass
        finally:
            conn.close()
            logger.info(f"Server {server_id}: Connection closed from {addr}")

    def server_thread(port, server_id):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(5)
        server.settimeout(0.5)  # Allow for clean shutdown
        logger.info(f"Server {server_id} listening on port {port}")
        
        while not GLOBAL_SHUTDOWN_EVENT.is_set():
            try:
                conn, addr = server.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr, server_id))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in test server {server_id}: {e}")
                break
                
        server.close()
        logger.info(f"Server {server_id} stopped")
    
    # Create and start test servers
    threads = []
    
    for i, port in enumerate(ports):
        thread = threading.Thread(target=server_thread, args=(port, i+1))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    return threads, ports

# Simple test client for demonstration
def test_client(lb_port, message="Hello from test client", num_messages=5):
    """Create a test client that connects to the load balancer and sends messages."""
    results = []
    
    try:
        # Connect to the load balancer
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('localhost', lb_port))
        
        # Receive the welcome message
        welcome = client.recv(1024).decode()
        results.append(f"Received: {welcome}")
        
        # Send some test messages
        for i in range(num_messages):
            msg = f"{message} #{i+1}"
            results.append(f"Sending: {msg}")
            client.send(msg.encode())
            
            # Receive the response
            response = client.recv(1024).decode()
            results.append(f"Received: {response}")
            
            # Add a small delay between messages
            time.sleep(0.5)
        
        # Close the connection
        client.close()
        results.append("Client connection closed")
        
    except Exception as e:
        results.append(f"Client error: {str(e)}")
    
    return results

# Load testing function
def load_test(lb_port, num_clients=5, messages_per_client=3):
    """Perform a load test by creating multiple client connections."""
    results = []
    
    def client_thread(client_id):
        try:
            client_results = test_client(lb_port, f"Client {client_id} message", messages_per_client)
            # No need to do anything with the results in this thread
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
    
    # Create and start client threads
    threads = []
    for i in range(num_clients):
        thread = threading.Thread(target=client_thread, args=(i+1,))
        thread.daemon = True
        threads.append(thread)
    
    # Start all client threads
    results.append(f"Starting {num_clients} test clients connecting to port {lb_port}...")
    for thread in threads:
        thread.start()
        # Add a small delay between client starts
        time.sleep(0.2)
    
    # Wait for all clients to finish
    for thread in threads:
        thread.join()
    
    results.append("Load test completed")
    return results