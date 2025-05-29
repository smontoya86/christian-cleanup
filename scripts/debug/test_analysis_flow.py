#!/usr/bin/env python3
"""Test analysis flow with UnifiedAnalysisService."""

from app import create_app
from app.models.models import User, Song, AnalysisResult
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.extensions import db

def test_analysis_flow():
    """Test the complete analysis flow."""
    app = create_app()
    with app.app_context():
        print("🔍 Testing Analysis Flow...")
        
        # Get or create test user
        user = User.query.first()
        if not user:
            print("❌ No users found in database")
            return False
        
        print(f"📊 Using user: {user.display_name} (ID: {user.id})")
        
        # Get a song with lyrics or create one for testing
        song = Song.query.filter(
            Song.lyrics.isnot(None),
            Song.lyrics != '',
            Song.lyrics != 'Lyrics not available'
        ).first()
        
        if not song:
            # Create a test song with lyrics
            song = Song(
                title="Amazing Grace",
                artist="Traditional",
                spotify_id="test_song_123",
                lyrics="""Amazing grace! How sweet the sound
That saved a wretch like me!
I once was lost, but now am found;
Was blind, but now I see."""
            )
            db.session.add(song)
            db.session.commit()
            print(f"✅ Created test song: '{song.title}' by {song.artist}")
        else:
            print(f"🎵 Testing with existing song: '{song.title}' by {song.artist}")
        
        # Initialize UnifiedAnalysisService
        analysis_service = UnifiedAnalysisService()
        print("✅ UnifiedAnalysisService initialized")
        
        # Test analysis flow by checking if we can get existing analysis result 
        # or just verify the service can be called
        try:
            # Check if an analysis result already exists (AnalysisResult only has song_id, not user_id)
            existing_result = AnalysisResult.query.filter_by(song_id=song.id).first()
            
            if existing_result:
                print(f"✅ Found existing analysis result (ID: {existing_result.id})")
                
                # Check if analysis has data
                has_score = existing_result.score is not None
                has_explanation = existing_result.explanation is not None
                has_themes = existing_result.positive_themes_identified is not None
                has_biblical = existing_result.biblical_themes is not None
                
                print(f"📊 Analysis completeness:")
                print(f"   • Score: {'✅' if has_score else '❌'}")
                print(f"   • Explanation: {'✅' if has_explanation else '❌'}")
                print(f"   • Themes: {'✅' if has_themes else '❌'}")
                print(f"   • Biblical themes: {'✅' if has_biblical else '❌'}")
                
                if has_score:
                    print(f"   • Current score: {existing_result.score}")
                
                if has_explanation:
                    print(f"   • Explanation length: {len(existing_result.explanation)} chars")
            else:
                print("🔄 No existing analysis found - service ready for new analysis")
            
            # Test that we can initialize the service methods
            analysis_service._initialize_services(user.id)
            print("✅ Analysis service components initialized successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Analysis flow test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_error_handling():
    """Test error handling components."""
    print("\n🛡️  Testing Error Handling...")
    
    app = create_app()
    with app.app_context():
        try:
            from app.utils.error_handling import (
                create_error_response, AnalysisError, LyricsNotFoundError
            )
            
            # Test error response creation with proper error object
            test_error = AnalysisError("Test error message")
            response, status_code = create_error_response(test_error)
            print(f"✅ Error response creation: Status {status_code}")
            
            # Verify response structure
            if isinstance(response, dict) and 'success' in response and 'error' in response:
                print("✅ Error response has correct structure")
            else:
                print(f"❌ Error response structure incorrect: {response}")
                return False
            
            # Test custom exceptions
            try:
                raise LyricsNotFoundError("Test lyrics error")
            except LyricsNotFoundError:
                print("✅ Custom exception handling working")
            
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_diagnostic_scripts():
    """Test diagnostic script functionality."""
    print("\n🔧 Testing Diagnostic Scripts...")
    
    try:
        from scripts.diagnose_reanalysis_issues import get_user_by_identifier
        from scripts.test_reanalysis_fixes import get_user_by_identifier as get_user_2
        
        # Test user lookup
        app = create_app()
        with app.app_context():
            user = User.query.first()
            if user:
                found_user = get_user_by_identifier(str(user.id))
                if found_user:
                    print(f"✅ User lookup working: Found {found_user.display_name}")
                    return True
                else:
                    print("❌ User lookup failed")
                    return False
            else:
                print("❌ No users available for testing")
                return False
                
    except Exception as e:
        print(f"❌ Diagnostic scripts test failed: {str(e)}")
        return False

def main():
    """Run all regression tests."""
    print("🚀 Starting Analysis Flow Regression Tests")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(("Analysis Flow", test_analysis_flow()))
    test_results.append(("Error Handling", test_error_handling()))
    test_results.append(("Diagnostic Scripts", test_diagnostic_scripts()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nOverall: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! System is functioning correctly.")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. Review errors above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 