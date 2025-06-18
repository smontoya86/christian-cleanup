"""
Analysis Orchestrator - Comprehensive Song Analysis Engine

Orchestrates the analysis process across multiple domain components (content detection,
biblical themes, AI models) to provide comprehensive song analysis.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from .text import LyricsPreprocessor, TextTokenizer, TextCleaner
from .patterns import PatternRegistry
from .biblical import EnhancedBiblicalDetector
from .scoring import CompositeScorer
from .models import ModelManager, ContentModerationModel
from .config import AnalysisConfig
from .analysis_result import AnalysisResult
from .content import ContentAnalysisEngine
from .biblical import BiblicalAnalysisEngine  
from .quality import QualityAssuranceEngine
from .data.scoring import ScoringEngine
from .text import TextCleaningEngine
from .patterns import PatternDetectionRegistry
from .models.model_manager import ModelManager
from ..logging import get_logger
# Add function instrumentation import
from ..function_instrumentation import instrument_function, performance_context
from .huggingface_analyzer import HuggingFaceAnalyzer

logger = get_logger('app.utils.analysis.orchestrator')

DEFAULT_CONFIG = {
    'analysis_provider': 'huggingface', 
    'device': 'cpu', 
    'content_moderation_model': 'cardiffnlp/twitter-roberta-base-offensive'
}

class AnalysisOrchestrator:
    """
    Orchestrates comprehensive song analysis across multiple domain components.
    
    Coordinates content detection, biblical analysis, AI model processing, and 
    quality assurance to provide reliable and comprehensive song analysis.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        Initialize the analysis orchestrator.
        
        Args:
            config: Analysis configuration (uses defaults if None)
        """
        self.config = config or AnalysisConfig()
        
        # Initialize domain components
        self._initialize_components()
        
        logger.info("AnalysisOrchestrator initialized successfully")
    
    def _initialize_components(self) -> None:
        """Initialize all domain components."""
        try:
            # Text Processing Domain
            self.lyrics_preprocessor = LyricsPreprocessor()
            self.text_tokenizer = TextTokenizer()
            self.text_cleaner = TextCleaner()
            
            # Pattern Detection Domain
            pattern_config = self.config.sensitivity_settings.to_dict() if hasattr(self.config.sensitivity_settings, 'to_dict') else {}
            self.pattern_registry = PatternRegistry(pattern_config)
            
            # Biblical Analysis Domain
            biblical_config = self.config.user_preferences.get_biblical_preferences() if hasattr(self.config.user_preferences, 'get_biblical_preferences') else {}
            self.biblical_detector = EnhancedBiblicalDetector(biblical_config)
            
            # Model Integration Domain
            model_config = self.config.get_model_config() if hasattr(self.config, 'get_model_config') else DEFAULT_CONFIG
            self.model_manager = ModelManager(device=model_config['device'])
            self.content_model = ContentModerationModel(
                self.model_manager,
                model_config['content_moderation_model']
            )
            
            # Scoring Engine Domain
            scoring_config = self.config.scoring_weights.to_dict() if hasattr(self.config.scoring_weights, 'to_dict') else {}
            self.scorer = CompositeScorer(scoring_config)
            
            # Analysis engines
            self.content_engine = ContentAnalysisEngine(config=self.config)
            self.biblical_engine = BiblicalAnalysisEngine(config=self.config)
            self.qa_engine = QualityAssuranceEngine(config=self.config)
            
            # Scoring and detection systems
            self.scoring_engine = ScoringEngine(config=self.config.scoring_weights if hasattr(self.config, 'scoring_weights') else None)
            
            # Free AI analyzer using Hugging Face models
            self.huggingface_analyzer = HuggingFaceAnalyzer()
            
            logger.info("All domain components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
    
    @instrument_function(category="analysis", min_duration=0.1)
    def analyze_song(self, title: str, artist: str, lyrics_text: str, user_id: Optional[int] = None) -> AnalysisResult:
        """
        Analyze a song using the orchestrated analysis pipeline.
        
        Args:
            title: Song title
            artist: Song artist  
            lyrics_text: Song lyrics
            user_id: Optional user ID for personalization
            
        Returns:
            AnalysisResult with comprehensive analysis
        """
        # Use free Hugging Face models for comprehensive AI analysis
        logger.info(f"Using HuggingFace analysis for '{title}' by {artist}")
        return self._analyze_with_huggingface(title, artist, lyrics_text, user_id)

    def _analyze_with_pattern_matching(self, title: str, artist: str, lyrics_text: str, user_id: Optional[int] = None) -> AnalysisResult:
        """
        Fallback analysis using only pattern matching (no AI APIs required).
        
        Args:
            title: Song title
            artist: Song artist
            lyrics_text: Song lyrics
            user_id: Optional user ID
            
        Returns:
            AnalysisResult with basic pattern-matching analysis
        """
        # Combine all text for analysis
        all_text = f"{title or ''} {artist or ''} {lyrics_text or ''}".lower()
        
        # Christian theme keywords for detection
        christian_keywords = ['jesus', 'christ', 'god', 'lord', 'faith', 'holy', 'praise', 'worship', 'hallelujah']
        love_grace_keywords = ['love', 'grace', 'mercy', 'forgiveness']
        concern_keywords = ['damn', 'hell', 'shit', 'fuck']
        
        # Simple theme detection based on keywords
        positive_themes = []
        if any(word in all_text for word in christian_keywords):
            positive_themes.append({
                'theme': 'love_grace',
                'score': 1.0,
                'verses': []
            })
        if any(word in all_text for word in love_grace_keywords):
            positive_themes.append({
                'theme': 'biblical_references',
                'score': 0.76,
                'verses': []
            })
        
        # Simple concern detection - with debug logging
        concern_flags = []
        total_penalty = 0
        found_concerns = []
        
        # Check each concern keyword individually for debugging
        for word in concern_keywords:
            if word in all_text:
                found_concerns.append(word)
                logger.info(f"Pattern matching found concern keyword: '{word}' in '{title}'")
        
        if found_concerns:
            concern_flags.append({'type': 'explicit_language', 'confidence': 0.9})
            total_penalty += 30
            logger.info(f"Applied penalty of {total_penalty} for concern words: {found_concerns}")
        
        # Calculate score
        base_score = 100
        theme_bonus = len(positive_themes) * 10
        final_score = max(0, min(100, base_score + theme_bonus - total_penalty))
        
        # Determine concern level
        if final_score >= 80:
            concern_level = 'Low'
        elif final_score >= 60:
            concern_level = 'Medium'
        else:
            concern_level = 'High'
        
        # Create explanation
        if positive_themes and not concern_flags:
            explanation = f"This song is well-aligned with Christian values, featuring {len(positive_themes)} positive Christian themes with minimal concerning content."
        elif concern_flags:
            explanation = f"This song contains {len(concern_flags)} concerning content flags that may not align with Christian values."
        else:
            explanation = "This song appears to be neutral with no explicitly Christian or concerning content detected."

        # Create result with proper structure
        result = AnalysisResult(
            title=title,
            artist=artist,
            lyrics_text=lyrics_text,
            processed_text=all_text,
            content_analysis={
                'concern_flags': concern_flags,
                'total_penalty': total_penalty
            },
            biblical_analysis={
                'themes': positive_themes,
                'supporting_scripture': {
                    'verses': [],
                    'themes_covered': [t['theme'] for t in positive_themes],
                    'recommendation_basis': [f"Pattern matching analysis: Score {final_score}, Level {concern_level}"]
                },
                'biblical_themes_count': len(positive_themes)
            },
            scoring_results={
                'final_score': final_score,
                'quality_level': concern_level,
                'component_scores': {
                    'base_score': base_score,
                    'theme_bonus': theme_bonus,
                    'concern_penalty': -total_penalty
                },
                'explanation': explanation
            }
        )
        
        return result

    def _analyze_with_huggingface(self, title: str, artist: str, lyrics_text: str, user_id: Optional[int] = None) -> AnalysisResult:
        """
        Analyze song using free Hugging Face models.
        
        Args:
            title: Song title
            artist: Song artist
            lyrics_text: Song lyrics
            user_id: Optional user ID
            
        Returns:
            AnalysisResult with comprehensive AI analysis using free models
        """
        try:
            # Use the HuggingFace analyzer
            result = self.huggingface_analyzer.analyze_song(title, artist, lyrics_text, user_id)
            final_score = result.scoring_results.get('final_score', 0.0) if result.scoring_results else 0.0
            logger.info(f"HuggingFace analysis completed for '{title}' - Score: {final_score}")
            return result
        except Exception as e:
            logger.warning(f"HuggingFace analysis failed for '{title}': {str(e)}, falling back to pattern matching")
            # Fallback to pattern matching if HuggingFace models fail
            return self._analyze_with_pattern_matching(title, artist, lyrics_text, user_id)

    def _analyze_with_ai_models(self, title: str, artist: str, lyrics_text: str, user_id: Optional[int] = None) -> AnalysisResult:
        """
        Analyze text with AI models.
        
        Args:
            title: Song title
            artist: Song artist
            lyrics_text: Song lyrics
            user_id: Optional user ID
            
        Returns:
            AnalysisResult with model analysis
        """
        start_time = time.time()
        
        try:
            # Update user preferences if user_id provided
            if user_id:
                self.config.user_preferences.user_id = user_id
            
            # Validate inputs
            if not lyrics_text:
                return AnalysisResult.create_error(
                    title=title,
                    artist=artist,
                    error_message="No lyrics provided for analysis"
                )
            
            logger.info(f"Starting analysis for '{title}' by {artist}")
            
            # Phase 1: Text Processing
            with performance_context("text_processing"):
                processed_text = self._process_text(lyrics_text)
            
            # Phase 2: Content Detection
            with performance_context("content_detection"):
                content_results = self._detect_content(processed_text)
            
            # Phase 3: Biblical Analysis
            with performance_context("biblical_analysis"):
                biblical_results = self._analyze_biblical_content(processed_text)
            
            # Phase 4: AI Model Analysis
            with performance_context("model_analysis"):
                model_results = self._analyze_with_models(processed_text)
            
            # Phase 5: Score Calculation
            with performance_context("score_calculation"):
                final_score = self._calculate_scores(
                    content_results, biblical_results, model_results
                )
            
            # Phase 6: Generate Result
            with performance_context("result_generation"):
                result = self._create_analysis_result(
                    title=title,
                    artist=artist,
                    lyrics_text=lyrics_text,
                    processed_text=processed_text,
                    content_results=content_results,
                    biblical_results=biblical_results,
                    model_results=model_results,
                    final_score=final_score,
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"Analysis completed for '{title}' in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error in song analysis: {str(e)}")
            return AnalysisResult.create_error(
                title=title,
                artist=artist,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    @instrument_function(category="text_processing", min_duration=0.01)
    def _process_text(self, lyrics_text: str) -> str:
        """
        Process lyrics text through text domain components.
        
        Args:
            lyrics_text: Raw lyrics text
            
        Returns:
            Processed and cleaned text
        """
        # Clean and process text
        cleaned_text = self.text_cleaner.clean_advanced(lyrics_text)
        processed_text = self.lyrics_preprocessor.preprocess(cleaned_text)
        
        return processed_text
    
    @instrument_function(category="content_detection", min_duration=0.01) 
    def _detect_content(self, text: str) -> Dict[str, Any]:
        """
        Detect problematic content patterns.
        
        Args:
            text: Processed text
            
        Returns:
            Content detection results
        """
        enabled_filters = self.config.user_preferences.get_enabled_filters()
        
        # Get all detection results
        all_results = self.pattern_registry.detect_all(text)
        
        results = {}
        total_penalty = 0.0
        
        for detector_name, detection_result in all_results.items():
            # Map detector names to filter types if needed
            filter_type = detection_result.category
            
            if filter_type in enabled_filters:
                results[filter_type] = detection_result
                
                if detection_result.detected:
                    penalty = self.config.scoring_weights.get_penalty_for_content(
                        filter_type, detection_result.confidence
                    )
                    total_penalty += penalty
        
        results['total_penalty'] = total_penalty
        return results
    
    @instrument_function(category="biblical_analysis", min_duration=0.01)
    def _analyze_biblical_content(self, text: str) -> Dict[str, Any]:
        """
        Analyze biblical themes and content.
        
        Args:
            text: Processed text
            
        Returns:
            Biblical analysis results
        """
        if not self.config.user_preferences.include_biblical_themes:
            return {'themes': [], 'total_bonus': 0.0}
        
        # Detect themes using the base detector
        themes = self.biblical_detector.base_detector.detect_themes(text)
        
        # Calculate bonuses
        total_bonus = 0.0
        for theme in themes:
            bonus = self.config.scoring_weights.get_bonus_for_theme(
                theme.theme_name, theme.confidence
            )
            total_bonus += bonus
        
        return {
            'themes': [theme.__dict__ for theme in themes],  # Convert to dict format
            'total_bonus': total_bonus
        }
    
    @instrument_function(category="model_analysis", min_duration=0.1)
    def _analyze_with_models(self, text: str) -> Dict[str, Any]:
        """
        Analyze text with AI models.
        
        Args:
            text: Processed text
            
        Returns:
            Model analysis results
        """
        results = {}
        
        try:
            # Content moderation
            if self.content_model.is_ready():
                content_prediction = self.content_model.predict(
                    text, 
                    chunk_size=self.config.max_chunk_size
                )
                results['content_moderation'] = content_prediction.to_dict()
            else:
                logger.warning("Content moderation model not ready")
                results['content_moderation'] = None
                
        except Exception as e:
            logger.error(f"Error in model analysis: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    @instrument_function(category="scoring", min_duration=0.01) 
    def _calculate_scores(self, content_results: Dict[str, Any],
                         biblical_results: Dict[str, Any],
                         model_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate final scores using the scoring engine.
        
        Args:
            content_results: Content detection results
            biblical_results: Biblical analysis results
            model_results: AI model results
            
        Returns:
            Final scoring results
        """
        # Prepare component scores
        component_scores = {
            'content_penalty': content_results.get('total_penalty', 0.0),
            'biblical_bonus': biblical_results.get('total_bonus', 0.0),
            'model_adjustments': 0.0  # Could be expanded based on model results
        }
        
        # Calculate using scoring engine
        final_scores = self.scoring_engine.calculate_final_scores(component_scores)
        
        return final_scores
    
    def _create_analysis_result(self, **kwargs) -> AnalysisResult:
        """
        Create comprehensive analysis result.
        
        Args:
            **kwargs: All analysis data
            
        Returns:
            AnalysisResult instance
        """
        return AnalysisResult(
            title=kwargs['title'],
            artist=kwargs['artist'],
            lyrics_text=kwargs['lyrics_text'],
            processed_text=kwargs['processed_text'],
            content_analysis=kwargs['content_results'],
            biblical_analysis=kwargs['biblical_results'],
            model_analysis=kwargs['model_results'],
            scoring_results=kwargs['final_score'],
            processing_time=kwargs['processing_time'],
            user_id=self.config.user_preferences.user_id,
            configuration_snapshot=self.config.to_dict()
        )
    
    def update_configuration(self, config_updates: Dict[str, Any]) -> None:
        """
        Update configuration dynamically.
        
        Args:
            config_updates: Configuration updates to apply
        """
        try:
            # Update main config
            self.config = AnalysisConfig.from_dict({
                **self.config.to_dict(),
                **config_updates
            })
            
            # Reinitialize components if needed
            self._initialize_components()
            
            logger.info("Configuration updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            raise
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics and status.
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_analyses': getattr(self, '_analysis_count', 0),
            'pattern_detectors': len(self.pattern_registry.detectors),
            'biblical_themes': 8,  # Default value since we know we have 8 themes
            'model_status': {
                'content_moderation': self.model_manager.get_model_status('content_moderation')
            },
            'memory_usage': self._get_memory_usage()
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.model_manager.clear_cache()
            logger.info("Orchestrator cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage information.
        
        Returns:
            Memory usage statistics
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent()
            }
        except Exception as e:
            logger.warning(f"Could not get memory usage: {e}")
            return {
                'rss_mb': 0,
                'vms_mb': 0,  
                'percent': 0
            } 