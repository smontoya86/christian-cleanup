"""
Service layer exceptions for the Christian Music Curator application.
Simple error handling without complex hierarchy.
"""


class ServiceException(Exception):
    """Base exception for service layer errors."""

    pass


class RateLimitException(ServiceException):
    """Raised when API rate limits are exceeded."""

    def __init__(self, message, service_name=None, retry_after=None):
        super().__init__(message)
        self.service_name = service_name
        self.retry_after = retry_after


class SpotifyAPIException(ServiceException):
    """Raised when Spotify API errors occur."""

    pass


class AnalysisException(ServiceException):
    """Raised when song analysis fails."""

    pass


class DataException(ServiceException):
    """Raised when data operations fail."""

    pass


class ResourceNotFoundException(ServiceException):
    """Raised when a requested resource is not found."""

    def __init__(self, message, context=None):
        super().__init__(message)
        self.context = context or {}


class ValidationException(ServiceException):
    """Raised when input validation fails."""

    def __init__(self, message, field=None, value=None):
        super().__init__(message)
        self.field = field
        self.value = value


# Aliases for test compatibility
SpotifyAPIError = SpotifyAPIException
