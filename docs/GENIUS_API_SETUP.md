# Genius API Setup Guide

## Overview
The Christian Music Curator already has comprehensive Genius API integration built-in. This guide explains how to configure and test it.

## Quick Setup

### 1. Get Genius API Token
1. Visit [Genius API Documentation](https://docs.genius.com/)
2. Sign up for a free account
3. Create a new API client
4. Copy your **Client Access Token**

### 2. Configure Environment
Add your Genius token to your environment configuration:

```bash
# For local development - add to .env file
GENIUS_ACCESS_TOKEN=your_genius_token_here

# For Docker - add to docker-compose.yml env section
GENIUS_ACCESS_TOKEN=your_genius_token_here
```

### 3. Provider Chain (Already Configured)
The system uses a smart fallback chain:
1. **LRCLib** - Primary (free, time-synced, no API key needed)
2. **Lyrics.ovh** - Secondary (free, simple API)
3. **Genius** - Tertiary (requires token, comprehensive database)

## Testing Your Setup

### Test Lyrics Fetching
```python
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher

# Create fetcher (will auto-detect Genius token)
fetcher = LyricsFetcher()

# Test lyrics fetching
lyrics = fetcher.fetch_lyrics("Amazing Grace", "Chris Tomlin")
if lyrics:
    print("✅ Genius API working!")
    print(f"Found lyrics: {len(lyrics)} characters")
else:
    print("❌ No lyrics found - check your token")
```

### Check Provider Status
```python
# Check which providers are available
provider_stats = fetcher.get_provider_stats()
print("Available providers:", list(provider_stats.keys()))

# Check if Genius is configured
if 'GeniusProvider' in provider_stats:
    print("✅ Genius provider active")
else:
    print("❌ Genius provider not available - check token")
```

## Current Implementation Features

### ✅ Already Implemented
- **Multi-provider fallback** (LRCLib → Lyrics.ovh → Genius)
- **Smart rate limiting** with token bucket algorithm
- **Database caching** with configurable TTL
- **Lyrics cleaning** (removes timestamps, annotations, etc.)
- **Error handling** with retry logic
- **Performance metrics** and logging
- **Configuration management** via environment variables

### 🎯 Provider Advantages
- **LRCLib**: Time-synced lyrics, no rate limits, free
- **Lyrics.ovh**: Simple, reliable, free  
- **Genius**: Comprehensive database, detailed metadata

### ⚙️ Smart Configuration
The system automatically:
- Detects available API tokens
- Configures provider chain based on availability
- Uses optimal timeouts and retry settings
- Cleans and normalizes lyrics text
- Caches results to minimize API calls

## Production Deployment

### Environment Variables
```bash
# Required for Genius (optional - system works without it)
GENIUS_ACCESS_TOKEN=your_token_here

# Optional configuration (defaults are good)
LYRICS_CACHE_MAX_AGE_DAYS=30
LYRICS_RETRY_MAX_ATTEMPTS=3
LYRICS_RETRY_BACKOFF_FACTOR=2
```

### Docker Configuration
Add to your `docker-compose.yml`:
```yaml
services:
  web:
    environment:
      - GENIUS_ACCESS_TOKEN=${GENIUS_ACCESS_TOKEN}
```

## Benefits of Current Implementation

1. **Resilient**: Works even without Genius token (fallback providers)
2. **Efficient**: Smart caching reduces API calls
3. **Fast**: Optimized provider chain (fastest sources first)
4. **Clean**: Advanced text processing for better analysis
5. **Monitored**: Built-in metrics and error tracking

## Conclusion

The Genius API integration is **already complete and production-ready**. Simply add your token to enable the Genius provider as a tertiary fallback source. The system will work excellently even without it thanks to the robust multi-provider architecture.

**Status**: ✅ **COMPLETE** - No additional development needed! 