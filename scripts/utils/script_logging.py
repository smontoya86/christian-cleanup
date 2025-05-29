"""
Standalone Logging Utility for Scripts
Provides structured logging for scripts that run outside the Flask application context.
"""

import logging
import json
import time
import os
import sys
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


class ScriptLogFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs for scripts."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "level": record.levelname,
            "message": record.getMessage(),
            "script": getattr(record, 'script_name', 'unknown'),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "logger": record.name
        }
        
        # Add exception info if present
        if record.exc_info:
            import traceback
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add any extra fields from the log record
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)
            
        return json.dumps(log_record)


class ScriptLoggerFilter(logging.Filter):
    """Filter that adds script-specific context to log records."""
    
    def __init__(self, script_name):
        super().__init__()
        self.script_name = script_name
    
    def filter(self, record):
        """Add script context to the log record."""
        record.script_name = self.script_name
        return True


def setup_script_logging(script_name: str = None, log_level: str = None) -> logging.Logger:
    """
    Set up logging for a standalone script.
    
    Args:
        script_name: Name of the script (auto-detected if None)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Logger instance configured for the script
    """
    if script_name is None:
        # Auto-detect script name from the calling frame
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            script_path = frame.f_back.f_globals.get('__file__', 'unknown_script.py')
            script_name = os.path.basename(script_path).replace('.py', '')
        else:
            script_name = 'unknown_script'
    
    # Determine log level
    if log_level is None:
        log_level = os.getenv('SCRIPT_LOG_LEVEL', 'INFO')
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger_name = f'scripts.{script_name}'
    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = ScriptLogFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ScriptLoggerFilter(script_name))
    logger.addHandler(console_handler)
    
    # File handler (if logs directory exists)
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    if os.path.exists(log_dir):
        log_file = os.path.join(log_dir, f'scripts.{script_name}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5242880,  # 5MB
            backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ScriptLoggerFilter(script_name))
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_script_logger(name: str = None) -> logging.Logger:
    """
    Get or create a script logger.
    
    Args:
        name: Logger name (auto-detected if None)
        
    Returns:
        Logger instance
    """
    return setup_script_logging(name)


def log_operation_start(logger: logging.Logger, operation: str, **context):
    """Log the start of an operation with context."""
    logger.info(f"🚀 Starting: {operation}", extra={
        'extra_fields': {
            'operation': operation,
            'phase': 'start',
            **context
        }
    })


def log_operation_success(logger: logging.Logger, operation: str, duration: float = None, **context):
    """Log successful completion of an operation."""
    message = f"✅ Completed: {operation}"
    if duration:
        message += f" (took {duration:.2f}s)"
    
    logger.info(message, extra={
        'extra_fields': {
            'operation': operation,
            'phase': 'success',
            'duration': duration,
            **context
        }
    })


def log_operation_error(logger: logging.Logger, operation: str, error: Exception, **context):
    """Log an operation error."""
    logger.error(f"❌ Failed: {operation} - {str(error)}", extra={
        'extra_fields': {
            'operation': operation,
            'phase': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            **context
        }
    }, exc_info=True)


def log_progress(logger: logging.Logger, operation: str, current: int, total: int, **context):
    """Log progress of a long-running operation."""
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"📊 Progress: {operation} - {current}/{total} ({percentage:.1f}%)", extra={
        'extra_fields': {
            'operation': operation,
            'phase': 'progress',
            'current': current,
            'total': total,
            'percentage': percentage,
            **context
        }
    })


def log_warning(logger: logging.Logger, message: str, **context):
    """Log a warning with context."""
    logger.warning(f"⚠️ {message}", extra={
        'extra_fields': {
            'phase': 'warning',
            **context
        }
    })


def log_milestone(logger: logging.Logger, milestone: str, **context):
    """Log a milestone or important checkpoint."""
    logger.info(f"🎯 Milestone: {milestone}", extra={
        'extra_fields': {
            'phase': 'milestone',
            'milestone': milestone,
            **context
        }
    }) 