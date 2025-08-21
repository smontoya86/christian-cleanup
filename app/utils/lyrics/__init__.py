"""
Lyrics processing utilities for Christian Cleanup application.

This module provides lyrics fetching, caching, and processing functionality
for analyzing song content.
"""

from ..lyrics_config import LyricsFetcherConfig
from .exceptions import (
    LyricsFetcherException,
    LyricsNotFoundException,
    LyricsProviderException,
    RateLimitException,
)
from .lyrics_fetcher import (
    GeniusProvider,
    LRCLibProvider,
    LyricsFetcher,
    LyricsOvhProvider,
    LyricsProvider,
    RateLimitTracker,
    TokenBucket,
)

__all__ = [
    "LyricsFetcher",
    "LyricsFetcherConfig",
    "LyricsProvider",
    "LRCLibProvider",
    "LyricsOvhProvider",
    "GeniusProvider",
    "TokenBucket",
    "RateLimitTracker",
    "LyricsFetcherException",
    "LyricsProviderException",
    "RateLimitException",
    "LyricsNotFoundException",
]

# Provide time module re-export for tests that patch 'app.utils.lyrics.time.*'
import datetime as datetime  # noqa: F401
import random as random  # noqa: F401
import time as time  # noqa: F401

import lyricsgenius as lyricsgenius  # noqa: F401

# Re-export commonly patched modules for tests targeting 'app.utils.lyrics.*'
import requests as requests  # noqa: F401
