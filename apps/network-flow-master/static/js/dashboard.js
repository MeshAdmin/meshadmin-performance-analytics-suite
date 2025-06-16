/**
 * Dashboard Visualization
 * Provides interactive visualizations for the main dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up time period buttons
    const timePeriodButtons = document.querySelectorAll('.time-period-selector');
    if (timePeriodButtons.length > 0) {
        timePeriodButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                timePeriodButtons.forEach(btn => btn.classList.remove('active'));
                // Add active class to clicked button
                this.classList.add('active');
                // Update dashboard with the selected time period
                loadDashboardData(this.dataset.period);
            });
        });
    }
    
    // Initialize charts with available data
    initializeCharts();
});

/**
 * Load dashboard data from the API
 * @param {string} timePeriod - The time period to retrieve data for ('hour', 'day', 'week')
 */
function loadDashboardData(timePeriod = 'hour') {
    showLoading();
    
    // Fetch dashboard data
    fetch(`/api/flow_stats?period=${timePeriod}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            renderDashboard(data);
        })
        .catch(error => {
            hideLoading();
            showError('Failed to load dashboard data. Please try again later.');
            console.error('Error loading dashboard data:', error);
        });
}

/**
 * Render dashboard with the fetched data
 * @param {Object} data - Dashboard data from the API
 */
function renderDashboard(data) {
    // Render statistics cards
    renderStatisticsCards(data.statistics);
    
    // Render time series chart
    renderTimeSeriesChart(data.time_series);
    
    // Render protocol distribution chart
    renderProtocolDistributionChart(data.statistics.protocol_distribution);
    
    // Render top source IPs chart
    renderTopSourcesChart(data.statistics.top_source_ips);
    
    // Render top destination IPs chart
    renderTopDestinationsChart(data.statistics.top_destination_ips);
    
    // Render recent flows table
    renderRecentFlowsTable(data.recent_flows);
    
    // Render devices table
    renderDevicesTable(data.devices);
}

/**
 * Render statistics cards
 * @param {Object} statistics - Dashboard statistics data
 */
function renderStatisticsCards(statistics) {
    // Update count elements if they exist
    const totalFlowsElement = document.getElementById('total-flows');
    const netflowCountElement = document.getElementById('netflow-count');
    const sflowCountElement = document.getElementById('sflow-count');
    const deviceCountElement = document.getElementById('device-count');
    
    if (totalFlowsElement) totalFlowsElement.textContent = formatNumber(statistics.total_flows);
    if (netflowCountElement) netflowCountElement.textContent = formatNumber(statistics.netflow_count);
    if (sflowCountElement) sflowCountElement.textContent = formatNumber(statistics.sflow_count);
    if (deviceCountElement) deviceCountElement.textContent = formatNumber(statistics.device_count);
}

/**
 * Render time series chart
 * @param {Object} timeSeriesData - Time series data
 */
function renderTimeSeriesChart(timeSeriesData) {
    const ctx = document.getElementById('flow-time-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.flowTimeChart) {
        window.flowTimeChart.destroy();
    }
    
    // Create chart
    window.flowTimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeSeriesData.labels,
            datasets: [
                {
                    label: 'NetFlow',
                    data: timeSeriesData.netflow,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'sFlow',
                    data: timeSeriesData.sflow,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Flow Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += formatNumber(context.raw);
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render protocol distribution chart
 * @param {Object} protocolData - Protocol distribution data
 */
function renderProtocolDistributionChart(protocolData) {
    const ctx = document.getElementById('protocol-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.protocolChart) {
        window.protocolChart.destroy();
    }
    
    // Prepare data for chart
    const labels = Object.keys(protocolData).map(key => getProtocolName(key));
    const data = Object.values(protocolData);
    
    // Chart colors
    const backgroundColors = [
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
        'rgba(201, 203, 207, 0.8)'
    ];
    
    // Create chart
    window.protocolChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: backgroundColors.map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${percentage}% (${formatNumber(value)})`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render top source IPs chart
 * @param {Object} sourceData - Top source IPs data
 */
function renderTopSourcesChart(sourceData) {
    const ctx = document.getElementById('source-ips-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.sourceIpsChart) {
        window.sourceIpsChart.destroy();
    }
    
    // Prepare data for chart
    const labels = Object.keys(sourceData);
    const data = Object.values(sourceData);
    
    // Create chart
    window.sourceIpsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Flow Count',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.8)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Flow Count'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = 'Flow Count: ';
                            label += formatNumber(context.raw);
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render top destination IPs chart
 * @param {Object} destinationData - Top destination IPs data
 */
function renderTopDestinationsChart(destinationData) {
    const ctx = document.getElementById('destination-ips-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.destinationIpsChart) {
        window.destinationIpsChart.destroy();
    }
    
    // Prepare data for chart
    const labels = Object.keys(destinationData);
    const data = Object.values(destinationData);
    
    // Create chart
    window.destinationIpsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Flow Count',
                data: data,
                backgroundColor: 'rgba(255, 99, 132, 0.8)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Flow Count'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = 'Flow Count: ';
                            label += formatNumber(context.raw);
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render recent flows table
 * @param {Array} flows - Recent flows data
 */
function renderRecentFlowsTable(flows) {
    const tableBody = document.getElementById('recent-flows-table-body');
    tableBody.innerHTML = '';
    
    flows.forEach(flow => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(flow.timestamp).toLocaleString()}</td>
            <td>${flow.flow_type}</td>
            <td>${flow.src_ip}:${flow.src_port}</td>
            <td>${flow.dst_ip}:${flow.dst_port}</td>
            <td>${getProtocolName(flow.protocol)}</td>
            <td>${formatNumber(flow.bytes)}</td>
            <td>${formatNumber(flow.packets)}</td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Render devices table
 * @param {Array} devices - Devices data
 */
function renderDevicesTable(devices) {
    const tableBody = document.getElementById('devices-table-body');
    tableBody.innerHTML = '';
    
    devices.forEach(device => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <a href="/ai_insights/${device.id}">${device.name}</a>
            </td>
            <td>${device.ip_address}</td>
            <td>${device.flow_type} v${device.flow_version}</td>
            <td>${new Date(device.last_seen).toLocaleString()}</td>
            <td>${formatNumber(device.statistics.flow_count)}</td>
            <td>
                <a href="/analyzer?device_id=${device.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-chart-line"></i>
                </a>
                <a href="/ai_insights/${device.id}" class="btn btn-sm btn-outline-info">
                    <i class="fas fa-brain"></i>
                </a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Update last refreshed timestamp
 */
function updateLastRefreshed() {
    document.getElementById('last-refreshed').textContent = new Date().toLocaleString();
}

/**
 * Show loading indicator
 */
function showLoading() {
    document.getElementById('loading-overlay').classList.remove('d-none');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('d-none');
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showError(message) {
    const errorContainer = document.getElementById('error-container');
    errorContainer.textContent = message;
    errorContainer.classList.remove('d-none');
    
    // Hide error after 5 seconds
    setTimeout(() => {
        errorContainer.classList.add('d-none');
    }, 5000);
}

/**
 * Format number with commas
 * @param {number} num - Number to format
 * @return {string} Formatted number
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Initialize charts with default empty data
 */
function initializeCharts() {
    // Initialize flow rate chart
    const flowRateCtx = document.getElementById('flow-rate-chart');
    if (flowRateCtx) {
        window.flowRateChart = new Chart(flowRateCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'NetFlow',
                        data: [],
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'sFlow',
                        data: [],
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Flow Count'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }

    // Initialize protocol chart
    const protocolCtx = document.getElementById('protocol-chart');
    if (protocolCtx) {
        window.protocolChart = new Chart(protocolCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['TCP', 'UDP', 'ICMP'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // Load actual data
    loadDashboardData('hour');
}

/**
 * Get protocol name from protocol number
 * @param {number|string} protocol - Protocol number
 * @return {string} Protocol name
 */
function getProtocolName(protocol) {
    // Convert to number if it's a string
    if (typeof protocol === 'string') {
        protocol = parseInt(protocol, 10);
    }
    
    const protocolMap = {
        1: 'ICMP',
        6: 'TCP',
        17: 'UDP',
        47: 'GRE',
        50: 'ESP',
        89: 'OSPF'
    };
    
    return protocolMap[protocol] || `Protocol ${protocol}`;
}
