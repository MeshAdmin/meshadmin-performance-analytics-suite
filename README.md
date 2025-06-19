# MPTCP Performance Analytics Suite

Comprehensive network flow monitoring, load balancing analytics, and observability dashboard with real-time metrics.

![MPTCP Performance Analytics Suite Dashboard](docs/images/dashboard-v0.9-ui-redesign.png)
*The new v0.9 UI featuring the Dark Red theme with improved navigation, real-time metrics, and customizable theming*

## Overview

The MPTCP Performance Analytics Suite provides a complete solution for monitoring, analyzing, and optimizing MPTCP network performance. This mono-repository consolidates multiple performance analytics tools into a unified platform designed specifically for MPTCP environments.

## Architecture

This suite consists of the following integrated components:

### Core Applications

1. **Network Flow Master** (`apps/network-flow-master/`)
   - Real-time network flow analysis and monitoring
   - MPTCP subflow tracking and correlation
   - Advanced flow analytics and pattern detection

2. **Load Balancer Pro** (`apps/load-balancer-pro/`)
   - Intelligent load balancing analytics
   - Performance optimization recommendations
   - Traffic distribution analysis

3. **Network Observability Dashboard** (`apps/observability-dashboard/`)
   - Comprehensive monitoring and visualization
   - Real-time metrics and alerts
   - Performance trend analysis

### Shared Libraries

- **Analytics Engine** (`packages/analytics-engine/`) - Core analytics processing and algorithms
- **Metrics Collection** (`packages/metrics/`) - Unified metrics collection and aggregation
- **Visualization Components** (`packages/visualization/`) - Reusable charts and dashboards
- **MPTCP Core** (`packages/mptcp-core/`) - MPTCP-specific utilities and parsers
- **Data Processing** (`packages/data-processing/`) - Stream processing and data transformation

## Features

### Real-time Performance Monitoring
- Live MPTCP connection tracking
- Subflow performance metrics
- Bandwidth utilization analysis
- Latency and throughput monitoring
- Packet loss detection and analysis

### Advanced Analytics
- Machine learning-based anomaly detection
- Performance trend prediction
- Load balancing optimization
- Network path quality assessment
- Congestion analysis and prediction

### Visualization & Reporting
- Interactive performance dashboards
- Customizable metrics visualization
- Historical performance reports
- Real-time alerting system
- Export capabilities (PDF, CSV, JSON)

### Integration Capabilities
- REST API for all functionality
- WebSocket real-time data streaming
- Prometheus metrics export
- Grafana dashboard templates
- Integration with monitoring tools

## Getting Started

### Prerequisites

- Node.js 20 LTS or later
- pnpm 8.x or later
- InfluxDB 2.x (for time-series data)
- Redis 6.x or later (for caching)
- Python 3.11+ (for observability dashboard)
- Sass compiler (for theme building)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

```bash
# Clone the repository
git clone https://github.com/MeshAdmin/mptcp-performance-analytics-suite.git
cd mptcp-performance-analytics-suite

# Install dependencies
pnpm install

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start infrastructure services
docker-compose up -d influxdb redis

# Build all packages
pnpm build

# Build themes and styles
pnpm scss:build

# Start development servers
pnpm dev
```

### Development

This is a pnpm workspace-based mono-repository:

```bash
# Work on specific app
pnpm --filter network-flow-master dev

# Run tests for all packages
pnpm test

# Run integration tests
pnpm test:integration

# Lint all code
pnpm lint

# Build for production
pnpm build

# Start production servers
pnpm start
```

## Project Structure

```
mptcp-performance-analytics-suite/
├── apps/
│   ├── network-flow-master/       # Network Flow Master application
│   ├── load-balancer-pro/         # Load Balancer Pro analytics
│   └── observability-dashboard/   # Observability Dashboard
├── packages/
│   ├── analytics-engine/          # Core analytics processing
│   ├── metrics/                   # Metrics collection and aggregation
│   ├── visualization/             # Visualization components
│   ├── mptcp-core/               # MPTCP-specific utilities
│   └── data-processing/          # Data transformation
├── infrastructure/
│   ├── docker/                   # Docker configurations
│   ├── k8s/                      # Kubernetes manifests
│   └── monitoring/               # Monitoring stack configs
├── docs/                         # Documentation
├── tools/                        # Build tools and utilities
└── examples/                     # Example configurations
```

## Configuration

### Environment Variables

```bash
# Database Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=meshadmin
INFLUXDB_BUCKET=mptcp-metrics

# Redis Configuration
REDIS_URL=redis://localhost:6379

# API Configuration
API_PORT=3000
API_HOST=0.0.0.0

# Monitoring
METRICS_INTERVAL=5000
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=85
```

### MPTCP Configuration

```yaml
mptcp:
  monitoring:
    interval: 1000  # milliseconds
    metrics:
      - subflow_count
      - bandwidth_utilization
      - latency
      - packet_loss
      - congestion_window
  
  alerting:
    thresholds:
      latency_p95: 100  # milliseconds
      packet_loss: 0.1  # percentage
      bandwidth_utilization: 90  # percentage
```

## API Documentation

### REST API Endpoints

```bash
# Get real-time metrics
GET /api/v1/metrics/realtime

# Get historical performance data
GET /api/v1/metrics/history?start=2024-01-01&end=2024-01-31

# Get MPTCP connection details
GET /api/v1/connections/{id}

# Get load balancing recommendations
GET /api/v1/recommendations/load-balancing

# Configure alerting rules
POST /api/v1/alerts/rules
```

### WebSocket Events

```javascript
// Connect to real-time metrics stream
const ws = new WebSocket('ws://localhost:3000/ws/metrics');

ws.on('metrics', (data) => {
  console.log('Real-time metrics:', data);
});

ws.on('alert', (alert) => {
  console.log('Performance alert:', alert);
});
```

## Deployment

### Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Development environment
docker-compose up -d
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f infrastructure/k8s/

# Port forward for local access
kubectl port-forward svc/analytics-dashboard 3000:3000
```

## UI Theming System

### Overview

The UI redesign includes a powerful theming system that supports:
- Multiple built-in themes (Dark Red, Dark, Light)
- Custom color wheel for accent colors
- Real-time theme switching
- CSS custom properties for seamless transitions
- Theme persistence across sessions

### Available Themes

#### 1. Dark Red Theme (Default)
- **Primary Background**: Pure black (#000000)
- **Secondary Background**: Dark grey (#1a1a1a)
- **Accent Color**: Dark red (#8B0000)
- **Text**: Light colors for high contrast

#### 2. Dark Theme
- **Primary Background**: Pure black (#000000)
- **Secondary Background**: Dark grey (#1a1a1a)
- **Accent Color**: Teal (#03dac6)
- **Text**: Light colors for high contrast

#### 3. Light Theme
- **Primary Background**: Light grey (#f5f5f5)
- **Secondary Background**: White (#ffffff)
- **Accent Color**: Teal green (#018786)
- **Text**: Dark colors for readability

### Building Themes

```bash
# Build all themes and styles (production)
pnpm scss:build

# Build with source maps for development
pnpm scss:build:dev

# Watch for changes during development
pnpm scss:watch

# Watch with source maps
pnpm scss:watch:dev
```

### Creating Custom Themes

#### Method 1: Using the Color Wheel (Runtime)

1. Click the color wheel icon in the sidebar footer
2. Choose a new accent color
3. Toggle between light/dark modes
4. Click "Apply" to save your custom theme

#### Method 2: Creating Theme Files

1. Create a new CSS file in `apps/observability-dashboard/static/css/`:

```css
/* custom_theme.css */
:root[data-theme="custom"] {
  --primary-bg: #your-bg-color;
  --secondary-bg: #your-secondary-bg;
  --accent-color: #your-accent-color;
  --primary-text: #your-text-color;
  /* ... other variables */
}
```

2. Add the theme to the theme selector in `themes.js`:

```javascript
const colorSchemes = {
  // ... existing themes
  custom: {
    name: 'Custom Theme',
    id: 'custom',
    primaryBg: '#your-bg-color',
    // ... other properties
  }
};
```

### Theme Variables

All themes use CSS custom properties for consistency:

```css
:root {
  --primary-bg: /* Main background color */
  --secondary-bg: /* Card and sidebar backgrounds */
  --tertiary-bg: /* Interactive elements */
  --primary-text: /* Main text color */
  --secondary-text: /* Secondary text color */
  --accent-color: /* Brand/highlight color */
  --border-color: /* Border and separator color */
  --hover-bg: /* Hover state background */
  --shadow: /* Box shadow definition */
}
```

### SCSS Architecture

The theming system is built using SCSS with the following structure:

```
apps/observability-dashboard/src/scss/
├── abstracts/
│   ├── _variables.scss    # Theme variables and color definitions
│   ├── _mixins.scss      # Theming mixins and utilities
│   └── _index.scss       # Abstracts barrel file
└── main.scss             # Main stylesheet with CSS custom properties
```

### Integration with Applications

Themes are automatically applied across all applications:

- **Observability Dashboard**: Full theming support with live switching
- **Network Flow Master**: Inherits theme variables for consistency
- **Load Balancer Pro**: Uses shared theme system

## Build Commands

### Complete Build Process

```bash
# Full production build
pnpm build

# Development build with file watching
pnpm dev

# Build specific application
pnpm --filter observability-dashboard build
pnpm --filter network-flow-master build
```

### SCSS/Theme Building

```bash
# Production theme build (minified, no source maps)
pnpm scss:build

# Development build (with source maps)
pnpm scss:build:dev

# Watch mode for development
pnpm scss:watch
pnpm scss:watch:dev  # With source maps
```

### Testing

```bash
# Run all tests
pnpm test

# Visual regression tests (includes theme testing)
pnpm test:visual

# Accessibility tests across themes
pnpm test:accessibility

# End-to-end tests
pnpm test:e2e

# Performance tests
pnpm test:performance

# Complete QA suite
pnpm test:qa
```

### Docker Operations

```bash
# Build Docker images
pnpm docker:build

# Start services
pnpm docker:up

# Stop services
pnpm docker:down
```

### Kubernetes Deployment

```bash
# Deploy to Kubernetes
pnpm k8s:deploy

# Remove from Kubernetes
pnpm k8s:delete
```

## Monitoring & Alerting

### Prometheus Metrics

The suite exposes Prometheus-compatible metrics at `/metrics`:

- `mptcp_connections_total` - Total MPTCP connections
- `mptcp_subflows_active` - Active subflows count
- `mptcp_bandwidth_utilization` - Bandwidth utilization percentage
- `mptcp_latency_p95` - 95th percentile latency
- `mptcp_packet_loss_rate` - Packet loss rate

### Grafana Dashboards

Pre-built Grafana dashboards are available in `monitoring/grafana/dashboards/`:

- MPTCP Performance Overview
- Network Flow Analysis
- Load Balancing Analytics
- Alert Management

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and standards
- Testing requirements
- Pull request process
- Issue reporting
- Development setup

## License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- 📧 Email: info@meshadmin.com
- 🌐 Website: https://meshadmin.com
- 📚 Documentation: https://docs.meshadmin.com
- 🐛 Issues: GitHub Issues

## Roadmap

- [ ] Machine learning-based performance prediction
- [ ] Advanced anomaly detection algorithms
- [ ] Mobile application for monitoring
- [ ] Integration with cloud providers' load balancers
- [ ] AI-powered optimization recommendations
- [ ] Real-time performance tuning automation

---

**MPTCP Performance Analytics Suite** - Creating Software for Awesomeness

