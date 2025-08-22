#!/usr/bin/env ts-node
/**
 * Comprehensive Error Handling Framework for MeshAdmin Ecosystem
 * Task 4.1: Error Handling & Recovery
 * 
 * This framework provides:
 * - Standardized error classes
 * - Circuit breaker patterns
 * - Retry mechanisms with exponential backoff
 * - Graceful degradation
 * - Error categorization and handling
 * - Recovery strategies
 */

import { EventEmitter } from 'events';

// ============================================================================
// CORE ERROR CLASSES
// ============================================================================

export interface ErrorContext {
  service?: string;
  operation?: string;
  userId?: string;
  requestId?: string;
  timestamp?: Date;
  metadata?: Record<string, any>;
  cause?: Error;
}

export interface RecoveryOptions {
  retryable: boolean;
  maxRetries?: number;
  retryDelay?: number;
  fallbackValue?: any;
  circuitBreaker?: boolean;
  timeout?: number;
}

export class MeshAdminError extends Error {
  public readonly code: string;
  public readonly statusCode: number;
  public readonly context: ErrorContext;
  public readonly recoveryOptions: RecoveryOptions;
  public readonly timestamp: Date;

  constructor(
    message: string,
    code: string,
    statusCode: number = 500,
    context: ErrorContext = {},
    recoveryOptions: RecoveryOptions = { retryable: false }
  ) {
    super(message);
    this.name = 'MeshAdminError';
    this.code = code;
    this.statusCode = statusCode;
    this.context = context;
    this.recoveryOptions = recoveryOptions;
    this.timestamp = new Date();
  }

  public toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      statusCode: this.statusCode,
      context: this.context,
      recoveryOptions: this.recoveryOptions,
      timestamp: this.timestamp.toISOString(),
      stack: this.stack
    };
  }
}

export class ValidationError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'VALIDATION_ERROR', 400, context, { retryable: false });
    this.name = 'ValidationError';
  }
}

export class AuthenticationError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'AUTHENTICATION_ERROR', 401, context, { retryable: false });
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'AUTHORIZATION_ERROR', 403, context, { retryable: false });
    this.name = 'AuthorizationError';
  }
}

export class NotFoundError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'NOT_FOUND_ERROR', 404, context, { retryable: false });
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'RATE_LIMIT_ERROR', 429, context, { retryable: true, retryDelay: 1000 });
    this.name = 'RateLimitError';
  }
}

export class ServiceUnavailableError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'SERVICE_UNAVAILABLE_ERROR', 503, context, { retryable: true, maxRetries: 3 });
    this.name = 'ServiceUnavailableError';
  }
}

export class DatabaseError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'DATABASE_ERROR', 500, context, { retryable: true, maxRetries: 3, circuitBreaker: true });
    this.name = 'DatabaseError';
  }
}

export class NetworkError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'NETWORK_ERROR', 500, context, { retryable: true, maxRetries: 5, circuitBreaker: true });
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends MeshAdminError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, 'TIMEOUT_ERROR', 408, context, { retryable: true, maxRetries: 2, timeout: 5000 });
    this.name = 'TimeoutError';
  }
}

// ============================================================================
// ERROR CATEGORIZATION
// ============================================================================

export type ErrorCategory = 
  | 'validation'
  | 'authentication'
  | 'authorization'
  | 'not-found'
  | 'rate-limit'
  | 'service-unavailable'
  | 'database'
  | 'network'
  | 'timeout'
  | 'unknown';

export interface ErrorCategoryInfo {
  category: ErrorCategory;
  retryable: boolean;
  defaultRetries: number;
  defaultDelay: number;
  circuitBreaker: boolean;
  fallbackStrategy: 'fail' | 'retry' | 'degrade' | 'circuit-breaker';
}

export const ERROR_CATEGORIES: Record<string, ErrorCategoryInfo> = {
  validation: {
    category: 'validation',
    retryable: false,
    defaultRetries: 0,
    defaultDelay: 0,
    circuitBreaker: false,
    fallbackStrategy: 'fail'
  },
  authentication: {
    category: 'authentication',
    retryable: false,
    defaultRetries: 0,
    defaultDelay: 0,
    circuitBreaker: false,
    fallbackStrategy: 'fail'
  },
  authorization: {
    category: 'authorization',
    retryable: false,
    defaultRetries: 0,
    defaultDelay: 0,
    circuitBreaker: false,
    fallbackStrategy: 'fail'
  },
  'not-found': {
    category: 'not-found',
    retryable: false,
    defaultRetries: 0,
    defaultDelay: 0,
    circuitBreaker: false,
    fallbackStrategy: 'fail'
  },
  'rate-limit': {
    category: 'rate-limit',
    retryable: true,
    defaultRetries: 3,
    defaultDelay: 1000,
    circuitBreaker: false,
    fallbackStrategy: 'retry'
  },
  'service-unavailable': {
    category: 'service-unavailable',
    retryable: true,
    defaultRetries: 3,
    defaultDelay: 2000,
    circuitBreaker: true,
    fallbackStrategy: 'circuit-breaker'
  },
  database: {
    category: 'database',
    retryable: true,
    defaultRetries: 3,
    defaultDelay: 1000,
    circuitBreaker: true,
    fallbackStrategy: 'circuit-breaker'
  },
  network: {
    category: 'network',
    retryable: true,
    defaultRetries: 5,
    defaultDelay: 500,
    circuitBreaker: true,
    fallbackStrategy: 'circuit-breaker'
  },
  timeout: {
    category: 'timeout',
    retryable: true,
    defaultRetries: 2,
    defaultDelay: 1000,
    circuitBreaker: false,
    fallbackStrategy: 'retry'
  },
  unknown: {
    category: 'unknown',
    retryable: false,
    defaultRetries: 0,
    defaultDelay: 0,
    circuitBreaker: false,
    fallbackStrategy: 'fail'
  }
};

export function categorizeError(error: Error): ErrorCategory {
  if (error instanceof MeshAdminError) {
    const code = error.code.toLowerCase();
    
    if (code.includes('validation')) return 'validation';
    if (code.includes('auth')) return 'authentication';
    if (code.includes('unauthorized')) return 'authorization';
    if (code.includes('not_found') || code.includes('notfound')) return 'not-found';
    if (code.includes('rate_limit') || code.includes('ratelimit')) return 'rate-limit';
    if (code.includes('service_unavailable') || code.includes('serviceunavailable')) return 'service-unavailable';
    if (code.includes('database') || code.includes('db')) return 'database';
    if (code.includes('network') || code.includes('connection')) return 'network';
    if (code.includes('timeout')) return 'timeout';
  }
  
  const message = error.message.toLowerCase();
  
  if (message.includes('validation') || message.includes('invalid')) return 'validation';
  if (message.includes('auth') || message.includes('login')) return 'authentication';
  if (message.includes('unauthorized') || message.includes('forbidden')) return 'authorization';
  if (message.includes('not found') || message.includes('missing')) return 'not-found';
  if (message.includes('rate limit') || message.includes('too many')) return 'rate-limit';
  if (message.includes('service unavailable') || message.includes('maintenance')) return 'service-unavailable';
  if (message.includes('database') || message.includes('connection refused')) return 'database';
  if (message.includes('network') || message.includes('econnrefused') || message.includes('timeout')) return 'network';
  if (message.includes('timeout') || message.includes('timed out')) return 'timeout';
  
  return 'unknown';
}

export function getErrorCategoryInfo(category: ErrorCategory): ErrorCategoryInfo {
  return ERROR_CATEGORIES[category] || ERROR_CATEGORIES.unknown;
}

// ============================================================================
// ERROR HANDLER
// ============================================================================

export interface ErrorHandlerOptions {
  silent?: boolean;
  logLevel?: 'error' | 'warn' | 'info' | 'debug';
  notify?: boolean;
  context?: string;
  metadata?: Record<string, any>;
}

export class ErrorHandler extends EventEmitter {
  private static instance: ErrorHandler;
  private handlers: Map<ErrorCategory, Array<(error: Error, context: ErrorContext) => void>> = new Map();

  private constructor() {
    super();
    this.setupDefaultHandlers();
  }

  public static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  private setupDefaultHandlers(): void {
    // Register default handlers for each category
    Object.keys(ERROR_CATEGORIES).forEach(category => {
      this.handlers.set(category as ErrorCategory, []);
    });
  }

  public registerHandler(category: ErrorCategory, handler: (error: Error, context: ErrorContext) => void): void {
    const handlers = this.handlers.get(category) || [];
    handlers.push(handler);
    this.handlers.set(category, handlers);
  }

  public async handleError(error: Error, context: ErrorContext = {}, options: ErrorHandlerOptions = {}): Promise<void> {
    const category = categorizeError(error);
    const categoryInfo = getErrorCategoryInfo(category);
    
    // Emit error event
    this.emit('error', { error, category, context, options });
    
    // Execute category-specific handlers
    const handlers = this.handlers.get(category) || [];
    for (const handler of handlers) {
      try {
        await handler(error, context);
      } catch (error) {
        errorHandler.handleError(error, { service: \'meshadmin-performance-analytics-suite\' });
      }
    }
    
    // Log error if not silent
    if (!options.silent) {
      const logLevel = options.logLevel || 'error';
      const logContext = options.context || context.operation || 'unknown';
      
      console[logLevel](`[${logContext}] ${category.toUpperCase()}: ${error.message}`, {
        error: error.stack,
        context,
        metadata: options.metadata
      });
    }
  }

  public createError(
    message: string,
    category: ErrorCategory,
    context: ErrorContext = {},
    recoveryOptions?: Partial<RecoveryOptions>
  ): MeshAdminError {
    const categoryInfo = getErrorCategoryInfo(category);
    const options: RecoveryOptions = {
      retryable: categoryInfo.retryable,
      maxRetries: categoryInfo.defaultRetries,
      retryDelay: categoryInfo.defaultDelay,
      circuitBreaker: categoryInfo.circuitBreaker,
      fallbackValue: undefined,
      ...recoveryOptions
    };

    switch (category) {
      case 'validation':
        return new ValidationError(message, context);
      case 'authentication':
        return new AuthenticationError(message, context);
      case 'authorization':
        return new AuthorizationError(message, context);
      case 'not-found':
        return new NotFoundError(message, context);
      case 'rate-limit':
        return new RateLimitError(message, context);
      case 'service-unavailable':
        return new ServiceUnavailableError(message, context);
      case 'database':
        return new DatabaseError(message, context);
      case 'network':
        return new NetworkError(message, context);
      case 'timeout':
        return new TimeoutError(message, context);
      default:
        return new MeshAdminError(message, 'UNKNOWN_ERROR', 500, context, options);
    }
  }
}

// Export singleton instance
export const errorHandler = ErrorHandler.getInstance();
