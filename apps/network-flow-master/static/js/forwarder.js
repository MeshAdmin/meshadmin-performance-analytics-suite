document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    initializeFormValidation();
    
    // Set up event listeners for form fields
    setupFormEvents();
    
    // Add event listeners to toggle buttons
    setupToggleButtons();
    
    // Load forwarder statistics
    loadForwarderStats();
    
    // Set up periodic refresh of statistics
    setInterval(loadForwarderStats, 10000);
});

function initializeFormValidation() {
    // Get the forward target form
    const form = document.getElementById('forward-target-form');
    if (!form) return;
    
    // Add form submission handler
    form.addEventListener('submit', function(event) {
        if (!this.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        this.classList.add('was-validated');
    });
}

function setupFormEvents() {
    // Flow type selector
    const flowTypeSelect = document.getElementById('flow-type');
    if (flowTypeSelect) {
        flowTypeSelect.addEventListener('change', updateVersionOptions);
    }
    
    // Protocol selector
    const protocolSelect = document.getElementById('protocol');
    if (protocolSelect) {
        protocolSelect.addEventListener('change', function() {
            // Could add special handling for different protocols if needed
        });
    }
}

function updateVersionOptions() {
    const flowTypeSelect = document.getElementById('flow-type');
    const versionSelect = document.getElementById('flow-version');
    
    if (!flowTypeSelect || !versionSelect) return;
    
    // Clear current options
    versionSelect.innerHTML = '';
    
    // Add empty option
    addOption(versionSelect, '', 'All Versions');
    
    // Add new options based on selected flow type
    if (flowTypeSelect.value === 'netflow') {
        addOption(versionSelect, '5', 'Version 5');
        addOption(versionSelect, '9', 'Version 9');
        addOption(versionSelect, '10', 'IPFIX (v10)');
    } else if (flowTypeSelect.value === 'sflow') {
        addOption(versionSelect, '4', 'Version 4');
        addOption(versionSelect, '5', 'Version 5');
    }
}

function addOption(selectElement, value, text) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = text;
    selectElement.appendChild(option);
}

function setupToggleButtons() {
    // Use event delegation for toggle buttons (including future ones)
    document.addEventListener('click', function(event) {
        const target = event.target;
        
        // Check if the click was on a toggle button or its child
        const toggleButton = target.closest('.toggle-target');
        if (!toggleButton) return;
        
        // Get the target ID
        const targetId = toggleButton.getAttribute('data-target-id');
        if (!targetId) return;
        
        // Toggle the target
        toggleForwardTarget(targetId, toggleButton);
    });
}

function toggleForwardTarget(targetId, button) {
    // Disable the button during the request
    button.disabled = true;
    
    // Send request to toggle the target
    fetch(`/toggle_forward_target/${targetId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update button state
            updateToggleButton(button, data.active);
        } else {
            showError(data.error || 'Failed to toggle target');
        }
        
        // Re-enable the button
        button.disabled = false;
    })
    .catch(error => {
        console.error('Error toggling forward target:', error);
        if (typeof notify !== 'undefined') {
            notify('error', 'Failed to toggle target');
        } else {
            showError('Failed to toggle target');
        }
        button.disabled = false;
    });
}

function updateToggleButton(button, active) {
    if (active) {
        button.style.backgroundColor = '#8B0000'; // Dark red for Tritanopia
        button.style.color = '#e0e0e0';
        button.innerHTML = '<i class="fas fa-toggle-on"></i> Active';
    } else {
        button.style.backgroundColor = '#444444'; // Dark gray for inactive
        button.style.color = '#e0e0e0';
        button.innerHTML = '<i class="fas fa-toggle-off"></i> Inactive';
    }
}

function loadForwarderStats() {
    fetch('/api/forwarder_stats')
        .then(response => response.json())
        .then(data => {
            updateForwarderStats(data);
        })
        .catch(error => {
            console.error('Error loading forwarder stats:', error);
            if (typeof notify !== 'undefined') {
                notify('error', 'Failed to load forwarder statistics');
            }
        });
}

function updateForwarderStats(stats) {
    const statsContainer = document.getElementById('forwarder-stats');
    if (!statsContainer) return;
    
    // Calculate queue percentage
    const queuePercentage = stats.queue_capacity > 0 ? 
        Math.round((stats.queue_size / stats.queue_capacity) * 100) : 0;
    
    // Generate color for queue based on percentage - using custom colors for Tritanopia
    let queueColor = '#008800'; // Green equivalent for normal
    if (queuePercentage > 75) {
        queueColor = '#8B0000'; // Dark red for danger
    } else if (queuePercentage > 50) {
        queueColor = '#CC5500'; // Orange-brown for warning
    }
    let queueColorClass = `style="color: ${queueColor}"`;
    
    // Main stats cards
    let statsHtml = `
        <div class="row">
            <div class="col-md-3">
                <div class="card bg-dark text-light border-secondary mb-3">
                    <div class="card-body text-center">
                        <h2>${stats.running ? '<span style="color: #008800">Active</span>' : '<span style="color: #8B0000">Inactive</span>'}</h2>
                        <p class="mb-0">Forwarder Status</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark text-light border-secondary mb-3">
                    <div class="card-body text-center">
                        <h2>${stats.active_targets} / ${stats.total_targets}</h2>
                        <p class="mb-0">Active Targets</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark text-light border-secondary mb-3">
                    <div class="card-body text-center">
                        <h2><span class="${queueColorClass}">${stats.queue_size}</span> / ${stats.queue_capacity}</h2>
                        <p class="mb-0">Queue Size</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark text-light border-secondary mb-3">
                    <div class="card-body text-center">
                        <h2>${formatNumber(stats.forwarded_flows)}</h2>
                        <p class="mb-0">Flows Forwarded</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add target status if available
    if (stats.targets && stats.targets.length > 0) {
        statsHtml += `
            <div class="row mt-4">
                <div class="col-12">
                    <h4>Target Status</h4>
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Address</th>
                                    <th>Protocol</th>
                                    <th>Status</th>
                                    <th>Connection</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        stats.targets.forEach(target => {
            statsHtml += `
                <tr>
                    <td>${target.name}</td>
                    <td>${target.address}</td>
                    <td>${target.protocol.toUpperCase()}${target.use_tls ? ' (TLS)' : ''}</td>
                    <td>
                        <span class="badge" style="background-color: ${target.active ? '#008800' : '#444444'}; color: #e0e0e0;">
                            ${target.active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <span class="badge" style="background-color: ${target.connected ? '#008800' : '#8B0000'}; color: #e0e0e0;">
                            ${target.connected ? 'Connected' : 'Disconnected'}
                        </span>
                    </td>
                </tr>
            `;
        });
        
        statsHtml += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    statsContainer.innerHTML = statsHtml;
}

// Helper function to format large numbers
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function deleteForwardTarget(targetId) {
    if (!confirm('Are you sure you want to delete this forward target?')) {
        return;
    }
    
    fetch(`/api/forward_target/${targetId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Forward target deleted successfully');
            // Reload the page to update the target list
            window.location.reload();
        } else {
            showError(data.error || 'Failed to delete forward target');
        }
    })
    .catch(error => {
        console.error('Error deleting forward target:', error);
        if (typeof notify !== 'undefined') {
            notify('error', 'Failed to delete forward target');
        } else {
            showError('Failed to delete forward target');
        }
    });
}

function showError(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

function showSuccess(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 3000);
}
