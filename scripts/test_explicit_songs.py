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
from app.services.analysis_service import perform_christian_song_analysis_and_store
from app.utils.database import get_by_filter  # Add SQLAlchemy 2.0 utilities

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_song(title, artist, lyrics):
    """Analyze a song with the given title, artist, and lyrics."""
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Song, AnalysisResult
        from app.services.analysis_service import perform_christian_song_analysis_and_store
        
        # Create Flask app and push app context
        app = create_app()
        with app.app_context():
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
            
            # Create analysis result with lyrics
            analysis = AnalysisResult(
                song_id=test_song.id,
                analyzed_by_user_id=1,  # Assuming user 1 exists
                lyrics_provided=True,
                lyrics_used_for_analysis=lyrics,
                content_moderation_raw_predictions=[],  # Will be populated by the analyzer
                alternative_model_raw_predictions={},   # Will be populated by the analyzer
                christian_purity_flags_details=[],      # Will be populated by the analyzer
                christian_positive_themes_detected=[],  # Will be populated by the analyzer
                christian_negative_themes_detected=[],  # Will be populated by the analyzer
                christian_score=100,                    # Will be updated by the analyzer
                christian_concern_level="Pending"        # Will be updated by the analyzer
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            logger.info(f"Created analysis record for song ID {test_song.id}")
            
            # Trigger analysis
            logger.info(f"Analyzing song: {title} by {artist}")
            job = perform_christian_song_analysis_and_store(test_song.id, 1)  # User ID 1
            
            if not job:
                logger.error("Failed to enqueue analysis job")
                return False
                
            logger.info(f"Analysis job enqueued with ID: {job.id}")
            
            # For testing purposes, we'll wait a bit for the job to complete
            import time
            time.sleep(5)
            
            # Get the updated analysis using SQLAlchemy 2.0 pattern
            updated_analysis = get_by_filter(AnalysisResult, song_id=test_song.id)
            
            if not updated_analysis:
                logger.error("No analysis results found after job completion")
                return False
                
            # Print the results
            logger.info("\n=== Analysis Results ===")
            logger.info(f"Song: {title} by {artist}")
            logger.info(f"Final Score: {updated_analysis.christian_score}")
            logger.info(f"Concern Level: {updated_analysis.christian_concern_level}")
            
            if updated_analysis.christian_purity_flags_details:
                logger.info("\n=== Purity Flags ===")
                for flag in updated_analysis.christian_purity_flags_details:
                    logger.info(f"- {flag.get('flag')} (Confidence: {flag.get('confidence', 0):.2f})")
                    logger.info(f"  Details: {flag.get('details', 'No details')}")
            
            if updated_analysis.christian_positive_themes_detected:
                logger.info("\n=== Positive Themes ===")
                for theme in updated_analysis.christian_positive_themes_detected:
                    logger.info(f"- {theme.get('theme')}")
            
            if updated_analysis.christian_negative_themes_detected:
                logger.info("\n=== Negative Themes ===")
                for theme in updated_analysis.christian_negative_themes_detected:
                    logger.info(f"- {theme.get('theme')}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error analyzing song: {str(e)}", exc_info=True)
        return False

def main():
    """Main function to test song analysis."""
    print("Testing song analysis with explicit content...\n")
    
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
            lyrics=song['lyrics']
        )
        
        if not success:
            print(f"Failed to analyze {song['title']} by {song['artist']}")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
