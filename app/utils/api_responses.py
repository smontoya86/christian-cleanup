"""
Standardized API response utilities for consistent error handling and responses.

This module provides utilities for generating consistent API responses,
especially for error conditions, with proper HTTP status codes, error IDs,
and structured response formats.
"""

import uuid
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, List
from flask import jsonify, current_app, request, g
import logging

logger = logging.getLogger(__name__)


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Generate a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        meta: Optional metadata
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "status": "success",
        "data": data,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if meta:
        response["meta"] = meta
        
    return jsonify(response), status_code


def error_response(
    status_code: int,
    message: str,
    error_type: str = None,
    details: Any = None,
    error_id: str = None,
    request_id: str = None,
    force_include_details: bool = False
) -> tuple:
    """
    Generate a standardized error response.
    
    Args:
        status_code: HTTP status code
        message: User-friendly error message
        error_type: Type/category of error
        details: Additional error details (only in development)
        error_id: Unique identifier for the error
        request_id: Request identifier for tracing
        force_include_details: Force inclusion of details regardless of config
        
    Returns:
        Tuple of (response, status_code)
    """
    if error_id is None:
        error_id = str(uuid.uuid4())
    
    if request_id is None:
        try:
            request_id = getattr(g, "request_id", None)
        except RuntimeError:
            # No application context
            request_id = None
    
    # Always provide a request_id for consistency
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    # Build error response
    response = {
        "status": "error",
        "data": None,
        "message": message,
        "error": {
            "code": status_code,
            "type": error_type or "GenericError",
            "message": message,
            "id": error_id,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    # Include details based on context and environment
    include_details = True  # Default to including details
    if not force_include_details:
        try:
            # In testing, we usually want details for assertions
            # Only exclude details if explicitly in production mode simulation
            is_production_simulation = (
                current_app.config.get("DEBUG") is False and 
                current_app.config.get("TESTING") is False
            )
            
            if is_production_simulation:
                include_details = False
                
        except RuntimeError:
            # No application context, include details for safety (likely in testing)
            include_details = True
    
    if details is not None and include_details:
        response["error"]["details"] = details
    
    return jsonify(response), status_code


def validation_error(
    errors: Union[str, Dict[str, Any], List[str]],
    message: str = "Validation error",
    field: str = None
) -> tuple:
    """
    Helper for validation errors with field-specific details.
    
    Args:
        errors: Validation error details
        message: Error message
        field: Specific field that failed validation
        
    Returns:
        Tuple of (response, status_code)
    """
    details = {"validation_errors": errors}
    if field:
        details["field"] = field
        
    return error_response(
        400,
        message,
        "ValidationError",
        details
    )


def not_found_error(
    resource_type: str,
    resource_id: Union[str, int],
    message: str = None
) -> tuple:
    """
    Helper for resource not found errors.
    
    Args:
        resource_type: Type of resource (e.g., 'Playlist', 'Song')
        resource_id: ID of the resource that wasn't found
        message: Custom error message
        
    Returns:
        Tuple of (response, status_code)
    """
    if message is None:
        message = f"{resource_type} with ID '{resource_id}' not found"
        
    details = {
        "resource_type": resource_type,
        "resource_id": str(resource_id)
    }
    
    return error_response(
        404,
        message,
        "ResourceNotFound",
        details
    )


def unauthorized_error(
    message: str = "Authentication required",
    auth_type: str = "bearer"
) -> tuple:
    """
    Helper for authentication errors.
    
    Args:
        message: Error message
        auth_type: Type of authentication required
        
    Returns:
        Tuple of (response, status_code)
    """
    details = {"auth_type": auth_type}
    
    return error_response(
        401,
        message,
        "AuthenticationError",
        details
    )


def forbidden_error(
    message: str = "Access denied",
    required_permission: str = None
) -> tuple:
    """
    Helper for authorization errors.
    
    Args:
        message: Error message
        required_permission: Permission required for access
        
    Returns:
        Tuple of (response, status_code)
    """
    details = None
    if required_permission:
        details = {"required_permission": required_permission}
        
    return error_response(
        403,
        message,
        "AuthorizationError",
        details
    )


def rate_limit_error(
    message: str = "Rate limit exceeded",
    retry_after: int = None,
    limit: int = None,
    remaining: int = None
) -> tuple:
    """
    Helper for rate limiting errors.
    
    Args:
        message: Error message
        retry_after: Seconds to wait before retrying
        limit: Rate limit threshold
        remaining: Remaining requests in current window
        
    Returns:
        Tuple of (response, status_code)
    """
    details = {}
    if retry_after is not None:
        details["retry_after"] = retry_after
    if limit is not None:
        details["limit"] = limit
    if remaining is not None:
        details["remaining"] = remaining
    
    # Only pass details if there are actual details to include    
    details_to_pass = details if details else None
        
    return error_response(
        429,
        message,
        "RateLimitError",
        details_to_pass
    )


def server_error(
    exception: Exception,
    message: str = "An unexpected error occurred",
    include_traceback: bool = None
) -> tuple:
    """
    Helper for server errors with automatic logging.
    
    Args:
        exception: The exception that caused the error
        message: User-friendly error message
        include_traceback: Whether to include traceback in response
        
    Returns:
        Tuple of (response, status_code)
    """
    error_id = str(uuid.uuid4())
    
    # Log the error with full details
    logger.error(
        f"Server error {error_id}: {str(exception)}",
        extra={
            'error_id': error_id,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc()
        },
        exc_info=True
    )
    
    # Prepare details for response
    details = None
    try:
        debug_mode = current_app.config.get("DEBUG", False)
        testing_mode = current_app.config.get("TESTING", False)
        
        if include_traceback is None:
            include_traceback = debug_mode or testing_mode
            
        if include_traceback:
            details = {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "traceback": traceback.format_exc().split('\n')
            }
    except RuntimeError:
        # No application context
        if include_traceback:
            details = {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            }
    
    return error_response(
        500,
        message,
        "ServerError",
        details,
        error_id
    )


def external_service_error(
    service_name: str,
    error_details: str = None,
    status_code: int = 502,
    retry_possible: bool = True
) -> tuple:
    """
    Helper for external service errors.
    
    Args:
        service_name: Name of the external service
        error_details: Details about the error
        status_code: HTTP status code
        retry_possible: Whether retrying the request might succeed
        
    Returns:
        Tuple of (response, status_code)
    """
    message = f"Error communicating with {service_name}"
    if not retry_possible:
        message += " (retry not recommended)"
        
    details = {
        "service_name": service_name,
        "retry_possible": retry_possible
    }
    
    if error_details:
        details["error_details"] = error_details
        
    return error_response(
        status_code,
        message,
        "ExternalServiceError",
        details,
        force_include_details=True  # Always include details for external service errors
    )


def timeout_error(
    operation: str,
    timeout_duration: float,
    message: str = None
) -> tuple:
    """
    Helper for timeout errors.
    
    Args:
        operation: Description of the operation that timed out
        timeout_duration: Timeout duration in seconds
        message: Custom error message
        
    Returns:
        Tuple of (response, status_code)
    """
    if message is None:
        message = f"Operation '{operation}' timed out after {timeout_duration}s"
        
    details = {
        "operation": operation,
        "timeout_duration": timeout_duration
    }
    
    return error_response(
        408,
        message,
        "TimeoutError",
        details,
        force_include_details=True  # Always include details for timeout errors
    )


def conflict_error(
    message: str = "Resource conflict",
    conflicting_resource: str = None,
    conflict_reason: str = None
) -> tuple:
    """
    Helper for resource conflict errors.
    
    Args:
        message: Error message
        conflicting_resource: Description of conflicting resource
        conflict_reason: Reason for the conflict
        
    Returns:
        Tuple of (response, status_code)
    """
    details = {}
    if conflicting_resource:
        details["conflicting_resource"] = conflicting_resource
    if conflict_reason:
        details["conflict_reason"] = conflict_reason
    
    # Only pass details if there are actual details to include    
    details_to_pass = details if details else None
    # Force include details when we have meaningful information
    force_details = bool(details)
        
    return error_response(
        409,
        message,
        "ConflictError",
        details_to_pass,
        force_include_details=force_details
    ) 