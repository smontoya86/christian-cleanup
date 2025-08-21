"""
Lyrics-related exceptions for the Christian Cleanup application.
"""


class LyricsFetcherException(Exception):
    """Base exception for lyrics fetcher operations."""

    pass


class LyricsProviderException(LyricsFetcherException):
    """Exception raised by lyrics providers."""

    pass


class RateLimitException(LyricsFetcherException):
    """Exception raised when rate limits are exceeded."""

    pass


class LyricsNotFoundException(LyricsFetcherException):
    """Exception raised when lyrics cannot be found."""

    pass
