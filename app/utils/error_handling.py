"""
Error handling utilities for analysis routes and other application endpoints.

This module provides standardized error handling, logging, and response formatting
for consistent error management across the application.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Tuple, Union
from flask import jsonify, flash, redirect, url_for, request, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db

# Custom exception classes for analysis-related errors
class AnalysisError(Exception):
    """Base exception for analysis-related errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "ANALYSIS_ERROR"
        self.details = details or {}

class LyricsNotFoundError(AnalysisError):
    """Raised when lyrics cannot be retrieved for a song"""
    def __init__(self, message: str = "Lyrics could not be retrieved", **kwargs):
        super().__init__(message, error_code="LYRICS_NOT_FOUND", **kwargs)

class AnalysisTimeoutError(AnalysisError):
    """Raised when analysis operation times out"""
    def __init__(self, message: str = "Analysis operation timed out", **kwargs):
        super().__init__(message, error_code="ANALYSIS_TIMEOUT", **kwargs)

class UnifiedAnalysisServiceError(AnalysisError):
    """Raised when unified analysis service encounters an error"""
    def __init__(self, message: str = "Analysis service error", **kwargs):
        super().__init__(message, error_code="ANALYSIS_SERVICE_ERROR", **kwargs)

class SpotifyAPIError(AnalysisError):
    """Raised when Spotify API encounters an error"""
    def __init__(self, message: str = "Spotify API error", **kwargs):
        super().__init__(message, error_code="SPOTIFY_API_ERROR", **kwargs)

class DatabaseError(AnalysisError):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)

def log_error_with_context(error: Exception, context: Dict[str, Any] = None) -> None:
    """
    Log an error with comprehensive context information.
    
    Args:
        error: The exception that occurred
        context: Additional context information (user_id, song_id, etc.)
    """
    logger = current_app.logger
    
    # Build context string
    context_str = ""
    if context:
        context_parts = [f"{k}={v}" for k, v in context.items() if v is not None]
        context_str = f" [{', '.join(context_parts)}]"
    
    # Log the error with context
    error_msg = f"{type(error).__name__}: {str(error)}{context_str}"
    logger.error(error_msg)
    
    # Log stack trace for debugging
    if hasattr(error, '__traceback__') and error.__traceback__:
        tb_str = ''.join(traceback.format_tb(error.__traceback__))
        logger.debug(f"Stack trace for {type(error).__name__}:\n{tb_str}")

def create_error_response(
    error: Exception,
    context: Dict[str, Any] = None,
    user_message: str = None,
    status_code: int = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response for API endpoints.
    
    Args:
        error: The exception that occurred
        context: Additional context (song_id, playlist_id, etc.)
        user_message: Custom user-friendly message
        status_code: HTTP status code override
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    # Determine default status code based on error type
    if status_code is None:
        if isinstance(error, LyricsNotFoundError):
            status_code = 404
        elif isinstance(error, AnalysisTimeoutError):
            status_code = 504
        elif isinstance(error, SpotifyAPIError):
            status_code = 502
        elif isinstance(error, DatabaseError):
            status_code = 500
        elif isinstance(error, AnalysisError):
            status_code = 400
        elif isinstance(error, HTTPException):
            status_code = error.code
        else:
            status_code = 500
    
    # Create error response
    response = {
        "success": False,
        "error": True,
        "error_type": type(error).__name__,
        "message": user_message or str(error),
        "timestamp": context.get('timestamp') if context else None
    }
    
    # Add error code for AnalysisError instances
    if isinstance(error, AnalysisError):
        response["error_code"] = error.error_code
        if error.details:
            response["details"] = error.details
    
    # Add context if provided
    if context:
        response["context"] = {k: v for k, v in context.items() if k != 'timestamp'}
    
    # Log the error
    log_error_with_context(error, context)
    
    return response, status_code

def handle_analysis_route_error(
    error: Exception,
    context: Dict[str, Any] = None,
    success_redirect: str = None,
    error_redirect: str = None
) -> Union[Tuple[Dict, int], str]:
    """
    Handle errors in analysis routes with proper response based on request type.
    
    Args:
        error: The exception that occurred
        context: Context information
        success_redirect: URL to redirect to on success (for non-AJAX)
        error_redirect: URL to redirect to on error (for non-AJAX)
        
    Returns:
        JSON response for AJAX requests, redirect for form submissions
    """
    # Rollback database session on any error
    try:
        db.session.rollback()
    except Exception as rollback_error:
        current_app.logger.error(f"Failed to rollback database session: {rollback_error}")
    
    # Determine user-friendly message
    user_message = str(error)
    if isinstance(error, LyricsNotFoundError):
        user_message = "Could not retrieve lyrics for this song. Analysis may be limited."
    elif isinstance(error, AnalysisTimeoutError):
        user_message = "Analysis is taking longer than expected. Please try again later."
    elif isinstance(error, SpotifyAPIError):
        user_message = "Spotify service is temporarily unavailable. Please try again later."
    elif isinstance(error, DatabaseError):
        user_message = "A database error occurred. Please try again."
    elif isinstance(error, UnifiedAnalysisServiceError):
        user_message = "Analysis service encountered an error. Please try again."
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        # Return JSON response for AJAX requests
        response, status_code = create_error_response(error, context, user_message)
        return jsonify(response), status_code
    else:
        # Flash message and redirect for form submissions
        flash(user_message, 'error')
        
        # Determine redirect URL
        if error_redirect:
            return redirect(error_redirect)
        elif context and 'playlist_id' in context:
            return redirect(url_for('main.playlist_detail', playlist_id=context['playlist_id']))
        else:
            return redirect(url_for('main.dashboard'))

def safe_analysis_operation(
    operation_func,
    operation_name: str,
    context: Dict[str, Any] = None,
    success_redirect: str = None,
    error_redirect: str = None
):
    """
    Safely execute an analysis operation with comprehensive error handling.
    
    Args:
        operation_func: The function to execute
        operation_name: Name of the operation for logging
        context: Context information
        success_redirect: URL to redirect to on success
        error_redirect: URL to redirect to on error
        
    Returns:
        Operation result or error response
    """
    operation_context = context or {}
    operation_context['operation'] = operation_name
    
    try:
        current_app.logger.info(f"Starting {operation_name}", extra=operation_context)
        result = operation_func()
        current_app.logger.info(f"Completed {operation_name} successfully", extra=operation_context)
        return result
        
    except LyricsNotFoundError as e:
        return handle_analysis_route_error(e, operation_context, success_redirect, error_redirect)
        
    except AnalysisTimeoutError as e:
        return handle_analysis_route_error(e, operation_context, success_redirect, error_redirect)
        
    except SpotifyAPIError as e:
        return handle_analysis_route_error(e, operation_context, success_redirect, error_redirect)
        
    except UnifiedAnalysisServiceError as e:
        return handle_analysis_route_error(e, operation_context, success_redirect, error_redirect)
        
    except SQLAlchemyError as e:
        db_error = DatabaseError(f"Database operation failed: {str(e)}")
        return handle_analysis_route_error(db_error, operation_context, success_redirect, error_redirect)
        
    except Exception as e:
        # Catch-all for unexpected errors
        analysis_error = AnalysisError(f"Unexpected error in {operation_name}: {str(e)}")
        return handle_analysis_route_error(analysis_error, operation_context, success_redirect, error_redirect)

def validate_analysis_request(song_id: int = None, playlist_id: str = None, user_id: int = None) -> Dict[str, Any]:
    """
    Validate common analysis request parameters.
    
    Args:
        song_id: Song ID to validate
        playlist_id: Playlist ID to validate  
        user_id: User ID to validate
        
    Returns:
        Validation context dictionary
        
    Raises:
        AnalysisError: If validation fails
    """
    context = {}
    
    if song_id is not None:
        if not isinstance(song_id, int) or song_id <= 0:
            raise AnalysisError(f"Invalid song ID: {song_id}")
        context['song_id'] = song_id
    
    if playlist_id is not None:
        if not isinstance(playlist_id, str) or not playlist_id.strip():
            raise AnalysisError(f"Invalid playlist ID: {playlist_id}")
        context['playlist_id'] = playlist_id
    
    if user_id is not None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise AnalysisError(f"Invalid user ID: {user_id}")
        context['user_id'] = user_id
    
    return context

# Decorator for route error handling
def handle_route_errors(success_redirect: str = None, error_redirect: str = None):
    """
    Decorator to automatically handle errors in route functions.
    
    Args:
        success_redirect: URL to redirect to on success
        error_redirect: URL to redirect to on error
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'route': func.__name__,
                    'args': str(args) if args else None,
                    'kwargs': str(kwargs) if kwargs else None
                }
                return handle_analysis_route_error(e, context, success_redirect, error_redirect)
        return wrapper
    return decorator 