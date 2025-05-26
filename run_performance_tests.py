#!/usr/bin/env python
"""
Performance test runner with regression detection.
"""
import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from tests.utils.regression_detector import RegressionDetector


def main():
    """Main function to run performance tests."""
    parser = argparse.ArgumentParser(description='Run performance tests with regression detection')
    parser.add_argument('--test', help='Run a specific test file (e.g., test_database, test_cache)')
    parser.add_argument('--check-regressions', action='store_true', 
                       help='Check for performance regressions after running tests')
    parser.add_argument('--threshold', type=float, default=0.1,
                       help='Regression threshold as percentage (default: 0.1 = 10%%)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--iterations', type=int, default=None,
                       help='Override default iterations for benchmarks')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive performance report')
    parser.add_argument('--clean', action='store_true',
                       help='Clean previous test results before running')
    
    args = parser.parse_args()
    
    # Setup paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(project_root, 'tests', 'results')
    
    # Ensure results directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    # Clean previous results if requested
    if args.clean:
        print("Cleaning previous test results...")
        import shutil
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)
    
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    if not os.environ.get('TEST_DATABASE_URL'):
        os.environ['TEST_DATABASE_URL'] = 'postgresql://localhost/christian_music_analyzer_test'
    if not os.environ.get('TEST_REDIS_URL'):
        os.environ['TEST_REDIS_URL'] = 'redis://localhost:6379/1'
    
    # Build pytest command
    if args.test:
        test_path = f'tests/performance/test_{args.test}.py'
        if not test_path.endswith('.py'):
            test_path += '.py'
        
        if not os.path.exists(test_path):
            print(f"Error: Test file {test_path} not found")
            return 1
        
        cmd = ['python', '-m', 'pytest', test_path]
    else:
        cmd = ['python', '-m', 'pytest', 'tests/performance/']
    
    # Add verbose flag if requested
    if args.verbose:
        cmd.append('-v')
    
    # Add additional pytest options
    cmd.extend(['-s', '--tb=short'])
    
    print(f"Running performance tests: {' '.join(cmd)}")
    print(f"Results will be saved to: {results_dir}")
    print("-" * 60)
    
    # Run the tests
    start_time = datetime.now()
    result = subprocess.run(cmd, cwd=project_root)
    end_time = datetime.now()
    
    test_duration = (end_time - start_time).total_seconds()
    print(f"\nTest execution completed in {test_duration:.2f} seconds")
    
    # Check for regressions if requested
    if args.check_regressions:
        print("\nChecking for performance regressions...")
        detector = RegressionDetector(results_dir, threshold=args.threshold)
        regressions = detector.detect_regressions()
        
        if regressions:
            print(f"\n⚠️  Performance regressions detected ({len(regressions)} issues):")
            print("-" * 60)
            
            for regression in regressions:
                severity_emoji = {
                    'low': '🟡',
                    'medium': '🟠', 
                    'high': '🔴',
                    'critical': '💥'
                }.get(regression['severity'], '❓')
                
                print(f"{severity_emoji} {regression['benchmark']} - {regression['metric']}")
                print(f"   Change: {regression['change_percent']:.2f}% slower")
                print(f"   Previous: {regression['previous']:.4f}")
                print(f"   Current: {regression['current']:.4f}")
                print(f"   Severity: {regression['severity']}")
                print(f"   Time: {regression['timestamp']}")
                print()
            
            return 1
        else:
            print("✅ No performance regressions detected")
    
    # Generate comprehensive report if requested
    if args.report:
        print("\nGenerating comprehensive performance report...")
        detector = RegressionDetector(results_dir, threshold=args.threshold)
        report = detector.generate_report()
        
        # Save report to file
        report_file = os.path.join(results_dir, f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Performance report saved to: {report_file}")
        
        # Print summary
        summary = report['summary']
        print(f"\nPerformance Summary:")
        print(f"  Total benchmarks: {summary['total_benchmarks']}")
        print(f"  Benchmarks with regressions: {summary['benchmarks_with_regressions']}")
        print(f"  Total regressions: {summary['total_regressions']}")
        print(f"  Regression rate: {summary['regression_rate']:.1%}")
        
        if report['most_problematic_benchmarks']:
            print(f"\nMost problematic benchmarks:")
            for benchmark, count in report['most_problematic_benchmarks']:
                print(f"  {benchmark}: {count} regressions")
    
    return result.returncode


def check_dependencies():
    """Check if required dependencies are available."""
    required_packages = ['pytest', 'psutil', 'redis']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Error: Missing required packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install " + ' '.join(missing_packages))
        return False
    
    return True


def check_services():
    """Check if required services (PostgreSQL, Redis) are available."""
    import socket
    
    services = [
        ('PostgreSQL', 'localhost', 5432),
        ('Redis', 'localhost', 6379)
    ]
    
    unavailable_services = []
    
    for service_name, host, port in services:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            unavailable_services.append(f"{service_name} ({host}:{port})")
    
    if unavailable_services:
        print(f"Warning: The following services are not available:")
        for service in unavailable_services:
            print(f"  - {service}")
        print("Some tests may fail or be skipped.")
        return False
    
    return True


if __name__ == '__main__':
    print("Christian Music Analyzer - Performance Test Runner")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check services (warn but don't fail)
    check_services()
    
    # Run main function
    sys.exit(main()) 