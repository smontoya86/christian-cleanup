"""
Global error handlers for Flask application.

This module provides centralized error handling for the Flask application,
ensuring consistent error responses and proper logging of exceptions.
It integrates with the standardized API response utilities.
"""

import logging

import requests
from flask import Flask, request
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    TooManyRequests,
    Unauthorized,
)

from .api_responses import (
    conflict_error,
    error_response,
    external_service_error,
    forbidden_error,
    not_found_error,
    rate_limit_error,
    server_error,
    timeout_error,
    unauthorized_error,
    validation_error,
)
from .validation.exceptions import ValidationError as CustomValidationError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for the Flask application.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(400)
    def handle_bad_request(error: BadRequest):
        """Handle 400 Bad Request errors."""
        return error_response(
            400,
            "Bad request - invalid input provided",
            "BadRequestError",
            {"description": error.description} if error.description else None,
        )

    @app.errorhandler(401)
    def handle_unauthorized(error: Unauthorized):
        """Handle 401 Unauthorized errors."""
        return unauthorized_error(
            message="Authentication required",
        )

    @app.errorhandler(403)
    def handle_forbidden(error: Forbidden):
        """Handle 403 Forbidden errors."""
        return forbidden_error(message="Access denied - insufficient permissions")

    @app.errorhandler(404)
    def handle_not_found(error: NotFound):
        """Handle 404 Not Found errors."""
        # Try to determine the resource type from the request path
        resource_type = "Resource"
        resource_id = "unknown"

        # Extract resource info from request path if possible
        if request and request.path:
            path_parts = request.path.strip("/").split("/")
            if len(path_parts) >= 2:
                resource_type = (
                    path_parts[-2].rstrip("s").title()
                )  # Remove trailing 's' and capitalize
                resource_id = path_parts[-1]

        return not_found_error(
            resource_type=resource_type,
            resource_id=resource_id,
            message="The requested resource was not found",
        )

    @app.errorhandler(409)
    def handle_conflict(error: Conflict):
        """Handle 409 Conflict errors."""
        return conflict_error(
            message="Resource conflict occurred",
            conflict_reason=error.description if error.description else None,
        )

    @app.errorhandler(429)
    def handle_rate_limit(error: TooManyRequests):
        """Handle 429 Too Many Requests errors."""
        retry_after = None
        if hasattr(error, "retry_after"):
            retry_after = error.retry_after

        return rate_limit_error(
            message="Too many requests - please try again later", retry_after=retry_after
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        allowed_methods = error.valid_methods if hasattr(error, "valid_methods") else None

        details = {"allowed_methods": list(allowed_methods)} if allowed_methods else None

        return error_response(
            status_code=405,
            message=f"Method {request.method} not allowed for this endpoint",
            error_type="MethodNotAllowed",
            details=details,
        )

    @app.errorhandler(500)
    def handle_internal_server_error(error: Exception):
        """Handle 500 Internal Server Error."""
        # Log the full traceback for internal errors
        logger.error(
            f"Internal server error on {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "user_agent": request.headers.get("User-Agent"),
                "remote_addr": request.remote_addr,
            },
            exc_info=True,
        )

        return server_error(error, message="An unexpected error occurred")

    @app.errorhandler(CustomValidationError)
    def handle_validation_exception(error: CustomValidationError):
        """Handle custom validation exceptions."""
        return validation_error(
            errors=error.errors, message=error.message, field=getattr(error, "field", None)
        )

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_validation_error(error: MarshmallowValidationError):
        """Handle Marshmallow validation errors."""
        return validation_error(errors=error.messages, message="Request validation failed")

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error: SQLAlchemyError):
        """Handle SQLAlchemy database errors."""
        logger.error(
            f"Database error on {request.method} {request.path}: {str(error)}",
            extra={
                "method": request.method,
                "path": request.path,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )

        # Don't expose internal database errors to clients
        return server_error(error, message="A database error occurred")

    @app.errorhandler(requests.exceptions.RequestException)
    def handle_requests_error(error: requests.exceptions.RequestException):
        """Handle requests library errors (external API calls)."""
        service_name = "external service"
        retry_possible = True

        # Try to extract service name from request URL if available
        if hasattr(error, "request") and error.request and error.request.url:
            url = error.request.url
            if "spotify.com" in url:
                service_name = "Spotify"
            elif "genius.com" in url:
                service_name = "Genius"
            elif "api.bible" in url:
                service_name = "Bible API"

        # Determine if retry is possible based on error type
        if isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
            retry_possible = True
        elif isinstance(error, requests.exceptions.HTTPError):
            # Check status code if available
            if hasattr(error, "response") and error.response:
                status_code = error.response.status_code
                # Don't retry on client errors (except rate limits)
                if 400 <= status_code < 500 and status_code != 429:
                    retry_possible = False

        logger.warning(
            f"External API error for {service_name}: {str(error)}",
            extra={
                "service_name": service_name,
                "error_type": type(error).__name__,
                "retry_possible": retry_possible,
            },
        )

        return external_service_error(
            service_name=service_name, error_details=str(error), retry_possible=retry_possible
        )

    @app.errorhandler(TimeoutError)
    def handle_timeout_error(error: TimeoutError):
        """Handle timeout errors."""
        operation = "unknown operation"

        # Try to determine operation from request context
        if request and request.endpoint:
            operation = request.endpoint.replace("_", " ")

        return timeout_error(
            operation=operation,
            timeout_duration=30.0,  # Default timeout duration
            message=f"Request timed out during {operation}",
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception):
        """Handle any unhandled exceptions."""
        # Log the unexpected exception
        logger.error(
            f"Unhandled exception on {request.method} {request.path}: {str(error)}",
            extra={
                "method": request.method,
                "path": request.path,
                "exception_type": type(error).__name__,
                "user_agent": request.headers.get("User-Agent"),
                "remote_addr": request.remote_addr,
            },
            exc_info=True,
        )

        return server_error(error, message="An unexpected error occurred")


def create_error_response_for_api(status_code: int, message: str, **kwargs):
    """
    Create a standardized error response for API endpoints.

    This is a helper function for manual error creation in route handlers.

    Args:
        status_code: HTTP status code
        message: Error message
        **kwargs: Additional error details

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(status_code, message, **kwargs)


def log_error_context(error: Exception, additional_context: dict = None):
    """
    Log error with additional context information.

    Args:
        error: Exception that occurred
        additional_context: Additional context to include in logs
    """
    context = {
        "method": request.method if request else None,
        "path": request.path if request else None,
        "user_agent": request.headers.get("User-Agent") if request else None,
        "remote_addr": request.remote_addr if request else None,
        "exception_type": type(error).__name__,
        "exception_message": str(error),
    }

    if additional_context:
        context.update(additional_context)

    logger.error(f"Error occurred: {str(error)}", extra=context, exc_info=True)
