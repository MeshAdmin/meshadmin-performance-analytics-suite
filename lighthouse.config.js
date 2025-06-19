module.exports = {
  extends: 'lighthouse:default',
  
  settings: {
    // Audit categories to run
    onlyCategories: [
      'performance',
      'accessibility', 
      'best-practices',
      'seo'
    ],
    
    // Skip PWA audits since our apps may not be PWAs
    skipAudits: [
      'service-worker',
      'works-offline', 
      'installable-manifest',
      'splash-screen',
      'themed-omnibox',
      'content-width'
    ],
    
    // Performance budgets
    budgets: [
      {
        path: '/*',
        timings: [
          {
            metric: 'first-contentful-paint',
            budget: 2000,
            tolerance: 200
          },
          {
            metric: 'largest-contentful-paint', 
            budget: 3000,
            tolerance: 300
          },
          {
            metric: 'speed-index',
            budget: 3000,
            tolerance: 300
          },
          {
            metric: 'interactive',
            budget: 4000,
            tolerance: 400
          },
          {
            metric: 'total-blocking-time',
            budget: 300,
            tolerance: 50
          }
        ],
        resourceSizes: [
          {
            resourceType: 'script',
            budget: 500
          },
          {
            resourceType: 'stylesheet',
            budget: 100
          },
          {
            resourceType: 'image',
            budget: 1000
          },
          {
            resourceType: 'document',
            budget: 50
          },
          {
            resourceType: 'font',
            budget: 200
          },
          {
            resourceType: 'total',
            budget: 2000
          }
        ],
        resourceCounts: [
          {
            resourceType: 'script',
            budget: 10
          },
          {
            resourceType: 'stylesheet',
            budget: 5
          },
          {
            resourceType: 'image',
            budget: 20
          },
          {
            resourceType: 'total',
            budget: 50
          }
        ]
      }
    ],
    
    // Throttling configuration
    throttling: {
      rttMs: 40,
      throughputKbps: 10240,
      cpuSlowdownMultiplier: 1,
      requestLatencyMs: 0,
      downloadThroughputKbps: 0,
      uploadThroughputKbps: 0
    },
    
    // Accessibility configuration  
    accessibility: {
      // Color contrast ratio requirements
      colorContrastRatio: 4.5, // WCAG AA standard
      
      // Additional accessibility audits
      additionalAudits: [
        'aria-allowed-attr',
        'aria-hidden-body',
        'aria-hidden-focus', 
        'aria-input-field-name',
        'aria-required-attr',
        'aria-required-children',
        'aria-required-parent',
        'aria-roles',
        'aria-valid-attr-value',
        'aria-valid-attr',
        'audio-caption',
        'button-name',
        'bypass',
        'color-contrast',
        'definition-list',
        'dlitem',
        'document-title',
        'duplicate-id-active',
        'duplicate-id-aria',
        'focus-traps',
        'focusable-controls',
        'form-field-multiple-labels',
        'frame-title',
        'heading-order',
        'html-has-lang',
        'html-lang-valid',
        'image-alt',
        'input-image-alt',
        'label',
        'landmark-one-main',
        'link-name',
        'list',
        'listitem',
        'meta-refresh',
        'meta-viewport',
        'object-alt',
        'tabindex',
        'table-fake-caption',
        'td-headers-attr',
        'th-has-data-cells',
        'valid-lang',
        'video-caption'
      ]
    }
  },
  
  // Custom audit configurations
  audits: [
    // Add custom accessibility audits
    {
      path: 'lighthouse/lighthouse-core/audits/accessibility/color-contrast.js',
      options: {
        // Require higher contrast ratio
        requiredRatio: 4.5
      }
    }
  ],
  
  // Custom categories
  categories: {
    performance: {
      title: 'Performance',
      auditRefs: [
        {id: 'first-contentful-paint', weight: 10, group: 'metrics'},
        {id: 'largest-contentful-paint', weight: 25, group: 'metrics'},
        {id: 'cumulative-layout-shift', weight: 25, group: 'metrics'},
        {id: 'total-blocking-time', weight: 30, group: 'metrics'},
        {id: 'speed-index', weight: 10, group: 'metrics'}
      ]
    },
    accessibility: {
      title: 'Accessibility',
      description: 'These checks ensure your app is accessible to all users.',
      manualDescription: 'Additional manual checks required for full accessibility compliance.',
      auditRefs: [
        {id: 'color-contrast', weight: 3, group: 'a11y-color-contrast'},
        {id: 'image-alt', weight: 10, group: 'a11y-names-labels'},
        {id: 'label', weight: 10, group: 'a11y-names-labels'},
        {id: 'link-name', weight: 3, group: 'a11y-names-labels'},
        {id: 'button-name', weight: 10, group: 'a11y-names-labels'}
      ]
    }
  },
  
  // Report output configuration
  output: ['json', 'html'],
  
  // Chrome flags for consistent results
  chromeFlags: [
    '--disable-web-security',
    '--disable-features=TranslateUI',
    '--disable-extensions',
    '--no-sandbox',
    '--disable-dev-shm-usage'
  ]
};

