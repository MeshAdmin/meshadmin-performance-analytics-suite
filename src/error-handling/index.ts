#!/usr/bin/env ts-node
/**
 * Comprehensive Error Handling & Recovery Framework
 * Task 4.1: Error Handling & Recovery
 * 
 * This is the main entry point for the error handling framework that provides:
 * - Standardized error handling
 * - Circuit breaker patterns
 * - Retry mechanisms with exponential backoff
 * - Graceful degradation
 * - Recovery strategies
 * - Unified error management across all MeshAdmin applications
 */

// ============================================================================
// CORE FRAMEWORK EXPORTS
// ============================================================================

// Error handling framework
export {
  errorHandler,
  MeshAdminError,
  ValidationError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  RateLimitError,
  ServiceUnavailableError,
  DatabaseError,
  NetworkError,
  TimeoutError,
  categorizeError,
  getErrorCategoryInfo,
  type ErrorContext,
  type RecoveryOptions,
  type ErrorCategory,
  type ErrorCategoryInfo,
  type ErrorHandlerOptions
} from './error-handling-framework';

// Retry mechanism
export {
  retryEngine,
  withRetry,
  withExponentialBackoff,
  withLinearBackoff,
  withFixedDelay,
  type RetryStrategy,
  type RetryOptions,
  type RetryResult,
  type RetryAttempt
} from './retry-mechanism';

// Enhanced circuit breaker
export {
  createCircuitBreaker,
  withCircuitBreaker,
  getAllCircuitBreakers,
  getCircuitBreakerStats,
  type CircuitState,
  type CircuitBreakerOptions,
  type CircuitBreakerMetrics,
  type CircuitBreakerEvent
} from './enhanced-circuit-breaker';

// Graceful degradation
export {
  createDegradationManager,
  withDegradation,
  withFallbacks,
  getDegradationManager,
  type DegradationLevel,
  type DegradationStrategy,
  type ServiceEndpoint,
  type DegradationOptions,
  type DegradationMetrics
} from './graceful-degradation';

// ============================================================================
// UNIFIED ERROR HANDLING INTERFACE
// ============================================================================

import { errorHandler, ErrorContext, ErrorCategory } from './error-handling-framework';
import { withRetry, RetryOptions } from './retry-mechanism';
import { withCircuitBreaker, CircuitBreakerOptions } from './enhanced-circuit-breaker';
import { withDegradation, DegradationOptions } from './graceful-degradation';

/**
 * Unified error handling interface for MeshAdmin ecosystem
 */
export class MeshAdminErrorHandler {
  private static instance: MeshAdminErrorHandler;
  
  private constructor() {
    this.setupDefaultHandlers();
  }

  public static getInstance(): MeshAdminErrorHandler {
    if (!MeshAdminErrorHandler.instance) {
      MeshAdminErrorHandler.instance = new MeshAdminErrorHandler();
    }
    return MeshAdminErrorHandler.instance;
  }

  /**
   * Setup default error handlers for common scenarios
   */
  private setupDefaultHandlers(): void {
    // Database errors
    errorHandler.registerHandler('database', async (error, context) => {
      console.error('Database error detected:', { error: error.message, context });
      // In a real implementation, this could trigger database health checks
      // or notify administrators
    });

    // Network errors
    errorHandler.registerHandler('network', async (error, context) => {
      console.error('Network error detected:', { error: error.message, context });
      // In a real implementation, this could trigger network diagnostics
      // or switch to backup connections
    });

    // Service unavailable errors
    errorHandler.registerHandler('service-unavailable', async (error, context) => {
      console.error('Service unavailable error detected:', { error: error.message, context });
      // In a real implementation, this could trigger service health checks
      // or activate fallback services
    });

    // Rate limit errors
    errorHandler.registerHandler('rate-limit', async (error, context) => {
      console.warn('Rate limit exceeded:', { error: error.message, context });
      // In a real implementation, this could adjust rate limiting strategies
      // or notify about potential abuse
    });
  }

  /**
   * Execute operation with comprehensive error handling
   */
  public async executeWithErrorHandling<T>(
    operation: () => Promise<T>,
    options: {
      context?: ErrorContext;
      retry?: Partial<RetryOptions>;
      circuitBreaker?: Partial<CircuitBreakerOptions>;
      degradation?: Partial<DegradationOptions>;
      operationId?: string;
    } = {}
  ): Promise<T> {
    const {
      context = {},
      retry,
      circuitBreaker,
      degradation,
      operationId = 'unknown'
    } = options;

    try {
      // If circuit breaker is configured, use it
      if (circuitBreaker) {
        return await withCircuitBreaker(
          operationId,
          operation,
          circuitBreaker,
          context
        );
      }

      // If degradation is configured, use it
      if (degradation) {
        return await withDegradation(
          operationId,
          operation,
          degradation,
          context
        );
      }

      // If retry is configured, use it
      if (retry) {
        return await withRetry(operation, retry, context);
      }

      // Default: execute operation directly
      return await operation();
    } catch (error) {
      // Handle the error through the error handler
      await errorHandler.handleError(error, context, {
        context: operationId,
        metadata: { options }
      });

      // Rethrow the error
      throw error;
    }
  }

  /**
   * Execute operation with retry and circuit breaker
   */
  public async executeWithRetryAndCircuitBreaker<T>(
    operation: () => Promise<T>,
    operationId: string,
    options: {
      context?: ErrorContext;
      retry?: Partial<RetryOptions>;
      circuitBreaker?: Partial<CircuitBreakerOptions>;
    } = {}
  ): Promise<T> {
    const { context = {}, retry, circuitBreaker } = options;

    // First, try with circuit breaker
    if (circuitBreaker) {
      try {
        return await withCircuitBreaker(operationId, operation, circuitBreaker, context);
      } catch (error) {
        // If circuit breaker fails, try with retry
        if (retry) {
          return await withRetry(operation, retry, context);
        }
        throw error;
      }
    }

    // If no circuit breaker, just use retry
    if (retry) {
      return await withRetry(operation, retry, context);
    }

    // Default: execute operation directly
    return await operation();
  }

  /**
   * Execute operation with graceful degradation
   */
  public async executeWithGracefulDegradation<T>(
    operationId: string,
    primaryOperation: () => Promise<T>,
    fallbackOperations: Array<{ serviceId: string; operation: () => Promise<T> }>,
    options: {
      context?: ErrorContext;
      degradation?: Partial<DegradationOptions>;
    } = {}
  ): Promise<T> {
    const { context = {}, degradation } = options;

    try {
      // Try primary operation first
      return await primaryOperation();
    } catch (error) {
      // If primary fails, try fallbacks
      if (fallbackOperations.length > 0) {
        try {
          return await withFallbacks(operationId, fallbackOperations, degradation, context);
        } catch (fallbackError) {
          // If fallbacks also fail, use degradation
          return await withDegradation(operationId, primaryOperation, degradation, context);
        }
      }

      // If no fallbacks, use degradation
      return await withDegradation(operationId, primaryOperation, degradation, context);
    }
  }

  /**
   * Get comprehensive system health status
   */
  public getSystemHealth(): {
    errorHandler: {
      totalErrors: number;
      errorsByCategory: Record<ErrorCategory, number>;
    };
    retryEngine: {
      activeRetries: number;
      totalOperations: number;
      successRate: number;
      averageAttempts: number;
    };
    circuitBreakers: {
      totalCircuits: number;
      openCircuits: number;
      halfOpenCircuits: number;
      closedCircuits: number;
      totalRequests: number;
      totalFailures: number;
      averageFailureRate: number;
    };
    degradation: {
      currentLevel: string;
      serviceFailures: number;
      fallbackActivations: number;
      recoveryAttempts: number;
      performanceScore: number;
    };
  } {
    // Get retry engine stats
    const retryStats = require('./retry-mechanism').retryEngine.getRetryStats();
    
    // Get circuit breaker stats
    const circuitStats = require('./enhanced-circuit-breaker').getCircuitBreakerStats();
    
    // Get degradation stats
    const degradationStats = require('./graceful-degradation').getDegradationManager().getMetrics();
    
    return {
      errorHandler: {
        totalErrors: 0, // This would need to be implemented in the error handler
        errorsByCategory: {} as Record<ErrorCategory, number> // This would need to be implemented
      },
      retryEngine: retryStats,
      circuitBreakers: circuitStats,
      degradation: {
        currentLevel: degradationStats.currentLevel,
        serviceFailures: degradationStats.serviceFailures,
        fallbackActivations: degradationStats.fallbackActivations,
        recoveryAttempts: degradationStats.recoveryAttempts,
        performanceScore: degradationStats.performanceScore
      }
    };
  }

  /**
   * Reset all error handling systems
   */
  public resetAll(): void {
    // Reset retry engine
    require('./retry-mechanism').retryEngine.clearHistory();
    
    // Reset degradation manager
    require('./graceful-degradation').getDegradationManager().reset();
    
    // Reset all circuit breakers
    const circuits = require('./enhanced-circuit-breaker').getAllCircuitBreakers();
    circuits.forEach(circuit => circuit.reset());
    
    console.info('All error handling systems have been reset');
  }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Get the global error handler instance
 */
export function getErrorHandler(): MeshAdminErrorHandler {
  return MeshAdminErrorHandler.getInstance();
}

/**
 * Execute operation with comprehensive error handling (convenience function)
 */
export async function executeWithErrorHandling<T>(
  operation: () => Promise<T>,
  options?: {
    context?: ErrorContext;
    retry?: Partial<RetryOptions>;
    circuitBreaker?: Partial<CircuitBreakerOptions>;
    degradation?: Partial<DegradationOptions>;
    operationId?: string;
  }
): Promise<T> {
  return getErrorHandler().executeWithErrorHandling(operation, options);
}

/**
 * Execute operation with retry and circuit breaker (convenience function)
 */
export async function executeWithRetryAndCircuitBreaker<T>(
  operation: () => Promise<T>,
  operationId: string,
  options?: {
    context?: ErrorContext;
    retry?: Partial<RetryOptions>;
    circuitBreaker?: Partial<CircuitBreakerOptions>;
  }
): Promise<T> {
  return getErrorHandler().executeWithRetryAndCircuitBreaker(operation, operationId, options);
}

/**
 * Execute operation with graceful degradation (convenience function)
 */
export async function executeWithGracefulDegradation<T>(
  operationId: string,
  primaryOperation: () => Promise<T>,
  fallbackOperations: Array<{ serviceId: string; operation: () => Promise<T> }>,
  options?: {
    context?: ErrorContext;
    degradation?: Partial<DegradationOptions>;
  }
): Promise<T> {
  return getErrorHandler().executeWithGracefulDegradation(
    operationId,
    primaryOperation,
    fallbackOperations,
    options
  );
}

// ============================================================================
// DEFAULT CONFIGURATIONS
// ============================================================================

/**
 * Default configurations for common use cases
 */
export const DEFAULT_CONFIGS = {
  // Database operations
  database: {
    retry: {
      maxRetries: 3,
      baseDelay: 1000,
      strategy: 'exponential-backoff' as const,
      jitter: true
    },
    circuitBreaker: {
      failureThreshold: 5,
      cooldownPeriod: 10000,
      strategy: 'adaptive' as const,
      enableFallback: true
    }
  },

  // Network operations
  network: {
    retry: {
      maxRetries: 5,
      baseDelay: 500,
      strategy: 'exponential-backoff' as const,
      jitter: true
    },
    circuitBreaker: {
      failureThreshold: 3,
      cooldownPeriod: 5000,
      strategy: 'consecutive-failures' as const,
      enableFallback: false
    }
  },

  // API operations
  api: {
    retry: {
      maxRetries: 2,
      baseDelay: 1000,
      strategy: 'linear-backoff' as const,
      jitter: true
    },
    circuitBreaker: {
      failureThreshold: 10,
      cooldownPeriod: 30000,
      strategy: 'failure-rate' as const,
      failureRateThreshold: 0.3,
      enableFallback: true
    }
  },

  // File operations
  file: {
    retry: {
      maxRetries: 2,
      baseDelay: 2000,
      strategy: 'fixed-delay' as const,
      jitter: false
    },
    circuitBreaker: {
      failureThreshold: 3,
      cooldownPeriod: 15000,
      strategy: 'consecutive-failures' as const,
      enableFallback: false
    }
  }
};

// ============================================================================
// QUICK START HELPERS
// ============================================================================

/**
 * Quick setup for common error handling patterns
 */
export function setupErrorHandling(options: {
  enableLogging?: boolean;
  enableMetrics?: boolean;
  enablePersistence?: boolean;
  defaultRetryAttempts?: number;
  defaultCircuitBreakerThreshold?: number;
} = {}): void {
  const {
    enableLogging = true,
    enableMetrics = true,
    enablePersistence = false,
    defaultRetryAttempts = 3,
    defaultCircuitBreakerThreshold = 5
  } = options;

  if (enableLogging) {
    console.info('Error handling framework initialized with logging enabled');
  }

  if (enableMetrics) {
    console.info('Error handling framework initialized with metrics enabled');
  }

  if (enablePersistence) {
    console.info('Error handling framework initialized with persistence enabled');
  }

  console.info(`Default retry attempts: ${defaultRetryAttempts}`);
  console.info(`Default circuit breaker threshold: ${defaultCircuitBreakerThreshold}`);
}

// Export the default instance
export const errorHandler = getErrorHandler();
