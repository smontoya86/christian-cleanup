"""
Lightweight Song Analyzer

A fast, lightweight replacement for the heavy KoalaAI transformer model.
Uses pattern matching and keyword detection for content analysis.
Maintains interface compatibility with the original SongAnalyzer.
"""
import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class LightweightSongAnalyzer:
    """
    Lightweight song analyzer using pattern matching instead of heavy ML models.
    
    Provides the same interface as the original SongAnalyzer but with:
    - No dependency on torch/transformers
    - Fast execution (< 100ms typical)
    - Low memory footprint
    - Reasonable accuracy for common cases
    """
    
    def __init__(self, user_id: int):
        """Initialize the lightweight analyzer"""
        self.user_id = user_id
        self._setup_patterns()
        
    def _setup_patterns(self):
        """Setup pattern matching rules for content detection"""
        
        # Explicit language patterns (case insensitive)
        self.explicit_patterns = [
            r'\b(damn|hell|shit|fuck|bitch|ass|crap)\b',
            r'\b(goddamn|wtf|omg)\b',
            r'\b(piss|bloody)\b'
        ]
        
        # Drug/substance patterns
        self.drug_patterns = [
            r'\b(weed|marijuana|cannabis|joint|blunt|smoke|smoking|high|stoned)\b',
            r'\b(cocaine|crack|heroin|meth|pills|drugs|drunk|drinking|alcohol)\b',
            r'\b(party|partying).*(drunk|high|wasted)\b',
            r'\b(rolling|molly|ecstasy|lsd|acid)\b'
        ]
        
        # Violence patterns
        self.violence_patterns = [
            r'\b(kill|murder|death|die|dead|blood|violence|violent|fight|fighting)\b',
            r'\b(gun|knife|weapon|shoot|shooting|shot|stab|stabbing)\b',
            r'\b(hate|hatred|revenge|destroy|destruction)\b'
        ]
        
        # Sexual content patterns
        self.sexual_patterns = [
            r'\b(sex|sexual|making love|intimate|intimacy|bedroom|naked)\b',
            r'\b(body|desire|lust|seduction|seduce|sexy)\b',
            r'\b(kiss|kissing|touch|touching|caress)\b'
        ]
        
        # Positive Christian content patterns
        self.positive_patterns = [
            r'\b(jesus|christ|lord|god|blessed|blessing|faith|hope|love|grace)\b',
            r'\b(prayer|pray|worship|praise|glory|hallelujah|amen)\b',
            r'\b(heaven|salvation|forgiveness|mercy|peace|joy)\b',
            r'\b(righteous|holy|sacred|divine|spiritual)\b'
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = {
            'explicit': [re.compile(p, re.IGNORECASE) for p in self.explicit_patterns],
            'drugs': [re.compile(p, re.IGNORECASE) for p in self.drug_patterns],
            'violence': [re.compile(p, re.IGNORECASE) for p in self.violence_patterns],
            'sexual': [re.compile(p, re.IGNORECASE) for p in self.sexual_patterns],
            'positive': [re.compile(p, re.IGNORECASE) for p in self.positive_patterns]
        }
        
    def analyze_song(self, song_data: Dict[str, Any], lyrics: Optional[str]) -> Dict[str, Any]:
        """
        Analyze a song and return Christian purity score and flags.
        
        Args:
            song_data: Dictionary containing song metadata (name, artists, explicit, etc.)
            lyrics: Song lyrics text (can be None or empty)
            
        Returns:
            Dictionary with:
            - christian_score: Integer 0-100 (higher = more Christian-appropriate)
            - explanation: String explaining the score
            - purity_flags: List of detected issues
        """
        try:
            # Start with neutral score
            base_score = 80
            penalty_total = 0
            flags = []
            
            # Handle explicit flag from Spotify
            if song_data.get('explicit', False):
                penalty = 50  # Increased from 20 to 50 for more impact
                penalty_total += penalty
                flags.append({
                    'flag': 'Explicit Content Flag',
                    'category': 'explicit',
                    'penalty_applied': penalty,
                    'confidence': 1.0,
                    'details': 'Song marked as explicit by Spotify - contains explicit language or content'
                })
                
            # Analyze lyrics if available
            if lyrics and lyrics.strip():
                lyrics_flags, lyrics_penalty = self._analyze_lyrics(lyrics)
                flags.extend(lyrics_flags)
                penalty_total += lyrics_penalty
            elif not lyrics:
                # No lyrics available - neutral scoring
                logger.info(f"No lyrics available for song: {song_data.get('name', 'Unknown')}")
                
            # Calculate final score
            final_score = max(0, min(100, base_score - penalty_total))
            
            # Determine concern level based on score and flags
            concern_level = self._determine_concern_level(final_score, flags)
            
            # Generate explanation
            explanation = self._generate_explanation(final_score, flags)
            
            return {
                'christian_score': final_score,
                'explanation': explanation,
                'purity_flags': flags,
                'concern_level': concern_level
            }
            
        except Exception as e:
            logger.error(f"Error analyzing song {song_data.get('name', 'Unknown')}: {str(e)}")
            # Return safe default on error
            return {
                'christian_score': 50,
                'explanation': 'Analysis failed - assigned neutral score',
                'purity_flags': [],
                'concern_level': 'Unknown'
            }
            
    def _analyze_lyrics(self, lyrics: str) -> tuple[List[Dict], int]:
        """Analyze lyrics for content issues"""
        flags = []
        total_penalty = 0
        
        lyrics_lower = lyrics.lower()
        
        # Check for positive content first (bonus points)
        positive_matches = self._find_pattern_matches(lyrics, 'positive')
        if positive_matches:
            # Positive content reduces penalties
            total_penalty -= 10
            
        # Check explicit language
        explicit_matches = self._find_pattern_matches(lyrics, 'explicit')
        if explicit_matches:
            penalty = min(30, len(explicit_matches) * 15)  # Cap at 30
            total_penalty += penalty
            flags.append({
                'flag': 'Explicit Language / Corrupting Talk',
                'category': 'explicit',
                'penalty_applied': penalty,
                'confidence': 0.9,
                'details': f'Found {len(explicit_matches)} explicit language patterns'
            })
            
        # Check drug content
        drug_matches = self._find_pattern_matches(lyrics, 'drugs')
        if drug_matches:
            penalty = min(40, len(drug_matches) * 20)  # Cap at 40
            total_penalty += penalty
            flags.append({
                'flag': 'Glorification of Drugs / Substance Abuse',
                'category': 'drugs',
                'penalty_applied': penalty,
                'confidence': 0.8,
                'details': f'Found {len(drug_matches)} drug-related patterns'
            })
            
        # Check violence
        violence_matches = self._find_pattern_matches(lyrics, 'violence')
        if violence_matches:
            penalty = min(35, len(violence_matches) * 18)  # Cap at 35
            total_penalty += penalty
            flags.append({
                'flag': 'Violent Content',
                'category': 'violence',
                'penalty_applied': penalty,
                'confidence': 0.85,
                'details': f'Found {len(violence_matches)} violence-related patterns'
            })
            
        # Check sexual content
        sexual_matches = self._find_pattern_matches(lyrics, 'sexual')
        if sexual_matches:
            penalty = min(30, len(sexual_matches) * 15)  # Cap at 30
            total_penalty += penalty
            flags.append({
                'flag': 'Sexual Content',
                'category': 'sexual',
                'penalty_applied': penalty,
                'confidence': 0.75,
                'details': f'Found {len(sexual_matches)} sexual content patterns'
            })
            
        return flags, total_penalty
        
    def _find_pattern_matches(self, lyrics: str, category: str) -> List[str]:
        """Find pattern matches for a given category"""
        matches = []
        patterns = self.compiled_patterns.get(category, [])
        
        for pattern in patterns:
            found = pattern.findall(lyrics)
            matches.extend(found)
            
        return list(set(matches))  # Remove duplicates
        
    def _generate_explanation(self, score: int, flags: List[Dict]) -> str:
        """Generate explanation of the analysis results"""
        explanation_parts = []
        
        # Add baseline information
        explanation_parts.append(f"Analysis started with a baseline score of 80 points.")
        
        if flags:
            total_penalty = sum(flag.get('penalty_applied', 0) for flag in flags)
            explanation_parts.append(f"Content concerns detected with total penalty of -{total_penalty} points:")
            
            # Add details for each flag
            for flag in flags:
                penalty = flag.get('penalty_applied', 0)
                flag_name = flag.get('flag', 'Unknown Issue')
                details = flag.get('details', '')
                explanation_parts.append(f"• {flag_name} (-{penalty} points): {details}")
            
            # Add calculation
            explanation_parts.append(f"Final calculation: 80 base - {total_penalty} penalty = {score}/100.")
        else:
            explanation_parts.append("No concerning content detected.")
            explanation_parts.append(f"Final score: {score}/100.")
        
        return " ".join(explanation_parts)

    # Maintain interface compatibility with original SongAnalyzer
    def detect_christian_purity_flags(self, lyrics: str, song_data: Dict) -> List[Dict]:
        """Legacy interface compatibility method"""
        if not lyrics:
            return []
            
        flags, _ = self._analyze_lyrics(lyrics)
        return flags 

    def _determine_concern_level(self, score: int, flags: List[Dict]) -> str:
        """Determine concern level based on score and flags"""
        # Check for explicit content specifically - always high concern
        explicit_flags = [f for f in flags if f.get('category') == 'explicit']
        if explicit_flags:
            return 'High'
            
        # Check for other high-severity content
        high_penalty_flags = [f for f in flags if f.get('penalty_applied', 0) >= 30]
        if high_penalty_flags:
            return 'High'
            
        # Score-based determination with stricter thresholds
        if score >= 85:
            return 'Low'
        elif score >= 70:
            return 'Medium'
        elif score >= 50:
            return 'High'
        else:
            return 'Very High' 