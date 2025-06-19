/**
 * @file MPTCP Performance Analytics Engine
 * @description Core analytics processing engine for unified data handling across all applications
 */

import { EventEmitter } from 'eventemitter3';
import { v4 as uuidv4 } from 'uuid';

// =============================================================================
// Core Types and Interfaces
// =============================================================================

export interface MetricPoint {
  timestamp: number;
  value: number;
  tags?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface FlowMetrics {
  source: 'network-flow-master' | 'load-balancer-pro' | 'observability-dashboard';
  type: 'netflow' | 'sflow' | 'load-balancing' | 'system' | 'custom';
  device_id?: string;
  session_id?: string;
  metrics: {
    packets_per_second?: MetricPoint[];
    bytes_per_second?: MetricPoint[];
    connections_active?: MetricPoint[];
    response_time?: MetricPoint[];
    error_rate?: MetricPoint[];
    cache_hit_ratio?: MetricPoint[];
    [key: string]: MetricPoint[] | undefined;
  };
  aggregations?: {
    interval: '1m' | '5m' | '15m' | '1h' | '1d';
    functions: ('avg' | 'sum' | 'min' | 'max' | 'count')[];
  };
}

export interface AnalyticsEvent {
  id: string;
  timestamp: number;
  source: string;
  type: 'metric' | 'alert' | 'anomaly' | 'performance' | 'error';
  severity: 'low' | 'medium' | 'high' | 'critical';
  data: any;
  correlation_id?: string;
}

export interface ProcessingPipeline {
  id: string;
  name: string;
  input_sources: string[];
  processors: ProcessorConfig[];
  output_targets: string[];
  enabled: boolean;
}

export interface ProcessorConfig {
  type: 'filter' | 'transform' | 'aggregate' | 'correlation' | 'anomaly_detection';
  config: Record<string, any>;
}

// =============================================================================
// Analytics Engine Core Class
// =============================================================================

export class AnalyticsEngine extends EventEmitter {
  private pipelines: Map<string, ProcessingPipeline> = new Map();
  private metrics: Map<string, FlowMetrics[]> = new Map();
  private processors: Map<string, MetricProcessor> = new Map();
  private isRunning: boolean = false;
  private processingInterval?: NodeJS.Timeout;

  constructor(private config: AnalyticsEngineConfig = {}) {
    super();
    this.setupDefaultProcessors();
  }

  // =========================================================================
  // Core Engine Operations
  // =========================================================================

  /**
   * Start the analytics engine
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      throw new Error('Analytics engine is already running');
    }

    this.isRunning = true;
    
    // Start processing interval
    this.processingInterval = setInterval(() => {
      this.processMetrics();
    }, this.config.processingInterval || 5000);

    this.emit('started');
    console.log('✅ Analytics Engine started');
  }

  /**
   * Stop the analytics engine
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;
    
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
    }

    this.emit('stopped');
    console.log('🛑 Analytics Engine stopped');
  }

  /**
   * Ingest metrics from any source application
   */
  async ingestMetrics(metrics: FlowMetrics): Promise<string> {
    const id = uuidv4();
    const source = metrics.source;

    // Store metrics by source
    if (!this.metrics.has(source)) {
      this.metrics.set(source, []);
    }
    
    this.metrics.get(source)!.push({
      ...metrics,
      session_id: metrics.session_id || id
    });

    // Emit event for real-time processing
    this.emit('metrics:ingested', {
      id,
      source,
      timestamp: Date.now(),
      metrics
    });

    return id;
  }

  /**
   * Create and register a processing pipeline
   */
  createPipeline(pipeline: Omit<ProcessingPipeline, 'id'>): string {
    const id = uuidv4();
    const fullPipeline: ProcessingPipeline = {
      ...pipeline,
      id
    };

    this.pipelines.set(id, fullPipeline);
    this.emit('pipeline:created', fullPipeline);

    return id;
  }

  /**
   * Get real-time metrics for a specific source
   */
  getMetrics(source: string, timeRange?: { start: number; end: number }): FlowMetrics[] {
    const sourceMetrics = this.metrics.get(source) || [];
    
    if (!timeRange) {
      return sourceMetrics;
    }

    return sourceMetrics.filter(metric => {
      const latestTimestamp = Math.max(
        ...Object.values(metric.metrics)
          .flat()
          .filter(Boolean)
          .map(point => point.timestamp)
      );
      return latestTimestamp >= timeRange.start && latestTimestamp <= timeRange.end;
    });
  }

  /**
   * Get aggregated metrics across all sources
   */
  getAggregatedMetrics(timeRange: { start: number; end: number }): AggregatedMetrics {
    const allMetrics = Array.from(this.metrics.values()).flat();
    
    const aggregated: AggregatedMetrics = {
      timestamp: Date.now(),
      total_packets_per_second: 0,
      total_connections: 0,
      average_response_time: 0,
      error_rate: 0,
      cache_efficiency: 0,
      source_breakdown: {}
    };

    // Process metrics from each source
    for (const [source, metrics] of this.metrics.entries()) {
      const filteredMetrics = metrics.filter(metric => {
        const latestTimestamp = Math.max(
          ...Object.values(metric.metrics)
            .flat()
            .filter(Boolean)
            .map(point => point.timestamp)
        );
        return latestTimestamp >= timeRange.start && latestTimestamp <= timeRange.end;
      });

      aggregated.source_breakdown[source] = this.calculateSourceMetrics(filteredMetrics);
      
      // Add to totals
      aggregated.total_packets_per_second += aggregated.source_breakdown[source].packets_per_second;
      aggregated.total_connections += aggregated.source_breakdown[source].connections;
    }

    return aggregated;
  }

  // =========================================================================
  // Private Methods
  // =========================================================================

  private setupDefaultProcessors(): void {
    // Performance Correlation Processor
    this.processors.set('correlation', new CorrelationProcessor());
    
    // Anomaly Detection Processor
    this.processors.set('anomaly', new AnomalyDetectionProcessor());
    
    // Real-time Aggregation Processor
    this.processors.set('aggregation', new AggregationProcessor());
  }

  private async processMetrics(): Promise<void> {
    for (const [id, pipeline] of this.pipelines.entries()) {
      if (!pipeline.enabled) continue;

      try {
        await this.executePipeline(pipeline);
      } catch (error) {
        this.emit('error', {
          type: 'pipeline_error',
          pipeline_id: id,
          error: error instanceof Error ? error.message : String(error)
        });
      }
    }
  }

  private async executePipeline(pipeline: ProcessingPipeline): Promise<void> {
    // Get input data from specified sources
    const inputData: FlowMetrics[] = [];
    for (const source of pipeline.input_sources) {
      inputData.push(...(this.metrics.get(source) || []));
    }

    if (inputData.length === 0) return;

    // Process through each processor in the pipeline
    let processedData: any = inputData;
    
    for (const processorConfig of pipeline.processors) {
      const processor = this.processors.get(processorConfig.type);
      if (processor) {
        processedData = await processor.process(processedData, processorConfig.config);
      }
    }

    // Emit results
    this.emit('pipeline:processed', {
      pipeline_id: pipeline.id,
      data: processedData,
      timestamp: Date.now()
    });
  }

  private calculateSourceMetrics(metrics: FlowMetrics[]): SourceMetrics {
    if (metrics.length === 0) {
      return {
        packets_per_second: 0,
        connections: 0,
        response_time: 0,
        error_rate: 0,
        cache_hit_ratio: 0
      };
    }

    // Calculate averages from the latest metrics
    const latest = metrics[metrics.length - 1];
    
    return {
      packets_per_second: this.getLatestValue(latest.metrics.packets_per_second) || 0,
      connections: this.getLatestValue(latest.metrics.connections_active) || 0,
      response_time: this.getLatestValue(latest.metrics.response_time) || 0,
      error_rate: this.getLatestValue(latest.metrics.error_rate) || 0,
      cache_hit_ratio: this.getLatestValue(latest.metrics.cache_hit_ratio) || 0
    };
  }

  private getLatestValue(points?: MetricPoint[]): number | undefined {
    if (!points || points.length === 0) return undefined;
    return points[points.length - 1].value;
  }
}

// =============================================================================
// Metric Processors
// =============================================================================

abstract class MetricProcessor {
  abstract process(data: any, config: Record<string, any>): Promise<any>;
}

class CorrelationProcessor extends MetricProcessor {
  async process(data: FlowMetrics[], config: Record<string, any>): Promise<CorrelationResult[]> {
    // Correlate metrics across different sources
    const correlations: CorrelationResult[] = [];
    
    // Find patterns between load balancer performance and flow metrics
    const networkMetrics = data.filter(m => m.source === 'network-flow-master');
    const lbMetrics = data.filter(m => m.source === 'load-balancer-pro');
    
    if (networkMetrics.length > 0 && lbMetrics.length > 0) {
      correlations.push({
        id: uuidv4(),
        type: 'network_lb_correlation',
        correlation_score: this.calculateCorrelation(networkMetrics, lbMetrics),
        timestamp: Date.now(),
        sources: ['network-flow-master', 'load-balancer-pro']
      });
    }
    
    return correlations;
  }

  private calculateCorrelation(metricsA: FlowMetrics[], metricsB: FlowMetrics[]): number {
    // Simplified correlation calculation
    // In practice, this would use statistical correlation algorithms
    return Math.random() * 0.5 + 0.5; // Mock correlation score
  }
}

class AnomalyDetectionProcessor extends MetricProcessor {
  async process(data: FlowMetrics[], config: Record<string, any>): Promise<AnomalyAlert[]> {
    const anomalies: AnomalyAlert[] = [];
    
    for (const metrics of data) {
      // Check for packet rate anomalies
      const packetRates = metrics.metrics.packets_per_second || [];
      if (packetRates.length > 5) {
        const recent = packetRates.slice(-5);
        const avg = recent.reduce((sum, point) => sum + point.value, 0) / recent.length;
        const latest = recent[recent.length - 1].value;
        
        if (Math.abs(latest - avg) > avg * 0.5) { // 50% deviation
          anomalies.push({
            id: uuidv4(),
            type: 'packet_rate_anomaly',
            severity: latest > avg * 1.5 ? 'high' : 'medium',
            description: `Packet rate anomaly detected: ${latest.toFixed(2)} pps (avg: ${avg.toFixed(2)} pps)`,
            timestamp: Date.now(),
            source: metrics.source,
            device_id: metrics.device_id
          });
        }
      }
    }
    
    return anomalies;
  }
}

class AggregationProcessor extends MetricProcessor {
  async process(data: FlowMetrics[], config: Record<string, any>): Promise<AggregatedMetrics> {
    const now = Date.now();
    const interval = config.interval || 60000; // 1 minute default
    
    const aggregated: AggregatedMetrics = {
      timestamp: now,
      total_packets_per_second: 0,
      total_connections: 0,
      average_response_time: 0,
      error_rate: 0,
      cache_efficiency: 0,
      source_breakdown: {}
    };
    
    // Aggregate metrics by source
    const sourceGroups = new Map<string, FlowMetrics[]>();
    for (const metrics of data) {
      if (!sourceGroups.has(metrics.source)) {
        sourceGroups.set(metrics.source, []);
      }
      sourceGroups.get(metrics.source)!.push(metrics);
    }
    
    for (const [source, metrics] of sourceGroups.entries()) {
      aggregated.source_breakdown[source] = this.aggregateSourceMetrics(metrics);
      aggregated.total_packets_per_second += aggregated.source_breakdown[source].packets_per_second;
      aggregated.total_connections += aggregated.source_breakdown[source].connections;
    }
    
    return aggregated;
  }
  
  private aggregateSourceMetrics(metrics: FlowMetrics[]): SourceMetrics {
    // Calculate aggregated metrics for a source
    let totalPackets = 0;
    let totalConnections = 0;
    let totalResponseTime = 0;
    let count = 0;
    
    for (const metric of metrics) {
      if (metric.metrics.packets_per_second) {
        totalPackets += metric.metrics.packets_per_second.reduce((sum, p) => sum + p.value, 0);
      }
      if (metric.metrics.connections_active) {
        totalConnections += metric.metrics.connections_active.reduce((sum, p) => sum + p.value, 0);
      }
      if (metric.metrics.response_time) {
        totalResponseTime += metric.metrics.response_time.reduce((sum, p) => sum + p.value, 0);
      }
      count++;
    }
    
    return {
      packets_per_second: count > 0 ? totalPackets / count : 0,
      connections: count > 0 ? totalConnections / count : 0,
      response_time: count > 0 ? totalResponseTime / count : 0,
      error_rate: 0, // Would calculate from error metrics
      cache_hit_ratio: 0 // Would calculate from cache metrics
    };
  }
}

// =============================================================================
// Supporting Types
// =============================================================================

export interface AnalyticsEngineConfig {
  processingInterval?: number;
  maxMetricsHistory?: number;
  enabledProcessors?: string[];
  storage?: {
    type: 'memory' | 'redis' | 'influxdb';
    connection?: any;
  };
}

export interface AggregatedMetrics {
  timestamp: number;
  total_packets_per_second: number;
  total_connections: number;
  average_response_time: number;
  error_rate: number;
  cache_efficiency: number;
  source_breakdown: Record<string, SourceMetrics>;
}

export interface SourceMetrics {
  packets_per_second: number;
  connections: number;
  response_time: number;
  error_rate: number;
  cache_hit_ratio: number;
}

export interface CorrelationResult {
  id: string;
  type: string;
  correlation_score: number;
  timestamp: number;
  sources: string[];
}

export interface AnomalyAlert {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  timestamp: number;
  source: string;
  device_id?: string;
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new analytics engine instance with optimal configuration
 */
export function createAnalyticsEngine(config?: Partial<AnalyticsEngineConfig>): AnalyticsEngine {
  const defaultConfig: AnalyticsEngineConfig = {
    processingInterval: 5000, // 5 seconds
    maxMetricsHistory: 1000,
    enabledProcessors: ['correlation', 'anomaly', 'aggregation'],
    storage: {
      type: 'memory'
    }
  };

  return new AnalyticsEngine({ ...defaultConfig, ...config });
}

// =============================================================================
// Exports
// =============================================================================

export default AnalyticsEngine;
export { AnalyticsEngine, createAnalyticsEngine };

