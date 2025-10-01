#!/usr/bin/env python3
"""
Build golden eval set by fetching lyrics and preparing JSONL format.

Usage:
    python scripts/eval/build_golden_set.py --input scripts/eval/golden_eval_starter_50.md --output scripts/eval/golden_eval_150.jsonl
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

from app import create_app
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher


def parse_song_list(md_file: str) -> List[Dict]:
    """Parse markdown file with song list."""
    songs = []
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: number. **title** - artist
    pattern = r'^\d+\.\s+\*\*(.+?)\*\*\s+-\s+(.+?)$'
    
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            title = match.group(1).strip()
            artist = match.group(2).strip()
            
            # Extract expected score/verdict from following lines if present
            songs.append({
                'title': title,
                'artist': artist,
                'lyrics': None,
                'labels': {
                    'verdict': None,
                    'score': None,
                    'concern_flags': [],
                    'scripture_refs': []
                }
            })
    
    return songs


def fetch_lyrics_for_songs(songs: List[Dict]) -> List[Dict]:
    """Fetch lyrics for each song using existing lyrics service."""
    app = create_app()
    with app.app_context():
        fetcher = LyricsFetcher()
        
        for i, song in enumerate(songs):
            print(f"[{i+1}/{len(songs)}] Fetching lyrics for: {song['title']} - {song['artist']}")
            
            try:
                lyrics = fetcher.get_lyrics(song['title'], song['artist'])
                if lyrics:
                    song['lyrics'] = lyrics
                    print(f"  ✅ Found lyrics ({len(lyrics)} chars)")
                else:
                    song['lyrics'] = None
                    print(f"  ⚠️  No lyrics found")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                song['lyrics'] = None
    
    return songs


def write_jsonl(songs: List[Dict], output_file: str):
    """Write songs to JSONL format."""
    written = 0
    skipped = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, song in enumerate(songs):
            if not song['lyrics']:
                print(f"Skipping {song['title']} - no lyrics")
                skipped += 1
                continue
            
            record = {
                'id': f'golden-{i+1:03d}',
                'title': song['title'],
                'artist': song['artist'],
                'lyrics': song['lyrics'],
                'labels': song['labels']
            }
            
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            written += 1
    
    print(f"\n✅ Written {written} songs to {output_file}")
    print(f"⚠️  Skipped {skipped} songs (no lyrics)")


def main():
    parser = argparse.ArgumentParser(description='Build golden eval set')
    parser.add_argument('--input', default='scripts/eval/golden_eval_starter_50.md',
                        help='Input markdown file with song list')
    parser.add_argument('--output', default='scripts/eval/golden_eval_50_unlabeled.jsonl',
                        help='Output JSONL file')
    parser.add_argument('--skip-fetch', action='store_true',
                        help='Skip fetching lyrics (for testing parsing)')
    
    args = parser.parse_args()
    
    print(f"📖 Parsing song list from: {args.input}")
    songs = parse_song_list(args.input)
    print(f"Found {len(songs)} songs\n")
    
    if not args.skip_fetch:
        print("🎵 Fetching lyrics...")
        songs = fetch_lyrics_for_songs(songs)
    
    print(f"\n💾 Writing to: {args.output}")
    write_jsonl(songs, args.output)
    
    print("\n" + "="*60)
    print("Next steps:")
    print("1. Review golden_eval_50_unlabeled.jsonl")
    print("2. Add ground truth labels (verdict, score, concerns, scripture)")
    print("3. Rename to golden_eval_50.jsonl")
    print("4. Run eval: scripts/eval/run_in_container.sh golden_eval_50.jsonl")
    print("="*60)


if __name__ == '__main__':
    main()
