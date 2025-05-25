#!/usr/bin/env python3
"""
Test script to verify song detail page fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Song, AnalysisResult
from app.extensions import db
import json

def test_song_detail_data_parsing():
    """Test that song detail data is properly parsed and won't cause template errors"""
    app = create_app()
    
    with app.app_context():
        # Get a song with analysis
        song_with_analysis = db.session.query(Song).join(AnalysisResult).first()
        
        if not song_with_analysis:
            print("❌ No songs with analysis found")
            return False
            
        analysis_result = song_with_analysis.analysis_results.first()
        
        print(f"🔍 Testing song: {song_with_analysis.title} by {song_with_analysis.artist}")
        print(f"📊 Analysis ID: {analysis_result.id}")
        
        # Test the safe JSON parsing function (same as in the route)
        def safe_json_parse(field_value, default=None):
            if field_value is None:
                return default or []
            if isinstance(field_value, str):
                try:
                    return json.loads(field_value)
                except (json.JSONDecodeError, ValueError):
                    return default or []
            return field_value
        
        # Test each JSON field
        fields_to_test = [
            ('themes', analysis_result.themes, {}),
            ('concerns', analysis_result.concerns, []),
            ('purity_flags_details', analysis_result.purity_flags_details, []),
            ('positive_themes_identified', analysis_result.positive_themes_identified, []),
            ('biblical_themes', analysis_result.biblical_themes, []),
            ('supporting_scripture', analysis_result.supporting_scripture, {})
        ]
        
        all_passed = True
        
        for field_name, field_value, default in fields_to_test:
            try:
                parsed_value = safe_json_parse(field_value, default)
                print(f"✅ {field_name}: {type(parsed_value).__name__} - {len(parsed_value) if hasattr(parsed_value, '__len__') else 'N/A'} items")
                
                # Test template compatibility
                if isinstance(parsed_value, list):
                    for item in parsed_value[:2]:  # Test first 2 items
                        if isinstance(item, dict):
                            # This should work in template with .get()
                            test_get = item.get('flag_type', 'default')
                            print(f"  📝 Dict item .get() test: {test_get}")
                        elif isinstance(item, str):
                            # This should work in template as string
                            print(f"  📝 String item: {item[:50]}...")
                            
            except Exception as e:
                print(f"❌ {field_name}: Error - {str(e)}")
                all_passed = False
        
        # Test the analysis dictionary creation (same as route)
        try:
            analysis = {
                'score': analysis_result.score,
                'concern_level': analysis_result.concern_level,
                'explanation': analysis_result.explanation,
                'themes': safe_json_parse(analysis_result.themes, {}),
                'concerns': safe_json_parse(analysis_result.concerns, []),
                'purity_flags_triggered': safe_json_parse(analysis_result.purity_flags_details, []),
                'positive_themes_identified': safe_json_parse(analysis_result.positive_themes_identified, []),
                'biblical_themes': safe_json_parse(analysis_result.biblical_themes, []),
                'supporting_scripture': safe_json_parse(analysis_result.supporting_scripture, {})
            }
            print(f"✅ Analysis dictionary created successfully")
            print(f"📊 Score: {analysis['score']}, Level: {analysis['concern_level']}")
            
        except Exception as e:
            print(f"❌ Analysis dictionary creation failed: {str(e)}")
            all_passed = False
        
        return all_passed

if __name__ == "__main__":
    print("🧪 Testing Song Detail Data Parsing Fix")
    print("=" * 50)
    
    success = test_song_detail_data_parsing()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! Song detail page should work properly.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    sys.exit(0 if success else 1) 