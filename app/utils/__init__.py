"""
Utilities Package - Common Helper Functions and Tools for Christian Music Curation Application.

This package provides reusable utility functions, helper classes, and tools that
support various aspects of the application including data processing, formatting,
analysis, caching, and system monitoring. These utilities are designed to be
lightweight, focused, and reusable across different parts of the application.

Key Utility Categories:
    - Data Formatting: Functions for formatting data for display and processing
    - Analysis Tools: Content analysis engines and scoring algorithms
    - Caching: Redis-based caching utilities and cache management
    - Database: Database query helpers and optimization tools
    - Error Handling: Error tracking, logging, and recovery utilities
    - Lyrics Processing: Lyrics fetching, parsing, and content extraction
    - Monitoring: Performance monitoring and metrics collection
    - Biblical References: Scripture detection and biblical theme analysis

Common Patterns:
    Most utilities follow consistent patterns:
    - Pure functions where possible for predictability
    - Graceful error handling with meaningful defaults
    - Comprehensive logging for debugging and monitoring
    - Type annotations for better development experience
    - Configurable behavior through parameters

Performance Considerations:
    - Utilities are optimized for frequent use
    - Caching strategies implemented where beneficial
    - Lazy loading for expensive operations
    - Memory-efficient data structures
    - Minimal external dependencies

Examples:
    Time formatting utilities:
        >>> from app.utils import format_ms_filter
        >>> duration = format_ms_filter(123456)  # Returns "02:03"

    Cache utilities:
        >>> from app.utils.cache import get_cached, set_cached
        >>> cached_data = get_cached('key', fetch_function, timeout=3600)

Dependencies:
    - Redis: Caching and session storage
    - SQLAlchemy: Database utilities and query optimization
    - Flask: Application context and configuration access
    - Various analysis libraries: Natural language processing and pattern matching
"""


def format_ms_filter(ms):
    """
    Convert milliseconds to a human-readable MM:SS time format.

    This utility function formats song duration from milliseconds (as provided
    by Spotify API) into a user-friendly minutes:seconds format for display
    in templates and user interfaces.

    Args:
        ms (int, str, or None): Duration in milliseconds to format.
            Can be an integer, string representation of an integer, or None.

    Returns:
        str: Formatted time string in "MM:SS" format, or "N/A" for invalid input.

    Examples:
        >>> format_ms_filter(123456)
        '02:03'
        >>> format_ms_filter(60000)
        '01:00'
        >>> format_ms_filter(None)
        'N/A'
        >>> format_ms_filter("invalid")
        'N/A'
        >>> format_ms_filter(0)
        '00:00'

    Note:
        This function is commonly used as a Jinja2 template filter for
        displaying song durations in the user interface. It handles
        edge cases gracefully by returning "N/A" for invalid input.
    """
    if ms is None:
        return "N/A"
    try:
        ms = int(ms)
    except (ValueError, TypeError):
        return "N/A"  # Or some other placeholder for invalid input

    seconds = int((ms / 1000) % 60)
    minutes = int((ms / (1000 * 60)) % 60)
    # hours = int((ms / (1000 * 60 * 60)) % 24)  # Uncomment if you need hours

    return f"{minutes:02d}:{seconds:02d}"
