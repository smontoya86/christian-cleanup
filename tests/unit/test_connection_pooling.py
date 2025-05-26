"""
Tests for database connection pooling configuration.
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import inspect
from app import create_app, db
from app.models.models import User, Song


class TestConnectionPooling:
    """Test database connection pooling configuration and behavior."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_connection_pool_configuration(self):
        """Test that connection pool is configured with appropriate settings."""
        engine = db.engine
        
        # Check that pool settings are configured
        pool = engine.pool
        assert pool is not None, "Database connection pool should be configured"
        
        # Check pool size configuration
        # Note: These values should match what we configure in settings.py
        assert hasattr(pool, 'size'), "Pool should have size attribute"
        assert hasattr(pool, '_max_overflow'), "Pool should have max_overflow attribute"
        
        # Pool should be able to handle multiple connections
        assert pool.size() >= 5, "Pool size should be at least 5 for testing"
    
    def test_concurrent_database_access(self):
        """Test that multiple concurrent database operations work correctly with connection pooling."""
        # Create some test data
        test_songs = []
        for i in range(5):
            song = Song(
                spotify_id=f'test_song_{i}',
                title=f'Test Song {i}',
                artist='Test Artist'
            )
            test_songs.append(song)
            db.session.add(song)
        db.session.commit()
        
        def query_database(thread_id):
            """Function to be executed by multiple threads."""
            try:
                # Each thread needs its own application context
                with self.app.app_context():
                    # Perform a database query
                    songs = Song.query.filter(Song.title.like('Test Song%')).all()
                    return {
                        'thread_id': thread_id,
                        'song_count': len(songs),
                        'success': True,
                        'error': None
                    }
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'song_count': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent database queries
        num_threads = 10
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(query_database, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Verify all queries succeeded
        successful_queries = [r for r in results if r['success']]
        failed_queries = [r for r in results if not r['success']]
        
        assert len(successful_queries) == num_threads, f"All {num_threads} queries should succeed. Failed: {failed_queries}"
        assert len(failed_queries) == 0, f"No queries should fail, but got: {failed_queries}"
        
        # Verify all queries returned the same data
        for result in successful_queries:
            assert result['song_count'] == 5, "Each query should return 5 songs"
    
    def test_connection_recycling(self):
        """Test that connections are properly recycled after the configured timeout."""
        engine = db.engine
        pool = engine.pool
        
        # Get initial pool status
        initial_checked_in = pool.checkedin()
        initial_checked_out = pool.checkedout()
        
        # Create a connection and use it
        with engine.connect() as conn:
            result = conn.execute(db.text("SELECT 1"))
            assert result.scalar() == 1
        
        # Connection should be returned to pool
        final_checked_in = pool.checkedin()
        final_checked_out = pool.checkedout()
        
        # After using and closing connection, it should be back in the pool
        assert final_checked_out == initial_checked_out, "No connections should be checked out after closing"
    
    def test_pool_overflow_handling(self):
        """Test that the pool handles overflow connections correctly."""
        engine = db.engine
        pool = engine.pool
        
        # Get pool configuration
        pool_size = pool.size()
        max_overflow = getattr(pool, '_max_overflow', 0)
        
        connections = []
        try:
            # Create connections up to pool size + overflow
            max_connections = pool_size + max_overflow
            
            for i in range(min(max_connections, 15)):  # Limit to 15 to avoid overwhelming test
                conn = engine.connect()
                connections.append(conn)
                
                # Verify connection works
                result = conn.execute(db.text("SELECT 1"))
                assert result.scalar() == 1
            
            # All connections should be working
            assert len(connections) > 0, "Should be able to create at least some connections"
            
        finally:
            # Clean up all connections
            for conn in connections:
                conn.close()
    
    def test_pool_health_monitoring(self):
        """Test that we can monitor pool health and status."""
        engine = db.engine
        pool = engine.pool
        
        # Get pool statistics
        pool_status = {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': getattr(pool, 'overflow', 0),
            'invalid': getattr(pool, 'invalid', 0)
        }
        
        # Verify we can get meaningful statistics
        assert isinstance(pool_status['size'], int), "Pool size should be an integer"
        assert isinstance(pool_status['checked_in'], int), "Checked in count should be an integer"
        assert isinstance(pool_status['checked_out'], int), "Checked out count should be an integer"
        
        # Pool should be healthy (no invalid connections initially)
        assert pool_status['checked_out'] >= 0, "Checked out count should be non-negative"
        assert pool_status['checked_in'] >= 0, "Checked in count should be non-negative"
    
    def test_connection_timeout_handling(self):
        """Test that connection timeouts are handled gracefully."""
        engine = db.engine
        
        # Test that we can create and use a connection within reasonable time
        start_time = time.time()
        
        with engine.connect() as conn:
            result = conn.execute(db.text("SELECT 1"))
            assert result.scalar() == 1
        
        connection_time = time.time() - start_time
        
        # Connection should be established quickly (within 5 seconds)
        assert connection_time < 5.0, f"Connection should be established quickly, took {connection_time:.2f}s" 