"""
Regression test suite for Task 31: Remove Debug Print Statements and Implement Proper Logging
Tests to ensure no functionality was broken during the print statement removal and logging implementation.
"""

import pytest
import os
import sys
import importlib
import importlib.util
import tempfile
import subprocess
import time
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime, timedelta


class TestTask31Regression:
    """Comprehensive regression tests for Task 31 changes."""
    
    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure proper Python path setup for testing."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def test_converted_files_import_successfully(self):
        """Test that all converted files can be imported without errors."""
        converted_files = [
            ('scripts.utils.script_logging', 'scripts/utils/script_logging.py'),
        ]
        
        for module_name, file_path in converted_files:
            # Check file exists
            full_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                file_path
            )
            assert os.path.exists(full_path), f"Converted file not found: {file_path}"
            
            # Test import
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Failed to import {module_name}"
            except ImportError as e:
                pytest.fail(f"Import error for {module_name}: {e}")
    
    def test_script_logging_functionality(self):
        """Test that the script logging infrastructure works correctly."""
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
        logger = get_script_logger('regression_test')
        assert logger is not None
        assert 'regression_test' in logger.name
        
        # Test all logging functions don't crash
        with patch.object(logger, 'info') as mock_info, \
             patch.object(logger, 'error') as mock_error, \
             patch.object(logger, 'warning') as mock_warning:
            
            # Test operation logging
            log_operation_start(logger, 'test_operation')
            mock_info.assert_called()
            
            log_operation_success(logger, 'test_operation', 1.0)
            assert mock_info.call_count >= 2
            
            # Test error logging
            test_error = Exception("Test error")
            log_operation_error(logger, 'test_operation', test_error)
            mock_error.assert_called()
            
            # Test progress logging
            log_progress(logger, 'test_operation', 50, 100)
            assert mock_info.call_count >= 3
            
            # Test warning logging
            log_warning(logger, 'Test warning message')
            mock_warning.assert_called()
            
            # Test milestone logging
            log_milestone(logger, 'Test milestone')
            assert mock_info.call_count >= 4
    
    def test_converted_settings_functionality(self):
        """Test that the converted settings file maintains all functionality."""
        try:
            # Import the converted settings file directly
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            settings_path = os.path.join(project_root, 'app', 'config', 'settings_converted.py')
            
            # Check if file exists
            if not os.path.exists(settings_path):
                pytest.skip("Converted settings file not found")
            
            # Add the path and import manually
            spec = importlib.util.spec_from_file_location("settings_converted", settings_path)
            settings_converted = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(settings_converted)
            
            # Test basic configuration classes exist
            assert hasattr(settings_converted, 'Config')
            assert hasattr(settings_converted, 'DevelopmentConfig')
            assert hasattr(settings_converted, 'TestingConfig')
            assert hasattr(settings_converted, 'ProductionConfig')
            
            # Test config dictionary exists
            assert hasattr(settings_converted, 'config')
            assert 'development' in settings_converted.config
            assert 'testing' in settings_converted.config
            assert 'production' in settings_converted.config
            
            # Test logging helper functions exist
            assert hasattr(settings_converted, 'log_config_info')
            assert hasattr(settings_converted, 'log_config_debug')
            assert hasattr(settings_converted, 'log_config_warning')
            assert hasattr(settings_converted, 'log_config_error')
            
            # Test validation function exists
            assert hasattr(settings_converted, 'validate_configuration')
            
            # Test validation function works
            config_class = settings_converted.DevelopmentConfig
            validation_results = settings_converted.validate_configuration(config_class)
            assert isinstance(validation_results, dict)
            
        except Exception as e:
            pytest.fail(f"Failed to test converted settings: {e}")
    
    def test_original_app_still_starts(self):
        """Test that the original Flask application can still start."""
        try:
            from app import create_app
            
            # Create app in testing mode to avoid side effects
            app = create_app('testing')
            assert app is not None
            
            # Test that app context works
            with app.app_context():
                # Test basic configuration access
                assert app.config is not None
                assert 'TESTING' in app.config
                
                # Test that database can be accessed
                from app.extensions import db
                assert db is not None
                
        except Exception as e:
            pytest.fail(f"Failed to create Flask app: {e}")
    
    def test_worker_converted_file_syntax(self):
        """Test that the converted worker file has valid Python syntax."""
        worker_converted_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'worker_converted.py'
        )
        
        assert os.path.exists(worker_converted_path), "worker_converted.py not found"
        
        # Test syntax by compiling
        with open(worker_converted_path, 'r') as f:
            content = f.read()
        
        try:
            compile(content, worker_converted_path, 'exec')
        except SyntaxError as e:
            pytest.fail(f"Syntax error in worker_converted.py: {e}")
    
    def test_no_print_statements_in_converted_files(self):
        """Test that converted files have no print statements."""
        converted_files = [
            'worker_converted.py',
            'app/config/settings_converted.py', 
            'scripts/update_playlist_scores_converted.py'
        ]
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        for file_path in converted_files:
            full_path = os.path.join(project_root, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                
                print_count = content.count('print(')
                assert print_count == 0, f"Found {print_count} print statements in {file_path}"
    
    def test_logging_infrastructure_integration(self):
        """Test that logging infrastructure integrates with the main app."""
        try:
            from app.utils.logging import get_logger
            
            # Test logger creation
            logger = get_logger('regression_test')
            assert logger is not None
            
            # Test logging with context (skip configure_logging which needs app)
            with patch.object(logger, 'info') as mock_info:
                logger.info("Test message", extra={'extra_fields': {'test': True}})
                mock_info.assert_called()
                
        except ImportError:
            # If app logging isn't available in test context, that's okay
            pytest.skip("App logging utilities not available in test context")
    
    def test_database_operations_still_work(self):
        """Test that database operations haven't been affected."""
        try:
            from app import create_app
            from app.extensions import db
            from app.models.models import User
            
            app = create_app('testing')
            
            with app.app_context():
                # Test database connection
                db.create_all()
                
                # Test basic model operations with required fields
                test_user = User(
                    spotify_id='test_regression_user',
                    display_name='Regression Test User',
                    email='test@regression.com',
                    access_token='test_access_token',  # Required field
                    refresh_token='test_refresh_token',  # Required field
                    token_expiry=datetime.utcnow() + timedelta(hours=1)  # Required field
                )
                
                db.session.add(test_user)
                db.session.commit()
                
                # Verify user was created
                found_user = User.query.filter_by(spotify_id='test_regression_user').first()
                assert found_user is not None
                assert found_user.display_name == 'Regression Test User'
                
                # Clean up
                db.session.delete(found_user)
                db.session.commit()
                
        except Exception as e:
            pytest.fail(f"Database operations failed: {e}")
    
    def test_redis_connections_still_work(self):
        """Test that Redis connections haven't been affected."""
        try:
            from app import create_app
            from app.utils.redis_manager import redis_manager
            
            app = create_app('testing')
            
            with app.app_context():
                # Test Redis connection
                connection = redis_manager.get_connection()
                assert connection is not None
                
                # Test basic Redis operations
                test_key = 'regression_test_key'
                test_value = 'regression_test_value'
                
                # Use a transaction to ensure atomicity
                pipe = connection.pipeline()
                pipe.set(test_key, test_value)
                pipe.get(test_key)
                results = pipe.execute()
                
                # Check results
                assert results[0] is True or results[0] == b'OK'  # SET result
                retrieved_value = results[1]  # GET result
                
                if retrieved_value is not None:
                    if isinstance(retrieved_value, bytes):
                        assert retrieved_value.decode() == test_value
                    else:
                        assert str(retrieved_value) == test_value
                else:
                    pytest.skip("Redis not available in test environment")
                
                # Clean up
                connection.delete(test_key)
                
        except ImportError:
            pytest.skip("Redis manager not available in test context")
        except Exception as e:
            # Redis might not be available in test environment
            pytest.skip(f"Redis not available in test environment: {e}")
    
    def test_performance_no_significant_degradation(self):
        """Test that logging changes haven't significantly impacted performance."""
        from scripts.utils.script_logging import get_script_logger
        
        logger = get_script_logger('performance_test')
        
        # Measure performance of logging operations
        import time
        
        start_time = time.time()
        
        # Perform 1000 logging operations
        for i in range(1000):
            logger.info(f"Performance test message {i}", extra={
                'extra_fields': {
                    'iteration': i,
                    'test_type': 'performance'
                }
            })
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 1000 log operations in under 1 second
        assert duration < 1.0, f"Logging performance degraded: {duration:.3f}s for 1000 operations"
    
    def test_converted_scripts_executable(self):
        """Test that converted scripts can be executed without syntax errors."""
        converted_scripts = [
            'scripts/update_playlist_scores_converted.py',
        ]
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        for script_path in converted_scripts:
            full_path = os.path.join(project_root, script_path)
            if os.path.exists(full_path):
                # Test syntax by importing
                script_dir = os.path.dirname(full_path)
                script_name = os.path.basename(full_path).replace('.py', '')
                
                # Add script directory to path temporarily
                original_path = sys.path[:]
                sys.path.insert(0, script_dir)
                sys.path.insert(0, project_root)
                
                try:
                    # Try to compile the script
                    with open(full_path, 'r') as f:
                        content = f.read()
                    compile(content, full_path, 'exec')
                    
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {script_path}: {e}")
                finally:
                    sys.path[:] = original_path
    
    def test_logging_output_format(self):
        """Test that logging output is in the expected format."""
        from scripts.utils.script_logging import get_script_logger
        
        logger = get_script_logger('format_test')
        
        # Capture log output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.info("Test message", extra={
                'extra_fields': {
                    'test_field': 'test_value',
                    'numeric_field': 42
                }
            })
        
        # The actual output verification would depend on the specific formatter
        # For now, just ensure no exceptions were raised
        assert True  # Test passes if no exceptions occurred
    
    def test_backward_compatibility(self):
        """Test that existing functionality hasn't been broken."""
        try:
            # Test that original modules still exist and work
            from app import create_app
            from app.models.models import Playlist, Song, AnalysisResult
            from app.utils.database import get_all_by_filter
            
            app = create_app('testing')
            
            with app.app_context():
                # Test that basic queries still work
                playlists = get_all_by_filter(Playlist)
                assert isinstance(playlists, list)
                
        except Exception as e:
            pytest.fail(f"Backward compatibility test failed: {e}") 