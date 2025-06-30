import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from app.services.unified_analysis_service import UnifiedAnalysisService
from app.models.models import Song, AnalysisResult, Playlist, PlaylistSong, User
from app import db


class TestBatchProcessing:
    """Test batch processing functionality for large music libraries."""
    
    def test_analyze_songs_batch_basic_functionality(self, app, sample_songs):
        """Test basic batch processing of multiple songs."""
        with app.app_context():
            service = UnifiedAnalysisService()
            song_ids = [song.id for song in sample_songs[:5]]
            
            # Mock the analysis service to return consistent results
            with patch.object(service.analysis_service, 'analyze_song') as mock_analyze:
                mock_analyze.return_value = Mock(
                    scoring_results={'final_score': 85, 'quality_level': 'good', 'explanation': 'Test analysis'},
                    biblical_analysis={'themes': ['faith', 'hope']},
                    content_analysis={'concern_flags': []},
                    model_analysis={'sentiment': {'label': 'POSITIVE', 'score': 0.8}}
                )
                
                result = service.analyze_songs_batch(song_ids, batch_size=2)
                
                assert result['success'] is True
                assert result['total_analyzed'] == 5
                assert result['batch_count'] == 3  # 5 songs in batches of 2 = 3 batches
                assert len(result['results']) == 5
                assert mock_analyze.call_count == 5
    
    def test_analyze_songs_batch_with_existing_analysis(self, app, sample_songs):
        """Test batch processing skips songs that already have analysis."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Create existing analysis for first song
            existing_analysis = AnalysisResult(
                song_id=sample_songs[0].id,
                status='completed',
                score=90,
                concern_level='low'
            )
            db.session.add(existing_analysis)
            db.session.commit()
            
            song_ids = [song.id for song in sample_songs[:3]]
            
            with patch.object(service.analysis_service, 'analyze_song') as mock_analyze:
                mock_analyze.return_value = Mock(
                    scoring_results={'final_score': 85, 'quality_level': 'good', 'explanation': 'Test analysis'},
                    biblical_analysis={'themes': ['faith']},
                    content_analysis={'concern_flags': []},
                    model_analysis={'sentiment': {'label': 'POSITIVE', 'score': 0.8}}
                )
                
                result = service.analyze_songs_batch(song_ids, skip_existing=True)
                
                # Should only analyze 2 songs (skipping the first one)
                assert result['total_analyzed'] == 2
                assert result['skipped_existing'] == 1
                assert mock_analyze.call_count == 2
    
    def test_analyze_songs_batch_performance_tracking(self, app, sample_songs):
        """Test that batch processing tracks performance metrics."""
        with app.app_context():
            service = UnifiedAnalysisService()
            song_ids = [song.id for song in sample_songs[:3]]
            
            with patch.object(service.analysis_service, 'analyze_song') as mock_analyze:
                mock_analyze.return_value = Mock(
                    scoring_results={'final_score': 85, 'quality_level': 'good', 'explanation': 'Test analysis'},
                    biblical_analysis={'themes': ['faith']},
                    content_analysis={'concern_flags': []},
                    model_analysis={'sentiment': {'label': 'POSITIVE', 'score': 0.8}}
                )
                
                result = service.analyze_songs_batch(song_ids)
                
                assert 'processing_time' in result
                assert 'average_time_per_song' in result
                assert result['processing_time'] > 0
                assert result['average_time_per_song'] > 0
    
    def test_analyze_songs_batch_error_handling(self, app, sample_songs):
        """Test batch processing handles individual song analysis errors gracefully."""
        with app.app_context():
            service = UnifiedAnalysisService()
            song_ids = [song.id for song in sample_songs[:3]]
            
            # Mock analyze_song_complete to fail on second song
            def mock_analyze_complete_side_effect(song, force=False, user_id=None):
                if song.title == sample_songs[1].title:
                    raise Exception("Analysis failed")
                return {
                    'score': 85,
                    'concern_level': 'good',
                    'explanation': 'Test analysis',
                    'themes': ['faith'],
                    'detailed_concerns': [],
                    'positive_themes': [],
                    'biblical_themes': [],
                    'supporting_scripture': []
                }
            
            with patch.object(service, 'analyze_song_complete', side_effect=mock_analyze_complete_side_effect):
                result = service.analyze_songs_batch(song_ids)
                
                assert result['total_analyzed'] == 2  # 2 successful, 1 failed
                assert result['failed_count'] == 1
                assert len(result['errors']) == 1
                assert 'Analysis failed' in result['errors'][0]['error']


class TestSmartFiltering:
    """Test smart filtering functionality to avoid unnecessary analysis."""
    
    def test_get_songs_needing_analysis_basic(self, app, sample_songs):
        """Test basic filtering of songs that need analysis."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Create analysis for first song only
            existing_analysis = AnalysisResult(
                song_id=sample_songs[0].id,
                status='completed',
                score=90
            )
            db.session.add(existing_analysis)
            db.session.commit()
            
            # Get all song IDs
            all_song_ids = [song.id for song in sample_songs]
            
            result = service.get_songs_needing_analysis(all_song_ids)
            
            # Should return all songs except the first one
            expected_count = len(sample_songs) - 1
            assert len(result['song_ids']) == expected_count
            assert sample_songs[0].id not in result['song_ids']
            assert result['total_filtered'] == 1
            assert result['needs_analysis'] == expected_count
    
    def test_get_songs_needing_analysis_with_failed_analysis(self, app, sample_songs):
        """Test filtering includes songs with failed analysis for retry."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Create failed analysis for first song
            failed_analysis = AnalysisResult(
                song_id=sample_songs[0].id,
                status='failed',
                error_message='Previous analysis failed'
            )
            db.session.add(failed_analysis)
            db.session.commit()
            
            all_song_ids = [song.id for song in sample_songs[:2]]
            
            result = service.get_songs_needing_analysis(all_song_ids, retry_failed=True)
            
            # Should include the failed song for retry
            assert len(result['song_ids']) == 2
            assert sample_songs[0].id in result['song_ids']
            assert result['retry_count'] == 1
    
    def test_get_songs_needing_analysis_recent_analysis_threshold(self, app, sample_songs):
        """Test filtering respects analysis age threshold."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Create old analysis (older than threshold)
            old_analysis = AnalysisResult(
                song_id=sample_songs[0].id,
                status='completed',
                score=90,
                created_at=datetime.utcnow() - timedelta(days=31)  # 31 days old
            )
            db.session.add(old_analysis)
            db.session.commit()
            
            all_song_ids = [song.id for song in sample_songs[:2]]
            
            # Filter with 30-day threshold
            result = service.get_songs_needing_analysis(
                all_song_ids, 
                max_analysis_age_days=30
            )
            
            # Should include the song with old analysis
            assert len(result['song_ids']) == 2
            assert sample_songs[0].id in result['song_ids']
            assert result['outdated_count'] == 1
    
    def test_get_songs_needing_analysis_blacklist_whitelist_priority(self, app, sample_songs, sample_user):
        """Test filtering prioritizes blacklisted/whitelisted songs correctly."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Mock blacklist/whitelist checks
            with patch.object(service, '_is_blacklisted') as mock_blacklist, \
                 patch.object(service, '_is_whitelisted') as mock_whitelist:
                
                # First song is blacklisted, second is whitelisted
                mock_blacklist.side_effect = lambda song, user_id: song.id == sample_songs[0].id
                mock_whitelist.side_effect = lambda song, user_id: song.id == sample_songs[1].id
                
                all_song_ids = [song.id for song in sample_songs[:3]]
                
                result = service.get_songs_needing_analysis(
                    all_song_ids, 
                    user_id=sample_user.id,
                    prioritize_user_lists=True
                )
                
                # Should prioritize blacklisted/whitelisted songs
                assert result['blacklisted_count'] == 1
                assert result['whitelisted_count'] == 1
                assert len(result['priority_songs']) == 2  # blacklisted + whitelisted
    
    def test_filter_songs_by_criteria_comprehensive(self, app, sample_songs):
        """Test comprehensive song filtering by multiple criteria."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Set up test data
            sample_songs[0].lyrics = "explicit content here"  # Has lyrics
            sample_songs[1].lyrics = ""  # No lyrics
            sample_songs[2].lyrics = None  # No lyrics
            db.session.commit()
            
            all_song_ids = [song.id for song in sample_songs]
            
            # Filter with multiple criteria
            result = service.filter_songs_by_criteria(
                all_song_ids,
                require_lyrics=True,
                exclude_instrumentals=True
            )
            
            assert 'filtered_songs' in result
            assert 'filter_stats' in result
            assert result['filter_stats']['has_lyrics'] >= 0
            assert result['filter_stats']['missing_lyrics'] >= 0


class TestLargeLibraryOptimizations:
    """Test optimizations specifically for large music libraries."""
    
    def test_batch_processing_memory_efficiency(self, app):
        """Test that batch processing doesn't load all songs into memory at once."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            # Create a large number of song IDs (simulate 18k songs)
            large_song_list = list(range(1, 1001))  # 1000 songs for testing
            
            with patch.object(service, '_analyze_song_batch_chunk') as mock_chunk:
                mock_chunk.return_value = {
                    'analyzed': 10,
                    'results': [],
                    'errors': []
                }
                
                result = service.analyze_songs_batch(
                    large_song_list, 
                    batch_size=50,
                    memory_efficient=True
                )
                
                # Should process in chunks, not all at once
                expected_chunks = len(large_song_list) // 50
                assert mock_chunk.call_count == expected_chunks
    
    def test_priority_based_processing_order(self, app, sample_songs, sample_user):
        """Test that high-priority songs are processed first in large batches."""
        with app.app_context():
            service = UnifiedAnalysisService()
            
            song_ids = [song.id for song in sample_songs]
            
            with patch.object(service, '_is_blacklisted') as mock_blacklist:
                # Make first song blacklisted (high priority)
                mock_blacklist.side_effect = lambda song, user_id: song.id == sample_songs[0].id
                
                result = service.get_songs_needing_analysis(
                    song_ids,
                    user_id=sample_user.id,
                    prioritize_user_lists=True
                )
                
                # Priority songs should be listed first
                assert len(result['priority_songs']) > 0
                assert sample_songs[0].id in result['priority_songs']
    
    def test_incremental_analysis_progress_tracking(self, app, sample_songs):
        """Test progress tracking for large batch operations."""
        with app.app_context():
            service = UnifiedAnalysisService()
            song_ids = [song.id for song in sample_songs]
            
            progress_updates = []
            
            def mock_progress_callback(current, total, song_title):
                progress_updates.append({
                    'current': current,
                    'total': total,
                    'song': song_title,
                    'percentage': (current / total) * 100
                })
            
            with patch.object(service.analysis_service, 'analyze_song') as mock_analyze:
                mock_analyze.return_value = Mock(
                    scoring_results={'final_score': 85, 'quality_level': 'good', 'explanation': 'Test'},
                    biblical_analysis={'themes': []},
                    content_analysis={'concern_flags': []},
                    model_analysis={'sentiment': {'label': 'POSITIVE', 'score': 0.8}}
                )
                
                result = service.analyze_songs_batch(
                    song_ids,
                    progress_callback=mock_progress_callback
                )
                
                # Should have progress updates
                assert len(progress_updates) == len(song_ids)
                assert progress_updates[-1]['current'] == len(song_ids)
                assert progress_updates[-1]['percentage'] == 100.0


@pytest.fixture
def sample_songs(app):
    """Create sample songs for testing."""
    with app.app_context():
        # Clear any existing songs to avoid conflicts
        db.session.query(Song).delete()
        db.session.commit()
        
        songs = []
        for i in range(10):
            song = Song(
                title=f"Test Song {i}",
                artist=f"Test Artist {i}",
                spotify_id=f"spotify_id_{i}",
                lyrics=f"Test lyrics for song {i}" if i % 2 == 0 else ""
            )
            db.session.add(song)
            songs.append(song)
        
        db.session.commit()
        
        # Refresh all songs to ensure they're bound to the session
        for song in songs:
            db.session.refresh(song)
        
        return songs


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        # Clear any existing users to avoid conflicts
        db.session.query(User).delete()
        db.session.commit()
        
        user = User(
            id=1,
            spotify_id="test_user_123",
            display_name="Test User",
            email="test@example.com",
            access_token="test_access_token",  # Required field
            token_expiry=datetime.utcnow() + timedelta(hours=1)  # Required field
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user 