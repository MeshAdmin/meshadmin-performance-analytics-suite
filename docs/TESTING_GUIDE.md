# Visual Regression Testing & Lighthouse Audits

This project includes comprehensive visual regression testing and Lighthouse audits to ensure UI consistency, performance, and accessibility standards are maintained across all changes.

## 🎯 Overview

Our testing suite includes:

- **Visual Regression Testing**: Automated screenshot comparison to detect visual changes
- **Lighthouse Audits**: Performance, accessibility, best practices, and SEO validation  
- **Accessibility Testing**: WCAG AA compliance verification
- **Performance Budgets**: Automated enforcement of performance thresholds
- **Multi-browser Testing**: Cross-browser compatibility validation

## 🏗️ Architecture

### Test Structure
```
tests/
├── e2e/
│   ├── network-flow-visual.spec.ts       # Visual tests for Network Flow Master
│   ├── observability-dashboard-visual.spec.ts  # Visual tests for Dashboard
│   └── lighthouse-audit.spec.ts          # Lighthouse performance/accessibility audits
├── visual-snapshots/                     # Stored reference screenshots
│   ├── chromium/
│   ├── firefox/
│   └── webkit/
└── test-results/                         # Test output and reports
    ├── lighthouse/                       # Lighthouse HTML/JSON reports
    └── html-report/                      # Playwright test reports
```

### Applications Tested
- **Network Flow Master** (`localhost:5000`)
  - Home page
  - Dashboard
  - Analytics page
  - AI Insights
  - Device Info
  
- **Observability Dashboard** (`localhost:8080`)
  - Dashboard home
  - Sites management
  - Site details
  - Devices page
  - Report builder

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- pnpm 8+
- Chrome/Chromium browser

### Installation
```bash
# Install dependencies
pnpm install

# Install Playwright browsers
pnpm run playwright:install

# Make scripts executable (Unix/Mac only)
chmod +x scripts/run-visual-tests.sh
```

### Running Tests

#### All Tests
```bash
# Run complete test suite
pnpm run test:qa

# Or using the script directly
./scripts/run-visual-tests.sh all
```

#### Specific Test Types
```bash
# Visual regression only
pnpm run test:visual

# Lighthouse audits only  
pnpm run test:lighthouse

# Accessibility tests only
pnpm run test:accessibility

# Performance budget tests only
pnpm run test:performance
```

#### Playwright Commands
```bash
# Interactive test runner
pnpm run playwright:ui

# Generate/update visual snapshots
pnpm exec playwright test --update-snapshots

# Run specific browser
pnpm exec playwright test --project=chromium

# View test report
pnpm run playwright:report
```

## 📸 Visual Regression Testing

### How It Works
1. **Baseline Creation**: First run captures reference screenshots
2. **Comparison**: Subsequent runs compare against baselines
3. **Threshold Tolerance**: 20% pixel difference allowed by default
4. **Multi-Browser**: Tests across Chromium, Firefox, and WebKit
5. **Responsive**: Covers desktop, tablet, and mobile viewports

### Key Features
- **Dynamic Content Handling**: Hides timestamps and animations
- **Stable Screenshots**: Waits for network idle and component loading
- **Cross-Browser**: Consistent rendering across browsers
- **Accessibility Modes**: Dark mode and high contrast testing
- **Mobile Responsive**: Multiple viewport breakpoints

### Managing Visual Tests
```bash
# Update all baselines
pnpm exec playwright test --update-snapshots

# Update specific test
pnpm exec playwright test network-flow-visual.spec.ts --update-snapshots

# Review differences in UI mode
pnpm run playwright:ui
```

## 🏮 Lighthouse Audits

### Performance Thresholds
- **Performance Score**: ≥80
- **Accessibility Score**: ≥95  
- **Best Practices Score**: ≥90
- **SEO Score**: ≥85

### Core Web Vitals Budgets
- **First Contentful Paint**: ≤2.0s
- **Largest Contentful Paint**: ≤3.0s
- **Cumulative Layout Shift**: ≤0.1
- **Total Blocking Time**: ≤300ms
- **Speed Index**: ≤3.0s

### Resource Budgets
- **JavaScript**: ≤500KB
- **CSS**: ≤100KB
- **Images**: ≤1MB
- **Total Resources**: ≤2MB

### Accessibility Requirements
- **Color Contrast**: WCAG AA (4.5:1 ratio)
- **Alt Text**: Required for all images
- **Form Labels**: Required for all inputs
- **ARIA**: Proper usage validation
- **Keyboard Navigation**: Full support required

## 🔧 Configuration

### Playwright Config (`playwright.config.ts`)
- Browser configurations
- Test timeouts and retries
- Visual comparison thresholds
- Web server setup for apps

### Lighthouse Config (`lighthouse.config.js`)
- Performance budgets
- Accessibility standards  
- Chrome flags for consistency
- Custom audit weights

### GitHub Actions (`.github/workflows/visual-regression-and-lighthouse.yml`)
- Automated CI/CD pipeline
- Multi-job parallel execution
- Artifact preservation
- Failure notifications

## 📊 Reports and Artifacts

### Lighthouse Reports
- **HTML Reports**: Visual performance/accessibility reports
- **JSON Data**: Structured audit results
- **Screenshots**: Page captures during audits

### Playwright Reports  
- **HTML Report**: Interactive test results viewer
- **Screenshots**: Failure/comparison images
- **Videos**: Test execution recordings
- **Traces**: Detailed debugging information

### CI Artifacts
All test results are automatically uploaded to GitHub Actions artifacts:
- `lighthouse-reports`: Lighthouse HTML/JSON reports
- `visual-test-results-{browser}`: Visual comparison results
- `playwright-report-{browser}`: Detailed test reports

## 🛠️ Troubleshooting

### Common Issues

#### Applications Won't Start
```bash
# Check if ports are in use
lsof -ti:5000 -ti:8080

# Kill existing processes
kill $(lsof -ti:5000 -ti:8080)

# Check app dependencies
cd apps/network-flow-master && pip install -r requirements.txt
cd apps/observability-dashboard && pip install -r requirements.txt
```

#### Visual Test Failures
```bash
# Review differences visually
pnpm run playwright:ui

# Update snapshots if changes are intentional
pnpm exec playwright test --update-snapshots

# Check for dynamic content causing flakiness
# Look for timestamps, animations, or real-time data
```

#### Lighthouse Failures
```bash
# Run lighthouse directly for debugging
npx lighthouse http://localhost:5000 --chrome-flags="--headless"

# Check Chrome debugging port
google-chrome --remote-debugging-port=9222 --headless &

# Verify performance in dev tools
# Use Chrome DevTools Performance and Lighthouse tabs
```

#### CI/CD Issues
- **App Startup**: Increase wait times in workflow
- **Dependencies**: Ensure Python requirements are correctly installed
- **Permissions**: Check script execution permissions
- **Resources**: Monitor CI runner resource usage

### Debug Commands
```bash
# Verbose test output
DEBUG=pw:* pnpm exec playwright test

# Run with headed browser
pnpm exec playwright test --headed

# Slow motion for debugging
pnpm exec playwright test --slow-mo=1000

# Single test file
pnpm exec playwright test lighthouse-audit.spec.ts
```

## 🎨 Best Practices

### Writing Visual Tests
1. **Wait for Stability**: Use `waitForLoadState('networkidle')`
2. **Hide Dynamic Content**: Use CSS to hide timestamps/animations
3. **Consistent Viewports**: Test multiple breakpoints
4. **Unique Selectors**: Use stable element selectors
5. **Meaningful Names**: Clear test and snapshot names

### Performance Testing
1. **Representative Data**: Use realistic test data
2. **Network Conditions**: Test various connection speeds
3. **Resource Monitoring**: Track asset sizes
4. **Progressive Enhancement**: Ensure basic functionality works
5. **Performance Budgets**: Set and enforce limits

### Accessibility Testing
1. **Screen Readers**: Test with assistive technologies
2. **Keyboard Navigation**: Verify full keyboard support
3. **Color Contrast**: Ensure WCAG compliance
4. **Focus Management**: Proper focus handling
5. **Semantic HTML**: Use appropriate HTML elements

## 📈 Metrics Dashboard

### Performance Tracking
Monitor trends over time for:
- Lighthouse scores
- Core Web Vitals
- Resource budgets
- Test execution time

### Quality Gates
- All visual tests must pass
- Lighthouse thresholds must be met
- No accessibility violations
- Performance budgets enforced

## 🔄 Maintenance

### Regular Tasks
- **Weekly**: Review failed tests and update baselines if needed
- **Monthly**: Update performance budgets based on improvements
- **Quarterly**: Review and update accessibility standards
- **Release**: Generate comprehensive QA reports

### Updating Baselines
Visual baselines should be updated when:
- UI changes are intentional and approved
- New features are added
- Design system updates are implemented
- Browser rendering changes occur

```bash
# Selective baseline updates
pnpm exec playwright test specific-test.spec.ts --update-snapshots

# Full baseline regeneration (use sparingly)
rm -rf tests/visual-snapshots/
pnpm exec playwright test --update-snapshots
```

## 📚 Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [Lighthouse Documentation](https://developers.google.com/web/tools/lighthouse)  
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Core Web Vitals](https://web.dev/vitals/)
- [Performance Budgets](https://web.dev/performance-budgets-101/)

## 🤝 Contributing

When contributing changes that affect the UI:

1. Run visual tests locally first
2. Update snapshots if changes are intentional
3. Ensure Lighthouse scores meet thresholds
4. Document any accessibility considerations
5. Include performance impact analysis

For questions or issues with the testing setup, please refer to the troubleshooting section or open an issue with detailed reproduction steps.

