"""
Database Connection Pool Monitor

Provides visibility into SQLAlchemy connection pool health and usage.
"""

import logging
from typing import Dict, Any, Optional
from app.extensions import db

logger = logging.getLogger(__name__)


def get_pool_stats() -> Dict[str, Any]:
    """
    Get database connection pool statistics.
    
    Returns:
        Dictionary with pool stats including:
        - pool_size: Total connections in pool
        - checked_in: Connections available
        - checked_out: Connections in use
        - overflow: Connections beyond pool_size
        - max_overflow: Maximum allowed overflow
        - capacity: Total capacity (pool_size + max_overflow)
        - utilization: Percentage of capacity in use
    """
    try:
        engine = db.get_engine()
        pool = engine.pool
        
        # Get pool statistics
        pool_size = pool.size()
        checked_out = pool.checkedout()
        checked_in = pool_size - checked_out
        overflow = pool.overflow()
        max_overflow = pool._max_overflow if hasattr(pool, '_max_overflow') else 0
        
        total_capacity = pool_size + max_overflow
        utilization = round((checked_out + overflow) / max(total_capacity, 1) * 100, 1)
        
        return {
            'healthy': True,
            'pool_size': pool_size,
            'checked_in': checked_in,
            'checked_out': checked_out,
            'overflow': overflow,
            'max_overflow': max_overflow,
            'total_capacity': total_capacity,
            'utilization_percent': utilization,
            'status': _get_status_message(utilization)
        }
    except Exception as e:
        logger.error(f"Failed to get pool stats: {e}")
        return {
            'healthy': False,
            'error': str(e),
            'status': 'Error retrieving pool stats'
        }


def _get_status_message(utilization: float) -> str:
    """
    Get human-readable status based on utilization.
    
    Args:
        utilization: Pool utilization percentage
        
    Returns:
        Status message
    """
    if utilization < 50:
        return 'Healthy'
    elif utilization < 75:
        return 'Moderate Load'
    elif utilization < 90:
        return 'High Load'
    else:
        return 'Critical - Near Capacity'


def check_pool_health() -> bool:
    """
    Check if connection pool is healthy.
    
    Returns:
        True if healthy, False otherwise
    """
    try:
        stats = get_pool_stats()
        
        if not stats.get('healthy'):
            return False
        
        # Consider unhealthy if utilization > 95%
        if stats.get('utilization_percent', 0) > 95:
            logger.warning(
                f"Database pool nearing capacity: "
                f"{stats['utilization_percent']}% utilized"
            )
            return False
        
        return True
    except Exception as e:
        logger.error(f"Pool health check failed: {e}")
        return False


def log_pool_stats():
    """Log current pool statistics (useful for debugging)."""
    stats = get_pool_stats()
    
    if stats.get('healthy'):
        logger.info(
            f"DB Pool Stats: {stats['checked_out']}/{stats['pool_size']} in use, "
            f"{stats['overflow']} overflow, {stats['utilization_percent']}% utilized"
        )
    else:
        logger.error(f"DB Pool Error: {stats.get('error', 'Unknown error')}")

