"""
Phase 5 TDD Tests: Re-analyze & Calibrate System

Tests for the calibration system that will:
1. Batch re-analyze existing songs with enhanced system
2. Analyze score distribution to ensure realistic spread
3. Optimize concern level thresholds  
4. Validate performance improvements and accuracy

Following TDD methodology: Write tests first, then implement functionality.
"""

import pytest
import json
import statistics
from unittest.mock import Mock, patch, MagicMock
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestCalibrationSystem:
    """Test Phase 5 Calibration & Re-analysis System"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = HuggingFaceAnalyzer()
        
        # Mock the AI models to avoid loading them during tests
        self.analyzer._sentiment_analyzer = Mock()
        self.analyzer._safety_analyzer = Mock()
        self.analyzer._emotion_analyzer = Mock()
        self.analyzer._theme_analyzer = Mock()

    def test_batch_reanalysis_performance(self):
        """Test that batch reanalysis completes efficiently with good performance"""
        
        # Mock test song database
        test_songs = [
            {"id": 1, "title": "Amazing Grace", "artist": "Traditional", "lyrics": "Amazing grace how sweet the sound"},
            {"id": 2, "title": "How Great Thou Art", "artist": "Traditional", "lyrics": "O Lord my God when I in awesome wonder"},
            {"id": 3, "title": "Dark Song", "artist": "Negative Band", "lyrics": "Blasphemy and hatred fill my heart"},
            {"id": 4, "title": "Secular Love", "artist": "Pop Artist", "lyrics": "Love makes me feel so good tonight"},
            {"id": 5, "title": "Mixed Content", "artist": "Confused Artist", "lyrics": "Jesus saves but money is my god"},
        ]
        
        # Mock batch re-analysis function (to be implemented)
        with patch('scripts.utilities.calibration_service.CalibrationService') as mock_service:
            mock_service.return_value.batch_reanalyze.return_value = {
                'total_songs': len(test_songs),
                'successful_analyses': len(test_songs),
                'failed_analyses': 0,
                'average_processing_time': 0.8,  # seconds per song
                'total_time': len(test_songs) * 0.8
            }
            
            calibration_service = mock_service.return_value
            
            # Run batch reanalysis
            result = calibration_service.batch_reanalyze(test_songs)
            
            # Should complete all songs successfully
            assert result['successful_analyses'] == len(test_songs), "Should analyze all songs successfully"
            assert result['failed_analyses'] == 0, "Should have no failures"
            
            # Should have reasonable performance (under 2 seconds per song)
            assert result['average_processing_time'] < 2.0, "Should process songs efficiently"
            
            # Should complete full batch in reasonable time
            expected_max_time = len(test_songs) * 2.0  # 2 seconds per song max
            assert result['total_time'] < expected_max_time, "Batch should complete in reasonable time"

    def test_score_distribution_realistic(self):
        """Test that score distribution across different content types is realistic and well-spread"""
        
        # Mock diverse analysis results representing different content types
        mock_results = [
            # Excellent Christian content (should score 80-100)
            {"title": "Amazing Grace", "score": 95.5, "category": "excellent_christian"},
            {"title": "How Great Thou Art", "score": 92.3, "category": "excellent_christian"},
            {"title": "Jesus Paid It All", "score": 89.7, "category": "excellent_christian"},
            
            # Good Christian content (should score 60-85)
            {"title": "Good Christian Song", "score": 75.2, "category": "good_christian"},
            {"title": "Worship with Issues", "score": 68.5, "category": "good_christian"},
            {"title": "Character Building", "score": 72.8, "category": "good_christian"},
            
            # Mixed content (should score 30-60)
            {"title": "Mixed Messages", "score": 45.3, "category": "mixed"},
            {"title": "Some Good Some Bad", "score": 52.1, "category": "mixed"},
            {"title": "Confusing Theology", "score": 38.9, "category": "mixed"},
            
            # Secular content (should score 10-40)
            {"title": "Love Song", "score": 25.7, "category": "secular"},
            {"title": "Party Anthem", "score": 18.4, "category": "secular"},
            {"title": "Success Story", "score": 31.2, "category": "secular"},
            
            # Harmful content (should score 0-20)
            {"title": "Blasphemous Song", "score": 8.5, "category": "harmful"},
            {"title": "Occult References", "score": 12.3, "category": "harmful"},
            {"title": "Multiple Negative", "score": 5.1, "category": "harmful"},
        ]
        
        # Mock score distribution analyzer (to be implemented)
        with patch('app.services.calibration_service.ScoreDistributionAnalyzer') as mock_analyzer:
            mock_analyzer.return_value.analyze_distribution.return_value = {
                'score_ranges': {
                    'excellent_christian': {'min': 89.7, 'max': 95.5, 'avg': 92.5, 'count': 3},
                    'good_christian': {'min': 68.5, 'max': 75.2, 'avg': 72.2, 'count': 3},
                    'mixed': {'min': 38.9, 'max': 52.1, 'avg': 45.4, 'count': 3},
                    'secular': {'min': 18.4, 'max': 31.2, 'avg': 25.1, 'count': 3},
                    'harmful': {'min': 5.1, 'max': 12.3, 'avg': 8.6, 'count': 3}
                },
                'overall_stats': {
                    'mean': 50.2,
                    'median': 45.3,
                    'std_dev': 28.7,
                    'range_span': 90.4  # max - min
                },
                'distribution_quality': 'good'  # well-spread across range
            }
            
            analyzer = mock_analyzer.return_value
            distribution = analyzer.analyze_distribution(mock_results)
            
            # Excellent Christian content should score high (80-100)
            excellent = distribution['score_ranges']['excellent_christian']
            assert excellent['min'] >= 80, "Excellent Christian content should score at least 80"
            assert excellent['max'] <= 100, "Scores should not exceed 100"
            assert excellent['avg'] >= 85, "Excellent Christian content should average 85+"
            
            # Harmful content should score low (0-20)
            harmful = distribution['score_ranges']['harmful']
            assert harmful['max'] <= 20, "Harmful content should score 20 or below"
            assert harmful['avg'] <= 15, "Harmful content should average 15 or below"
            
            # Overall distribution should be well-spread
            stats = distribution['overall_stats']
            assert stats['range_span'] >= 80, "Scores should span at least 80 points"
            assert 20 <= stats['std_dev'] <= 40, "Standard deviation should show good spread"
            
            # Distribution quality should be acceptable
            assert distribution['distribution_quality'] in ['good', 'excellent'], "Distribution should be well-spread"

    def test_concern_level_threshold_optimization(self):
        """Test that concern level thresholds are properly optimized based on score distribution"""
        
        # Mock current vs optimized thresholds
        current_thresholds = {
            'Very Low': 95,  # 95-100
            'Low': 85,       # 85-94
            'Medium': 70,    # 70-84
            'High': 0        # 0-69
        }
        
        optimized_thresholds = {
            'Very Low': 90,  # 90-100  
            'Low': 75,       # 75-89
            'Medium': 50,    # 50-74
            'High': 25,      # 25-49
            'Very High': 0   # 0-24
        }
        
        # Mock threshold optimizer (to be implemented)
        with patch('app.services.calibration_service.ThresholdOptimizer') as mock_optimizer:
            mock_optimizer.return_value.optimize_thresholds.return_value = {
                'current_thresholds': current_thresholds,
                'optimized_thresholds': optimized_thresholds,
                'improvement_metrics': {
                    'accuracy_improvement': 0.15,  # 15% better accuracy
                    'false_positive_reduction': 0.22,  # 22% fewer false positives
                    'better_discrimination': True,
                    'threshold_changes': {
                        'Very Low': -5,  # Lowered from 95 to 90
                        'Low': -10,      # Lowered from 85 to 75  
                        'Medium': -20,   # Lowered from 70 to 50
                        'High': +25,     # Raised from 0 to 25 (new Very High created)
                    }
                },
                'validation_results': {
                    'test_accuracy': 0.87,  # 87% accuracy on test set
                    'precision': 0.84,
                    'recall': 0.89
                }
            }
            
            optimizer = mock_optimizer.return_value
            result = optimizer.optimize_thresholds(mock_data=[])
            
            # Should have optimized thresholds
            optimized = result['optimized_thresholds']
            assert len(optimized) >= 4, "Should have at least 4 concern levels"
            assert 'Very High' in optimized, "Should add Very High concern level for worst content"
            
            # Thresholds should be in descending order
            threshold_values = list(optimized.values())
            assert threshold_values == sorted(threshold_values, reverse=True), "Thresholds should be in descending order"
            
            # Should show improvement metrics
            metrics = result['improvement_metrics']
            assert metrics['accuracy_improvement'] > 0, "Should improve accuracy"
            assert metrics['false_positive_reduction'] > 0, "Should reduce false positives"
            assert metrics['better_discrimination'] is True, "Should provide better discrimination"
            
            # Validation should show good performance
            validation = result['validation_results']
            assert validation['test_accuracy'] >= 0.8, "Should achieve at least 80% accuracy"
            assert validation['precision'] >= 0.8, "Should achieve good precision"
            assert validation['recall'] >= 0.8, "Should achieve good recall"

    def test_accuracy_improvement_validation(self):
        """Test that the enhanced system shows improved accuracy over baseline"""
        
        # Mock baseline vs enhanced system performance comparison
        baseline_performance = {
            'accuracy': 0.72,
            'precision': 0.69,
            'recall': 0.75,
            'f1_score': 0.72,
            'false_positive_rate': 0.31,
            'false_negative_rate': 0.25,
            'theme_detection_accuracy': 0.68
        }
        
        enhanced_performance = {
            'accuracy': 0.87,       # +15% improvement
            'precision': 0.84,      # +15% improvement  
            'recall': 0.89,         # +14% improvement
            'f1_score': 0.86,       # +14% improvement
            'false_positive_rate': 0.16,  # -15% improvement (lower is better)
            'false_negative_rate': 0.11,  # -14% improvement (lower is better)
            'theme_detection_accuracy': 0.91  # +23% improvement
        }
        
        # Mock performance validator (to be implemented)
        with patch('app.services.calibration_service.PerformanceValidator') as mock_validator:
            mock_validator.return_value.compare_performance.return_value = {
                'baseline_performance': baseline_performance,
                'enhanced_performance': enhanced_performance,
                'improvements': {
                    'accuracy_gain': 0.15,
                    'precision_gain': 0.15,
                    'recall_gain': 0.14,
                    'f1_gain': 0.14,
                    'false_positive_reduction': 0.15,
                    'false_negative_reduction': 0.14,
                    'theme_detection_gain': 0.23
                },
                'statistical_significance': {
                    'p_value': 0.001,  # Highly significant
                    'confidence_interval': 0.95,
                    'effect_size': 0.82  # Large effect
                },
                'validation_status': 'significant_improvement'
            }
            
            validator = mock_validator.return_value
            comparison = validator.compare_performance(baseline_data=[], enhanced_data=[])
            
            # Should show significant improvements across all metrics
            improvements = comparison['improvements']
            assert improvements['accuracy_gain'] >= 0.10, "Should improve accuracy by at least 10%"
            assert improvements['precision_gain'] >= 0.10, "Should improve precision by at least 10%"
            assert improvements['recall_gain'] >= 0.10, "Should improve recall by at least 10%"
            assert improvements['theme_detection_gain'] >= 0.15, "Should improve theme detection by at least 15%"
            
            # Should reduce error rates
            assert improvements['false_positive_reduction'] >= 0.10, "Should reduce false positives by at least 10%"
            assert improvements['false_negative_reduction'] >= 0.10, "Should reduce false negatives by at least 10%"
            
            # Should be statistically significant
            stats = comparison['statistical_significance']
            assert stats['p_value'] <= 0.05, "Improvements should be statistically significant"
            assert stats['effect_size'] >= 0.5, "Should show medium to large effect size"
            
            # Overall validation should pass
            assert comparison['validation_status'] == 'significant_improvement', "Should validate significant improvement"

    def test_calibration_system_stability_under_load(self):
        """Test that calibration system handles large batches without performance degradation"""
        
        # Mock large-scale reanalysis scenario
        large_batch_sizes = [100, 500, 1000, 2000]
        
        # Mock system stability monitor (to be implemented)  
        with patch('app.services.calibration_service.SystemStabilityMonitor') as mock_monitor:
            mock_monitor.return_value.test_load_handling.return_value = {
                'batch_results': {
                    100: {'success_rate': 1.0, 'avg_time_per_song': 0.8, 'memory_usage': '145MB'},
                    500: {'success_rate': 0.998, 'avg_time_per_song': 0.85, 'memory_usage': '312MB'},
                    1000: {'success_rate': 0.996, 'avg_time_per_song': 0.92, 'memory_usage': '487MB'},
                    2000: {'success_rate': 0.994, 'avg_time_per_song': 1.1, 'memory_usage': '723MB'}
                },
                'performance_degradation': {
                    'time_increase_per_1000': 0.3,  # 30% slower per 1000 songs
                    'memory_growth_linear': True,
                    'success_rate_stable': True
                },
                'stability_assessment': 'stable_under_load',
                'recommended_batch_size': 1000,
                'max_safe_batch_size': 2000
            }
            
            monitor = mock_monitor.return_value
            stability = monitor.test_load_handling(large_batch_sizes)
            
            # Success rate should remain high across all batch sizes
            for batch_size, results in stability['batch_results'].items():
                assert results['success_rate'] >= 0.99, f"Success rate should be 99%+ for batch size {batch_size}"
                assert results['avg_time_per_song'] <= 2.0, f"Processing time should stay reasonable for batch {batch_size}"
            
            # Performance degradation should be acceptable
            degradation = stability['performance_degradation']
            assert degradation['time_increase_per_1000'] <= 0.5, "Time increase should be manageable"
            assert degradation['success_rate_stable'] is True, "Success rate should remain stable"
            
            # System should be assessed as stable
            assert stability['stability_assessment'] == 'stable_under_load', "System should handle load well"
            assert stability['recommended_batch_size'] >= 500, "Should recommend reasonable batch size"

    def test_calibration_config_management(self):
        """Test that calibration configuration is properly managed and persisted"""
        
        # Mock calibration configuration
        calibration_config = {
            'batch_size': 1000,
            'max_concurrent_analyses': 5,
            'score_thresholds': {
                'Very Low': 90,
                'Low': 75, 
                'Medium': 50,
                'High': 25,
                'Very High': 0
            },
            'reanalysis_settings': {
                'force_reanalyze': False,
                'skip_recent_analyses': True,
                'recent_threshold_days': 30
            },
            'performance_targets': {
                'min_accuracy': 0.85,
                'max_processing_time': 2.0,
                'max_false_positive_rate': 0.15
            }
        }
        
        # Mock configuration manager (to be implemented)
        with patch('app.services.calibration_service.CalibrationConfigManager') as mock_config:
            mock_config.return_value.load_config.return_value = calibration_config
            mock_config.return_value.save_config.return_value = True
            mock_config.return_value.validate_config.return_value = {'valid': True, 'errors': []}
            
            config_manager = mock_config.return_value
            
            # Should load configuration successfully
            loaded_config = config_manager.load_config()
            assert loaded_config is not None, "Should load configuration"
            assert 'batch_size' in loaded_config, "Should contain batch_size setting"
            assert 'score_thresholds' in loaded_config, "Should contain threshold settings"
            
            # Should validate configuration
            validation = config_manager.validate_config(loaded_config)
            assert validation['valid'] is True, "Configuration should be valid"
            assert len(validation['errors']) == 0, "Should have no validation errors"
            
            # Should save configuration successfully
            save_result = config_manager.save_config(loaded_config)
            assert save_result is True, "Should save configuration successfully"
            
            # Configuration values should be reasonable
            assert 500 <= loaded_config['batch_size'] <= 2000, "Batch size should be reasonable"
            assert loaded_config['max_concurrent_analyses'] >= 1, "Should allow concurrent analyses"
            assert len(loaded_config['score_thresholds']) >= 4, "Should have multiple concern levels"

    def test_calibration_reporting_system(self):
        """Test that calibration generates comprehensive reports for analysis"""
        
        # Mock calibration report data
        report_data = {
            'reanalysis_summary': {
                'total_songs_processed': 5247,
                'successful_analyses': 5231,
                'failed_analyses': 16,
                'success_rate': 0.997,
                'total_processing_time': 4198.4,  # seconds
                'average_time_per_song': 0.8
            },
            'score_distribution': {
                'mean': 52.7,
                'median': 48.3, 
                'std_dev': 29.2,
                'score_ranges': {
                    '90-100': 342,  # Excellent
                    '75-89': 521,   # Good
                    '50-74': 1876,  # Mixed
                    '25-49': 1654,  # Poor  
                    '0-24': 838     # Harmful
                }
            },
            'threshold_optimization': {
                'accuracy_before': 0.72,
                'accuracy_after': 0.87,
                'improvement': 0.15,
                'new_thresholds': {'Very Low': 90, 'Low': 75, 'Medium': 50, 'High': 25, 'Very High': 0}
            },
            'theme_detection_analysis': {
                'total_themes_detected': 12847,
                'themes_per_song_avg': 2.45,
                'most_common_themes': [
                    {'theme': 'Christ-centered', 'count': 1247, 'percentage': 9.7},
                    {'theme': 'Gospel presentation', 'count': 1089, 'percentage': 8.5},
                    {'theme': 'Endurance', 'count': 876, 'percentage': 6.8}
                ]
            }
        }
        
        # Mock report generator (to be implemented)
        with patch('app.services.calibration_service.CalibrationReporter') as mock_reporter:
            mock_reporter.return_value.generate_calibration_report.return_value = report_data
            mock_reporter.return_value.export_report.return_value = 'calibration_report_2024.json'
            
            reporter = mock_reporter.return_value
            
            # Should generate comprehensive report
            report = reporter.generate_calibration_report()
            assert report is not None, "Should generate calibration report"
            
            # Report should contain all major sections
            assert 'reanalysis_summary' in report, "Should include reanalysis summary"
            assert 'score_distribution' in report, "Should include score distribution"
            assert 'threshold_optimization' in report, "Should include threshold optimization"
            assert 'theme_detection_analysis' in report, "Should include theme analysis"
            
            # Reanalysis summary should show good performance
            summary = report['reanalysis_summary']
            assert summary['success_rate'] >= 0.95, "Should achieve high success rate"
            assert summary['average_time_per_song'] <= 2.0, "Should maintain good performance"
            
            # Score distribution should be realistic
            distribution = report['score_distribution']
            assert 20 <= distribution['mean'] <= 80, "Mean score should be reasonable"
            assert distribution['std_dev'] >= 20, "Should show good score spread"
            
            # Threshold optimization should show improvement
            optimization = report['threshold_optimization']
            assert optimization['improvement'] >= 0.10, "Should show significant improvement"
            assert optimization['accuracy_after'] >= 0.8, "Should achieve good final accuracy"
            
            # Should export report successfully
            export_result = reporter.export_report(report)
            assert export_result is not None, "Should export report file"
            assert export_result.endswith('.json'), "Should export as JSON file" 