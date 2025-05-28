"""
Comprehensive Structured Logging Configuration for Christian Cleanup Application
Provides centralized logging with JSON formatting, request tracking, and component-specific loggers.
"""

import logging
import json
import time
import traceback
import uuid
import os
from typing import Dict, Any, Optional
from flask import request, g, has_request_context
from logging.handlers import RotatingFileHandler


class StructuredLogFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with request context."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "logger": record.name
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add request context if available
        if has_request_context():
            log_record["request"] = {
                "id": getattr(g, 'request_id', None),
                "method": request.method,
                "path": request.path,
                "ip": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown')
            }
            
        # Add any extra fields from the log record
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)
            
        return json.dumps(log_record)


class RequestContextFilter(logging.Filter):
    """Filter that adds request context to log records."""
    
    def filter(self, record):
        """Add request context to the log record."""
        if has_request_context():
            record.request_id = getattr(g, 'request_id', None)
            record.request_method = request.method
            record.request_path = request.path
        return True


def configure_logging(app):
    """
    Configure comprehensive logging for the application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Logger: Main application logger
    """
    # Create logs directory if it doesn't exist
    log_dir = app.config.get('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Get log level from config
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create structured formatter
    structured_formatter = StructuredLogFormatter()
    
    # Console handler with structured logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(structured_formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)
    
    # File handlers with rotation
    if not app.config.get('TESTING', False):
        # Main application log
        app_log_file = os.path.join(log_dir, 'app.log')
        app_handler = RotatingFileHandler(
            app_log_file, 
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        app_handler.setFormatter(structured_formatter)
        app_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(app_handler)
        
        # Error log (ERROR level and above)
        error_log_file = os.path.join(log_dir, 'error.log')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10485760,  # 10MB
            backupCount=20
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(structured_formatter)
        error_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(error_handler)
        
        # Performance log for slow operations
        performance_log_file = os.path.join(log_dir, 'performance.log')
        performance_handler = RotatingFileHandler(
            performance_log_file,
            maxBytes=5242880,  # 5MB
            backupCount=5
        )
        performance_handler.setFormatter(structured_formatter)
        performance_handler.addFilter(RequestContextFilter())
        
        # Create performance logger
        performance_logger = logging.getLogger('app.performance')
        performance_logger.addHandler(performance_handler)
        performance_logger.setLevel(logging.INFO)
        performance_logger.propagate = False  # Don't propagate to root logger
    
    # Configure component-specific loggers
    components = [
        'analysis', 'lyrics', 'worker', 'database', 'redis', 'api', 
        'auth', 'spotify', 'cache', 'queue', 'monitoring'
    ]
    
    component_loggers = {}
    for component in components:
        component_logger = logging.getLogger(f'app.{component}')
        component_level = app.config.get(f'{component.upper()}_LOG_LEVEL', log_level)
        component_logger.setLevel(component_level)
        component_loggers[component] = component_logger
    
    # Create main app logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    
    # Log configuration startup
    app_logger.info("Structured logging configured", extra={
        'extra_fields': {
            'log_level': logging.getLevelName(log_level),
            'log_dir': log_dir,
            'components': components,
            'handlers': [handler.__class__.__name__ for handler in root_logger.handlers]
        }
    })
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (e.g., 'app.analysis', 'app.worker')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **extra_fields):
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (e.g., logging.INFO)
        message: Log message
        **extra_fields: Additional fields to include in the log
    """
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


def setup_request_id_middleware(app):
    """
    Set up middleware to assign unique IDs to each request.
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def before_request():
        """Assign a unique request ID to each request."""
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()
        
        # Log request start
        logger = get_logger('app.api')
        logger.info(f"Request started: {request.method} {request.path}", extra={
            'extra_fields': {
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
        })
    
    @app.after_request
    def after_request(response):
        """Log request completion with timing information."""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            logger = get_logger('app.api')
            logger.info(f"Request completed: {request.method} {request.path}", extra={
                'extra_fields': {
                    'request_id': getattr(g, 'request_id', None),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                    'content_length': response.content_length
                }
            })
            
            # Log slow requests to performance logger
            if duration > app.config.get('SLOW_REQUEST_THRESHOLD', 2.0):
                perf_logger = get_logger('app.performance')
                perf_logger.warning(f"Slow request detected: {request.method} {request.path}", extra={
                    'extra_fields': {
                        'request_id': getattr(g, 'request_id', None),
                        'duration_ms': round(duration * 1000, 2),
                        'threshold_ms': app.config.get('SLOW_REQUEST_THRESHOLD', 2.0) * 1000
                    }
                })
        
        return response


def log_analysis_metrics(song_id: int, duration: float, success: bool, **extra_data):
    """
    Log analysis performance metrics.
    
    Args:
        song_id: ID of the analyzed song
        duration: Analysis duration in seconds
        success: Whether the analysis was successful
        **extra_data: Additional metrics data
    """
    logger = get_logger('app.analysis')
    level = logging.INFO if success else logging.ERROR
    message = f"Song analysis {'completed' if success else 'failed'}: song_id={song_id}"
    
    logger.log(level, message, extra={
        'extra_fields': {
            'song_id': song_id,
            'duration_ms': round(duration * 1000, 2),
            'success': success,
            **extra_data
        }
    })


def log_worker_metrics(job_id: str, queue: str, duration: float, success: bool, **extra_data):
    """
    Log worker job performance metrics.
    
    Args:
        job_id: Job identifier
        queue: Queue name
        duration: Job duration in seconds
        success: Whether the job was successful
        **extra_data: Additional metrics data
    """
    logger = get_logger('app.worker')
    level = logging.INFO if success else logging.ERROR
    message = f"Worker job {'completed' if success else 'failed'}: {job_id}"
    
    logger.log(level, message, extra={
        'extra_fields': {
            'job_id': job_id,
            'queue': queue,
            'duration_ms': round(duration * 1000, 2),
            'success': success,
            **extra_data
        }
    })


def log_database_metrics(operation: str, duration: float, affected_rows: int = None, **extra_data):
    """
    Log database operation metrics.
    
    Args:
        operation: Database operation type
        duration: Operation duration in seconds
        affected_rows: Number of affected rows (if applicable)
        **extra_data: Additional metrics data
    """
    logger = get_logger('app.database')
    message = f"Database operation: {operation}"
    
    logger.info(message, extra={
        'extra_fields': {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'affected_rows': affected_rows,
            **extra_data
        }
    })


def log_redis_metrics(operation: str, duration: float, success: bool, **extra_data):
    """
    Log Redis operation metrics.
    
    Args:
        operation: Redis operation type
        duration: Operation duration in seconds
        success: Whether the operation was successful
        **extra_data: Additional metrics data
    """
    logger = get_logger('app.redis')
    level = logging.INFO if success else logging.ERROR
    message = f"Redis operation {'completed' if success else 'failed'}: {operation}"
    
    logger.log(level, message, extra={
        'extra_fields': {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'success': success,
            **extra_data
        }
    }) 