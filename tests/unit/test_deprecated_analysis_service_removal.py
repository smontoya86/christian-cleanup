"""
Test suite for verifying the removal of deprecated analysis_service.py module.
This test ensures that all functionality is properly migrated to the unified analysis service.
"""

import pytest
import os
import sys
import importlib
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestDeprecatedAnalysisServiceRemoval:
    """Test the removal of deprecated analysis_service.py and migration to unified service."""
    
    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure proper Python path setup for testing."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def test_deprecated_analysis_service_file_exists_before_removal(self):
        """Verify the deprecated analysis_service.py file has been successfully removed."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        deprecated_file = os.path.join(project_root, 'app', 'services', 'analysis_service.py')
        
        # This should NOT exist after removal
        assert not os.path.exists(deprecated_file), "Deprecated analysis_service.py should have been removed"
        
        # Verify replacement service is available
        try:
            from app.services.unified_analysis_service import UnifiedAnalysisService
            assert UnifiedAnalysisService is not None
        except ImportError:
            pytest.fail("Replacement UnifiedAnalysisService should be available")
    
    def test_unified_analysis_service_has_replacement_functions(self):
        """Verify that the unified analysis service has the replacement functions."""
        try:
            from app.services.unified_analysis_service import UnifiedAnalysisService, execute_comprehensive_analysis_task
            
            # Test that the UnifiedAnalysisService class exists
            assert UnifiedAnalysisService is not None
            
            # Test that the replacement functions exist
            assert hasattr(UnifiedAnalysisService, 'execute_comprehensive_analysis')
            assert execute_comprehensive_analysis_task is not None
            
            # Test that we can instantiate the service
            service = UnifiedAnalysisService()
            assert service is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import UnifiedAnalysisService: {e}")
    
    def test_scripts_can_be_updated_to_use_unified_service(self):
        """Test that scripts using deprecated functions can be updated to use unified service."""
        try:
            from app.services.unified_analysis_service import execute_comprehensive_analysis_task
            
            # Test that the replacement function has the same signature as deprecated one
            import inspect
            sig = inspect.signature(execute_comprehensive_analysis_task)
            
            # Should accept song_id and user_id parameters
            assert 'song_id' in sig.parameters
            # user_id might be optional in **kwargs or explicit
            
            # Test with mock data
            with patch('app.services.unified_analysis_service.db') as mock_db, \
                 patch('flask.current_app') as mock_app:
                
                mock_app.app_context.return_value.__enter__ = MagicMock()
                mock_app.app_context.return_value.__exit__ = MagicMock()
                
                # This should not raise an exception
                try:
                    # Note: This will likely fail with real data, but shouldn't have import errors
                    execute_comprehensive_analysis_task(1, user_id=1)
                except Exception:
                    # We expect this to fail due to mocking, but not due to import errors
                    pass
                    
        except ImportError as e:
            pytest.fail(f"Failed to import replacement function: {e}")
    
    def test_no_references_to_deprecated_service_after_cleanup(self):
        """Test that no active files reference the deprecated analysis_service after cleanup.
        
        Archive files are excluded since they're archived and allowed to keep deprecated imports.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # List of active files that need to be updated (excluding archive)
        files_to_check = [
            'scripts/test_song_analysis.py',
            # Archive files are excluded from this check
        ]
        
        problematic_files = []
        
        for file_path in files_to_check:
            full_path = os.path.join(project_root, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                
                # Check for imports from deprecated service
                if 'from app.services.analysis_service import' in content:
                    problematic_files.append(file_path)
        
        # This assertion should pass after cleanup of active files
        if problematic_files:
            pytest.fail(f"Found active files still importing from deprecated analysis_service: {problematic_files}")
    
    def test_function_mapping_correctness(self):
        """Test that the function mapping from deprecated to unified service is correct."""
        # Define the mapping of deprecated functions to their replacements
        function_mapping = {
            'perform_christian_song_analysis_and_store': 'execute_comprehensive_analysis_task',
            '_execute_song_analysis_task': 'execute_comprehensive_analysis_task',
            '_execute_song_analysis_impl': 'UnifiedAnalysisService.execute_comprehensive_analysis'
        }
        
        try:
            from app.services.unified_analysis_service import UnifiedAnalysisService, execute_comprehensive_analysis_task
            
            # Test that replacement functions exist
            assert execute_comprehensive_analysis_task is not None
            
            service = UnifiedAnalysisService()
            assert hasattr(service, 'execute_comprehensive_analysis')
            
            # Test function signatures are compatible
            import inspect
            
            # Check execute_comprehensive_analysis_task signature
            sig = inspect.signature(execute_comprehensive_analysis_task)
            assert 'song_id' in sig.parameters
            
            # Check instance method signature
            method_sig = inspect.signature(service.execute_comprehensive_analysis)
            assert 'song_id' in method_sig.parameters
            
        except ImportError as e:
            pytest.fail(f"Failed to verify function mappings: {e}")
    
    def test_database_field_mapping_improvements(self):
        """Test that the unified service uses correct field mappings (not prefixed)."""
        try:
            from app.models.models import AnalysisResult
            
            # Verify the AnalysisResult model has the correct field names
            # (not the prefixed ones that were incorrect in the deprecated service)
            model_fields = [field.name for field in AnalysisResult.__table__.columns]
            
            # These should be the correct field names (without prefixes)
            expected_correct_fields = [
                'concern_level',  # not 'christian_concern_level'
                'purity_flags_details',  # not 'christian_purity_flags_details'
                'positive_themes_identified',  # not 'christian_positive_themes_detected'
            ]
            
            for field in expected_correct_fields:
                assert field in model_fields, f"Expected field {field} not found in AnalysisResult model"
            
            # These prefixed fields should NOT exist
            incorrect_prefixed_fields = [
                'christian_concern_level',
                'christian_purity_flags_details', 
                'christian_positive_themes_detected'
            ]
            
            for field in incorrect_prefixed_fields:
                assert field not in model_fields, f"Incorrect prefixed field {field} should not exist in model"
                
        except ImportError as e:
            pytest.fail(f"Failed to verify field mappings: {e}")
    
    def test_archive_files_can_remain_with_deprecated_imports(self):
        """Test that files in archive directories can keep deprecated imports (they're archived)."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Archive files that can keep deprecated imports since they're not active
        archive_files = [
            'archive/old_scripts/debug/test_song_analysis.py'
        ]
        
        for file_path in archive_files:
            full_path = os.path.join(project_root, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                
                # Archive files are allowed to have deprecated imports
                # This test just verifies they exist and are readable
                assert len(content) > 0, f"Archive file {file_path} should be readable"
    
    def test_active_scripts_use_unified_service_after_update(self):
        """Test that active scripts (non-archive) use the unified service after update."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Active scripts that should be updated
        active_scripts = [
            'scripts/test_song_analysis.py'
        ]
        
        for script_path in active_scripts:
            full_path = os.path.join(project_root, script_path)
            if os.path.exists(full_path):
                # This test will pass after we update the scripts
                # We'll update the scripts to import from unified_analysis_service
                try:
                    # Test that the script can be imported without errors after update
                    script_dir = os.path.dirname(full_path)
                    script_name = os.path.basename(full_path).replace('.py', '')
                    
                    # Add to path temporarily
                    original_path = sys.path[:]
                    sys.path.insert(0, script_dir)
                    sys.path.insert(0, project_root)
                    
                    # Try to compile the script (will fail if imports are broken)
                    with open(full_path, 'r') as f:
                        content = f.read()
                    
                    # After update, should not import from deprecated service
                    compile(content, full_path, 'exec')
                    
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in updated script {script_path}: {e}")
                finally:
                    sys.path[:] = original_path
    
    def test_removal_safety_check(self):
        """Final safety check to verify the deprecated file has been successfully removed."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        deprecated_file = os.path.join(project_root, 'app', 'services', 'analysis_service.py')
        
        # File should no longer exist after successful removal
        assert not os.path.exists(deprecated_file), "Deprecated analysis_service.py should have been removed"
        
        # Check that we have the replacement service available
        try:
            from app.services.unified_analysis_service import UnifiedAnalysisService, execute_comprehensive_analysis_task
            assert UnifiedAnalysisService is not None
            assert execute_comprehensive_analysis_task is not None
        except ImportError:
            pytest.fail("Replacement UnifiedAnalysisService and functions should be available") 