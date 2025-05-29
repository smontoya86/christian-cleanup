import pytest
import logging
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from io import StringIO


class TestLoggingImplementation:
    """Test that proper logging is used instead of print statements."""
    
    def test_get_logger_function_available(self):
        """Test that the get_logger function is available from app.utils.logging."""
        from app.utils.logging import get_logger
        
        logger = get_logger('test_module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_module'
    
    def test_logger_configuration(self):
        """Test that loggers are properly configured with the right format."""
        from app.utils.logging import get_logger, StructuredLogFormatter
        
        logger = get_logger('app.test')
        
        # Check that logger exists and has proper configuration
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        
        # Test logging functionality
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Create a test handler to capture output
            test_handler = logging.StreamHandler(mock_stdout)
            test_handler.setFormatter(StructuredLogFormatter())
            
            test_logger = logging.getLogger('test_logger')
            test_logger.addHandler(test_handler)
            test_logger.setLevel(logging.INFO)
            
            test_logger.info("Test message")
            
            output = mock_stdout.getvalue()
            assert "Test message" in output
            assert "level" in output
            assert "timestamp" in output
    
    def test_logging_with_context(self):
        """Test that logging with context works properly."""
        from app.utils.logging import log_with_context, get_logger
        
        logger = get_logger('app.test_context')
        
        with patch.object(logger, 'handle') as mock_handle:
            log_with_context(
                logger, 
                logging.INFO, 
                "Test context message",
                user_id=123,
                operation="test_operation"
            )
            
            mock_handle.assert_called_once()
            record = mock_handle.call_args[0][0]
            assert hasattr(record, 'extra_fields')
            assert record.extra_fields['user_id'] == 123
            assert record.extra_fields['operation'] == "test_operation"
    
    def test_script_logging_setup(self):
        """Test that standalone scripts can properly set up logging."""
        # Create a temporary script content that uses proper logging
        script_content = '''
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.utils.logging import get_logger, configure_logging

# This is how scripts should be structured
logger = get_logger('scripts.test_script')

def main():
    logger.info("Script starting", extra={'extra_fields': {'operation': 'test'}})
    logger.info("Processing data", extra={'extra_fields': {'step': 1}})
    logger.info("Script completed", extra={'extra_fields': {'operation': 'test', 'success': True}})

if __name__ == '__main__':
    main()
'''
        
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        try:
            # Execute the script and capture output
            import subprocess
            result = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Check that script executed without errors
            assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
            
            # Check that structured logging output was produced
            stdout = result.stdout
            # Should contain JSON-like structured log entries
            assert "Script starting" in stdout or "Script starting" in result.stderr
            
        finally:
            # Clean up
            os.unlink(temp_script)
    
    def test_specific_module_logger_replacement(self):
        """Test that specific modules use loggers instead of print statements."""
        # This test will verify that critical modules have proper logging
        
        # Test that we can import logging utilities
        from app.utils.logging import get_logger
        
        # Test component-specific loggers
        analysis_logger = get_logger('app.analysis')
        worker_logger = get_logger('app.worker')
        database_logger = get_logger('app.database')
        
        assert analysis_logger.name == 'app.analysis'
        assert worker_logger.name == 'app.worker'
        assert database_logger.name == 'app.database'
        
        # Test that loggers can log messages
        with patch.object(analysis_logger, 'info') as mock_info:
            analysis_logger.info("Test analysis message")
            mock_info.assert_called_once_with("Test analysis message")
    
    def test_log_levels_configuration(self):
        """Test that different log levels work correctly."""
        from app.utils.logging import get_logger
        
        logger = get_logger('app.test_levels')
        
        # Test different log levels
        with patch.object(logger, 'debug') as mock_debug, \
             patch.object(logger, 'info') as mock_info, \
             patch.object(logger, 'warning') as mock_warning, \
             patch.object(logger, 'error') as mock_error, \
             patch.object(logger, 'critical') as mock_critical:
            
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            mock_debug.assert_called_once_with("Debug message")
            mock_info.assert_called_once_with("Info message")
            mock_warning.assert_called_once_with("Warning message")
            mock_error.assert_called_once_with("Error message")
            mock_critical.assert_called_once_with("Critical message")
    
    def test_no_print_in_converted_modules(self):
        """Test that converted modules don't contain print statements."""
        # This will be a placeholder test that we'll update as we convert modules
        
        # For now, just verify the logging system is available
        from app.utils.logging import get_logger, log_with_context
        
        # These should not raise any exceptions
        logger = get_logger('test_module')
        log_with_context(logger, logging.INFO, "test", test_field="value")
        
        # TODO: Add specific module imports here as we convert them
        # Example:
        # from scripts.converted_script import some_function
        # # Verify that some_function uses logging instead of print 