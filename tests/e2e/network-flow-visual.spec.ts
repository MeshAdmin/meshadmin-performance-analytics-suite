import { test, expect } from '@playwright/test';

test.describe('Network Flow Master - Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for any animations to complete
    await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
    
    // Hide dynamic elements that could cause flaky tests
    await page.addStyleTag({
      content: `
        /* Hide timestamps and other dynamic content */
        .timestamp, .current-time, .last-updated { visibility: hidden !important; }
        /* Disable animations */
        *, *::before, *::after { 
          animation-duration: 0s !important; 
          animation-delay: 0s !important; 
          transition-duration: 0s !important; 
          transition-delay: 0s !important; 
        }
      `
    });
  });

  test('Home page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await page.waitForLoadState('networkidle');
    
    // Wait for main content to load
    await expect(page.locator('.page-header')).toBeVisible();
    await expect(page.locator('.feature-card')).toHaveCount(6);
    
    // Take full page screenshot
    await expect(page).toHaveScreenshot('network-flow-home.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Dashboard page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000/dashboard');
    await page.waitForLoadState('networkidle');
    
    // Wait for dashboard components to load
    await page.waitForTimeout(2000); // Allow charts to render
    
    // Take screenshot of the main dashboard area
    await expect(page).toHaveScreenshot('network-flow-dashboard.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Analytics page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000/analyzer');
    await page.waitForLoadState('networkidle');
    
    // Wait for analytics components
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('network-flow-analytics.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('AI Insights page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000/ai_insights');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('network-flow-ai-insights.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Device Info page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000/device_info');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('network-flow-device-info.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Navigation and layout consistency', async ({ page }) => {
    // Test that navigation is consistent across pages
    await page.goto('http://localhost:5000');
    
    // Take screenshot of header/navigation area only
    const nav = page.locator('nav, .navbar, header').first();
    if (await nav.isVisible()) {
      await expect(nav).toHaveScreenshot('network-flow-navigation.png');
    }
  });

  test('Feature cards layout snapshot', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await page.waitForLoadState('networkidle');
    
    // Take screenshot of just the feature cards section
    const featureSection = page.locator('.row').first();
    await expect(featureSection).toHaveScreenshot('network-flow-features.png');
  });

  test('Mobile responsive - key breakpoints', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    await page.goto('http://localhost:5000');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('network-flow-mobile-375.png', {
      fullPage: true,
      animations: 'disabled'
    });

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 }); // iPad
    await page.goto('http://localhost:5000');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('network-flow-tablet-768.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Dark mode visual regression', async ({ page, browserName }) => {
    // Skip for webkit as it doesn't support forced-colors well
    test.skip(browserName === 'webkit', 'WebKit has limited forced-colors support');
    
    // Enable dark mode via media query
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('http://localhost:5000');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('network-flow-dark-mode.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });
});

