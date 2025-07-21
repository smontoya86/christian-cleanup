"""
Phase 2 TDD Tests: Character & Spiritual Themes Detection

Tests for the 10 character and spiritual themes:
- Endurance: Perseverance by faith (+6 points)
- Obedience: Willingness to follow God (+5 points)  
- Justice: Advocacy for truth and righteousness (+5 points)
- Mercy: Compassion for others (+4 points)
- Truth: Moral and doctrinal fidelity (+4 points)
- Identity in Christ: New creation reality (+5 points)
- Victory in Christ: Triumph over sin and death (+4 points)
- Gratitude: Thankful posture before God (+4 points)
- Discipleship: Following Jesus intentionally (+4 points)
- Evangelistic Zeal: Passion to proclaim Christ (+4 points)

Following TDD methodology: Write tests first, then implement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestCharacterSpiritualThemes:
    """Test Character & Spiritual Themes detection with enhanced HuggingFace models."""
    
    @pytest.fixture
    def mock_hf_analyzer(self):
        """Create a mock HuggingFace analyzer for testing."""
        with patch('app.utils.analysis.huggingface_analyzer.pipeline') as mock_pipeline:
            analyzer = HuggingFaceAnalyzer()
            
            # Mock the analyzers
            analyzer._sentiment_analyzer = Mock()
            analyzer._safety_analyzer = Mock()
            analyzer._emotion_analyzer = Mock()
            analyzer._theme_analyzer = Mock()
            
            return analyzer

    @pytest.fixture
    def endurance_song(self):
        """Sample song demonstrating endurance/perseverance themes."""
        return {
            "title": "Through the Storm",
            "artist": "Christian Endurance Band",
            "lyrics": """
                When the storm rages on and I cannot see the light
                I will trust in Your promise, hold on through the night
                Perseverance is my strength, endurance is my song
                Through trials I will stand, by faith I carry on
                
                Never give up, never surrender to fear
                The race is not over, victory is near
                Patient endurance leads to spiritual growth
                Standing firm in trials, keeping faithful oath
            """
        }

    @pytest.fixture
    def obedience_song(self):
        """Sample song demonstrating obedience themes."""
        return {
            "title": "Follow You",
            "artist": "Obedient Heart",
            "lyrics": """
                Lord, I choose to follow where You lead
                Obedience is better than sacrifice indeed
                Your commands are not a burden to bear
                I submit to Your will with faith and prayer
                
                Not my will but Yours be done
                Walking in obedience to the Holy One
                Surrendering my plans to Your design
                Your ways are higher, Your will divine
            """
        }

    @pytest.fixture
    def justice_song(self):
        """Sample song demonstrating justice themes."""
        return {
            "title": "Stand for Justice",
            "artist": "Righteous Warriors",
            "lyrics": """
                Stand up for justice, defend the oppressed
                Fight for the righteous, put evil to test
                God loves justice, He hates what is wrong
                We are His hands, His justice made strong
                
                Speak for the voiceless, defend the weak
                Let justice roll down like waters that speak
                Righteousness matters, truth will prevail
                God's justice endures, it will never fail
            """
        }

    @pytest.fixture
    def mercy_song(self):
        """Sample song demonstrating mercy themes."""
        return {
            "title": "Merciful Heart",
            "artist": "Compassion Ministry",
            "lyrics": """
                Show mercy to others as God shows to you
                Compassion and kindness in all that you do
                Forgive as forgiven, love as you're loved
                Mercy flows freely from the Father above
                
                Blessed are the merciful, they will receive
                The mercy of God, His grace they'll perceive
                Kind hearts and gentle spirits filled with grace
                Reflecting God's mercy in every place
            """
        }

    @pytest.fixture
    def truth_song(self):
        """Sample song demonstrating truth themes."""
        return {
            "title": "Truth Prevails",
            "artist": "Doctrine Defenders",
            "lyrics": """
                Your Word is truth, it lights my way
                In a world of lies, truth shows the day
                Sound doctrine matters, theology clear
                Biblical truth we hold so dear
                
                Test everything against Your Word
                Let false teaching never be heard
                Truth is absolute, not relative
                In Your truth alone we truly live
            """
        }

    @pytest.fixture
    def identity_in_christ_song(self):
        """Sample song demonstrating identity in Christ themes."""
        return {
            "title": "New Creation",
            "artist": "Identity Ministry",
            "lyrics": """
                I am a new creation in Christ Jesus
                Old things have passed away, behold the new
                My identity is found in Him alone
                Child of God, this truth I've always known
                
                No longer slave to sin but free indeed
                In Christ I have all that I will ever need
                His righteousness covers all my shame
                I am who He says I am, blessed be His name
            """
        }

    @pytest.fixture
    def victory_in_christ_song(self):
        """Sample song demonstrating victory in Christ themes."""
        return {
            "title": "Victory Song",
            "artist": "Triumphant Church",
            "lyrics": """
                We have victory in Jesus, triumph over sin
                Death has lost its sting, the battle's won within
                Christ has conquered Satan, evil has no power
                Victory is ours in this triumphant hour
                
                Resurrection power lives within our hearts
                Overcoming spirit, victory imparts
                More than conquerors through Him who loves us
                In Christ we triumph, in Him we trust
            """
        }

    @pytest.fixture
    def gratitude_song(self):
        """Sample song demonstrating gratitude themes."""
        return {
            "title": "Thankful Heart",
            "artist": "Grateful Worshipers",
            "lyrics": """
                Thankful for Your blessings, grateful for Your love
                All good gifts come down from the Father above
                In everything give thanks, this is Your will
                Grateful hearts worship You, praising You still
                
                Count your many blessings, name them one by one
                Thanksgiving fills our hearts for all that You have done
                Grateful living demonstrates Your grace
                Thankful hearts reflect Your love in every place
            """
        }

    @pytest.fixture
    def discipleship_song(self):
        """Sample song demonstrating discipleship themes."""
        return {
            "title": "Follow Jesus",
            "artist": "Disciple Makers",
            "lyrics": """
                Take up your cross and follow Me
                The path of discipleship will set you free
                Count the cost and walk this way
                Growing closer to Christ each day
                
                Make disciples of all nations
                Teaching them His declarations
                Spiritual growth through study and prayer
                Following Jesus everywhere
            """
        }

    @pytest.fixture
    def evangelistic_zeal_song(self):
        """Sample song demonstrating evangelistic zeal themes."""
        return {
            "title": "Go and Tell",
            "artist": "Mission Heart",
            "lyrics": """
                Go and tell the world about Jesus
                Share the gospel message true
                Passion for the lost compels us
                Souls to save and lives renew
                
                Great Commission is our calling
                Preach the Word to every nation
                Evangelistic fire is burning
                Hearts aflame for God's salvation
            """
        }

    def test_endurance_theme_detection(self, mock_hf_analyzer, endurance_song):
        """Test endurance/perseverance theme detection."""
        # Mock zero-shot classification for endurance themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Perseverance and endurance', 'score': 0.91},
            {'label': 'Faith through trials', 'score': 0.88},
            {'label': 'Spiritual perseverance', 'score': 0.85}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.82}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.94}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'determination', 'score': 0.86}]
        
        result = mock_hf_analyzer.analyze_song(
            endurance_song["title"],
            endurance_song["artist"],
            endurance_song["lyrics"]
        )
        
        # Expected: +6 points for endurance theme
        assert result is not None
        
        # Check for endurance-related themes
        themes = result.biblical_analysis.get('themes', [])
        endurance_keywords = ['endurance', 'perseverance', 'trials', 'standing firm', 'never give up']
        endurance_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in endurance_keywords)
            for t in themes
        )
        assert endurance_themes_found, "Should detect endurance/perseverance themes"
        
        # Score should reflect endurance points
        assert result.scoring_results['final_score'] >= 40, "Endurance themes should contribute meaningfully to score"

    def test_obedience_theme_detection(self, mock_hf_analyzer, obedience_song):
        """Test obedience theme detection."""
        # Mock zero-shot classification for obedience themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Obedience to God', 'score': 0.93},
            {'label': 'Submission to divine will', 'score': 0.90},
            {'label': 'Following Gods commands', 'score': 0.87}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.89}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.96}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'devotion', 'score': 0.84}]
        
        result = mock_hf_analyzer.analyze_song(
            obedience_song["title"],
            obedience_song["artist"],
            obedience_song["lyrics"]
        )
        
        # Expected: +5 points for obedience theme
        assert result is not None
        
        # Check for obedience-related themes
        themes = result.biblical_analysis.get('themes', [])
        obedience_keywords = ['obedience', 'submit', 'follow', 'commands', 'will']
        obedience_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in obedience_keywords)
            for t in themes
        )
        assert obedience_themes_found, "Should detect obedience themes"

    def test_justice_theme_detection(self, mock_hf_analyzer, justice_song):
        """Test justice theme detection."""
        # Mock zero-shot classification for justice themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Justice and righteousness', 'score': 0.94},
            {'label': 'Defending the oppressed', 'score': 0.89},
            {'label': 'Gods justice', 'score': 0.86}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.87}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.95}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'righteousness', 'score': 0.88}]
        
        result = mock_hf_analyzer.analyze_song(
            justice_song["title"],
            justice_song["artist"],
            justice_song["lyrics"]
        )
        
        # Expected: +5 points for justice theme
        assert result is not None
        
        # Check for justice-related themes
        themes = result.biblical_analysis.get('themes', [])
        justice_keywords = ['justice', 'righteous', 'defend', 'oppressed', 'truth']
        justice_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in justice_keywords)
            for t in themes
        )
        assert justice_themes_found, "Should detect justice themes"

    def test_mercy_theme_detection(self, mock_hf_analyzer, mercy_song):
        """Test mercy theme detection."""
        # Mock zero-shot classification for mercy themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Mercy and compassion', 'score': 0.92},
            {'label': 'Showing kindness', 'score': 0.88},
            {'label': 'Gods mercy', 'score': 0.85}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.91}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.97}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'compassion', 'score': 0.90}]
        
        result = mock_hf_analyzer.analyze_song(
            mercy_song["title"],
            mercy_song["artist"],
            mercy_song["lyrics"]
        )
        
        # Expected: +4 points for mercy theme
        assert result is not None
        
        # Check for mercy-related themes
        themes = result.biblical_analysis.get('themes', [])
        mercy_keywords = ['mercy', 'compassion', 'kindness', 'forgive', 'gentle']
        mercy_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in mercy_keywords)
            for t in themes
        )
        assert mercy_themes_found, "Should detect mercy themes"

    def test_truth_theme_detection(self, mock_hf_analyzer, truth_song):
        """Test truth theme detection."""
        # Mock zero-shot classification for truth themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Biblical truth and doctrine', 'score': 0.95},
            {'label': 'Gods Word as truth', 'score': 0.91},
            {'label': 'Sound doctrine', 'score': 0.87}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.85}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.96}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'conviction', 'score': 0.83}]
        
        result = mock_hf_analyzer.analyze_song(
            truth_song["title"],
            truth_song["artist"],
            truth_song["lyrics"]
        )
        
        # Expected: +4 points for truth theme
        assert result is not None
        
        # Check for truth-related themes
        themes = result.biblical_analysis.get('themes', [])
        truth_keywords = ['truth', 'doctrine', 'word', 'biblical', 'teaching']
        truth_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in truth_keywords)
            for t in themes
        )
        assert truth_themes_found, "Should detect truth themes"

    def test_identity_in_christ_detection(self, mock_hf_analyzer, identity_in_christ_song):
        """Test identity in Christ theme detection."""
        # Mock zero-shot classification for identity themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Identity in Christ', 'score': 0.96},
            {'label': 'New creation in Christ', 'score': 0.93},
            {'label': 'Child of God identity', 'score': 0.89}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.92}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.98}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'confidence', 'score': 0.87}]
        
        result = mock_hf_analyzer.analyze_song(
            identity_in_christ_song["title"],
            identity_in_christ_song["artist"],
            identity_in_christ_song["lyrics"]
        )
        
        # Expected: +5 points for identity in Christ theme
        assert result is not None
        
        # Check for identity-related themes  
        themes = result.biblical_analysis.get('themes', [])
        identity_keywords = ['identity', 'new creation', 'child of god', 'who he says', 'in christ']
        identity_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in identity_keywords)
            for t in themes
        )
        assert identity_themes_found, "Should detect identity in Christ themes"

    def test_victory_in_christ_detection(self, mock_hf_analyzer, victory_in_christ_song):
        """Test victory in Christ theme detection."""
        # Mock zero-shot classification for victory themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Victory in Christ', 'score': 0.94},
            {'label': 'Triumph over sin and death', 'score': 0.91},
            {'label': 'Spiritual victory', 'score': 0.88}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.90}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.95}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'triumph', 'score': 0.89}]
        
        result = mock_hf_analyzer.analyze_song(
            victory_in_christ_song["title"],
            victory_in_christ_song["artist"],
            victory_in_christ_song["lyrics"]
        )
        
        # Expected: +4 points for victory theme
        assert result is not None
        
        # Check for victory-related themes
        themes = result.biblical_analysis.get('themes', [])
        victory_keywords = ['victory', 'triumph', 'overcome', 'conquer', 'resurrection power']
        victory_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in victory_keywords)
            for t in themes
        )
        assert victory_themes_found, "Should detect victory in Christ themes"

    def test_gratitude_theme_detection(self, mock_hf_analyzer, gratitude_song):
        """Test gratitude theme detection."""
        # Mock zero-shot classification for gratitude themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Gratitude and thanksgiving', 'score': 0.93},
            {'label': 'Thankful heart', 'score': 0.90},
            {'label': 'Counting blessings', 'score': 0.86}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.94}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.97}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'gratitude', 'score': 0.91}]
        
        result = mock_hf_analyzer.analyze_song(
            gratitude_song["title"],
            gratitude_song["artist"],
            gratitude_song["lyrics"]
        )
        
        # Expected: +4 points for gratitude theme
        assert result is not None
        
        # Check for gratitude-related themes
        themes = result.biblical_analysis.get('themes', [])
        gratitude_keywords = ['gratitude', 'thankful', 'grateful', 'blessing', 'thanksgiving', 'praise']
        gratitude_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in gratitude_keywords)
            for t in themes
        )
        assert gratitude_themes_found, "Should detect gratitude themes"

    def test_discipleship_theme_detection(self, mock_hf_analyzer, discipleship_song):
        """Test discipleship theme detection."""
        # Mock zero-shot classification for discipleship themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Discipleship and following Jesus', 'score': 0.95},
            {'label': 'Spiritual growth', 'score': 0.89},
            {'label': 'Take up your cross', 'score': 0.86}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.86}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.94}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'devotion', 'score': 0.85}]
        
        result = mock_hf_analyzer.analyze_song(
            discipleship_song["title"],
            discipleship_song["artist"],
            discipleship_song["lyrics"]
        )
        
        # Expected: +4 points for discipleship theme
        assert result is not None
        
        # Check for discipleship-related themes
        themes = result.biblical_analysis.get('themes', [])
        discipleship_keywords = ['discipleship', 'follow', 'cross', 'spiritual growth', 'disciple']
        discipleship_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in discipleship_keywords)
            for t in themes
        )
        assert discipleship_themes_found, "Should detect discipleship themes"

    def test_evangelistic_zeal_detection(self, mock_hf_analyzer, evangelistic_zeal_song):
        """Test evangelistic zeal theme detection."""
        # Mock zero-shot classification for evangelistic themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Evangelism and mission', 'score': 0.96},
            {'label': 'Great Commission', 'score': 0.92},
            {'label': 'Sharing the gospel', 'score': 0.88}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.88}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.96}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'passion', 'score': 0.90}]
        
        result = mock_hf_analyzer.analyze_song(
            evangelistic_zeal_song["title"],
            evangelistic_zeal_song["artist"],
            evangelistic_zeal_song["lyrics"]
        )
        
        # Expected: +4 points for evangelistic zeal theme
        assert result is not None
        
        # Check for evangelistic-related themes
        themes = result.biblical_analysis.get('themes', [])
        evangelistic_keywords = ['gospel', 'mission', 'evangelism', 'great commission', 'share']
        evangelistic_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in evangelistic_keywords)
            for t in themes
        )
        assert evangelistic_themes_found, "Should detect evangelistic zeal themes"

    def test_phase2_combined_themes_scoring(self, mock_hf_analyzer):
        """Test combined Phase 2 themes contribute appropriately to scoring."""
        # Mock zero-shot classification for multiple Phase 2 themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Perseverance and endurance', 'score': 0.90},
            {'label': 'Obedience to God', 'score': 0.88},
            {'label': 'Justice and righteousness', 'score': 0.85},
            {'label': 'Mercy and compassion', 'score': 0.83}
        ]
        
        # Mock other analyzers for positive song
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.89}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.96}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.87}]
        
        result = mock_hf_analyzer.analyze_song(
            "Combined Themes Song",
            "Character Builder",
            "A song with endurance, obedience, justice, and mercy themes combined"
        )
        
        # Expected: Multiple theme points should accumulate
        assert result is not None
        
        # Should have high score due to multiple character themes
        assert result.scoring_results['final_score'] >= 60, "Multiple Phase 2 themes should result in high score"
        
        # Should detect multiple character themes
        themes = result.biblical_analysis.get('themes', [])
        assert len(themes) >= 3, "Should detect multiple character themes"

    def test_phase2_false_positive_prevention(self, mock_hf_analyzer):
        """Test Phase 2 doesn't create false positives for secular songs."""
        # Mock zero-shot classification for secular song
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Romantic love', 'score': 0.92},
            {'label': 'Personal success', 'score': 0.88},
            {'label': 'Material wealth', 'score': 0.85}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.85}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.93}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'happiness', 'score': 0.82}]
        
        result = mock_hf_analyzer.analyze_song(
            "Love Song",
            "Pop Artist",
            "A secular love song about romantic relationships and personal success"
        )
        
        # Should not falsely detect Phase 2 character themes
        assert result is not None
        
        themes = result.biblical_analysis.get('themes', [])
        phase2_keywords = ['endurance', 'obedience', 'justice', 'mercy', 'truth', 'identity', 'victory', 'gratitude', 'discipleship', 'evangelism']
        phase2_false_positives = any(
            any(keyword in t.get('theme', '').lower() for keyword in phase2_keywords)
            for t in themes
        )
        assert not phase2_false_positives, "Should not falsely detect Phase 2 themes in secular content"

    def test_phase2_integration_with_phase1(self, mock_hf_analyzer):
        """Test Phase 2 themes work together with Phase 1 Core Gospel themes."""
        # Mock zero-shot classification combining Phase 1 and Phase 2 themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            # Phase 1 themes
            {'label': 'Christ-centered worship', 'score': 0.94},
            {'label': 'Gospel presentation', 'score': 0.91},
            # Phase 2 themes
            {'label': 'Perseverance and endurance', 'score': 0.88},
            {'label': 'Obedience to God', 'score': 0.86}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.92}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.97}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'worship', 'score': 0.90}]
        
        result = mock_hf_analyzer.analyze_song(
            "Complete Christian Song",
            "Full Gospel Band",
            "A song combining Christ-centered worship, gospel message, endurance, and obedience"
        )
        
        # Should detect both Phase 1 and Phase 2 themes
        assert result is not None
        
        themes = result.biblical_analysis.get('themes', [])
        
        # Check for Phase 1 themes
        phase1_keywords = ['christ', 'gospel', 'redemption', 'sacrificial love', 'light']
        phase1_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in phase1_keywords)
            for t in themes
        )
        
        # Check for Phase 2 themes
        phase2_keywords = ['endurance', 'obedience', 'perseverance']
        phase2_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in phase2_keywords)
            for t in themes
        )
        
        assert phase1_themes_found, "Should still detect Phase 1 themes"
        assert phase2_themes_found, "Should detect Phase 2 themes"
        
        # Combined themes should result in very high score
        assert result.scoring_results['final_score'] >= 80, "Combined Phase 1 + Phase 2 themes should score very highly" 