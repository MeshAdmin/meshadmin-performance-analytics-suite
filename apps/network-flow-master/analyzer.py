import logging
import json
import pandas as pd
import numpy as np
from sqlalchemy import func, desc, asc
from datetime import datetime, timedelta
from database import db
from ai_insights import FlowAnomalyDetector, TrafficPatternAnalyzer

logger = logging.getLogger(__name__)

class FlowAnalyzer:
    """
    Analyzes NetFlow and sFlow data to provide insights and visualizations
    """
    
    def __init__(self):
        """Initialize the flow analyzer"""
        self.anomaly_detector = FlowAnomalyDetector()
        self.pattern_analyzer = TrafficPatternAnalyzer()
    
    def get_flow_statistics(self, start_time=None, end_time=None, device_id=None, 
                            src_ip=None, dst_ip=None, protocol=None, limit=1000):
        """
        Get flow statistics for a given time period and filters
        
        Args:
            start_time (datetime): Start time for analysis
            end_time (datetime): End time for analysis
            device_id (int): Filter by device ID
            src_ip (str): Filter by source IP
            dst_ip (str): Filter by destination IP
            protocol (int): Filter by protocol
            limit (int): Maximum number of records to return
        
        Returns:
            dict: Flow statistics
        """
        from models import FlowData
        
        try:
            # Build the query with filters
            query = db.session.query(FlowData)
            
            if start_time:
                query = query.filter(FlowData.timestamp >= start_time)
            
            if end_time:
                query = query.filter(FlowData.timestamp <= end_time)
            
            if device_id:
                query = query.filter(FlowData.device_id == device_id)
            
            if src_ip:
                query = query.filter(FlowData.src_ip == src_ip)
            
            if dst_ip:
                query = query.filter(FlowData.dst_ip == dst_ip)
            
            if protocol:
                query = query.filter(FlowData.protocol == protocol)
            
            # Get total record count
            total_count = query.count()
            
            # Get the flow records
            flows = query.order_by(desc(FlowData.timestamp)).limit(limit).all()
            
            # Calculate basic statistics
            if flows:
                # Convert to pandas DataFrame for easier analysis
                flow_data = pd.DataFrame([{
                    'id': flow.id,
                    'timestamp': flow.timestamp,
                    'flow_type': flow.flow_type,
                    'src_ip': flow.src_ip,
                    'dst_ip': flow.dst_ip,
                    'src_port': flow.src_port,
                    'dst_port': flow.dst_port,
                    'protocol': flow.protocol,
                    'bytes': flow.bytes,
                    'packets': flow.packets
                } for flow in flows])
                
                # Calculate statistics
                stats = {
                    'total_flows': total_count,
                    'total_bytes': int(flow_data['bytes'].sum()),
                    'total_packets': int(flow_data['packets'].sum()),
                    'avg_bytes_per_flow': int(flow_data['bytes'].mean()),
                    'avg_packets_per_flow': int(flow_data['packets'].mean()),
                    'protocol_distribution': flow_data.groupby('protocol').size().to_dict(),
                    'top_source_ips': flow_data.groupby('src_ip').size().nlargest(10).to_dict(),
                    'top_destination_ips': flow_data.groupby('dst_ip').size().nlargest(10).to_dict(),
                    'flow_types': flow_data.groupby('flow_type').size().to_dict(),
                }
                
                # Convert flow records to dictionaries
                formatted_flows = [{
                    'id': flow.id,
                    'timestamp': flow.timestamp.isoformat(),
                    'flow_type': flow.flow_type,
                    'src_ip': flow.src_ip,
                    'dst_ip': flow.dst_ip,
                    'src_port': flow.src_port,
                    'dst_port': flow.dst_port,
                    'protocol': flow.protocol,
                    'protocol_name': self._get_protocol_name(flow.protocol),
                    'bytes': flow.bytes,
                    'packets': flow.packets
                } for flow in flows]
                
                return {
                    'statistics': stats,
                    'flows': formatted_flows
                }
            else:
                return {
                    'statistics': {
                        'total_flows': 0,
                        'total_bytes': 0,
                        'total_packets': 0,
                    },
                    'flows': []
                }
        
        except Exception as e:
            logger.error(f"Error getting flow statistics: {str(e)}")
            return {
                'error': str(e),
                'statistics': {},
                'flows': []
            }
    
    def get_device_summary(self, device_id=None):
        """
        Get a summary of flow data for devices
        
        Args:
            device_id (int): Optional device ID to filter by
        
        Returns:
            dict: Device summary
        """
        from models import FlowData, Device
        
        try:
            # Get devices
            if device_id:
                devices = Device.query.filter_by(id=device_id).all()
            else:
                devices = Device.query.all()
            
            device_summaries = []
            for device in devices:
                # Get flow statistics for this device
                flow_count = db.session.query(func.count(FlowData.id)).filter(
                    FlowData.device_id == device.id
                ).scalar()
                
                # Get total bytes
                total_bytes = db.session.query(func.sum(FlowData.bytes)).filter(
                    FlowData.device_id == device.id
                ).scalar() or 0
                
                # Get recent flows
                recent_flows = FlowData.query.filter_by(
                    device_id=device.id
                ).order_by(desc(FlowData.timestamp)).limit(5).all()
                
                # Format device summary
                device_summary = {
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'device_type': device.device_type,
                    'flow_type': device.flow_type,
                    'flow_version': device.flow_version,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                    'statistics': {
                        'flow_count': flow_count,
                        'total_bytes': total_bytes,
                    },
                    'recent_flows': [{
                        'id': flow.id,
                        'timestamp': flow.timestamp.isoformat(),
                        'src_ip': flow.src_ip,
                        'dst_ip': flow.dst_ip,
                        'bytes': flow.bytes,
                        'packets': flow.packets
                    } for flow in recent_flows]
                }
                
                device_summaries.append(device_summary)
            
            return {
                'devices': device_summaries
            }
        
        except Exception as e:
            logger.error(f"Error getting device summary: {str(e)}")
            return {
                'error': str(e),
                'devices': []
            }
    
    def get_time_series_data(self, start_time=None, end_time=None, device_id=None, 
                            interval='1h', metric='bytes'):
        """
        Get time series data for flow metrics
        
        Args:
            start_time (datetime): Start time for analysis
            end_time (datetime): End time for analysis
            device_id (int): Filter by device ID
            interval (str): Time interval for binning ('1h', '1d', etc.)
            metric (str): Metric to analyze ('bytes', 'packets', 'flows')
        
        Returns:
            dict: Time series data
        """
        from models import FlowData
        
        try:
            # Set default time range if not provided
            if not end_time:
                end_time = datetime.utcnow()
            
            if not start_time:
                start_time = end_time - timedelta(hours=24)
            
            # Build query base
            query = db.session.query(FlowData)
            
            # Apply filters
            query = query.filter(FlowData.timestamp >= start_time)
            query = query.filter(FlowData.timestamp <= end_time)
            
            if device_id:
                query = query.filter(FlowData.device_id == device_id)
            
            # Get all flows in the time range
            flows = query.order_by(asc(FlowData.timestamp)).all()
            
            if not flows:
                return {
                    'labels': [],
                    'data': []
                }
            
            # Convert to DataFrame for time series analysis
            df = pd.DataFrame([{
                'timestamp': flow.timestamp,
                'bytes': flow.bytes,
                'packets': flow.packets,
                'flow_type': flow.flow_type
            } for flow in flows])
            
            # Set the timestamp as index
            df.set_index('timestamp', inplace=True)
            
            # Resample based on interval
            if interval == '1h':
                resampled = df.resample('1H')
            elif interval == '15m':
                resampled = df.resample('15T')
            elif interval == '1d':
                resampled = df.resample('1D')
            else:
                resampled = df.resample('1H')  # Default to hourly
            
            # Calculate the requested metric
            if metric == 'bytes':
                result = resampled.sum()['bytes']
            elif metric == 'packets':
                result = resampled.sum()['packets']
            elif metric == 'flows':
                result = resampled.count()['bytes']  # Count rows
            else:
                result = resampled.sum()['bytes']  # Default to bytes
            
            # Format for the chart
            labels = [ts.strftime('%Y-%m-%d %H:%M') for ts in result.index]
            data = result.tolist()
            
            return {
                'labels': labels,
                'data': data
            }
        
        except Exception as e:
            logger.error(f"Error getting time series data: {str(e)}")
            return {
                'error': str(e),
                'labels': [],
                'data': []
            }
    
    def detect_anomalies(self, device_id=None, start_time=None, end_time=None):
        """
        Detect anomalies in flow data
        
        Args:
            device_id (int): Optional device ID to filter by
            start_time (datetime): Start time for analysis
            end_time (datetime): End time for analysis
        
        Returns:
            dict: Anomaly detection results
        """
        from models import FlowData, AnalysisResult
        
        try:
            # Set default time range if not provided
            if not end_time:
                end_time = datetime.utcnow()
            
            if not start_time:
                start_time = end_time - timedelta(hours=24)
            
            # Get flow data for analysis
            query = db.session.query(FlowData)
            query = query.filter(FlowData.timestamp >= start_time)
            query = query.filter(FlowData.timestamp <= end_time)
            
            if device_id:
                query = query.filter(FlowData.device_id == device_id)
            
            flows = query.all()
            
            if not flows:
                return {
                    'anomalies': [],
                    'message': 'No flow data available for anomaly detection'
                }
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([{
                'id': flow.id,
                'timestamp': flow.timestamp,
                'device_id': flow.device_id,
                'src_ip': flow.src_ip,
                'dst_ip': flow.dst_ip,
                'src_port': flow.src_port,
                'dst_port': flow.dst_port,
                'protocol': flow.protocol,
                'bytes': flow.bytes,
                'packets': flow.packets
            } for flow in flows])
            
            # Detect anomalies
            anomalies = self.anomaly_detector.detect(df)
            
            # Store results in database
            if anomalies and len(anomalies) > 0:
                result = AnalysisResult(
                    device_id=device_id,
                    analysis_type='anomaly',
                    result_data=json.dumps(anomalies),
                    confidence=0.8,  # Example confidence score
                    timestamp=datetime.utcnow()
                )
                db.session.add(result)
                db.session.commit()
            
            return {
                'anomalies': anomalies
            }
        
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return {
                'error': str(e),
                'anomalies': []
            }
    
    def analyze_traffic_patterns(self, device_id=None, start_time=None, end_time=None):
        """
        Analyze traffic patterns in flow data
        
        Args:
            device_id (int): Optional device ID to filter by
            start_time (datetime): Start time for analysis
            end_time (datetime): End time for analysis
        
        Returns:
            dict: Traffic pattern analysis results
        """
        from models import FlowData, AnalysisResult
        
        try:
            # Set default time range if not provided
            if not end_time:
                end_time = datetime.utcnow()
            
            if not start_time:
                start_time = end_time - timedelta(hours=24)
            
            # Get flow data for analysis
            query = db.session.query(FlowData)
            query = query.filter(FlowData.timestamp >= start_time)
            query = query.filter(FlowData.timestamp <= end_time)
            
            if device_id:
                query = query.filter(FlowData.device_id == device_id)
            
            flows = query.all()
            
            if not flows:
                return {
                    'patterns': {},
                    'message': 'No flow data available for pattern analysis'
                }
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([{
                'id': flow.id,
                'timestamp': flow.timestamp,
                'device_id': flow.device_id,
                'src_ip': flow.src_ip,
                'dst_ip': flow.dst_ip,
                'src_port': flow.src_port,
                'dst_port': flow.dst_port,
                'protocol': flow.protocol,
                'bytes': flow.bytes,
                'packets': flow.packets
            } for flow in flows])
            
            # Analyze traffic patterns
            patterns = self.pattern_analyzer.analyze(df)
            
            # Store results in database
            if patterns:
                result = AnalysisResult(
                    device_id=device_id,
                    analysis_type='traffic_pattern',
                    result_data=json.dumps(patterns),
                    confidence=0.9,  # Example confidence score
                    timestamp=datetime.utcnow()
                )
                db.session.add(result)
                db.session.commit()
            
            return {
                'patterns': patterns
            }
        
        except Exception as e:
            logger.error(f"Error analyzing traffic patterns: {str(e)}")
            return {
                'error': str(e),
                'patterns': {}
            }
    
    def _get_protocol_name(self, protocol_number):
        """
        Get the name of a protocol by number
        
        Args:
            protocol_number (int): Protocol number
        
        Returns:
            str: Protocol name
        """
        protocols = {
            1: "ICMP",
            6: "TCP",
            17: "UDP",
            47: "GRE",
            50: "ESP",
            51: "AH",
            58: "IPv6-ICMP",
            89: "OSPF",
            132: "SCTP"
        }
        
        return protocols.get(protocol_number, f"Protocol {protocol_number}")
