"""
Biblical Themes Configuration

Centralized configuration for biblical themes, patterns, and scripture references.
Extracted and organized from original analysis utilities.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class BiblicalThemesConfig:
    """
    Centralized configuration for biblical themes and patterns.
    
    This class consolidates all theme definitions that were previously
    scattered across multiple analyzer classes.
    """
    
    def __init__(self):
        """Initialize biblical themes configuration."""
        self._load_theme_patterns()
        self._load_scripture_references()
        
        logger.debug(f"BiblicalThemesConfig loaded {len(self.theme_patterns)} themes")
    
    def get_theme_patterns(self) -> Dict[str, Dict[str, float]]:
        """
        Get all theme patterns with their weights.
        
        Returns:
            Dictionary mapping theme names to pattern-weight dictionaries
        """
        return self.theme_patterns
    
    def get_theme_pattern(self, theme_name: str) -> Dict[str, float]:
        """
        Get patterns for a specific theme.
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            Dictionary mapping patterns to weights
        """
        return self.theme_patterns.get(theme_name, {})
    
    def get_scripture_references(self) -> Dict[str, List[str]]:
        """
        Get scripture references by theme.
        
        Returns:
            Dictionary mapping themes to scripture references
        """
        return self.scripture_references
    
    def get_theme_list(self) -> List[str]:
        """
        Get list of all available theme names.
        
        Returns:
            List of theme names
        """
        return list(self.theme_patterns.keys())
    
    def _load_theme_patterns(self) -> None:
        """Load biblical theme patterns with weights."""
        self.theme_patterns = {
            'worship_praise': {
                r'\b(worship|praise|glory|honor|adore|glorify)\b': 1.0,
                r'\b(hallelujah|hosanna|amen|blessed)\b': 1.2,
                r'\b(holy|sacred|divine|almighty)\b': 0.9,
                r'\b(exalt|magnify|lift\s+up|bow\s+down)\b': 1.1,
                r'\b(sanctuary|temple|altar|throne)\b': 0.8
            },
            
            'faith_trust': {
                r'\b(faith|faithful|believe|trust|hope)\b': 1.0,
                r'\b(confidence|assurance|certainty)\b': 0.9,
                r'\b(rely|depend|lean\s+on)\b': 0.8,
                r'\b(doubt|fear|anxiety|worry)\b': -0.5,  # Negative patterns
                r'\b(strength|courage|bold|fearless)\b': 0.7
            },
            
            'salvation_redemption': {
                r'\b(salvation|saved|redeemed|redemption)\b': 1.2,
                r'\b(born\s+again|new\s+life|eternal\s+life)\b': 1.1,
                r'\b(forgiven|forgiveness|mercy|grace)\b': 1.0,
                r'\b(cross|blood|sacrifice|lamb)\b': 0.9,
                r'\b(sin|sinner|repent|repentance)\b': 0.8
            },
            
            'love_grace': {
                r'\b(love|beloved|loving|charity)\b': 1.0,
                r'\b(grace|gracious|mercy|merciful)\b': 1.1,
                r'\b(compassion|kindness|gentleness)\b': 0.9,
                r'\b(forgive|forgiveness|patient|patience)\b': 0.8,
                r'\b(heart|soul|spirit)\b': 0.6
            },
            
            'prayer_communion': {
                r'\b(pray|prayer|praying|intercede)\b': 1.2,
                r'\b(communion|fellowship|presence)\b': 1.0,
                r'\b(seek|seeking|call|calling)\b': 0.8,
                r'\b(meditate|meditation|quiet|still)\b': 0.9,
                r'\b(listen|hear|voice|speak)\b': 0.7
            },
            
            'hope_encouragement': {
                r'\b(hope|hopeful|encourage|encouragement)\b': 1.0,
                r'\b(strength|strengthen|comfort|peace)\b': 0.9,
                r'\b(joy|joyful|rejoice|celebrate)\b': 0.8,
                r'\b(overcome|victory|triumph|conquer)\b': 0.7,
                r'\b(persevere|endure|stand\s+firm)\b': 0.8
            },
            
            'service_discipleship': {
                r'\b(serve|service|servant|ministry)\b': 1.0,
                r'\b(disciple|discipleship|follow|follower)\b': 1.1,
                r'\b(mission|missionary|witness|testify)\b': 0.9,
                r'\b(share|give|giving|generous)\b': 0.8,
                r'\b(help|helping|care|caring)\b': 0.7
            },
            
            'biblical_references': {
                r'\b(scripture|bible|biblical|verse)\b': 1.0,
                r'\b(psalm|psalms|proverbs|matthew|john)\b': 0.9,
                r'\b(genesis|exodus|romans|corinthians)\b': 0.9,
                r'\b(revelation|acts|ephesians|philippians)\b': 0.9,
                r'\b(word|words|testament|gospel)\b': 0.8
            }
        }
    
    def _load_scripture_references(self) -> None:
        """Load supporting scripture references for each theme."""
        self.scripture_references = {
            'worship_praise': [
                'Psalm 150:6 - Let everything that has breath praise the Lord',
                'Psalm 95:6 - Come, let us bow down in worship',
                'John 4:24 - God is spirit, and his worshipers must worship in spirit and truth',
                'Revelation 4:11 - You are worthy, our Lord and God, to receive glory and honor'
            ],
            
            'faith_trust': [
                'Hebrews 11:1 - Faith is confidence in what we hope for',
                'Proverbs 3:5 - Trust in the Lord with all your heart',
                'Romans 10:17 - Faith comes from hearing the message',
                'Mark 11:24 - Whatever you ask for in prayer, believe that you have received it'
            ],
            
            'salvation_redemption': [
                'Ephesians 2:8-9 - For it is by grace you have been saved, through faith',
                'Romans 6:23 - The gift of God is eternal life in Christ Jesus',
                'John 3:16 - For God so loved the world that he gave his one and only Son',
                '1 Peter 1:18-19 - You were redeemed with the precious blood of Christ'
            ],
            
            'love_grace': [
                '1 John 4:8 - Whoever does not love does not know God, because God is love',
                'Romans 5:8 - God demonstrates his own love for us in this: While we were still sinners',
                'Ephesians 2:4-5 - Because of his great love for us, God, who is rich in mercy',
                '1 Corinthians 13:4-7 - Love is patient, love is kind'
            ],
            
            'prayer_communion': [
                '1 Thessalonians 5:17 - Pray continually',
                'Matthew 6:6 - When you pray, go into your room, close the door',
                'Philippians 4:6 - Do not be anxious about anything, but in every situation, by prayer',
                'James 5:16 - The prayer of a righteous person is powerful and effective'
            ],
            
            'hope_encouragement': [
                'Romans 15:13 - May the God of hope fill you with all joy and peace',
                'Jeremiah 29:11 - For I know the plans I have for you, declares the Lord',
                'Isaiah 40:31 - Those who hope in the Lord will renew their strength',
                'Philippians 4:13 - I can do all this through him who gives me strength'
            ],
            
            'service_discipleship': [
                'Matthew 28:19-20 - Therefore go and make disciples of all nations',
                'Mark 10:43 - Whoever wants to become great among you must be your servant',
                'Galatians 5:13 - Serve one another humbly in love',
                '1 Peter 4:10 - Each of you should use whatever gift you have received to serve others'
            ],
            
            'biblical_references': [
                '2 Timothy 3:16 - All Scripture is God-breathed and is useful for teaching',
                'Psalm 119:105 - Your word is a lamp for my feet, a light on my path',
                'Hebrews 4:12 - The word of God is alive and active',
                'Isaiah 55:11 - My word will not return to me empty'
            ]
        } 