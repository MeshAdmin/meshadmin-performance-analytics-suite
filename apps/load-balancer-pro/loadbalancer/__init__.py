# Load balancer package
import threading

# Import core modules
from loadbalancer.core import LBManager, BackendServer, ConnectionInfo
from loadbalancer.stats import StatsCollector
from loadbalancer.ui import LoadBalancerUI
from loadbalancer.syslog import syslog_forwarder, LogLevel
from loadbalancer.analytics import analytics_collector

# Create a global shutdown event for graceful termination
GLOBAL_SHUTDOWN_EVENT = threading.Event()

__version__ = "1.1.0"
__all__ = [
    "LBManager", 
    "StatsCollector", 
    "LoadBalancerUI", 
    "BackendServer", 
    "ConnectionInfo",
    "syslog_forwarder", 
    "LogLevel", 
    "analytics_collector", 
    "GLOBAL_SHUTDOWN_EVENT",
    "create_test_servers", 
    "test_client", 
    "load_test"
]

# Test utilities
def create_test_servers(num_servers=2, base_port=8081):
    """Create test backend servers for demonstration."""
    import socket
    import threading
    import time
    import random
    import logging
    
    logger = logging.getLogger("loadbalancer.test_servers")
    
    def handle_client(client_sock, server_id):
        """Handle a client connection in the test server."""
        try:
            # Read data from the client
            data = client_sock.recv(4096)
            if data:
                # Simulate some processing delay
                time.sleep(random.uniform(0.01, 0.1))
                
                # Prepare a response
                response = f"Response from Server {server_id}\n"
                if data.strip():
                    response += f"Received: {data.decode('utf-8')}\n"
                
                # Send the response
                client_sock.sendall(response.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error handling client in test server {server_id}: {e}")
        finally:
            client_sock.close()
    
    def server_loop(port, server_id):
        """Main loop for the test server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', port))
            server_socket.listen(5)
            server_socket.settimeout(0.5)  # Allow checking for shutdown
            
            logger.info(f"Server {server_id} listening on port {port}")
            
            while not GLOBAL_SHUTDOWN_EVENT.is_set():
                try:
                    client_sock, client_addr = server_socket.accept()
                    
                    # Handle client in a new thread
                    client_thread = threading.Thread(
                        target=handle_client,
                        args=(client_sock, server_id),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not GLOBAL_SHUTDOWN_EVENT.is_set():
                        logger.error(f"Error accepting connection on test server {server_id}: {e}")
        except Exception as e:
            logger.error(f"Error in test server {server_id}: {e}")
        finally:
            server_socket.close()
            logger.info(f"Test server {server_id} stopped")
    
    # Start test servers
    server_threads = []
    server_ports = []
    
    for i in range(num_servers):
        port = base_port + i
        server_thread = threading.Thread(
            target=server_loop,
            args=(port, i+1),
            daemon=True
        )
        server_thread.start()
        
        server_threads.append(server_thread)
        server_ports.append(port)
        
    return server_threads, server_ports

def test_client(lb_port, message="Test message", num_messages=1):
    """Test client to send messages to the load balancer."""
    import socket
    import time
    
    results = []
    
    for i in range(num_messages):
        try:
            # Connect to the load balancer
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect(('127.0.0.1', lb_port))
            
            # Send a message
            send_message = f"{message} #{i+1}"
            sock.sendall(send_message.encode('utf-8'))
            
            # Receive response
            data = sock.recv(4096)
            response = data.decode('utf-8')
            
            # Record result
            results.append({
                "message": send_message,
                "response": response,
                "time": time.time()
            })
            
        except Exception as e:
            results.append({
                "message": send_message if 'send_message' in locals() else f"{message} #{i+1}",
                "error": str(e),
                "time": time.time()
            })
        finally:
            if 'sock' in locals():
                sock.close()
                
    return results

def load_test(lb_port, num_clients=5, messages_per_client=3):
    """Run a load test with multiple clients."""
    import threading
    import time
    
    all_results = []
    client_threads = []
    
    for i in range(num_clients):
        client_results = []
        
        def run_client(client_id):
            results = test_client(
                lb_port, 
                f"Load test client {client_id}",
                messages_per_client
            )
            client_results.extend(results)
        
        thread = threading.Thread(
            target=run_client,
            args=(i+1,),
            daemon=True
        )
        thread.start()
        client_threads.append((thread, client_results))
    
    # Wait for all clients to finish
    for thread, results in client_threads:
        thread.join(timeout=10.0)
        all_results.extend(results)
    
    return all_results
