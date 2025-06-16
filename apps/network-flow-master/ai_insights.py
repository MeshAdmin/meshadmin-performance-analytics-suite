import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from database import db

logger = logging.getLogger(__name__)

class FlowAnomalyDetector:
    """
    Uses machine learning to detect anomalies in flow data
    """
    
    def __init__(self):
        """Initialize the anomaly detector"""
        self.model = IsolationForest(
            n_estimators=100,
            max_samples='auto',
            contamination=0.05,  # Assume 5% of data might be anomalous
            random_state=42
        )
    
    def detect(self, flow_data):
        """
        Detect anomalies in flow data
        
        Args:
            flow_data (DataFrame): Pandas DataFrame with flow data
        
        Returns:
            list: List of detected anomalies
        """
        try:
            if len(flow_data) < 10:
                logger.info("Not enough data for anomaly detection, minimum 10 flows needed")
                return []
            
            # Extract features for anomaly detection
            features = flow_data[['bytes', 'packets']].copy()
            
            # Add derived features
            if 'timestamp' in flow_data.columns:
                flow_data['hour'] = flow_data['timestamp'].dt.hour
                features['hour'] = flow_data['timestamp'].dt.hour
            
            # Add bytes per packet ratio
            features['bytes_per_packet'] = features['bytes'] / features['packets'].replace(0, 1)
            
            # Normalize features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)
            
            # Fit the model and predict
            self.model.fit(scaled_features)
            predictions = self.model.predict(scaled_features)
            
            # Isolation Forest returns -1 for anomalies and 1 for normal data
            anomaly_indices = np.where(predictions == -1)[0]
            
            # Prepare results
            anomalies = []
            for idx in anomaly_indices:
                flow = flow_data.iloc[idx]
                anomaly = {
                    'flow_id': int(flow['id']) if 'id' in flow else None,
                    'timestamp': flow['timestamp'].isoformat() if 'timestamp' in flow else None,
                    'src_ip': flow['src_ip'],
                    'dst_ip': flow['dst_ip'],
                    'protocol': int(flow['protocol']),
                    'bytes': int(flow['bytes']),
                    'packets': int(flow['packets']),
                    'score': float(self.model.score_samples(scaled_features[idx].reshape(1, -1))[0]),
                    'reason': self._get_anomaly_reason(flow, features.iloc[idx], scaled_features[idx])
                }
                anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []
    
    def _get_anomaly_reason(self, flow, features, scaled_features):
        """
        Determine the reason why a flow was classified as anomalous
        
        Args:
            flow (Series): Original flow data
            features (Series): Extracted features
            scaled_features (array): Normalized features
        
        Returns:
            str: Reason for anomaly classification
        """
        # Check for unusually large flow
        if features['bytes'] > features['bytes'].mean() * 3:
            return "Unusually large flow size"
        
        # Check for unusual bytes/packet ratio
        if features['bytes_per_packet'] > 1500:
            return "Unusually high bytes per packet ratio"
        
        # Check for unusual protocol behavior
        if flow['protocol'] not in [6, 17]:  # Not TCP or UDP
            return "Unusual protocol"
        
        # Check for unusual hour (if time data is available)
        if 'hour' in features and (features['hour'] < 8 or features['hour'] > 18):
            return "Activity outside normal business hours"
        
        # Generic reason
        return "Statistical outlier in flow patterns"


class TrafficPatternAnalyzer:
    """
    Analyzes network traffic patterns to identify trends and behaviors
    """
    
    def __init__(self):
        """Initialize the traffic pattern analyzer"""
        pass
    
    def analyze(self, flow_data):
        """
        Analyze traffic patterns in flow data
        
        Args:
            flow_data (DataFrame): Pandas DataFrame with flow data
        
        Returns:
            dict: Analysis results
        """
        try:
            if len(flow_data) < 10:
                logger.info("Not enough data for pattern analysis, minimum 10 flows needed")
                return {}
            
            results = {}
            
            # Add time-based analysis if timestamp is available
            if 'timestamp' in flow_data.columns:
                results['time_patterns'] = self._analyze_time_patterns(flow_data)
            
            # Add protocol distribution
            results['protocol_distribution'] = self._analyze_protocol_distribution(flow_data)
            
            # Add communication patterns
            results['communication_patterns'] = self._analyze_communication_patterns(flow_data)
            
            # Add flow size analysis
            results['flow_size_patterns'] = self._analyze_flow_sizes(flow_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing traffic patterns: {str(e)}")
            return {}
    
    def _analyze_time_patterns(self, flow_data):
        """
        Analyze time patterns in flow data
        
        Args:
            flow_data (DataFrame): Flow data with timestamp column
        
        Returns:
            dict: Time pattern analysis
        """
        # Extract hour of day
        flow_data['hour'] = flow_data['timestamp'].dt.hour
        flow_data['day_of_week'] = flow_data['timestamp'].dt.dayofweek
        
        # Group by hour and count flows
        hourly_counts = flow_data.groupby('hour').size()
        
        # Group by day of week and count flows
        dow_counts = flow_data.groupby('day_of_week').size()
        
        # Identify peak hours
        peak_hour = hourly_counts.idxmax()
        peak_hour_count = hourly_counts.max()
        
        # Identify peak days
        peak_day = dow_counts.idxmax()
        peak_day_count = dow_counts.max()
        
        # Map day numbers to names
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return {
            'peak_hour': int(peak_hour),
            'peak_hour_count': int(peak_hour_count),
            'peak_day': day_names[peak_day],
            'peak_day_count': int(peak_day_count),
            'hourly_distribution': hourly_counts.to_dict(),
            'daily_distribution': {day_names[i]: int(count) for i, count in dow_counts.items()}
        }
    
    def _analyze_protocol_distribution(self, flow_data):
        """
        Analyze protocol distribution in flow data
        
        Args:
            flow_data (DataFrame): Flow data with protocol column
        
        Returns:
            dict: Protocol distribution analysis
        """
        # Count flows by protocol
        proto_counts = flow_data.groupby('protocol').size()
        
        # Calculate protocol bytes
        proto_bytes = flow_data.groupby('protocol')['bytes'].sum()
        
        # Map common protocol numbers to names
        protocol_names = {
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
        
        # Format the result
        protocol_distribution = {}
        for proto, count in proto_counts.items():
            protocol_distribution[str(proto)] = {
                'name': protocol_names.get(proto, f"Protocol {proto}"),
                'count': int(count),
                'bytes': int(proto_bytes.get(proto, 0)),
                'percentage': float(count / len(flow_data) * 100)
            }
        
        return protocol_distribution
    
    def _analyze_communication_patterns(self, flow_data):
        """
        Analyze communication patterns between hosts
        
        Args:
            flow_data (DataFrame): Flow data with src_ip and dst_ip columns
        
        Returns:
            dict: Communication pattern analysis
        """
        # Count flows by source IP
        src_counts = flow_data.groupby('src_ip').size().sort_values(ascending=False)
        
        # Count flows by destination IP
        dst_counts = flow_data.groupby('dst_ip').size().sort_values(ascending=False)
        
        # Find top talkers (source IPs)
        top_talkers = [{'ip': ip, 'flow_count': int(count)} 
                     for ip, count in src_counts.head(10).items()]
        
        # Find top receivers (destination IPs)
        top_receivers = [{'ip': ip, 'flow_count': int(count)} 
                       for ip, count in dst_counts.head(10).items()]
        
        # Count unique communication pairs
        flow_data['ip_pair'] = flow_data.apply(lambda row: f"{row['src_ip']}-{row['dst_ip']}", axis=1)
        pair_counts = flow_data.groupby('ip_pair').size().sort_values(ascending=False)
        
        # Find top communication pairs
        top_pairs = []
        for pair, count in pair_counts.head(10).items():
            src, dst = pair.split('-')
            top_pairs.append({
                'src_ip': src,
                'dst_ip': dst,
                'flow_count': int(count)
            })
        
        return {
            'top_talkers': top_talkers,
            'top_receivers': top_receivers,
            'top_communication_pairs': top_pairs,
            'unique_sources': len(src_counts),
            'unique_destinations': len(dst_counts),
            'unique_pairs': len(pair_counts)
        }
    
    def _analyze_flow_sizes(self, flow_data):
        """
        Analyze flow size patterns
        
        Args:
            flow_data (DataFrame): Flow data with bytes and packets columns
        
        Returns:
            dict: Flow size analysis
        """
        # Basic statistics for bytes
        bytes_mean = flow_data['bytes'].mean()
        bytes_median = flow_data['bytes'].median()
        bytes_std = flow_data['bytes'].std()
        bytes_max = flow_data['bytes'].max()
        
        # Basic statistics for packets
        packets_mean = flow_data['packets'].mean()
        packets_median = flow_data['packets'].median()
        packets_std = flow_data['packets'].std()
        packets_max = flow_data['packets'].max()
        
        # Calculate bytes per packet
        flow_data['bytes_per_packet'] = flow_data['bytes'] / flow_data['packets'].replace(0, 1)
        bpp_mean = flow_data['bytes_per_packet'].mean()
        
        # Create clusters of flow sizes
        if len(flow_data) >= 5:
            try:
                # Use 3 clusters for small, medium, and large flows
                kmeans = KMeans(n_clusters=3, random_state=42)
                flow_data['size_cluster'] = kmeans.fit_predict(flow_data[['bytes']])
                
                # Get cluster centers (average size for each cluster)
                cluster_centers = kmeans.cluster_centers_
                
                # Sort clusters by center value (smallest to largest)
                sorted_clusters = sorted(range(len(cluster_centers)), key=lambda k: cluster_centers[k][0])
                
                # Count flows in each cluster
                cluster_counts = flow_data.groupby('size_cluster').size()
                
                # Map sorted clusters to size categories
                size_distribution = {
                    'small': int(cluster_counts.get(sorted_clusters[0], 0)),
                    'medium': int(cluster_counts.get(sorted_clusters[1], 0)),
                    'large': int(cluster_counts.get(sorted_clusters[2], 0))
                }
            except Exception as e:
                logger.error(f"Error clustering flow sizes: {str(e)}")
                size_distribution = {}
        else:
            size_distribution = {}
        
        return {
            'bytes_mean': float(bytes_mean),
            'bytes_median': float(bytes_median),
            'bytes_std': float(bytes_std),
            'bytes_max': float(bytes_max),
            'packets_mean': float(packets_mean),
            'packets_median': float(packets_median),
            'packets_std': float(packets_std),
            'packets_max': float(packets_max),
            'bytes_per_packet_mean': float(bpp_mean),
            'size_distribution': size_distribution
        }


class NetworkBehaviorClassifier:
    """
    Classifies network behavior based on flow patterns
    """
    
    def __init__(self):
        """Initialize the network behavior classifier"""
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )
        self.behaviors = [
            'normal_traffic',
            'p2p_traffic',
            'scan_activity',
            'data_transfer',
            'interactive_session',
            'streaming',
            'bulk_transfer'
        ]
        self.trained = False
    
    def train(self, flow_data, labels=None):
        """
        Train the classifier with labeled data
        
        Args:
            flow_data (DataFrame): Pandas DataFrame with flow data
            labels (array): Optional behavior labels (if not provided, synthetic labels are created)
        
        Returns:
            bool: Success/failure
        """
        try:
            if len(flow_data) < 20:
                logger.info("Not enough data for behavior classification training")
                return False
            
            # Extract features for classification
            features = self._extract_features(flow_data)
            
            # If labels are not provided, create synthetic ones based on heuristics
            if labels is None:
                labels = self._create_heuristic_labels(flow_data)
            
            # Train the classifier
            self.classifier.fit(features, labels)
            self.trained = True
            
            return True
            
        except Exception as e:
            logger.error(f"Error training network behavior classifier: {str(e)}")
            return False
    
    def classify(self, flow_data):
        """
        Classify network behavior
        
        Args:
            flow_data (DataFrame): Pandas DataFrame with flow data
        
        Returns:
            dict: Classification results
        """
        try:
            if not self.trained:
                # Train on the provided data first
                self.train(flow_data)
            
            if len(flow_data) < 5:
                logger.info("Not enough data for behavior classification")
                return {}
            
            # Extract features for classification
            features = self._extract_features(flow_data)
            
            # Predict behaviors
            predictions = self.classifier.predict(features)
            
            # Summarize results
            behavior_counts = {}
            for behavior in self.behaviors:
                behavior_counts[behavior] = int(np.sum(predictions == behavior))
            
            # Determine dominant behavior
            if len(behavior_counts) > 0:
                dominant_behavior = max(behavior_counts.items(), key=lambda x: x[1])[0]
            else:
                dominant_behavior = 'unknown'
            
            return {
                'dominant_behavior': dominant_behavior,
                'behavior_distribution': behavior_counts,
                'confidence': float(np.max(self.classifier.predict_proba(features), axis=1).mean() if len(features) > 0 else 0)
            }
            
        except Exception as e:
            logger.error(f"Error classifying network behavior: {str(e)}")
            return {}
    
    def _extract_features(self, flow_data):
        """
        Extract features for behavior classification
        
        Args:
            flow_data (DataFrame): Flow data
        
        Returns:
            DataFrame: Extracted features
        """
        features = pd.DataFrame()
        
        # Basic numeric features
        for col in ['bytes', 'packets']:
            if col in flow_data.columns:
                features[col] = flow_data[col]
        
        # Bytes per packet ratio
        features['bytes_per_packet'] = flow_data['bytes'] / flow_data['packets'].replace(0, 1)
        
        # Protocol as one-hot encoding
        if 'protocol' in flow_data.columns:
            # Common protocols to one-hot encode
            common_protocols = [1, 6, 17]  # ICMP, TCP, UDP
            for proto in common_protocols:
                features[f'proto_{proto}'] = (flow_data['protocol'] == proto).astype(int)
        
        # Port features
        for port_col in ['src_port', 'dst_port']:
            if port_col in flow_data.columns:
                # Check for common port ranges
                features[f'{port_col}_well_known'] = (flow_data[port_col] < 1024).astype(int)
                features[f'{port_col}_high'] = (flow_data[port_col] > 49152).astype(int)
        
        # Temporal features
        if 'timestamp' in flow_data.columns:
            flow_data['hour'] = flow_data['timestamp'].dt.hour
            features['business_hours'] = ((flow_data['hour'] >= 8) & (flow_data['hour'] <= 18)).astype(int)
            
            # Day of week (weekday vs weekend)
            flow_data['day_of_week'] = flow_data['timestamp'].dt.dayofweek
            features['weekend'] = (flow_data['day_of_week'] >= 5).astype(int)
        
        return features
    
    def _create_heuristic_labels(self, flow_data):
        """
        Create heuristic labels for training
        
        Args:
            flow_data (DataFrame): Flow data
        
        Returns:
            array: Behavior labels
        """
        labels = []
        
        for _, flow in flow_data.iterrows():
            bytes_value = flow.get('bytes', 0)
            packets = flow.get('packets', 0)
            protocol = flow.get('protocol', 0)
            src_port = flow.get('src_port', 0)
            dst_port = flow.get('dst_port', 0)
            
            # Calculate bytes per packet
            bpp = bytes_value / max(packets, 1)
            
            # Apply heuristics to classify behavior
            if bytes_value > 1000000:  # Large data transfer
                if bpp > 1000:
                    behavior = 'bulk_transfer'
                else:
                    behavior = 'data_transfer'
            elif protocol == 6:  # TCP
                if dst_port in [80, 443, 8080]:  # Web traffic
                    if bytes_value > 100000:
                        behavior = 'streaming'
                    else:
                        behavior = 'normal_traffic'
                elif dst_port in [22, 23, 3389]:  # SSH, Telnet, RDP
                    behavior = 'interactive_session'
                else:
                    behavior = 'normal_traffic'
            elif protocol == 17:  # UDP
                if dst_port > 1024 and src_port > 1024:  # High ports on both sides
                    behavior = 'p2p_traffic'
                else:
                    behavior = 'normal_traffic'
            elif protocol == 1:  # ICMP
                if packets > 10:
                    behavior = 'scan_activity'
                else:
                    behavior = 'normal_traffic'
            else:
                behavior = 'normal_traffic'
            
            labels.append(behavior)
        
        return np.array(labels)


class AIInsightsManager:
    """
    Manages AI insights for flow data analysis
    """
    
    def __init__(self):
        """Initialize the AI insights manager"""
        self.anomaly_detector = FlowAnomalyDetector()
        self.pattern_analyzer = TrafficPatternAnalyzer()
        self.behavior_classifier = NetworkBehaviorClassifier()
    
    def analyze_device_data(self, device_id, time_window=None):
        """
        Analyze flow data for a specific device
        
        Args:
            device_id (int): Device ID
            time_window (dict): Optional time window with 'start' and 'end' datetime
        
        Returns:
            dict: Analysis results
        """
        from models import FlowData, Device
        
        try:
            # Get device
            device = Device.query.get(device_id)
            if not device:
                return {'error': f'Device not found: {device_id}'}
            
            # Retrieve flow data for this device
            query = FlowData.query.filter_by(device_id=device_id)
            
            # Apply time window if provided
            if time_window:
                if 'start' in time_window:
                    query = query.filter(FlowData.timestamp >= time_window['start'])
                if 'end' in time_window:
                    query = query.filter(FlowData.timestamp <= time_window['end'])
            
            # Default to last 24 hours if no time window specified
            else:
                query = query.filter(
                    FlowData.timestamp >= datetime.utcnow() - timedelta(days=1)
                )
            
            # Get the flow data
            flow_records = query.all()
            
            if len(flow_records) < 10:
                return {'error': 'Not enough flow data for analysis (minimum 10 flows required)'}
            
            # Convert to pandas DataFrame for analysis
            flows_df = pd.DataFrame([
                {
                    'id': flow.id,
                    'src_ip': flow.src_ip,
                    'dst_ip': flow.dst_ip,
                    'src_port': flow.src_port,
                    'dst_port': flow.dst_port,
                    'protocol': flow.protocol,
                    'bytes': flow.bytes,
                    'packets': flow.packets,
                    'timestamp': flow.timestamp
                }
                for flow in flow_records
            ])
            
            # Run the analysis
            analysis_results = {
                'device_id': device_id,
                'device_name': device.name,
                'device_ip': device.ip_address,
                'flow_count': len(flows_df),
                'time_window': {
                    'start': flows_df['timestamp'].min().isoformat() if 'timestamp' in flows_df.columns else None,
                    'end': flows_df['timestamp'].max().isoformat() if 'timestamp' in flows_df.columns else None,
                },
                'anomalies': self.anomaly_detector.detect(flows_df),
                'traffic_patterns': self.pattern_analyzer.analyze(flows_df),
                'behavior_classification': self.behavior_classifier.classify(flows_df)
            }
            
            # Store the analysis results
            self._store_analysis_results(device_id, analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing device data: {str(e)}")
            return {'error': str(e)}
    
    def get_recent_anomalies(self, limit=10):
        """
        Get recent anomaly detections across all devices
        
        Args:
            limit (int): Maximum number of results to return
        
        Returns:
            list: Recent anomaly detection results
        """
        from models import AnalysisResult
        
        try:
            # Query recent anomaly analysis results
            anomaly_results = AnalysisResult.query.filter_by(
                analysis_type='anomaly'
            ).order_by(
                AnalysisResult.timestamp.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': result.id,
                    'device_id': result.device_id,
                    'device_name': result.device.name if result.device else 'Unknown',
                    'timestamp': result.timestamp.isoformat(),
                    'confidence': result.confidence,
                    'anomalies': json.loads(result.result_data)
                }
                for result in anomaly_results
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving recent anomalies: {str(e)}")
            return []
    
    def _store_analysis_results(self, device_id, analysis_results):
        """
        Store analysis results in the database
        
        Args:
            device_id (int): Device ID
            analysis_results (dict): Analysis results
        """
        from models import AnalysisResult
        
        try:
            # Store anomaly detection results
            if 'anomalies' in analysis_results and analysis_results['anomalies']:
                anomaly_result = AnalysisResult(
                    device_id=device_id,
                    analysis_type='anomaly',
                    result_data=json.dumps(analysis_results['anomalies']),
                    confidence=0.95 if analysis_results['anomalies'] else 0.5,
                    timestamp=datetime.utcnow()
                )
                db.session.add(anomaly_result)
            
            # Store traffic pattern analysis
            if 'traffic_patterns' in analysis_results and analysis_results['traffic_patterns']:
                pattern_result = AnalysisResult(
                    device_id=device_id,
                    analysis_type='traffic_pattern',
                    result_data=json.dumps(analysis_results['traffic_patterns']),
                    confidence=0.9,
                    timestamp=datetime.utcnow()
                )
                db.session.add(pattern_result)
            
            # Store behavior classification
            if 'behavior_classification' in analysis_results and analysis_results['behavior_classification']:
                behavior_result = AnalysisResult(
                    device_id=device_id,
                    analysis_type='behavior',
                    result_data=json.dumps(analysis_results['behavior_classification']),
                    confidence=analysis_results['behavior_classification'].get('confidence', 0.8),
                    timestamp=datetime.utcnow()
                )
                db.session.add(behavior_result)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing analysis results: {str(e)}")


# Singleton instance
ai_insights_manager = None

def get_ai_insights_manager():
    """Get the global AI insights manager instance"""
    global ai_insights_manager
    if ai_insights_manager is None:
        ai_insights_manager = AIInsightsManager()
    return ai_insights_manager
