import pytest
import os
import re


class TestConvertedScripts:
    """Test that converted scripts use proper logging instead of print statements."""
    
    def test_quick_test_converted_no_prints(self):
        """Test that the converted quick_test script has no print statements."""
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'scripts', 
            'debug', 
            'quick_test_converted.py'
        )
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Split into lines for analysis
        lines = content.split('\n')
        print_statements = []
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                continue
            
            # Look for print statements
            if re.search(r'\bprint\s*\(', line):
                # Check if it's in a string literal (simple check)
                quote_count = line.count('"') + line.count("'")
                if quote_count % 2 == 0:  # Not in a string
                    print_statements.append((line_num, stripped_line))
        
        assert len(print_statements) == 0, f"Found print statements: {print_statements}"
    
    def test_quick_test_converted_uses_logging(self):
        """Test that the converted script imports and uses the logging utilities."""
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'scripts', 
            'debug', 
            'quick_test_converted.py'
        )
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Should import logging utilities
        assert 'from scripts.utils.script_logging import' in content
        assert 'get_script_logger' in content
        assert 'log_operation_start' in content
        
        # Should use logger methods
        assert 'logger.info(' in content
        assert 'logger.warning(' in content or 'log_operation_success(' in content
        
        # Should have structured logging with extra fields
        assert 'extra_fields' in content
    
    def test_original_vs_converted_functionality(self):
        """Test that converted script has equivalent functionality to original."""
        original_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'scripts', 
            'debug', 
            'quick_test.py'
        )
        
        converted_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'scripts', 
            'debug', 
            'quick_test_converted.py'
        )
        
        # Both files should exist
        assert os.path.exists(original_path)
        assert os.path.exists(converted_path)
        
        # Read both files
        with open(original_path, 'r') as f:
            original_content = f.read()
        
        with open(converted_path, 'r') as f:
            converted_content = f.read()
        
        # Converted should be longer (more detailed logging)
        assert len(converted_content) > len(original_content)
        
        # Both should have the same core functionality
        core_functions = [
            'User.query.count()',
            'Song.query.count()',
            'AnalysisResult.query.count()',
            'UnifiedAnalysisService()',
            'User.query.first()'
        ]
        
        for func in core_functions:
            assert func in original_content
            assert func in converted_content
    
    def test_logging_pattern_compliance(self):
        """Test that the converted script follows the logging patterns."""
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'scripts', 
            'debug', 
            'quick_test_converted.py'
        )
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Should follow the recommended pattern
        assert "logger = get_script_logger(" in content
        assert "log_operation_start(logger," in content
        assert "log_operation_success(" in content
        assert "log_milestone(logger," in content
        
        # Should have proper error handling
        assert "log_operation_error(" in content
        assert "except Exception as e:" in content 