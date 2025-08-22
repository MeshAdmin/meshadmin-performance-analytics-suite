import { errorHandler, setupErrorHandling } from './src/error-handling';
/**
 * Interactive tooltips for server metrics
 * This script creates rich, interactive tooltips for displaying server metrics.
 */

class ServerMetricsTooltips {
    constructor() {
        this.tooltips = new Map();
        this.darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.theme = this.darkMode ? 'dark' : 'light';
        this.colorScheme = {
            dark: {
                background: '#424242',
                border: '#666666',
                text: '#FFFFFF',
                header: '#BBDEFB',
                success: '#81C784',
                warning: '#FFD54F',
                danger: '#E57373',
                chart: {
                    grid: '#666666',
                    line: '#42A5F5',
                    fill: 'rgba(66, 165, 245, 0.2)'
                }
            },
            light: {
                background: '#FFFFFF',
                border: '#E0E0E0',
                text: '#212121',
                header: '#1976D2',
                success: '#388E3C',
                warning: '#FFA000',
                danger: '#D32F2F',
                chart: {
                    grid: '#E0E0E0',
                    line: '#1976D2',
                    fill: 'rgba(25, 118, 210, 0.1)'
                }
            }
        };
    }
    
    /**
     * Initialize tooltips for elements with a specific data attribute
     */
    initialize(selector = '[data-server-tooltip]') {
        const elements = document.querySelectorAll(selector);
        
        elements.forEach(el => {
            const serverId = el.getAttribute('data-server-id');
            if (!serverId) return;
            
            // Create tooltip instance
            if (!this.tooltips.has(serverId)) {
                const tooltip = document.createElement('div');
                tooltip.className = 'server-tooltip';
                tooltip.style.position = 'absolute';
                tooltip.style.zIndex = '1000';
                tooltip.style.display = 'none';
                tooltip.style.pointerEvents = 'none';
                tooltip.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
                tooltip.style.borderRadius = '4px';
                tooltip.style.padding = '0';
                tooltip.style.maxWidth = '320px';
                tooltip.style.backgroundColor = this.colorScheme[this.theme].background;
                tooltip.style.border = `1px solid ${this.colorScheme[this.theme].border}`;
                tooltip.style.color = this.colorScheme[this.theme].text;
                
                document.body.appendChild(tooltip);
                this.tooltips.set(serverId, tooltip);
            }
            
            // Attach event listeners
            el.addEventListener('mouseenter', e => this.showTooltip(e, serverId));
            el.addEventListener('mouseleave', e => this.hideTooltip(serverId));
            el.addEventListener('mousemove', e => this.positionTooltip(e, serverId));
        });
    }
    
    /**
     * Show tooltip for a specific server
     */
    showTooltip(event, serverId) {
        const tooltip = this.tooltips.get(serverId);
        if (!tooltip) return;
        
        // Get server data from the element
        const target = event.currentTarget;
        const serverData = this.getServerData(target);
        
        // Update tooltip content
        this.updateTooltipContent(tooltip, serverData);
        
        // Position and show tooltip
        this.positionTooltip(event, serverId);
        tooltip.style.display = 'block';
        
        // Start/resume mini chart animation if present
        const miniChart = tooltip.querySelector('.mini-chart');
        if (miniChart && miniChart._chart) {
            miniChart._chart.play();
        }
    }
    
    /**
     * Hide tooltip for a specific server
     */
    hideTooltip(serverId) {
        const tooltip = this.tooltips.get(serverId);
        if (!tooltip) return;
        
        tooltip.style.display = 'none';
        
        // Pause mini chart animation if present
        const miniChart = tooltip.querySelector('.mini-chart');
        if (miniChart && miniChart._chart) {
            miniChart._chart.pause();
        }
    }
    
    /**
     * Position tooltip based on mouse position
     */
    positionTooltip(event, serverId) {
        const tooltip = this.tooltips.get(serverId);
        if (!tooltip || tooltip.style.display === 'none') return;
        
        const x = event.pageX;
        const y = event.pageY;
        
        // Position tooltip relative to mouse pointer
        tooltip.style.left = `${x + 15}px`;
        tooltip.style.top = `${y - 15}px`;
        
        // Ensure tooltip stays in viewport
        const rect = tooltip.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (rect.right > viewportWidth) {
            tooltip.style.left = `${x - rect.width - 15}px`;
        }
        
        if (rect.bottom > viewportHeight) {
            tooltip.style.top = `${y - rect.height - 15}px`;
        }
    }
    
    /**
     * Extract server data from element data attributes
     */
    getServerData(element) {
        return {
            id: element.getAttribute('data-server-id'),
            name: element.getAttribute('data-server-name') || 'Unknown Server',
            host: element.getAttribute('data-server-host') || 'localhost',
            port: element.getAttribute('data-server-port') || '80',
            status: element.getAttribute('data-server-status') || 'unknown',
            responseTime: parseInt(element.getAttribute('data-server-response-time') || '0', 10),
            connections: parseInt(element.getAttribute('data-server-connections') || '0', 10),
            healthChecks: parseInt(element.getAttribute('data-server-health-checks') || '0', 10),
            failedChecks: parseInt(element.getAttribute('data-server-failed-checks') || '0', 10),
            weight: parseInt(element.getAttribute('data-server-weight') || '1', 10),
            type: element.getAttribute('data-server-type') || 'backend'
        };
    }
    
    /**
     * Update tooltip content with server data
     */
    updateTooltipContent(tooltip, server) {
        // Determine status color
        let statusColor, statusText;
        if (server.status === 'healthy') {
            statusColor = this.colorScheme[this.theme].success;
            statusText = 'HEALTHY';
        } else if (server.status === 'unhealthy') {
            statusColor = this.colorScheme[this.theme].danger;
            statusText = 'UNHEALTHY';
        } else {
            statusColor = this.colorScheme[this.theme].warning;
            statusText = 'UNKNOWN';
        }
        
        let content = `
            <div style="padding: 10px; background-color: ${this.colorScheme[this.theme].header}; border-top-left-radius: 4px; border-top-right-radius: 4px; font-weight: bold; color: ${this.theme === 'dark' ? '#000' : '#fff'}">
                ${server.name}
            </div>
            <div style="padding: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <div style="font-weight: bold; margin-bottom: 3px;">Address</div>
                        <div>${server.host}:${server.port}</div>
                    </div>
                    <div>
                        <div style="font-weight: bold; margin-bottom: 3px;">Status</div>
                        <div style="color: ${statusColor}; font-weight: bold;">${statusText}</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 3px;">Response Time</div>
                    <div class="progress" style="height: 8px; background-color: ${this.colorScheme[this.theme].border}; border-radius: 4px; position: relative; overflow: hidden; margin-top: 5px;">
                        <div class="progress-bar" style="height: 100%; width: ${Math.min(100, server.responseTime / 5)}%; background-color: ${server.responseTime > 300 ? this.colorScheme[this.theme].danger : (server.responseTime > 100 ? this.colorScheme[this.theme].warning : this.colorScheme[this.theme].success)}; border-radius: 4px;"></div>
                    </div>
                    <div style="text-align: right; font-size: 12px; margin-top: 2px;">${server.responseTime} ms</div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <div style="font-weight: bold; margin-bottom: 3px;">Active Connections</div>
                        <div>${server.connections}</div>
                    </div>
                    <div>
                        <div style="font-weight: bold; margin-bottom: 3px;">Weight</div>
                        <div>${server.weight}</div>
                    </div>
                </div>
                
                <div style="font-weight: bold; margin-bottom: 3px;">Health Checks</div>
                <div style="font-size: 12px;">
                    Total: ${server.healthChecks} | Failed: ${server.failedChecks}
                </div>
                
                <div class="mini-chart" style="height: 60px; margin-top: 10px;"></div>
            </div>
        `;
        
        tooltip.innerHTML = content;
        
        // Create mini sparkline chart
        const miniChartEl = tooltip.querySelector('.mini-chart');
        if (miniChartEl) {
            this.createMiniChart(miniChartEl, server);
        }
    }
    
    /**
     * Create a mini chart for the tooltip
     */
    createMiniChart(element, server) {
        // Generate some fake data points for the mini chart
        const now = Date.now();
        const data = Array.from({length: 20}, (_, i) => {
            const time = now - (19 - i) * 5000; // 5 second intervals
            let value;
            
            if (i < 5) {
                // Earlier values
                value = Math.floor(Math.random() * 20) + 10;
            } else if (i >= 15) {
                // Recent values - trend toward current response time
                const blend = (i - 15) / 5;
                const randomComponent = Math.floor(Math.random() * 20) + 10;
                value = Math.round(randomComponent * (1 - blend) + server.responseTime * blend);
            } else {
                // Middle values
                value = Math.floor(Math.random() * 20) + 10;
            }
            
            return {
                time,
                value
            };
        });
        
        // Add current value
        data.push({
            time: now,
            value: server.responseTime
        });
        
        // Create SVG
        const width = element.clientWidth;
        const height = element.clientHeight;
        
        // Clear existing content
        element.innerHTML = '';
        
        // Create SVG element
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.style.overflow = 'visible';
        element.appendChild(svg);
        
        // Find min and max values
        const values = data.map(d => d.value);
        const minValue = Math.max(0, Math.min(...values) * 0.8);
        const maxValue = Math.max(...values) * 1.2;
        
        // Create scales
        const xScale = time => (time - data[0].time) / (data[data.length-1].time - data[0].time) * width;
        const yScale = value => height - (value - minValue) / (maxValue - minValue) * height;
        
        // Draw grid lines
        const grid = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        svg.appendChild(grid);
        
        // Horizontal grid lines
        for (let i = 0; i <= 3; i++) {
            const y = height * i / 3;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', 0);
            line.setAttribute('x2', width);
            line.setAttribute('y1', y);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', this.colorScheme[this.theme].chart.grid);
            line.setAttribute('stroke-width', '0.5');
            line.setAttribute('stroke-dasharray', '2 2');
            grid.appendChild(line);
        }
        
        // Create line and area paths
        const linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        
        // Build paths
        let lineD = '';
        let areaD = '';
        
        data.forEach((d, i) => {
            const x = xScale(d.time);
            const y = yScale(d.value);
            
            if (i === 0) {
                lineD += `M ${x} ${y}`;
                areaD += `M ${x} ${height} L ${x} ${y}`;
            } else {
                lineD += ` L ${x} ${y}`;
                areaD += ` L ${x} ${y}`;
            }
        });
        
        // Close area path
        areaD += ` L ${width} ${height} Z`;
        
        // Set attributes
        areaPath.setAttribute('d', areaD);
        areaPath.setAttribute('fill', this.colorScheme[this.theme].chart.fill);
        
        linePath.setAttribute('d', lineD);
        linePath.setAttribute('stroke', this.colorScheme[this.theme].chart.line);
        linePath.setAttribute('stroke-width', '2');
        linePath.setAttribute('fill', 'none');
        
        svg.appendChild(areaPath);
        svg.appendChild(linePath);
        
        // Add current value point
        const currentPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        currentPoint.setAttribute('cx', width);
        currentPoint.setAttribute('cy', yScale(data[data.length-1].value));
        currentPoint.setAttribute('r', '3');
        currentPoint.setAttribute('fill', this.colorScheme[this.theme].chart.line);
        svg.appendChild(currentPoint);
        
        // Add animation to make the chart feel alive
        const animate = timestamp => {
            // Subtle animation of the last few points
            const lastPoints = data.slice(-5);
            const now = Date.now();
            
            lastPoints.forEach((d, i) => {
                const originalValue = d.value;
                const time = now - (4 - i) * 5000;
                
                // Add a small sine wave to the value
                const waveFactor = Math.sin((timestamp + i * 1000) / 1000) * (5 - i) * 0.5;
                d.value = originalValue + waveFactor;
                d.time = time;
            });
            
            // Rebuild paths
            lineD = '';
            areaD = '';
            
            data.forEach((d, i) => {
                const x = xScale(d.time);
                const y = yScale(d.value);
                
                if (i === 0) {
                    lineD += `M ${x} ${y}`;
                    areaD += `M ${x} ${height} L ${x} ${y}`;
                } else {
                    lineD += ` L ${x} ${y}`;
                    areaD += ` L ${x} ${y}`;
                }
            });
            
            // Close area path
            areaD += ` L ${width} ${height} Z`;
            
            // Update paths
            linePath.setAttribute('d', lineD);
            areaPath.setAttribute('d', areaD);
            
            // Update current point
            currentPoint.setAttribute('cy', yScale(data[data.length-1].value));
            
            if (!element._stopped) {
                element._animationFrame = requestAnimationFrame(animate);
            }
        };
        
        const chart = {
            play: () => {
                element._stopped = false;
                if (!element._animationFrame) {
                    element._animationFrame = requestAnimationFrame(animate);
                }
            },
            pause: () => {
                element._stopped = true;
                if (element._animationFrame) {
                    cancelAnimationFrame(element._animationFrame);
                    element._animationFrame = null;
                }
            }
        };
        
        element._chart = chart;
        chart.play();
    }
    
    /**
     * Update tooltip data for a specific server
     */
    updateServerData(serverId, newData) {
        const elements = document.querySelectorAll(`[data-server-id="${serverId}"]`);
        elements.forEach(el => {
            for (const [key, value] of Object.entries(newData)) {
                const attr = `data-server-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
                el.setAttribute(attr, value);
            }
        });
    }
}

// Create global instance
const serverTooltips = new ServerMetricsTooltips();