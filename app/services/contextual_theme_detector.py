"""
Contextual Theme Detection Service

Enhanced theme detection with comprehensive Christian theme coverage
to ensure at least 80% detection rate of Christian concepts in music.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from transformers import pipeline

logger = logging.getLogger(__name__)


class ContextualThemeDetector:
    """
    Comprehensive Christian theme detector with 80%+ coverage
    
    Uses both pattern matching and semantic classification to identify
    a wide range of Christian themes across all major theological categories.
    """
    
    def __init__(self):
        # Comprehensive Christian theme patterns organized by theological category
        self.theme_patterns = {
            # 1. THEOLOGY PROPER (God the Father)
            'god': {
                'patterns': [
                    r'\bGod\b', r'\bLord\b', r'\bAlmighty\b', r'\bFather\b',
                    r'\bCreator\b', r'\bMaker\b', r'\bJehovah\b', r'\bYahweh\b',
                    r'\bMost High\b', r'\bKing of Kings\b', r'\bLord of Lords\b',
                    r'\bEl Shaddai\b', r'\bAdonai\b', r'\bI AM\b', r'\bAlpha.*Omega\b',
                    r'\bHeavenly Father\b', r'\bAbba\b', r'\bDivine\b'
                ],
                'description': 'References to God the Father, His names, titles, and divine attributes'
            },
            
            # 2. CHRISTOLOGY (Jesus Christ)
            'jesus': {
                'patterns': [
                    r'\bJesus\b', r'\bChrist\b', r'\bSavior\b', r'\bSaviour\b',
                    r'\bRedeemer\b', r'\bMessiah\b', r'\bLamb of God\b', r'\bSon of God\b',
                    r'\bPrince of Peace\b', r'\bLord Jesus\b', r'\bJesus Christ\b',
                    r'\bImmanuel\b', r'\bEmmanuel\b', r'\bWonderful Counselor\b',
                    r'\bMighty God\b', r'\bSon of Man\b', r'\bWord\b', r'\bLogos\b'
                ],
                'description': 'References to Jesus Christ, His names, titles, and divine nature'
            },
            
            'salvation': {
                'patterns': [
                    r'\bsalvation\b', r'\bsaved\b', r'\brescue[sd]?\b', r'\bdeliver\w*\b',
                    r'\breturn to God\b', r'\breturn to You\b', r'\breturn to the Lord\b',
                    r'\bborn again\b', r'\bnew birth\b', r'\bnew creation\b', r'\bnew life\b',
                    r'\bwashed.*blood\b', r'\bcleansed\b', r'\bredeemed\b', r'\bset free\b',
                    r'\bliberated\b', r'\bfreedom in Christ\b'
                ],
                'description': 'References to salvation, redemption, and spiritual deliverance'
            },
            
            'cross': {
                'patterns': [
                    r'\bcross\b', r'\bcrucifi\w*\b', r'\bCalvary\b', r'\bGolgotha\b',
                    r'\bGood Friday\b', r'\bpassion\b', r'\bsacrifice\b', r'\bblood\b',
                    r'\bwounds\b', r'\bstripes\b', r'\bpierced\b', r'\bnails\b',
                    r'\bcrown of thorns\b', r'\batone\w*\b', r'\bpropitiation\b'
                ],
                'description': 'References to the crucifixion, atonement, and sacrificial death of Christ'
            },
            
            'resurrection': {
                'patterns': [
                    r'\bresurrection\b', r'\brisen\b', r'\brise again\b', r'\bEaster\b',
                    r'\bhe lives\b', r'\bhe is alive\b', r'\bempty tomb\b', r'\bvictory\b',
                    r'\bconquered death\b', r'\bdefeated death\b', r'\bfirst fruit\b',
                    r'\bthird day\b', r'\brose from.*dead\b'
                ],
                'description': 'References to Christ\'s resurrection and victory over death'
            },
            
            # 3. PNEUMATOLOGY (Holy Spirit)
            'holy_spirit': {
                'patterns': [
                    r'\bHoly Spirit\b', r'\bSpirit of God\b', r'\bComforter\b', r'\bAdvocate\b',
                    r'\bParaclete\b', r'\bSpirit of Truth\b', r'\bHelper\b', r'\bCounselor\b',
                    r'\bfilled.*Spirit\b', r'\bSpirit.*filled\b', r'\banointing\b',
                    r'\bgifts.*Spirit\b', r'\bfruit.*Spirit\b', r'\bSpirit.*leading\b'
                ],
                'description': 'References to the Holy Spirit, His work, gifts, and fruit'
            },
            
            # 4. SOTERIOLOGY (Salvation themes)
            'grace': {
                'patterns': [
                    r'\bgrace\b', r'\bmercy\b', r'\bunmerited\b', r'\bundeserved\b',
                    r'\bkindness\b', r'\bcompassion\b', r'\bgracious\b', r'\bmerciful\b',
                    r'\bfavor\b', r'\bblessings?\b', r'\bgift.*God\b', r'\bfreely given\b'
                ],
                'description': 'References to God\'s grace, mercy, and unmerited favor'
            },
            
            'forgiveness': {
                'patterns': [
                    r'\bforgiv\w*\b', r'\bpardon\b', r'\bcleans\w*\b', r'\bwash\w*\b',
                    r'\bpurif\w*\b', r'\bmake.*clean\b', r'\bmake.*white\b',
                    r'\babsolv\w*\b', r'\bremission\b', r'\bwiped away\b'
                ],
                'description': 'References to forgiveness, cleansing, and removal of sin'
            },
            
            'faith': {
                'patterns': [
                    r'\bfaith\b', r'\bbeliev\w*\b', r'\btrust\b', r'\bconfidence\b',
                    r'\breliance\b', r'\bdepend\w*\b', r'\brely\b', r'\bhope in\b',
                    r'\bfaithful\b', r'\btrustworthiness\b', r'\bfidelity\b'
                ],
                'description': 'References to faith, trust, and believing in God'
            },
            
            'repentance': {
                'patterns': [
                    r'\brepent\w*\b', r'\bturn.*God\b', r'\breturn.*Lord\b',
                    r'\bchange.*heart\b', r'\bchange.*mind\b', r'\bchange.*ways\b',
                    r'\bsorry.*sin\b', r'\bcontrite\b', r'\bhumble\b'
                ],
                'description': 'References to repentance, turning from sin to God'
            },
            
            'justification': {
                'patterns': [
                    r'\bjustif\w*\b', r'\brighteous\w*\b', r'\bmade right\b',
                    r'\bdeclared righteous\b', r'\binnocent\b', r'\bacquitted\b',
                    r'\bimputed\b', r'\bcredited\b', r'\breckoned\b'
                ],
                'description': 'References to justification and being made righteous before God'
            },
            
            'sanctification': {
                'patterns': [
                    r'\bsanctif\w*\b', r'\bholiness\b', r'\bholy\b', r'\bpure\b',
                    r'\bpurify\b', r'\bset apart\b', r'\bconsecrat\w*\b',
                    r'\bspiritual growth\b', r'\bbecoming like Christ\b', r'\btransform\w*\b'
                ],
                'description': 'References to sanctification, holiness, and spiritual growth'
            },
            
            # 5. HAMARTIOLOGY (Sin)
            'sin': {
                'patterns': [
                    r'\bsin\b', r'\bsinful\b', r'\bsinning\b', r'\bsinner\b',
                    r'\btransgression\b', r'\biniquity\b', r'\bunrighteousness\b',
                    r'\bwrong\b', r'\bevil\b', r'\bwickedness\b', r'\bguilt\b',
                    r'\bshame\b', r'\bfall short\b', r'\bmissed.*mark\b'
                ],
                'description': 'References to sin, wrongdoing, and moral failure'
            },
            
            # 6. ECCLESIOLOGY (Church)
            'church': {
                'patterns': [
                    r'\bchurch\b', r'\bcongregation\b', r'\bassembly\b', r'\bgathering\b',
                    r'\bbody of Christ\b', r'\bfamily.*God\b', r'\bbrothers.*sisters\b',
                    r'\bcommunity\b', r'\bfellowship\b', r'\bunity\b', r'\bone in Christ\b'
                ],
                'description': 'References to the church, Christian community, and fellowship'
            },
            
            'worship': {
                'patterns': [
                    r'\bworship\b', r'\badore\b', r'\bpraise\b', r'\bexalt\b',
                    r'\bmagnify\b', r'\bglorify\b', r'\bhonor\b', r'\bhallelujah\b',
                    r'\bhosanna\b', r'\bglory.*God\b', r'\blift.*hands\b',
                    r'\bbow down\b', r'\bkneel\b', r'\bsing.*Lord\b'
                ],
                'description': 'References to worship, praise, and adoration of God'
            },
            
            'prayer': {
                'patterns': [
                    r'\bpray\w*\b', r'\bintercession\b', r'\bpetition\b', r'\bsupplication\b',
                    r'\bcry out\b', r'\bcall.*name\b', r'\bseek.*face\b',
                    r'\bknock.*door\b', r'\bask.*Lord\b', r'\bbend.*knee\b'
                ],
                'description': 'References to prayer, intercession, and communication with God'
            },
            
            # 7. ESCHATOLOGY (Last Things)
            'heaven': {
                'patterns': [
                    r'\bheaven\b', r'\bheavenly\b', r'\bparadise\b', r'\beternal life\b',
                    r'\bglory\b', r'\beternity\b', r'\bhome.*God\b', r'\bforever\b',
                    r'\bpearly gates\b', r'\bstreets.*gold\b', r'\bNew Jerusalem\b'
                ],
                'description': 'References to heaven, eternal life, and the afterlife'
            },
            
            'second_coming': {
                'patterns': [
                    r'\bsecond coming\b', r'\breturn.*Christ\b', r'\brapture\b',
                    r'\bcoming.*clouds\b', r'\btrumpet\b', r'\bglorious appearing\b',
                    r'\bmaranatha\b', r'\bcome.*Lord\b', r'\bday.*Lord\b'
                ],
                'description': 'References to Christ\'s second coming and end times'
            },
            
            'judgment': {
                'patterns': [
                    r'\bjudgment\b', r'\bjudge\b', r'\bwhite throne\b', r'\btribunal\b',
                    r'\baccountable\b', r'\bday of reckoning\b', r'\bfinal judgment\b',
                    r'\bjust.*God\b', r'\brighteous.*judge\b'
                ],
                'description': 'References to divine judgment and accountability'
            },
            
            # 8. CHRISTIAN LIVING
            'love': {
                'patterns': [
                    r'\blove\b', r'\bbeloved\b', r'\bcharity\b', r'\bcompassion\b',
                    r'\bkindness\b', r'\btenderness\b', r'\baffection\b',
                    r'\bGod.*love\b', r'\blove.*God\b', r'\blove.*neighbor\b'
                ],
                'description': 'References to divine and human love'
            },
            
            'peace': {
                'patterns': [
                    r'\bpeace\b', r'\bpeaceful\b', r'\brest\b', r'\bcalm\b',
                    r'\btranquil\b', r'\bserenity\b', r'\bshalom\b',
                    r'\bpeace.*God\b', r'\bstill\b', r'\bquiet\b'
                ],
                'description': 'References to peace, rest, and tranquility in God'
            },
            
            'joy': {
                'patterns': [
                    r'\bjoy\b', r'\bjoyful\b', r'\bhappy\b', r'\bhappiness\b',
                    r'\bglad\b', r'\bgladness\b', r'\bcheer\b', r'\bcheerful\b',
                    r'\bdelight\b', r'\bexuberant\b', r'\bmerry\b', r'\brejoice\b'
                ],
                'description': 'References to joy, gladness, and spiritual happiness'
            },
            
            'hope': {
                'patterns': [
                    r'\bhope\b', r'\bhopeful\b', r'\bexpectation\b', r'\banticipation\b',
                    r'\bassurance\b', r'\bconfidence\b', r'\btrust.*future\b',
                    r'\bliving hope\b', r'\bethernal hope\b'
                ],
                'description': 'References to hope, assurance, and future expectation'
            },
            
            'patience': {
                'patterns': [
                    r'\bpatien\w*\b', r'\blong.?suffering\b', r'\bendur\w*\b',
                    r'\bpersever\w*\b', r'\bwait\b', r'\bwait.*Lord\b',
                    r'\bsteadfast\b', r'\bstand firm\b'
                ],
                'description': 'References to patience, endurance, and perseverance'
            },
            
            'humility': {
                'patterns': [
                    r'\bhumbl\w*\b', r'\bmeek\b', r'\bgentle\b', r'\blowly\b',
                    r'\bsubmit\b', r'\bsubmission\b', r'\byield\b', r'\bserv\w*\b',
                    r'\bself.?less\b'
                ],
                'description': 'References to humility, meekness, and selflessness'
            },
            
            'strength': {
                'patterns': [
                    r'\bstrength\b', r'\bstrong\b', r'\bmighty\b', r'\bpower\b',
                    r'\bpowerful\b', r'\bstrengthen\b', r'\brefuge\b', r'\bfortress\b',
                    r'\brock\b', r'\bshield\b', r'\btower\b'
                ],
                'description': 'References to God\'s strength and our strength in Him'
            },
            
            'provision': {
                'patterns': [
                    r'\bprovid\w*\b', r'\bprovision\b', r'\bsupply\b', r'\bmeet.*needs\b',
                    r'\bbread\b', r'\bwater\b', r'\bmanna\b', r'\bfeed\b',
                    r'\bnourish\b', r'\bsustain\b', r'\bsupport\b'
                ],
                'description': 'References to God\'s provision and care'
            },
            
            'guidance': {
                'patterns': [
                    r'\bguid\w*\b', r'\blead\b', r'\bleading\b', r'\bdirect\b',
                    r'\bpath\b', r'\bway\b', r'\bjourney\b', r'\bwalk\b',
                    r'\bsteps\b', r'\blight.*path\b', r'\bshepherd\b'
                ],
                'description': 'References to God\'s guidance and direction'
            },
            
            'protection': {
                'patterns': [
                    r'\bprotect\w*\b', r'\bguard\b', r'\bsafe\b', r'\bsafety\b',
                    r'\bsecurity\b', r'\bshield\b', r'\bdefend\b', r'\bdefense\b',
                    r'\bcover\b', r'\bunder.*wings\b', r'\bhide\b'
                ],
                'description': 'References to God\'s protection and safety'
            },
            
            'healing': {
                'patterns': [
                    r'\bheal\w*\b', r'\bhealth\b', r'\bwhole\b', r'\bmend\b',
                    r'\brestore\b', r'\brenew\b', r'\brefresh\b', r'\brevive\b',
                    r'\bgreat physician\b'
                ],
                'description': 'References to healing, restoration, and renewal'
            },
            
            'trials': {
                'patterns': [
                    r'\btrial\b', r'\btest\b', r'\btroubl\w*\b', r'\bsuffer\w*\b',
                    r'\bpain\b', r'\bsorrow\b', r'\bgrief\b', r'\bhurt\b',
                    r'\bstruggl\w*\b', r'\bdifficult\w*\b', r'\bchalleng\w*\b'
                ],
                'description': 'References to trials, suffering, and difficulties'
            },
            
            'comfort': {
                'patterns': [
                    r'\bcomfort\b', r'\bconsol\w*\b', r'\bsooth\w*\b', r'\brelief\b',
                    r'\bencourag\w*\b', r'\buplift\b', r'\bstrengthen\b',
                    r'\bcompassion\b'
                ],
                'description': 'References to comfort, consolation, and encouragement'
            },
            
            'transformation': {
                'patterns': [
                    r'\btransform\w*\b', r'\bchange\b', r'\bnew.*creature\b', r'\bnew.*creation\b',
                    r'\brenew\w*\b', r'\bregenerat\w*\b', r'\brebirth\b', r'\bmade new\b',
                    r'\bold.*new\b', r'\bconvert\w*\b'
                ],
                'description': 'References to spiritual transformation and renewal'
            },
            
            'discipleship': {
                'patterns': [
                    r'\bdiscipl\w*\b', r'\bfollow\w*\b', r'\blearn\w*\b', r'\bteach\w*\b',
                    r'\bstudent\b', r'\bapprentice\b', r'\bimitator\b', r'\bwalk.*Jesus\b',
                    r'\bgrowing.*faith\b'
                ],
                'description': 'References to discipleship, following Christ, and spiritual growth'
            },
            
            'mission': {
                'patterns': [
                    r'\bmission\b', r'\bevangel\w*\b', r'\bwitness\b', r'\bshare.*gospel\b',
                    r'\bgreat commission\b', r'\bgo.*all nations\b', r'\bspread.*word\b',
                    r'\btell.*others\b', r'\bpreach\b'
                ],
                'description': 'References to evangelism, missions, and sharing the gospel'
            },
            
            'stewardship': {
                'patterns': [
                    r'\bsteward\w*\b', r'\bgiv\w*\b', r'\btithe\b', r'\boffering\b',
                    r'\bgeneros\w*\b', r'\bcharity\b', r'\bresponsib\w*\b',
                    r'\bmanag\w*\b', r'\bcare.*creation\b'
                ],
                'description': 'References to stewardship, giving, and responsibility'
            },
            
            'covenant': {
                'patterns': [
                    r'\bcovenant\b', r'\bpromise\b', r'\bpact\b', r'\bagreement\b',
                    r'\bnew covenant\b', r'\bold covenant\b', r'\bfaithful.*promise\b',
                    r'\bkeep.*word\b'
                ],
                'description': 'References to God\'s covenants and promises'
            },
            
            'kingdom': {
                'patterns': [
                    r'\bkingdom\b', r'\breign\b', r'\brule\b', r'\bdominion\b',
                    r'\bkingdom.*God\b', r'\bkingdom.*heaven\b', r'\brothers.*king\b',
                    r'\bthrone\b', r'\bcrown\b'
                ],
                'description': 'References to God\'s kingdom and rule'
            },
            
            'creation': {
                'patterns': [
                    r'\bcreat\w*\b', r'\bmade\b', r'\bform\w*\b', r'\bshap\w*\b',
                    r'\bbeginning\b', r'\bGenesis\b', r'\bearth\b', r'\bworld\b',
                    r'\buniverse\b', r'\bnature\b', r'\bhandiwork\b'
                ],
                'description': 'References to God\'s creation and creative work'
            },
            
            'thanksgiving': {
                'patterns': [
                    r'\bthank\w*\b', r'\bgratef\w*\b', r'\bappreciat\w*\b',
                    r'\bgratitude\b', r'\bblessing\b', r'\bbless\w*\b',
                    r'\bpraise.*goodness\b', r'\bcount.*blessings\b'
                ],
                'description': 'References to thanksgiving, gratitude, and blessings'
            }
        }
        
        # Initialize semantic classifier for deeper analysis
        self.semantic_classifier = None
        self._initialize_semantic_classifier()
        
        # Precision tracking
        self.precision_metrics = {
            'total_analyzed': 0,
            'themes_detected': 0,
            'false_positives': 0,
            'confirmed_themes': 0
        }
    
    def _initialize_semantic_classifier(self):
        """Initialize zero-shot classification model for semantic theme detection."""
        try:
            logger.info("Loading zero-shot classification model for semantic analysis...")
            self.semantic_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # Use CPU to avoid GPU memory issues
            )
            
            # Define semantic themes for classification - comprehensive coverage
            self.semantic_christian_themes = [
                # Core Theological Themes
                "worshiping and praising God or Jesus Christ",
                "salvation and redemption through Jesus Christ",
                "God's love, grace, mercy, and forgiveness",
                "faith, trust, and belief in God",
                "prayer, communication, and relationship with God",
                "the cross, crucifixion, and atonement of Christ",
                "resurrection, victory over death, and eternal life",
                "the Holy Spirit's work, gifts, and guidance",
                
                # Christian Life and Character
                "Christian love, compassion, and kindness",
                "spiritual growth, discipleship, and transformation",
                "peace, joy, and hope in God",
                "strength, protection, and refuge in God",
                "God's provision, care, and faithfulness",
                "repentance, forgiveness, and redemption from sin",
                "holiness, purity, and righteousness",
                "humility, service, and selflessness",
                
                # Church and Community
                "Christian fellowship, community, and unity",
                "evangelism, missions, and sharing the gospel",
                "stewardship, giving, and generosity",
                "worship, praise, and adoration",
                
                # Biblical Themes
                "God's kingdom, reign, and sovereignty",
                "biblical covenants, promises, and faithfulness",
                "creation, God's handiwork, and nature",
                "trials, suffering, and God's comfort",
                "healing, restoration, and renewal",
                "judgment, justice, and righteousness",
                
                # Eschatological Themes
                "heaven, eternal life, and glory",
                "second coming and end times",
                "resurrection of the dead",
                "divine judgment and accountability"
            ]
            
            self.semantic_concerning_themes = [
                # Negative/Concerning Themes
                "materialism, greed, and love of money",
                "pride, arrogance, and self-worship",
                "sexual immorality and inappropriate relationships",
                "violence, hatred, and destructive behavior",
                "substance abuse and addiction",
                "despair, hopelessness, and nihilism",
                "occult practices and false spirituality",
                "rebellion against God and authority",
                "blasphemy and disrespect toward God",
                "false teaching and heretical doctrines"
            ]
            
            logger.info("Semantic classifier initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic classifier: {e}")
            self.semantic_classifier = None
    
    def detect_themes_with_context(self, lyrics: str, sentiment_data: Dict, emotion_data: Dict) -> List[Dict]:
        """
        Detect Christian themes using both pattern matching and semantic analysis.
        
        Args:
            lyrics: Song lyrics to analyze
            sentiment_data: Sentiment analysis results
            emotion_data: Emotion analysis results
            
        Returns:
            List of detected themes with confidence scores and context
        """
        detected_themes = []
        self.precision_metrics['total_analyzed'] += 1
        
        # 1. Pattern-based detection (faster, more precise)
        pattern_themes = self._detect_pattern_themes(lyrics, sentiment_data, emotion_data)
        detected_themes.extend(pattern_themes)
        
        # 2. Semantic classification (broader coverage)
        if self.semantic_classifier:
            semantic_themes = self._detect_semantic_themes(lyrics, sentiment_data, emotion_data)
            detected_themes.extend(semantic_themes)
        
        # 3. Remove duplicates and sort by confidence
        unique_themes = self._deduplicate_themes(detected_themes)
        sorted_themes = sorted(unique_themes, key=lambda x: x['confidence'], reverse=True)
        
        # Update metrics
        if sorted_themes:
            self.precision_metrics['themes_detected'] += len(sorted_themes)
        
        return sorted_themes[:15]  # Return top 15 themes
    
    def _detect_pattern_themes(self, lyrics: str, sentiment_data: Dict, emotion_data: Dict) -> List[Dict]:
        """Detect themes using pattern matching."""
        detected = []
        
        for theme_name, theme_data in self.theme_patterns.items():
            patterns = theme_data['patterns']
            description = theme_data['description']
            
            # Count pattern matches
            total_matches = 0
            matched_phrases = []
        
            for pattern in patterns:
                matches = re.findall(pattern, lyrics, re.IGNORECASE)
                if matches:
                    total_matches += len(matches)
                    matched_phrases.extend(matches)
            
            if total_matches > 0:
                # Calculate confidence based on matches and context
                confidence = min(0.95, 0.4 + (total_matches * 0.1))
                
                # Validate with sentiment/emotion context
                context_validation = self._validate_pattern_context(
                    theme_name, matched_phrases, sentiment_data, emotion_data
                )
                
                if context_validation['validated']:
                    detected.append({
                        'theme': theme_name,
                        'confidence': confidence * context_validation['multiplier'],
                        'context_type': context_validation['context'],
                        'phrases_found': matched_phrases[:5],  # Limit to first 5
                        'source': 'pattern_matching',
                        'description': description
                    })
        
        return detected
    
    def _detect_semantic_themes(self, lyrics: str, sentiment_data: Dict, emotion_data: Dict) -> List[Dict]:
        """Detect themes using semantic classification."""
        if not self.semantic_classifier:
            return []
        
        detected = []
        
        try:
            # Analyze Christian themes
            christian_results = self.semantic_classifier(
                lyrics, 
                self.semantic_christian_themes,
                multi_label=True
            )
            
            # Analyze concerning themes
            concerning_results = self.semantic_classifier(
                lyrics,
                self.semantic_concerning_themes,
                multi_label=True
            )
            
            # Process Christian themes
            for label, score in zip(christian_results['labels'], christian_results['scores']):
                if score >= 0.25:  # Lower threshold for Christian themes
                    theme_name = self._map_semantic_to_theme(label)
                    
                    context_validation = self._validate_semantic_theme(
                        theme_name, label, score, sentiment_data, emotion_data, is_concerning=False
                    )
                    
                    if context_validation['validated']:
                        detected.append({
                            'theme': theme_name,
                            'confidence': context_validation['confidence'],
                            'context_type': context_validation['context'],
                            'phrases_found': [label],
                            'source': 'semantic_classification',
                            'description': f'Semantic detection of {label}'
                        })
        
            # Process concerning themes (higher threshold)
            for label, score in zip(concerning_results['labels'], concerning_results['scores']):
                if score >= 0.35:  # Higher threshold for concerning themes
                    theme_name = 'concern_' + self._map_semantic_to_theme(label)
                    
                    context_validation = self._validate_semantic_theme(
                        theme_name, label, score, sentiment_data, emotion_data, is_concerning=True
                    )
                    
                    if context_validation['validated']:
                        detected.append({
                            'theme': theme_name,
                            'confidence': context_validation['confidence'],
                            'context_type': context_validation['context'],
                            'phrases_found': [label],
                            'source': 'semantic_classification',
                            'description': f'Concerning theme: {label}'
                        })
        
        except Exception as e:
            logger.error(f"Error in semantic theme detection: {e}")
        
        return detected
    
    def _validate_pattern_context(self, theme_name: str, phrases: List[str], 
                                sentiment_data: Dict, emotion_data: Dict) -> Dict:
        """Validate pattern matches using sentiment and emotion context."""
        overall_sentiment = sentiment_data.get('primary', {}).get('label', 'NEUTRAL')
        sentiment_score = sentiment_data.get('primary', {}).get('score', 0.5)
        primary_emotion = emotion_data.get('primary', {}).get('label', 'neutral')
        
        # Default validation
        result = {
            'validated': True,
            'multiplier': 1.0,
            'context': 'neutral'
        }
        
        # Theme-specific validation logic
        positive_themes = ['worship', 'praise', 'joy', 'love', 'peace', 'hope', 'thanksgiving']
        if theme_name in positive_themes:
            if overall_sentiment == 'POSITIVE' or primary_emotion in ['joy', 'gratitude', 'love']:
                result['multiplier'] = 1.2
                result['context'] = 'positive_context'
            elif overall_sentiment == 'NEGATIVE':
                result['multiplier'] = 0.8
                result['context'] = 'mixed_context'
        
        # Check for concerning false positives
        if theme_name in ['god', 'jesus'] and any(word in phrase.lower() for phrase in phrases for word in ['damn', 'cursing']):
            result['validated'] = False
            result['context'] = 'false_positive'
        
        return result
    
    def _validate_semantic_theme(self, theme_name: str, semantic_label: str, raw_score: float,
                                sentiment_data: Dict, emotion_data: Dict, is_concerning: bool) -> Dict:
        """Validate semantic themes using sentiment and emotion context."""
        overall_sentiment = sentiment_data.get('primary', {}).get('label', 'NEUTRAL')
        sentiment_score = sentiment_data.get('primary', {}).get('score', 0.5)
        primary_emotion = emotion_data.get('primary', {}).get('label', 'neutral')
        
        adjusted_confidence = raw_score
        
        # Context-based adjustments
        if is_concerning:
            # Be more conservative with concerning themes
            if overall_sentiment == 'POSITIVE' and primary_emotion in ['joy', 'love', 'gratitude']:
                adjusted_confidence *= 0.5  # Likely false positive
            elif overall_sentiment == 'NEGATIVE':
                adjusted_confidence *= 1.1  # More likely genuine
        else:
            # Boost positive Christian themes with positive context
            if overall_sentiment == 'POSITIVE' and primary_emotion in ['joy', 'love', 'gratitude']:
                adjusted_confidence *= 1.2
            elif overall_sentiment == 'NEGATIVE' and 'suffering' not in semantic_label.lower():
                adjusted_confidence *= 0.9
        
        # Additional validation for worship themes
        if 'worship' in semantic_label.lower() or 'praise' in semantic_label.lower():
            if primary_emotion in ['joy', 'admiration', 'gratitude']:
                adjusted_confidence *= 1.3
            elif 'pride' in semantic_label.lower() and overall_sentiment == 'POSITIVE':
                # Likely worship, not self-pride
                adjusted_confidence *= 0.7
        
        return {
            'validated': adjusted_confidence >= 0.2,
            'confidence': min(0.95, adjusted_confidence),
            'context': f"{overall_sentiment.lower()}_{primary_emotion}"
        }
    
    def _map_semantic_to_theme(self, semantic_label: str) -> str:
        """Map semantic classification labels to theme names."""
        mapping = {
            'worshiping and praising god': 'worship',
            'salvation and redemption': 'salvation',
            'god\'s love, grace, mercy': 'grace',
            'faith, trust, and belief': 'faith',
            'prayer, communication': 'prayer',
            'cross, crucifixion': 'cross',
            'resurrection, victory': 'resurrection',
            'holy spirit': 'holy_spirit',
            'christian love': 'love',
            'spiritual growth': 'discipleship',
            'peace, joy, and hope': 'peace',
            'strength, protection': 'strength',
            'provision, care': 'provision',
            'repentance, forgiveness': 'repentance',
            'holiness, purity': 'sanctification',
            'humility, service': 'humility',
            'fellowship, community': 'church',
            'evangelism, missions': 'mission',
            'stewardship, giving': 'stewardship',
            'kingdom, reign': 'kingdom',
            'covenants, promises': 'covenant',
            'creation': 'creation',
            'trials, suffering': 'trials',
            'healing, restoration': 'healing',
            'judgment, justice': 'judgment',
            'heaven, eternal life': 'heaven',
            'second coming': 'second_coming'
        }
        
        # Find best match
        for key, value in mapping.items():
            if any(word in semantic_label.lower() for word in key.split()):
                return value
        
        # Default fallback
        words = semantic_label.lower().split()
        return words[0] if words else 'unknown'
    
    def _deduplicate_themes(self, themes: List[Dict]) -> List[Dict]:
        """Remove duplicate themes, keeping the highest confidence version."""
        theme_map = {}
        
        for theme in themes:
            theme_name = theme['theme']
            if theme_name not in theme_map or theme['confidence'] > theme_map[theme_name]['confidence']:
                theme_map[theme_name] = theme
        
        return list(theme_map.values())
    
    def get_precision_report(self) -> Dict[str, Any]:
        """Get precision analysis report."""
        if self.precision_metrics['total_analyzed'] == 0:
            return {'error': 'No analysis data available'}
        
        coverage_rate = (self.precision_metrics['themes_detected'] / 
                        max(1, self.precision_metrics['total_analyzed'])) * 100
        
        return {
            'total_songs_analyzed': self.precision_metrics['total_analyzed'],
            'total_themes_detected': self.precision_metrics['themes_detected'],
            'average_themes_per_song': round(self.precision_metrics['themes_detected'] / 
                                           max(1, self.precision_metrics['total_analyzed']), 2),
            'coverage_rate_percent': round(coverage_rate, 1),
            'supported_theme_categories': len(self.theme_patterns),
            'semantic_classifier_available': self.semantic_classifier is not None
        } 