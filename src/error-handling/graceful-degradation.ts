#!/usr/bin/env ts-node
/**
 * Graceful Degradation System
 * Task 4.1: Error Handling & Recovery
 * 
 * Features:
 * - Service degradation strategies
 * - Fallback service chains
 * - Quality of service management
 * - Automatic service recovery
 * - Performance monitoring during degradation
 */

import { EventEmitter } from 'events';
import { errorHandler, MeshAdminError, ErrorContext, ErrorCategory } from './error-handling-framework';
import { createCircuitBreaker, CircuitBreakerOptions } from './enhanced-circuit-breaker';
import { withRetry, RetryOptions } from './retry-mechanism';

// ============================================================================
// DEGRADATION STRATEGIES
// ============================================================================

export type DegradationLevel = 'full' | 'degraded' | 'minimal' | 'offline';

export type DegradationStrategy = 
  | 'failover'           // Switch to backup service
  | 'cascade'            // Try services in priority order
  | 'parallel'           // Try multiple services simultaneously
  | 'adaptive'           // Dynamically adjust based on performance
  | 'graceful'           // Gradually reduce functionality
  | 'hybrid';            // Combine multiple strategies

export interface ServiceEndpoint {
  id: string;
  name: string;
  url: string;
  priority: number;
  healthCheck: () => Promise<boolean>;
  timeout: number;
  circuitBreaker?: CircuitBreakerOptions;
  retryOptions?: Partial<RetryOptions>;
  fallbackData?: any;
  metadata?: Record<string, any>;
}

export interface DegradationOptions {
  strategy: DegradationStrategy;
  maxDegradationLevel: DegradationLevel;
  enableAutoRecovery: boolean;
  recoveryThreshold: number;
  recoveryCheckInterval: number;
  performanceThreshold: number;
  enableMetrics: boolean;
  fallbackChain: string[];
  timeout: number;
  retryAttempts: number;
}

export interface DegradationMetrics {
  currentLevel: DegradationLevel;
  serviceFailures: number;
  fallbackActivations: number;
  recoveryAttempts: number;
  averageResponseTime: number;
  lastDegradation: Date;
  totalDowntime: number;
  performanceScore: number;
}

// ============================================================================
// GRACEFUL DEGRADATION MANAGER
// ============================================================================

export class GracefulDegradationManager extends EventEmitter {
  private static instance: GracefulDegradationManager;
  
  private services: Map<string, ServiceEndpoint> = new Map();
  private degradationLevel: DegradationLevel = 'full';
  private options: Required<DegradationOptions>;
  private metrics: DegradationMetrics;
  private recoveryTimer?: NodeJS.Timeout;
  private performanceHistory: Array<{ timestamp: number; responseTime: number; success: boolean }> = [];

  private constructor(options: Partial<DegradationOptions> = {}) {
    super();
    
    this.options = this.mergeDefaultOptions(options);
    this.metrics = this.initializeMetrics();
    this.setupAutoRecovery();
  }

  public static getInstance(options?: Partial<DegradationOptions>): GracefulDegradationManager {
    if (!GracefulDegradationManager.instance) {
      GracefulDegradationManager.instance = new GracefulDegradationManager(options);
    }
    return GracefulDegradationManager.instance;
  }

  /**
   * Register a service endpoint
   */
  public registerService(service: ServiceEndpoint): void {
    this.services.set(service.id, service);
    
    // Create circuit breaker for the service if specified
    if (service.circuitBreaker) {
      createCircuitBreaker(service.id, service.circuitBreaker);
    }
    
    this.emit('service-registered', { serviceId: service.id, service });
  }

  /**
   * Execute operation with graceful degradation
   */
  public async executeWithDegradation<T>(
    operationId: string,
    primaryOperation: () => Promise<T>,
    context: ErrorContext = {}
  ): Promise<T> {
    const startTime = Date.now();
    
    try {
      // Try primary operation first
      const result = await this.executeWithTimeout(primaryOperation, this.options.timeout);
      
      // Record success
      this.recordPerformance(Date.now() - startTime, true);
      
      // If we were degraded, check if we can recover
      if (this.degradationLevel !== 'full') {
        this.attemptRecovery();
      }
      
      return result;
    } catch (error) {
      // Record failure
      this.recordPerformance(Date.now() - startTime, false);
      
      // Attempt degradation
      return this.attemptDegradation(operationId, context);
    }
  }

  /**
   * Execute operation with multiple service fallbacks
   */
  public async executeWithFallbacks<T>(
    operationId: string,
    operations: Array<{ serviceId: string; operation: () => Promise<T> }>,
    context: ErrorContext = {}
  ): Promise<T> {
    const startTime = Date.now();
    let lastError: Error | undefined;
    
    // Try operations in order
    for (const { serviceId, operation } of operations) {
      try {
        const result = await this.executeWithTimeout(operation, this.options.timeout);
        
        // Record success
        this.recordPerformance(Date.now() - startTime, true);
        
        // If we were degraded, check if we can recover
        if (this.degradationLevel !== 'full') {
          this.attemptRecovery();
        }
        
        return result;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        // Record failure
        this.recordPerformance(Date.now() - startTime, false);
        
        // Log service failure
        console.warn(`Service ${serviceId} failed for operation ${operationId}:`, error);
        
        // Continue to next service
        continue;
      }
    }
    
    // All services failed, attempt degradation
    return this.attemptDegradation(operationId, context);
  }

  /**
   * Attempt service degradation
   */
  private async attemptDegradation<T>(operationId: string, context: ErrorContext): Promise<T> {
    this.metrics.serviceFailures++;
    
    // Determine degradation level
    const newLevel = this.calculateDegradationLevel();
    if (newLevel !== this.degradationLevel) {
      this.setDegradationLevel(newLevel);
    }
    
    // Try fallback strategies based on degradation level
    switch (this.degradationLevel) {
      case 'degraded':
        return this.executeDegradedOperation<T>(operationId, context);
      
      case 'minimal':
        return this.executeMinimalOperation<T>(operationId, context);
      
      case 'offline':
        return this.executeOfflineOperation<T>(operationId, context);
      
      default:
        throw new MeshAdminError(
          `All services failed for operation ${operationId}`,
          'SERVICE_DEGRADATION_ERROR',
          503,
          context,
          { retryable: true, circuitBreaker: true }
        );
    }
  }

  /**
   * Execute operation in degraded mode
   */
  private async executeDegradedOperation<T>(operationId: string, context: ErrorContext): Promise<T> {
    this.metrics.fallbackActivations++;
    
    // Try to use cached or fallback data
    const fallbackData = this.getFallbackData(operationId);
    if (fallbackData) {
      return fallbackData as T;
    }
    
    // Try alternative services with reduced functionality
    const alternativeServices = this.getAlternativeServices(operationId);
    if (alternativeServices.length > 0) {
      try {
        return await this.executeWithFallbacks(operationId, alternativeServices, context);
      } catch (error) {
        // Continue to minimal mode
      }
    }
    
    // Fall back to minimal mode
    return this.executeMinimalOperation<T>(operationId, context);
  }

  /**
   * Execute operation in minimal mode
   */
  private async executeMinimalOperation<T>(operationId: string, context: ErrorContext): Promise<T> {
    // Return minimal functionality or cached data
    const minimalData = this.getMinimalData(operationId);
    if (minimalData) {
      return minimalData as T;
    }
    
    // Try offline mode
    return this.executeOfflineOperation<T>(operationId, context);
  }

  /**
   * Execute operation in offline mode
   */
  private async executeOfflineOperation<T>(operationId: string, context: ErrorContext): Promise<T> {
    // Return offline/static data
    const offlineData = this.getOfflineData(operationId);
    if (offlineData) {
      return offlineData as T;
    }
    
    // If no offline data available, throw error
    throw new MeshAdminError(
      `Service completely unavailable for operation ${operationId}`,
      'SERVICE_OFFLINE_ERROR',
      503,
      context,
      { retryable: false, circuitBreaker: true }
    );
  }

  /**
   * Calculate appropriate degradation level
   */
  private calculateDegradationLevel(): DegradationLevel {
    const failureRate = this.metrics.serviceFailures / Math.max(this.metrics.serviceFailures + this.metrics.fallbackActivations, 1);
    const performanceScore = this.metrics.performanceScore;
    
    if (failureRate > 0.8 || performanceScore < 0.2) {
      return 'offline';
    } else if (failureRate > 0.5 || performanceScore < 0.5) {
      return 'minimal';
    } else if (failureRate > 0.2 || performanceScore < 0.8) {
      return 'degraded';
    } else {
      return 'full';
    }
  }

  /**
   * Set degradation level
   */
  private setDegradationLevel(level: DegradationLevel): void {
    const oldLevel = this.degradationLevel;
    this.degradationLevel = level;
    this.metrics.currentLevel = level;
    this.metrics.lastDegradation = new Date();
    
    this.emit('degradation-level-changed', {
      oldLevel,
      newLevel: level,
      timestamp: new Date(),
      reason: this.getDegradationReason(level)
    });
    
    console.warn(`Service degradation level changed from ${oldLevel} to ${level}`);
  }

  /**
   * Get reason for degradation level
   */
  private getDegradationReason(level: DegradationLevel): string {
    switch (level) {
      case 'degraded':
        return 'Service performance degraded, using fallbacks';
      case 'minimal':
        return 'Multiple services failed, providing minimal functionality';
      case 'offline':
        return 'All services unavailable, providing offline functionality';
      default:
        return 'Services operating normally';
    }
  }

  /**
   * Attempt service recovery
   */
  private attemptRecovery(): void {
    if (!this.options.enableAutoRecovery) return;
    
    this.metrics.recoveryAttempts++;
    
    // Check if recovery conditions are met
    if (this.canRecover()) {
      this.setDegradationLevel('full');
      console.info('Service recovery successful, returning to full functionality');
    }
  }

  /**
   * Check if service can recover
   */
  private canRecover(): boolean {
    const recentFailures = this.performanceHistory
      .filter(h => h.timestamp > Date.now() - this.options.recoveryThreshold)
      .filter(h => !h.success).length;
    
    const recentSuccesses = this.performanceHistory
      .filter(h => h.timestamp > Date.now() - this.options.recoveryThreshold)
      .filter(h => h.success).length;
    
    const totalRecent = recentFailures + recentSuccesses;
    
    if (totalRecent < 5) return false; // Need minimum sample size
    
    const successRate = recentSuccesses / totalRecent;
    return successRate > 0.8; // 80% success rate required for recovery
  }

  /**
   * Setup auto-recovery timer
   */
  private setupAutoRecovery(): void {
    if (this.options.enableAutoRecovery) {
      this.recoveryTimer = setInterval(() => {
        this.attemptRecovery();
      }, this.options.recoveryCheckInterval);
    }
  }

  /**
   * Record performance metrics
   */
  private recordPerformance(responseTime: number, success: boolean): void {
    const timestamp = Date.now();
    
    this.performanceHistory.push({ timestamp, responseTime, success });
    
    // Keep only recent history
    const cutoff = timestamp - this.options.recoveryThreshold;
    this.performanceHistory = this.performanceHistory.filter(h => h.timestamp > cutoff);
    
    // Update metrics
    this.metrics.averageResponseTime = this.performanceHistory.reduce((sum, h) => sum + h.responseTime, 0) / this.performanceHistory.length;
    
    // Calculate performance score (0-1, higher is better)
    const recentHistory = this.performanceHistory.filter(h => h.timestamp > timestamp - 60000); // Last minute
    if (recentHistory.length > 0) {
      const successRate = recentHistory.filter(h => h.success).length / recentHistory.length;
      const avgResponseTime = recentHistory.reduce((sum, h) => sum + h.responseTime, 0) / recentHistory.length;
      const responseTimeScore = Math.max(0, 1 - (avgResponseTime / 10000)); // Normalize to 10s max
      this.metrics.performanceScore = (successRate + responseTimeScore) / 2;
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
   * Get fallback data for operation
   */
  private getFallbackData(operationId: string): any {
    // In a real implementation, this would retrieve cached or fallback data
    // For now, return null to indicate no fallback data available
    return null;
  }

  /**
   * Get alternative services for operation
   */
  private getAlternativeServices(operationId: string): Array<{ serviceId: string; operation: () => Promise<any> }> {
    // In a real implementation, this would return alternative service implementations
    // For now, return empty array
    return [];
  }

  /**
   * Get minimal data for operation
   */
  private getMinimalData(operationId: string): any {
    // In a real implementation, this would return minimal functionality data
    // For now, return null to indicate no minimal data available
    return null;
  }

  /**
   * Get offline data for operation
   */
  private getOfflineData(operationId: string): any {
    // In a real implementation, this would return offline/static data
    // For now, return null to indicate no offline data available
    return null;
  }

  /**
   * Get current degradation level
   */
  public getDegradationLevel(): DegradationLevel {
    return this.degradationLevel;
  }

  /**
   * Get degradation metrics
   */
  public getMetrics(): DegradationMetrics {
    return { ...this.metrics };
  }

  /**
   * Force degradation level
   */
  public forceDegradationLevel(level: DegradationLevel): void {
    this.setDegradationLevel(level);
  }

  /**
   * Reset degradation manager
   */
  public reset(): void {
    this.degradationLevel = 'full';
    this.metrics = this.initializeMetrics();
    this.performanceHistory = [];
    
    this.emit('reset', { timestamp: new Date() });
  }

  /**
   * Initialize metrics
   */
  private initializeMetrics(): DegradationMetrics {
    return {
      currentLevel: 'full',
      serviceFailures: 0,
      fallbackActivations: 0,
      recoveryAttempts: 0,
      averageResponseTime: 0,
      lastDegradation: new Date(),
      totalDowntime: 0,
      performanceScore: 1.0
    };
  }

  /**
   * Merge options with defaults
   */
  private mergeDefaultOptions(options: Partial<DegradationOptions>): Required<DegradationOptions> {
    return {
      strategy: 'cascade',
      maxDegradationLevel: 'minimal',
      enableAutoRecovery: true,
      recoveryThreshold: 60000, // 1 minute
      recoveryCheckInterval: 30000, // 30 seconds
      performanceThreshold: 0.5,
      enableMetrics: true,
      fallbackChain: [],
      timeout: 10000,
      retryAttempts: 3,
      ...options
    };
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    if (this.recoveryTimer) {
      clearInterval(this.recoveryTimer);
    }
    
    this.removeAllListeners();
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Create degradation manager with default settings
 */
export function createDegradationManager(options?: Partial<DegradationOptions>): GracefulDegradationManager {
  return GracefulDegradationManager.getInstance(options);
}

/**
 * Execute operation with graceful degradation
 */
export async function withDegradation<T>(
  operationId: string,
  primaryOperation: () => Promise<T>,
  options?: Partial<DegradationOptions>,
  context: ErrorContext = {}
): Promise<T> {
  const manager = createDegradationManager(options);
  return manager.executeWithDegradation(operationId, primaryOperation, context);
}

/**
 * Execute operation with multiple fallback services
 */
export async function withFallbacks<T>(
  operationId: string,
  operations: Array<{ serviceId: string; operation: () => Promise<T> }>,
  options?: Partial<DegradationOptions>,
  context: ErrorContext = {}
): Promise<T> {
  const manager = createDegradationManager(options);
  return manager.executeWithFallbacks(operationId, operations, context);
}

/**
 * Get global degradation manager instance
 */
export function getDegradationManager(): GracefulDegradationManager {
  return GracefulDegradationManager.getInstance();
}
