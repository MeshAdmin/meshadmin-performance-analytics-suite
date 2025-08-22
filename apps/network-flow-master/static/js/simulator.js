/**
 * Flow Traffic Simulator JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize flatpickr for date/time inputs if they exist
    if (typeof flatpickr !== 'undefined') {
        flatpickr('.date-picker', {
            enableTime: true,
            dateFormat: 'Y-m-d H:i',
            time_24hr: true
        });
    } else {
        console.warn('Flatpickr library not loaded. Date pickers may not work correctly.');
    }

    // Form validation
    const simulationForm = document.getElementById('simulation-form');
    if (simulationForm) {
        simulationForm.addEventListener('submit', function(event) {
            if (!this.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    }

    // Update template info when template is selected
    const templateSelect = document.getElementById('template-id');
    if (templateSelect) {
        templateSelect.addEventListener('change', function() {
            updateTemplateInfo(this.value);
        });
    }
    
    // Update version options when flow type is selected
    const flowTypeSelect = document.getElementById('flow-type');
    if (flowTypeSelect) {
        flowTypeSelect.addEventListener('change', updateVersionOptions);
        
        // Initialize version dropdown if flow type is already selected
        if (flowTypeSelect.value) {
            updateVersionOptions();
        }
    }

    // Preview template button
    const previewButton = document.getElementById('preview-template');
    if (previewButton) {
        previewButton.addEventListener('click', function() {
            const templateId = document.getElementById('template-id').value;
            if (templateId) {
                previewTemplate(templateId);
            } else {
                showAlert('Please select a template to preview', 'warning');
            }
        });
    }

    // Initialize the simulation status poller
    initSimulationPoller();
});

/**
 * Update template info panel
 * @param {string} templateId - Template ID
 */
function updateTemplateInfo(templateId) {
    const templateInfo = document.getElementById('template-info');
    
    if (!templateId) {
        templateInfo.innerHTML = `
            <div class="alert border-accent">
                No template selected. Random flow data will be generated.
            </div>
        `;
        return;
    }
    
    templateInfo.innerHTML = `
        <div class="d-flex justify-content-center">
            <div class="spinner-border text-accent" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Fetch template details
    fetch(`/template/${templateId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            templateInfo.innerHTML = `
                <div class="alert border-accent">
                    <h6 class="mb-2">${data.name}</h6>
                    <p class="mb-2">${data.description || 'No description provided'}</p>
                    <div class="row">
                        <div class="col-md-6">
                            <small class="d-block"><strong>Type:</strong> ${data.flow_type}</small>
                            <small class="d-block"><strong>Version:</strong> ${data.flow_version}</small>
                        </div>
                        <div class="col-md-6">
                            <small class="d-block"><strong>Source IPs:</strong> ${data.source_ips || 'Random'}</small>
                            <small class="d-block"><strong>Destination IPs:</strong> ${data.destination_ips || 'Random'}</small>
                        </div>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
            templateInfo.innerHTML = `
                <div class="alert alert-danger">
                    Error loading template information. Please try again.
                </div>
            `;
        });
}

/**
 * Preview template
 * @param {string} templateId - Template ID
 */
function previewTemplate(templateId) {
    // Show modal with template preview
    // This is a placeholder for actual implementation
    alert('Template preview functionality is coming soon!');
}

/**
 * Initialize simulation status poller
 */
function initSimulationPoller() {
    loadSimulations();
    
    // Poll for simulation status updates every 5 seconds
    setInterval(loadSimulations, 5000);
}

/**
 * Load active simulations
 */
function loadSimulations() {
    const simulationsTable = document.getElementById('simulations-table-body');
    if (!simulationsTable) return;
    
    fetch('/simulations')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.simulations && data.simulations.length > 0) {
                let html = '';
                data.simulations.forEach(sim => {
                    html += `
                        <tr>
                            <td>${sim.id}</td>
                            <td>${sim.flow_type} v${sim.flow_version}</td>
                            <td>${sim.packets_per_second} pps</td>
                            <td>${new Date(sim.start_time).toLocaleString()}</td>
                            <td>
                                <span class="badge" style="background-color: ${sim.status === 'running' ? '#008800' : '#444444'}; color: #e0e0e0;">
                                    ${sim.status}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-sm stop-simulation" style="background-color: #8B0000; color: #e0e0e0;" data-id="${sim.id}">
                                    <i class="fas fa-stop"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                });
                simulationsTable.innerHTML = html;
                
                // Add event listeners to stop buttons
                document.querySelectorAll('.stop-simulation').forEach(btn => {
                    btn.addEventListener('click', function() {
                        stopSimulation(this.getAttribute('data-id'));
                    });
                });
            } else {
                simulationsTable.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">No active simulations</td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Stop a simulation
 * @param {string} simulationId - Simulation ID
 */
function stopSimulation(simulationId) {
    fetch(`/stop_simulation/${simulationId}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showAlert('Simulation stopped successfully', 'success');
            loadSimulations();
        } else {
            showAlert(data.message || 'Failed to stop simulation', 'danger');
        }
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showAlert('Error stopping simulation. Please try again.', 'danger');
    });
}

/**
 * Update version options based on flow type selection
 */
function updateVersionOptions() {
    const flowTypeSelect = document.getElementById('flow-type');
    const versionSelect = document.getElementById('flow-version');
    
    if (!flowTypeSelect || !versionSelect) return;
    
    // Clear current options except the first disabled option
    while (versionSelect.options.length > 1) {
        versionSelect.remove(1);
    }
    
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

/**
 * Add an option to a select element
 * @param {HTMLSelectElement} selectElement - The select element
 * @param {string} value - The option value
 * @param {string} text - The option text
 */
function addOption(selectElement, value, text) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = text;
    selectElement.appendChild(option);
}

/**
 * Show an alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}