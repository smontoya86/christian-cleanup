"""
Enhanced Concern Detection Service

Provides detailed concern analysis with educational explanations to help users
understand why content may be problematic from a Christian perspective.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class EnhancedConcernDetector:
    """
    Enhanced concern detector for Christian music analysis.
    
    Provides detailed analysis of content concerns with educational explanations
    to help users develop biblical discernment skills.
    """
    
    def __init__(self):
        """Initialize the enhanced concern detector."""
        logger.info("Initializing EnhancedConcernDetector")
        self._initialize_concern_patterns()
    
    def _initialize_concern_patterns(self):
        """Initialize comprehensive concern detection patterns."""
        self.concern_patterns = {
            'explicit_language': {
                'category': 'Language and Expression',
                'severity': 'high',
                'patterns': [
                    r'\b(f[*u]ck|sh[*i]t|d[*a]mn|b[*i]tch|a[*s]s|hell|crap)\b',
                    r'\b(stupid|idiot|moron|dumb)\b',
                    r'\b(hate|revenge|kill|murder|die)\b'
                ],
                'biblical_perspective': 'Ephesians 4:29 teaches us to use words that build up rather than tear down.',
                'explanation': 'Inappropriate language can harm our witness and fail to reflect Christ\'s love.',
                'alternative_approach': 'Choose words that encourage and edify others, reflecting God\'s character.'
            },
            
            'sexual_content': {
                'category': 'Sexual Purity',
                'severity': 'high',
                'patterns': [
                    r'\b(sex|sexual|sexy|seduction|lust|desire|passion|intimate|romance)\b',
                    r'\b(body|curves|touch|kiss|bed|night|temptation)\b',
                    r'\b(love\s+me|want\s+you|need\s+you|take\s+me)\b'
                ],
                'biblical_perspective': '1 Corinthians 6:18-20 calls us to honor God with our bodies and flee sexual immorality.',
                'explanation': 'Sexual content outside biblical marriage context can promote impure thoughts and desires.',
                'alternative_approach': 'Focus on pure love, commitment, and God-honoring relationships.'
            },
            
            'substance_abuse': {
                'category': 'Substance Use',
                'severity': 'medium',
                'patterns': [
                    r'\b(drunk|drinking|alcohol|beer|wine|whiskey|vodka|party|club)\b',
                    r'\b(high|weed|marijuana|drugs|smoke|pills|substance)\b',
                    r'\b(escape|numb|forget|drown|relief)\b'
                ],
                'biblical_perspective': '1 Corinthians 6:19-20 reminds us our bodies are temples of the Holy Spirit.',
                'explanation': 'Substance use can impair judgment and become a substitute for finding peace in God.',
                'alternative_approach': 'Seek comfort, joy, and peace through prayer, fellowship, and God\'s presence.'
            },
            
            'violence_aggression': {
                'category': 'Violence and Aggression',
                'severity': 'high',
                'patterns': [
                    r'\b(fight|violence|hurt|pain|blood|gun|weapon|war)\b',
                    r'\b(anger|rage|fury|destroy|break|smash|hit)\b',
                    r'\b(enemy|battle|conflict|struggle|defeat)\b'
                ],
                'biblical_perspective': 'Matthew 5:39 teaches us to turn the other cheek rather than seek revenge.',
                'explanation': 'Violent themes can promote aggression rather than the peace Christ calls us to.',
                'alternative_approach': 'Embrace forgiveness, peace-making, and resolving conflicts with love.'
            },
            
            'materialism_greed': {
                'category': 'Materialism and Greed',
                'severity': 'medium',
                'patterns': [
                    r'\b(money|cash)\s+(is|comes|first|everything|all)\b',
                    r'\b(rich|wealth|expensive|luxury)\s+(life|lifestyle|living)\b',
                    r'\b(buy|shopping|possess|own)\s+(everything|anything|more)\b',
                    r'\blove\s+(money|cash|wealth|riches)\b',
                    r'\b(greed|greedy|materialistic|selfish)\b'
                ],
                'biblical_perspective': '1 Timothy 6:10 warns that the love of money is the root of all kinds of evil.',
                'explanation': 'Excessive focus on material wealth can distract from spiritual priorities and contentment in God.',
                'alternative_approach': 'Find satisfaction in God\'s provision and focus on eternal rather than temporary treasures.'
            },
            
            'pride_arrogance': {
                'category': 'Pride and Self-Focus',
                'severity': 'medium',
                'patterns': [
                    r'\bi\s+(am|m)\s+(better|superior|perfect|amazing|incredible|awesome)\s+(than|you)\b',
                    r'\bi\s+(deserve|earned|command|demand)\s+(everything|anything|more|respect)\b',
                    r'\b(arrogant|conceited|prideful|boastful|self-righteous)\b',
                    r'\blook\s+down\s+on\b',
                    r'\bi\s+(don\'t|dont)\s+need\s+(god|jesus|anyone|help)\b'
                ],
                'biblical_perspective': 'Proverbs 16:18 warns that pride goes before destruction and a haughty spirit before a fall.',
                'explanation': 'Excessive self-focus can lead to pride and take glory away from God.',
                'alternative_approach': 'Practice humility, recognizing that all good things come from God.'
            },
            
            'occult_spiritual_darkness': {
                'category': 'Occult and Spiritual Darkness',
                'severity': 'high',
                'patterns': [
                    r'\b(magic|spell|witch|demon|devil|satan|evil|dark|curse)\b',
                    r'\b(fortune|destiny|fate|luck|karma|energy|universe)\b',
                    r'\b(horoscope|astrology|psychic|medium|spirit|ghost)\b'
                ],
                'biblical_perspective': 'Deuteronomy 18:10-12 prohibits involvement with occult practices.',
                'explanation': 'Occult themes can open doors to spiritual deception and draw us away from God\'s truth.',
                'alternative_approach': 'Seek guidance through prayer, Scripture, and the Holy Spirit alone.'
            },
            
            'despair_hopelessness': {
                'category': 'Despair and Mental Health',
                'severity': 'medium',
                'patterns': [
                    r'\b(hopeless|pointless|meaningless|worthless|empty|lost)\b',
                    r'\b(depression|anxiety|fear|worry|stress|overwhelmed)\b',
                    r'\b(alone|isolated|abandoned|rejected|broken|damaged)\b'
                ],
                'biblical_perspective': 'Romans 15:13 declares God as the source of hope who fills us with joy and peace.',
                'explanation': 'While acknowledging struggles is healthy, constant focus on despair without hope can be spiritually harmful.',
                'alternative_approach': 'Balance honest expression of difficulties with reminders of God\'s love, hope, and healing.'
            },
            
            'rebellion_authority': {
                'category': 'Rebellion Against Authority',
                'severity': 'medium',
                'patterns': [
                    r'\b(rebel|defiant|resist|oppose|against|rules|authority)\b',
                    r'\b(my\s+way|do\s+what|independent|free|nobody|control)\b',
                    r'\b(parents|teacher|boss|law|government|church)\s+(wrong|stupid|unfair)\b'
                ],
                'biblical_perspective': 'Romans 13:1 teaches that all authority is established by God.',
                'explanation': 'Constant rebellion against legitimate authority contradicts biblical principles of submission and respect.',
                'alternative_approach': 'Address grievances respectfully while honoring God-given authority structures.'
            },
            
            'false_teaching': {
                'category': 'False Teaching and Heresy',
                'severity': 'high',
                'patterns': [
                    r'\b(all\s+gods|many\s+paths|universal|relative|truth|your\s+truth)\b',
                    r'\b(deserve\s+heaven|good\s+person|earn\s+salvation|works)\b',
                    r'\b(new\s+age|enlightenment|consciousness|awakening|meditation)\b'
                ],
                'biblical_perspective': 'John 14:6 declares Jesus as the only way to the Father.',
                'explanation': 'Teachings that contradict core Christian doctrines can lead believers away from biblical truth.',
                'alternative_approach': 'Affirm the exclusivity of Christ and salvation by grace through faith alone.'
            }
        }
    
    def analyze_content_concerns(self, title: str, artist: str, lyrics: str) -> Dict[str, Any]:
        """
        Analyze content for concerns with educational explanations.
        
        Args:
            title: Song title
            artist: Artist name
            lyrics: Song lyrics
            
        Returns:
            Comprehensive concern analysis with educational insights
        """
        try:
            logger.info(f"Analyzing content concerns for '{title}' by {artist}")
            
            # Combine all text for analysis
            full_text = f"{title} {artist} {lyrics}".lower()
            
            # Detect concerns
            detected_concerns = []
            concern_score = 0
            
            for concern_type, concern_data in self.concern_patterns.items():
                matches = self._detect_pattern_matches(full_text, concern_data['patterns'])
                
                if matches:
                    severity_weight = self._get_severity_weight(concern_data['severity'])
                    concern_score += len(matches) * severity_weight
                    
                    detected_concerns.append({
                        'type': concern_type,
                        'category': concern_data['category'],
                        'severity': concern_data['severity'],
                        'matches': matches,
                        'match_count': len(matches),
                        'biblical_perspective': concern_data['biblical_perspective'],
                        'explanation': concern_data['explanation'],
                        'alternative_approach': concern_data['alternative_approach'],
                        'educational_value': self._generate_educational_explanation(concern_type, concern_data, matches)
                    })
            
            # Calculate overall concern level
            overall_concern = self._calculate_overall_concern(concern_score, detected_concerns)
            
            # Generate educational summary
            educational_summary = self._generate_educational_summary(detected_concerns, overall_concern)
            
            return {
                'concern_score': concern_score,
                'overall_concern_level': overall_concern,
                'concerns_detected': len(detected_concerns),
                'detailed_concerns': detected_concerns,
                'educational_summary': educational_summary,
                'discernment_guidance': self._generate_discernment_guidance(detected_concerns),
                'is_content_safe': overall_concern in ['Very Low', 'Low'],
                'recommendation': self._generate_recommendation(overall_concern, detected_concerns)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content concerns: {e}")
            return {
                'concern_score': 0,
                'overall_concern_level': 'Unknown',
                'concerns_detected': 0,
                'detailed_concerns': [],
                'educational_summary': 'Content analysis temporarily unavailable.',
                'discernment_guidance': ['Content requires manual review.'],
                'is_content_safe': True,
                'recommendation': 'Please review content manually for Christian appropriateness.'
            }
    
    def _detect_pattern_matches(self, text: str, patterns: List[str]) -> List[str]:
        """Detect pattern matches in text."""
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        return list(set(matches))  # Remove duplicates
    
    def _get_severity_weight(self, severity: str) -> int:
        """Get numeric weight for severity level."""
        weights = {
            'low': 1,
            'medium': 3,
            'high': 5
        }
        return weights.get(severity, 2)
    
    def _calculate_overall_concern(self, score: int, concerns: List[Dict]) -> str:
        """Calculate overall concern level."""
        if not concerns:
            return 'Very Low'
        
        # Check for high-severity concerns
        high_severity_count = sum(1 for c in concerns if c['severity'] == 'high')
        
        if high_severity_count >= 2 or score >= 15:
            return 'High'
        elif high_severity_count >= 1 or score >= 10:
            return 'Medium'
        elif score >= 5:
            return 'Low'
        else:
            return 'Very Low'
    
    def _generate_educational_explanation(self, concern_type: str, concern_data: Dict, matches: List[str]) -> str:
        """Generate educational explanation for a specific concern."""
        explanation = f"This content shows {concern_data['category'].lower()} concerns. "
        explanation += f"{concern_data['explanation']} "
        explanation += f"Biblical guidance: {concern_data['biblical_perspective']} "
        explanation += f"Consider: {concern_data['alternative_approach']}"
        
        return explanation
    
    def _generate_educational_summary(self, concerns: List[Dict], overall_level: str) -> str:
        """Generate educational summary of all concerns."""
        if not concerns:
            return "This content shows no significant concerns and appears suitable for Christian listeners. It can support spiritual growth and positive thinking."
        
        summary = f"This content has {overall_level.lower()} concern level with {len(concerns)} area(s) requiring discernment: "
        
        categories = list(set(c['category'] for c in concerns))
        summary += ", ".join(categories) + ". "
        
        if overall_level in ['High', 'Medium']:
            summary += "This content requires careful consideration of whether it aligns with biblical values and supports your spiritual growth. "
        else:
            summary += "While minor concerns exist, this content can likely be enjoyed with proper biblical perspective. "
        
        summary += "Use this analysis as a tool for developing your own discernment skills."
        
        return summary
    
    def _generate_discernment_guidance(self, concerns: List[Dict]) -> List[str]:
        """Generate specific discernment guidance."""
        if not concerns:
            return [
                "This content appears to align with Christian values.",
                "It can support your spiritual growth and positive thinking.",
                "Consider how it points you toward God and biblical truth."
            ]
        
        guidance = []
        
        # Add specific guidance for each concern category
        categories = list(set(c['category'] for c in concerns))
        
        for category in categories:
            if 'Language' in category:
                guidance.append("Consider whether the language used honors God and builds others up.")
            elif 'Purity' in category:
                guidance.append("Evaluate whether this content promotes pure thoughts and God-honoring relationships.")
            elif 'Substance' in category:
                guidance.append("Reflect on whether this content encourages healthy, God-honoring choices.")
            elif 'Violence' in category:
                guidance.append("Consider whether this content promotes peace and forgiveness over conflict.")
            elif 'Materialism' in category:
                guidance.append("Ask whether this content encourages contentment and trust in God's provision.")
            elif 'Pride' in category:
                guidance.append("Evaluate whether this content promotes humility and recognition of God's grace.")
            elif 'Occult' in category:
                guidance.append("Ensure this content doesn't promote spiritual practices contrary to Christianity.")
            elif 'Despair' in category:
                guidance.append("Consider whether this content ultimately points toward hope in God or away from it.")
            elif 'Rebellion' in category:
                guidance.append("Reflect on whether this content respects God-given authority and promotes biblical submission.")
            elif 'False Teaching' in category:
                guidance.append("Verify that this content aligns with core Christian doctrines and biblical truth.")
        
        # Add general discernment principles
        guidance.extend([
            "Ask: Does this content draw me closer to God or pull me away?",
            "Consider: What values and attitudes does this content promote?",
            "Reflect: How might this content influence my thoughts and actions?"
        ])
        
        return guidance[:5]  # Limit to 5 most relevant points
    
    def _generate_recommendation(self, concern_level: str, concerns: List[Dict]) -> str:
        """Generate overall recommendation based on analysis."""
        if concern_level == 'Very Low':
            return "This content is suitable for Christian listeners and can support spiritual growth."
        elif concern_level == 'Low':
            return "This content is generally suitable but consider the minor concerns mentioned above."
        elif concern_level == 'Medium':
            return "This content requires discernment. Consider whether the themes align with your Christian values."
        else:  # High
            return "This content has significant concerns that conflict with Christian values. Consider avoiding or choosing alternative content." 