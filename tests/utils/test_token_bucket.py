"""
Tests for TokenBucket throttling algorithm
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from app.utils.lyrics import TokenBucket


class TestTokenBucket:
    """Test suite for TokenBucket throttling algorithm"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Standard bucket: 10 tokens max, refill 5 tokens per second
        self.bucket = TokenBucket(capacity=10, refill_rate=5.0)
    
    def test_initial_bucket_is_full(self):
        """Test that bucket starts at full capacity"""
        assert self.bucket.tokens == 10
        assert self.bucket.capacity == 10
        assert self.bucket.refill_rate == 5.0
    
    def test_consume_tokens_when_available(self):
        """Test consuming tokens when bucket has sufficient tokens"""
        assert self.bucket.consume(3) is True
        assert self.bucket.tokens == 7
    
    def test_consume_all_tokens(self):
        """Test consuming all available tokens"""
        assert self.bucket.consume(10) is True
        assert self.bucket.tokens == 0
    
    def test_consume_more_than_available(self):
        """Test consuming more tokens than available fails"""
        assert self.bucket.consume(15) is False
        assert self.bucket.tokens == 10  # Should remain unchanged
    
    def test_consume_zero_tokens(self):
        """Test consuming zero tokens always succeeds"""
        assert self.bucket.consume(0) is True
        assert self.bucket.tokens == 10
    
    def test_consume_negative_tokens_fails(self):
        """Test that consuming negative tokens fails"""
        assert self.bucket.consume(-1) is False
        assert self.bucket.tokens == 10
    
    @patch('time.time')
    def test_refill_tokens_over_time(self, mock_time):
        """Test that tokens refill correctly over time"""
        # Start at time 0 with empty bucket
        mock_time.return_value = 0
        self.bucket.tokens = 0
        self.bucket.last_refill = 0
        
        # Move forward 2 seconds - should refill 10 tokens (5 per second * 2)
        mock_time.return_value = 2
        self.bucket._refill()
        
        assert self.bucket.tokens == 10  # Capped at capacity
        assert self.bucket.last_refill == 2
    
    @patch('time.time')
    def test_partial_refill(self, mock_time):
        """Test partial refill that doesn't exceed capacity"""
        # Start at time 0 with 5 tokens
        mock_time.return_value = 0
        self.bucket.tokens = 5
        self.bucket.last_refill = 0
        
        # Move forward 0.5 seconds - should add 2.5 tokens (fractional tokens allowed)
        mock_time.return_value = 0.5
        self.bucket._refill()
        
        assert self.bucket.tokens == 7.5  # 5 + 2.5 (fractional tokens preserved)
        assert self.bucket.last_refill == 0.5
    
    @patch('time.time')
    def test_refill_capped_at_capacity(self, mock_time):
        """Test that refill doesn't exceed bucket capacity"""
        # Start at time 0 with 8 tokens
        mock_time.return_value = 0
        self.bucket.tokens = 8
        self.bucket.last_refill = 0
        
        # Move forward 1 second - would add 5 tokens but capped at capacity 10
        mock_time.return_value = 1
        self.bucket._refill()
        
        assert self.bucket.tokens == 10  # Capped at capacity
        assert self.bucket.last_refill == 1
    
    @patch('time.time')
    def test_no_refill_when_time_unchanged(self, mock_time):
        """Test that no refill occurs when time hasn't advanced"""
        mock_time.return_value = 5
        self.bucket.tokens = 3
        self.bucket.last_refill = 5
        
        # Time hasn't changed
        self.bucket._refill()
        
        assert self.bucket.tokens == 3  # No change
        assert self.bucket.last_refill == 5
    
    @patch('time.time')
    def test_consume_with_refill(self, mock_time):
        """Test consuming tokens after automatic refill"""
        # Start with empty bucket at time 0
        mock_time.return_value = 0
        self.bucket.tokens = 0
        self.bucket.last_refill = 0
        
        # Move to time 1 - should refill 5 tokens
        mock_time.return_value = 1
        
        # Try to consume 3 tokens - should succeed after refill
        assert self.bucket.consume(3) is True
        assert self.bucket.tokens == 2  # 5 refilled - 3 consumed
    
    @patch('time.time')
    def test_consume_fails_even_after_refill(self, mock_time):
        """Test consuming fails when not enough tokens even after refill"""
        # Start with empty bucket at time 0
        mock_time.return_value = 0
        self.bucket.tokens = 0
        self.bucket.last_refill = 0
        
        # Move to time 1 - should refill 5 tokens
        mock_time.return_value = 1
        
        # Try to consume 8 tokens - should fail (only 5 available after refill)
        assert self.bucket.consume(8) is False
        assert self.bucket.tokens == 5  # Refilled but not consumed
    
    def test_get_available_tokens(self):
        """Test getting current available token count"""
        assert self.bucket.get_available_tokens() == 10
        
        self.bucket.consume(3)
        assert self.bucket.get_available_tokens() == 7
    
    @patch('time.time')
    def test_get_available_tokens_with_refill(self, mock_time):
        """Test getting available tokens includes automatic refill"""
        # Start with 2 tokens at time 0
        mock_time.return_value = 0
        self.bucket.tokens = 2
        self.bucket.last_refill = 0
        
        # Move to time 1 - should refill 5 more tokens
        mock_time.return_value = 1
        
        assert self.bucket.get_available_tokens() == 7  # 2 + 5 refilled
    
    def test_time_until_available_when_tokens_available(self):
        """Test time calculation when tokens are already available"""
        assert self.bucket.time_until_available(5) == 0
        
        self.bucket.consume(8)  # 2 tokens left
        assert self.bucket.time_until_available(2) == 0
    
    def test_time_until_available_when_tokens_needed(self):
        """Test time calculation when need to wait for refill"""
        self.bucket.consume(9)  # 1 token left
        
        # Need 5 tokens total, have 1, need 4 more
        # At 5 tokens/second, need 4/5 = 0.8 seconds
        expected_time = 4.0 / 5.0  # 0.8 seconds
        assert abs(self.bucket.time_until_available(5) - expected_time) < 0.01
    
    def test_time_until_available_more_than_capacity(self):
        """Test time calculation when requesting more than bucket capacity"""
        # Requesting 15 tokens but capacity is only 10
        # Should return time to reach capacity (if empty)
        self.bucket.tokens = 0
        
        # Need 10 tokens at 5 per second = 2 seconds
        expected_time = 10.0 / 5.0  # 2 seconds  
        assert abs(self.bucket.time_until_available(15) - expected_time) < 0.01
    
    def test_custom_bucket_parameters(self):
        """Test bucket with custom capacity and refill rate"""
        custom_bucket = TokenBucket(capacity=50, refill_rate=10.0)
        
        assert custom_bucket.capacity == 50
        assert custom_bucket.refill_rate == 10.0
        assert custom_bucket.tokens == 50
    
    @patch('time.time')
    def test_fractional_refill_accumulation(self, mock_time):
        """Test that fractional tokens accumulate correctly"""
        # Use bucket with 1 token/second for easier fractional testing
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        mock_time.return_value = 0
        bucket.tokens = 0
        bucket.last_refill = 0
        
        # Move forward 0.3 seconds - should add 0.3 tokens
        mock_time.return_value = 0.3
        bucket._refill()
        assert bucket.tokens == 0.3  # Has fractional tokens
        assert bucket.get_available_tokens() == 0  # But no full tokens available
        
        # Move forward another 0.8 seconds (total 1.1) - should add 0.8 more tokens
        mock_time.return_value = 1.1
        bucket._refill()
        assert bucket.tokens == 1.1  # Now has 1.1 fractional tokens
        assert bucket.get_available_tokens() == 1  # One full token available
    
    def test_reset_bucket(self):
        """Test resetting bucket to full capacity"""
        self.bucket.consume(5)
        assert self.bucket.tokens == 5
        
        before_reset = time.time()
        self.bucket.reset()
        after_reset = time.time()
        
        assert self.bucket.tokens == 10
        assert before_reset <= self.bucket.last_refill <= after_reset  # Should update to current time 