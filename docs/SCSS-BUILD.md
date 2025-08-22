# SCSS Build Pipeline Documentation

## Overview

The observability dashboard now uses a comprehensive SCSS build pipeline that compiles into the existing `static/css/styles.css` file. This setup makes future palette changes easy and avoids duplicated hex values.

## Directory Structure

```
apps/observability-dashboard/src/scss/
├── abstracts/
│   ├── _variables.scss     # Color palette, typography, spacing
│   ├── _mixins.scss        # Utility mixins for common patterns
│   └── _index.scss         # Forwards all abstracts
└── main.scss              # Main SCSS file that compiles to styles.css
```

## Available NPM Scripts

### Production Build (recommended)
```bash
pnpm scss:build
```
Compiles SCSS to CSS without source maps for production use.

### Development Build
```bash
pnpm scss:build:dev
```
Compiles SCSS to CSS with source maps for development debugging.

### Watch Mode for Development
```bash
pnpm scss:watch
```
Watches for changes and automatically recompiles SCSS without source maps.

### Watch Mode with Source Maps
```bash
pnpm scss:watch:dev
```
Watches for changes and automatically recompiles SCSS with source maps for debugging.

## Variables Available

### Color Palette
- **Primary Colors**: `$color-primary`, `$color-primary-light`, `$color-primary-dark`
- **Background Colors**: `$bg-primary`, `$bg-secondary`, `$bg-tertiary`, `$bg-card`, `$bg-hover`
- **Text Colors**: `$color-primary-text`, `$color-secondary-text`
- **Semantic Colors**: `$color-success`, `$color-warning`, `$color-error`, `$color-info`, `$color-critical`

### Typography
- **Font Families**: `$font-family-primary`, `$font-family-mono`
- **Font Sizes**: `$font-size-xs` through `$font-size-3xl`
- **Font Weights**: `$font-weight-light` through `$font-weight-bold`

### Spacing Scale
- **Spacing**: `$spacing-xs` (4px) through `$spacing-2xl` (48px)
- **Component Padding**: `$padding-btn`, `$padding-card`, `$padding-form-control`

### Breakpoints
- **Responsive**: `$breakpoint-sm`, `$breakpoint-md`, `$breakpoint-lg`, `$breakpoint-xl`

## Useful Mixins

### Layout & Flexbox
```scss
@include flex-center;           // Centers content with flexbox
@include flex-between;          // Space-between layout
@include flex-column-center;    // Vertical centered column
@include container;             // Max-width container with padding
```

### Grid Utilities
```scss
@include grid-auto-fit(300px);  // Auto-fit grid with min column width
@include grid-auto-fill(250px); // Auto-fill grid with min column width
```

### Components
```scss
@include card-base;             // Base card styling
@include card-hover;            // Hover effects for cards
@include theme-card;            // Complete themed card
@include btn-variant($bg, $text); // Custom button variant
@include badge-variant($bg, $text); // Custom badge variant
```

### Responsive Design
```scss
@include mobile-only {          // Mobile breakpoint only
  // styles here
}

@include tablet-up {            // Tablet and up
  // styles here
}

@include desktop-up {           // Desktop and up
  // styles here
}

@include respond-above(768px) { // Custom breakpoint
  // styles here
}
```

### Form Elements
```scss
@include form-control;          // Themed form input
@include form-group;            // Form group spacing
@include form-label;            // Form label styling
```

## Making Palette Changes

To change the color palette, simply modify the variables in `src/scss/abstracts/_variables.scss`:

```scss
// Example: Change primary color from dark red to blue
$color-primary: #2563eb;        // Blue
$color-primary-light: #3b82f6;  // Lighter blue
$color-primary-dark: #1d4ed8;   // Darker blue
```

Then run:
```bash
pnpm scss:build
```

The changes will automatically propagate throughout the entire stylesheet.

## Benefits

1. **DRY Principle**: No more duplicated color values
2. **Easy Theming**: Change the entire color scheme by modifying a few variables
3. **Powerful Mixins**: Reusable patterns for consistent styling
4. **Modern SCSS**: Uses modern `@use` syntax instead of deprecated `@import`
5. **Watch Mode**: Automatic compilation during development
6. **Source Maps**: Available for debugging in development mode

## Example Usage

### Creating a new themed component:

```scss
.my-custom-widget {
  @include theme-card;
  
  .header {
    @include flex-between;
    padding: $spacing-base;
    color: $color-primary;
    border-bottom: 1px solid $border-primary;
  }
  
  .content {
    padding: $spacing-base;
    color: $color-secondary-text;
  }
  
  @include mobile-only {
    margin: $spacing-sm;
  }
}
```

This approach ensures consistency with the existing design system while making it easy to maintain and extend.

