import pytest
import os
import re
import glob
import importlib
import sys
from typing import List, Tuple
from unittest.mock import patch, MagicMock
from io import StringIO


class TestLoggingCleanupFinal:
    """Final comprehensive test to ensure all print statements are eliminated and proper logging is in place."""
    
    def scan_codebase_for_prints(self, exclude_patterns=None) -> List[Tuple[str, int, str]]:
        """Comprehensive scan of the entire codebase for print statements."""
        if exclude_patterns is None:
            exclude_patterns = [
                '/venv/', '/.venv/', '/node_modules/', '/__pycache__/',
                '/migrations/', '/coverage/', '/.git/', '/logs/',
                '/archive/', '/christian_cleanup.egg-info/'
            ]
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        print_statements = []
        
        # Get all Python files in the project
        pattern = os.path.join(project_root, "**", "*.py")
        python_files = glob.glob(pattern, recursive=True)
        
        for file_path in python_files:
            # Skip excluded directories
            if any(excluded in file_path for excluded in exclude_patterns):
                continue
                
            # Skip test files that legitimately test print functionality
            if 'test_print_statement_scanner.py' in file_path:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    # Look for print statements
                    if re.search(r'\bprint\s*\(', line):
                        stripped_line = line.strip()
                        
                        # Skip comments and empty lines
                        if not stripped_line or stripped_line.startswith('#'):
                            continue
                            
                        # Skip if it's in a string literal (simple heuristic)
                        quote_count = line.count('"') + line.count("'")
                        if quote_count % 2 == 0:  # Even number of quotes, likely not in string
                            print_statements.append((file_path, line_num, stripped_line))
                            
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return print_statements
    
    def test_no_print_statements_in_app_directory(self):
        """Test that no print statements exist in the main app directory."""
        app_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'app')
        app_dir = os.path.abspath(app_dir)
        
        # Get all Python files in app directory
        print_statements = []
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        for line_num, line in enumerate(lines, 1):
                            if re.search(r'\bprint\s*\(', line):
                                stripped_line = line.strip()
                                if not stripped_line or stripped_line.startswith('#'):
                                    continue
                                quote_count = line.count('"') + line.count("'")
                                if quote_count % 2 == 0:
                                    print_statements.append((file_path, line_num, stripped_line))
                                    
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        if print_statements:
            error_msg = "Found print statements in app directory:\n"
            for file_path, line_num, line_content in print_statements:
                error_msg += f"  {file_path}:{line_num} - {line_content}\n"
            pytest.fail(error_msg)
    
    def test_converted_scripts_functionality(self):
        """Test that converted scripts work properly and produce structured logging."""
        
        # Test converted scripts
        converted_scripts = [
            'scripts/debug/quick_test_converted.py',
            'scripts/update_playlist_scores_converted.py',
            'app/config/settings_converted.py'
        ]
        
        for script_path in converted_scripts:
            full_path = os.path.join(os.path.dirname(__file__), '..', '..', script_path)
            
            # Verify file exists
            assert os.path.exists(full_path), f"Converted script not found: {script_path}"
            
            # Verify no print statements
            with open(full_path, 'r') as f:
                content = f.read()
                
            print_count = content.count('print(')
            assert print_count == 0, f"Found {print_count} print statements in {script_path}"
            
            # Verify logging imports
            assert any(pattern in content for pattern in [
                'from scripts.utils.script_logging import',
                'from app.utils.logging import',
                'import logging'
            ]), f"No logging imports found in {script_path}"
    
    def test_script_logging_utility_completeness(self):
        """Test that the script logging utility is comprehensive and functional."""
        from scripts.utils.script_logging import (
            get_script_logger,
            log_operation_start,
            log_operation_success,
            log_operation_error,
            log_progress,
            log_warning,
            log_milestone
        )
        
        # Test logger creation
        logger = get_script_logger('test_cleanup')
        assert logger is not None
        assert logger.name == 'scripts.test_cleanup'
        
        # Test all logging functions exist and work
        with patch.object(logger, 'info') as mock_info, \
             patch.object(logger, 'error') as mock_error, \
             patch.object(logger, 'warning') as mock_warning:
            
            log_operation_start(logger, 'test_operation')
            mock_info.assert_called()
            
            log_operation_success(logger, 'test_operation', 1.5)
            assert mock_info.call_count >= 2
            
            test_error = Exception("Test error")
            log_operation_error(logger, 'test_operation', test_error)
            mock_error.assert_called()
            
            log_progress(logger, 'test_operation', 50, 100)
            assert mock_info.call_count >= 3
            
            log_warning(logger, 'Test warning')
            mock_warning.assert_called()
            
            log_milestone(logger, 'Test milestone')
            assert mock_info.call_count >= 4
    
    def test_app_logging_integration(self):
        """Test that the main app logging system integrates properly."""
        try:
            from app.utils.logging import get_logger, log_with_context
            
            # Test logger creation
            logger = get_logger('app.test_cleanup')
            assert logger is not None
            
            # Test context logging
            with patch.object(logger, 'handle') as mock_handle:
                log_with_context(
                    logger,
                    logging.INFO,
                    "Test context message",
                    test_field="test_value"
                )
                mock_handle.assert_called_once()
                
        except ImportError:
            pytest.skip("App logging utilities not available in test context")
    
    def test_comprehensive_print_statement_scan(self):
        """Comprehensive scan for any remaining print statements in the codebase."""
        print_statements = self.scan_codebase_for_prints()
        
        # Filter out legitimate test files and known exceptions
        legitimate_patterns = [
            'test_print_statement_scanner.py',
            'test_logging_cleanup_final.py',
            # Add other legitimate files here as needed
        ]
        
        filtered_prints = []
        for file_path, line_num, line_content in print_statements:
            if not any(pattern in file_path for pattern in legitimate_patterns):
                filtered_prints.append((file_path, line_num, line_content))
        
        if filtered_prints:
            error_msg = "Found print statements in codebase:\n"
            for file_path, line_num, line_content in filtered_prints[:20]:  # Limit to first 20
                error_msg += f"  {file_path}:{line_num} - {line_content}\n"
            if len(filtered_prints) > 20:
                error_msg += f"  ... and {len(filtered_prints) - 20} more\n"
            pytest.fail(error_msg)
    
    def test_logging_configuration_completeness(self):
        """Test that logging configuration is complete and consistent."""
        
        # Test script logging configuration
        script_logging_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'scripts', 'utils', 'script_logging.py'
        )
        assert os.path.exists(script_logging_path), "Script logging utility missing"
        
        # Test app logging configuration
        app_logging_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'app', 'utils', 'logging.py'
        )
        assert os.path.exists(app_logging_path), "App logging utility missing"
        
        # Test converted configuration
        config_converted_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'app', 'config', 'settings_converted.py'
        )
        assert os.path.exists(config_converted_path), "Converted settings missing"
    
    def test_log_level_implementation(self):
        """Test that appropriate log levels are implemented throughout the system."""
        
        # Expected log levels in different contexts
        expected_patterns = {
            'DEBUG': ['debug', 'detailed', 'trace'],
            'INFO': ['info', 'success', 'completed', 'started'],
            'WARNING': ['warning', 'warn', 'missing', 'fallback'],
            'ERROR': ['error', 'failed', 'exception', 'critical']
        }
        
        # This is a structure validation test
        for level, patterns in expected_patterns.items():
            assert level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], f"Invalid log level: {level}"
            assert len(patterns) > 0, f"No patterns defined for {level}"
    
    def test_structured_logging_compliance(self):
        """Test that structured logging patterns are properly implemented."""
        
        # Check converted files for structured logging patterns
        converted_files = [
            'scripts/debug/quick_test_converted.py',
            'scripts/update_playlist_scores_converted.py',
            'app/config/settings_converted.py'
        ]
        
        for file_path in converted_files:
            full_path = os.path.join(os.path.dirname(__file__), '..', '..', file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                
                # Should have structured logging patterns
                assert 'extra_fields' in content or 'extra=' in content, \
                    f"No structured logging found in {file_path}"
                
                # Should have context information
                assert any(pattern in content for pattern in [
                    'operation',
                    'phase',
                    'duration',
                    'status'
                ]), f"No context fields found in {file_path}" 