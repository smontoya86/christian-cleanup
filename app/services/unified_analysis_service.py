"""
Unified Analysis Service
Consolidates all analysis functionality into one comprehensive service.
Always performs full biblical analysis - no half-measures.
"""

from flask import current_app
import logging
import json
import time
import hashlib
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..extensions import rq, db
from ..models import Song, AnalysisResult, User, Playlist, PlaylistSong
from ..utils.analysis_enhanced import EnhancedSongAnalyzer
from ..utils.lyrics import LyricsFetcher
from sqlalchemy import and_, or_

# Quality Assurance System Components
class AnalysisQualityLevel(Enum):
    """Analysis quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"

@dataclass
class QualityMetrics:
    """Quality metrics for analysis validation"""
    completeness_score: float  # 0.0 - 1.0
    confidence_score: float    # 0.0 - 1.0
    consistency_score: float   # 0.0 - 1.0
    overall_quality: AnalysisQualityLevel
    missing_fields: List[str]
    validation_errors: List[str]
    recommendations: List[str]

logger = logging.getLogger(__name__)

# Global cache for analysis results to avoid re-analyzing identical songs
_analysis_cache = {}
_lyrics_cache = {}

class UnifiedAnalysisService:
    """
    Unified service for all Christian song analysis.
    This service replaces all fragmented analysis services and always performs comprehensive analysis.
    """
    
    def __init__(self):
        self.analyzer = None
        self.lyrics_fetcher = None
    
    def _get_song_cache_key(self, title: str, artist: str, is_explicit: bool) -> str:
        """Generate a cache key for a song based on title, artist, and explicit flag"""
        content = f"{title.lower().strip()}|{artist.lower().strip()}|{is_explicit}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _initialize_services(self, user_id: int = None):
        """Initialize analysis services if not already done"""
        if not self.analyzer:
            self.analyzer = EnhancedSongAnalyzer(user_id=user_id or 1)
        if not self.lyrics_fetcher:
            self.lyrics_fetcher = LyricsFetcher()
    
    def execute_comprehensive_analysis(self, song_id: int, user_id: int = None, force_reanalysis: bool = False) -> Optional[AnalysisResult]:
        """
        Execute comprehensive biblical analysis for a song with quality assurance.
        This is the ONLY analysis method - always performs full analysis.
        
        Args:
            song_id: ID of the song to analyze
            user_id: ID of the user requesting analysis
            force_reanalysis: Whether to force re-analysis even if cached
            
        Returns:
            AnalysisResult object if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            # Get song from database
            song = db.session.get(Song, song_id)
            if not song:
                logger.error(f"Song with ID {song_id} not found in database")
                return None
                
            song_title = song.title
            song_artist = song.artist
            is_explicit = song.explicit
            
            logger.info(f"🎵 Starting comprehensive biblical analysis for: '{song_title}' by {song_artist}")
            
            # Check cache first (unless force_reanalysis is True)
            cache_key = self._get_song_cache_key(song_title, song_artist, is_explicit)
            if not force_reanalysis and cache_key in _analysis_cache:
                cached_result = _analysis_cache[cache_key]
                logger.info(f"⚡ Using cached comprehensive analysis for: {song_title}")
                
                # Clear any existing analysis results for this song
                existing_results = AnalysisResult.query.filter_by(song_id=song_id).all()
                for existing_result in existing_results:
                    db.session.delete(existing_result)
                
                # Create AnalysisResult from cached data with ALL comprehensive fields
                analysis_result = self._create_analysis_result_from_data(song_id, cached_result)
                
                # Save to database
                db.session.add(analysis_result)
                
                # Update song's last_analyzed timestamp
                song = db.session.get(Song, song_id)
                if song:
                    song.last_analyzed = datetime.utcnow()
                
                db.session.commit()
                
                elapsed = time.time() - start_time
                logger.info(f"✅ Cached comprehensive analysis completed for song ID {song_id} in {elapsed:.2f}s")
                return analysis_result
            
            # Initialize services
            self._initialize_services(user_id)
            
            # Always perform COMPREHENSIVE analysis - no lightweight or half-measures
            logger.info(f"🔬 Performing FULL COMPREHENSIVE biblical analysis for: {song_title}")
            
            # Prepare song data in the format expected by EnhancedSongAnalyzer
            song_data = {
                'title': song_title,
                'artist': song_artist,
                'explicit': is_explicit,
                'id': song_id
            }
            
            # COMPREHENSIVE ANALYSIS: Always fetch lyrics for complete analysis
            logger.info(f"🎵 Fetching lyrics for comprehensive analysis: {song_title} by {song_artist}")
            start_fetch = time.time()
            
            if not self.lyrics_fetcher:
                self._initialize_services(user_id)
            lyrics = self.lyrics_fetcher.fetch_lyrics(song_title, song_artist)
            
            fetch_time = time.time() - start_fetch
            if lyrics:
                logger.info(f"✅ Lyrics fetched successfully in {fetch_time:.2f}s ({len(lyrics)} characters)")
            else:
                logger.warning(f"⚠️ No lyrics found for {song_title} by {song_artist} after {fetch_time:.2f}s - analysis will be limited")
            
            result = self.analyzer.analyze_song(
                song_data=song_data,
                lyrics=lyrics  # Now includes actual lyrics for comprehensive analysis
            )
            
            if not result:
                logger.error(f"❌ Comprehensive analysis failed for song ID {song_id}: No result returned")
                return None
            
            # QUALITY ASSURANCE: Validate analysis result quality
            logger.info(f"🔍 Performing quality assurance validation for song ID {song_id}")
            quality_metrics = self._validate_analysis_result(result, song_id)
            
            # Handle different quality levels
            if quality_metrics.overall_quality == AnalysisQualityLevel.FAILED:
                logger.error(f"❌ Analysis quality validation FAILED for song ID {song_id}")
                logger.error(f"   Errors: {'; '.join(quality_metrics.validation_errors)}")
                
                # Queue for immediate reanalysis with high priority
                self._queue_for_reanalysis(
                    song_id, 
                    f"Quality validation failed: {'; '.join(quality_metrics.validation_errors)}", 
                    priority='high',
                    delay_seconds=60  # Retry in 1 minute
                )
                return None
                
            elif quality_metrics.overall_quality == AnalysisQualityLevel.POOR:
                logger.warning(f"⚠️ Analysis quality is POOR for song ID {song_id} - flagging for review")
                
                # Flag for manual review and queue for reanalysis
                self._flag_for_manual_review(song_id, "Poor analysis quality detected", quality_metrics)
                self._queue_for_reanalysis(
                    song_id, 
                    "Poor analysis quality - automatic retry", 
                    priority='default',
                    delay_seconds=300  # Retry in 5 minutes
                )
                
            elif quality_metrics.overall_quality == AnalysisQualityLevel.ACCEPTABLE:
                logger.info(f"⚠️ Analysis quality is ACCEPTABLE for song ID {song_id} - proceeding with caution")
                
                # Log recommendations for improvement
                if quality_metrics.recommendations:
                    logger.info(f"💡 Quality improvement recommendations: {'; '.join(quality_metrics.recommendations)}")
                    
            else:  # GOOD or EXCELLENT
                logger.info(f"✅ Analysis quality is {quality_metrics.overall_quality.value.upper()} for song ID {song_id}")
            
            # Validate that we got comprehensive results (basic validation)
            if not self._validate_comprehensive_analysis(result):
                logger.warning(f"⚠️ Analysis result appears incomplete for song ID {song_id}, but proceeding")
            
            # Cache the result for future identical songs
            _analysis_cache[cache_key] = result
            
            # Limit cache size to prevent memory issues
            if len(_analysis_cache) > 1000:
                oldest_keys = list(_analysis_cache.keys())[:100]
                for key in oldest_keys:
                    del _analysis_cache[key]
            
            # Clear any existing analysis results for this song (for re-analysis scenarios)
            existing_results = AnalysisResult.query.filter_by(song_id=song_id).all()
            for existing_result in existing_results:
                db.session.delete(existing_result)
            
            # Create new AnalysisResult with ALL comprehensive data
            analysis_result = self._create_analysis_result_from_data(song_id, result)
            
            # Add quality metrics to the analysis result explanation if quality is not excellent
            if quality_metrics.overall_quality != AnalysisQualityLevel.EXCELLENT:
                quality_info = f"\n\n[QUALITY ASSESSMENT: {quality_metrics.overall_quality.value.upper()}]\n"
                quality_info += f"Completeness: {quality_metrics.completeness_score:.2f} | "
                quality_info += f"Confidence: {quality_metrics.confidence_score:.2f} | "
                quality_info += f"Consistency: {quality_metrics.consistency_score:.2f}"
                
                if quality_metrics.recommendations:
                    quality_info += f"\nRecommendations: {'; '.join(quality_metrics.recommendations)}"
                    
                analysis_result.explanation = (analysis_result.explanation or "") + quality_info
            
            # Save to database
            db.session.add(analysis_result)
            
            # Update song's last_analyzed timestamp
            song = db.session.get(Song, song_id)
            if song:
                song.last_analyzed = datetime.utcnow()
                
            db.session.commit()
            
            elapsed = time.time() - start_time
            
            # Log comprehensive analysis completion with quality metrics
            self._log_analysis_completion_with_quality(song_id, result, quality_metrics, elapsed)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive analysis for song '{song_title if 'song_title' in locals() else 'Unknown'}' (ID: {song_id}): {str(e)}")
            # Log traceback for debugging
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            
            # For unexpected errors, queue for reanalysis
            try:
                self._queue_for_reanalysis(
                    song_id, 
                    f"Unexpected error during analysis: {str(e)}", 
                    priority='low',
                    delay_seconds=600  # Retry in 10 minutes
                )
            except Exception as queue_error:
                logger.error(f"Failed to queue reanalysis after error: {str(queue_error)}")
            
            raise e
    
    def _create_analysis_result_from_data(self, song_id: int, result: Dict[str, Any]) -> AnalysisResult:
        """Create AnalysisResult with comprehensive data mapping"""
        return AnalysisResult(
            song_id=song_id,
            status=AnalysisResult.STATUS_COMPLETED,
            score=result.get('christian_score', 85),
            concern_level=result.get('concern_level', 'Low'),  # FIXED: correct field mapping
            # Map ALL comprehensive analysis fields to database with correct field names
            purity_flags_details=json.dumps(result.get('purity_flags', [])),
            positive_themes_identified=json.dumps(result.get('positive_themes', [])),
            biblical_themes=json.dumps(result.get('biblical_themes', [])),
            supporting_scripture=json.dumps(result.get('supporting_scripture', {})),
            concerns=json.dumps(result.get('detailed_concerns', [])),
            explanation=result.get('explanation', ''),
            analyzed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
    
    def _validate_comprehensive_analysis(self, result: Dict[str, Any]) -> bool:
        """Validate that analysis result contains comprehensive biblical data"""
        required_fields = [
            'christian_score',
            'concern_level', 
            'biblical_themes',
            'supporting_scripture',
            'explanation'
        ]
        
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required analysis field: {field}")
                return False
        
        # Check for substantial content (Note: biblical themes might be empty for non-Christian songs)
        biblical_themes = result.get('biblical_themes', [])
        supporting_scripture = result.get('supporting_scripture', {})
        
        # For validation, we'll accept that non-Christian songs may have empty biblical content
        logger.info(f"Analysis validation: {len(biblical_themes)} biblical themes, {len(supporting_scripture)} scripture references")
        
        return True
    
    def _validate_analysis_result(self, result: Dict[str, Any], song_id: int = None) -> QualityMetrics:
        """
        Comprehensive validation and quality assurance for analysis results.
        
        Args:
            result: Analysis result dictionary to validate
            song_id: Optional song ID for logging purposes
            
        Returns:
            QualityMetrics object with detailed quality assessment
        """
        missing_fields = []
        validation_errors = []
        recommendations = []
        
        # Define required and optional fields with their validation criteria
        required_fields = {
            'christian_score': {'type': (int, float), 'range': (0, 100)},
            'concern_level': {'type': str, 'values': ['Very Low', 'Low', 'Moderate', 'Medium', 'High', 'Very High']},
            'biblical_themes': {'type': list},
            'supporting_scripture': {'type': dict},
            'explanation': {'type': str, 'min_length': 10}
        }
        
        desirable_fields = {
            'positive_themes': {'type': list},
            'purity_flags': {'type': list},
            'detailed_concerns': {'type': list},
            'positive_score_bonus': {'type': (int, float), 'range': (0, 200)},
            'analysis_version': {'type': str}
        }
        
        # Check required fields
        completeness_score = 0.0
        total_required = len(required_fields)
        
        for field, criteria in required_fields.items():
            if field not in result:
                missing_fields.append(field)
                validation_errors.append(f"Missing required field: {field}")
            else:
                value = result[field]
                
                # Type validation
                if not isinstance(value, criteria['type']):
                    validation_errors.append(f"Field '{field}' has incorrect type. Expected {criteria['type']}, got {type(value)}")
                    continue
                
                # Range validation for numeric fields
                if 'range' in criteria and isinstance(value, (int, float)):
                    min_val, max_val = criteria['range']
                    if not (min_val <= value <= max_val):
                        validation_errors.append(f"Field '{field}' value {value} outside valid range {criteria['range']}")
                        continue
                
                # Values validation for string fields
                if 'values' in criteria and isinstance(value, str):
                    if value not in criteria['values']:
                        validation_errors.append(f"Field '{field}' has invalid value '{value}'. Valid values: {criteria['values']}")
                        continue
                
                # Minimum length validation for string fields
                if 'min_length' in criteria and isinstance(value, str):
                    if len(value.strip()) < criteria['min_length']:
                        validation_errors.append(f"Field '{field}' is too short. Minimum length: {criteria['min_length']}")
                        continue
                
                # Field is valid
                completeness_score += 1.0
        
        # Check desirable fields (don't count against completeness but add to quality)
        desirable_present = 0
        for field, criteria in desirable_fields.items():
            if field in result and isinstance(result[field], criteria['type']):
                desirable_present += 1
                completeness_score += 0.1  # Bonus for desirable fields
        
        # Normalize completeness score
        completeness_score = min(1.0, completeness_score / total_required)
        
        # Calculate confidence score based on data quality
        confidence_score = 0.0
        
        # Score quality metrics
        if 'christian_score' in result:
            score = result['christian_score']
            if isinstance(score, (int, float)) and 0 <= score <= 100:
                confidence_score += 0.3
        
        if 'biblical_themes' in result:
            themes = result['biblical_themes']
            if isinstance(themes, list) and len(themes) > 0:
                confidence_score += 0.3
                # Bonus for theme diversity
                if len(themes) >= 3:
                    confidence_score += 0.1
        
        if 'supporting_scripture' in result:
            scripture = result['supporting_scripture']
            if isinstance(scripture, dict) and len(scripture) > 0:
                confidence_score += 0.3
        
        if 'explanation' in result:
            explanation = result['explanation']
            if isinstance(explanation, str) and len(explanation.strip()) >= 50:
                confidence_score += 0.1
        
        confidence_score = min(1.0, confidence_score)
        
        # Calculate consistency score (internal logic validation)
        consistency_score = 1.0
        
        # Check score-concern level consistency
        if 'christian_score' in result and 'concern_level' in result:
            score = result['christian_score']
            concern = result['concern_level']
            
            expected_concern = self._get_expected_concern_level(score)
            if concern != expected_concern:
                consistency_score -= 0.1  # Reduced from 0.2 to 0.1 for less strict penalty
                validation_errors.append(f"Inconsistent score ({score}) and concern level ({concern}). Expected: {expected_concern}")
        
        # Check biblical themes vs score consistency
        if 'biblical_themes' in result and 'christian_score' in result:
            themes_count = len(result['biblical_themes']) if isinstance(result['biblical_themes'], list) else 0
            score = result['christian_score']
            
            if score >= 80 and themes_count == 0:
                consistency_score -= 0.2  # Reduced from 0.3 to 0.2
                validation_errors.append("High Christian score but no biblical themes detected")
            elif score <= 30 and themes_count > 2:
                consistency_score -= 0.15  # Reduced from 0.2 to 0.15
                validation_errors.append("Low Christian score but many biblical themes detected")
        
        consistency_score = max(0.0, consistency_score)
        
        # Determine overall quality level
        overall_score = (completeness_score * 0.4) + (confidence_score * 0.4) + (consistency_score * 0.2)
        
        if overall_score >= 0.85 and len(validation_errors) == 0:
            overall_quality = AnalysisQualityLevel.EXCELLENT
        elif overall_score >= 0.75 and len(validation_errors) <= 1:
            overall_quality = AnalysisQualityLevel.GOOD
        elif overall_score >= 0.55 and len(validation_errors) <= 3:
            overall_quality = AnalysisQualityLevel.ACCEPTABLE
        elif overall_score >= 0.25:
            overall_quality = AnalysisQualityLevel.POOR
        else:
            overall_quality = AnalysisQualityLevel.FAILED
        
        # Generate recommendations
        if completeness_score < 0.8:
            recommendations.append("Ensure all required analysis fields are present")
        if confidence_score < 0.7:
            recommendations.append("Improve analysis depth and biblical content detection")
        if consistency_score < 0.8:
            recommendations.append("Review analysis logic for internal consistency")
        if len(missing_fields) > 0:
            recommendations.append(f"Add missing fields: {', '.join(missing_fields)}")
        
        # Log quality assessment
        if song_id:
            logger.info(f"🔍 Quality assessment for song {song_id}: {overall_quality.value} "
                       f"(completeness: {completeness_score:.2f}, confidence: {confidence_score:.2f}, "
                       f"consistency: {consistency_score:.2f})")
            
            if validation_errors:
                logger.warning(f"⚠️ Validation issues for song {song_id}: {'; '.join(validation_errors)}")
        
        return QualityMetrics(
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            consistency_score=consistency_score,
            overall_quality=overall_quality,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            recommendations=recommendations
        )
    
    def _get_expected_concern_level(self, score: int) -> str:
        """Get expected concern level based on Christian score"""
        if score >= 85:
            return 'Low'
        elif score >= 70:
            return 'Medium' 
        elif score >= 50:
            return 'High'
        else:
            return 'Very High'
    
    def _queue_for_reanalysis(self, song_id: int, reason: str, priority: str = 'low', 
                             delay_seconds: int = 300) -> bool:
        """
        Queue a song for reanalysis due to quality issues.
        
        Args:
            song_id: ID of song to reanalyze
            reason: Reason for reanalysis
            priority: Queue priority ('high', 'default', 'low')
            delay_seconds: Delay before reanalysis (default 5 minutes)
            
        Returns:
            True if successfully queued, False otherwise
        """
        try:
            logger.info(f"🔄 Queueing song {song_id} for reanalysis: {reason}")
            
            # Create reanalysis job with delay
            from ..extensions import rq
            
            # Use appropriate queue based on priority
            if priority == 'high':
                queue = rq.get_queue('high')
            elif priority == 'default':
                queue = rq.get_queue('default')
            else:
                queue = rq.get_queue('low')
            
            # Schedule reanalysis job
            job = queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                'app.services.unified_analysis_service.execute_comprehensive_analysis_task',
                song_id,
                user_id=None,
                force_reanalysis=True,
                reanalysis_reason=reason,
                job_timeout='300s',
                description=f"Reanalysis: {reason}"
            )
            
            if job:
                logger.info(f"✅ Reanalysis job {job.id} scheduled for song {song_id} in {delay_seconds}s")
                
                # Update song analysis status to indicate pending reanalysis
                song = db.session.get(Song, song_id)
                if song:
                    # Add or update analysis result to indicate reanalysis pending
                    existing_result = AnalysisResult.query.filter_by(song_id=song_id).first()
                    if existing_result:
                        existing_result.status = AnalysisResult.STATUS_PENDING
                        existing_result.explanation = f"Reanalysis scheduled: {reason}"
                    else:
                        new_result = AnalysisResult(
                            song_id=song_id,
                            status=AnalysisResult.STATUS_PENDING,
                            explanation=f"Reanalysis scheduled: {reason}",
                            created_at=datetime.utcnow()
                        )
                        db.session.add(new_result)
                    
                    db.session.commit()
                
                return True
            else:
                logger.error(f"❌ Failed to schedule reanalysis job for song {song_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error queueing reanalysis for song {song_id}: {str(e)}")
            traceback.print_exc()
            return False
    
    def _flag_for_manual_review(self, song_id: int, reason: str, quality_metrics: QualityMetrics) -> bool:
        """
        Flag a song for manual review when automated analysis is uncertain.
        
        Args:
            song_id: ID of song to flag
            reason: Reason for manual review
            quality_metrics: Quality assessment metrics
            
        Returns:
            True if successfully flagged, False otherwise
        """
        try:
            logger.warning(f"🚩 Flagging song {song_id} for manual review: {reason}")
            
            # Update analysis result with manual review flag
            existing_result = AnalysisResult.query.filter_by(song_id=song_id).first()
            if existing_result:
                # Add manual review information to explanation
                review_info = f"\n\n[MANUAL REVIEW REQUIRED]\nReason: {reason}\nQuality: {quality_metrics.overall_quality.value}\nIssues: {'; '.join(quality_metrics.validation_errors)}"
                existing_result.explanation = (existing_result.explanation or "") + review_info
                existing_result.status = AnalysisResult.STATUS_REQUIRES_REVIEW
            else:
                # Create new result with manual review flag
                new_result = AnalysisResult(
                    song_id=song_id,
                    status=AnalysisResult.STATUS_REQUIRES_REVIEW,
                    explanation=f"Manual review required: {reason}\nQuality: {quality_metrics.overall_quality.value}",
                    created_at=datetime.utcnow()
                )
                db.session.add(new_result)
            
            db.session.commit()
            
            # Log detailed quality metrics for manual review
            logger.warning(f"📊 Quality metrics for song {song_id}:")
            logger.warning(f"   - Completeness: {quality_metrics.completeness_score:.2f}")
            logger.warning(f"   - Confidence: {quality_metrics.confidence_score:.2f}")
            logger.warning(f"   - Consistency: {quality_metrics.consistency_score:.2f}")
            logger.warning(f"   - Missing fields: {quality_metrics.missing_fields}")
            logger.warning(f"   - Validation errors: {quality_metrics.validation_errors}")
            logger.warning(f"   - Recommendations: {quality_metrics.recommendations}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error flagging song {song_id} for manual review: {str(e)}")
            traceback.print_exc()
            return False
    
    def _log_analysis_completion(self, song_id: int, result: Dict[str, Any], elapsed: float):
        """Log detailed completion metrics for comprehensive analysis"""
        biblical_themes_count = len(result.get('biblical_themes', []))
        concerns_count = len(result.get('detailed_concerns', []))
        positive_themes_count = len(result.get('positive_themes', []))
        scripture_count = len(result.get('supporting_scripture', {}))
        
        logger.info(f"✅ COMPREHENSIVE biblical analysis completed for song ID {song_id}: "
                   f"Score={result.get('christian_score')}, Level={result.get('concern_level')}, "
                   f"Biblical Themes={biblical_themes_count}, Scripture References={scripture_count}, "
                   f"Concerns={concerns_count}, Positive Themes={positive_themes_count} in {elapsed:.2f}s")
    
    def _log_analysis_completion_with_quality(self, song_id: int, result: Dict[str, Any], 
                                            quality_metrics: QualityMetrics, elapsed: float):
        """Log comprehensive analysis completion with quality metrics"""
        biblical_themes_count = len(result.get('biblical_themes', []))
        concerns_count = len(result.get('detailed_concerns', []))
        positive_themes_count = len(result.get('positive_themes', []))
        scripture_count = len(result.get('supporting_scripture', {}))
        
        # Base completion log
        logger.info(f"✅ COMPREHENSIVE biblical analysis completed for song ID {song_id}: "
                   f"Score={result.get('christian_score')}, Level={result.get('concern_level')}, "
                   f"Biblical Themes={biblical_themes_count}, Scripture References={scripture_count}, "
                   f"Concerns={concerns_count}, Positive Themes={positive_themes_count} in {elapsed:.2f}s")
        
        # Quality metrics log
        logger.info(f"📊 QUALITY METRICS for song ID {song_id}: "
                   f"Overall={quality_metrics.overall_quality.value.upper()}, "
                   f"Completeness={quality_metrics.completeness_score:.2f}, "
                   f"Confidence={quality_metrics.confidence_score:.2f}, "
                   f"Consistency={quality_metrics.consistency_score:.2f}")
        
        # Log quality issues if any
        if quality_metrics.validation_errors:
            logger.warning(f"⚠️ Quality validation errors for song ID {song_id}: {'; '.join(quality_metrics.validation_errors)}")
        
        if quality_metrics.missing_fields:
            logger.warning(f"⚠️ Missing analysis fields for song ID {song_id}: {', '.join(quality_metrics.missing_fields)}")
        
        if quality_metrics.recommendations:
            logger.info(f"💡 Quality improvement recommendations for song ID {song_id}: {'; '.join(quality_metrics.recommendations)}")
        
        # Overall quality assessment
        if quality_metrics.overall_quality == AnalysisQualityLevel.EXCELLENT:
            logger.info(f"🌟 EXCELLENT analysis quality achieved for song ID {song_id}")
        elif quality_metrics.overall_quality == AnalysisQualityLevel.GOOD:
            logger.info(f"✅ GOOD analysis quality achieved for song ID {song_id}")
        elif quality_metrics.overall_quality == AnalysisQualityLevel.ACCEPTABLE:
            logger.info(f"⚠️ ACCEPTABLE analysis quality for song ID {song_id} - room for improvement")
        elif quality_metrics.overall_quality == AnalysisQualityLevel.POOR:
            logger.warning(f"🔴 POOR analysis quality for song ID {song_id} - requires attention")
        else:  # FAILED
            logger.error(f"❌ FAILED analysis quality for song ID {song_id} - critical issues detected")
    
    def enqueue_analysis_job(self, song_id: int, user_id: int = None, priority: str = 'default') -> Optional[Any]:
        """
        Enqueue a comprehensive analysis task to be processed by RQ worker.
        
        Args:
            song_id: ID of the song to analyze
            user_id: ID of the user requesting analysis
            priority: Job priority ('high', 'default', 'low')
            
        Returns:
            Job object if enqueued successfully, None otherwise
        """
        try:
            # Ensure environment variables are set
            import os
            if 'LYRICSGENIUS_API_KEY' not in os.environ and 'LYRICSGENIUS_API_KEY' in current_app.config:
                os.environ['LYRICSGENIUS_API_KEY'] = current_app.config['LYRICSGENIUS_API_KEY']
            if 'BIBLE_API_KEY' not in os.environ and 'BIBLE_API_KEY' in current_app.config:
                os.environ['BIBLE_API_KEY'] = current_app.config['BIBLE_API_KEY']
            
            # Commit any pending changes to ensure the song is in the database
            db.session.commit()
            
            # Verify the song exists
            song = db.session.get(Song, song_id)
            if not song:
                current_app.logger.error(f"Cannot enqueue analysis: Song with ID {song_id} not found in database")
                return None
            
            # If user_id was provided, verify it's valid
            if user_id is not None:
                user = db.session.get(User, user_id)
                if not user:
                    current_app.logger.warning(f"User with ID {user_id} not found, but continuing with analysis")
                    user_id = None
            
            # Select appropriate queue based on priority
            queue_name = {
                'high': 'high',
                'default': 'default', 
                'low': 'low'
            }.get(priority, 'default')
            
            queue = rq.get_queue(queue_name)
            
            # Enqueue the comprehensive analysis job
            job = queue.enqueue(
                f'{self.__module__}.execute_comprehensive_analysis_task',
                song_id,
                user_id=user_id,
                job_timeout=600,  # 10 minutes for comprehensive analysis
                result_ttl=86400,  # 24 hours
                failure_ttl=86400,  # 24 hours
                job_id=f"comprehensive_analysis_{song_id}"
            )
            
            current_app.logger.info(f"Enqueued COMPREHENSIVE biblical analysis for song: {song.title} (ID: {song_id}) "
                                  f"with {priority} priority, job ID: {job.id}")
            
            return job
            
        except Exception as e:
            current_app.logger.error(f"Failed to enqueue comprehensive analysis for song {song_id}: {e}")
            return None
    
    def analyze_user_songs(self, user_id: int, force_reanalysis: bool = False, 
                          max_songs: int = None) -> Dict[str, Any]:
        """
        Analyze all songs for a user with comprehensive biblical analysis.
        
        Args:
            user_id: ID of the user
            force_reanalysis: Whether to re-analyze already analyzed songs
            max_songs: Maximum number of songs to analyze (None for all)
            
        Returns:
            Dictionary with analysis results and statistics
        """
        try:
            # Get all songs for this user
            songs_query = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct()
            
            if not force_reanalysis:
                # Filter out already analyzed songs
                songs_query = songs_query.outerjoin(
                    AnalysisResult, Song.id == AnalysisResult.song_id
                ).filter(AnalysisResult.id.is_(None))
            
            if max_songs:
                songs_query = songs_query.limit(max_songs)
            
            all_songs = songs_query.all()
            
            if not all_songs:
                return {
                    'status': 'complete',
                    'message': 'No songs to analyze',
                    'songs_analyzed': 0,
                    'songs_failed': 0,
                    'total_songs': 0
                }
            
            logger.info(f"Starting comprehensive analysis for {len(all_songs)} songs for user {user_id}")
            
            songs_analyzed = 0
            songs_failed = 0
            
            for i, song in enumerate(all_songs):
                try:
                    job = self.enqueue_analysis_job(song.id, user_id=user_id)
                    if job:
                        songs_analyzed += 1
                        logger.debug(f"Enqueued comprehensive analysis for song {song.id}: {song.title}")
                    else:
                        songs_failed += 1
                        logger.warning(f"Failed to enqueue analysis for song {song.id}: {song.title}")
                    
                    # Commit every 10 songs to avoid long transactions
                    if i % 10 == 0:
                        db.session.commit()
                        
                except Exception as e:
                    songs_failed += 1
                    logger.error(f"Error processing song {song.id}: {e}")
                    continue
            
            # Final commit
            db.session.commit()
            
            logger.info(f"Comprehensive analysis queued for user {user_id}: "
                       f"{songs_analyzed} songs queued, {songs_failed} failed")
            
            return {
                'status': 'started',
                'message': f'Queued {songs_analyzed} songs for comprehensive biblical analysis',
                'songs_analyzed': songs_analyzed,
                'songs_failed': songs_failed,
                'total_songs': len(all_songs)
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_user_songs for user {user_id}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to start analysis: {str(e)}',
                'songs_analyzed': 0,
                'songs_failed': 0,
                'total_songs': 0
            }
    
    def get_analysis_progress(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive analysis progress for a user"""
        try:
            # Get total songs for user
            total_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct().count()
            
            # Get completed comprehensive analyses
            completed_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'completed',
                    AnalysisResult.biblical_themes.isnot(None)  # Ensure comprehensive analysis
                )
            ).distinct().count()
            
            # Get in-progress analyses
            in_progress_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'in_progress'
                )
            ).distinct().count()
            
            # Get failed analyses
            failed_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'failed'
                )
            ).distinct().count()
            
            pending_analyses = total_songs - completed_analyses - in_progress_analyses - failed_analyses
            
            # Calculate progress percentage
            progress_percentage = (completed_analyses / total_songs * 100) if total_songs > 0 else 0
            
            return {
                'total_songs': total_songs,
                'completed': completed_analyses,
                'in_progress': in_progress_analyses,
                'pending': pending_analyses,
                'failed': failed_analyses,
                'progress_percentage': round(progress_percentage, 1),
                'has_active_analysis': in_progress_analyses > 0,
                'analysis_type': 'comprehensive_biblical'
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis progress for user {user_id}: {e}")
            return {
                'total_songs': 0,
                'completed': 0,
                'in_progress': 0,
                'pending': 0,
                'failed': 0,
                'progress_percentage': 0,
                'has_active_analysis': False,
                'analysis_type': 'comprehensive_biblical'
            }
    
    def analyze_playlist_content(self, playlist_id: str, user_id: int) -> Dict[str, Any]:
        """
        Analyze all songs in a playlist that haven't been analyzed yet.
        
        Args:
            playlist_id: Spotify ID of the playlist to analyze
            user_id: ID of the user requesting analysis
            
        Returns:
            dict: Summary of the analysis operation
        """
        logger.info(f"🎯 Starting playlist analysis for playlist {playlist_id} requested by user {user_id}")
        
        try:
            # Get the playlist from the database
            playlist = db.session.query(Playlist).filter_by(
                spotify_id=playlist_id, 
                owner_id=user_id
            ).first()
            
            if not playlist:
                logger.error(f"❌ Playlist {playlist_id} not found or not owned by user {user_id}")
                return {
                    "status": "error",
                    "error": "Playlist not found or access denied"
                }
            
            # Get all songs in the playlist that don't have analysis results
            unanalyzed_songs = db.session.query(Song).join(
                PlaylistSong, 
                Song.id == PlaylistSong.song_id
            ).outerjoin(
                AnalysisResult, 
                Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    PlaylistSong.playlist_id == playlist.id,
                    AnalysisResult.id.is_(None)  # No analysis result exists
                )
            ).all()
            
            total_songs = db.session.query(Song).join(
                PlaylistSong, 
                Song.id == PlaylistSong.song_id
            ).filter(PlaylistSong.playlist_id == playlist.id).count()
            
            unanalyzed_count = len(unanalyzed_songs)
            
            if unanalyzed_count == 0:
                logger.info(f"✅ All songs in playlist '{playlist.name}' are already analyzed")
                return {
                    "status": "complete",
                    "message": f"All {total_songs} songs in playlist '{playlist.name}' are already analyzed",
                    "total_songs": total_songs,
                    "unanalyzed_songs": 0,
                    "jobs_queued": 0
                }
            
            # Queue analysis jobs for unanalyzed songs
            jobs_queued = 0
            failed_jobs = 0
            
            logger.info(f"🔄 Queueing analysis for {unanalyzed_count} unanalyzed songs in playlist '{playlist.name}'")
            
            for song in unanalyzed_songs:
                try:
                    job = self.enqueue_analysis_job(song.id, user_id=user_id, priority='default')
                    if job:
                        jobs_queued += 1
                        logger.debug(f"✅ Queued analysis for '{song.title}' by {song.artist} (Job ID: {job.id})")
                    else:
                        failed_jobs += 1
                        logger.warning(f"⚠️ Failed to queue analysis for '{song.title}' by {song.artist}")
                except Exception as e:
                    failed_jobs += 1
                    logger.error(f"❌ Error queueing analysis for song {song.id}: {str(e)}")
            
            # Update playlist's last analyzed timestamp
            playlist.last_analyzed_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"🎯 Playlist analysis summary: {jobs_queued} jobs queued, {failed_jobs} failed for playlist '{playlist.name}'")
            
            return {
                "status": "started",
                "message": f"Started analysis for {jobs_queued} out of {unanalyzed_count} unanalyzed songs in playlist '{playlist.name}'",
                "playlist_name": playlist.name,
                "total_songs": total_songs,
                "unanalyzed_songs": unanalyzed_count,
                "jobs_queued": jobs_queued,
                "failed_jobs": failed_jobs
            }
            
        except Exception as e:
            logger.error(f"❌ Error in playlist analysis for playlist {playlist_id}: {str(e)}")
            return {
                "status": "error",
                "error": f"Failed to analyze playlist: {str(e)}"
            }


# Module-level function for RQ worker
def execute_comprehensive_analysis_task(song_id: int, user_id: int = None, **kwargs):
    """
    Background task function that executes comprehensive analysis.
    This function is called by RQ workers and uses proper Flask app context.
    """
    from flask import current_app
    
    # Ensure we're in an application context
    if not current_app:
        from app import create_app
        app = create_app('development')
        with app.app_context():
            service = UnifiedAnalysisService()
            return service.execute_comprehensive_analysis(song_id, user_id)
    else:
        service = UnifiedAnalysisService()
        return service.execute_comprehensive_analysis(song_id, user_id)


# Singleton instance for use throughout the application
unified_analysis_service = UnifiedAnalysisService() 