/**
 * Reports Management Script
 * Handles report creation, editing, scheduling, and execution
 */

// Initialize report functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initReportBuilder();
    initReportScheduler();
    initReportExport();
    initDataSourceSelectors();
    setupPreviewRefresh();
});

/**
 * Initialize the report builder interface
 */
function initReportBuilder() {
    console.log('Initializing report builder...');
    
    // Initialize the report format selector
    const formatSelector = document.getElementById('report-format');
    if (formatSelector) {
        formatSelector.addEventListener('change', updateFormatOptions);
    }
    
    // Initialize save report button
    const saveButton = document.getElementById('save-report-button');
    if (saveButton) {
        saveButton.addEventListener('click', saveReport);
    }
    
    // Initialize run report button
    const runButton = document.getElementById('run-report-button');
    if (runButton) {
        runButton.addEventListener('click', runReport);
    }
    
    // Initialize custom fields for parameters
    initParameterFields();
    
    // Initialize drag and drop for report sections
    initDragAndDrop();
}

/**
 * Initialize parameter fields for the report
 */
function initParameterFields() {
    const paramContainer = document.getElementById('parameter-container');
    if (!paramContainer) return;
    
    const addParamButton = document.getElementById('add-parameter-button');
    if (addParamButton) {
        addParamButton.addEventListener('click', () => {
            const paramId = 'param-' + Date.now();
            const paramHtml = `
                <div class="parameter-row" id="${paramId}">
                    <div class="form-group">
                        <label class="form-label">Parameter Name</label>
                        <input type="text" class="form-control param-name" placeholder="e.g., site_id">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Parameter Type</label>
                        <select class="form-control param-type">
                            <option value="string">Text</option>
                            <option value="number">Number</option>
                            <option value="date">Date</option>
                            <option value="boolean">Yes/No</option>
                            <option value="list">List</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Default Value</label>
                        <input type="text" class="form-control param-default" placeholder="Default value">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Required</label>
                        <div class="toggle-switch">
                            <input type="checkbox" id="required-${paramId}" class="param-required">
                            <label for="required-${paramId}"></label>
                        </div>
                    </div>
                    <button class="btn btn-danger remove-param" data-param-id="${paramId}">Remove</button>
                </div>
            `;
            
            paramContainer.insertAdjacentHTML('beforeend', paramHtml);
            
            // Add event listener for the remove button
            const removeButton = document.querySelector(`#${paramId} .remove-param`);
            if (removeButton) {
                removeButton.addEventListener('click', (e) => {
                    const paramId = e.target.getAttribute('data-param-id');
                    const paramRow = document.getElementById(paramId);
                    if (paramRow) {
                        paramRow.remove();
                    }
                });
            }
            
            // Add event listener for parameter type changes
            const typeSelect = document.querySelector(`#${paramId} .param-type`);
            if (typeSelect) {
                typeSelect.addEventListener('change', (e) => {
                    const defaultInput = e.target.closest('.parameter-row').querySelector('.param-default');
                    
                    // Update the default input based on type
                    switch (e.target.value) {
                        case 'number':
                            defaultInput.type = 'number';
                            defaultInput.placeholder = '0';
                            break;
                        case 'date':
                            defaultInput.type = 'date';
                            defaultInput.placeholder = '';
                            break;
                        case 'boolean':
                            defaultInput.type = 'text';
                            defaultInput.placeholder = 'true or false';
                            break;
                        case 'list':
                            defaultInput.type = 'text';
                            defaultInput.placeholder = 'Option 1, Option 2, Option 3';
                            break;
                        default:
                            defaultInput.type = 'text';
                            defaultInput.placeholder = 'Default value';
                    }
                });
            }
        });
    }
    
    // Set up event delegation for remove buttons
    paramContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-param')) {
            const paramId = e.target.getAttribute('data-param-id');
            const paramRow = document.getElementById(paramId);
            if (paramRow) {
                paramRow.remove();
            }
        }
    });
}

/**
 * Initialize drag and drop for report sections
 */
function initDragAndDrop() {
    const reportSections = document.getElementById('report-sections');
    if (!reportSections) return;
    
    // Initialize drag and drop functionality using a library like SortableJS
    if (typeof Sortable !== 'undefined') {
        new Sortable(reportSections, {
            animation: 150,
            handle: '.drag-handle',
            onEnd: function(evt) {
                // Update the section order when items are reordered
                updateSectionOrder();
            }
        });
    }
    
    // Add section button
    const addSectionButton = document.getElementById('add-section-button');
    if (addSectionButton) {
        addSectionButton.addEventListener('click', addReportSection);
    }
    
    // Set up event delegation for section controls
    reportSections.addEventListener('click', (e) => {
        // Remove section button
        if (e.target.classList.contains('remove-section')) {
            const sectionId = e.target.closest('.report-section').id;
            removeReportSection(sectionId);
        }
        
        // Edit section button
        if (e.target.classList.contains('edit-section')) {
            const sectionId = e.target.closest('.report-section').id;
            editReportSection(sectionId);
        }
    });
}

/**
 * Add a new section to the report
 */
function addReportSection() {
    const reportSections = document.getElementById('report-sections');
    if (!reportSections) return;
    
    const sectionId = 'section-' + Date.now();
    const sectionHtml = `
        <div class="report-section card" id="${sectionId}">
            <div class="card-header">
                <div class="drag-handle">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="3" y1="12" x2="21" y2="12"></line>
                        <line x1="3" y1="6" x2="21" y2="6"></line>
                        <line x1="3" y1="18" x2="21" y2="18"></line>
                    </svg>
                </div>
                <h3 class="section-title">New Section</h3>
                <div class="section-actions">
                    <button class="btn btn-icon btn-secondary edit-section" title="Edit Section">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-danger remove-section" title="Remove Section">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="section-content">
                    <p class="text-center text-secondary">Click Edit to configure this section.</p>
                </div>
                <div class="section-config" style="display: none;">
                    <input type="hidden" class="section-type" value="text">
                    <input type="hidden" class="section-data" value="">
                </div>
            </div>
        </div>
    `;
    
    reportSections.insertAdjacentHTML('beforeend', sectionHtml);
    
    // Open the edit dialog for the new section
    editReportSection(sectionId);
}

/**
 * Remove a section from the report
 * @param {string} sectionId - The ID of the section to remove
 */
function removeReportSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section && confirm('Are you sure you want to remove this section?')) {
        section.remove();
        updateSectionOrder();
    }
}

/**
 * Edit a report section
 * @param {string} sectionId - The ID of the section to edit
 */
function editReportSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    const sectionType = section.querySelector('.section-type').value;
    const sectionData = section.querySelector('.section-data').value;
    let sectionDataObj = {};
    
    try {
        if (sectionData) {
            sectionDataObj = JSON.parse(sectionData);
        }
    } catch (e) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
    }
    
    // Create modal for editing section
    const modal = document.createElement('div');
    modal.className = 'modal fade-in';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Edit Section</h2>
                <button class="close-modal">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-section-form">
                    <div class="form-group">
                        <label for="section-title" class="form-label">Section Title</label>
                        <input type="text" id="section-title" class="form-control" value="${section.querySelector('.section-title').textContent}" required>
                    </div>
                    <div class="form-group">
                        <label for="section-type" class="form-label">Section Type</label>
                        <select id="section-type" class="form-control" required>
                            <option value="text" ${sectionType === 'text' ? 'selected' : ''}>Text</option>
                            <option value="table" ${sectionType === 'table' ? 'selected' : ''}>Table</option>
                            <option value="chart" ${sectionType === 'chart' ? 'selected' : ''}>Chart</option>
                            <option value="metrics" ${sectionType === 'metrics' ? 'selected' : ''}>Metrics</option>
                            <option value="logs" ${sectionType === 'logs' ? 'selected' : ''}>Logs</option>
                        </select>
                    </div>
                    
                    <div id="section-type-config">
                        <!-- Dynamic content based on section type -->
                    </div>
                    
                    <div class="form-group mt-4">
                        <button type="submit" class="btn btn-primary">Save Section</button>
                        <button type="button" class="btn btn-secondary close-modal">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add event listeners
    const closeButtons = modal.querySelectorAll('.close-modal');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modal.remove();
        });
    });
    
    // Handle section type change
    const sectionTypeSelect = document.getElementById('section-type');
    sectionTypeSelect.addEventListener('change', () => {
        loadSectionConfigForm(sectionTypeSelect.value, sectionDataObj);
    });
    
    // Initialize section config form
    loadSectionConfigForm(sectionType, sectionDataObj);
    
    // Handle form submission
    const form = document.getElementById('edit-section-form');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Get form data
        const title = document.getElementById('section-title').value;
        const type = document.getElementById('section-type').value;
        
        // Get section data based on type
        let data = {};
        
        switch (type) {
            case 'text':
                data.content = document.getElementById('text-content').value;
                break;
                
            case 'table':
                data.source = document.getElementById('table-data-source').value;
                data.query = document.getElementById('table-query').value;
                data.limit = parseInt(document.getElementById('table-limit').value);
                break;
                
            case 'chart':
                data.type = document.getElementById('chart-type').value;
                data.source = document.getElementById('chart-data-source').value;
                data.query = document.getElementById('chart-query').value;
                data.options = document.getElementById('chart-options').value;
                break;
                
            case 'metrics':
                data.source = document.getElementById('metrics-data-source').value;
                data.metrics = document.getElementById('metrics-list').value.split(',').map(m => m.trim());
                data.period = document.getElementById('metrics-period').value;
                break;
                
            case 'logs':
                data.source = document.getElementById('logs-data-source').value;
                data.filter = document.getElementById('logs-filter').value;
                data.limit = parseInt(document.getElementById('logs-limit').value);
                break;
        }
        
        // Update section in the DOM
        section.querySelector('.section-title').textContent = title;
        section.querySelector('.section-type').value = type;
        section.querySelector('.section-data').value = JSON.stringify(data);
        
        // Update section preview
        updateSectionPreview(section, type, data);
        
        // Close modal
        modal.remove();
    });
}

/**
 * Load configuration form for a specific section type
 * @param {string} type - Section type
 * @param {Object} data - Section data
 */
function loadSectionConfigForm(type, data) {
    const configContainer = document.getElementById('section-type-config');
    if (!configContainer) return;
    
    let formHtml = '';
    
    switch (type) {
        case 'text':
            formHtml = `
                <div class="form-group">
                    <label for="text-content" class="form-label">Content</label>
                    <textarea id="text-content" class="form-control" rows="5">${data.content || ''}</textarea>
                    <small class="text-muted">You can use Markdown formatting.</small>
                </div>
            `;
            break;
            
        case 'table':
            formHtml = `
                <div class="form-group">
                    <label for="table-data-source" class="form-label">Data Source</label>
                    <select id="table-data-source" class="form-control">
                        <option value="syslog" ${data.source === 'syslog' ? 'selected' : ''}>Syslog</option>
                        <option value="snmp" ${data.source === 'snmp' ? 'selected' : ''}>SNMP Traps</option>
                        <option value="netflow" ${data.source === 'netflow' ? 'selected' : ''}>NetFlow</option>
                        <option value="sflow" ${data.source === 'sflow' ? 'selected' : ''}>sFlow</option>
                        <option value="windows_events" ${data.source === 'windows_events' ? 'selected' : ''}>Windows Events</option>
                        <option value="otel" ${data.source === 'otel' ? 'selected' : ''}>OTEL</option>
                        <option value="custom" ${data.source === 'custom' ? 'selected' : ''}>Custom SQL</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="table-query" class="form-label">Query/Filter</label>
                    <textarea id="table-query" class="form-control" rows="3">${data.query || ''}</textarea>
                    <small class="text-muted">For SQL or filter expression.</small>
                </div>
                <div class="form-group">
                    <label for="table-limit" class="form-label">Row Limit</label>
                    <input type="number" id="table-limit" class="form-control" value="${data.limit || 100}" min="1" max="1000">
                </div>
            `;
            break;
            
        case 'chart':
            formHtml = `
                <div class="form-group">
                    <label for="chart-type" class="form-label">Chart Type</label>
                    <select id="chart-type" class="form-control">
                        <option value="line" ${data.type === 'line' ? 'selected' : ''}>Line Chart</option>
                        <option value="bar" ${data.type === 'bar' ? 'selected' : ''}>Bar Chart</option>
                        <option value="pie" ${data.type === 'pie' ? 'selected' : ''}>Pie Chart</option>
                        <option value="doughnut" ${data.type === 'doughnut' ? 'selected' : ''}>Doughnut Chart</option>
                        <option value="area" ${data.type === 'area' ? 'selected' : ''}>Area Chart</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="chart-data-source" class="form-label">Data Source</label>
                    <select id="chart-data-source" class="form-control">
                        <option value="syslog" ${data.source === 'syslog' ? 'selected' : ''}>Syslog</option>
                        <option value="snmp" ${data.source === 'snmp' ? 'selected' : ''}>SNMP Traps</option>
                        <option value="netflow" ${data.source === 'netflow' ? 'selected' : ''}>NetFlow</option>
                        <option value="sflow" ${data.source === 'sflow' ? 'selected' : ''}>sFlow</option>
                        <option value="windows_events" ${data.source === 'windows_events' ? 'selected' : ''}>Windows Events</option>
                        <option value="otel" ${data.source === 'otel' ? 'selected' : ''}>OTEL</option>
                        <option value="metrics" ${data.source === 'metrics' ? 'selected' : ''}>Metrics</option>
                        <option value="custom" ${data.source === 'custom' ? 'selected' : ''}>Custom SQL</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="chart-query" class="form-label">Query/Filter</label>
                    <textarea id="chart-query" class="form-control" rows="3">${data.query || ''}</textarea>
                    <small class="text-muted">For SQL or filter expression.</small>
                </div>
                <div class="form-group">
                    <label for="chart-options" class="form-label">Chart Options (JSON)</label>
                    <textarea id="chart-options" class="form-control" rows="3">${data.options || '{}'}</textarea>
                    <small class="text-muted">Additional options in JSON format.</small>
                </div>
            `;
            break;
            
        case 'metrics':
            formHtml = `
                <div class="form-group">
                    <label for="metrics-data-source" class="form-label">Data Source</label>
                    <select id="metrics-data-source" class="form-control">
                        <option value="snmp" ${data.source === 'snmp' ? 'selected' : ''}>SNMP</option>
                        <option value="netflow" ${data.source === 'netflow' ? 'selected' : ''}>NetFlow</option>
                        <option value="sflow" ${data.source === 'sflow' ? 'selected' : ''}>sFlow</option>
                        <option value="otel" ${data.source === 'otel' ? 'selected' : ''}>OTEL</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="metrics-list" class="form-label">Metrics (comma separated)</label>
                    <input type="text" id="metrics-list" class="form-control" value="${(data.metrics || []).join(', ')}">
                    <small class="text-muted">e.g., cpu.usage, memory.used, disk.io</small>
                </div>
                <div class="form-group">
                    <label for="metrics-period" class="form-label">Time Period</label>
                    <select id="metrics-period" class="form-control">
                        <option value="hour" ${data.period === 'hour' ? 'selected' : ''}>Last Hour</option>
                        <option value="day" ${data.period === 'day' ? 'selected' : ''}>Last 24 Hours</option>
                        <option value="week" ${data.period === 'week' ? 'selected' : ''}>Last 7 Days</option>
                        <option value="month" ${data.period === 'month' ? 'selected' : ''}>Last 30 Days</option>
                        <option value="custom" ${data.period === 'custom' ? 'selected' : ''}>Custom</option>
                    </select>
                </div>
            `;
            break;
            
        case 'logs':
            formHtml = `
                <div class="form-group">
                    <label for="logs-data-source" class="form-label">Log Source</label>
                    <select id="logs-data-source" class="form-control">
                        <option value="syslog" ${data.source === 'syslog' ? 'selected' : ''}>Syslog</option>
                        <option value="snmp" ${data.source === 'snmp' ? 'selected' : ''}>SNMP Traps</option>
                        <option value="windows_events" ${data.source === 'windows_events' ? 'selected' : ''}>Windows Events</option>
                        <option value="all" ${data.source === 'all' ? 'selected' : ''}>All Logs</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="logs-filter" class="form-label">Filter Expression</label>
                    <input type="text" id="logs-filter" class="form-control" value="${data.filter || ''}">
                    <small class="text-muted">e.g., severity:error, contains:failed</small>
                </div>
                <div class="form-group">
                    <label for="logs-limit" class="form-label">Log Limit</label>
                    <input type="number" id="logs-limit" class="form-control" value="${data.limit || 100}" min="1" max="1000">
                </div>
            `;
            break;
    }
    
    configContainer.innerHTML = formHtml;
}

/**
 * Update the preview of a section
 * @param {HTMLElement} section - Section element
 * @param {string} type - Section type
 * @param {Object} data - Section data
 */
function updateSectionPreview(section, type, data) {
    const contentDiv = section.querySelector('.section-content');
    if (!contentDiv) return;
    
    let previewHtml = '';
    
    switch (type) {
        case 'text':
            previewHtml = `<div class="text-section">${data.content || ''}</div>`;
            break;
            
        case 'table':
            previewHtml = `
                <div class="table-section">
                    <p><strong>Data Source:</strong> ${data.source}</p>
                    <p><strong>Query:</strong> ${data.query || 'None'}</p>
                    <p><strong>Limit:</strong> ${data.limit} rows</p>
                    <div class="table-preview">
                        <p class="text-center text-secondary">Table preview will be shown in the generated report.</p>
                    </div>
                </div>
            `;
            break;
            
        case 'chart':
            previewHtml = `
                <div class="chart-section">
                    <p><strong>Chart Type:</strong> ${data.type}</p>
                    <p><strong>Data Source:</strong> ${data.source}</p>
                    <p><strong>Query:</strong> ${data.query || 'None'}</p>
                    <div class="chart-preview">
                        <p class="text-center text-secondary">Chart preview will be shown in the generated report.</p>
                    </div>
                </div>
            `;
            break;
            
        case 'metrics':
            previewHtml = `
                <div class="metrics-section">
                    <p><strong>Data Source:</strong> ${data.source}</p>
                    <p><strong>Metrics:</strong> ${(data.metrics || []).join(', ')}</p>
                    <p><strong>Period:</strong> ${data.period}</p>
                    <div class="metrics-preview">
                        <p class="text-center text-secondary">Metrics preview will be shown in the generated report.</p>
                    </div>
                </div>
            `;
            break;
            
        case 'logs':
            previewHtml = `
                <div class="logs-section">
                    <p><strong>Log Source:</strong> ${data.source}</p>
                    <p><strong>Filter:</strong> ${data.filter || 'None'}</p>
                    <p><strong>Limit:</strong> ${data.limit} logs</p>
                    <div class="logs-preview">
                        <p class="text-center text-secondary">Logs preview will be shown in the generated report.</p>
                    </div>
                </div>
            `;
            break;
            
        default:
            previewHtml = `<p class="text-center text-secondary">Unknown section type.</p>`;
    }
    
    contentDiv.innerHTML = previewHtml;
}

/**
 * Update the section order in the report
 */
function updateSectionOrder() {
    // This function would update section orders in a real implementation
    console.log('Updating section order...');
}

/**
 * Initialize the report scheduler interface
 */
function initReportScheduler() {
    const scheduleToggle = document.getElementById('schedule-toggle');
    const scheduleOptions = document.getElementById('schedule-options');
    
    if (scheduleToggle && scheduleOptions) {
        scheduleToggle.addEventListener('change', () => {
            scheduleOptions.style.display = scheduleToggle.checked ? 'block' : 'none';
        });
    }
    
    const scheduleType = document.getElementById('schedule-type');
    const customSchedule = document.getElementById('custom-schedule');
    
    if (scheduleType && customSchedule) {
        scheduleType.addEventListener('change', () => {
            customSchedule.style.display = scheduleType.value === 'custom' ? 'block' : 'none';
        });
    }
}

/**
 * Initialize the report export options
 */
function initReportExport() {
    const exportButtons = document.querySelectorAll('.export-report');
    
    exportButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const format = e.target.getAttribute('data-format');
            exportReport(format);
        });
    });
}

/**
 * Export a report in the specified format
 * @param {string} format - Report format (pdf, csv, json, etc.)
 */
function exportReport(format) {
    const reportId = document.getElementById('report-container').dataset.reportId;
    
    if (!reportId) {
        showNotification('Please save the report first.', 'warning');
        return;
    }
    
    const url = `/api/reports/${reportId}/export?format=${format}`;
    
    // Show loading indicator
    showNotification('Generating export...', 'info');
    
    // Request the export
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error exporting report: ${response.statusText}`);
            }
            return response.blob();
        })
        .then(blob => {
            // Create a download link and click it
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `report-${reportId}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            showNotification(`Report exported as ${format.toUpperCase()}.`, 'success');
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
            showNotification('Failed to export report.', 'error');
        });
}

/**
 * Initialize data source selectors
 */
function initDataSourceSelectors() {
    const sourceSelectors = document.querySelectorAll('.data-source-selector');
    
    sourceSelectors.forEach(selector => {
        selector.addEventListener('change', (e) => {
            const targetId = e.target.getAttribute('data-target');
            const target = document.getElementById(targetId);
            
            if (target) {
                // Update available fields or options based on selected data source
                updateAvailableFields(e.target.value, target);
            }
        });
        
        // Initial update if there's a default selection
        const targetId = selector.getAttribute('data-target');
        const target = document.getElementById(targetId);
        
        if (target && selector.value) {
            updateAvailableFields(selector.value, target);
        }
    });
}

/**
 * Update available fields based on selected data source
 * @param {string} source - Selected data source
 * @param {HTMLElement} target - Target element to update
 */
function updateAvailableFields(source, target) {
    // In a real implementation, this would fetch available fields from the server
    // For now, we'll use hardcoded examples
    
    let fields = [];
    
    switch (source) {
        case 'syslog':
            fields = ['timestamp', 'severity', 'facility', 'host', 'message'];
            break;
            
        case 'snmp':
            fields = ['timestamp', 'oid', 'type', 'value', 'source_ip'];
            break;
            
        case 'netflow':
            fields = ['timestamp', 'src_ip', 'dst_ip', 'protocol', 'src_port', 'dst_port', 'bytes', 'packets'];
            break;
            
        case 'sflow':
            fields = ['timestamp', 'agent_ip', 'input_port', 'output_port', 'src_mac', 'dst_mac', 'bytes'];
            break;
            
        case 'windows_events':
            fields = ['timestamp', 'event_id', 'source', 'level', 'computer', 'message'];
            break;
            
        case 'otel':
            fields = ['timestamp', 'service', 'name', 'value', 'attributes', 'resource'];
            break;
            
        default:
            fields = ['timestamp', 'value', 'source', 'message'];
    }
    
    // Update target with available fields
    if (target.tagName === 'SELECT') {
        // Clear existing options
        target.innerHTML = '';
        
        // Add new options
        fields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            target.appendChild(option);
        });
    } else if (target.classList.contains('field-list')) {
        // Update field list
        target.innerHTML = '';
        
        fields.forEach(field => {
            const fieldItem = document.createElement('div');
            fieldItem.className = 'field-item';
            fieldItem.innerHTML = `
                <span class="field-name">${field}</span>
                <button class="btn btn-sm btn-primary add-field" data-field="${field}">Add</button>
            `;
            target.appendChild(fieldItem);
        });
        
        // Add event listeners to the add buttons
        const addButtons = target.querySelectorAll('.add-field');
        addButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const field = e.target.getAttribute('data-field');
                const targetInput = document.getElementById(target.getAttribute('data-target'));
                
                if (targetInput) {
                    // Add field to input
                    if (targetInput.tagName === 'INPUT') {
                        targetInput.value += (targetInput.value ? ', ' : '') + field;
                    } else if (targetInput.tagName === 'TEXTAREA') {
                        const cursorPos = targetInput.selectionStart;
                        const textBefore = targetInput.value.substring(0, cursorPos);
                        const textAfter = targetInput.value.substring(cursorPos);
                        
                        targetInput.value = textBefore + field + textAfter;
                        
                        // Set cursor position after inserted field
                        targetInput.selectionStart = cursorPos + field.length;
                        targetInput.selectionEnd = cursorPos + field.length;
                    }
                    
                    targetInput.focus();
                }
            });
        });
    }
}

/**
 * Update format options based on selected format
 */
function updateFormatOptions() {
    const formatSelector = document.getElementById('report-format');
    const formatOptions = document.getElementById('format-options');
    
    if (!formatSelector || !formatOptions) return;
    
    // Clear existing options
    formatOptions.innerHTML = '';
    
    // Add format-specific options
    let optionsHtml = '';
    
    switch (formatSelector.value) {
        case 'pdf':
            optionsHtml = `
                <div class="form-group">
                    <label for="pdf-page-size" class="form-label">Page Size</label>
                    <select id="pdf-page-size" class="form-control">
                        <option value="letter">Letter</option>
                        <option value="a4">A4</option>
                        <option value="legal">Legal</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="pdf-orientation" class="form-label">Orientation</label>
                    <select id="pdf-orientation" class="form-control">
                        <option value="portrait">Portrait</option>
                        <option value="landscape">Landscape</option>
                    </select>
                </div>
            `;
            break;
            
        case 'excel':
            optionsHtml = `
                <div class="form-group">
                    <label for="excel-sheet-name" class="form-label">Sheet Name</label>
                    <input type="text" id="excel-sheet-name" class="form-control" value="Report">
                </div>
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="excel-include-charts" class="form-check-input" checked>
                        <label for="excel-include-charts" class="form-check-label">Include Charts</label>
                    </div>
                </div>
            `;
            break;
            
        case 'csv':
            optionsHtml = `
                <div class="form-group">
                    <label for="csv-delimiter" class="form-label">Delimiter</label>
                    <select id="csv-delimiter" class="form-control">
                        <option value="comma">Comma (,)</option>
                        <option value="semicolon">Semicolon (;)</option>
                        <option value="tab">Tab</option>
                    </select>
                </div>
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="csv-include-headers" class="form-check-input" checked>
                        <label for="csv-include-headers" class="form-check-label">Include Headers</label>
                    </div>
                </div>
            `;
            break;
            
        case 'html':
            optionsHtml = `
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="html-include-styles" class="form-check-input" checked>
                        <label for="html-include-styles" class="form-check-label">Include Styles</label>
                    </div>
                </div>
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="html-include-scripts" class="form-check-input" checked>
                        <label for="html-include-scripts" class="form-check-label">Include Interactive Elements</label>
                    </div>
                </div>
            `;
            break;
            
        case 'json':
            optionsHtml = `
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="json-pretty" class="form-check-input" checked>
                        <label for="json-pretty" class="form-check-label">Pretty Print</label>
                    </div>
                </div>
            `;
            break;
    }
    
    formatOptions.innerHTML = optionsHtml;
}

/**
 * Save the current report
 */
function saveReport() {
    const reportForm = document.getElementById('report-form');
    if (!reportForm) return;
    
    // Validate form
    if (!reportForm.checkValidity()) {
        reportForm.reportValidity();
        return;
    }
    
    // Get report data
    const reportId = document.getElementById('report-container').dataset.reportId;
    const reportName = document.getElementById('report-name').value;
    const reportDescription = document.getElementById('report-description').value;
    const reportFormat = document.getElementById('report-format').value;
    
    // Collect sections
    const sections = [];
    const sectionElements = document.querySelectorAll('.report-section');
    
    sectionElements.forEach((element, index) => {
        const title = element.querySelector('.section-title').textContent;
        const type = element.querySelector('.section-type').value;
        const dataStr = element.querySelector('.section-data').value;
        
        let data = {};
        try {
            if (dataStr) {
                data = JSON.parse(dataStr);
            }
        } catch (e) {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        }
        
        sections.push({
            title: title,
            type: type,
            data: data,
            order: index
        });
    });
    
    // Collect parameters
    const parameters = [];
    const parameterRows = document.querySelectorAll('.parameter-row');
    
    parameterRows.forEach(row => {
        const name = row.querySelector('.param-name').value;
        const type = row.querySelector('.param-type').value;
        const defaultValue = row.querySelector('.param-default').value;
        const required = row.querySelector('.param-required').checked;
        
        parameters.push({
            name: name,
            type: type,
            default: defaultValue,
            required: required
        });
    });
    
    // Get schedule data
    const scheduled = document.getElementById('schedule-toggle').checked;
    let schedule = null;
    
    if (scheduled) {
        const scheduleType = document.getElementById('schedule-type').value;
        const recipients = document.getElementById('schedule-recipients').value;
        
        schedule = {
            type: scheduleType,
            recipients: recipients.split(',').map(r => r.trim())
        };
        
        if (scheduleType === 'custom') {
            schedule.cron = document.getElementById('schedule-cron').value;
        }
    }
    
    // Create report object
    const report = {
        id: reportId,
        name: reportName,
        description: reportDescription,
        format: reportFormat,
        sections: sections,
        parameters: parameters,
        schedule: schedule
    };
    
    // Save format options
    switch (reportFormat) {
        case 'pdf':
            report.options = {
                pageSize: document.getElementById('pdf-page-size').value,
                orientation: document.getElementById('pdf-orientation').value
            };
            break;
            
        case 'excel':
            report.options = {
                sheetName: document.getElementById('excel-sheet-name').value,
                includeCharts: document.getElementById('excel-include-charts').checked
            };
            break;
            
        case 'csv':
            report.options = {
                delimiter: document.getElementById('csv-delimiter').value,
                includeHeaders: document.getElementById('csv-include-headers').checked
            };
            break;
            
        case 'html':
            report.options = {
                includeStyles: document.getElementById('html-include-styles').checked,
                includeScripts: document.getElementById('html-include-scripts').checked
            };
            break;
            
        case 'json':
            report.options = {
                pretty: document.getElementById('json-pretty').checked
            };
            break;
    }
    
    // Send report to server
    fetch('/api/reports/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(report),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error saving report: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        // Update report ID if it's a new report
        if (data.id && !reportId) {
            document.getElementById('report-container').dataset.reportId = data.id;
            
            // Update URL without reloading
            history.pushState(null, '', `/reports/builder/${data.id}`);
        }
        
        showNotification('Report saved successfully', 'success');
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Failed to save report', 'error');
    });
}

/**
 * Run the current report
 */
function runReport() {
    const reportId = document.getElementById('report-container').dataset.reportId;
    
    if (!reportId) {
        showNotification('Please save the report first.', 'warning');
        return;
    }
    
    // Collect parameter values
    const paramValues = {};
    const paramInputs = document.querySelectorAll('.param-input');
    
    paramInputs.forEach(input => {
        const paramName = input.getAttribute('data-param-name');
        paramValues[paramName] = input.value;
    });
    
    // Show loading indicator
    showNotification('Generating report...', 'info');
    
    // Send request to run report
    fetch(`/api/reports/${reportId}/run`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ parameters: paramValues }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error running report: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.runId) {
            // Redirect to report run result
            window.location.href = `/reports/run/${data.runId}`;
        } else {
            showNotification('Report generation started.', 'success');
        }
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Failed to run report', 'error');
    });
}

/**
 * Setup automatic refresh for the report preview
 */
function setupPreviewRefresh() {
    const previewContainer = document.getElementById('report-preview');
    if (!previewContainer) return;
    
    // Auto-refresh preview when there are changes
    let previewTimer;
    
    // Detect changes in the report form
    const reportForm = document.getElementById('report-form');
    if (reportForm) {
        reportForm.addEventListener('input', () => {
            clearTimeout(previewTimer);
            previewTimer = setTimeout(refreshPreview, 1000);
        });
    }
    
    // Initial preview refresh
    refreshPreview();
}

/**
 * Refresh the report preview
 */
function refreshPreview() {
    const previewContainer = document.getElementById('report-preview');
    if (!previewContainer) return;
    
    const reportName = document.getElementById('report-name').value || 'Untitled Report';
    const reportDescription = document.getElementById('report-description').value || 'No description provided.';
    const sections = document.querySelectorAll('.report-section');
    
    let previewHtml = `
        <div class="preview-header">
            <h1>${reportName}</h1>
            <p>${reportDescription}</p>
        </div>
        <div class="preview-content">
    `;
    
    if (sections.length === 0) {
        previewHtml += `
            <div class="empty-state">
                <p>This report is empty. Add sections to see a preview.</p>
            </div>
        `;
    } else {
        sections.forEach(section => {
            const title = section.querySelector('.section-title').textContent;
            const content = section.querySelector('.section-content').innerHTML;
            
            previewHtml += `
                <div class="preview-section">
                    <h2>${title}</h2>
                    <div class="preview-section-content">
                        ${content}
                    </div>
                </div>
            `;
        });
    }
    
    previewHtml += `</div>`;
    
    previewContainer.innerHTML = previewHtml;
}

/**
 * Show notification to the user
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, info, warning)
 */
function showNotification(message, type = 'info') {
    // Check if notification container exists, if not create it
    let notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} fade-in`;
    notification.textContent = message;
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.className = 'close-notification';
    closeButton.style.marginLeft = '10px';
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.cursor = 'pointer';
    closeButton.addEventListener('click', () => {
        notification.remove();
    });
    
    notification.appendChild(closeButton);
    notificationContainer.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}
