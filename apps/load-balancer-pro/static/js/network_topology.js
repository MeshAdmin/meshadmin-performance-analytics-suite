/**
 * Network Topology Visualization for the Load Balancer
 * This script creates an interactive, animated visualization of the load balancer
 * network topology using D3.js.
 */

class NetworkTopology {
    constructor(elementId) {
        this.container = d3.select(`#${elementId}`);
        this.width = this.container.node().getBoundingClientRect().width || 800;
        this.height = 400;
        this.connections = [];
        this.backends = [];
        this.stats = {};
        this.simulation = null;
        this.nodes = [];
        this.links = [];
        this.isInitialized = false;
        this.darkMode = true; // Always use dark mode for better visibility
        
        // Color scheme - enhanced for better visibility
        this.colors = {
            node: {
                loadBalancer: "#2196F3", // Bright blue
                client: "#4CAF50", // Bright green
                backend: {
                    healthy: "#4CAF50", // Bright green
                    unhealthy: "#F44336" // Bright red
                }
            },
            link: {
                active: "rgba(255, 255, 255, 0.8)", // Brighter for visibility
                inactive: "rgba(255, 255, 255, 0.3)" // More visible in dark mode
            },
            text: "#FFFFFF" // White text
        };
    }

    initialize() {
        if (this.isInitialized) return;
        
        // Create SVG
        this.svg = this.container.append("svg")
            .attr("width", this.width)
            .attr("height", this.height)
            .attr("class", "network-topology-svg");
            
        // Create arrow marker definitions
        this.svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", this.colors.link.active);
            
        // Create the link group first so it's behind nodes
        this.linkGroup = this.svg.append("g").attr("class", "links");
        this.nodeGroup = this.svg.append("g").attr("class", "nodes");
        this.labelGroup = this.svg.append("g").attr("class", "labels");
        
        // Create tooltip
        this.tooltip = d3.select("body").append("div")
            .attr("class", "topology-tooltip")
            .style("position", "absolute")
            .style("background-color", this.darkMode ? "#424242" : "#f9f9f9")
            .style("color", this.colors.text)
            .style("padding", "10px")
            .style("border-radius", "5px")
            .style("box-shadow", "0 0 10px rgba(0,0,0,0.2)")
            .style("pointer-events", "none")
            .style("opacity", 0)
            .style("z-index", 1000);
        
        // Initialize the force simulation
        this.simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .force("x", d3.forceX(this.width / 2).strength(0.1))
            .force("y", d3.forceY(this.height / 2).strength(0.1))
            .on("tick", () => this.tick());
            
        this.isInitialized = true;
        
        // Initial empty state
        this.setInitialNodesAndLinks();
        this.updateVisualization();
    }
    
    setInitialNodesAndLinks() {
        // Create the load balancer node
        const lbNode = {
            id: "loadbalancer",
            name: "Load Balancer",
            type: "loadbalancer",
            fixed: true,
            x: this.width / 2,
            y: this.height / 2
        };
        
        this.nodes = [lbNode];
        this.links = [];
    }
    
    updateData(connections, backends, stats) {
        if (!this.isInitialized) this.initialize();
        
        // Set default values for empty data
        this.connections = connections || [];
        
        // Make sure backends is an array
        if (!backends || !Array.isArray(backends) || backends.length === 0) {
            // Create mock backend nodes for demonstration if none exist
            this.backends = [
                { 
                    host: '127.0.0.1', 
                    port: 8081, 
                    healthy: true, 
                    active_connections: 0, 
                    response_time: 0 
                },
                { 
                    host: '127.0.0.1', 
                    port: 8082, 
                    healthy: true, 
                    active_connections: 0, 
                    response_time: 0 
                }
            ];
        } else {
            this.backends = backends;
        }
        
        this.stats = stats || { active_connections: 0, total_connections: 0 };
        
        // Update nodes and links based on new data
        this.updateNodesAndLinks();
        this.updateVisualization();
    }
    
    updateNodesAndLinks() {
        // Get current nodes for smooth transitions
        const existingNodesMap = {};
        if (this.nodes) {
            this.nodes.forEach(node => {
                existingNodesMap[node.id] = node;
            });
        }

        // Start with the load balancer node
        const nodes = [{
            id: "loadbalancer",
            name: "Load Balancer",
            type: "loadbalancer",
            fixed: true,
            x: this.width / 2,
            y: this.height / 2
        }];
        
        // Add backend servers with positions in a circle around the load balancer
        const backendCount = this.backends.length;
        const radius = Math.min(this.width, this.height) * 0.3; // Circle radius
        
        this.backends.forEach((backend, index) => {
            // Calculate position on a circle
            const angle = (index / backendCount) * 2 * Math.PI;
            const x = this.width / 2 + radius * Math.cos(angle);
            const y = this.height / 2 + radius * Math.sin(angle);
            
            const backendId = `backend-${backend.host}-${backend.port}`;
            
            // Preserve position if node already exists for smooth transitions
            let nodeX = x;
            let nodeY = y;
            
            if (existingNodesMap[backendId]) {
                nodeX = existingNodesMap[backendId].x || x;
                nodeY = existingNodesMap[backendId].y || y;
            }
            
            nodes.push({
                id: backendId,
                name: `${backend.host}:${backend.port}`,
                type: "backend",
                healthy: backend.healthy !== undefined ? backend.healthy : true,
                host: backend.host,
                port: backend.port,
                responseTime: backend.response_time || 0,
                connections: backend.active_connections || 0,
                x: nodeX,
                y: nodeY
            });
        });
        
        // Create a map of existing sources to prevent duplicates
        const sourceMap = new Map();
        const connMap = new Map(); // Track connections
        
        // Add client nodes and connections
        this.connections.forEach(conn => {
            if (!conn.source || !conn.destination) return;
            
            // Extract client information
            const sourceId = `client-${conn.source}`;
            
            // Check if we already have this source
            if (!sourceMap.has(conn.source)) {
                sourceMap.set(conn.source, true);
                
                // Calculate random position around the circle but farther out
                const angle = Math.random() * 2 * Math.PI;
                const outerRadius = radius * 1.8;
                const x = this.width / 2 + outerRadius * Math.cos(angle);
                const y = this.height / 2 + outerRadius * Math.sin(angle);
                
                // Preserve position if node already exists
                let nodeX = x;
                let nodeY = y;
                
                if (existingNodesMap[sourceId]) {
                    nodeX = existingNodesMap[sourceId].x || x;
                    nodeY = existingNodesMap[sourceId].y || y;
                }
                
                // Add the source node
                nodes.push({
                    id: sourceId,
                    name: conn.source,
                    type: "client",
                    x: nodeX,
                    y: nodeY
                });
            }
            
            // Parse destination and track the connection
            try {
                const destParts = conn.destination.split(':');
                if (destParts.length >= 2) {
                    const destHost = destParts[0];
                    const destPort = destParts[1];
                    const destId = `backend-${destHost}-${destPort}`;
                    
                    // Add to connection map - we'll use this to create links
                    connMap.set(`${sourceId}-${destId}`, {
                        source: sourceId,
                        target: destId,
                        id: conn.id
                    });
                }
            } catch (e) {
                console.error("Error parsing destination:", e);
            }
        });
        
        // Create links between nodes
        const links = [];
        
        // Client to load balancer links
        sourceMap.forEach((_, source) => {
            const sourceId = `client-${source}`;
            links.push({
                id: `${sourceId}-loadbalancer`,
                source: sourceId,
                target: "loadbalancer",
                active: true
            });
        });
        
        // Load balancer to backend links
        this.backends.forEach(backend => {
            const backendId = `backend-${backend.host}-${backend.port}`;
            links.push({
                id: `loadbalancer-${backendId}`,
                source: "loadbalancer",
                target: backendId,
                active: backend.active_connections > 0,
                healthy: backend.healthy !== undefined ? backend.healthy : true
            });
        });
        
        // Add direct client to backend links for visualizing connection paths
        connMap.forEach((conn, id) => {
            links.push({
                id: `direct-${id}`,
                source: conn.source,
                target: conn.target,
                active: true,
                directConnection: true
            });
        });
        
        this.nodes = nodes;
        this.links = links;
    }
    
    updateVisualization() {
        if (!this.isInitialized) return;
        
        // Update links
        const link = this.linkGroup.selectAll(".link")
            .data(this.links, d => d.id);
            
        link.exit()
            .transition()
            .duration(300)
            .attr("stroke-opacity", 0)
            .remove();
        
        const linkEnter = link.enter()
            .append("line")
            .attr("class", d => `link ${d.directConnection ? 'direct-link' : ''}`)
            .attr("stroke-width", d => d.directConnection ? 1 : 2)
            .attr("stroke-opacity", 0) // Start invisible for transition
            .attr("marker-end", d => d.directConnection ? "" : "url(#arrowhead)");
        
        // Merge and transition all links    
        this.link = linkEnter.merge(link)
            .attr("stroke", d => {
                if (d.directConnection) {
                    return "rgba(255, 255, 255, 0.2)"; // Very subtle for direct connections
                }
                if (d.target.type === "backend" && d.healthy === false) {
                    return this.colors.node.backend.unhealthy;
                }
                return d.active ? this.colors.link.active : this.colors.link.inactive;
            })
            .attr("stroke-dasharray", d => {
                if (d.directConnection) return "1,2";
                return d.active ? "none" : "3,3";
            })
            .attr("class", d => {
                let classes = "link";
                if (d.directConnection) classes += " direct-link";
                if (d.active && !d.directConnection) classes += " data-flow";
                return classes;
            })
            .transition()
            .duration(300)
            .attr("stroke-opacity", d => d.directConnection ? 0.3 : 1);
            
        // Update nodes
        const node = this.nodeGroup.selectAll(".node")
            .data(this.nodes, d => d.id);
            
        node.exit()
            .transition()
            .duration(300)
            .attr("r", 0)
            .remove();
        
        const nodeEnter = node.enter()
            .append("circle")
            .attr("class", d => `node node-${d.type}`)
            .attr("r", 0) // Start with radius 0 for transition
            .attr("cx", d => d.x)
            .attr("cy", d => d.y)
            .attr("data-id", d => d.id) // Add data attribute for tooltips
            .call(d3.drag()
                .on("start", (event, d) => this.dragstarted(event, d))
                .on("drag", (event, d) => this.dragged(event, d))
                .on("end", (event, d) => this.dragended(event, d)))
            .on("mouseover", (event, d) => this.showTooltip(event, d))
            .on("mouseout", () => this.hideTooltip())
            .transition()
            .duration(300)
            .attr("r", d => {
                if (d.type === "loadbalancer") return 20;
                if (d.type === "backend") return 15;
                return 10; // client
            });
            
        // Update existing nodes
        this.node = nodeEnter.merge(node)
            .attr("fill", d => {
                if (d.type === "loadbalancer") return this.colors.node.loadBalancer;
                if (d.type === "backend") {
                    return d.healthy ? this.colors.node.backend.healthy : this.colors.node.backend.unhealthy;
                }
                return this.colors.node.client;
            })
            .attr("stroke", "#ffffff")
            .attr("stroke-width", 1.5)
            .attr("stroke-opacity", 0.5);
            
        // Update labels
        const label = this.labelGroup.selectAll(".node-label")
            .data(this.nodes, d => d.id);
            
        label.exit()
            .transition()
            .duration(300)
            .attr("opacity", 0)
            .remove();
        
        const labelEnter = label.enter()
            .append("text")
            .attr("class", "node-label")
            .attr("text-anchor", "middle")
            .attr("dy", 30)
            .attr("font-size", "12px")
            .attr("opacity", 0) // Start invisible for transition
            .attr("fill", this.colors.text)
            .attr("x", d => d.x)
            .attr("y", d => d.y)
            .transition()
            .duration(300)
            .attr("opacity", 1);
            
        this.label = labelEnter.merge(label)
            .text(d => {
                if (d.type === "loadbalancer") return "Load Balancer";
                if (d.type === "backend") {
                    const shortHost = d.host === "127.0.0.1" ? "localhost" : d.host;
                    return `${shortHost}:${d.port}`;
                }
                // For clients, just show "Client"
                return "Client";
            });
            
        // Create node pulse animation for active backends and clients
        this.nodeGroup.selectAll(".node-pulse").remove();
        
        // Add pulse effect to active nodes
        this.nodes.forEach(node => {
            if ((node.type === "backend" && node.connections > 0) || 
                (node.type === "client") || 
                (node.type === "loadbalancer")) { // Always add pulse to load balancer
                
                // Determine pulse color and size based on node type
                let pulseColor = this.colors.node.client;
                let maxRadius = 20;
                
                if (node.type === "backend") {
                    pulseColor = node.healthy ? 
                        this.colors.node.backend.healthy : 
                        this.colors.node.backend.unhealthy;
                    maxRadius = 25;
                } else if (node.type === "loadbalancer") {
                    pulseColor = this.colors.node.loadBalancer;
                    maxRadius = 35;
                }
                
                // Add pulse circle
                const pulse = this.nodeGroup.append("circle")
                    .attr("class", "node-pulse")
                    .attr("cx", node.x)
                    .attr("cy", node.y)
                    .attr("r", node.type === "loadbalancer" ? 20 : (node.type === "backend" ? 15 : 10))
                    .attr("fill", "none")
                    .attr("stroke", pulseColor)
                    .attr("stroke-width", 2)
                    .attr("stroke-opacity", 0.7);
                    
                // Create pulse animation
                function animatePulse() {
                    pulse.transition()
                        .duration(1500)
                        .attr("r", maxRadius)
                        .attr("stroke-width", 0.5)
                        .attr("stroke-opacity", 0)
                        .on("end", () => {
                            pulse
                                .attr("r", node.type === "loadbalancer" ? 20 : (node.type === "backend" ? 15 : 10))
                                .attr("stroke-width", 2)
                                .attr("stroke-opacity", 0.7);
                            animatePulse();
                        });
                }
                
                // Start animation
                animatePulse();
            }
        });
            
        // Update the simulation
        this.simulation.nodes(this.nodes);
        this.simulation.force("link").links(this.links);
        this.simulation.alpha(0.3).restart();
    }
    
    tick() {
        if (this.link) {
            this.link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
        }
        
        if (this.node) {
            this.node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        }
        
        if (this.label) {
            this.label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        }
        
        // Update data flow animation on active links
        if (this.linkGroup) {
            this.linkGroup.selectAll(".data-flow")
                .each(function() {
                    const link = d3.select(this);
                    // Randomize animation to create more natural data flow appearance
                    const speed = Math.random() * 0.5 + 0.5; // speed between 0.5 and 1
                    const delay = Math.random() * 0.5; // random delay
                    
                    link.style("animation", `dataFlow ${speed}s linear infinite`)
                        .style("animation-delay", `${delay}s`);
                });
            
            // Create pulse effect for active nodes
            this.nodeGroup.selectAll(".node-pulse").remove();
            
            // Identify active nodes based on connections
            const activeNodeIds = new Set();
            this.links.forEach(link => {
                if (link.active && !link.directConnection) {
                    activeNodeIds.add(link.source.id);
                    activeNodeIds.add(link.target.id);
                }
            });
            
            // Add pulse effects
            if (activeNodeIds.size > 0) {
                this.nodes.forEach(node => {
                    if (activeNodeIds.has(node.id)) {
                        // Add pulse effect around active nodes
                        this.nodeGroup.append("circle")
                            .attr("class", "node-pulse")
                            .attr("cx", node.x)
                            .attr("cy", node.y)
                            .attr("r", node.type === "loadbalancer" ? 25 : 20)
                            .attr("fill", "none")
                            .attr("stroke", node.type === "loadbalancer" ? 
                                  this.colors.node.loadBalancer : this.colors.node.client)
                            .attr("stroke-width", 2)
                            .attr("stroke-opacity", 0.5)
                            .style("animation", "pulse 1.5s ease-out infinite");
                    }
                });
            }
        }
    }
    
    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        if (!d.fixed) {
            d.fx = null;
            d.fy = null;
        }
    }
    
    showTooltip(event, d) {
        let content = "";
        
        if (d.type === "loadbalancer") {
            content = `
                <div style="font-weight: bold; margin-bottom: 8px;">Load Balancer</div>
                <div>Active Connections: ${this.stats.active_connections || 0}</div>
                <div>Total Connections: ${this.stats.total_connections || 0}</div>
                <div>Algorithm: ${this.stats.algorithm || "round_robin"}</div>
            `;
        } else if (d.type === "backend") {
            const healthStatus = d.healthy ? 
                `<span style="color: ${this.colors.node.backend.healthy}">HEALTHY</span>` : 
                `<span style="color: ${this.colors.node.backend.unhealthy}">UNHEALTHY</span>`;
                
            content = `
                <div style="font-weight: bold; margin-bottom: 8px;">Backend Server</div>
                <div>Address: ${d.host}:${d.port}</div>
                <div>Status: ${healthStatus}</div>
                <div>Response Time: ${d.responseTime || 0}ms</div>
                <div>Active Connections: ${d.connections || 0}</div>
            `;
        } else if (d.type === "client") {
            content = `
                <div style="font-weight: bold; margin-bottom: 8px;">Client</div>
                <div>Address: ${d.name}</div>
            `;
        }
        
        this.tooltip
            .html(content)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px")
            .transition()
            .duration(200)
            .style("opacity", 0.9);
    }
    
    hideTooltip() {
        this.tooltip.transition()
            .duration(200)
            .style("opacity", 0);
    }
    
    resize() {
        const newWidth = this.container.node().getBoundingClientRect().width;
        if (newWidth !== this.width) {
            this.width = newWidth;
            this.svg.attr("width", this.width);
            this.simulation.force("center", d3.forceCenter(this.width / 2, this.height / 2))
                .force("x", d3.forceX(this.width / 2).strength(0.1));
            this.simulation.alpha(0.3).restart();
        }
    }
}