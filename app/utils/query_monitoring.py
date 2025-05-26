"""
Query monitoring utilities for tracking and logging slow database queries.
"""
import logging
from typing import Dict, Any, List
from flask import current_app, g, request
from flask_sqlalchemy.record_queries import get_recorded_queries

logger = logging.getLogger(__name__)


def log_slow_queries():
    """
    Log slow queries that exceed the configured threshold.
    Should be called after request completion.
    """
    try:
        # Check if query recording is enabled
        if not current_app.config.get('SQLALCHEMY_RECORD_QUERIES', False):
            return
        
        # Get the slow query threshold (default to 0.5 seconds)
        threshold = current_app.config.get('SLOW_QUERY_THRESHOLD', 0.5)
        
        # Get all queries executed during this request
        queries = get_recorded_queries()
        
        if not queries:
            return
        
        # Log slow queries
        for query in queries:
            if query.duration >= threshold:
                logger.warning(
                    f"Slow query detected - Duration: {query.duration:.3f}s | "
                    f"Statement: {query.statement} | "
                    f"Parameters: {query.parameters} | "
                    f"Location: {getattr(query, 'location', 'unknown')}"
                )
                
                # Store slow query info in app context for statistics
                if not hasattr(g, 'slow_queries'):
                    g.slow_queries = []
                g.slow_queries.append({
                    'duration': query.duration,
                    'statement': query.statement,
                    'parameters': query.parameters,
                    'location': getattr(query, 'location', 'unknown')
                })
    
    except Exception as e:
        logger.error(f"Error logging slow queries: {e}")


def get_query_statistics() -> Dict[str, Any]:
    """
    Get statistics about queries executed during the current request.
    
    Returns:
        Dictionary containing query statistics
    """
    try:
        # Check if query recording is enabled
        if not current_app.config.get('SQLALCHEMY_RECORD_QUERIES', False):
            return {
                'total_queries': 0,
                'slow_queries': 0,
                'average_duration': 0.0,
                'queries': []
            }
        
        # Get the slow query threshold
        threshold = current_app.config.get('SLOW_QUERY_THRESHOLD', 0.5)
        
        # Get all queries executed during this request
        queries = get_recorded_queries()
        
        if not queries:
            return {
                'total_queries': 0,
                'slow_queries': 0,
                'average_duration': 0.0,
                'queries': []
            }
        
        # Calculate statistics
        total_queries = len(queries)
        slow_queries = sum(1 for q in queries if q.duration >= threshold)
        total_duration = sum(q.duration for q in queries)
        average_duration = total_duration / total_queries if total_queries > 0 else 0.0
        
        # Prepare query details
        query_details = []
        for query in queries:
            query_details.append({
                'duration': query.duration,
                'statement': query.statement,
                'parameters': query.parameters,
                'is_slow': query.duration >= threshold,
                'location': getattr(query, 'location', 'unknown')
            })
        
        return {
            'total_queries': total_queries,
            'slow_queries': slow_queries,
            'average_duration': average_duration,
            'queries': query_details
        }
    
    except Exception as e:
        logger.error(f"Error getting query statistics: {e}")
        return {
            'total_queries': 0,
            'slow_queries': 0,
            'average_duration': 0.0,
            'queries': []
        }


def setup_query_monitoring(app):
    """
    Set up query monitoring for the application.
    
    Args:
        app: Flask application instance
    """
    # Enable query recording if not already set
    if 'SQLALCHEMY_RECORD_QUERIES' not in app.config:
        app.config['SQLALCHEMY_RECORD_QUERIES'] = app.debug
    
    # Set default slow query threshold if not configured
    if 'SLOW_QUERY_THRESHOLD' not in app.config:
        app.config['SLOW_QUERY_THRESHOLD'] = 0.5  # 500ms default
    
    @app.after_request
    def log_slow_queries_after_request(response):
        """After request handler to log slow queries."""
        try:
            log_slow_queries()
        except Exception as e:
            logger.error(f"Error in slow query logging after request: {e}")
        return response
    
    # Log configuration on startup
    with app.app_context():
        if app.config.get('SQLALCHEMY_RECORD_QUERIES', False):
            threshold = app.config.get('SLOW_QUERY_THRESHOLD', 0.5)
            logger.info(f"Query monitoring enabled with {threshold}s slow query threshold")
        else:
            logger.info("Query monitoring disabled (SQLALCHEMY_RECORD_QUERIES=False)")


def create_query_monitoring_endpoint(app):
    """
    Create an endpoint to view query statistics for the current request.
    
    Args:
        app: Flask application instance
    """
    @app.route('/debug/query-stats')
    def query_statistics():
        """Debug endpoint to view query statistics."""
        if not app.debug:
            return {'error': 'Debug mode required'}, 403
        
        stats = get_query_statistics()
        return {
            'query_statistics': stats,
            'config': {
                'recording_enabled': app.config.get('SQLALCHEMY_RECORD_QUERIES', False),
                'slow_query_threshold': app.config.get('SLOW_QUERY_THRESHOLD', 0.5)
            }
        } 