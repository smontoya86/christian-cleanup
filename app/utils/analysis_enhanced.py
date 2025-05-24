"""
Enhanced Song Analyzer - Prototype for Task 12.1

Smart pattern matching with context awareness for better accuracy
while maintaining the performance benefits of the lightweight system.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContentFlag:
    """Structured representation of a content flag"""
    category: str
    severity: str
    confidence: float
    penalty: int
    context: str
    matched_text: str

@dataclass
class AnalysisConfig:
    """User-configurable analysis parameters"""
    sensitivity_level: str = 'moderate'  # conservative, moderate, progressive
    profanity_weight: float = 1.0
    violence_weight: float = 1.0
    sexual_weight: float = 1.0
    drug_weight: float = 1.0
    positive_boost: float = 1.0
    denominational_preferences: Dict[str, float] = None
    
    def __post_init__(self):
        if self.denominational_preferences is None:
            self.denominational_preferences = {}

class EnhancedSongAnalyzer:
    """
    Enhanced song analyzer with context-aware pattern matching.
    
    Improvements over lightweight analyzer:
    - Context-aware patterns to reduce false positives
    - Intensity-based scoring for nuanced penalties
    - Better positive Christian content detection
    - User-configurable analysis parameters
    """
    
    def __init__(self, user_id: int, config: Optional[AnalysisConfig] = None):
        """Initialize the enhanced analyzer"""
        self.user_id = user_id
        self.config = config or AnalysisConfig()
        self._setup_enhanced_patterns()
        
    def _setup_enhanced_patterns(self):
        """Setup enhanced pattern matching rules with context awareness"""
        
        # Context-aware profanity patterns
        self.profanity_patterns = {
            'mild': {
                'weight': 0.3,
                'patterns': [
                    # "damn" but not "condemnation" or "damn right"
                    r'\b(?<!con)damn(?!ation\b)(?!\s+(?:right|straight|sure))\b',
                    # "hell" but not "he'll" or "hello" or "hell yeah"
                    r'\b(?<!he\')(?<!s)hell(?!o\b)(?!\s+(?:yeah|yes))\b',
                    r'\bcrap\b',
                ]
            },
            'moderate': {
                'weight': 0.7,
                'patterns': [
                    r'\bshit(?!ake)\b',  # shit but not shiitake
                    r'\bass(?!emble|ess|ume|ign)\b',  # ass but not assemble, assess, etc.
                    r'\bbitch(?!es\s+brew)\b',  # bitch but not "bitches brew" (jazz album)
                ]
            },
            'strong': {
                'weight': 1.0,
                'patterns': [
                    r'\bf\*{2,}k|\bfuck\b',
                    r'\bc\*{2,}t|\bcunt\b',
                    r'\bn\*{2,}r|\bnigger\b',
                ]
            }
        }
        
        # Enhanced drug/substance patterns with context
        self.drug_patterns = {
            'moderate': {
                'weight': 0.7,
                'patterns': [
                    r'\b(?:drink|drinking|drunk|wasted|hammered)\b',
                    r'\b(?:smoke|smoking|joint|blunt)\b',
                    # Fixed: "high" with proper negative lookahead for spiritual contexts
                    r'\bhigh(?!\s+(?:on\s+)?(?:life|love|faith|hope|praise|calling|ground|heaven|places|praise))\b',
                ]
            },
            'strong': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:cocaine|crack|heroin|meth|fentanyl)\b',
                    r'\b(?:pills|drugs|dealer|dealing)\b',
                    r'\b(?:rolling|molly|ecstasy|lsd|acid)\b',
                ]
            }
        }
        
        # Violence patterns with context awareness
        self.violence_patterns = {
            'mild': {
                'weight': 0.3,
                'patterns': [
                    # These patterns should give positive context, not penalties
                ]
            },
            'moderate': {
                'weight': 0.7,
                'patterns': [
                    # Exclude spiritual warfare contexts
                    r'\b(?:kill|murder|death|blood|violence)(?!\s+(?:of\s+)?(?:sin|evil|darkness))\b',
                    r'\b(?:fight|fighting|beat|beating)(?!\s+(?:the\s+)?(?:good\s+)?(?:fight|temptation|evil|sin))\b',
                    r'\b(?:hate|hatred|revenge)\b',
                ]
            },
            'strong': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:gun|knife|weapon|shoot|shooting|stab)\b',
                    r'\b(?:murder|kill)\s+(?:them|him|her|you)\b',
                    r'\b(?:blow\s+(?:up|away)|massacre|slaughter)\b',
                ]
            }
        }
        
        # Enhanced positive Christian content detection
        self.positive_patterns = {
            'worship': {
                'weight': 1.2,
                'patterns': [
                    r'\b(?:praise|worship|glorify|exalt|magnify)\s+(?:the\s+)?(?:lord|god|jesus|christ)\b',
                    r'\b(?:hallelujah|alleluia|hosanna|amen)\b',
                    r'\b(?:holy|sacred|divine|blessed)\s+(?:is\s+)?(?:the\s+)?(?:lord|god|jesus)\b',
                ]
            },
            'faith': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:i|we)\s+(?:believe|trust|have\s+faith)\s+in\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:faith|hope|love|grace|mercy|forgiveness)\b',
                    r'\b(?:salvation|redemption|eternal\s+life)\b',
                ]
            },
            'biblical': {
                'weight': 0.8,
                'patterns': [
                    r'\b(?:psalm|matthew|mark|luke|john|acts|romans|corinthians|galatians|ephesians|philippians|colossians|thessalonians|timothy|titus|philemon|hebrews|james|peter|jude|revelation)\s+\d+\b',
                    r'\b(?:scripture|biblical|word\s+of\s+god|gospel|testament)\b',
                    r'\b(?:disciples|apostles|prophets|angels)\b',
                ]
            },
            'prayer': {
                'weight': 0.9,
                'patterns': [
                    r'\b(?:pray|prayer|praying|prayers)\b',
                    r'\b(?:our\s+father|hail\s+mary|glory\s+be)\b',
                    r'\b(?:bless|blessing|blessed)\b',
                ]
            },
            'spiritual_warfare': {
                'weight': 1.1,
                'patterns': [
                    r'\bfight\s+(?:the\s+)?(?:good\s+)?fight\b',  # Biblical reference
                    r'\b(?:spiritual\s+)?(?:battle|warfare)(?:\s+against\s+(?:evil|sin|darkness))?\b',  # Spiritual warfare
                    r'\b(?:armor\s+of\s+god|sword\s+of\s+the\s+spirit)\b',
                ]
            },
            'positive_context': {
                'weight': 0.5,
                'patterns': [
                    r'\b(?:wine|beer|champagne)\s+(?:and|&)\s+(?:dine|dining)\b',  # Social drinking context
                    r'\bhigh\s+(?:on\s+)?(?:life|love|faith|hope|praise|calling|ground|heaven|places)\b',  # Spiritual high
                ]
            }
        }
        
        # Compile all patterns for performance
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        self.compiled_patterns = {}
        
        for category, levels in [
            ('profanity', self.profanity_patterns),
            ('drugs', self.drug_patterns),
            ('violence', self.violence_patterns),
            ('positive', self.positive_patterns)
        ]:
            self.compiled_patterns[category] = {}
            for level, data in levels.items():
                self.compiled_patterns[category][level] = {
                    'weight': data['weight'],
                    'compiled': [re.compile(pattern, re.IGNORECASE) for pattern in data['patterns']]
                }
    
    def analyze_song(self, song_data: Dict[str, Any], lyrics: Optional[str]) -> Dict[str, Any]:
        """
        Analyze a song with enhanced context-aware detection.
        
        Args:
            song_data: Dictionary containing song metadata
            lyrics: Song lyrics text (can be None or empty)
            
        Returns:
            Dictionary with enhanced analysis results
        """
        try:
            # Start with base score
            base_score = 85  # Slightly more optimistic than lightweight version
            flags = []
            positive_score = 0
            
            # Handle explicit flag from Spotify
            if song_data.get('explicit', False):
                penalty_amount = int(50 * self.config.profanity_weight)  # Increased from 20 to 50
                flag = ContentFlag(
                    category='explicit',
                    severity='high',
                    confidence=1.0,
                    penalty=penalty_amount,
                    context='Spotify explicit flag - Flagged by Spotify as containing explicit content',
                    matched_text='[EXPLICIT]'
                )
                flags.append(flag)
                base_score -= penalty_amount  # Apply penalty to base score
                
            # Analyze lyrics if available
            if lyrics and lyrics.strip():
                lyrics_flags, lyrics_penalty, positive_bonus = self._analyze_lyrics_enhanced(lyrics)
                flags.extend(lyrics_flags)
                base_score -= lyrics_penalty
                positive_score += positive_bonus
                
            # Apply positive score boost (this affects the bonus calculation)
            final_positive_bonus = int(positive_score * self.config.positive_boost)
            final_score = min(100, base_score + final_positive_bonus)
            final_score = max(0, final_score)
            
            # Determine concern level with enhanced logic
            concern_level = self._determine_concern_level(final_score, flags)
            
            # Generate detailed explanation
            explanation = self._generate_enhanced_explanation(final_score, flags, final_positive_bonus)
            
            return {
                'christian_score': final_score,
                'explanation': explanation,
                'purity_flags': [self._flag_to_dict(flag) for flag in flags],
                'positive_score_bonus': final_positive_bonus,
                'concern_level': concern_level,
                'analysis_version': 'enhanced_v1'
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis for song {song_data.get('name', 'Unknown')}: {str(e)}")
            # Return safe default
            return {
                'christian_score': 50,
                'explanation': 'Analysis failed - assigned neutral score',
                'purity_flags': [],
                'positive_score_bonus': 0,
                'concern_level': 'Medium',
                'analysis_version': 'enhanced_v1_error'
            }
    
    def _analyze_lyrics_enhanced(self, lyrics: str) -> Tuple[List[ContentFlag], int, int]:
        """Enhanced lyrics analysis with context awareness"""
        flags = []
        total_penalty = 0
        positive_bonus = 0
        
        # Analyze negative content with context awareness
        for category in ['profanity', 'drugs', 'violence']:
            category_flags, category_penalty = self._analyze_category(lyrics, category)
            flags.extend(category_flags)
            total_penalty += category_penalty
            
        # Analyze positive content for bonus points
        positive_matches = self._analyze_positive_content(lyrics)
        positive_bonus = sum(match['bonus'] for match in positive_matches)
        
        return flags, total_penalty, positive_bonus
    
    def _analyze_category(self, lyrics: str, category: str) -> Tuple[List[ContentFlag], int]:
        """Analyze a specific category with intensity-based scoring"""
        flags = []
        total_penalty = 0
        
        category_patterns = self.compiled_patterns.get(category, {})
        category_weight = getattr(self.config, f'{category}_weight', 1.0)
        
        for severity, pattern_data in category_patterns.items():
            weight = pattern_data['weight']
            compiled_patterns = pattern_data['compiled']
            
            for pattern in compiled_patterns:
                matches = pattern.findall(lyrics)
                if matches:
                    # Calculate penalty based on severity, frequency, and user config
                    base_penalty = self._get_base_penalty(category, severity)
                    frequency_multiplier = min(len(matches), 3)  # Cap at 3x
                    
                    penalty = int(base_penalty * weight * frequency_multiplier * category_weight)
                    total_penalty += penalty
                    
                    flag = ContentFlag(
                        category=category,
                        severity=severity,
                        confidence=0.8 + (0.2 * weight),  # Higher confidence for stronger patterns
                        penalty=penalty,
                        context=f'Found {len(matches)} matches',
                        matched_text=matches[0] if matches else ''
                    )
                    flags.append(flag)
                    
                    # Don't double-penalize similar patterns
                    break
                    
        return flags, total_penalty
    
    def _analyze_positive_content(self, lyrics: str) -> List[Dict[str, Any]]:
        """Analyze positive Christian content for bonus scoring"""
        positive_matches = []
        
        for theme, pattern_data in self.compiled_patterns['positive'].items():
            weight = pattern_data['weight']
            compiled_patterns = pattern_data['compiled']
            
            for pattern in compiled_patterns:
                matches = pattern.findall(lyrics)
                if matches:
                    bonus = int(10 * weight * min(len(matches), 2))  # Cap bonus
                    positive_matches.append({
                        'theme': theme,
                        'matches': len(matches),
                        'bonus': bonus,
                        'examples': matches[:3]  # Keep first 3 examples
                    })
                    break  # Don't double-count similar patterns
                    
        return positive_matches
    
    def _get_base_penalty(self, category: str, severity: str) -> int:
        """Get base penalty for category and severity"""
        penalties = {
            'profanity': {'mild': 8, 'moderate': 15, 'strong': 25},
            'drugs': {'mild': 5, 'moderate': 20, 'strong': 35},
            'violence': {'mild': 5, 'moderate': 18, 'strong': 30},
        }
        return penalties.get(category, {}).get(severity, 10)
    
    def _determine_concern_level(self, score: int, flags: List[ContentFlag]) -> str:
        """Determine concern level with enhanced logic"""
        # Check for explicit content specifically - always high concern
        explicit_flags = [f for f in flags if f.category == 'explicit']
        if explicit_flags:
            return 'High'
            
        # Check for other high-severity flags
        high_severity_flags = [f for f in flags if f.severity in ['strong', 'high'] and f.category != 'explicit']
        if high_severity_flags:
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
    
    def _generate_enhanced_explanation(self, score: int, flags: List[ContentFlag], positive_bonus: int) -> str:
        """Generate detailed explanation of the analysis"""
        explanation_parts = []
        
        # Add starting baseline info
        explanation_parts.append(f"Analysis started with a baseline score of 85 points.")
        
        if positive_bonus > 0:
            explanation_parts.append(f"Positive Christian content detected (+{positive_bonus} points).")
        
        if flags:
            flag_summary = {}
            flag_details = []
            for flag in flags:
                if flag.category not in flag_summary:
                    flag_summary[flag.category] = 0
                flag_summary[flag.category] += flag.penalty
                
                # Add detailed information about the specific flag
                if flag.category == 'explicit':
                    flag_details.append(f"Explicit content flag applied (-{flag.penalty} points): {flag.context}")
                else:
                    flag_details.append(f"{flag.category.title()} content detected (-{flag.penalty} points): {flag.context}")
                
            # Add summary line
            total_penalties = sum(flag_summary.values())
            explanation_parts.append(f"Content concerns detected with total penalty of -{total_penalties} points:")
            
            # Add detailed flag information
            for detail in flag_details:
                explanation_parts.append(f"• {detail}")
        
        if not flags and positive_bonus == 0:
            explanation_parts.append("No concerning content detected.")
        
        # Add final score calculation
        if flags or positive_bonus != 0:
            explanation_parts.append(f"Final calculation: 85 base {'+' + str(positive_bonus) if positive_bonus > 0 else ''}{'-' + str(sum(flag.penalty for flag in flags)) if flags else ''} = {score}/100.")
        else:
            explanation_parts.append(f"Final score: {score}/100.")
        
        return " ".join(explanation_parts)
    
    def _flag_to_dict(self, flag: ContentFlag) -> Dict[str, Any]:
        """Convert ContentFlag to dictionary for JSON serialization"""
        return {
            'flag': f"{flag.category.title()} Content ({flag.severity})",
            'category': flag.category,
            'severity': flag.severity,
            'penalty_applied': flag.penalty,
            'confidence': flag.confidence,
            'details': f"{flag.context}: {flag.matched_text}"
        }

# Factory function for backward compatibility
def create_enhanced_analyzer(user_id: int, config: Optional[Dict[str, Any]] = None) -> EnhancedSongAnalyzer:
    """Create an enhanced analyzer with optional configuration"""
    analysis_config = None
    if config:
        analysis_config = AnalysisConfig(**config)
    return EnhancedSongAnalyzer(user_id, analysis_config) 