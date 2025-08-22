/**
 * Flow Analyzer Visualization
 * Provides interactive visualizations for flow data analysis
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers
    flatpickr('.datepicker', {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true
    });
    
    // Set default date range to last 24 hours
    const now = new Date();
    const yesterday = new Date(now.getTime() - (24 * 60 * 60 * 1000));
    
    document.getElementById('start-date').value = formatDateTime(yesterday);
    document.getElementById('end-date').value = formatDateTime(now);
    
    // Get device ID from query parameter, if present
    const deviceId = getQueryParameter('device_id');
    if (deviceId) {
        document.getElementById('device-filter').value = deviceId;
    }
    
    // Load initial data
    loadFlowStatistics();
    
    // Set up event listeners
    document.getElementById('apply-filters').addEventListener('click', function() {
        loadFlowStatistics();
    });
    
    document.getElementById('reset-filters').addEventListener('click', function() {
        resetFilters();
    });
    
    document.getElementById('export-data').addEventListener('click', function() {
        exportData();
    });
    
    // Refresh data automatically every 5 minutes
    setInterval(function() {
        if (document.getElementById('auto-refresh').checked) {
            loadFlowStatistics();
        }
    }, 300000); // 5 minutes
});

/**
 * Load flow statistics based on current filters
 */
function loadFlowStatistics() {
    showLoading();
    
    // Get filter values
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const deviceId = document.getElementById('device-filter').value;
    const srcIp = document.getElementById('src-ip-filter').value;
    const dstIp = document.getElementById('dst-ip-filter').value;
    const protocol = document.getElementById('protocol-filter').value;
    
    // Build query string
    let queryParams = [];
    if (startDate) queryParams.push(`start_time=${encodeURIComponent(startDate)}`);
    if (endDate) queryParams.push(`end_time=${encodeURIComponent(endDate)}`);
    if (deviceId) queryParams.push(`device_id=${encodeURIComponent(deviceId)}`);
    if (srcIp) queryParams.push(`src_ip=${encodeURIComponent(srcIp)}`);
    if (dstIp) queryParams.push(`dst_ip=${encodeURIComponent(dstIp)}`);
    if (protocol) queryParams.push(`protocol=${encodeURIComponent(protocol)}`);
    
    const queryString = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';
    
    // Fetch data from API
    fetch(`/api/analyzer/flow_statistics${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            renderFlowStatistics(data);
            updateLastRefreshed();
        })
        .catch(error => {
            hideLoading();
            showError('Failed to load flow statistics. Please try again later.');
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Render flow statistics visualizations
 * @param {Object} data - Flow statistics data from the API
 */
function renderFlowStatistics(data) {
    // Render summary statistics
    renderSummaryStatistics(data.summary);
    
    // Render time series chart
    renderTimeSeriesChart(data.time_series);
    
    // Render flow size distribution chart
    renderFlowSizeDistributionChart(data.flow_size_distribution);
    
    // Render protocol distribution chart
    renderProtocolDistributionChart(data.protocol_distribution);
    
    // Render top talkers tables
    renderTopTalkers(data.top_talkers);
    
    // Render flow data table
    renderFlowTable(data.flows);
}

/**
 * Render summary statistics
 * @param {Object} summary - Summary statistics data
 */
function renderSummaryStatistics(summary) {
    document.getElementById('total-flows').textContent = formatNumber(summary.total_flows);
    document.getElementById('total-bytes').textContent = formatBytes(summary.total_bytes);
    document.getElementById('total-packets').textContent = formatNumber(summary.total_packets);
    document.getElementById('avg-flow-size').textContent = formatBytes(summary.avg_flow_size);
    document.getElementById('unique-src-ips').textContent = formatNumber(summary.unique_src_ips);
    document.getElementById('unique-dst-ips').textContent = formatNumber(summary.unique_dst_ips);
}

/**
 * Render time series chart
 * @param {Object} timeSeriesData - Time series data
 */
function renderTimeSeriesChart(timeSeriesData) {
    const ctx = document.getElementById('time-series-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.timeSeriesChart) {
        window.timeSeriesChart.destroy();
    }
    
    // Create chart
    window.timeSeriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeSeriesData.labels,
            datasets: [
                {
                    label: 'Flows',
                    data: timeSeriesData.flows,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Bytes',
                    data: timeSeriesData.bytes,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Flow Count'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Bytes'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.dataset.yAxisID === 'y1') {
                                label += formatBytes(context.raw);
                            } else {
                                label += formatNumber(context.raw);
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render flow size distribution chart
 * @param {Object} flowSizeData - Flow size distribution data
 */
function renderFlowSizeDistributionChart(flowSizeData) {
    const ctx = document.getElementById('flow-size-distribution-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.flowSizeChart) {
        window.flowSizeChart.destroy();
    }
    
    // Create chart
    window.flowSizeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: flowSizeData.labels,
            datasets: [{
                label: 'Flow Count',
                data: flowSizeData.values,
                backgroundColor: 'rgba(75, 192, 192, 0.8)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
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
                        text: 'Flow Size (bytes)'
                    }
                }
            },
            plugins: {
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
    const ctx = document.getElementById('protocol-distribution-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.protocolChart) {
        window.protocolChart.destroy();
    }
    
    // Prepare data for chart
    const labels = Object.keys(protocolData);
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
 * Render top talkers tables
 * @param {Object} topTalkers - Top talkers data
 */
function renderTopTalkers(topTalkers) {
    // Render top source IPs
    const topSrcIpsTable = document.getElementById('top-source-ips');
    topSrcIpsTable.innerHTML = '';
    
    Object.entries(topTalkers.sources).forEach(([ip, count], index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${ip}</td>
            <td>${formatNumber(count)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="applySourceIpFilter('${ip}')">
                    <i class="fas fa-filter"></i>
                </button>
            </td>
        `;
        topSrcIpsTable.appendChild(row);
    });
    
    // Render top destination IPs
    const topDstIpsTable = document.getElementById('top-destination-ips');
    topDstIpsTable.innerHTML = '';
    
    Object.entries(topTalkers.destinations).forEach(([ip, count], index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${ip}</td>
            <td>${formatNumber(count)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="applyDestinationIpFilter('${ip}')">
                    <i class="fas fa-filter"></i>
                </button>
            </td>
        `;
        topDstIpsTable.appendChild(row);
    });
    
    // Render top flows
    const topFlowsTable = document.getElementById('top-flows');
    topFlowsTable.innerHTML = '';
    
    topTalkers.flows.forEach((flow, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${flow.src_ip}</td>
            <td>${flow.dst_ip}</td>
            <td>${getProtocolName(flow.protocol)}</td>
            <td>${formatBytes(flow.bytes)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewFlowDetails(${flow.id})">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        `;
        topFlowsTable.appendChild(row);
    });
}

/**
 * Render flow data table
 * @param {Array} flows - Flow data array
 */
function renderFlowTable(flows) {
    const flowTable = document.getElementById('flow-data-table').getElementsByTagName('tbody')[0];
    flowTable.innerHTML = '';
    
    flows.forEach(flow => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(flow.timestamp).toLocaleString()}</td>
            <td>${flow.src_ip}</td>
            <td>${flow.src_port}</td>
            <td>${flow.dst_ip}</td>
            <td>${flow.dst_port}</td>
            <td>${getProtocolName(flow.protocol)}</td>
            <td>${formatBytes(flow.bytes)}</td>
            <td>${flow.packets}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewFlowDetails(${flow.id})">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        `;
        flowTable.appendChild(row);
    });
    
    // Enable DataTables for the flow table
    if (!$.fn.DataTable.isDataTable('#flow-data-table')) {
        $('#flow-data-table').DataTable({
            order: [[0, 'desc']],
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100],
            responsive: true
        });
    } else {
        $('#flow-data-table').DataTable().clear().rows.add($(flowTable).find('tr')).draw();
    }
}

/**
 * View flow details
 * @param {number} flowId - Flow ID
 */
function viewFlowDetails(flowId) {
    // Fetch flow details from API
    fetch(`/api/analyzer/flow/${flowId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            showFlowDetailsModal(data);
        })
        .catch(error => {
            showError('Failed to load flow details. Please try again later.');
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Show flow details modal
 * @param {Object} flow - Flow details data
 */
function showFlowDetailsModal(flow) {
    // Set modal content
    document.getElementById('flow-details-id').textContent = flow.id;
    document.getElementById('flow-details-timestamp').textContent = new Date(flow.timestamp).toLocaleString();
    document.getElementById('flow-details-src-ip').textContent = flow.src_ip;
    document.getElementById('flow-details-src-port').textContent = flow.src_port;
    document.getElementById('flow-details-dst-ip').textContent = flow.dst_ip;
    document.getElementById('flow-details-dst-port').textContent = flow.dst_port;
    document.getElementById('flow-details-protocol').textContent = getProtocolName(flow.protocol);
    document.getElementById('flow-details-bytes').textContent = formatBytes(flow.bytes);
    document.getElementById('flow-details-packets').textContent = flow.packets;
    
    // Additional flow details
    const additionalDetailsContainer = document.getElementById('flow-details-additional');
    additionalDetailsContainer.innerHTML = '';
    
    const additionalFields = ['tos', 'tcp_flags', 'start_time', 'end_time', 'duration', 'bits_per_second', 'packets_per_second'];
    
    additionalFields.forEach(field => {
        if (flow[field] !== undefined && flow[field] !== null) {
            const row = document.createElement('tr');
            let value = flow[field];
            
            // Format specific fields
            if (field === 'tcp_flags') {
                value = formatTcpFlags(value);
            } else if (field === 'duration') {
                value = `${value.toFixed(2)} seconds`;
            } else if (field === 'bits_per_second') {
                value = `${formatNumber(value)} bps`;
            } else if (field === 'packets_per_second') {
                value = `${formatNumber(value)} pps`;
            } else if (field === 'start_time' || field === 'end_time') {
                value = new Date(value).toLocaleString();
            }
            
            row.innerHTML = `
                <th>${formatFieldName(field)}</th>
                <td>${value}</td>
            `;
            additionalDetailsContainer.appendChild(row);
        }
    });
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('flow-details-modal'));
    modal.show();
}

/**
 * Apply source IP filter
 * @param {string} ip - Source IP to filter
 */
function applySourceIpFilter(ip) {
    document.getElementById('src-ip-filter').value = ip;
    loadFlowStatistics();
}

/**
 * Apply destination IP filter
 * @param {string} ip - Destination IP to filter
 */
function applyDestinationIpFilter(ip) {
    document.getElementById('dst-ip-filter').value = ip;
    loadFlowStatistics();
}

/**
 * Apply protocol filter
 * @param {string} protocol - Protocol to filter
 */
function applyProtocolFilter(protocol) {
    document.getElementById('protocol-filter').value = protocol;
    loadFlowStatistics();
}

/**
 * Reset all filters
 */
function resetFilters() {
    // Reset date range to last 24 hours
    const now = new Date();
    const yesterday = new Date(now.getTime() - (24 * 60 * 60 * 1000));
    
    document.getElementById('start-date').value = formatDateTime(yesterday);
    document.getElementById('end-date').value = formatDateTime(now);
    
    // Reset other filters
    document.getElementById('device-filter').value = '';
    document.getElementById('src-ip-filter').value = '';
    document.getElementById('dst-ip-filter').value = '';
    document.getElementById('protocol-filter').value = '';
    
    // Load data with reset filters
    loadFlowStatistics();
}

/**
 * Export data to CSV
 */
function exportData() {
    // Get filter values
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const deviceId = document.getElementById('device-filter').value;
    const srcIp = document.getElementById('src-ip-filter').value;
    const dstIp = document.getElementById('dst-ip-filter').value;
    const protocol = document.getElementById('protocol-filter').value;
    
    // Build query string
    let queryParams = [];
    if (startDate) queryParams.push(`start_time=${encodeURIComponent(startDate)}`);
    if (endDate) queryParams.push(`end_time=${encodeURIComponent(endDate)}`);
    if (deviceId) queryParams.push(`device_id=${encodeURIComponent(deviceId)}`);
    if (srcIp) queryParams.push(`src_ip=${encodeURIComponent(srcIp)}`);
    if (dstIp) queryParams.push(`dst_ip=${encodeURIComponent(dstIp)}`);
    if (protocol) queryParams.push(`protocol=${encodeURIComponent(protocol)}`);
    
    const queryString = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';
    
    // Redirect to CSV export endpoint
    window.location.href = `/api/analyzer/export_csv${queryString}`;
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
 * Format bytes to human-readable format
 * @param {number} bytes - Bytes to format
 * @return {string} Formatted bytes
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format date-time for input fields
 * @param {Date} date - Date to format
 * @return {string} Formatted date-time string
 */
function formatDateTime(date) {
    return date.toISOString().slice(0, 16).replace('T', ' ');
}

/**
 * Format TCP flags
 * @param {number} flags - TCP flags as a number
 * @return {string} Formatted TCP flags
 */
function formatTcpFlags(flags) {
    const flagsMap = {
        1: 'FIN',
        2: 'SYN',
        4: 'RST',
        8: 'PSH',
        16: 'ACK',
        32: 'URG',
        64: 'ECE',
        128: 'CWR'
    };
    
    let result = [];
    
    for (const [bit, name] of Object.entries(flagsMap)) {
        if ((flags & bit) !== 0) {
            result.push(name);
        }
    }
    
    return result.length > 0 ? result.join(', ') : 'None';
}

/**
 * Format field name for display
 * @param {string} field - Field name
 * @return {string} Formatted field name
 */
function formatFieldName(field) {
    // Convert snake_case to Title Case
    return field
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Get protocol name from protocol number
 * @param {number} protocol - Protocol number
 * @return {string} Protocol name
 */
function getProtocolName(protocol) {
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

/**
 * Get query parameter value by name
 * @param {string} name - Parameter name
 * @return {string} Parameter value or empty string
 */
function getQueryParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name) || '';
}
