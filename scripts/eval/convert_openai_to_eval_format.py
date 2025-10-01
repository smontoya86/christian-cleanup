#!/usr/bin/env python3
"""
Convert OpenAI fine-tuning format back to eval format for testing.
"""

import json
import re
from pathlib import Path

def extract_from_user_message(content: str):
    """Extract title, artist, and lyrics from user message."""
    # Pattern: Title: X\nArtist: Y\n\nLyrics:\n...
    title_match = re.search(r'Title:\s*(.+?)\n', content)
    artist_match = re.search(r'Artist:\s*(.+?)\n', content)
    lyrics_match = re.search(r'Lyrics:\s*(.+?)(?:\n\nProvide|$)', content, re.DOTALL)
    
    return {
        'title': title_match.group(1).strip() if title_match else '',
        'artist': artist_match.group(1).strip() if artist_match else '',
        'lyrics': lyrics_match.group(1).strip() if lyrics_match else ''
    }

def convert_openai_to_eval(input_file: str, output_file: str):
    """Convert OpenAI format to eval format."""
    print(f"📥 Loading OpenAI format from: {input_file}")
    
    converted = []
    with open(input_file, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            messages = data.get('messages', [])
            
            # Extract user message (contains title/artist/lyrics)
            user_msg = next((m for m in messages if m['role'] == 'user'), None)
            if not user_msg:
                print(f"  ⚠️  Skipping entry without user message")
                continue
            
            # Extract assistant message (contains label/expected output)
            assistant_msg = next((m for m in messages if m['role'] == 'assistant'), None)
            if not assistant_msg:
                print(f"  ⚠️  Skipping entry without assistant message")
                continue
            
            # Parse data
            song_data = extract_from_user_message(user_msg['content'])
            
            try:
                label = json.loads(assistant_msg['content'])
            except json.JSONDecodeError:
                print(f"  ⚠️  Failed to parse label for {song_data['title']}")
                continue
            
            # Build eval format
            eval_entry = {
                'title': song_data['title'],
                'artist': song_data['artist'],
                'lyrics': song_data['lyrics'],
                'labels': label  # Changed from 'label' to 'labels' to match run_eval.py
            }
            
            converted.append(eval_entry)
    
    # Write to output
    print(f"📤 Writing {len(converted)} songs to: {output_file}")
    with open(output_file, 'w') as f:
        for entry in converted:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✅ Conversion complete! {len(converted)} songs converted.")
    print(f"\nSample entry:")
    print(f"  Title: {converted[0]['title']}")
    print(f"  Artist: {converted[0]['artist']}")
    print(f"  Label Score: {converted[0]['labels'].get('score')}")
    print(f"  Label Verdict: {converted[0]['labels'].get('verdict')}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python convert_openai_to_eval_format.py <input_openai.jsonl> <output_eval.jsonl>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_openai_to_eval(input_file, output_file)

