"""
Enhanced Biblical Reference Detection Algorithm
Comprehensive system for detecting biblical references, themes, names, and concepts in song lyrics.
"""

import re
import json
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

@dataclass
class BiblicalMatch:
    """Represents a detected biblical reference"""
    type: str  # 'scripture', 'name', 'theme', 'concept'
    confidence: float
    matched_text: str
    context: str
    reference: Optional[str] = None
    verse_text: Optional[str] = None
    category: Optional[str] = None

class EnhancedBiblicalDetector:
    """Enhanced biblical reference detection with comprehensive pattern matching"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_scripture_patterns()
        self._setup_biblical_names()
        self._setup_enhanced_themes()
        self._setup_biblical_concepts()
        self._setup_verses_database()
        
    def _setup_scripture_patterns(self):
        """Setup comprehensive scripture reference patterns"""
        # Bible books with common abbreviations
        self.bible_books = {
            # Old Testament
            'genesis': ['gen', 'gn'],
            'exodus': ['exod', 'ex'],
            'leviticus': ['lev', 'lv'],
            'numbers': ['num', 'nm'],
            'deuteronomy': ['deut', 'dt'],
            'joshua': ['josh', 'jos'],
            'judges': ['judg', 'jdg'],
            'ruth': ['ru'],
            '1 samuel': ['1 sam', '1sam', 'i samuel', 'i sam'],
            '2 samuel': ['2 sam', '2sam', 'ii samuel', 'ii sam'],
            '1 kings': ['1 kgs', '1kgs', 'i kings', 'i kgs'],
            '2 kings': ['2 kgs', '2kgs', 'ii kings', 'ii kgs'],
            '1 chronicles': ['1 chr', '1chr', 'i chronicles', 'i chr'],
            '2 chronicles': ['2 chr', '2chr', 'ii chronicles', 'ii chr'],
            'ezra': ['ezr'],
            'nehemiah': ['neh'],
            'esther': ['est'],
            'job': ['jb'],
            'psalm': ['ps', 'psa', 'psalms'],
            'proverbs': ['prov', 'prv'],
            'ecclesiastes': ['eccl', 'ecc'],
            'song of solomon': ['song', 'sos', 'song of songs'],
            'isaiah': ['isa', 'is'],
            'jeremiah': ['jer'],
            'lamentations': ['lam'],
            'ezekiel': ['ezek', 'ezk'],
            'daniel': ['dan', 'dn'],
            'hosea': ['hos'],
            'joel': ['joe'],
            'amos': ['am'],
            'obadiah': ['obad', 'ob'],
            'jonah': ['jon'],
            'micah': ['mic'],
            'nahum': ['nah'],
            'habakkuk': ['hab'],
            'zephaniah': ['zeph', 'zep'],
            'haggai': ['hag'],
            'zechariah': ['zech', 'zec'],
            'malachi': ['mal'],
            
            # New Testament
            'matthew': ['matt', 'mt'],
            'mark': ['mk'],
            'luke': ['lk'],
            'john': ['jn'],
            'acts': ['ac'],
            'romans': ['rom', 'rm'],
            '1 corinthians': ['1 cor', '1cor', 'i corinthians', 'i cor'],
            '2 corinthians': ['2 cor', '2cor', 'ii corinthians', 'ii cor'],
            'galatians': ['gal'],
            'ephesians': ['eph'],
            'philippians': ['phil', 'php'],
            'colossians': ['col'],
            '1 thessalonians': ['1 thess', '1thess', 'i thessalonians', 'i thess'],
            '2 thessalonians': ['2 thess', '2thess', 'ii thessalonians', 'ii thess'],
            '1 timothy': ['1 tim', '1tim', 'i timothy', 'i tim'],
            '2 timothy': ['2 tim', '2tim', 'ii timothy', 'ii tim'],
            'titus': ['tit'],
            'philemon': ['phlm', 'phm'],
            'hebrews': ['heb'],
            'james': ['jas', 'jm'],
            '1 peter': ['1 pet', '1pet', 'i peter', 'i pet'],
            '2 peter': ['2 pet', '2pet', 'ii peter', 'ii pet'],
            '1 john': ['1 jn', '1jn', 'i john', 'i jn'],
            '2 john': ['2 jn', '2jn', 'ii john', 'ii jn'],
            '3 john': ['3 jn', '3jn', 'iii john', 'iii jn'],
            'jude': ['jud'],
            'revelation': ['rev']
        }
        
        # Create all possible book patterns
        all_book_patterns = []
        for book, abbreviations in self.bible_books.items():
            all_patterns = [book] + abbreviations
            all_book_patterns.extend(all_patterns)
        
        # Scripture reference patterns
        book_pattern = '|'.join(re.escape(book) for book in sorted(all_book_patterns, key=len, reverse=True))
        
        self.scripture_patterns = [
            # Full references like "John 3:16" or "1 Corinthians 13:4-7"
            rf'\b({book_pattern})\s+(\d+):(\d+)(?:-(\d+))?\b',
            # Chapter only like "Psalm 23" or "Romans 8"
            rf'\b({book_pattern})\s+(\d+)\b',
            # Verse ranges like "John 3:16-17"
            rf'\b({book_pattern})\s+(\d+):(\d+)-(\d+)\b',
        ]
        
        self.compiled_scripture_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.scripture_patterns]
        
    def _setup_biblical_names(self):
        """Setup comprehensive biblical names database"""
        self.biblical_names = {
            # Divine names and titles
            'divine': {
                'names': ['god', 'lord', 'jehovah', 'yahweh', 'elohim', 'adonai', 'el shaddai', 'father', 'abba'],
                'jesus': ['jesus', 'christ', 'yeshua', 'messiah', 'savior', 'redeemer', 'lamb of god', 'son of god', 'king of kings', 'lord of lords'],
                'holy_spirit': ['holy spirit', 'spirit', 'comforter', 'advocate', 'paraclete']
            },
            
            # Old Testament figures
            'old_testament': {
                'patriarchs': ['abraham', 'isaac', 'jacob', 'israel', 'joseph'],
                'prophets': ['moses', 'elijah', 'elisha', 'isaiah', 'jeremiah', 'ezekiel', 'daniel', 'jonah', 'samuel'],
                'kings': ['david', 'solomon', 'saul', 'hezekiah', 'josiah'],
                'judges': ['gideon', 'samson', 'deborah', 'jephthah'],
                'women': ['sarah', 'rebekah', 'rachel', 'leah', 'miriam', 'ruth', 'esther', 'hannah'],
                'others': ['noah', 'job', 'caleb', 'joshua', 'nehemiah', 'ezra']
            },
            
            # New Testament figures
            'new_testament': {
                'apostles': ['peter', 'paul', 'john', 'james', 'andrew', 'philip', 'bartholomew', 'matthew', 'thomas', 'simon', 'judas'],
                'disciples': ['mary magdalene', 'martha', 'mary', 'lazarus', 'nicodemus'],
                'others': ['john the baptist', 'stephen', 'barnabas', 'timothy', 'titus']
            }
        }
        
        # Compile name patterns for better matching
        all_names = []
        for category in self.biblical_names.values():
            for subcategory in category.values():
                all_names.extend(subcategory)
        
        self.name_patterns = [rf'\b{re.escape(name)}\b' for name in all_names]
        self.compiled_name_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.name_patterns]
        
    def _setup_enhanced_themes(self):
        """Setup enhanced biblical themes with expanded coverage"""
        self.enhanced_themes = {
            'salvation_redemption': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:salvation|saved|save me|saving grace)\b',
                    r'\b(?:redemption|redeemed|redeem|ransom)\b',
                    r'\b(?:born again|new birth|regeneration)\b',
                    r'\b(?:eternal life|everlasting life|life eternal)\b',
                    r'\b(?:forgiven|forgiveness|pardon|cleansed)\b',
                    r'\b(?:justified|justification|righteous)\b',
                    r'\b(?:atonement|propitiation|reconciliation)\b'
                ],
                'scriptures': ['John 3:16', 'Romans 10:9', 'Ephesians 2:8-9', '1 Peter 1:18-19']
            },
            
            'worship_praise': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:worship|praise|glorify|exalt|magnify|adore)\b',
                    r'\b(?:hallelujah|alleluia|hosanna|amen|glory)\b',
                    r'\b(?:holy|sacred|divine|blessed|mighty)\b',
                    r'\b(?:sing|singing|song|melody|hymn)\s+(?:to|unto|for)\s+(?:god|lord|jesus)\b',
                    r'\b(?:lift|lifting)\s+(?:up\s+)?(?:my|our)\s+(?:hands|voice|heart|praise)\b',
                    r'\b(?:bow|kneel|prostrate)\s+(?:before|down)\b'
                ],
                'scriptures': ['Psalm 150:6', 'Psalm 95:1', 'Ephesians 5:19', 'Colossians 3:16']
            },
            
            'faith_trust': {
                'weight': 0.9,
                'patterns': [
                    r'\b(?:faith|trust|believe|belief|confidence)\b',
                    r'\b(?:hope|hopeful|hoping|assurance)\b',
                    r'\b(?:lean|leaning|depend|depending|rely|relying)\s+on\b',
                    r'\b(?:anchor|foundation|rock|refuge|fortress)\b',
                    r'\b(?:faithful|faithfulness|trustworthy)\b'
                ],
                'scriptures': ['Proverbs 3:5-6', 'Hebrews 11:1', 'Romans 10:17', 'Psalm 56:3']
            },
            
            'love_grace': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:love|grace|mercy|compassion|kindness)\b',
                    r'\b(?:unconditional|agape|amazing grace|endless love)\b',
                    r'\b(?:merciful|gracious|loving|kind)\b',
                    r'\b(?:beloved|cherished|precious)\b'
                ],
                'scriptures': ['1 John 4:8', 'Romans 8:38-39', 'Ephesians 2:4-5', 'Lamentations 3:22-23']
            },
            
            'prayer_communion': {
                'weight': 0.8,
                'patterns': [
                    r'\b(?:pray|prayer|praying|prayers|intercession)\b',
                    r'\b(?:talk|talking|speak|speaking|commune)\s+(?:to|with)\s+(?:god|lord|jesus)\b',
                    r'\b(?:fellowship|communion|intimacy)\b',
                    r'\b(?:quiet time|devotion|meditation|contemplation)\b'
                ],
                'scriptures': ['1 Thessalonians 5:17', 'Philippians 4:6', 'Matthew 6:9-11', 'James 5:16']
            },
            
            'spiritual_warfare': {
                'weight': 0.9,
                'patterns': [
                    r'\b(?:fight|fighting)\s+(?:the\s+)?(?:good\s+)?fight\b',
                    r'\b(?:spiritual\s+)?(?:battle|warfare|combat)\b',
                    r'\b(?:armor\s+of\s+god|sword\s+of\s+the\s+spirit|shield\s+of\s+faith)\b',
                    r'\b(?:victory|victorious|overcome|overcoming|conquer)\b',
                    r'\b(?:enemy|satan|devil|evil|darkness)\b',
                    r'\b(?:stronghold|fortress|weapon|battle cry)\b'
                ],
                'scriptures': ['Ephesians 6:11', '2 Timothy 4:7', '1 John 5:4', 'Romans 8:37']
            },
            
            'hope_encouragement': {
                'weight': 0.8,
                'patterns': [
                    r'\b(?:hope|hopeful|encouraged|encouragement|comfort)\b',
                    r'\b(?:strength|strengthen|strong|mighty)\b',
                    r'\b(?:peace|peaceful|rest|comfort|consolation)\b',
                    r'\b(?:never give up|persevere|endure|persist)\b',
                    r'\b(?:refuge|shelter|haven|sanctuary)\b'
                ],
                'scriptures': ['Jeremiah 29:11', 'Romans 15:13', 'Isaiah 40:31', 'Philippians 4:13']
            },
            
            'cross_crucifixion': {
                'weight': 1.0,
                'patterns': [
                    r'\b(?:cross|crucifixion|calvary|golgotha)\b',
                    r'\b(?:blood|precious blood|shed blood)\b',
                    r'\b(?:sacrifice|sacrificial|offering)\b',
                    r'\b(?:resurrection|risen|easter|empty tomb)\b',
                    r'\b(?:crown of thorns|nails|spear)\b'
                ],
                'scriptures': ['1 Corinthians 1:18', 'Galatians 6:14', '1 Peter 2:24', 'Romans 6:6']
            },
            
            'kingdom_heaven': {
                'weight': 0.9,
                'patterns': [
                    r'\b(?:kingdom|heaven|heavenly|celestial)\b',
                    r'\b(?:eternal|everlasting|forever|immortal)\b',
                    r'\b(?:paradise|new jerusalem|promised land)\b',
                    r'\b(?:throne|crown|glory|majesty)\b'
                ],
                'scriptures': ['Matthew 5:3', 'Matthew 6:33', 'Revelation 21:4', 'John 14:2']
            },
            
            'covenant_promise': {
                'weight': 0.8,
                'patterns': [
                    r'\b(?:covenant|promise|oath|vow)\b',
                    r'\b(?:faithful|faithfulness|steadfast)\b',
                    r'\b(?:inheritance|heir|blessed)\b',
                    r'\b(?:chosen|elect|beloved)\b'
                ],
                'scriptures': ['2 Corinthians 1:20', 'Hebrews 8:6', 'Romans 8:28', '1 Peter 2:9']
            }
        }
        
        # Compile patterns
        self.compiled_theme_patterns = {}
        for theme, data in self.enhanced_themes.items():
            self.compiled_theme_patterns[theme] = [re.compile(pattern, re.IGNORECASE) for pattern in data['patterns']]
    
    def _setup_biblical_concepts(self):
        """Setup abstract biblical concepts and theological terms"""
        self.biblical_concepts = {
            'theological_terms': [
                'trinity', 'incarnation', 'sanctification', 'glorification',
                'predestination', 'election', 'rapture', 'millennium',
                'eschatology', 'soteriology', 'pneumatology'
            ],
            'spiritual_disciplines': [
                'fasting', 'tithing', 'stewardship', 'discipleship',
                'evangelism', 'missions', 'ministry', 'calling'
            ],
            'biblical_locations': [
                'jerusalem', 'bethlehem', 'nazareth', 'galilee',
                'jordan river', 'mount sinai', 'mount zion', 'gethsemane'
            ],
            'biblical_symbols': [
                'dove', 'lamb', 'lion', 'shepherd', 'vine', 'bread',
                'light', 'salt', 'fire', 'oil', 'water', 'rock'
            ]
        }
        
    def _setup_verses_database(self):
        """Setup database of popular verses for content matching"""
        self.popular_verses = {
            'John 3:16': 'For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.',
            'Romans 8:28': 'And we know that in all things God works for the good of those who love him, who have been called according to his purpose.',
            'Philippians 4:13': 'I can do all this through him who gives me strength.',
            'Jeremiah 29:11': 'For I know the plans I have for you," declares the Lord, "plans to prosper you and not to harm you, plans to give you hope and a future.',
            'Psalm 23:1': 'The Lord is my shepherd, I lack nothing.',
            'Isaiah 40:31': 'But those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.',
            'Proverbs 3:5-6': 'Trust in the Lord with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight.',
            'Romans 10:9': 'If you declare with your mouth, "Jesus is Lord," and believe in your heart that God raised him from the dead, you will be saved.',
            'Ephesians 2:8-9': 'For it is by grace you have been saved, through faith—and this is not from yourselves, it is the gift of God—not by works, so that no one can boast.',
            '1 John 4:8': 'Whoever does not love does not know God, because God is love.',
            'Matthew 28:19': 'Therefore go and make disciples of all nations, baptizing them in the name of the Father and of the Son and of the Holy Spirit.',
            'Galatians 2:20': 'I have been crucified with Christ and I no longer live, but Christ lives in me. The life I now live in the body, I live by faith in the Son of God, who loved me and gave himself for me.'
        }
        
    def analyze_lyrics(self, lyrics: str) -> Dict[str, Any]:
        """
        Comprehensive biblical analysis of lyrics
        
        Args:
            lyrics: Song lyrics to analyze
            
        Returns:
            Dictionary with detected biblical references, themes, and supporting scripture
        """
        if not lyrics or not lyrics.strip():
            return {
                'biblical_themes': [],
                'supporting_scripture': {},
                'biblical_names': [],
                'scripture_references': [],
                'verse_content_matches': [],
                'total_biblical_score': 0,
                'confidence_score': 0.0
            }
        
        try:
            # Detect different types of biblical content
            scripture_refs = self._detect_scripture_references(lyrics)
            biblical_names = self._detect_biblical_names(lyrics)
            themes = self._detect_biblical_themes(lyrics)
            verse_matches = self._detect_verse_content(lyrics)
            concepts = self._detect_biblical_concepts(lyrics)
            
            # Calculate overall biblical score
            biblical_score = self._calculate_biblical_score(scripture_refs, biblical_names, themes, verse_matches, concepts)
            
            # Generate supporting scripture
            supporting_scripture = self._generate_supporting_scripture(themes, scripture_refs)
            
            return {
                'biblical_themes': themes,
                'supporting_scripture': supporting_scripture,
                'biblical_names': biblical_names,
                'scripture_references': scripture_refs,
                'verse_content_matches': verse_matches,
                'biblical_concepts': concepts,
                'total_biblical_score': biblical_score,
                'confidence_score': min(1.0, biblical_score / 100.0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in biblical analysis: {str(e)}")
            return {
                'biblical_themes': [],
                'supporting_scripture': {},
                'biblical_names': [],
                'scripture_references': [],
                'verse_content_matches': [],
                'biblical_concepts': [],
                'total_biblical_score': 0,
                'confidence_score': 0.0,
                'error': str(e)
            }
    
    def _detect_scripture_references(self, lyrics: str) -> List[Dict[str, Any]]:
        """Detect explicit scripture references like 'John 3:16'"""
        references = []
        
        for pattern in self.compiled_scripture_patterns:
            matches = pattern.finditer(lyrics)
            for match in matches:
                book = match.group(1).lower()
                
                # Find the canonical book name
                canonical_book = None
                for canon_name, abbreviations in self.bible_books.items():
                    if book == canon_name.lower() or book in [abbr.lower() for abbr in abbreviations]:
                        canonical_book = canon_name.title()
                        break
                
                if canonical_book:
                    ref_text = match.group(0)
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(lyrics), match.end() + 30)
                    context = lyrics[context_start:context_end].strip()
                    
                    references.append({
                        'reference': ref_text,
                        'canonical_book': canonical_book,
                        'matched_text': match.group(0),
                        'context': context,
                        'confidence': 0.95,
                        'position': match.start()
                    })
        
        return references
    
    def _detect_biblical_names(self, lyrics: str) -> List[Dict[str, Any]]:
        """Detect biblical names and characters"""
        names_found = []
        lyrics_lower = lyrics.lower()
        
        for category, subcategories in self.biblical_names.items():
            for subcategory, names in subcategories.items():
                for name in names:
                    # Use word boundaries for exact matches
                    pattern = rf'\b{re.escape(name)}\b'
                    matches = re.finditer(pattern, lyrics, re.IGNORECASE)
                    
                    for match in matches:
                        context_start = max(0, match.start() - 25)
                        context_end = min(len(lyrics), match.end() + 25)
                        context = lyrics[context_start:context_end].strip()
                        
                        confidence = 0.8
                        # Increase confidence for divine names in religious context
                        if category == 'divine':
                            confidence = 0.95
                        
                        names_found.append({
                            'name': name.title(),
                            'category': category,
                            'subcategory': subcategory,
                            'matched_text': match.group(0),
                            'context': context,
                            'confidence': confidence,
                            'position': match.start()
                        })
        
        # Remove duplicates based on position
        unique_names = []
        seen_positions = set()
        for name_match in sorted(names_found, key=lambda x: x['confidence'], reverse=True):
            if name_match['position'] not in seen_positions:
                unique_names.append(name_match)
                seen_positions.add(name_match['position'])
        
        return unique_names
    
    def _detect_biblical_themes(self, lyrics: str) -> List[Dict[str, Any]]:
        """Detect biblical themes with enhanced patterns"""
        themes_found = []
        
        for theme_name, theme_data in self.enhanced_themes.items():
            patterns = self.compiled_theme_patterns[theme_name]
            matches = []
            
            for pattern in patterns:
                pattern_matches = pattern.finditer(lyrics)
                for match in pattern_matches:
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(lyrics), match.end() + 30)
                    context = lyrics[context_start:context_end].strip()
                    
                    matches.append({
                        'text': match.group(0),
                        'context': context,
                        'position': match.start()
                    })
            
            if matches:
                # Calculate confidence based on number of matches and theme weight
                base_confidence = 0.6
                match_bonus = min(0.3, len(matches) * 0.1)
                weight_bonus = theme_data['weight'] * 0.1
                confidence = min(0.95, base_confidence + match_bonus + weight_bonus)
                
                theme_info = {
                    'theme': theme_name.replace('_', ' ').title(),
                    'theme_key': theme_name,
                    'matches': len(matches),
                    'examples': [m['text'] for m in matches[:3]],
                    'contexts': [m['context'] for m in matches[:3]],
                    'confidence': confidence,
                    'weight': theme_data['weight'],
                    'scriptures': theme_data.get('scriptures', [])
                }
                themes_found.append(theme_info)
        
        return sorted(themes_found, key=lambda x: x['confidence'], reverse=True)
    
    def _detect_verse_content(self, lyrics: str) -> List[Dict[str, Any]]:
        """Detect paraphrases or quotes of popular Bible verses"""
        verse_matches = []
        
        for reference, verse_text in self.popular_verses.items():
            # Calculate similarity with fuzzy matching
            similarity = SequenceMatcher(None, lyrics.lower(), verse_text.lower()).ratio()
            
            # Also check for key phrase matches
            verse_words = set(verse_text.lower().split())
            lyrics_words = set(lyrics.lower().split())
            word_overlap = len(verse_words.intersection(lyrics_words)) / len(verse_words)
            
            # Combined score
            content_score = (similarity * 0.6) + (word_overlap * 0.4)
            
            if content_score > 0.3:  # Threshold for potential match
                verse_matches.append({
                    'reference': reference,
                    'verse_text': verse_text,
                    'similarity_score': similarity,
                    'word_overlap_score': word_overlap,
                    'combined_score': content_score,
                    'confidence': min(0.9, content_score)
                })
        
        return sorted(verse_matches, key=lambda x: x['combined_score'], reverse=True)[:5]  # Top 5 matches
    
    def _detect_biblical_concepts(self, lyrics: str) -> List[Dict[str, Any]]:
        """Detect biblical concepts and theological terms"""
        concepts_found = []
        lyrics_lower = lyrics.lower()
        
        for category, concepts in self.biblical_concepts.items():
            for concept in concepts:
                if concept.lower() in lyrics_lower:
                    # Find exact positions
                    pattern = rf'\b{re.escape(concept)}\b'
                    matches = re.finditer(pattern, lyrics, re.IGNORECASE)
                    
                    for match in matches:
                        context_start = max(0, match.start() - 25)
                        context_end = min(len(lyrics), match.end() + 25)
                        context = lyrics[context_start:context_end].strip()
                        
                        concepts_found.append({
                            'concept': concept.title(),
                            'category': category,
                            'matched_text': match.group(0),
                            'context': context,
                            'confidence': 0.7,
                            'position': match.start()
                        })
        
        return concepts_found
    
    def _calculate_biblical_score(self, scripture_refs: List, names: List, themes: List, 
                                verse_matches: List, concepts: List) -> int:
        """Calculate overall biblical content score"""
        score = 0
        
        # Scripture references (high value)
        score += len(scripture_refs) * 15
        
        # Biblical names (medium-high value, varies by category)
        for name in names:
            if name['category'] == 'divine':
                score += 12
            elif name['category'] == 'new_testament':
                score += 8
            else:
                score += 6
        
        # Themes (high value, weighted)
        for theme in themes:
            theme_score = int(10 * theme['weight'] * theme['confidence'])
            score += theme_score
        
        # Verse content matches (very high value)
        for verse_match in verse_matches:
            score += int(20 * verse_match['confidence'])
        
        # Biblical concepts (medium value)
        score += len(concepts) * 5
        
        return min(100, score)  # Cap at 100
    
    def _generate_supporting_scripture(self, themes: List[Dict], scripture_refs: List[Dict]) -> Dict[str, Any]:
        """Generate supporting scripture based on detected themes"""
        supporting_scripture = {}
        
        # Add scripture from detected themes
        for theme in themes:
            if 'scriptures' in theme and theme['scriptures']:
                theme_key = theme['theme_key']
                supporting_scripture[theme_key] = []
                
                for scripture_ref in theme['scriptures']:
                    if scripture_ref in self.popular_verses:
                        supporting_scripture[theme_key].append({
                            'reference': scripture_ref,
                            'text': self.popular_verses[scripture_ref],
                            'relevance': theme['confidence']
                        })
        
        return supporting_scripture


def create_biblical_detector() -> EnhancedBiblicalDetector:
    """Factory function to create biblical detector"""
    return EnhancedBiblicalDetector() 