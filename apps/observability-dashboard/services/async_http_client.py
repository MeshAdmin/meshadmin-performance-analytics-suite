#!/usr/bin/env python3
"""
Async HTTP Client for Observability Dashboard
Handles concurrent HTTP requests for better performance
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import json
import time

logger = logging.getLogger(__name__)

class AsyncHTTPClient:
    """Async HTTP client for concurrent API requests"""
    
    def __init__(self, 
                 max_connections: int = 100,
                 timeout: int = 30,
                 retry_attempts: int = 3,
                 retry_delay: float = 1.0):
        self.max_connections = max_connections
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Connection pool and session
        self.connector = None
        self.session = None
        
        # Request statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_requests': 0,
            'start_time': datetime.utcnow()
        }
        
        # Rate limiting
        self.rate_limiter = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Initialize the HTTP client"""
        try:
            # Create connection pool
            self.connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # Create session
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'MeshAdmin-Observatory/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            logger.info("Async HTTP client started")
            
        except Exception as e:
            logger.error(f"Error starting async HTTP client: {e}")
            await self.close()
            raise
    
    async def close(self):
        """Close the HTTP client"""
        try:
            if self.session:
                await self.session.close()
            
            if self.connector:
                await self.connector.close()
            
            logger.info("Async HTTP client closed")
            
        except Exception as e:
            logger.error(f"Error closing async HTTP client: {e}")
    
    async def get(self, url: str, **kwargs) -> Optional[Dict]:
        """Async GET request"""
        return await self._request('GET', url, **kwargs)
    
    async def post(self, url: str, data: Any = None, **kwargs) -> Optional[Dict]:
        """Async POST request"""
        return await self._request('POST', url, data=data, **kwargs)
    
    async def put(self, url: str, data: Any = None, **kwargs) -> Optional[Dict]:
        """Async PUT request"""
        return await self._request('PUT', url, data=data, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Optional[Dict]:
        """Async DELETE request"""
        return await self._request('DELETE', url, **kwargs)
    
    async def _request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Make an async HTTP request with retry logic"""
        
        # Check rate limiting
        if not await self._check_rate_limit(url):
            logger.warning(f"Rate limit exceeded for {url}")
            return None
        
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                self.stats['total_requests'] += 1
                
                # Make the request
                response_data = await self._make_request(method, url, **kwargs)
                
                if response_data is not None:
                    self.stats['successful_requests'] += 1
                    return response_data
                else:
                    # Failed request, prepare for retry
                    if attempt < self.retry_attempts - 1:
                        self.stats['retry_requests'] += 1
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                
            except Exception as e:
                last_exception = e
                logger.error(f"Request attempt {attempt + 1} failed for {method} {url}: {e}")
                
                if attempt < self.retry_attempts - 1:
                    self.stats['retry_requests'] += 1
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # All attempts failed
        self.stats['failed_requests'] += 1
        logger.error(f"All {self.retry_attempts} attempts failed for {method} {url}")
        
        if last_exception:
            raise last_exception
        
        return None
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Make a single HTTP request"""
        try:
            # Prepare request data
            request_kwargs = {}
            
            if 'data' in kwargs and kwargs['data'] is not None:
                if isinstance(kwargs['data'], dict):
                    request_kwargs['json'] = kwargs['data']
                else:
                    request_kwargs['data'] = kwargs['data']
            
            if 'headers' in kwargs:
                request_kwargs['headers'] = kwargs['headers']
            
            if 'params' in kwargs:
                request_kwargs['params'] = kwargs['params']
            
            # Make the request
            async with self.session.request(method, url, **request_kwargs) as response:
                # Check response status
                if response.status >= 400:
                    error_text = await response.text()
                    logger.warning(f"HTTP {response.status} for {method} {url}: {error_text}")
                    return None
                
                # Try to parse JSON response
                try:
                    if response.content_type == 'application/json':
                        return await response.json()
                    else:
                        # Return text content wrapped in dict
                        text_content = await response.text()
                        return {'content': text_content, 'content_type': response.content_type}
                
                except Exception as e:
                    logger.warning(f"Error parsing response from {url}: {e}")
                    return {'raw_response': await response.text()}
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {method} {url}")
            return None
        
        except Exception as e:
            logger.error(f"Request error for {method} {url}: {e}")
            raise
    
    async def _check_rate_limit(self, url: str) -> bool:
        """Check if request is within rate limits"""
        try:
            # Extract domain for rate limiting
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            if not domain:
                return True
            
            current_time = time.time()
            
            # Initialize rate limit tracking for domain
            if domain not in self.rate_limiter:
                self.rate_limiter[domain] = {
                    'requests': [],
                    'limit': 100,  # requests per minute
                    'window': 60   # seconds
                }
            
            rate_info = self.rate_limiter[domain]
            
            # Clean old requests outside the window
            rate_info['requests'] = [
                req_time for req_time in rate_info['requests'] 
                if current_time - req_time < rate_info['window']
            ]
            
            # Check if we're within limits
            if len(rate_info['requests']) >= rate_info['limit']:
                return False
            
            # Add current request
            rate_info['requests'].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow request on error
    
    async def batch_get(self, urls: List[str], max_concurrent: int = 10) -> List[Dict]:
        """Make multiple GET requests concurrently"""
        return await self.batch_requests([('GET', url) for url in urls], max_concurrent)
    
    async def batch_requests(self, 
                           requests: List[tuple], 
                           max_concurrent: int = 10) -> List[Dict]:
        """Make multiple requests concurrently with semaphore control"""
        
        if not requests:
            return []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _bounded_request(method: str, url: str, **kwargs):
            async with semaphore:
                return await self._request(method, url, **kwargs)
        
        # Create tasks for all requests
        tasks = []
        for request in requests:
            if len(request) == 2:
                method, url = request
                task = asyncio.create_task(_bounded_request(method, url))
            elif len(request) == 3:
                method, url, kwargs = request
                task = asyncio.create_task(_bounded_request(method, url, **kwargs))
            else:
                continue
            
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch request {i} failed: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def health_check_services(self, services: Dict[str, str]) -> Dict[str, bool]:
        """Check health of multiple services concurrently"""
        
        health_requests = []
        for service_name, health_url in services.items():
            health_requests.append(('GET', health_url))
        
        results = await self.batch_requests(health_requests, max_concurrent=20)
        
        # Process health check results
        health_status = {}
        for i, (service_name, _) in enumerate(services.items()):
            result = results[i] if i < len(results) else None
            
            if result is not None:
                # Service responded
                health_status[service_name] = True
            else:
                # Service didn't respond or error occurred
                health_status[service_name] = False
        
        return health_status
    
    async def fetch_metrics_from_endpoints(self, endpoints: List[Dict]) -> List[Dict]:
        """Fetch metrics from multiple endpoints concurrently"""
        
        metrics_requests = []
        for endpoint in endpoints:
            url = endpoint.get('url')
            method = endpoint.get('method', 'GET')
            headers = endpoint.get('headers', {})
            
            if url:
                if method.upper() == 'GET':
                    metrics_requests.append(('GET', url, {'headers': headers}))
                elif method.upper() == 'POST':
                    data = endpoint.get('data', {})
                    metrics_requests.append(('POST', url, {'headers': headers, 'data': data}))
        
        results = await self.batch_requests(metrics_requests, max_concurrent=15)
        
        # Combine results with endpoint info
        metrics_data = []
        for i, endpoint in enumerate(endpoints):
            result = results[i] if i < len(results) else None
            
            metrics_data.append({
                'endpoint': endpoint.get('name', f'endpoint_{i}'),
                'url': endpoint.get('url'),
                'data': result,
                'timestamp': datetime.utcnow(),
                'success': result is not None
            })
        
        return metrics_data
    
    def get_stats(self) -> Dict:
        """Get client statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        success_rate = 0
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_requests'] / self.stats['total_requests']) * 100
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.stats['total_requests'],
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'retry_requests': self.stats['retry_requests'],
            'success_rate_percent': round(success_rate, 2),
            'active_connections': len(self.connector._conns) if self.connector else 0,
            'rate_limited_domains': len(self.rate_limiter)
        }


# Global async HTTP client instance
async_http_client = AsyncHTTPClient()

async def start_async_http_client():
    """Start the global async HTTP client"""
    await async_http_client.start()
    logger.info("Global async HTTP client started")

async def stop_async_http_client():
    """Stop the global async HTTP client"""
    await async_http_client.close()
    logger.info("Global async HTTP client stopped")

# Context manager for temporary HTTP client
async def get_http_client(**kwargs) -> AsyncHTTPClient:
    """Get a temporary HTTP client (context manager)"""
    client = AsyncHTTPClient(**kwargs)
    return client

if __name__ == '__main__':
    # For testing
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_client():
        """Test the async HTTP client"""
        
        async with AsyncHTTPClient() as client:
            # Test single request
            result = await client.get('https://httpbin.org/json')
            print(f"Single request result: {result}")
            
            # Test batch requests
            urls = [
                'https://httpbin.org/json',
                'https://httpbin.org/uuid',
                'https://httpbin.org/ip'
            ]
            
            batch_results = await client.batch_get(urls)
            print(f"Batch results: {len(batch_results)} responses")
            
            # Show stats
            stats = client.get_stats()
            print(f"Client stats: {stats}")
    
    # Run test
    try:
        asyncio.run(test_client())
    except KeyboardInterrupt:
        print("Test interrupted") 