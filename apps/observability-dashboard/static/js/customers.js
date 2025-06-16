/**
 * Initialize the customers management functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initModals();
    setupMonitoringFormListeners();
    
    // Add event listeners for organization filtering if applicable
    const orgSearch = document.getElementById('org-search');
    if (orgSearch) {
        orgSearch.addEventListener('input', filterOrganizations);
    }
    
    // Add event listeners for site filtering if applicable
    const siteSearch = document.getElementById('site-search');
    if (siteSearch) {
        siteSearch.addEventListener('input', filterSites);
    }
    
    // Add event listeners for device filtering if applicable
    const deviceSearch = document.getElementById('device-search');
    if (deviceSearch) {
        deviceSearch.addEventListener('input', filterDevices);
    }
});

/**
 * Initialize modal behavior
 */
function initModals() {
    // Close modals when clicking outside the content
    window.addEventListener('click', function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(function(modal) {
            if (event.target === modal) {
                closeModal(modal.id);
            }
        });
    });
    
    // Close modals with Escape key
    window.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.active');
            if (openModals.length > 0) {
                closeModal(openModals[0].id);
            }
        }
    });
}

/**
 * Setup listeners for the monitoring configuration form
 */
function setupMonitoringFormListeners() {
    const monitorNetflow = document.getElementById('monitor-netflow');
    const monitorSflow = document.getElementById('monitor-sflow');
    const monitorOtel = document.getElementById('monitor-otel');
    
    if (monitorNetflow) {
        monitorNetflow.addEventListener('change', function() {
            document.getElementById('netflow-settings').style.display = 
                this.checked ? 'block' : 'none';
        });
    }
    
    if (monitorSflow) {
        monitorSflow.addEventListener('change', function() {
            document.getElementById('sflow-settings').style.display = 
                this.checked ? 'block' : 'none';
        });
    }
    
    if (monitorOtel) {
        monitorOtel.addEventListener('change', function() {
            document.getElementById('otel-settings').style.display = 
                this.checked ? 'block' : 'none';
        });
    }
}

/**
 * Filter organizations based on search input and filters
 */
function filterOrganizations() {
    const searchText = document.getElementById('org-search').value.toLowerCase();
    const mspOnly = document.getElementById('filter-msp')?.checked || false;
    
    // Check if we're in card view or table view
    const orgCards = document.querySelectorAll('.card[data-org-id]');
    const orgRows = document.querySelectorAll('tr[data-org-id]');
    
    if (orgCards.length > 0) {
        // Card view
        orgCards.forEach(function(card) {
            const name = card.querySelector('.card-title').textContent.toLowerCase();
            const isMsp = card.getAttribute('data-is-msp') === 'true';
            
            const matchesSearch = name.includes(searchText);
            const matchesMspFilter = !mspOnly || isMsp;
            
            card.style.display = (matchesSearch && matchesMspFilter) ? 'block' : 'none';
        });
    } else if (orgRows.length > 0) {
        // Table view
        orgRows.forEach(function(row) {
            const name = row.cells[0].textContent.toLowerCase();
            const isMsp = row.getAttribute('data-is-msp') === 'true';
            
            const matchesSearch = name.includes(searchText);
            const matchesMspFilter = !mspOnly || isMsp;
            
            row.style.display = (matchesSearch && matchesMspFilter) ? 'table-row' : 'none';
        });
    }
}

/**
 * Sort organizations based on selected sort option
 */
function sortOrganizations() {
    const sortValue = document.getElementById('sort-orgs').value;
    const [property, direction] = sortValue.split('-');
    
    const table = document.getElementById('organizations-table');
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    
    rows.sort(function(a, b) {
        let valueA, valueB;
        
        if (property === 'name') {
            valueA = a.cells[0].textContent.trim();
            valueB = b.cells[0].textContent.trim();
        } else if (property === 'created') {
            valueA = new Date(a.cells[4].getAttribute('title'));
            valueB = new Date(b.cells[4].getAttribute('title'));
        }
        
        if (direction === 'asc') {
            return valueA > valueB ? 1 : -1;
        } else {
            return valueA < valueB ? 1 : -1;
        }
    });
    
    // Remove existing rows
    rows.forEach(row => row.parentNode.removeChild(row));
    
    // Add sorted rows
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Filter sites based on search input and filters
 */
function filterSites() {
    const searchText = document.getElementById('site-search').value.toLowerCase();
    const orgFilter = document.getElementById('filter-organization')?.value || '';
    
    // Check if we're in card view or table view
    const siteCards = document.querySelectorAll('.card[data-site-id]');
    const siteRows = document.querySelectorAll('tr[data-site-id]');
    
    if (siteCards.length > 0) {
        // Card view
        siteCards.forEach(function(card) {
            const name = card.querySelector('.card-title').textContent.toLowerCase();
            const orgId = card.getAttribute('data-org-id');
            
            const matchesSearch = name.includes(searchText);
            const matchesOrgFilter = !orgFilter || orgId === orgFilter;
            
            card.style.display = (matchesSearch && matchesOrgFilter) ? 'block' : 'none';
        });
    } else if (siteRows.length > 0) {
        // Table view
        siteRows.forEach(function(row) {
            const name = row.cells[0].textContent.toLowerCase();
            const orgId = row.getAttribute('data-org-id');
            
            const matchesSearch = name.includes(searchText);
            const matchesOrgFilter = !orgFilter || orgId === orgFilter;
            
            row.style.display = (matchesSearch && matchesOrgFilter) ? 'table-row' : 'none';
        });
    }
}

/**
 * Sort sites based on selected sort option
 */
function sortSites() {
    const sortValue = document.getElementById('sort-sites').value;
    const [property, direction] = sortValue.split('-');
    
    const table = document.getElementById('sites-table');
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    
    rows.sort(function(a, b) {
        let valueA, valueB;
        
        if (property === 'name') {
            valueA = a.cells[0].textContent.trim();
            valueB = b.cells[0].textContent.trim();
        } else if (property === 'created') {
            valueA = new Date(a.cells[4].getAttribute('title'));
            valueB = new Date(b.cells[4].getAttribute('title'));
        }
        
        if (direction === 'asc') {
            return valueA > valueB ? 1 : -1;
        } else {
            return valueA < valueB ? 1 : -1;
        }
    });
    
    // Remove existing rows
    rows.forEach(row => row.parentNode.removeChild(row));
    
    // Add sorted rows
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Filter devices based on search input
 */
function filterDevices() {
    const searchText = document.getElementById('device-search').value.toLowerCase();
    
    const deviceRows = document.querySelectorAll('tr[data-device-id]');
    
    deviceRows.forEach(function(row) {
        const name = row.cells[0].textContent.toLowerCase();
        const ip = row.cells[1].textContent.toLowerCase();
        const type = row.cells[2].textContent.toLowerCase();
        
        const matchesSearch = name.includes(searchText) || 
                              ip.includes(searchText) || 
                              type.includes(searchText);
        
        row.style.display = matchesSearch ? 'table-row' : 'none';
    });
}

/**
 * Filter device activity based on selected activity type
 */
function filterDeviceActivity() {
    const activityType = document.getElementById('activity-type').value;
    
    // Implementation depends on the structure of the activity data
    console.log(`Filtering activity to type: ${activityType}`);
    
    // For now this is a placeholder as we don't have activity data yet
}

/**
 * Show modal for creating a new organization
 */
function showCreateOrganizationModal() {
    // Reset the form
    document.getElementById('organization-form').reset();
    document.getElementById('org-id').value = '';
    document.getElementById('modal-title').textContent = 'Create Organization';
    document.getElementById('save-org-btn').textContent = 'Create';
    
    // Show the modal
    showModal('organization-modal');
}

/**
 * Show modal for editing an existing organization
 * @param {number} orgId - Organization ID
 */
function editOrganization(orgId) {
    // Fetch organization data
    fetch(`/api/organizations/${orgId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch organization data');
            }
            return response.json();
        })
        .then(organization => {
            // Populate the form
            document.getElementById('org-id').value = organization.id;
            document.getElementById('org-name').value = organization.name;
            document.getElementById('org-description').value = organization.description || '';
            document.getElementById('org-is-msp').checked = organization.is_msp;
            
            // Update the modal title and button
            document.getElementById('modal-title').textContent = 'Edit Organization';
            document.getElementById('save-org-btn').textContent = 'Save Changes';
            
            // Show the modal
            showModal('organization-modal');
        })
        .catch(error => {
            showNotification(error.message, 'error');
        });
}

/**
 * Save organization (create or update)
 */
function saveOrganization() {
    const orgId = document.getElementById('org-id').value;
    const orgName = document.getElementById('org-name').value;
    const orgDescription = document.getElementById('org-description').value;
    const orgIsMsp = document.getElementById('org-is-msp').checked;
    
    // Validate form
    if (!orgName) {
        showNotification('Organization name is required', 'error');
        return;
    }
    
    const orgData = {
        name: orgName,
        description: orgDescription,
        is_msp: orgIsMsp
    };
    
    let url = '/api/organizations';
    let method = 'POST';
    
    if (orgId) {
        url = `/api/organizations/${orgId}`;
        method = 'PUT';
    }
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(orgData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save organization');
        }
        return response.json();
    })
    .then(data => {
        closeModal('organization-modal');
        showNotification(`Organization ${orgId ? 'updated' : 'created'} successfully`, 'success');
        
        // Reload the page to show the new/updated organization
        setTimeout(() => window.location.reload(), 1000);
    })
    .catch(error => {
        showNotification(error.message, 'error');
    });
}

/**
 * Show modal for creating a new site
 */
function showCreateSiteModal() {
    // Reset the form
    document.getElementById('site-form').reset();
    document.getElementById('site-id').value = '';
    document.getElementById('site-modal-title').textContent = 'Add Site';
    document.getElementById('save-site-btn').textContent = 'Create';
    
    // Show the modal
    showModal('site-modal');
}

/**
 * Show modal for editing an existing site
 * @param {number} siteId - Site ID
 */
function editSite(siteId) {
    // Fetch site data
    fetch(`/api/sites/${siteId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch site data');
            }
            return response.json();
        })
        .then(site => {
            // Populate the form
            document.getElementById('site-id').value = site.id;
            document.getElementById('site-name').value = site.name;
            document.getElementById('site-description').value = site.description || '';
            document.getElementById('site-address').value = site.address || '';
            document.getElementById('site-contact').value = site.contact_info || '';
            
            // Set organization if the select exists
            const orgSelect = document.getElementById('site-organization');
            if (orgSelect) {
                orgSelect.value = site.organization_id;
            } else {
                // Hidden field for when we're in organization detail view
                document.getElementById('site-organization-id').value = site.organization_id;
            }
            
            // Update the modal title and button
            document.getElementById('site-modal-title').textContent = 'Edit Site';
            document.getElementById('save-site-btn').textContent = 'Save Changes';
            
            // Show the modal
            showModal('site-modal');
        })
        .catch(error => {
            showNotification(error.message, 'error');
        });
}

/**
 * Save site (create or update)
 */
function saveSite() {
    const siteId = document.getElementById('site-id').value;
    const siteName = document.getElementById('site-name').value;
    const siteDescription = document.getElementById('site-description').value;
    const siteAddress = document.getElementById('site-address').value;
    const siteContact = document.getElementById('site-contact').value;
    
    // Get organization ID either from select or hidden field
    let organizationId;
    const orgSelect = document.getElementById('site-organization');
    if (orgSelect) {
        organizationId = orgSelect.value;
    } else {
        organizationId = document.getElementById('site-organization-id').value;
    }
    
    // Validate form
    if (!siteName) {
        showNotification('Site name is required', 'error');
        return;
    }
    
    if (!organizationId) {
        showNotification('Organization is required', 'error');
        return;
    }
    
    const siteData = {
        name: siteName,
        description: siteDescription,
        address: siteAddress,
        contact_info: siteContact,
        organization_id: organizationId
    };
    
    let url = '/api/sites';
    let method = 'POST';
    
    if (siteId) {
        url = `/api/sites/${siteId}`;
        method = 'PUT';
    }
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(siteData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save site');
        }
        return response.json();
    })
    .then(data => {
        closeModal('site-modal');
        showNotification(`Site ${siteId ? 'updated' : 'created'} successfully`, 'success');
        
        // Reload the page to show the new/updated site
        setTimeout(() => window.location.reload(), 1000);
    })
    .catch(error => {
        showNotification(error.message, 'error');
    });
}

/**
 * Show modal for creating a new device
 */
function showCreateDeviceModal() {
    // Reset the form
    document.getElementById('device-form').reset();
    document.getElementById('device-id').value = '';
    document.getElementById('device-modal-title').textContent = 'Add Device';
    document.getElementById('save-device-btn').textContent = 'Create';
    
    // Show the modal
    showModal('device-modal');
}

/**
 * Show modal for editing an existing device
 * @param {number} deviceId - Device ID
 */
function editDevice(deviceId) {
    // Fetch device data
    fetch(`/api/devices/${deviceId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch device data');
            }
            return response.json();
        })
        .then(device => {
            // Populate the form
            document.getElementById('device-id').value = device.id;
            document.getElementById('device-name').value = device.name;
            document.getElementById('device-ip').value = device.ip_address;
            document.getElementById('device-type').value = device.device_type || '';
            document.getElementById('device-os-type').value = device.os_type || '';
            document.getElementById('device-os-version').value = device.os_version || '';
            document.getElementById('device-description').value = device.description || '';
            document.getElementById('device-site-id').value = device.site_id;
            
            // Update the modal title and button
            document.getElementById('device-modal-title').textContent = 'Edit Device';
            document.getElementById('save-device-btn').textContent = 'Save Changes';
            
            // Show the modal
            showModal('device-modal');
        })
        .catch(error => {
            showNotification(error.message, 'error');
        });
}

/**
 * Save device (create or update)
 */
function saveDevice() {
    const deviceId = document.getElementById('device-id').value;
    const deviceName = document.getElementById('device-name').value;
    const deviceIp = document.getElementById('device-ip').value;
    const deviceType = document.getElementById('device-type').value;
    const deviceOsType = document.getElementById('device-os-type').value;
    const deviceOsVersion = document.getElementById('device-os-version').value;
    const deviceDescription = document.getElementById('device-description').value;
    const siteId = document.getElementById('device-site-id').value;
    
    // Validate form
    if (!deviceName) {
        showNotification('Device name is required', 'error');
        return;
    }
    
    if (!deviceIp) {
        showNotification('IP address is required', 'error');
        return;
    }
    
    if (!siteId) {
        showNotification('Site is required', 'error');
        return;
    }
    
    // Validate IP address format
    const ipPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
    if (!ipPattern.test(deviceIp)) {
        showNotification('Invalid IP address format', 'error');
        return;
    }
    
    const deviceData = {
        name: deviceName,
        ip_address: deviceIp,
        device_type: deviceType,
        os_type: deviceOsType,
        os_version: deviceOsVersion,
        description: deviceDescription,
        site_id: siteId
    };
    
    let url = '/api/devices';
    let method = 'POST';
    
    if (deviceId) {
        url = `/api/devices/${deviceId}`;
        method = 'PUT';
    }
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(deviceData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save device');
        }
        return response.json();
    })
    .then(data => {
        closeModal('device-modal');
        showNotification(`Device ${deviceId ? 'updated' : 'created'} successfully`, 'success');
        
        // Reload the page to show the new/updated device
        setTimeout(() => window.location.reload(), 1000);
    })
    .catch(error => {
        showNotification(error.message, 'error');
    });
}

/**
 * Show modal for configuring device monitoring
 * @param {number} deviceId - Device ID
 */
function configureMonitoring(deviceId) {
    document.getElementById('monitoring-device-id').value = deviceId;
    showModal('monitoring-modal');
}

/**
 * Save monitoring configuration for a device
 */
function saveMonitoringConfig() {
    const deviceId = document.getElementById('monitoring-device-id').value;
    
    const monitoringConfig = {
        device_id: deviceId,
        syslog: document.getElementById('monitor-syslog').checked,
        snmp: document.getElementById('monitor-snmp').checked,
        netflow: document.getElementById('monitor-netflow').checked,
        sflow: document.getElementById('monitor-sflow').checked,
        windows_events: document.getElementById('monitor-windows-events').checked,
        otel: document.getElementById('monitor-otel').checked,
        config: {}
    };
    
    // Add specific configurations if enabled
    if (monitoringConfig.netflow) {
        monitoringConfig.config.netflow = {
            port: document.getElementById('netflow-port').value,
            version: document.getElementById('netflow-version').value
        };
    }
    
    if (monitoringConfig.sflow) {
        monitoringConfig.config.sflow = {
            port: document.getElementById('sflow-port').value
        };
    }
    
    if (monitoringConfig.otel) {
        monitoringConfig.config.otel = {
            port: document.getElementById('otel-port').value,
            protocol: document.getElementById('otel-protocol').value
        };
    }
    
    fetch(`/api/devices/${deviceId}/monitoring`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(monitoringConfig)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save monitoring configuration');
        }
        return response.json();
    })
    .then(data => {
        closeModal('monitoring-modal');
        showNotification('Monitoring configuration saved successfully', 'success');
        
        // Reload the page to show the new configuration
        setTimeout(() => window.location.reload(), 1000);
    })
    .catch(error => {
        showNotification(error.message, 'error');
    });
}

/**
 * Show a modal
 * @param {string} modalId - ID of the modal to show
 */
function showModal(modalId) {
    document.getElementById(modalId).classList.add('active');
    document.body.classList.add('modal-open');
}

/**
 * Close a modal
 * @param {string} modalId - ID of the modal to close
 */
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
    document.body.classList.remove('modal-open');
}

/**
 * Show notification to the user
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, info, warning)
 */
function showNotification(message, type = 'info') {
    const notificationContainer = document.querySelector('.flash-messages') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        ${message}
        <button class="close-alert">&times;</button>
    `;
    
    // Add close button functionality
    notification.querySelector('.close-alert').addEventListener('click', function() {
        notification.remove();
    });
    
    notificationContainer.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Create notification container if it doesn't exist
 * @returns {HTMLElement} The notification container
 */
function createNotificationContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    
    // Insert after header or at the beginning of main-content
    const header = document.querySelector('header');
    const mainContent = document.querySelector('.main-content');
    
    if (header && header.nextElementSibling) {
        mainContent.insertBefore(container, header.nextElementSibling);
    } else if (mainContent) {
        mainContent.prepend(container);
    } else {
        document.body.prepend(container);
    }
    
    return container;
}