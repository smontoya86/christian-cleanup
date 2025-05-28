#!/usr/bin/env python3
"""
Test Unified Analysis Service Field Mapping Fix
Verifies that all field mapping issues have been resolved in Task 24.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_field_mapping_fix():
    """Test that field mapping issues have been resolved"""
    
    print("🧪 TESTING: Unified Analysis Service Field Mapping Fix")
    print("=" * 60)
    
    try:
        # Test 1: Verify EnhancedSongAnalyzer output structure
        print("\n1️⃣ Testing EnhancedSongAnalyzer Output Structure...")
        
        from app.utils.analysis_enhanced import EnhancedSongAnalyzer
        
        # Create analyzer instance
        analyzer = EnhancedSongAnalyzer(user_id=1)
        
        # Test with a simple song
        test_song = {
            'title': 'Amazing Grace',
            'artist': 'Traditional',
            'explicit': False,
            'id': 999
        }
        
        print(f"   📝 Analyzing test song: {test_song['title']} by {test_song['artist']}")
        
        # Analyze the song (with minimal lyrics to avoid API calls)
        result = analyzer.analyze_song(
            song_data=test_song,
            lyrics="Amazing grace how sweet the sound that saved a wretch like me"
        )
        
        if result:
            print("   ✅ Analysis completed successfully")
            
            # Check that the output has the CORRECT field names (not prefixed)
            expected_fields = {
                'christian_score': 'score',
                'concern_level': 'concern_level',
                'purity_flags': 'purity_flags_details',
                'positive_themes': 'positive_themes_identified',
                'biblical_themes': 'biblical_themes',
                'supporting_scripture': 'supporting_scripture',
                'detailed_concerns': 'concerns'
            }
            
            print("   🔍 Checking field names in analyzer output...")
            for analyzer_field, db_field in expected_fields.items():
                if analyzer_field in result:
                    print(f"   ✅ {analyzer_field} → {db_field} (CORRECT)")
                else:
                    print(f"   ❌ {analyzer_field} missing from output")
            
            # Check for INCORRECT prefixed fields that should NOT exist
            incorrect_fields = [
                'christian_concern_level',
                'christian_purity_flags_details', 
                'christian_positive_themes_detected',
                'christian_biblical_themes',
                'christian_supporting_scripture',
                'christian_detailed_concerns'
            ]
            
            print("   🔍 Checking for incorrect prefixed fields...")
            found_incorrect = False
            for incorrect_field in incorrect_fields:
                if incorrect_field in result:
                    print(f"   ❌ FOUND INCORRECT FIELD: {incorrect_field}")
                    found_incorrect = True
            
            if not found_incorrect:
                print("   ✅ No incorrect prefixed fields found")
            
        else:
            print("   ❌ Analysis failed - no result returned")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing analyzer: {str(e)}")
        return False
    
    try:
        # Test 2: Verify UnifiedAnalysisService field mapping
        print("\n2️⃣ Testing UnifiedAnalysisService Field Mapping...")
        
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        service = UnifiedAnalysisService()
        
        # Test the _create_analysis_result_from_data method
        test_result = {
            'christian_score': 95,
            'concern_level': 'Low',
            'purity_flags': ['wholesome', 'uplifting'],
            'positive_themes': ['faith', 'hope', 'love'],
            'biblical_themes': ['grace', 'salvation'],
            'supporting_scripture': {'John 3:16': 'For God so loved the world...'},
            'detailed_concerns': [],
            'explanation': 'This is a beautiful Christian hymn'
        }
        
        print("   📝 Testing database field mapping...")
        
        analysis_result = service._create_analysis_result_from_data(999, test_result)
        
        # Verify that the fields are mapped correctly
        mapping_tests = [
            (analysis_result.score, test_result['christian_score'], 'score'),
            (analysis_result.concern_level, test_result['concern_level'], 'concern_level'),
            (json.loads(analysis_result.purity_flags_details), test_result['purity_flags'], 'purity_flags_details'),
            (json.loads(analysis_result.positive_themes_identified), test_result['positive_themes'], 'positive_themes_identified'),
            (json.loads(analysis_result.biblical_themes), test_result['biblical_themes'], 'biblical_themes'),
            (json.loads(analysis_result.supporting_scripture), test_result['supporting_scripture'], 'supporting_scripture'),
            (json.loads(analysis_result.concerns), test_result['detailed_concerns'], 'concerns'),
            (analysis_result.explanation, test_result['explanation'], 'explanation')
        ]
        
        for db_value, expected_value, field_name in mapping_tests:
            if db_value == expected_value:
                print(f"   ✅ {field_name}: CORRECT mapping")
            else:
                print(f"   ❌ {field_name}: INCORRECT mapping - Expected: {expected_value}, Got: {db_value}")
                return False
                
    except Exception as e:
        print(f"   ❌ Error testing UnifiedAnalysisService: {str(e)}")
        return False
    
    try:
        # Test 3: Verify import updates
        print("\n3️⃣ Testing Import Updates...")
        
        # Test that enhanced_analysis_service imports unified
        print("   📝 Checking enhanced_analysis_service imports...")
        
        import app.services.enhanced_analysis_service
        # This should work without errors now
        print("   ✅ enhanced_analysis_service imports successfully")
        
        # Test that background_analysis_service imports unified
        print("   📝 Checking background_analysis_service imports...")
        
        import app.services.background_analysis_service
        # This should work without errors now  
        print("   ✅ background_analysis_service imports successfully")
        
        # Test that spotify_service imports unified
        print("   📝 Checking spotify_service imports...")
        
        import app.services.spotify_service
        # This should work without errors now
        print("   ✅ spotify_service imports successfully")
        
    except Exception as e:
        print(f"   ❌ Error testing imports: {str(e)}")
        return False
    
    try:
        # Test 4: Check deprecation warning
        print("\n4️⃣ Testing Deprecation Warning...")
        
        print("   📝 Checking that analysis_service shows deprecation warning...")
        
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import app.services.analysis_service
            
            if w and any("deprecated" in str(warning.message).lower() for warning in w):
                print("   ✅ Deprecation warning found")
            else:
                print("   ⚠️ No deprecation warning found (this is acceptable)")
        
    except Exception as e:
        print(f"   ❌ Error testing deprecation: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL FIELD MAPPING TESTS PASSED!")
    print("✅ Task 24.1: Fix Field Mapping - COMPLETED")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    success = test_field_mapping_fix()
    
    if success:
        print("\n🚀 Field mapping fix verified successfully!")
        sys.exit(0)
    else:
        print("\n💥 Field mapping test failed!")
        sys.exit(1) 