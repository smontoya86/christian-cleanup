"""
Tests for the performance regression detector.
"""
import pytest
import json
import os
import tempfile
import shutil
import time
from datetime import datetime
from tests.utils.regression_detector import RegressionDetector


class TestRegressionDetector:
    """Test the RegressionDetector class."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory for test results."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def detector(self, temp_results_dir):
        """Create a regression detector instance."""
        return RegressionDetector(temp_results_dir, threshold=0.1)
    
    def create_test_result(self, name, execution_time, memory_usage, timestamp=None):
        """Helper method to create test benchmark results."""
        if timestamp is None:
            timestamp = time.time()
        
        return {
            'name': name,
            'iterations': 5,
            'execution_time': {
                'mean': execution_time,
                'median': execution_time,
                'min': execution_time * 0.9,
                'max': execution_time * 1.1,
                'stdev': execution_time * 0.05,
                'raw_values': [execution_time] * 5
            },
            'memory_usage': {
                'mean': memory_usage,
                'median': memory_usage,
                'min': memory_usage * 0.9,
                'max': memory_usage * 1.1,
                'stdev': memory_usage * 0.05,
                'raw_values': [memory_usage] * 5
            },
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).isoformat()
        }
    
    def save_test_result(self, temp_dir, result, suffix=""):
        """Helper method to save test results to files."""
        timestamp_str = datetime.fromtimestamp(result['timestamp']).strftime('%Y%m%d_%H%M%S')
        filename = f"{result['name']}_{timestamp_str}{suffix}.json"
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(result, f)
        
        return filepath
    
    def test_detector_initialization(self, detector, temp_results_dir):
        """Test that detector initializes correctly."""
        assert detector.results_dir == temp_results_dir
        assert detector.threshold == 0.1
    
    def test_detect_regressions_no_files(self, detector):
        """Test regression detection with no result files."""
        regressions = detector.detect_regressions()
        assert regressions == []
    
    def test_detect_regressions_insufficient_data(self, detector, temp_results_dir):
        """Test regression detection with insufficient data."""
        # Create only one result file
        result = self.create_test_result('test_benchmark', 1.0, 10.0)
        self.save_test_result(temp_results_dir, result)
        
        regressions = detector.detect_regressions()
        assert regressions == []
    
    def test_detect_execution_time_regression(self, detector, temp_results_dir):
        """Test detection of execution time regression."""
        # Create two results with execution time regression
        base_time = time.time()
        
        result1 = self.create_test_result('test_benchmark', 1.0, 10.0, base_time)
        result2 = self.create_test_result('test_benchmark', 1.2, 10.0, base_time + 60)  # 20% slower
        
        self.save_test_result(temp_results_dir, result1)
        self.save_test_result(temp_results_dir, result2)
        
        regressions = detector.detect_regressions()
        
        assert len(regressions) == 1
        regression = regressions[0]
        assert regression['benchmark'] == 'test_benchmark'
        assert regression['metric'] == 'execution_time'
        assert regression['previous'] == 1.0
        assert regression['current'] == 1.2
        assert abs(regression['change_percent'] - 20.0) < 0.001
        assert regression['severity'] == 'medium'
    
    def test_detect_memory_usage_regression(self, detector, temp_results_dir):
        """Test detection of memory usage regression."""
        # Create two results with memory usage regression
        base_time = time.time()
        
        result1 = self.create_test_result('test_benchmark', 1.0, 10.0, base_time)
        result2 = self.create_test_result('test_benchmark', 1.0, 15.0, base_time + 60)  # 50% more memory
        
        self.save_test_result(temp_results_dir, result1)
        self.save_test_result(temp_results_dir, result2)
        
        regressions = detector.detect_regressions()
        
        assert len(regressions) == 1
        regression = regressions[0]
        assert regression['benchmark'] == 'test_benchmark'
        assert regression['metric'] == 'memory_usage'
        assert regression['previous'] == 10.0
        assert regression['current'] == 15.0
        assert abs(regression['change_percent'] - 50.0) < 0.001
        assert regression['severity'] == 'high'
    
    def test_no_regression_detected(self, detector, temp_results_dir):
        """Test that no regression is detected when performance improves."""
        # Create two results with improved performance
        base_time = time.time()
        
        result1 = self.create_test_result('test_benchmark', 1.0, 10.0, base_time)
        result2 = self.create_test_result('test_benchmark', 0.9, 9.0, base_time + 60)  # Better performance
        
        self.save_test_result(temp_results_dir, result1)
        self.save_test_result(temp_results_dir, result2)
        
        regressions = detector.detect_regressions()
        assert regressions == []
    
    def test_multiple_benchmarks(self, detector, temp_results_dir):
        """Test regression detection across multiple benchmarks."""
        base_time = time.time()
        
        # Benchmark 1: No regression
        result1a = self.create_test_result('benchmark1', 1.0, 10.0, base_time)
        result1b = self.create_test_result('benchmark1', 1.05, 10.0, base_time + 60)  # 5% slower (below threshold)
        
        # Benchmark 2: Has regression
        result2a = self.create_test_result('benchmark2', 2.0, 20.0, base_time)
        result2b = self.create_test_result('benchmark2', 2.5, 20.0, base_time + 60)  # 25% slower
        
        self.save_test_result(temp_results_dir, result1a)
        self.save_test_result(temp_results_dir, result1b)
        self.save_test_result(temp_results_dir, result2a)
        self.save_test_result(temp_results_dir, result2b)
        
        regressions = detector.detect_regressions()
        
        assert len(regressions) == 1
        assert regressions[0]['benchmark'] == 'benchmark2'
    
    def test_analyze_trends_insufficient_data(self, detector, temp_results_dir):
        """Test trend analysis with insufficient data."""
        # Create only 2 results (need 5 for default window)
        base_time = time.time()
        
        result1 = self.create_test_result('test_benchmark', 1.0, 10.0, base_time)
        result2 = self.create_test_result('test_benchmark', 1.1, 10.0, base_time + 60)
        
        self.save_test_result(temp_results_dir, result1)
        self.save_test_result(temp_results_dir, result2)
        
        trends = detector.analyze_trends('test_benchmark')
        
        assert 'error' in trends
        assert trends['available_results'] == 2
    
    def test_analyze_trends_degrading(self, detector, temp_results_dir):
        """Test trend analysis for degrading performance."""
        base_time = time.time()
        
        # Create 5 results with increasing execution times
        for i in range(5):
            execution_time = 1.0 + (i * 0.1)  # Gradually increasing
            result = self.create_test_result('test_benchmark', execution_time, 10.0, base_time + (i * 60))
            self.save_test_result(temp_results_dir, result)
        
        trends = detector.analyze_trends('test_benchmark')
        
        assert trends['benchmark_name'] == 'test_benchmark'
        assert trends['window_size'] == 5
        assert trends['execution_time']['trend'] == 'degrading'
        assert trends['execution_time']['current'] == 1.4
        assert trends['memory_usage']['trend'] == 'stable'
    
    def test_analyze_trends_improving(self, detector, temp_results_dir):
        """Test trend analysis for improving performance."""
        base_time = time.time()
        
        # Create 5 results with decreasing execution times
        for i in range(5):
            execution_time = 2.0 - (i * 0.1)  # Gradually decreasing
            result = self.create_test_result('test_benchmark', execution_time, 10.0, base_time + (i * 60))
            self.save_test_result(temp_results_dir, result)
        
        trends = detector.analyze_trends('test_benchmark', window_size=5)
        
        assert trends['execution_time']['trend'] == 'improving'
        assert trends['execution_time']['current'] == 1.6
    
    def test_analyze_trends_stable(self, detector, temp_results_dir):
        """Test trend analysis for stable performance."""
        base_time = time.time()
        
        # Create 5 results with stable execution times
        for i in range(5):
            execution_time = 1.0  # Constant
            result = self.create_test_result('test_benchmark', execution_time, 10.0, base_time + (i * 60))
            self.save_test_result(temp_results_dir, result)
        
        trends = detector.analyze_trends('test_benchmark')
        
        assert trends['execution_time']['trend'] == 'stable'
        assert trends['execution_time']['variance'] == 0
    
    def test_generate_report(self, detector, temp_results_dir):
        """Test comprehensive report generation."""
        base_time = time.time()
        
        # Create multiple benchmarks with different scenarios
        # Benchmark 1: Has regression
        result1a = self.create_test_result('benchmark1', 1.0, 10.0, base_time)
        result1b = self.create_test_result('benchmark1', 1.3, 10.0, base_time + 60)  # 30% slower
        
        # Benchmark 2: No regression
        result2a = self.create_test_result('benchmark2', 2.0, 20.0, base_time)
        result2b = self.create_test_result('benchmark2', 2.05, 20.0, base_time + 60)  # 2.5% slower
        
        self.save_test_result(temp_results_dir, result1a)
        self.save_test_result(temp_results_dir, result1b)
        self.save_test_result(temp_results_dir, result2a)
        self.save_test_result(temp_results_dir, result2b)
        
        report = detector.generate_report()
        
        # Verify report structure
        assert 'generated_at' in report
        assert 'summary' in report
        assert 'regressions' in report
        assert 'trends' in report
        assert 'most_problematic_benchmarks' in report
        assert 'threshold' in report
        
        # Verify summary
        summary = report['summary']
        assert summary['total_benchmarks'] == 2
        assert summary['benchmarks_with_regressions'] == 1
        assert summary['total_regressions'] == 1
        assert summary['regression_rate'] == 0.5
        
        # Verify regressions
        assert len(report['regressions']) == 1
        assert report['regressions'][0]['benchmark'] == 'benchmark1'
        
        # Verify most problematic benchmarks
        assert len(report['most_problematic_benchmarks']) == 1
        assert report['most_problematic_benchmarks'][0][0] == 'benchmark1'
        assert report['most_problematic_benchmarks'][0][1] == 1
    
    def test_severity_determination(self, detector):
        """Test severity level determination."""
        # Test different severity levels
        assert detector._determine_severity(0.05) == 'low'      # 5%
        assert detector._determine_severity(0.15) == 'medium'   # 15%
        assert detector._determine_severity(0.35) == 'high'     # 35%
        assert detector._determine_severity(0.75) == 'critical' # 75%
    
    def test_division_by_zero_handling(self, detector, temp_results_dir):
        """Test handling of division by zero in regression detection."""
        base_time = time.time()
        
        # Create results where previous value is 0
        result1 = self.create_test_result('test_benchmark', 0.0, 0.0, base_time)
        result2 = self.create_test_result('test_benchmark', 1.0, 5.0, base_time + 60)
        
        self.save_test_result(temp_results_dir, result1)
        self.save_test_result(temp_results_dir, result2)
        
        regressions = detector.detect_regressions()
        
        # Should detect critical regressions for both metrics
        assert len(regressions) == 2
        
        for regression in regressions:
            assert regression['previous'] == 0.0
            assert regression['change_percent'] == 100.0
            assert regression['severity'] == 'critical'
    
    def test_ignore_latest_files(self, detector, temp_results_dir):
        """Test that _latest.json files are ignored during analysis."""
        base_time = time.time()
        
        # Create regular result file
        result1 = self.create_test_result('test_benchmark', 1.0, 10.0, base_time)
        self.save_test_result(temp_results_dir, result1)
        
        # Create latest file (should be ignored)
        result2 = self.create_test_result('test_benchmark', 2.0, 20.0, base_time + 60)
        latest_file = os.path.join(temp_results_dir, 'test_benchmark_latest.json')
        with open(latest_file, 'w') as f:
            json.dump(result2, f)
        
        regressions = detector.detect_regressions()
        
        # Should not detect any regressions since latest file is ignored
        assert regressions == []
    
    def test_malformed_json_handling(self, detector, temp_results_dir):
        """Test handling of malformed JSON files."""
        # Create a malformed JSON file
        malformed_file = os.path.join(temp_results_dir, 'malformed_20230101_120000.json')
        with open(malformed_file, 'w') as f:
            f.write('{ invalid json }')
        
        # Create a valid result file
        result = self.create_test_result('test_benchmark', 1.0, 10.0)
        self.save_test_result(temp_results_dir, result)
        
        # Should not crash and should process valid files
        regressions = detector.detect_regressions()
        assert regressions == []  # No regressions since only one valid file 