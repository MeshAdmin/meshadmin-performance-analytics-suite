#!/usr/bin/env python3
"""
MeshAdmin Advanced Analytics Engine with Machine Learning

This module provides advanced analytics capabilities including:
- Predictive performance modeling
- Anomaly detection algorithms
- Capacity planning recommendations
- Pattern recognition and learning
- Real-time intelligent insights

Features:
- Scikit-learn based ML models
- Time series forecasting
- Statistical anomaly detection
- Performance trend prediction
- Automated model training and updating
"""

import sys
import os
import time
import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)

# Machine Learning imports
try:
    from sklearn.ensemble import IsolationForest, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LinearRegression
    from sklearn.cluster import DBSCAN
    import joblib
    ML_AVAILABLE = True
except ImportError:
    print("⚠️ ML dependencies not available. Install scikit-learn, pandas, numpy for full functionality.")
    ML_AVAILABLE = False

# Statistical analysis imports
try:
    from scipy import stats
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    print("⚠️ SciPy not available. Some statistical features will be limited.")
    SCIPY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ml-analytics")

# =============================================================================
# Data Classes and Enums
# =============================================================================

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ModelType(Enum):
    ANOMALY_DETECTION = "anomaly_detection"
    PERFORMANCE_PREDICTION = "performance_prediction"
    CAPACITY_PLANNING = "capacity_planning"
    PATTERN_RECOGNITION = "pattern_recognition"

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: float
    source: str  # 'network_flow_master' or 'load_balancer_pro'
    metric_name: str
    value: float
    metadata: Dict[str, Any] = None

@dataclass
class Anomaly:
    """Detected anomaly"""
    timestamp: float
    source: str
    metric_name: str
    value: float
    expected_value: float
    severity: AlertSeverity
    confidence: float
    description: str

@dataclass
class Prediction:
    """Performance prediction"""
    target_time: float
    metric_name: str
    predicted_value: float
    confidence_interval: Tuple[float, float]
    model_accuracy: float

@dataclass
class CapacityRecommendation:
    """Capacity planning recommendation"""
    component: str  # 'network_flow_master' or 'load_balancer_pro'
    metric: str
    current_utilization: float
    predicted_peak: float
    recommendation: str
    urgency: AlertSeverity
    estimated_time_to_limit: Optional[float] = None

# =============================================================================
# Advanced Analytics Engine
# =============================================================================

class MLAnalyticsEngine:
    """
    Advanced Machine Learning Analytics Engine for MeshAdmin
    
    Provides intelligent analysis of performance data with predictive capabilities,
    anomaly detection, and capacity planning recommendations.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.metrics_buffer: List[PerformanceMetric] = []
        self.anomalies: List[Anomaly] = []
        self.predictions: List[Prediction] = []
        self.recommendations: List[CapacityRecommendation] = []
        
        # Configuration parameters
        self.buffer_size = self.config.get('buffer_size', 1000)
        self.train_threshold = self.config.get('train_threshold', 100)
        self.anomaly_threshold = self.config.get('anomaly_threshold', -0.1)
        self.prediction_horizon = self.config.get('prediction_horizon', 3600)  # 1 hour
        self.model_update_interval = self.config.get('model_update_interval', 1800)  # 30 minutes
        
        # Model storage
        self.model_dir = self.config.get('model_dir', 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Initialize models if ML is available
        if ML_AVAILABLE:
            self._initialize_models()
        
        # Performance tracking
        self.last_model_update = 0
        self.model_performance = {}
        
        logger.info("🧠 ML Analytics Engine initialized")
    
    def _initialize_models(self) -> None:
        """Initialize machine learning models"""
        try:
            # Anomaly Detection Model
            self.models[ModelType.ANOMALY_DETECTION] = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            # Performance Prediction Models
            self.models[ModelType.PERFORMANCE_PREDICTION] = {
                'response_time': RandomForestRegressor(n_estimators=100, random_state=42),
                'packet_rate': RandomForestRegressor(n_estimators=100, random_state=42),
                'connection_count': RandomForestRegressor(n_estimators=100, random_state=42),
                'error_rate': LinearRegression()
            }
            
            # Capacity Planning Model
            self.models[ModelType.CAPACITY_PLANNING] = RandomForestRegressor(
                n_estimators=150, 
                random_state=42,
                max_depth=10
            )
            
            # Pattern Recognition Model (Clustering)
            self.models[ModelType.PATTERN_RECOGNITION] = DBSCAN(
                eps=0.3,
                min_samples=10
            )
            
            # Initialize scalers
            self.scalers['features'] = StandardScaler()
            self.scalers['targets'] = MinMaxScaler()
            
            logger.info("✅ ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {e}")
    
    def ingest_metrics(self, metrics: List[PerformanceMetric]) -> None:
        """Ingest new performance metrics for analysis"""
        try:
            # Add metrics to buffer
            self.metrics_buffer.extend(metrics)
            
            # Maintain buffer size
            if len(self.metrics_buffer) > self.buffer_size:
                self.metrics_buffer = self.metrics_buffer[-self.buffer_size:]
            
            # Check if we should update models
            current_time = time.time()
            if (current_time - self.last_model_update > self.model_update_interval and 
                len(self.metrics_buffer) >= self.train_threshold):
                self._update_models()
                self.last_model_update = current_time
            
            # Perform real-time analysis
            self._analyze_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error ingesting metrics: {e}")
    
    def _update_models(self) -> None:
        """Update machine learning models with latest data"""
        if not ML_AVAILABLE:
            return
        
        try:
            logger.info("🔄 Updating ML models with latest data...")
            
            # Prepare training data
            df = self._metrics_to_dataframe()
            if df.empty or len(df) < self.train_threshold:
                logger.warning("Insufficient data for model training")
                return
            
            # Update anomaly detection model
            self._train_anomaly_detection(df)
            
            # Update prediction models
            self._train_prediction_models(df)
            
            # Update capacity planning model
            self._train_capacity_model(df)
            
            # Save models
            self._save_models()
            
            logger.info("✅ ML models updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating models: {e}")
    
    def _metrics_to_dataframe(self) -> pd.DataFrame:
        """Convert metrics buffer to pandas DataFrame"""
        try:
            data = []
            for metric in self.metrics_buffer:
                data.append({
                    'timestamp': metric.timestamp,
                    'source': metric.source,
                    'metric_name': metric.metric_name,
                    'value': metric.value,
                    'hour': datetime.fromtimestamp(metric.timestamp).hour,
                    'day_of_week': datetime.fromtimestamp(metric.timestamp).weekday(),
                })
            
            df = pd.DataFrame(data)
            
            # Pivot to create feature matrix
            if not df.empty:
                pivot_df = df.pivot_table(
                    index='timestamp',
                    columns=['source', 'metric_name'],
                    values='value',
                    aggfunc='mean'
                ).fillna(method='ffill').fillna(0)
                
                # Add time-based features
                pivot_df['hour'] = pd.to_datetime(pivot_df.index, unit='s').hour
                pivot_df['day_of_week'] = pd.to_datetime(pivot_df.index, unit='s').dayofweek
                
                return pivot_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error creating DataFrame: {e}")
            return pd.DataFrame()
    
    def _train_anomaly_detection(self, df: pd.DataFrame) -> None:
        """Train anomaly detection model"""
        try:
            if df.empty:
                return
            
            # Prepare features (exclude time-based features for anomaly detection)
            feature_cols = [col for col in df.columns if not col in ['hour', 'day_of_week']]
            X = df[feature_cols].values
            
            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            
            if X.shape[0] < 10:  # Need minimum samples
                return
            
            # Scale features
            X_scaled = self.scalers['features'].fit_transform(X)
            
            # Train model
            self.models[ModelType.ANOMALY_DETECTION].fit(X_scaled)
            
            # Evaluate model performance
            scores = self.models[ModelType.ANOMALY_DETECTION].decision_function(X_scaled)
            anomaly_threshold = np.percentile(scores, 10)  # Bottom 10% as anomalies
            
            self.model_performance['anomaly_threshold'] = anomaly_threshold
            
            logger.info(f"✅ Anomaly detection model trained on {X.shape[0]} samples")
            
        except Exception as e:
            logger.error(f"Error training anomaly detection: {e}")
    
    def _train_prediction_models(self, df: pd.DataFrame) -> None:
        """Train performance prediction models"""
        try:
            if df.empty or len(df) < 20:
                return
            
            # Create time series features
            for lag in [1, 2, 3, 5]:
                for col in df.columns:
                    if col not in ['hour', 'day_of_week']:
                        df[f'{col}_lag_{lag}'] = df[col].shift(lag)
            
            df = df.dropna()
            
            if df.empty:
                return
            
            # Train models for each target metric
            target_metrics = ['response_time', 'packet_rate', 'connection_count', 'error_rate']
            
            for target in target_metrics:
                # Find columns that contain this target
                target_cols = [col for col in df.columns if target in str(col) and 'lag' not in str(col)]
                
                if not target_cols:
                    continue
                
                target_col = target_cols[0]  # Use first matching column
                
                # Prepare features and targets
                feature_cols = [col for col in df.columns if 'lag' in str(col) or col in ['hour', 'day_of_week']]
                X = df[feature_cols].values
                y = df[target_col].values
                
                # Handle missing values
                X = np.nan_to_num(X, nan=0.0)
                y = np.nan_to_num(y, nan=0.0)
                
                if len(X) < 10:
                    continue
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                
                # Train model
                model = self.models[ModelType.PERFORMANCE_PREDICTION][target]
                model.fit(X_train, y_train)
                
                # Evaluate performance
                if len(X_test) > 0:
                    y_pred = model.predict(X_test)
                    mse = mean_squared_error(y_test, y_pred)
                    mae = mean_absolute_error(y_test, y_pred)
                    
                    self.model_performance[f'{target}_mse'] = mse
                    self.model_performance[f'{target}_mae'] = mae
                
                logger.info(f"✅ Prediction model for {target} trained")
            
        except Exception as e:
            logger.error(f"Error training prediction models: {e}")
    
    def _train_capacity_model(self, df: pd.DataFrame) -> None:
        """Train capacity planning model"""
        try:
            if df.empty or len(df) < 20:
                return
            
            # Create capacity features
            capacity_features = []
            target_values = []
            
            # Calculate utilization rates and growth trends
            for i in range(10, len(df)):
                window = df.iloc[i-10:i]
                
                # Calculate trends and utilization
                features = []
                
                # Add mean values from recent window
                for col in df.columns:
                    if col not in ['hour', 'day_of_week']:
                        features.append(window[col].mean())
                        features.append(window[col].std())
                        
                        # Calculate growth rate
                        if len(window) > 1:
                            growth = (window[col].iloc[-1] - window[col].iloc[0]) / max(window[col].iloc[0], 1e-6)
                            features.append(growth)
                        else:
                            features.append(0)
                
                # Add time features
                features.extend([df.iloc[i]['hour'], df.iloc[i]['day_of_week']])
                
                capacity_features.append(features)
                
                # Target: maximum utilization in next period
                next_window = df.iloc[i:min(i+5, len(df))]
                max_util = 0
                for col in df.columns:
                    if col not in ['hour', 'day_of_week']:
                        max_util = max(max_util, next_window[col].max())
                
                target_values.append(max_util)
            
            if len(capacity_features) < 10:
                return
            
            X = np.array(capacity_features)
            y = np.array(target_values)
            
            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            y = np.nan_to_num(y, nan=0.0)
            
            # Train model
            self.models[ModelType.CAPACITY_PLANNING].fit(X, y)
            
            logger.info("✅ Capacity planning model trained")
            
        except Exception as e:
            logger.error(f"Error training capacity model: {e}")
    
    def _analyze_metrics(self, metrics: List[PerformanceMetric]) -> None:
        """Perform real-time analysis on new metrics"""
        try:
            # Detect anomalies
            self._detect_anomalies(metrics)
            
            # Generate predictions
            self._generate_predictions(metrics)
            
            # Update capacity recommendations
            self._update_capacity_recommendations()
            
        except Exception as e:
            logger.error(f"Error in real-time analysis: {e}")
    
    def _detect_anomalies(self, metrics: List[PerformanceMetric]) -> None:
        """Detect anomalies in new metrics"""
        if not ML_AVAILABLE or ModelType.ANOMALY_DETECTION not in self.models:
            return
        
        try:
            # Convert recent metrics to features
            recent_df = self._metrics_to_dataframe()
            if recent_df.empty or len(recent_df) < 5:
                return
            
            # Get latest data point
            latest_data = recent_df.iloc[-1:]
            feature_cols = [col for col in recent_df.columns if col not in ['hour', 'day_of_week']]
            X = latest_data[feature_cols].values
            
            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            
            if X.shape[1] == 0:
                return
            
            # Scale features
            X_scaled = self.scalers['features'].transform(X)
            
            # Detect anomalies
            scores = self.models[ModelType.ANOMALY_DETECTION].decision_function(X_scaled)
            predictions = self.models[ModelType.ANOMALY_DETECTION].predict(X_scaled)
            
            # Check if anomaly detected
            if predictions[0] == -1:  # Anomaly detected
                anomaly_threshold = self.model_performance.get('anomaly_threshold', -0.1)
                confidence = abs(scores[0] - anomaly_threshold) / abs(anomaly_threshold)
                
                # Determine severity based on confidence
                if confidence > 0.8:
                    severity = AlertSeverity.CRITICAL
                elif confidence > 0.6:
                    severity = AlertSeverity.HIGH
                elif confidence > 0.4:
                    severity = AlertSeverity.MEDIUM
                else:
                    severity = AlertSeverity.LOW
                
                # Create anomaly record
                for metric in metrics:
                    if abs(metric.timestamp - latest_data.index[0]) < 60:  # Within 1 minute
                        anomaly = Anomaly(
                            timestamp=metric.timestamp,
                            source=metric.source,
                            metric_name=metric.metric_name,
                            value=metric.value,
                            expected_value=self._get_expected_value(metric),
                            severity=severity,
                            confidence=min(confidence, 1.0),
                            description=f"Anomalous {metric.metric_name} detected in {metric.source}"
                        )
                        
                        self.anomalies.append(anomaly)
                        logger.warning(f"🚨 Anomaly detected: {anomaly.description} (confidence: {confidence:.2f})")
            
            # Clean old anomalies (keep last 100)
            if len(self.anomalies) > 100:
                self.anomalies = self.anomalies[-50:]
                
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
    
    def _generate_predictions(self, metrics: List[PerformanceMetric]) -> None:
        """Generate performance predictions"""
        if not ML_AVAILABLE or ModelType.PERFORMANCE_PREDICTION not in self.models:
            return
        
        try:
            # Convert metrics to DataFrame for prediction
            recent_df = self._metrics_to_dataframe()
            if recent_df.empty or len(recent_df) < 10:
                return
            
            # Generate predictions for each target metric
            target_metrics = ['response_time', 'packet_rate', 'connection_count', 'error_rate']
            
            for target in target_metrics:
                if target not in self.models[ModelType.PERFORMANCE_PREDICTION]:
                    continue
                
                model = self.models[ModelType.PERFORMANCE_PREDICTION][target]
                
                # Prepare features for prediction
                feature_cols = [col for col in recent_df.columns if 'lag' in str(col) or col in ['hour', 'day_of_week']]
                
                if not feature_cols:
                    continue
                
                # Get latest features
                latest_features = recent_df[feature_cols].iloc[-1:].values
                latest_features = np.nan_to_num(latest_features, nan=0.0)
                
                if latest_features.shape[1] == 0:
                    continue
                
                # Make prediction
                try:
                    predicted_value = model.predict(latest_features)[0]
                    
                    # Calculate confidence interval based on model performance
                    mse = self.model_performance.get(f'{target}_mse', 1.0)
                    confidence_range = np.sqrt(mse) * 1.96  # 95% confidence interval
                    
                    confidence_interval = (
                        predicted_value - confidence_range,
                        predicted_value + confidence_range
                    )
                    
                    # Model accuracy
                    accuracy = 1.0 / (1.0 + mse)
                    
                    # Create prediction
                    prediction = Prediction(
                        target_time=time.time() + self.prediction_horizon,
                        metric_name=target,
                        predicted_value=predicted_value,
                        confidence_interval=confidence_interval,
                        model_accuracy=min(accuracy, 1.0)
                    )
                    
                    self.predictions.append(prediction)
                    
                except Exception as e:
                    logger.error(f"Error making prediction for {target}: {e}")
            
            # Clean old predictions (keep last 50)
            if len(self.predictions) > 50:
                self.predictions = self.predictions[-25:]
                
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
    
    def _update_capacity_recommendations(self) -> None:
        """Update capacity planning recommendations"""
        try:
            # Analyze recent metrics for capacity trends
            recent_df = self._metrics_to_dataframe()
            if recent_df.empty or len(recent_df) < 20:
                return
            
            current_time = time.time()
            
            # Analyze each component
            components = ['network_flow_master', 'load_balancer_pro']
            
            for component in components:
                component_cols = [col for col in recent_df.columns if component in str(col)]
                
                if not component_cols:
                    continue
                
                for col in component_cols:
                    if 'lag' in str(col) or col in ['hour', 'day_of_week']:
                        continue
                    
                    # Calculate utilization trend
                    recent_values = recent_df[col].tail(10)
                    if len(recent_values) < 5:
                        continue
                    
                    current_value = recent_values.iloc[-1]
                    trend_slope = self._calculate_trend_slope(recent_values)
                    
                    # Estimate capacity limits (simple heuristic)
                    max_observed = recent_df[col].max()
                    capacity_limit = max_observed * 1.5  # Assume 50% headroom
                    
                    current_utilization = current_value / capacity_limit if capacity_limit > 0 else 0
                    
                    # Predict when limit will be reached
                    time_to_limit = None
                    if trend_slope > 0:
                        remaining_capacity = capacity_limit - current_value
                        time_to_limit = remaining_capacity / trend_slope if trend_slope > 0 else None
                    
                    # Generate recommendation based on utilization and trend
                    recommendation, urgency = self._generate_capacity_recommendation(
                        current_utilization, trend_slope, time_to_limit
                    )
                    
                    if recommendation:
                        capacity_rec = CapacityRecommendation(
                            component=component,
                            metric=col,
                            current_utilization=current_utilization,
                            predicted_peak=current_value + (trend_slope * self.prediction_horizon),
                            recommendation=recommendation,
                            urgency=urgency,
                            estimated_time_to_limit=time_to_limit
                        )
                        
                        self.recommendations.append(capacity_rec)
            
            # Clean old recommendations (keep last 20)
            if len(self.recommendations) > 20:
                self.recommendations = self.recommendations[-10:]
                
        except Exception as e:
            logger.error(f"Error updating capacity recommendations: {e}")
    
    def _calculate_trend_slope(self, values: pd.Series) -> float:
        """Calculate trend slope using linear regression"""
        try:
            if len(values) < 2:
                return 0.0
            
            x = np.arange(len(values))
            y = values.values
            
            # Handle missing values
            mask = ~np.isnan(y)
            if np.sum(mask) < 2:
                return 0.0
            
            x_clean = x[mask]
            y_clean = y[mask]
            
            # Calculate slope
            slope, _, _, _, _ = stats.linregress(x_clean, y_clean)
            return slope
            
        except Exception:
            return 0.0
    
    def _generate_capacity_recommendation(self, utilization: float, trend: float, time_to_limit: Optional[float]) -> Tuple[Optional[str], AlertSeverity]:
        """Generate capacity recommendation based on metrics"""
        try:
            # High utilization
            if utilization > 0.9:
                return ("CRITICAL: Immediate capacity expansion required", AlertSeverity.CRITICAL)
            elif utilization > 0.8:
                return ("HIGH: Plan capacity expansion within 24 hours", AlertSeverity.HIGH)
            elif utilization > 0.7:
                return ("MEDIUM: Monitor closely, plan expansion", AlertSeverity.MEDIUM)
            
            # Growing trend
            if trend > 0:
                if time_to_limit and time_to_limit < 3600:  # Less than 1 hour
                    return ("CRITICAL: Capacity limit will be reached within 1 hour", AlertSeverity.CRITICAL)
                elif time_to_limit and time_to_limit < 86400:  # Less than 1 day
                    return ("HIGH: Capacity limit approaching within 24 hours", AlertSeverity.HIGH)
                elif utilization > 0.5 and trend > 0.1:
                    return ("MEDIUM: Monitor growth trend", AlertSeverity.MEDIUM)
            
            # No immediate action needed
            if utilization < 0.3 and trend <= 0:
                return ("LOW: Capacity is adequate", AlertSeverity.LOW)
            
            return (None, AlertSeverity.LOW)
            
        except Exception:
            return (None, AlertSeverity.LOW)
    
    def _get_expected_value(self, metric: PerformanceMetric) -> float:
        """Get expected value for a metric (simple moving average)"""
        try:
            # Find similar metrics in buffer
            similar_metrics = [
                m for m in self.metrics_buffer 
                if (m.source == metric.source and 
                    m.metric_name == metric.metric_name and 
                    abs(m.timestamp - metric.timestamp) < 3600)
            ]
            
            if len(similar_metrics) > 1:
                values = [m.value for m in similar_metrics[:-1]]  # Exclude current metric
                return np.mean(values)
            
            return metric.value
            
        except Exception:
            return metric.value
    
    def _save_models(self) -> None:
        """Save trained models to disk"""
        try:
            if not ML_AVAILABLE:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save each model
            for model_type, model in self.models.items():
                if model_type == ModelType.PERFORMANCE_PREDICTION:
                    # Save prediction models separately
                    for metric_name, metric_model in model.items():
                        filename = f"{self.model_dir}/prediction_{metric_name}_{timestamp}.joblib"
                        joblib.dump(metric_model, filename)
                else:
                    filename = f"{self.model_dir}/{model_type.value}_{timestamp}.joblib"
                    joblib.dump(model, filename)
            
            # Save scalers
            for scaler_name, scaler in self.scalers.items():
                filename = f"{self.model_dir}/scaler_{scaler_name}_{timestamp}.joblib"
                joblib.dump(scaler, filename)
            
            # Save model performance metrics
            performance_file = f"{self.model_dir}/performance_{timestamp}.pkl"
            with open(performance_file, 'wb') as f:
                pickle.dump(self.model_performance, f)
            
            logger.info(f"✅ Models saved with timestamp {timestamp}")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self, timestamp: str = None) -> bool:
        """Load previously trained models"""
        try:
            if not ML_AVAILABLE:
                return False
            
            if not timestamp:
                # Find latest models
                model_files = [f for f in os.listdir(self.model_dir) if f.endswith('.joblib')]
                if not model_files:
                    return False
                
                # Extract timestamps and find latest
                timestamps = set()
                for f in model_files:
                    parts = f.split('_')
                    if len(parts) >= 2:
                        ts = '_'.join(parts[-2:]).replace('.joblib', '')
                        timestamps.add(ts)
                
                if not timestamps:
                    return False
                
                timestamp = max(timestamps)
            
            # Load models
            models_loaded = 0
            
            # Load anomaly detection
            ad_file = f"{self.model_dir}/anomaly_detection_{timestamp}.joblib"
            if os.path.exists(ad_file):
                self.models[ModelType.ANOMALY_DETECTION] = joblib.load(ad_file)
                models_loaded += 1
            
            # Load prediction models
            target_metrics = ['response_time', 'packet_rate', 'connection_count', 'error_rate']
            self.models[ModelType.PERFORMANCE_PREDICTION] = {}
            
            for metric in target_metrics:
                pred_file = f"{self.model_dir}/prediction_{metric}_{timestamp}.joblib"
                if os.path.exists(pred_file):
                    self.models[ModelType.PERFORMANCE_PREDICTION][metric] = joblib.load(pred_file)
                    models_loaded += 1
            
            # Load capacity planning
            cap_file = f"{self.model_dir}/capacity_planning_{timestamp}.joblib"
            if os.path.exists(cap_file):
                self.models[ModelType.CAPACITY_PLANNING] = joblib.load(cap_file)
                models_loaded += 1
            
            # Load scalers
            for scaler_name in ['features', 'targets']:
                scaler_file = f"{self.model_dir}/scaler_{scaler_name}_{timestamp}.joblib"
                if os.path.exists(scaler_file):
                    self.scalers[scaler_name] = joblib.load(scaler_file)
                    models_loaded += 1
            
            # Load performance metrics
            performance_file = f"{self.model_dir}/performance_{timestamp}.pkl"
            if os.path.exists(performance_file):
                with open(performance_file, 'rb') as f:
                    self.model_performance = pickle.load(f)
                models_loaded += 1
            
            logger.info(f"✅ Loaded {models_loaded} models from timestamp {timestamp}")
            return models_loaded > 0
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        try:
            current_time = time.time()
            
            # Recent anomalies (last hour)
            recent_anomalies = [
                a for a in self.anomalies 
                if current_time - a.timestamp < 3600
            ]
            
            # Recent predictions
            valid_predictions = [
                p for p in self.predictions 
                if p.target_time > current_time
            ]
            
            # Current recommendations
            urgent_recommendations = [
                r for r in self.recommendations 
                if r.urgency in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
            ]
            
            summary = {
                'timestamp': current_time,
                'ml_available': ML_AVAILABLE,
                'models_trained': len(self.models) > 0,
                'metrics_analyzed': len(self.metrics_buffer),
                'anomalies': {
                    'total_detected': len(self.anomalies),
                    'recent_count': len(recent_anomalies),
                    'severity_breakdown': self._get_severity_breakdown(recent_anomalies)
                },
                'predictions': {
                    'total_generated': len(self.predictions),
                    'valid_count': len(valid_predictions),
                    'metrics_covered': list(set(p.metric_name for p in valid_predictions))
                },
                'capacity': {
                    'total_recommendations': len(self.recommendations),
                    'urgent_count': len(urgent_recommendations),
                    'components_analyzed': list(set(r.component for r in self.recommendations))
                },
                'model_performance': self.model_performance.copy()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating analysis summary: {e}")
            return {'error': str(e)}
    
    def _get_severity_breakdown(self, anomalies: List[Anomaly]) -> Dict[str, int]:
        """Get breakdown of anomalies by severity"""
        breakdown = {severity.value: 0 for severity in AlertSeverity}
        
        for anomaly in anomalies:
            breakdown[anomaly.severity.value] += 1
        
        return breakdown
    
    def get_recent_anomalies(self, hours: float = 1.0) -> List[Dict[str, Any]]:
        """Get recent anomalies as dictionary list"""
        cutoff_time = time.time() - (hours * 3600)
        
        recent = [
            {
                'timestamp': a.timestamp,
                'source': a.source,
                'metric_name': a.metric_name,
                'value': a.value,
                'expected_value': a.expected_value,
                'severity': a.severity.value,
                'confidence': a.confidence,
                'description': a.description
            }
            for a in self.anomalies
            if a.timestamp > cutoff_time
        ]
        
        return sorted(recent, key=lambda x: x['timestamp'], reverse=True)
    
    def get_predictions(self) -> List[Dict[str, Any]]:
        """Get current predictions as dictionary list"""
        current_time = time.time()
        
        valid = [
            {
                'target_time': p.target_time,
                'metric_name': p.metric_name,
                'predicted_value': p.predicted_value,
                'confidence_interval': p.confidence_interval,
                'model_accuracy': p.model_accuracy,
                'time_to_prediction': p.target_time - current_time
            }
            for p in self.predictions
            if p.target_time > current_time
        ]
        
        return sorted(valid, key=lambda x: x['target_time'])
    
    def get_capacity_recommendations(self) -> List[Dict[str, Any]]:
        """Get capacity recommendations as dictionary list"""
        return [
            {
                'component': r.component,
                'metric': r.metric,
                'current_utilization': r.current_utilization,
                'predicted_peak': r.predicted_peak,
                'recommendation': r.recommendation,
                'urgency': r.urgency.value,
                'estimated_time_to_limit': r.estimated_time_to_limit
            }
            for r in self.recommendations
        ]

# =============================================================================
# Factory Function
# =============================================================================

def create_ml_analytics_engine(config: Dict[str, Any] = None) -> MLAnalyticsEngine:
    """Factory function to create ML Analytics Engine"""
    return MLAnalyticsEngine(config)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point for testing"""
    print("🧠 MeshAdmin ML Analytics Engine")
    print("=" * 50)
    
    if not ML_AVAILABLE:
        print("❌ Machine Learning dependencies not available")
        print("Install with: pip install scikit-learn pandas numpy")
        return
    
    # Create engine
    engine = create_ml_analytics_engine({
        'buffer_size': 500,
        'train_threshold': 50,
        'model_update_interval': 300  # 5 minutes for testing
    })
    
    # Generate sample metrics for testing
    print("📊 Generating sample metrics...")
    
    import random
    
    sample_metrics = []
    base_time = time.time()
    
    for i in range(100):
        timestamp = base_time + (i * 60)  # 1 minute intervals
        
        # Network Flow Master metrics
        sample_metrics.append(PerformanceMetric(
            timestamp=timestamp,
            source='network_flow_master',
            metric_name='packet_rate',
            value=random.uniform(1000, 5000) + (i * 10)  # Trending upward
        ))
        
        # Load Balancer Pro metrics
        sample_metrics.append(PerformanceMetric(
            timestamp=timestamp,
            source='load_balancer_pro',
            metric_name='response_time',
            value=random.uniform(50, 200) + random.choice([-1, 1]) * random.uniform(0, 50)
        ))
        
        # Add some anomalies
        if i % 20 == 0:
            sample_metrics.append(PerformanceMetric(
                timestamp=timestamp,
                source='load_balancer_pro',
                metric_name='response_time',
                value=random.uniform(500, 1000)  # Anomalous high response time
            ))
    
    # Ingest metrics
    print("🔄 Ingesting metrics...")
    engine.ingest_metrics(sample_metrics)
    
    # Get analysis summary
    print("📋 Analysis Summary:")
    summary = engine.get_analysis_summary()
    
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")
    
    # Show recent anomalies
    anomalies = engine.get_recent_anomalies(hours=24)
    if anomalies:
        print(f"\n🚨 Recent Anomalies ({len(anomalies)} found):")
        for anomaly in anomalies[:5]:  # Show first 5
            print(f"  - {anomaly['description']} (confidence: {anomaly['confidence']:.2f})")
    
    # Show predictions
    predictions = engine.get_predictions()
    if predictions:
        print(f"\n🔮 Predictions ({len(predictions)} found):")
        for pred in predictions[:3]:  # Show first 3
            print(f"  - {pred['metric_name']}: {pred['predicted_value']:.2f} in {pred['time_to_prediction']/60:.1f} minutes")
    
    # Show capacity recommendations
    recommendations = engine.get_capacity_recommendations()
    if recommendations:
        print(f"\n💡 Capacity Recommendations ({len(recommendations)} found):")
        for rec in recommendations[:3]:  # Show first 3
            print(f"  - {rec['component']}: {rec['recommendation']} ({rec['urgency']})")
    
    print("\n✅ ML Analytics Engine test complete!")

if __name__ == "__main__":
    main()

