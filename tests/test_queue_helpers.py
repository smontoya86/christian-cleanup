"""
Unit tests for queue helper functions.

Tests the utility functions added to app/queue.py for monitoring and managing
the Redis Queue.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock


def test_get_queue_length():
    """Test getting the current queue length"""
    from app.queue import get_queue_length
    
    with patch('app.queue.analysis_queue') as mock_queue:
        # Mock __len__ method
        mock_queue.__len__.return_value = 5
        
        length = get_queue_length()
        
        assert length == 5


def test_get_active_workers():
    """Test getting the number of active workers"""
    from app.queue import get_active_workers
    
    with patch('rq.Worker') as MockWorker:
        # Mock Worker.all() to return list of 2 workers
        mock_worker1 = Mock()
        mock_worker2 = Mock()
        MockWorker.all.return_value = [mock_worker1, mock_worker2]
        
        count = get_active_workers()
        
        assert count == 2


def test_get_job_status():
    """Test getting job status by ID"""
    from app.queue import get_job_status
    from datetime import datetime
    
    with patch('rq.job.Job') as MockJob:
        mock_job = Mock()
        mock_job.get_status.return_value = 'started'
        mock_job.meta = {'progress': 50}
        mock_job.is_finished = False
        mock_job.created_at = datetime.now()
        mock_job.started_at = datetime.now()
        mock_job.ended_at = None
        mock_job.result = None
        
        MockJob.fetch.return_value = mock_job
        
        status = get_job_status('test-job-123')
        
        assert status['status'] == 'started'
        assert status['meta'] == {'progress': 50}


def test_cancel_job():
    """Test canceling a queued or running job"""
    from app.queue import cancel_job
    
    with patch('rq.job.Job') as MockJob:
        mock_job = Mock()
        MockJob.fetch.return_value = mock_job
        
        result = cancel_job('test-job-456')
        
        mock_job.cancel.assert_called_once()
        assert result is True


def test_clean_failed_jobs():
    """Test cleaning up failed jobs"""
    from app.queue import clean_failed_jobs
    
    with patch('rq.registry.FailedJobRegistry') as MockRegistry:
        # Mock failed registry
        mock_registry_instance = Mock()
        mock_registry_instance.get_job_ids.return_value = ['job1', 'job2', 'job3']
        MockRegistry.return_value = mock_registry_instance
        
        count = clean_failed_jobs()
        
        assert count == 3
        assert mock_registry_instance.remove.call_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

