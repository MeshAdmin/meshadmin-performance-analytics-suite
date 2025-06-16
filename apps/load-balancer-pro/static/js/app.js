/**
 * Python Load Balancer - Main Application JavaScript
 */

// Dark mode detection
const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

// Refresh data periodically
function refreshData() {
    fetchStats();
    fetchConnections();
    
    // Set interval for regular updates
    setInterval(() => {
        fetchStats();
        fetchConnections(); 
    }, 2000);
    
    // Update health plot less frequently
    setInterval(() => {
        if (document.getElementById('health-plot')) {
            loadHealthPlot();
        }
    }, 5000);
    
    // Update topology visualization
    setInterval(() => {
        updateTopology();
    }, 1000);
}

// Fetch stats data via API
function fetchStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update stats display
            updateStats(data);
            
            // Update topology data if available
            if (typeof topology !== 'undefined') {
                topology.updateData(data.connections, data.backend_servers, data);
            }
            
            // Update server tooltips if available
            updateServerTooltipData(data.backend_servers);
        })
        .catch(error => console.error('Error fetching stats:', error));
}

// Update stats display
function updateStats(data) {
    // Update basic stats
    const totalConns = document.getElementById('stat-total');
    const activeConns = document.getElementById('stat-active');
    const uptime = document.getElementById('stat-uptime');
    const dataTransferred = document.getElementById('stat-data');
    
    if (totalConns) totalConns.textContent = data.stats.total_connections;
    if (activeConns) activeConns.textContent = data.stats.active_connections;
    
    // Format uptime
    if (uptime && data.stats.start_time) {
        const uptimeSeconds = data.stats.uptime;
        const hours = Math.floor(uptimeSeconds / 3600);
        const minutes = Math.floor((uptimeSeconds % 3600) / 60);
        const seconds = Math.floor(uptimeSeconds % 60);
        
        uptime.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Format data transferred
    if (dataTransferred) {
        const totalBytes = data.stats.bytes_sent + data.stats.bytes_received;
        let dataStr;
        
        if (totalBytes < 1024) {
            dataStr = `${totalBytes} B`;
        } else if (totalBytes < 1024 * 1024) {
            dataStr = `${(totalBytes / 1024).toFixed(2)} KB`;
        } else {
            dataStr = `${(totalBytes / (1024 * 1024)).toFixed(2)} MB`;
        }
        
        dataTransferred.textContent = dataStr;
    }
}

// Fetch connections data via API
function fetchConnections() {
    fetch('/api/connections')
        .then(response => response.json())
        .then(data => {
            updateConnectionsTable(data.connections);
        })
        .catch(error => console.error('Error fetching connections:', error));
}

// Update connections table
function updateConnectionsTable(connections) {
    const table = document.querySelector('table.table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Handle empty connections
    if (connections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No active connections</td></tr>';
        return;
    }
    
    // Create a document fragment to minimize DOM operations
    const fragment = document.createDocumentFragment();
    
    // Create or update rows
    connections.forEach(conn => {
        // Check if this connection already exists in the table
        let row = tbody.querySelector(`tr[data-conn-id="${conn.id}"]`);
        
        if (!row) {
            // Create new row
            row = document.createElement('tr');
            row.setAttribute('data-conn-id', conn.id);
            row.classList.add('connection-row');
            
            // Add cells
            for (let i = 0; i < 5; i++) {
                row.appendChild(document.createElement('td'));
            }
            
            fragment.appendChild(row);
        }
        
        // Update row cells
        const cells = row.querySelectorAll('td');
        cells[0].textContent = conn.id.substring(0, 8) + '...';
        cells[1].textContent = conn.source;
        cells[2].textContent = conn.destination;
        cells[3].textContent = conn.start_time;
        cells[4].textContent = conn.duration.toFixed(1) + 's';
        
        // Highlight active connections with better contrast that won't disappear on hover
        if (conn.active) {
            row.classList.add('active-connection');
        } else {
            row.classList.remove('active-connection');
        }
    });
    
    // Add new rows to the table
    tbody.appendChild(fragment);
    
    // Remove rows for connections that no longer exist
    const existingRows = tbody.querySelectorAll('tr[data-conn-id]');
    const existingIds = connections.map(conn => conn.id);
    
    existingRows.forEach(row => {
        const connId = row.getAttribute('data-conn-id');
        if (!existingIds.includes(connId)) {
            row.remove();
        }
    });
}

// Update topology visualization
function updateTopology() {
    if (typeof topology === 'undefined') return;
    
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            topology.updateData(data.connections, data.backend_servers, data);
        })
        .catch(error => console.error('Error updating topology:', error));
}

// Update server tooltip data
function updateServerTooltipData(backends) {
    if (typeof serverTooltips === 'undefined' || !backends) return;
    
    backends.forEach(backend => {
        const serverId = `backend-${backend.host}-${backend.port}`;
        const status = backend.healthy ? 'healthy' : 'unhealthy';
        
        serverTooltips.updateServerData(serverId, {
            status: status,
            responseTime: backend.response_time,
            connections: backend.active_connections,
            healthChecks: backend.total_checks || 0,
            failedChecks: backend.failed_checks
        });
    });
}

// Initialize server tooltips when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add data attributes to backend server elements
    function initializeServerTooltips() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (!data.backend_servers) return;
                
                const serverContainers = document.querySelectorAll('.backend-server');
                
                // If no containers found, add data attributes to server indicators in network topology
                if (serverContainers.length === 0 && document.querySelector('.node[class*="backend"]')) {
                    const backendNodes = document.querySelectorAll('.node[class*="backend"]');
                    
                    backendNodes.forEach(node => {
                        // Add tooltip data attributes
                        node.setAttribute('data-server-tooltip', '');
                        
                        // Try to extract server details from the node
                        const serverId = node.getAttribute('data-id') || '';
                        if (serverId.startsWith('backend-')) {
                            // Find the matching backend data
                            const parts = serverId.replace('backend-', '').split('-');
                            if (parts.length >= 2) {
                                const host = parts[0];
                                const port = parts[1];
                                
                                // Find backend data
                                const backend = data.backend_servers.find(b => 
                                    b.host === host && b.port.toString() === port);
                                
                                if (backend) {
                                    node.setAttribute('data-server-id', serverId);
                                    node.setAttribute('data-server-name', `Backend ${backend.host}:${backend.port}`);
                                    node.setAttribute('data-server-host', backend.host);
                                    node.setAttribute('data-server-port', backend.port);
                                    node.setAttribute('data-server-status', backend.healthy ? 'healthy' : 'unhealthy');
                                    node.setAttribute('data-server-response-time', backend.response_time);
                                    node.setAttribute('data-server-connections', backend.active_connections);
                                    node.setAttribute('data-server-weight', backend.weight || 1);
                                    node.setAttribute('data-server-health-checks', backend.total_checks || 0);
                                    node.setAttribute('data-server-failed-checks', backend.failed_checks);
                                }
                            }
                        }
                    });
                }
                
                // Initialize server tooltips
                if (typeof serverTooltips !== 'undefined') {
                    serverTooltips.initialize('[data-server-tooltip]');
                }
            })
            .catch(error => console.error('Error initializing server tooltips:', error));
    }
    
    // Check if D3 and network topology are loaded
    const checkAndInitialize = setInterval(() => {
        if (typeof d3 !== 'undefined' && document.querySelector('#network-topology svg')) {
            clearInterval(checkAndInitialize);
            
            // Wait a bit for the topology to fully initialize
            setTimeout(() => {
                initializeServerTooltips();
            }, 1000);
        }
    }, 500);
});

// Handle log level slider
document.addEventListener('DOMContentLoaded', function() {
    const logLevelSlider = document.getElementById('log_level_slider');
    const logLevelSelect = document.querySelector('select[name="syslog_level"]');
    
    if (logLevelSlider && logLevelSelect) {
        // Map log levels to slider values
        const logLevels = [
            'emergency', // 0
            'alert',     // 1
            'critical',  // 2
            'error',     // 3
            'warning',   // 4
            'notice',    // 5
            'informational', // 6
            'debug'      // 7
        ];
        
        // Update select when slider changes
        logLevelSlider.addEventListener('input', function() {
            const level = logLevels[this.value];
            logLevelSelect.value = level;
        });
        
        // Update slider when select changes
        logLevelSelect.addEventListener('change', function() {
            const level = this.value;
            const index = logLevels.indexOf(level);
            if (index !== -1) {
                logLevelSlider.value = index;
            }
        });
    }
});

// Initialize dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
    // Check if we should add dark mode
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
    }
    
    // Add toggle button if it exists
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            // Redraw charts if needed
            if (typeof Plotly !== 'undefined') {
                const plots = document.querySelectorAll('[id^="plotly"]');
                plots.forEach(plot => {
                    Plotly.relayout(plot.id, {
                        template: document.body.classList.contains('dark-mode') ? 'plotly_dark' : 'plotly'
                    });
                });
            }
            
            // Redraw topology if needed
            if (typeof topology !== 'undefined') {
                topology.darkMode = document.body.classList.contains('dark-mode');
                topology.updateVisualization();
            }
        });
    }
});

// Auto-resize visualizations on window resize
window.addEventListener('resize', function() {
    if (typeof topology !== 'undefined') {
        topology.resize();
    }
});