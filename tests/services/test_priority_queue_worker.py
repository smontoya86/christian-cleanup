"""
Tests for Priority Queue Worker

Tests the priority queue worker functionality including job processing,
priority handling, graceful shutdown, and integration with the Flask app.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.priority_queue_worker import PriorityQueueWorker, init_worker, get_worker
from app.services.priority_analysis_queue import AnalysisJob, JobType, JobPriority, JobStatus


class TestPriorityQueueWorker:
    """Test the PriorityQueueWorker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock Redis to avoid actual Redis dependency
        self.redis_mock = Mock()
        self.app_mock = Mock()
        self.app_mock.app_context.return_value.__enter__ = Mock()
        self.app_mock.app_context.return_value.__exit__ = Mock()
        
    def test_worker_initialization(self):
        """Test worker initializes correctly."""
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.5)
        
        assert worker.app == self.app_mock
        assert worker.poll_interval == 0.5
        assert not worker.running
        assert not worker.shutdown_requested
        assert worker.current_job is None
        assert worker.stats['jobs_processed'] == 0
        assert worker.stats['jobs_failed'] == 0
        assert worker.stats['jobs_interrupted'] == 0
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_worker_start_background(self, mock_queue_class):
        """Test worker starts in background mode."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_queue.dequeue.return_value = None  # No jobs available
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        worker.start(background=True)
        
        assert worker.running
        assert worker.worker_thread is not None
        assert worker.worker_thread.is_alive()
        
        # Clean up
        worker.shutdown(timeout=1.0)
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_worker_start_foreground(self, mock_queue_class):
        """Test worker starts in foreground mode."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_queue.dequeue.return_value = None
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        
        # Start worker in background thread for testing
        def start_worker():
            worker.start(background=False)
        
        worker_thread = threading.Thread(target=start_worker, daemon=True)
        worker_thread.start()
        
        # Give it time to start
        time.sleep(0.2)
        
        assert worker.running
        assert worker.worker_thread is None  # No background thread in foreground mode
        
        # Clean up
        worker.shutdown(timeout=1.0)
        worker_thread.join(timeout=1.0)
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_worker_shutdown_graceful(self, mock_queue_class):
        """Test worker shuts down gracefully."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_queue.dequeue.return_value = None
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        worker.start(background=True)
        
        # Verify it's running
        assert worker.running
        
        # Shutdown
        worker.shutdown(timeout=1.0)
        
        assert not worker.running
        assert worker.shutdown_requested
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    @patch('app.services.priority_queue_worker.UnifiedAnalysisService')
    def test_process_song_analysis_job(self, mock_analysis_service_class, mock_queue_class):
        """Test processing a song analysis job."""
        # Setup mocks
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        
        mock_analysis_service = Mock()
        mock_analysis_service_class.return_value = mock_analysis_service
        
        # Mock analysis result
        mock_analysis_result = Mock()
        mock_analysis_result.score = 85
        mock_analysis_result.concern_level = 'low'
        mock_analysis_result.status = 'completed'
        mock_analysis_result.themes = ['faith', 'hope']
        mock_analysis_result.explanation = 'Good Christian song'
        
        mock_analysis_service.analyze_song.return_value = mock_analysis_result
        
        # Create test job
        test_job = AnalysisJob(
            job_id='test_song_123',
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=123,
            created_at=datetime.now(),
            metadata={'song_id': 123}
        )
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        worker._process_job(test_job)
        
        # Verify analysis was called
        mock_analysis_service.analyze_song.assert_called_once_with(123, 1)
        
        # Verify job was marked as completed
        mock_queue.complete_job.assert_called_once_with('test_song_123', success=True)
        
        # Verify stats were updated
        assert worker.stats['jobs_processed'] == 1
        assert worker.stats['jobs_failed'] == 0
        
    def test_process_playlist_analysis_job(self):
        """Test processing a playlist analysis job."""
        # Setup mocks
        mock_queue = Mock()
        # Mock queue status to avoid interruption logic issues
        mock_queue.get_queue_status.return_value = {
            'priority_counts': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        }
        
        mock_analysis_service = Mock()

        # Mock analysis result
        mock_analysis_result = Mock()
        mock_analysis_result.score = 85
        mock_analysis_result.concern_level = 'low'
        mock_analysis_result.status = 'completed'
        mock_analysis_result.themes = ['faith']
        mock_analysis_result.explanation = 'Good song'

        mock_analysis_service.analyze_song.return_value = mock_analysis_result

        # Create test job
        test_job = AnalysisJob(
            job_id='test_playlist_456',
            job_type=JobType.PLAYLIST_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=1,
            target_id=456,
            created_at=datetime.now(),
            metadata={
                'playlist_id': 456,
                'song_ids': [101, 102, 103]
            }
        )

        worker = PriorityQueueWorker(
            app=None,  # Don't use Flask app to avoid context issues
            poll_interval=0.1,
            queue=mock_queue,
            analysis_service=mock_analysis_service
        )
        worker._process_job(test_job)

        # Verify all songs were analyzed
        assert mock_analysis_service.analyze_song.call_count == 3
        
        # Verify job was marked as completed
        mock_queue.complete_job.assert_called_once_with('test_playlist_456', success=True)
        
    def test_process_background_analysis_job(self):
        """Test processing a background analysis job."""
        # Setup mocks
        mock_queue = Mock()
        # Mock queue status to avoid interruption logic issues
        mock_queue.get_queue_status.return_value = {
            'priority_counts': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        }
        
        mock_analysis_service = Mock()

        # Mock analysis result
        mock_analysis_result = Mock()
        mock_analysis_result.score = 75
        mock_analysis_result.concern_level = 'medium'
        mock_analysis_result.status = 'completed'
        mock_analysis_result.themes = ['worship']
        mock_analysis_result.explanation = 'Decent song'

        mock_analysis_service.analyze_song.return_value = mock_analysis_result

        # Create test job
        test_job = AnalysisJob(
            job_id='test_background_789',
            job_type=JobType.BACKGROUND_ANALYSIS,
            priority=JobPriority.LOW,
            user_id=2,
            target_id=0,  # Not used for background analysis
            created_at=datetime.now(),
            metadata={
                'song_ids': [201, 202]
            }
        )

        worker = PriorityQueueWorker(
            app=None,  # Don't use Flask app to avoid context issues
            poll_interval=0.1,
            queue=mock_queue,
            analysis_service=mock_analysis_service
        )
        worker._process_job(test_job)

        # Verify songs were analyzed
        assert mock_analysis_service.analyze_song.call_count == 2
        
        # Verify job was marked as completed
        mock_queue.complete_job.assert_called_once_with('test_background_789', success=True)
        
    def test_job_failure_handling(self):
        """Test handling of job failures."""
        # Setup mocks
        mock_queue = Mock()
        mock_analysis_service = Mock()

        # Make analysis service raise an exception using a callable
        def raise_exception(*args, **kwargs):
            raise Exception("Analysis failed")
        
        mock_analysis_service.analyze_song.side_effect = raise_exception

        # Create test job
        test_job = AnalysisJob(
            job_id='test_fail_999',
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=999,
            created_at=datetime.now(),
            metadata={'song_id': 999}
        )

        worker = PriorityQueueWorker(
            app=None,  # Don't use Flask app to avoid context issues
            poll_interval=0.1,
            queue=mock_queue,
            analysis_service=mock_analysis_service
        )
        
        worker._process_job(test_job)

        # Verify job was marked as failed
        mock_queue.complete_job.assert_called_once_with(
            'test_fail_999',
            success=False,
            error_message='Job failed: Analysis failed'
        )
        
        # Verify stats were updated
        assert worker.stats['jobs_processed'] == 0
        assert worker.stats['jobs_failed'] == 1
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_job_interruption_logic(self, mock_queue_class):
        """Test job interruption logic for higher priority jobs."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        
        # Mock queue status showing high priority jobs available
        mock_queue.get_queue_status.return_value = {
            'priority_counts': {  # Use priority_counts instead of priority_breakdown
                'HIGH': 2,
                'MEDIUM': 1,
                'LOW': 0
            }
        }
        
        worker = PriorityQueueWorker(
            app=None,  # Don't use Flask app to avoid context issues
            poll_interval=0.1,
            queue=mock_queue
        )
        
        # Set current job as medium priority
        worker.current_job = AnalysisJob(
            job_id='current_medium',
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=1,
            target_id=123,
            created_at=datetime.now(),
            metadata={'song_id': 123}
        )
        
        # Check if interruption should happen
        should_interrupt = worker._should_interrupt_current_job()
        assert should_interrupt  # Medium priority job should be interrupted for high priority
        
        # Test interruption
        worker._interrupt_current_job()
        
        # Verify job was interrupted
        mock_queue.interrupt_job.assert_called_once_with('current_medium')
        assert worker.stats['jobs_interrupted'] == 1
        assert worker.current_job is None
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_worker_health_check(self, mock_queue_class):
        """Test worker health checking."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_queue.health_check.return_value = {'healthy': True}
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        worker.running = True
        
        # Test healthy worker
        assert worker.is_healthy()
        
        # Test unhealthy worker (not running)
        worker.running = False
        assert not worker.is_healthy()
        
        # Test unhealthy worker (stale heartbeat)
        worker.running = True
        worker.stats['last_heartbeat'] = datetime.now() - timedelta(seconds=60)
        assert not worker.is_healthy()
        
        # Test unhealthy queue
        worker.stats['last_heartbeat'] = datetime.now()
        mock_queue.health_check.return_value = {'healthy': False}
        assert not worker.is_healthy()
        
    @patch('app.services.priority_queue_worker.PriorityAnalysisQueue')
    def test_worker_status_reporting(self, mock_queue_class):
        """Test worker status reporting."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_queue.get_queue_status.return_value = {'total_jobs': 5}
        mock_queue.health_check.return_value = {'healthy': True}
        
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        worker.running = True
        worker.stats['jobs_processed'] = 10
        worker.stats['jobs_failed'] = 2
        
        # Set current job
        worker.current_job = AnalysisJob(
            job_id='status_test',
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=123,
            created_at=datetime.now(),
            metadata={'song_id': 123}
        )
        
        status = worker.get_status()
        
        assert status['running']
        assert status['current_job']['job_id'] == 'status_test'
        assert status['current_job']['job_type'] == 'SONG_ANALYSIS'
        assert status['current_job']['priority'] == 'HIGH'
        assert status['current_job']['user_id'] == 1
        assert status['stats']['jobs_processed'] == 10
        assert status['stats']['jobs_failed'] == 2
        assert status['queue_status']['total_jobs'] == 5
        assert status['health']['healthy']
        
    def test_missing_song_id_error(self):
        """Test error handling when song_id is missing from job metadata."""
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        
        # Create job without song_id
        test_job = AnalysisJob(
            job_id='test_missing_song',
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=123,
            created_at=datetime.now(),
            metadata={}  # Missing song_id
        )
        
        with pytest.raises(ValueError, match="Song analysis job missing song_id in metadata"):
            worker._process_song_analysis(test_job)
            
    def test_missing_playlist_id_error(self):
        """Test error handling when playlist_id is missing from job metadata."""
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        
        # Create job without playlist_id
        test_job = AnalysisJob(
            job_id='test_missing_playlist',
            job_type=JobType.PLAYLIST_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=1,
            target_id=456,
            created_at=datetime.now(),
            metadata={'song_ids': [1, 2, 3]}  # Missing playlist_id
        )
        
        with pytest.raises(ValueError, match="Playlist analysis job missing playlist_id in metadata"):
            worker._process_playlist_analysis(test_job)
            
    def test_missing_song_ids_error(self):
        """Test error handling when song_ids is missing from background job metadata."""
        worker = PriorityQueueWorker(app=self.app_mock, poll_interval=0.1)
        
        # Create job without song_ids
        test_job = AnalysisJob(
            job_id='test_missing_songs',
            job_type=JobType.BACKGROUND_ANALYSIS,
            priority=JobPriority.LOW,
            user_id=1,
            target_id=0,
            created_at=datetime.now(),
            metadata={}  # Missing song_ids
        )
        
        with pytest.raises(ValueError, match="Background analysis job missing song_ids in metadata"):
            worker._process_background_analysis(test_job)


class TestWorkerGlobalFunctions:
    """Test global worker management functions."""
    
    def test_init_worker(self):
        """Test worker initialization."""
        app_mock = Mock()
        
        # Clear any existing worker
        import app.services.priority_queue_worker as worker_module
        worker_module._worker_instance = None
        
        worker = init_worker(app_mock)
        
        assert worker is not None
        assert worker.app == app_mock
        assert get_worker() == worker
        
        # Test that calling init_worker again returns the same instance
        worker2 = init_worker(app_mock)
        assert worker2 is worker
        
    def test_get_worker_none(self):
        """Test get_worker returns None when no worker initialized."""
        import app.services.priority_queue_worker as worker_module
        worker_module._worker_instance = None
        
        assert get_worker() is None
        
    @patch('app.services.priority_queue_worker.get_worker')
    def test_start_worker_success(self, mock_get_worker):
        """Test starting the global worker instance."""
        from app.services.priority_queue_worker import start_worker
        
        mock_worker = Mock()
        mock_get_worker.return_value = mock_worker
        
        start_worker(background=True)
        
        mock_worker.start.assert_called_once_with(background=True)
        
    @patch('app.services.priority_queue_worker.get_worker')
    def test_start_worker_no_instance(self, mock_get_worker):
        """Test starting worker when no instance exists."""
        from app.services.priority_queue_worker import start_worker
        
        mock_get_worker.return_value = None
        
        # Should not raise an exception, just log an error
        start_worker(background=True)
        
    @patch('app.services.priority_queue_worker.get_worker')
    def test_shutdown_worker_success(self, mock_get_worker):
        """Test shutting down the global worker instance."""
        from app.services.priority_queue_worker import shutdown_worker
        
        mock_worker = Mock()
        mock_get_worker.return_value = mock_worker
        
        shutdown_worker()
        
        mock_worker.shutdown.assert_called_once()
        
    @patch('app.services.priority_queue_worker.get_worker')
    def test_shutdown_worker_no_instance(self, mock_get_worker):
        """Test shutting down worker when no instance exists."""
        from app.services.priority_queue_worker import shutdown_worker
        
        mock_get_worker.return_value = None
        
        # Should not raise an exception
        shutdown_worker()


class TestWorkerIntegration:
    """Integration tests for the worker with Flask app."""
    
    def test_worker_with_flask_context(self):
        """Test worker operates correctly with Flask app context."""
        from flask import Flask
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        with app.app_context():
            worker = PriorityQueueWorker(app=app, poll_interval=0.1)
            
            # Test that worker can access app context
            assert worker.app == app
            
            # Test _execute_song_analysis uses app context
            with patch.object(worker.analysis_service, 'analyze_song') as mock_analyze:
                mock_result = Mock()
                mock_result.score = 85
                mock_result.concern_level = 'low'
                mock_result.status = 'completed'
                mock_result.themes = ['faith']
                mock_result.explanation = 'Good song'
                mock_analyze.return_value = mock_result
                
                result = worker._execute_song_analysis(123, 1)
                
                assert result['score'] == 85
                assert result['concern_level'] == 'low'
                assert result['themes'] == ['faith']
                mock_analyze.assert_called_once_with(123, 1) 