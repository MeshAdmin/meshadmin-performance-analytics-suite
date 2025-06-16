"""
Python Load Balancer - Web UI and Core Functionality
This standalone file includes both the load balancer functionality and Flask web UI.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional
import socket
import threading
import time
import uuid
import logging
import queue
import json
import os
import random
import io
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("loadbalancer")

#------------------------------------------------------------------------------
# LOAD BALANCER CORE FUNCTIONALITY
#------------------------------------------------------------------------------

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

class StatsCollector:
    """Collect and process statistics from the load balancer."""
    
    def __init__(self, lb_manager):
        self.lb_manager = lb_manager
        self._lock = threading.RLock()
        self._time_series = {
            "timestamps": [],
            "active_connections": [],
            "bytes_sent": [],
            "bytes_received": [],
        }
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        self._interval = 1.0  # collection interval in seconds
    
    def start(self, interval=1.0):
        """Start collecting statistics."""
        with self._lock:
            if self._running:
                return
            
            self._interval = interval
            self._running = True
            self._stop_event.clear()
            
            self._thread = threading.Thread(
                target=self._collector_loop,
                daemon=True
            )
            self._thread.start()
    
    def stop(self):
        """Stop collecting statistics."""
        with self._lock:
            if not self._running:
                return
            
            self._stop_event.set()
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
    
    def is_running(self):
        """Check if the collector is running."""
        with self._lock:
            return self._running
    
    def get_time_series(self, timespan=60):
        """Get time series data for plotting."""
        with self._lock:
            if not self._time_series["timestamps"]:
                return {
                    "timestamps": [],
                    "active_connections": [],
                    "bytes_sent": [],
                    "bytes_received": [],
                }
            
            # Filter to the requested timespan
            now = datetime.now()
            cutoff = now - timedelta(seconds=timespan)
            
            # Convert timestamps to strings for JSON serialization
            timestamps_str = [ts.strftime("%H:%M:%S") for ts in self._time_series["timestamps"]]
            
            # Find the index of the first element to include
            start_idx = 0
            for i, ts in enumerate(self._time_series["timestamps"]):
                if ts >= cutoff:
                    start_idx = i
                    break
            
            return {
                "timestamps": timestamps_str[start_idx:],
                "active_connections": self._time_series["active_connections"][start_idx:],
                "bytes_sent": self._time_series["bytes_sent"][start_idx:],
                "bytes_received": self._time_series["bytes_received"][start_idx:],
            }
    
    def _collector_loop(self):
        """Background thread to collect statistics."""
        while not self._stop_event.is_set():
            try:
                if self.lb_manager.is_running():
                    with self._lock:
                        # Get current stats
                        stats = self.lb_manager.get_statistics()
                        
                        # Record time series
                        now = datetime.now()
                        self._time_series["timestamps"].append(now)
                        self._time_series["active_connections"].append(stats["active_connections"])
                        self._time_series["bytes_sent"].append(stats["bytes_sent"])
                        self._time_series["bytes_received"].append(stats["bytes_received"])
                        
                        # Limit the size of our time series to avoid memory growth
                        max_points = 3600  # Keep at most 1 hour of 1-second data
                        if len(self._time_series["timestamps"]) > max_points:
                            self._time_series["timestamps"] = self._time_series["timestamps"][-max_points:]
                            self._time_series["active_connections"] = self._time_series["active_connections"][-max_points:]
                            self._time_series["bytes_sent"] = self._time_series["bytes_sent"][-max_points:]
                            self._time_series["bytes_received"] = self._time_series["bytes_received"][-max_points:]
            except Exception as e:
                logger.error(f"Error in stats collector: {e}")
            
            # Wait for the next collection interval
            time.sleep(self._interval)

class LBManager:
    """Manager class for the load balancer."""
    
    # Load balancing algorithm constants
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    IP_HASH = "ip_hash"
    
    def __init__(self):
        self._active_conns = {}  # Dictionary of active connections
        self._backends = []  # List of backend servers
        self._backend_index = 0  # Current index for round-robin
        self._lock = threading.RLock()  # Lock for thread safety
        self._running = False  # Flag to indicate if the load balancer is running
        self._listener_thread = None  # Thread for accepting connections
        self._stop_event = threading.Event()  # Event to signal stop
        self._stats_collector = None  # Will be set later
        self._listen_port = None  # Current listen port
        self._algorithm = self.ROUND_ROBIN  # Default algorithm
        
        # Health check configuration
        self._health_check_enabled = True
        self._health_check_interval = 10  # seconds
        self._health_check_timeout = 2  # seconds
        self._health_check_path = "/"
        self._unhealthy_threshold = 3
        self._healthy_threshold = 2
        self._health_check_thread = None
        self._backend_health = {}  # Health status for each backend
        
        self._statistics = {
            "total_connections": 0,
            "active_connections": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "start_time": None,
            "connection_history": []  # Limited history of connections
        }
    
    def set_stats_collector(self, collector):
        """Set the stats collector instance."""
        self._stats_collector = collector
    
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
            
            # Add listen port and backends to stats
            stats["listen_port"] = self._listen_port
            stats["backends"] = self._backends.copy() if self._backends else []
                
            return stats
    
    def pick_backend(self):
        """Pick a backend server using the selected algorithm."""
        with self._lock:
            if not self._backends:
                raise ValueError("No backends available")
            
            # Get healthy backends
            healthy_backends = []
            if self._health_check_enabled:
                for backend in self._backends:
                    is_healthy = self._backend_health.get(backend, {}).get("healthy", True)
                    if is_healthy:
                        healthy_backends.append(backend)
            
            # If no healthy backends, use all of them
            backends_to_use = healthy_backends if healthy_backends else self._backends
            
            # Select backend based on algorithm
            if self._algorithm == self.ROUND_ROBIN or not backends_to_use:
                # Round-robin selection (default)
                backend = backends_to_use[self._backend_index % len(backends_to_use)]
                self._backend_index += 1
            elif self._algorithm == self.LEAST_CONNECTIONS:
                # Least connections selection
                backend_connections = {}
                for backend in backends_to_use:
                    connection_count = 0
                    for conn in self._active_conns.values():
                        if conn.destination == backend:
                            connection_count += 1
                    backend_connections[backend] = connection_count
                
                # Get backend with minimum connections
                backend = min(backend_connections.items(), key=lambda x: x[1])[0]
            elif self._algorithm == self.RANDOM:
                # Random selection
                import random
                backend = random.choice(backends_to_use)
            elif self._algorithm == self.IP_HASH:
                # Dummy implementation for now - just use round-robin
                # In a real implementation, we'd use the client IP to hash
                backend = backends_to_use[self._backend_index % len(backends_to_use)]
                self._backend_index += 1
            else:
                # Fallback to round-robin
                backend = backends_to_use[self._backend_index % len(backends_to_use)]
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
            self._listen_port = listen_port
            
            # Start stats collector if available
            if self._stats_collector:
                self._stats_collector.start()
            
            # Start health checker if enabled
            if self._health_check_enabled:
                self._start_health_checker()
            
            self._listener_thread = threading.Thread(
                target=self._listener_loop, 
                args=(listen_port,),
                daemon=True
            )
            self._listener_thread.start()
            logger.info(f"Load balancer listening on port {listen_port} with algorithm: {self._algorithm}")
            return True
    
    def stop_listener(self):
        """Stop the load balancer."""
        with self._lock:
            if not self._running:
                return False
            
            logger.info("Stopping load balancer...")
            self._stop_event.set()
            self._running = False
            
            # Stop stats collector if available
            if self._stats_collector:
                self._stats_collector.stop()
            
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
    
    def get_listen_port(self):
        """Get the current listen port."""
        with self._lock:
            return self._listen_port
    
    def get_backends(self):
        """Get the current backend list."""
        with self._lock:
            return self._backends.copy()
    
    def get_time_series_data(self, timespan=60):
        """Get time series data for graphing."""
        if self._stats_collector:
            return self._stats_collector.get_time_series(timespan)
        return None
        
    def set_algorithm(self, algorithm):
        """Set the load balancing algorithm."""
        with self._lock:
            if algorithm in [self.ROUND_ROBIN, self.LEAST_CONNECTIONS, 
                          self.WEIGHTED_ROUND_ROBIN, self.RANDOM, self.IP_HASH]:
                self._algorithm = algorithm
                logger.info(f"Load balancing algorithm set to {algorithm}")
                return True
            else:
                logger.warning(f"Unknown algorithm: {algorithm}, using round_robin")
                self._algorithm = self.ROUND_ROBIN
                return False
    
    def get_algorithm(self):
        """Get the current load balancing algorithm."""
        with self._lock:
            return self._algorithm
            
    def set_health_check_config(self, interval=10, timeout=2, path="/", 
                              unhealthy_threshold=3, healthy_threshold=2, enabled=True):
        """Configure health checking parameters."""
        with self._lock:
            self._health_check_enabled = enabled
            self._health_check_interval = interval
            self._health_check_timeout = timeout
            self._health_check_path = path
            self._unhealthy_threshold = unhealthy_threshold
            self._healthy_threshold = healthy_threshold
            
            logger.info(f"Health checks {'enabled' if enabled else 'disabled'}")
            if enabled:
                logger.info(f"Health check config: interval={interval}s, timeout={timeout}s, " +
                          f"path={path}, unhealthy_threshold={unhealthy_threshold}, " +
                          f"healthy_threshold={healthy_threshold}")
            
            # Start health checker if running
            if self._running and enabled and not self._health_check_thread:
                self._start_health_checker()
            
            return True
    
    def get_backend_servers(self):
        """Get information about backend servers."""
        with self._lock:
            backend_info = []
            
            for backend in self._backends:
                try:
                    host, port = backend.split(":")
                    healthy = self._backend_health.get(backend, {}).get("healthy", True)
                    response_time = self._backend_health.get(backend, {}).get("response_time", 0)
                    
                    backend_info.append({
                        "host": host,
                        "port": int(port),
                        "healthy": healthy,
                        "response_time": response_time,
                        "connections": sum(1 for conn in self._active_conns.values() 
                                         if conn.destination == backend)
                    })
                except ValueError:
                    # Skip invalid backends
                    pass
            
            return backend_info
    
    def _start_health_checker(self):
        """Start the health checker thread."""
        if not self._health_check_enabled:
            return
            
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("Health checker started")
    
    def _health_check_loop(self):
        """Main loop for health checking."""
        while self._running and self._health_check_enabled and not self._stop_event.is_set():
            try:
                # Check all backends
                for backend in self._backends:
                    try:
                        # Initialize health status if not exists
                        if backend not in self._backend_health:
                            self._backend_health[backend] = {
                                "healthy": True,
                                "consecutive_failures": 0,
                                "consecutive_successes": 0,
                                "response_time": 0
                            }
                            
                        # Check health
                        host, port = backend.split(":")
                        start_time = time.time()
                        is_healthy = self._check_backend_health(backend)
                        end_time = time.time()
                        
                        # Update health status
                        health_info = self._backend_health[backend]
                        
                        if is_healthy:
                            health_info["consecutive_successes"] += 1
                            health_info["consecutive_failures"] = 0
                            
                            # Mark as healthy if reached threshold
                            if not health_info["healthy"] and health_info["consecutive_successes"] >= self._healthy_threshold:
                                health_info["healthy"] = True
                                logger.info(f"Backend {backend} is now healthy")
                        else:
                            health_info["consecutive_failures"] += 1
                            health_info["consecutive_successes"] = 0
                            
                            # Mark as unhealthy if reached threshold
                            if health_info["healthy"] and health_info["consecutive_failures"] >= self._unhealthy_threshold:
                                health_info["healthy"] = False
                                logger.warning(f"Backend {backend} is now unhealthy")
                        
                        # Update response time (only for successful checks)
                        if is_healthy:
                            response_time = int((end_time - start_time) * 1000)  # in ms
                            health_info["response_time"] = response_time
                    
                    except Exception as e:
                        logger.error(f"Error checking health of {backend}: {e}")
                
                # Sleep until next check
                time.sleep(self._health_check_interval)
            
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(5)  # Sleep a bit before retrying
    
    def _check_backend_health(self, backend):
        """Check health of a single backend server."""
        try:
            host, port = backend.split(":")
            port = int(port)
            
            # Simple TCP connection check
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self._health_check_timeout)
            s.connect((host, port))
            s.close()
            
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {backend}: {e}")
            return False
    
    def _listener_loop(self, listen_port):
        """Main listener loop to accept connections."""
        server_socket = None
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
            if server_socket:
                server_socket.close()
            self._running = False
    
    def _handle_client(self, client_sock, addr):
        """Handle a client connection."""
        conn_id = str(uuid.uuid4())
        source = f"{addr[0]}:{addr[1]}"
        backend_sock = None
        
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
                if backend_sock:
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

# Global shutdown event for clean shutdown
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
        server = None
        try:
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
        except Exception as e:
            logger.error(f"Error starting test server {server_id}: {e}")
        finally:
            if server:
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
        results.append({
            "message": "Connection established", 
            "response": welcome,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "success": True
        })
        
        # Send some test messages
        for i in range(num_messages):
            msg = f"{message} #{i+1}"
            client.send(msg.encode())
            
            # Receive the response
            response = client.recv(1024).decode()
            results.append({
                "message": msg,
                "response": response,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "success": True
            })
            
            # Add a small delay between messages
            time.sleep(0.5)
        
        # Close the connection
        client.close()
        results.append({
            "message": "Connection closed",
            "response": "Client terminated successfully",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "success": True
        })
        
    except Exception as e:
        results.append({
            "message": "Error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "success": False
        })
    
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
    results.append({
        "message": "Load Test Starting",
        "response": f"Starting {num_clients} test clients connecting to port {lb_port}...",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "success": True
    })
    
    for thread in threads:
        thread.start()
        # Add a small delay between client starts
        time.sleep(0.2)
    
    # Wait for all clients to finish
    for thread in threads:
        thread.join()
    
    results.append({
        "message": "Load Test Complete",
        "response": f"Completed test with {num_clients} clients, {messages_per_client} messages each",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "success": True
    })
    
    return results

#------------------------------------------------------------------------------
# FLASK WEB USER INTERFACE
#------------------------------------------------------------------------------

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Create a singleton for our load balancer
lb_manager = LBManager()
stats_collector = StatsCollector(lb_manager)
lb_manager.set_stats_collector(stats_collector)

test_server_threads = None
test_server_ports = None

# Store test client results in a global variable
test_client_results = []

# Form for configuring the load balancer
class LoadBalancerForm(FlaskForm):
    port = IntegerField('Listen Port', validators=[DataRequired(), NumberRange(min=1024, max=65535)], default=8080)
    backends = TextAreaField('Backend Servers (host:port, one per line)', 
                           validators=[DataRequired()], 
                           default='127.0.0.1:8081\n127.0.0.1:8082')
    
    # Load balancing algorithm options
    algorithm = SelectField('Load Balancing Algorithm', 
                         choices=[
                             ('round_robin', 'Round Robin'),
                             ('least_connections', 'Least Connections'),
                             ('weighted_round_robin', 'Weighted Round Robin'),
                             ('random', 'Random'),
                             ('ip_hash', 'IP Hash')
                         ], 
                         default='round_robin')
    
    # Health check options
    enable_health_checks = BooleanField('Enable Health Checks', default=True)
    health_check_interval = IntegerField('Health Check Interval (seconds)', 
                                     validators=[Optional(), NumberRange(min=1, max=60)], 
                                     default=10)
    health_check_timeout = IntegerField('Health Check Timeout (seconds)', 
                                    validators=[Optional(), NumberRange(min=1, max=10)], 
                                    default=2)
    unhealthy_threshold = IntegerField('Unhealthy Threshold', 
                                   validators=[Optional(), NumberRange(min=1, max=10)], 
                                   default=3,
                                   description="Number of consecutive failures before marking a backend as unhealthy")
    healthy_threshold = IntegerField('Healthy Threshold', 
                                 validators=[Optional(), NumberRange(min=1, max=10)], 
                                 default=2,
                                 description="Number of consecutive successes before marking a backend as healthy again")
                                 
    submit = SubmitField('Start')

class TestClientForm(FlaskForm):
    message = StringField('Test Message', validators=[DataRequired()], default='Hello from test client')
    num_messages = IntegerField('Number of Messages', validators=[DataRequired(), NumberRange(min=1, max=10)], default=3)
    submit = SubmitField('Send Test Messages')

class LoadTestForm(FlaskForm):
    num_clients = IntegerField('Number of Clients', validators=[DataRequired(), NumberRange(min=1, max=20)], default=5)
    messages_per_client = IntegerField('Messages Per Client', validators=[DataRequired(), NumberRange(min=1, max=10)], default=3)
    submit = SubmitField('Run Load Test')

def get_ip_addresses():
    """Get the IP addresses of the server."""
    import socket
    ip_info = {
        'hostname': socket.gethostname(),
        'local_ips': [],
        'public_ip': None
    }
    
    # Get local IPs
    try:
        # Get all local IP addresses
        hostname = socket.gethostname()
        ip_info['local_ips'] = [
            ip for ip in socket.gethostbyname_ex(hostname)[2] 
            if not ip.startswith('127.')
        ]
        
        # Try to add all network interfaces
        import netifaces
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if ip not in ip_info['local_ips'] and not ip.startswith('127.'):
                        ip_info['local_ips'].append(ip)
    except:
        # Fallback method if netifaces is not available
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip not in ip_info['local_ips']:
                ip_info['local_ips'].append(ip)
            s.close()
        except:
            pass
    
    # Try to get public IP
    try:
        import urllib.request
        external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        ip_info['public_ip'] = external_ip
    except:
        # If we can't reach the external service, try another one
        try:
            external_ip = urllib.request.urlopen('https://ifconfig.me/ip').read().decode('utf8')
            ip_info['public_ip'] = external_ip
        except:
            pass
    
    return ip_info

@app.route('/')
def index():
    """Home page with load balancer configuration."""
    start_form = LoadBalancerForm()
    test_form = TestClientForm()
    load_test_form = LoadTestForm()
    
    # Set the current port if running
    listen_port = lb_manager.get_listen_port()
    if listen_port:
        start_form.port.data = listen_port
    
    # Set current backends if running
    backends = lb_manager.get_backends()
    if backends:
        start_form.backends.data = '\n'.join(backends)
    
    # Get stats for display
    stats = lb_manager.get_statistics()
    if stats["start_time"]:
        uptime = datetime.now() - stats["start_time"]
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    else:
        uptime_str = "Not running"
    
    # Format data transferred
    total_bytes = stats["bytes_sent"] + stats["bytes_received"]
    if total_bytes < 1024:
        data_str = f"{total_bytes} B"
    elif total_bytes < 1024 * 1024:
        data_str = f"{total_bytes / 1024:.2f} KB"
    else:
        data_str = f"{total_bytes / (1024 * 1024):.2f} MB"
    
    # For the connections table
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    
    # Get connection history
    history = stats.get("connection_history", [])
    
    # Get network information
    ip_info = get_ip_addresses()
    
    return render_template('index.html', 
                          form=start_form,
                          test_form=test_form,
                          load_test_form=load_test_form,
                          is_running=lb_manager.is_running(),
                          stats=stats,
                          uptime=uptime_str,
                          data_transferred=data_str,
                          connections=connections,
                          history=history,
                          client_results=test_client_results,
                          ip_info=ip_info)

@app.route('/start', methods=['POST'])
def start():
    """Start the load balancer."""
    form = LoadBalancerForm()
    if form.validate_on_submit():
        port = form.port.data
        backends_text = form.backends.data
        backends = [line.strip() for line in backends_text.split('\n') if line.strip()]
        
        if not backends:
            return jsonify({"status": "error", "message": "No backends specified"})
        
        try:
            # Set the load balancing algorithm
            algorithm = form.algorithm.data
            if hasattr(lb_manager, 'set_algorithm'):
                lb_manager.set_algorithm(algorithm)
            
            # Configure health checks
            if hasattr(lb_manager, 'set_health_check_config'):
                enable_health_checks = form.enable_health_checks.data
                health_check_interval = form.health_check_interval.data
                health_check_timeout = form.health_check_timeout.data
                unhealthy_threshold = form.unhealthy_threshold.data
                healthy_threshold = form.healthy_threshold.data
                
                lb_manager.set_health_check_config(
                    interval=health_check_interval,
                    timeout=health_check_timeout,
                    path="/",  # Default path for health check
                    unhealthy_threshold=unhealthy_threshold,
                    healthy_threshold=healthy_threshold,
                    enabled=enable_health_checks
                )
            
            # Start the load balancer
            lb_manager.start_listener(port, backends)
            return redirect(url_for('index'))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return redirect(url_for('index'))

@app.route('/stop')
def stop():
    """Stop the load balancer."""
    lb_manager.stop_listener()
    return redirect(url_for('index'))

@app.route('/test-servers/start')
def start_test_servers():
    """Start test backend servers."""
    global test_server_threads, test_server_ports
    if test_server_threads is None:
        test_server_threads, test_server_ports = create_test_servers()
        return jsonify({"status": "success", "message": f"Test servers started on ports {', '.join(map(str, test_server_ports))}"})
    else:
        return jsonify({"status": "error", "message": "Test servers are already running"})

@app.route('/test-servers/stop')
def stop_test_servers():
    """Stop test backend servers."""
    global test_server_threads, test_server_ports
    if test_server_threads is not None:
        GLOBAL_SHUTDOWN_EVENT.set()
        time.sleep(1)  # Give servers time to shut down
        GLOBAL_SHUTDOWN_EVENT.clear()
        test_server_threads = None
        test_server_ports = None
        return jsonify({"status": "success", "message": "Test servers stopped"})
    else:
        return jsonify({"status": "error", "message": "No test servers are running"})

@app.route('/test-client', methods=['POST'])
def run_test_client():
    """Run a test client."""
    global test_client_results
    form = TestClientForm()
    if form.validate_on_submit():
        if not lb_manager.is_running():
            return jsonify({"status": "error", "message": "Load balancer is not running"})
        
        port = lb_manager.get_listen_port() or request.form.get('lb_port', type=int)
        message = form.message.data
        num_messages = form.num_messages.data
        
        # Run test client in a background thread to avoid blocking
        def run_client():
            global test_client_results
            results = test_client(port, message, num_messages)
            test_client_results = results
        
        client_thread = threading.Thread(target=run_client)
        client_thread.daemon = True
        client_thread.start()
        
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/load-test', methods=['POST'])
def run_load_test():
    """Run a load test with multiple clients."""
    global test_client_results
    form = LoadTestForm()
    if form.validate_on_submit():
        if not lb_manager.is_running():
            return jsonify({"status": "error", "message": "Load balancer is not running"})
        
        port = lb_manager.get_listen_port() or request.form.get('lb_port', type=int)
        num_clients = form.num_clients.data
        messages_per_client = form.messages_per_client.data
        
        # Run load test in a background thread
        def run_test():
            global test_client_results
            results = load_test(port, num_clients, messages_per_client)
            test_client_results = results
        
        test_thread = threading.Thread(target=run_test)
        test_thread.daemon = True
        test_thread.start()
        
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/api/stats')
def get_stats():
    """API endpoint to get current stats."""
    stats = lb_manager.get_statistics()
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    backend_servers = lb_manager.get_backend_servers()
    
    return jsonify({
        "stats": stats,
        "connections": connections,
        "backend_servers": backend_servers,
        "is_running": lb_manager.is_running(),
        "algorithm": lb_manager.get_algorithm()
    })

@app.route('/api/connections')
def get_connections():
    """API endpoint to get current connections."""
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    return jsonify({"connections": connections})

@app.route('/api/plot/health')
def plot_health():
    """Generate a plot of backend health over time."""
    backend_servers = lb_manager.get_backend_servers()
    
    # Create a health dashboard with multiple indicators
    fig = go.Figure()
    
    # Add indicators for each backend server
    total_backends = len(backend_servers)
    if total_backends > 0:
        healthy_backends = sum(1 for backend in backend_servers if backend['healthy'])
        
        # Add health ratio gauge
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=100 * healthy_backends / total_backends if total_backends > 0 else 0,
            title={"text": "Backend Health %"},
            domain={'row': 0, 'column': 0},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#19d3f3"},
                'steps': [
                    {'range': [0, 33], 'color': "#ff0000"},
                    {'range': [33, 66], 'color': "#ffa500"},
                    {'range': [66, 100], 'color': "#00ff00"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ))
        
        # Add individual server status
        for i, backend in enumerate(backend_servers):
            color = "green" if backend['healthy'] else "red"
            symbol = "✓" if backend['healthy'] else "✗"
            response_time = backend.get('response_time', 0)
            
            # Create text display for server status
            status_text = f"{symbol} {backend['host']}:{backend['port']}  •  {response_time}ms"
            
            # Add text annotation
            fig.add_annotation(
                text=status_text,
                x=0.5,
                y=0.7 - (i * 0.1),
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(
                    family="Arial",
                    size=14,
                    color=color
                )
            )
    else:
        # If no backend servers, show empty message
        fig.add_annotation(
            text="No backend servers configured",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                family="Arial",
                size=14
            )
        )
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(50,50,50,0.8)',  # Dark background for dark mode
        font=dict(color='white'),  # White text for dark mode
        plot_bgcolor='rgba(50,50,50,0.3)'    # Dark plot area for dark mode
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/api/client-results')
def get_client_results():
    """API endpoint to get test client results."""
    global test_client_results
    return jsonify({"results": test_client_results})

@app.route('/api/clear-results')
def clear_results():
    """Clear test client results."""
    global test_client_results
    test_client_results = []
    return redirect(url_for('index'))

@app.route('/api/connection/<connection_id>')
def get_connection_details(connection_id):
    """API endpoint to get details about a specific connection."""
    # Find the connection in the active connections
    connections = lb_manager.list_connections()
    connection = next((conn for conn in connections if conn.id == connection_id), None)
    
    if connection:
        # Return the connection details
        return jsonify({
            'status': 'success',
            'connection': {
                'id': connection.id,
                'source': connection.source,
                'destination': connection.destination,
                'start_time': connection.start_time.isoformat(),
                'duration': (datetime.now() - connection.start_time).total_seconds(),
                'bytes_sent': connection.bytes_sent,
                'bytes_received': connection.bytes_received,
            }
        })
    else:
        # For demo purposes, return a mock connection
        mock_connection = {
            'id': connection_id,
            'source': '192.168.1.100:54321',
            'destination': '10.0.0.1:8081',
            'start_time': (datetime.now() - timedelta(seconds=30)).isoformat(),
            'duration': 30,
            'bytes_sent': 15400,
            'bytes_received': 67200
        }
        
        return jsonify({
            'status': 'success',
            'connection': mock_connection
        })

@app.route('/api/logs')
def get_logs():
    """API endpoint to get system logs with filtering."""
    # Extract query parameters
    level = request.args.get('level', 'all')
    timespan = request.args.get('timespan', '24h')
    search = request.args.get('search', '')
    
    # In a real application, we would query actual logs from a database or log files
    # For this demo, we'll generate some mock logs
    
    # Convert timespan to seconds
    seconds = {
        '1h': 3600,
        '6h': 21600,
        '12h': 43200,
        '24h': 86400,
        'all': float('inf')
    }.get(timespan, 86400)
    
    # Generate mock logs
    now = datetime.now()
    mock_logs = []
    
    # Simulated startup logs
    mock_logs.append({
        'timestamp': (now - timedelta(seconds=seconds - 100)).isoformat(),
        'level': 'INFO',
        'source': 'System',
        'message': 'Load balancer starting up'
    })
    
    # Random log entries
    for i in range(30):
        # Random timestamp within the timespan
        ts = now - timedelta(seconds=random.randint(1, min(seconds, 86400)))
        
        # Random level
        level_choice = random.choice(['DEBUG', 'INFO', 'INFO', 'INFO', 'WARNING', 'ERROR'])
        
        # Source based on level
        source_map = {
            'DEBUG': 'Core',
            'INFO': random.choice(['Server', 'LoadBalancer', 'Core']),
            'WARNING': random.choice(['Server', 'Core']),
            'ERROR': random.choice(['Server', 'Core', 'Network'])
        }
        source = source_map.get(level_choice, 'System')
        
        # Message based on level and source
        messages = {
            'DEBUG': [
                f'Connection pool size: {random.randint(1, 10)}',
                f'Backend selection: Round-robin picked server {random.randint(1, 3)}',
                f'Socket buffer size: {random.randint(1024, 8192)} bytes',
                f'Connection timeout set to {random.randint(10, 60)} seconds'
            ],
            'INFO': {
                'Server': [
                    f'New connection from 192.168.1.{random.randint(1, 255)}:{random.randint(10000, 60000)}',
                    f'Connection closed after {random.randint(1, 30)} seconds',
                    f'Data transferred: {random.randint(1024, 102400)} bytes',
                    f'Server started on port {random.randint(8000, 9000)}'
                ],
                'LoadBalancer': [
                    f'Started load balancer on port {random.randint(8000, 9000)}',
                    f'Registered new backend: 10.0.0.{random.randint(1, 10)}:{random.randint(8000, 9000)}',
                    f'Load balancer stopped',
                    f'Configuration updated'
                ],
                'Core': [
                    f'Thread pool size: {random.randint(2, 8)}',
                    f'Using round-robin algorithm',
                    f'Statistics collector started',
                    f'Memory usage: {random.randint(10, 100)}MB'
                ]
            },
            'WARNING': [
                f'Slow connection detected (RTT: {random.randint(100, 500)}ms)',
                f'High CPU usage: {random.randint(70, 95)}%',
                f'Connection pool near capacity: {random.randint(80, 95)}%',
                f'Backend server response time degraded: {random.randint(200, 800)}ms'
            ],
            'ERROR': [
                f'Connection refused to backend 10.0.0.{random.randint(1, 10)}:{random.randint(8000, 9000)}',
                f'Socket error: Connection reset by peer',
                f'Out of memory error',
                f'Failed to bind to port {random.randint(8000, 9000)}: Address already in use'
            ]
        }
        
        if level_choice == 'INFO':
            message = random.choice(messages[level_choice][source])
        else:
            message = random.choice(messages[level_choice])
        
        mock_logs.append({
            'timestamp': ts.isoformat(),
            'level': level_choice,
            'source': source,
            'message': message
        })
    
    # Sort logs by timestamp (newest first)
    mock_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Filter by level if specified
    if level != 'all':
        mock_logs = [log for log in mock_logs if log['level'] == level]
    
    # Filter by search term if specified
    if search:
        search = search.lower()
        mock_logs = [log for log in mock_logs if 
                      search in log['message'].lower() or 
                      search in log['source'].lower()]
    
    return jsonify({
        'status': 'success',
        'logs': mock_logs
    })

@app.route('/api/logs/download')
def download_logs():
    """Download logs as a CSV file."""
    # This would normally fetch the actual logs, but we'll use the mock data
    level = request.args.get('level', 'all')
    timespan = request.args.get('timespan', '24h')
    search = request.args.get('search', '')
    
    # Get the logs (reusing the same logic as the get_logs endpoint)
    logs_response = get_logs()
    logs_data = json.loads(logs_response.get_data(as_text=True))
    logs = logs_data['logs']
    
    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Timestamp', 'Level', 'Source', 'Message'])
    
    # Write log entries
    for log in logs:
        writer.writerow([
            log['timestamp'],
            log['level'],
            log['source'],
            log['message']
        ])
    
    # Prepare the response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=loadbalancer_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

@app.route('/api/plot/connections')
def plot_connections():
    """Generate a plot of connections over time."""
    # Get connection data
    stats = lb_manager.get_statistics()
    connections = [conn.to_dict() for conn in lb_manager.list_connections()]
    
    # Simple plot for now - this would be better with time series data
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode = "number",
        value = len(connections),
        title = {"text": "Active Connections"},
        domain = {'row': 0, 'column': 0}
    ))
    
    fig.add_trace(go.Indicator(
        mode = "number",
        value = stats["total_connections"],
        title = {"text": "Total Connections"},
        domain = {'row': 0, 'column': 1}
    ))
    
    fig.update_layout(
        grid = {'rows': 1, 'columns': 2},
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(50,50,50,0.8)',  # Dark background for dark mode
        font=dict(color='white'),  # White text for dark mode
        plot_bgcolor='rgba(50,50,50,0.3)'    # Dark plot area for dark mode
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/api/plot/analytics')
def plot_analytics():
    """Generate analytics dashboard with historical data."""
    # Get timespan from query parameter (default: 1 hour)
    timespan = request.args.get('timespan', 3600, type=int)
    
    # Create dashboard using simulated historical data
    # Since we don't have real historical data, we'll create a mock dashboard for visualization
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Connection History", "Response Time", "Traffic Volume", "Backend Health"),
        specs=[
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "bar"}, {"type": "indicator"}]
        ]
    )
    
    # Create timestamps for historical data (past hour)
    now = datetime.now()
    timestamps = [now - timedelta(seconds=i*60) for i in range(60)][::-1]  # Last 60 minutes
    timestamps_str = [ts.strftime('%H:%M') for ts in timestamps]
    
    # Mock connection data
    connections_data = [random.randint(0, 10) for _ in range(60)]
    fig.add_trace(
        go.Scatter(x=timestamps_str, y=connections_data, mode='lines+markers', name='Connections'),
        row=1, col=1
    )
    
    # Mock response time data
    response_times = [random.randint(10, 200) for _ in range(60)]
    fig.add_trace(
        go.Scatter(x=timestamps_str, y=response_times, mode='lines', name='Response Time (ms)'),
        row=1, col=2
    )
    
    # Mock traffic volume by backend
    backends = ['Backend 1', 'Backend 2', 'Backend 3']
    traffic_volume = [random.randint(100, 1000) for _ in range(len(backends))]
    fig.add_trace(
        go.Bar(x=backends, y=traffic_volume, name='Traffic Volume'),
        row=2, col=1
    )
    
    # Mock health status gauge
    healthy_backends = random.randint(0, len(backends))
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=100 * healthy_backends / len(backends),
            title={"text": "Healthy Backends %"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#19d3f3"},
                'steps': [
                    {'range': [0, 33], 'color': "#ff0000"},
                    {'range': [33, 66], 'color': "#ffa500"},
                    {'range': [66, 100], 'color': "#00ff00"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
        paper_bgcolor='rgba(50,50,50,0.8)',  # Dark background for dark mode
        font=dict(color='white'),  # White text for dark mode
        plot_bgcolor='rgba(50,50,50,0.3)'    # Dark plot area for dark mode
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/shutdown')
def shutdown():
    """Shut down the load balancer and the web server."""
    # Stop the load balancer
    if lb_manager.is_running():
        lb_manager.stop_listener()
    
    # Stop test servers if running
    if test_server_threads is not None:
        GLOBAL_SHUTDOWN_EVENT.set()
        time.sleep(1)  # Give servers time to shut down
    
    # Shut down the Flask server (only works in dev mode)
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    # Start the Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)