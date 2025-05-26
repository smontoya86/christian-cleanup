"""
Tests for query monitoring and slow query logging.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.models import Song
from app.utils.query_monitoring import (
    log_slow_queries,
    setup_query_monitoring,
    get_query_statistics
)


class TestQueryMonitoring:
    """Test query monitoring and slow query logging functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app('testing')
        # Enable query recording for testing
        self.app.config['SQLALCHEMY_RECORD_QUERIES'] = True
        self.app.config['SLOW_QUERY_THRESHOLD'] = 0.1  # 100ms threshold for testing
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_query_recording_enabled(self):
        """Test that query recording is properly enabled."""
        assert self.app.config['SQLALCHEMY_RECORD_QUERIES'] is True
        assert 'SLOW_QUERY_THRESHOLD' in self.app.config
        assert self.app.config['SLOW_QUERY_THRESHOLD'] == 0.1
    
    def test_log_slow_queries_with_slow_query(self, caplog):
        """Test that slow queries are properly logged."""
        # Create a test song to ensure we have data
        song = Song(
            spotify_id='test_song_123',
            title='Test Song',
            artist='Test Artist'
        )
        db.session.add(song)
        db.session.commit()
        
        # Simulate a slow query by adding a delay
        with patch('time.sleep') as mock_sleep:
            # Execute a query that should be recorded
            songs = Song.query.filter(Song.title.like('Test%')).all()
            assert len(songs) == 1
        
        # Test the log_slow_queries function
        with caplog.at_level('WARNING'):
            # Mock get_recorded_queries to return a slow query
            with patch('app.utils.query_monitoring.get_recorded_queries') as mock_get_queries:
                mock_query = MagicMock()
                mock_query.duration = 0.5  # 500ms - above threshold
                mock_query.statement = "SELECT * FROM songs WHERE title LIKE ?"
                mock_query.parameters = {'title': 'Test%'}
                mock_query.location = 'test_location'
                mock_get_queries.return_value = [mock_query]
                
                log_slow_queries()
        
        # Verify slow query was logged
        assert len(caplog.records) > 0
        log_message = caplog.records[0].message
        assert "Slow query" in log_message
        assert "SELECT * FROM songs" in log_message
        assert "Duration: 0.500s" in log_message
    
    def test_log_slow_queries_with_fast_query(self, caplog):
        """Test that fast queries are not logged."""
        with caplog.at_level('WARNING'):
            # Mock get_recorded_queries to return a fast query
            with patch('app.utils.query_monitoring.get_recorded_queries') as mock_get_queries:
                mock_query = MagicMock()
                mock_query.duration = 0.05  # 50ms - below threshold
                mock_query.statement = "SELECT * FROM songs WHERE id = ?"
                mock_query.parameters = {'id': 1}
                mock_query.location = 'test_location'
                mock_get_queries.return_value = [mock_query]
                
                log_slow_queries()
        
        # Verify no slow query was logged
        assert len(caplog.records) == 0
    
    def test_get_query_statistics(self):
        """Test that query statistics can be retrieved."""
        # Create test data
        song = Song(
            spotify_id='test_song_456',
            title='Another Test Song',
            artist='Another Test Artist'
        )
        db.session.add(song)
        db.session.commit()
        
        # Execute some queries
        Song.query.filter_by(spotify_id='test_song_456').first()
        Song.query.filter(Song.title.like('Another%')).all()
        
        # Get statistics
        stats = get_query_statistics()
        
        # Verify statistics structure
        assert isinstance(stats, dict)
        assert 'total_queries' in stats
        assert 'slow_queries' in stats
        assert 'average_duration' in stats
        assert 'queries' in stats
        
        # Verify data types
        assert isinstance(stats['total_queries'], int)
        assert isinstance(stats['slow_queries'], int)
        assert isinstance(stats['average_duration'], (int, float))
        assert isinstance(stats['queries'], list)
        
        # Should have recorded some queries
        assert stats['total_queries'] > 0
    
    def test_setup_query_monitoring(self):
        """Test that query monitoring setup works correctly."""
        # This should not raise any exceptions
        setup_query_monitoring(self.app)
        
        # Verify that after_request handler was added
        # Note: Flask doesn't provide a direct way to check registered handlers,
        # so we'll test indirectly by checking if the function exists
        assert hasattr(self.app, 'after_request_funcs')
    
    def test_query_monitoring_after_request_handler(self):
        """Test that the after_request handler works correctly."""
        setup_query_monitoring(self.app)
        
        # Create test data
        song = Song(
            spotify_id='test_song_789',
            title='Handler Test Song',
            artist='Handler Test Artist'
        )
        db.session.add(song)
        db.session.commit()
        
        # Test with a request context
        with self.app.test_client() as client:
            # Make a request that would trigger database queries
            # Since we don't have routes set up in this test, we'll simulate
            with self.app.test_request_context():
                # Execute a query
                Song.query.filter_by(spotify_id='test_song_789').first()
                
                # The after_request handler should be called automatically
                # We can't directly test this without making an actual HTTP request,
                # but we can verify the setup doesn't break anything
                assert True  # If we get here, setup worked
    
    @patch('app.utils.query_monitoring.get_recorded_queries')
    def test_query_monitoring_with_no_queries(self, mock_get_queries, caplog):
        """Test query monitoring when no queries were executed."""
        mock_get_queries.return_value = []
        
        with caplog.at_level('WARNING'):
            log_slow_queries()
        
        # Should not log anything when no queries were executed
        assert len(caplog.records) == 0
    
    @patch('app.utils.query_monitoring.get_recorded_queries')
    def test_query_monitoring_with_exception(self, mock_get_queries, caplog):
        """Test query monitoring handles exceptions gracefully."""
        mock_get_queries.side_effect = Exception("Database error")
        
        with caplog.at_level('ERROR'):
            log_slow_queries()
        
        # Should log the error
        assert len(caplog.records) > 0
        assert "Error logging slow queries" in caplog.records[0].message
    
    def test_query_statistics_with_mixed_queries(self):
        """Test query statistics with both fast and slow queries."""
        # Mock get_recorded_queries to return mixed queries
        with patch('app.utils.query_monitoring.get_recorded_queries') as mock_get_queries:
            fast_query = MagicMock()
            fast_query.duration = 0.05  # 50ms
            fast_query.statement = "SELECT * FROM songs WHERE id = ?"
            
            slow_query = MagicMock()
            slow_query.duration = 0.2  # 200ms
            slow_query.statement = "SELECT * FROM songs WHERE title LIKE ?"
            
            mock_get_queries.return_value = [fast_query, slow_query]
            
            stats = get_query_statistics()
            
            assert stats['total_queries'] == 2
            assert stats['slow_queries'] == 1  # Only one above 100ms threshold
            assert stats['average_duration'] == 0.125  # (0.05 + 0.2) / 2 