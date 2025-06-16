import os
import json
import logging
import datetime
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from app import db
from models import FlowData
import config

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Manages storage of flow data in both local database and external storage (Minio)
    """
    
    def __init__(self):
        """Initialize the storage manager"""
        self.use_external_storage = config.USE_EXTERNAL_STORAGE
        self.minio_client = None
        
        # Performance optimization settings
        self.max_batch_size = 1000  # Maximum size of batch for bulk operations
        self.max_external_batch_size = 100  # Maximum batch size for external storage operations
        
        # Initialize Minio client if external storage is enabled
        if self.use_external_storage:
            self._init_minio_client()
    
    def _init_minio_client(self):
        """Initialize the Minio client"""
        try:
            self.minio_client = Minio(
                endpoint=config.MINIO_ENDPOINT,
                access_key=config.MINIO_ACCESS_KEY,
                secret_key=config.MINIO_SECRET_KEY,
                secure=config.MINIO_SECURE  # Use HTTPS if enabled
            )
            
            # Create bucket if it doesn't exist
            if not self.minio_client.bucket_exists(config.MINIO_BUCKET):
                self.minio_client.make_bucket(config.MINIO_BUCKET)
                logger.info(f"Created Minio bucket: {config.MINIO_BUCKET}")
            
            logger.info(f"Connected to Minio storage: {config.MINIO_ENDPOINT}")
            return True
            
        except S3Error as e:
            logger.error(f"Error initializing Minio client: {str(e)}")
            self.use_external_storage = False
            return False
    
    def store_flow_data(self, flow_data, device_id, flow_type, raw_data=None, store_locally=True):
        """
        Store flow data in the selected storage
        
        Args:
            flow_data (dict): Parsed flow data
            device_id (int): Device ID
            flow_type (str): Flow type and version (e.g., netflow5)
            raw_data (bytes): Raw flow packet data (if available)
            store_locally (bool): Whether to store in local database
        
        Returns:
            FlowData: Stored flow data record or None
        """
        # Store in local database if requested
        db_record = None
        if store_locally:
            db_record = self._store_in_database(flow_data, device_id, flow_type)
        
        # Store in external storage if enabled
        if self.use_external_storage and raw_data:
            self._store_in_minio(flow_data, raw_data, device_id, flow_type)
        
        return db_record
    
    def _store_in_database(self, flow_data, device_id, flow_type):
        """
        Store flow data in the local database
        
        Args:
            flow_data (dict): Parsed flow data
            device_id (int): Device ID
            flow_type (str): Flow type and version
        
        Returns:
            FlowData: Stored flow data record
        """
        try:
            # Create flow data record
            record = FlowData(
                device_id=device_id,
                flow_type=flow_type,
                src_ip=flow_data.get('src_ip', '0.0.0.0'),
                dst_ip=flow_data.get('dst_ip', '0.0.0.0'),
                src_port=flow_data.get('src_port'),
                dst_port=flow_data.get('dst_port'),
                protocol=flow_data.get('protocol'),
                tos=flow_data.get('tos'),
                bytes=flow_data.get('bytes', 0),
                packets=flow_data.get('packets', 0),
                start_time=flow_data.get('start_time'),
                end_time=flow_data.get('end_time'),
                timestamp=datetime.datetime.now(),
                raw_data=json.dumps(flow_data)
            )
            
            db.session.add(record)
            db.session.commit()
            
            return record
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing flow data in database: {str(e)}")
            return None
    
    def _store_in_minio(self, flow_data, raw_data, device_id, flow_type):
        """
        Store raw flow data in Minio
        
        Args:
            flow_data (dict): Parsed flow data
            raw_data (bytes): Raw flow packet data
            device_id (int): Device ID
            flow_type (str): Flow type and version
        
        Returns:
            bool: Success/failure
        """
        if not self.minio_client:
            return False
            
        try:
            # Generate object name based on timestamp and flow info
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            object_name = f"flows/{flow_type}/{device_id}/{timestamp}.flow"
            
            # Store raw data
            data_stream = BytesIO(raw_data)
            self.minio_client.put_object(
                bucket_name=config.MINIO_BUCKET,
                object_name=object_name,
                data=data_stream,
                length=len(raw_data),
                content_type='application/octet-stream'
            )
            
            # Store metadata
            metadata = {
                'device_id': str(device_id),
                'flow_type': flow_type,
                'src_ip': flow_data.get('src_ip', '0.0.0.0'),
                'dst_ip': flow_data.get('dst_ip', '0.0.0.0'),
                'timestamp': timestamp
            }
            
            metadata_object_name = f"{object_name}.meta.json"
            metadata_stream = BytesIO(json.dumps(metadata).encode('utf-8'))
            self.minio_client.put_object(
                bucket_name=config.MINIO_BUCKET,
                object_name=metadata_object_name,
                data=metadata_stream,
                length=len(json.dumps(metadata)),
                content_type='application/json'
            )
            
            logger.debug(f"Stored flow data in Minio: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"Error storing flow data in Minio: {str(e)}")
            return False
    
    def retrieve_flow_data(self, flow_id=None, device_id=None, start_time=None, end_time=None, limit=1000):
        """
        Retrieve flow data from storage
        
        Args:
            flow_id (int): Specific flow ID to retrieve
            device_id (int): Filter by device ID
            start_time (datetime): Start time for filtering
            end_time (datetime): End time for filtering
            limit (int): Maximum number of records to return
        
        Returns:
            list: List of flow data records
        """
        try:
            query = FlowData.query
            
            # Apply filters
            if flow_id:
                query = query.filter(FlowData.id == flow_id)
            
            if device_id:
                query = query.filter(FlowData.device_id == device_id)
            
            if start_time:
                query = query.filter(FlowData.timestamp >= start_time)
            
            if end_time:
                query = query.filter(FlowData.timestamp <= end_time)
            
            # Order by timestamp and limit
            query = query.order_by(FlowData.timestamp.desc()).limit(limit)
            
            # Execute query
            results = query.all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving flow data: {str(e)}")
            return []
    
    def retrieve_external_flow_data(self, device_id=None, flow_type=None, start_time=None, end_time=None, limit=100):
        """
        Retrieve flow data from external storage (Minio)
        
        Args:
            device_id (int): Filter by device ID
            flow_type (str): Filter by flow type
            start_time (datetime): Start time for filtering
            end_time (datetime): End time for filtering
            limit (int): Maximum number of objects to return
        
        Returns:
            list: List of flow data objects
        """
        if not self.minio_client:
            return []
            
        try:
            # Construct prefix for listing objects
            prefix = "flows/"
            
            if flow_type:
                prefix += f"{flow_type}/"
                
                if device_id:
                    prefix += f"{device_id}/"
            
            # List objects
            objects = list(self.minio_client.list_objects(
                bucket_name=config.MINIO_BUCKET,
                prefix=prefix,
                recursive=True
            ))
            
            # Sort and limit results
            objects.sort(key=lambda obj: obj.last_modified, reverse=True)
            objects = objects[:limit]
            
            # Filter by time range if specified
            if start_time or end_time:
                filtered_objects = []
                for obj in objects:
                    # Extract timestamp from object name
                    try:
                        obj_time_parts = obj.object_name.split('/')[-1].split('.')[0].split('_')
                        obj_time_str = f"{obj_time_parts[0][:4]}-{obj_time_parts[0][4:6]}-{obj_time_parts[0][6:8]} " \
                                      f"{obj_time_parts[1][:2]}:{obj_time_parts[1][2:4]}:{obj_time_parts[1][4:6]}"
                        obj_time = datetime.datetime.strptime(obj_time_str, '%Y-%m-%d %H:%M:%S')
                        
                        if start_time and obj_time < start_time:
                            continue
                        
                        if end_time and obj_time > end_time:
                            continue
                        
                        filtered_objects.append(obj)
                    except (IndexError, ValueError):
                        continue
                
                objects = filtered_objects
            
            # Return only objects that are actual flow data (not metadata)
            return [obj for obj in objects if not obj.object_name.endswith('.meta.json')]
            
        except S3Error as e:
            logger.error(f"Error retrieving flow data from Minio: {str(e)}")
            return []
    
    def clean_old_data(self, days=None):
        """
        Clean old flow data from storage
        
        Args:
            days (int): Number of days to keep data, defaults to FLOW_RETENTION_DAYS
        
        Returns:
            tuple: (local_cleaned, external_cleaned) counts
        """
        if days is None:
            days = config.FLOW_RETENTION_DAYS
            
        local_cleaned = self._clean_old_database_data(days)
        external_cleaned = 0
        
        if self.use_external_storage and self.minio_client:
            external_cleaned = self._clean_old_minio_data(days)
        
        return local_cleaned, external_cleaned
    
    def _clean_old_database_data(self, days):
        """
        Clean old data from local database
        
        Args:
            days (int): Number of days to keep data
        
        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            result = db.session.query(FlowData).filter(FlowData.timestamp < cutoff_date).delete()
            db.session.commit()
            
            logger.info(f"Cleaned {result} old flow records from database")
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning old database data: {str(e)}")
            return 0
    
    def _clean_old_minio_data(self, days):
        """
        Clean old data from Minio
        
        Args:
            days (int): Number of days to keep data
        
        Returns:
            int: Number of objects deleted
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            deleted_count = 0
            
            # Get all objects older than cutoff date
            objects = list(self.minio_client.list_objects(
                bucket_name=config.MINIO_BUCKET,
                prefix="flows/",
                recursive=True
            ))
            
            objects_to_delete = []
            for obj in objects:
                if obj.last_modified < cutoff_date:
                    objects_to_delete.append(obj.object_name)
            
            # Delete objects in batches
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                errors = self.minio_client.remove_objects(
                    bucket_name=config.MINIO_BUCKET,
                    delete_object_list=batch
                )
                
                # Count successful deletions
                error_count = sum(1 for _ in errors)
                deleted_count += len(batch) - error_count
            
            logger.info(f"Cleaned {deleted_count} old flow objects from Minio")
            return deleted_count
            
        except S3Error as e:
            logger.error(f"Error cleaning old Minio data: {str(e)}")
            return 0

    def store_flow_batch(self, flow_batch):
        """
        Store a batch of flow data for improved performance
        
        Args:
            flow_batch (list): List of flow data items to store
                Each item is a dict with: 
                - flow_data: The actual flow data
                - device_id: Device ID
                - flow_type: Flow type and version
                - raw_data: Optional raw packet data
                - timestamp: Timestamp of the flow
        
        Returns:
            int: Number of items successfully stored
        """
        if not flow_batch:
            return 0
            
        # Split batch if it exceeds maximum size
        if len(flow_batch) > self.max_batch_size:
            logger.info(f"Splitting large batch of {len(flow_batch)} items")
            results = []
            for i in range(0, len(flow_batch), self.max_batch_size):
                sub_batch = flow_batch[i:i+self.max_batch_size]
                results.append(self.store_flow_batch(sub_batch))
            return sum(results)
            
        # Process database batch
        success_count = self._store_batch_in_database(flow_batch)
        
        # Process external storage batch if enabled
        if self.use_external_storage and self.minio_client:
            # Filter items that have raw data
            external_batch = [item for item in flow_batch if 'raw_data' in item and item['raw_data']]
            
            # Process in smaller sub-batches to avoid overwhelming external storage
            for i in range(0, len(external_batch), self.max_external_batch_size):
                sub_batch = external_batch[i:i+self.max_external_batch_size]
                self._store_batch_in_minio(sub_batch)
        
        return success_count
        
    def _store_batch_in_database(self, flow_batch):
        """
        Store a batch of flow data in the database using bulk insert
        
        Args:
            flow_batch (list): List of flow data items to store
        
        Returns:
            int: Number of items successfully stored
        """
        if not flow_batch:
            return 0
            
        try:
            # Prepare records for bulk insert
            records = []
            
            for item in flow_batch:
                flow_data = item['flow_data']
                device_id = item['device_id']
                flow_type = item['flow_type']
                
                record = FlowData(
                    device_id=device_id,
                    flow_type=flow_type,
                    src_ip=flow_data.get('src_ip', '0.0.0.0'),
                    dst_ip=flow_data.get('dst_ip', '0.0.0.0'),
                    src_port=flow_data.get('src_port'),
                    dst_port=flow_data.get('dst_port'),
                    protocol=flow_data.get('protocol'),
                    tos=flow_data.get('tos'),
                    bytes=flow_data.get('bytes', 0),
                    packets=flow_data.get('packets', 0),
                    start_time=flow_data.get('start_time'),
                    end_time=flow_data.get('end_time'),
                    timestamp=item.get('timestamp', datetime.datetime.now()),
                    raw_data=json.dumps(flow_data)
                )
                records.append(record)
            
            # Add all records in one transaction
            db.session.add_all(records)
            db.session.commit()
            
            return len(records)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing flow batch in database: {str(e)}")
            return 0
            
    def _store_batch_in_minio(self, flow_batch):
        """
        Store a batch of flow data in Minio
        
        Args:
            flow_batch (list): List of flow data items to store
        
        Returns:
            int: Number of items successfully stored
        """
        if not self.minio_client or not flow_batch:
            return 0
            
        success_count = 0
        
        for item in flow_batch:
            try:
                flow_data = item['flow_data']
                device_id = item['device_id']
                flow_type = item['flow_type']
                raw_data = item['raw_data']
                
                # Generate object name based on timestamp and flow info
                timestamp = item.get('timestamp', datetime.datetime.now()).strftime('%Y%m%d_%H%M%S_%f')
                object_name = f"flows/{flow_type}/{device_id}/{timestamp}.flow"
                
                # Store raw data
                data_stream = BytesIO(raw_data)
                self.minio_client.put_object(
                    bucket_name=config.MINIO_BUCKET,
                    object_name=object_name,
                    data=data_stream,
                    length=len(raw_data),
                    content_type='application/octet-stream'
                )
                
                # Store metadata
                metadata = {
                    'device_id': str(device_id),
                    'flow_type': flow_type,
                    'src_ip': flow_data.get('src_ip', '0.0.0.0'),
                    'dst_ip': flow_data.get('dst_ip', '0.0.0.0'),
                    'timestamp': timestamp
                }
                
                metadata_object_name = f"{object_name}.meta.json"
                metadata_stream = BytesIO(json.dumps(metadata).encode('utf-8'))
                self.minio_client.put_object(
                    bucket_name=config.MINIO_BUCKET,
                    object_name=metadata_object_name,
                    data=metadata_stream,
                    length=len(json.dumps(metadata)),
                    content_type='application/json'
                )
                
                success_count += 1
                
            except S3Error as e:
                logger.error(f"Error storing flow in Minio: {str(e)}")
                continue
        
        return success_count

# Global storage manager instance
storage_manager = None

def get_storage_manager():
    """Get the global storage manager instance"""
    global storage_manager
    if storage_manager is None:
        storage_manager = StorageManager()
    return storage_manager