"""
Pytest configuration and shared fixtures
"""

import os
from datetime import datetime, timezone

import pytest

# Set test environment variables before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'true'
os.environ['DISABLE_ANALYZER_PREFLIGHT'] = '1'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'test-key-123')

from app import create_app
from app.extensions import db
from app.models.models import AnalysisResult, LyricsCache, Playlist, Song, User


@pytest.fixture(scope='function')
def app():
    """Create application for testing with isolated database"""
    # Override DATABASE_URL for testing
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        yield db.session
        
        # Rollback and clean up
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user"""
    from datetime import datetime, timedelta, timezone
    
    user = User(
        spotify_id='test_user_123',
        display_name='Test User',
        email='test@example.com',
        access_token='test_access_token',
        refresh_token='test_refresh_token',
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_song(db_session):
    """Create a sample song"""
    song = Song(
        spotify_id='test_song_123',
        title='Amazing Grace',
        artist='John Newton',
        album='Hymns',
        duration_ms=240000
    )
    db_session.add(song)
    db_session.commit()
    return song


@pytest.fixture
def sample_playlist(db_session, sample_user):
    """Create a sample playlist"""
    playlist = Playlist(
        spotify_id='test_playlist_123',
        name='Test Playlist',
        owner_id=sample_user.id,
        spotify_snapshot_id='snapshot_123'
    )
    db_session.add(playlist)
    db_session.commit()
    return playlist


@pytest.fixture
def sample_analysis(db_session, sample_song):
    """Create a sample analysis result"""
    analysis = AnalysisResult(
        song_id=sample_song.id,
        score=75,
        verdict='context_required',
        biblical_themes=['faith', 'grace'],
        concerns=[],
        explanation='Positive Christian content'
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


@pytest.fixture
def sample_lyrics_cache(db_session):
    """Create a sample lyrics cache entry"""
    cache = LyricsCache(
        artist='John Newton',
        title='Amazing Grace',
        lyrics='Amazing grace, how sweet the sound...',
        source='test'
    )
    db_session.add(cache)
    db_session.commit()
    return cache


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "score": 85,
        "verdict": "freely_listen",
        "formation_risk": "low",
        "narrative_voice": "artist",
        "lament_filter_applied": False,
        "themes_positive": ["Worship (+15)", "Grace (+10)"],
        "themes_negative": [],
        "concerns": [],
        "scripture_references": ["Ephesians 2:8-9", "Psalm 103:1"],
        "analysis": "Strong Christian hymn about salvation by grace"
    }


@pytest.fixture
def mock_analysis_service(monkeypatch, mock_openai_response):
    """Mock the analysis service to avoid real API calls"""
    from app.services.simplified_christian_analysis_service import (
        SimplifiedChristianAnalysisService,
    )
    
    def mock_analyze(*args, **kwargs):
        return {
            'overall_score': mock_openai_response['score'],
            'verdict': mock_openai_response['verdict'],
            'biblical_analysis': {
                'themes': mock_openai_response['themes_positive'],
                'concerns': mock_openai_response['concerns'],
            },
            'supporting_scripture': [
                {'reference': ref, 'relevance': 'high'}
                for ref in mock_openai_response['scripture_references']
            ],
            'detailed_explanation': mock_openai_response['analysis']
        }
    
    monkeypatch.setattr(
        SimplifiedChristianAnalysisService,
        'analyze_song_content',
        mock_analyze
    )
    
    return mock_openai_response

