import os
import sys
from rq import Queue
from redis import Redis
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Import app modules after setting up environment
from app import create_app
from app.services.analysis_service import perform_christian_song_analysis_and_store
from app.models import db, Song

# Create app and push app context
app = create_app()
app.app_context().push()

def test_song_analysis():
    # Check if the song already exists
    song = Song.query.filter_by(spotify_id='test_song_1').first()
    if song:
        print(f"Song already exists with ID: {song.id}")
        return song.id
    
    # Create a test song
    song = Song(
        spotify_id='test_song_1',
        title='Test Song',
        artist='Test Artist',
        album='Test Album',
        duration_ms=180000,
        explicit=False,
        album_art_url='',
        lyrics='Test lyrics for analysis'
    )
    db.session.add(song)
    db.session.commit()
    print(f"Created test song with ID: {song.id}")
    
    # Add analysis job to the queue
    redis_conn = Redis.from_url(os.getenv('REDIS_URL'))
    q = Queue(connection=redis_conn)
    job = q.enqueue(perform_christian_song_analysis_and_store, song.id)
    print(f"Added analysis job to queue. Job ID: {job.id}")
    
    return song.id

if __name__ == '__main__':
    test_song_id = test_song_analysis()
    print(f"Test song ID: {test_song_id}")
