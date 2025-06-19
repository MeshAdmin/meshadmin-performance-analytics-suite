import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // Test directory
  testDir: './tests/e2e',
  
  // Directory for visual comparison screenshots
  snapshotDir: './tests/visual-snapshots',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use. See https://playwright.dev/docs/test-reporters
  reporter: [
    ['html', { outputFolder: './test-results/html-report' }],
    ['junit', { outputFile: './test-results/junit.xml' }],
    ['json', { outputFile: './test-results/results.json' }]
  ],
  
  // Shared settings for all the projects below
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: 'http://localhost:8000',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Capture screenshot on failure
    screenshot: 'only-on-failure',
    
    // Capture video on failure
    video: 'retain-on-failure',
    
    // Expect timeouts
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Enable accessibility testing
        colorScheme: 'light',
      },
    },
    
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    
    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
    
    // High contrast mode for accessibility testing
    {
      name: 'chromium-high-contrast',
      use: {
        ...devices['Desktop Chrome'],
        colorScheme: 'dark',
        forcedColors: 'active',
      },
    },
  ],

  // Visual comparison settings
  expect: {
    // Threshold for pixel comparison (0-1, where 0.2 = 20% difference allowed)
    toHaveScreenshot: { 
      threshold: 0.2,
      // Animation handling
      animations: 'disabled',
      // Clipping mask for dynamic content
      clip: { x: 0, y: 0, width: 1280, height: 720 }
    },
    toMatchSnapshot: { 
      threshold: 0.2,
      animations: 'disabled'
    }
  },

  // Run your local dev server before starting the tests
  webServer: [
    {
      command: 'cd apps/network-flow-master && python app.py',
      port: 5000,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'cd apps/observability-dashboard && python app.py',
      port: 8080,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    }
  ],
});

