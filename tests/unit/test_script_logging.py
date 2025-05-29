import pytest
import logging
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from io import StringIO


class TestScriptLogging:
    """Test the standalone script logging utility."""
    
    def test_script_logging_import(self):
        """Test that the script logging utility can be imported."""
        from scripts.utils.script_logging import (
            setup_script_logging, 
            get_script_logger,
            log_operation_start,
            log_operation_success,
            log_operation_error,
            log_progress,
            log_warning,
            log_milestone
        )
        
        # Should not raise any exceptions
        assert setup_script_logging is not None
        assert get_script_logger is not None
        assert log_operation_start is not None
    
    def test_setup_script_logging(self):
        """Test setting up script logging."""
        from scripts.utils.script_logging import setup_script_logging
        
        logger = setup_script_logging('test_script', 'INFO')
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'scripts.test_script'
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1  # At least console handler
    
    def test_auto_detect_script_name(self):
        """Test auto-detection of script name."""
        from scripts.utils.script_logging import setup_script_logging
        
        logger = setup_script_logging()
        
        # Should auto-detect from current context
        assert isinstance(logger, logging.Logger)
        assert logger.name.startswith('scripts.')
    
    def test_operation_logging_functions(self):
        """Test the operation logging helper functions."""
        from scripts.utils.script_logging import (
            setup_script_logging,
            log_operation_start,
            log_operation_success,
            log_operation_error,
            log_progress,
            log_warning,
            log_milestone
        )
        
        logger = setup_script_logging('test_operations')
        
        # Test all operation logging functions
        with patch.object(logger, 'info') as mock_info, \
             patch.object(logger, 'error') as mock_error, \
             patch.object(logger, 'warning') as mock_warning:
            
            # Test operation start
            log_operation_start(logger, 'test_operation', context_key='value')
            mock_info.assert_called()
            
            # Test operation success
            log_operation_success(logger, 'test_operation', duration=1.5)
            assert mock_info.call_count >= 2
            
            # Test operation error
            test_error = ValueError("Test error")
            log_operation_error(logger, 'test_operation', test_error)
            mock_error.assert_called()
            
            # Test progress logging
            log_progress(logger, 'test_operation', 50, 100)
            assert mock_info.call_count >= 3
            
            # Test warning
            log_warning(logger, 'Test warning message')
            mock_warning.assert_called()
            
            # Test milestone
            log_milestone(logger, 'Test milestone')
            assert mock_info.call_count >= 4
    
    def test_structured_logging_format(self):
        """Test that the script logger produces structured JSON output."""
        from scripts.utils.script_logging import setup_script_logging
        
        # Capture log output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger = setup_script_logging('test_format')
            logger.info("Test message", extra={
                'extra_fields': {
                    'test_key': 'test_value',
                    'operation': 'test'
                }
            })
            
            output = mock_stdout.getvalue()
            
            # Should contain JSON-like structure
            assert '"level": "INFO"' in output
            assert '"message": "Test message"' in output
            assert '"script": "test_format"' in output
            assert '"test_key": "test_value"' in output
    
    def test_log_levels(self):
        """Test different log levels work correctly."""
        from scripts.utils.script_logging import setup_script_logging
        
        # Test different log levels
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            logger = setup_script_logging('test_levels', level)
            assert logger.level == getattr(logging, level)
    
    def test_get_script_logger_convenience(self):
        """Test the convenience function for getting a script logger."""
        from scripts.utils.script_logging import get_script_logger
        
        logger = get_script_logger('convenience_test')
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'scripts.convenience_test' 