#!/usr/bin/env python3
"""
Code Complexity Analysis Script for Analysis Utilities

Analyzes the structure and complexity of analysis.py and analysis_enhanced.py
to identify refactoring opportunities.
"""

import ast
import os
import re
from typing import List, Dict, Any

class CodeAnalyzer:
    def __init__(self):
        self.results = {}
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file for complexity metrics"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Basic metrics
            total_lines = len(content.splitlines())
            
            # Parse AST
            tree = ast.parse(content)
            
            # Find classes and methods
            classes = []
            methods = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': getattr(node, 'end_lineno', node.lineno),
                        'methods': []
                    }
                    
                    # Find methods in this class
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_info = {
                                'name': child.name,
                                'line_start': child.lineno,
                                'line_end': getattr(child, 'end_lineno', child.lineno),
                                'length': getattr(child, 'end_lineno', child.lineno) - child.lineno + 1
                            }
                            class_info['methods'].append(method_info)
                            methods.append(method_info)
                    
                    classes.append(class_info)
                elif isinstance(node, ast.FunctionDef) and not any(node.lineno >= cls['line_start'] and node.lineno <= cls['line_end'] for cls in classes):
                    # Top-level function
                    method_info = {
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': getattr(node, 'end_lineno', node.lineno),
                        'length': getattr(node, 'end_lineno', node.lineno) - node.lineno + 1
                    }
                    methods.append(method_info)
            
            # Find duplicated patterns
            duplicated_patterns = self._find_duplicated_patterns(content)
            
            # Identify complex methods (>25 lines)
            complex_methods = [m for m in methods if m['length'] > 25]
            
            return {
                'file_path': file_path,
                'total_lines': total_lines,
                'classes': classes,
                'methods': methods,
                'complex_methods': complex_methods,
                'duplicated_patterns': duplicated_patterns
            }
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {'error': str(e)}
    
    def _find_duplicated_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Find potential duplicated code patterns"""
        patterns = []
        
        # Look for regex patterns that appear multiple times
        regex_matches = re.findall(r'r[\'"]([^\'\"]+)[\'"]', content)
        regex_counts = {}
        for regex in regex_matches:
            if len(regex) > 10:  # Only consider substantial patterns
                regex_counts[regex] = regex_counts.get(regex, 0) + 1
        
        duplicated_regex = {k: v for k, v in regex_counts.items() if v > 1}
        if duplicated_regex:
            patterns.append({
                'type': 'regex_patterns',
                'duplicates': duplicated_regex
            })
        
        # Look for repeated function calls
        function_calls = re.findall(r'(\w+)\s*\([^)]*\)', content)
        call_counts = {}
        for call in function_calls:
            if call not in ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set']:
                call_counts[call] = call_counts.get(call, 0) + 1
        
        frequent_calls = {k: v for k, v in call_counts.items() if v > 5}
        if frequent_calls:
            patterns.append({
                'type': 'frequent_function_calls',
                'calls': frequent_calls
            })
        
        return patterns
    
    def generate_report(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive analysis report"""
        report = []
        report.append("# Code Complexity Analysis Report")
        report.append("=" * 50)
        
        total_lines = sum(r.get('total_lines', 0) for r in analysis_results)
        total_classes = sum(len(r.get('classes', [])) for r in analysis_results)
        total_methods = sum(len(r.get('methods', [])) for r in analysis_results)
        total_complex = sum(len(r.get('complex_methods', [])) for r in analysis_results)
        
        report.append(f"\n## Summary")
        report.append(f"- Total Lines: {total_lines}")
        report.append(f"- Total Classes: {total_classes}")
        report.append(f"- Total Methods: {total_methods}")
        report.append(f"- Complex Methods (>25 lines): {total_complex}")
        
        for result in analysis_results:
            if 'error' in result:
                continue
                
            file_path = result['file_path']
            report.append(f"\n## {file_path}")
            report.append(f"- Lines: {result['total_lines']}")
            report.append(f"- Classes: {len(result['classes'])}")
            report.append(f"- Methods: {len(result['methods'])}")
            report.append(f"- Complex Methods: {len(result['complex_methods'])}")
            
            # Show complex methods
            if result['complex_methods']:
                report.append(f"\n### Complex Methods (>25 lines):")
                for method in sorted(result['complex_methods'], key=lambda x: x['length'], reverse=True):
                    report.append(f"- {method['name']}: {method['length']} lines (line {method['line_start']})")
            
            # Show classes
            if result['classes']:
                report.append(f"\n### Classes:")
                for cls in result['classes']:
                    method_count = len(cls['methods'])
                    lines = cls['line_end'] - cls['line_start'] + 1
                    report.append(f"- {cls['name']}: {method_count} methods, {lines} lines")
        
        return "\n".join(report)

def main():
    analyzer = CodeAnalyzer()
    
    files_to_analyze = [
        'app/utils/analysis.py',
        'app/utils/analysis_enhanced.py'
    ]
    
    results = []
    for file_path in files_to_analyze:
        if os.path.exists(file_path):
            print(f"Analyzing {file_path}...")
            result = analyzer.analyze_file(file_path)
            results.append(result)
        else:
            print(f"File not found: {file_path}")
    
    # Generate and print report
    report = analyzer.generate_report(results)
    print("\n" + report)
    
    # Save report to file
    with open('scripts/code_complexity_analysis_report.md', 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: scripts/code_complexity_analysis_report.md")

if __name__ == '__main__':
    main() 