#!/usr/bin/env python3
"""
Simple Lyrics Fetching Test

Test lyrics fetching functionality without database dependencies.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_lyrics_providers():
    """Test lyrics fetching with different providers."""

    print("🔍 Testing Lyrics Fetching Functionality")
    print("=" * 60)

    # Check environment variables
    genius_key = os.getenv("LYRICSGENIUS_API_KEY")
    genius_token = os.getenv("GENIUS_ACCESS_TOKEN")

    print("📋 Environment Variables:")
    print(f"   LYRICSGENIUS_API_KEY: {'✅ Set' if genius_key else '❌ Not set'}")
    print(f"   GENIUS_ACCESS_TOKEN: {'✅ Set' if genius_token else '❌ Not set'}")

    if genius_key and genius_key != "your-genius-api-key-here":
        print(f"   LYRICSGENIUS_API_KEY value: {genius_key[:10]}...")
    if genius_token and genius_token != "your-genius-api-key-here":
        print(f"   GENIUS_ACCESS_TOKEN value: {genius_token[:10]}...")

    # Test individual providers
    print("\n🔧 Testing Individual Providers...")

    # Test LRCLib (no API key required)
    print("\n1. Testing LRCLibProvider (no API key required):")
    try:
        from app.utils.lyrics.lyrics_fetcher import LRCLibProvider

        provider = LRCLibProvider()

        test_songs = [
            ("Amazing Grace", "Chris Tomlin"),
            ("How Great Thou Art", "Chris Tomlin"),
            ("What a Beautiful Name", "Hillsong Worship"),
        ]

        lrclib_success = 0
        for title, artist in test_songs:
            print(f"   Testing: '{title}' by {artist}")
            try:
                lyrics = provider.fetch_lyrics(artist, title)
                if lyrics and len(lyrics.strip()) > 10:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    lrclib_success += 1
                else:
                    print("   ❌ No lyrics found")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        print(f"   LRCLib success rate: {lrclib_success}/{len(test_songs)}")

    except Exception as e:
        print(f"   ❌ Failed to import LRCLibProvider: {e}")

    # Test Lyrics.ovh (no API key required)
    print("\n2. Testing LyricsOvhProvider (no API key required):")
    try:
        from app.utils.lyrics.lyrics_fetcher import LyricsOvhProvider

        provider = LyricsOvhProvider()

        ovh_success = 0
        for title, artist in test_songs:
            print(f"   Testing: '{title}' by {artist}")
            try:
                lyrics = provider.fetch_lyrics(artist, title)
                if lyrics and len(lyrics.strip()) > 10:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    ovh_success += 1
                else:
                    print("   ❌ No lyrics found")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        print(f"   LyricsOvh success rate: {ovh_success}/{len(test_songs)}")

    except Exception as e:
        print(f"   ❌ Failed to import LyricsOvhProvider: {e}")

    # Test Genius (requires API key)
    print("\n3. Testing GeniusProvider (requires API key):")
    if genius_key or genius_token:
        try:
            import lyricsgenius

            from app.utils.lyrics.lyrics_fetcher import GeniusProvider

            token = genius_key or genius_token
            if token and token != "your-genius-api-key-here":
                genius_client = lyricsgenius.Genius(token, verbose=False, timeout=10)
                provider = GeniusProvider(genius_client)

                genius_success = 0
                for title, artist in test_songs:
                    print(f"   Testing: '{title}' by {artist}")
                    try:
                        lyrics = provider.fetch_lyrics(artist, title)
                        if lyrics and len(lyrics.strip()) > 10:
                            print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                            genius_success += 1
                        else:
                            print("   ❌ No lyrics found")
                    except Exception as e:
                        print(f"   ❌ ERROR: {e}")

                print(f"   Genius success rate: {genius_success}/{len(test_songs)}")
            else:
                print("   ❌ Invalid API key (placeholder value)")
        except Exception as e:
            print(f"   ❌ Failed to test Genius: {e}")
    else:
        print("   ❌ No Genius API key available")

    # Test complete LyricsFetcher
    print("\n4. Testing Complete LyricsFetcher:")
    try:
        from app.utils.lyrics.lyrics_fetcher import LyricsFetcher

        fetcher = LyricsFetcher()

        print(f"   Available providers: {len(fetcher.providers)}")
        for i, provider in enumerate(fetcher.providers):
            print(f"      {i+1}. {provider.get_provider_name()}")

        fetcher_success = 0
        for title, artist in test_songs:
            print(f"   Testing: '{title}' by {artist}")
            try:
                lyrics = fetcher.fetch_lyrics(title, artist)
                if lyrics and len(lyrics.strip()) > 10:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    fetcher_success += 1
                else:
                    print("   ❌ No lyrics found")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        print(f"   LyricsFetcher success rate: {fetcher_success}/{len(test_songs)}")

    except Exception as e:
        print(f"   ❌ Failed to test LyricsFetcher: {e}")

    # Recommendations
    print("\n💡 Recommendations:")

    if not genius_key and not genius_token:
        print("   1. ⚠️  Add a Genius API key for better lyrics coverage")
        print("      - Go to https://genius.com/api-clients")
        print("      - Sign up for a free account")
        print("      - Create a new API client")
        print("      - Generate a Client Access Token")
        print("      - Add LYRICSGENIUS_API_KEY=your_token_here to .env")
    elif genius_key == "your-genius-api-key-here" or genius_token == "your-genius-api-key-here":
        print("   1. ⚠️  Replace placeholder Genius API key with real key")
        print("      - The current key is just a placeholder")
        print("      - Get a real key from https://genius.com/api-clients")
    else:
        print("   1. ✅ Genius API key is configured")

    print("   2. 🔄 Even without Genius, LRCLib and LyricsOvh should provide some lyrics")
    print("   3. 🚀 Once working, re-run analysis to fetch missing lyrics")


if __name__ == "__main__":
    test_lyrics_providers()
