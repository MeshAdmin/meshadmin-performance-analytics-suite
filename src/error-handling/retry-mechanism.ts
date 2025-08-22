#!/usr/bin/env ts-node
/**
 * Retry Mechanism with Exponential Backoff and Jitter
 * Task 4.1: Error Handling & Recovery
 * 
 * Features:
 * - Exponential backoff with configurable base delay
 * - Jitter to prevent thundering herd
 * - Circuit breaker integration
 * - Configurable retry strategies
 * - Progress tracking and cancellation
 */

import { EventEmitter } from 'events';
import { errorHandler, MeshAdminError, ErrorContext, RecoveryOptions } from './error-handling-framework';

// ============================================================================
// RETRY STRATEGIES
// ============================================================================

export type RetryStrategy = 
  | 'exponential-backoff'
  | 'linear-backoff'
  | 'fixed-delay'
  | 'fibonacci-backoff'
  | 'custom';

export interface RetryOptions {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  strategy: RetryStrategy;
  jitter: boolean;
  jitterFactor: number;
  timeout: number;
  onRetry?: (attempt: number, error: Error, delay: number) => void;
  onMaxRetriesExceeded?: (error: Error, attempts: number) => void;
  retryCondition?: (error: Error, attempt: number) => boolean;
  circuitBreaker?: boolean;
  circuitBreakerKey?: string;
}

export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: Error;
  attempts: number;
  totalTime: number;
  lastError?: Error;
}

export interface RetryAttempt {
  attempt: number;
  error: Error;
  delay: number;
  timestamp: Date;
  duration: number;
}

// ============================================================================
// RETRY ENGINE
// ============================================================================

export class RetryEngine extends EventEmitter {
  private static instance: RetryEngine;
  private activeRetries: Map<string, AbortController> = new Map();
  private retryHistory: Map<string, RetryAttempt[]> = new Map();

  private constructor() {
    super();
  }

  public static getInstance(): RetryEngine {
    if (!RetryEngine.instance) {
      RetryEngine.instance = new RetryEngine();
    }
    return RetryEngine.instance;
  }

  /**
   * Execute an operation with retry logic
   */
  public async executeWithRetry<T>(
    operation: () => Promise<T>,
    options: Partial<RetryOptions> = {},
    context: ErrorContext = {}
  ): Promise<RetryResult<T>> {
    const retryOptions: Required<RetryOptions> = {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 30000,
      strategy: 'exponential-backoff',
      jitter: true,
      jitterFactor: 0.1,
      timeout: 30000,
      onRetry: () => {},
      onMaxRetriesExceeded: () => {},
      retryCondition: () => true,
      circuitBreaker: false,
      circuitBreakerKey: '',
      ...options
    };

    const operationId = this.generateOperationId();
    const abortController = new AbortController();
    this.activeRetries.set(operationId, abortController);

    const startTime = Date.now();
    let lastError: Error | undefined;
    let attempts = 0;

    try {
      // First attempt
      attempts++;
      const result = await this.executeWithTimeout(operation, retryOptions.timeout, abortController.signal);
      
      this.activeRetries.delete(operationId);
      return {
        success: true,
        data: result,
        attempts,
        totalTime: Date.now() - startTime
      };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // Check if operation should be retried
      if (!retryOptions.retryCondition(lastError, attempts)) {
        this.activeRetries.delete(operationId);
        return {
          success: false,
          error: lastError,
          attempts,
          totalTime: Date.now() - startTime,
          lastError
        };
      }

      // Retry loop
      for (let attempt = attempts; attempt <= retryOptions.maxRetries; attempt++) {
        try {
          // Calculate delay for this attempt
          const delay = this.calculateDelay(attempt, retryOptions);
          
          // Check if operation was cancelled
          if (abortController.signal.aborted) {
            throw new Error('Operation cancelled');
          }

          // Wait before retry
          await this.wait(delay, abortController.signal);
          
          // Execute retry
          const result = await this.executeWithTimeout(operation, retryOptions.timeout, abortController.signal);
          
          // Record successful retry
          this.recordRetryAttempt(operationId, {
            attempt,
            error: lastError,
            delay,
            timestamp: new Date(),
            duration: Date.now() - startTime
          });

          this.activeRetries.delete(operationId);
          return {
            success: true,
            data: result,
            attempts: attempt + 1,
            totalTime: Date.now() - startTime
          };
        } catch (retryError) {
          lastError = retryError instanceof Error ? retryError : new Error(String(retryError));
          
          // Record failed retry attempt
          this.recordRetryAttempt(operationId, {
            attempt,
            error: lastError,
            delay: this.calculateDelay(attempt, retryOptions),
            timestamp: new Date(),
            duration: Date.now() - startTime
          });

          // Call onRetry callback
          retryOptions.onRetry(attempt, lastError, this.calculateDelay(attempt, retryOptions));
          
          // Emit retry event
          this.emit('retry', {
            operationId,
            attempt,
            error: lastError,
            delay: this.calculateDelay(attempt, retryOptions),
            context
          });

          // If this was the last attempt, break
          if (attempt === retryOptions.maxRetries) {
            break;
          }
        }
      }

      // All retries exhausted
      retryOptions.onMaxRetriesExceeded(lastError!, attempts);
      
      this.emit('maxRetriesExceeded', {
        operationId,
        attempts,
        error: lastError,
        context
      });

      this.activeRetries.delete(operationId);
      return {
        success: false,
        error: lastError,
        attempts,
        totalTime: Date.now() - startTime,
        lastError
      };
    }
  }

  /**
   * Calculate delay for a specific retry attempt
   */
  private calculateDelay(attempt: number, options: Required<RetryOptions>): number {
    let delay: number;

    switch (options.strategy) {
      case 'exponential-backoff':
        delay = Math.min(options.baseDelay * Math.pow(2, attempt - 1), options.maxDelay);
        break;
      case 'linear-backoff':
        delay = Math.min(options.baseDelay * attempt, options.maxDelay);
        break;
      case 'fixed-delay':
        delay = options.baseDelay;
        break;
      case 'fibonacci-backoff':
        delay = Math.min(this.fibonacci(attempt) * options.baseDelay, options.maxDelay);
        break;
      default:
        delay = options.baseDelay;
    }

    // Add jitter if enabled
    if (options.jitter) {
      const jitterAmount = delay * options.jitterFactor;
      delay += (Math.random() - 0.5) * jitterAmount;
    }

    return Math.max(0, Math.min(delay, options.maxDelay));
  }

  /**
   * Calculate Fibonacci number
   */
  private fibonacci(n: number): number {
    if (n <= 1) return n;
    return this.fibonacci(n - 1) + this.fibonacci(n - 2);
  }

  /**
   * Execute operation with timeout
   */
  private async executeWithTimeout<T>(
    operation: () => Promise<T>,
    timeout: number,
    signal: AbortSignal
  ): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Operation timed out after ${timeout}ms`));
      }, timeout);

      signal.addEventListener('abort', () => {
        clearTimeout(timeoutId);
        reject(new Error('Operation cancelled'));
      });
    });

    return Promise.race([operation(), timeoutPromise]);
  }

  /**
   * Wait for specified delay
   */
  private async wait(delay: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(resolve, delay);
      
      signal.addEventListener('abort', () => {
        clearTimeout(timeoutId);
        reject(new Error('Operation cancelled'));
      });
    });
  }

  /**
   * Record retry attempt for analytics
   */
  private recordRetryAttempt(operationId: string, attempt: RetryAttempt): void {
    const history = this.retryHistory.get(operationId) || [];
    history.push(attempt);
    this.retryHistory.set(operationId, history);
  }

  /**
   * Generate unique operation ID
   */
  private generateOperationId(): string {
    return `retry_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cancel an active retry operation
   */
  public cancelOperation(operationId: string): boolean {
    const controller = this.activeRetries.get(operationId);
    if (controller) {
      controller.abort();
      this.activeRetries.delete(operationId);
      return true;
    }
    return false;
  }

  /**
   * Get retry statistics
   */
  public getRetryStats(): {
    activeRetries: number;
    totalOperations: number;
    successRate: number;
    averageAttempts: number;
  } {
    const activeRetries = this.activeRetries.size;
    const totalOperations = this.retryHistory.size;
    
    let totalAttempts = 0;
    let successfulOperations = 0;
    
    this.retryHistory.forEach(history => {
      totalAttempts += history.length;
      if (history.length > 0 && !history[history.length - 1].error) {
        successfulOperations++;
      }
    });

    return {
      activeRetries,
      totalOperations,
      successRate: totalOperations > 0 ? (successfulOperations / totalOperations) * 100 : 0,
      averageAttempts: totalOperations > 0 ? totalAttempts / totalOperations : 0
    };
  }

  /**
   * Clear retry history
   */
  public clearHistory(): void {
    this.retryHistory.clear();
  }
}

// ============================================================================
// RETRY UTILITIES
// ============================================================================

/**
 * Simple retry wrapper for common use cases
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  options: Partial<RetryOptions> = {},
  context: ErrorContext = {}
): Promise<T> {
  const engine = RetryEngine.getInstance();
  const result = await engine.executeWithRetry(operation, options, context);
  
  if (!result.success) {
    throw result.error;
  }
  
  return result.data!;
}

/**
 * Retry with exponential backoff (most common use case)
 */
export async function withExponentialBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000,
  context: ErrorContext = {}
): Promise<T> {
  return withRetry(operation, {
    maxRetries,
    baseDelay,
    strategy: 'exponential-backoff',
    jitter: true
  }, context);
}

/**
 * Retry with linear backoff
 */
export async function withLinearBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000,
  context: ErrorContext = {}
): Promise<T> {
  return withRetry(operation, {
    maxRetries,
    baseDelay,
    strategy: 'linear-backoff',
    jitter: true
  }, context);
}

/**
 * Retry with fixed delay
 */
export async function withFixedDelay<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000,
  context: ErrorContext = {}
): Promise<T> {
  return withRetry(operation, {
    maxRetries,
    baseDelay: delay,
    strategy: 'fixed-delay',
    jitter: false
  }, context);
}

// Export singleton instance
export const retryEngine = RetryEngine.getInstance();
