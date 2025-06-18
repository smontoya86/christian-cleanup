"""
Simple logging utility to replace the complex logging system.
This provides a minimal interface compatible with the analysis engine.
"""
import logging

def get_logger(name):
    """Get a logger instance by name."""
    return logging.getLogger(name)

def setup_logging(level=logging.INFO):
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 