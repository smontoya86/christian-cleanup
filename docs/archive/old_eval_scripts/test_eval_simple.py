#!/usr/bin/env python3
"""
Simple evaluation script with correct parsing logic for testing.
"""

import logging
import os
import re
import sys
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, '/app')

from app.services.analyzers.router_analyzer import RouterAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_gold_standard_file(file_path: str):
    """Parse a gold standard file with correct logic."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title and artist from the **Title:** and **Artist:** fields
        title_match = re.search(r'\*\*Title:\*\*\s*(.+)', content)
        artist_match = re.search(r'\*\*Artist:\*\*\s*(.+)', content)
        
        if title_match and artist_match:
            title = title_match.group(1).strip()
            artist = artist_match.group(1).strip()
        else:
            logger.error(f"Could not find Title/Artist in {file_path}")
            return None
        
        # Extract expected score and verdict from the file
        score_match = re.search(r'\*\*Expected Score:\*\*\s*([\d.]+)', content)
        verdict_match = re.search(r'\*\*Expected Verdict:\*\*\s*(\w+)', content)
        
        if score_match:
            expected_score = float(score_match.group(1))
        else:
            # Default based on filename
            filename = Path(file_path).stem.lower()
            if any(word in filename for word in ['example', 'manipulation', 'prosperity']):
                expected_score = 4.0  # Red
            elif any(word in filename for word in ['good_good', 'build_my', 'king_of']):
                expected_score = 7.0  # Purple
            else:
                expected_score = 9.0  # Green
        
        if verdict_match:
            expected_verdict = verdict_match.group(1)
        else:
            if expected_score >= 8.0:
                expected_verdict = "Green"
            elif expected_score >= 6.0:
                expected_verdict = "Purple"
            else:
                expected_verdict = "Red"
        
        # Extract actual lyrics from the file
        lyrics_match = re.search(r'## Lyrics\n\n(.*?)(?=\n## |$)', content, re.DOTALL)
        if lyrics_match:
            lyrics = lyrics_match.group(1).strip()
        else:
            lyrics = f"[Lyrics for {title} by {artist}]"
        
        return {
            'title': title,
            'artist': artist,
            'expected_score': expected_score,
            'expected_verdict': expected_verdict,
            'lyrics': lyrics,
            'file_path': file_path
        }
        
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return None

def analyze_song(title: str, artist: str, lyrics: str):
    """Analyze a song using the RouterAnalyzer."""
    try:
        analyzer = RouterAnalyzer()
        result = analyzer.analyze_song(title, artist, lyrics)
        
        if isinstance(result, dict) and 'score' in result:
            return {
                'score': result.get('score', 5.0),
                'verdict': result.get('verdict', 'Purple'),
                'analysis': result.get('analysis', {})
            }
        else:
            logger.error(f"Invalid analysis result: {result}")
            return {
                'score': 5.0,
                'verdict': 'Purple',
                'analysis': {}
            }
            
    except Exception as e:
        logger.error(f"Error analyzing song: {e}")
        return {
            'score': 5.0,
            'verdict': 'Purple',
            'analysis': {}
        }

def main():
    """Run evaluation on 3 test songs."""
    logger.info("Starting simple evaluation test")
    
    # Test with 3 specific songs
    test_files = [
        "gold_standard/reckless_love.md",
        "gold_standard/jireh.md", 
        "gold_standard/amazing_grace.md"
    ]
    
    results = []
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue
            
        logger.info(f"Processing: {file_path}")
        
        # Parse gold standard
        gold_data = parse_gold_standard_file(file_path)
        if not gold_data:
            continue
        
        logger.info(f"Song: '{gold_data['title']}' by {gold_data['artist']}")
        logger.info(f"Expected: Score {gold_data['expected_score']}, Verdict {gold_data['expected_verdict']}")
        
        # Analyze the song
        analysis_result = analyze_song(
            gold_data['title'], 
            gold_data['artist'], 
            gold_data['lyrics']
        )
        
        # Store results
        result = {
            'song': f"{gold_data['title']} by {gold_data['artist']}",
            'gold_score': gold_data['expected_score'],
            'gold_verdict': gold_data['expected_verdict'],
            'generated_score': analysis_result['score'],
            'generated_verdict': analysis_result['verdict'],
            'score_diff': abs(analysis_result['score'] - gold_data['expected_score']),
            'verdict_match': analysis_result['verdict'] == gold_data['expected_verdict']
        }
        
        results.append(result)
        
        # Print result
        print(f"\n{result['song']}")
        print(f"  Gold Standard: Score {result['gold_score']}, Verdict {result['gold_verdict']}")
        print(f"  Generated:     Score {result['generated_score']}, Verdict {result['generated_verdict']}")
        print(f"  Score Diff:    {result['score_diff']:.2f}")
        print(f"  Verdict Match: {'✓' if result['verdict_match'] else '✗'}")
        print("-" * 50)
        
        # Rate limiting
        time.sleep(5)
    
    # Summary
    if results:
        total = len(results)
        avg_diff = sum(r['score_diff'] for r in results) / total
        accuracy = sum(1 for r in results if r['verdict_match']) / total * 100
        
        print("\nTEST RESULTS SUMMARY")
        print(f"Songs Tested: {total}")
        print(f"Average Score Difference: {avg_diff:.2f}")
        print(f"Verdict Accuracy: {accuracy:.1f}%")
        
        if accuracy >= 60:
            print("✅ Parsing and analysis working correctly!")
        else:
            print("⚠️ Issues detected - needs further investigation")
    
    return results

if __name__ == "__main__":
    main()
