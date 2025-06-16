// Flow rate chart
let flowRateChart = null;

function initializeFlowRateChart() {
    const ctx = document.getElementById('flow-rate-chart')?.getContext('2d');
    if (!ctx) return;
    
    // Initialize with empty data - using dark red colors for Tritanopia
    flowRateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'NetFlow',
                    data: [],
                    borderColor: 'rgba(179, 0, 0, 1)', // Dark red
                    backgroundColor: 'rgba(179, 0, 0, 0.3)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'sFlow',
                    data: [],
                    borderColor: 'rgba(128, 0, 0, 1)', // Darker red
                    backgroundColor: 'rgba(128, 0, 0, 0.3)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Flow Traffic Rate',
                    color: '#e0e0e0'
                },
                legend: {
                    labels: {
                        color: '#e0e0e0'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                }
            }
        }
    });
}

function updateFlowRateChart(data) {
    if (!flowRateChart) return;
    
    flowRateChart.data.labels = data.labels || [];
    flowRateChart.data.datasets[0].data = data.netflow || [];
    flowRateChart.data.datasets[1].data = data.sflow || [];
    flowRateChart.update();
}

// Protocol distribution chart
let protocolChart = null;

function initializeProtocolDistributionChart() {
    const ctx = document.getElementById('protocol-chart')?.getContext('2d');
    if (!ctx) return;
    
    // Initialize with empty data - using dark red variations for Tritanopia
    protocolChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(139, 0, 0, 0.8)',     // Dark red
                    'rgba(179, 0, 0, 0.8)',     // Medium dark red
                    'rgba(220, 20, 60, 0.8)',   // Crimson
                    'rgba(165, 42, 42, 0.8)',   // Brown
                    'rgba(128, 0, 0, 0.8)',     // Maroon
                    'rgba(178, 34, 34, 0.8)',   // Firebrick
                    'rgba(205, 92, 92, 0.8)'    // Indian Red
                ],
                borderColor: 'rgba(30, 30, 30, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Protocol Distribution',
                    color: '#e0e0e0'
                },
                legend: {
                    position: 'right',
                    labels: {
                        color: '#e0e0e0'
                    }
                }
            }
        }
    });
}

function updateProtocolDistributionChart(protocolData) {
    if (!protocolChart) return;
    
    // Convert protocol data to arrays
    const protocolLabels = [];
    const protocolCounts = [];
    const protocolColors = [
        'rgba(139, 0, 0, 0.8)',     // Dark red
        'rgba(179, 0, 0, 0.8)',     // Medium dark red
        'rgba(220, 20, 60, 0.8)',   // Crimson
        'rgba(165, 42, 42, 0.8)',   // Brown
        'rgba(128, 0, 0, 0.8)',     // Maroon
        'rgba(178, 34, 34, 0.8)',   // Firebrick
        'rgba(205, 92, 92, 0.8)'    // Indian Red
    ];
    
    // Map protocol numbers to names
    const protocolNames = {
        1: 'ICMP',
        6: 'TCP',
        17: 'UDP',
        47: 'GRE',
        50: 'ESP',
        51: 'AH'
    };
    
    // Process protocol data
    Object.entries(protocolData).forEach(([protocol, count], index) => {
        const protocolName = protocolNames[protocol] || `Protocol ${protocol}`;
        protocolLabels.push(protocolName);
        protocolCounts.push(count);
    });
    
    // Update chart
    protocolChart.data.labels = protocolLabels;
    protocolChart.data.datasets[0].data = protocolCounts;
    protocolChart.update();
}

// Top talkers chart
let topTalkersChart = null;

function initializeTopTalkersChart() {
    const ctx = document.getElementById('top-talkers-chart')?.getContext('2d');
    if (!ctx) return;
    
    // Initialize with empty data
    topTalkersChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Flow Count',
                data: [],
                backgroundColor: 'rgba(139, 0, 0, 0.8)', // Dark red
                borderColor: 'rgba(139, 0, 0, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Top Talkers',
                    color: '#e0e0e0'
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                },
                y: {
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                }
            }
        }
    });
}

function updateTopTalkersChart(talkerData) {
    if (!topTalkersChart) return;
    
    // Convert talker data to arrays
    const ips = [];
    const counts = [];
    
    // Process talker data
    Object.entries(talkerData)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .forEach(([ip, count]) => {
            ips.push(ip);
            counts.push(count);
        });
    
    // Update chart
    topTalkersChart.data.labels = ips;
    topTalkersChart.data.datasets[0].data = counts;
    topTalkersChart.update();
}

// Time series chart for analyzer
let timeSeriesChart = null;

function initializeTimeSeriesChart(elementId = 'time-series-chart') {
    const ctx = document.getElementById(elementId)?.getContext('2d');
    if (!ctx) return;
    
    // Initialize with empty data
    timeSeriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Bytes',
                data: [],
                borderColor: 'rgba(139, 0, 0, 1)', // Dark red
                backgroundColor: 'rgba(139, 0, 0, 0.3)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Traffic Over Time',
                    color: '#e0e0e0'
                },
                legend: {
                    labels: {
                        color: '#e0e0e0'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: 'rgba(70, 70, 70, 0.3)'
                    }
                }
            }
        }
    });
    
    return timeSeriesChart;
}

function updateTimeSeriesChart(chart, data, label = 'Bytes') {
    if (!chart) return;
    
    chart.data.labels = data.labels || [];
    chart.data.datasets[0].data = data.data || [];
    chart.data.datasets[0].label = label;
    chart.options.plugins.title.text = `${label} Over Time`;
    chart.update();
}
