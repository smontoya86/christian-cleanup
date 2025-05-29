#!/usr/bin/env python3
"""
Test script to analyze songs with explicit content.
"""
import os
import sys
import logging
from datetime import datetime
from app import create_app, db
from app.models.models import Song, AnalysisResult, Playlist, User
from app.services.unified_analysis_service import UnifiedAnalysisService  # Updated import
from app.utils.database import get_by_filter  # Add SQLAlchemy 2.0 utilities

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_song(title, artist, lyrics, user_id=None):
    """Analyze a song with the given title, artist, and lyrics."""
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Song, AnalysisResult
        from app.services.unified_analysis_service import UnifiedAnalysisService  # Updated import
        
        # Create Flask app and push app context
        app = create_app()
        with app.app_context():
            # Determine user ID to use
            if user_id is None:
                from app.models import User
                user = User.query.first()
                if not user:
                    logger.error("No users found in database")
                    return False
                user_id = user.id
                logger.warning(f"No user specified, using first available user: {user.display_name} (ID: {user_id})")
            
            # Create test song
            test_song = Song(
                spotify_id=f"test_{title.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}",
                title=title,
                artist=artist,
                album="Test Album",
                explicit=True,  # Mark as explicit since we know these are
                album_art_url="https://example.com/default.jpg"
            )
            
            db.session.add(test_song)
            db.session.flush()  # Get the ID without committing
            
            logger.info(f"Created test song: {test_song.title} by {test_song.artist} (ID: {test_song.id})")
            
            # Initialize unified analysis service
            analysis_service = UnifiedAnalysisService()
            
            # Trigger comprehensive analysis
            logger.info(f"Analyzing song: {title} by {artist}")
            result = analysis_service.execute_comprehensive_analysis(
                song_id=test_song.id, 
                user_id=user_id, 
                force_reanalysis=True
            )
            
            if not result:
                logger.error("Failed to complete analysis")
                return False
                
            logger.info(f"Analysis completed successfully")
            
            # Get the updated analysis using SQLAlchemy 2.0 pattern
            updated_analysis = get_by_filter(AnalysisResult, song_id=test_song.id)
            
            if not updated_analysis:
                logger.error("No analysis results found after analysis completion")
                return False
                
            # Print the results
            logger.info("\n=== Analysis Results ===")
            logger.info(f"Song: {title} by {artist}")
            logger.info(f"Final Score: {updated_analysis.score}")
            logger.info(f"Concern Level: {updated_analysis.concern_level}")
            
            # Parse JSON fields for display
            import json
            
            if updated_analysis.purity_flags_details:
                try:
                    purity_flags = json.loads(updated_analysis.purity_flags_details) if isinstance(updated_analysis.purity_flags_details, str) else updated_analysis.purity_flags_details
                    logger.info("\n=== Purity Flags ===")
                    for flag in purity_flags:
                        logger.info(f"- {flag.get('flag')} (Confidence: {flag.get('confidence', 0):.2f})")
                        logger.info(f"  Details: {flag.get('details', 'No details')}")
                except (json.JSONDecodeError, TypeError):
                    logger.info("=== Purity Flags === (parsing error)")
            
            if updated_analysis.positive_themes_identified:
                try:
                    positive_themes = json.loads(updated_analysis.positive_themes_identified) if isinstance(updated_analysis.positive_themes_identified, str) else updated_analysis.positive_themes_identified
                    logger.info("\n=== Positive Themes ===")
                    for theme in positive_themes:
                        logger.info(f"- {theme.get('theme')}")
                except (json.JSONDecodeError, TypeError):
                    logger.info("=== Positive Themes === (parsing error)")
            
            if updated_analysis.concerns:
                try:
                    concerns = json.loads(updated_analysis.concerns) if isinstance(updated_analysis.concerns, str) else updated_analysis.concerns
                    logger.info("\n=== Concerns ===")
                    for concern in concerns:
                        logger.info(f"- {concern.get('concern')}")
                except (json.JSONDecodeError, TypeError):
                    logger.info("=== Concerns === (parsing error)")
            
            return True
            
    except Exception as e:
        logger.error(f"Error analyzing song: {str(e)}", exc_info=True)
        return False

def get_user_by_identifier(identifier):
    """Get user by ID, Spotify ID, or display name"""
    from app import create_app
    from app.models import User
    
    app = create_app()
    with app.app_context():
        try:
            # Try as integer ID first
            user_id = int(identifier)
            user = User.query.filter_by(id=user_id).first()
            if user:
                return user
        except ValueError:
            # Not an integer, try as Spotify ID
            user = User.query.filter_by(spotify_id=identifier).first()
            if user:
                return user
        
        # Try as display name
        user = User.query.filter_by(display_name=identifier).first()
        return user

def main(user_identifier=None):
    """Main function to test song analysis."""
    print("Testing song analysis with explicit content...\n")
    
    # Determine user ID to use
    user_id = None
    if user_identifier:
        user = get_user_by_identifier(user_identifier)
        if user:
            user_id = user.id
            print(f"Using user: {user.display_name} (ID: {user_id})")
        else:
            print(f"❌ User not found with identifier: {user_identifier}")
            return
    
    # Test song 1: Seeing Red by Architects
    seeing_red_lyrics = """
    Returning to the roots of the band's pre-FTTWTE sound, "Seeing Red" talks about the struggle the band's members go through with some people saying their music isn't heavy enough because of their alternative read more
    
    Rent-free living in your head
    (R.I.P.) they commented
    I felt it when they said
    We only ever love you when you're seeing red
    
    Blegh!
    
    Seeing red
    You oughta know that I'm like a broken machine
    I'm not as bulletproof as you all paint me to be
    Time hasn't frozen, why do you want me to scream?
    Are you a junkie punk medicating for free?
    
    We're all you need
    We'll make you royalty
    We'll be the best of enemies
    
    Read me all my rights
    I'll never grow tired of your great advice
    Won't somebody tell me what I believe?
    I'm sorry for your sacrifice
    I guess I must've sounded like the Antichrist
    Won't somebody tell me? Won't somebody tell me what I believe?
    
    No debts, all love, I don't give a fuck
    My head, my heart wouldn't be enough
    I won't think twice, I'm afraid
    I'm the priest, you're the poltergeist
    
    We're like one big family
    Gee, thanks so much for the death threat
    Do you hear the audacity?
    You dummies only live on the internet
    
    We're all you need (Oh yeah, that's right)
    We'll make you royalty (Gimme that gold)
    We'll be the best of enemies
    
    Read me all my rights
    I'll never grow tired of your great advice
    Won't somebody tell me what I believe?
    I'm sorry for your sacrifice
    I guess I must've sounded like the Antichrist
    Won't somebody tell me? Won't somebody tell me what I believe?
    
    Oh, are you happy now?
    Rent-free living in your head
    (R.I.P.) they commented
    I felt it when they said
    We only ever love you when you're seeing red
    
    Heaven burning bright
    You've really gotta wonder how I sleep at night
    Won't somebody tell me? Won't somebody tell me?
    
    Read me all my rights
    I'll never grow tired of your great advice
    Won't somebody tell me what I believe?
    I'm sorry for your sacrifice
    I guess I must've sounded like the Antichrist
    Won't somebody tell me? Won't somebody tell me what I believe?
    What I believe
    What I believe
    All eyes on me
    What I believe
    """
    
    # Test song 2: Animals by Maroon 5
    animals_lyrics = """
    [Verse 1]
    Baby, I'm preying on you tonight
    Hunt you down, eat you alive
    Just like animals, animals, like animals-mals
    
    [Pre-Chorus]
    Maybe you think that you can hide
    I can smell your scent from miles
    Just like animals, animals, like animals-mals
    
    [Chorus]
    Baby, I'm
    So what you trying to do to me?
    It's like we can't stop, we're enemies
    But we get along when I'm inside you, eh
    You're like a drug that's killing me
    I cut you out entirely
    But I get so high when I'm inside you
    
    [Verse 2]
    Yeah, you can start over, you can run free
    You can find other fish in the sea
    You can pretend it's meant to be
    But you can't stay away from me
    I can still hear you making that sound
    Taking me down, rolling on the ground
    You can pretend that it was me, but no
    
    [Pre-Chorus]
    Baby, I'm preying on you tonight
    Hunt you down, eat you alive
    Just like animals, animals, like animals-mals
    
    [Chorus]
    Baby, I'm
    So what you trying to do to me?
    It's like we can't stop, we're enemies
    But we get along when I'm inside you, eh
    You're like a drug that's killing me
    I cut you out entirely
    But I get so high when I'm inside you
    
    [Bridge]
    Don't tell no lie, lie, lie, lie
    You can't deny-ny-ny-ny
    The beast inside, si-si-side
    Yeah, yeah, yeah
    No girl, don't lie, lie, lie, lie (No, no)
    Don't lie
    
    [Chorus]
    So what you trying to do to me?
    It's like we can't stop, we're enemies
    But we get along when I'm inside you, eh
    You're like a drug that's killing me
    I cut you out entirely
    But I get so high when I'm inside you
    """
    
    # Test songs
    test_songs = [
        {"title": "Seeing Red", "artist": "Architects", "lyrics": seeing_red_lyrics},
        {"title": "Animals", "artist": "Maroon 5", "lyrics": animals_lyrics}
    ]
    
    for song in test_songs:
        print(f"\n{'='*50}")
        print(f"Analyzing: {song['title']} by {song['artist']}")
        print(f"{'='*50}\n")
        
        success = analyze_song(
            title=song['title'],
            artist=song['artist'],
            lyrics=song['lyrics'],
            user_id=user_id
        )
        
        if not success:
            print(f"Failed to analyze {song['title']} by {song['artist']}")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test explicit song analysis")
    parser.add_argument("--user", type=str, help="User identifier (ID, Spotify ID, or display name)")
    args = parser.parse_args()
    
    main(args.user)
