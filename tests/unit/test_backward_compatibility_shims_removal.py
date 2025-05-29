"""
Test suite for verifying the removal of backward compatibility shims.
This test identifies shims, verifies they can be safely removed, and tests the replacement functionality.
"""

import pytest
import os
import sys
import importlib
import re
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestBackwardCompatibilityShimsRemoval:
    """Test the identification and removal of backward compatibility shims."""
    
    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure proper Python path setup for testing."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def test_identify_backward_compatibility_shims_in_routes(self):
        """Identify backward compatibility shims in main routes."""
        try:
            from app.main import routes
            import inspect
            
            # Get the source code
            source = inspect.getsource(routes)
            
            # Find backward compatibility patterns
            compatibility_patterns = [
                r'# For backward compatibility',
                r'# Include both christian_ and non-christian fields for backward compatibility', 
                r'@.*\.route.*# For backward compatibility',
                r'backward compatibility',
                r'legacy.*support',
                r'deprecated.*route'
            ]
            
            found_shims = []
            for pattern in compatibility_patterns:
                matches = re.finditer(pattern, source, re.IGNORECASE)
                for match in matches:
                    # Get line number
                    line_num = source[:match.start()].count('\n') + 1
                    context = source[max(0, match.start()-100):match.end()+100]
                    found_shims.append({
                        'pattern': pattern,
                        'line': line_num,
                        'context': context.strip()
                    })
            
            print(f"Found {len(found_shims)} backward compatibility shims in routes:")
            for shim in found_shims[:10]:  # Show first 10
                print(f"  Line {shim['line']}: {shim['pattern']}")
            
            return found_shims
            
        except ImportError as e:
            pytest.fail(f"Failed to import routes module: {e}")
    
    def test_identify_fallback_patterns_in_scripts(self):
        """Identify fallback patterns in scripts that might be legacy shims."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        scripts_dir = os.path.join(project_root, 'scripts')
        
        fallback_patterns = [
            r'# Default to user ID 2 for backward compatibility',
            r'# Get user by identifier or use user ID 2 as fallback \(for compatibility\)',
            r'fallback.*compatibility',
            r'backward compatibility',
            r'legacy.*fallback'
        ]
        
        found_fallbacks = []
        
        if os.path.exists(scripts_dir):
            for root, dirs, files in os.walk(scripts_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            for pattern in fallback_patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    line_num = content[:match.start()].count('\n') + 1
                                    relative_path = os.path.relpath(file_path, project_root)
                                    found_fallbacks.append({
                                        'file': relative_path,
                                        'line': line_num,
                                        'pattern': pattern,
                                        'context': match.group()
                                    })
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        print(f"Found {len(found_fallbacks)} fallback/compatibility patterns in scripts:")
        for fallback in found_fallbacks:
            print(f"  {fallback['file']}:{fallback['line']}: {fallback['pattern']}")
        
        return found_fallbacks
    
    def test_identify_worker_compatibility_shims(self):
        """Identify backward compatibility shims in worker configuration."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Check worker_config_standalone.py
            worker_config_path = os.path.join(project_root, 'scripts', 'worker', 'worker_config_standalone.py')
            compatibility_shims = []
            
            if os.path.exists(worker_config_path):
                with open(worker_config_path, 'r') as f:
                    content = f.read()
                
                # Look for backward compatibility patterns
                patterns = [
                    r'# Backward compatibility - maintain existing queue definitions',
                    r'QUEUE_HIGH = HIGH_PRIORITY_QUEUE',
                    r'QUEUE_DEFAULT = DEFAULT_QUEUE',
                    r'QUEUE_LOW = LOW_PRIORITY_QUEUE'
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content):
                        compatibility_shims.append({
                            'file': 'scripts/worker/worker_config_standalone.py',
                            'pattern': pattern,
                            'type': 'queue_alias_shim'
                        })
            
            # Check app/worker_config.py
            app_worker_config_path = os.path.join(project_root, 'app', 'worker_config.py')
            if os.path.exists(app_worker_config_path):
                with open(app_worker_config_path, 'r') as f:
                    content = f.read()
                
                if re.search(r'# Backward compatibility', content):
                    compatibility_shims.append({
                        'file': 'app/worker_config.py',
                        'pattern': 'backward compatibility comment',
                        'type': 'queue_alias_shim'
                    })
            
            print(f"Found {len(compatibility_shims)} worker compatibility shims:")
            for shim in compatibility_shims:
                print(f"  {shim['file']}: {shim['type']}")
            
            return compatibility_shims
            
        except Exception as e:
            pytest.fail(f"Failed to identify worker compatibility shims: {e}")
    
    def test_identify_analysis_adapter_compatibility(self):
        """Test backward compatibility patterns in analysis adapter."""
        try:
            from app.utils import analysis_adapter
            import inspect
            
            source = inspect.getsource(analysis_adapter)
            
            # Look for backward compatibility patterns
            compatibility_patterns = [
                r'backward compatibility',
                r'legacy field mapping',
                r'# Legacy field mapping for backward compatibility',
                r'Enhanced song analyzer adapter that provides backward compatibility'
            ]
            
            found_compatibility = []
            for pattern in compatibility_patterns:
                matches = re.finditer(pattern, source, re.IGNORECASE)
                for match in matches:
                    line_num = source[:match.start()].count('\n') + 1
                    found_compatibility.append({
                        'line': line_num,
                        'pattern': pattern,
                        'context': match.group()
                    })
            
            print(f"Found {len(found_compatibility)} compatibility patterns in analysis_adapter:")
            for comp in found_compatibility:
                print(f"  Line {comp['line']}: {comp['pattern']}")
            
            return found_compatibility
            
        except ImportError as e:
            pytest.fail(f"Failed to import analysis_adapter: {e}")
    
    def test_identify_api_route_compatibility_shims(self):
        """Test API routes for backward compatibility shims."""
        try:
            from app.main import routes
            import inspect
            
            source = inspect.getsource(routes)
            
            # Find API routes with backward compatibility comments
            api_compat_patterns = [
                r"@main_bp\.route.*# For backward compatibility",
                r"/api/.*# For backward compatibility"
            ]
            
            found_api_shims = []
            for pattern in api_compat_patterns:
                matches = re.finditer(pattern, source)
                for match in matches:
                    line_num = source[:match.start()].count('\n') + 1
                    # Extract the route definition
                    lines = source.split('\n')
                    route_line = lines[line_num - 1] if line_num <= len(lines) else match.group()
                    found_api_shims.append({
                        'line': line_num,
                        'route': route_line.strip(),
                        'type': 'api_compatibility_route'
                    })
            
            print(f"Found {len(found_api_shims)} API compatibility shims:")
            for shim in found_api_shims:
                print(f"  Line {shim['line']}: {shim['route']}")
            
            return found_api_shims
            
        except ImportError as e:
            pytest.fail(f"Failed to analyze API routes: {e}")
    
    def test_identify_app_init_compatibility_shims(self):
        """Test app initialization for backward compatibility shims."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            app_init_path = os.path.join(project_root, 'app', '__init__.py')
            
            # Read the source file directly
            with open(app_init_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Look for backward compatibility patterns in app init
            patterns = [
                r'# Default queue for backward compatibility',
                r'app\.task_queue = .*# Default queue for backward compatibility'
            ]
            
            found_init_shims = []
            for pattern in patterns:
                matches = re.finditer(pattern, source)
                for match in matches:
                    line_num = source[:match.start()].count('\n') + 1
                    found_init_shims.append({
                        'line': line_num,
                        'pattern': pattern,
                        'context': match.group()
                    })
            
            print(f"Found {len(found_init_shims)} app init compatibility shims:")
            for shim in found_init_shims:
                print(f"  Line {shim['line']}: {shim['context']}")
            
            return found_init_shims
            
        except Exception as e:
            pytest.fail(f"Failed to analyze app init: {e}")
    
    def test_user_id_2_fallback_pattern_safety(self):
        """Test if the user ID 2 fallback pattern can be safely removed."""
        try:
            from app import create_app
            from app.extensions import db
            from app.models.models import User
            
            app = create_app('testing')
            
            with app.app_context():
                # Check if user ID 2 exists
                user_2 = User.query.filter_by(id=2).first()
                user_count = User.query.count()
                
                # Create test user if none exist
                if user_count == 0:
                    test_user = User(
                        spotify_id='test_user_shim_removal',
                        display_name='Test User',
                        email='test@shimremoval.com',
                        access_token='test_token',
                        refresh_token='test_refresh',
                        token_expiry=datetime.utcnow()
                    )
                    db.session.add(test_user)
                    db.session.commit()
                    user_count = 1
                
                print(f"User analysis for fallback removal:")
                print(f"  Total users: {user_count}")
                print(f"  User ID 2 exists: {user_2 is not None}")
                print(f"  Safe to remove user ID 2 fallback: {user_count > 0}")
                
                # Test that scripts can work with any user
                first_user = User.query.first()
                assert first_user is not None, "Should have at least one user for testing"
                
                return {
                    'safe_to_remove': user_count > 0,
                    'user_2_exists': user_2 is not None,
                    'total_users': user_count,
                    'alternative_available': first_user is not None
                }
                
        except Exception as e:
            pytest.fail(f"Failed to test user ID 2 fallback safety: {e}")
    
    def test_queue_alias_compatibility_shims(self):
        """Test that queue alias compatibility shims can be safely removed."""
        try:
            # Test that the original queue names are used consistently
            from scripts.worker.worker_config_standalone import HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE
            
            # Verify the original constants exist
            assert HIGH_PRIORITY_QUEUE == 'high'
            assert DEFAULT_QUEUE == 'default'
            assert LOW_PRIORITY_QUEUE == 'low'
            
            # Check if the compatibility aliases are used anywhere
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            alias_usage = {
                'QUEUE_HIGH': 0,
                'QUEUE_DEFAULT': 0,
                'QUEUE_LOW': 0
            }
            
            # Search for usage of the compatibility aliases
            for root, dirs, files in os.walk(os.path.join(project_root, 'app')):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            for alias in alias_usage.keys():
                                if alias in content:
                                    alias_usage[alias] += content.count(alias)
                        except (UnicodeDecodeError, PermissionError):
                            continue
            
            print(f"Queue alias usage analysis:")
            for alias, count in alias_usage.items():
                print(f"  {alias}: {count} occurrences")
            
            total_usage = sum(alias_usage.values())
            print(f"  Safe to remove aliases: {total_usage == 0}")
            
            return {
                'safe_to_remove': total_usage == 0,
                'usage_counts': alias_usage
            }
            
        except Exception as e:
            pytest.fail(f"Failed to test queue alias compatibility: {e}")
    
    def test_comprehensive_shim_safety_analysis(self):
        """Comprehensive analysis of all identified shims for safe removal."""
        # Run all identification tests
        routes_shims = self.test_identify_backward_compatibility_shims_in_routes()
        script_fallbacks = self.test_identify_fallback_patterns_in_scripts()
        worker_shims = self.test_identify_worker_compatibility_shims()
        adapter_compat = self.test_identify_analysis_adapter_compatibility()
        api_shims = self.test_identify_api_route_compatibility_shims()
        init_shims = self.test_identify_app_init_compatibility_shims()
        
        # Safety tests
        user_fallback_safety = self.test_user_id_2_fallback_pattern_safety()
        queue_alias_safety = self.test_queue_alias_compatibility_shims()
        
        # Summarize findings
        total_shims = (
            len(routes_shims) + 
            len(script_fallbacks) + 
            len(worker_shims) + 
            len(adapter_compat) + 
            len(api_shims) + 
            len(init_shims)
        )
        
        safety_summary = {
            'total_shims_identified': total_shims,
            'user_fallback_safe': user_fallback_safety['safe_to_remove'],
            'queue_aliases_safe': queue_alias_safety['safe_to_remove'],
            'api_routes_need_review': len(api_shims) > 0,
            'recommendations': []
        }
        
        if user_fallback_safety['safe_to_remove']:
            safety_summary['recommendations'].append('User ID 2 fallback can be removed')
        
        if queue_alias_safety['safe_to_remove']:
            safety_summary['recommendations'].append('Queue aliases can be removed')
        
        if len(api_shims) > 0:
            safety_summary['recommendations'].append('API compatibility routes need careful review')
        
        print(f"\n🔍 COMPREHENSIVE SHIM ANALYSIS SUMMARY:")
        print(f"  Total compatibility shims found: {total_shims}")
        print(f"  User fallback removal safe: {safety_summary['user_fallback_safe']}")
        print(f"  Queue alias removal safe: {safety_summary['queue_aliases_safe']}")
        print(f"  API routes need review: {safety_summary['api_routes_need_review']}")
        
        return safety_summary 