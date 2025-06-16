"""
UI components for the load balancer Jupyter notebook interface.
"""

import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import plotly.graph_objs as go
from datetime import datetime, timedelta
import threading
import time
from typing import List, Dict, Any, Optional, Callable

from .core import LBManager, ConnectionInfo
from .stats import StatsCollector

class LoadBalancerUI:
    """UI class for the load balancer."""
    
    def __init__(self, lb_manager: LBManager, stats_collector: StatsCollector):
        self.lb_manager = lb_manager
        self.stats_collector = stats_collector
        self._is_initialized = False
        self._update_thread = None
        self._stop_event = threading.Event()
        
        # Main UI components
        self.port_input = widgets.IntText(
            value=8080,
            description='Listen Port:',
            min=1024,
            max=65535,
            style={'description_width': 'initial'}
        )
        
        self.backends_input = widgets.Textarea(
            value='127.0.0.1:8081\n127.0.0.1:8082',
            description='Backend Servers:',
            layout=widgets.Layout(width='100%', height='100px'),
            style={'description_width': 'initial'}
        )
        
        self.start_button = widgets.Button(
            description='Start',
            button_style='success',
            icon='play',
            layout=widgets.Layout(width='120px')
        )
        
        self.stop_button = widgets.Button(
            description='Stop',
            button_style='danger',
            icon='stop',
            layout=widgets.Layout(width='120px'),
            disabled=True
        )
        
        self.status_label = widgets.HTML(
            value='<span style="color: #888;">Status: Not Running</span>'
        )
        
        # Connections table
        self.connections_table = widgets.HTML(
            value='<div class="lb-table-container"><table class="lb-connections-table">'
                  '<thead><tr><th>ID</th><th>Source</th><th>Destination</th><th>Start Time</th><th>Duration</th></tr></thead>'
                  '<tbody><tr><td colspan="5">No active connections</td></tr></tbody></table></div>'
        )
        
        # Statistics section
        self.stats_container = widgets.HTML(
            value='<div class="lb-stats-container">'
                  '<div class="lb-stat-box"><div class="lb-stat-title">Total Connections</div><div class="lb-stat-value" id="stat-total">0</div></div>'
                  '<div class="lb-stat-box"><div class="lb-stat-title">Active Connections</div><div class="lb-stat-value" id="stat-active">0</div></div>'
                  '<div class="lb-stat-box"><div class="lb-stat-title">Uptime</div><div class="lb-stat-value" id="stat-uptime">00:00:00</div></div>'
                  '<div class="lb-stat-box"><div class="lb-stat-title">Data Transferred</div><div class="lb-stat-value" id="stat-data">0 B</div></div>'
                  '</div>'
        )
        
        # Graph outputs
        self.connections_graph_output = widgets.Output()
        self.throughput_graph_output = widgets.Output()
        
        # Timespan selector for graphs
        self.timespan_selector = widgets.Dropdown(
            options=[
                ('Last minute', 60),
                ('Last 5 minutes', 300),
                ('Last 15 minutes', 900),
                ('Last hour', 3600)
            ],
            value=60,
            description='Time Range:',
            style={'description_width': 'initial'}
        )
        
        # Button event handlers
        self.start_button.on_click(self._on_start_click)
        self.stop_button.on_click(self._on_stop_click)
        self.timespan_selector.observe(self._on_timespan_change, names='value')
        
        # Create the layout
        self._create_layout()
    
    def _create_layout(self) -> None:
        """Create the UI layout."""
        # Configuration section
        config_box = widgets.VBox([
            widgets.HTML('<h3>Load Balancer Configuration</h3>'),
            self.port_input,
            self.backends_input,
            widgets.HBox([self.start_button, self.stop_button, self.status_label])
        ], layout=widgets.Layout(margin='10px 0px'))
        
        # Stats and graphs section
        stats_box = widgets.VBox([
            widgets.HTML('<h3>Statistics Dashboard</h3>'),
            self.stats_container,
            widgets.HBox([
                self.timespan_selector
            ]),
            widgets.HBox([
                widgets.VBox([
                    widgets.HTML('<h4>Active Connections</h4>'),
                    self.connections_graph_output
                ]),
                widgets.VBox([
                    widgets.HTML('<h4>Throughput</h4>'),
                    self.throughput_graph_output
                ])
            ])
        ], layout=widgets.Layout(margin='20px 0px'))
        
        # Connections section
        connections_box = widgets.VBox([
            widgets.HTML('<h3>Active Connections</h3>'),
            self.connections_table
        ], layout=widgets.Layout(margin='20px 0px'))
        
        # Main layout
        self.main_container = widgets.VBox([
            widgets.HTML('<h1>Python Load Balancer</h1>'),
            config_box,
            stats_box,
            connections_box
        ])
    
    def display(self) -> None:
        """Display the UI in the notebook."""
        # Load CSS
        display(HTML("""
        <style>
        .lb-table-container {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }
        .lb-connections-table {
            width: 100%;
            border-collapse: collapse;
        }
        .lb-connections-table th, .lb-connections-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        .lb-connections-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        .lb-connections-table tr:hover {
            background-color: #f9f9f9;
        }
        .lb-stats-container {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 15px 0;
        }
        .lb-stat-box {
            background-color: #f5f5f5;
            border-radius: 5px;
            padding: 15px;
            flex: 1;
            min-width: 150px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .lb-stat-title {
            font-size: 14px;
            color: #555;
            margin-bottom: 5px;
        }
        .lb-stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        h1, h3, h4 {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            color: #333;
        }
        .widget-button {
            margin-right: 10px;
        }
        </style>
        """))
        
        # Display the main container
        display(self.main_container)
        
        # Initialize the UI updater
        if not self._is_initialized:
            self._is_initialized = True
            self._stop_event.clear()
            self._update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
            self._update_thread.start()
            
            # Initial graph rendering
            self._update_graphs()
    
    def _on_start_click(self, b) -> None:
        """Handle start button click."""
        try:
            port = self.port_input.value
            
            # Parse backends
            backends_text = self.backends_input.value
            backends = [line.strip() for line in backends_text.split('\n') if line.strip()]
            
            if not backends:
                self.status_label.value = '<span style="color: red;">Error: No backends specified</span>'
                return
            
            # Start the load balancer
            self.lb_manager.start_listener(port, backends)
            
            # Start the stats collector
            self.stats_collector.start()
            
            # Update UI
            self.start_button.disabled = True
            self.stop_button.disabled = False
            self.port_input.disabled = True
            self.backends_input.disabled = True
            self.status_label.value = f'<span style="color: green;">Status: Running on port {port}</span>'
            
        except Exception as e:
            self.status_label.value = f'<span style="color: red;">Error: {str(e)}</span>'
    
    def _on_stop_click(self, b) -> None:
        """Handle stop button click."""
        try:
            # Stop the load balancer
            self.lb_manager.stop_listener()
            
            # Update UI
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.port_input.disabled = False
            self.backends_input.disabled = False
            self.status_label.value = '<span style="color: #888;">Status: Stopped</span>'
            
        except Exception as e:
            self.status_label.value = f'<span style="color: red;">Error: {str(e)}</span>'
    
    def _on_timespan_change(self, change) -> None:
        """Handle timespan selector change."""
        if change['type'] == 'change' and change['name'] == 'value':
            self._update_graphs()
    
    def _ui_update_loop(self) -> None:
        """Background thread to update the UI."""
        while not self._stop_event.is_set():
            try:
                self._update_connection_table()
                self._update_stats_display()
                
                # Update graphs every 5 seconds to avoid excessive rendering
                if int(time.time()) % 5 == 0:
                    self._update_graphs()
            except Exception as e:
                print(f"Error updating UI: {e}")
            
            # Sleep for a short time to avoid hammering the CPU
            time.sleep(1)
    
    def _update_connection_table(self) -> None:
        """Update the connections table."""
        connections = self.lb_manager.list_connections()
        
        if not connections:
            html = '<div class="lb-table-container"><table class="lb-connections-table">' \
                   '<thead><tr><th>ID</th><th>Source</th><th>Destination</th><th>Start Time</th><th>Duration</th></tr></thead>' \
                   '<tbody><tr><td colspan="5">No active connections</td></tr></tbody></table></div>'
        else:
            rows = []
            for conn in connections:
                # Calculate duration
                duration = datetime.now() - conn.start_time
                duration_str = str(duration).split('.')[0]  # Remove microseconds
                
                # Format the row
                rows.append(
                    f'<tr>'
                    f'<td>{conn.id[:8]}...</td>'  # Truncate UUID to first 8 chars
                    f'<td>{conn.source}</td>'
                    f'<td>{conn.destination}</td>'
                    f'<td>{conn.start_time.strftime("%H:%M:%S")}</td>'
                    f'<td>{duration_str}</td>'
                    f'</tr>'
                )
            
            html = '<div class="lb-table-container"><table class="lb-connections-table">' \
                   '<thead><tr><th>ID</th><th>Source</th><th>Destination</th><th>Start Time</th><th>Duration</th></tr></thead>' \
                   '<tbody>' + ''.join(rows) + '</tbody></table></div>'
        
        self.connections_table.value = html
    
    def _update_stats_display(self) -> None:
        """Update the statistics display."""
        stats = self.lb_manager.get_statistics()
        
        # Format uptime
        if stats["start_time"]:
            uptime = datetime.now() - stats["start_time"]
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        else:
            uptime_str = "00:00:00"
        
        # Format data transferred
        total_bytes = stats["bytes_sent"] + stats["bytes_received"]
        if total_bytes < 1024:
            data_str = f"{total_bytes} B"
        elif total_bytes < 1024 * 1024:
            data_str = f"{total_bytes / 1024:.2f} KB"
        else:
            data_str = f"{total_bytes / (1024 * 1024):.2f} MB"
        
        # Update the HTML
        html = f'<div class="lb-stats-container">' \
               f'<div class="lb-stat-box"><div class="lb-stat-title">Total Connections</div><div class="lb-stat-value" id="stat-total">{stats["total_connections"]}</div></div>' \
               f'<div class="lb-stat-box"><div class="lb-stat-title">Active Connections</div><div class="lb-stat-value" id="stat-active">{stats["active_connections"]}</div></div>' \
               f'<div class="lb-stat-box"><div class="lb-stat-title">Uptime</div><div class="lb-stat-value" id="stat-uptime">{uptime_str}</div></div>' \
               f'<div class="lb-stat-box"><div class="lb-stat-title">Data Transferred</div><div class="lb-stat-value" id="stat-data">{data_str}</div></div>' \
               f'</div>'
        
        self.stats_container.value = html
    
    def _update_graphs(self) -> None:
        """Update the graphs."""
        timespan = self.timespan_selector.value
        
        # Update connections graph
        with self.connections_graph_output:
            clear_output(wait=True)
            fig = self.stats_collector.plot_connections(timespan)
            display(fig)
        
        # Update throughput graph
        with self.throughput_graph_output:
            clear_output(wait=True)
            fig = self.stats_collector.plot_throughput(timespan)
            display(fig)
    
    def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._stop_event.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2.0)
        
        # Stop the load balancer if it's running
        if self.lb_manager.is_running():
            self.lb_manager.stop_listener()
        
        # Stop the stats collector
        self.stats_collector.stop()
