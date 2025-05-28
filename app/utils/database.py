"""
Database Utilities for SQLAlchemy 2.0 Compatibility

This module provides utilities for consistent database session management
and SQLAlchemy 2.0 compatible query patterns.
"""

from contextlib import contextmanager
from typing import Optional, Type, Any, List
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session
from app.extensions import db
import logging
from sqlalchemy import func
import time
from datetime import datetime

logger = logging.getLogger(__name__)


@contextmanager
def db_transaction():
    """
    Context manager for database transactions with automatic rollback on errors.
    
    Usage:
        with db_transaction() as session:
            song = session.get(Song, song_id)
            song.title = "New Title"
            # Automatic commit/rollback
    """
    try:
        yield db.session
        db.session.commit()
        logger.debug("Database transaction committed successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database transaction rolled back due to error: {e}")
        raise
    finally:
        db.session.remove()


def get_by_id(model_class: Type, id_value: Any) -> Optional[Any]:
    """
    SQLAlchemy 2.0 compatible get by ID.
    
    Args:
        model_class: The SQLAlchemy model class
        id_value: The ID value to search for
        
    Returns:
        Model instance or None if not found
    """
    try:
        return db.session.get(model_class, id_value)
    except Exception as e:
        logger.error(f"Error getting {model_class.__name__} with ID {id_value}: {e}")
        return None


def get_by_filter(model_class: Type, **filters) -> Optional[Any]:
    """
    SQLAlchemy 2.0 compatible filter query for single result.
    
    Args:
        model_class: The SQLAlchemy model class
        **filters: Keyword arguments for filtering
        
    Returns:
        First matching model instance or None
    """
    from .metrics import metrics_collector
    from .logging import log_database_metrics
    
    start_time = time.time()
    operation = f"get_by_filter_{model_class.__name__}"
    
    try:
        stmt = select(model_class)
        for key, value in filters.items():
            if hasattr(model_class, key):
                stmt = stmt.where(getattr(model_class, key) == value)
            else:
                logger.warning(f"Model {model_class.__name__} has no attribute {key}", extra={
                    'extra_fields': {
                        'model': model_class.__name__,
                        'invalid_attribute': key,
                        'operation': operation
                    }
                })
                return None
        
        result = db.session.execute(stmt).scalar_one_or_none()
        duration = time.time() - start_time
        
        # Log successful database operation
        logger.debug(f"🔍 Database query completed", extra={
            'extra_fields': {
                'model': model_class.__name__,
                'operation': operation,
                'filters': filters,
                'duration_ms': round(duration * 1000, 2),
                'result_found': result is not None
            }
        })
        
        # Track database metrics
        log_database_metrics(
            operation=operation,
            duration=duration,
            affected_rows=1 if result else 0,
            model=model_class.__name__
        )
        
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"💥 Database query failed", extra={
            'extra_fields': {
                'model': model_class.__name__,
                'operation': operation,
                'filters': filters,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'duration_ms': round(duration * 1000, 2)
            }
        }, exc_info=True)
        
        # Track failed database operation
        metrics_collector.record_error(
            error_type='database_error',
            error_message=str(e),
            operation=operation,
            model=model_class.__name__
        )
        
        return None


def get_all_by_filter(model_class: Type, **filters) -> List[Any]:
    """
    SQLAlchemy 2.0 compatible filter query for multiple results.
    
    Args:
        model_class: The SQLAlchemy model class
        **filters: Keyword arguments for filtering
        
    Returns:
        List of matching model instances
    """
    try:
        stmt = select(model_class)
        for key, value in filters.items():
            if hasattr(model_class, key):
                stmt = stmt.where(getattr(model_class, key) == value)
            else:
                logger.warning(f"Model {model_class.__name__} has no attribute {key}")
                return []
        
        result = db.session.execute(stmt).scalars().all()
        return list(result)
    except Exception as e:
        logger.error(f"Error filtering {model_class.__name__} with {filters}: {e}")
        return []


def execute_raw_sql(sql_query: str, params: Optional[dict] = None) -> Any:
    """
    Execute raw SQL with SQLAlchemy 2.0 compatible pattern.
    
    Args:
        sql_query: The SQL query string
        params: Optional parameters dictionary
        
    Returns:
        Query result
    """
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(sql_query), params or {})
            return result
    except Exception as e:
        logger.error(f"Error executing raw SQL: {e}")
        raise


def safe_commit():
    """
    Safely commit the current session with error handling.
    """
    try:
        db.session.commit()
        logger.debug("Session committed successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Session commit failed, rolled back: {e}")
        raise


def safe_rollback():
    """
    Safely rollback the current session.
    """
    try:
        db.session.rollback()
        logger.debug("Session rolled back successfully")
    except Exception as e:
        logger.error(f"Session rollback failed: {e}")


# Compatibility helpers for common patterns
def count_records(model_class: Type, **filters) -> int:
    """
    Count records matching the given filters.
    
    Args:
        model_class: The SQLAlchemy model class
        **filters: Keyword arguments for filtering
        
    Returns:
        Count of matching records
    """
    try:
        stmt = select(model_class)
        for key, value in filters.items():
            if hasattr(model_class, key):
                stmt = stmt.where(getattr(model_class, key) == value)
        
        # Count the results
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = db.session.execute(count_stmt).scalar()
        return result or 0
    except Exception as e:
        logger.error(f"Error counting {model_class.__name__} with {filters}: {e}")
        return 0


def count_by_filter(model: Type, **filters) -> int:
    """
    Count records matching the given filters using SQLAlchemy 2.0 patterns.
    
    Args:
        model: The SQLAlchemy model class
        **filters: Filter conditions as keyword arguments
        
    Returns:
        int: Count of matching records
        
    Example:
        count = count_by_filter(User, active=True, role='admin')
    """
    try:
        stmt = select(func.count()).select_from(model)
        for key, value in filters.items():
            if hasattr(model, key):
                stmt = stmt.where(getattr(model, key) == value)
            else:
                logger.warning(f"Model {model.__name__} has no attribute '{key}'")
                return 0
        
        result = db.session.execute(stmt)
        return result.scalar() or 0
        
    except Exception as e:
        logger.error(f"Error counting {model.__name__} records with filters {filters}: {e}")
        return 0


def safe_add_and_commit(obj, error_message: str = "Database operation failed") -> bool:
    """
    Safely add an object to the session and commit with error handling.
    
    Args:
        obj: The object to add to the database
        error_message: Custom error message for logging
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.session.add(obj)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"{error_message}: {e}")
        return False


def safe_commit(error_message: str = "Database commit failed") -> bool:
    """
    Safely commit the current session with error handling.
    
    Args:
        error_message: Custom error message for logging
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"{error_message}: {e}")
        return False


def safe_delete_and_commit(obj, error_message: str = "Database delete failed") -> bool:
    """
    Safely delete an object from the session and commit with error handling.
    
    Args:
        obj: The object to delete from the database
        error_message: Custom error message for logging
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"{error_message}: {e}")
        return False


@contextmanager
def db_transaction_safe():
    """
    Enhanced context manager for database transactions with comprehensive error handling.
    
    Usage:
        with db_transaction_safe() as session:
            song = session.get(Song, song_id)
            song.title = "New Title"
            # Automatic commit/rollback with error logging
    """
    try:
        yield db.session
        db.session.commit()
        logger.debug("Database transaction committed successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database transaction failed, rolled back: {e}")
        raise 


def bulk_get_by_ids(model: Type, ids: List[Any]) -> List[Any]:
    """
    Get multiple records by their IDs using SQLAlchemy 2.0 patterns.
    
    Args:
        model: The SQLAlchemy model class
        ids: List of IDs to fetch
        
    Returns:
        List of model instances
        
    Example:
        songs = bulk_get_by_ids(Song, [1, 2, 3, 4, 5])
    """
    if not ids:
        return []
        
    try:
        stmt = select(model).where(model.id.in_(ids))
        result = db.session.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error in bulk_get_by_ids for {model.__name__}: {e}")
        return []


def bulk_update(model: Type, updates: List[dict], key_field: str = 'id') -> bool:
    """
    Perform bulk updates using SQLAlchemy 2.0 patterns.
    
    Args:
        model: The SQLAlchemy model class
        updates: List of dictionaries with update data
        key_field: Field to use as key for updates (default: 'id')
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        updates = [{'id': 1, 'title': 'New Title'}, {'id': 2, 'title': 'Another Title'}]
        success = bulk_update(Song, updates)
    """
    try:
        for update_data in updates:
            key_value = update_data.pop(key_field)
            stmt = update(model).where(getattr(model, key_field) == key_value).values(**update_data)
            db.session.execute(stmt)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk_update for {model.__name__}: {e}")
        return False


def exists_by_filter(model: Type, **filters) -> bool:
    """
    Check if a record exists with the given filters using SQLAlchemy 2.0 patterns.
    
    Args:
        model: The SQLAlchemy model class
        **filters: Filter conditions as keyword arguments
        
    Returns:
        bool: True if record exists, False otherwise
        
    Example:
        exists = exists_by_filter(User, email='test@example.com')
    """
    try:
        stmt = select(func.count()).select_from(model)
        for key, value in filters.items():
            if hasattr(model, key):
                stmt = stmt.where(getattr(model, key) == value)
            else:
                logger.warning(f"Model {model.__name__} has no attribute '{key}'")
                return False
        
        result = db.session.execute(stmt)
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking existence for {model.__name__}: {e}")
        return False


def get_or_create(model: Type, defaults: dict = None, **filters):
    """
    Get or create a record using SQLAlchemy 2.0 patterns.
    
    Args:
        model: The SQLAlchemy model class
        defaults: Default values for creation
        **filters: Filter conditions for lookup
        
    Returns:
        tuple: (instance, created) where created is boolean
        
    Example:
        user, created = get_or_create(User, 
                                     defaults={'display_name': 'New User'}, 
                                     email='test@example.com')
    """
    try:
        # Try to get existing record
        instance = get_by_filter(model, **filters)
        if instance:
            return instance, False
            
        # Create new record
        create_data = filters.copy()
        if defaults:
            create_data.update(defaults)
            
        instance = model(**create_data)
        if safe_add_and_commit(instance):
            return instance, True
        else:
            # Try one more time to get existing (race condition)
            existing = get_by_filter(model, **filters)
            if existing:
                return existing, False
            raise Exception("Failed to create and couldn't find existing record")
            
    except Exception as e:
        logger.error(f"Error in get_or_create for {model.__name__}: {e}")
        return None, False


@contextmanager
def db_connection():
    """
    Context manager for raw database connections using SQLAlchemy 2.0 patterns.
    
    Usage:
        with db_connection() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
    """
    try:
        with db.engine.connect() as connection:
            yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def health_check() -> dict:
    """
    Perform a comprehensive database health check.
    
    Returns:
        dict: Health check results
    """
    try:
        start_time = time.time()
        
        # Test basic connection
        with db_connection() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            
        connection_time = time.time() - start_time
        
        # Test session operations with a simple query
        start_time = time.time()
        test_result = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()
        session_time = time.time() - start_time
        
        return {
            'status': 'healthy',
            'connection_test': result == 1,
            'connection_time_ms': round(connection_time * 1000, 2),
            'session_test': test_result >= 0,
            'session_time_ms': round(session_time * 1000, 2),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        } 