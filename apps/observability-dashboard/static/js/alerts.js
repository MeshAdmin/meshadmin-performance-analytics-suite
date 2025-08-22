/**
 * Initialize the alert rules functionality
 */
function initAlertRules() {
    console.log('Initializing alert rules interface');
    createAlertEventListeners();
}

/**
 * Initialize the alert history view
 */
function initAlertHistory() {
    console.log('Initializing alert history interface');
    
    // Set up select all checkbox
    const selectAllCheckbox = document.getElementById('select-all-alerts');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            toggleSelectAllAlerts(this.checked);
        });
    }
    
    updateFilteredAlertCount();
}

/**
 * Initialize alert dashboard
 */
function initAlertDashboard() {
    console.log('Initializing alert dashboard');
    
    // Initialize notification permissions
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        requestNotificationPermission();
    }
    
    // Set up alert polling
    setInterval(checkForNewAlerts, 30000); // Check every 30 seconds
}

/**
 * Show modal for creating a new alert rule
 */
function showCreateAlertModal() {
    // Reset form
    const form = document.getElementById('alert-rule-form');
    if (form) form.reset();
    
    // Set default values
    document.getElementById('rule-id').value = '';
    document.getElementById('rule-severity').value = 'warning';
    document.getElementById('rule-enabled').checked = true;
    document.getElementById('rule-status-text').textContent = 'Enabled';
    document.getElementById('rule-cooldown').value = '15';
    
    // Clear notification channel configs
    document.getElementById('notify-email').checked = false;
    document.getElementById('notify-slack').checked = false;
    document.getElementById('notify-pagerduty').checked = false;
    document.getElementById('email-config').style.display = 'none';
    document.getElementById('slack-config').style.display = 'none';
    document.getElementById('pagerduty-config').style.display = 'none';
    
    // Reset condition builder
    const conditionBuilder = document.getElementById('condition-builder');
    while (conditionBuilder.children.length > 1) {
        conditionBuilder.removeChild(conditionBuilder.lastChild);
    }
    
    const conditionFields = conditionBuilder.querySelector('.condition-field');
    const conditionOperators = conditionBuilder.querySelector('.condition-operator');
    const conditionValue = conditionBuilder.querySelector('.condition-value');
    
    if (conditionFields) conditionFields.innerHTML = '<option value="">Select Field</option>';
    if (conditionOperators) conditionOperators.value = 'eq';
    if (conditionValue) conditionValue.value = '';
    
    document.getElementById('condition-logic').value = 'AND';
    
    // Update modal title and button
    document.getElementById('alert-rule-modal-title').textContent = 'Create Alert Rule';
    document.getElementById('save-rule-btn').textContent = 'Create';
    
    // Show modal
    showModal('alert-rule-modal');
}

/**
 * Update condition fields based on selected data source
 * @param {string} dataSource - Selected data source
 */
function updateConditionFields(dataSource) {
    const conditionFieldSelects = document.querySelectorAll('.condition-field');
    
    // Clear all field options
    conditionFieldSelects.forEach(select => {
        select.innerHTML = '<option value="">Select Field</option>';
    });
    
    // Add fields based on data source
    let fields = [];
    
    switch (dataSource) {
        case 'syslog':
            fields = [
                { value: 'severity', label: 'Severity' },
                { value: 'facility', label: 'Facility' },
                { value: 'host', label: 'Host' },
                { value: 'program', label: 'Program' },
                { value: 'message', label: 'Message' }
            ];
            break;
            
        case 'snmp':
            fields = [
                { value: 'oid', label: 'OID' },
                { value: 'trap_type', label: 'Trap Type' },
                { value: 'device_ip', label: 'Device IP' },
                { value: 'value', label: 'Value' }
            ];
            break;
            
        case 'netflow':
        case 'sflow':
            fields = [
                { value: 'src_ip', label: 'Source IP' },
                { value: 'dst_ip', label: 'Destination IP' },
                { value: 'src_port', label: 'Source Port' },
                { value: 'dst_port', label: 'Destination Port' },
                { value: 'protocol', label: 'Protocol' },
                { value: 'bytes', label: 'Bytes' },
                { value: 'packets', label: 'Packets' },
                { value: 'duration', label: 'Duration (s)' }
            ];
            break;
            
        case 'windows_events':
            fields = [
                { value: 'event_id', label: 'Event ID' },
                { value: 'source', label: 'Source' },
                { value: 'level', label: 'Level' },
                { value: 'computer', label: 'Computer' },
                { value: 'message', label: 'Message' }
            ];
            break;
            
        case 'otel':
            fields = [
                { value: 'metric_name', label: 'Metric Name' },
                { value: 'metric_value', label: 'Metric Value' },
                { value: 'service_name', label: 'Service Name' },
                { value: 'span_duration', label: 'Span Duration (ms)' },
                { value: 'status_code', label: 'Status Code' },
                { value: 'span_name', label: 'Span Name' },
                { value: 'error', label: 'Error' }
            ];
            break;
    }
    
    // Populate field options
    conditionFieldSelects.forEach(select => {
        fields.forEach(field => {
            const option = document.createElement('option');
            option.value = field.value;
            option.textContent = field.label;
            select.appendChild(option);
        });
    });
}

/**
 * Add a new condition row to the condition builder
 */
function addConditionRow() {
    const conditionBuilder = document.getElementById('condition-builder');
    const dataSource = document.getElementById('rule-data-source').value;
    
    const newRow = document.createElement('div');
    newRow.className = 'condition-row';
    
    // Create field select
    const fieldSelect = document.createElement('select');
    fieldSelect.className = 'condition-field form-control';
    fieldSelect.innerHTML = '<option value="">Select Field</option>';
    
    // Create operator select
    const operatorSelect = document.createElement('select');
    operatorSelect.className = 'condition-operator form-control';
    operatorSelect.innerHTML = `
        <option value="eq">equals</option>
        <option value="neq">not equals</option>
        <option value="gt">greater than</option>
        <option value="lt">less than</option>
        <option value="gte">greater than or equal</option>
        <option value="lte">less than or equal</option>
        <option value="contains">contains</option>
        <option value="not_contains">does not contain</option>
        <option value="regex">matches regex</option>
    `;
    
    // Create value input
    const valueInput = document.createElement('input');
    valueInput.type = 'text';
    valueInput.className = 'condition-value form-control';
    valueInput.placeholder = 'Value';
    
    // Create remove button
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'btn btn-sm btn-danger remove-condition';
    removeButton.innerHTML = '<i class="fas fa-times"></i>';
    
    // Add elements to row
    newRow.appendChild(fieldSelect);
    newRow.appendChild(operatorSelect);
    newRow.appendChild(valueInput);
    newRow.appendChild(removeButton);
    
    // Add row to builder
    conditionBuilder.appendChild(newRow);
    
    // Update fields based on current data source
    if (dataSource) {
        updateConditionFields(dataSource);
    }
}

/**
 * Create a new alert rule from form data
 */
function saveAlertRule() {
    const form = document.getElementById('alert-rule-form');
    const ruleId = document.getElementById('rule-id').value;
    
    // Validate form
    const ruleName = document.getElementById('rule-name').value;
    const ruleDataSource = document.getElementById('rule-data-source').value;
    
    if (!ruleName) {
        showNotification('Please enter a rule name', 'error');
        return;
    }
    
    if (!ruleDataSource) {
        showNotification('Please select a data source', 'error');
        return;
    }
    
    // Get conditions
    const conditions = [];
    const conditionRows = document.querySelectorAll('.condition-row');
    let validConditions = true;
    
    conditionRows.forEach(row => {
        const field = row.querySelector('.condition-field').value;
        const operator = row.querySelector('.condition-operator').value;
        const value = row.querySelector('.condition-value').value;
        
        if (!field || !value) {
            validConditions = false;
            return;
        }
        
        conditions.push({
            field,
            operator,
            value
        });
    });
    
    if (!validConditions || conditions.length === 0) {
        showNotification('Please complete all condition fields', 'error');
        return;
    }
    
    // Get notification channels
    const notificationChannels = [];
    
    if (document.getElementById('notify-email').checked) {
        const recipients = document.getElementById('email-recipients').value;
        if (recipients) {
            notificationChannels.push({
                type: 'email',
                recipients: recipients.split(',').map(r => r.trim())
            });
        }
    }
    
    if (document.getElementById('notify-slack').checked) {
        const channel = document.getElementById('slack-channel').value;
        if (channel) {
            notificationChannels.push({
                type: 'slack',
                channel: channel
            });
        }
    }
    
    if (document.getElementById('notify-pagerduty').checked) {
        const severity = document.getElementById('pagerduty-severity').value;
        notificationChannels.push({
            type: 'pagerduty',
            severity: severity
        });
    }
    
    // Build rule object
    const rule = {
        name: ruleName,
        description: document.getElementById('rule-description').value,
        data_source: ruleDataSource,
        severity: document.getElementById('rule-severity').value,
        enabled: document.getElementById('rule-enabled').checked,
        condition: {
            logic: document.getElementById('condition-logic').value,
            conditions: conditions
        },
        cooldown_minutes: parseInt(document.getElementById('rule-cooldown').value, 10) || 15,
        notification_channels: notificationChannels
    };
    
    // Send to server
    const url = ruleId ? `/api/alert_rules/${ruleId}` : '/api/alert_rules';
    const method = ruleId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(rule)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to save alert rule');
        return response.json();
    })
    .then(data => {
        if (typeof notify !== 'undefined') {
            notify('success', `Alert rule ${ruleId ? 'updated' : 'created'} successfully`);
        } else {
            console.log(`Alert rule ${ruleId ? 'updated' : 'created'} successfully`);
        }
        closeModal('alert-rule-modal');
        
        // Reload rules list
        window.location.reload();
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        if (typeof notify !== 'undefined') {
            notify('error', `Error ${ruleId ? 'updating' : 'creating'} alert rule`);
        } else {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        }
    });
}

/**
 * Update the status of an alert rule
 * @param {string} ruleId - The ID of the alert rule
 * @param {boolean} enabled - Whether the rule is enabled
 */
function updateAlertRuleStatus(ruleId, enabled) {
    fetch(`/api/alert_rules/${ruleId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to update alert rule status');
        return response.json();
    })
    .then(data => {
        if (typeof notify !== 'undefined') {
            notify('success', `Alert rule ${enabled ? 'enabled' : 'disabled'}`);
        } else {
            console.log(`Alert rule ${enabled ? 'enabled' : 'disabled'}`);
        }
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        if (typeof notify !== 'undefined') {
            notify('error', 'Error updating alert rule status');
        } else {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        }
        
        // Revert toggle
        const toggle = document.getElementById(`status-toggle-${ruleId}`);
        if (toggle) toggle.checked = !enabled;
    });
}

/**
 * Edit an alert rule
 * @param {string} ruleId - The ID of the rule to edit
 */
function editAlertRule(ruleId) {
    fetch(`/api/alert_rules/${ruleId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch alert rule');
            return response.json();
        })
        .then(rule => {
            showEditAlertModal(rule);
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
            if (typeof notify !== 'undefined') {
                notify('error', 'Error fetching alert rule');
            } else {
                errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
            }
        });
}

/**
 * Show modal for editing an alert rule
 * @param {Object} rule - Alert rule object
 */
function showEditAlertModal(rule) {
    // Set form values
    document.getElementById('rule-id').value = rule.id;
    document.getElementById('rule-name').value = rule.name;
    document.getElementById('rule-description').value = rule.description || '';
    document.getElementById('rule-data-source').value = rule.data_source;
    document.getElementById('rule-severity').value = rule.severity;
    document.getElementById('rule-enabled').checked = rule.enabled;
    document.getElementById('rule-status-text').textContent = rule.enabled ? 'Enabled' : 'Disabled';
    document.getElementById('rule-cooldown').value = rule.cooldown_minutes || 15;
    
    // Set up condition builder
    updateConditionFields(rule.data_source);
    
    const conditionBuilder = document.getElementById('condition-builder');
    while (conditionBuilder.children.length > 0) {
        conditionBuilder.removeChild(conditionBuilder.lastChild);
    }
    
    const conditionLogic = document.getElementById('condition-logic');
    conditionLogic.value = rule.condition.logic || 'AND';
    
    rule.condition.conditions.forEach((condition, index) => {
        const row = document.createElement('div');
        row.className = 'condition-row';
        
        // Create field select
        const fieldSelect = document.createElement('select');
        fieldSelect.className = 'condition-field form-control';
        fieldSelect.innerHTML = '<option value="">Select Field</option>';
        
        // Create operator select
        const operatorSelect = document.createElement('select');
        operatorSelect.className = 'condition-operator form-control';
        operatorSelect.innerHTML = `
            <option value="eq">equals</option>
            <option value="neq">not equals</option>
            <option value="gt">greater than</option>
            <option value="lt">less than</option>
            <option value="gte">greater than or equal</option>
            <option value="lte">less than or equal</option>
            <option value="contains">contains</option>
            <option value="not_contains">does not contain</option>
            <option value="regex">matches regex</option>
        `;
        
        // Create value input
        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.className = 'condition-value form-control';
        valueInput.placeholder = 'Value';
        
        // Create remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-sm btn-danger remove-condition';
        removeButton.innerHTML = '<i class="fas fa-times"></i>';
        
        // Add elements to row
        row.appendChild(fieldSelect);
        row.appendChild(operatorSelect);
        row.appendChild(valueInput);
        row.appendChild(removeButton);
        
        // Add row to builder
        conditionBuilder.appendChild(row);
        
        // Update fields based on data source
        updateConditionFields(rule.data_source);
        
        // Set field values
        fieldSelect.value = condition.field;
        operatorSelect.value = condition.operator;
        valueInput.value = condition.value;
    });
    
    // Set notification channels
    document.getElementById('notify-email').checked = false;
    document.getElementById('notify-slack').checked = false;
    document.getElementById('notify-pagerduty').checked = false;
    document.getElementById('email-recipients').value = '';
    document.getElementById('slack-channel').value = '';
    document.getElementById('pagerduty-severity').value = 'info';
    
    document.getElementById('email-config').style.display = 'none';
    document.getElementById('slack-config').style.display = 'none';
    document.getElementById('pagerduty-config').style.display = 'none';
    
    if (rule.notification_channels && rule.notification_channels.length > 0) {
        rule.notification_channels.forEach(channel => {
            if (channel.type === 'email') {
                document.getElementById('notify-email').checked = true;
                document.getElementById('email-config').style.display = 'block';
                document.getElementById('email-recipients').value = channel.recipients.join(', ');
            } else if (channel.type === 'slack') {
                document.getElementById('notify-slack').checked = true;
                document.getElementById('slack-config').style.display = 'block';
                document.getElementById('slack-channel').value = channel.channel;
            } else if (channel.type === 'pagerduty') {
                document.getElementById('notify-pagerduty').checked = true;
                document.getElementById('pagerduty-config').style.display = 'block';
                document.getElementById('pagerduty-severity').value = channel.severity || 'info';
            }
        });
    }
    
    // Update modal title and button
    document.getElementById('alert-rule-modal-title').textContent = 'Edit Alert Rule';
    document.getElementById('save-rule-btn').textContent = 'Update';
    
    // Show modal
    showModal('alert-rule-modal');
}

/**
 * Filter alert rules based on selected filters
 */
function filterAlertRules() {
    const searchTerm = document.getElementById('rule-search').value.toLowerCase();
    const severityFilter = document.getElementById('filter-severity').value;
    const dataSourceFilter = document.getElementById('filter-data-source').value;
    const statusFilter = document.getElementById('filter-status').value;
    
    const rows = document.querySelectorAll('#alert-rules-table tbody tr');
    
    rows.forEach(row => {
        const name = row.cells[0].textContent.toLowerCase();
        const severity = row.getAttribute('data-severity');
        const dataSource = row.getAttribute('data-source');
        const status = row.getAttribute('data-status');
        
        const matchesSearch = searchTerm === '' || name.includes(searchTerm);
        const matchesSeverity = severityFilter === '' || severity === severityFilter;
        const matchesDataSource = dataSourceFilter === '' || dataSource === dataSourceFilter;
        const matchesStatus = statusFilter === '' || status === statusFilter;
        
        if (matchesSearch && matchesSeverity && matchesDataSource && matchesStatus) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Sort alert rules based on selected sort option
 */
function sortAlertRules() {
    const sortOption = document.getElementById('sort-rules').value;
    const table = document.getElementById('alert-rules-table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        switch (sortOption) {
            case 'name-asc':
                return a.cells[0].textContent.localeCompare(b.cells[0].textContent);
            case 'name-desc':
                return b.cells[0].textContent.localeCompare(a.cells[0].textContent);
            case 'severity-asc':
                return getSeverityValue(a.getAttribute('data-severity')) - getSeverityValue(b.getAttribute('data-severity'));
            case 'severity-desc':
                return getSeverityValue(b.getAttribute('data-severity')) - getSeverityValue(a.getAttribute('data-severity'));
            case 'created-desc':
                // Assuming the ID is numeric and sequential
                return b.getAttribute('data-rule-id') - a.getAttribute('data-rule-id');
            case 'created-asc':
                return a.getAttribute('data-rule-id') - b.getAttribute('data-rule-id');
            default:
                return 0;
        }
    });
    
    // Reorder rows
    rows.forEach(row => {
        tbody.appendChild(row);
    });
}

/**
 * Get numeric value for severity (for sorting)
 * @param {string} severity - Severity text
 * @returns {number} Numeric value
 */
function getSeverityValue(severity) {
    switch (severity) {
        case 'info': return 1;
        case 'warning': return 2;
        case 'error': return 3;
        case 'critical': return 4;
        default: return 0;
    }
}

/**
 * Acknowledge an alert
 * @param {string} alertId - The ID of the alert to acknowledge
 * @param {Function} callback - Optional callback after success
 */
function acknowledgeAlert(alertId, callback) {
    fetch(`/api/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to acknowledge alert');
        return response.json();
    })
    .then(data => {
        showNotification('Alert acknowledged', 'success');
        
        // Update row if it exists
        const row = document.querySelector(`tr[data-alert-id="${alertId}"]`);
        if (row) {
            row.setAttribute('data-status', 'acknowledged');
            
            // Update status badge
            const statusCell = row.cells[row.cells.length - 2];
            if (statusCell) {
                statusCell.innerHTML = '<span class="badge badge-warning">Acknowledged</span>';
            }
            
            // Update actions
            const actionsCell = row.cells[row.cells.length - 1];
            if (actionsCell) {
                const ackBtn = actionsCell.querySelector('button:first-child');
                if (ackBtn && ackBtn.querySelector('i.fa-check')) {
                    ackBtn.style.display = 'none';
                }
            }
        }
        
        if (typeof callback === 'function') {
            callback();
        }
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Error acknowledging alert', 'error');
    });
}

/**
 * Resolve an alert
 * @param {string} alertId - The ID of the alert to resolve
 * @param {Function} callback - Optional callback after success
 */
function resolveAlert(alertId, callback) {
    fetch(`/api/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to resolve alert');
        return response.json();
    })
    .then(data => {
        showNotification('Alert resolved', 'success');
        
        // Update row if it exists
        const row = document.querySelector(`tr[data-alert-id="${alertId}"]`);
        if (row) {
            row.setAttribute('data-status', 'resolved');
            
            // Update status badge
            const statusCell = row.cells[row.cells.length - 2];
            if (statusCell) {
                statusCell.innerHTML = '<span class="badge badge-success">Resolved</span>';
            }
            
            // Update actions
            const actionsCell = row.cells[row.cells.length - 1];
            if (actionsCell) {
                const actionBtns = actionsCell.querySelectorAll('button');
                actionBtns.forEach(btn => {
                    if (btn.querySelector('i.fa-check') || btn.querySelector('i.fa-check-double')) {
                        btn.style.display = 'none';
                    }
                });
            }
        }
        
        if (typeof callback === 'function') {
            callback();
        }
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Error resolving alert', 'error');
    });
}

/**
 * Filter alert history based on selected filters
 */
function filterAlertHistory() {
    const searchTerm = document.getElementById('alert-search').value.toLowerCase();
    const severityFilter = document.getElementById('filter-alert-severity').value;
    const statusFilter = document.getElementById('filter-alert-status').value;
    const timeFilter = document.getElementById('filter-alert-time').value;
    const sortOption = document.getElementById('sort-alerts').value;
    
    const rows = document.querySelectorAll('#alerts-table tbody tr');
    let filteredCount = 0;
    
    rows.forEach(row => {
        const message = row.cells[3].textContent.toLowerCase();
        const severity = row.getAttribute('data-severity');
        const status = row.getAttribute('data-status');
        const timestamp = new Date(row.getAttribute('data-timestamp'));
        
        // Check time filter
        let matchesTime = true;
        if (timeFilter) {
            const now = new Date();
            switch (timeFilter) {
                case '24h':
                    matchesTime = (now - timestamp) <= 24 * 60 * 60 * 1000;
                    break;
                case '7d':
                    matchesTime = (now - timestamp) <= 7 * 24 * 60 * 60 * 1000;
                    break;
                case '30d':
                    matchesTime = (now - timestamp) <= 30 * 24 * 60 * 60 * 1000;
                    break;
                case 'all':
                    matchesTime = true;
                    break;
            }
        }
        
        const matchesSearch = searchTerm === '' || message.includes(searchTerm);
        const matchesSeverity = severityFilter === '' || severity === severityFilter;
        const matchesStatus = statusFilter === '' || status === statusFilter;
        
        if (matchesSearch && matchesSeverity && matchesStatus && matchesTime) {
            row.style.display = '';
            filteredCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update filtered count
    updateFilteredAlertCount(filteredCount);
    
    // Sort the visible rows
    sortAlerts(sortOption);
}

/**
 * Sort alert history rows
 * @param {string} sortOption - Sort option
 */
function sortAlerts(sortOption) {
    const table = document.getElementById('alerts-table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr:not([style*="display: none"])'));
    
    rows.sort((a, b) => {
        const aTimestamp = new Date(a.getAttribute('data-timestamp'));
        const bTimestamp = new Date(b.getAttribute('data-timestamp'));
        const aSeverity = getSeverityValue(a.getAttribute('data-severity'));
        const bSeverity = getSeverityValue(b.getAttribute('data-severity'));
        
        switch (sortOption) {
            case 'time-desc':
                return bTimestamp - aTimestamp;
            case 'time-asc':
                return aTimestamp - bTimestamp;
            case 'severity-desc':
                return bSeverity - aSeverity;
            case 'severity-asc':
                return aSeverity - bSeverity;
            default:
                return 0;
        }
    });
    
    // Reorder rows
    rows.forEach(row => {
        tbody.appendChild(row);
    });
}

/**
 * Update the count of filtered alerts
 * @param {number} count - Count of filtered alerts
 */
function updateFilteredAlertCount(count) {
    const countEl = document.getElementById('filtered-alert-count');
    if (countEl) {
        if (count === undefined) {
            // Count visible rows
            const visibleRows = document.querySelectorAll('#alerts-table tbody tr:not([style*="display: none"])');
            count = visibleRows.length;
        }
        countEl.textContent = count;
    }
}

/**
 * Toggle select all alerts
 * @param {boolean} checked - Whether to select or deselect all
 */
function toggleSelectAllAlerts(checked) {
    const checkboxes = document.querySelectorAll('.alert-select');
    checkboxes.forEach(checkbox => {
        checkbox.checked = checked;
    });
    
    updateBulkActionButtons();
}

/**
 * Update the state of bulk action buttons
 */
function updateBulkActionButtons() {
    const selectedAlerts = getSelectedAlerts();
    const bulkAcknowledgeBtn = document.getElementById('bulk-acknowledge-btn');
    const bulkResolveBtn = document.getElementById('bulk-resolve-btn');
    
    if (bulkAcknowledgeBtn) {
        bulkAcknowledgeBtn.disabled = selectedAlerts.length === 0;
    }
    
    if (bulkResolveBtn) {
        bulkResolveBtn.disabled = selectedAlerts.length === 0;
    }
}

/**
 * Bulk acknowledge selected alerts
 */
function bulkAcknowledgeAlerts() {
    const selectedAlerts = getSelectedAlerts();
    if (selectedAlerts.length === 0) return;
    
    fetch('/api/alerts/bulk_acknowledge', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            alert_ids: selectedAlerts
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to acknowledge alerts');
        return response.json();
    })
    .then(data => {
        showNotification(`${data.acknowledged_count} alerts acknowledged`, 'success');
        
        // Update UI
        selectedAlerts.forEach(alertId => {
            const row = document.querySelector(`tr[data-alert-id="${alertId}"]`);
            if (row) {
                row.setAttribute('data-status', 'acknowledged');
                
                // Update status badge
                const statusCell = row.cells[row.cells.length - 2];
                if (statusCell) {
                    statusCell.innerHTML = '<span class="badge badge-warning">Acknowledged</span>';
                }
                
                // Update actions
                const actionsCell = row.cells[row.cells.length - 1];
                if (actionsCell) {
                    const ackBtn = actionsCell.querySelector('button:first-child');
                    if (ackBtn && ackBtn.querySelector('i.fa-check')) {
                        ackBtn.style.display = 'none';
                    }
                }
            }
        });
        
        // Reset checkboxes
        document.getElementById('select-all-alerts').checked = false;
        document.querySelectorAll('.alert-select').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        updateBulkActionButtons();
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Error acknowledging alerts', 'error');
    });
}

/**
 * Bulk resolve selected alerts
 */
function bulkResolveAlerts() {
    const selectedAlerts = getSelectedAlerts();
    if (selectedAlerts.length === 0) return;
    
    fetch('/api/alerts/bulk_resolve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            alert_ids: selectedAlerts
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to resolve alerts');
        return response.json();
    })
    .then(data => {
        showNotification(`${data.resolved_count} alerts resolved`, 'success');
        
        // Update UI
        selectedAlerts.forEach(alertId => {
            const row = document.querySelector(`tr[data-alert-id="${alertId}"]`);
            if (row) {
                row.setAttribute('data-status', 'resolved');
                
                // Update status badge
                const statusCell = row.cells[row.cells.length - 2];
                if (statusCell) {
                    statusCell.innerHTML = '<span class="badge badge-success">Resolved</span>';
                }
                
                // Update actions
                const actionsCell = row.cells[row.cells.length - 1];
                if (actionsCell) {
                    const actionBtns = actionsCell.querySelectorAll('button');
                    actionBtns.forEach(btn => {
                        if (btn.querySelector('i.fa-check') || btn.querySelector('i.fa-check-double')) {
                            btn.style.display = 'none';
                        }
                    });
                }
            }
        });
        
        // Reset checkboxes
        document.getElementById('select-all-alerts').checked = false;
        document.querySelectorAll('.alert-select').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        updateBulkActionButtons();
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Error resolving alerts', 'error');
    });
}

/**
 * Get IDs of selected alerts
 * @returns {Array} Array of selected alert IDs
 */
function getSelectedAlerts() {
    const checkboxes = document.querySelectorAll('.alert-select:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.value);
}

/**
 * Check for new alerts
 */
function checkForNewAlerts() {
    const lastChecked = localStorage.getItem('lastAlertCheck') || new Date(0).toISOString();
    
    fetch(`/api/alerts/check?since=${encodeURIComponent(lastChecked)}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to check for new alerts');
            return response.json();
        })
        .then(data => {
            localStorage.setItem('lastAlertCheck', new Date().toISOString());
            
            if (data.alerts && data.alerts.length > 0) {
                showNewAlertsNotification(data.alerts);
                loadNewAlerts(data.alerts);
            }
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Show notification for new alerts
 * @param {Array} alerts - Array of new alerts
 */
function showNewAlertsNotification(alerts) {
    if (!alerts || alerts.length === 0) return;
    
    const notificationSettings = JSON.parse(localStorage.getItem('alertNotificationSettings') || '{}');
    
    // Check if browser notifications are enabled
    if (notificationSettings.browser && Notification.permission === 'granted') {
        const criticalAlerts = alerts.filter(a => a.severity === 'critical').length;
        const errorAlerts = alerts.filter(a => a.severity === 'error').length;
        const warningAlerts = alerts.filter(a => a.severity === 'warning').length;
        const infoAlerts = alerts.filter(a => a.severity === 'info').length;
        
        let title = `${alerts.length} New Alert${alerts.length > 1 ? 's' : ''}`;
        let message = '';
        
        if (criticalAlerts > 0) {
            message += `${criticalAlerts} Critical, `;
        }
        if (errorAlerts > 0) {
            message += `${errorAlerts} Error, `;
        }
        if (warningAlerts > 0) {
            message += `${warningAlerts} Warning, `;
        }
        if (infoAlerts > 0) {
            message += `${infoAlerts} Info, `;
        }
        
        message = message.slice(0, -2); // Remove trailing comma and space
        
        const notification = new Notification(title, {
            body: message,
            icon: '/static/img/logo-icon.png'
        });
        
        notification.onclick = function() {
            window.focus();
            this.close();
        };
    }
    
    // Show in-app notification
    const message = `${alerts.length} new alert${alerts.length > 1 ? 's' : ''} received`;
    showNotification(message, 'info');
}

/**
 * Load new alerts into the alerts table
 * @param {Array} alerts - Array of new alerts
 */
function loadNewAlerts(alerts) {
    if (!alerts || alerts.length === 0) return;
    
    const alertsTable = document.getElementById('alerts-table');
    if (!alertsTable) return;
    
    const tableBody = alertsTable.querySelector('tbody');
    if (!tableBody) return;
    
    alerts.forEach(alert => {
        // Check if alert already exists
        if (document.querySelector(`tr[data-alert-id="${alert.id}"]`)) {
            return;
        }
        
        // Create new row
        const row = document.createElement('tr');
        row.setAttribute('data-alert-id', alert.id);
        row.setAttribute('data-severity', alert.severity);
        row.setAttribute('data-status', 'active');
        row.setAttribute('data-timestamp', alert.timestamp);
        
        // Create checkbox cell
        const checkboxCell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'alert-select';
        checkbox.value = alert.id;
        checkbox.onchange = updateBulkActionButtons;
        checkboxCell.appendChild(checkbox);
        
        // Create time cell
        const timeCell = document.createElement('td');
        timeCell.textContent = formatTimestamp(alert.timestamp);
        
        // Create rule cell
        const ruleCell = document.createElement('td');
        ruleCell.textContent = alert.rule_name || 'System';
        
        // Create message cell
        const messageCell = document.createElement('td');
        messageCell.textContent = alert.message;
        
        // Create severity cell
        const severityCell = document.createElement('td');
        severityCell.innerHTML = `<span class="badge badge-${alert.severity}">${alert.severity}</span>`;
        
        // Create status cell
        const statusCell = document.createElement('td');
        statusCell.innerHTML = '<span class="badge badge-error">Active</span>';
        
        // Create actions cell
        const actionsCell = document.createElement('td');
        actionsCell.innerHTML = `
            <div class="btn-group">
                <button class="btn btn-sm btn-secondary" onclick="acknowledgeAlert(${alert.id})">
                    <i class="fas fa-check"></i>
                </button>
                <button class="btn btn-sm btn-success" onclick="resolveAlert(${alert.id})">
                    <i class="fas fa-check-double"></i>
                </button>
                <button class="btn btn-sm btn-info" onclick="showAlertDetails(${alert.id})">
                    <i class="fas fa-info-circle"></i>
                </button>
            </div>
        `;
        
        // Add cells to row
        row.appendChild(checkboxCell);
        row.appendChild(timeCell);
        row.appendChild(ruleCell);
        row.appendChild(messageCell);
        row.appendChild(severityCell);
        row.appendChild(statusCell);
        row.appendChild(actionsCell);
        
        // Add row to table
        tableBody.insertBefore(row, tableBody.firstChild);
    });
    
    // Update stats if they exist
    updateAlertCounts();
}

/**
 * Update alert counts in UI
 */
function updateAlertCounts() {
    const alertsTable = document.getElementById('alerts-table');
    if (!alertsTable) return;
    
    const rows = alertsTable.querySelectorAll('tbody tr');
    
    const totalCount = rows.length;
    const activeCount = Array.from(rows).filter(row => row.getAttribute('data-status') === 'active').length;
    const acknowledgedCount = Array.from(rows).filter(row => row.getAttribute('data-status') === 'acknowledged').length;
    const resolvedCount = Array.from(rows).filter(row => row.getAttribute('data-status') === 'resolved').length;
    
    const criticalCount = Array.from(rows).filter(row => row.getAttribute('data-severity') === 'critical').length;
    const errorCount = Array.from(rows).filter(row => row.getAttribute('data-severity') === 'error').length;
    const warningCount = Array.from(rows).filter(row => row.getAttribute('data-severity') === 'warning').length;
    const infoCount = Array.from(rows).filter(row => row.getAttribute('data-severity') === 'info').length;
    
    // Update stat elements if they exist
    const elements = {
        'total-alerts-count': totalCount,
        'active-alerts-count': activeCount,
        'acknowledged-alerts-count': acknowledgedCount,
        'resolved-alerts-count': resolvedCount,
        'critical-count': criticalCount,
        'error-count': errorCount,
        'warning-count': warningCount,
        'info-count': infoCount,
        'filtered-alert-count': totalCount
    };
    
    Object.entries(elements).forEach(([id, count]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = count;
    });
    
    // Update severity bars if they exist
    const updateSeverityBar = (selector, count) => {
        const bar = document.querySelector(selector);
        if (bar && totalCount > 0) {
            const percentage = (count / totalCount * 100).toFixed(1);
            bar.style.width = `${percentage}%`;
        }
    };
    
    updateSeverityBar('.critical-bar', criticalCount);
    updateSeverityBar('.error-bar', errorCount);
    updateSeverityBar('.warning-bar', warningCount);
    updateSeverityBar('.info-bar', infoCount);
}

/**
 * Request notification permission
 */
function requestNotificationPermission() {
    Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') {
            // Store this preference
            const settings = JSON.parse(localStorage.getItem('alertNotificationSettings') || '{}');
            settings.browser = true;
            localStorage.setItem('alertNotificationSettings', JSON.stringify(settings));
            
            showNotification('Browser notifications enabled', 'success');
        }
    });
}

/**
 * Update notification settings
 */
function updateNotificationSettings() {
    const browserNotifications = document.getElementById('browser-notifications').checked;
    const desktopNotifications = document.getElementById('desktop-notifications').checked;
    const emailNotifications = document.getElementById('email-notifications').checked;
    
    const settings = {
        browser: browserNotifications,
        desktop: desktopNotifications,
        email: emailNotifications
    };
    
    // Save to local storage
    localStorage.setItem('alertNotificationSettings', JSON.stringify(settings));
    
    // Save to server
    fetch('/api/alerts/notification_settings', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(settings)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to update notification settings');
        return response.json();
    })
    .then(data => {
        showNotification('Notification settings updated', 'success');
    })
    .catch(error => {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        showNotification('Error updating notification settings', 'error');
    });
    
    // Request browser notification permission if enabled
    if (browserNotifications && Notification.permission !== 'granted') {
        requestNotificationPermission();
    }
}

/**
 * Set up automatic refresh for alerts
 */
function setupAlertRefresh() {
    setInterval(refreshAlerts, 60000); // Refresh every minute
}

/**
 * Refresh alerts from server
 */
function refreshAlerts() {
    fetch('/api/alerts')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch alerts');
            return response.json();
        })
        .then(data => {
            if (data.alerts) {
                loadNewAlerts(data.alerts);
                filterAlertHistory(); // Re-apply filters
            }
        })
        .catch(error => {
            errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        });
}

/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted timestamp
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Create event listeners for alert functionality
 */
function createAlertEventListeners() {
    // Filter alert rules when filter controls change
    document.querySelectorAll('#filter-severity, #filter-data-source, #filter-status').forEach(el => {
        el.addEventListener('change', filterAlertRules);
    });
    
    // Sort alert rules when sort control changes
    const sortRulesSelect = document.getElementById('sort-rules');
    if (sortRulesSelect) {
        sortRulesSelect.addEventListener('change', sortAlertRules);
    }
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

/**
 * Show notification to the user
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, info, warning)
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Get icon based on type
    let icon = '';
    switch (type) {
        case 'success':
            icon = 'fa-check-circle';
            break;
        case 'error':
            icon = 'fa-exclamation-circle';
            break;
        case 'warning':
            icon = 'fa-exclamation-triangle';
            break;
        case 'info':
        default:
            icon = 'fa-info-circle';
            break;
    }
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas ${icon}"></i>
        </div>
        <div class="notification-content">${message}</div>
        <button class="notification-close">&times;</button>
    `;
    
    container.appendChild(notification);
    
    // Add close button functionality
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.classList.add('notification-hide');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
}

/**
 * Create notification container if it doesn't exist
 * @returns {HTMLElement} The notification container
 */
function createNotificationContainer() {
    let container = document.getElementById('notification-container');
    
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }
    
    return container;
}

// Export functions for use in other modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initAlertRules,
        initAlertHistory,
        initAlertDashboard,
        showCreateAlertModal,
        updateConditionFields,
        addConditionRow,
        saveAlertRule,
        updateAlertRuleStatus,
        filterAlertRules,
        sortAlertRules,
        acknowledgeAlert,
        resolveAlert,
        filterAlertHistory,
        bulkAcknowledgeAlerts,
        bulkResolveAlerts,
        getSelectedAlerts,
        checkForNewAlerts,
        updateNotificationSettings,
        showNotification
    };
}