import pytest
import os
import re
import glob
from typing import List, Tuple


class TestPrintStatements:
    """Test to ensure no print statements remain in the codebase."""
    
    def scan_for_print_statements(self, directory: str) -> List[Tuple[str, int, str]]:
        """
        Scan a directory for print statements in Python files.
        
        Returns:
            List of tuples containing (file_path, line_number, line_content)
        """
        print_statements = []
        
        # Get all Python files in the directory
        pattern = os.path.join(directory, "**", "*.py")
        python_files = glob.glob(pattern, recursive=True)
        
        for file_path in python_files:
            # Skip virtual environment directories and migrations
            if any(excluded in file_path for excluded in ['/venv/', '/.venv/', '/migrations/', '__pycache__']):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    # Look for print statements (but not in comments or strings)
                    stripped_line = line.strip()
                    
                    # Skip empty lines and full-line comments
                    if not stripped_line or stripped_line.startswith('#'):
                        continue
                    
                    # Look for print( pattern
                    if re.search(r'\bprint\s*\(', line):
                        # Check if it's in a string literal (simple heuristic)
                        # This won't catch all cases but will catch most
                        quote_count = line.count('"') + line.count("'")
                        if quote_count % 2 == 0:  # Even number of quotes, likely not in string
                            print_statements.append((file_path, line_num, stripped_line))
                            
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue
                
        return print_statements
    
    def test_no_print_statements_in_app_directory(self):
        """Test that no print statements exist in the app directory."""
        app_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'app')
        app_dir = os.path.abspath(app_dir)
        
        print_statements = self.scan_for_print_statements(app_dir)
        
        if print_statements:
            error_msg = "Found print statements in app directory:\n"
            for file_path, line_num, line_content in print_statements:
                error_msg += f"  {file_path}:{line_num} - {line_content}\n"
            pytest.fail(error_msg)
    
    def test_no_print_statements_in_config_directory(self):
        """Test that no print statements exist in the config directory."""
        config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
        config_dir = os.path.abspath(config_dir)
        
        if os.path.exists(config_dir):
            print_statements = self.scan_for_print_statements(config_dir)
            
            if print_statements:
                error_msg = "Found print statements in config directory:\n"
                for file_path, line_num, line_content in print_statements:
                    error_msg += f"  {file_path}:{line_num} - {line_content}\n"
                pytest.fail(error_msg)
    
    def test_no_print_statements_in_scripts_directory(self):
        """Test that no print statements exist in the scripts directory."""
        scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
        scripts_dir = os.path.abspath(scripts_dir)
        
        if os.path.exists(scripts_dir):
            print_statements = self.scan_for_print_statements(scripts_dir)
            
            if print_statements:
                error_msg = "Found print statements in scripts directory:\n"
                for file_path, line_num, line_content in print_statements:
                    error_msg += f"  {file_path}:{line_num} - {line_content}\n"
                pytest.fail(error_msg)
    
    def test_scan_functionality(self):
        """Test that the scanner can find print statements."""
        # Create a temporary test file with print statements
        test_content = '''
def test_function():
    print("This is a test")
    x = 5
    print(f"Value is {x}")
'''
        
        # Write to a temporary file in tests directory
        test_file = os.path.join(os.path.dirname(__file__), 'temp_test_file.py')
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        try:
            # Scan just the tests directory
            test_dir = os.path.dirname(__file__)
            print_statements = self.scan_for_print_statements(test_dir)
            
            # Filter for our test file
            test_file_prints = [p for p in print_statements if 'temp_test_file.py' in p[0]]
            
            # Should find 2 print statements
            assert len(test_file_prints) == 2
            assert any('This is a test' in p[2] for p in test_file_prints)
            assert any('Value is' in p[2] for p in test_file_prints)
            
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file) 