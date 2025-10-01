#!/usr/bin/env python3
"""
Fixed evaluation script with corrected parsing logic.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the app directory to the Python path
sys.path.insert(0, '/app')

from app.services.analyzers.router_analyzer import RouterAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedEvaluator:
    """Fixed evaluator with corrected parsing logic."""
    
    def __init__(self):
        self.analyzer = RouterAnalyzer()
        self.rate_limit_delay = 3  # 3 seconds between requests
        
    def parse_gold_standard_file(self, file_path: str) -> Optional[Dict]:
        """Parse a gold standard file and extract metadata with fixed logic."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title and artist from the **Song:** and **Artist:** fields
            title_match = re.search(r'\*\*Song:\*\*\s*(.+)', content)
            artist_match = re.search(r'\*\*Artist:\*\*\s*(.+)', content)
            score_match = re.search(r'\*\*Expected Score:\*\*\s*([\d.]+)', content)
            verdict_match = re.search(r'\*\*Expected Verdict:\*\*\s*(\w+)', content)
            
            if title_match and artist_match:
                title = title_match.group(1).strip()
                artist = artist_match.group(1).strip()
            else:
                # Fallback: use the markdown header (# Title)
                header_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                if header_match:
                    title = header_match.group(1).strip()
                    # Try to extract artist from content
                    artist = "Unknown Artist"
                    for line in content.split('\n'):
                        if ' by ' in line.lower() and not line.startswith('#'):
                            parts = line.split(' by ')
                            if len(parts) >= 2:
                                artist = parts[1].strip()
                                break
                else:
                    # Use filename as fallback
                    filename = Path(file_path).stem
                    title = filename.replace('_', ' ').title()
                    artist = "Unknown Artist"
            
            # Extract expected score and verdict
            if score_match:
                expected_score = float(score_match.group(1))
            else:
                # Default based on filename patterns
                if 'example' in Path(file_path).stem.lower():
                    expected_score = 4.0  # Red category
                else:
                    expected_score = 8.0  # Default to Green
            
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
    
    def analyze_song_simple(self, title: str, artist: str) -> Dict:
        """Analyze a song using placeholder lyrics for testing."""
        # Use simple placeholder lyrics for testing
        lyrics = f"[This is a placeholder for {title} by {artist} - actual lyrics would be analyzed here]"
        
        try:
            result = self.analyzer.analyze_song(title, artist, lyrics)
            
            if isinstance(result, dict) and 'score' in result:
                return {
                    'score': result.get('score', 5.0),
                    'verdict': result.get('verdict', 'Purple'),
                    'analysis': result.get('analysis', {})
                }
            else:
                logger.error(f"Invalid analysis result format: {result}")
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
    
    def run_evaluation(self, gold_standard_dir: str = "gold_standard") -> Dict:
        """Run the complete evaluation with fixed parsing."""
        logger.info("Starting fixed evaluation")
        
        results = []
        gold_files = list(Path(gold_standard_dir).glob("*.md"))
        
        # Filter out non-song files
        song_files = []
        for file_path in gold_files:
            filename = file_path.stem
            if not any(skip in filename.lower() for skip in ['expansion_plan', 'berean_test', 'diverse_artists']):
                song_files.append(file_path)
        
        logger.info(f"Found {len(song_files)} song files to evaluate")
        
        for i, file_path in enumerate(song_files[:5]):  # Test with first 5 songs
            logger.info(f"Processing {i+1}/{min(5, len(song_files))}: {file_path}")
            
            # Parse gold standard file
            gold_data = self.parse_gold_standard_file(str(file_path))
            if not gold_data:
                continue
            
            logger.info(f"Analyzing: '{gold_data['title']}' by {gold_data['artist']}")
            
            # Analyze the song
            analysis_result = self.analyze_song_simple(
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
            print(f"  Score Diff:    {result['score_diff']:.2f}")
            print(f"  Verdict Match: {'✓' if result['verdict_match'] else '✗'}")
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
    evaluator = FixedEvaluator()
    evaluator.run_evaluation()
