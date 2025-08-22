/**
 * AI Insights Visualization
 * Provides interactive visualizations for AI-powered flow data analysis
 */

document.addEventListener('DOMContentLoaded', function() {
    const deviceId = document.getElementById('device-id').value;
    const timePeriodSelect = document.getElementById('time-period');
    
    // Load initial data
    loadAIInsights(deviceId, timePeriodSelect.value);
    
    // Set up event listener for time period changes
    timePeriodSelect.addEventListener('change', function() {
        loadAIInsights(deviceId, this.value);
    });
});

/**
 * Load AI insights data for a device
 * @param {number} deviceId - The device ID
 * @param {string} timePeriod - Time period for analysis (hour, day, week, month)
 */
function loadAIInsights(deviceId, timePeriod) {
    showLoading();
    
    fetch(`/api/ai_insights/${deviceId}?period=${timePeriod}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            renderAIInsights(data);
        })
        .catch(error => {
            hideLoading();
            showError('Failed to load AI insights data. Please try again later.');
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Render AI insights visualizations
 * @param {Object} data - AI insights data from the API
 */
function renderAIInsights(data) {
    // Extract data
    const analysisResults = data.analysis_results;
    
    // Display analysis period
    const periodStart = new Date(data.analysis_period.start);
    const periodEnd = new Date(data.analysis_period.end);
    document.getElementById('analysis-period').textContent = 
        `${periodStart.toLocaleString()} - ${periodEnd.toLocaleString()}`;
    
    // Render anomalies
    renderAnomalies(analysisResults.anomalies);
    
    // Render traffic patterns
    renderTrafficPatterns(analysisResults.traffic_patterns);
    
    // Render behavior classification
    renderBehaviorClassification(analysisResults.behavior);
    
    // Render recommendations
    renderRecommendations(analysisResults.recommendations);
}

/**
 * Render anomalies section
 * @param {Array} anomalies - List of detected anomalies
 */
function renderAnomalies(anomalies) {
    const anomalyContainer = document.getElementById('anomaly-list');
    anomalyContainer.innerHTML = '';
    
    if (!anomalies || anomalies.length === 0) {
        anomalyContainer.innerHTML = '<div class="alert alert-success">No anomalies detected during this period.</div>';
        return;
    }
    
    // Sort anomalies by timestamp (newest first)
    anomalies.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Create anomaly cards
    anomalies.forEach(anomaly => {
        const severityClass = getSeverityClass(anomaly.severity);
        const confidencePercent = Math.round(anomaly.confidence * 100);
        
        const anomalyCard = document.createElement('div');
        anomalyCard.className = 'card mb-3';
        anomalyCard.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center ${severityClass}">
                <span>${anomaly.anomaly_type}</span>
                <span class="badge bg-light text-dark">${new Date(anomaly.timestamp).toLocaleString()}</span>
            </div>
            <div class="card-body">
                <h5 class="card-title">
                    ${anomaly.src_ip} → ${anomaly.dst_ip}
                    <small class="text-muted">(Protocol: ${getProtocolName(anomaly.protocol)})</small>
                </h5>
                <p class="card-text">${anomaly.description}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <span>Confidence: ${confidencePercent}%</span>
                    <button class="btn btn-sm btn-outline-primary" 
                        onclick="showAnomalyDetails(${JSON.stringify(anomaly).replace(/"/g, '&quot;')})">
                        View Details
                    </button>
                </div>
            </div>
        `;
        
        anomalyContainer.appendChild(anomalyCard);
    });
}

/**
 * Render traffic patterns section
 * @param {Object} patterns - Traffic pattern analysis
 */
function renderTrafficPatterns(patterns) {
    // Render time patterns chart
    if (patterns.time_patterns) {
        renderTimePatternChart(patterns.time_patterns);
    }
    
    // Render protocol distribution chart
    if (patterns.protocol_distribution) {
        renderProtocolDistributionChart(patterns.protocol_distribution);
    }
    
    // Render communication patterns
    if (patterns.communication_patterns && patterns.communication_patterns.top_pairs) {
        renderCommunicationPatterns(patterns.communication_patterns.top_pairs);
    }
}

/**
 * Render time pattern chart
 * @param {Object} timePatterns - Time pattern data
 */
function renderTimePatternChart(timePatterns) {
    const ctx = document.getElementById('time-pattern-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.timePatternChart) {
        window.timePatternChart.destroy();
    }
    
    // Create chart
    window.timePatternChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timePatterns.hours.map(hour => `${hour}:00`),
            datasets: [{
                label: 'Traffic Volume',
                data: timePatterns.values,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                tension: 0.4
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
                        text: 'Hour of Day'
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                },
                legend: {
                    display: true,
                    position: 'top',
                }
            }
        }
    });
}

/**
 * Render protocol distribution chart
 * @param {Object} protocolDist - Protocol distribution data
 */
function renderProtocolDistributionChart(protocolDist) {
    const ctx = document.getElementById('protocol-distribution-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.protocolDistChart) {
        window.protocolDistChart.destroy();
    }
    
    // Prepare data for chart
    const labels = Object.keys(protocolDist);
    const data = Object.values(protocolDist);
    
    // Chart colors
    const backgroundColors = [
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)'
    ];
    
    // Create chart
    window.protocolDistChart = new Chart(ctx, {
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
                            return `${label}: ${percentage}% (${value})`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render communication patterns
 * @param {Array} topPairs - Top communication pairs
 */
function renderCommunicationPatterns(topPairs) {
    const pairsContainer = document.getElementById('communication-patterns');
    pairsContainer.innerHTML = '';
    
    if (!topPairs || topPairs.length === 0) {
        pairsContainer.innerHTML = '<div class="alert alert-info">No significant communication patterns detected.</div>';
        return;
    }
    
    // Create table for top pairs
    const table = document.createElement('table');
    table.className = 'table table-hover';
    
    // Create table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Source IP</th>
            <th>Destination IP</th>
            <th>Protocol</th>
            <th>Ports</th>
            <th>Flow Count</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    topPairs.forEach(pair => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${pair.src_ip}</td>
            <td>${pair.dst_ip}</td>
            <td>${pair.protocol}</td>
            <td>${pair.ports}</td>
            <td>${pair.flow_count}</td>
        `;
        tbody.appendChild(row);
    });
    table.appendChild(tbody);
    
    pairsContainer.appendChild(table);
}

/**
 * Render behavior classification
 * @param {Object} behavior - Behavior classification data
 */
function renderBehaviorClassification(behavior) {
    if (!behavior) {
        return;
    }
    
    // Set behavior classification
    document.getElementById('behavior-classification').textContent = behavior.classification;
    document.getElementById('behavior-description').textContent = behavior.description;
    
    // Render behavior patterns
    if (behavior.patterns) {
        renderBehaviorPatterns(behavior.patterns);
    }
}

/**
 * Render behavior patterns
 * @param {Object} patterns - Behavior patterns data
 */
function renderBehaviorPatterns(patterns) {
    const patternsContainer = document.getElementById('behavior-patterns');
    patternsContainer.innerHTML = '';
    
    // Create progress bars for each pattern
    Object.entries(patterns).forEach(([pattern, value]) => {
        const patternName = formatPatternName(pattern);
        const percentage = Math.round(value * 100);
        
        const progressBarContainer = document.createElement('div');
        progressBarContainer.className = 'mb-3';
        
        progressBarContainer.innerHTML = `
            <div class="d-flex justify-content-between mb-1">
                <span>${patternName}</span>
                <span>${percentage}%</span>
            </div>
            <div class="progress">
                <div class="progress-bar" role="progressbar" 
                     style="width: ${percentage}%" 
                     aria-valuenow="${percentage}" 
                     aria-valuemin="0" 
                     aria-valuemax="100"></div>
            </div>
        `;
        
        patternsContainer.appendChild(progressBarContainer);
    });
}

/**
 * Render recommendations
 * @param {Array} recommendations - List of recommendations
 */
function renderRecommendations(recommendations) {
    const recommendationsContainer = document.getElementById('recommendations-list');
    recommendationsContainer.innerHTML = '';
    
    if (!recommendations || recommendations.length === 0) {
        recommendationsContainer.innerHTML = '<div class="alert alert-info">No recommendations available for this device.</div>';
        return;
    }
    
    // Create list of recommendations
    const list = document.createElement('ul');
    list.className = 'list-group';
    
    recommendations.forEach(recommendation => {
        const item = document.createElement('li');
        item.className = 'list-group-item';
        item.innerHTML = `
            <i class="fas fa-lightbulb text-warning me-2"></i>
            ${recommendation}
        `;
        list.appendChild(item);
    });
    
    recommendationsContainer.appendChild(list);
}

/**
 * Show anomaly details in a modal
 * @param {Object} anomaly - Anomaly data
 */
function showAnomalyDetails(anomaly) {
    const modal = new bootstrap.Modal(document.getElementById('anomaly-details-modal'));
    
    // Set modal content
    document.getElementById('modal-anomaly-type').textContent = anomaly.anomaly_type;
    document.getElementById('modal-anomaly-time').textContent = new Date(anomaly.timestamp).toLocaleString();
    document.getElementById('modal-anomaly-description').textContent = anomaly.description;
    document.getElementById('modal-anomaly-severity').textContent = anomaly.severity;
    document.getElementById('modal-anomaly-confidence').textContent = `${Math.round(anomaly.confidence * 100)}%`;
    
    // Format traffic details
    document.getElementById('modal-anomaly-src').textContent = anomaly.src_ip;
    document.getElementById('modal-anomaly-dst').textContent = anomaly.dst_ip;
    document.getElementById('modal-anomaly-protocol').textContent = getProtocolName(anomaly.protocol);
    
    // Show the modal
    modal.show();
}

/**
 * Get CSS class for severity level
 * @param {string} severity - Severity level (low, medium, high)
 * @return {string} CSS class
 */
function getSeverityClass(severity) {
    switch (severity.toLowerCase()) {
        case 'high':
            return 'bg-danger text-white';
        case 'medium':
            return 'bg-warning text-dark';
        case 'low':
            return 'bg-info text-dark';
        default:
            return 'bg-light text-dark';
    }
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
 * Format pattern name for display
 * @param {string} pattern - Pattern key
 * @return {string} Formatted pattern name
 */
function formatPatternName(pattern) {
    // Convert snake_case to Title Case
    return pattern
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
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
