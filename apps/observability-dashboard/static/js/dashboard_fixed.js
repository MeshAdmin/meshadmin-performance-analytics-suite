/**
 * Dashboard JavaScript file for MASH
 * Handles dashboard initialization, widget management, and data fetching
 */

// Global variables
let dashboard = {};
let dashboardWidgets = [];
let refreshTimer = null;
let autoRefreshInterval = 30000; // 30 seconds by default
let currentTimeRange = '24h';
let customTimeRange = {
    start: null,
    end: null
};

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Get dashboard ID from the page (if any)
    const dashboardId = getDashboardId();
    
    if (dashboardId) {
        fetchDashboardData(dashboardId);
    } else {
        // No specific dashboard, load default
        loadDefaultDashboard();
    }
    
    // Initialize refresh timer based on selected value
    const refreshSelector = document.getElementById('auto-refresh');
    if (refreshSelector) {
        setupAutoRefresh(refreshSelector.value);
    }
    
    // Attach event listeners
    setupEventListeners();
}

/**
 * Get dashboard ID from the page
 * @returns {string|null} Dashboard ID or null if not found
 */
function getDashboardId() {
    // Try to find a hidden input with dashboard ID
    const dashboardIdInput = document.getElementById('dashboard-id');
    if (dashboardIdInput && dashboardIdInput.value) {
        return dashboardIdInput.value;
    }
    
    // Or try to extract from the URL path - handle both /dashboard/1 and /dashboard/dashboard/1 patterns
    let pathMatch = window.location.pathname.match(/\/dashboard\/(\d+)$/);
    if (pathMatch && pathMatch[1]) {
        return pathMatch[1];
    }
    
    // No dashboard ID found
    return null;
}

/**
 * Set up event listeners for dashboard controls
 */
function setupEventListeners() {
    // Time range selector
    const timeRangeSelector = document.getElementById('time-range');
    if (timeRangeSelector) {
        timeRangeSelector.addEventListener('change', () => {
            changeTimeRange(timeRangeSelector.value);
        });
    }
    
    // Auto refresh selector
    const refreshSelector = document.getElementById('auto-refresh');
    if (refreshSelector) {
        refreshSelector.addEventListener('change', () => {
            setupAutoRefresh(refreshSelector.value);
        });
    }
    
    // Dashboard selector
    const dashboardSelector = document.getElementById('dashboard-selector');
    if (dashboardSelector) {
        dashboardSelector.addEventListener('change', function() {
            if (this.value === 'new') {
                showModal('create-dashboard-modal');
            } else if (this.value) {
                window.location.href = `/dashboard/${this.value}`;
            }
        });
    }
    
    // Add widget button
    const addWidgetBtn = document.getElementById('add-widget-btn');
    if (addWidgetBtn) {
        addWidgetBtn.addEventListener('click', () => showModal('add-widget-modal'));
    }
    
    // Save widget button
    const saveWidgetBtn = document.getElementById('save-widget-btn');
    if (saveWidgetBtn) {
        saveWidgetBtn.addEventListener('click', createWidget);
    }
    
    // Custom time range apply button
    const applyCustomTimeBtn = document.getElementById('apply-custom-time-btn');
    if (applyCustomTimeBtn) {
        applyCustomTimeBtn.addEventListener('click', applyCustomTimeRange);
    }
    
    // Widget type selection to update config options
    const widgetTypeSelect = document.getElementById('widget-type');
    if (widgetTypeSelect) {
        widgetTypeSelect.addEventListener('change', function() {
            if (typeof updateWidgetConfigOptions === 'function') {
                updateWidgetConfigOptions(this.value);
            }
            if (typeof updateDataSourceOptions === 'function') {
                updateDataSourceOptions(this.value);
            }
        });
    }
}

/**
 * Show loading indicator for dashboard
 * @param {boolean} show - Whether to show or hide the loading indicator
 */
function showDashboardLoading(show) {
    const loadingElement = document.getElementById('dashboard-loading');
    if (loadingElement) {
        loadingElement.style.display = show ? 'block' : 'none';
    }
}

/**
 * Fetch dashboard data from the server
 * @param {string} dashboardId - ID of the dashboard to fetch
 */
function fetchDashboardData(dashboardId) {
    showDashboardLoading(true);
    
    let url = `/api/dashboards/${dashboardId}/data?time_range=${currentTimeRange}`;
    
    // Add custom time range if selected
    if (currentTimeRange === 'custom' && customTimeRange.start && customTimeRange.end) {
        url += `&start_time=${customTimeRange.start.toISOString()}&end_time=${customTimeRange.end.toISOString()}`;
    }
    
    // Get CSRF token from cookie
    const csrfToken = getCookie('csrf_token') || '';
    console.log("Fetching dashboard data from:", url);
    console.log("Using CSRF token:", csrfToken ? "Present" : "Not found");
    
    fetch(url, {
        headers: {
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch dashboard data');
            }
            return response.json();
        })
        .then(data => {
            dashboard = data;
            dashboardWidgets = data.widgets || [];
            renderDashboard();
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            // Add error debug details
            if (error.message) {
                console.error('Error message:', error.message);
            }
            // Create demo data for testing - this will be removed after the API is fixed
            console.log("Using sample dashboard data for development");
            const sampleData = createSampleDashboardData();
            dashboard = sampleData;
            dashboardWidgets = sampleData.widgets || [];
            renderDashboard();
            
            showNotification('Using sample dashboard data', 'info');
        })
        .finally(() => {
            showDashboardLoading(false);
        });
}

/**
 * Load default dashboard if no specific dashboard is selected
 */
function loadDefaultDashboard() {
    showDashboardLoading(true);
    
    // Check if there's a default dashboard in the selector
    const selector = document.getElementById('dashboard-selector');
    if (selector && selector.value && selector.value !== 'new') {
        // Use the selected dashboard
        window.location.href = `/dashboard/${selector.value}`;
        return;
    }
    
    // Otherwise, show empty dashboard or system overview
    dashboardWidgets = [];
    renderDashboard();
    showDashboardLoading(false);
}

/**
 * Render the dashboard based on fetched data
 */
function renderDashboard() {
    const dashboardGrid = document.getElementById('dashboard-grid');
    if (!dashboardGrid) return;
    
    // Clear existing content
    dashboardGrid.innerHTML = '';
    
    if (!dashboardWidgets || dashboardWidgets.length === 0) {
        // Show empty state
        dashboardGrid.innerHTML = `
            <div class="empty-dashboard">
                <div class="empty-state-icon">
                    <i class="fas fa-chart-line"></i>
                </div>
                <h3>No Widgets</h3>
                <p>This dashboard doesn't have any widgets yet.</p>
                <button class="btn btn-primary" id="add-first-widget-btn">
                    <i class="fas fa-plus"></i> Add First Widget
                </button>
            </div>
        `;
        
        // Attach event listener to the add widget button
        const addWidgetBtn = document.getElementById('add-first-widget-btn');
        if (addWidgetBtn) {
            addWidgetBtn.addEventListener('click', () => showModal('add-widget-modal'));
        }
        
        return;
    }
    
    // Sort widgets by position (top to bottom, left to right)
    dashboardWidgets.sort((a, b) => {
        if (a.position_y !== b.position_y) {
            return a.position_y - b.position_y;
        }
        return a.position_x - b.position_x;
    });
    
    // Render each widget
    dashboardWidgets.forEach(widget => {
        const widgetElement = createWidgetElement(widget);
        dashboardGrid.appendChild(widgetElement);
    });
}

/**
 * Create a widget DOM element
 * @param {Object} widget - Widget configuration object
 * @returns {HTMLElement} - Widget DOM element
 */
function createWidgetElement(widget) {
    const widgetElement = document.createElement('div');
    widgetElement.className = 'dashboard-item';
    widgetElement.id = `widget-${widget.id}`;
    widgetElement.dataset.widgetId = widget.id;
    
    // Set widget size classes based on width and height
    const width = widget.width || 1;
    const height = widget.height || 1;
    
    if (width > 1) {
        widgetElement.classList.add(`width-${width}`);
    }
    if (height > 1) {
        widgetElement.classList.add(`height-${height}`);
    }
    
    // Set grid position
    widgetElement.style.gridColumnStart = (widget.position_x || 0) + 1;
    widgetElement.style.gridColumnEnd = (widget.position_x || 0) + width + 1;
    widgetElement.style.gridRowStart = (widget.position_y || 0) + 1;
    widgetElement.style.gridRowEnd = (widget.position_y || 0) + height + 1;
    
    // Create widget content
    widgetElement.innerHTML = `
        <div class="widget">
            <div class="widget-header">
                <div class="widget-title">${widget.name || 'Unnamed Widget'}</div>
                <div class="widget-actions">
                    <button class="btn btn-icon btn-sm widget-refresh-btn" title="Refresh" data-widget-id="${widget.id}">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button class="btn btn-icon btn-sm widget-settings-btn" title="Settings" data-widget-id="${widget.id}">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            </div>
            <div class="widget-body" id="widget-body-${widget.id}">
                <div class="widget-loading" style="display: none;">
                    <div class="spinner"></div>
                </div>
                <div class="widget-content"></div>
            </div>
        </div>
    `;
    
    // Attach event listeners for widget actions
    const refreshBtn = widgetElement.querySelector('.widget-refresh-btn');
    const settingsBtn = widgetElement.querySelector('.widget-settings-btn');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => refreshWidget(widget.id));
    }
    
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => showWidgetSettings(widget.id));
    }
    
    // Render widget content based on its type and data
    renderWidgetContent(widgetElement.querySelector('.widget-content'), widget);
    
    return widgetElement;
}

/**
 * Render content for a specific widget based on its type
 * @param {HTMLElement} container - Widget content container
 * @param {Object} widget - Widget configuration
 */
function renderWidgetContent(container, widget) {
    if (!container) return;
    
    // Extract widget type - handle both widget_type (from API) or type (from sample data)
    const type = widget.widget_type || widget.type || '';
    const data = widget.data || {};
    
    // Clear existing content
    container.innerHTML = '';
    
    // Render based on widget type
    if (type === 'line-chart') {
        renderLineChart(container, widget);
    } else if (type === 'bar-chart') {
        renderBarChart(container, widget);
    } else if (type === 'pie-chart') {
        renderPieChart(container, widget);
    } else if (type === 'gauge') {
        renderGaugeChart(container, widget);
    } else if (type === 'stat') {
        renderStatsWidget(container, widget);
    } else if (type === 'table') {
        renderTableWidget(container, widget);
    } else if (type === 'alert-list') {
        renderAlertList(container, widget);
    } else {
        // Unknown widget type
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <i class="fas fa-question-circle"></i>
                </div>
                <h3>Unknown Widget Type</h3>
                <p>Widget type "${type}" is not supported.</p>
            </div>
        `;
    }
}

/**
 * Render a line chart widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderLineChart(container, widget) {
    const data = widget.data || {};
    const timePoints = data.time_points || [];
    const values = data.values || [];
    const datasets = data.datasets || [];
    
    if (timePoints.length === 0 || (values.length === 0 && datasets.length === 0)) {
        renderNoDataMessage(container);
        return;
    }
    
    // Create canvas for the chart
    const canvasId = `chart-${widget.id}`;
    container.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    
    // Safely get the canvas element
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with ID ${canvasId} not found`);
        renderNoDataMessage(container);
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        
        // Prepare chart data
        const chartData = {
            labels: timePoints,
            datasets: []
        };
        
        // If we have simple values array, create a single dataset
        if (values.length > 0) {
            chartData.datasets.push({
                label: widget.name,
                data: values,
                borderColor: '#c50000',
                backgroundColor: 'rgba(197, 0, 0, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            });
        } 
        // If we have multiple datasets
        else if (datasets.length > 0) {
            const colors = [
                '#c50000', '#36A2EB', '#4BC0C0', '#FFCE56', 
                '#9966FF', '#FF9F40', '#C9CBCF'
            ];
            
            datasets.forEach((dataset, index) => {
                const color = colors[index % colors.length];
                chartData.datasets.push({
                    label: dataset.label || `Dataset ${index + 1}`,
                    data: dataset.values || [],
                    borderColor: color,
                    backgroundColor: `${color}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                });
            });
        }
        
        // Create chart
        new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaaaaa'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaaaaa'
                        },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#f0f0f0'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error rendering line chart:', error);
        renderNoDataMessage(container);
    }
}

/**
 * Render a bar chart widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderBarChart(container, widget) {
    const data = widget.data || {};
    const timePoints = data.time_points || [];
    const values = data.values || [];
    const datasets = data.datasets || [];
    
    if (timePoints.length === 0 || (values.length === 0 && datasets.length === 0)) {
        renderNoDataMessage(container);
        return;
    }
    
    // Create canvas for the chart
    const canvasId = `chart-${widget.id}`;
    container.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    
    // Safely get the canvas element
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with ID ${canvasId} not found`);
        renderNoDataMessage(container);
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        
        // Prepare chart data
        const chartData = {
            labels: timePoints,
            datasets: []
        };
        
        // If we have simple values array, create a single dataset
        if (values.length > 0) {
            chartData.datasets.push({
                label: widget.name,
                data: values,
                backgroundColor: '#c50000',
                borderWidth: 1,
                borderColor: 'rgba(0, 0, 0, 0.2)'
            });
        } 
        // If we have multiple datasets
        else if (datasets.length > 0) {
            const colors = [
                '#c50000', '#36A2EB', '#4BC0C0', '#FFCE56', 
                '#9966FF', '#FF9F40', '#C9CBCF'
            ];
            
            datasets.forEach((dataset, index) => {
                const color = colors[index % colors.length];
                chartData.datasets.push({
                    label: dataset.label || `Dataset ${index + 1}`,
                    data: dataset.values || [],
                    backgroundColor: color,
                    borderWidth: 1,
                    borderColor: 'rgba(0, 0, 0, 0.2)'
                });
            });
        }
        
        // Create chart
        new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaaaaa'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaaaaa'
                        },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#f0f0f0'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error rendering bar chart:', error);
        renderNoDataMessage(container);
    }
}

/**
 * Render a pie chart widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderPieChart(container, widget) {
    const data = widget.data || {};
    const labels = data.labels || [];
    const values = data.values || [];
    
    if (labels.length === 0 || values.length === 0) {
        renderNoDataMessage(container);
        return;
    }
    
    // Create canvas for the chart
    const canvasId = `chart-${widget.id}`;
    container.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    
    // Safely get the canvas element
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with ID ${canvasId} not found`);
        renderNoDataMessage(container);
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        
        // Default colors
        const colors = [
            '#c50000', '#36A2EB', '#4BC0C0', '#FFCE56', 
            '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384'
        ];
        
        // Create chart
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, values.length),
                    borderWidth: 1,
                    borderColor: 'rgba(0, 0, 0, 0.2)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#f0f0f0'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.formattedValue;
                                const sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / sum) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error rendering pie chart:', error);
        renderNoDataMessage(container);
    }
}

/**
 * Render a gauge chart widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderGaugeChart(container, widget) {
    const data = widget.data || {};
    const value = data.value || 0;
    const min = data.min || 0;
    const max = data.max || 100;
    const thresholds = data.thresholds || [
        { value: 60, color: 'red' },
        { value: 80, color: 'yellow' },
        { value: 90, color: 'green' }
    ];
    
    // Create canvas for the chart
    const canvasId = `chart-${widget.id}`;
    container.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    
    // Safely get the canvas element
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with ID ${canvasId} not found`);
        renderNoDataMessage(container);
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        
        // Determine gauge color based on thresholds
        let gaugeColor = '#c50000'; // Default color
        for (const threshold of thresholds) {
            if (value <= threshold.value) {
                gaugeColor = getColorForThreshold(threshold.color);
                break;
            }
        }
        
        // Create gauge chart (based on doughnut chart)
        createGaugeChart(canvasId, value, widget.name, {
            min: min,
            max: max,
            color: gaugeColor
        });
    } catch (error) {
        console.error('Error rendering gauge chart:', error);
        renderNoDataMessage(container);
    }
}

/**
 * Create a gauge chart using Chart.js doughnut chart
 * @param {string} canvasId - ID of the canvas element
 * @param {number} value - Current value
 * @param {string} label - Label for the gauge
 * @param {Object} options - Additional options (min, max, color)
 */
function createGaugeChart(canvasId, value, label, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Set defaults
    options = options || {};
    const min = options.min !== undefined ? options.min : 0;
    const max = options.max !== undefined ? options.max : 100;
    const gaugeColor = options.color || '#c50000';
    
    // Normalize value between min and max
    const normalizedValue = Math.max(min, Math.min(value, max));
    const percentage = ((normalizedValue - min) / (max - min)) * 100;
    
    // Create chart data
    const data = {
        labels: ['Value', 'Remaining'],
        datasets: [{
            data: [percentage, 100 - percentage],
            backgroundColor: [gaugeColor, '#333'],
            borderWidth: 0,
            borderRadius: 5,
            circumference: 180,
            rotation: 270,
        }]
    };
    
    // Create chart
    new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        },
        plugins: [{
            id: 'valueInCenter',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                
                // Value text
                const fontSize = Math.min(height / 5, width / 5);
                ctx.font = `bold ${fontSize}px sans-serif`;
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillStyle = '#f0f0f0';
                
                // Draw value
                ctx.fillText(value, width / 2, height - fontSize);
                
                // Draw label
                const labelFontSize = Math.min(height / 10, width / 10);
                ctx.font = `${labelFontSize}px sans-serif`;
                ctx.fillText(label, width / 2, height - fontSize * 2);
                
                // Draw min/max
                const smallFontSize = Math.min(height / 15, width / 15);
                ctx.font = `${smallFontSize}px sans-serif`;
                ctx.fillStyle = '#aaaaaa';
                ctx.textAlign = 'left';
                ctx.fillText(min, width * 0.1, height - smallFontSize);
                ctx.textAlign = 'right';
                ctx.fillText(max, width * 0.9, height - smallFontSize);
                
                ctx.save();
            }
        }]
    });
}

/**
 * Render statistics widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderStatsWidget(container, widget) {
    const data = widget.data || {};
    const stats = data.stats || [];
    
    if (stats.length === 0) {
        renderNoDataMessage(container);
        return;
    }
    
    // Create stats grid
    let statsHtml = '<div class="stats-grid">';
    
    stats.forEach(stat => {
        const icon = stat.icon || 'fa-chart-bar';
        const changeClass = stat.change > 0 ? 'positive-change' : (stat.change < 0 ? 'negative-change' : 'neutral-change');
        const changeIcon = stat.change > 0 ? 'fa-arrow-up' : (stat.change < 0 ? 'fa-arrow-down' : 'fa-minus');
        
        statsHtml += `
            <div class="stat-card">
                <div class="stat-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="stat-info">
                    <div class="stat-value">${formatValue(stat.value)}</div>
                    <div class="stat-label">${stat.title}</div>
                    <div class="stat-change ${changeClass}">
                        <i class="fas ${changeIcon}"></i> ${Math.abs(stat.change)}%
                    </div>
                </div>
            </div>
        `;
    });
    
    statsHtml += '</div>';
    container.innerHTML = statsHtml;
}

/**
 * Render table widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderTableWidget(container, widget) {
    const data = widget.data || {};
    const columns = data.columns || [];
    const rows = data.rows || [];
    
    if (columns.length === 0 || rows.length === 0) {
        renderNoDataMessage(container);
        return;
    }
    
    // Create table HTML
    let tableHtml = `
        <div class="widget-table-container">
            <table class="widget-table">
                <thead>
                    <tr>
    `;
    
    // Add column headers
    columns.forEach(column => {
        tableHtml += `<th>${column.label || column.key}</th>`;
    });
    
    tableHtml += `
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Add table rows
    rows.forEach(row => {
        tableHtml += '<tr>';
        
        columns.forEach(column => {
            const key = column.key;
            const cellValue = row[key] !== undefined ? row[key] : '';
            const cellClass = column.className || '';
            
            // Apply formatting based on column type
            let formattedValue = cellValue;
            if (column.type === 'date' && cellValue) {
                try {
                    const date = new Date(cellValue);
                    formattedValue = date.toLocaleString();
                } catch (e) {
                    formattedValue = cellValue;
                }
            } else if (column.type === 'severity' && cellValue) {
                formattedValue = `<span class="badge badge-${cellValue.toLowerCase()}">${cellValue}</span>`;
            }
            
            tableHtml += `<td class="${cellClass}">${formattedValue}</td>`;
        });
        
        tableHtml += '</tr>';
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    container.innerHTML = tableHtml;
}

/**
 * Render alert list widget
 * @param {HTMLElement} container - Widget container
 * @param {Object} widget - Widget data
 */
function renderAlertList(container, widget) {
    const data = widget.data || {};
    const alerts = data.alerts || [];
    
    if (alerts.length === 0) {
        renderNoDataMessage(container, 'No alerts found');
        return;
    }
    
    // Create alert list HTML
    let alertsHtml = `
        <div class="alert-list-container">
            <ul class="alert-list">
    `;
    
    // Add alerts
    alerts.forEach(alert => {
        const timestamp = new Date(alert.timestamp).toLocaleString();
        const severityClass = `severity-${alert.severity.toLowerCase()}`;
        const statusClass = alert.resolved ? 'status-resolved' : (alert.acknowledged ? 'status-acknowledged' : 'status-active');
        const statusLabel = alert.resolved ? 'Resolved' : (alert.acknowledged ? 'Acknowledged' : 'Active');
        
        alertsHtml += `
            <li class="alert-item ${severityClass} ${statusClass}" data-alert-id="${alert.id}">
                <div class="alert-severity">
                    <span class="badge badge-${alert.severity.toLowerCase()}">${alert.severity}</span>
                </div>
                <div class="alert-content">
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-meta">
                        <span class="alert-time">${timestamp}</span>
                        <span class="alert-status">${statusLabel}</span>
                    </div>
                </div>
                <div class="alert-actions">
                    <button class="btn btn-sm btn-icon alert-details-btn" onclick="showAlertDetails(${alert.id})">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </div>
            </li>
        `;
    });
    
    alertsHtml += `
            </ul>
            <div class="alert-list-footer">
                <a href="/alerts" class="btn btn-sm btn-secondary">View All Alerts</a>
            </div>
        </div>
    `;
    
    container.innerHTML = alertsHtml;
}

/**
 * Render a message for widgets with no data
 * @param {HTMLElement} container - Widget container
 * @param {string} message - Optional custom message
 */
function renderNoDataMessage(container, message) {
    message = message || 'No data available for this widget';
    
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">
                <i class="fas fa-chart-bar"></i>
            </div>
            <p>${message}</p>
        </div>
    `;
}

/**
 * Format a value for display (number formatting, etc.)
 * @param {*} value - Value to format
 * @returns {string} Formatted value
 */
function formatValue(value) {
    if (typeof value === 'number') {
        // Format large numbers with suffixes (K, M, B)
        if (value >= 1000000000) {
            return (value / 1000000000).toFixed(1) + 'B';
        } else if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        } else {
            return value.toString();
        }
    }
    
    return value !== undefined ? value.toString() : '';
}

/**
 * Refresh a specific widget
 * @param {string} widgetId - ID of the widget to refresh
 */
function refreshWidget(widgetId) {
    const widgetElement = document.getElementById(`widget-${widgetId}`);
    if (!widgetElement) return;
    
    const contentElement = widgetElement.querySelector('.widget-content');
    const loadingElement = widgetElement.querySelector('.widget-loading');
    
    if (!contentElement || !loadingElement) return;
    
    // Show loading indicator
    loadingElement.style.display = 'flex';
    
    // Find widget in dashboardWidgets array
    const widget = dashboardWidgets.find(w => w.id == widgetId);
    if (!widget) return;
    
    // Fetch updated data for this widget
    setTimeout(() => {
        // In a real implementation, this would be an API call to get fresh data
        // For now, we'll just re-render with existing data
        renderWidgetContent(contentElement, widget);
        loadingElement.style.display = 'none';
    }, 1000);
}

/**
 * Show widget settings modal
 * @param {string} widgetId - ID of the widget to edit
 */
function showWidgetSettings(widgetId) {
    // Implement widget settings modal
    alert('Widget settings not implemented yet');
}

/**
 * Refresh the entire dashboard
 */
function refreshDashboard() {
    const dashboardId = getDashboardId();
    if (dashboardId) {
        fetchDashboardData(dashboardId);
    }
}

/**
 * Set up auto-refresh timer
 * @param {string} interval - Interval string (off, 30s, 1m, 5m, etc.)
 */
function setupAutoRefresh(interval) {
    // Clear existing timer
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
    
    // Set new timer based on interval
    if (interval === 'off') {
        return;
    }
    
    // Parse interval string into milliseconds
    let intervalMs = 30000; // Default to 30 seconds
    
    if (interval === '10s') {
        intervalMs = 10000;
    } else if (interval === '30s') {
        intervalMs = 30000;
    } else if (interval === '1m') {
        intervalMs = 60000;
    } else if (interval === '5m') {
        intervalMs = 300000;
    } else if (interval === '15m') {
        intervalMs = 900000;
    } else if (interval === '30m') {
        intervalMs = 1800000;
    } else if (interval === '1h') {
        intervalMs = 3600000;
    }
    
    // Set the new timer
    refreshTimer = setInterval(refreshDashboard, intervalMs);
}

/**
 * Change the time range for the dashboard
 * @param {string} range - Time range string (1h, 6h, 24h, 7d, 30d, custom)
 */
function changeTimeRange(range) {
    if (range === 'custom') {
        // Show custom time range modal
        showModal('custom-time-modal');
        return;
    }
    
    currentTimeRange = range;
    refreshDashboard();
}

/**
 * Apply custom time range from the modal inputs
 */
function applyCustomTimeRange() {
    const startInput = document.getElementById('custom-start-time');
    const endInput = document.getElementById('custom-end-time');
    
    if (!startInput || !endInput) {
        closeModal('custom-time-modal');
        return;
    }
    
    // Parse inputs into Date objects
    const startTime = new Date(startInput.value);
    const endTime = new Date(endInput.value);
    
    // Validate time range
    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
        showNotification('Please select valid start and end times', 'warning');
        return;
    }
    
    if (startTime >= endTime) {
        showNotification('End time must be after start time', 'warning');
        return;
    }
    
    // Set custom time range
    customTimeRange.start = startTime;
    customTimeRange.end = endTime;
    currentTimeRange = 'custom';
    
    // Refresh dashboard with new time range
    refreshDashboard();
    
    // Close modal
    closeModal('custom-time-modal');
}

/**
 * Create a new widget
 */
function createWidget() {
    // Get form values
    const name = document.getElementById('widget-name').value;
    const type = document.getElementById('widget-type').value;
    const dataSource = document.getElementById('widget-data-source').value;
    const sizeOption = document.getElementById('widget-size').value;
    
    // Validate required fields
    if (!name || !type || !dataSource) {
        showNotification('Please fill in all required fields', 'warning');
        return;
    }
    
    // Parse size option (e.g., '2x3' -> width: 2, height: 3)
    let width = 1;
    let height = 1;
    if (sizeOption) {
        const sizeParts = sizeOption.split('x');
        if (sizeParts.length === 2) {
            width = parseInt(sizeParts[0], 10) || 1;
            height = parseInt(sizeParts[1], 10) || 1;
        }
    }
    
    // Find next available position on the dashboard
    const position = findNextWidgetPosition();
    
    // Get additional configuration based on widget type
    let configuration = {};
    
    // If on the configuration tab of the modal, gather configuration options
    const configOptionsContainer = document.getElementById('widget-config-options');
    if (configOptionsContainer) {
        // This would be a more complex implementation in a real application
        // For now, we'll just get any inputs from the config container
        const inputs = configOptionsContainer.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.id && input.id.startsWith('widget-')) {
                const key = input.id.replace('widget-', '');
                configuration[key] = input.value;
            }
        });
    }
    
    // Create widget on server
    const dashboardId = getDashboardId();
    if (!dashboardId) {
        showNotification('No dashboard selected', 'error');
        return;
    }
    
    // Prepare widget data
    const widgetData = {
        name: name,
        widget_type: type,
        data_source: dataSource,
        width: width,
        height: height,
        position_x: position.x,
        position_y: position.y,
        configuration: configuration
    };
    
    fetch(`/api/dashboards/${dashboardId}/widgets`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrf_token') || ''
        },
        body: JSON.stringify(widgetData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to create widget');
        }
        return response.json();
    })
    .then(data => {
        showNotification('Widget added successfully', 'success');
        
        // Refresh dashboard to show new widget
        refreshDashboard();
    })
    .catch(error => {
        console.error('Error creating widget:', error);
        showNotification('Failed to create widget', 'error');
    })
    .finally(() => {
        closeModal('add-widget-modal');
        
        // Reset form
        document.getElementById('widget-name').value = '';
        document.getElementById('widget-type').value = '';
        document.getElementById('widget-data-source').value = '';
        document.getElementById('widget-size').value = '2x2';
    });
}

/**
 * Update the available widget configuration options based on the widget type
 * @param {string} widgetType - Type of widget
 */
function updateWidgetConfigOptions(widgetType) {
    const configOptionsContainer = document.getElementById('widget-config-options');
    if (!configOptionsContainer) return;
    
    // Clear current options
    configOptionsContainer.innerHTML = '';
    
    // Add relevant configuration options based on widget type
    switch (widgetType) {
        case 'line-chart':
        case 'bar-chart':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-time-period">Time Period</label>
                    <select id="widget-time-period" class="form-control">
                        <option value="1h">Last Hour</option>
                        <option value="6h">Last 6 Hours</option>
                        <option value="24h" selected>Last 24 Hours</option>
                        <option value="7d">Last 7 Days</option>
                        <option value="30d">Last 30 Days</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="widget-aggregation">Aggregation</label>
                    <select id="widget-aggregation" class="form-control">
                        <option value="avg" selected>Average</option>
                        <option value="sum">Sum</option>
                        <option value="min">Minimum</option>
                        <option value="max">Maximum</option>
                        <option value="count">Count</option>
                    </select>
                </div>
            `;
            break;
            
        case 'pie-chart':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-category">Category</label>
                    <select id="widget-category" class="form-control">
                        <option value="severity" selected>Severity</option>
                        <option value="source">Source</option>
                        <option value="device">Device</option>
                    </select>
                </div>
            `;
            break;
            
        case 'gauge':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-metric">Metric</label>
                    <select id="widget-metric" class="form-control">
                        <option value="cpu" selected>CPU Usage</option>
                        <option value="memory">Memory Usage</option>
                        <option value="disk">Disk Usage</option>
                        <option value="network">Network Utilization</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="widget-min-value">Minimum Value</label>
                    <input type="number" id="widget-min-value" class="form-control" value="0">
                </div>
                <div class="form-group">
                    <label for="widget-max-value">Maximum Value</label>
                    <input type="number" id="widget-max-value" class="form-control" value="100">
                </div>
            `;
            break;
            
        case 'stat':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-stat-type">Stat Type</label>
                    <select id="widget-stat-type" class="form-control">
                        <option value="count" selected>Count</option>
                        <option value="latest">Latest Value</option>
                        <option value="average">Average</option>
                        <option value="sum">Sum</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="widget-comparison">Comparison Period</label>
                    <select id="widget-comparison" class="form-control">
                        <option value="1h">Previous Hour</option>
                        <option value="24h" selected>Previous Day</option>
                        <option value="7d">Previous Week</option>
                        <option value="30d">Previous Month</option>
                    </select>
                </div>
            `;
            break;
            
        case 'table':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-table-columns">Columns</label>
                    <textarea id="widget-table-columns" class="form-control" rows="3" placeholder="timestamp,severity,message"></textarea>
                    <small class="form-text text-muted">Comma-separated list of columns to display</small>
                </div>
                <div class="form-group">
                    <label for="widget-limit">Row Limit</label>
                    <input type="number" id="widget-limit" class="form-control" value="10">
                </div>
            `;
            break;
            
        case 'alert-list':
            configOptionsContainer.innerHTML = `
                <div class="form-group">
                    <label for="widget-alert-status">Alert Status</label>
                    <select id="widget-alert-status" class="form-control">
                        <option value="active" selected>Active</option>
                        <option value="all">All</option>
                        <option value="acknowledged">Acknowledged</option>
                        <option value="resolved">Resolved</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="widget-alert-limit">Limit</label>
                    <input type="number" id="widget-alert-limit" class="form-control" value="5">
                </div>
            `;
            break;
            
        default:
            // No specific options for unknown widget types
            break;
    }
}

/**
 * Update the available data source options based on the widget type
 * @param {string} widgetType - Type of widget
 */
function updateDataSourceOptions(widgetType) {
    const dataSourceSelect = document.getElementById('widget-data-source');
    if (!dataSourceSelect) return;
    
    // Clear current options
    dataSourceSelect.innerHTML = '<option value="">Select a data source</option>';
    
    // Add relevant data sources based on widget type
    switch (widgetType) {
        case 'line-chart':
        case 'bar-chart':
        case 'gauge':
        case 'stat':
            // These can use any data source
            dataSourceSelect.innerHTML += `
                <option value="SYSLOG">Syslog</option>
                <option value="SNMP">SNMP</option>
                <option value="NETFLOW">NetFlow</option>
                <option value="SFLOW">sFlow</option>
                <option value="WINDOWS_EVENTS">Windows Events</option>
                <option value="OTEL">OpenTelemetry</option>
            `;
            break;
            
        case 'pie-chart':
        case 'table':
            // These work better with log-based sources
            dataSourceSelect.innerHTML += `
                <option value="SYSLOG">Syslog</option>
                <option value="WINDOWS_EVENTS">Windows Events</option>
                <option value="SNMP">SNMP</option>
            `;
            break;
            
        case 'alert-list':
            // Only one source for alerts
            dataSourceSelect.innerHTML += `
                <option value="ALERTS" selected>Alerts</option>
            `;
            break;
            
        default:
            // Default set of data sources
            dataSourceSelect.innerHTML += `
                <option value="SYSLOG">Syslog</option>
                <option value="SNMP">SNMP</option>
            `;
            break;
    }
}

/**
 * Find the next available position for a new widget
 * @returns {Object} Position object with x and y coordinates
 */
function findNextWidgetPosition() {
    // Start with position (0, 0)
    let position = { x: 0, y: 0 };
    
    if (!dashboardWidgets || dashboardWidgets.length === 0) {
        return position;
    }
    
    // Find the widget with the highest y position
    const maxY = Math.max(...dashboardWidgets.map(w => (w.position_y || 0) + (w.height || 1)));
    
    // Place the new widget below all existing widgets
    position.y = maxY;
    
    return position;
}

/**
 * Get color for threshold based on name
 * @param {string} colorName - Color name
 * @returns {string} CSS color value
 */
function getColorForThreshold(colorName) {
    switch (colorName.toLowerCase()) {
        case 'red':
            return '#ff4136';
        case 'yellow':
            return '#ffdc00';
        case 'green':
            return '#2ecc40';
        case 'blue':
            return '#0074d9';
        case 'orange':
            return '#ff851b';
        default:
            return colorName;
    }
}

/**
 * Show notification message
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, info, warning, error)
 */
function showNotification(message, type) {
    const notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        // Create notification container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type || 'info'}`;
    
    // Add notification content
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas ${getIconForNotificationType(type)}"></i>
        </div>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">&times;</button>
    `;
    
    // Add event listener for close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.classList.add('notification-hiding');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    // Add to container
    document.getElementById('notification-container').appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 5000);
}

/**
 * Get icon class for notification type
 * @param {string} type - Notification type
 * @returns {string} FontAwesome icon class
 */
function getIconForNotificationType(type) {
    switch (type) {
        case 'success':
            return 'fa-check-circle';
        case 'warning':
            return 'fa-exclamation-triangle';
        case 'error':
            return 'fa-times-circle';
        case 'info':
        default:
            return 'fa-info-circle';
    }
}

/**
 * Show a modal
 * @param {string} modalId - ID of the modal to show
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

/**
 * Close a modal
 * @param {string} modalId - ID of the modal to close
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Get cookie value by name
 * @param {string} name - Name of the cookie
 * @returns {string} Cookie value
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

/**
 * Create sample dashboard data for development
 * @returns {Object} Sample dashboard data
 */
function createSampleDashboardData() {
    const now = new Date();
    const timePoints = [];
    const values1 = [];
    const values2 = [];
    
    // Generate time points and values for the last 24 hours
    for (let i = 0; i < 24; i++) {
        const time = new Date(now);
        time.setHours(now.getHours() - 24 + i);
        timePoints.push(time.getHours() + ':00');
        values1.push(Math.floor(Math.random() * 500) + 100);
        values2.push(Math.floor(Math.random() * 300) + 50);
    }
    
    return {
        dashboard_id: 1,
        widgets: [
            {
                id: 1,
                name: 'System Overview',
                type: 'stat',
                data_source: 'SYSLOG',
                position_x: 0,
                position_y: 0,
                width: 1,
                height: 1,
                configuration: JSON.stringify({}),
                data: {
                    stats: [
                        {
                            title: 'Total Logs',
                            value: 12345,
                            change: 15,
                            icon: 'fa-file-alt'
                        },
                        {
                            title: 'Errors',
                            value: 42,
                            change: -8,
                            icon: 'fa-exclamation-circle'
                        },
                        {
                            title: 'Warnings',
                            value: 156,
                            change: 12,
                            icon: 'fa-exclamation-triangle'
                        }
                    ]
                }
            },
            {
                id: 2,
                name: 'Recent Alerts',
                type: 'alert-list',
                data_source: 'SYSLOG',
                position_x: 1,
                position_y: 0,
                width: 2,
                height: 1,
                configuration: JSON.stringify({}),
                data: {
                    alerts: [
                        {
                            id: 1,
                            timestamp: new Date().toISOString(),
                            severity: 'WARNING',
                            message: 'High CPU utilization on Core Router',
                            acknowledged: false,
                            resolved: false
                        },
                        {
                            id: 2,
                            timestamp: new Date(now.getTime() - 30*60000).toISOString(),
                            severity: 'CRITICAL',
                            message: 'Web Server disk space critically low',
                            acknowledged: false,
                            resolved: false
                        },
                        {
                            id: 3,
                            timestamp: new Date(now.getTime() - 60*60000).toISOString(),
                            severity: 'ERROR',
                            message: 'Database server connection timeouts exceeding threshold',
                            acknowledged: false,
                            resolved: false
                        }
                    ]
                }
            },
            {
                id: 3,
                name: 'Log Volume',
                type: 'line-chart',
                data_source: 'SYSLOG',
                position_x: 0,
                position_y: 1,
                width: 2,
                height: 1,
                configuration: JSON.stringify({}),
                data: {
                    time_points: timePoints,
                    values: values1
                }
            },
            {
                id: 4,
                name: 'Error Distribution',
                type: 'pie-chart',
                data_source: 'SYSLOG',
                position_x: 2,
                position_y: 1,
                width: 1,
                height: 1,
                configuration: JSON.stringify({}),
                data: {
                    labels: ['Network', 'System', 'Application', 'Security'],
                    values: [42, 18, 27, 13]
                }
            }
        ],
        summary: {
            total_logs: 12345,
            total_metrics: 54321,
            active_alerts: 7,
            devices_count: 42
        },
        time_range: {
            start: new Date(now.getTime() - 24*60*60*1000).toISOString(),
            end: now.toISOString()
        }
    };
}

// Initialize the dashboard when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});