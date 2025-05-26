"""
Tests for the performance benchmarking framework.
"""
import pytest
import time
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from tests.utils.benchmark import PerformanceBenchmark, BenchmarkSuite, benchmark_function, compare_benchmarks


class TestPerformanceBenchmark:
    """Test the PerformanceBenchmark class."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory for test results."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def benchmark(self, temp_results_dir):
        """Create a benchmark instance with temporary results directory."""
        benchmark = PerformanceBenchmark('test_benchmark', iterations=3)
        benchmark.results_dir = temp_results_dir
        return benchmark
    
    def test_benchmark_initialization(self, benchmark):
        """Test that benchmark initializes correctly."""
        assert benchmark.name == 'test_benchmark'
        assert benchmark.iterations == 3
        assert os.path.exists(benchmark.results_dir)
    
    def test_benchmark_measure_decorator(self, benchmark):
        """Test that the measure decorator works correctly."""
        @benchmark.measure
        def test_function():
            time.sleep(0.01)  # Small delay to measure
            return 'test_result'
        
        result = test_function()
        
        # Verify function result is preserved
        assert result == 'test_result'
        
        # Verify results file was created
        latest_file = os.path.join(benchmark.results_dir, 'test_benchmark_latest.json')
        assert os.path.exists(latest_file)
        
        # Verify results content
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        assert results['name'] == 'test_benchmark'
        assert results['iterations'] == 3
        assert 'execution_time' in results
        assert 'memory_usage' in results
        assert 'timestamp' in results
        assert 'datetime' in results
        
        # Verify execution time statistics
        exec_time = results['execution_time']
        assert 'mean' in exec_time
        assert 'median' in exec_time
        assert 'min' in exec_time
        assert 'max' in exec_time
        assert 'stdev' in exec_time
        assert 'raw_values' in exec_time
        assert len(exec_time['raw_values']) == 3
        
        # Verify memory usage statistics
        memory = results['memory_usage']
        assert 'mean' in memory
        assert 'median' in memory
        assert 'min' in memory
        assert 'max' in memory
        assert 'stdev' in memory
        assert 'raw_values' in memory
        assert len(memory['raw_values']) == 3
    
    def test_benchmark_with_exception(self, benchmark):
        """Test that benchmark handles exceptions correctly."""
        @benchmark.measure
        def failing_function():
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError, match="Test exception"):
            failing_function()
    
    def test_benchmark_multiple_runs(self, benchmark):
        """Test that multiple benchmark runs create separate files."""
        @benchmark.measure
        def test_function():
            time.sleep(0.001)
            return True
        
        # Run benchmark twice
        test_function()
        time.sleep(0.1)  # Ensure different timestamps
        test_function()
        
        # Check that multiple timestamped files exist
        result_files = [f for f in os.listdir(benchmark.results_dir) 
                       if f.startswith('test_benchmark_') and f.endswith('.json')]
        
        # Should have at least 2 files: 1 timestamped + 1 latest (latest overwrites)
        assert len(result_files) >= 2
        
        # Verify latest file exists
        latest_file = os.path.join(benchmark.results_dir, 'test_benchmark_latest.json')
        assert os.path.exists(latest_file)
    
    @patch('tests.utils.benchmark.psutil.Process')
    def test_memory_measurement(self, mock_process, benchmark):
        """Test that memory usage is measured correctly."""
        # Mock memory info
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        @benchmark.measure
        def test_function():
            return True
        
        result = test_function()
        assert result is True
        
        # Verify memory measurement was called
        assert mock_process.called
        assert mock_process.return_value.memory_info.called


class TestBenchmarkSuite:
    """Test the BenchmarkSuite class."""
    
    def test_suite_initialization(self):
        """Test that benchmark suite initializes correctly."""
        suite = BenchmarkSuite('test_suite')
        assert suite.name == 'test_suite'
        assert suite.benchmarks == []
    
    def test_add_benchmark(self):
        """Test adding benchmarks to suite."""
        suite = BenchmarkSuite('test_suite')
        benchmark1 = PerformanceBenchmark('test1')
        benchmark2 = PerformanceBenchmark('test2')
        
        suite.add_benchmark(benchmark1)
        suite.add_benchmark(benchmark2)
        
        assert len(suite.benchmarks) == 2
        assert benchmark1 in suite.benchmarks
        assert benchmark2 in suite.benchmarks
    
    def test_run_all(self):
        """Test running all benchmarks in suite."""
        suite = BenchmarkSuite('test_suite')
        benchmark1 = PerformanceBenchmark('test1')
        benchmark2 = PerformanceBenchmark('test2')
        
        suite.add_benchmark(benchmark1)
        suite.add_benchmark(benchmark2)
        
        results = suite.run_all()
        
        assert results['suite_name'] == 'test_suite'
        assert 'timestamp' in results
        assert 'datetime' in results
        assert 'benchmarks' in results
        assert 'test1' in results['benchmarks']
        assert 'test2' in results['benchmarks']


class TestBenchmarkFunction:
    """Test the benchmark_function decorator."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory for test results."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_benchmark_function_decorator(self, temp_results_dir):
        """Test the convenience decorator function."""
        # Patch the benchmark results directory
        with patch.object(PerformanceBenchmark, '__init__') as mock_init:
            mock_init.return_value = None
            
            # Create a mock benchmark instance
            mock_benchmark = MagicMock()
            mock_benchmark.measure = lambda func: func  # Return function unchanged
            
            with patch('tests.utils.benchmark.PerformanceBenchmark', return_value=mock_benchmark):
                @benchmark_function('decorator_test', iterations=2)
                def test_function():
                    time.sleep(0.001)
                    return 'decorated_result'
                
                result = test_function()
                assert result == 'decorated_result'


class TestCompareBenchmarks:
    """Test the compare_benchmarks function."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory with test results."""
        temp_dir = tempfile.mkdtemp()
        
        # Create two test result files
        result1 = {
            'name': 'test_benchmark',
            'execution_time': {'mean': 1.0},
            'memory_usage': {'mean': 10.0},
            'datetime': '2023-01-01T10:00:00'
        }
        result2 = {
            'name': 'test_benchmark',
            'execution_time': {'mean': 1.1},  # 10% slower
            'memory_usage': {'mean': 12.0},   # 20% more memory
            'datetime': '2023-01-01T11:00:00'
        }
        
        # Save older result first
        with open(os.path.join(temp_dir, 'test_benchmark_20230101_100000.json'), 'w') as f:
            json.dump(result1, f)
        
        time.sleep(0.01)  # Ensure different modification times
        
        # Save newer result
        with open(os.path.join(temp_dir, 'test_benchmark_20230101_110000.json'), 'w') as f:
            json.dump(result2, f)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_compare_benchmarks_success(self, temp_results_dir):
        """Test successful benchmark comparison."""
        comparison = compare_benchmarks('test_benchmark', temp_results_dir)
        
        assert comparison['benchmark_name'] == 'test_benchmark'
        assert comparison['latest_run'] == '2023-01-01T11:00:00'
        assert comparison['previous_run'] == '2023-01-01T10:00:00'
        assert abs(comparison['execution_time_change_percent'] - 10.0) < 0.001
        assert comparison['memory_usage_change_percent'] == 20.0
        assert comparison['latest_execution_time'] == 1.1
        assert comparison['previous_execution_time'] == 1.0
        assert comparison['latest_memory_usage'] == 12.0
        assert comparison['previous_memory_usage'] == 10.0
        assert comparison['is_regression'] is True  # Both changes > 10%
    
    def test_compare_benchmarks_insufficient_data(self, temp_results_dir):
        """Test comparison with insufficient data."""
        # Remove one file to have only one result
        files = os.listdir(temp_results_dir)
        os.remove(os.path.join(temp_results_dir, files[0]))
        
        comparison = compare_benchmarks('test_benchmark', temp_results_dir)
        
        assert 'error' in comparison
        assert 'Need at least 2 benchmark runs' in comparison['error']
    
    def test_compare_benchmarks_no_regression(self, temp_results_dir):
        """Test comparison with no regression detected."""
        # Create results with minimal change
        result1 = {
            'name': 'test_benchmark',
            'execution_time': {'mean': 1.0},
            'memory_usage': {'mean': 10.0},
            'datetime': '2023-01-01T10:00:00'
        }
        result2 = {
            'name': 'test_benchmark',
            'execution_time': {'mean': 1.05},  # 5% slower (below threshold)
            'memory_usage': {'mean': 10.5},   # 5% more memory (below threshold)
            'datetime': '2023-01-01T11:00:00'
        }
        
        # Clear existing files
        for file in os.listdir(temp_results_dir):
            os.remove(os.path.join(temp_results_dir, file))
        
        # Save new results
        with open(os.path.join(temp_results_dir, 'test_benchmark_20230101_100000.json'), 'w') as f:
            json.dump(result1, f)
        
        time.sleep(0.01)
        
        with open(os.path.join(temp_results_dir, 'test_benchmark_20230101_110000.json'), 'w') as f:
            json.dump(result2, f)
        
        comparison = compare_benchmarks('test_benchmark', temp_results_dir)
        
        assert comparison['is_regression'] is False  # Both changes < 10%


class TestBenchmarkIntegration:
    """Integration tests for the benchmarking framework."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory for test results."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_end_to_end_benchmark_workflow(self, temp_results_dir):
        """Test complete benchmarking workflow."""
        # Create benchmark
        benchmark = PerformanceBenchmark('integration_test', iterations=2)
        benchmark.results_dir = temp_results_dir
        
        # Define test function
        @benchmark.measure
        def cpu_intensive_task():
            # Simulate CPU-intensive work
            total = 0
            for i in range(10000):
                total += i * i
            return total
        
        # Run benchmark
        result = cpu_intensive_task()
        assert result > 0
        
        # Verify results file exists
        latest_file = os.path.join(temp_results_dir, 'integration_test_latest.json')
        assert os.path.exists(latest_file)
        
        # Load and verify results
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        assert results['name'] == 'integration_test'
        assert results['iterations'] == 2
        assert results['execution_time']['mean'] > 0
        assert len(results['execution_time']['raw_values']) == 2
        assert len(results['memory_usage']['raw_values']) == 2
        
        # Run again to create history
        time.sleep(0.1)
        cpu_intensive_task()
        
        # Compare results
        comparison = compare_benchmarks('integration_test', temp_results_dir)
        assert 'benchmark_name' in comparison
        assert comparison['benchmark_name'] == 'integration_test' 