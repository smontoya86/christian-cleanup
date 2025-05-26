#!/usr/bin/env python3
"""
Performance Assessment Script for Database Optimizations

This script benchmarks database operations to measure the impact of performance optimizations.
It can be run before and after optimizations to quantify improvements.
"""

import os
import sys
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.services.batch_operations import BatchOperationService
from app.utils.database_monitoring import get_pool_status, check_pool_health
from app.utils.query_monitoring import get_query_statistics
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy import text


class PerformanceAssessment:
    """
    Comprehensive performance assessment for database operations.
    """
    
    def __init__(self, app=None):
        """Initialize the performance assessment."""
        self.app = app or create_app('development')
        self.results = {}
        self.batch_service = BatchOperationService()
    
    def run_assessment(self, output_file: str = None) -> Dict[str, Any]:
        """
        Run the complete performance assessment.
        
        Args:
            output_file: Optional file path to save results
            
        Returns:
            Dictionary containing all benchmark results
        """
        print("🚀 Starting Performance Assessment...")
        print("=" * 60)
        
        with self.app.app_context():
            # Ensure we have test data
            self._ensure_test_data()
            
            # Run all benchmarks
            self.results = {
                'timestamp': datetime.now().isoformat(),
                'database_info': self._get_database_info(),
                'connection_pool': self._assess_connection_pool(),
                'playlist_loading': self.benchmark_playlist_loading(),
                'song_queries': self.benchmark_song_queries(),
                'batch_operations': self.benchmark_batch_operations(),
                'index_performance': self._benchmark_index_performance(),
                'query_monitoring': self._assess_query_monitoring(),
                'memory_usage': self._benchmark_memory_usage(),
                'concurrent_access': self._benchmark_concurrent_access(),
                'summary': {}
            }
            
            # Generate summary
            self.results['summary'] = self._generate_summary()
            
            # Save results if requested
            if output_file:
                self._save_results(output_file)
            
            # Print summary
            self._print_summary()
            
        return self.results
    
    def _ensure_test_data(self):
        """Ensure we have sufficient test data for benchmarking."""
        print("📊 Ensuring test data exists...")
        
        # Check if we have enough data
        user_count = User.query.count()
        playlist_count = Playlist.query.count()
        song_count = Song.query.count()
        
        if user_count < 1 or playlist_count < 5 or song_count < 20:
            print("⚠️  Insufficient test data. Creating sample data...")
            self._create_sample_data()
        else:
            print(f"✅ Found sufficient test data: {user_count} users, {playlist_count} playlists, {song_count} songs")
    
    def _create_sample_data(self):
        """Create sample data for testing."""
        # Create test user if none exists
        user = User.query.first()
        if not user:
            from datetime import timedelta
            user = User(
                spotify_id='perf_test_user',
                display_name='Performance Test User',
                email='perf@test.com',
                access_token='test_token',
                refresh_token='test_refresh',
                token_expiry=datetime.now() + timedelta(hours=1)
            )
            db.session.add(user)
            db.session.commit()
        
        # Create playlists
        for i in range(10):
            playlist = Playlist(
                spotify_id=f'perf_playlist_{i}',
                name=f'Performance Test Playlist {i}',
                owner_id=user.id
            )
            db.session.add(playlist)
        
        db.session.commit()
        
        # Create songs using batch operations
        song_data = []
        for i in range(50):
            song_data.append({
                'spotify_id': f'perf_song_{i}',
                'title': f'Performance Test Song {i}',
                'artist': f'Test Artist {i % 10}',
                'album': f'Test Album {i % 5}'
            })
        
        songs = self.batch_service.create_songs_batch(song_data)
        
        # Create playlist-song associations
        playlists = Playlist.query.filter(Playlist.spotify_id.like('perf_playlist_%')).all()
        for playlist in playlists:
            for i, song in enumerate(songs[:5]):  # 5 songs per playlist
                playlist_song = PlaylistSong(
                    playlist_id=playlist.id,
                    song_id=song.id,
                    track_position=i
                )
                db.session.add(playlist_song)
        
        # Create analysis results
        for song in songs:
            analysis = AnalysisResult(
                song_id=song.id,
                score=85.0,
                concern_level='Low',
                explanation='Performance test analysis',
                status=AnalysisResult.STATUS_COMPLETED
            )
            db.session.add(analysis)
        
        db.session.commit()
        print("✅ Sample data created successfully")
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get database configuration information."""
        return {
            'database_uri': self.app.config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1] if '@' in self.app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'sqlite',
            'pool_size': self.app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).get('pool_size', 'default'),
            'max_overflow': self.app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).get('max_overflow', 'default'),
            'query_recording': self.app.config.get('SQLALCHEMY_RECORD_QUERIES', False),
            'slow_query_threshold': self.app.config.get('SLOW_QUERY_THRESHOLD', 0.5)
        }
    
    def _assess_connection_pool(self) -> Dict[str, Any]:
        """Assess connection pool performance and health."""
        print("🔗 Assessing connection pool...")
        
        pool_status = get_pool_status()
        health_status = check_pool_health()
        
        return {
            'pool_status': pool_status,
            'health_status': health_status,
            'timestamp': datetime.now().isoformat()
        }
    
    def benchmark_playlist_loading(self) -> Dict[str, Any]:
        """Benchmark playlist loading with different strategies."""
        print("📋 Benchmarking playlist loading...")
        
        user = User.query.first()
        if not user:
            return {'error': 'No test user found'}
        
        results = {}
        
        # Benchmark 1: Unoptimized (N+1 pattern)
        times = []
        for _ in range(3):  # Run 3 times for average
            start_time = time.time()
            playlists = Playlist.query.filter_by(owner_id=user.id).all()
            for playlist in playlists:
                songs = Song.query.join(PlaylistSong).filter(
                    PlaylistSong.playlist_id == playlist.id
                ).all()
                for song in songs:
                    analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            times.append(time.time() - start_time)
        
        results['unoptimized'] = {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'runs': len(times)
        }
        
        # Benchmark 2: Optimized with eager loading
        times = []
        for _ in range(3):
            start_time = time.time()
            playlists = Playlist.query.filter_by(owner_id=user.id).options(
                subqueryload(Playlist.songs).joinedload(Song.analysis_result)
            ).all()
            # Access the data to trigger loading
            for playlist in playlists:
                for song in playlist.songs:
                    analysis = song.analysis_result
            times.append(time.time() - start_time)
        
        results['optimized'] = {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'runs': len(times)
        }
        
        # Calculate improvement
        if results['unoptimized']['avg_time'] > 0:
            improvement = (results['unoptimized']['avg_time'] - results['optimized']['avg_time']) / results['unoptimized']['avg_time'] * 100
            results['improvement_percent'] = improvement
        
        return results
    
    def benchmark_song_queries(self) -> Dict[str, Any]:
        """Benchmark various song query patterns."""
        print("🎵 Benchmarking song queries...")
        
        results = {}
        
        # Benchmark indexed queries (spotify_id)
        times = []
        for _ in range(10):
            start_time = time.time()
            song = Song.query.filter_by(spotify_id='perf_song_0').first()
            times.append(time.time() - start_time)
        
        results['indexed_lookup'] = {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times)
        }
        
        # Benchmark text search queries
        times = []
        for _ in range(5):
            start_time = time.time()
            songs = Song.query.filter(Song.title.like('Performance Test%')).all()
            times.append(time.time() - start_time)
        
        results['text_search'] = {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'result_count': len(songs) if 'songs' in locals() else 0
        }
        
        # Benchmark join queries
        times = []
        for _ in range(5):
            start_time = time.time()
            songs_with_analysis = Song.query.join(AnalysisResult).filter(
                AnalysisResult.score > 50.0
            ).all()
            times.append(time.time() - start_time)
        
        results['join_query'] = {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'result_count': len(songs_with_analysis) if 'songs_with_analysis' in locals() else 0
        }
        
        return results
    
    def benchmark_batch_operations(self) -> Dict[str, Any]:
        """Benchmark batch vs individual operations."""
        print("📦 Benchmarking batch operations...")
        
        results = {}
        
        # Benchmark individual operations
        start_time = time.time()
        individual_songs = []
        for i in range(20):
            song = Song(
                spotify_id=f'individual_bench_{i}',
                title=f'Individual Benchmark Song {i}',
                artist=f'Individual Artist {i}'
            )
            db.session.add(song)
            db.session.commit()
            individual_songs.append(song)
        individual_time = time.time() - start_time
        
        # Clean up
        for song in individual_songs:
            db.session.delete(song)
        db.session.commit()
        
        # Benchmark batch operations
        start_time = time.time()
        song_data = [
            {
                'spotify_id': f'batch_bench_{i}',
                'title': f'Batch Benchmark Song {i}',
                'artist': f'Batch Artist {i}'
            }
            for i in range(20)
        ]
        batch_songs = self.batch_service.create_songs_batch(song_data)
        batch_time = time.time() - start_time
        
        # Clean up batch songs
        for song in batch_songs:
            db.session.delete(song)
        db.session.commit()
        
        results = {
            'individual_operations': {
                'time': individual_time,
                'items': 20,
                'time_per_item': individual_time / 20
            },
            'batch_operations': {
                'time': batch_time,
                'items': 20,
                'time_per_item': batch_time / 20
            }
        }
        
        if individual_time > 0:
            results['speedup_factor'] = individual_time / batch_time
            results['improvement_percent'] = (individual_time - batch_time) / individual_time * 100
        
        return results
    
    def _benchmark_index_performance(self) -> Dict[str, Any]:
        """Benchmark index performance."""
        print("📇 Benchmarking index performance...")
        
        results = {}
        
        # Test various indexed columns
        indexed_columns = [
            ('songs', 'spotify_id', 'perf_song_0'),
            ('playlists', 'spotify_id', 'perf_playlist_0'),
            ('users', 'spotify_id', 'perf_test_user')
        ]
        
        for table, column, value in indexed_columns:
            times = []
            for _ in range(10):
                start_time = time.time()
                if table == 'songs':
                    result = Song.query.filter_by(spotify_id=value).first()
                elif table == 'playlists':
                    result = Playlist.query.filter_by(spotify_id=value).first()
                elif table == 'users':
                    result = User.query.filter_by(spotify_id=value).first()
                times.append(time.time() - start_time)
            
            results[f'{table}_{column}'] = {
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times)
            }
        
        return results
    
    def _assess_query_monitoring(self) -> Dict[str, Any]:
        """Assess query monitoring functionality."""
        print("📊 Assessing query monitoring...")
        
        # Execute some queries to generate statistics
        playlists = Playlist.query.limit(5).all()
        songs = Song.query.filter(Song.artist.like('Test Artist%')).limit(10).all()
        
        # Get query statistics
        stats = get_query_statistics()
        
        return {
            'monitoring_enabled': self.app.config.get('SQLALCHEMY_RECORD_QUERIES', False),
            'slow_query_threshold': self.app.config.get('SLOW_QUERY_THRESHOLD', 0.5),
            'query_statistics': stats
        }
    
    def _benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage for large operations."""
        print("💾 Benchmarking memory usage...")
        
        results = {}
        
        # Test large batch operation
        start_time = time.time()
        large_song_data = [
            {
                'spotify_id': f'memory_test_{i}',
                'title': f'Memory Test Song {i}',
                'artist': f'Memory Artist {i % 20}'
            }
            for i in range(200)
        ]
        
        created_songs = self.batch_service.create_songs_batch(large_song_data)
        creation_time = time.time() - start_time
        
        # Test large query
        start_time = time.time()
        queried_songs = Song.query.filter(Song.spotify_id.like('memory_test_%')).all()
        query_time = time.time() - start_time
        
        # Clean up
        for song in created_songs:
            db.session.delete(song)
        db.session.commit()
        
        results = {
            'large_batch_creation': {
                'items': 200,
                'time': creation_time,
                'time_per_item': creation_time / 200
            },
            'large_query': {
                'items': len(queried_songs),
                'time': query_time,
                'time_per_item': query_time / len(queried_songs) if queried_songs else 0
            }
        }
        
        return results
    
    def _benchmark_concurrent_access(self) -> Dict[str, Any]:
        """Benchmark concurrent database access."""
        print("🔄 Benchmarking concurrent access...")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def worker(worker_id):
            """Worker function for concurrent access test."""
            try:
                start_time = time.time()
                # Simulate typical operations
                playlists = Playlist.query.limit(3).all()
                for playlist in playlists:
                    songs = Song.query.join(PlaylistSong).filter(
                        PlaylistSong.playlist_id == playlist.id
                    ).limit(2).all()
                end_time = time.time()
                results_queue.put(('success', worker_id, end_time - start_time))
            except Exception as e:
                results_queue.put(('error', worker_id, str(e)))
        
        # Run concurrent workers
        threads = []
        start_time = time.time()
        
        for i in range(10):  # 10 concurrent workers
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        worker_times = []
        errors = []
        
        while not results_queue.empty():
            result = results_queue.get()
            if result[0] == 'success':
                worker_times.append(result[2])
            else:
                errors.append(result[2])
        
        return {
            'total_time': total_time,
            'worker_count': 10,
            'successful_workers': len(worker_times),
            'failed_workers': len(errors),
            'avg_worker_time': statistics.mean(worker_times) if worker_times else 0,
            'min_worker_time': min(worker_times) if worker_times else 0,
            'max_worker_time': max(worker_times) if worker_times else 0,
            'errors': errors
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of all benchmark results."""
        summary = {
            'overall_status': 'healthy',
            'key_metrics': {},
            'recommendations': []
        }
        
        # Extract key metrics
        if 'playlist_loading' in self.results:
            playlist_data = self.results['playlist_loading']
            if 'improvement_percent' in playlist_data:
                summary['key_metrics']['playlist_loading_improvement'] = f"{playlist_data['improvement_percent']:.1f}%"
        
        if 'batch_operations' in self.results:
            batch_data = self.results['batch_operations']
            if 'speedup_factor' in batch_data:
                summary['key_metrics']['batch_speedup'] = f"{batch_data['speedup_factor']:.1f}x"
        
        if 'song_queries' in self.results:
            song_data = self.results['song_queries']
            if 'indexed_lookup' in song_data:
                summary['key_metrics']['indexed_lookup_time'] = f"{song_data['indexed_lookup']['avg_time']*1000:.1f}ms"
        
        # Generate recommendations
        if 'connection_pool' in self.results:
            pool_health = self.results['connection_pool']['health_status']
            if pool_health.get('status') != 'healthy':
                summary['recommendations'].extend(pool_health.get('recommendations', []))
        
        return summary
    
    def _save_results(self, output_file: str):
        """Save results to a JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"📄 Results saved to {output_file}")
    
    def _print_summary(self):
        """Print a formatted summary of results."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE ASSESSMENT SUMMARY")
        print("=" * 60)
        
        summary = self.results.get('summary', {})
        
        print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
        print("\nKey Metrics:")
        for metric, value in summary.get('key_metrics', {}).items():
            print(f"  • {metric.replace('_', ' ').title()}: {value}")
        
        if summary.get('recommendations'):
            print("\nRecommendations:")
            for rec in summary['recommendations']:
                print(f"  • {rec}")
        
        print("\n" + "=" * 60)


def main():
    """Main function to run the performance assessment."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run database performance assessment')
    parser.add_argument('--output', '-o', help='Output file for results (JSON format)')
    parser.add_argument('--config', '-c', default='development', help='Flask configuration to use')
    
    args = parser.parse_args()
    
    # Create app with specified config
    app = create_app(args.config)
    
    # Run assessment
    assessment = PerformanceAssessment(app)
    results = assessment.run_assessment(args.output)
    
    return results


if __name__ == '__main__':
    main() 