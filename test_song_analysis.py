#!/usr/bin/env python3
"""
Test the enhanced analysis on the specific problematic song
"""
import sys
sys.path.append('/app')

from app import create_app
from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
from app.services.contextual_theme_detector import ContextualThemeDetector
from app.services.enhanced_concern_detector import EnhancedConcernDetector

def test_problematic_song():
    print("=== DEBUGGING 'In The Name of Jesus' ANALYSIS ===")
    
    app = create_app()
    with app.app_context():
        # Sample lyrics that should be clearly positive
        song_title = "In The Name of Jesus"
        artist = "Maverick City Music"
        sample_lyrics = """
        In the name of Jesus every knee will bow
        Every tongue confess that He is Lord
        Jesus Christ the King of Kings
        Lord of Lords He reigns forever
        Glory to His name
        """
        
        print(f"\nTesting: '{song_title}' by {artist}")
        print(f"Lyrics preview: {sample_lyrics[:100]}...")
        
        # Test each component separately
        print("\n1. TESTING CONCERN DETECTOR:")
        concern_detector = EnhancedConcernDetector()
        concern_result = concern_detector.analyze_content_concerns(song_title, artist, sample_lyrics)
        
        print(f"   Concerns detected: {len(concern_result.get('detailed_concerns', []))}")
        for concern in concern_result.get('detailed_concerns', [])[:5]:
            print(f"   - {concern.get('category', 'Unknown')}: {concern.get('explanation', 'No explanation')}")
        
        print(f"   Overall concern level: {concern_result.get('overall_concern_level', 'Unknown')}")
        
        print("\n2. TESTING THEME DETECTOR:")
        theme_detector = ContextualThemeDetector()
        
        # Test if we can get sentiment/emotion data
        from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
        analyzer = HuggingFaceAnalyzer()
        sentiment = analyzer._analyze_sentiment(sample_lyrics)
        emotion = analyzer._analyze_emotions(sample_lyrics)
        
        print(f"   Sentiment: {sentiment}")
        print(f"   Emotion: {emotion}")
        
        themes = theme_detector.detect_themes_with_context(sample_lyrics, sentiment, emotion)
        print(f"   Themes detected: {len(themes)}")
        for theme in themes[:5]:
            method = theme.get('detection_method', 'unknown')
            print(f"   - {theme['theme']}: {theme['confidence']:.3f} ({method})")
        
        print("\n3. TESTING FULL ANALYSIS:")
        service = SimplifiedChristianAnalysisService()
        result = service.analyze_song(song_title, artist, sample_lyrics)
        
        print(f"   Final Score: {result.score}%")
        print(f"   Concern Level: {result.concern_level}")
        print(f"   Biblical Themes: {len(result.biblical_themes)}")
        print(f"   Supporting Scripture: {len(result.supporting_scripture)}")
        print(f"   Concerns: {len(result.concerns)}")
        
        if result.biblical_themes:
            print("   Sample biblical themes:")
            for theme in result.biblical_themes[:3]:
                print(f"     - {theme}")
        
        if result.concerns:
            print("   Sample concerns:")
            for concern in result.concerns[:3]:
                print(f"     - {concern}")
        
        print(f"\n4. ANALYSIS SUMMARY:")
        print(f"   ✅ Expected: High score (80+), Low concern, Multiple Christian themes")
        print(f"   ❌ Actual: {result.score}% score, {result.concern_level} concern, {len(result.biblical_themes)} themes")

if __name__ == "__main__":
    test_problematic_song() 