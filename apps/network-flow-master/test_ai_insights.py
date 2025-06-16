"""
Unit tests for AI insights functionality
"""
import unittest
from unittest.mock import patch, MagicMock
import datetime
import pandas as pd
import numpy as np
from ai_insights import FlowAnomalyDetector, TrafficPatternAnalyzer, NetworkBehaviorClassifier, AIInsightsManager

class TestFlowAnomalyDetector(unittest.TestCase):
    """Test the flow anomaly detector"""

    def setUp(self):
        """Set up test environment"""
        self.detector = FlowAnomalyDetector()
        
        # Create sample flow data DataFrame
        self.sample_flows = pd.DataFrame({
            'src_ip': ['192.168.1.1', '192.168.1.2', '192.168.1.1', '10.0.0.1', '10.0.0.2'],
            'dst_ip': ['8.8.8.8', '8.8.4.4', '1.1.1.1', '192.168.1.10', '10.0.0.254'],
            'src_port': [12345, 54321, 23456, 3389, 22],
            'dst_port': [53, 80, 443, 5000, 22],
            'protocol': [17, 6, 6, 6, 6],  # UDP, TCP
            'bytes': [500, 1500, 2500, 1000000, 3000],
            'packets': [5, 10, 15, 1000, 30],
            'timestamp': [
                datetime.datetime.utcnow() - datetime.timedelta(minutes=5),
                datetime.datetime.utcnow() - datetime.timedelta(minutes=4),
                datetime.datetime.utcnow() - datetime.timedelta(minutes=3),
                datetime.datetime.utcnow() - datetime.timedelta(minutes=2),
                datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
            ],
            'flow_type': ['netflow5', 'netflow5', 'netflow5', 'netflow5', 'netflow5'],
            'tos': [0, 0, 0, 0, 0],
            'tcp_flags': [0, 16, 16, 24, 0],  # 0, ACK, ACK, ACK+PSH
            'duration': [1.5, 2.0, 1.0, 30.0, 2.5]
        })
        
        # Add an anomalous flow (very large)
        self.anomalous_flow = pd.DataFrame({
            'src_ip': ['192.168.1.1'],
            'dst_ip': ['8.8.8.8'],
            'src_port': [12345],
            'dst_port': [53],
            'protocol': [17],  # UDP
            'bytes': [100000000],  # 100MB - very large
            'packets': [100000],
            'timestamp': [datetime.datetime.utcnow()],
            'flow_type': ['netflow5'],
            'tos': [0],
            'tcp_flags': [0],
            'duration': [1.5]
        })

    def test_detect_normal(self):
        """Test anomaly detection with normal flows"""
        # Mock the preprocessing and model
        with patch.object(self.detector, '_preprocess_flows', return_value=(self.sample_flows, None, None)):
            with patch.object(self.detector, '_model', MagicMock()) as mock_model:
                # Make the model return all -1 (normal) predictions
                mock_model.predict.return_value = np.array([-1, -1, -1, -1, -1])
                
                # Run detection
                anomalies = self.detector.detect(self.sample_flows)
                
                # Should be empty since all flows are normal
                self.assertEqual(len(anomalies), 0)
                
                # Verify model was called
                mock_model.predict.assert_called_once()

    def test_detect_anomalies(self):
        """Test anomaly detection with anomalous flows"""
        # Mock the preprocessing and model
        with patch.object(self.detector, '_preprocess_flows', return_value=(self.sample_flows, None, None)):
            with patch.object(self.detector, '_model', MagicMock()) as mock_model:
                # Make the model return some 1 (anomaly) predictions
                mock_model.predict.return_value = np.array([-1, -1, 1, -1, 1])
                
                # Run detection
                anomalies = self.detector.detect(self.sample_flows)
                
                # Should have 2 anomalies
                self.assertEqual(len(anomalies), 2)
                
                # Check the anomaly details
                self.assertEqual(anomalies[0]['src_ip'], '192.168.1.1')
                self.assertEqual(anomalies[0]['dst_ip'], '1.1.1.1')
                self.assertEqual(anomalies[1]['src_ip'], '10.0.0.2')
                self.assertEqual(anomalies[1]['dst_ip'], '10.0.0.254')
                
                # Verify model was called
                mock_model.predict.assert_called_once()

    def test_get_anomaly_reason(self):
        """Test getting the anomaly reason"""
        # Create sample flow, features, and scaled features
        flow = self.sample_flows.iloc[3]  # The large RDP flow
        
        # Features with packet_size and bytes_per_packet
        features = pd.Series({
            'bytes': 1000000,
            'packets': 1000,
            'duration': 30.0,
            'packet_size': 1000,  # bytes / packets
            'bytes_per_second': 33333.33  # bytes / duration
        })
        
        # Scaled features (after normalization)
        scaled_features = np.array([3.5, 2.8, 1.5, 4.0, 3.8])  # High z-scores
        
        # Get the reason
        reason = self.detector._get_anomaly_reason(flow, features, scaled_features)
        
        # Should mention high data volume
        self.assertIn('data volume', reason.lower())
        
        # Now try with a different flow (port scan)
        flow = pd.Series({
            'src_ip': '192.168.1.1',
            'dst_ip': '192.168.1.10',
            'src_port': 12345,
            'dst_port': 22,
            'protocol': 6,
            'bytes': 100,
            'packets': 100,
            'timestamp': datetime.datetime.utcnow(),
            'duration': 0.1
        })
        
        features = pd.Series({
            'bytes': 100,
            'packets': 100,
            'duration': 0.1,
            'packet_size': 1,  # tiny packets
            'bytes_per_second': 1000  # normal rate
        })
        
        scaled_features = np.array([0.1, 2.8, -1.5, -3.0, 0.3])  # Unusual packet size
        
        # Get the reason
        reason = self.detector._get_anomaly_reason(flow, features, scaled_features)
        
        # Should mention unusual packet size
        self.assertIn('packet size', reason.lower())

class TestTrafficPatternAnalyzer(unittest.TestCase):
    """Test the traffic pattern analyzer"""

    def setUp(self):
        """Set up test environment"""
        self.analyzer = TrafficPatternAnalyzer()
        
        # Create sample flow data DataFrame spanning several days
        base_time = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        self.sample_flows = pd.DataFrame({
            'src_ip': ['192.168.1.1', '192.168.1.2', '192.168.1.1', '10.0.0.1', '10.0.0.2'] * 20,
            'dst_ip': ['8.8.8.8', '8.8.4.4', '1.1.1.1', '192.168.1.10', '10.0.0.254'] * 20,
            'src_port': [12345, 54321, 23456, 3389, 22] * 20,
            'dst_port': [53, 80, 443, 5000, 22] * 20,
            'protocol': [17, 6, 6, 6, 6] * 20,  # UDP, TCP
            'bytes': [500, 1500, 2500, 10000, 3000] * 20,
            'packets': [5, 10, 15, 100, 30] * 20,
            'timestamp': [
                base_time + datetime.timedelta(hours=i) 
                for i in range(100)
            ],
            'flow_type': ['netflow5'] * 100,
            'tos': [0] * 100,
            'tcp_flags': [0, 16, 16, 24, 0] * 20,  # 0, ACK, ACK, ACK+PSH
            'duration': [1.5, 2.0, 1.0, 5.0, 2.5] * 20
        })

    def test_analyze_time_patterns(self):
        """Test time pattern analysis"""
        # Analyze time patterns
        patterns = self.analyzer._analyze_time_patterns(self.sample_flows)
        
        # Check the result structure
        self.assertIn('hourly_distribution', patterns)
        self.assertIn('daily_distribution', patterns)
        self.assertIn('busiest_hour', patterns)
        self.assertIn('quietest_hour', patterns)
        
        # Hourly distribution should have 24 entries
        self.assertEqual(len(patterns['hourly_distribution']), 24)
        
        # Daily distribution should have 7 entries
        self.assertEqual(len(patterns['daily_distribution']), 7)

    def test_analyze_protocol_distribution(self):
        """Test protocol distribution analysis"""
        # Analyze protocol distribution
        distribution = self.analyzer._analyze_protocol_distribution(self.sample_flows)
        
        # Check the result structure
        self.assertIn('protocol_counts', distribution)
        self.assertIn('top_protocols', distribution)
        
        # Protocol counts should include TCP (6) and UDP (17)
        self.assertIn('6', distribution['protocol_counts'])
        self.assertIn('17', distribution['protocol_counts'])
        
        # Top protocols should have entries
        self.assertGreater(len(distribution['top_protocols']), 0)

    def test_analyze_communication_patterns(self):
        """Test communication pattern analysis"""
        # Analyze communication patterns
        patterns = self.analyzer._analyze_communication_patterns(self.sample_flows)
        
        # Check the result structure
        self.assertIn('top_talkers', patterns)
        self.assertIn('top_destinations', patterns)
        self.assertIn('internal_external_ratio', patterns)
        
        # Top talkers and destinations should have entries
        self.assertGreater(len(patterns['top_talkers']), 0)
        self.assertGreater(len(patterns['top_destinations']), 0)
        
        # Internal/external ratio should be between 0 and 1
        self.assertGreaterEqual(patterns['internal_external_ratio'], 0)
        self.assertLessEqual(patterns['internal_external_ratio'], 1)

    def test_analyze(self):
        """Test the main analyze method"""
        # Analyze the flow data
        results = self.analyzer.analyze(self.sample_flows)
        
        # Check the result structure
        self.assertIn('time_patterns', results)
        self.assertIn('protocol_distribution', results)
        self.assertIn('communication_patterns', results)
        self.assertIn('flow_size_patterns', results)
        
        # All components should be present
        self.assertIn('hourly_distribution', results['time_patterns'])
        self.assertIn('protocol_counts', results['protocol_distribution'])
        self.assertIn('top_talkers', results['communication_patterns'])
        self.assertIn('avg_flow_size', results['flow_size_patterns'])

class TestNetworkBehaviorClassifier(unittest.TestCase):
    """Test the network behavior classifier"""

    def setUp(self):
        """Set up test environment"""
        self.classifier = NetworkBehaviorClassifier()
        
        # Create sample flow data DataFrame
        self.sample_flows = pd.DataFrame({
            'src_ip': ['192.168.1.1', '192.168.1.2', '192.168.1.1', '10.0.0.1', '10.0.0.2'] * 5,
            'dst_ip': ['8.8.8.8', '8.8.4.4', '1.1.1.1', '192.168.1.10', '10.0.0.254'] * 5,
            'src_port': [12345, 54321, 23456, 3389, 22] * 5,
            'dst_port': [53, 80, 443, 5000, 22] * 5,
            'protocol': [17, 6, 6, 6, 6] * 5,  # UDP, TCP
            'bytes': [500, 1500, 2500, 10000, 3000] * 5,
            'packets': [5, 10, 15, 100, 30] * 5,
            'timestamp': [datetime.datetime.utcnow()] * 25,
            'flow_type': ['netflow5'] * 25,
            'tos': [0] * 25,
            'tcp_flags': [0, 16, 16, 24, 0] * 5,  # 0, ACK, ACK, ACK+PSH
            'duration': [1.5, 2.0, 1.0, 5.0, 2.5] * 5
        })

    @patch('ai_insights.KMeans')
    def test_train(self, mock_kmeans):
        """Test training the classifier"""
        # Mock the KMeans model
        mock_model = MagicMock()
        mock_kmeans.return_value = mock_model
        
        # Train the classifier
        result = self.classifier.train(self.sample_flows)
        
        # Should be successful
        self.assertTrue(result)
        
        # Verify model was trained
        mock_model.fit.assert_called_once()
        
        # Verify model is saved
        self.assertEqual(self.classifier._model, mock_model)

    @patch('ai_insights.KMeans')
    def test_classify(self, mock_kmeans):
        """Test classifying network behavior"""
        # Mock the KMeans model
        mock_model = MagicMock()
        mock_kmeans.return_value = mock_model
        
        # Set up the model to return cluster labels
        mock_model.predict.return_value = np.array([0, 1, 0, 2, 1] * 5)
        mock_model.cluster_centers_ = np.array([
            [1, 2, 3],  # Cluster 0 - normal web browsing
            [4, 5, 6],  # Cluster 1 - file transfer
            [7, 8, 9]   # Cluster 2 - remote access
        ])
        
        # Set the model
        self.classifier._model = mock_model
        
        # Mock feature extraction
        with patch.object(self.classifier, '_extract_features') as mock_extract:
            # Return dummy features
            mock_extract.return_value = pd.DataFrame({
                'feature1': [1, 2, 3, 4, 5] * 5,
                'feature2': [5, 4, 3, 2, 1] * 5,
                'feature3': [1, 1, 1, 1, 1] * 5
            })
            
            # Classify the flows
            result = self.classifier.classify(self.sample_flows)
            
            # Check result structure
            self.assertIn('classes', result)
            self.assertIn('class_distribution', result)
            self.assertIn('class_details', result)
            
            # Should have classified all flows
            self.assertEqual(len(result['classes']), 25)
            
            # Should have 3 distinct classes
            self.assertEqual(len(result['class_distribution']), 3)
            
            # Verify model was called
            mock_model.predict.assert_called_once()

class TestAIInsightsManager(unittest.TestCase):
    """Test the AI insights manager"""

    def setUp(self):
        """Set up test environment"""
        self.manager = AIInsightsManager()

    @patch('ai_insights.FlowAnomalyDetector')
    @patch('ai_insights.TrafficPatternAnalyzer')
    @patch('ai_insights.NetworkBehaviorClassifier')
    @patch('ai_insights.pd.read_sql')
    @patch('ai_insights.db')
    def test_analyze_device_data(self, mock_db, mock_read_sql, mock_classifier, mock_analyzer, mock_detector):
        """Test analyzing device data"""
        # Mock the SQL query result
        mock_flow_data = pd.DataFrame({
            'src_ip': ['192.168.1.1', '192.168.1.2'],
            'dst_ip': ['8.8.8.8', '8.8.4.4'],
            'src_port': [12345, 54321],
            'dst_port': [53, 80],
            'protocol': [17, 6],  # UDP, TCP
            'bytes': [500, 1500],
            'packets': [5, 10],
            'timestamp': [
                datetime.datetime.utcnow() - datetime.timedelta(minutes=5),
                datetime.datetime.utcnow() - datetime.timedelta(minutes=4)
            ],
            'flow_type': ['netflow5', 'netflow5'],
            'tos': [0, 0],
            'tcp_flags': [0, 16],  # 0, ACK
            'duration': [1.5, 2.0]
        })
        mock_read_sql.return_value = mock_flow_data
        
        # Mock the detector, analyzer, and classifier
        mock_detector_instance = mock_detector.return_value
        mock_analyzer_instance = mock_analyzer.return_value
        mock_classifier_instance = mock_classifier.return_value
        
        # Set up return values
        mock_detector_instance.detect.return_value = [
            {'src_ip': '192.168.1.1', 'dst_ip': '8.8.8.8', 'reason': 'Unusual data volume'}
        ]
        mock_analyzer_instance.analyze.return_value = {
            'time_patterns': {'hourly_distribution': {0: 5, 1: 10}},
            'protocol_distribution': {'protocol_counts': {'17': 1, '6': 1}},
            'communication_patterns': {'top_talkers': {'192.168.1.1': 1}},
            'flow_size_patterns': {'avg_flow_size': 1000}
        }
        mock_classifier_instance.classify.return_value = {
            'classes': [0, 1],
            'class_distribution': {0: 1, 1: 1},
            'class_details': {
                0: 'Web browsing',
                1: 'DNS traffic'
            }
        }
        
        # Call analyze_device_data
        result = self.manager.analyze_device_data(1)
        
        # Check the result structure
        self.assertIn('anomalies', result)
        self.assertIn('patterns', result)
        self.assertIn('behavior', result)
        
        # Verify detectors and analyzers were called
        mock_detector_instance.detect.assert_called_once_with(mock_flow_data)
        mock_analyzer_instance.analyze.assert_called_once_with(mock_flow_data)
        mock_classifier_instance.classify.assert_called_once_with(mock_flow_data)
        
        # Verify DB operations
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()

if __name__ == '__main__':
    unittest.main()