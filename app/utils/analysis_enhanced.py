"""
Enhanced Song Analyzer - Comprehensive Biblical Analysis

Smart pattern matching with context awareness and comprehensive biblical analysis
including supporting scripture, detailed themes, and thorough explanations.
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
    Enhanced song analyzer with comprehensive biblical analysis.
    
    Provides:
    - Context-aware pattern matching to reduce false positives
    - Intensity-based scoring for nuanced penalties
    - Comprehensive positive Christian content detection
    - Biblical themes identification with supporting scripture
    - Detailed explanations of analysis decisions
    - User-configurable analysis parameters
    """
    
    def __init__(self, user_id: int, config: Optional[AnalysisConfig] = None):
        """Initialize the enhanced analyzer"""
        self.user_id = user_id
        self.config = config or AnalysisConfig()
        self._setup_enhanced_patterns()
        self._setup_biblical_themes()
        
    def _setup_biblical_themes(self):
        """Setup biblical themes with supporting scripture"""
        self.biblical_themes = {
            'worship_and_praise': {
                'patterns': [
                    r'\b(?:praise|worship|glorify|exalt|magnify)\s+(?:the\s+)?(?:lord|god|jesus|christ)\b',
                    r'\b(?:hallelujah|alleluia|hosanna|amen)\b',
                    r'\b(?:holy|sacred|divine|blessed)\s+(?:is\s+)?(?:the\s+)?(?:lord|god|jesus)\b',
                    r'\b(?:sing|singing)\s+(?:to\s+)?(?:the\s+)?(?:lord|god|jesus)\b',
                    r'\b(?:lift|lifting)\s+(?:up\s+)?(?:my|our)\s+(?:hands|voice|heart)\b'
                ],
                'scripture': {
                    'Psalm 150:6': 'Let everything that has breath praise the Lord. Praise the Lord!',
                    'Psalm 95:1': 'Come, let us sing for joy to the Lord; let us shout aloud to the Rock of our salvation.',
                    'Ephesians 5:19': 'Speaking to one another with psalms, hymns, and songs from the Spirit. Sing and make music from your heart to the Lord.',
                    'Colossians 3:16': 'Let the message of Christ dwell among you richly as you teach and admonish one another with all wisdom through psalms, hymns, and songs from the Spirit, singing to God with gratitude in your hearts.'
                },
                'description': 'Songs that focus on worshiping and praising God'
            },
            'faith_and_trust': {
                'patterns': [
                    r'\b(?:i|we)\s+(?:believe|trust|have\s+faith)\s+in\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:faith|hope|trust)\s+in\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:lean|leaning)\s+on\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:depend|depending)\s+on\s+(?:god|jesus|christ|the\s+lord)\b'
                ],
                'scripture': {
                    'Proverbs 3:5-6': 'Trust in the Lord with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight.',
                    'Hebrews 11:1': 'Now faith is confidence in what we hope for and assurance about what we do not see.',
                    'Romans 10:17': 'Consequently, faith comes from hearing the message, and the message is heard through the word about Christ.',
                    'Psalm 56:3': 'When I am afraid, I put my trust in you.'
                },
                'description': 'Songs expressing faith and trust in God'
            },
            'salvation_and_redemption': {
                'patterns': [
                    r'\b(?:salvation|redemption|eternal\s+life|born\s+again)\b',
                    r'\b(?:saved|redeemed|forgiven|cleansed)\b',
                    r'\b(?:cross|calvary|crucifixion|resurrection)\b',
                    r'\b(?:blood\s+of\s+jesus|blood\s+of\s+christ|blood\s+of\s+the\s+lamb)\b'
                ],
                'scripture': {
                    'Romans 10:9': 'If you declare with your mouth, "Jesus is Lord," and believe in your heart that God raised him from the dead, you will be saved.',
                    'Ephesians 2:8-9': 'For it is by grace you have been saved, through faith—and this is not from yourselves, it is the gift of God—not by works, so that no one can boast.',
                    '1 Peter 1:18-19': 'For you know that it was not with perishable things such as silver or gold that you were redeemed from the empty way of life handed down to you from your ancestors, but with the precious blood of Christ, a lamb without blemish or defect.',
                    'John 3:16': 'For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.'
                },
                'description': 'Songs about salvation through Jesus Christ'
            },
            'love_and_grace': {
                'patterns': [
                    r'\b(?:love|grace|mercy|compassion|kindness)\s+of\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:unconditional\s+love|amazing\s+grace|endless\s+love)\b',
                    r'\b(?:forgiveness|forgiven|mercy|merciful)\b',
                    r'\b(?:god\s+loves|jesus\s+loves|christ\s+loves)\b'
                ],
                'scripture': {
                    '1 John 4:8': 'Whoever does not love does not know God, because God is love.',
                    'Romans 8:38-39': 'For I am convinced that neither death nor life, neither angels nor demons, neither the present nor the future, nor any powers, neither height nor depth, nor anything else in all creation, will be able to separate us from the love of God that is in Christ Jesus our Lord.',
                    'Ephesians 2:4-5': 'But because of his great love for us, God, who is rich in mercy, made us alive with Christ even when we were dead in transgressions—it is by grace you have been saved.',
                    'Lamentations 3:22-23': 'Because of the Lord\'s great love we are not consumed, for his compassions never fail. They are new every morning; great is your faithfulness.'
                },
                'description': 'Songs celebrating God\'s love and grace'
            },
            'prayer_and_communion': {
                'patterns': [
                    r'\b(?:pray|prayer|praying|prayers)\b',
                    r'\b(?:talk|talking|speak|speaking)\s+(?:to|with)\s+(?:god|jesus|christ|the\s+lord)\b',
                    r'\b(?:communion|fellowship)\s+with\s+(?:god|jesus|christ)\b',
                    r'\b(?:quiet\s+time|devotion|devotional)\b'
                ],
                'scripture': {
                    '1 Thessalonians 5:17': 'Pray continually.',
                    'Philippians 4:6': 'Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God.',
                    'Matthew 6:9-11': 'This, then, is how you should pray: "Our Father in heaven, hallowed be your name, your kingdom come, your will be done, on earth as it is in heaven. Give us today our daily bread."',
                    'James 5:16': 'Therefore confess your sins to each other and pray for each other so that you may be healed. The prayer of a righteous person is powerful and effective.'
                },
                'description': 'Songs about prayer and communion with God'
            },
            'spiritual_warfare': {
                'patterns': [
                    r'\bfight\s+(?:the\s+)?(?:good\s+)?fight\b',
                    r'\b(?:spiritual\s+)?(?:battle|warfare)(?:\s+against\s+(?:evil|sin|darkness))?\b',
                    r'\b(?:armor\s+of\s+god|sword\s+of\s+the\s+spirit|shield\s+of\s+faith)\b',
                    r'\b(?:victory|victorious|overcome|overcoming)\s+(?:in\s+)?(?:jesus|christ)\b'
                ],
                'scripture': {
                    'Ephesians 6:11': 'Put on the full armor of God, so that you can take your stand against the devil\'s schemes.',
                    '2 Timothy 4:7': 'I have fought the good fight, I have finished the race, I have kept the faith.',
                    '1 John 5:4': 'For everyone born of God overcomes the world. This is the victory that has overcome the world, even our faith.',
                    'Romans 8:37': 'No, in all these things we are more than conquerors through him who loved us.'
                },
                'description': 'Songs about spiritual warfare and victory in Christ'
            },
            'hope_and_encouragement': {
                'patterns': [
                    r'\b(?:hope|hopeful|encouraged|encouragement)\b',
                    r'\b(?:strength|strengthen|strong)\s+in\s+(?:the\s+)?(?:lord|god|jesus)\b',
                    r'\b(?:peace|peaceful|comfort|comforting)\b',
                    r'\b(?:never\s+give\s+up|persevere|endure)\b'
                ],
                'scripture': {
                    'Jeremiah 29:11': 'For I know the plans I have for you," declares the Lord, "plans to prosper you and not to harm you, plans to give you hope and a future.',
                    'Romans 15:13': 'May the God of hope fill you with all joy and peace as you trust in him, so that you may overflow with hope by the power of the Holy Spirit.',
                    'Isaiah 40:31': 'But those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.',
                    'Philippians 4:13': 'I can do all this through him who gives me strength.'
                },
                'description': 'Songs offering hope and encouragement through faith'
            }
        }
        
        # Compile biblical theme patterns
        self.compiled_biblical_patterns = {}
        for theme, data in self.biblical_themes.items():
            self.compiled_biblical_patterns[theme] = [
                re.compile(pattern, re.IGNORECASE) for pattern in data['patterns']
            ]
    
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
        Analyze a song with comprehensive biblical analysis.
        
        Args:
            song_data: Dictionary containing song metadata
            lyrics: Song lyrics text (can be None or empty)
            
        Returns:
            Dictionary with comprehensive analysis results including biblical themes and supporting scripture
        """
        try:
            # Start with base score
            base_score = 100  # Start with perfect score, deduct for issues
            flags = []
            positive_score = 0
            biblical_themes_found = []
            supporting_scripture = {}
            detailed_concerns = []
            positive_themes = []
            
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
                detailed_concerns.append({
                    'type': 'explicit_content',
                    'severity': 'high',
                    'description': 'Song is marked as explicit by Spotify, indicating potentially inappropriate language or themes',
                    'biblical_concern': 'Christians are called to think on things that are pure and lovely (Philippians 4:8)'
                })
                
            # Analyze lyrics if available
            if lyrics and lyrics.strip():
                lyrics_flags, lyrics_penalty, positive_bonus, themes_found, scripture_refs, concerns, pos_themes = self._analyze_lyrics_comprehensive(lyrics)
                flags.extend(lyrics_flags)
                base_score -= lyrics_penalty
                positive_score += positive_bonus
                biblical_themes_found.extend(themes_found)
                supporting_scripture.update(scripture_refs)
                detailed_concerns.extend(concerns)
                positive_themes.extend(pos_themes)
                
            # Apply positive score boost (this affects the bonus calculation)
            final_positive_bonus = int(positive_score * self.config.positive_boost)
            final_score = min(100, base_score + final_positive_bonus)
            final_score = max(0, final_score)
            
            # Determine concern level with enhanced logic
            concern_level = self._determine_concern_level(final_score, flags)
            
            # Generate comprehensive explanation
            explanation = self._generate_comprehensive_explanation(
                final_score, flags, final_positive_bonus, biblical_themes_found, detailed_concerns, positive_themes
            )
            
            return {
                'christian_score': final_score,
                'explanation': explanation,
                'purity_flags': [self._flag_to_dict(flag) for flag in flags],
                'positive_score_bonus': final_positive_bonus,
                'concern_level': concern_level,
                'biblical_themes': biblical_themes_found,
                'supporting_scripture': supporting_scripture,
                'detailed_concerns': detailed_concerns,
                'positive_themes': positive_themes,
                'analysis_version': 'enhanced_v2_comprehensive'
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis for song {song_data.get('name', 'Unknown')}: {str(e)}")
            # Return safe default
            return {
                'christian_score': 50,
                'explanation': 'Analysis failed - assigned neutral score due to processing error',
                'purity_flags': [],
                'positive_score_bonus': 0,
                'concern_level': 'Medium',
                'biblical_themes': [],
                'supporting_scripture': {},
                'detailed_concerns': [{'type': 'analysis_error', 'description': 'Unable to complete full analysis'}],
                'positive_themes': [],
                'analysis_version': 'enhanced_v2_error'
            }
    
    def _analyze_lyrics_comprehensive(self, lyrics: str) -> Tuple[List[ContentFlag], int, int, List[Dict], Dict, List[Dict], List[Dict]]:
        """Comprehensive lyrics analysis with biblical themes and detailed concerns"""
        flags = []
        total_penalty = 0
        positive_bonus = 0
        biblical_themes_found = []
        supporting_scripture = {}
        detailed_concerns = []
        positive_themes = []
        
        # Analyze negative content with context awareness
        for category in ['profanity', 'drugs', 'violence']:
            category_flags, category_penalty, category_concerns = self._analyze_category_comprehensive(lyrics, category)
            flags.extend(category_flags)
            total_penalty += category_penalty
            detailed_concerns.extend(category_concerns)
            
        # Analyze positive content for bonus points
        positive_matches = self._analyze_positive_content(lyrics)
        positive_bonus = sum(match['bonus'] for match in positive_matches)
        positive_themes = positive_matches
        
        # Analyze biblical themes
        biblical_themes_found, theme_scripture = self._analyze_biblical_themes(lyrics)
        supporting_scripture.update(theme_scripture)
        
        return flags, total_penalty, positive_bonus, biblical_themes_found, supporting_scripture, detailed_concerns, positive_themes
    
    def _analyze_category_comprehensive(self, lyrics: str, category: str) -> Tuple[List[ContentFlag], int, List[Dict]]:
        """Analyze a specific category with comprehensive concern details"""
        flags = []
        total_penalty = 0
        detailed_concerns = []
        
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
                    
                    # Add detailed concern
                    concern = self._create_detailed_concern(category, severity, matches, penalty)
                    if concern:
                        detailed_concerns.append(concern)
                    
                    # Don't double-penalize similar patterns
                    break
                    
        return flags, total_penalty, detailed_concerns
    
    def _create_detailed_concern(self, category: str, severity: str, matches: List[str], penalty: int) -> Dict[str, Any]:
        """Create detailed concern with biblical context"""
        concern_templates = {
            'profanity': {
                'mild': {
                    'description': 'Contains mild profanity or inappropriate language',
                    'biblical_concern': 'Ephesians 4:29 - "Do not let any unwholesome talk come out of your mouths, but only what is helpful for building others up according to their needs, that it may benefit those who listen."'
                },
                'moderate': {
                    'description': 'Contains moderate profanity that may be offensive',
                    'biblical_concern': 'Colossians 3:8 - "But now you must also rid yourselves of all such things as these: anger, rage, malice, slander, and filthy language from your lips."'
                },
                'strong': {
                    'description': 'Contains strong profanity or vulgar language',
                    'biblical_concern': 'Ephesians 5:4 - "Nor should there be obscenity, foolish talk or coarse joking, which are out of place, but rather thanksgiving."'
                }
            },
            'drugs': {
                'moderate': {
                    'description': 'References substance use or drinking that may promote unhealthy behaviors',
                    'biblical_concern': '1 Corinthians 6:19-20 - "Do you not know that your bodies are temples of the Holy Spirit, who is in you, whom you have received from God? You are not your own; you were bought at a price. Therefore honor God with your bodies."'
                },
                'strong': {
                    'description': 'Contains explicit references to illegal drugs or substance abuse',
                    'biblical_concern': '1 Peter 5:8 - "Be alert and of sober mind. Your enemy the devil prowls around like a roaring lion looking for someone to devour."'
                }
            },
            'violence': {
                'moderate': {
                    'description': 'Contains themes of violence, hatred, or aggression',
                    'biblical_concern': 'Matthew 5:39 - "But I tell you, do not resist an evil person. If anyone slaps you on the right cheek, turn to them the other cheek also."'
                },
                'strong': {
                    'description': 'Contains explicit violent imagery or threats',
                    'biblical_concern': 'Romans 12:18 - "If it is possible, as far as it depends on you, live at peace with everyone."'
                }
            }
        }
        
        template = concern_templates.get(category, {}).get(severity)
        if not template:
            return None
            
        return {
            'type': f'{category}_{severity}',
            'severity': severity,
            'description': template['description'],
            'biblical_concern': template['biblical_concern'],
            'examples': matches[:3],  # First 3 examples
            'penalty_applied': penalty
        }
    
    def _analyze_biblical_themes(self, lyrics: str) -> Tuple[List[Dict], Dict]:
        """Analyze lyrics for biblical themes and return supporting scripture"""
        themes_found = []
        supporting_scripture = {}
        
        for theme_name, theme_data in self.biblical_themes.items():
            patterns = self.compiled_biblical_patterns[theme_name]
            matches = []
            
            for pattern in patterns:
                pattern_matches = pattern.findall(lyrics)
                if pattern_matches:
                    matches.extend(pattern_matches)
            
            if matches:
                theme_info = {
                    'theme': theme_name,
                    'description': theme_data['description'],
                    'matches': len(matches),
                    'examples': matches[:3],  # First 3 examples
                    'confidence': min(0.9, 0.5 + (len(matches) * 0.1))  # Higher confidence with more matches
                }
                themes_found.append(theme_info)
                
                # Add supporting scripture for this theme
                supporting_scripture[theme_name] = theme_data['scripture']
        
        return themes_found, supporting_scripture
    
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
                        'examples': matches[:3],  # Keep first 3 examples
                        'description': f'Positive {theme} content detected'
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
    
    def _generate_comprehensive_explanation(self, score: int, flags: List[ContentFlag], positive_bonus: int, 
                                          biblical_themes: List[Dict], detailed_concerns: List[Dict], 
                                          positive_themes: List[Dict]) -> str:
        """Generate comprehensive explanation of the analysis"""
        explanation_parts = []
        
        # Add starting baseline info
        explanation_parts.append(f"**Analysis Summary:** This song received a score of {score}/100 based on comprehensive biblical analysis.")
        explanation_parts.append(f"**Baseline:** Analysis started with a baseline score of 85 points.")
        
        # Add positive content information
        if positive_bonus > 0:
            explanation_parts.append(f"**Positive Content:** Positive Christian content detected (+{positive_bonus} points).")
            if positive_themes:
                theme_names = [theme['theme'] for theme in positive_themes]
                explanation_parts.append(f"**Positive Themes:** {', '.join(theme_names)}")
        
        # Add biblical themes
        if biblical_themes:
            theme_descriptions = [f"{theme['theme'].replace('_', ' ').title()}" for theme in biblical_themes]
            explanation_parts.append(f"**Biblical Themes Identified:** {', '.join(theme_descriptions)}")
        
        # Add concerns
        if detailed_concerns:
            explanation_parts.append("**Areas of Concern:**")
            for concern in detailed_concerns:
                penalty = concern.get('penalty_applied', 0)
                if penalty > 0:
                    explanation_parts.append(f"- {concern['description']} (-{penalty} points)")
                else:
                    explanation_parts.append(f"- {concern['description']}")
        
        # Add flag summary
        if flags:
            flag_summary = {}
            for flag in flags:
                if flag.category not in flag_summary:
                    flag_summary[flag.category] = 0
                flag_summary[flag.category] += flag.penalty
            
            penalty_details = [f"{category}: -{penalty} points" for category, penalty in flag_summary.items()]
            explanation_parts.append(f"**Penalties Applied:** {', '.join(penalty_details)}")
        
        # Add final assessment
        if score >= 85:
            explanation_parts.append("**Assessment:** This song aligns well with Christian values and is suitable for Christian listening.")
        elif score >= 70:
            explanation_parts.append("**Assessment:** This song has some positive elements but may contain content that requires discernment.")
        elif score >= 50:
            explanation_parts.append("**Assessment:** This song contains concerning content that may not align with Christian values.")
        else:
            explanation_parts.append("**Assessment:** This song contains significant content that conflicts with Christian values and is not recommended.")
        
        return " ".join(explanation_parts)
    
    def _flag_to_dict(self, flag: ContentFlag) -> Dict[str, Any]:
        """Convert ContentFlag to dictionary"""
        return {
            'flag': flag.category,
            'category': flag.category,
            'severity': flag.severity,
            'confidence': flag.confidence,
            'penalty_applied': flag.penalty,
            'context': flag.context,
            'details': flag.matched_text
        }

def create_enhanced_analyzer(user_id: int, config: Optional[Dict[str, Any]] = None) -> EnhancedSongAnalyzer:
    """Factory function to create an enhanced analyzer with optional configuration"""
    analysis_config = AnalysisConfig()
    if config:
        for key, value in config.items():
            if hasattr(analysis_config, key):
                setattr(analysis_config, key, value)
    
    return EnhancedSongAnalyzer(user_id=user_id, config=analysis_config) 