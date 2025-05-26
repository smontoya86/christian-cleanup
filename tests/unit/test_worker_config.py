"""
Tests for enhanced worker configuration system.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from app import create_app


class TestWorkerConfig:
    """Test enhanced worker configuration functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    def test_queue_configuration(self):
        """Test that priority queues are configured correctly."""
        from app.worker_config import get_queues, HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE
        
        # Test queue names
        assert HIGH_QUEUE == 'high'
        assert DEFAULT_QUEUE == 'default'
        assert LOW_QUEUE == 'low'
        
        # Test get_queues function
        queues = get_queues()
        assert len(queues) == 3
        
        # Test queue names in order
        queue_names = [q.name for q in queues]
        assert queue_names == ['high', 'default', 'low']
    
    def test_queue_timeout_configuration(self):
        """Test that queues have correct timeout configurations."""
        from app.worker_config import get_queues
        
        queues = get_queues()
        high_queue, default_queue, low_queue = queues
        
        # Test timeout configuration (RQ stores this in _default_timeout)
        assert high_queue._default_timeout == 300  # 5 minutes
        assert default_queue._default_timeout == 600  # 10 minutes
        assert low_queue._default_timeout == 1800  # 30 minutes
    
    def test_redis_connection_configuration(self):
        """Test Redis connection configuration."""
        from app.worker_config import redis_conn
        
        # Test that Redis connection is configured
        assert redis_conn is not None
        
        # Test connection can ping (if Redis is available)
        try:
            result = redis_conn.ping()
            assert result is True
        except Exception:
            # Redis might not be available in test environment
            pass
    
    @patch.dict(os.environ, {'RQ_REDIS_URL': 'redis://test:6379/2'})
    def test_redis_url_from_environment(self):
        """Test that Redis URL can be configured from environment."""
        # Reload the module to pick up environment changes
        import importlib
        from app import worker_config
        importlib.reload(worker_config)
        
        # Test that the URL is picked up from environment
        # Check the connection pool's connection kwargs
        connection_kwargs = worker_config.redis_conn.connection_pool.connection_kwargs
        assert connection_kwargs['host'] == 'test'
        assert connection_kwargs['port'] == 6379
        assert connection_kwargs['db'] == 2


class TestTaskPrioritization:
    """Test task prioritization functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    @patch('app.services.enhanced_analysis_service.rq')
    def test_high_priority_task_enqueue(self, mock_rq):
        """Test that high priority tasks are enqueued correctly."""
        from app.services.enhanced_analysis_service import analyze_song_user_initiated
        
        # Setup mock
        mock_high_queue = MagicMock()
        mock_rq.get_queue.return_value = mock_high_queue
        mock_high_queue.enqueue.return_value = MagicMock(id='job123')
        
        # Call the function
        job = analyze_song_user_initiated('song123')
        
        # Verify high queue was used
        mock_high_queue.enqueue.assert_called_once()
        args, kwargs = mock_high_queue.enqueue.call_args
        assert args[0] == 'app.services.analysis_service.perform_christian_song_analysis_and_store'
        assert args[1] == 'song123'
        assert kwargs['job_timeout'] == 300
        assert kwargs['job_id'] == 'analyze_song:song123'
    
    @patch('app.services.enhanced_analysis_service.rq')
    def test_default_priority_task_enqueue(self, mock_rq):
        """Test that default priority tasks are enqueued correctly."""
        from app.services.enhanced_analysis_service import analyze_song_background
        
        # Setup mock
        mock_default_queue = MagicMock()
        mock_rq.get_queue.return_value = mock_default_queue
        mock_default_queue.enqueue.return_value = MagicMock(id='job456')
        
        # Call the function
        job = analyze_song_background('song456')
        
        # Verify default queue was used
        mock_default_queue.enqueue.assert_called_once()
        args, kwargs = mock_default_queue.enqueue.call_args
        assert args[0] == 'app.services.analysis_service.perform_christian_song_analysis_and_store'
        assert args[1] == 'song456'
        assert kwargs['job_timeout'] == 600
    
    @patch('app.services.enhanced_analysis_service.rq')
    def test_low_priority_batch_enqueue(self, mock_rq):
        """Test that low priority batch tasks are enqueued correctly."""
        from app.services.enhanced_analysis_service import analyze_songs_batch
        
        # Setup mock
        mock_low_queue = MagicMock()
        mock_rq.get_queue.return_value = mock_low_queue
        mock_low_queue.enqueue.return_value = MagicMock(id='job789')
        
        # Call the function
        jobs = analyze_songs_batch(['song1', 'song2', 'song3'])
        
        # Verify low queue was used 3 times
        assert mock_low_queue.enqueue.call_count == 3
        assert len(jobs) == 3
        
        # Check the first call
        args, kwargs = mock_low_queue.enqueue.call_args_list[0]
        assert args[0] == 'app.services.analysis_service.perform_christian_song_analysis_and_store'
        assert args[1] == 'song1'
        assert kwargs['job_timeout'] == 1800


class TestRetryLogic:
    """Test retry logic functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    @patch('time.sleep', return_value=None)  # Don't actually sleep in tests
    @patch('rq.get_current_job')
    def test_retry_success_after_failure(self, mock_get_job, mock_sleep):
        """Test retry decorator succeeds after failures."""
        from app.utils.retry import retry_on_failure
        
        # Mock job
        mock_job = MagicMock()
        mock_job.id = 'test_job_123'
        mock_get_job.return_value = mock_job
        
        # Mock function that fails twice then succeeds
        call_count = 0
        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("test error")
            return "success"
        
        # Apply retry decorator
        decorated_func = retry_on_failure(max_retries=3, delay=1)(mock_func)
        
        # Call the function
        result = decorated_func()
        
        # Verify the function was called 3 times
        assert call_count == 3
        # Verify sleep was called twice (after first and second failures)
        assert mock_sleep.call_count == 2
        # Verify the result
        assert result == "success"
    
    @patch('time.sleep', return_value=None)
    @patch('rq.get_current_job')
    def test_retry_max_attempts_exceeded(self, mock_get_job, mock_sleep):
        """Test retry decorator fails after max attempts."""
        from app.utils.retry import retry_on_failure
        
        # Mock job
        mock_job = MagicMock()
        mock_job.id = 'test_job_456'
        mock_get_job.return_value = mock_job
        
        # Mock function that always fails
        call_count = 0
        def mock_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("test error")
        
        # Apply retry decorator
        decorated_func = retry_on_failure(max_retries=3, delay=1)(mock_func)
        
        # Call the function and expect it to raise an exception
        with pytest.raises(ValueError):
            decorated_func()
        
        # Verify the function was called 4 times (initial + 3 retries)
        assert call_count == 4
        # Verify sleep was called 3 times
        assert mock_sleep.call_count == 3
    
    @patch('time.sleep', return_value=None)
    @patch('rq.get_current_job')
    def test_retry_backoff_calculation(self, mock_get_job, mock_sleep):
        """Test retry decorator backoff calculation."""
        from app.utils.retry import retry_on_failure
        
        # Mock job
        mock_job = MagicMock()
        mock_job.id = 'test_job_789'
        mock_get_job.return_value = mock_job
        
        # Mock function that always fails
        def mock_func():
            raise ValueError("test error")
        
        # Apply retry decorator with backoff
        decorated_func = retry_on_failure(max_retries=3, delay=2, backoff=2)(mock_func)
        
        # Call the function and expect it to raise an exception
        with pytest.raises(ValueError):
            decorated_func()
        
        # Verify sleep was called with increasing delays: 2, 4, 8
        expected_calls = [((2,), {}), ((4,), {}), ((8,), {})]
        assert mock_sleep.call_args_list == expected_calls


class TestWorkerMonitoring:
    """Test worker monitoring functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    @patch('psutil.Process')
    @patch('redis.from_url')
    def test_monitored_worker_registration(self, mock_redis_from_url, mock_process):
        """Test that monitored worker registers correctly."""
        from app.utils.worker_monitoring import MonitoredWorker
        from rq import Queue
        
        # Setup process mock
        process_instance = MagicMock()
        process_instance.pid = 12345
        process_instance.memory_percent.return_value = 2.5
        process_instance.cpu_percent.return_value = 1.8
        mock_process.return_value = process_instance
        
        # Setup Redis connection mock
        redis_conn = MagicMock()
        redis_conn.connection_pool.connection_kwargs = {'socket_timeout': 30}
        mock_redis_from_url.return_value = redis_conn
        
        # Create real Queue object with mocked connection
        test_queue = Queue('test_queue', connection=redis_conn)
        
        # Create a worker with mocked connection
        worker = MonitoredWorker(
            queues=[test_queue],
            connection=redis_conn,
            name='test_worker'
        )
        
        # Call register_birth
        worker.register_birth()
        
        # Verify Redis hset was called with correct data
        redis_conn.hset.assert_called()
        call_args = redis_conn.hset.call_args[0]
        assert call_args[0] == 'worker:test_worker:info'
        
        # Verify mapping contains expected keys
        mapping = redis_conn.hset.call_args[1]['mapping']
        assert 'pid' in mapping
        assert 'queues' in mapping
        assert 'memory_percent' in mapping
        assert 'cpu_percent' in mapping
        assert mapping['pid'] == 12345
        assert 'test_queue' in mapping['queues']
    
    @patch('psutil.Process')
    @patch('time.time')
    @patch('redis.from_url')
    def test_monitored_worker_heartbeat(self, mock_redis_from_url, mock_time, mock_process):
        """Test that monitored worker sends heartbeat correctly."""
        from app.utils.worker_monitoring import MonitoredWorker
        from rq import Queue
        
        # Setup time mock
        mock_time.return_value = 1000.0
        
        # Setup process mock
        process_instance = MagicMock()
        process_instance.memory_percent.return_value = 3.0
        process_instance.cpu_percent.return_value = 2.5
        mock_process.return_value = process_instance
        
        # Setup Redis connection mock
        redis_conn = MagicMock()
        redis_conn.connection_pool.connection_kwargs = {'socket_timeout': 30}
        mock_redis_from_url.return_value = redis_conn
        
        # Create real Queue object
        test_queue = Queue('test_queue', connection=redis_conn)
        
        # Create a worker
        worker = MonitoredWorker(
            queues=[test_queue],
            connection=redis_conn,
            name='test_worker',
            health_check_interval=60
        )
        
        # Set last heartbeat to trigger update
        worker.last_heartbeat = 900.0  # 100 seconds ago
        
        # Call heartbeat
        worker.heartbeat()
        
        # Verify Redis hset was called for heartbeat
        assert redis_conn.hset.call_count >= 1
        
        # Find the heartbeat call (should be the second call after register_birth)
        heartbeat_call = None
        for call in redis_conn.hset.call_args_list:
            # Check if this call has mapping with last_heartbeat
            if len(call) > 1 and 'mapping' in call[1]:
                mapping = call[1]['mapping']
                if 'last_heartbeat' in mapping:
                    heartbeat_call = call
                    break
        
        assert heartbeat_call is not None, f"No heartbeat call found in: {redis_conn.hset.call_args_list}"
        mapping = heartbeat_call[1]['mapping']
        assert 'last_heartbeat' in mapping
        assert 'memory_percent' in mapping
        assert 'cpu_percent' in mapping
        assert mapping['last_heartbeat'] == 1000.0 