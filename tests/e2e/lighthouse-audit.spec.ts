import { test, expect } from '@playwright/test';
import { playAudit } from 'playwright-lighthouse';

const LIGHTHOUSE_CONFIG = {
  // Performance thresholds
  performance: 80,
  accessibility: 95,
  'best-practices': 90,
  seo: 85,
  
  // Specific metric thresholds
  'first-contentful-paint': 2000,
  'largest-contentful-paint': 3000,
  'cumulative-layout-shift': 0.1,
  'total-blocking-time': 300,
  'speed-index': 3000,
};

const PAGES_TO_AUDIT = [
  { name: 'Network Flow Home', url: 'http://localhost:5000', app: 'network-flow' },
  { name: 'Network Flow Dashboard', url: 'http://localhost:5000/dashboard', app: 'network-flow' },
  { name: 'Network Flow Analytics', url: 'http://localhost:5000/analyzer', app: 'network-flow' },
  { name: 'Observability Dashboard Home', url: 'http://localhost:8080', app: 'dashboard' },
  { name: 'Observability Sites', url: 'http://localhost:8080/sites', app: 'dashboard' },
  { name: 'Observability Devices', url: 'http://localhost:8080/devices', app: 'dashboard' },
];

test.describe('Lighthouse Performance & Accessibility Audits', () => {
  
  PAGES_TO_AUDIT.forEach(({ name, url, app }) => {
    test(`${name} - Lighthouse Audit`, async ({ page, browserName }) => {
      // Skip for non-Chromium browsers as Lighthouse only works with Chromium
      test.skip(browserName !== 'chromium', 'Lighthouse only works with Chromium browsers');
      
      // Navigate to page and wait for it to be ready
      await page.goto(url, { waitUntil: 'networkidle' });
      
      // Wait for dynamic content to load
      await page.waitForTimeout(3000);
      
      // Run Lighthouse audit
      const lighthouseReport = await playAudit({
        page,
        port: 9222, // Chrome debugging port
        config: {
          extends: 'lighthouse:default',
          settings: {
            onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
            // Skip PWA for now as our apps may not be PWAs
            skipAudits: ['service-worker', 'works-offline', 'installable-manifest'],
          }
        },
        reports: {
          formats: {
            json: true,
            html: true,
          },
          name: `lighthouse-${app}-${name.toLowerCase().replace(/\s+/g, '-')}`,
          directory: './test-results/lighthouse',
        }
      });
      
      // Assert core web vitals and scores
      expect(lighthouseReport.lhr.categories.performance.score * 100).toBeGreaterThanOrEqual(LIGHTHOUSE_CONFIG.performance);
      expect(lighthouseReport.lhr.categories.accessibility.score * 100).toBeGreaterThanOrEqual(LIGHTHOUSE_CONFIG.accessibility);
      expect(lighthouseReport.lhr.categories['best-practices'].score * 100).toBeGreaterThanOrEqual(LIGHTHOUSE_CONFIG['best-practices']);
      expect(lighthouseReport.lhr.categories.seo.score * 100).toBeGreaterThanOrEqual(LIGHTHOUSE_CONFIG.seo);
      
      // Assert specific performance metrics
      const audits = lighthouseReport.lhr.audits;
      
      if (audits['first-contentful-paint']) {
        expect(audits['first-contentful-paint'].numericValue).toBeLessThanOrEqual(LIGHTHOUSE_CONFIG['first-contentful-paint']);
      }
      
      if (audits['largest-contentful-paint']) {
        expect(audits['largest-contentful-paint'].numericValue).toBeLessThanOrEqual(LIGHTHOUSE_CONFIG['largest-contentful-paint']);
      }
      
      if (audits['cumulative-layout-shift']) {
        expect(audits['cumulative-layout-shift'].numericValue).toBeLessThanOrEqual(LIGHTHOUSE_CONFIG['cumulative-layout-shift']);
      }
      
      if (audits['total-blocking-time']) {
        expect(audits['total-blocking-time'].numericValue).toBeLessThanOrEqual(LIGHTHOUSE_CONFIG['total-blocking-time']);
      }
      
      if (audits['speed-index']) {
        expect(audits['speed-index'].numericValue).toBeLessThanOrEqual(LIGHTHOUSE_CONFIG['speed-index']);
      }
    });
  });

  test('Accessibility specific checks', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Lighthouse only works with Chromium browsers');
    
    // Test the main dashboard for comprehensive accessibility
    await page.goto('http://localhost:8080', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const lighthouseReport = await playAudit({
      page,
      port: 9222,
      config: {
        extends: 'lighthouse:default',
        settings: {
          onlyCategories: ['accessibility'],
          // Include additional accessibility audits
          onlyAudits: [
            'color-contrast',
            'image-alt',
            'label',
            'link-name',
            'button-name',
            'document-title',
            'html-has-lang',
            'html-lang-valid',
            'meta-viewport',
            'aria-allowed-attr',
            'aria-required-attr',
            'aria-valid-attr-value',
            'aria-valid-attr',
            'focus-traps',
            'focusable-controls',
            'interactive-element-affordance',
            'logical-tab-order',
            'managed-focus',
            'use-landmarks',
          ]
        }
      },
      reports: {
        formats: { json: true, html: true },
        name: 'accessibility-deep-audit',
        directory: './test-results/lighthouse',
      }
    });
    
    // Strict accessibility requirements
    expect(lighthouseReport.lhr.categories.accessibility.score * 100).toBeGreaterThanOrEqual(95);
    
    // Check specific accessibility audits
    const audits = lighthouseReport.lhr.audits;
    
    // Color contrast must pass
    expect(audits['color-contrast'].score).toBe(1);
    
    // Images must have alt text
    expect(audits['image-alt'].score).toBe(1);
    
    // Form elements must have labels
    expect(audits['label'].score).toBe(1);
    
    // Links must have descriptive text
    expect(audits['link-name'].score).toBe(1);
    
    // Buttons must have accessible names
    expect(audits['button-name'].score).toBe(1);
  });

  test('Performance budget enforcement', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Lighthouse only works with Chromium browsers');
    
    // Test the most complex page (dashboard) for performance budget
    await page.goto('http://localhost:5000/dashboard', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    const lighthouseReport = await playAudit({
      page,
      port: 9222,
      config: {
        extends: 'lighthouse:default',
        settings: {
          onlyCategories: ['performance'],
          // Performance budget configuration
          budgets: [{
            path: '/*',
            timings: [
              { metric: 'first-contentful-paint', budget: 2000 },
              { metric: 'largest-contentful-paint', budget: 3000 },
              { metric: 'speed-index', budget: 3000 },
              { metric: 'interactive', budget: 4000 }
            ],
            resourceSizes: [
              { resourceType: 'script', budget: 500 },
              { resourceType: 'stylesheet', budget: 100 },
              { resourceType: 'image', budget: 1000 },
              { resourceType: 'total', budget: 2000 }
            ]
          }]
        }
      },
      reports: {
        formats: { json: true, html: true },
        name: 'performance-budget-audit',
        directory: './test-results/lighthouse',
      }
    });
    
    // Assert performance score is maintained
    expect(lighthouseReport.lhr.categories.performance.score * 100).toBeGreaterThanOrEqual(80);
    
    // Check resource budgets
    const audits = lighthouseReport.lhr.audits;
    
    if (audits['resource-summary']) {
      const resourceSummary = audits['resource-summary'].details;
      if (resourceSummary && resourceSummary.items) {
        const totalSize = resourceSummary.items.reduce((sum, item) => sum + (item.size || 0), 0);
        expect(totalSize).toBeLessThanOrEqual(2000 * 1024); // 2MB budget
      }
    }
  });

  test('Mobile performance audit', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Lighthouse only works with Chromium browsers');
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Test mobile performance on key pages
    await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const lighthouseReport = await playAudit({
      page,
      port: 9222,
      config: {
        extends: 'lighthouse:default',
        settings: {
          onlyCategories: ['performance', 'accessibility'],
          formFactor: 'mobile',
          throttling: {
            rttMs: 150,
            throughputKbps: 1638.4,
            cpuSlowdownMultiplier: 4,
          }
        }
      },
      reports: {
        formats: { json: true, html: true },
        name: 'mobile-performance-audit',
        directory: './test-results/lighthouse',
      }
    });
    
    // Mobile performance should be slightly lower than desktop but still good
    expect(lighthouseReport.lhr.categories.performance.score * 100).toBeGreaterThanOrEqual(70);
    expect(lighthouseReport.lhr.categories.accessibility.score * 100).toBeGreaterThanOrEqual(95);
  });
});

