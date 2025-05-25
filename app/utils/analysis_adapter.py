"""
Analysis Adapter for Enhanced Song Analyzer

Provides a unified interface for song analysis while maintaining backward compatibility
with the existing system. Now uses the enhanced analyzer with context-aware pattern matching.
Optimized for thorough analysis with smart rate limiting.
"""
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from ..utils.lyrics import LyricsFetcher
from ..utils.analysis_enhanced import EnhancedSongAnalyzer, AnalysisConfig
import re

logger = logging.getLogger(__name__)

class SongAnalyzer:
    """
    Enhanced song analyzer adapter that provides backward compatibility
    while using the new context-aware enhanced analyzer.
    Optimized for thorough analysis with smart processing.
    """
    
    def __init__(self, device: Optional[str] = None, user_id: Optional[int] = None):
        """Initialize the song analyzer with enhanced capabilities"""
        self.device = device
        self.user_id = user_id or 1  # Default user_id if not provided
        
        # Initialize enhanced analyzer
        self.enhanced_analyzer = self._create_enhanced_analyzer()
        
        # Initialize lyrics fetcher
        self.lyrics_fetcher = None
        try:
            genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
            if genius_token:
                self.lyrics_fetcher = LyricsFetcher(genius_token=genius_token)
                logger.debug("LyricsFetcher initialized successfully")
            else:
                logger.warning("No GENIUS_ACCESS_TOKEN found - lyrics fetching disabled")
        except Exception as e:
            logger.error(f"Failed to initialize LyricsFetcher: {e}")
            self.lyrics_fetcher = None
    
    def _create_enhanced_analyzer(self) -> EnhancedSongAnalyzer:
        """Create and configure the enhanced analyzer"""
        try:
            # Use moderate sensitivity for consistent analysis
            config = AnalysisConfig(
                sensitivity_level='moderate',
                profanity_weight=1.0,
                violence_weight=1.0,
                sexual_weight=1.0,
                drug_weight=1.0,
                positive_boost=1.0
            )
            return EnhancedSongAnalyzer(user_id=self.user_id, config=config)
        except Exception as e:
            logger.error(f"Failed to create enhanced analyzer: {e}")
            # Fallback to basic configuration
            return EnhancedSongAnalyzer(user_id=self.user_id)
    
    def _should_skip_lyrics(self, title: str, artist: str) -> bool:
        """
        Determine if we should skip lyrics fetching for this song.
        Only skip for truly safe cases like instrumentals and classical music.
        """
        title_lower = title.lower()
        artist_lower = artist.lower()
        
        # Skip for obvious instrumentals
        instrumental_patterns = [
            r'\binstrumental\b',
            r'\bkaraoke\b',
            r'\bminus one\b',
            r'\bbackground music\b',
            r'\bsoundtrack\b',
            r'\binterlude\b',
            r'\bintro\b',
            r'\boutro\b'
        ]
        
        for pattern in instrumental_patterns:
            if re.search(pattern, title_lower):
                logger.debug(f"⚡ Skipping lyrics for instrumental: '{title}'")
                return True
        
        # Skip for very short titles that are unlikely to have meaningful lyrics
        if len(title.strip()) <= 3:
            logger.debug(f"⚡ Skipping lyrics for short title: '{title}'")
            return True
        
        # Skip for classical/orchestral music
        classical_patterns = [
            r'\bsymphony\b',
            r'\bconcerto\b',
            r'\bsonata\b',
            r'\bprelude\b',
            r'\bfugue\b',
            r'\bminuet\b',
            r'\bwaltz\b',
            r'\bmozart\b',
            r'\bbeethoven\b',
            r'\bbach\b',
            r'\bchopinb',
            r'\borchestra\b',
            r'\bphilharmonic\b'
        ]
        
        for pattern in classical_patterns:
            if re.search(pattern, title_lower) or re.search(pattern, artist_lower):
                logger.debug(f"⚡ Skipping lyrics for classical music: '{title}' by '{artist}'")
                return True
        
        # REMOVED: Christian artist skipping - even Christian artists need analysis
        # We want thorough analysis for all vocal music
        
        return False

    def analyze_song(self, title: str, artist: str, lyrics_text: Optional[str] = None, 
                    fetch_lyrics_if_missing: bool = True, is_explicit: bool = False) -> Dict[str, Any]:
        """
        Analyze a song using the enhanced analyzer with thorough analysis.
        
        Returns results in the format expected by the existing system for backward compatibility.
        """
        log_prefix = f"[User {self.user_id}] " if self.user_id else ""
        logger.info(f"{log_prefix}🔍 Analyzing '{title}' by '{artist}' (thorough mode)")
        
        # Default analysis results with safe defaults
        analysis_results = {
            "title": title,
            "artist": artist,
            "analyzed_by_user_id": self.user_id,
            "is_explicit": is_explicit,
            "lyrics_provided": lyrics_text is not None,
            "lyrics_fetched_successfully": False,
            "lyrics_used_for_analysis": "",
            "christian_score": 100,  # Default score for clean songs
            "christian_concern_level": "Low",
            "christian_purity_flags_details": [],
            "christian_positive_themes_detected": [],
            "christian_negative_themes_detected": [],
            "christian_supporting_scripture": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Note: We no longer fast-track explicit songs - let the enhanced analyzer handle them properly
            
            # 2. Determine if we should fetch lyrics
            should_fetch_lyrics = fetch_lyrics_if_missing and not lyrics_text
            if should_fetch_lyrics and self._should_skip_lyrics(title, artist):
                should_fetch_lyrics = False
                logger.debug(f"⚡ Skipping lyrics fetch for '{title}' - instrumental/classical")
            
            # 3. Fetch lyrics for thorough analysis
            if should_fetch_lyrics and self.lyrics_fetcher:
                logger.debug(f"🔍 Fetching lyrics for '{title}'...")
                try:
                    lyrics_text = self.lyrics_fetcher.fetch_lyrics(title, artist)
                    if lyrics_text:
                        logger.debug(f"✅ Lyrics fetched for '{title}'. Length: {len(lyrics_text)}")
                        analysis_results["lyrics_fetched_successfully"] = True
                    else:
                        logger.debug(f"❌ No lyrics found for '{title}'")
                        analysis_results["warnings"].append("No lyrics found. Analysis based on title/artist only.")
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching lyrics for '{title}': {e}")
                    error_msg = f"Error fetching lyrics: {str(e)}"
                    analysis_results["warnings"].append(error_msg)
            
            # Store the lyrics used for analysis
            analysis_results["lyrics_used_for_analysis"] = lyrics_text or ""
            
            # 4. Prepare song data for enhanced analyzer
            song_data = {
                'name': title,
                'artists': [{'name': artist}],
                'explicit': is_explicit
            }
            
            # 5. Run enhanced analysis with lyrics
            enhanced_result = self.enhanced_analyzer.analyze_song(song_data, lyrics_text)
            
            # 6. Convert enhanced results to backward-compatible format with comprehensive data
            analysis_results.update({
                "christian_score": enhanced_result['christian_score'],
                "christian_purity_flags_details": self._convert_purity_flags(enhanced_result['purity_flags']),
                "christian_concern_level": enhanced_result.get('concern_level', self._determine_concern_level(enhanced_result['christian_score'], enhanced_result['purity_flags'])),
                "explanation": enhanced_result.get('explanation', ''),
                "positive_score_bonus": enhanced_result.get('positive_score_bonus', 0),
                "analysis_version": enhanced_result.get('analysis_version', 'enhanced_v2_comprehensive'),
                
                # Map comprehensive biblical analysis fields
                "christian_biblical_themes": enhanced_result.get('biblical_themes', []),
                "christian_supporting_scripture": enhanced_result.get('supporting_scripture', {}),
                "christian_detailed_concerns": enhanced_result.get('detailed_concerns', []),
                "christian_positive_themes_detected": enhanced_result.get('positive_themes', []),
                
                # Legacy field mapping for backward compatibility
                "christian_negative_themes_detected": self._extract_negative_themes(enhanced_result.get('detailed_concerns', []))
            })
            
            # Log completion with comprehensive analysis details
            lyrics_status = "with lyrics" if lyrics_text else "title/artist only"
            biblical_themes_count = len(enhanced_result.get('biblical_themes', []))
            concerns_count = len(enhanced_result.get('detailed_concerns', []))
            positive_themes_count = len(enhanced_result.get('positive_themes', []))
            
            logger.info(f"{log_prefix}✅ Enhanced analysis completed for '{title}': Score={enhanced_result['christian_score']}, "
                       f"Level={analysis_results['christian_concern_level']}, Biblical Themes={biblical_themes_count}, "
                       f"Concerns={concerns_count}, Positive Themes={positive_themes_count} ({lyrics_status})")
            return analysis_results
            
        except Exception as e:
            logger.error(f"❌ Error in analysis for '{title}': {e}", exc_info=True)
            analysis_results["errors"].append(f"Analysis error: {str(e)}")
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

    def _extract_negative_themes(self, concerns: List[Dict[str, Any]]) -> List[str]:
        """Extract negative themes from detailed concerns"""
        negative_themes = []
        for concern in concerns:
            if concern.get('theme') and concern.get('theme').lower() in ['negative', 'sin', 'evil', 'wrong', 'harmful']:
                negative_themes.append(concern.get('theme'))
        return negative_themes 