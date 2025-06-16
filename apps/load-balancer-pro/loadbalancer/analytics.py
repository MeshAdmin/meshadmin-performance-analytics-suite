"""
Analytics module for the load balancer.
This module handles collecting, storing and analyzing historical data.
"""

import pandas as pd
import numpy as np
import time
import threading
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer.analytics")

class AnalyticsCollector:
    """Collects and stores historical analytics data."""
    
    def __init__(self, data_dir: str = "data"):
        self._lock = threading.RLock()
        self._running = False
        self._data_dir = data_dir
        self._stop_event = threading.Event()
        self._thread = None
        self._interval = 60.0  # Store data every minute
        
        # Historical data storage
        self._connection_history = []
        self._traffic_history = []
        self._latency_history = []
        self._health_history = []
        self._lb_manager = None
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data if any
        self._load_data()
    
    def set_lb_manager(self, lb_manager) -> None:
        """Set the load balancer manager instance."""
        self._lb_manager = lb_manager
    
    def start(self, interval: float = 60.0) -> None:
        """Start collecting analytics data."""
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
            logger.info(f"Analytics collector started, interval={interval}s")
    
    def stop(self) -> None:
        """Stop collecting analytics data."""
        with self._lock:
            if not self._running:
                return
            
            self._stop_event.set()
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
                
            # Save data before stopping
            self._save_data()
            logger.info("Analytics collector stopped")
    
    def get_connection_history(self, timespan: int = 3600) -> List[Dict]:
        """Get connection history data for specified timespan in seconds."""
        with self._lock:
            if not self._connection_history:
                return []
            
            # Filter by timespan
            cutoff = datetime.now() - timedelta(seconds=timespan)
            filtered = [entry for entry in self._connection_history if entry["timestamp"] > cutoff]
            return filtered
    
    def get_traffic_history(self, timespan: int = 3600) -> List[Dict]:
        """Get traffic history data for specified timespan in seconds."""
        with self._lock:
            if not self._traffic_history:
                return []
            
            # Filter by timespan
            cutoff = datetime.now() - timedelta(seconds=timespan)
            filtered = [entry for entry in self._traffic_history if entry["timestamp"] > cutoff]
            return filtered
    
    def get_latency_history(self, timespan: int = 3600) -> List[Dict]:
        """Get latency history data for specified timespan in seconds."""
        with self._lock:
            if not self._latency_history:
                return []
            
            # Filter by timespan
            cutoff = datetime.now() - timedelta(seconds=timespan)
            filtered = [entry for entry in self._latency_history if entry["timestamp"] > cutoff]
            return filtered
    
    def get_health_history(self, timespan: int = 3600) -> List[Dict]:
        """Get health check history data for specified timespan in seconds."""
        with self._lock:
            if not self._health_history:
                return []
            
            # Filter by timespan
            cutoff = datetime.now() - timedelta(seconds=timespan)
            filtered = [entry for entry in self._health_history if entry["timestamp"] > cutoff]
            return filtered
    
    def plot_connections_over_time(self, timespan: int = 3600) -> go.Figure:
        """Create a plot of connections over time."""
        with self._lock:
            history = self.get_connection_history(timespan)
            
            if not history:
                # Return empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="Connections Over Time",
                    xaxis_title="Time",
                    yaxis_title="Connections",
                    height=300
                )
                return fig
            
            # Extract data
            timestamps = [entry["timestamp"] for entry in history]
            active_conns = [entry["active_connections"] for entry in history]
            total_conns = [entry["total_connections"] for entry in history]
            
            # Create figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=active_conns,
                mode='lines',
                name='Active Connections',
                line=dict(color='#1976D2', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=total_conns,
                mode='lines',
                name='Total Connections',
                line=dict(color='#388E3C', width=2, dash='dot')
            ))
            
            fig.update_layout(
                title="Connections Over Time",
                xaxis_title="Time",
                yaxis_title="Connections",
                height=300
            )
            
            return fig
    
    def plot_traffic_over_time(self, timespan: int = 3600) -> go.Figure:
        """Create a plot of traffic over time."""
        with self._lock:
            history = self.get_traffic_history(timespan)
            
            if not history:
                # Return empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="Traffic Over Time",
                    xaxis_title="Time",
                    yaxis_title="Bytes/s",
                    height=300
                )
                return fig
            
            # Extract data
            timestamps = [entry["timestamp"] for entry in history]
            bytes_sent = [entry["bytes_sent_rate"] for entry in history]
            bytes_received = [entry["bytes_received_rate"] for entry in history]
            
            # Create figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=bytes_sent,
                mode='lines',
                name='Bytes Sent/s',
                line=dict(color='#2ca02c', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=bytes_received,
                mode='lines',
                name='Bytes Received/s',
                line=dict(color='#d62728', width=2)
            ))
            
            fig.update_layout(
                title="Traffic Over Time",
                xaxis_title="Time",
                yaxis_title="Bytes/s",
                height=300
            )
            
            return fig
    
    def plot_latency_over_time(self, timespan: int = 3600) -> go.Figure:
        """Create a plot of backend latency over time."""
        with self._lock:
            history = self.get_latency_history(timespan)
            
            if not history:
                # Return empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="Backend Latency",
                    xaxis_title="Time",
                    yaxis_title="Response Time (ms)",
                    height=300
                )
                return fig
            
            # Extract data
            timestamps = [entry["timestamp"] for entry in history]
            
            # Create figure
            fig = go.Figure()
            
            # Add a trace for each backend
            backend_data = {}
            
            for entry in history:
                for backend, latency in entry["backend_latencies"].items():
                    if backend not in backend_data:
                        backend_data[backend] = {"timestamps": [], "latencies": []}
                    
                    backend_data[backend]["timestamps"].append(entry["timestamp"])
                    backend_data[backend]["latencies"].append(latency)
            
            # Add traces
            for backend, data in backend_data.items():
                fig.add_trace(go.Scatter(
                    x=data["timestamps"],
                    y=data["latencies"],
                    mode='lines',
                    name=backend,
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title="Backend Latency",
                xaxis_title="Time",
                yaxis_title="Response Time (ms)",
                height=300
            )
            
            return fig
    
    def plot_health_over_time(self, timespan: int = 3600) -> go.Figure:
        """Create a plot of backend health over time."""
        with self._lock:
            history = self.get_health_history(timespan)
            
            if not history:
                # Return empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="Backend Health",
                    xaxis_title="Time",
                    yaxis_title="Healthy Backends (%)",
                    height=300
                )
                return fig
            
            # Extract data
            timestamps = [entry["timestamp"] for entry in history]
            health_percentage = []
            
            for entry in history:
                if entry["total_backends"] > 0:
                    percentage = (entry["healthy_backends"] / entry["total_backends"]) * 100
                else:
                    percentage = 0
                health_percentage.append(percentage)
            
            # Create figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=health_percentage,
                mode='lines',
                fill='tozeroy',
                line=dict(color='#26a69a', width=2)
            ))
            
            fig.update_layout(
                title="Backend Health",
                xaxis_title="Time",
                yaxis_title="Healthy Backends (%)",
                height=300,
                yaxis=dict(range=[0, 100])
            )
            
            return fig
    
    def create_dashboard(self, timespan: int = 3600) -> go.Figure:
        """Create a comprehensive dashboard with all analytics."""
        # Create a figure with subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Connections Over Time", "Traffic Over Time", 
                           "Backend Latency", "Backend Health"),
            vertical_spacing=0.1
        )
        
        # Add connection data
        conn_history = self.get_connection_history(timespan)
        if conn_history:
            timestamps = [entry["timestamp"] for entry in conn_history]
            active_conns = [entry["active_connections"] for entry in conn_history]
            total_conns = [entry["total_connections"] for entry in conn_history]
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps, 
                    y=active_conns, 
                    mode='lines',
                    name='Active Connections',
                    line=dict(color='#1976D2', width=2)
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=timestamps, 
                    y=total_conns, 
                    mode='lines',
                    name='Total Connections',
                    line=dict(color='#388E3C', width=2, dash='dot')
                ),
                row=1, col=1
            )
        
        # Add traffic data
        traffic_history = self.get_traffic_history(timespan)
        if traffic_history:
            timestamps = [entry["timestamp"] for entry in traffic_history]
            bytes_sent = [entry["bytes_sent_rate"] for entry in traffic_history]
            bytes_received = [entry["bytes_received_rate"] for entry in traffic_history]
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps, 
                    y=bytes_sent, 
                    mode='lines',
                    name='Bytes Sent/s',
                    line=dict(color='#2ca02c', width=2)
                ),
                row=1, col=2
            )
            fig.add_trace(
                go.Scatter(
                    x=timestamps, 
                    y=bytes_received, 
                    mode='lines',
                    name='Bytes Received/s',
                    line=dict(color='#d62728', width=2)
                ),
                row=1, col=2
            )
        
        # Add latency data
        latency_history = self.get_latency_history(timespan)
        if latency_history:
            # Add a trace for each backend
            backend_data = {}
            
            for entry in latency_history:
                for backend, latency in entry["backend_latencies"].items():
                    if backend not in backend_data:
                        backend_data[backend] = {"timestamps": [], "latencies": []}
                    
                    backend_data[backend]["timestamps"].append(entry["timestamp"])
                    backend_data[backend]["latencies"].append(latency)
            
            # Add traces
            for backend, data in backend_data.items():
                fig.add_trace(
                    go.Scatter(
                        x=data["timestamps"],
                        y=data["latencies"],
                        mode='lines',
                        name=backend,
                        line=dict(width=2)
                    ),
                    row=2, col=1
                )
        
        # Add health data
        health_history = self.get_health_history(timespan)
        if health_history:
            timestamps = [entry["timestamp"] for entry in health_history]
            health_percentage = []
            
            for entry in health_history:
                if entry["total_backends"] > 0:
                    percentage = (entry["healthy_backends"] / entry["total_backends"]) * 100
                else:
                    percentage = 0
                health_percentage.append(percentage)
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=health_percentage,
                    mode='lines',
                    fill='tozeroy',
                    name='Backend Health',
                    line=dict(color='#26a69a', width=2)
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            height=700,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Update axes
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_xaxes(title_text="Time", row=2, col=2)
        fig.update_yaxes(title_text="Connections", row=1, col=1)
        fig.update_yaxes(title_text="Bytes/s", row=1, col=2)
        fig.update_yaxes(title_text="Response Time (ms)", row=2, col=1)
        fig.update_yaxes(title_text="Healthy Backends (%)", range=[0, 100], row=2, col=2)
        
        return fig
    
    def _collector_loop(self) -> None:
        """Background thread to collect analytics data."""
        last_save_time = time.time()
        prev_bytes_sent = 0
        prev_bytes_received = 0
        prev_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                if self._lb_manager and self._lb_manager.is_running():
                    # Get current stats
                    stats = self._lb_manager.get_statistics()
                    backend_servers = self._lb_manager.get_backend_servers()
                    now = datetime.now()
                    current_time = time.time()
                    
                    # Connection history
                    connection_entry = {
                        "timestamp": now,
                        "active_connections": stats["active_connections"],
                        "total_connections": stats["total_connections"]
                    }
                    
                    # Traffic history - calculate rates
                    time_diff = current_time - prev_time
                    if time_diff <= 0:
                        time_diff = 1.0  # Avoid division by zero
                        
                    bytes_sent_rate = (stats["bytes_sent"] - prev_bytes_sent) / time_diff
                    bytes_received_rate = (stats["bytes_received"] - prev_bytes_received) / time_diff
                    
                    traffic_entry = {
                        "timestamp": now,
                        "bytes_sent": stats["bytes_sent"],
                        "bytes_received": stats["bytes_received"],
                        "bytes_sent_rate": bytes_sent_rate,
                        "bytes_received_rate": bytes_received_rate
                    }
                    
                    # Health history
                    health_check_history = stats.get("health_check_history", [])
                    if health_check_history:
                        latest_health_check = health_check_history[-1]
                        health_entry = {
                            "timestamp": now,
                            "healthy_backends": latest_health_check.get("healthy_backends", 0),
                            "total_backends": latest_health_check.get("total_backends", 0)
                        }
                        with self._lock:
                            self._health_history.append(health_entry)
                    
                    # Latency history
                    latency_entry = {
                        "timestamp": now,
                        "backend_latencies": {}
                    }
                    
                    for backend in backend_servers:
                        backend_id = f"{backend['host']}:{backend['port']}"
                        latency_entry["backend_latencies"][backend_id] = backend["response_time"]
                    
                    # Store entries
                    with self._lock:
                        self._connection_history.append(connection_entry)
                        self._traffic_history.append(traffic_entry)
                        self._latency_history.append(latency_entry)
                        
                        # Limit the size of history to avoid memory issues
                        max_entries = 10000  # Approximately 1 week at 1-minute intervals
                        if len(self._connection_history) > max_entries:
                            self._connection_history = self._connection_history[-max_entries:]
                        if len(self._traffic_history) > max_entries:
                            self._traffic_history = self._traffic_history[-max_entries:]
                        if len(self._latency_history) > max_entries:
                            self._latency_history = self._latency_history[-max_entries:]
                        if len(self._health_history) > max_entries:
                            self._health_history = self._health_history[-max_entries:]
                    
                    # Save data periodically (every 15 minutes)
                    if current_time - last_save_time > 900:
                        self._save_data()
                        last_save_time = current_time
                    
                    # Update for next iteration
                    prev_bytes_sent = stats["bytes_sent"]
                    prev_bytes_received = stats["bytes_received"]
                    prev_time = current_time
            
            except Exception as e:
                logger.error(f"Error in analytics collector: {e}")
            
            # Sleep for the collection interval
            time.sleep(self._interval)
    
    def _save_data(self) -> None:
        """Save analytics data to disk."""
        try:
            with self._lock:
                # Save connection history
                with open(os.path.join(self._data_dir, "connection_history.json"), 'w') as f:
                    history_data = []
                    for entry in self._connection_history:
                        history_data.append({
                            "timestamp": entry["timestamp"].isoformat(),
                            "active_connections": entry["active_connections"],
                            "total_connections": entry["total_connections"]
                        })
                    json.dump(history_data, f)
                
                # Save traffic history
                with open(os.path.join(self._data_dir, "traffic_history.json"), 'w') as f:
                    traffic_data = []
                    for entry in self._traffic_history:
                        traffic_data.append({
                            "timestamp": entry["timestamp"].isoformat(),
                            "bytes_sent": entry["bytes_sent"],
                            "bytes_received": entry["bytes_received"],
                            "bytes_sent_rate": entry["bytes_sent_rate"],
                            "bytes_received_rate": entry["bytes_received_rate"]
                        })
                    json.dump(traffic_data, f)
                
                # Save latency history
                with open(os.path.join(self._data_dir, "latency_history.json"), 'w') as f:
                    latency_data = []
                    for entry in self._latency_history:
                        latency_data.append({
                            "timestamp": entry["timestamp"].isoformat(),
                            "backend_latencies": entry["backend_latencies"]
                        })
                    json.dump(latency_data, f)
                
                # Save health history
                with open(os.path.join(self._data_dir, "health_history.json"), 'w') as f:
                    health_data = []
                    for entry in self._health_history:
                        health_data.append({
                            "timestamp": entry["timestamp"].isoformat(),
                            "healthy_backends": entry["healthy_backends"],
                            "total_backends": entry["total_backends"]
                        })
                    json.dump(health_data, f)
                
                logger.info("Analytics data saved to disk")
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")
    
    def _load_data(self) -> None:
        """Load analytics data from disk."""
        try:
            # Load connection history
            connection_file = os.path.join(self._data_dir, "connection_history.json")
            if os.path.exists(connection_file):
                with open(connection_file, 'r') as f:
                    data = json.load(f)
                    for entry in data:
                        self._connection_history.append({
                            "timestamp": datetime.fromisoformat(entry["timestamp"]),
                            "active_connections": entry["active_connections"],
                            "total_connections": entry["total_connections"]
                        })
            
            # Load traffic history
            traffic_file = os.path.join(self._data_dir, "traffic_history.json")
            if os.path.exists(traffic_file):
                with open(traffic_file, 'r') as f:
                    data = json.load(f)
                    for entry in data:
                        self._traffic_history.append({
                            "timestamp": datetime.fromisoformat(entry["timestamp"]),
                            "bytes_sent": entry["bytes_sent"],
                            "bytes_received": entry["bytes_received"],
                            "bytes_sent_rate": entry["bytes_sent_rate"],
                            "bytes_received_rate": entry["bytes_received_rate"]
                        })
            
            # Load latency history
            latency_file = os.path.join(self._data_dir, "latency_history.json")
            if os.path.exists(latency_file):
                with open(latency_file, 'r') as f:
                    data = json.load(f)
                    for entry in data:
                        self._latency_history.append({
                            "timestamp": datetime.fromisoformat(entry["timestamp"]),
                            "backend_latencies": entry["backend_latencies"]
                        })
            
            # Load health history
            health_file = os.path.join(self._data_dir, "health_history.json")
            if os.path.exists(health_file):
                with open(health_file, 'r') as f:
                    data = json.load(f)
                    for entry in data:
                        self._health_history.append({
                            "timestamp": datetime.fromisoformat(entry["timestamp"]),
                            "healthy_backends": entry["healthy_backends"],
                            "total_backends": entry["total_backends"]
                        })
            
            logger.info(f"Loaded analytics data: {len(self._connection_history)} connection records, " +
                      f"{len(self._traffic_history)} traffic records, " +
                      f"{len(self._latency_history)} latency records, " +
                      f"{len(self._health_history)} health records")
                      
        except Exception as e:
            logger.error(f"Error loading analytics data: {e}")

# Global instance
analytics_collector = AnalyticsCollector()