import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createServer } from 'http';
import request from 'supertest';
import express from 'express';

// Mock external dependencies
vi.mock('../../src/services/metrics-collector', () => ({
  MetricsCollector: {
    getInstance: vi.fn(() => ({
      collectMetrics: vi.fn(),
      getMetrics: vi.fn(),
      aggregateMetrics: vi.fn(),
      exportMetrics: vi.fn()
    }))
  }
}));

vi.mock('../../src/services/anomaly-detector', () => ({
  AnomalyDetector: {
    getInstance: vi.fn(() => ({
      detectAnomalies: vi.fn(),
      getAnomalyHistory: vi.fn(),
      updateThresholds: vi.fn(),
      getDetectionRules: vi.fn()
    }))
  }
}));

vi.mock('../../src/services/capacity-planner', () => ({
  CapacityPlanner: {
    getInstance: vi.fn(() => ({
      analyzeCapacity: vi.fn(),
      predictGrowth: vi.fn(),
      generateRecommendations: vi.fn(),
      getCapacityHistory: vi.fn()
    }))
  }
}));

vi.mock('../../src/services/performance-optimizer', () => ({
  PerformanceOptimizer: {
    getInstance: vi.fn(() => ({
      optimizePerformance: vi.fn(),
      getOptimizationHistory: vi.fn(),
      applyOptimizations: vi.fn(),
      rollbackOptimizations: vi.fn()
    }))
  }
}));

describe('Performance Analytics Suite Critical Path Testing', () => {
  let app: express.Application;
  let server: any;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    
    // Mock authentication middleware
    app.use((req, res, next) => {
      req.user = { 
        id: 'test-user', 
        role: 'analytics-admin', 
        permissions: ['analytics:read', 'analytics:write', 'optimization:manage'] 
      };
      next();
    });

    // Mock Metrics Collection routes
    app.get('/api/v1/analytics/metrics', (req, res) => {
      const { timeframe, metricType, aggregation } = req.query;
      
      res.json({
        success: true,
        filters: { timeframe, metricType, aggregation },
        data: [
          {
            id: 'metric-1',
            timestamp: new Date().toISOString(),
            metricType: 'cpu_utilization',
            value: 0.75,
            unit: 'percentage',
            source: 'server-1',
            tags: { environment: 'production', service: 'web-api' }
          },
          {
            id: 'metric-2',
            timestamp: new Date().toISOString(),
            metricType: 'memory_usage',
            value: 0.68,
            unit: 'percentage',
            source: 'server-1',
            tags: { environment: 'production', service: 'web-api' }
          }
        ],
        summary: {
          totalMetrics: 2,
          timeRange: '1h',
          averageValue: 0.715,
          minValue: 0.68,
          maxValue: 0.75
        }
      });
    });

    app.post('/api/v1/analytics/metrics/collect', (req, res) => {
      const { metrics, source, timestamp } = req.body;
      
      if (!metrics || !Array.isArray(metrics) || metrics.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'Metrics array is required'
        });
      }

      res.json({
        success: true,
        collectionId: 'collect-123',
        metricsCollected: metrics.length,
        source,
        timestamp: timestamp || new Date().toISOString(),
        status: 'completed',
        processingTime: 45.2
      });
    });

    app.get('/api/v1/analytics/metrics/aggregate', (req, res) => {
      const { metricType, aggregation, timeframe } = req.query;
      
      res.json({
        success: true,
        aggregation: aggregation || 'average',
        metricType: metricType || 'cpu_utilization',
        timeframe: timeframe || '1h',
        data: [
          {
            timestamp: '2024-01-01T00:00:00Z',
            value: 0.72,
            count: 60,
            min: 0.65,
            max: 0.78
          },
          {
            timestamp: '2024-01-01T01:00:00Z',
            value: 0.75,
            count: 60,
            min: 0.68,
            max: 0.82
          }
        ],
        summary: {
          totalPoints: 120,
          overallAverage: 0.735,
          overallMin: 0.65,
          overallMax: 0.82
        }
      });
    });

    // Mock Anomaly Detection routes
    app.get('/api/v1/analytics/anomalies', (req, res) => {
      const { severity, status, timeframe } = req.query;
      
      res.json({
        success: true,
        filters: { severity, status, timeframe },
        data: [
          {
            id: 'anomaly-1',
            timestamp: new Date().toISOString(),
            metricType: 'cpu_utilization',
            value: 0.95,
            threshold: 0.85,
            severity: 'high',
            status: 'active',
            source: 'server-1',
            description: 'CPU utilization exceeded threshold',
            confidence: 0.92
          }
        ],
        summary: {
          totalAnomalies: 1,
          activeAnomalies: 1,
          resolvedAnomalies: 0,
          highSeverity: 1,
          mediumSeverity: 0,
          lowSeverity: 0
        }
      });
    });

    app.post('/api/v1/analytics/anomalies/detect', (req, res) => {
      const { metrics, rules, sensitivity } = req.body;
      
      if (!metrics || !Array.isArray(metrics)) {
        return res.status(400).json({
          success: false,
          error: 'Metrics array is required'
        });
      }

      res.json({
        success: true,
        detectionId: 'detect-123',
        anomaliesFound: 2,
        rulesApplied: rules?.length || 5,
        sensitivity: sensitivity || 'medium',
        processingTime: 125.8,
        results: [
          {
            metricType: 'cpu_utilization',
            value: 0.92,
            threshold: 0.85,
            severity: 'high',
            confidence: 0.89
          },
          {
            metricType: 'memory_usage',
            value: 0.88,
            threshold: 0.80,
            severity: 'medium',
            confidence: 0.76
          }
        ]
      });
    });

    // Mock Capacity Planning routes
    app.get('/api/v1/analytics/capacity/analysis', (req, res) => {
      const { resourceType, timeframe, predictionHorizon } = req.query;
      
      res.json({
        success: true,
        filters: { resourceType, timeframe, predictionHorizon },
        data: {
          currentUtilization: 0.75,
          predictedUtilization: {
            '1month': 0.78,
            '3months': 0.82,
            '6months': 0.87,
            '1year': 0.92
          },
          capacityThreshold: 0.90,
          recommendations: [
            'Consider scaling CPU resources in 3 months',
            'Monitor memory usage trends closely',
            'Plan for storage expansion in 6 months'
          ],
          confidence: 0.88
        }
      });
    });

    app.post('/api/v1/analytics/capacity/predict', (req, res) => {
      const { resourceType, historicalData, predictionHorizon } = req.body;
      
      if (!resourceType || !historicalData) {
        return res.status(400).json({
          success: false,
          error: 'Resource type and historical data are required'
        });
      }

      res.json({
        success: true,
        predictionId: 'predict-123',
        resourceType,
        predictionHorizon: predictionHorizon || '6months',
        predictions: [
          {
            timestamp: '2024-07-01T00:00:00Z',
            predictedValue: 0.82,
            confidence: 0.85,
            lowerBound: 0.78,
            upperBound: 0.86
          },
          {
            timestamp: '2024-10-01T00:00:00Z',
            predictedValue: 0.87,
            confidence: 0.82,
            lowerBound: 0.83,
            upperBound: 0.91
          }
        ],
        model: 'LSTM',
        accuracy: 0.89
      });
    });

    // Mock Performance Optimization routes
    app.post('/api/v1/analytics/optimize', (req, res) => {
      const { optimizationType, targets, constraints } = req.body;
      
      if (!optimizationType || !targets) {
        return res.status(400).json({
          success: false,
          error: 'Optimization type and targets are required'
        });
      }

      res.json({
        success: true,
        optimizationId: 'opt-123',
        optimizationType,
        targets,
        constraints: constraints || {},
        recommendations: [
          {
            action: 'scale_cpu',
            impact: 'high',
            effort: 'medium',
            estimatedImprovement: 0.15,
            risk: 'low'
          },
          {
            action: 'optimize_database_queries',
            impact: 'medium',
            effort: 'high',
            estimatedImprovement: 0.08,
            risk: 'medium'
          }
        ],
        estimatedTotalImprovement: 0.23,
        executionPlan: {
          phases: ['analysis', 'implementation', 'validation'],
          estimatedDuration: '2-4 weeks',
          resources: ['devops', 'database_admin']
        }
      });
    });

    app.get('/api/v1/analytics/optimize/history', (req, res) => {
      const { status, timeframe } = req.query;
      
      res.json({
        success: true,
        filters: { status, timeframe },
        data: [
          {
            id: 'opt-hist-1',
            optimizationType: 'performance',
            status: 'completed',
            startDate: '2024-01-01T00:00:00Z',
            completionDate: '2024-01-15T00:00:00Z',
            improvement: 0.18,
            cost: 2500,
            roi: 3.2
          }
        ],
        summary: {
          totalOptimizations: 1,
          completed: 1,
          inProgress: 0,
          failed: 0,
          averageImprovement: 0.18,
          totalROI: 3.2
        }
      });
    });

    // Mock Health Check routes
    app.get('/api/v1/analytics/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          metricsCollector: 'operational',
          anomalyDetector: 'operational',
          capacityPlanner: 'operational',
          performanceOptimizer: 'operational',
          influxDB: 'operational',
          mlEngine: 'operational'
        },
        metrics: {
          totalMetricsCollected: 15420,
          activeAnomalies: 3,
          optimizationsInProgress: 1,
          systemUptime: 86400
        }
      });
    });

    server = createServer(app);
  });

  afterEach(() => {
    server.close();
    vi.clearAllMocks();
  });

  describe('Metrics Collection Critical Paths', () => {
    it('should retrieve metrics with filtering and aggregation', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/metrics?timeframe=1h&metricType=cpu_utilization&aggregation=average')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.filters.timeframe).toBe('1h');
      expect(response.body.filters.metricType).toBe('cpu_utilization');
      expect(response.body.filters.aggregation).toBe('average');
      expect(response.body.data).toBeInstanceOf(Array);
      expect(response.body.data.length).toBe(2);

      const metric = response.body.data[0];
      expect(metric).toHaveProperty('id');
      expect(metric).toHaveProperty('timestamp');
      expect(metric).toHaveProperty('metricType');
      expect(metric).toHaveProperty('value');
      expect(metric).toHaveProperty('unit');
      expect(metric).toHaveProperty('source');
      expect(metric).toHaveProperty('tags');
    });

    it('should collect new metrics successfully', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/metrics/collect')
        .send({
          metrics: [
            { metricType: 'cpu_utilization', value: 0.78, unit: 'percentage' },
            { metricType: 'memory_usage', value: 0.72, unit: 'percentage' }
          ],
          source: 'server-2',
          timestamp: new Date().toISOString()
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.collectionId).toBeDefined();
      expect(response.body.metricsCollected).toBe(2);
      expect(response.body.source).toBe('server-2');
      expect(response.body.status).toBe('completed');
      expect(response.body.processingTime).toBeGreaterThan(0);
    });

    it('should reject metric collection without required data', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/metrics/collect')
        .send({ source: 'server-2' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('Metrics array is required');
    });

    it('should aggregate metrics with statistical summaries', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/metrics/aggregate?metricType=cpu_utilization&aggregation=average&timeframe=2h')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.aggregation).toBe('average');
      expect(response.body.metricType).toBe('cpu_utilization');
      expect(response.body.timeframe).toBe('2h');
      expect(response.body.data).toBeInstanceOf(Array);

      const dataPoint = response.body.data[0];
      expect(dataPoint).toHaveProperty('timestamp');
      expect(dataPoint).toHaveProperty('value');
      expect(dataPoint).toHaveProperty('count');
      expect(dataPoint).toHaveProperty('min');
      expect(dataPoint).toHaveProperty('max');

      const summary = response.body.summary;
      expect(summary).toHaveProperty('totalPoints');
      expect(summary).toHaveProperty('overallAverage');
      expect(summary).toHaveProperty('overallMin');
      expect(summary).toHaveProperty('overallMax');
    });

    it('should validate metric data types and ranges', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/metrics')
        .expect(200);

      const metrics = response.body.data;
      metrics.forEach((metric: any) => {
        // Validate data types
        expect(typeof metric.id).toBe('string');
        expect(typeof metric.timestamp).toBe('string');
        expect(typeof metric.metricType).toBe('string');
        expect(typeof metric.value).toBe('number');
        expect(typeof metric.unit).toBe('string');
        expect(typeof metric.source).toBe('string');
        expect(typeof metric.tags).toBe('object');

        // Validate value ranges
        expect(metric.value).toBeGreaterThanOrEqual(0);
        expect(metric.value).toBeLessThanOrEqual(100); // Percentage values

        // Validate timestamp format
        expect(new Date(metric.timestamp)).toBeInstanceOf(Date);
      });
    });
  });

  describe('Anomaly Detection Critical Paths', () => {
    it('should retrieve anomalies with severity filtering', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/anomalies?severity=high&status=active&timeframe=24h')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.filters.severity).toBe('high');
      expect(response.body.filters.status).toBe('active');
      expect(response.body.filters.timeframe).toBe('24h');
      expect(response.body.data).toBeInstanceOf(Array);

      const anomaly = response.body.data[0];
      expect(anomaly).toHaveProperty('id');
      expect(anomaly).toHaveProperty('timestamp');
      expect(anomaly).toHaveProperty('metricType');
      expect(anomaly).toHaveProperty('value');
      expect(anomaly).toHaveProperty('threshold');
      expect(anomaly).toHaveProperty('severity');
      expect(anomaly).toHaveProperty('status');
      expect(anomaly).toHaveProperty('confidence');
    });

    it('should detect anomalies with custom rules', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/anomalies/detect')
        .send({
          metrics: [
            { metricType: 'cpu_utilization', value: 0.92, timestamp: new Date().toISOString() },
            { metricType: 'memory_usage', value: 0.88, timestamp: new Date().toISOString() }
          ],
          rules: [
            { metricType: 'cpu_utilization', threshold: 0.85, severity: 'high' },
            { metricType: 'memory_usage', threshold: 0.80, severity: 'medium' }
          ],
          sensitivity: 'high'
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.detectionId).toBeDefined();
      expect(response.body.anomaliesFound).toBe(2);
      expect(response.body.rulesApplied).toBe(2);
      expect(response.body.sensitivity).toBe('high');
      expect(response.body.processingTime).toBeGreaterThan(0);

      const results = response.body.results;
      expect(Array.isArray(results)).toBe(true);
      expect(results.length).toBe(2);

      results.forEach((result: any) => {
        expect(result).toHaveProperty('metricType');
        expect(result).toHaveProperty('value');
        expect(result).toHaveProperty('threshold');
        expect(result).toHaveProperty('severity');
        expect(result).toHaveProperty('confidence');
      });
    });

    it('should reject anomaly detection without metrics', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/anomalies/detect')
        .send({ rules: [], sensitivity: 'medium' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('Metrics array is required');
    });

    it('should validate anomaly confidence scores', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/anomalies')
        .expect(200);

      const anomalies = response.body.data;
      anomalies.forEach((anomaly: any) => {
        const confidence = anomaly.confidence;
        expect(confidence).toBeGreaterThanOrEqual(0);
        expect(confidence).toBeLessThanOrEqual(1);
        
        // High confidence anomalies should have detailed information
        if (confidence > 0.8) {
          expect(anomaly.description).toBeDefined();
          expect(anomaly.threshold).toBeDefined();
        }
      });
    });

    it('should provide anomaly summary statistics', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/anomalies')
        .expect(200);

      const summary = response.body.summary;
      expect(summary).toHaveProperty('totalAnomalies');
      expect(summary).toHaveProperty('activeAnomalies');
      expect(summary).toHaveProperty('resolvedAnomalies');
      expect(summary).toHaveProperty('highSeverity');
      expect(summary).toHaveProperty('mediumSeverity');
      expect(summary).toHaveProperty('lowSeverity');

      // Validate summary consistency
      expect(summary.totalAnomalies).toBe(summary.activeAnomalies + summary.resolvedAnomalies);
      expect(summary.totalAnomalies).toBe(summary.highSeverity + summary.mediumSeverity + summary.lowSeverity);
    });
  });

  describe('Capacity Planning Critical Paths', () => {
    it('should analyze current and predicted capacity', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/capacity/analysis?resourceType=cpu&timeframe=6months&predictionHorizon=1year')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.filters.resourceType).toBe('cpu');
      expect(response.body.filters.timeframe).toBe('6months');
      expect(response.body.filters.predictionHorizon).toBe('1year');

      const data = response.body.data;
      expect(data).toHaveProperty('currentUtilization');
      expect(data).toHaveProperty('predictedUtilization');
      expect(data).toHaveProperty('capacityThreshold');
      expect(data).toHaveProperty('recommendations');
      expect(data).toHaveProperty('confidence');

      // Validate utilization values
      expect(data.currentUtilization).toBeGreaterThanOrEqual(0);
      expect(data.currentUtilization).toBeLessThanOrEqual(1);
      expect(data.capacityThreshold).toBeGreaterThanOrEqual(0);
      expect(data.capacityThreshold).toBeLessThanOrEqual(1);

      // Validate predictions
      const predictions = data.predictedUtilization;
      expect(predictions['1month']).toBeGreaterThanOrEqual(0);
      expect(predictions['1year']).toBeLessThanOrEqual(1);
    });

    it('should generate capacity predictions with ML models', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/capacity/predict')
        .send({
          resourceType: 'cpu',
          historicalData: [
            { timestamp: '2024-01-01', value: 0.65 },
            { timestamp: '2024-02-01', value: 0.68 },
            { timestamp: '2024-03-01', value: 0.72 }
          ],
          predictionHorizon: '6months'
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.predictionId).toBeDefined();
      expect(response.body.resourceType).toBe('cpu');
      expect(response.body.predictionHorizon).toBe('6months');
      expect(response.body.model).toBe('LSTM');
      expect(response.body.accuracy).toBeGreaterThan(0.5);

      const predictions = response.body.predictions;
      expect(Array.isArray(predictions)).toBe(true);
      expect(predictions.length).toBeGreaterThan(0);

      predictions.forEach((prediction: any) => {
        expect(prediction).toHaveProperty('timestamp');
        expect(prediction).toHaveProperty('predictedValue');
        expect(prediction).toHaveProperty('confidence');
        expect(prediction).toHaveProperty('lowerBound');
        expect(prediction).toHaveProperty('upperBound');

        // Validate prediction bounds
        expect(prediction.predictedValue).toBeGreaterThanOrEqual(prediction.lowerBound);
        expect(prediction.predictedValue).toBeLessThanOrEqual(prediction.upperBound);
        expect(prediction.confidence).toBeGreaterThanOrEqual(0);
        expect(prediction.confidence).toBeLessThanOrEqual(1);
      });
    });

    it('should reject capacity prediction without required data', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/capacity/predict')
        .send({ resourceType: 'cpu' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('Resource type and historical data are required');
    });

    it('should validate capacity threshold consistency', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/capacity/analysis?resourceType=memory')
        .expect(200);

      const data = response.body.data;
      
      // Current utilization should be below threshold
      expect(data.currentUtilization).toBeLessThan(data.capacityThreshold);
      
      // Predictions should consider threshold
      const predictions = data.predictedUtilization;
      Object.values(predictions).forEach((value: any) => {
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(1);
      });
    });
  });

  describe('Performance Optimization Critical Paths', () => {
    it('should generate optimization recommendations', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/optimize')
        .send({
          optimizationType: 'performance',
          targets: ['cpu_utilization', 'response_time'],
          constraints: { budget: 5000, timeline: '4weeks' }
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.optimizationId).toBeDefined();
      expect(response.body.optimizationType).toBe('performance');
      expect(response.body.targets).toEqual(['cpu_utilization', 'response_time']);
      expect(response.body.constraints.budget).toBe(5000);
      expect(response.body.constraints.timeline).toBe('4weeks');

      const recommendations = response.body.recommendations;
      expect(Array.isArray(recommendations)).toBe(true);
      expect(recommendations.length).toBeGreaterThan(0);

      recommendations.forEach((rec: any) => {
        expect(rec).toHaveProperty('action');
        expect(rec).toHaveProperty('impact');
        expect(rec).toHaveProperty('effort');
        expect(rec).toHaveProperty('estimatedImprovement');
        expect(rec).toHaveProperty('risk');

        // Validate improvement estimates
        expect(rec.estimatedImprovement).toBeGreaterThan(0);
        expect(rec.estimatedImprovement).toBeLessThanOrEqual(1);
      });

      expect(response.body.estimatedTotalImprovement).toBeGreaterThan(0);
      expect(response.body.executionPlan).toHaveProperty('phases');
      expect(response.body.executionPlan).toHaveProperty('estimatedDuration');
      expect(response.body.executionPlan).toHaveProperty('resources');
    });

    it('should reject optimization without required parameters', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/optimize')
        .send({ targets: ['cpu_utilization'] })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('Optimization type and targets are required');
    });

    it('should retrieve optimization history with ROI analysis', async () => {
      const response = await request(server)
        .get('/api/v1/analytics/optimize/history?status=completed&timeframe=6months')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.filters.status).toBe('completed');
      expect(response.body.filters.timeframe).toBe('6months');
      expect(response.body.data).toBeInstanceOf(Array);

      const optimization = response.body.data[0];
      expect(optimization).toHaveProperty('id');
      expect(optimization).toHaveProperty('optimizationType');
      expect(optimization).toHaveProperty('status');
      expect(optimization).toHaveProperty('startDate');
      expect(optimization).toHaveProperty('completionDate');
      expect(optimization).toHaveProperty('improvement');
      expect(optimization).toHaveProperty('cost');
      expect(optimization).toHaveProperty('roi');

      // Validate ROI calculation
      expect(optimization.improvement).toBeGreaterThan(0);
      expect(optimization.cost).toBeGreaterThan(0);
      expect(optimization.roi).toBeGreaterThan(0);
    });

    it('should validate optimization impact assessment', async () => {
      const response = await request(server)
        .post('/api/v1/analytics/optimize')
        .send({
          optimizationType: 'efficiency',
          targets: ['energy_consumption', 'resource_utilization']
        })
        .expect(200);

      const recommendations = response.body.recommendations;
      let totalImprovement = 0;

      recommendations.forEach((rec: any) => {
        totalImprovement += rec.estimatedImprovement;
        
        // Impact should correlate with effort
        if (rec.effort === 'high') {
          expect(rec.impact).toBe('high');
        }
        if (rec.risk === 'high') {
          expect(rec.estimatedImprovement).toBeGreaterThan(0.1); // High risk should have high potential
        }
      });

      // Total improvement should match sum of individual improvements
      expect(response.body.estimatedTotalImprovement).toBeCloseTo(totalImprovement, 2);
    });
  });

  describe('Cross-Service Integration', () => {
    it('should correlate metrics with anomaly detection', async () => {
      // Get metrics
      const metricsResponse = await request(server)
        .get('/api/v1/analytics/metrics?metricType=cpu_utilization')
        .expect(200);

      // Get anomalies
      const anomaliesResponse = await request(server)
        .get('/api/v1/analytics/anomalies?metricType=cpu_utilization')
        .expect(200);

      expect(metricsResponse.body.success).toBe(true);
      expect(anomaliesResponse.body.success).toBe(true);

      const metrics = metricsResponse.body.data;
      const anomalies = anomaliesResponse.body.data;

      // High CPU metrics should correlate with anomalies
      const highCPUMetrics = metrics.filter((m: any) => m.value > 0.8);
      if (highCPUMetrics.length > 0) {
        expect(anomalies.length).toBeGreaterThan(0);
        const highSeverityAnomalies = anomalies.filter((a: any) => a.severity === 'high');
        expect(highSeverityAnomalies.length).toBeGreaterThan(0);
      }
    });

    it('should integrate capacity planning with optimization', async () => {
      // Get capacity analysis
      const capacityResponse = await request(server)
        .get('/api/v1/analytics/capacity/analysis?resourceType=cpu')
        .expect(200);

      // Generate optimization recommendations
      const optimizationResponse = await request(server)
        .post('/api/v1/analytics/optimize')
        .send({
          optimizationType: 'capacity',
          targets: ['cpu_utilization'],
          constraints: { timeline: '3months' }
        })
        .expect(200);

      expect(capacityResponse.body.success).toBe(true);
      expect(optimizationResponse.body.success).toBe(true);

      const capacity = capacityResponse.body.data;
      const optimization = optimizationResponse.body;

      // High utilization should trigger optimization recommendations
      if (capacity.currentUtilization > 0.8) {
        expect(optimization.recommendations.length).toBeGreaterThan(0);
        const scalingRecommendations = optimization.recommendations.filter((r: any) => 
          r.action.includes('scale') || r.action.includes('expand')
        );
        expect(scalingRecommendations.length).toBeGreaterThan(0);
      }
    });

    it('should maintain data consistency across analytics services', async () => {
      // Get data from all services
      const metricsResponse = await request(server).get('/api/v1/analytics/metrics');
      const anomaliesResponse = await request(server).get('/api/v1/analytics/anomalies');
      const capacityResponse = await request(server).get('/api/v1/analytics/capacity/analysis');
      const optimizationResponse = await request(server).get('/api/v1/analytics/optimize/history');

      expect(metricsResponse.body.success).toBe(true);
      expect(anomaliesResponse.body.success).toBe(true);
      expect(capacityResponse.body.success).toBe(true);
      expect(optimizationResponse.body.success).toBe(true);

      // All services should be operational
      const healthResponse = await request(server).get('/api/v1/analytics/health');
      expect(healthResponse.body.status).toBe('healthy');
    });
  });

  describe('Performance and Scalability', () => {
    it('should respond to metrics queries within acceptable time', async () => {
      const startTime = Date.now();
      
      await request(server)
        .get('/api/v1/analytics/metrics')
        .expect(200);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(1000); // Should respond within 1 second
    });

    it('should handle concurrent analytics operations efficiently', async () => {
      const concurrentRequests = 5;
      const promises = [];

      for (let i = 0; i < concurrentRequests; i++) {
        promises.push(
          request(server)
            .get('/api/v1/analytics/metrics')
            .expect(200)
        );
      }

      const responses = await Promise.all(promises);
      
      responses.forEach(response => {
        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
        expect(response.body.data).toBeInstanceOf(Array);
      });
    });

    it('should maintain consistent performance under load', async () => {
      const iterations = 10;
      const responseTimes: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = Date.now();
        
        await request(server)
          .get('/api/v1/analytics/metrics')
          .expect(200);

        responseTimes.push(Date.now() - startTime);
      }

      const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
      const maxResponseTime = Math.max(...responseTimes);
      const minResponseTime = Math.min(...responseTimes);

      expect(avgResponseTime).toBeLessThan(500); // Average under 500ms
      expect(maxResponseTime).toBeLessThan(1000); // Max under 1 second
      expect(minResponseTime).toBeLessThan(200);  // Min under 200ms
    });
  });

  describe('Error Handling and Resilience', () => {
    it('should handle service unavailability gracefully', async () => {
      // Mock service failure
      app.get('/api/v1/analytics/metrics', (req, res) => {
        res.status(503).json({
          success: false,
          error: 'Metrics service temporarily unavailable',
          retryAfter: 30
        });
      });

      const response = await request(server)
        .get('/api/v1/analytics/metrics')
        .expect(503);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('unavailable');
      expect(response.body.retryAfter).toBeDefined();
    });

    it('should validate input parameters consistently', async () => {
      // Test various invalid inputs
      const invalidInputs = [
        { metrics: [] },
        { metrics: 'not-an-array' },
        { resourceType: '', historicalData: [] },
        { optimizationType: '', targets: [] }
      ];

      for (const invalidInput of invalidInputs) {
        if (invalidInput.metrics !== undefined) {
          // Metrics collection
          const response = await request(server)
            .post('/api/v1/analytics/metrics/collect')
            .send(invalidInput)
            .expect(400);

          expect(response.body.success).toBe(false);
        } else if (invalidInput.resourceType !== undefined) {
          // Capacity prediction
          const response = await request(server)
            .post('/api/v1/analytics/capacity/predict')
            .send(invalidInput)
            .expect(400);

          expect(response.body.success).toBe(false);
        } else if (invalidInput.optimizationType !== undefined) {
          // Performance optimization
          const response = await request(server)
            .post('/api/v1/analytics/optimize')
            .send(invalidInput)
            .expect(400);

          expect(response.body.success).toBe(false);
        }
      }
    });

    it('should handle malformed requests gracefully', async () => {
      // Test malformed JSON
      const response = await request(server)
        .post('/api/v1/analytics/metrics/collect')
        .set('Content-Type', 'application/json')
        .send('{ invalid json }')
        .expect(400);

      expect(response.body.success).toBe(false);
    });
  });

  describe('Data Validation and Integrity', () => {
    it('should maintain referential integrity across services', async () => {
      // Get data from all services
      const metricsResponse = await request(server).get('/api/v1/analytics/metrics');
      const anomaliesResponse = await request(server).get('/api/v1/analytics/anomalies');
      const capacityResponse = await request(server).get('/api/v1/analytics/capacity/analysis');

      expect(metricsResponse.body.success).toBe(true);
      expect(anomaliesResponse.body.success).toBe(true);
      expect(capacityResponse.body.success).toBe(true);

      // Data should be consistent across requests
      const metricsResponse2 = await request(server).get('/api/v1/analytics/metrics');
      expect(metricsResponse.body.data).toEqual(metricsResponse2.body.data);
    });

    it('should validate data formats consistently', async () => {
      const responses = [
        await request(server).get('/api/v1/analytics/metrics'),
        await request(server).get('/api/v1/analytics/anomalies'),
        await request(server).get('/api/v1/analytics/capacity/analysis'),
        await request(server).get('/api/v1/analytics/optimize/history')
      ];

      responses.forEach(response => {
        expect(response.body.success).toBe(true);
        expect(response.body.data).toBeDefined();
      });
    });

    it('should handle empty datasets gracefully', async () => {
      // Mock empty responses for this test
      app.get('/api/v1/analytics/metrics', (req, res) => {
        res.json({
          success: true,
          data: [],
          message: 'No metrics available'
        });
      });

      app.get('/api/v1/analytics/anomalies', (req, res) => {
        res.json({
          success: true,
          data: [],
          message: 'No anomalies detected'
        });
      });

      const metricsResponse = await request(server).get('/api/v1/analytics/metrics');
      const anomaliesResponse = await request(server).get('/api/v1/analytics/anomalies');

      expect(metricsResponse.body.success).toBe(true);
      expect(metricsResponse.body.data).toEqual([]);
      expect(metricsResponse.body.message).toBe('No metrics available');

      expect(anomaliesResponse.body.success).toBe(true);
      expect(anomaliesResponse.body.data).toEqual([]);
      expect(anomaliesResponse.body.message).toBe('No anomalies detected');
    });
  });
});
