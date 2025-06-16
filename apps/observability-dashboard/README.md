# MASH - Mesh Admin System Heuristics

MASH is a comprehensive observability dashboard for MSPs to monitor, analyze, and report on network infrastructure data across multiple customer sites.

## Project Overview

MASH integrates multiple data sources (Syslog, SNMP Traps, NetFlow, sFlow, Windows Events, OTEL metrics/traces) with full correlation capabilities. The system supports multi-tenant monitoring across different customer sites with report building, drill-down analysis, and customizable alerts/notifications while interfacing with other MeshAdmin applications.

## Development Status

### Completed Features
- ✅ Core application structure with Flask framework
- ✅ Database models for users, organizations, sites, devices, logs, metrics, dashboards, widgets, reports, alerts
- ✅ Data collectors for all supported sources (Syslog, SNMP, NetFlow, sFlow, Windows Events, OTEL)
- ✅ Background services for data processing and alert management
- ✅ Theme system with customizable color schemes (dark, light, dark_red modes)

### Current Progress
- ✅ Fixed theme system (now using matte black with dark red accents)
- ✅ Implemented organization management UI in customers module
- ✅ Implemented device inventory view and management interface
- ✅ Implemented real-time metrics dashboard with Chart.js
- 🔄 Working on alert rule creation and management interface

### Current To-Do Items
1. ✅ Implement organization management UI in customers module
   - Created templates for organization, site, and device management
   - Added JavaScript for interactive UI elements
   - Implemented API endpoints for CRUD operations
   - Added CSS styling for consistent appearance
2. ✅ Create device inventory view and management interface
   - Created comprehensive device listing with filtering and sorting
   - Implemented device details page with performance metrics
   - Added device monitoring configuration interface
   - Implemented device CRUD operations via API endpoints
   - Added data visualization with Chart.js for device metrics
3. ✅ Implement real-time metrics dashboard with Chart.js
   - Created dashboard template with customizable layout
   - Implemented various widget types (line charts, bar charts, pie charts, gauges, etc.)
   - Added dashboard management with create, edit, and delete functionality
   - Implemented time range selection and auto-refresh capabilities
   - Added widget configuration and customization options
4. 🔄 Add alert rule creation and management interface
5. Create custom report builder interface
6. Implement user role and permission system
7. Add data retention settings and management
8. Create network topology visualization
9. Implement multi-tenant isolation between organizations
10. Add API endpoints for integration with external systems

## Technology Stack
- Python 3.11 with Flask framework
- PostgreSQL database
- Celery and Redis for background task processing
- Chart.js for data visualization
- Modern CSS with responsive design