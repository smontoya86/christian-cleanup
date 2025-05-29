"""
Comprehensive regression test suite for Task 32.1: Remove Deprecated analysis_service.py Module
Tests to ensure no functionality was broken during the deprecated analysis_service.py removal.
"""

import pytest
import os
import sys
import importlib
import tempfile
import subprocess
import time
import json
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime


class TestTask32_1Regression:
    """Comprehensive regression tests for Task 32.1 changes."""
    
    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure proper Python path setup for testing."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def test_application_starts_successfully(self):
        """Test that the Flask application starts without errors after removing analysis_service.py."""
        try:
            from app import create_app
            
            # Test different configurations
            for config in ['testing', 'development']:
                app = create_app(config)
                assert app is not None, f"Failed to create app with {config} configuration"
                
                with app.app_context():
                    # Verify app context works
                    assert app.config is not None
                    
            print("✅ Flask application starts successfully in all configurations")
            
        except Exception as e:
            pytest.fail(f"Application startup failed: {e}")
    
    def test_database_models_load_correctly(self):
        """Test that all database models load without errors."""
        try:
            from app import create_app
            from app.extensions import db
            from app.models.models import User, Song, AnalysisResult, Playlist
            
            app = create_app('testing')
            
            with app.app_context():
                # Test model creation
                db.create_all()
                
                # Test that models are accessible
                assert User is not None
                assert Song is not None
                assert AnalysisResult is not None
                assert Playlist is not None
                
                # Test basic model operations
                test_user = User(
                    spotify_id='regression_test_user_32_1',
                    display_name='Regression Test User',
                    email='test32_1@regression.com',
                    access_token='test_access_token',
                    refresh_token='test_refresh_token',
                    token_expiry=datetime.utcnow()
                )
                
                db.session.add(test_user)
                db.session.commit()
                
                # Verify user was created
                saved_user = User.query.filter_by(spotify_id='regression_test_user_32_1').first()
                assert saved_user is not None
                
                # Clean up
                db.session.delete(saved_user)
                db.session.commit()
                
            print("✅ Database models load and operate correctly")
            
        except Exception as e:
            pytest.fail(f"Database model test failed: {e}")
    
    def test_unified_analysis_service_functionality(self):
        """Test that the unified analysis service works correctly."""
        try:
            from app.services.unified_analysis_service import UnifiedAnalysisService, execute_comprehensive_analysis_task
            
            # Test service instantiation
            service = UnifiedAnalysisService()
            assert service is not None
            
            # Test that the replacement function exists and has correct signature
            import inspect
            sig = inspect.signature(execute_comprehensive_analysis_task)
            assert 'song_id' in sig.parameters
            
            print("✅ Unified analysis service is accessible and functional")
            
        except ImportError as e:
            pytest.fail(f"Failed to import unified analysis service: {e}")
        except Exception as e:
            pytest.fail(f"Unified analysis service test failed: {e}")
    
    def test_no_deprecated_analysis_service_imports(self):
        """Test that no active files import the removed analysis_service module."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Active directories to check (excluding archive)
        active_dirs = ['app', 'scripts']  # Removed 'tests' since test files may check for deprecated imports
        problematic_files = []
        
        for dir_name in active_dirs:
            dir_path = os.path.join(project_root, dir_name)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    # Skip archive directories
                    if 'archive' in root:
                        continue
                        
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                # Check for imports from deprecated service
                                if 'from app.services.analysis_service import' in content:
                                    relative_path = os.path.relpath(file_path, project_root)
                                    problematic_files.append(relative_path)
                            except (UnicodeDecodeError, PermissionError):
                                # Skip files that can't be read
                                continue
        
        if problematic_files:
            pytest.fail(f"Found active files still importing from deprecated analysis_service: {problematic_files}")
        
        print("✅ No active files reference the deprecated analysis_service module")
    
    def test_script_functionality(self):
        """Test that updated scripts work correctly."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Test that the updated script can be imported
            script_path = os.path.join(project_root, 'scripts', 'test_song_analysis.py')
            if os.path.exists(script_path):
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Verify it uses the new import
                assert 'from app.services.unified_analysis_service import execute_comprehensive_analysis_task' in content
                assert 'from app.services.analysis_service import' not in content
                
                # Test that the script compiles without errors
                compile(content, script_path, 'exec')
                
            print("✅ Updated scripts compile and use correct imports")
            
        except Exception as e:
            pytest.fail(f"Script functionality test failed: {e}")
    
    def test_api_routes_functionality(self):
        """Test that API routes still work correctly."""
        try:
            from app import create_app
            
            app = create_app('testing')
            
            with app.test_client() as client:
                # Test basic routes
                response = client.get('/')
                # Should not get 500 errors due to import issues
                assert response.status_code != 500, "Homepage returns 500 error"
                
                # Test API health endpoint if it exists
                try:
                    response = client.get('/api/health')
                    if response.status_code != 404:  # Route exists
                        assert response.status_code != 500, "API health endpoint returns 500 error"
                except:
                    # Route might not exist, that's okay
                    pass
                
            print("✅ API routes function correctly without import errors")
            
        except Exception as e:
            pytest.fail(f"API routes test failed: {e}")
    
    def test_worker_functionality(self):
        """Test that worker components can still be imported and function."""
        try:
            # Test worker can be imported
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            worker_path = os.path.join(project_root, 'worker.py')
            
            if os.path.exists(worker_path):
                # Test that worker compiles
                with open(worker_path, 'r') as f:
                    worker_content = f.read()
                
                compile(worker_content, worker_path, 'exec')
                
            # Test worker_converted.py if it exists
            worker_converted_path = os.path.join(project_root, 'worker_converted.py')
            if os.path.exists(worker_converted_path):
                with open(worker_converted_path, 'r') as f:
                    worker_converted_content = f.read()
                
                compile(worker_converted_content, worker_converted_path, 'exec')
                
            print("✅ Worker components compile successfully")
            
        except Exception as e:
            pytest.fail(f"Worker functionality test failed: {e}")
    
    def test_service_layer_integrity(self):
        """Test that all service layer components work together."""
        try:
            from app import create_app
            
            app = create_app('testing')
            
            with app.app_context():
                # Test unified analysis service
                from app.services.unified_analysis_service import UnifiedAnalysisService
                service = UnifiedAnalysisService()
                assert service is not None
                
                # Test background analysis service
                from app.services.background_analysis_service import BackgroundAnalysisService
                bg_service = BackgroundAnalysisService()
                assert bg_service is not None
                
                # Test enhanced analysis service
                from app.services.enhanced_analysis_service import analyze_song_background
                assert analyze_song_background is not None
                
                # Test spotify service
                from app.services.spotify_service import SpotifyService
                spotify_service = SpotifyService()
                assert spotify_service is not None
                
            print("✅ All service layer components are accessible and functional")
            
        except Exception as e:
            pytest.fail(f"Service layer integrity test failed: {e}")
    
    def test_analysis_result_field_mappings(self):
        """Test that AnalysisResult model has correct field mappings."""
        try:
            from app.models.models import AnalysisResult
            
            # Verify the AnalysisResult model has the correct field names
            model_fields = [field.name for field in AnalysisResult.__table__.columns]
            
            # These should be the correct field names (without prefixes)
            expected_correct_fields = [
                'concern_level',  # not 'christian_concern_level'
                'purity_flags_details',  # not 'christian_purity_flags_details'
                'positive_themes_identified',  # not 'christian_positive_themes_detected'
                'biblical_themes',
                'supporting_scripture',
                'concerns'
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
            
            print("✅ AnalysisResult model has correct field mappings")
            
        except Exception as e:
            pytest.fail(f"Field mapping test failed: {e}")
    
    def test_comprehensive_import_health(self):
        """Test that all major imports work correctly after the removal."""
        critical_imports = [
            # Core app
            'app',
            'app.extensions',
            'app.models.models',
            
            # Services
            'app.services.unified_analysis_service',
            'app.services.background_analysis_service',
            'app.services.enhanced_analysis_service',
            'app.services.spotify_service',
            
            # Routes
            'app.main.routes',
            'app.api.routes',
            'app.auth.routes',
            
            # Utils
            'app.utils.analysis_adapter',
            'app.utils.lyrics',
            'app.utils.database',
        ]
        
        failed_imports = []
        
        for import_name in critical_imports:
            try:
                importlib.import_module(import_name)
            except ImportError as e:
                failed_imports.append(f"{import_name}: {str(e)}")
        
        if failed_imports:
            pytest.fail(f"Critical imports failed: {failed_imports}")
        
        print("✅ All critical imports work correctly")
    
    def test_deprecated_file_removal(self):
        """Test that the deprecated analysis_service.py file has been properly removed."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        deprecated_file = os.path.join(project_root, 'app', 'services', 'analysis_service.py')
        
        # File should not exist
        assert not os.path.exists(deprecated_file), "Deprecated analysis_service.py should have been removed"
        
        print("✅ Deprecated analysis_service.py file has been successfully removed")
    
    def test_application_performance_baseline(self):
        """Test that application performance hasn't degraded significantly."""
        try:
            from app import create_app
            import time
            
            start_time = time.time()
            app = create_app('testing')
            creation_time = time.time() - start_time
            
            # App creation should be reasonably fast (under 5 seconds)
            assert creation_time < 5.0, f"App creation took too long: {creation_time:.2f}s"
            
            with app.app_context():
                start_time = time.time()
                from app.services.unified_analysis_service import UnifiedAnalysisService
                service = UnifiedAnalysisService()
                service_time = time.time() - start_time
                
                # Service instantiation should be fast
                assert service_time < 1.0, f"Service instantiation took too long: {service_time:.2f}s"
            
            print(f"✅ Application performance is good (app: {creation_time:.2f}s, service: {service_time:.2f}s)")
            
        except Exception as e:
            pytest.fail(f"Performance test failed: {e}") 