#!/usr/bin/env python3
"""
Debug script to test biblical themes generation and storage.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.models import Song, AnalysisResult
from app.extensions import db
from app.utils.analysis_enhanced import create_enhanced_analyzer
import json

def test_biblical_themes():
    """Test biblical themes generation and storage"""
    app = create_app()
    
    with app.app_context():
        print("=== TESTING BIBLICAL THEMES GENERATION ===")
        print()
        
        # Test the enhanced analyzer directly
        print("1. Testing Enhanced Analyzer Directly...")
        analyzer = create_enhanced_analyzer(user_id=1)
        
        # Test with Christian lyrics
        test_lyrics = """
        Praise the Lord with all my heart
        I will worship you forever
        Your love and grace surrounds me
        Jesus Christ is my salvation
        I trust in God almighty
        Amazing grace how sweet the sound
        """
        
        print(f"Test lyrics: {test_lyrics[:100]}...")
        
        # Test song data
        song_data = {
            'name': 'Test Worship Song',
            'artist': 'Test Artist',
            'explicit': False
        }
        
        # Analyze the song
        result = analyzer.analyze_song(song_data, test_lyrics)
        
        print(f"✅ Analysis completed")
        print(f"📊 Score: {result.get('christian_score', 'N/A')}")
        print(f"🔍 Biblical themes found: {len(result.get('biblical_themes', []))}")
        print(f"📖 Supporting scripture entries: {len(result.get('supporting_scripture', {}))}")
        
        # Display biblical themes
        biblical_themes = result.get('biblical_themes', [])
        if biblical_themes:
            print("\n📋 BIBLICAL THEMES DETECTED:")
            for i, theme in enumerate(biblical_themes, 1):
                print(f"   {i}. {theme.get('theme', 'Unknown')}")
                print(f"      Description: {theme.get('description', 'No description')}")
                print(f"      Matches: {theme.get('matches', 0)}")
                print(f"      Examples: {theme.get('examples', [])[:2]}")
                print()
        else:
            print("❌ No biblical themes detected")
        
        # Display supporting scripture
        supporting_scripture = result.get('supporting_scripture', {})
        if supporting_scripture:
            print("📖 SUPPORTING SCRIPTURE:")
            for theme_name, scripture_data in supporting_scripture.items():
                print(f"   Theme: {theme_name}")
                if isinstance(scripture_data, dict):
                    for ref, text in scripture_data.items():
                        print(f"      {ref}: {text[:100]}...")
                else:
                    print(f"      {scripture_data}")
                print()
        else:
            print("❌ No supporting scripture found")
        
        print()
        print("2. Testing Database Storage...")
        
        # Get a sample song from database for testing
        sample_song = db.session.query(Song).filter(
            Song.lyrics.isnot(None),
            Song.lyrics != '',
            Song.lyrics != 'Lyrics not available'
        ).first()
        
        if sample_song:
            print(f"📀 Testing with song: '{sample_song.title}' by {sample_song.artist}")
            
            # Check if it has analysis results
            analysis_result = db.session.query(AnalysisResult).filter_by(
                song_id=sample_song.id,
                status='completed'
            ).first()
            
            if analysis_result:
                print(f"✅ Found completed analysis for song")
                
                # Check biblical themes in database
                biblical_themes_db = analysis_result.biblical_themes
                if biblical_themes_db:
                    try:
                        if isinstance(biblical_themes_db, str):
                            themes_data = json.loads(biblical_themes_db)
                        else:
                            themes_data = biblical_themes_db
                        
                        print(f"📋 Biblical themes in DB: {len(themes_data) if themes_data else 0}")
                        if themes_data:
                            for theme in themes_data[:3]:  # Show first 3
                                print(f"   - {theme.get('theme', 'Unknown')}: {theme.get('description', 'No desc')}")
                        else:
                            print("❌ Biblical themes field is empty")
                    except json.JSONDecodeError as e:
                        print(f"❌ Error parsing biblical themes JSON: {e}")
                        print(f"Raw data: {biblical_themes_db}")
                else:
                    print("❌ No biblical themes stored in database")
                
                # Check supporting scripture in database
                supporting_scripture_db = analysis_result.supporting_scripture
                if supporting_scripture_db:
                    try:
                        if isinstance(supporting_scripture_db, str):
                            scripture_data = json.loads(supporting_scripture_db)
                        else:
                            scripture_data = supporting_scripture_db
                        
                        print(f"📖 Supporting scripture in DB: {len(scripture_data) if scripture_data else 0} entries")
                        if scripture_data:
                            for theme_name in list(scripture_data.keys())[:2]:  # Show first 2
                                print(f"   - {theme_name}: {len(scripture_data[theme_name])} references")
                        else:
                            print("❌ Supporting scripture field is empty")
                    except json.JSONDecodeError as e:
                        print(f"❌ Error parsing supporting scripture JSON: {e}")
                        print(f"Raw data: {supporting_scripture_db}")
                else:
                    print("❌ No supporting scripture stored in database")
            else:
                print("❌ No completed analysis found for this song")
        else:
            print("❌ No songs with lyrics found in database")
        
        print()
        print("3. Testing Template Data Format...")
        
        # Test how the template would receive the data
        if sample_song and analysis_result:
            # Simulate how the route passes data to template
            class MockAnalysis:
                def __init__(self, analysis_result):
                    self.score = analysis_result.score
                    self.concern_level = analysis_result.concern_level
                    self.explanation = analysis_result.explanation
                    
                    # Parse JSON fields
                    try:
                        self.biblical_themes = json.loads(analysis_result.biblical_themes) if analysis_result.biblical_themes else []
                    except:
                        self.biblical_themes = []
                    
                    try:
                        self.supporting_scripture = json.loads(analysis_result.supporting_scripture) if analysis_result.supporting_scripture else {}
                    except:
                        self.supporting_scripture = {}
            
            mock_analysis = MockAnalysis(analysis_result)
            
            print(f"📋 Template would receive biblical_themes: {len(mock_analysis.biblical_themes)} items")
            print(f"📖 Template would receive supporting_scripture: {len(mock_analysis.supporting_scripture)} items")
            
            if mock_analysis.biblical_themes:
                print("✅ Biblical themes data is properly formatted for template")
                print(f"   First theme: {mock_analysis.biblical_themes[0]}")
            else:
                print("❌ No biblical themes data for template")
            
            if mock_analysis.supporting_scripture:
                print("✅ Supporting scripture data is properly formatted for template")
                first_key = list(mock_analysis.supporting_scripture.keys())[0]
                print(f"   First scripture entry: {first_key}")
            else:
                print("❌ No supporting scripture data for template")
        
        print()
        print("=== DIAGNOSIS COMPLETE ===")

if __name__ == '__main__':
    test_biblical_themes() 