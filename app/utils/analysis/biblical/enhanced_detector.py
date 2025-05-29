"""
Enhanced Biblical Detector

Integrates with enhanced analysis patterns and provides
additional detection capabilities for biblical content.
"""

import re
import logging
from typing import Dict, List, Any, Optional

from .theme_detector import BiblicalThemeDetector, ThemeMatch

logger = logging.getLogger(__name__)


class EnhancedBiblicalDetector:
    """
    Enhanced biblical content detector with additional pattern matching.
    
    Integrates with the enhanced analysis engine to provide more
    sophisticated biblical content detection.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enhanced biblical detector.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.base_detector = BiblicalThemeDetector(config)
        
        # Enhanced pattern configurations
        self.enable_metaphor_detection = self.config.get('enable_metaphor_detection', True)
        self.enable_narrative_detection = self.config.get('enable_narrative_detection', True)
        self.context_window_size = self.config.get('context_window_size', 50)
        
        # Load enhanced patterns
        self._load_enhanced_patterns()
        
        logger.debug("EnhancedBiblicalDetector initialized with additional pattern sets")
    
    def detect_enhanced_themes(self, text: str) -> Dict[str, Any]:
        """
        Perform enhanced biblical theme detection.
        
        Args:
            text: Text to analyze
            
        Returns:
            Enhanced detection results with additional insights
        """
        if not text:
            return self._empty_result()
        
        try:
            # Get base theme detection
            base_themes = self.base_detector.detect_themes(text)
            
            # Perform enhanced detection
            enhanced_results = {
                'base_themes': base_themes,
                'metaphorical_content': [],
                'narrative_elements': [],
                'context_analysis': {},
                'enhancement_score': 0.0
            }
            
            if self.enable_metaphor_detection:
                enhanced_results['metaphorical_content'] = self._detect_metaphors(text)
            
            if self.enable_narrative_detection:
                enhanced_results['narrative_elements'] = self._detect_narratives(text)
            
            # Analyze context relationships
            enhanced_results['context_analysis'] = self._analyze_context_relationships(text, base_themes)
            
            # Calculate enhancement score
            enhanced_results['enhancement_score'] = self._calculate_enhancement_score(enhanced_results)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in enhanced biblical detection: {e}", exc_info=True)
            return self._empty_result()
    
    def get_enhanced_summary(self, enhanced_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an enhanced summary of biblical content detection.
        
        Args:
            enhanced_results: Results from detect_enhanced_themes
            
        Returns:
            Enhanced summary with additional metrics
        """
        base_themes = enhanced_results.get('base_themes', [])
        base_summary = self.base_detector.get_theme_summary(base_themes)
        
        # Add enhanced metrics
        enhanced_summary = {
            **base_summary,
            'has_metaphorical_content': len(enhanced_results.get('metaphorical_content', [])) > 0,
            'narrative_elements_count': len(enhanced_results.get('narrative_elements', [])),
            'context_richness': len(enhanced_results.get('context_analysis', {})),
            'enhancement_score': enhanced_results.get('enhancement_score', 0.0),
            'detection_method': 'enhanced'
        }
        
        return enhanced_summary
    
    def _detect_metaphors(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect biblical metaphors and symbolic language.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected metaphors with context
        """
        metaphors = []
        
        for category, patterns in self.metaphor_patterns.items():
            for pattern, description in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    metaphors.append({
                        'category': category,
                        'matches': matches,
                        'description': description,
                        'pattern': pattern
                    })
        
        return metaphors
    
    def _detect_narratives(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect biblical narrative elements and story patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected narrative elements
        """
        narratives = []
        
        for narrative_type, patterns in self.narrative_patterns.items():
            for pattern, description in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    narratives.append({
                        'type': narrative_type,
                        'matches': matches,
                        'description': description,
                        'pattern': pattern
                    })
        
        return narratives
    
    def _analyze_context_relationships(self, text: str, base_themes: List[ThemeMatch]) -> Dict[str, Any]:
        """
        Analyze relationships between detected themes and their contexts.
        
        Args:
            text: Full text for context analysis
            base_themes: Previously detected themes
            
        Returns:
            Context analysis results
        """
        if not base_themes:
            return {}
        
        context_analysis = {
            'theme_proximity': {},
            'reinforcement_patterns': [],
            'contextual_strength': 0.0
        }
        
        # Analyze proximity between themes
        for i, theme1 in enumerate(base_themes):
            for j, theme2 in enumerate(base_themes[i+1:], i+1):
                proximity = self._calculate_theme_proximity(text, theme1, theme2)
                if proximity > 0.5:
                    context_analysis['theme_proximity'][f"{theme1.theme_name}_{theme2.theme_name}"] = proximity
        
        # Look for reinforcement patterns
        context_analysis['reinforcement_patterns'] = self._find_reinforcement_patterns(text, base_themes)
        
        # Calculate overall contextual strength
        context_analysis['contextual_strength'] = self._calculate_contextual_strength(context_analysis)
        
        return context_analysis
    
    def _calculate_enhancement_score(self, enhanced_results: Dict[str, Any]) -> float:
        """
        Calculate a score representing the enhancement value.
        
        Args:
            enhanced_results: Enhanced detection results
            
        Returns:
            Enhancement score (0.0 to 10.0)
        """
        score = 0.0
        
        # Base score from themes
        base_themes = enhanced_results.get('base_themes', [])
        if base_themes:
            base_score = self.base_detector.calculate_biblical_score_bonus(base_themes)
            score += base_score * 0.6  # Weight base score
        
        # Bonus for metaphorical content
        metaphors = enhanced_results.get('metaphorical_content', [])
        score += min(len(metaphors) * 0.5, 2.0)
        
        # Bonus for narrative elements
        narratives = enhanced_results.get('narrative_elements', [])
        score += min(len(narratives) * 0.3, 1.5)
        
        # Bonus for context richness
        context_analysis = enhanced_results.get('context_analysis', {})
        contextual_strength = context_analysis.get('contextual_strength', 0.0)
        score += contextual_strength * 2.0
        
        return min(score, 10.0)
    
    def _load_enhanced_patterns(self) -> None:
        """Load enhanced biblical pattern sets."""
        self.metaphor_patterns = {
            'shepherd_flock': {
                r'\b(shepherd|sheep|flock|pasture|fold)\b': 'Biblical shepherd/flock metaphor'
            },
            'light_darkness': {
                r'\b(light|darkness|lamp|shine|bright|illuminate)\b': 'Light and darkness spiritual metaphor'
            },
            'path_journey': {
                r'\b(path|way|journey|walk|road|guide)\b': 'Spiritual journey metaphor'
            },
            'family_relationships': {
                r'\b(father|son|daughter|brother|sister|family|children)\b': 'Divine family relationship metaphor'
            }
        }
        
        self.narrative_patterns = {
            'redemption_story': {
                r'\b(lost|found|return|restore|heal|broken|whole)\b': 'Redemption narrative elements'
            },
            'transformation': {
                r'\b(change|transform|new|old|become|grow)\b': 'Spiritual transformation narrative'
            },
            'calling_mission': {
                r'\b(call|called|purpose|mission|sent|go)\b': 'Divine calling narrative'
            }
        }
    
    def _calculate_theme_proximity(self, text: str, theme1: ThemeMatch, theme2: ThemeMatch) -> float:
        """Calculate proximity between two themes in text."""
        # Find positions of theme matches
        positions1 = []
        positions2 = []
        
        for match in theme1.matched_patterns:
            for pos in [m.start() for m in re.finditer(re.escape(match), text, re.IGNORECASE)]:
                positions1.append(pos)
        
        for match in theme2.matched_patterns:
            for pos in [m.start() for m in re.finditer(re.escape(match), text, re.IGNORECASE)]:
                positions2.append(pos)
        
        if not positions1 or not positions2:
            return 0.0
        
        # Calculate minimum distance between any two matches
        min_distance = min(abs(p1 - p2) for p1 in positions1 for p2 in positions2)
        
        # Convert distance to proximity score (closer = higher score)
        max_proximity_distance = self.context_window_size * 2
        proximity = max(0.0, 1.0 - (min_distance / max_proximity_distance))
        
        return proximity
    
    def _find_reinforcement_patterns(self, text: str, themes: List[ThemeMatch]) -> List[str]:
        """Find patterns that reinforce biblical themes."""
        reinforcement_words = [
            'truly', 'indeed', 'surely', 'certainly', 'always', 'forever',
            'eternal', 'everlasting', 'never', 'completely', 'totally'
        ]
        
        reinforcements = []
        for word in reinforcement_words:
            if re.search(rf'\b{word}\b', text, re.IGNORECASE):
                reinforcements.append(word)
        
        return reinforcements
    
    def _calculate_contextual_strength(self, context_analysis: Dict[str, Any]) -> float:
        """Calculate overall contextual strength score."""
        strength = 0.0
        
        # Proximity contributes to strength
        proximities = context_analysis.get('theme_proximity', {})
        if proximities:
            avg_proximity = sum(proximities.values()) / len(proximities)
            strength += avg_proximity * 0.5
        
        # Reinforcement patterns contribute
        reinforcements = context_analysis.get('reinforcement_patterns', [])
        strength += min(len(reinforcements) * 0.1, 0.3)
        
        return min(strength, 1.0)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty enhanced detection result."""
        return {
            'base_themes': [],
            'metaphorical_content': [],
            'narrative_elements': [],
            'context_analysis': {},
            'enhancement_score': 0.0
        } 