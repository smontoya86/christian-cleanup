"""
Database monitoring utilities for connection pool health and performance.
"""
import logging
from typing import Dict, Any
from flask import current_app
from app.extensions import db

logger = logging.getLogger(__name__)


def get_pool_status() -> Dict[str, Any]:
    """
    Get current database connection pool status and statistics.
    
    Returns:
        Dictionary containing pool status information
    """
    try:
        engine = db.engine
        pool = engine.pool
        
        # Get overflow value - it might be a method or property
        overflow_value = 0
        if hasattr(pool, 'overflow'):
            overflow_attr = getattr(pool, 'overflow')
            if callable(overflow_attr):
                overflow_value = overflow_attr()
            else:
                overflow_value = overflow_attr
        
        # Get invalid value - it might be a method or property  
        invalid_value = 0
        if hasattr(pool, 'invalid'):
            invalid_attr = getattr(pool, 'invalid')
            if callable(invalid_attr):
                invalid_value = invalid_attr()
            else:
                invalid_value = invalid_attr
        
        status = {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': overflow_value,
            'invalid': invalid_value,
            'pool_class': pool.__class__.__name__,
            'engine_url': str(engine.url).replace(engine.url.password or '', '***') if engine.url.password else str(engine.url)
        }
        
        # Calculate utilization percentage
        total_connections = status['checked_in'] + status['checked_out']
        if status['pool_size'] > 0:
            status['utilization_percent'] = (total_connections / status['pool_size']) * 100
        else:
            status['utilization_percent'] = 0
            
        return status
        
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return {
            'error': str(e),
            'pool_size': 0,
            'checked_in': 0,
            'checked_out': 0,
            'overflow': 0,
            'invalid': 0,
            'utilization_percent': 0
        }


def log_pool_status():
    """Log current pool status for monitoring purposes."""
    status = get_pool_status()
    
    if 'error' in status:
        logger.error(f"Pool status error: {status['error']}")
        return
    
    logger.info(
        f"DB Pool Status - Size: {status['pool_size']}, "
        f"In: {status['checked_in']}, Out: {status['checked_out']}, "
        f"Overflow: {status['overflow']}, Invalid: {status['invalid']}, "
        f"Utilization: {status['utilization_percent']:.1f}%"
    )


def check_pool_health() -> Dict[str, Any]:
    """
    Check pool health and return status with recommendations.
    
    Returns:
        Dictionary containing health status and recommendations
    """
    status = get_pool_status()
    
    if 'error' in status:
        return {
            'healthy': False,
            'status': status,
            'issues': [f"Pool status error: {status['error']}"],
            'recommendations': ["Check database connectivity and configuration"]
        }
    
    issues = []
    recommendations = []
    
    # Check for high utilization
    if status['utilization_percent'] > 80:
        issues.append(f"High pool utilization: {status['utilization_percent']:.1f}%")
        recommendations.append("Consider increasing pool_size or max_overflow")
    
    # Check for invalid connections
    if status['invalid'] > 0:
        issues.append(f"Invalid connections detected: {status['invalid']}")
        recommendations.append("Check database connectivity and pool_recycle setting")
    
    # Check for overflow usage
    if status['overflow'] > status['pool_size'] * 0.5:
        issues.append(f"High overflow usage: {status['overflow']}")
        recommendations.append("Consider increasing base pool_size")
    
    # Check if all connections are checked out
    if status['checked_out'] >= status['pool_size'] and status['overflow'] > 0:
        issues.append("All base pool connections are in use, relying on overflow")
        recommendations.append("Monitor for connection leaks or increase pool_size")
    
    return {
        'healthy': len(issues) == 0,
        'status': status,
        'issues': issues,
        'recommendations': recommendations
    }


def create_pool_health_endpoint(app):
    """
    Create a health check endpoint for the database pool.
    
    Args:
        app: Flask application instance
    """
    @app.route('/health/database')
    def database_health():
        """Database pool health check endpoint."""
        health = check_pool_health()
        
        # Return appropriate HTTP status code
        status_code = 200 if health['healthy'] else 503
        
        return {
            'service': 'database',
            'healthy': health['healthy'],
            'pool_status': health['status'],
            'issues': health['issues'],
            'recommendations': health['recommendations']
        }, status_code


def setup_pool_monitoring(app):
    """
    Set up database pool monitoring for the application.
    
    Args:
        app: Flask application instance
    """
    # Create health endpoint
    create_pool_health_endpoint(app)
    
    # Log pool status on startup
    with app.app_context():
        log_pool_status()
    
    # Set up periodic logging if in debug mode
    if app.debug:
        @app.after_request
        def log_pool_after_request(response):
            # Only log every 10th request to avoid spam
            if hasattr(app, '_pool_log_counter'):
                app._pool_log_counter += 1
            else:
                app._pool_log_counter = 1
                
            if app._pool_log_counter % 10 == 0:
                log_pool_status()
                
            return response 