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
        """
        Initialize enhanced concern detector with Christian-context-aware patterns.
        
        Patterns are designed to avoid false positives in Christian worship songs
        while still detecting genuinely concerning content.
        """
        self.concern_patterns = {
            'explicit_language': {
                'category': 'Language and Expression',
                'severity': 'high',
                'patterns': [
                    # Only flag actual profanity, not spiritual references
                    r'\b(fuck|shit|damn|bitch|asshole|bastard|crap)\b',
                    r'\b(motherfucker|goddamn|jesus christ)\b(?!.*\b(lord|savior|praise|worship|holy)\b)',  # Exclude worship context
                    r'\b(piss|ass)\b(?!.*\b(pass|grass|class|mass|glass)\b)'  # Exclude innocent words
                ],
                'exclusions': [
                    # Christian contexts should not be flagged
                    r'\b(hell|damn)\b.*\b(victory|overcome|defeated|lost|free|salvation|redeemed)\b',
                    r'\b(hell)\b.*\b(another one|no more|cannot hold|lost its grip)\b'
                ],
                'biblical_perspective': 'Ephesians 4:29 teaches us to use words that build up rather than tear down.',
                'explanation': 'Inappropriate language can harm our witness and fail to reflect Christ\'s love.'
            },
            
            'sexual_content': {
                'category': 'Sexual Purity', 
                'severity': 'high',
                'patterns': [
                    # Much more specific sexual patterns
                    r'\b(sexual|explicit|seduction|erotic|pornography|adultery|fornication)\b',
                    r'\b(one night stand|hook up|make love|get naked|strip|seduce)\s+(me|you|tonight)\b',
                    r'\b(bedroom|sheets|undress)\s+(with you|tonight|now)\b',
                    r'\b(lust|lustful|sensual)\s+(desires|thoughts|body|touch)\b'
                ],
                'exclusions': [
                    # Common innocent words that appear in Christian songs
                    r'\b(night|body|touch|kiss|love|heart|soul|spirit)\b(?!.*\b(sexual|lust|desire|pleasure)\b)',
                    r'\b(embrace|hold|tender|gentle|beautiful)\b.*\b(god|lord|jesus|savior|faith|prayer)\b'
                ],
                'biblical_perspective': '1 Corinthians 6:18-20 calls us to honor God with our bodies and flee sexual immorality.',
                'explanation': 'Sexual content outside biblical marriage context can promote impure thoughts and desires.'
            },
            
            'violence_aggression': {
                'category': 'Violence and Aggression',
                'severity': 'high', 
                'patterns': [
                    # Specific actual violence, not spiritual warfare
                    r'\b(murder|kill|stab|shoot|assault|torture)\s+(you|him|her|them|people)\b',
                    r'\b(gun|knife|weapon|bomb)\s+(at|to kill|to hurt|to destroy)\b',
                    r'\b(hate|hurt|destroy|revenge)\s+(you|him|her|them|people)\b',
                    r'\b(blood|violence|brutal|savage)\s+(everywhere|spilled|graphic|gore)\b'
                ],
                'exclusions': [
                    # Spiritual warfare and Christian battle language should not be flagged
                    r'\b(battle|fight|war|enemy|armor|sword|shield)\b.*\b(god|lord|jesus|faith|prayer|spirit|evil|devil|darkness)\b',
                    r'\b(fight|battle|war)\s+(the good fight|for faith|against sin|spiritual)\b',
                    r'\b(victory|overcome|conquer|defeat)\b.*\b(sin|death|darkness|enemy|evil)\b'
                ],
                'biblical_perspective': 'Matthew 5:39 teaches us to turn the other cheek rather than seek revenge.',
                'explanation': 'Violent themes can promote aggression rather than the peace Christ calls us to.'
            },
            
            'substance_abuse': {
                'category': 'Substance Use',
                'severity': 'medium',
                'patterns': [
                    # Specific substance abuse contexts
                    r'\b(drunk|drinking|alcohol|beer|wine)\s+(heavily|everyday|to forget|to numb)\b',
                    r'\b(high|weed|marijuana|drugs|pills)\s+(on|from|everyday|to escape)\b',
                    r'\b(party|club|bar)\s+(drinking|drunk|wasted|hammered)\b',
                    r'\b(escape|numb|forget)\s+(with alcohol|with drugs|through drinking)\b'
                ],
                'exclusions': [
                    # Biblical wine/celebration contexts and metaphorical escape
                    r'\b(wine|celebrate|feast)\b.*\b(wedding|celebration|joy|blessing)\b',
                    r'\b(escape|refuge|shelter)\b.*\b(god|lord|jesus|faith|prayer|rock|fortress)\b'
                ],
                'biblical_perspective': '1 Corinthians 6:19-20 reminds us our bodies are temples of the Holy Spirit.',
                'explanation': 'Substance use can impair our judgment and dependence on God.'
            },
            
            'despair_hopelessness': {
                'category': 'Despair and Mental Health',
                'severity': 'medium',
                'patterns': [
                    # Specific hopeless contexts without redemptive themes
                    r'\b(hopeless|pointless|meaningless|worthless)\s+(?!.*\b(until|before|but now|then)\b)',
                    r'\b(suicide|kill myself|end it all|want to die)\b',
                    r'\b(no hope|no point|no meaning|give up)\s+(?!.*\b(until|before|but|except|unless)\b)'
                ],
                'exclusions': [
                    # "Lost and found" themes common in Christian testimony
                    r'\b(lost|alone|broken|empty)\b.*\b(found|filled|healed|restored|redeemed|saved)\b',
                    r'\b(once was|used to be|before)\s+(lost|alone|broken)\b.*\b(now|but|until)\b',
                    r'\b(lost|wandering|searching)\b.*\b(god|lord|jesus|home|way|light|truth)\b'
                ],
                'biblical_perspective': 'Romans 15:13 declares God as the source of hope who fills us with joy and peace.',
                'explanation': 'While acknowledging struggles is healthy, constant focus on despair without hope can be spiritually harmful.'
            },
            
            'rebellion_authority': {
                'category': 'Rebellion Against Authority',
                'severity': 'medium',
                'patterns': [
                    # Specific rebellious contexts
                    r'\b(rebel|rebellion|revolt)\s+(against|fight|destroy)\s+(parents|government|law|authority)\b',
                    r'\b(break|destroy|ignore|defy)\s+(the law|authority|rules|government)\b',
                    r'\b(anarchy|chaos|disorder|lawlessness)\s+(is good|forever|rules)\b'
                ],
                'exclusions': [
                    # Spiritual freedom and liberation themes
                    r'\b(free|freedom|liberty|liberated)\b.*\b(christ|god|lord|jesus|spirit|sin|death|hell|chains|bondage)\b',
                    r'\b(break|destroy)\s+(chains|bondage|sin|death|curse|stronghold)\b',
                    r'\b(rebel|fight|resist)\s+(sin|evil|devil|darkness|temptation)\b'
                ],
                'biblical_perspective': 'Romans 13:1 teaches that all authority is established by God.',
                'explanation': 'Constant rebellion against legitimate authority contradicts biblical principles of submission and respect.'
            },
            
            'occult_spiritual_darkness': {
                'category': 'Occult and Spiritual Darkness',
                'severity': 'high',
                'patterns': [
                    # Specific occult practices, not general Christian spirituality
                    r'\b(witch|witchcraft|spell|hex|curse|black magic|séance)\b',
                    r'\b(demon worship|satanic|devil worship|evil ritual)\b',
                    r'\b(ouija|tarot|crystal ball|horoscope|astrology|psychic reading)\b',
                    r'\b(new age|meditation|chakra|karma|reincarnation)\s+(?!.*\b(christian|biblical|prayer)\b)'
                ],
                'exclusions': [
                    # Christian spiritual language should not be flagged
                    r'\b(spirit|spiritual|soul|energy|universe|power)\b.*\b(god|lord|jesus|holy|divine|christian|prayer|worship)\b',
                    r'\b(meditation|prayer|worship|praise)\s+(on|in|to)\s+(god|jesus|lord|scripture|word)\b'
                ],
                'biblical_perspective': 'Deuteronomy 18:10-12 warns against involvement in occult practices.',
                'explanation': 'Occult involvement opens doors to spiritual deception and darkness.'
            }
        }
    
    def detect_concerns(self, lyrics: str, title: str = "", artist: str = "") -> Dict[str, Any]:
        """
        Detect potential concerns in song lyrics with Christian context awareness.
        
        Returns enhanced analysis with concern categories, biblical perspectives,
        and educational guidance while avoiding false positives in Christian songs.
        """
        if not lyrics:
            return {
                'concern_flags': [],
                'overall_concern_level': 'Low',
                'detailed_analysis': {},
                'educational_summary': 'No lyrics available for analysis.'
            }
        
        lyrics_lower = lyrics.lower()
        detected_concerns = []
        detailed_analysis = {}
        
        for concern_type, config in self.concern_patterns.items():
            concern_matches = []
            
            # Check main concern patterns
            for pattern in config['patterns']:
                matches = list(re.finditer(pattern, lyrics_lower, re.IGNORECASE))
                if matches:
                    # Check exclusions if they exist
                    should_exclude = False
                    if 'exclusions' in config:
                        for exclusion_pattern in config['exclusions']:
                            if re.search(exclusion_pattern, lyrics_lower, re.IGNORECASE):
                                should_exclude = True
                                break
                    
                    # Only add concerns if not excluded by Christian context
                    if not should_exclude:
                        concern_matches.extend([match.group() for match in matches])
            
            if concern_matches:
                # Remove duplicates while preserving order
                unique_matches = []
                seen = set()
                for match in concern_matches:
                    if match not in seen:
                        unique_matches.append(match)
                        seen.add(match)
                
                concern_detail = {
                    'type': concern_type,
                    'severity': config['severity'],
                    'category': config['category'],
                    'description': config['explanation'],
                    'biblical_perspective': config['biblical_perspective'],
                    'educational_value': f"This content shows {config['category'].lower()} concerns. {config['explanation']} Biblical guidance: {config['biblical_perspective']} Consider: Choose words that encourage and edify others, reflecting God's character." if concern_type == 'explicit_language' else f"This content shows {config['category'].lower()} concerns. {config['explanation']} Biblical guidance: {config['biblical_perspective']} Consider: Focus on themes that align with biblical values and spiritual growth.",
                    'matches': unique_matches[:5]  # Limit to top 5 matches
                }
                detected_concerns.append(concern_detail)
                detailed_analysis[concern_type] = concern_detail
        
        # Determine overall concern level based on severity and count
        overall_level = self._calculate_overall_concern_level(detected_concerns)
        
        # Generate educational summary
        educational_summary = self._generate_educational_summary(detected_concerns, title, artist)
        
        return {
            'concern_flags': detected_concerns,
            'overall_concern_level': overall_level,
            'detailed_analysis': detailed_analysis,
            'educational_summary': educational_summary,
            'context_awareness': 'Christian song analysis with false positive prevention'
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
    
    def _calculate_overall_concern_level(self, detected_concerns: List[Dict]) -> str:
        """Calculate overall concern level based on detected concerns."""
        if not detected_concerns:
            return 'Very Low'
        
        high_severity_count = sum(1 for concern in detected_concerns if concern.get('severity') == 'high')
        medium_severity_count = sum(1 for concern in detected_concerns if concern.get('severity') == 'medium')
        
        # More lenient thresholds to avoid over-flagging Christian content
        if high_severity_count >= 2:
            return 'High'
        elif high_severity_count >= 1 or medium_severity_count >= 3:
            return 'Medium'
        elif medium_severity_count >= 1:
            return 'Low'
        else:
            return 'Very Low'
    
    def _generate_educational_summary(self, detected_concerns: List[Dict], title: str, artist: str) -> str:
        """Generate educational summary for detected concerns."""
        if not detected_concerns:
            return "This content appears to align well with Christian values and supports spiritual growth."
        
        concern_categories = [concern.get('category', 'General') for concern in detected_concerns]
        concern_count = len(detected_concerns)
        
        if concern_count == 1:
            return f"This song contains content that may require discernment in the area of {concern_categories[0]}. Consider the biblical guidance provided and how this content aligns with your spiritual growth."
        else:
            categories_text = ", ".join(concern_categories)
            return f"This song contains content that may require discernment in {concern_count} areas: {categories_text}. Use this analysis as a tool for developing your own discernment skills and consider how this content supports your walk with Christ."

    # Backward compatibility method
    def analyze_content_concerns(self, title: str, artist: str, lyrics: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        result = self.detect_concerns(lyrics, title, artist)
        
        # Convert to old format for backward compatibility
        return {
            'concern_score': len(result['concern_flags']) * 10,  # Simple score calculation
            'overall_concern_level': result['overall_concern_level'],
            'concerns_detected': len(result['concern_flags']),
            'detailed_concerns': result['concern_flags'],
            'educational_summary': result['educational_summary'],
            'discernment_guidance': [concern.get('biblical_perspective', '') for concern in result['concern_flags']],
            'is_content_safe': result['overall_concern_level'] in ['Very Low', 'Low'],
            'recommendation': 'Review content based on the concerns identified above.'
        }
    
    def _generate_educational_explanation(self, concern_type: str, concern_data: Dict, matches: List[str]) -> str:
        """Generate educational explanation for a specific concern."""
        explanation = f"This content shows {concern_data['category'].lower()} concerns. "
        explanation += f"{concern_data['explanation']} "
        explanation += f"Biblical guidance: {concern_data['biblical_perspective']} "
        explanation += f"Consider: {concern_data['alternative_approach']}"
        
        return explanation
    
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