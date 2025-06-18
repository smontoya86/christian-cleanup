#!/usr/bin/env python3
"""
Script Logging Utilities

Centralized logging utilities for converted scripts to ensure consistent
logging configuration and behavior across all scripts.
"""

import logging
import sys
import os
import json
import time
from datetime import datetime


def get_logger(name, level=logging.INFO):
    """
    Get a configured logger for scripts.
    
    Args:
        name (str): Logger name (typically __name__)
        level (int): Logging level (default: INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        logger.setLevel(level)
        
        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False
    
    return logger


def configure_basic_logging(level=logging.INFO):
    """
    Configure basic logging for scripts that don't use get_logger.
    
    Args:
        level (int): Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def get_script_logger(script_name, level=logging.INFO):
    """
    Get a logger specifically configured for a script file.
    
    Args:
        script_name (str): Name of the script (e.g., 'quick_test_converted')
        level (int): Logging level (default: INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger_name = f"scripts.{script_name}"
    return get_logger(logger_name, level)


def log_script_start(logger, script_name, description=None):
    """
    Log the start of a script execution.
    
    Args:
        logger (logging.Logger): Logger instance
        script_name (str): Name of the script
        description (str, optional): Script description
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {script_name}")
    if description:
        logger.info(f"📝 {description}")
    logger.info(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


def log_script_end(logger, script_name, success=True, duration=None):
    """
    Log the end of a script execution.
    
    Args:
        logger (logging.Logger): Logger instance
        script_name (str): Name of the script
        success (bool): Whether the script completed successfully
        duration (float, optional): Execution duration in seconds
    """
    logger.info("=" * 60)
    status = "✅ Completed successfully" if success else "❌ Completed with errors"
    logger.info(f"{status}: {script_name}")
    if duration is not None:
        logger.info(f"⏱️ Duration: {duration:.2f} seconds")
    logger.info(f"⏰ Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


def log_section(logger, section_name):
    """
    Log a section header.
    
    Args:
        logger (logging.Logger): Logger instance
        section_name (str): Name of the section
    """
    logger.info("")
    logger.info(f"📋 {section_name}")
    logger.info("-" * 40)


# Default logger for quick access
default_logger = get_logger('scripts.utils.script_logging')


def log_operation_start(logger, operation, **context):
    """Log the start of an operation with context."""
    logger.info(f"🚀 Starting: {operation}")


def log_operation_success(logger, operation, duration=None, **context):
    """Log successful completion of an operation."""
    message = f"✅ Completed: {operation}"
    if duration:
        message += f" (took {duration:.2f}s)"
    logger.info(message)


def log_operation_error(logger, operation, error, **context):
    """Log an operation error."""
    logger.error(f"❌ Failed: {operation} - {str(error)}", exc_info=True)


def log_progress(logger, operation, current, total, **context):
    """Log progress of a long-running operation."""
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"📊 Progress: {operation} - {current}/{total} ({percentage:.1f}%)")


def setup_script_logging(script_name=None, log_level=None):
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
    
    # Custom JSON formatter
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                "level": record.levelname,
                "message": record.getMessage(),
                "script": script_name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "logger": record.name
            }
            
            # Add extra fields if present
            if hasattr(record, 'extra_fields'):
                log_record.update(record.extra_fields)
                
            return json.dumps(log_record)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def log_warning(logger, message, **context):
    """Log a warning with context."""
    logger.warning(f"⚠️ {message}")


def log_milestone(logger, milestone, **context):
    """Log a milestone or important checkpoint."""
    logger.info(f"🎯 Milestone: {milestone}") 