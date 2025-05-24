"""
Analysis Adapter for Enhanced Song Analyzer

Provides a unified interface for song analysis while maintaining backward compatibility
with the existing system. Now uses the enhanced analyzer with context-aware pattern matching.
"""
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from ..utils.lyrics import LyricsFetcher
from ..utils.analysis_enhanced import EnhancedSongAnalyzer, AnalysisConfig

logger = logging.getLogger(__name__)

class SongAnalyzer:
    """
    Enhanced song analyzer adapter that provides backward compatibility
    while using the new context-aware enhanced analyzer.
    """
    
    def __init__(self, device: Optional[str] = None, user_id: Optional[int] = None):
        """
        Initialize the enhanced song analyzer adapter.
        
        Args:
            device: Not used by enhanced analyzer (kept for compatibility)
            user_id: User ID for personalized analysis
        """
        self.user_id = user_id
        self.device = device  # Kept for backward compatibility
        
        # Initialize lyrics fetcher
        genius_token = os.environ.get('LYRICSGENIUS_API_KEY')
        try:
            from flask import current_app
            if current_app and not genius_token:
                genius_token = current_app.config.get('LYRICSGENIUS_API_KEY')
        except (RuntimeError, ImportError):
            pass
            
        self.lyrics_fetcher = LyricsFetcher(genius_token=genius_token)
        
        # Initialize enhanced analyzer with user configuration
        self.enhanced_analyzer = self._create_enhanced_analyzer()
        
        logger.info(f"Enhanced SongAnalyzer initialized for user {user_id}")
        
    def _create_enhanced_analyzer(self) -> EnhancedSongAnalyzer:
        """Create enhanced analyzer with consistent default configuration for all users"""
        # Use consistent default configuration for all users
        # This ensures reliable and consistent analysis across the platform
        config = AnalysisConfig(
            sensitivity_level='moderate',
            profanity_weight=1.0,
            violence_weight=1.0,
            sexual_weight=1.0,
            drug_weight=1.0,
            positive_boost=1.0,
            denominational_preferences={}
        )
        
        logger.info(f"Using standard analysis config for user {self.user_id}: moderate sensitivity")
        return EnhancedSongAnalyzer(user_id=self.user_id or 0, config=config)

    def analyze_song(self, title: str, artist: str, lyrics_text: Optional[str] = None, 
                    fetch_lyrics_if_missing: bool = True, is_explicit: bool = False) -> Dict[str, Any]:
        """
        Analyze a song using the enhanced analyzer.
        
        Returns results in the format expected by the existing system for backward compatibility.
        """
        log_prefix = f"[User {self.user_id}] " if self.user_id else ""
        logger.info(f"{log_prefix}Starting enhanced analysis for '{title}' by '{artist}'")
        
        # Default analysis results with safe defaults
        analysis_results = {
            "title": title,
            "artist": artist,
            "analyzed_by_user_id": self.user_id,
            "is_explicit": is_explicit,
            "lyrics_provided": lyrics_text is not None,
            "lyrics_fetched_successfully": False,
            "lyrics_used_for_analysis": "",
            "christian_score": 85,  # Default score
            "christian_concern_level": "Low",
            "christian_purity_flags_details": [],
            "christian_positive_themes_detected": [],
            "christian_negative_themes_detected": [],
            "christian_supporting_scripture": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # 1. Get Lyrics if needed
            if not lyrics_text and fetch_lyrics_if_missing and self.lyrics_fetcher:
                logger.info(f"Lyrics not provided for '{title}'. Fetching...")
                try:
                    lyrics_text = self.lyrics_fetcher.fetch_lyrics(title, artist)
                    if lyrics_text:
                        logger.info(f"Lyrics fetched successfully for '{title}'. Length: {len(lyrics_text)}")
                        analysis_results["lyrics_fetched_successfully"] = True
                    else:
                        logger.warning(f"Could not fetch lyrics for '{title}'.")
                        analysis_results["warnings"].append("Failed to fetch lyrics. Analysis will be limited.")
                except Exception as e:
                    logger.error(f"Error fetching lyrics for '{title}': {e}")
                    error_msg = f"Error fetching lyrics: {str(e)}"
                    analysis_results["warnings"].append(error_msg)
                    analysis_results["errors"].append(error_msg)
            
            # Store the lyrics used for analysis
            analysis_results["lyrics_used_for_analysis"] = lyrics_text or ""
            
            # 2. Prepare song data for enhanced analyzer
            song_data = {
                'name': title,
                'artists': [{'name': artist}],
                'explicit': is_explicit
            }
            
            # 3. Run enhanced analysis
            enhanced_result = self.enhanced_analyzer.analyze_song(song_data, lyrics_text)
            
            # 4. Convert enhanced results to backward-compatible format
            analysis_results.update({
                "christian_score": enhanced_result['christian_score'],
                "christian_purity_flags_details": self._convert_purity_flags(enhanced_result['purity_flags']),
                "christian_concern_level": enhanced_result.get('concern_level', self._determine_concern_level(enhanced_result['christian_score'], enhanced_result['purity_flags'])),
                "explanation": enhanced_result.get('explanation', ''),
                "positive_score_bonus": enhanced_result.get('positive_score_bonus', 0),
                "analysis_version": enhanced_result.get('analysis_version', 'enhanced_v1')
            })
            
            # Add themes if any positive content was detected
            if enhanced_result.get('positive_score_bonus', 0) > 0:
                analysis_results["christian_positive_themes_detected"] = [
                    {"theme": "Positive Christian Content", "confidence": 0.8}
                ]
            
            logger.info(f"{log_prefix}Enhanced analysis completed for '{title}': Score={enhanced_result['christian_score']}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis for '{title}': {e}", exc_info=True)
            analysis_results["errors"].append(f"Enhanced analysis error: {str(e)}")
            analysis_results["warnings"].append("Analysis may be incomplete due to processing error.")
            return analysis_results
            
    def _convert_purity_flags(self, purity_flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert enhanced analyzer purity flags to legacy format"""
        converted_flags = []
        
        for flag in purity_flags:
            converted_flag = {
                "flag_type": flag.get('flag', 'Unknown'),
                "category": flag.get('category', 'general'),
                "severity": flag.get('severity', 'medium'),
                "confidence": flag.get('confidence', 0.5),
                "description": flag.get('details', ''),
                "penalty_applied": flag.get('penalty_applied', 0)
            }
            converted_flags.append(converted_flag)
            
        return converted_flags
        
    def _determine_concern_level(self, score: int, flags: List[Dict[str, Any]]) -> str:
        """Determine concern level based on score and flags"""
        # Check for high-severity flags
        high_severity_flags = [f for f in flags if f.get('severity') in ['strong', 'high']]
        if high_severity_flags:
            return 'High'
            
        # Score-based determination
        if score >= 80:
            return 'Low'
        elif score >= 60:
            return 'Medium' 
        elif score >= 40:
            return 'High'
        else:
            return 'Very High' 