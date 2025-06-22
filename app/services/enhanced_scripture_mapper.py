"""
Enhanced Scripture Mapper Service

Provides comprehensive biblical theme-to-scripture mapping for educational
Christian music analysis. Maps identified themes to relevant Bible passages
with context and educational explanations.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EnhancedScriptureMapper:
    """
    Enhanced scripture reference mapper for educational biblical analysis.
    
    Provides comprehensive theme-to-scripture mapping with educational context
    to help users understand how biblical themes connect to scripture.
    """
    
    def __init__(self):
        """Initialize the enhanced scripture mapper."""
        logger.info("Initializing EnhancedScriptureMapper")
        self._initialize_scripture_database()
    
    def _initialize_scripture_database(self):
        """Initialize comprehensive scripture mapping database."""
        self.scripture_database = {
            # Core Biblical Themes
            'god': {
                'category': 'Deity and Worship',
                'scriptures': [
                    {
                        'reference': 'Psalm 46:1',
                        'text': 'God is our refuge and strength, an ever-present help in trouble.',
                        'relevance': 'Establishes God as our source of strength and protection',
                        'application': 'When songs speak of God, they point to our ultimate source of hope and security.'
                    },
                    {
                        'reference': 'Isaiah 55:8-9',
                        'text': 'For my thoughts are not your thoughts, neither are your ways my ways, declares the Lord.',
                        'relevance': 'Reminds us of God\'s sovereignty and wisdom above human understanding',
                        'application': 'Songs about God should inspire reverence and humility before His greatness.'
                    },
                    {
                        'reference': '1 John 4:8',
                        'text': 'Whoever does not love does not know God, because God is love.',
                        'relevance': 'Reveals the fundamental nature of God as love itself',
                        'application': 'True worship music reflects God\'s loving character and draws us to love others.'
                    }
                ]
            },
            
            'jesus': {
                'category': 'Deity and Worship',
                'scriptures': [
                    {
                        'reference': 'John 14:6',
                        'text': 'Jesus answered, "I am the way and the truth and the life. No one comes to the Father except through me."',
                        'relevance': 'Establishes Jesus as the exclusive path to salvation',
                        'application': 'Songs about Jesus should acknowledge His unique role as Savior and Lord.'
                    },
                    {
                        'reference': 'Philippians 2:9-11',
                        'text': 'Therefore God exalted him to the highest place and gave him the name that is above every name.',
                        'relevance': 'Celebrates Jesus\' exaltation and universal lordship',
                        'application': 'Worship songs should honor Jesus\' supreme position and authority.'
                    },
                    {
                        'reference': 'Hebrews 4:15',
                        'text': 'For we do not have a high priest who is unable to empathize with our weaknesses.',
                        'relevance': 'Shows Jesus\' compassionate understanding of human struggles',
                        'application': 'Songs can celebrate Jesus\' empathy and accessibility in our difficulties.'
                    }
                ]
            },
            
            'grace': {
                'category': 'Salvation and Redemption',
                'scriptures': [
                    {
                        'reference': 'Ephesians 2:8-9',
                        'text': 'For it is by grace you have been saved, through faith—and this is not from yourselves, it is the gift of God.',
                        'relevance': 'Defines salvation as entirely God\'s gift, not human effort',
                        'application': 'Songs about grace should emphasize God\'s unmerited favor and free salvation.'
                    },
                    {
                        'reference': '2 Corinthians 12:9',
                        'text': 'But he said to me, "My grace is sufficient for you, for my power is made perfect in weakness."',
                        'relevance': 'Shows how God\'s grace empowers us in our weaknesses',
                        'application': 'Grace-themed songs can encourage believers in their struggles and limitations.'
                    },
                    {
                        'reference': 'Romans 5:20',
                        'text': 'But where sin increased, grace increased all the more.',
                        'relevance': 'Demonstrates grace\'s power to overcome even the worst sin',
                        'application': 'Songs should celebrate grace\'s triumph over guilt and condemnation.'
                    }
                ]
            },
            
            'love': {
                'category': 'Character and Relationships',
                'scriptures': [
                    {
                        'reference': '1 Corinthians 13:4-7',
                        'text': 'Love is patient, love is kind. It does not envy, it does not boast, it is not proud.',
                        'relevance': 'Provides the biblical definition of true love',
                        'application': 'Love songs should reflect biblical virtues rather than selfish desires.'
                    },
                    {
                        'reference': 'John 3:16',
                        'text': 'For God so loved the world that he gave his one and only Son.',
                        'relevance': 'Demonstrates the ultimate expression of God\'s love',
                        'application': 'True love songs can point to God\'s sacrificial love as the highest example.'
                    },
                    {
                        'reference': '1 John 4:19',
                        'text': 'We love because he first loved us.',
                        'relevance': 'Shows that human love flows from God\'s love',
                        'application': 'Songs about love should acknowledge God as the source of our ability to love.'
                    }
                ]
            },
            
            'worship': {
                'category': 'Deity and Worship',
                'scriptures': [
                    {
                        'reference': 'Psalm 95:6',
                        'text': 'Come, let us bow down in worship, let us kneel before the Lord our Maker.',
                        'relevance': 'Calls for reverent worship acknowledging God as Creator',
                        'application': 'Worship songs should inspire genuine reverence and acknowledgment of God\'s sovereignty.'
                    },
                    {
                        'reference': 'John 4:23-24',
                        'text': 'Yet a time is coming and has now come when the true worshipers will worship the Father in the Spirit and in truth.',
                        'relevance': 'Defines authentic worship as spiritual and truthful',
                        'application': 'Worship music should be both emotionally genuine and biblically accurate.'
                    },
                    {
                        'reference': 'Romans 12:1',
                        'text': 'Therefore, I urge you, brothers and sisters, to offer your bodies as a living sacrifice, holy and pleasing to God—this is your true and proper worship.',
                        'relevance': 'Expands worship beyond music to include all of life',
                        'application': 'Worship songs should inspire total life dedication, not just emotional experiences.'
                    }
                ]
            },
            
            'faith': {
                'category': 'Spiritual Growth',
                'scriptures': [
                    {
                        'reference': 'Hebrews 11:1',
                        'text': 'Now faith is confidence in what we hope for and assurance about what we do not see.',
                        'relevance': 'Defines faith as confident trust in God\'s promises',
                        'application': 'Faith-based songs should build confidence in God\'s character and promises.'
                    },
                    {
                        'reference': 'Romans 10:17',
                        'text': 'Consequently, faith comes from hearing the message, and the message is heard through the word about Christ.',
                        'relevance': 'Shows that faith grows through exposure to God\'s word',
                        'application': 'Songs that build faith should be grounded in biblical truth about Christ.'
                    },
                    {
                        'reference': 'Mark 9:24',
                        'text': 'Immediately the boy\'s father exclaimed, "I do believe; help me overcome my unbelief!"',
                        'relevance': 'Acknowledges the struggle and growth process of faith',
                        'application': 'Faith songs can honestly address doubts while affirming trust in God.'
                    }
                ]
            },
            
            'hope': {
                'category': 'Spiritual Growth',
                'scriptures': [
                    {
                        'reference': 'Romans 15:13',
                        'text': 'May the God of hope fill you with all joy and peace as you trust in him.',
                        'relevance': 'Identifies God as the ultimate source of hope',
                        'application': 'Hope-filled songs should point to God\'s character as the foundation of confidence.'
                    },
                    {
                        'reference': '1 Peter 1:3',
                        'text': 'Praise be to the God and Father of our Lord Jesus Christ! In his great mercy he has given us new birth into a living hope.',
                        'relevance': 'Connects hope to spiritual rebirth and God\'s mercy',
                        'application': 'Songs of hope should celebrate the new life and future God provides.'
                    },
                    {
                        'reference': 'Jeremiah 29:11',
                        'text': 'For I know the plans I have for you," declares the Lord, "plans to prosper you and not to harm you, to give you hope and a future.',
                        'relevance': 'Assures believers of God\'s good intentions and plans',
                        'application': 'Hope songs can encourage trust in God\'s sovereignty over our circumstances.'
                    }
                ]
            },
            
            'peace': {
                'category': 'Spiritual Growth',
                'scriptures': [
                    {
                        'reference': 'John 14:27',
                        'text': 'Peace I leave with you; my peace I give you. I do not give to you as the world gives.',
                        'relevance': 'Distinguishes Christ\'s peace from worldly peace',
                        'application': 'Songs about peace should reflect supernatural calm that comes from Christ.'
                    },
                    {
                        'reference': 'Philippians 4:7',
                        'text': 'And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus.',
                        'relevance': 'Describes peace as divine protection for our thoughts and emotions',
                        'application': 'Peace songs should inspire trust in God\'s protective care over our inner lives.'
                    },
                    {
                        'reference': 'Isaiah 26:3',
                        'text': 'You will keep in perfect peace those whose minds are steadfast, because they trust in you.',
                        'relevance': 'Links peace to steadfast focus on God',
                        'application': 'Songs should encourage mental focus on God as the path to peace.'
                    }
                ]
            },
            
            'joy': {
                'category': 'Spiritual Growth',
                'scriptures': [
                    {
                        'reference': 'Psalm 16:11',
                        'text': 'You make known to me the path of life; you will fill me with joy in your presence.',
                        'relevance': 'Locates true joy in God\'s presence',
                        'application': 'Joyful songs should celebrate the delight of being with God.'
                    },
                    {
                        'reference': 'Galatians 5:22',
                        'text': 'But the fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness.',
                        'relevance': 'Identifies joy as a supernatural fruit of the Spirit',
                        'application': 'Joy in songs should reflect spiritual maturity, not just happiness.'
                    },
                    {
                        'reference': 'Nehemiah 8:10',
                        'text': 'Do not grieve, for the joy of the Lord is your strength.',
                        'relevance': 'Shows joy as a source of spiritual strength',
                        'application': 'Songs about joy should inspire resilience and spiritual fortitude.'
                    }
                ]
            },
            
            'forgiveness': {
                'category': 'Salvation and Redemption',
                'scriptures': [
                    {
                        'reference': '1 John 1:9',
                        'text': 'If we confess our sins, he is faithful and just and will forgive us our sins.',
                        'relevance': 'Assures believers of God\'s faithful forgiveness',
                        'application': 'Forgiveness songs should encourage honest confession and trust in God\'s mercy.'
                    },
                    {
                        'reference': 'Matthew 6:14-15',
                        'text': 'For if you forgive other people when they sin against you, your heavenly Father will also forgive you.',
                        'relevance': 'Links receiving forgiveness with extending forgiveness',
                        'application': 'Songs should inspire both gratitude for forgiveness and willingness to forgive others.'
                    },
                    {
                        'reference': 'Colossians 3:13',
                        'text': 'Bear with each other and forgive one another if any of you has a grievance against someone.',
                        'relevance': 'Commands mutual forgiveness in Christian community',
                        'application': 'Forgiveness themes should promote reconciliation and grace in relationships.'
                    }
                ]
            }
        }
    
    def find_relevant_passages(self, themes: List[str]) -> List[Dict[str, Any]]:
        """
        Find relevant scripture passages for given biblical themes.
        
        Args:
            themes: List of biblical themes to find scripture for
            
        Returns:
            List of scripture references with educational context
        """
        try:
            if not themes:
                return []
            
            relevant_passages = []
            seen_themes = set()  # Track themes to avoid duplicates
            
            for theme in themes[:5]:  # Limit to top 5 themes
                if not theme:  # Skip None or empty themes
                    continue
                    
                theme_lower = theme.lower().strip()
                
                # Skip if we've already processed this theme
                if theme_lower in seen_themes:
                    continue
                seen_themes.add(theme_lower)
                
                if theme_lower in self.scripture_database:
                    theme_data = self.scripture_database[theme_lower]
                    
                    # Select most relevant scripture (first one for now)
                    if theme_data['scriptures']:
                        scripture = theme_data['scriptures'][0]  # Take the primary reference
                        
                        relevant_passages.append({
                            'reference': scripture['reference'],
                            'text': scripture['text'],
                            'theme': theme.capitalize(),
                            'category': theme_data['category'],
                            'relevance': scripture['relevance'],
                            'application': scripture['application'],
                            'educational_value': f"This passage helps understand how '{theme.capitalize()}' relates to biblical truth and Christian living."
                        })
            
            return relevant_passages[:3]  # Return top 3 most relevant
            
        except Exception as e:
            logger.error(f"Error finding relevant passages: {e}")
            return []
    
    def get_theme_explanation(self, theme: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed explanation for a specific biblical theme.
        
        Args:
            theme: Biblical theme to explain
            
        Returns:
            Dictionary with theme explanation and educational context
        """
        theme_lower = theme.lower().strip()
        
        if theme_lower in self.scripture_database:
            theme_data = self.scripture_database[theme_lower]
            
            return {
                'theme': theme.capitalize(),
                'category': theme_data['category'],
                'scripture_count': len(theme_data['scriptures']),
                'primary_reference': theme_data['scriptures'][0]['reference'] if theme_data['scriptures'] else None,
                'description': f"The theme of '{theme.capitalize()}' is foundational to Christian faith and appears throughout Scripture.",
                'why_important': f"Understanding '{theme.capitalize()}' helps believers grow in their relationship with God and live according to His will."
            }
        
        return None
    
    def get_comprehensive_analysis(self, themes: List[str]) -> Dict[str, Any]:
        """
        Get comprehensive analysis of all biblical themes with educational insights.
        
        Args:
            themes: List of biblical themes found in content
            
        Returns:
            Comprehensive analysis with educational framework
        """
        try:
            analysis = {
                'themes_found': len(themes),
                'biblical_depth': 'High' if len(themes) >= 3 else 'Medium' if len(themes) >= 2 else 'Low',
                'educational_insights': [],
                'scripture_references': self.find_relevant_passages(themes),
                'learning_opportunities': []
            }
            
            # Add educational insights
            if themes:
                analysis['educational_insights'].append(
                    f"This content contains {len(themes)} biblical theme(s), indicating strong spiritual content that can support Christian growth."
                )
                
                # Add specific insights based on theme categories
                categories = set()
                for theme in themes:
                    theme_data = self.scripture_database.get(theme.lower())
                    if theme_data:
                        categories.add(theme_data['category'])
                
                if categories:
                    analysis['educational_insights'].append(
                        f"The themes span {len(categories)} biblical categories: {', '.join(categories)}, showing diverse spiritual content."
                    )
            
            # Add learning opportunities
            if analysis['scripture_references']:
                analysis['learning_opportunities'].append(
                    "Study the provided scripture references to deepen understanding of these biblical themes."
                )
                analysis['learning_opportunities'].append(
                    "Consider how these themes apply to your daily Christian walk and spiritual growth."
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {
                'themes_found': len(themes),
                'biblical_depth': 'Unknown',
                'educational_insights': ['Analysis temporarily unavailable'],
                'scripture_references': [],
                'learning_opportunities': []
            } 