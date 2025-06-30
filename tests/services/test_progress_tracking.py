"""
Tests for Progress Tracking and ETA functionality

This module tests the progress tracking system that provides real-time updates
on job progress and estimated completion times.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.progress_tracker import (
    ProgressTracker, ProgressUpdate, ETACalculator, 
    JobProgress, ProgressPersistence
)
from app.services.priority_analysis_queue import JobType, JobStatus, JobPriority


class TestProgressUpdate:
    """Test ProgressUpdate data structure"""
    
    def test_progress_update_creation(self):
        """Test creating a progress update"""
        update = ProgressUpdate(
            job_id="test-job-123",
            progress=0.5,
            message="Processing song 5 of 10",
            current_step="lyrics_analysis",
            total_steps=4,
            step_progress=0.8
        )
        
        assert update.job_id == "test-job-123"
        assert update.progress == 0.5
        assert update.message == "Processing song 5 of 10"
        assert update.current_step == "lyrics_analysis"
        assert update.total_steps == 4
        assert update.step_progress == 0.8
        assert update.timestamp is not None
    
    def test_progress_update_to_dict(self):
        """Test serializing progress update to dictionary"""
        timestamp = datetime.now(timezone.utc)
        update = ProgressUpdate(
            job_id="test-job-123",
            progress=0.75,
            message="Almost done",
            timestamp=timestamp
        )
        
        data = update.to_dict()
        
        assert data['job_id'] == "test-job-123"
        assert data['progress'] == 0.75
        assert data['message'] == "Almost done"
        assert data['timestamp'] == timestamp.isoformat()
        assert data['current_step'] is None
        assert data['total_steps'] is None
        assert data['step_progress'] is None
    
    def test_progress_update_from_dict(self):
        """Test deserializing progress update from dictionary"""
        timestamp = datetime.now(timezone.utc)
        data = {
            'job_id': "test-job-456",
            'progress': 0.25,
            'message': "Starting analysis",
            'timestamp': timestamp.isoformat(),
            'current_step': "preprocessing",
            'total_steps': 3,
            'step_progress': 0.1
        }
        
        update = ProgressUpdate.from_dict(data)
        
        assert update.job_id == "test-job-456"
        assert update.progress == 0.25
        assert update.message == "Starting analysis"
        assert update.current_step == "preprocessing"
        assert update.total_steps == 3
        assert update.step_progress == 0.1
        # Timestamp comparison with some tolerance for microseconds
        assert abs((update.timestamp - timestamp).total_seconds()) < 1


class TestJobProgress:
    """Test JobProgress tracking"""
    
    def test_job_progress_creation(self):
        """Test creating job progress tracker"""
        progress = JobProgress(
            job_id="test-job-789",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        
        assert progress.job_id == "test-job-789"
        assert progress.job_type == JobType.SONG_ANALYSIS
        assert progress.total_items == 1
        assert progress.completed_items == 0
        assert progress.estimated_duration_per_item == 30.0
        assert progress.start_time is not None
        assert progress.current_progress == 0.0
    
    def test_job_progress_update_completion(self):
        """Test updating job progress completion"""
        progress = JobProgress(
            job_id="test-job-789",
            job_type=JobType.PLAYLIST_ANALYSIS,
            total_items=10,
            estimated_duration_per_item=25.0
        )
        
        # Complete 3 items
        progress.update_completion(3)
        
        assert progress.completed_items == 3
        assert progress.current_progress == 0.3
        assert not progress.is_complete
        
        # Complete all items
        progress.update_completion(10)
        
        assert progress.completed_items == 10
        assert progress.current_progress == 1.0
        assert progress.is_complete
    
    def test_job_progress_update_step(self):
        """Test updating current step progress"""
        progress = JobProgress(
            job_id="test-job-789",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        
        progress.update_step("lyrics_fetching", 0.5, "Fetching lyrics from Genius")
        
        assert progress.current_step == "lyrics_fetching"
        assert progress.step_progress == 0.5
        assert progress.current_message == "Fetching lyrics from Genius"
    
    def test_job_progress_calculate_eta(self):
        """Test ETA calculation"""
        progress = JobProgress(
            job_id="test-job-789",
            job_type=JobType.PLAYLIST_ANALYSIS,
            total_items=10,
            estimated_duration_per_item=20.0
        )
        
        # Simulate 2 items completed after 30 seconds
        progress.start_time = datetime.now(timezone.utc) - timedelta(seconds=30)
        progress.update_completion(2)
        
        eta_seconds = progress.calculate_eta()
        
        # Should be approximately 120 seconds (8 remaining * 15 seconds average)
        assert 100 <= eta_seconds <= 140  # Allow some variance
    
    def test_job_progress_to_dict(self):
        """Test serializing job progress to dictionary"""
        start_time = datetime.now(timezone.utc)
        progress = JobProgress(
            job_id="test-job-789",
            job_type=JobType.BACKGROUND_ANALYSIS,
            total_items=50,
            estimated_duration_per_item=15.0
        )
        progress.start_time = start_time
        progress.update_completion(10)
        progress.update_step("analysis", 0.3, "Analyzing song content")
        
        data = progress.to_dict()
        
        assert data['job_id'] == "test-job-789"
        assert data['job_type'] == JobType.BACKGROUND_ANALYSIS.value
        assert data['total_items'] == 50
        assert data['completed_items'] == 10
        assert data['current_progress'] == 0.2
        assert data['start_time'] == start_time.isoformat()
        assert data['current_step'] == "analysis"
        assert data['step_progress'] == 0.3
        assert data['current_message'] == "Analyzing song content"


class TestETACalculator:
    """Test ETA calculation logic"""
    
    def test_eta_calculator_initialization(self):
        """Test ETA calculator initialization"""
        calculator = ETACalculator()
        
        assert calculator.historical_data == {}
        assert calculator.default_durations[JobType.SONG_ANALYSIS] == 30.0
        assert calculator.default_durations[JobType.PLAYLIST_ANALYSIS] == 25.0
        assert calculator.default_durations[JobType.BACKGROUND_ANALYSIS] == 20.0
    
    def test_eta_calculator_record_completion(self):
        """Test recording job completion for historical data"""
        calculator = ETACalculator()
        
        # Record some completions
        calculator.record_completion(JobType.SONG_ANALYSIS, 35.5)
        calculator.record_completion(JobType.SONG_ANALYSIS, 28.2)
        calculator.record_completion(JobType.PLAYLIST_ANALYSIS, 22.8)
        
        assert len(calculator.historical_data[JobType.SONG_ANALYSIS]) == 2
        assert len(calculator.historical_data[JobType.PLAYLIST_ANALYSIS]) == 1
        assert 35.5 in calculator.historical_data[JobType.SONG_ANALYSIS]
        assert 28.2 in calculator.historical_data[JobType.SONG_ANALYSIS]
        assert 22.8 in calculator.historical_data[JobType.PLAYLIST_ANALYSIS]
    
    def test_eta_calculator_get_average_duration(self):
        """Test getting average duration for job type"""
        calculator = ETACalculator()
        
        # Test with no historical data (should return default)
        avg_duration = calculator.get_average_duration(JobType.SONG_ANALYSIS)
        assert avg_duration == 30.0
        
        # Add historical data
        calculator.record_completion(JobType.SONG_ANALYSIS, 40.0)
        calculator.record_completion(JobType.SONG_ANALYSIS, 20.0)
        calculator.record_completion(JobType.SONG_ANALYSIS, 30.0)
        
        avg_duration = calculator.get_average_duration(JobType.SONG_ANALYSIS)
        assert avg_duration == 30.0  # (40 + 20 + 30) / 3
    
    def test_eta_calculator_calculate_eta(self):
        """Test ETA calculation with various scenarios"""
        calculator = ETACalculator()
        
        # Test with no progress
        eta = calculator.calculate_eta(
            job_type=JobType.SONG_ANALYSIS,
            total_items=5,
            completed_items=0,
            elapsed_time=0
        )
        assert eta == 150.0  # 5 * 30.0 default
        
        # Test with some progress
        eta = calculator.calculate_eta(
            job_type=JobType.SONG_ANALYSIS,
            total_items=10,
            completed_items=3,
            elapsed_time=60  # 1 minute for 3 items = 20 sec per item
        )
        assert eta == 140.0  # 7 remaining * 20 sec per item
        
        # Test with historical data
        calculator.record_completion(JobType.SONG_ANALYSIS, 25.0)
        calculator.record_completion(JobType.SONG_ANALYSIS, 35.0)
        
        eta = calculator.calculate_eta(
            job_type=JobType.SONG_ANALYSIS,
            total_items=6,
            completed_items=0,
            elapsed_time=0
        )
        assert eta == 180.0  # 6 * 30.0 (average of 25, 35, and default 30)


class TestProgressPersistence:
    """Test progress persistence across app restarts"""
    
    @patch('redis.Redis')
    def test_progress_persistence_initialization(self, mock_redis):
        """Test progress persistence initialization"""
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        
        persistence = ProgressPersistence()
        
        assert persistence.redis == mock_redis_instance
        mock_redis.from_url.assert_called_once()
    
    @patch('redis.Redis')
    def test_save_progress(self, mock_redis):
        """Test saving job progress to Redis"""
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        
        persistence = ProgressPersistence()
        
        progress = JobProgress(
            job_id="test-job-123",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        progress.update_completion(0)
        progress.update_step("analysis", 0.5, "Analyzing content")
        
        persistence.save_progress(progress)
        
        # Verify Redis set was called with correct key and serialized data
        mock_redis_instance.set.assert_called_once()
        call_args = mock_redis_instance.set.call_args
        assert call_args[0][0] == "progress:test-job-123"
        assert '"job_id": "test-job-123"' in call_args[0][1]
        assert call_args[1]['ex'] == 86400  # 24 hour TTL
    
    @patch('redis.Redis')
    def test_load_progress(self, mock_redis):
        """Test loading job progress from Redis"""
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        
        # Mock Redis get response
        progress_data = {
            'job_id': "test-job-456",
            'job_type': JobType.PLAYLIST_ANALYSIS.value,
            'total_items': 10,
            'completed_items': 3,
            'current_progress': 0.3,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'estimated_duration_per_item': 25.0,
            'current_step': "lyrics_fetching",
            'step_progress': 0.7,
            'current_message': "Fetching lyrics"
        }
        mock_redis_instance.get.return_value = json.dumps(progress_data)
        
        persistence = ProgressPersistence()
        progress = persistence.load_progress("test-job-456")
        
        assert progress is not None
        assert progress.job_id == "test-job-456"
        assert progress.job_type == JobType.PLAYLIST_ANALYSIS
        assert progress.total_items == 10
        assert progress.completed_items == 3
        assert progress.current_progress == 0.3
        assert progress.current_step == "lyrics_fetching"
        assert progress.step_progress == 0.7
        assert progress.current_message == "Fetching lyrics"
        
        mock_redis_instance.get.assert_called_once_with("progress:test-job-456")
    
    @patch('redis.Redis')
    def test_load_progress_not_found(self, mock_redis):
        """Test loading progress when job not found"""
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        
        persistence = ProgressPersistence()
        progress = persistence.load_progress("nonexistent-job")
        
        assert progress is None
        mock_redis_instance.get.assert_called_once_with("progress:nonexistent-job")
    
    @patch('redis.Redis')
    def test_delete_progress(self, mock_redis):
        """Test deleting job progress from Redis"""
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        
        persistence = ProgressPersistence()
        persistence.delete_progress("test-job-789")
        
        mock_redis_instance.delete.assert_called_once_with("progress:test-job-789")


class TestProgressTracker:
    """Test the main ProgressTracker class"""
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_progress_tracker_initialization(self, mock_eta_calc, mock_persistence):
        """Test progress tracker initialization"""
        tracker = ProgressTracker()
        
        assert tracker.eta_calculator is not None
        assert tracker.persistence is not None
        assert tracker.active_jobs == {}
        assert tracker.subscribers == {}
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_start_job_tracking(self, mock_eta_calc, mock_persistence):
        """Test starting job progress tracking"""
        tracker = ProgressTracker()
        
        job_progress = tracker.start_job_tracking(
            job_id="test-job-123",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        
        assert job_progress.job_id == "test-job-123"
        assert job_progress.job_type == JobType.SONG_ANALYSIS
        assert tracker.active_jobs["test-job-123"] == job_progress
        
        # Verify persistence save was called
        tracker.persistence.save_progress.assert_called_once_with(job_progress)
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_update_job_progress(self, mock_eta_calc, mock_persistence):
        """Test updating job progress"""
        tracker = ProgressTracker()
        
        # Start tracking a job
        job_progress = tracker.start_job_tracking(
            job_id="test-job-456",
            job_type=JobType.PLAYLIST_ANALYSIS,
            total_items=5,
            estimated_duration_per_item=25.0
        )
        
        # Update progress
        update = tracker.update_job_progress(
            job_id="test-job-456",
            completed_items=2,
            current_step="analysis",
            step_progress=0.6,
            message="Analyzing song 2 of 5"
        )
        
        assert update.job_id == "test-job-456"
        assert update.progress == 0.4  # 2/5
        assert update.message == "Analyzing song 2 of 5"
        assert update.current_step == "analysis"
        assert update.step_progress == 0.6
        
        # Verify job progress was updated
        assert job_progress.completed_items == 2
        assert job_progress.current_step == "analysis"
        assert job_progress.step_progress == 0.6
        
        # Verify persistence save was called
        assert tracker.persistence.save_progress.call_count == 2  # Initial + update
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_complete_job_tracking(self, mock_eta_calc, mock_persistence):
        """Test completing job tracking"""
        tracker = ProgressTracker()
        
        # Start tracking a job
        start_time = datetime.now(timezone.utc) - timedelta(seconds=45)
        job_progress = tracker.start_job_tracking(
            job_id="test-job-789",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        job_progress.start_time = start_time
        
        # Update progress to simulate completion
        job_progress.update_completion(1)
        
        # Complete the job
        tracker.complete_job_tracking("test-job-789", success=True)
        
        # Verify job was removed from active jobs
        assert "test-job-789" not in tracker.active_jobs
        
        # Verify ETA calculator recorded the completion
        tracker.eta_calculator.record_completion.assert_called_once()
        call_args = tracker.eta_calculator.record_completion.call_args[0]
        assert call_args[0] == JobType.SONG_ANALYSIS
        assert 40 <= call_args[1] <= 50  # Duration should be around 45 seconds
        
        # Verify persistence cleanup
        tracker.persistence.delete_progress.assert_called_once_with("test-job-789")
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_get_job_progress(self, mock_eta_calc, mock_persistence):
        """Test getting current job progress"""
        tracker = ProgressTracker()
        
        # Test with active job
        job_progress = tracker.start_job_tracking(
            job_id="test-job-active",
            job_type=JobType.SONG_ANALYSIS,
            total_items=1,
            estimated_duration_per_item=30.0
        )
        
        result = tracker.get_job_progress("test-job-active")
        assert result == job_progress
        
        # Test with non-active job (should try to load from persistence)
        mock_persistence_instance = Mock()
        tracker.persistence = mock_persistence_instance
        mock_persistence_instance.load_progress.return_value = None
        
        result = tracker.get_job_progress("test-job-inactive")
        assert result is None
        mock_persistence_instance.load_progress.assert_called_once_with("test-job-inactive")
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_subscribe_to_progress(self, mock_eta_calc, mock_persistence):
        """Test subscribing to progress updates"""
        tracker = ProgressTracker()
        
        callback = Mock()
        tracker.subscribe_to_progress("test-job-123", callback)
        
        assert "test-job-123" in tracker.subscribers
        assert callback in tracker.subscribers["test-job-123"]
    
    @patch('app.services.progress_tracker.ProgressPersistence')
    @patch('app.services.progress_tracker.ETACalculator')
    def test_notify_subscribers(self, mock_eta_calc, mock_persistence):
        """Test notifying progress subscribers"""
        tracker = ProgressTracker()
        
        # Set up subscribers
        callback1 = Mock()
        callback2 = Mock()
        tracker.subscribe_to_progress("test-job-123", callback1)
        tracker.subscribe_to_progress("test-job-123", callback2)
        
        # Create and notify with progress update
        update = ProgressUpdate(
            job_id="test-job-123",
            progress=0.5,
            message="Halfway done"
        )
        
        tracker._notify_subscribers(update)
        
        # Verify both callbacks were called
        callback1.assert_called_once_with(update)
        callback2.assert_called_once_with(update)


# Import json for serialization tests
import json 