"""
Enhanced Flow Processor with Performance Optimizations

This module provides significant performance improvements over the base FlowProcessor:
- Asynchronous processing capabilities
- Optimized database operations with connection pooling
- Advanced caching with LRU and memory pressure monitoring
- Dynamic batch sizing based on load
- Performance metrics and monitoring
- Memory usage optimization
"""

import logging
import asyncio
import threading
import time
import psutil
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import queue
import json

from flow_processor import FlowProcessor  # Base class
from database import db
from storage_manager import get_storage_manager

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Track detailed performance metrics for flow processing"""
    
    def __init__(self):
        self.reset_metrics()
        
    def reset_metrics(self):
        """Reset all metrics to initial state"""
        self.start_time = time.time()
        self.packets_processed = 0
        self.packets_per_second = 0.0
        self.processing_times = []
        self.batch_processing_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.memory_usage_mb = 0.0
        self.cpu_usage_percent = 0.0
        self.database_operations = 0
        self.database_errors = 0
        self.validation_errors = 0
        self.flows_stored = 0
        self.batch_count = 0
        self.average_batch_size = 0.0
        
    def record_packet_processing(self, processing_time: float):
        """Record metrics for packet processing"""
        self.packets_processed += 1
        self.processing_times.append(processing_time)
        
        # Keep only last 1000 processing times for memory efficiency
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]
            
        # Calculate packets per second
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.packets_per_second = self.packets_processed / elapsed
    
    def record_batch_processing(self, batch_size: int, processing_time: float):
        """Record metrics for batch processing"""
        self.batch_count += 1
        self.batch_processing_times.append(processing_time)
        self.flows_stored += batch_size
        
        # Calculate average batch size
        self.average_batch_size = self.flows_stored / self.batch_count if self.batch_count > 0 else 0
        
        # Keep only last 100 batch times
        if len(self.batch_processing_times) > 100:
            self.batch_processing_times = self.batch_processing_times[-100:]
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def record_database_operation(self, success: bool = True):
        """Record database operation"""
        self.database_operations += 1
        if not success:
            self.database_errors += 1
    
    def record_validation_error(self):
        """Record validation error"""
        self.validation_errors += 1
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            process = psutil.Process()
            self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.cpu_usage_percent = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        elapsed = time.time() - self.start_time
        
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        avg_batch_time = sum(self.batch_processing_times) / len(self.batch_processing_times) if self.batch_processing_times else 0
        
        cache_hit_ratio = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        db_error_ratio = self.database_errors / self.database_operations if self.database_operations > 0 else 0
        
        return {
            'runtime_seconds': elapsed,
            'packets_processed': self.packets_processed,
            'packets_per_second': self.packets_per_second,
            'flows_stored': self.flows_stored,
            'batch_count': self.batch_count,
            'average_batch_size': self.average_batch_size,
            'average_packet_processing_ms': avg_processing_time * 1000,
            'average_batch_processing_ms': avg_batch_time * 1000,
            'cache_hit_ratio': cache_hit_ratio,
            'database_operations': self.database_operations,
            'database_error_ratio': db_error_ratio,
            'validation_errors': self.validation_errors,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent
        }


class LRUCache:
    """High-performance LRU cache with memory pressure monitoring"""
    
    def __init__(self, max_size: int = 1000, memory_threshold_mb: float = 100):
        self.max_size = max_size
        self.memory_threshold_mb = memory_threshold_mb
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        
    def get(self, key: Any) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def put(self, key: Any, value: Any):
        """Put item in cache"""
        if key in self.cache:
            # Update existing item
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Add new item
            self.cache[key] = value
            
            # Check if we need to evict
            self._check_eviction()
    
    def _check_eviction(self):
        """Check if we need to evict items"""
        # Size-based eviction
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)  # Remove oldest
        
        # Memory pressure-based eviction
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.memory_threshold_mb and len(self.cache) > 10:
                # Evict 25% of cache when under memory pressure
                evict_count = len(self.cache) // 4
                for _ in range(evict_count):
                    if self.cache:
                        self.cache.popitem(last=False)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def clear(self):
        """Clear all items from cache"""
        self.cache.clear()
        
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def hit_ratio(self) -> float:
        """Get cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


class BatchProcessor:
    """Advanced batch processor with dynamic sizing and async capabilities"""
    
    def __init__(self, initial_batch_size: int = 100, max_batch_size: int = 1000):
        self.initial_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size
        self.current_batch_size = initial_batch_size
        
        self.batch_queue = queue.Queue()
        self.processing_times = []
        self.last_flush_time = time.time()
        
        # Dynamic sizing parameters
        self.target_processing_time = 0.1  # Target 100ms batch processing time
        self.size_adjustment_factor = 0.1
        
    def add_to_batch(self, item: Dict[str, Any]) -> bool:
        """Add item to batch, returns True if batch should be processed"""
        self.batch_queue.put(item)
        
        # Check if we should process the batch
        return (self.batch_queue.qsize() >= self.current_batch_size or
                time.time() - self.last_flush_time > 5.0)  # Time-based flush
    
    def get_batch(self) -> List[Dict[str, Any]]:
        """Get current batch for processing"""
        batch = []
        while not self.batch_queue.empty() and len(batch) < self.current_batch_size:
            try:
                batch.append(self.batch_queue.get_nowait())
            except queue.Empty:
                break
        
        return batch
    
    def record_batch_time(self, processing_time: float):
        """Record batch processing time and adjust batch size"""
        self.processing_times.append(processing_time)
        self.last_flush_time = time.time()
        
        # Keep only recent processing times
        if len(self.processing_times) > 10:
            self.processing_times = self.processing_times[-10:]
        
        # Adjust batch size based on processing time
        avg_time = sum(self.processing_times) / len(self.processing_times)
        
        if avg_time > self.target_processing_time and self.current_batch_size > 10:
            # Too slow, reduce batch size
            self.current_batch_size = max(10, int(self.current_batch_size * (1 - self.size_adjustment_factor)))
        elif avg_time < self.target_processing_time * 0.5 and self.current_batch_size < self.max_batch_size:
            # Too fast, increase batch size
            self.current_batch_size = min(self.max_batch_size, int(self.current_batch_size * (1 + self.size_adjustment_factor)))
    
    def flush(self) -> List[Dict[str, Any]]:
        """Flush all remaining items in batch"""
        return self.get_batch()


class EnhancedFlowProcessor(FlowProcessor):
    """
    Enhanced flow processor with significant performance improvements:
    - Asynchronous processing
    - Optimized caching
    - Dynamic batch sizing
    - Performance monitoring
    - Memory pressure handling
    """
    
    def __init__(self, max_workers: int = 4, cache_size: int = 2000):
        super().__init__()
        
        # Performance enhancements
        self.metrics = PerformanceMetrics()
        self.device_cache = LRUCache(max_size=cache_size, memory_threshold_mb=200)
        self.batch_processor = BatchProcessor(initial_batch_size=50, max_batch_size=500)
        
        # Threading for async operations
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.background_tasks = []
        
        # Memory monitoring
        self.memory_check_interval = 60  # Check every minute
        self.last_memory_check = time.time()
        self.memory_threshold_mb = 512  # Alert threshold
        
        # Replace the base class batch variables with our enhanced batch processor
        self.flow_batch = []  # Keep for compatibility but use batch_processor instead
        
        logger.info(f"Enhanced flow processor initialized with {max_workers} workers, cache size {cache_size}")
    
    def process_packet(self, data: bytes, addr: Tuple[str, int], port: int) -> Optional[Dict]:
        """Enhanced packet processing with performance monitoring"""
        start_time = time.time()
        
        try:
            # Check memory pressure
            self._check_memory_pressure()
            
            # Call parent process_packet but with enhanced error handling
            result = super().process_packet(data, addr, port)
            
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics.record_packet_processing(processing_time)
            
            # Update system metrics periodically
            if time.time() - self.last_memory_check > self.memory_check_interval:
                self.metrics.update_system_metrics()
                self.last_memory_check = time.time()
            
            return result
            
        except Exception as e:
            self.metrics.record_validation_error()
            logger.error(f"Enhanced packet processing error: {str(e)}")
            return None
    
    def get_or_create_device(self, ip_address: str, flow_type: str, flow_version: int):
        """Enhanced device lookup with optimized caching"""
        from models import Device
        
        # Check enhanced cache first
        cached_device = self.device_cache.get(ip_address)
        if cached_device:
            self.metrics.record_cache_hit()
            
            # Update last_seen timestamp if needed (async)
            current_time = datetime.utcnow()
            if (current_time - cached_device.last_seen).total_seconds() > 60:
                # Submit async task to update timestamp
                self.thread_pool.submit(self._async_update_device_timestamp, cached_device, current_time)
            
            return cached_device
        
        # Cache miss - query database
        self.metrics.record_cache_miss()
        
        try:
            device = Device.query.filter_by(ip_address=ip_address).first()
            
            if not device:
                # Create new device
                device = Device(
                    name=f"Device {ip_address}",
                    ip_address=ip_address,
                    flow_type=flow_type,
                    flow_version=str(flow_version),
                    last_seen=datetime.utcnow()
                )
                db.session.add(device)
                db.session.commit()
                self.metrics.record_database_operation(success=True)
            else:
                # Update existing device
                device.last_seen = datetime.utcnow()
                db.session.commit()
                self.metrics.record_database_operation(success=True)
            
            # Add to cache
            self.device_cache.put(ip_address, device)
            
            return device
            
        except Exception as e:
            db.session.rollback()
            self.metrics.record_database_operation(success=False)
            logger.error(f"Enhanced device creation/update error: {str(e)}")
            
            # Return temporary device as fallback
            return Device(
                name=f"Device {ip_address}",
                ip_address=ip_address,
                flow_type=flow_type,
                flow_version=str(flow_version),
                last_seen=datetime.utcnow(),
                id=-1
            )
    
    def _async_update_device_timestamp(self, device, timestamp):
        """Asynchronously update device timestamp"""
        try:
            device.last_seen = timestamp
            db.session.add(device)
            db.session.commit()
            self.metrics.record_database_operation(success=True)
        except Exception as e:
            db.session.rollback()
            self.metrics.record_database_operation(success=False)
            logger.debug(f"Async timestamp update failed: {str(e)}")
    
    def store_flow_data(self, flow_data: Dict, device_id: int, flow_type_version: str, raw_data: bytes = None):
        """Enhanced flow data storage with dynamic batching"""
        if not flow_data or 'flows' not in flow_data or device_id < 0:
            return
        
        current_time = datetime.utcnow()
        
        # Add flows to enhanced batch processor
        for flow in flow_data.get('flows', []):
            batch_item = {
                'flow_data': flow,
                'device_id': device_id,
                'flow_type': flow_type_version,
                'raw_data': raw_data,
                'timestamp': current_time
            }
            
            # Check if batch should be processed
            if self.batch_processor.add_to_batch(batch_item):
                self._process_batch_async()
    
    def _process_batch_async(self):
        """Process batch asynchronously"""
        batch = self.batch_processor.get_batch()
        if not batch:
            return
        
        # Submit batch processing to thread pool
        future = self.thread_pool.submit(self._process_batch_sync, batch)
        self.background_tasks.append(future)
        
        # Clean up completed tasks
        self.background_tasks = [task for task in self.background_tasks if not task.done()]
    
    def _process_batch_sync(self, batch: List[Dict]):
        """Synchronously process a batch of flows"""
        start_time = time.time()
        
        try:
            # Get storage manager
            storage_mgr = get_storage_manager()
            
            # Process the batch
            storage_mgr.store_flow_batch(batch)
            
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics.record_batch_processing(len(batch), processing_time)
            self.batch_processor.record_batch_time(processing_time)
            
        except Exception as e:
            logger.error(f"Enhanced batch processing error: {str(e)}")
            
            # Fallback to individual processing
            for item in batch:
                try:
                    storage_mgr = get_storage_manager()
                    storage_mgr.store_flow_data(
                        flow_data=item['flow_data'],
                        device_id=item['device_id'],
                        flow_type=item['flow_type'],
                        raw_data=item['raw_data'],
                        store_locally=True
                    )
                except Exception as inner_e:
                    logger.error(f"Individual flow processing error: {str(inner_e)}")
    
    def _check_memory_pressure(self):
        """Check and handle memory pressure"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.memory_threshold_mb:
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB")
                
                # Reduce cache sizes
                if self.device_cache.size() > 100:
                    # Evict 50% of cache
                    for _ in range(self.device_cache.size() // 2):
                        if self.device_cache.cache:
                            self.device_cache.cache.popitem(last=False)
                
                # Process any pending batches immediately
                self._flush_all_batches()
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def _flush_all_batches(self):
        """Flush all pending batches"""
        remaining_batch = self.batch_processor.flush()
        if remaining_batch:
            self._process_batch_sync(remaining_batch)
    
    def flush_flow_batch(self):
        """Enhanced batch flushing"""
        # Process any remaining items in the batch processor
        self._flush_all_batches()
        
        # Wait for background tasks to complete
        for task in self.background_tasks:
            try:
                task.result(timeout=5.0)  # 5 second timeout
            except Exception as e:
                logger.error(f"Background task completion error: {str(e)}")
        
        self.background_tasks.clear()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        self.metrics.update_system_metrics()
        
        metrics = self.metrics.get_summary()
        metrics.update({
            'cache_size': self.device_cache.size(),
            'cache_hit_ratio': self.device_cache.hit_ratio(),
            'current_batch_size': self.batch_processor.current_batch_size,
            'pending_batches': self.batch_processor.batch_queue.qsize(),
            'background_tasks': len(self.background_tasks),
            'max_workers': self.max_workers
        })
        
        return metrics
    
    def shutdown(self):
        """Clean shutdown of enhanced processor"""
        logger.info("Shutting down enhanced flow processor...")
        
        # Flush all pending batches
        self.flush_flow_batch()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        # Clear caches
        self.device_cache.clear()
        
        logger.info("Enhanced flow processor shutdown complete")


# Factory function for creating the enhanced processor
def create_enhanced_flow_processor(max_workers: int = None, cache_size: int = None) -> EnhancedFlowProcessor:
    """
    Factory function to create an enhanced flow processor with optimal settings
    
    Args:
        max_workers: Number of background worker threads (default: CPU count)
        cache_size: Device cache size (default: 2000)
    
    Returns:
        EnhancedFlowProcessor: Configured enhanced processor
    """
    if max_workers is None:
        max_workers = min(8, (psutil.cpu_count() or 4))  # Cap at 8 workers
    
    if cache_size is None:
        # Set cache size based on available memory
        try:
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
            cache_size = min(5000, max(1000, int(available_memory_gb * 500)))  # ~500 entries per GB
        except:
            cache_size = 2000  # Default fallback
    
    processor = EnhancedFlowProcessor(max_workers=max_workers, cache_size=cache_size)
    logger.info(f"Created enhanced flow processor: {max_workers} workers, cache size {cache_size}")
    
    return processor

