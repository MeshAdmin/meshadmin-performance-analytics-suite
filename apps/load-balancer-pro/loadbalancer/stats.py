"""
Statistics collection and visualization for the load balancer.
"""

import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
import time
import threading
from typing import Dict, List, Any, Optional
from .core import LBManager

class StatsCollector:
    """Collect and process statistics from the load balancer."""
    
    def __init__(self, lb_manager: LBManager):
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
    
    def start(self, interval: float = 1.0) -> None:
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
    
    def stop(self) -> None:
        """Stop collecting statistics."""
        with self._lock:
            if not self._running:
                return
            
            self._stop_event.set()
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        """Check if the collector is running."""
        with self._lock:
            return self._running
    
    def get_time_series(self, timespan: int = 60) -> Dict[str, List]:
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
            
            # Find the index of the first element to include
            start_idx = 0
            for i, ts in enumerate(self._time_series["timestamps"]):
                if ts >= cutoff:
                    start_idx = i
                    break
            
            return {
                "timestamps": self._time_series["timestamps"][start_idx:],
                "active_connections": self._time_series["active_connections"][start_idx:],
                "bytes_sent": self._time_series["bytes_sent"][start_idx:],
                "bytes_received": self._time_series["bytes_received"][start_idx:],
            }
    
    def plot_connections(self, timespan: int = 60) -> go.Figure:
        """Create a plot of active connections over time."""
        ts_data = self.get_time_series(timespan)
        
        if not ts_data["timestamps"]:
            # Return an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Active Connections",
                xaxis_title="Time",
                yaxis_title="Connections",
                height=300,
                margin=dict(l=10, r=10, t=40, b=20)
            )
            return fig
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts_data["timestamps"],
            y=ts_data["active_connections"],
            mode='lines',
            name='Active Connections',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title="Active Connections",
            xaxis_title="Time",
            yaxis_title="Connections",
            height=300,
            margin=dict(l=10, r=10, t=40, b=20)
        )
        
        return fig
    
    def plot_throughput(self, timespan: int = 60) -> go.Figure:
        """Create a plot of throughput over time."""
        ts_data = self.get_time_series(timespan)
        
        if not ts_data["timestamps"]:
            # Return an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Throughput",
                xaxis_title="Time",
                yaxis_title="Bytes/s",
                height=300,
                margin=dict(l=10, r=10, t=40, b=20)
            )
            return fig
        
        # Convert cumulative bytes to bytes/s
        bytes_sent_rate = []
        bytes_received_rate = []
        
        for i in range(1, len(ts_data["timestamps"])):
            # Calculate time difference
            dt = (ts_data["timestamps"][i] - ts_data["timestamps"][i-1]).total_seconds()
            if dt <= 0:
                dt = 1.0  # Avoid division by zero
            
            # Calculate byte rate
            sent_rate = (ts_data["bytes_sent"][i] - ts_data["bytes_sent"][i-1]) / dt
            recv_rate = (ts_data["bytes_received"][i] - ts_data["bytes_received"][i-1]) / dt
            
            bytes_sent_rate.append(sent_rate)
            bytes_received_rate.append(recv_rate)
        
        # Skip the first timestamp since we can't calculate a rate for it
        plot_times = ts_data["timestamps"][1:]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_times,
            y=bytes_sent_rate,
            mode='lines',
            name='Bytes Sent/s',
            line=dict(color='#2ca02c', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=plot_times,
            y=bytes_received_rate,
            mode='lines',
            name='Bytes Received/s',
            line=dict(color='#d62728', width=2)
        ))
        
        fig.update_layout(
            title="Throughput",
            xaxis_title="Time",
            yaxis_title="Bytes/s",
            height=300,
            margin=dict(l=10, r=10, t=40, b=20)
        )
        
        return fig
    
    def _collector_loop(self) -> None:
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
                print(f"Error in stats collector: {e}")
            
            # Wait for the next collection interval
            time.sleep(self._interval)
