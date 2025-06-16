/**
 * Theme management for MASH - MeshAdmin System Heuristics
 * Handles theme customization with color wheel
 */

// Default color schemes
const colorSchemes = {
    dark_red: {
        name: 'Dark Red',
        id: 'dark_red',
        primaryBg: '#121212',      // Matte black
        secondaryBg: '#1e1e1e',    // Slightly lighter black
        tertiaryBg: '#2d2d2d',     // Even lighter black
        accentColor: '#c50000',    // Dark red accent
        borderColor: '#333333'     // Dark border
    },
    dark: {
        name: 'Dark',
        id: 'dark',
        primaryBg: '#121212',
        secondaryBg: '#1e1e1e',
        tertiaryBg: '#2d2d2d',
        accentColor: '#03dac6',
        borderColor: '#333333'
    },
    light: {
        name: 'Light',
        id: 'light',
        primaryBg: '#f5f5f5',
        secondaryBg: '#ffffff',
        tertiaryBg: '#e9ecef',
        accentColor: '#018786',
        borderColor: '#e0e0e0'
    }
};

// Current theme properties
let currentTheme = {
    id: 'dark_red',
    primaryBg: '#121212',      // Matte black
    secondaryBg: '#1e1e1e',    // Slightly lighter black
    tertiaryBg: '#2d2d2d',     // Even lighter black
    accentColor: '#c50000',    // Dark red accent
    borderColor: '#333333'     // Dark border
};

// Clear any potentially corrupted theme data from localStorage
function cleanupThemeStorage() {
    try {
        // Get the current theme ID
        const themeId = localStorage.getItem('theme');
        const customColors = localStorage.getItem('customColors');
        
        // Check if theme ID is valid
        if (themeId && !colorSchemes[themeId] && themeId !== 'custom') {
            console.warn(`Invalid theme ID in localStorage: ${themeId}. Resetting to default.`);
            localStorage.removeItem('theme');
        }
        
        // Check if custom colors are valid JSON
        if (customColors) {
            try {
                const colors = JSON.parse(customColors);
                if (!colors || typeof colors !== 'object' || 
                    !colors.primaryBg || !colors.secondaryBg || !colors.accentColor) {
                    console.warn('Corrupted custom colors in localStorage. Removing.');
                    localStorage.removeItem('customColors');
                }
            } catch (e) {
                console.warn('Invalid JSON in customColors localStorage. Removing.');
                localStorage.removeItem('customColors');
            }
        }
    } catch (error) {
        console.error('Error cleaning up theme storage:', error);
    }
}

// Initialize theme when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Clean up any corrupted theme storage before initializing
        cleanupThemeStorage();
        
        // Set the dark_red theme initially if no theme is stored
        if (!localStorage.getItem('theme') && !localStorage.getItem('customColors')) {
            localStorage.setItem('theme', 'dark_red');
            console.log("Setting default theme to dark_red");
            
            // Apply default theme colors to avoid flash of unstyled content
            document.documentElement.setAttribute('data-theme', 'dark_red');
            applyThemeProperties(colorSchemes.dark_red);
        }
        
        // Initialize theme
        initTheme();
        setupThemeToggle();
        setupColorWheel();
        
        // Expose theme functions globally for other scripts to use
        window.themeSystem = {
            getCurrentTheme: () => currentTheme,
            applyTheme,
            applyCustomTheme,
            refreshTheme: () => {
                // Re-apply the current theme to ensure consistent state
                if (currentTheme.id === 'custom') {
                    applyCustomTheme(currentTheme);
                } else {
                    applyTheme(currentTheme.id);
                }
            }
        };
        
        // Log successful initialization
        console.log("Theme system initialized successfully");
    } catch (error) {
        console.error("Error initializing theme system:", error);
        
        // Fallback to ensure some theme is applied even if there's an error
        try {
            document.documentElement.setAttribute('data-theme', 'dark_red');
            applyThemeProperties(colorSchemes.dark_red);
            currentTheme = { ...colorSchemes.dark_red, id: 'dark_red' };
        } catch (e) {
            console.error("Failed to apply fallback theme:", e);
        }
    }
});

/**
 * Initialize the theme based on stored preferences or default
 */
function initTheme() {
    try {
        // Get stored theme or use default dark red theme
        const storedThemeId = localStorage.getItem('theme') || 'dark_red';
        const storedCustomColors = localStorage.getItem('customColors');
        
        // For debugging theme issues
        console.log("Theme initialization: stored theme ID =", storedThemeId);
        
        if (storedCustomColors) {
            try {
                console.log("Found custom theme colors in localStorage");
                const customTheme = JSON.parse(storedCustomColors);
                
                // Validate custom theme has required properties
                if (!customTheme.primaryBg || !customTheme.secondaryBg || !customTheme.accentColor) {
                    console.warn("Custom theme is missing required properties, falling back to stored theme ID");
                    applyTheme(storedThemeId);
                    return;
                }
                
                // Make sure ID is set in custom theme
                if (!customTheme.id) {
                    customTheme.id = 'custom';
                }
                
                applyCustomTheme(customTheme);
                console.log("Successfully applied custom theme");
            } catch (e) {
                console.error('Failed to parse stored custom theme, using default', e);
                applyTheme(storedThemeId);
            }
        } else {
            console.log("No custom theme found, applying theme:", storedThemeId);
            applyTheme(storedThemeId);
        }
        
        // Update charts if they exist
        if (typeof window.updateChartsForTheme === 'function') {
            window.updateChartsForTheme();
        } else {
            console.log("Charts update function not available yet");
        }
    } catch (error) {
        console.error("Error during theme initialization:", error);
        
        // Apply default theme as fallback
        try {
            document.documentElement.setAttribute('data-theme', 'dark_red');
            applyThemeProperties(colorSchemes.dark_red);
            currentTheme = { ...colorSchemes.dark_red };
        } catch (e) {
            console.error("Critical error in theme fallback:", e);
        }
    }
}

/**
 * Apply a predefined theme
 * @param {string} themeId - Theme identifier
 */
function applyTheme(themeId) {
    // Validate theme ID
    if (!colorSchemes[themeId]) {
        console.error(`Theme ${themeId} does not exist, falling back to dark red theme`);
        themeId = 'dark_red';
    }
    
    const theme = colorSchemes[themeId];
    currentTheme = { 
        ...theme,
        id: themeId // Ensure id property is set
    };
    
    // Set the data-theme attribute on html element
    document.documentElement.setAttribute('data-theme', themeId);
    
    // Apply the theme CSS
    applyThemeProperties(theme);
    
    // Store the selected theme in local storage
    localStorage.setItem('theme', themeId);
    
    // Load appropriate CSS file if needed
    updateThemeStylesheet(themeId);
    
    // Dispatch theme changed event
    const event = new CustomEvent('themeChanged', { detail: { theme: themeId } });
    document.dispatchEvent(event);
    
    console.log(`Theme set to ${themeId}`);
}

/**
 * Apply a custom theme with specific colors
 * @param {Object} theme - Theme object with color properties
 */
function applyCustomTheme(theme) {
    // Apply the custom colors to CSS variables
    currentTheme = { 
        ...theme,
        id: 'custom' // Ensure id property is set
    };
    
    // Set the data-theme attribute to custom
    document.documentElement.setAttribute('data-theme', 'custom');
    
    // Apply the theme CSS properties
    applyThemeProperties(theme);
    
    // Store the custom theme in local storage
    localStorage.setItem('customColors', JSON.stringify(currentTheme));
    
    // Dispatch theme changed event
    const event = new CustomEvent('themeChanged', { detail: { theme: 'custom' } });
    document.dispatchEvent(event);
    
    console.log('Custom theme applied');
}

/**
 * Apply theme properties to CSS variables
 * @param {Object} theme - Theme object with color properties
 */
function applyThemeProperties(theme) {
    document.documentElement.style.setProperty('--primary-bg', theme.primaryBg);
    document.documentElement.style.setProperty('--secondary-bg', theme.secondaryBg);
    document.documentElement.style.setProperty('--tertiary-bg', theme.tertiaryBg);
    document.documentElement.style.setProperty('--accent-color', theme.accentColor);
    document.documentElement.style.setProperty('--border-color', theme.borderColor);
}

/**
 * Update the theme stylesheet link
 * @param {string} themeId - Theme identifier
 */
function updateThemeStylesheet(themeId) {
    const themeLink = document.getElementById('theme-css');
    if (themeLink) {
        themeLink.href = `/static/css/${themeId}_theme.css`;
    }
}

/**
 * Set up the light/dark theme toggle
 */
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    // Set initial state
    const currentThemeId = localStorage.getItem('theme') || 'dark_red';
    themeToggle.checked = currentThemeId === 'light';
    
    // Add event listener for theme toggle
    themeToggle.addEventListener('change', (e) => {
        // Check if we're using a custom accent color
        const customColors = localStorage.getItem('customColors');
        let accentColor = null;
        
        if (customColors) {
            try {
                const customTheme = JSON.parse(customColors);
                accentColor = customTheme.accentColor;
            } catch (e) {
                console.error('Failed to parse stored custom theme', e);
            }
        }
        
        // Determine the next theme to apply
        const nextThemeId = e.target.checked ? 'light' : 'dark_red';
        
        if (accentColor) {
            // Preserve the accent color but change the theme mode
            const newTheme = { ...colorSchemes[nextThemeId] };
            newTheme.accentColor = accentColor;
            
            // Apply the modified theme
            currentTheme = { 
                ...newTheme,
                id: nextThemeId // Ensure id property is set
            };
            document.documentElement.setAttribute('data-theme', nextThemeId);
            applyThemeProperties(newTheme);
            updateThemeStylesheet(nextThemeId);
            
            // Store the theme name (not the custom colors)
            localStorage.setItem('theme', nextThemeId);
            
            // Dispatch theme changed event
            const event = new CustomEvent('themeChanged', { detail: { theme: nextThemeId } });
            document.dispatchEvent(event);
            
            console.log(`Theme set to ${nextThemeId} with custom accent color`);
            
            // Save preference to server if user is logged in
            saveThemePreference({ theme: nextThemeId, accentColor: accentColor });
        } else {
            // Standard theme change
            applyTheme(nextThemeId);
            
            // Save preference to server if user is logged in
            saveThemePreference(nextThemeId);
        }
    });
}

/**
 * Set up the color wheel customization tool
 */
function setupColorWheel() {
    // Create color wheel button in the sidebar footer
    const sidebarFooter = document.querySelector('.sidebar-footer');
    if (!sidebarFooter) return;
    
    // Create color wheel button
    const colorWheelButton = document.createElement('button');
    colorWheelButton.id = 'color-wheel-button';
    colorWheelButton.className = 'color-wheel-button';
    colorWheelButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>';
    colorWheelButton.title = 'Customize Colors';
    
    // Create color wheel container
    const colorWheelContainer = document.createElement('div');
    colorWheelContainer.id = 'color-wheel-container';
    colorWheelContainer.className = 'color-wheel-container';
    colorWheelContainer.style.display = 'none';
    
    // Add content to color wheel container
    colorWheelContainer.innerHTML = `
        <div class="color-wheel-header">
            <div class="color-wheel-title">Customize Colors</div>
        </div>
        <div class="color-wheel-settings">
            <div class="color-selector">
                <label for="accent-color"><strong>Accent Color</strong></label>
                <div class="color-row">
                    <div class="color-preview" style="background-color:${currentTheme.accentColor}"></div>
                    <input type="color" id="accent-color-picker" value="${currentTheme.accentColor}">
                </div>
                <div class="selector-description">Main highlight color used throughout the interface</div>
            </div>
            <div class="accent-preview">
                <div class="preview-label">Preview:</div>
                <div class="preview-items">
                    <button class="preview-button">Button</button>
                    <div class="preview-badge">Badge</div>
                    <div class="preview-link">Link</div>
                </div>
            </div>
            <div class="preset-colors">
                <div class="preset-color" style="background-color:#c50000" data-theme="dark_red" title="Dark Red"></div>
                <div class="preset-color" style="background-color:#03dac6" data-theme="dark" title="Dark"></div>
                <div class="preset-color" style="background-color:#006064" data-theme="light" title="Light"></div>
                <div class="preset-color" style="background-color:#673ab7" title="Purple"></div>
                <div class="preset-color" style="background-color:#ff5722" title="Orange"></div>
                <div class="preset-color" style="background-color:#2196f3" title="Blue"></div>
            </div>
            <div class="theme-mode-toggle">
                <span>Dark</span>
                <label class="switch">
                    <input type="checkbox" id="theme-mode-toggle" ${currentTheme.id === 'light' ? 'checked' : ''}>
                    <span class="slider round"></span>
                </label>
                <span>Light</span>
            </div>
            <div class="color-wheel-buttons">
                <button class="theme-reset-button" id="reset-theme">Reset</button>
                <button class="theme-apply-button" id="apply-theme">Apply</button>
            </div>
        </div>
    `;
    
    // Add elements to the sidebar footer
    sidebarFooter.appendChild(colorWheelButton);
    sidebarFooter.appendChild(colorWheelContainer);
    
    // Setup event listeners
    colorWheelButton.addEventListener('click', () => {
        colorWheelContainer.style.display = colorWheelContainer.style.display === 'none' ? 'block' : 'none';
    });
    
    // Theme mode toggle in color wheel
    const themeModeToggle = document.getElementById('theme-mode-toggle');
    if (themeModeToggle) {
        // Set initial state based on current theme
        const currentThemeId = localStorage.getItem('theme') || 'dark_red';
        themeModeToggle.checked = currentThemeId === 'light';
        
        // Add event listener
        themeModeToggle.addEventListener('change', (e) => {
            const accentColor = document.getElementById('accent-color-picker').value;
            const newThemeId = e.target.checked ? 'light' : 'dark_red';
            
            // Get the base theme
            const baseTheme = colorSchemes[newThemeId];
            
            // Create a theme with the current accent color but changing the light/dark mode
            const newTheme = {
                ...baseTheme,
                accentColor: accentColor
            };
            
            // Apply the theme
            currentTheme = { 
                ...newTheme,
                id: newThemeId // Ensure id property is set
            };
            document.documentElement.setAttribute('data-theme', newThemeId);
            applyThemeProperties(newTheme);
            updateThemeStylesheet(newThemeId);
            
            // Update preview elements with the accent color
            document.querySelectorAll('.preview-button, .preview-badge').forEach(el => {
                el.style.backgroundColor = accentColor;
            });
            document.querySelector('.preview-link').style.color = accentColor;
            
            // Store the theme name
            localStorage.setItem('theme', newThemeId);
            
            console.log(`Theme mode changed to ${newThemeId}`);
        });
    }
    
    // Color input event listeners
    const accentColorInput = document.getElementById('accent-color-picker');
    
    // Update color preview when input changes
    accentColorInput.addEventListener('input', (e) => {
        // Update the color preview
        document.querySelector('label[for="accent-color"] + .color-row .color-preview').style.backgroundColor = e.target.value;
        
        // Also update the preview elements
        document.querySelectorAll('.preview-button, .preview-badge').forEach(el => {
            el.style.backgroundColor = e.target.value;
        });
        document.querySelector('.preview-link').style.color = e.target.value;
    });
    
    // Apply button event listener
    document.getElementById('apply-theme').addEventListener('click', () => {
        // Get the current theme (light or dark)
        const currentThemeId = localStorage.getItem('theme') || 'dark_red';
        const baseTheme = currentThemeId === 'light' ? colorSchemes.light : colorSchemes.dark_red;
        
        // Create a custom theme based on the current mode but with the new accent color
        const customTheme = {
            id: 'custom',
            primaryBg: baseTheme.primaryBg,
            secondaryBg: baseTheme.secondaryBg,
            tertiaryBg: baseTheme.tertiaryBg,
            accentColor: accentColorInput.value,
            borderColor: baseTheme.borderColor
        };
        
        // Apply the custom theme
        applyCustomTheme(customTheme);
        saveThemePreference(customTheme);
        colorWheelContainer.style.display = 'none';
    });
    
    // Reset button event listener
    document.getElementById('reset-theme').addEventListener('click', () => {
        applyTheme('dark_red');
        saveThemePreference('dark_red');
        
        // Reset accent color input value
        accentColorInput.value = colorSchemes.dark_red.accentColor;
        
        // Reset accent color preview
        document.querySelector('label[for="accent-color"] + .color-row .color-preview').style.backgroundColor = colorSchemes.dark_red.accentColor;
        
        // Reset preview elements
        document.querySelectorAll('.preview-button, .preview-badge').forEach(el => {
            el.style.backgroundColor = colorSchemes.dark_red.accentColor;
        });
        document.querySelector('.preview-link').style.color = colorSchemes.dark_red.accentColor;
        
        // Reset theme mode toggle to dark
        const themeModeToggle = document.getElementById('theme-mode-toggle');
        if (themeModeToggle) {
            themeModeToggle.checked = false; // Dark is unchecked
        }
        
        colorWheelContainer.style.display = 'none';
    });
    
    // Preset colors event listeners
    document.querySelectorAll('.preset-color').forEach(preset => {
        preset.addEventListener('click', (e) => {
            const themeId = e.target.dataset.theme;
            if (themeId) {
                // Apply predefined theme
                applyTheme(themeId);
                saveThemePreference(themeId);
                
                // Update theme mode toggle to match the theme
                const themeModeToggle = document.getElementById('theme-mode-toggle');
                if (themeModeToggle) {
                    themeModeToggle.checked = themeId === 'light';
                }
                
                // Update accent color input and preview
                accentColorInput.value = colorSchemes[themeId].accentColor;
                document.querySelector('label[for="accent-color"] + .color-row .color-preview').style.backgroundColor = colorSchemes[themeId].accentColor;
                
                // Update preview elements
                document.querySelectorAll('.preview-button, .preview-badge').forEach(el => {
                    el.style.backgroundColor = colorSchemes[themeId].accentColor;
                });
                document.querySelector('.preview-link').style.color = colorSchemes[themeId].accentColor;
            } else {
                // Custom presets without a theme ID
                const color = e.target.style.backgroundColor;
                
                // Generate a theme based on the selected color
                const customTheme = generateThemeFromColor(color);
                
                // Apply the custom theme
                applyCustomTheme(customTheme);
                saveThemePreference(customTheme);
                
                // Update accent color input and preview
                accentColorInput.value = customTheme.accentColor;
                document.querySelector('label[for="accent-color"] + .color-row .color-preview').style.backgroundColor = customTheme.accentColor;
                
                // Update preview elements
                document.querySelectorAll('.preview-button, .preview-badge').forEach(el => {
                    el.style.backgroundColor = customTheme.accentColor;
                });
                document.querySelector('.preview-link').style.color = customTheme.accentColor;
            }
        });
    });
}

/**
 * Generate a theme based on a primary color
 * @param {string} color - The primary color to build theme around
 * @returns {Object} - Theme object
 */
function generateThemeFromColor(color) {
    // Convert RGB to HEX if needed
    let hexColor = color;
    if (color.startsWith('rgb')) {
        const rgbValues = color.match(/\d+/g);
        hexColor = rgbToHex(parseInt(rgbValues[0]), parseInt(rgbValues[1]), parseInt(rgbValues[2]));
    }
    
    // Get the current theme (light or dark)
    const currentThemeId = localStorage.getItem('theme') || 'dark_red';
    const isCurrentlyLight = currentThemeId === 'light';
    
    // Decide whether to use light or dark background based on current theme
    // Always keep the user's current theme type (light/dark) but update accent color
    let primaryBg, secondaryBg, tertiaryBg, borderColor;
    
    if (isCurrentlyLight) {
        // Use light theme background colors with the new accent color
        primaryBg = colorSchemes.light.primaryBg;
        secondaryBg = colorSchemes.light.secondaryBg;
        tertiaryBg = colorSchemes.light.tertiaryBg;
        borderColor = colorSchemes.light.borderColor;
    } else {
        // Use dark theme background colors with the new accent color
        primaryBg = colorSchemes.dark_red.primaryBg;
        secondaryBg = colorSchemes.dark_red.secondaryBg;
        tertiaryBg = colorSchemes.dark_red.tertiaryBg;
        borderColor = colorSchemes.dark_red.borderColor;
    }
    
    return {
        id: 'custom',
        primaryBg: primaryBg,
        secondaryBg: secondaryBg,
        tertiaryBg: tertiaryBg,
        accentColor: hexColor,
        borderColor: borderColor
    };
}

/**
 * Convert RGB values to HEX color
 * @param {number} r - Red value (0-255)
 * @param {number} g - Green value (0-255)
 * @param {number} b - Blue value (0-255)
 * @returns {string} - HEX color string
 */
function rgbToHex(r, g, b) {
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

/**
 * Get the perceived brightness of a color (0-255)
 * @param {string} color - HEX color
 * @returns {number} - Brightness value (0-255)
 */
function getColorBrightness(color) {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    return (r * 299 + g * 587 + b * 114) / 1000;
}

/**
 * Adjust a color by a percentage (positive for lighter, negative for darker)
 * @param {string} color - HEX color
 * @param {number} percent - Percentage to adjust (-100 to 100)
 * @returns {string} - Adjusted HEX color
 */
function adjustColor(color, percent) {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    
    const amount = Math.floor((percent / 100) * 255);
    
    const newR = clamp(r + amount, 0, 255);
    const newG = clamp(g + amount, 0, 255);
    const newB = clamp(b + amount, 0, 255);
    
    return `#${componentToHex(newR)}${componentToHex(newG)}${componentToHex(newB)}`;
}

/**
 * Convert a component value to a HEX string
 * @param {number} c - Component value (0-255)
 * @returns {string} - HEX string for component
 */
function componentToHex(c) {
    const hex = c.toString(16);
    return hex.length === 1 ? '0' + hex : hex;
}

/**
 * Clamp a value between min and max
 * @param {number} value - Value to clamp
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} - Clamped value
 */
function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

/**
 * Save theme preference to the server
 * @param {string|Object} theme - Theme identifier or custom theme object
 */
function saveThemePreference(theme) {
    try {
        // Send preference to server if user is logged in
        const userDataElem = document.getElementById('user-data');
        if (!userDataElem || !userDataElem.dataset.userId) {
            console.log('User not logged in, skipping theme preference save');
            return;
        }
        
        // Prepare the theme data for the API
        let themeData;
        
        try {
            themeData = typeof theme === 'string' 
                ? { theme } 
                : { theme: 'custom', customColors: theme };
                
            console.log('Saving theme preference:', 
                typeof theme === 'string' ? theme : 'custom theme');
        } catch (parseError) {
            console.error('Error preparing theme data:', parseError);
            return;
        }
        
        // Get CSRF token if available
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (csrfToken) {
            headers['X-CSRF-Token'] = csrfToken;
        }
        
        fetch('/api/users/preferences', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(themeData),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error saving preference: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Theme preference saved successfully');
        })
        .catch(error => {
            console.error('Failed to save theme preference:', error);
        });
    } catch (error) {
        console.error('Critical error in saveThemePreference:', error);
    }
}

// Watch for Chart.js initialization and apply theme when ready
(function watchForChartInit() {
    const checkForChart = setInterval(() => {
        if (typeof Chart !== 'undefined' && typeof window.chartUtils !== 'undefined') {
            console.log("Chart.js detected, applying theme to charts");
            if (window.chartUtils.applyThemeToCharts) {
                window.chartUtils.applyThemeToCharts();
            }
            clearInterval(checkForChart);
        }
    }, 200);
    
    // Don't check indefinitely - stop after 10 seconds
    setTimeout(() => {
        clearInterval(checkForChart);
    }, 10000);
})();

// Expose theme functions to global scope
window.themeSystem = {
    applyTheme,
    applyCustomTheme,
    getCurrentTheme: () => currentTheme,
    getColorSchemes: () => colorSchemes,
    cleanup: cleanupThemeStorage,
    refreshTheme: () => {
        // Re-apply the current theme to ensure consistent state
        if (currentTheme.id === 'custom') {
            applyCustomTheme(currentTheme);
        } else {
            applyTheme(currentTheme.id);
        }
    }
};