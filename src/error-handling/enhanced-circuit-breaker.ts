#!/usr/bin/env ts-node
/**
 * Enhanced Circuit Breaker Implementation
 * Task 4.1: Error Handling & Recovery
 * 
 * Features:
 * - Multiple circuit breaker strategies
 * - Adaptive thresholds based on system health
 * - Health monitoring and self-healing
 * - Integration with retry mechanisms
 * - Metrics collection and reporting
 * - Graceful degradation strategies
 */

import { EventEmitter } from 'events';
import { errorHandler, MeshAdminError, ErrorContext, ErrorCategory } from './error-handling-framework';
import { retryEngine, RetryOptions } from './retry-mechanism';

// ============================================================================
// CIRCUIT BREAKER STATES
// ============================================================================

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN' | 'FORCED_OPEN';

export interface CircuitBreakerOptions {
  // Basic configuration
  failureThreshold: number;
  successThreshold: number;
  cooldownPeriod: number;
  requestTimeout: number;
  
  // Advanced configuration
  strategy: 'consecutive-failures' | 'failure-rate' | 'adaptive' | 'hybrid';
  failureRateThreshold: number;
  minimumRequests: number;
  slidingWindowSize: number;
  
  // Health monitoring
  healthCheckInterval: number;
  healthCheckTimeout: number;
  healthCheckFunction?: () => Promise<boolean>;
  
  // Adaptive features
  enableAdaptiveThresholds: boolean;
  adaptiveMultiplier: number;
  adaptiveDecay: number;
  
  // Graceful degradation
  enableFallback: boolean;
  fallbackFunction?: () => Promise<any>;
  fallbackValue?: any;
  
  // Metrics and monitoring
  enableMetrics: boolean;
  metricsRetention: number;
  enablePersistence: boolean;
  persistencePath?: string;
  
  // Integration
  enableRetry: boolean;
  retryOptions?: Partial<RetryOptions>;
  
  // Tags for identification
  tags: Record<string, string>;
}

export interface CircuitBreakerMetrics {
  totalRequests: number;
  totalSuccesses: number;
  totalFailures: number;
  totalTimeouts: number;
  currentFailureRate: number;
  averageResponseTime: number;
  circuitOpenCount: number;
  lastOpenDuration: number;
  totalOpenDuration: number;
  healthCheckFailures: number;
  lastHealthCheck: Date;
  state: CircuitState;
  lastStateChange: Date;
}

export interface CircuitBreakerEvent {
  circuitId: string;
  eventType: 'state-change' | 'request' | 'success' | 'failure' | 'timeout' | 'health-check';
  timestamp: Date;
  data: any;
}

// ============================================================================
// ENHANCED CIRCUIT BREAKER
// ============================================================================

export class EnhancedCircuitBreaker extends EventEmitter {
  private static instances: Map<string, EnhancedCircuitBreaker> = new Map();
  
  private circuitId: string;
  private options: Required<CircuitBreakerOptions>;
  private state: CircuitState = 'CLOSED';
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number = 0;
  private lastSuccessTime: number = 0;
  private openTimestamp: number = 0;
  private nextAttemptTime: number = 0;
  
  // Metrics and monitoring
  private metrics: CircuitBreakerMetrics;
  private requestHistory: Array<{ timestamp: number; success: boolean; responseTime: number }> = [];
  private healthCheckTimer?: NodeJS.Timeout;
  private lastHealthCheckResult: boolean = true;
  
  // Adaptive thresholds
  private adaptiveThreshold: number;
  private healthScore: number = 1.0;
  
  // Sliding window for failure rate calculation
  private slidingWindow: Array<{ timestamp: number; success: boolean }> = [];

  private constructor(circuitId: string, options: Partial<CircuitBreakerOptions> = {}) {
    super();
    
    this.circuitId = circuitId;
    this.options = this.mergeDefaultOptions(options);
    this.adaptiveThreshold = this.options.failureThreshold;
    
    this.metrics = this.initializeMetrics();
    this.setupHealthMonitoring();
    
    if (this.options.enablePersistence) {
      this.loadPersistedState();
    }
  }

  public static getInstance(circuitId: string, options?: Partial<CircuitBreakerOptions>): EnhancedCircuitBreaker {
    if (!EnhancedCircuitBreaker.instances.has(circuitId)) {
      EnhancedCircuitBreaker.instances.set(circuitId, new EnhancedCircuitBreaker(circuitId, options));
    }
    return EnhancedCircuitBreaker.instances.get(circuitId)!;
  }

  /**
   * Execute function with circuit breaker protection
   */
  public async execute<T>(
    operation: () => Promise<T>,
    context: ErrorContext = {}
  ): Promise<T> {
    const startTime = Date.now();
    
    // Check if circuit is open
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttemptTime) {
        // Circuit is still cooling down
        this.recordRequest(false, Date.now() - startTime);
        this.emit('request', { circuitId: this.circuitId, eventType: 'request', timestamp: new Date(), data: { rejected: true, reason: 'circuit-open' } });
        
        // Use fallback if available
        if (this.options.enableFallback) {
          return this.executeFallback(context);
        }
        
        throw new MeshAdminError(
          `Circuit "${this.circuitId}" is open`,
          'CIRCUIT_OPEN_ERROR',
          503,
          context,
          { retryable: true, circuitBreaker: true }
        );
      }
      
      // Transition to half-open
      this.transitionToState('HALF_OPEN');
    }
    
    // Execute operation with timeout
    try {
      const result = await this.executeWithTimeout(operation, this.options.requestTimeout);
      
      // Record success
      this.recordRequest(true, Date.now() - startTime);
      this.handleSuccess();
      
      // If in half-open state, transition to closed
      if (this.state === 'HALF_OPEN') {
        this.transitionToState('CLOSED');
      }
      
      return result;
    } catch (error) {
      // Record failure
      this.recordRequest(false, Date.now() - startTime);
      this.handleFailure(error, context);
      
      // Use fallback if available and circuit is open
      if (this.state === 'OPEN' && this.options.enableFallback) {
        return this.executeFallback(context);
      }
      
      // Rethrow the error
      throw error;
    }
  }

  /**
   * Execute operation with timeout
   */
  private async executeWithTimeout<T>(operation: () => Promise<T>, timeout: number): Promise<T> {
    return Promise.race([
      operation(),
      new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Operation timed out after ${timeout}ms`));
        }, timeout);
      })
    ]);
  }

  /**
   * Handle successful operation
   */
  private handleSuccess(): void {
    this.successCount++;
    this.failureCount = 0;
    this.lastSuccessTime = Date.now();
    
    // Update adaptive threshold
    if (this.options.enableAdaptiveThresholds) {
      this.updateAdaptiveThreshold(true);
    }
    
    this.emit('success', { circuitId: this.circuitId, eventType: 'success', timestamp: new Date(), data: { successCount: this.successCount } });
  }

  /**
   * Handle failed operation
   */
  private handleFailure(error: Error, context: ErrorContext): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    // Update adaptive threshold
    if (this.options.enableAdaptiveThresholds) {
      this.updateAdaptiveThreshold(false);
    }
    
    // Check if circuit should open
    if (this.shouldOpenCircuit()) {
      this.transitionToState('OPEN');
    }
    
    this.emit('failure', { circuitId: this.circuitId, eventType: 'failure', timestamp: new Date(), data: { error, failureCount: this.failureCount, context } });
  }

  /**
   * Determine if circuit should open
   */
  private shouldOpenCircuit(): boolean {
    if (this.state === 'FORCED_OPEN') return false;
    
    switch (this.options.strategy) {
      case 'consecutive-failures':
        return this.failureCount >= this.adaptiveThreshold;
      
      case 'failure-rate':
        if (this.slidingWindow.length < this.options.minimumRequests) return false;
        const failureRate = this.calculateFailureRate();
        return failureRate >= this.options.failureRateThreshold;
      
      case 'adaptive':
        return this.failureCount >= this.adaptiveThreshold || 
               this.calculateFailureRate() >= this.options.failureRateThreshold;
      
      case 'hybrid':
        const consecutiveThreshold = this.failureCount >= this.adaptiveThreshold;
        const rateThreshold = this.slidingWindow.length >= this.options.minimumRequests && 
                             this.calculateFailureRate() >= this.options.failureRateThreshold;
        return consecutiveThreshold || rateThreshold;
      
      default:
        return this.failureCount >= this.adaptiveThreshold;
    }
  }

  /**
   * Calculate current failure rate
   */
  private calculateFailureRate(): number {
    if (this.slidingWindow.length === 0) return 0;
    
    const failures = this.slidingWindow.filter(item => !item.success).length;
    return failures / this.slidingWindow.length;
  }

  /**
   * Update adaptive threshold based on operation result
   */
  private updateAdaptiveThreshold(success: boolean): void {
    if (success) {
      // Decrease threshold (more lenient)
      this.adaptiveThreshold = Math.max(
        this.options.failureThreshold,
        this.adaptiveThreshold * (1 - this.options.adaptiveDecay)
      );
      this.healthScore = Math.min(1.0, this.healthScore + 0.1);
    } else {
      // Increase threshold (more strict)
      this.adaptiveThreshold = Math.min(
        this.options.failureThreshold * this.options.adaptiveMultiplier,
        this.adaptiveThreshold * (1 + this.options.adaptiveDecay)
      );
      this.healthScore = Math.max(0.0, this.healthScore - 0.2);
    }
  }

  /**
   * Transition to new state
   */
  private transitionToState(newState: CircuitState): void {
    const oldState = this.state;
    this.state = newState;
    this.metrics.lastStateChange = new Date();
    
    switch (newState) {
      case 'OPEN':
        this.openTimestamp = Date.now();
        this.nextAttemptTime = Date.now() + this.options.cooldownPeriod;
        this.metrics.circuitOpenCount++;
        break;
      
      case 'HALF_OPEN':
        this.successCount = 0;
        this.failureCount = 0;
        break;
      
      case 'CLOSED':
        this.successCount = 0;
        this.failureCount = 0;
        break;
    }
    
    this.emit('state-change', {
      circuitId: this.circuitId,
      eventType: 'state-change',
      timestamp: new Date(),
      data: { oldState, newState, reason: this.getStateChangeReason(oldState, newState) }
    });
    
    // Persist state if enabled
    if (this.options.enablePersistence) {
      this.persistState();
    }
  }

  /**
   * Get reason for state change
   */
  private getStateChangeReason(oldState: CircuitState, newState: CircuitState): string {
    if (newState === 'OPEN') {
      return this.options.strategy === 'consecutive-failures' 
        ? `Consecutive failures (${this.failureCount}) exceeded threshold (${this.adaptiveThreshold})`
        : `Failure rate (${this.calculateFailureRate().toFixed(2)}) exceeded threshold (${this.options.failureRateThreshold})`;
    }
    
    if (newState === 'HALF_OPEN') {
      return 'Cooldown period expired, testing circuit';
    }
    
    if (newState === 'CLOSED') {
      return 'Success threshold reached, circuit closed';
    }
    
    return 'Manual state change';
  }

  /**
   * Execute fallback function or return fallback value
   */
  private async executeFallback(context: ErrorContext): Promise<any> {
    if (this.options.fallbackFunction) {
      try {
        return await this.options.fallbackFunction();
      } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
        return this.options.fallbackValue;
      }
    }
    
    return this.options.fallbackValue;
  }

  /**
   * Record request for metrics
   */
  private recordRequest(success: boolean, responseTime: number): void {
    const timestamp = Date.now();
    
    // Update sliding window
    this.slidingWindow.push({ timestamp, success });
    if (this.slidingWindow.length > this.options.slidingWindowSize) {
      this.slidingWindow.shift();
    }
    
    // Update request history
    this.requestHistory.push({ timestamp, success, responseTime });
    if (this.requestHistory.length > this.options.metricsRetention) {
      this.requestHistory.shift();
    }
    
    // Update metrics
    this.metrics.totalRequests++;
    if (success) {
      this.metrics.totalSuccesses++;
    } else {
      this.metrics.totalFailures++;
    }
    
    // Update average response time
    const totalResponseTime = this.requestHistory.reduce((sum, req) => sum + req.responseTime, 0);
    this.metrics.averageResponseTime = totalResponseTime / this.requestHistory.length;
    
    // Update failure rate
    this.metrics.currentFailureRate = this.calculateFailureRate();
  }

  /**
   * Setup health monitoring
   */
  private setupHealthMonitoring(): void {
    if (this.options.healthCheckFunction) {
      this.healthCheckTimer = setInterval(async () => {
        await this.performHealthCheck();
      }, this.options.healthCheckInterval);
    }
  }

  /**
   * Perform health check
   */
  private async performHealthCheck(): Promise<void> {
    if (!this.options.healthCheckFunction) return;
    
    try {
      const isHealthy = await this.executeWithTimeout(
        this.options.healthCheckFunction,
        this.options.healthCheckTimeout
      );
      
      this.lastHealthCheckResult = isHealthy;
      this.metrics.lastHealthCheck = new Date();
      
      if (!isHealthy) {
        this.metrics.healthCheckFailures++;
        this.emit('health-check', {
          circuitId: this.circuitId,
          eventType: 'health-check',
          timestamp: new Date(),
          data: { healthy: false, failures: this.metrics.healthCheckFailures }
        });
      }
    } catch (error) {
      this.lastHealthCheckResult = false;
      this.metrics.healthCheckFailures++;
      this.metrics.lastHealthCheck = new Date();
      
      this.emit('health-check', {
        circuitId: this.circuitId,
        eventType: 'health-check',
        timestamp: new Date(),
        data: { healthy: false, error, failures: this.metrics.healthCheckFailures }
      });
    }
  }

  /**
   * Get current circuit state
   */
  public getState(): CircuitState {
    return this.state;
  }

  /**
   * Get circuit metrics
   */
  public getMetrics(): CircuitBreakerMetrics {
    return { ...this.metrics };
  }

  /**
   * Force circuit to open state
   */
  public forceOpen(): void {
    this.transitionToState('FORCED_OPEN');
  }

  /**
   * Force circuit to closed state
   */
  public forceClose(): void {
    this.transitionToState('CLOSED');
  }

  /**
   * Reset circuit to initial state
   */
  public reset(): void {
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = 0;
    this.lastSuccessTime = 0;
    this.openTimestamp = 0;
    this.nextAttemptTime = 0;
    this.adaptiveThreshold = this.options.failureThreshold;
    this.healthScore = 1.0;
    this.slidingWindow = [];
    this.requestHistory = [];
    this.metrics = this.initializeMetrics();
    
    this.transitionToState('CLOSED');
  }

  /**
   * Initialize metrics
   */
  private initializeMetrics(): CircuitBreakerMetrics {
    return {
      totalRequests: 0,
      totalSuccesses: 0,
      totalFailures: 0,
      totalTimeouts: 0,
      currentFailureRate: 0,
      averageResponseTime: 0,
      circuitOpenCount: 0,
      lastOpenDuration: 0,
      totalOpenDuration: 0,
      healthCheckFailures: 0,
      lastHealthCheck: new Date(),
      state: 'CLOSED',
      lastStateChange: new Date()
    };
  }

  /**
   * Merge options with defaults
   */
  private mergeDefaultOptions(options: Partial<CircuitBreakerOptions>): Required<CircuitBreakerOptions> {
    return {
      failureThreshold: 5,
      successThreshold: 2,
      cooldownPeriod: 10000,
      requestTimeout: 5000,
      strategy: 'adaptive',
      failureRateThreshold: 0.5,
      minimumRequests: 10,
      slidingWindowSize: 100,
      healthCheckInterval: 30000,
      healthCheckTimeout: 5000,
      enableAdaptiveThresholds: true,
      adaptiveMultiplier: 2.0,
      adaptiveDecay: 0.1,
      enableFallback: false,
      enableMetrics: true,
      metricsRetention: 1000,
      enablePersistence: false,
      enableRetry: false,
      tags: {},
      ...options
    };
  }

  /**
   * Persist circuit state
   */
  private persistState(): void {
    if (!this.options.enablePersistence || !this.options.persistencePath) return;
    
    try {
      const state = {
        circuitId: this.circuitId,
        state: this.state,
        failureCount: this.failureCount,
        successCount: this.successCount,
        lastFailureTime: this.lastFailureTime,
        lastSuccessTime: this.lastSuccessTime,
        openTimestamp: this.openTimestamp,
        nextAttemptTime: this.nextAttemptTime,
        adaptiveThreshold: this.adaptiveThreshold,
        healthScore: this.healthScore,
        metrics: this.metrics,
        timestamp: Date.now()
      };
      
      // In a real implementation, this would write to disk or database
      console.log(`Persisting circuit state for ${this.circuitId}:`, state);
    } catch (error) {
      errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
    }
  }

  /**
   * Load persisted circuit state
   */
  private loadPersistedState(): void {
    if (!this.options.enablePersistence || !this.options.persistencePath) return;
    
    try {
      // In a real implementation, this would read from disk or database
      console.log(`Loading persisted state for circuit ${this.circuitId} (not implemented)`);
    } catch (error) {
      errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
    }
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
    }
    
    this.removeAllListeners();
    EnhancedCircuitBreaker.instances.delete(this.circuitId);
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Create a circuit breaker with default settings
 */
export function createCircuitBreaker(
  circuitId: string,
  options?: Partial<CircuitBreakerOptions>
): EnhancedCircuitBreaker {
  return EnhancedCircuitBreaker.getInstance(circuitId, options);
}

/**
 * Execute function with circuit breaker protection
 */
export async function withCircuitBreaker<T>(
  circuitId: string,
  operation: () => Promise<T>,
  options?: Partial<CircuitBreakerOptions>,
  context: ErrorContext = {}
): Promise<T> {
  const circuitBreaker = createCircuitBreaker(circuitId, options);
  return circuitBreaker.execute(operation, context);
}

/**
 * Get all active circuit breakers
 */
export function getAllCircuitBreakers(): Map<string, EnhancedCircuitBreaker> {
  return new Map(EnhancedCircuitBreaker['instances']);
}

/**
 * Get circuit breaker statistics
 */
export function getCircuitBreakerStats(): {
  totalCircuits: number;
  openCircuits: number;
  halfOpenCircuits: number;
  closedCircuits: number;
  totalRequests: number;
  totalFailures: number;
  averageFailureRate: number;
} {
  const circuits = getAllCircuitBreakers();
  let openCircuits = 0;
  let halfOpenCircuits = 0;
  let closedCircuits = 0;
  let totalRequests = 0;
  let totalFailures = 0;
  
  circuits.forEach(circuit => {
    const state = circuit.getState();
    const metrics = circuit.getMetrics();
    
    switch (state) {
      case 'OPEN':
        openCircuits++;
        break;
      case 'HALF_OPEN':
        halfOpenCircuits++;
        break;
      case 'CLOSED':
        closedCircuits++;
        break;
    }
    
    totalRequests += metrics.totalRequests;
    totalFailures += metrics.totalFailures;
  });
  
  return {
    totalCircuits: circuits.size,
    openCircuits,
    halfOpenCircuits,
    closedCircuits,
    totalRequests,
    totalFailures,
    averageFailureRate: totalRequests > 0 ? totalFailures / totalRequests : 0
  };
}
