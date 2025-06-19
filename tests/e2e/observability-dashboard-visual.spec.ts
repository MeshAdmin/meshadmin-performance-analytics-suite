import { test, expect } from '@playwright/test';

test.describe('Observability Dashboard - Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for any animations to complete
    await page.goto('http://localhost:8080', { waitUntil: 'networkidle' });
    
    // Hide dynamic elements that could cause flaky tests
    await page.addStyleTag({
      content: `
        /* Hide timestamps and other dynamic content */
        .timestamp, .current-time, .last-updated, .real-time-data { visibility: hidden !important; }
        /* Disable animations */
        *, *::before, *::after { 
          animation-duration: 0s !important; 
          animation-delay: 0s !important; 
          transition-duration: 0s !important; 
          transition-delay: 0s !important; 
        }
        /* Hide dynamic charts that change constantly */
        .chart-container canvas { opacity: 0.8 !important; }
      `
    });
  });

  test('Dashboard home page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    
    // Wait for dashboard widgets to load
    await page.waitForTimeout(2000);
    
    await expect(page).toHaveScreenshot('dashboard-home.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Sites management page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:8080/sites');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-sites.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Site details page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:8080/site_details');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-site-details.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Devices page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:8080/devices');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-devices.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Report builder page visual snapshot', async ({ page }) => {
    await page.goto('http://localhost:8080/report_builder');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-report-builder.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Sidebar navigation consistency', async ({ page }) => {
    await page.goto('http://localhost:8080');
    
    // Take screenshot of sidebar navigation
    const sidebar = page.locator('.sidebar, .nav-sidebar, .side-nav').first();
    if (await sidebar.isVisible()) {
      await expect(sidebar).toHaveScreenshot('dashboard-sidebar.png');
    }
  });

  test('Dashboard widgets layout', async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    
    // Wait for widgets to render
    await page.waitForTimeout(2000);
    
    // Take screenshot of main content area (excluding sidebar)
    const mainContent = page.locator('.main-content, .content-area, main').first();
    if (await mainContent.isVisible()) {
      await expect(mainContent).toHaveScreenshot('dashboard-widgets.png');
    }
  });

  test('Responsive design - tablet view', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1500);
    
    await expect(page).toHaveScreenshot('dashboard-tablet.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Responsive design - mobile view', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1500);
    
    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Theme variations', async ({ page }) => {
    // Test light theme (default)
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-light-theme.png', {
      fullPage: true,
      animations: 'disabled'
    });
    
    // Test dark theme if available
    const themeToggle = page.locator('[data-bs-theme-value="dark"], .theme-toggle, .dark-mode-toggle').first();
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      await page.waitForTimeout(500);
      
      await expect(page).toHaveScreenshot('dashboard-dark-theme.png', {
        fullPage: true,
        animations: 'disabled'
      });
    }
  });

  test('High contrast mode accessibility', async ({ page, browserName }) => {
    test.skip(browserName === 'webkit', 'WebKit has limited forced-colors support');
    
    await page.emulateMedia({ forcedColors: 'active' });
    await page.goto('http://localhost:8080');
    await page.waitForLoadState('networkidle');
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('dashboard-high-contrast.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('Form layouts consistency', async ({ page }) => {
    await page.goto('http://localhost:8080/report_builder');
    await page.waitForLoadState('networkidle');
    
    // Take screenshot of form elements
    const forms = page.locator('form, .form-container').first();
    if (await forms.isVisible()) {
      await expect(forms).toHaveScreenshot('dashboard-forms.png');
    }
  });
});

