"""
Performance regression detection utility.
"""
import os
import json
import glob
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional


class RegressionDetector:
    """
    Detects performance regressions by analyzing benchmark results over time.
    """
    
    def __init__(self, results_dir: str, threshold: float = 0.1):
        """
        Initialize the regression detector.
        
        Args:
            results_dir: Directory containing benchmark result files
            threshold: Regression threshold as a percentage (0.1 = 10%)
        """
        self.results_dir = results_dir
        self.threshold = threshold
        
    def detect_regressions(self) -> List[Dict[str, Any]]:
        """
        Detect performance regressions across all benchmarks.
        
        Returns:
            List of detected regressions with details
        """
        regressions = []
        
        # Get all benchmark result files
        result_files = glob.glob(os.path.join(self.results_dir, '*_*.json'))
        
        # Group files by benchmark name
        benchmarks = self._group_results_by_benchmark(result_files)
        
        # Analyze each benchmark for regressions
        for name, results in benchmarks.items():
            if len(results) < 2:
                continue  # Need at least 2 results to compare
                
            # Sort by timestamp (oldest first)
            results.sort(key=lambda x: x['timestamp'])
            
            # Compare latest result with previous
            latest = results[-1]
            previous = results[-2]
            
            # Check for execution time regression
            time_regression = self._check_metric_regression(
                latest['execution_time']['mean'],
                previous['execution_time']['mean'],
                'execution_time'
            )
            if time_regression:
                time_regression.update({
                    'benchmark': name,
                    'timestamp': datetime.fromtimestamp(latest['timestamp']).isoformat(),
                    'latest_run': latest['datetime'],
                    'previous_run': previous['datetime']
                })
                regressions.append(time_regression)
            
            # Check for memory usage regression
            memory_regression = self._check_metric_regression(
                latest['memory_usage']['mean'],
                previous['memory_usage']['mean'],
                'memory_usage'
            )
            if memory_regression:
                memory_regression.update({
                    'benchmark': name,
                    'timestamp': datetime.fromtimestamp(latest['timestamp']).isoformat(),
                    'latest_run': latest['datetime'],
                    'previous_run': previous['datetime']
                })
                regressions.append(memory_regression)
        
        return regressions
    
    def analyze_trends(self, benchmark_name: str, window_size: int = 5) -> Dict[str, Any]:
        """
        Analyze performance trends for a specific benchmark.
        
        Args:
            benchmark_name: Name of the benchmark to analyze
            window_size: Number of recent results to analyze
            
        Returns:
            Dictionary containing trend analysis
        """
        # Get results for specific benchmark
        pattern = os.path.join(self.results_dir, f'{benchmark_name}_*.json')
        result_files = glob.glob(pattern)
        
        if len(result_files) < window_size:
            return {
                'error': f'Need at least {window_size} results for trend analysis',
                'available_results': len(result_files)
            }
        
        # Load and sort results
        results = []
        for file_path in result_files:
            with open(file_path, 'r') as f:
                results.append(json.load(f))
        
        results.sort(key=lambda x: x['timestamp'])
        recent_results = results[-window_size:]
        
        # Extract metrics
        execution_times = [r['execution_time']['mean'] for r in recent_results]
        memory_usages = [r['memory_usage']['mean'] for r in recent_results]
        timestamps = [r['timestamp'] for r in recent_results]
        
        # Calculate trends
        execution_trend = self._calculate_trend(execution_times)
        memory_trend = self._calculate_trend(memory_usages)
        
        return {
            'benchmark_name': benchmark_name,
            'window_size': window_size,
            'time_range': {
                'start': datetime.fromtimestamp(timestamps[0]).isoformat(),
                'end': datetime.fromtimestamp(timestamps[-1]).isoformat()
            },
            'execution_time': {
                'trend': execution_trend,
                'current': execution_times[-1],
                'average': statistics.mean(execution_times),
                'min': min(execution_times),
                'max': max(execution_times),
                'variance': statistics.variance(execution_times) if len(execution_times) > 1 else 0
            },
            'memory_usage': {
                'trend': memory_trend,
                'current': memory_usages[-1],
                'average': statistics.mean(memory_usages),
                'min': min(memory_usages),
                'max': max(memory_usages),
                'variance': statistics.variance(memory_usages) if len(memory_usages) > 1 else 0
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Dictionary containing the complete performance report
        """
        # Detect regressions
        regressions = self.detect_regressions()
        
        # Get all benchmarks
        result_files = glob.glob(os.path.join(self.results_dir, '*_*.json'))
        benchmarks = self._group_results_by_benchmark(result_files)
        
        # Analyze trends for each benchmark
        trends = {}
        for name in benchmarks.keys():
            trends[name] = self.analyze_trends(name)
        
        # Calculate summary statistics
        total_benchmarks = len(benchmarks)
        benchmarks_with_regressions = len(set(r['benchmark'] for r in regressions))
        
        # Find most problematic benchmarks
        regression_counts = {}
        for regression in regressions:
            benchmark = regression['benchmark']
            regression_counts[benchmark] = regression_counts.get(benchmark, 0) + 1
        
        most_problematic = sorted(
            regression_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_benchmarks': total_benchmarks,
                'benchmarks_with_regressions': benchmarks_with_regressions,
                'total_regressions': len(regressions),
                'regression_rate': benchmarks_with_regressions / total_benchmarks if total_benchmarks > 0 else 0
            },
            'regressions': regressions,
            'trends': trends,
            'most_problematic_benchmarks': most_problematic,
            'threshold': self.threshold
        }
    
    def _group_results_by_benchmark(self, result_files: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group benchmark result files by benchmark name.
        
        Args:
            result_files: List of result file paths
            
        Returns:
            Dictionary mapping benchmark names to their results
        """
        benchmarks = {}
        
        for file_path in result_files:
            # Skip 'latest' files as they're duplicates
            if '_latest.json' in file_path:
                continue
                
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    name = data['name']
                    if name not in benchmarks:
                        benchmarks[name] = []
                    benchmarks[name].append(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not parse {file_path}: {e}")
                continue
        
        return benchmarks
    
    def _check_metric_regression(self, current: float, previous: float, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if a metric shows regression.
        
        Args:
            current: Current metric value
            previous: Previous metric value
            metric_name: Name of the metric
            
        Returns:
            Regression details if detected, None otherwise
        """
        # Handle division by zero
        if previous == 0:
            if current > 0:
                return {
                    'metric': metric_name,
                    'previous': previous,
                    'current': current,
                    'change_percent': 100.0,
                    'severity': 'critical'
                }
            return None
        
        # Calculate percentage change
        change = (current - previous) / previous
        
        # Check if change exceeds threshold
        if change > self.threshold:
            severity = self._determine_severity(change)
            return {
                'metric': metric_name,
                'previous': previous,
                'current': current,
                'change_percent': change * 100,
                'severity': severity
            }
        
        return None
    
    def _determine_severity(self, change: float) -> str:
        """
        Determine the severity of a performance regression.
        
        Args:
            change: Percentage change as a decimal
            
        Returns:
            Severity level string
        """
        if change > 0.5:  # 50% or more
            return 'critical'
        elif change > 0.25:  # 25-50%
            return 'high'
        elif change > 0.1:  # 10-25%
            return 'medium'
        else:  # Less than 10%
            return 'low'
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate the trend direction for a series of values.
        
        Args:
            values: List of metric values over time
            
        Returns:
            Trend direction: 'improving', 'degrading', or 'stable'
        """
        if len(values) < 2:
            return 'stable'
        
        # Calculate simple linear trend
        n = len(values)
        x = list(range(n))
        
        # Calculate slope using least squares
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        # Determine trend based on slope
        if slope > 0.01:  # Increasing (degrading for performance metrics)
            return 'degrading'
        elif slope < -0.01:  # Decreasing (improving for performance metrics)
            return 'improving'
        else:
            return 'stable' 