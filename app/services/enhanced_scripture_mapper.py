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
            },
            
            # Biblical Foundations for Addressing Concerns
            'concern_themes': {
                'explicit_language': {
                    'category': 'Communication and Speech Purity',
                    'concern_addressed': 'explicit_language',
                    'scriptures': [
                        {
                            'reference': 'Ephesians 4:29',
                            'text': 'Do not let any unwholesome talk come out of your mouths, but only what is helpful for building others up according to their needs.',
                            'teaching_point': 'God calls us to use words that build up rather than tear down. Our speech should reflect His character and promote the wellbeing of others.',
                            'application': 'Choose music with lyrics that encourage, inspire, and reflect the purity of heart that God desires for His children.',
                            'contrast_principle': 'Rather than crude or offensive language, seek music that demonstrates the transformed heart through pure speech.'
                        },
                        {
                            'reference': 'James 3:9-10',
                            'text': 'With the tongue we praise our Lord and Father, and with it we curse human beings, who have been made in God\'s likeness. Out of the same mouth come praise and cursing. My brothers and sisters, this should not be.',
                            'teaching_point': 'Our words reveal the condition of our hearts. The same voice that praises God should not be used to degrade what He has created.',
                            'application': 'Select music that honors both God and fellow human beings, avoiding content that demeans or degrades others.',
                            'contrast_principle': 'Let your music choices reflect the consistency of heart that honors God in all speech.'
                        },
                        {
                            'reference': 'Colossians 4:6',
                            'text': 'Let your conversation be always full of grace, seasoned with salt, so that you may know how to answer everyone.',
                            'teaching_point': 'Christian speech should be gracious and purposeful, adding value to conversations and relationships.',
                            'application': 'Seek music that models gracious communication and positive interaction with others.',
                            'contrast_principle': 'Choose content that seasons your mind with grace rather than coarseness or negativity.'
                        }
                    ]
                },
                
                'sexual_content': {
                    'category': 'Sexual Purity and Holiness',
                    'concern_addressed': 'sexual_content',
                    'scriptures': [
                        {
                            'reference': '1 Corinthians 6:18-20',
                            'text': 'Flee from sexual immorality. All other sins a person commits are outside the body, but whoever sins sexually, sins against their own body. Do you not know that your bodies are temples of the Holy Spirit?',
                            'teaching_point': 'Sexual purity is not just a moral guideline but a recognition that our bodies are sacred dwelling places of God\'s Spirit.',
                            'application': 'Choose music that honors the sacredness of sexuality within God\'s design and avoid content that promotes casual or immoral sexual behavior.',
                            'contrast_principle': 'Rather than music that stimulates lustful desires, seek content that promotes pure love and God-honoring relationships.'
                        },
                        {
                            'reference': '1 Thessalonians 4:3-5',
                            'text': 'It is God\'s will that you should be sanctified: that you should avoid sexual immorality; that each of you should learn to control your own body in a way that is holy and honorable.',
                            'teaching_point': 'God\'s will for believers includes sexual purity as part of our overall sanctification and spiritual growth.',
                            'application': 'Select music that supports your commitment to sexual purity and helps you maintain holy thoughts and desires.',
                            'contrast_principle': 'Instead of content that inflames sexual desires outside marriage, choose music that supports self-control and honor.'
                        },
                        {
                            'reference': 'Matthew 5:28',
                            'text': 'But I tell you that anyone who looks at a woman lustfully has already committed adultery with her in his heart.',
                            'teaching_point': 'Jesus teaches that sexual purity begins in the heart and mind, not just in physical actions.',
                            'application': 'Be mindful that music can influence your thought life; choose content that helps maintain pure thoughts.',
                            'contrast_principle': 'Guard your heart by avoiding music that promotes lustful thinking or objectifies others.'
                        }
                    ]
                },
                
                'substance_abuse': {
                    'category': 'Body Stewardship and Sobriety',
                    'concern_addressed': 'substance_abuse',
                    'scriptures': [
                        {
                            'reference': '1 Corinthians 6:19-20',
                            'text': 'Do you not know that your bodies are temples of the Holy Spirit, who is in you, whom you have received from God? You are not your own; you were bought at a price. Therefore honor God with your bodies.',
                            'teaching_point': 'Our bodies belong to God and should be treated with the respect due to His dwelling place. Substance abuse dishonors this sacred relationship.',
                            'application': 'Choose music that promotes healthy living and respect for the body as God\'s temple, avoiding content that glorifies substance abuse.',
                            'contrast_principle': 'Rather than music that promotes escape through substances, seek content that finds comfort and joy in God.'
                        },
                        {
                            'reference': 'Proverbs 20:1',
                            'text': 'Wine is a mocker and beer a brawler; whoever is led astray by them is not wise.',
                            'teaching_point': 'Scripture warns against being controlled by alcohol or substances that impair judgment and lead to unwise decisions.',
                            'application': 'Select music that promotes wisdom and clear thinking rather than celebrating intoxication or substance use.',
                            'contrast_principle': 'Choose music that inspires clarity of mind and wisdom rather than escapism through substances.'
                        },
                        {
                            'reference': 'Galatians 5:16-17',
                            'text': 'So I say, walk by the Spirit, and you will not gratify the desires of the flesh. For the flesh desires what is contrary to the Spirit.',
                            'teaching_point': 'Living by the Spirit means rejecting fleshly desires, including dependencies on substances for comfort or escape.',
                            'application': 'Choose music that encourages spiritual dependence on God rather than physical dependence on substances.',
                            'contrast_principle': 'Seek music that promotes spiritual highs and God-centered joy rather than chemical escapes.'
                        }
                    ]
                },
                
                'violence_aggression': {
                    'category': 'Peace and Love',
                    'concern_addressed': 'violence_aggression',
                    'scriptures': [
                        {
                            'reference': 'Matthew 5:39',
                            'text': 'But I tell you, do not resist an evil person. If anyone slaps you on the right cheek, turn to them the other cheek also.',
                            'teaching_point': 'Jesus teaches a radical alternative to violence - responding to aggression with love and restraint rather than retaliation.',
                            'application': 'Choose music that promotes peace-making and love over violence, even when facing conflict or injustice.',
                            'contrast_principle': 'Instead of music that glorifies revenge or violence, seek content that models Christ\'s way of peace.'
                        },
                        {
                            'reference': 'Romans 12:19-21',
                            'text': 'Do not take revenge, my dear friends, but leave room for God\'s wrath, for it is written: "It is mine to avenge; I will repay," says the Lord. On the contrary: "If your enemy is hungry, feed him; if he is thirsty, give him something to drink."',
                            'teaching_point': 'God calls believers to overcome evil with good, trusting Him for justice rather than taking matters into our own hands.',
                            'application': 'Select music that inspires forgiveness and kindness toward enemies rather than promoting aggressive responses.',
                            'contrast_principle': 'Choose music that demonstrates love conquering hate rather than celebrating aggression or revenge.'
                        },
                        {
                            'reference': 'Ephesians 4:31-32',
                            'text': 'Get rid of all bitterness, rage and anger, brawling and slander, along with every form of malice. Be kind and compassionate to one another, forgiving each other, just as in Christ God forgave you.',
                            'teaching_point': 'Christians are called to eliminate aggressive emotions and behaviors, replacing them with kindness and forgiveness.',
                            'application': 'Choose music that promotes emotional healing and forgiveness rather than feeding anger or aggressive feelings.',
                            'contrast_principle': 'Seek music that builds up rather than tears down, that heals rather than wounds.'
                        }
                    ]
                },
                
                'materialism_greed': {
                    'category': 'Stewardship and Contentment',
                    'concern_addressed': 'materialism_greed',
                    'scriptures': [
                        {
                            'reference': '1 Timothy 6:10',
                            'text': 'For the love of money is a root of all kinds of evil. Some people, eager for money, have wandered from the faith and pierced themselves with many griefs.',
                            'teaching_point': 'The pursuit of wealth can become an idol that leads us away from God and causes spiritual harm.',
                            'application': 'Choose music that promotes contentment and gratitude rather than materialism and the pursuit of wealth.',
                            'contrast_principle': 'Seek music that celebrates spiritual riches and God\'s provision rather than material accumulation.'
                        },
                        {
                            'reference': 'Matthew 6:19-21',
                            'text': 'Do not store up for yourselves treasures on earth, where moths and vermin destroy, and where thieves break in and steal. But store up for yourselves treasures in heaven.',
                            'teaching_point': 'Jesus teaches that earthly possessions are temporary and unreliable, while spiritual investments have eternal value.',
                            'application': 'Select music that focuses on eternal values and spiritual growth rather than temporary material pursuits.',
                            'contrast_principle': 'Choose content that inspires investment in relationships, character, and spiritual growth over material gain.'
                        },
                        {
                            'reference': 'Hebrews 13:5',
                            'text': 'Keep your lives free from the love of money and be content with what you have, because God has said, "Never will I leave you; never will I forsake you."',
                            'teaching_point': 'True security comes from God\'s presence and promises, not from financial accumulation.',
                            'application': 'Choose music that promotes trust in God\'s provision and contentment with His blessings.',
                            'contrast_principle': 'Seek music that finds joy in God\'s presence rather than in possessions or wealth.'
                        }
                    ]
                },
                
                'pride_arrogance': {
                    'category': 'Humility and Character',
                    'concern_addressed': 'pride_arrogance',
                    'scriptures': [
                        {
                            'reference': 'Proverbs 16:18',
                            'text': 'Pride goes before destruction, a haughty spirit before a fall.',
                            'teaching_point': 'Pride is spiritually dangerous because it leads to poor decisions and separation from God who opposes the proud.',
                            'application': 'Choose music that promotes humility and dependence on God rather than self-exaltation or arrogance.',
                            'contrast_principle': 'Seek music that gives glory to God and recognizes our dependence on Him rather than celebrating self-sufficiency.'
                        },
                        {
                            'reference': 'James 4:6',
                            'text': 'But he gives us more grace. That is why Scripture says: "God opposes the proud but shows favor to the humble."',
                            'teaching_point': 'God actively resists pride but blesses humility with His grace and favor.',
                            'application': 'Select music that cultivates a humble heart and acknowledges our need for God\'s grace.',
                            'contrast_principle': 'Choose music that promotes humility and service to others over self-promotion and ego.'
                        },
                        {
                            'reference': 'Philippians 2:3-4',
                            'text': 'Do nothing out of selfish ambition or vain conceit. Rather, in humility value others above yourselves, not looking to your own interests but each of you to the interests of the others.',
                            'teaching_point': 'True Christian character involves putting others\' needs before our own and avoiding self-centered motivations.',
                            'application': 'Choose music that inspires service to others and selfless love rather than self-focused content.',
                            'contrast_principle': 'Seek music that celebrates community, service, and love for others over personal achievement or status.'
                        }
                    ]
                },
                
                'occult_spiritual_darkness': {
                    'category': 'Spiritual Discernment and Truth',
                    'concern_addressed': 'occult_spiritual_darkness',
                    'scriptures': [
                        {
                            'reference': 'Deuteronomy 18:10-12',
                            'text': 'Let no one be found among you who sacrifices their son or daughter in the fire, who practices divination or sorcery, interprets omens, engages in witchcraft, or casts spells, or who is a medium or spiritist or who consults the dead.',
                            'teaching_point': 'God explicitly forbids involvement with occult practices because they represent attempts to access spiritual power apart from Him.',
                            'application': 'Avoid music that promotes or glorifies occult practices, witchcraft, or communication with spirits other than God.',
                            'contrast_principle': 'Seek music that directs you to God as the only source of spiritual truth and power.'
                        },
                        {
                            'reference': '1 John 4:1',
                            'text': 'Dear friends, do not believe every spirit, but test the spirits to see whether they are from God.',
                            'teaching_point': 'Christians must exercise spiritual discernment to distinguish between God\'s Spirit and deceptive spiritual influences.',
                            'application': 'Carefully evaluate music for spiritual content, ensuring it aligns with biblical truth rather than promoting false spiritual concepts.',
                            'contrast_principle': 'Choose music that affirms biblical truth and promotes relationship with God rather than spiritual experimentation.'
                        },
                        {
                            'reference': '2 Corinthians 11:14',
                            'text': 'And no wonder, for Satan himself masquerades as an angel of light.',
                            'teaching_point': 'Spiritual deception can appear attractive and enlightening, making discernment essential for believers.',
                            'application': 'Be cautious of music that promotes spiritual concepts that contradict Scripture, even if they seem positive or enlightening.',
                            'contrast_principle': 'Seek music grounded in biblical revelation rather than alternative spiritual philosophies or practices.'
                        }
                    ]
                },
                
                'despair_hopelessness': {
                    'category': 'Hope and Mental Health',
                    'concern_addressed': 'despair_hopelessness',
                    'scriptures': [
                        {
                            'reference': 'Romans 15:13',
                            'text': 'May the God of hope fill you with all joy and peace as you trust in him, so that you may overflow with hope by the power of the Holy Spirit.',
                            'teaching_point': 'God is the ultimate source of hope, providing supernatural joy and peace even in difficult circumstances.',
                            'application': 'While acknowledging struggles is healthy, balance music that expresses pain with content that points to God\'s hope and healing.',
                            'contrast_principle': 'Seek music that processes pain honestly but also directs you toward God\'s comfort and future hope.'
                        },
                        {
                            'reference': 'Psalm 42:11',
                            'text': 'Why, my soul, are you downcast? Why so disturbed within me? Put your hope in God, for I will yet praise him, my Savior and my God.',
                            'teaching_point': 'Even in depression and despair, believers can redirect their thoughts toward God\'s faithfulness and future deliverance.',
                            'application': 'Choose music that acknowledges emotional struggles but also encourages faith and hope in God\'s goodness.',
                            'contrast_principle': 'Rather than music that wallows in despair, seek content that processes pain while building faith and hope.'
                        },
                        {
                            'reference': '2 Corinthians 4:16-18',
                            'text': 'Therefore we do not lose heart. Though outwardly we are wasting away, yet inwardly we are being renewed day by day. For our light and momentary troubles are achieving for us an eternal glory.',
                            'teaching_point': 'Present sufferings are temporary and serve a purpose in God\'s plan, leading to future glory and spiritual growth.',
                            'application': 'Select music that maintains eternal perspective on current struggles and encourages perseverance through difficulty.',
                            'contrast_principle': 'Choose music that finds meaning in suffering and points to eternal hope rather than focusing only on present pain.'
                        }
                    ]
                },
                
                'rebellion_authority': {
                    'category': 'Authority and Submission',
                    'concern_addressed': 'rebellion_authority',
                    'scriptures': [
                        {
                            'reference': 'Romans 13:1',
                            'text': 'Let everyone be subject to the governing authorities, for there is no authority except that which God has established.',
                            'teaching_point': 'God establishes human authority structures and expects believers to respect them, even when we disagree.',
                            'application': 'Choose music that promotes respect for legitimate authority while maintaining allegiance to God\'s ultimate authority.',
                            'contrast_principle': 'Seek music that models respectful disagreement and constructive change rather than rebellious defiance.'
                        },
                        {
                            'reference': 'Hebrews 13:17',
                            'text': 'Have confidence in your leaders and submit to their authority, because they keep watch over you as those who must give an account.',
                            'teaching_point': 'Submission to authority is not weakness but recognition of God\'s order and the accountability of leaders.',
                            'application': 'Select music that encourages working within proper channels for change rather than promoting destructive rebellion.',
                            'contrast_principle': 'Choose music that promotes wisdom, patience, and respectful engagement over angry rebellion.'
                        },
                        {
                            'reference': '1 Peter 2:13-14',
                            'text': 'Submit yourselves for the Lord\'s sake to every human authority: whether to the emperor, as the supreme authority, or to governors, who are sent by him to punish the wrongdoer and to commend those who do right.',
                            'teaching_point': 'Submission to authority is ultimately an act of obedience to God, not just compliance with human institutions.',
                            'application': 'Choose music that demonstrates respect for authority as a way of honoring God, even while seeking justice.',
                            'contrast_principle': 'Seek music that promotes positive change through proper channels rather than destructive rebellion.'
                        }
                    ]
                },
                
                'false_teaching': {
                    'category': 'Truth and Doctrine',
                    'concern_addressed': 'false_teaching',
                    'scriptures': [
                        {
                            'reference': 'John 14:6',
                            'text': 'Jesus answered, "I am the way and the truth and the life. No one comes to the Father except through me."',
                            'teaching_point': 'Jesus claims to be the exclusive path to God, making Christianity unique among world religions.',
                            'application': 'Avoid music that promotes religious pluralism or suggests multiple paths to God apart from Jesus Christ.',
                            'contrast_principle': 'Choose music that affirms the uniqueness of Christ and the exclusivity of salvation through Him.'
                        },
                        {
                            'reference': 'Galatians 1:8-9',
                            'text': 'But even if we or an angel from heaven should preach a gospel other than the one we preached to you, let them be under God\'s curse!',
                            'teaching_point': 'The gospel message is unchanging and must not be modified to fit cultural preferences or alternative teachings.',
                            'application': 'Be cautious of music that modifies core Christian doctrines or promotes teachings contrary to Scripture.',
                            'contrast_principle': 'Seek music that affirms traditional Christian doctrine and the authority of Scripture.'
                        },
                        {
                            'reference': '2 Timothy 4:3-4',
                            'text': 'For the time will come when people will not put up with sound doctrine. Instead, to suit their own desires, they will gather around them a great number of teachers to say what their itching ears want to hear.',
                            'teaching_point': 'There is a natural human tendency to prefer comfortable lies over difficult truths, making discernment essential.',
                            'application': 'Choose music that challenges you with biblical truth rather than simply reinforcing what you want to hear.',
                            'contrast_principle': 'Seek music that upholds sound doctrine even when it challenges popular culture or personal preferences.'
                        }
                    ]
                }
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
    
    def find_scriptural_foundation_for_concern(self, concern_type: str) -> List[Dict[str, Any]]:
        """
        Find scriptural foundations for a specific concern type.
        
        This method provides biblical context for why certain content types are concerning,
        supporting comprehensive discernment training.
        
        Args:
            concern_type: The type of concern (e.g., 'explicit_language', 'substance_abuse')
            
        Returns:
            List of scripture references with biblical foundation for the concern
        """
        concern_themes = self.scripture_database.get('concern_themes', {})
        if concern_type not in concern_themes:
            return []
        
        concern_theme = concern_themes[concern_type]
        scripture_refs = []
        
        for scripture in concern_theme['scriptures']:
            scripture_ref = {
                'reference': scripture['reference'],
                'text': scripture['text'],
                'theme': concern_theme['category'],  # Use category as the theme name
                'category': concern_theme['category'],
                'relevance': scripture['teaching_point'],  # Use teaching_point as relevance
                'application': scripture['application'],
                'educational_value': f"This passage helps understand why {concern_type} is concerning from a biblical perspective.",
                'concern_type': concern_type
            }
            scripture_refs.append(scripture_ref)
        
        return scripture_refs
    
    def find_scriptural_foundation_for_concerns(self, concerns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find scriptural foundation for detected concerns to provide biblical context
        for why certain content may be problematic.
        
        Args:
            concerns: List of detected concerns with type and severity
            
        Returns:
            List of scriptural foundations with teaching context
        """
        try:
            scriptural_foundations = []
            
            for concern in concerns:
                concern_type = concern.get('type')
                if not concern_type:
                    continue
                    
                # Look up concern in our concern_themes database
                concern_themes = self.scripture_database.get('concern_themes', {})
                if concern_type in concern_themes:
                    concern_data = concern_themes[concern_type]
                    
                    # Get primary scripture reference for this concern
                    scriptures = concern_data.get('scriptures', [])
                    if scriptures:
                        primary_scripture = scriptures[0]  # Take the first as primary
                        
                        scriptural_foundations.append({
                            'concern_type': concern_type,
                            'biblical_theme': concern_data['category'].lower().replace(' ', '_'),
                            'scriptures': [primary_scripture],
                            'teaching_summary': primary_scripture['teaching_point'],
                            'practical_application': primary_scripture['application'],
                            'alternative_approach': primary_scripture['contrast_principle'],
                            'severity_context': f"This {concern.get('severity', 'medium')} concern has biblical foundation for discernment."
                        })
            
            return scriptural_foundations
            
        except Exception as e:
            logger.error(f"Error finding scriptural foundation for concerns: {e}")
            return []
    
    def get_comprehensive_scripture_references(self, positive_themes: List[str], concern_themes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get comprehensive scripture references covering both positive themes and concerns
        to provide balanced biblical education.
        
        Args:
            positive_themes: List of positive biblical themes found
            concern_themes: List of concern types with their biblical themes
            
        Returns:
            Comprehensive scripture reference structure with balanced teaching
        """
        try:
            # Get positive references using existing method
            positive_references = self.find_relevant_passages(positive_themes)
            
            # Convert concern themes to list of concerns for processing
            concerns = [{'type': theme['concern_type']} for theme in concern_themes if 'concern_type' in theme]
            concern_references = self.find_scriptural_foundation_for_concerns(concerns)
            
            # Generate balanced teaching that addresses both sides
            balanced_teaching = self._generate_balanced_teaching(positive_references, concern_references)
            
            return {
                'positive_references': positive_references,
                'concern_references': concern_references,
                'balanced_teaching': balanced_teaching,
                'total_scripture_count': len(positive_references) + len(concern_references),
                'educational_summary': self._generate_educational_summary(positive_references, concern_references)
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive scripture references: {e}")
            return {
                'positive_references': [],
                'concern_references': [],
                'balanced_teaching': [],
                'total_scripture_count': 0,
                'educational_summary': 'Scripture analysis temporarily unavailable.'
            }
    
    def _generate_balanced_teaching(self, positive_refs: List[Dict], concern_refs: List[Dict]) -> List[str]:
        """Generate balanced teaching points from both positive and concern references."""
        teaching_points = []
        
        if positive_refs and concern_refs:
            teaching_points.append(
                "This content provides an opportunity for balanced discernment - celebrating what aligns with biblical truth while learning why certain elements may be concerning."
            )
            teaching_points.append(
                f"The {len(positive_refs)} positive themes show godly elements, while the {len(concern_refs)} areas of concern provide learning opportunities about biblical standards."
            )
        elif positive_refs:
            teaching_points.append(
                "This content aligns well with biblical themes, providing positive spiritual input for growth."
            )
        elif concern_refs:
            teaching_points.append(
                "This content primarily presents opportunities for discernment, learning why certain themes conflict with biblical principles."
            )
        
        # Add specific teaching from concern references
        for concern_ref in concern_refs[:2]:  # Limit to top 2 for brevity
            teaching_points.append(
                f"Regarding {concern_ref['concern_type'].replace('_', ' ')}: {concern_ref['teaching_summary']}"
            )
        
        return teaching_points
    
    def _generate_educational_summary(self, positive_refs: List[Dict], concern_refs: List[Dict]) -> str:
        """Generate an educational summary of the biblical analysis."""
        if not positive_refs and not concern_refs:
            return "No biblical themes or concerns identified for educational analysis."
        
        summary_parts = []
        
        if positive_refs:
            summary_parts.append(f"Found {len(positive_refs)} positive biblical theme(s) that support spiritual growth")
        
        if concern_refs:
            summary_parts.append(f"identified {len(concern_refs)} area(s) where biblical discernment can provide guidance")
        
        summary = "This analysis " + " and ".join(summary_parts) + "."
        
        if positive_refs and concern_refs:
            summary += " This combination provides an excellent opportunity for developing mature Christian discernment."
        elif positive_refs:
            summary += " This content supports your spiritual journey with biblical truth."
        else:
            summary += " This provides valuable learning about biblical standards and godly choices."
        
        return summary 