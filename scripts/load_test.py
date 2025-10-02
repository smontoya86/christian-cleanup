"""
Load Testing Suite for Christian Cleanup

Tests system performance under various load scenarios to:
- Determine optimal database pool sizes
- Identify bottlenecks
- Measure cache effectiveness
- Test circuit breaker behavior
- Validate rate limiting
"""

import os
import sys
import time
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTester:
    """
    Load testing utility for Christian Cleanup API.
    """
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        
    def test_single_request(self, song_id: int = 1) -> Dict[str, Any]:
        """
        Test a single analysis request.
        
        Returns:
            Dict with timing and result info
        """
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/analyze/{song_id}",
                timeout=30
            )
            elapsed = time.time() - start
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'elapsed': elapsed,
                'cache_hit': response.json().get('cache_hit', False) if response.status_code == 200 else False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                'success': False,
                'error': str(e),
                'elapsed': elapsed,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def test_concurrent_requests(
        self,
        num_requests: int = 10,
        song_ids: List[int] = None
    ) -> Dict[str, Any]:
        """
        Test concurrent requests to measure connection pool behavior.
        
        Args:
            num_requests: Number of concurrent requests
            song_ids: List of song IDs to test (cycles if needed)
            
        Returns:
            Dict with aggregate statistics
        """
        if song_ids is None:
            song_ids = list(range(1, 101))  # Use first 100 songs
        
        logger.info(f"Starting {num_requests} concurrent requests...")
        
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                song_id = song_ids[i % len(song_ids)]
                future = executor.submit(self.test_single_request, song_id)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        cache_hits = [r for r in results if r.get('cache_hit')]
        
        elapsed_times = [r['elapsed'] for r in successful]
        
        stats = {
            'total_requests': num_requests,
            'successful': len(successful),
            'failed': len(failed),
            'cache_hits': len(cache_hits),
            'total_time': round(total_time, 2),
            'requests_per_second': round(num_requests / total_time, 2),
            'cache_hit_rate': round(len(cache_hits) / max(len(successful), 1) * 100, 1),
            'avg_response_time': round(sum(elapsed_times) / max(len(elapsed_times), 1), 3) if elapsed_times else 0,
            'min_response_time': round(min(elapsed_times), 3) if elapsed_times else 0,
            'max_response_time': round(max(elapsed_times), 3) if elapsed_times else 0,
            'p95_response_time': round(sorted(elapsed_times)[int(len(elapsed_times) * 0.95)], 3) if elapsed_times else 0,
            'p99_response_time': round(sorted(elapsed_times)[int(len(elapsed_times) * 0.99)], 3) if elapsed_times else 0,
        }
        
        logger.info(f"✅ Completed: {stats['successful']}/{num_requests} successful")
        logger.info(f"⚡ RPS: {stats['requests_per_second']}")
        logger.info(f"⏱️  Avg: {stats['avg_response_time']}s, P95: {stats['p95_response_time']}s")
        logger.info(f"💾 Cache hit rate: {stats['cache_hit_rate']}%")
        
        return stats
    
    def test_ramp_up(
        self,
        start_workers: int = 1,
        max_workers: int = 50,
        step: int = 5,
        requests_per_level: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Test with ramping concurrency to find breaking point.
        
        Args:
            start_workers: Starting concurrency level
            max_workers: Maximum concurrency level
            step: Increment for each level
            requests_per_level: Requests to make at each level
            
        Returns:
            List of stats for each level
        """
        logger.info("🚀 Starting ramp-up load test...")
        logger.info(f"Range: {start_workers} → {max_workers} workers (step: {step})")
        
        all_stats = []
        
        for workers in range(start_workers, max_workers + 1, step):
            logger.info(f"\n📊 Testing with {workers} concurrent workers...")
            
            stats = self.test_concurrent_requests(
                num_requests=requests_per_level,
            )
            stats['concurrency'] = workers
            all_stats.append(stats)
            
            # Check for degradation
            if stats['failed'] > requests_per_level * 0.1:  # >10% failure rate
                logger.warning(f"⚠️  High failure rate at {workers} workers: {stats['failed']}/{requests_per_level}")
            
            if stats['avg_response_time'] > 5.0:  # >5s average
                logger.warning(f"⚠️  Slow responses at {workers} workers: {stats['avg_response_time']}s avg")
            
            # Pause between levels
            time.sleep(2)
        
        return all_stats
    
    def test_sustained_load(
        self,
        duration_seconds: int = 60,
        requests_per_second: int = 10
    ) -> Dict[str, Any]:
        """
        Test sustained load over time.
        
        Args:
            duration_seconds: How long to run test
            requests_per_second: Target RPS
            
        Returns:
            Dict with aggregate statistics
        """
        logger.info(f"🔥 Starting sustained load test: {requests_per_second} RPS for {duration_seconds}s")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        interval = 1.0 / requests_per_second
        
        results = []
        request_count = 0
        
        with ThreadPoolExecutor(max_workers=requests_per_second * 2) as executor:
            while time.time() < end_time:
                future = executor.submit(self.test_single_request, (request_count % 100) + 1)
                future.add_done_callback(lambda f: results.append(f.result()))
                request_count += 1
                
                # Maintain target RPS
                time.sleep(interval)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        cache_hits = [r for r in results if r.get('cache_hit')]
        
        elapsed_times = [r['elapsed'] for r in successful]
        
        stats = {
            'duration': round(total_time, 2),
            'total_requests': len(results),
            'target_rps': requests_per_second,
            'actual_rps': round(len(results) / total_time, 2),
            'successful': len(successful),
            'failed': len(failed),
            'cache_hits': len(cache_hits),
            'cache_hit_rate': round(len(cache_hits) / max(len(successful), 1) * 100, 1),
            'avg_response_time': round(sum(elapsed_times) / max(len(elapsed_times), 1), 3) if elapsed_times else 0,
            'p95_response_time': round(sorted(elapsed_times)[int(len(elapsed_times) * 0.95)], 3) if elapsed_times else 0,
            'p99_response_time': round(sorted(elapsed_times)[int(len(elapsed_times) * 0.99)], 3) if elapsed_times else 0,
        }
        
        logger.info(f"✅ Completed {stats['total_requests']} requests in {stats['duration']}s")
        logger.info(f"⚡ Actual RPS: {stats['actual_rps']} (target: {requests_per_second})")
        logger.info(f"📊 Success rate: {round(stats['successful']/stats['total_requests']*100, 1)}%")
        
        return stats
    
    def generate_report(self, stats_list: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive report from test results.
        
        Args:
            stats_list: List of statistics from tests
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("\n" + "="*80)
        report.append("LOAD TEST REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report.append(f"Base URL: {self.base_url}")
        report.append("")
        
        if not stats_list:
            report.append("No test results available.")
            return "\n".join(report)
        
        # Overall summary
        report.append("OVERALL SUMMARY")
        report.append("-" * 80)
        total_requests = sum(s['total_requests'] for s in stats_list)
        total_successful = sum(s['successful'] for s in stats_list)
        total_failed = sum(s['failed'] for s in stats_list)
        avg_cache_hit_rate = sum(s.get('cache_hit_rate', 0) for s in stats_list) / len(stats_list)
        
        report.append(f"Total Requests: {total_requests}")
        report.append(f"Successful: {total_successful} ({round(total_successful/total_requests*100, 1)}%)")
        report.append(f"Failed: {total_failed} ({round(total_failed/total_requests*100, 1)}%)")
        report.append(f"Avg Cache Hit Rate: {round(avg_cache_hit_rate, 1)}%")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-" * 80)
        report.append(f"{'Concurrency':<12} {'Requests':<10} {'Success':<8} {'RPS':<8} {'Avg(s)':<8} {'P95(s)':<8} {'Cache%':<8}")
        report.append("-" * 80)
        
        for stats in stats_list:
            concurrency = stats.get('concurrency', 'N/A')
            report.append(
                f"{concurrency:<12} "
                f"{stats['total_requests']:<10} "
                f"{stats['successful']:<8} "
                f"{stats['requests_per_second']:<8.1f} "
                f"{stats['avg_response_time']:<8.3f} "
                f"{stats.get('p95_response_time', 0):<8.3f} "
                f"{stats.get('cache_hit_rate', 0):<8.1f}"
            )
        
        report.append("")
        report.append("="*80)
        
        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 80)
        
        # Find optimal concurrency (best RPS with <5% failure rate)
        optimal = None
        for stats in stats_list:
            failure_rate = stats['failed'] / stats['total_requests'] * 100
            if failure_rate < 5 and (optimal is None or stats['requests_per_second'] > optimal['requests_per_second']):
                optimal = stats
        
        if optimal:
            report.append(f"✅ Optimal concurrency: {optimal.get('concurrency', 'N/A')} workers")
            report.append(f"   - RPS: {optimal['requests_per_second']}")
            report.append(f"   - Avg response time: {optimal['avg_response_time']}s")
            report.append(f"   - Failure rate: {round(optimal['failed']/optimal['total_requests']*100, 2)}%")
            report.append("")
            report.append(f"📊 Recommended DB pool settings:")
            suggested_pool = max(5, optimal.get('concurrency', 10) // 2)
            suggested_overflow = max(10, optimal.get('concurrency', 10))
            report.append(f"   - DB_POOL_SIZE={suggested_pool}")
            report.append(f"   - DB_MAX_OVERFLOW={suggested_overflow}")
            report.append(f"   - Total capacity: {suggested_pool + suggested_overflow}")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)


def main():
    """Run load tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load test Christian Cleanup API')
    parser.add_argument('--url', default='http://localhost:5001', help='Base URL')
    parser.add_argument('--test', choices=['quick', 'rampup', 'sustained', 'all'], 
                       default='quick', help='Test type')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent workers for quick test')
    parser.add_argument('--duration', type=int, default=60, help='Duration for sustained test (seconds)')
    parser.add_argument('--rps', type=int, default=10, help='Target RPS for sustained test')
    
    args = parser.parse_args()
    
    tester = LoadTester(base_url=args.url)
    all_stats = []
    
    if args.test in ['quick', 'all']:
        logger.info("Running quick test...")
        stats = tester.test_concurrent_requests(num_requests=args.workers)
        all_stats.append(stats)
    
    if args.test in ['rampup', 'all']:
        logger.info("Running ramp-up test...")
        stats_list = tester.test_ramp_up(
            start_workers=5,
            max_workers=50,
            step=5,
            requests_per_level=20
        )
        all_stats.extend(stats_list)
    
    if args.test in ['sustained', 'all']:
        logger.info("Running sustained load test...")
        stats = tester.test_sustained_load(
            duration_seconds=args.duration,
            requests_per_second=args.rps
        )
        all_stats.append(stats)
    
    # Generate and print report
    report = tester.generate_report(all_stats)
    print(report)
    
    # Save report
    report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"📄 Report saved to: {report_file}")


if __name__ == '__main__':
    main()

