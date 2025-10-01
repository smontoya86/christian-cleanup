#!/usr/bin/env python3
"""
Fetch lyrics for baseline eval set using existing lyrics service.

Usage:
    docker compose exec web python scripts/eval/fetch_baseline_lyrics.py
"""

import json
import sys
from pathlib import Path

from app import create_app
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher


BASELINE_SONGS = [
    {"id": "baseline-01", "title": "Amazing Grace", "artist": "John Newton", 
     "labels": {"verdict": "freely_listen", "score": 100, "concern_flags": [], "scripture_refs": ["Ephesians 2:8-9"]}},
    {"id": "baseline-02", "title": "Oceans (Where Feet May Fail)", "artist": "Hillsong United",
     "labels": {"verdict": "freely_listen", "score": 92, "concern_flags": [], "scripture_refs": ["Matthew 14:29"]}},
    {"id": "baseline-03", "title": "Reckless Love", "artist": "Cory Asbury",
     "labels": {"verdict": "context_required", "score": 82, "concern_flags": ["Theological Imprecision"], "scripture_refs": ["Luke 15:4-7"]}},
    {"id": "baseline-04", "title": "You Say", "artist": "Lauren Daigle",
     "labels": {"verdict": "context_required", "score": 78, "concern_flags": ["Vague Spirituality"], "scripture_refs": ["1 John 3:1"]}},
    {"id": "baseline-05", "title": "Believer", "artist": "Imagine Dragons",
     "labels": {"verdict": "caution_limit", "score": 58, "concern_flags": ["Self-Focus"], "scripture_refs": []}},
    {"id": "baseline-06", "title": "Fight Song", "artist": "Rachel Platten",
     "labels": {"verdict": "caution_limit", "score": 55, "concern_flags": ["Self-Salvation"], "scripture_refs": []}},
    {"id": "baseline-07", "title": "Imagine", "artist": "John Lennon",
     "labels": {"verdict": "avoid_formation", "score": 35, "concern_flags": ["Anti-Christian Themes"], "scripture_refs": []}},
    {"id": "baseline-08", "title": "Highway to Hell", "artist": "AC/DC",
     "labels": {"verdict": "avoid_formation", "score": 12, "concern_flags": ["Rebellion Against Authority"], "scripture_refs": []}},
    {"id": "baseline-09", "title": "Held", "artist": "Natalie Grant",
     "labels": {"verdict": "context_required", "score": 79, "concern_flags": ["Lament"], "scripture_refs": ["Psalm 34:18"]}},
    {"id": "baseline-10", "title": "Stressed Out", "artist": "Twenty One Pilots",
     "labels": {"verdict": "caution_limit", "score": 60, "concern_flags": ["Despair and Mental Health"], "scripture_refs": []}},
]


def main():
    app = create_app()
    output_file = Path("scripts/eval/baseline_10.jsonl")
    
    with app.app_context():
        fetcher = LyricsFetcher()
        results = []
        
        print("Fetching lyrics for baseline eval set...\n")
        
        for i, song in enumerate(BASELINE_SONGS, 1):
            print(f"[{i}/10] {song['title']} - {song['artist']}")
            
            try:
                lyrics = fetcher.fetch_lyrics(song['title'], song['artist'])
                if lyrics:
                    song['lyrics'] = lyrics
                    results.append(song)
                    print(f"  ✅ Found ({len(lyrics)} chars)")
                else:
                    print(f"  ⚠️  No lyrics found - skipping")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Write JSONL
        print(f"\n💾 Writing {len(results)} songs to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for song in results:
                f.write(json.dumps(song, ensure_ascii=False) + '\n')
        
        print(f"✅ Done! Created baseline eval set with {len(results)}/10 songs")
        print(f"\nNext step: Run eval with:")
        print(f"  LLM_MODEL=qwen3:8b scripts/eval/run_in_container.sh scripts/eval/baseline_10.jsonl")


if __name__ == '__main__':
    main()
