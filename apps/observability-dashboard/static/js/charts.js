/**
 * Charts Utility Library
 * Provides functions for creating and updating charts in the dashboard
 */

// Chart color schemes for different themes
const chartColorSchemes = {
    dark: {
        primary: '#03dac6',
        secondary: '#2196f3',
        success: '#4caf50',
        warning: '#ff9800',
        error: '#cf6679',
        background: 'rgba(255, 255, 255, 0.05)',
        line: '#03dac6',
        area: 'rgba(3, 218, 198, 0.1)',
        grid: '#333333',
        text: '#a0a0a0'
    },
    dark_red: {
        primary: '#c50000',
        secondary: '#2196f3',
        success: '#4caf50',
        warning: '#ff9800',
        error: '#cf6679',
        background: 'rgba(255, 255, 255, 0.05)',
        line: '#c50000',
        area: 'rgba(197, 0, 0, 0.1)',
        grid: '#333333',
        text: '#a0a0a0'
    },
    light: {
        primary: '#018786',
        secondary: '#1976d2',
        success: '#388e3c',
        warning: '#f57c00',
        error: '#d32f2f',
        background: 'rgba(0, 0, 0, 0.05)',
        line: '#018786',
        area: 'rgba(1, 135, 134, 0.1)',
        grid: '#e0e0e0',
        text: '#616161'
    },
    custom: {
        // This will be dynamically handled in getChartColors()
        primary: '#03dac6',
        secondary: '#2196f3',
        success: '#4caf50',
        warning: '#ff9800',
        error: '#cf6679',
        background: 'rgba(255, 255, 255, 0.05)',
        line: '#03dac6',
        area: 'rgba(3, 218, 198, 0.1)',
        grid: '#333333',
        text: '#a0a0a0'
    }
};

/**
 * Get current theme colors for charts
 * @returns {Object} Color scheme object with color values for different chart elements
 */
function getChartColors() {
    try {
        const theme = document.documentElement.getAttribute('data-theme') || 'dark_red';
        
        // Check if window.themeSystem is available to get more precise theme information
        if (window.themeSystem && typeof window.themeSystem.getCurrentTheme === 'function') {
            const currentTheme = window.themeSystem.getCurrentTheme();
            
            // For custom themes, we need to create a color scheme based on the accent color
            if (theme === 'custom' && currentTheme) {
                console.log("Using custom theme colors for charts");
                
                // Generate colors based on accent color
                const customColors = {
                    primary: currentTheme.accentColor || '#03dac6',
                    secondary: adjustColorBrightness(currentTheme.accentColor, -20) || '#2196f3',
                    success: '#4caf50',
                    warning: '#ff9800',
                    error: '#cf6679',
                    background: theme.includes('dark') 
                        ? 'rgba(255, 255, 255, 0.05)' 
                        : 'rgba(0, 0, 0, 0.05)',
                    line: currentTheme.accentColor || '#03dac6',
                    area: adjustColorOpacity(currentTheme.accentColor, 0.1) || 'rgba(3, 218, 198, 0.1)',
                    grid: theme.includes('dark') ? '#333333' : '#e0e0e0',
                    text: theme.includes('dark') ? '#a0a0a0' : '#616161',
                    tooltipBg: theme.includes('dark') ? '#303030' : '#ffffff',
                    tooltipText: theme.includes('dark') ? '#ffffff' : '#000000',
                    tooltipBorder: theme.includes('dark') ? '#424242' : '#e0e0e0',
                    // Additional palette for multiple datasets
                    colorPalette: [
                        currentTheme.accentColor || '#03dac6',
                        adjustColorBrightness(currentTheme.accentColor, -20) || '#2196f3',
                        '#4caf50', 
                        '#ff9800', 
                        '#cf6679'
                    ]
                };
                
                return customColors;
            }
        }
        
        // Regular theme handling for pre-defined themes
        let colorScheme;
        if (chartColorSchemes[theme]) {
            // Use exact match if available
            colorScheme = { ...chartColorSchemes[theme] };
        } else if (theme === 'dark_red') {
            colorScheme = { ...chartColorSchemes['dark_red'] };
        } else if (theme.includes('dark')) {
            // For any other dark themes, use dark theme colors
            colorScheme = { ...chartColorSchemes['dark'] };
        } else {
            // For any other light themes or fallback
            colorScheme = { ...chartColorSchemes['light'] };
        }
        
        // Add additional properties that might not be in the base schemes
        colorScheme.tooltipBg = theme.includes('dark') ? '#303030' : '#ffffff';
        colorScheme.tooltipText = theme.includes('dark') ? '#ffffff' : '#000000';
        colorScheme.tooltipBorder = theme.includes('dark') ? '#424242' : '#e0e0e0';
        colorScheme.colorPalette = [
            colorScheme.primary, 
            colorScheme.secondary, 
            colorScheme.success, 
            colorScheme.warning, 
            colorScheme.error
        ];
        
        return colorScheme;
    } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        // Fallback to dark_red scheme
        return {
            ...chartColorSchemes['dark_red'],
            tooltipBg: '#303030',
            tooltipText: '#ffffff',
            tooltipBorder: '#424242',
            colorPalette: ['#c50000', '#2196f3', '#4caf50', '#ff9800', '#cf6679']
        };
    }
}

/**
 * Adjust color brightness
 * @param {string} color - HEX color
 * @param {number} percent - Percentage to adjust (-100 to 100)
 * @returns {string} Adjusted HEX color
 */
function adjustColorBrightness(color, percent) {
    if (!color) return null;
    
    try {
        // Convert HEX to RGB
        let R = parseInt(color.substring(1, 3), 16);
        let G = parseInt(color.substring(3, 5), 16);
        let B = parseInt(color.substring(5, 7), 16);

        // Adjust brightness
        R = Math.max(0, Math.min(255, R + (R * percent / 100)));
        G = Math.max(0, Math.min(255, G + (G * percent / 100)));
        B = Math.max(0, Math.min(255, B + (B * percent / 100)));

        // Convert back to HEX
        const RR = ((R.toString(16).length === 1) ? "0" + R.toString(16) : R.toString(16));
        const GG = ((G.toString(16).length === 1) ? "0" + G.toString(16) : G.toString(16));
        const BB = ((B.toString(16).length === 1) ? "0" + B.toString(16) : B.toString(16));

        return "#" + RR + GG + BB;
    } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return color;
    }
}

/**
 * Adjust color opacity
 * @param {string} color - HEX color
 * @param {number} opacity - Opacity value (0 to 1)
 * @returns {string} RGBA color string
 */
function adjustColorOpacity(color, opacity) {
    if (!color) return null;
    
    try {
        // Convert HEX to RGB
        const R = parseInt(color.substring(1, 3), 16);
        const G = parseInt(color.substring(3, 5), 16);
        const B = parseInt(color.substring(5, 7), 16);

        return `rgba(${R}, ${G}, ${B}, ${opacity})`;
    } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return color;
    }
}

/**
 * Create a line chart
 * @param {string} elementId - ID of the canvas element
 * @param {Object} data - Chart data
 * @param {Object} options - Chart options
 * @returns {Object} Chart.js chart instance
 */
function createLineChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return null;
    }
    
    const colors = getChartColors();
    
    // Process dataset colors if not specified
    if (data.datasets) {
        data.datasets.forEach((dataset, index) => {
            if (!dataset.borderColor) {
                const colorKeys = ['primary', 'secondary', 'success', 'warning', 'error'];
                dataset.borderColor = colors[colorKeys[index % colorKeys.length]];
            }
            
            if (!dataset.backgroundColor && dataset.fill) {
                dataset.backgroundColor = colors.area;
            }
        });
    }
    
    // Default options for line charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: colors.text
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            x: {
                grid: {
                    color: colors.grid
                },
                ticks: {
                    color: colors.text
                }
            },
            y: {
                grid: {
                    color: colors.grid
                },
                ticks: {
                    color: colors.text
                }
            }
        }
    };
    
    // Merge options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: chartOptions
    });
}

/**
 * Create a bar chart
 * @param {string} elementId - ID of the canvas element
 * @param {Object} data - Chart data
 * @param {Object} options - Chart options
 * @returns {Object} Chart.js chart instance
 */
function createBarChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return null;
    }
    
    const colors = getChartColors();
    
    // Process dataset colors if not specified
    if (data.datasets) {
        data.datasets.forEach((dataset, index) => {
            if (!dataset.backgroundColor) {
                const colorKeys = ['primary', 'secondary', 'success', 'warning', 'error'];
                dataset.backgroundColor = colors[colorKeys[index % colorKeys.length]];
            }
        });
    }
    
    // Default options for bar charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: colors.text
                }
            }
        },
        scales: {
            x: {
                grid: {
                    color: colors.grid
                },
                ticks: {
                    color: colors.text
                }
            },
            y: {
                grid: {
                    color: colors.grid
                },
                ticks: {
                    color: colors.text
                }
            }
        }
    };
    
    // Merge options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: chartOptions
    });
}

/**
 * Create a pie chart
 * @param {string} elementId - ID of the canvas element
 * @param {Object} data - Chart data
 * @param {Object} options - Chart options
 * @returns {Object} Chart.js chart instance
 */
function createPieChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return null;
    }
    
    const colors = getChartColors();
    
    // Set default colors if not specified
    if (data.datasets && data.datasets.length > 0) {
        if (!data.datasets[0].backgroundColor) {
            data.datasets[0].backgroundColor = [
                colors.primary,
                colors.secondary,
                colors.success,
                colors.warning,
                colors.error
            ];
        }
    }
    
    // Default options for pie charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    color: colors.text
                }
            }
        }
    };
    
    // Merge options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    return new Chart(ctx, {
        type: 'pie',
        data: data,
        options: chartOptions
    });
}

/**
 * Create a doughnut chart
 * @param {string} elementId - ID of the canvas element
 * @param {Object} data - Chart data
 * @param {Object} options - Chart options
 * @returns {Object} Chart.js chart instance
 */
function createDoughnutChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return null;
    }
    
    const colors = getChartColors();
    
    // Set default colors if not specified
    if (data.datasets && data.datasets.length > 0) {
        if (!data.datasets[0].backgroundColor) {
            data.datasets[0].backgroundColor = [
                colors.primary,
                colors.secondary,
                colors.success,
                colors.warning,
                colors.error
            ];
        }
    }
    
    // Default options for doughnut charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    color: colors.text
                }
            }
        },
        cutout: '70%'
    };
    
    // Merge options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: chartOptions
    });
}

/**
 * Create a gauge chart (based on doughnut chart)
 * @param {string} elementId - ID of the canvas element
 * @param {number} value - Current gauge value (0-100)
 * @param {string} label - Gauge label
 * @param {Object} options - Chart options
 * @returns {Object} Chart.js chart instance
 */
function createGaugeChart(elementId, value, label, options = {}) {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return null;
    }
    
    const colors = getChartColors();
    
    // Get color based on value
    let gaugeColor = colors.error;
    if (value >= 70) gaugeColor = colors.success;
    else if (value >= 30) gaugeColor = colors.warning;
    
    // Create the gauge chart data
    const data = {
        datasets: [{
            label: label,
            data: [value, 100 - value],
            backgroundColor: [
                gaugeColor,
                colors.background
            ],
            circumference: 180,
            rotation: 270,
            cutout: '70%'
        }]
    };
    
    // Create gauge chart text plugin
    const gaugeChartText = {
        id: 'gaugeChartText',
        afterDatasetsDraw(chart) {
            const { ctx, data, chartArea: { top, bottom, left, right, width, height } } = chart;
            
            ctx.save();
            const xCenter = chart.getDatasetMeta(0).data[0].x;
            const yCenter = chart.getDatasetMeta(0).data[0].y;
            const score = data.datasets[0].data[0];
            
            // Draw value text
            ctx.font = 'bold 24px Arial';
            ctx.fillStyle = colors.text;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${score}%`, xCenter, yCenter);
            
            // Draw label text
            ctx.font = '14px Arial';
            ctx.fillStyle = colors.text;
            ctx.fillText(label, xCenter, yCenter + 30);
            
            ctx.restore();
        }
    };
    
    // Default options for gauge charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                enabled: false
            }
        }
    };
    
    // Merge options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: chartOptions,
        plugins: [gaugeChartText]
    });
}

/**
 * Create a heat map (based on a matrix of colored cells)
 * @param {string} containerId - ID of the container element
 * @param {Array} data - 2D array of data values
 * @param {Array} xLabels - X-axis labels
 * @param {Array} yLabels - Y-axis labels
 * @param {Object} options - Heatmap options
 */
function createHeatmap(containerId, data, xLabels, yLabels, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return;
    }
    
    const colors = getChartColors();
    
    // Default options
    const defaultOptions = {
        cellSize: 30,
        colorScale: [
            '#313695',
            '#4575b4',
            '#74add1',
            '#abd9e9',
            '#e0f3f8',
            '#fee090',
            '#fdae61',
            '#f46d43',
            '#d73027',
            '#a50026'
        ],
        minValue: Math.min(...data.flat()),
        maxValue: Math.max(...data.flat())
    };
    
    // Merge options
    const heatmapOptions = Object.assign({}, defaultOptions, options);
    
    // Clear container
    container.innerHTML = '';
    
    // Find min and max values
    const minValue = heatmapOptions.minValue;
    const maxValue = heatmapOptions.maxValue;
    const valueRange = maxValue - minValue;
    
    // Create table
    const table = document.createElement('table');
    table.className = 'heatmap-table';
    
    // Create header row
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    // Empty corner cell
    const cornerCell = document.createElement('th');
    headerRow.appendChild(cornerCell);
    
    // Add X labels
    xLabels.forEach(label => {
        const th = document.createElement('th');
        th.textContent = label;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create body rows
    const tbody = document.createElement('tbody');
    
    data.forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        
        // Add Y label
        const th = document.createElement('th');
        th.textContent = yLabels[rowIndex];
        tr.appendChild(th);
        
        // Add data cells
        row.forEach((value, colIndex) => {
            const td = document.createElement('td');
            
            // Calculate color based on value
            const normalizedValue = valueRange === 0 ? 0 : (value - minValue) / valueRange;
            const colorIndex = Math.floor(normalizedValue * (heatmapOptions.colorScale.length - 1));
            const color = heatmapOptions.colorScale[colorIndex];
            
            td.style.backgroundColor = color;
            td.style.width = `${heatmapOptions.cellSize}px`;
            td.style.height = `${heatmapOptions.cellSize}px`;
            td.setAttribute('title', `${value}`);
            
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
    
    // Apply styles
    const style = document.createElement('style');
    style.textContent = `
        .heatmap-table {
            border-collapse: collapse;
            margin: 0 auto;
        }
        
        .heatmap-table th {
            padding: 5px;
            text-align: center;
            color: ${colors.text};
        }
        
        .heatmap-table td {
            padding: 0;
            border: 1px solid ${colors.background};
        }
    `;
    
    container.appendChild(style);
}

/**
 * Create a time series heatmap (e.g., for activity by hour and day)
 * @param {string} containerId - ID of the container element
 * @param {Array} data - Array of {x, y, value} objects
 * @param {Array} xLabels - X-axis labels
 * @param {Array} yLabels - Y-axis labels
 * @param {Object} options - Heatmap options
 */
function createTimeSeriesHeatmap(containerId, data, xLabels, yLabels, options = {}) {
    // Convert data array to 2D matrix
    const matrix = Array(yLabels.length).fill().map(() => Array(xLabels.length).fill(0));
    
    data.forEach(point => {
        const xIndex = xLabels.indexOf(point.x);
        const yIndex = yLabels.indexOf(point.y);
        
        if (xIndex >= 0 && yIndex >= 0) {
            matrix[yIndex][xIndex] = point.value;
        }
    });
    
    // Create regular heatmap
    createHeatmap(containerId, matrix, xLabels, yLabels, options);
}

/**
 * Create a network graph visualization
 * @param {string} containerId - ID of the container element
 * @param {Array} nodes - Array of node objects {id, label, ...}
 * @param {Array} edges - Array of edge objects {from, to, ...}
 * @param {Object} options - Graph options
 */
function createNetworkGraph(containerId, nodes, edges, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return;
    }
    
    const colors = getChartColors();
    
    // Default options
    const defaultOptions = {
        nodes: {
            shape: 'dot',
            size: 16,
            font: {
                color: colors.text
            },
            borderWidth: 2,
            color: {
                background: colors.primary,
                border: colors.secondary,
                highlight: {
                    background: colors.secondary,
                    border: colors.primary
                }
            }
        },
        edges: {
            width: 2,
            color: {
                color: colors.primary,
                highlight: colors.secondary
            },
            arrows: 'to'
        },
        physics: {
            enabled: true,
            stabilization: {
                iterations: 100
            },
            barnesHut: {
                gravitationalConstant: -5000,
                centralGravity: 0.3,
                springLength: 150,
                springConstant: 0.04,
                damping: 0.09
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 300,
            zoomView: true
        }
    };
    
    // Merge options
    const graphOptions = Object.assign({}, defaultOptions, options);
    
    // Create a network
    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };
    
    return new vis.Network(container, data, graphOptions);
}

/**
 * Update chart colors when theme changes
 * @param {Array} charts - Array of Chart.js instances
 */
function updateChartsForTheme(charts) {
    try {
        // If no valid charts array, exit
        if (!charts || !charts.length) {
            console.log("No charts provided to update");
            return;
        }

        console.log(`Updating ${charts.length} charts for theme change`);
        
        const colors = getChartColors();
        
        charts.forEach((chart, chartIndex) => {
            try {
                if (!chart || !chart.options) {
                    console.log(`Chart ${chartIndex} invalid or has no options, skipping`);
                    return;
                }
                
                // Update grid colors
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        // Safety check for missing properties
                        if (!chart.options.scales.x.grid) chart.options.scales.x.grid = {};
                        if (!chart.options.scales.x.ticks) chart.options.scales.x.ticks = {};
                        
                        chart.options.scales.x.grid.color = colors.grid;
                        chart.options.scales.x.ticks.color = colors.text;
                    }
                    
                    if (chart.options.scales.y) {
                        // Safety check for missing properties
                        if (!chart.options.scales.y.grid) chart.options.scales.y.grid = {};
                        if (!chart.options.scales.y.ticks) chart.options.scales.y.ticks = {};
                        
                        chart.options.scales.y.grid.color = colors.grid;
                        chart.options.scales.y.ticks.color = colors.text;
                    }
                    
                    // Handle additional scales or non-standard scale names
                    Object.keys(chart.options.scales).forEach(scaleKey => {
                        if (scaleKey !== 'x' && scaleKey !== 'y') {
                            const scale = chart.options.scales[scaleKey];
                            if (scale) {
                                if (scale.grid) {
                                    scale.grid.color = colors.grid;
                                }
                                if (scale.ticks) {
                                    scale.ticks.color = colors.text;
                                }
                            }
                        }
                    });
                }
                
                // Update legend colors
                if (chart.options.plugins && chart.options.plugins.legend) {
                    if (!chart.options.plugins.legend.labels) {
                        chart.options.plugins.legend.labels = {};
                    }
                    chart.options.plugins.legend.labels.color = colors.text;
                }
                
                // Update dataset colors based on chart type
                if (chart.data && chart.data.datasets) {
                    chart.data.datasets.forEach((dataset, index) => {
                        const colorKeys = ['primary', 'secondary', 'success', 'warning', 'error'];
                        
                        // Log if any dataset has preserved colors for debugging
                        if (dataset._preserveColor) {
                            console.log(`Chart ${chartIndex}: Dataset ${index} has preserved colors`);
                        }
                        
                        // Handle different chart types differently
                        if (chart.config && chart.config.type) {
                            // Line charts
                            if (chart.config.type === 'line') {
                                // Only update colors if they were not explicitly set
                                if (!dataset._preserveColor) {
                                    dataset.borderColor = colors[colorKeys[index % colorKeys.length]];
                                    if (dataset.fill) {
                                        dataset.backgroundColor = colors.area;
                                    }
                                }
                            }
                            // Bar charts
                            else if (chart.config.type === 'bar') {
                                if (!dataset._preserveColor) {
                                    dataset.backgroundColor = colors[colorKeys[index % colorKeys.length]];
                                }
                            }
                            // Pie/Doughnut charts
                            else if (chart.config.type === 'pie' || chart.config.type === 'doughnut') {
                                if (!dataset._preserveColor && Array.isArray(dataset.backgroundColor)) {
                                    dataset.backgroundColor = colorKeys.map(key => colors[key]);
                                }
                            }
                        }
                    });
                }
                
                // Special handling for gauge charts (modified doughnut charts)
                if (chart.config && chart.config.type === 'doughnut' && 
                    chart.data.datasets.length === 1 && 
                    chart.data.datasets[0].data.length === 2) {
                    
                    const value = chart.data.datasets[0].data[0];
                    let gaugeColor = colors.error;
                    
                    if (value >= 70) gaugeColor = colors.success;
                    else if (value >= 30) gaugeColor = colors.warning;
                    
                    // Only update if not explicitly preserved
                    if (!chart.data.datasets[0]._preserveColor) {
                        chart.data.datasets[0].backgroundColor = [
                            gaugeColor,
                            colors.background
                        ];
                    }
                }
                
                // Update chart
                chart.update();
            } catch (chartError) {
                errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
                // Continue with other charts
            }
        });
        
        console.log("Charts updated for theme");
    } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
    }
}

/**
 * Apply theme to all charts
 */
function applyThemeToCharts() {
    try {
        const colors = getChartColors();
        
        console.log("Applying theme to all charts");
        
        // Update global chart defaults for theme
        if (typeof Chart !== 'undefined' && Chart.defaults) {
            Chart.defaults.color = colors.text;
            Chart.defaults.borderColor = colors.grid;
            
            // Find all chart instances
            const charts = Object.values(Chart.instances || {});
            
            if (charts.length > 0) {
                console.log(`Found ${charts.length} chart instances to update`);
                updateChartsForTheme(charts);
            } else {
                console.log("No chart instances found to update");
            }
        } else {
            console.log("Chart library not available yet");
        }
    } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
    }
}

// Add event listener for theme changes
document.addEventListener('themeChanged', (event) => {
    console.log(`Theme changed event received: ${event.detail?.theme || 'unknown'}`);
    setTimeout(() => {
        // Run after a small delay to ensure DOM is updated
        applyThemeToCharts();
    }, 10);
});

// Also expose the function globally for direct access
window.updateChartsForTheme = function() {
    applyThemeToCharts();
};

// Export chart functions for use in other modules
window.chartUtils = {
    createLineChart,
    createBarChart,
    createPieChart,
    createDoughnutChart,
    createGaugeChart,
    createHeatmap,
    createTimeSeriesHeatmap,
    createNetworkGraph,
    applyThemeToCharts,
    updateChartsForTheme, // Additional export for theme system
    getChartColors,
    // Utility for preserving custom colors in charts
    preserveDatasetColors: function(chart) {
        if (chart && chart.data && chart.data.datasets) {
            chart.data.datasets.forEach(dataset => {
                dataset._preserveColor = true;
            });
            return true;
        }
        return false;
    }
};
