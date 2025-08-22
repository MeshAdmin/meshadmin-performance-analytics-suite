from app import app
from services import syslog_collector, snmp_collector, netflow_collector
from services import sflow_collector, windows_events_collector, otel_collector
from services import data_processor, alert_manager
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_collectors():
    """Start all data collectors in separate threads"""
    logger.info("Starting data collectors...")
    
    # Create and start collector threads
    collectors = [
        threading.Thread(target=syslog_collector.start, daemon=True),
        threading.Thread(target=snmp_collector.start, daemon=True),
        threading.Thread(target=netflow_collector.start, daemon=True),
        threading.Thread(target=sflow_collector.start, daemon=True),
        threading.Thread(target=windows_events_collector.start, daemon=True),
        threading.Thread(target=otel_collector.start, daemon=True)
    ]
    
    # Start data processor
    processors = [
        threading.Thread(target=data_processor.start, daemon=True),
        threading.Thread(target=alert_manager.start, daemon=True)
    ]
    
    # Start all threads
    for collector in collectors:
        collector.start()
    
    for processor in processors:
        processor.start()
    
    logger.info("All collectors and processors started")

if __name__ == "__main__":
    # Start collectors in background
    background_thread = threading.Thread(target=start_collectors)
    background_thread.daemon = True
    background_thread.start()
    
    # Start Flask app
    import os
    port = int(os.environ.get('PORT', 8081))  # Use PORT env var or default to 8081
    app.run(host="0.0.0.0", port=port, debug=False)
