import pytest
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import redis

from app.services.priority_analysis_queue import (
    PriorityAnalysisQueue, AnalysisJob, JobType, JobPriority, JobStatus,
    enqueue_song_analysis, enqueue_playlist_analysis, enqueue_background_analysis
)


class TestAnalysisJob:
    """Test the AnalysisJob dataclass"""
    
    def test_job_creation(self):
        """Test basic job creation"""
        job = AnalysisJob(
            job_id="test-123",
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=100,
            created_at=datetime.now(timezone.utc)
        )
        
        assert job.job_id == "test-123"
        assert job.job_type == JobType.SONG_ANALYSIS
        assert job.priority == JobPriority.HIGH
        assert job.user_id == 1
        assert job.target_id == 100
        assert job.status == JobStatus.PENDING
        assert job.metadata == {}
    
    def test_job_to_dict(self):
        """Test job serialization to dictionary"""
        created_at = datetime.now(timezone.utc)
        job = AnalysisJob(
            job_id="test-123",
            job_type=JobType.PLAYLIST_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=2,
            target_id=200,
            created_at=created_at,
            metadata={"test": "value"}
        )
        
        data = job.to_dict()
        
        assert data['job_id'] == "test-123"
        assert data['job_type'] == "playlist_analysis"
        assert data['priority'] == 2
        assert data['user_id'] == 2
        assert data['target_id'] == 200
        assert data['status'] == "pending"
        assert data['created_at'] == created_at.isoformat()
        assert data['metadata'] == {"test": "value"}
    
    def test_job_from_dict(self):
        """Test job deserialization from dictionary"""
        created_at = datetime.now(timezone.utc)
        data = {
            'job_id': "test-123",
            'job_type': "background_analysis",
            'priority': 3,
            'user_id': 3,
            'target_id': 300,
            'status': "completed",
            'created_at': created_at.isoformat(),
            'started_at': created_at.isoformat(),
            'completed_at': created_at.isoformat(),
            'metadata': {"batch": "1"},
            'error_message': None
        }
        
        job = AnalysisJob.from_dict(data)
        
        assert job.job_id == "test-123"
        assert job.job_type == JobType.BACKGROUND_ANALYSIS
        assert job.priority == JobPriority.LOW
        assert job.user_id == 3
        assert job.target_id == 300
        assert job.status == JobStatus.COMPLETED
        assert job.created_at == created_at
        assert job.metadata == {"batch": "1"}


class TestPriorityAnalysisQueue:
    """Test the PriorityAnalysisQueue class"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        return Mock(spec=redis.Redis)
    
    @pytest.fixture
    def queue(self, mock_redis):
        """Create a queue instance with mock Redis"""
        return PriorityAnalysisQueue(redis_client=mock_redis)
    
    def test_queue_initialization(self, mock_redis):
        """Test queue initialization"""
        queue = PriorityAnalysisQueue(redis_client=mock_redis)
        
        assert queue.redis == mock_redis
        assert queue.queue_key == "analysis_queue"
        assert queue.jobs_key == "analysis_jobs"
        assert queue.active_key == "analysis_active"
    
    def test_enqueue_job(self, queue, mock_redis):
        """Test job enqueueing"""
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.zadd.return_value = 1
        
        # Enqueue a job
        job_id = queue.enqueue(
            job_type=JobType.SONG_ANALYSIS,
            user_id=1,
            target_id=100,
            priority=JobPriority.HIGH,
            metadata={"test": "data"}
        )
        
        # Verify job ID is returned
        assert job_id is not None
        assert len(job_id) == 36  # UUID4 length
        
        # Verify Redis operations were called
        mock_redis.hset.assert_called_once()
        mock_redis.zadd.assert_called_once()
        
        # Check the data stored in Redis
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "analysis_jobs"  # jobs_key
        assert call_args[0][1] == job_id
        
        # Parse the job data
        job_data = json.loads(call_args[0][2])
        assert job_data['job_type'] == "song_analysis"
        assert job_data['priority'] == 1
        assert job_data['user_id'] == 1
        assert job_data['target_id'] == 100
        assert job_data['metadata'] == {"test": "data"}
    
    def test_dequeue_job(self, queue, mock_redis):
        """Test job dequeueing"""
        # Create test job data
        job_id = "test-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.PLAYLIST_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=2,
            target_id=200,
            created_at=datetime.now(timezone.utc)
        )
        
        # Mock Redis operations
        mock_redis.zpopmin.return_value = [(job_id, 2.0)]
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        mock_redis.hset.return_value = True
        mock_redis.set.return_value = True
        
        # Dequeue the job
        dequeued_job = queue.dequeue()
        
        # Verify job was returned
        assert dequeued_job is not None
        assert dequeued_job.job_id == job_id
        assert dequeued_job.job_type == JobType.PLAYLIST_ANALYSIS
        assert dequeued_job.status == JobStatus.IN_PROGRESS
        assert dequeued_job.started_at is not None
        
        # Verify Redis operations
        mock_redis.zpopmin.assert_called_once_with("analysis_queue")
        mock_redis.hget.assert_called_once_with("analysis_jobs", job_id)
        mock_redis.hset.assert_called()  # Job status updated
        mock_redis.set.assert_called_once_with("analysis_active", job_id, ex=3600)
    
    def test_dequeue_empty_queue(self, queue, mock_redis):
        """Test dequeueing from empty queue"""
        mock_redis.zpopmin.return_value = []
        
        result = queue.dequeue()
        
        assert result is None
        mock_redis.zpopmin.assert_called_once_with("analysis_queue")
    
    def test_complete_job_success(self, queue, mock_redis):
        """Test successful job completion"""
        job_id = "test-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=100,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.IN_PROGRESS
        )
        
        # Mock Redis operations
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        mock_redis.hset.return_value = True
        mock_redis.get.return_value = job_id
        mock_redis.delete.return_value = 1
        mock_redis.expire.return_value = True
        
        # Complete the job
        result = queue.complete_job(job_id, success=True)
        
        assert result is True
        
        # Verify job status was updated
        mock_redis.hset.assert_called()
        call_args = mock_redis.hset.call_args
        job_data = json.loads(call_args[0][2])
        assert job_data['status'] == "completed"
        assert job_data['completed_at'] is not None
        
        # Verify active job was cleared
        mock_redis.delete.assert_called_once_with("analysis_active")
        mock_redis.expire.assert_called()
    
    def test_complete_job_failure(self, queue, mock_redis):
        """Test job completion with failure"""
        job_id = "test-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=100,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.IN_PROGRESS
        )
        
        # Mock Redis operations
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        mock_redis.hset.return_value = True
        mock_redis.get.return_value = job_id
        mock_redis.delete.return_value = 1
        mock_redis.expire.return_value = True
        
        # Complete the job with failure
        result = queue.complete_job(job_id, success=False, error_message="Test error")
        
        assert result is True
        
        # Verify job status and error were updated
        call_args = mock_redis.hset.call_args
        job_data = json.loads(call_args[0][2])
        assert job_data['status'] == "failed"
        assert job_data['error_message'] == "Test error"
    
    def test_interrupt_job(self, queue, mock_redis):
        """Test job interruption"""
        job_id = "test-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.BACKGROUND_ANALYSIS,
            priority=JobPriority.LOW,
            user_id=3,
            target_id=300,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.IN_PROGRESS
        )
        
        # Mock Redis operations
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        mock_redis.hset.return_value = True
        mock_redis.zadd.return_value = 1
        mock_redis.get.return_value = job_id
        mock_redis.delete.return_value = 1
        
        # Interrupt the job
        result = queue.interrupt_job(job_id)
        
        assert result is True
        
        # Verify job was marked as interrupted
        call_args = mock_redis.hset.call_args
        job_data = json.loads(call_args[0][2])
        assert job_data['status'] == "interrupted"
        
        # Verify job was re-queued
        mock_redis.zadd.assert_called()
        mock_redis.delete.assert_called_once_with("analysis_active")
    
    def test_get_job(self, queue, mock_redis):
        """Test getting job by ID"""
        job_id = "test-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=100,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        
        retrieved_job = queue.get_job(job_id)
        
        assert retrieved_job is not None
        assert retrieved_job.job_id == job_id
        assert retrieved_job.job_type == JobType.SONG_ANALYSIS
        mock_redis.hget.assert_called_once_with("analysis_jobs", job_id)
    
    def test_get_active_job(self, queue, mock_redis):
        """Test getting active job"""
        job_id = "active-job-123"
        job = AnalysisJob(
            job_id=job_id,
            job_type=JobType.PLAYLIST_ANALYSIS,
            priority=JobPriority.MEDIUM,
            user_id=2,
            target_id=200,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.IN_PROGRESS
        )
        
        mock_redis.get.return_value = job_id
        mock_redis.hget.return_value = json.dumps(job.to_dict())
        
        active_job = queue.get_active_job()
        
        assert active_job is not None
        assert active_job.job_id == job_id
        assert active_job.status == JobStatus.IN_PROGRESS
        
        mock_redis.get.assert_called_once_with("analysis_active")
        mock_redis.hget.assert_called_once_with("analysis_jobs", job_id)
    
    def test_get_queue_status(self, queue, mock_redis):
        """Test getting queue status"""
        # Mock queue data
        mock_redis.zcard.return_value = 3
        mock_redis.zrange.return_value = [
            ("job1", 1.0),  # High priority
            ("job2", 2.0),  # Medium priority
            ("job3", 3.0)   # Low priority
        ]
        mock_redis.hkeys.return_value = ["job1", "job2", "job3", "job4"]
        
        # Mock active job
        active_job = AnalysisJob(
            job_id="job1",
            job_type=JobType.SONG_ANALYSIS,
            priority=JobPriority.HIGH,
            user_id=1,
            target_id=100,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.IN_PROGRESS
        )
        mock_redis.get.return_value = "job1"
        mock_redis.hget.side_effect = [
            json.dumps(active_job.to_dict()),  # For get_active_job
            json.dumps(active_job.to_dict()),  # For status counting
            json.dumps(AnalysisJob(
                job_id="job2",
                job_type=JobType.PLAYLIST_ANALYSIS,
                priority=JobPriority.MEDIUM,
                user_id=2,
                target_id=200,
                created_at=datetime.now(timezone.utc),
                status=JobStatus.PENDING
            ).to_dict()),
            json.dumps(AnalysisJob(
                job_id="job3",
                job_type=JobType.BACKGROUND_ANALYSIS,
                priority=JobPriority.LOW,
                user_id=3,
                target_id=300,
                created_at=datetime.now(timezone.utc),
                status=JobStatus.PENDING
            ).to_dict()),
            json.dumps(AnalysisJob(
                job_id="job4",
                job_type=JobType.SONG_ANALYSIS,
                priority=JobPriority.HIGH,
                user_id=1,
                target_id=101,
                created_at=datetime.now(timezone.utc),
                status=JobStatus.COMPLETED
            ).to_dict())
        ]
        
        status = queue.get_queue_status()
        
        assert status['queue_length'] == 3
        assert status['total_jobs'] == 4
        assert status['active_job'] is not None
        assert status['active_job']['job_id'] == "job1"
        assert 'priority_counts' in status
        assert 'status_counts' in status
    
    def test_clear_queue_all(self, queue, mock_redis):
        """Test clearing entire queue"""
        mock_redis.zcard.return_value = 5
        mock_redis.delete.return_value = 1
        
        cleared_count = queue.clear_queue()
        
        assert cleared_count == 5
        assert mock_redis.delete.call_count == 3  # queue, jobs, active
    
    def test_clear_queue_user(self, queue, mock_redis):
        """Test clearing queue for specific user"""
        job_ids = ["job1", "job2", "job3"]
        mock_redis.zrange.return_value = job_ids
        
        # Mock jobs - job1 and job3 belong to user 1, job2 to user 2
        jobs_data = [
            AnalysisJob(
                job_id="job1", job_type=JobType.SONG_ANALYSIS, priority=JobPriority.HIGH,
                user_id=1, target_id=100, created_at=datetime.now(timezone.utc)
            ),
            AnalysisJob(
                job_id="job2", job_type=JobType.PLAYLIST_ANALYSIS, priority=JobPriority.MEDIUM,
                user_id=2, target_id=200, created_at=datetime.now(timezone.utc)
            ),
            AnalysisJob(
                job_id="job3", job_type=JobType.BACKGROUND_ANALYSIS, priority=JobPriority.LOW,
                user_id=1, target_id=300, created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_redis.hget.side_effect = [json.dumps(job.to_dict()) for job in jobs_data]
        mock_redis.zrem.return_value = 1
        mock_redis.hdel.return_value = 1
        
        cleared_count = queue.clear_queue(user_id=1)
        
        assert cleared_count == 2  # job1 and job3
        assert mock_redis.zrem.call_count == 2
        assert mock_redis.hdel.call_count == 2
    
    def test_health_check_healthy(self, queue, mock_redis):
        """Test health check when system is healthy"""
        mock_redis.ping.return_value = True
        mock_redis.zcard.return_value = 2
        mock_redis.zrange.return_value = []
        mock_redis.hkeys.return_value = ["job1", "job2"]
        mock_redis.get.return_value = None
        mock_redis.hget.return_value = None  # No job data needed for basic health check
        
        health = queue.health_check()
        
        assert health['redis_healthy'] is True
        assert health['redis_error'] is None
        assert health['queue_operational'] is True
        assert 'queue_status' in health
        assert 'timestamp' in health
    
    def test_health_check_unhealthy(self, queue, mock_redis):
        """Test health check when Redis is unhealthy"""
        mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        # Mock other operations to prevent cascading failures
        mock_redis.zcard.return_value = 0
        mock_redis.zrange.return_value = []
        mock_redis.hkeys.return_value = []
        mock_redis.get.return_value = None
        
        health = queue.health_check()
        
        assert health['redis_healthy'] is False
        assert health['redis_error'] == "Connection failed"
        assert health['queue_operational'] is False


class TestConvenienceFunctions:
    """Test the convenience functions"""
    
    @patch('app.services.priority_analysis_queue.PriorityAnalysisQueue')
    def test_enqueue_song_analysis(self, mock_queue_class):
        """Test enqueue_song_analysis convenience function"""
        mock_queue = Mock()
        mock_queue.enqueue.return_value = "job-123"
        mock_queue_class.return_value = mock_queue
        
        job_id = enqueue_song_analysis(user_id=1, song_id=100, metadata={"test": "data"})
        
        assert job_id == "job-123"
        mock_queue.enqueue.assert_called_once_with(
            job_type=JobType.SONG_ANALYSIS,
            user_id=1,
            target_id=100,
            priority=JobPriority.HIGH,
            metadata={"test": "data"}
        )
    
    @patch('app.services.priority_analysis_queue.PriorityAnalysisQueue')
    def test_enqueue_playlist_analysis(self, mock_queue_class):
        """Test enqueue_playlist_analysis convenience function"""
        mock_queue = Mock()
        mock_queue.enqueue.return_value = "job-456"
        mock_queue_class.return_value = mock_queue
        
        job_id = enqueue_playlist_analysis(user_id=2, playlist_id=200)
        
        assert job_id == "job-456"
        mock_queue.enqueue.assert_called_once_with(
            job_type=JobType.PLAYLIST_ANALYSIS,
            user_id=2,
            target_id=200,
            priority=JobPriority.MEDIUM,
            metadata=None
        )
    
    @patch('app.services.priority_analysis_queue.PriorityAnalysisQueue')
    def test_enqueue_background_analysis(self, mock_queue_class):
        """Test enqueue_background_analysis convenience function"""
        mock_queue = Mock()
        mock_queue.enqueue.side_effect = ["job-1", "job-2", "job-3"]
        mock_queue_class.return_value = mock_queue
        
        job_ids = enqueue_background_analysis(
            user_id=3, 
            song_ids=[301, 302, 303],
            metadata={"batch": "1"}
        )
        
        assert job_ids == ["job-1", "job-2", "job-3"]
        assert mock_queue.enqueue.call_count == 3
        
        # Verify each call
        calls = mock_queue.enqueue.call_args_list
        for i, call in enumerate(calls):
            assert call[1]['job_type'] == JobType.BACKGROUND_ANALYSIS
            assert call[1]['user_id'] == 3
            assert call[1]['target_id'] == 301 + i
            assert call[1]['priority'] == JobPriority.LOW
            assert call[1]['metadata'] == {"batch": "1"}


class TestPriorityOrdering:
    """Test that jobs are processed in correct priority order"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client that maintains order"""
        mock = Mock(spec=redis.Redis)
        # Use a list to simulate sorted set behavior
        mock._queue_data = []
        
        def mock_zadd(key, mapping):
            for job_id, score in mapping.items():
                mock._queue_data.append((job_id, score))
            mock._queue_data.sort(key=lambda x: x[1])  # Sort by score
            return len(mapping)
        
        def mock_zpopmin(key):
            if not mock._queue_data:
                return []
            return [mock._queue_data.pop(0)]
        
        mock.zadd.side_effect = mock_zadd
        mock.zpopmin.side_effect = mock_zpopmin
        mock.hset.return_value = True
        mock.set.return_value = True
        
        return mock
    
    def test_priority_ordering(self, mock_redis):
        """Test that jobs are dequeued in priority order"""
        queue = PriorityAnalysisQueue(redis_client=mock_redis)
        
        # Create test jobs with different priorities
        jobs = [
            AnalysisJob(
                job_id="low-job",
                job_type=JobType.BACKGROUND_ANALYSIS,
                priority=JobPriority.LOW,
                user_id=1, target_id=100,
                created_at=datetime.now(timezone.utc)
            ),
            AnalysisJob(
                job_id="high-job",
                job_type=JobType.SONG_ANALYSIS,
                priority=JobPriority.HIGH,
                user_id=1, target_id=101,
                created_at=datetime.now(timezone.utc)
            ),
            AnalysisJob(
                job_id="medium-job",
                job_type=JobType.PLAYLIST_ANALYSIS,
                priority=JobPriority.MEDIUM,
                user_id=1, target_id=102,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Mock hget to return job data - store job data after enqueue
        job_data_store = {}
        
        def mock_hset(key, job_id, data):
            job_data_store[job_id] = data
            return True
            
        def mock_hget(key, job_id):
            return job_data_store.get(job_id)
        
        mock_redis.hset.side_effect = mock_hset
        mock_redis.hget.side_effect = mock_hget
        
        # Enqueue jobs in random order
        for job in [jobs[0], jobs[1], jobs[2]]:  # low, high, medium
            queue.enqueue(
                job_type=job.job_type,
                user_id=job.user_id,
                target_id=job.target_id,
                priority=job.priority
            )
        
        # Dequeue jobs and verify order
        first_job = queue.dequeue()
        assert first_job.priority == JobPriority.HIGH
        
        second_job = queue.dequeue()
        assert second_job.priority == JobPriority.MEDIUM
        
        third_job = queue.dequeue()
        assert third_job.priority == JobPriority.LOW 