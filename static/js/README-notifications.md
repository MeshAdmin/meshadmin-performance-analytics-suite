# MASH Central Notification System

A centralized, robust notification system for the MASH (MeshAdmin Performance Analytics Suite) that provides consistent error handling and user feedback across all applications.

## Features

- **Centralized notifications** with consistent styling and behavior
- **Four notification types**: success, error, warning, info
- **Customizable options**: duration, closability, positioning
- **FontAwesome icons** for visual clarity
- **Legacy compatibility** with existing `showNotification()` functions
- **XSS protection** with HTML escaping
- **Auto-hide functionality** with customizable durations
- **Modern animations** with smooth slide-in/out effects

## Quick Start

### 1. Include the notification system in your HTML

```html
<!-- Include FontAwesome for icons (if not already included) -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

<!-- Include the notification JavaScript -->
<script src="/static/js/notifications.js"></script>
```

### 2. Use in your JavaScript

```javascript
// Basic usage
notify('success', 'Operation completed successfully!');
notify('error', 'Something went wrong');
notify('warning', 'Please check your input');
notify('info', 'New feature available');

// Using convenience functions
notifications.success('File uploaded');
notifications.error('Connection failed');
notifications.warning('Session expiring');
notifications.info('Update available');
```

## API Reference

### Main Function

```javascript
notify(type, message, options)
```

**Parameters:**
- `type` (string): Notification type - 'success', 'error', 'warning', 'info'
- `message` (string): The message to display
- `options` (object, optional): Configuration options

**Options:**
```javascript
{
    duration: 5000,        // Auto-hide duration in ms (0 = no auto-hide)
    closable: true,        // Whether user can close manually
    position: 'bottom-right' // Position (future feature)
}
```

### Convenience Functions

```javascript
notifications.success(message, options)
notifications.error(message, options)  
notifications.warning(message, options)
notifications.info(message, options)
```

### Utility Functions

```javascript
clearAllNotifications()          // Remove all active notifications
showNotification(message, type)  // Legacy compatibility function
```

## Error Handling Integration

### Standard Pattern for .catch() blocks

Replace existing error handling with the notification system:

```javascript
// Before
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        // Handle success
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to load data');
    });

// After
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        // Handle success
        notify('success', 'Data loaded successfully');
    })
    .catch(error => {
        console.error('Error:', error);
        if (typeof notify !== 'undefined') {
            notify('error', `Failed to load data: ${error.message}`);
        } else {
            // Fallback for environments without notification system
            console.error('Failed to load data:', error.message);
        }
    });
```

### Defensive Programming

Always check if the notification system is available:

```javascript
if (typeof notify !== 'undefined') {
    notify('error', 'Something went wrong');
} else {
    // Fallback behavior
    console.error('Something went wrong');
}
```

## Styling

The notification system uses the existing `#notification-container` styles from your CSS. Key classes:

- `.notification` - Base notification styling
- `.notification-success` - Green border for success
- `.notification-error` - Red border for errors  
- `.notification-warning` - Orange border for warnings
- `.notification-info` - Blue border for info
- `.notification-hide` - Animation class for hiding

## Integration Examples

### Replace Custom Toast Systems

```javascript
// Old custom toast function
function showToast(message, type = 'info') {
    // Custom toast implementation
}

// New centralized approach
function showToast(message, type = 'info') {
    if (typeof notify !== 'undefined') {
        return notify(type, message);
    } else {
        // Fallback to console
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}
```

### Form Validation

```javascript
function validateForm() {
    if (!email.value) {
        notify('warning', 'Email is required');
        return false;
    }
    
    if (!isValidEmail(email.value)) {
        notify('error', 'Please enter a valid email address');
        return false;
    }
    
    notify('success', 'Form validation passed');
    return true;
}
```

### API Operations

```javascript
async function saveData(data) {
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        notify('success', 'Data saved successfully');
        return result;
        
    } catch (error) {
        notify('error', `Failed to save data: ${error.message}`);
        throw error;
    }
}
```

## Migration Guide

### Step 1: Include notifications.js
Add the script to your HTML templates after FontAwesome but before your application scripts.

### Step 2: Update .catch() blocks
Replace `console.error()`, `alert()`, or custom error displays with `notify()` calls.

### Step 3: Add success notifications
Add success notifications for positive user actions that were previously silent.

### Step 4: Test fallbacks
Ensure your application still works if the notification system fails to load.

## Browser Support

- Modern browsers with ES6+ support
- Graceful degradation in older browsers
- FontAwesome 5.0+ for icons

## Troubleshooting

### Notifications not appearing
1. Check that `notifications.js` is loaded
2. Verify FontAwesome is available for icons
3. Check browser console for JavaScript errors
4. Ensure CSS styles are properly loaded

### Icons not showing
1. Verify FontAwesome CSS is loaded
2. Check network requests for 404 errors
3. Ensure icon classes match FontAwesome version

### Animations not smooth
1. Check for CSS conflicts with animation properties
2. Verify browser supports CSS transitions
3. Test with hardware acceleration enabled

## Best Practices

1. **Use appropriate types**: Match the notification type to the message context
2. **Keep messages concise**: Users scan notifications quickly
3. **Provide actionable information**: Tell users what happened and what they can do
4. **Don't spam**: Avoid showing multiple similar notifications
5. **Test fallbacks**: Always provide fallback behavior
6. **Consider accessibility**: Ensure messages are screen-reader friendly

## Contributing

When adding new features or modifications:

1. Maintain backward compatibility with existing `showNotification()` calls
2. Test across different browsers and screen sizes
3. Update this documentation
4. Add examples for new functionality
5. Ensure XSS protection is maintained

## License

Part of the MASH suite - see main project license.

