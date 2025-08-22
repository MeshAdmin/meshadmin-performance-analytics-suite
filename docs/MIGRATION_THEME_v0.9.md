# Theme Migration Guide - v0.9 UI Redesign

This guide helps downstream theme developers migrate their custom themes to work with the new theming system introduced in v0.9-ui-redesign.

## Overview of Changes

The v0.9 UI redesign introduces a completely new theming architecture with the following improvements:

### New Features
- **CSS Custom Properties**: All themes now use CSS custom properties (CSS variables) for runtime switching
- **SCSS Architecture**: Structured SCSS with abstracts, variables, and mixins
- **Color Wheel Integration**: Users can customize accent colors through the UI
- **Theme Persistence**: Themes are saved to localStorage and user preferences
- **Real-time Switching**: Instant theme changes without page reload

### Breaking Changes
- Legacy CSS class-based theming is deprecated
- Theme files must use new CSS custom property structure
- JavaScript theme API has been updated
- SCSS compilation is now required for theme development

## Migration Steps

### 1. Update Theme CSS Structure

#### Before (Legacy v0.8)
```css
/* old-theme.css */
.dark-theme .sidebar {
  background-color: #1a1a1a;
  color: #f0f0f0;
}

.dark-theme .button-primary {
  background-color: #c50000;
  color: white;
}
```

#### After (v0.9)
```css
/* new-theme.css */
:root[data-theme="your-theme"] {
  --primary-bg: #000000;
  --secondary-bg: #1a1a1a;
  --tertiary-bg: #2d2d2d;
  --primary-text: #f0f0f0;
  --secondary-text: #aaaaaa;
  --accent-color: #c50000;
  --border-color: #333333;
  --hover-bg: rgba(255, 255, 255, 0.1);
  --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
```

### 2. Update Theme Registration

#### Before (Legacy v0.8)
```javascript
// themes.js
function applyTheme(themeName) {
  document.body.className = themeName + '-theme';
}
```

#### After (v0.9)
```javascript
// themes.js - Add to colorSchemes object
const colorSchemes = {
  // ... existing themes
  your_theme: {
    name: 'Your Theme Name',
    id: 'your_theme',
    primaryBg: '#000000',
    secondaryBg: '#1a1a1a',
    tertiaryBg: '#2d2d2d',
    accentColor: '#c50000',
    borderColor: '#333333'
  }
};
```

### 3. Update Component Styles

Replace hardcoded colors with CSS custom properties:

#### Before
```css
.my-component {
  background-color: #1a1a1a;
  color: #f0f0f0;
  border: 1px solid #333333;
}
```

#### After
```css
.my-component {
  background-color: var(--secondary-bg);
  color: var(--primary-text);
  border: 1px solid var(--border-color);
}
```

### 4. SCSS Integration (Recommended)

For advanced theme development, migrate to SCSS:

```scss
// _your-theme-variables.scss
$color-primary: #c50000;
$bg-primary: #000000;
$bg-secondary: #1a1a1a;
// ... other variables

// your-theme.scss
@use 'your-theme-variables' as *;

:root[data-theme="your-theme"] {
  --primary-bg: #{$bg-primary};
  --secondary-bg: #{$bg-secondary};
  --accent-color: #{$color-primary};
  // ... other properties
}
```

### 5. Update JavaScript Theme Logic

#### Before
```javascript
// Legacy theme switching
function switchTheme(themeName) {
  document.body.className = themeName;
  localStorage.setItem('theme', themeName);
}
```

#### After
```javascript
// Use the new theme system
function switchTheme(themeId) {
  // Use the global theme system
  if (window.themeSystem) {
    window.themeSystem.applyTheme(themeId);
  }
}

// Or for custom themes
function applyCustomTheme(colors) {
  if (window.themeSystem) {
    window.themeSystem.applyCustomTheme(colors);
  }
}
```

## Required CSS Custom Properties

All themes must define these essential CSS custom properties:

```css
:root[data-theme="your-theme"] {
  /* Background Colors */
  --primary-bg: #000000;           /* Main page background */
  --secondary-bg: #1a1a1a;         /* Cards, sidebar background */
  --tertiary-bg: #2d2d2d;          /* Interactive elements */
  --card-bg: rgba(255,255,255,0.05); /* Card backgrounds */
  --hover-bg: rgba(255,255,255,0.1);  /* Hover states */
  
  /* Text Colors */
  --primary-text: #f0f0f0;         /* Main text color */
  --secondary-text: #aaaaaa;       /* Secondary text color */
  
  /* Brand Colors */
  --accent-color: #c50000;         /* Primary brand color */
  --accent-color-light: #ff5252;   /* Lighter variant for hover */
  
  /* Semantic Colors */
  --warning-color: #ff9800;        /* Warning alerts */
  --error-color: #cf6679;          /* Error states */
  --success-color: #4caf50;        /* Success states */
  --info-color: #2196f3;           /* Info states */
  
  /* Layout */
  --border-color: #333333;         /* Borders and separators */
  --shadow: 0 4px 6px rgba(0,0,0,0.3); /* Box shadows */
}
```

## Optional Enhancements

### Chart Color Integration

Define chart-specific colors for data visualization:

```css
:root[data-theme="your-theme"] {
  /* Chart Colors */
  --chart-color-1: #c50000;
  --chart-color-2: #ff5252;
  --chart-color-3: #8c0000;
  --chart-color-4: #ff0000;
  --chart-color-5: #ffcdd2;
  --chart-grid-color: rgba(255, 255, 255, 0.1);
}
```

### Custom Scrollbar

Style scrollbars to match your theme:

```css
:root[data-theme="your-theme"] {
  /* Scrollbar colors */
  --scrollbar-track: var(--primary-bg);
  --scrollbar-thumb: var(--tertiary-bg);
  --scrollbar-thumb-hover: var(--accent-color);
}

/* Scrollbar implementation */
::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
}

::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}
```

## Testing Your Theme

### 1. Visual Testing

Run the visual regression tests to ensure your theme renders correctly:

```bash
# Test your theme across all components
pnpm test:visual

# Test specific theme
pnpm exec playwright test --project=chromium --grep="your-theme"
```

### 2. Accessibility Testing

Ensure your theme meets accessibility standards:

```bash
# Run accessibility tests
pnpm test:accessibility

# Check color contrast ratios
# Use browser dev tools or online contrast checkers
```

### 3. Manual Testing Checklist

- [ ] Theme switches correctly via color wheel
- [ ] All UI components render with correct colors
- [ ] Text is readable with sufficient contrast
- [ ] Interactive elements have visible hover states
- [ ] Charts and data visualizations use theme colors
- [ ] Theme persists across page reloads
- [ ] Theme works in all browsers (Chrome, Firefox, Safari)

## Common Migration Issues

### Issue 1: CSS Specificity
**Problem**: Existing CSS rules override CSS custom properties
**Solution**: Increase specificity or use `!important` carefully
```css
:root[data-theme="your-theme"] .component {
  background-color: var(--secondary-bg) !important;
}
```

### Issue 2: Missing Variables
**Problem**: Components break when custom properties are undefined
**Solution**: Provide fallback values
```css
.component {
  background-color: var(--secondary-bg, #1a1a1a);
}
```

### Issue 3: JavaScript Errors
**Problem**: Theme switching code fails
**Solution**: Check for theme system availability
```javascript
if (window.themeSystem && typeof window.themeSystem.applyTheme === 'function') {
  window.themeSystem.applyTheme('your-theme');
}
```

## Best Practices

### 1. Color Accessibility
- Ensure contrast ratio ≥ 4.5:1 for normal text
- Ensure contrast ratio ≥ 3:1 for large text
- Test with color blindness simulators

### 2. Performance
- Minimize CSS custom property reassignments
- Use CSS custom properties efficiently
- Test theme switching performance

### 3. Maintainability
- Document your color choices
- Use semantic naming for custom properties
- Provide both light and dark variants

### 4. User Experience
- Ensure smooth transitions between themes
- Maintain visual hierarchy across themes
- Test with real content and data

## Support and Resources

### Documentation
- [SCSS Architecture Guide](apps/observability-dashboard/src/scss/README.md)
- [Theme Variables Reference](apps/observability-dashboard/static/css/README.md)
- [Visual Testing Guide](docs/TESTING_GUIDE.md)

### Getting Help
- Review existing themes for examples
- Check the theme system source code in `themes.js`
- Open an issue for migration assistance

### Community Themes
Consider contributing your theme back to the community:
1. Fork the repository
2. Add your theme to the theme collection
3. Submit a pull request with documentation

## Backwards Compatibility

### Deprecation Timeline
- **v0.9**: New theme system introduced, legacy support maintained
- **v1.0**: Legacy theme system will be removed
- **Migration Period**: 6 months to update custom themes

### Legacy Support
Limited backwards compatibility is provided through:
- Automatic CSS custom property injection for common classes
- Warning messages for deprecated theme methods
- Migration helper utilities (temporary)

```javascript
// Temporary migration helper (will be removed in v1.0)
function migrateLegacyTheme(legacyThemeClass) {
  console.warn('Legacy theme classes are deprecated. Please migrate to CSS custom properties.');
  // Helper logic to convert legacy themes
}
```

---

For questions about theme migration, please refer to the documentation or open an issue in the GitHub repository.

