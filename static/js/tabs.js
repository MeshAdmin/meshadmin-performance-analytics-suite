/**
 * Tab System and Flyout Modal Management
 */

class TabSystem {
    constructor() {
        this.activeTab = 'system-status';
        this.init();
    }

    init() {
        this.bindTabEvents();
        this.bindFlyoutEvents();
        this.loadActiveTab();
        this.setupKeyboardNavigation();
    }

    bindTabEvents() {
        // Tab navigation click events
        document.addEventListener('click', (e) => {
            if (e.target.matches('.tab-nav-link') || e.target.closest('.tab-nav-link')) {
                e.preventDefault();
                const tabLink = e.target.closest('.tab-nav-link');
                const tabId = tabLink.getAttribute('data-tab');
                this.switchTab(tabId);
            }
        });
    }

    bindFlyoutEvents() {
        // Flyout trigger events
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-flyout]') || e.target.closest('[data-flyout]')) {
                e.preventDefault();
                const trigger = e.target.closest('[data-flyout]');
                const flyoutId = trigger.getAttribute('data-flyout');
                this.openFlyout(flyoutId);
            }
        });

        // Close flyout events
        document.addEventListener('click', (e) => {
            if (e.target.matches('.flyout-close') || e.target.matches('.flyout-backdrop')) {
                this.closeFlyout();
            }
        });

        // ESC key to close flyout
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFlyout();
            }
        });
    }

    setupKeyboardNavigation() {
        // Keyboard navigation for tabs
        document.addEventListener('keydown', (e) => {
            if (e.target.matches('.tab-nav-link')) {
                const tabs = [...document.querySelectorAll('.tab-nav-link')];
                const currentIndex = tabs.indexOf(e.target);
                
                let newIndex = -1;
                if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
                } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
                } else if (e.key === 'Home') {
                    newIndex = 0;
                } else if (e.key === 'End') {
                    newIndex = tabs.length - 1;
                }
                
                if (newIndex !== -1) {
                    e.preventDefault();
                    tabs[newIndex].focus();
                    const tabId = tabs[newIndex].getAttribute('data-tab');
                    this.switchTab(tabId);
                }
            }
        });
    }

    switchTab(tabId) {
        // Remove active class from all tabs and panes
        document.querySelectorAll('.tab-nav-link').forEach(link => {
            link.classList.remove('active');
            link.setAttribute('aria-selected', 'false');
        });
        
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });

        // Add active class to selected tab and pane
        const activeTabLink = document.querySelector(`[data-tab="${tabId}"]`);
        const activeTabPane = document.getElementById(tabId);
        
        if (activeTabLink && activeTabPane) {
            activeTabLink.classList.add('active');
            activeTabLink.setAttribute('aria-selected', 'true');
            activeTabPane.classList.add('active');
            
            this.activeTab = tabId;
            
            // Trigger tab change event
            this.onTabChange(tabId);
            
            // Update URL hash without triggering navigation
            if (history.replaceState) {
                history.replaceState(null, null, `#${tabId}`);
            }
        }
    }

    loadActiveTab() {
        // Check URL hash for active tab
        const hash = window.location.hash.substring(1);
        if (hash && document.getElementById(hash)) {
            this.switchTab(hash);
        } else {
            // Default to first tab
            const firstTab = document.querySelector('.tab-nav-link');
            if (firstTab) {
                const tabId = firstTab.getAttribute('data-tab');
                this.switchTab(tabId);
            }
        }
    }

    onTabChange(tabId) {
        // Handle specific tab loading logic
        switch(tabId) {
            case 'system-status':
                this.loadSystemStatus();
                break;
            case 'performance-summary':
                this.loadPerformanceCharts();
                break;
            case 'ml-insights':
                this.loadMLInsights();
                break;
            case 'llm-management':
                this.loadLLMManagement();
                break;
        }
        
        // Trigger custom event
        document.dispatchEvent(new CustomEvent('tabChanged', {
            detail: { tabId, activeTab: tabId }
        }));
    }

    loadSystemStatus() {
        // Refresh system status data
        console.log('Loading system status...');
    }

    loadPerformanceCharts() {
        // Refresh performance charts
        console.log('Loading performance charts...');
        if (window.loadCharts) {
            window.loadCharts();
        }
    }

    loadMLInsights() {
        // Load ML insights and correlation analysis
        console.log('Loading ML insights...');
        if (window.triggerCorrelation) {
            // Don't auto-trigger, just ensure charts are loaded
        }
    }

    loadLLMManagement() {
        // Load LLM management interface
        console.log('Loading LLM management...');
    }

    openFlyout(flyoutId) {
        // Create flyout backdrop
        let backdrop = document.querySelector('.flyout-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'flyout-backdrop';
            document.body.appendChild(backdrop);
        }

        // Show backdrop
        setTimeout(() => backdrop.classList.add('show'), 10);

        // Show flyout modal
        const flyout = document.getElementById(flyoutId);
        if (flyout) {
            flyout.classList.add('show');
            document.body.classList.add('flyout-open');
            
            // Focus management
            const firstFocusable = flyout.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 300);
            }

            // Trigger flyout open event
            document.dispatchEvent(new CustomEvent('flyoutOpened', {
                detail: { flyoutId }
            }));
        }
    }

    closeFlyout() {
        // Hide all flyouts
        document.querySelectorAll('.flyout-modal').forEach(flyout => {
            flyout.classList.remove('show');
        });

        // Hide backdrop
        const backdrop = document.querySelector('.flyout-backdrop');
        if (backdrop) {
            backdrop.classList.remove('show');
        }

        // Remove body class
        document.body.classList.remove('flyout-open');

        // Trigger flyout close event
        document.dispatchEvent(new CustomEvent('flyoutClosed'));
    }

    // Update tab badge (for notifications, alerts, etc.)
    updateTabBadge(tabId, count, type = 'danger') {
        const tabLink = document.querySelector(`[data-tab="${tabId}"]`);
        if (!tabLink) return;

        let badge = tabLink.querySelector('.tab-badge');
        
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = `tab-badge ${type}`;
                tabLink.appendChild(badge);
            }
            badge.textContent = count > 99 ? '99+' : count.toString();
            badge.className = `tab-badge ${type}`;
        } else if (badge) {
            badge.remove();
        }
    }

    // Refresh current tab content
    refreshCurrentTab() {
        this.onTabChange(this.activeTab);
    }

    // Get current active tab
    getCurrentTab() {
        return this.activeTab;
    }
}

// Flyout Form Handlers
class FlyoutForms {
    constructor() {
        this.init();
    }

    init() {
        this.bindFormEvents();
    }

    bindFormEvents() {
        // LLM Configuration form
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#llm-config-form')) {
                e.preventDefault();
                this.handleLLMConfig(e.target);
            }
        });

        // LLM Upload form
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#llm-upload-form')) {
                e.preventDefault();
                this.handleLLMUpload(e.target);
            }
        });

        // File input changes
        document.addEventListener('change', (e) => {
            if (e.target.matches('#llm-file')) {
                this.handleFileSelection(e.target);
            }
        });
    }

    handleLLMConfig(form) {
        const formData = new FormData(form);
        const config = Object.fromEntries(formData.entries());
        
        console.log('LLM Configuration:', config);
        
        // Show loading state
        this.showFormLoading(form);
        
        // Simulate API call
        setTimeout(() => {
            this.showFormSuccess(form, 'Configuration saved successfully!');
            setTimeout(() => tabSystem.closeFlyout(), 1500);
        }, 1000);
    }

    handleLLMUpload(form) {
        const formData = new FormData(form);
        const file = formData.get('llm-file');
        
        if (!file || file.size === 0) {
            this.showFormError(form, 'Please select a file to upload.');
            return;
        }
        
        console.log('LLM Upload:', file.name, file.size);
        
        // Show loading state
        this.showFormLoading(form);
        
        // Simulate upload with progress
        this.simulateUploadProgress(form);
    }

    handleFileSelection(input) {
        const file = input.files[0];
        const preview = document.getElementById('file-preview');
        
        if (preview) {
            if (file) {
                preview.innerHTML = `
                    <div class="alert alert-info">
                        <strong>Selected:</strong> ${file.name} (${this.formatFileSize(file.size)})
                    </div>
                `;
            } else {
                preview.innerHTML = '';
            }
        }
    }

    showFormLoading(form) {
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
    }

    showFormSuccess(form, message) {
        this.clearFormMessages(form);
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
        form.insertBefore(alert, form.firstChild);
        
        this.resetFormButton(form);
    }

    showFormError(form, message) {
        this.clearFormMessages(form);
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger';
        alert.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
        form.insertBefore(alert, form.firstChild);
        
        this.resetFormButton(form);
    }

    clearFormMessages(form) {
        form.querySelectorAll('.alert').forEach(alert => alert.remove());
    }

    resetFormButton(form) {
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Submit';
        }
    }

    simulateUploadProgress(form) {
        const progressContainer = document.getElementById('upload-progress');
        if (!progressContainer) return;
        
        progressContainer.style.display = 'block';
        const progressBar = progressContainer.querySelector('.progress-bar');
        let progress = 0;
        
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress > 100) progress = 100;
            
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
            
            if (progress >= 100) {
                clearInterval(interval);
                setTimeout(() => {
                    this.showFormSuccess(form, 'File uploaded successfully!');
                    progressContainer.style.display = 'none';
                    setTimeout(() => tabSystem.closeFlyout(), 1500);
                }, 500);
            }
        }, 200);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.tabSystem = new TabSystem();
    window.flyoutForms = new FlyoutForms();
    
    // Make globally available
    window.TabSystem = TabSystem;
    window.FlyoutForms = FlyoutForms;
});

// Handle hash changes
window.addEventListener('hashchange', () => {
    if (window.tabSystem) {
        window.tabSystem.loadActiveTab();
    }
});

