#!/usr/bin/env python3
"""
Enhanced evaluation script with dynamic lyrics fetching.
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Add the app directory to the Python path
sys.path.insert(0, '/app')

from app.services.analyzers.router_analyzer import RouterAnalyzer
from app.utils.lyrics_service import get_song_lyrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedEvaluator:
    """Enhanced evaluator with dynamic lyrics fetching."""
    
    def __init__(self):
        self.analyzer = RouterAnalyzer()
        self.rate_limit_delay = 2  # 2 seconds between requests
        
    def parse_gold_standard_file(self, file_path: str) -> Optional[Dict]:
        """Parse a gold standard file and extract metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title and artist from filename or content
            filename = Path(file_path).stem
            
            # Try to extract from content first
            title_match = re.search(r'\*\*Song:\*\*\s*(.+)', content)
            artist_match = re.search(r'\*\*Artist:\*\*\s*(.+)', content)
            score_match = re.search(r'\*\*Expected Score:\*\*\s*([\d.]+)', content)
            verdict_match = re.search(r'\*\*Expected Verdict:\*\*\s*(\w+)', content)
            
            if title_match and artist_match:
                title = title_match.group(1).strip()
                artist = artist_match.group(1).strip()
            else:
                # Fallback to parsing from existing content
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                else:
                    title = filename.replace('_', ' ').title()
                
                # Try to find artist in content
                for line in lines:
                    if ' by ' in line.lower():
                        parts = line.split(' by ')
                        if len(parts) >= 2:
                            artist = parts[1].strip()
                            break
                else:
                    artist = "Unknown Artist"
            
            # Extract expected score and verdict
            if score_match:
                expected_score = float(score_match.group(1))
            else:
                # Try to extract from analysis section
                score_match = re.search(r'Score.*?(\d+\.?\d*)', content)
                expected_score = float(score_match.group(1)) if score_match else 5.0
            
            if verdict_match:
                expected_verdict = verdict_match.group(1)
            else:
                # Determine verdict from score
                if expected_score >= 8.0:
                    expected_verdict = "Green"
                elif expected_score >= 6.0:
                    expected_verdict = "Purple"
                else:
                    expected_verdict = "Red"
            
            return {
                'title': title,
                'artist': artist,
                'expected_score': expected_score,
                'expected_verdict': expected_verdict,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    def fetch_lyrics_with_retry(self, artist: str, title: str, max_retries: int = 3) -> Optional[str]:
        """Fetch lyrics with retry logic and rate limiting."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching lyrics for '{title}' by {artist} (attempt {attempt + 1})")
                lyrics = get_song_lyrics(artist, title)
                
                if lyrics and len(lyrics.strip()) > 50:
                    logger.info(f"Successfully fetched lyrics ({len(lyrics)} characters)")
                    return lyrics
                
                logger.warning("No lyrics found or lyrics too short")
                
            except Exception as e:
                logger.error(f"Error fetching lyrics (attempt {attempt + 1}): {e}")
                
            # Rate limiting delay
            if attempt < max_retries - 1:
                time.sleep(self.rate_limit_delay)
        
        return None
    
    def analyze_song_with_lyrics(self, title: str, artist: str, lyrics: str = None) -> Dict:
        """Analyze a song with optional lyrics fetching."""
        if not lyrics:
            lyrics = self.fetch_lyrics_with_retry(artist, title)
            
        if not lyrics:
            logger.warning(f"Using placeholder lyrics for {title} by {artist}")
            lyrics = f"[Lyrics for {title} by {artist} would be fetched here]"
        
        try:
            result = self.analyzer.analyze_song(title, artist, lyrics)
            
            if isinstance(result, dict) and 'score' in result:
                return {
                    'score': result.get('score', 50),
                    'verdict': result.get('verdict', 'context_required'),
                    'analysis': result.get('analysis', {})
                }
            else:
                logger.error(f"Invalid analysis result format: {result}")
                return {
                    'score': 50,
                    'verdict': 'context_required',
                    'analysis': {}
                }
                
        except Exception as e:
            logger.error(f"Error analyzing song: {e}")
            return {
                'score': 50,
                'verdict': 'context_required',
                'analysis': {}
            }
    
    def run_evaluation(self, gold_standard_dir: str = "gold_standard") -> Dict:
        """Run the complete evaluation with dynamic lyrics fetching."""
        logger.info("Starting enhanced evaluation with dynamic lyrics fetching")
        
        results = []
        gold_files = list(Path(gold_standard_dir).glob("*.md"))
        
        for file_path in gold_files:
            logger.info(f"Processing: {file_path}")
            
            # Parse gold standard file
            gold_data = self.parse_gold_standard_file(str(file_path))
            if not gold_data:
                continue
            
            # Analyze the song
            analysis_result = self.analyze_song_with_lyrics(
                gold_data['title'], 
                gold_data['artist']
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
            
            # Print individual result
            print(f"Evaluating: {result['song']}")
            print(f"  Gold Standard: Score {result['gold_score']}, Verdict: {result['gold_verdict']}")
            print(f"  Generated:     Score {result['generated_score']}, Verdict: {result['generated_verdict']}")
            print("----------------------------------------")
            
            # Rate limiting between songs
            time.sleep(self.rate_limit_delay)
        
        # Calculate metrics
        if results:
            total_songs = len(results)
            avg_score_diff = sum(r['score_diff'] for r in results) / total_songs
            verdict_accuracy = sum(1 for r in results if r['verdict_match']) / total_songs
            score_diffs = [r['score_diff'] for r in results]
            
            metrics = {
                'total_songs': total_songs,
                'avg_score_diff': round(avg_score_diff, 2),
                'verdict_accuracy': round(verdict_accuracy * 100, 1),
                'score_diff_range': f"{min(score_diffs):.2f} - {max(score_diffs):.2f}",
                'results': results
            }
            
            # Print summary
            print("\nEVALUATION METRICS")
            print("=" * 30)
            print(f"Total Songs Evaluated: {metrics['total_songs']}")
            print(f"Average Score Difference: {metrics['avg_score_diff']}")
            print(f"Verdict Accuracy: {metrics['verdict_accuracy']}%")
            print(f"Score Difference Range: {metrics['score_diff_range']}")
            
            if metrics['verdict_accuracy'] >= 80:
                print("✅ EXCELLENT: Analysis system performing very well.")
            elif metrics['verdict_accuracy'] >= 60:
                print("✅ GOOD: Analysis system performing adequately.")
            elif metrics['verdict_accuracy'] >= 40:
                print("⚠️  FAIR: Analysis system needs improvement.")
            else:
                print("❌ POOR: Analysis system requires significant improvement.")
            
            return metrics
        else:
            print("No evaluation results generated.")
            return {}

if __name__ == "__main__":
    evaluator = EnhancedEvaluator()
    evaluator.run_evaluation()
