"""
Core functionality for the load balancer.
This module contains the main logic for the TCP load balancer.
"""

import socket
import threading
import time
import random
import logging
import uuid
from typing import List, Dict, Tuple, Optional, Callable
import queue
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer.core")

class ConnectionInfo:
    """Class to store information about active connections."""
    
    def __init__(self, conn_id: str, source: str, destination: str, start_time: datetime):
        self.id = conn_id
        self.source = source
        self.destination = destination
        self.start_time = start_time
        self.bytes_sent = 0
        self.bytes_received = 0
        self.active = True
        
    def __str__(self) -> str:
        return f"ID:{self.id} | {self.source} -> {self.destination} | {self.start_time.strftime('%H:%M:%S')}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for data processing."""
        return {
            "id": self.id,
            "source": self.source,
            "destination": self.destination,
            "start_time": self.start_time,
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "active": self.active
        }

class BackendServer:
    """Class to represent a backend server with health check status."""
    
    def __init__(self, host: str, port: int, weight: int = 1):
        self.host = host
        self.port = port
        self.weight = weight
        self.healthy = True
        self.last_checked = datetime.now()
        self.response_time = 0  # in milliseconds
        self.failed_checks = 0
        self.total_connections = 0
        self.active_connections = 0
        
    def __str__(self) -> str:
        status = "HEALTHY" if self.healthy else "UNHEALTHY"
        return f"{self.host}:{self.port} ({status})"
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for data processing."""
        return {
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "healthy": self.healthy,
            "last_checked": self.last_checked,
            "response_time": self.response_time,
            "failed_checks": self.failed_checks,
            "total_connections": self.total_connections,
            "active_connections": self.active_connections
        }

class LBManager:
    """Manager class for the load balancer."""
    
    # Load balancing algorithm types
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    IP_HASH = "ip_hash"
    
    def __init__(self):
        self._active_conns = {}  # Dictionary of active connections
        self._backends = []  # List of backend server objects
        self._backend_index = 0  # Current index for round-robin
        self._algorithm = self.ROUND_ROBIN  # Default algorithm
        self._health_check_interval = 10  # Seconds between health checks
        self._health_check_timeout = 2  # Seconds to wait for response
        self._health_check_path = "/"  # Path to check for HTTP servers
        self._unhealthy_threshold = 3  # Failed checks before marking unhealthy
        self._healthy_threshold = 2  # Successful checks before marking healthy again
        self._enable_health_checks = True  # Enable or disable health checking
        self._health_check_thread = None  # Thread for health checking
        self._lock = threading.RLock()  # Lock for thread safety
        self._running = False  # Flag to indicate if the load balancer is running
        self._listener_thread = None  # Thread for accepting connections
        self._stop_event = threading.Event()  # Event to signal stop
        self._conn_updates = queue.Queue()  # Queue of connection updates for UI
        self._statistics = {
            "total_connections": 0,
            "active_connections": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "start_time": None,
            "connection_history": [],  # Limited history of connections
            "health_check_history": []  # History of health check results
        }
    
    def add_connection(self, conn: ConnectionInfo) -> None:
        """Add a new connection to the active list."""
        with self._lock:
            self._active_conns[conn.id] = conn
            self._statistics["total_connections"] += 1
            self._statistics["active_connections"] += 1
            self._conn_updates.put(("add", conn))
    
    def remove_connection(self, conn_id: str) -> None:
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
                
                # Update backend server stats if found
                try:
                    dest_parts = conn.destination.split(':')
                    dest_host, dest_port = dest_parts[0], int(dest_parts[1])
                    
                    # Find the backend server
                    for backend in self._backends:
                        if backend.host == dest_host and backend.port == dest_port:
                            backend.active_connections -= 1
                            break
                except Exception as e:
                    logger.error(f"Error updating backend stats: {e}")
                
                # Remove from active connections
                del self._active_conns[conn_id]
                self._conn_updates.put(("remove", conn))
    
    def list_connections(self) -> List[ConnectionInfo]:
        """Return a list of all active connections."""
        with self._lock:
            return list(self._active_conns.values())
    
    def get_statistics(self) -> Dict:
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
    
    def get_updates(self, block: bool = False, timeout: Optional[float] = None) -> Tuple[str, ConnectionInfo]:
        """Get connection updates from the queue."""
        try:
            return self._conn_updates.get(block=block, timeout=timeout)
        except queue.Empty:
            return None, None
    
    def set_algorithm(self, algorithm: str) -> None:
        """Set the load balancing algorithm."""
        if algorithm not in [self.ROUND_ROBIN, self.LEAST_CONNECTIONS, self.WEIGHTED_ROUND_ROBIN, 
                            self.RANDOM, self.IP_HASH]:
            raise ValueError(f"Invalid algorithm: {algorithm}")
        
        with self._lock:
            self._algorithm = algorithm
            logger.info(f"Load balancing algorithm set to {algorithm}")
    
    def get_algorithm(self) -> str:
        """Get the current load balancing algorithm."""
        with self._lock:
            return self._algorithm
    
    def get_backend_servers(self) -> List[Dict]:
        """Get information about backend servers."""
        with self._lock:
            return [backend.to_dict() for backend in self._backends]
    
    def set_health_check_config(self, interval: int = 10, timeout: int = 2, 
                               path: str = "/", unhealthy_threshold: int = 3, 
                               healthy_threshold: int = 2, enabled: bool = True) -> None:
        """Configure health checking parameters."""
        with self._lock:
            self._health_check_interval = interval
            self._health_check_timeout = timeout
            self._health_check_path = path
            self._unhealthy_threshold = unhealthy_threshold
            self._healthy_threshold = healthy_threshold
            self._enable_health_checks = enabled
            
            # Restart health check thread if settings change
            if self._running and self._enable_health_checks:
                self._start_health_checker()
    
    def _start_health_checker(self) -> None:
        """Start the health checker thread."""
        # Stop existing thread if any
        if self._health_check_thread and self._health_check_thread.is_alive():
            return
        
        if not self._enable_health_checks:
            return
            
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("Health checker started")
    
    def _health_check_loop(self) -> None:
        """Main loop for health checking."""
        while not self._stop_event.is_set() and self._running:
            # Sleep first to allow initial setup
            time.sleep(self._health_check_interval)
            
            try:
                healthy_backends = 0
                for backend in self._backends:
                    is_healthy = self._check_backend_health(backend)
                    if is_healthy:
                        healthy_backends += 1
                        
                logger.info(f"Health check completed: {healthy_backends}/{len(self._backends)} healthy backends")
                
                # Record health check history
                timestamp = datetime.now()
                history_entry = {
                    "timestamp": timestamp,
                    "healthy_backends": healthy_backends,
                    "total_backends": len(self._backends)
                }
                
                with self._lock:
                    self._statistics["health_check_history"].append(history_entry)
                    # Limit history to 100 entries
                    if len(self._statistics["health_check_history"]) > 100:
                        self._statistics["health_check_history"].pop(0)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    def _check_backend_health(self, backend: BackendServer) -> bool:
        """Check health of a single backend server."""
        start_time = time.time()
        is_healthy = False
        
        try:
            # Simple TCP check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._health_check_timeout)
            
            result = sock.connect_ex((backend.host, backend.port))
            is_healthy = (result == 0)
            
            # Update backend status
            backend.last_checked = datetime.now()
            
            if is_healthy:
                # Reset failed checks if server becomes healthy
                if not backend.healthy and backend.failed_checks >= self._unhealthy_threshold:
                    if backend.failed_checks >= self._healthy_threshold:
                        backend.healthy = True
                        backend.failed_checks = 0
                        logger.info(f"Backend {backend} is now HEALTHY")
                else:
                    backend.healthy = True
                    backend.failed_checks = 0
            else:
                # Increment failed checks
                backend.failed_checks += 1
                
                # Mark as unhealthy after threshold
                if backend.healthy and backend.failed_checks >= self._unhealthy_threshold:
                    backend.healthy = False
                    logger.warning(f"Backend {backend} is now UNHEALTHY")
                    
        except Exception as e:
            # Connection failure
            logger.error(f"Health check failed for {backend}: {e}")
            backend.failed_checks += 1
            
            if backend.healthy and backend.failed_checks >= self._unhealthy_threshold:
                backend.healthy = False
                logger.warning(f"Backend {backend} is now UNHEALTHY")
                
        finally:
            # Record response time
            end_time = time.time()
            backend.response_time = int((end_time - start_time) * 1000)  # in ms
            
            try:
                if 'sock' in locals():
                    sock.close()
            except:
                pass
                
        return backend.healthy
    
    def pick_backend(self) -> Tuple[str, int]:
        """Pick a backend server using the current algorithm."""
        with self._lock:
            if not self._backends:
                raise ValueError("No backends available")
            
            # Filter healthy backends
            healthy_backends = [b for b in self._backends if b.healthy]
            
            if not healthy_backends:
                logger.warning("No healthy backends available, using all backends")
                healthy_backends = self._backends
            
            # Apply the selected algorithm
            if self._algorithm == self.ROUND_ROBIN:
                backend = self._pick_round_robin(healthy_backends)
            elif self._algorithm == self.LEAST_CONNECTIONS:
                backend = self._pick_least_connections(healthy_backends)
            elif self._algorithm == self.WEIGHTED_ROUND_ROBIN:
                backend = self._pick_weighted_round_robin(healthy_backends)
            elif self._algorithm == self.RANDOM:
                backend = self._pick_random(healthy_backends)
            elif self._algorithm == self.IP_HASH:
                # IP_HASH requires client IP which we don't have here
                # Fallback to round robin
                backend = self._pick_round_robin(healthy_backends)
            else:
                # Fallback to round robin
                backend = self._pick_round_robin(healthy_backends)
            
            # Update backend stats
            backend.total_connections += 1
            backend.active_connections += 1
            
            return backend.host, backend.port
    
    def _pick_round_robin(self, backends: List[BackendServer]) -> BackendServer:
        """Round-robin backend selection."""
        backend = backends[self._backend_index % len(backends)]
        self._backend_index += 1
        return backend
    
    def _pick_least_connections(self, backends: List[BackendServer]) -> BackendServer:
        """Select backend with least active connections."""
        return min(backends, key=lambda b: b.active_connections)
    
    def _pick_weighted_round_robin(self, backends: List[BackendServer]) -> BackendServer:
        """Weighted round-robin selection."""
        # Create a list with backends repeated according to their weight
        weighted_backends = []
        for backend in backends:
            weighted_backends.extend([backend] * backend.weight)
            
        if not weighted_backends:
            return self._pick_round_robin(backends)
            
        index = self._backend_index % len(weighted_backends)
        self._backend_index += 1
        return weighted_backends[index]
    
    def _pick_random(self, backends: List[BackendServer]) -> BackendServer:
        """Random backend selection."""
        return random.choice(backends)
    
    def start_listener(self, listen_port: int, backends: List[str]) -> None:
        """Start the load balancer listener."""
        with self._lock:
            if self._running:
                raise RuntimeError("Load balancer is already running")
            
            # Convert string backends to BackendServer objects
            self._backends = []
            for backend_str in backends:
                try:
                    host, port = backend_str.split(":")
                    backend = BackendServer(host, int(port))
                    self._backends.append(backend)
                except ValueError:
                    logger.error(f"Invalid backend format: {backend_str}")
            
            if not self._backends:
                raise ValueError("No valid backends provided")
                
            self._backend_index = 0
            self._running = True
            self._stop_event.clear()
            self._statistics["start_time"] = datetime.now()
            
            # Start health checker if enabled
            if self._enable_health_checks:
                self._start_health_checker()
            
            # Start listener thread
            self._listener_thread = threading.Thread(
                target=self._listener_loop, 
                args=(listen_port,),
                daemon=True
            )
            self._listener_thread.start()
            logger.info(f"Load balancer listening on port {listen_port} with {len(self._backends)} backends")
    
    def stop_listener(self) -> None:
        """Stop the load balancer."""
        with self._lock:
            if not self._running:
                return
            
            logger.info("Stopping load balancer...")
            self._stop_event.set()
            self._running = False
            
            # Wait for the listener thread to finish
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=2.0)
            
            # Close all active connections
            for conn_id in list(self._active_conns.keys()):
                self.remove_connection(conn_id)
    
    def is_running(self) -> bool:
        """Check if the load balancer is running."""
        with self._lock:
            return self._running
    
    def _listener_loop(self, listen_port: int) -> None:
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
    
    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
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
    
    def _forward_data(self, src: socket.socket, dst: socket.socket, conn: ConnectionInfo, client_to_backend: bool) -> None:
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
