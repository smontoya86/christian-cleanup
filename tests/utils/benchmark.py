"""
Performance benchmarking utility for regression testing.
"""

import json
import os
import statistics
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List

import psutil


class PerformanceBenchmark:
    """
    Performance benchmarking utility that measures execution time and memory usage.

    Usage:
        benchmark = PerformanceBenchmark('test_name', iterations=5)

        @benchmark.measure
        def my_function():
            # Function to benchmark
            return result

        result = my_function()
    """

    def __init__(self, name: str, iterations: int = 5):
        """
        Initialize the benchmark.

        Args:
            name: Name of the benchmark
            iterations: Number of iterations to run for statistical accuracy
        """
        self.name = name
        self.iterations = iterations
        self.results_dir = os.path.join(os.path.dirname(__file__), "../results")
        os.makedirs(self.results_dir, exist_ok=True)

    def measure(self, func: Callable) -> Callable:
        """
        Decorator to measure function performance.

        Args:
            func: Function to benchmark

        Returns:
            Wrapped function that performs benchmarking
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            execution_times = []
            memory_usages = []

            for i in range(self.iterations):
                # Clear cache between runs if available
                try:
                    from app.utils.cache import cache

                    if hasattr(cache, "clear"):
                        cache.clear()
                except ImportError:
                    pass  # Cache not available in test environment

                # Measure execution time and memory usage
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss / 1024 / 1024  # MB
                start_time = time.perf_counter()

                result = func(*args, **kwargs)

                end_time = time.perf_counter()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB

                execution_times.append(end_time - start_time)
                memory_usages.append(end_memory - start_memory)

            # Calculate statistics
            stats = self._calculate_stats(execution_times, memory_usages)

            # Save results to JSON file
            self._save_results(stats)

            return result

        return wrapper

    def _calculate_stats(
        self, execution_times: List[float], memory_usages: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate statistical metrics from benchmark data.

        Args:
            execution_times: List of execution times
            memory_usages: List of memory usage deltas

        Returns:
            Dictionary containing statistical metrics
        """
        return {
            "name": self.name,
            "iterations": self.iterations,
            "execution_time": {
                "mean": statistics.mean(execution_times),
                "median": statistics.median(execution_times),
                "min": min(execution_times),
                "max": max(execution_times),
                "stdev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "raw_values": execution_times,
            },
            "memory_usage": {
                "mean": statistics.mean(memory_usages),
                "median": statistics.median(memory_usages),
                "min": min(memory_usages),
                "max": max(memory_usages),
                "stdev": statistics.stdev(memory_usages) if len(memory_usages) > 1 else 0,
                "raw_values": memory_usages,
            },
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
        }

    def _save_results(self, stats: Dict[str, Any]) -> None:
        """
        Save benchmark results to JSON file.

        Args:
            stats: Statistical metrics to save
        """
        # Create timestamped filename to preserve history
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)

        with open(filepath, "w") as f:
            json.dump(stats, f, indent=2)

        # Also save as latest result for easy access
        latest_filepath = os.path.join(self.results_dir, f"{self.name}_latest.json")
        with open(latest_filepath, "w") as f:
            json.dump(stats, f, indent=2)


class BenchmarkSuite:
    """
    Collection of benchmarks that can be run together.
    """

    def __init__(self, name: str):
        """
        Initialize the benchmark suite.

        Args:
            name: Name of the benchmark suite
        """
        self.name = name
        self.benchmarks = []

    def add_benchmark(self, benchmark: PerformanceBenchmark) -> None:
        """
        Add a benchmark to the suite.

        Args:
            benchmark: Benchmark to add
        """
        self.benchmarks.append(benchmark)

    def run_all(self) -> Dict[str, Any]:
        """
        Run all benchmarks in the suite.

        Returns:
            Dictionary containing results from all benchmarks
        """
        results = {
            "suite_name": self.name,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "benchmarks": {},
        }

        for benchmark in self.benchmarks:
            # Note: Individual benchmarks need to be run separately
            # This method is for organizing and reporting
            results["benchmarks"][benchmark.name] = {
                "iterations": benchmark.iterations,
                "results_dir": benchmark.results_dir,
            }

        return results


def benchmark_function(name: str, iterations: int = 5):
    """
    Convenience decorator for benchmarking functions.

    Args:
        name: Name of the benchmark
        iterations: Number of iterations to run

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        benchmark = PerformanceBenchmark(name, iterations)
        return benchmark.measure(func)

    return decorator


def compare_benchmarks(benchmark_name: str, results_dir: str = None) -> Dict[str, Any]:
    """
    Compare the latest benchmark results with previous runs.

    Args:
        benchmark_name: Name of the benchmark to compare
        results_dir: Directory containing benchmark results

    Returns:
        Dictionary containing comparison metrics
    """
    if results_dir is None:
        results_dir = os.path.join(os.path.dirname(__file__), "../results")

    # Find all result files for this benchmark
    import glob

    pattern = os.path.join(results_dir, f"{benchmark_name}_*.json")
    result_files = glob.glob(pattern)

    if len(result_files) < 2:
        return {"error": "Need at least 2 benchmark runs to compare"}

    # Sort by timestamp (newest first)
    result_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # Load latest and previous results
    with open(result_files[0], "r") as f:
        latest = json.load(f)
    with open(result_files[1], "r") as f:
        previous = json.load(f)

    # Calculate percentage changes
    time_change = (
        (latest["execution_time"]["mean"] - previous["execution_time"]["mean"])
        / previous["execution_time"]["mean"]
        * 100
    )

    # Handle division by zero for memory usage
    if previous["memory_usage"]["mean"] == 0:
        memory_change = 0 if latest["memory_usage"]["mean"] == 0 else 100
    else:
        memory_change = (
            (latest["memory_usage"]["mean"] - previous["memory_usage"]["mean"])
            / previous["memory_usage"]["mean"]
            * 100
        )

    return {
        "benchmark_name": benchmark_name,
        "latest_run": latest["datetime"],
        "previous_run": previous["datetime"],
        "execution_time_change_percent": time_change,
        "memory_usage_change_percent": memory_change,
        "latest_execution_time": latest["execution_time"]["mean"],
        "previous_execution_time": previous["execution_time"]["mean"],
        "latest_memory_usage": latest["memory_usage"]["mean"],
        "previous_memory_usage": previous["memory_usage"]["mean"],
        "is_regression": time_change > 10 or memory_change > 10,  # 10% threshold
    }
