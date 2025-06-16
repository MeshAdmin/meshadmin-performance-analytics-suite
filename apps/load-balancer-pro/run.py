"""
Python Load Balancer - Startup Script
This script starts the standalone Load Balancer application.
"""

import os
import signal
import sys
import logging
import time
from standalone_app import app, GLOBAL_SHUTDOWN_EVENT, create_test_servers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("loadbalancer-runner")

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    logger.info("Shutdown signal received, cleaning up...")
    GLOBAL_SHUTDOWN_EVENT.set()
    time.sleep(1)  # Give threads time to clean up
    logger.info("Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting Python Load Balancer on port {port}")
    logger.info("Press Ctrl+C to exit")
    
    # Start test servers automatically for demonstration
    test_servers, test_ports = create_test_servers()
    logger.info(f"Started test servers on ports: {', '.join(map(str, test_ports))}")
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)