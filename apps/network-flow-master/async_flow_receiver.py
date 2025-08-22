#!/usr/bin/env python3
"""
Async Flow Receiver for Network Flow Master
Handles concurrent NetFlow/sFlow connections asynchronously for better performance
"""

import asyncio
import logging
import socket
import struct
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import json

logger = logging.getLogger(__name__)

class AsyncFlowReceiver:
    """Async version of FlowReceiver for improved concurrent handling"""
    
    def __init__(self, netflow_port: int = 2055, sflow_port: int = 6343, max_connections: int = 100):
        self.netflow_port = netflow_port
        self.sflow_port = sflow_port
        self.max_connections = max_connections
        self.running = False
        
        # Connection tracking
        self.active_connections = set()
        self.stats = {
            'total_packets': 0,
            'netflow_packets': 0,
            'sflow_packets': 0,
            'errors': 0,
            'start_time': None
        }
        
        # Flow processing queue
        self.flow_queue = asyncio.Queue(maxsize=10000)
        self.processing_tasks = []
        
    async def start(self):
        """Start the async flow receiver"""
        logger.info("Starting async flow receiver...")
        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        
        try:
            # Start UDP listeners for both NetFlow and sFlow
            netflow_task = asyncio.create_task(
                self._start_udp_listener(self.netflow_port, 'netflow')
            )
            sflow_task = asyncio.create_task(
                self._start_udp_listener(self.sflow_port, 'sflow')
            )
            
            # Start flow processors
            for i in range(4):  # 4 concurrent processors
                processor_task = asyncio.create_task(self._flow_processor(f"processor-{i}"))
                self.processing_tasks.append(processor_task)
            
            logger.info(f"Async flow receiver started on ports {self.netflow_port} (NetFlow) and {self.sflow_port} (sFlow)")
            
            # Wait for all tasks
            await asyncio.gather(netflow_task, sflow_task, *self.processing_tasks)
            
        except Exception as e:
            logger.error(f"Error in async flow receiver: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the async flow receiver"""
        logger.info("Stopping async flow receiver...")
        self.running = False
        
        # Cancel all processing tasks
        for task in self.processing_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        logger.info("Async flow receiver stopped")
    
    async def _start_udp_listener(self, port: int, flow_type: str):
        """Start UDP listener for a specific flow type"""
        try:
            # Create UDP endpoint
            transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
                lambda: AsyncUDPProtocol(self.flow_queue, flow_type, self.stats),
                local_addr=('0.0.0.0', port)
            )
            
            logger.info(f"UDP listener started for {flow_type} on port {port}")
            
            # Keep the transport alive while running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting UDP listener for {flow_type} on port {port}: {e}")
        finally:
            if 'transport' in locals():
                transport.close()
    
    async def _flow_processor(self, processor_id: str):
        """Process flows from the queue asynchronously"""
        logger.info(f"Flow processor {processor_id} started")
        
        processed_count = 0
        
        while self.running:
            try:
                # Get flow data from queue with timeout
                flow_data = await asyncio.wait_for(
                    self.flow_queue.get(), 
                    timeout=1.0
                )
                
                # Process the flow data
                await self._process_flow_data(flow_data)
                processed_count += 1
                
                # Mark task as done
                self.flow_queue.task_done()
                
                # Log progress periodically
                if processed_count % 1000 == 0:
                    logger.debug(f"{processor_id} processed {processed_count} flows")
                
            except asyncio.TimeoutError:
                # No data in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in flow processor {processor_id}: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(0.1)  # Brief pause on error
        
        logger.info(f"Flow processor {processor_id} stopped after processing {processed_count} flows")
    
    async def _process_flow_data(self, flow_data: Dict):
        """Process a single flow data record"""
        try:
            # Extract flow information
            flow_type = flow_data.get('type', 'unknown')
            source_ip = flow_data.get('source_ip', 'unknown')
            timestamp = flow_data.get('timestamp', datetime.utcnow())
            
            # Parse the flow records based on type
            if flow_type == 'netflow':
                flows = await self._parse_netflow_data(flow_data)
            elif flow_type == 'sflow':
                flows = await self._parse_sflow_data(flow_data)
            else:
                logger.warning(f"Unknown flow type: {flow_type}")
                return
            
            # Store flows in database (async)
            if flows:
                await self._store_flows_async(flows)
                
        except Exception as e:
            logger.error(f"Error processing flow data: {e}")
            self.stats['errors'] += 1
    
    async def _parse_netflow_data(self, flow_data: Dict) -> List[Dict]:
        """Parse NetFlow data asynchronously"""
        flows = []
        
        try:
            # Run CPU-intensive parsing in thread pool
            loop = asyncio.get_event_loop()
            flows = await loop.run_in_executor(
                None, 
                self._parse_netflow_sync, 
                flow_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing NetFlow data: {e}")
        
        return flows
    
    def _parse_netflow_sync(self, flow_data: Dict) -> List[Dict]:
        """Synchronous NetFlow parsing (runs in thread pool)"""
        flows = []
        
        try:
            raw_data = flow_data.get('data', b'')
            source_ip = flow_data.get('source_ip', 'unknown')
            
            # Basic NetFlow v5 parsing
            if len(raw_data) >= 24:  # Minimum header size
                # Parse NetFlow header
                header = struct.unpack('!HHIIIIH', raw_data[:24])
                version = header[0]
                count = header[1]
                
                if version == 5 and count > 0:
                    # Parse flow records
                    offset = 24
                    record_size = 48  # NetFlow v5 record size
                    
                    for i in range(min(count, 30)):  # Limit to prevent memory issues
                        if offset + record_size <= len(raw_data):
                            record_data = raw_data[offset:offset + record_size]
                            flow_record = self._parse_netflow_record(record_data, source_ip)
                            if flow_record:
                                flows.append(flow_record)
                            offset += record_size
                        else:
                            break
            
        except Exception as e:
            logger.error(f"Error in sync NetFlow parsing: {e}")
        
        return flows
    
    def _parse_netflow_record(self, record_data: bytes, source_ip: str) -> Optional[Dict]:
        """Parse a single NetFlow record"""
        try:
            # NetFlow v5 record structure
            if len(record_data) >= 48:
                fields = struct.unpack('!IIIHHIIIIHHBBBBH', record_data)
                
                return {
                    'source_ip': source_ip,
                    'flow_type': 'netflow_v5',
                    'src_addr': socket.inet_ntoa(struct.pack('!I', fields[0])),
                    'dst_addr': socket.inet_ntoa(struct.pack('!I', fields[1])),
                    'next_hop': socket.inet_ntoa(struct.pack('!I', fields[2])),
                    'input_snmp': fields[3],
                    'output_snmp': fields[4],
                    'packets': fields[5],
                    'bytes': fields[6],
                    'first_switched': fields[7],
                    'last_switched': fields[8],
                    'src_port': fields[9],
                    'dst_port': fields[10],
                    'tcp_flags': fields[12],
                    'protocol': fields[13],
                    'tos': fields[14],
                    'timestamp': datetime.utcnow()
                }
        
        except Exception as e:
            logger.error(f"Error parsing NetFlow record: {e}")
        
        return None
    
    async def _parse_sflow_data(self, flow_data: Dict) -> List[Dict]:
        """Parse sFlow data asynchronously"""
        flows = []
        
        try:
            # Run CPU-intensive parsing in thread pool
            loop = asyncio.get_event_loop()
            flows = await loop.run_in_executor(
                None, 
                self._parse_sflow_sync, 
                flow_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing sFlow data: {e}")
        
        return flows
    
    def _parse_sflow_sync(self, flow_data: Dict) -> List[Dict]:
        """Synchronous sFlow parsing (runs in thread pool)"""
        flows = []
        
        try:
            raw_data = flow_data.get('data', b'')
            source_ip = flow_data.get('source_ip', 'unknown')
            
            # Basic sFlow parsing (simplified)
            if len(raw_data) >= 20:  # Minimum header size
                # sFlow is more complex, this is a basic implementation
                flows.append({
                    'source_ip': source_ip,
                    'flow_type': 'sflow',
                    'raw_length': len(raw_data),
                    'timestamp': datetime.utcnow(),
                    'processed': True
                })
            
        except Exception as e:
            logger.error(f"Error in sync sFlow parsing: {e}")
        
        return flows
    
    async def _store_flows_async(self, flows: List[Dict]):
        """Store flows in database asynchronously"""
        try:
            # Use thread pool for database operations
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._store_flows_sync, 
                flows
            )
            
        except Exception as e:
            logger.error(f"Error storing flows asynchronously: {e}")
    
    def _store_flows_sync(self, flows: List[Dict]):
        """Synchronous flow storage (runs in thread pool)"""
        try:
            # Import here to avoid circular imports
            from models import FlowData, Device
            from app import db
            
            flow_objects = []
            
            for flow in flows:
                # Create flow object
                flow_obj = FlowData(
                    timestamp=flow.get('timestamp', datetime.utcnow()),
                    flow_type=flow.get('flow_type', 'unknown'),
                    src_ip=flow.get('src_addr', flow.get('source_ip', 'unknown')),
                    dst_ip=flow.get('dst_addr', 'unknown'),
                    src_port=flow.get('src_port', 0),
                    dst_port=flow.get('dst_port', 0),
                    protocol=flow.get('protocol', 0),
                    bytes=flow.get('bytes', 0),
                    packets=flow.get('packets', 0),
                    tos=flow.get('tos', 0)
                )
                
                flow_objects.append(flow_obj)
            
            # Bulk insert for better performance
            if flow_objects:
                db.session.bulk_save_objects(flow_objects)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error in sync flow storage: {e}")
            # Import here to avoid issues
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def get_stats(self) -> Dict:
        """Get receiver statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'total_packets': self.stats['total_packets'],
            'netflow_packets': self.stats['netflow_packets'],
            'sflow_packets': self.stats['sflow_packets'],
            'errors': self.stats['errors'],
            'queue_size': self.flow_queue.qsize(),
            'active_connections': len(self.active_connections),
            'processing_tasks': len([t for t in self.processing_tasks if not t.done()])
        }


class AsyncUDPProtocol(asyncio.DatagramProtocol):
    """Async UDP protocol for handling flow data"""
    
    def __init__(self, flow_queue: asyncio.Queue, flow_type: str, stats: Dict):
        self.flow_queue = flow_queue
        self.flow_type = flow_type
        self.stats = stats
        
    def connection_made(self, transport):
        self.transport = transport
        
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle received UDP datagram"""
        try:
            # Create flow data object
            flow_data = {
                'type': self.flow_type,
                'source_ip': addr[0],
                'source_port': addr[1],
                'data': data,
                'timestamp': datetime.utcnow(),
                'size': len(data)
            }
            
            # Try to add to queue (non-blocking)
            try:
                self.flow_queue.put_nowait(flow_data)
                
                # Update stats
                self.stats['total_packets'] += 1
                if self.flow_type == 'netflow':
                    self.stats['netflow_packets'] += 1
                elif self.flow_type == 'sflow':
                    self.stats['sflow_packets'] += 1
                    
            except asyncio.QueueFull:
                # Queue is full, drop the packet
                logger.warning(f"Flow queue full, dropping {self.flow_type} packet from {addr[0]}")
                self.stats['errors'] += 1
                
        except Exception as e:
            logger.error(f"Error processing {self.flow_type} datagram from {addr}: {e}")
            self.stats['errors'] += 1
    
    def error_received(self, exc):
        logger.error(f"UDP protocol error for {self.flow_type}: {exc}")


# Global async flow receiver instance
async_flow_receiver = AsyncFlowReceiver()

def start_async_flow_receiver(netflow_port: int = 2055, sflow_port: int = 6343):
    """Start the async flow receiver in a separate thread"""
    import threading
    
    def _run_async_receiver():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Configure receiver
        global async_flow_receiver
        async_flow_receiver = AsyncFlowReceiver(netflow_port, sflow_port)
        
        try:
            loop.run_until_complete(async_flow_receiver.start())
        except KeyboardInterrupt:
            logger.info("Async flow receiver interrupted")
        finally:
            loop.run_until_complete(async_flow_receiver.stop())
            loop.close()
    
    # Start in background thread
    receiver_thread = threading.Thread(target=_run_async_receiver, daemon=True)
    receiver_thread.start()
    
    logger.info("Async flow receiver started in background thread")
    return receiver_thread

if __name__ == '__main__':
    # For testing
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start receiver
    try:
        asyncio.run(async_flow_receiver.start())
    except KeyboardInterrupt:
        print("Shutting down...")
        asyncio.run(async_flow_receiver.stop()) 