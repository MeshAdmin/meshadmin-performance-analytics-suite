/**
 * Notifications.js - Central notification utility for MASH
 * Provides a consistent notification system across all applications
 */

/**
 * Show a notification to the user
 * @param {string} type - Notification type: 'success', 'error', 'warning', 'info'
 * @param {string} msg - The message to display
 * @param {Object} options - Optional configuration
 * @param {number} options.duration - Auto-hide duration in milliseconds (default: 5000)
 * @param {boolean} options.closable - Whether the notification can be manually closed (default: true)
 * @param {string} options.position - Position: 'top-right', 'top-left', 'bottom-right', 'bottom-left' (default: 'bottom-right')
 */
function notify(type, msg, options = {}) {
    // Default options
    const config = {
        duration: 5000,
        closable: true,
        position: 'bottom-right',
        ...options
    };
    
    // Ensure valid type
    const validTypes = ['success', 'error', 'warning', 'info'];
    if (!validTypes.includes(type)) {
        console.warn(`Invalid notification type: ${type}. Using 'info' instead.`);
        type = 'info';
    }
    
    // Get or create notification container
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Get icon for notification type
    const icon = getNotificationIcon(type);
    
    // Build notification HTML
    const closeButton = config.closable ? `<button class="notification-close" aria-label="Close notification">&times;</button>` : '';
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas ${icon}"></i>
        </div>
        <div class="notification-content">
            <div class="notification-message">${escapeHtml(msg)}</div>
        </div>
        ${closeButton}
    `;
    
    // Add close functionality if enabled
    if (config.closable) {
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => hideNotification(notification));
    }
    
    // Add to container
    container.appendChild(notification);
    
    // Trigger entrance animation
    requestAnimationFrame(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    });
    
    // Auto-hide after duration
    if (config.duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                hideNotification(notification);
            }
        }, config.duration);
    }
    
    return notification;
}

/**
 * Hide a notification with animation
 * @param {HTMLElement} notification - The notification element to hide
 */
function hideNotification(notification) {
    notification.classList.add('notification-hide');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 300);
}

/**
 * Get FontAwesome icon class for notification type
 * @param {string} type - Notification type
 * @returns {string} FontAwesome icon class
 */
function getNotificationIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-times-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    
    return icons[type] || icons.info;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Clear all notifications
 */
function clearAllNotifications() {
    const container = document.getElementById('notification-container');
    if (container) {
        container.innerHTML = '';
    }
}

/**
 * Legacy compatibility function - maps to the new notify function
 * @param {string} message - Notification message
 * @param {string} type - Notification type
 */
function showNotification(message, type = 'info') {
    return notify(type, message);
}

/**
 * Convenience functions for common notification types
 */
const notifications = {
    success: (msg, options) => notify('success', msg, options),
    error: (msg, options) => notify('error', msg, options),
    warning: (msg, options) => notify('warning', msg, options),
    info: (msg, options) => notify('info', msg, options)
};

// Make functions available globally
window.notify = notify;
window.notifications = notifications;
window.showNotification = showNotification;
window.clearAllNotifications = clearAllNotifications;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { notify, notifications, showNotification, clearAllNotifications };
}

