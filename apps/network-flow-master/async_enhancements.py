#!/usr/bin/env python3
"""
Async Enhancements for Network Flow Master
Provides async processing capabilities for improved performance
"""

import asyncio
import aiohttp
import aiodns
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import time
import concurrent.futures
from functools import wraps
import socket

logger = logging.getLogger(__name__)

class AsyncFlowProcessor:
    """Async processor for flow data with concurrent capabilities"""
    
    def __init__(self, max_workers: int = 4, max_concurrent_flows: int = 50):
        self.max_workers = max_workers
        self.max_concurrent_flows = max_concurrent_flows
        
        # Thread pool for CPU-intensive tasks
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Flow processing queue
        self.flow_queue = asyncio.Queue(maxsize=1000)
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_flows)
        
        # Statistics tracking
        self.stats = {
            'flows_processed': 0,
            'flows_failed': 0,
            'dns_lookups': 0,
            'enrichments_applied': 0,
            'start_time': datetime.utcnow()
        }
        
        # DNS resolver
        self.dns_resolver = None
        self.dns_cache = {}
        self.dns_cache_ttl = 300  # 5 minutes
        
        # Running state
        self.running = False
        self.worker_tasks = []
    
    async def start(self):
        """Start the async flow processor"""
        logger.info("Starting async flow processor...")
        self.running = True
        
        # Initialize DNS resolver
        self.dns_resolver = aiodns.DNSResolver()
        
        # Start worker tasks
        for i in range(self.max_workers):
            task = asyncio.create_task(self._flow_worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"Async flow processor started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the async flow processor"""
        logger.info("Stopping async flow processor...")
        self.running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Async flow processor stopped")
    
    async def process_flow_batch(self, flows: List[Dict]) -> List[Dict]:
        """Process a batch of flows asynchronously"""
        if not flows:
            return []
        
        # Create tasks for each flow
        tasks = []
        for flow in flows:
            task = asyncio.create_task(self.process_single_flow(flow))
            tasks.append(task)
        
        # Process all flows concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        processed_flows = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Flow processing failed: {result}")
                self.stats['flows_failed'] += 1
            else:
                processed_flows.append(result)
                self.stats['flows_processed'] += 1
        
        return processed_flows
    
    async def process_single_flow(self, flow: Dict) -> Dict:
        """Process a single flow with async enhancements"""
        async with self.processing_semaphore:
            try:
                # Enrich flow with additional data
                enriched_flow = await self._enrich_flow_data(flow)
                
                # Perform DNS lookups if needed
                enriched_flow = await self._perform_dns_lookups(enriched_flow)
                
                # Analyze flow patterns
                enriched_flow = await self._analyze_flow_patterns(enriched_flow)
                
                # Add processing metadata
                enriched_flow['processing_metadata'] = {
                    'processed_at': datetime.utcnow().isoformat(),
                    'processor': 'async_flow_processor',
                    'enrichments_applied': len(enriched_flow.get('enrichments', []))
                }
                
                return enriched_flow
                
            except Exception as e:
                logger.error(f"Error processing flow: {e}")
                raise
    
    async def _flow_worker(self, worker_id: str):
        """Background worker for processing flows from queue"""
        logger.info(f"Flow worker {worker_id} started")
        
        processed_count = 0
        
        while self.running:
            try:
                # Get flow from queue with timeout
                flow = await asyncio.wait_for(
                    self.flow_queue.get(),
                    timeout=1.0
                )
                
                # Process the flow
                processed_flow = await self.process_single_flow(flow)
                
                # Store processed flow (implement based on your storage needs)
                await self._store_processed_flow(processed_flow)
                
                processed_count += 1
                
                # Mark task as done
                self.flow_queue.task_done()
                
                # Log progress
                if processed_count % 100 == 0:
                    logger.debug(f"{worker_id} processed {processed_count} flows")
                
            except asyncio.TimeoutError:
                # No flow in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in flow worker {worker_id}: {e}")
                self.stats['flows_failed'] += 1
                await asyncio.sleep(0.1)
        
        logger.info(f"Flow worker {worker_id} stopped after processing {processed_count} flows")
    
    async def _enrich_flow_data(self, flow: Dict) -> Dict:
        """Enrich flow data with additional information"""
        enriched_flow = flow.copy()
        enrichments = []
        
        try:
            # Add geolocation data for IPs
            src_ip = flow.get('src_ip')
            dst_ip = flow.get('dst_ip')
            
            if src_ip and self._is_public_ip(src_ip):
                geo_data = await self._get_ip_geolocation(src_ip)
                if geo_data:
                    enriched_flow['src_geo'] = geo_data
                    enrichments.append('src_geolocation')
            
            if dst_ip and self._is_public_ip(dst_ip):
                geo_data = await self._get_ip_geolocation(dst_ip)
                if geo_data:
                    enriched_flow['dst_geo'] = geo_data
                    enrichments.append('dst_geolocation')
            
            # Add protocol information
            protocol = flow.get('protocol', 0)
            if protocol:
                protocol_name = self._get_protocol_name(protocol)
                enriched_flow['protocol_name'] = protocol_name
                enrichments.append('protocol_name')
            
            # Add port classification
            src_port = flow.get('src_port', 0)
            dst_port = flow.get('dst_port', 0)
            
            if src_port:
                enriched_flow['src_port_classification'] = self._classify_port(src_port)
                enrichments.append('src_port_classification')
            
            if dst_port:
                enriched_flow['dst_port_classification'] = self._classify_port(dst_port)
                enrichments.append('dst_port_classification')
            
            # Add flow direction
            enriched_flow['flow_direction'] = self._determine_flow_direction(flow)
            enrichments.append('flow_direction')
            
            enriched_flow['enrichments'] = enrichments
            self.stats['enrichments_applied'] += len(enrichments)
            
        except Exception as e:
            logger.error(f"Error enriching flow data: {e}")
        
        return enriched_flow
    
    async def _perform_dns_lookups(self, flow: Dict) -> Dict:
        """Perform DNS lookups for IP addresses"""
        enhanced_flow = flow.copy()
        
        try:
            src_ip = flow.get('src_ip')
            dst_ip = flow.get('dst_ip')
            
            # Perform concurrent DNS lookups
            tasks = []
            if src_ip and self._is_public_ip(src_ip):
                tasks.append(self._dns_lookup(src_ip, 'src'))
            
            if dst_ip and self._is_public_ip(dst_ip):
                tasks.append(self._dns_lookup(dst_ip, 'dst'))
            
            if tasks:
                dns_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in dns_results:
                    if isinstance(result, tuple) and len(result) == 3:
                        ip, direction, hostname = result
                        if hostname:
                            enhanced_flow[f'{direction}_hostname'] = hostname
                            self.stats['dns_lookups'] += 1
        
        except Exception as e:
            logger.error(f"Error performing DNS lookups: {e}")
        
        return enhanced_flow
    
    async def _dns_lookup(self, ip: str, direction: str) -> Tuple[str, str, Optional[str]]:
        """Perform DNS lookup for an IP address"""
        try:
            # Check cache first
            cache_key = f"dns_{ip}"
            if cache_key in self.dns_cache:
                cached_entry = self.dns_cache[cache_key]
                if time.time() - cached_entry['timestamp'] < self.dns_cache_ttl:
                    return ip, direction, cached_entry['hostname']
            
            # Perform DNS lookup
            hostname = await self.dns_resolver.gethostbyaddr(ip)
            
            # Cache result
            self.dns_cache[cache_key] = {
                'hostname': hostname.name,
                'timestamp': time.time()
            }
            
            return ip, direction, hostname.name
            
        except Exception as e:
            logger.debug(f"DNS lookup failed for {ip}: {e}")
            return ip, direction, None
    
    async def _analyze_flow_patterns(self, flow: Dict) -> Dict:
        """Analyze flow patterns using async processing"""
        enhanced_flow = flow.copy()
        
        try:
            # Run pattern analysis in thread pool (CPU-intensive)
            loop = asyncio.get_event_loop()
            pattern_analysis = await loop.run_in_executor(
                self.thread_pool,
                self._analyze_flow_patterns_sync,
                flow
            )
            
            if pattern_analysis:
                enhanced_flow['pattern_analysis'] = pattern_analysis
        
        except Exception as e:
            logger.error(f"Error analyzing flow patterns: {e}")
        
        return enhanced_flow
    
    def _analyze_flow_patterns_sync(self, flow: Dict) -> Dict:
        """Synchronous flow pattern analysis (runs in thread pool)"""
        try:
            analysis = {}
            
            # Analyze traffic volume
            bytes_count = flow.get('bytes', 0)
            packets_count = flow.get('packets', 0)
            
            if packets_count > 0:
                avg_packet_size = bytes_count / packets_count
                analysis['avg_packet_size'] = avg_packet_size
                
                # Classify traffic type based on packet size
                if avg_packet_size < 100:
                    analysis['traffic_type'] = 'control'
                elif avg_packet_size < 500:
                    analysis['traffic_type'] = 'interactive'
                elif avg_packet_size < 1400:
                    analysis['traffic_type'] = 'bulk'
                else:
                    analysis['traffic_type'] = 'jumbo'
            
            # Analyze flow duration
            first_switched = flow.get('first_switched', 0)
            last_switched = flow.get('last_switched', 0)
            
            if first_switched and last_switched and last_switched > first_switched:
                duration = last_switched - first_switched
                analysis['duration_ms'] = duration
                
                if duration < 1000:  # < 1 second
                    analysis['duration_classification'] = 'short'
                elif duration < 10000:  # < 10 seconds
                    analysis['duration_classification'] = 'medium'
                else:
                    analysis['duration_classification'] = 'long'
            
            # Analyze port patterns
            src_port = flow.get('src_port', 0)
            dst_port = flow.get('dst_port', 0)
            
            if src_port > 1024 and dst_port < 1024:
                analysis['connection_type'] = 'client_to_server'
            elif src_port < 1024 and dst_port > 1024:
                analysis['connection_type'] = 'server_to_client'
            else:
                analysis['connection_type'] = 'peer_to_peer'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in sync pattern analysis: {e}")
            return {}
    
    async def _get_ip_geolocation(self, ip: str) -> Optional[Dict]:
        """Get geolocation data for an IP address"""
        try:
            # Use a simple geolocation API (implement based on your needs)
            # This is a placeholder - in production, use a real geolocation service
            return {
                'country': 'Unknown',
                'city': 'Unknown',
                'latitude': 0.0,
                'longitude': 0.0,
                'asn': 'Unknown'
            }
        except Exception as e:
            logger.error(f"Error getting geolocation for {ip}: {e}")
            return None
    
    def _is_public_ip(self, ip: str) -> bool:
        """Check if an IP address is public"""
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            return not ip_obj.is_private
        except:
            return False
    
    def _get_protocol_name(self, protocol_number: int) -> str:
        """Get protocol name from number"""
        protocol_map = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            47: 'GRE',
            50: 'ESP',
            51: 'AH',
            89: 'OSPF'
        }
        return protocol_map.get(protocol_number, f'Protocol-{protocol_number}')
    
    def _classify_port(self, port: int) -> str:
        """Classify a port number"""
        if port < 1024:
            return 'well_known'
        elif port < 49152:
            return 'registered'
        else:
            return 'dynamic'
    
    def _determine_flow_direction(self, flow: Dict) -> str:
        """Determine flow direction based on ports and IPs"""
        src_port = flow.get('src_port', 0)
        dst_port = flow.get('dst_port', 0)
        
        # Simple heuristic
        if src_port > 1024 and dst_port < 1024:
            return 'outbound'
        elif src_port < 1024 and dst_port > 1024:
            return 'inbound'
        else:
            return 'internal'
    
    async def _store_processed_flow(self, flow: Dict):
        """Store processed flow (implement based on your storage needs)"""
        try:
            # This is a placeholder - implement based on your database
            # For example, you might store in PostgreSQL, InfluxDB, etc.
            logger.debug(f"Storing processed flow: {flow.get('src_ip', 'unknown')} -> {flow.get('dst_ip', 'unknown')}")
        except Exception as e:
            logger.error(f"Error storing processed flow: {e}")
    
    async def add_flow_to_queue(self, flow: Dict) -> bool:
        """Add a flow to the processing queue"""
        try:
            await self.flow_queue.put(flow)
            return True
        except asyncio.QueueFull:
            logger.warning("Flow processing queue is full, dropping flow")
            return False
    
    def get_stats(self) -> Dict:
        """Get processor statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'uptime_seconds': uptime,
            'flows_processed': self.stats['flows_processed'],
            'flows_failed': self.stats['flows_failed'],
            'dns_lookups': self.stats['dns_lookups'],
            'enrichments_applied': self.stats['enrichments_applied'],
            'queue_size': self.flow_queue.qsize(),
            'active_workers': len([t for t in self.worker_tasks if not t.done()]),
            'dns_cache_size': len(self.dns_cache)
        }


def async_processing_decorator(func):
    """Decorator to make regular functions async-compatible"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # If the function is already async, call it directly
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        
        # Otherwise, run it in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    return wrapper


class AsyncFlowEnhancer:
    """Enhances existing synchronous flow processing with async capabilities"""
    
    def __init__(self, sync_processor):
        self.sync_processor = sync_processor
        self.async_processor = AsyncFlowProcessor()
    
    async def start(self):
        """Start the async enhancer"""
        await self.async_processor.start()
    
    async def stop(self):
        """Stop the async enhancer"""
        await self.async_processor.stop()
    
    async def process_flows_hybrid(self, flows: List[Dict]) -> List[Dict]:
        """Process flows using both sync and async methods"""
        # Use async processor for I/O-intensive operations
        async_results = await self.async_processor.process_flow_batch(flows)
        
        # Use sync processor for specific legacy operations if needed
        # This allows gradual migration to async
        
        return async_results
    
    def get_combined_stats(self) -> Dict:
        """Get combined statistics from both processors"""
        async_stats = self.async_processor.get_stats()
        
        return {
            'async_processor': async_stats,
            'hybrid_mode': True,
            'total_flows_processed': async_stats['flows_processed']
        }


# Global async flow processor instance
global_async_processor = AsyncFlowProcessor()

async def start_global_async_processor():
    """Start the global async flow processor"""
    await global_async_processor.start()
    logger.info("Global async flow processor started")

async def stop_global_async_processor():
    """Stop the global async flow processor"""
    await global_async_processor.stop()
    logger.info("Global async flow processor stopped")

if __name__ == '__main__':
    # For testing
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_async_processor():
        """Test the async flow processor"""
        
        processor = AsyncFlowProcessor(max_workers=2)
        
        try:
            await processor.start()
            
            # Test flows
            test_flows = [
                {
                    'src_ip': '192.168.1.100',
                    'dst_ip': '8.8.8.8',
                    'src_port': 12345,
                    'dst_port': 53,
                    'protocol': 17,
                    'bytes': 1024,
                    'packets': 2,
                    'timestamp': datetime.utcnow()
                },
                {
                    'src_ip': '10.0.0.1',
                    'dst_ip': '1.1.1.1',
                    'src_port': 443,
                    'dst_port': 54321,
                    'protocol': 6,
                    'bytes': 2048,
                    'packets': 4,
                    'timestamp': datetime.utcnow()
                }
            ]
            
            # Process flows
            results = await processor.process_flow_batch(test_flows)
            print(f"Processed {len(results)} flows")
            
            # Show stats
            stats = processor.get_stats()
            print(f"Processor stats: {stats}")
            
        except Exception as e:
            print(f"Test error: {e}")
        finally:
            await processor.stop()
    
    # Run test
    try:
        asyncio.run(test_async_processor())
    except KeyboardInterrupt:
        print("Test interrupted") 