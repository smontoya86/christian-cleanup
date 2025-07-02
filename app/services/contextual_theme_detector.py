"""
Contextual Theme Detection Service

Enhanced theme detection that uses existing AI models to understand context
and provide more accurate Christian theme identification.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class ContextualThemeDetector:
    """
    Enhanced theme detector that uses existing AI analysis for contextual understanding.
    
    This detector leverages sentiment and emotion analysis to determine whether
    detected themes are appropriate (worship/positive) or inappropriate (profanity/negative).
    """
    
    def __init__(self):
        """Initialize the contextual theme detector."""
        logger.info("Initializing ContextualThemeDetector")
        self._initialize_theme_patterns()
    
    def _initialize_theme_patterns(self):
        """Initialize enhanced theme detection patterns with context awareness."""
        self.theme_patterns = {
            'God': {
                'positive_phrases': [
                    r'\bgod is (?:good|great|love|faithful|merciful|awesome|amazing)\b',
                    r'\bpraise (?:god|the lord)\b',
                    r'\bthank god\b',
                    r'\bgod bless\b',
                    r'\btrust in god\b',
                    r'\bgod almighty\b',
                    r'\bglory to god\b',
                    r'\bgod\s+(?:loves|cares|provides|saves)\b'
                ],
                'negative_phrases': [
                    r'\bgod damn\b',
                    r'\bgod\s*dammit\b'
                ],
                'ambiguous_phrases': [
                    r'\boh my god\b',
                    r'\bmy god\b'
                ]
            },
            'Jesus': {
                'positive_phrases': [
                    r'\bjesus (?:loves|saves|died|christ|is lord)\b',
                    r'\blord jesus\b',
                    r'\bin jesus name\b',
                    r'\bfollow jesus\b',
                    r'\bjesus christ\b',
                    r'\bsavior jesus\b'
                ],
                'negative_phrases': [],
                'ambiguous_phrases': [
                    r'\bjesus\b'  # Standalone Jesus can be neutral
                ]
            },
            'faith': {
                'positive_phrases': [
                    r'\bhave faith\b',
                    r'\bfaith will\b',
                    r'\bkeep the faith\b',
                    r'\bfaith in (?:god|jesus|christ|the lord)\b',
                    r'\bby faith\b',
                    r'\bfaith (?:saves|endures|overcomes)\b'
                ],
                'negative_phrases': [],
                'ambiguous_phrases': [
                    r'\bfaith\b'  # Standalone faith might be neutral
                ]
            },
            'love': {
                'positive_phrases': [
                    r'\bgod\s+(?:loves|is love)\b',
                    r'\bjesus loves\b',
                    r'\bchristian love\b',
                    r'\bunconditional love\b',
                    r'\bdivine love\b',
                    r'\bgod\'s love\b'
                ],
                'negative_phrases': [],
                'ambiguous_phrases': []  # Remove general "love" to avoid false positives
            },
            'worship': {
                'positive_phrases': [
                    r'\bworship (?:god|the lord|jesus)\b',
                    r'\bcome worship\b',
                    r'\bin worship\b',
                    r'\bworship and praise\b'
                ],
                'negative_phrases': [],
                'ambiguous_phrases': [
                    r'\bworship\b'
                ]
            }
        }
    
    def detect_themes_with_context(self, lyrics: str, sentiment_data: Dict, emotion_data: Dict) -> List[Dict]:
        """
        Detect themes with contextual understanding using existing AI analysis.
        
        Args:
            lyrics: Song lyrics text
            sentiment_data: Sentiment analysis from existing AI models
            emotion_data: Emotion analysis from existing AI models
            
        Returns:
            List of themes with confidence scores and context information
        """
        if not lyrics:
            return []
        
        logger.info(f"Detecting contextual themes in lyrics (length: {len(lyrics)})")
        
        # Find potential theme candidates
        theme_candidates = self._find_theme_candidates(lyrics.lower())
        
        # Analyze context for each candidate
        contextual_themes = []
        for candidate in theme_candidates:
            context_analysis = self._analyze_theme_context(
                candidate, lyrics.lower(), sentiment_data, emotion_data
            )
            
            # Only include themes with sufficient confidence
            if context_analysis['confidence'] >= 0.5:  # Configurable threshold
                contextual_themes.append({
                    'theme': candidate['theme'],
                    'confidence': context_analysis['confidence'],
                    'context_type': context_analysis['type'],
                    'supporting_phrases': candidate.get('found_phrases', []),
                    'reasoning': context_analysis.get('reasoning', '')
                })
        
        logger.info(f"Detected {len(contextual_themes)} contextual themes")
        return contextual_themes
    
    def _find_theme_candidates(self, lyrics: str) -> List[Dict]:
        """
        Find potential theme candidates using enhanced phrase detection.
        
        Args:
            lyrics: Lowercase lyrics text
            
        Returns:
            List of theme candidates with found phrases
        """
        candidates = []
        
        for theme, patterns in self.theme_patterns.items():
            candidate = self._check_theme_patterns(theme, patterns, lyrics)
            if candidate:
                candidates.append(candidate)
        
        return candidates
    
    def _check_theme_patterns(self, theme: str, patterns: Dict, lyrics: str) -> Optional[Dict]:
        """
        Check if a theme's patterns are found in the lyrics.
        
        Args:
            theme: Theme name (e.g., 'God', 'Jesus')
            patterns: Pattern dictionary with positive/negative/ambiguous phrases
            lyrics: Lowercase lyrics text
            
        Returns:
            Theme candidate dictionary or None
        """
        found_positive = []
        found_negative = []
        found_ambiguous = []
        
        # Check positive phrases
        for pattern in patterns.get('positive_phrases', []):
            matches = re.findall(pattern, lyrics, re.IGNORECASE)
            found_positive.extend(matches)
        
        # Check negative phrases  
        for pattern in patterns.get('negative_phrases', []):
            matches = re.findall(pattern, lyrics, re.IGNORECASE)
            found_negative.extend(matches)
        
        # Check ambiguous phrases
        for pattern in patterns.get('ambiguous_phrases', []):
            matches = re.findall(pattern, lyrics, re.IGNORECASE)
            found_ambiguous.extend(matches)
        
        # Return candidate if any phrases found
        if found_positive or found_negative or found_ambiguous:
            return {
                'theme': theme,
                'positive_phrases_found': found_positive,
                'negative_phrases_found': found_negative,
                'ambiguous_phrases_found': found_ambiguous,
                'found_phrases': found_positive + found_negative + found_ambiguous
            }
        
        return None
    
    def _analyze_theme_context(self, candidate: Dict, lyrics: str, sentiment_data: Dict, emotion_data: Dict) -> Dict:
        """
        Analyze the context of a theme candidate using existing AI analysis.
        
        Args:
            candidate: Theme candidate with found phrases
            lyrics: Lowercase lyrics text
            sentiment_data: Sentiment analysis from AI models
            emotion_data: Emotion analysis from AI models
            
        Returns:
            Context analysis with confidence score and type
        """
        theme = candidate['theme']
        
        # Extract AI analysis data
        overall_sentiment = sentiment_data.get('primary', {}).get('label', 'NEUTRAL')
        sentiment_score = sentiment_data.get('primary', {}).get('score', 0.5)
        
        primary_emotion = emotion_data.get('primary', {}).get('label', 'neutral')
        emotion_score = emotion_data.get('primary', {}).get('score', 0.5)
        
        # Start with base confidence
        confidence = 0.5
        context_type = 'neutral'
        reasoning_parts = []
        
        # Positive phrase detection (strong positive signal)
        positive_phrases = candidate.get('positive_phrases_found', [])
        if positive_phrases:
            confidence += 0.3
            context_type = 'worship' if theme in ['God', 'Jesus'] else 'positive'
            reasoning_parts.append(f"Found positive phrases: {positive_phrases}")
        
        # Negative phrase detection (strong negative signal)
        negative_phrases = candidate.get('negative_phrases_found', [])
        if negative_phrases:
            confidence -= 0.4  # Strong penalty for negative usage
            context_type = 'negative'
            reasoning_parts.append(f"Found negative phrases: {negative_phrases}")
        
        # Sentiment context analysis
        if overall_sentiment == 'POSITIVE' and sentiment_score > 0.7:
            confidence += 0.2
            if context_type == 'neutral':
                context_type = 'positive'
            reasoning_parts.append(f"Positive sentiment ({sentiment_score:.2f})")
        elif overall_sentiment == 'NEGATIVE' and sentiment_score > 0.7:
            confidence -= 0.2
            if context_type == 'neutral':
                context_type = 'negative'
            reasoning_parts.append(f"Negative sentiment ({sentiment_score:.2f})")
        
        # Emotion context analysis
        positive_emotions = ['joy', 'love', 'hope', 'peace', 'gratitude']
        negative_emotions = ['anger', 'fear', 'disgust', 'sadness']
        
        if primary_emotion in positive_emotions and emotion_score > 0.6:
            confidence += 0.15
            if context_type == 'neutral':
                context_type = 'worship' if theme in ['God', 'Jesus'] else 'positive'
            reasoning_parts.append(f"Positive emotion: {primary_emotion}")
        elif primary_emotion in negative_emotions and emotion_score > 0.6:
            confidence -= 0.15
            if context_type == 'neutral':
                context_type = 'negative'
            reasoning_parts.append(f"Negative emotion: {primary_emotion}")
        
        # Ambiguous phrase handling (requires strong context to be confident)
        ambiguous_phrases = candidate.get('ambiguous_phrases_found', [])
        if ambiguous_phrases and not positive_phrases and not negative_phrases:
            # Ambiguous phrases need strong positive context to be included
            if overall_sentiment != 'POSITIVE' or sentiment_score < 0.6:
                confidence -= 0.1
                reasoning_parts.append("Ambiguous usage with weak positive context")
        
        # Normalize confidence to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        reasoning = f"Sentiment: {overall_sentiment}, Emotion: {primary_emotion}"
        if reasoning_parts:
            reasoning += f". {'; '.join(reasoning_parts)}"
        
        return {
            'confidence': confidence,
            'type': context_type,
            'reasoning': reasoning
        } 