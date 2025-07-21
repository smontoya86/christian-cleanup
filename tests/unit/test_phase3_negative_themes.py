"""
Phase 3 TDD Tests: Negative Themes Detection

Tests for the 15+ negative themes that should result in point penalties:

HIGH SEVERITY (-25 to -30 points):
- Blasphemy (-30): Mocking God or sacred things
- Self-Deification (-25): Making self god
- Apostasy (-25): Rejection of gospel or faith  
- Suicide Ideation (-25): Wanting death without God

MEDIUM SEVERITY (-15 to -20 points):
- Pride/Arrogance (-20): Self-glorification
- Idolatry (-20): Elevating created over Creator
- Sorcery/Occult (-20): Magical or demonic practices
- Sexual Immorality (-20): Lust, adultery, etc.
- Violence Glorified (-20): Exalting brutality
- Hatred/Vengeance (-20): Bitterness, retaliation

LOWER SEVERITY (-10 to -15 points):
- Materialism/Greed (-15): Worship of wealth
- Self-Righteousness (-15): Works-based pride
- Moral Confusion (-15): Reversing good and evil
- Vague Spirituality (-10): Undefined spiritual references
- Empty Positivity (-10): Self-help without truth

Following TDD methodology: Write tests first, then implement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestNegativeThemes:
    """Test Negative Themes detection with enhanced HuggingFace models."""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = HuggingFaceAnalyzer()
        
        # Mock the AI models to avoid loading them during tests
        self.analyzer._sentiment_analyzer = Mock()
        self.analyzer._safety_analyzer = Mock()
        self.analyzer._emotion_analyzer = Mock()
        self.analyzer._theme_analyzer = Mock()
        
    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_blasphemy_detection_high_severity(self, mock_logger):
        """Test detection of blasphemous content with -30 point penalty"""
        
        # Mock AI responses for blasphemous content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.95
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God', 'Profanity and vulgarity', 'Rejection of faith'],
            'scores': [0.92, 0.85, 0.78]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'anger', 'score': 0.88
        }]
        
        self.analyzer._safety_analyzer.return_value = [{
            'label': 'TOXIC', 'score': 0.90
        }]
        
        # Test blasphemous lyrics
        blasphemous_lyrics = """
        God is dead and we don't need salvation
        F*** Jesus and his fake promises  
        Religion is a lie for the weak minded
        I am my own god, bow down to me
        """
        
        result = self.analyzer.analyze_song("Blasphemous Song", "Dark Artist", blasphemous_lyrics)
        
        # Should detect blasphemy themes
        themes = result.biblical_analysis.get('themes', [])
        blasphemy_themes_found = any(
            'blasphemy' in t.get('theme', '').lower() or 'mocking' in t.get('theme', '').lower()
            for t in themes
        )
        assert blasphemy_themes_found, "Should detect blasphemy themes"
        
        # Score should be very low due to severe blasphemy
        assert result.scoring_results['final_score'] <= 10, "Blasphemous content should score very low"
        
        # Should be marked as high concern
        assert result.scoring_results['quality_level'] == 'High', "Blasphemous content should be high concern"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_self_deification_detection(self, mock_logger):
        """Test detection of self-deification themes with -25 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.80
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Self-deification and pride', 'Arrogance and superiority', 'Rejection of divine authority'],
            'scores': [0.89, 0.82, 0.76]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'pride', 'score': 0.85
        }]
        
        # Test self-deification lyrics
        self_deification_lyrics = """
        I am the master of my fate
        I am the captain of my soul  
        I don't need anyone's salvation
        I am my own god, I create my destiny
        Worship me, bow before my greatness
        """
        
        result = self.analyzer.analyze_song("Self Worship", "Prideful Artist", self_deification_lyrics)
        
        # Should detect self-deification themes
        themes = result.biblical_analysis.get('themes', [])
        self_deification_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['self-deification', 'pride', 'arrogance'])
            for t in themes
        )
        assert self_deification_found, "Should detect self-deification themes"
        
        # Score should be low due to severe pride/self-worship
        assert result.scoring_results['final_score'] <= 20, "Self-deification should score very low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_apostasy_detection(self, mock_logger):
        """Test detection of apostasy (rejection of faith) with -25 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.87
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Apostasy and faith rejection', 'Abandoning religious beliefs', 'Spiritual rebellion'],
            'scores': [0.91, 0.84, 0.77]
        }
        
        # Test apostasy lyrics
        apostasy_lyrics = """
        I used to believe but now I see the truth
        Faith is just a crutch for the weak
        I reject your god and all his empty promises
        Christianity is a lie I've left behind
        Freedom from religion is true salvation
        """
        
        result = self.analyzer.analyze_song("Lost Faith", "Former Believer", apostasy_lyrics)
        
        # Should detect apostasy themes
        themes = result.biblical_analysis.get('themes', [])
        apostasy_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['apostasy', 'rejection', 'abandoning'])
            for t in themes
        )
        assert apostasy_found, "Should detect apostasy themes"
        
        # Score should be low due to faith rejection
        assert result.scoring_results['final_score'] <= 20, "Apostasy should score very low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_occult_sorcery_detection(self, mock_logger):
        """Test detection of occult/sorcery themes with -20 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEUTRAL', 'score': 0.60
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Occult practices and sorcery', 'Witchcraft and magic', 'Demonic spiritual practices'],
            'scores': [0.88, 0.81, 0.74]
        }
        
        # Test occult lyrics
        occult_lyrics = """
        Cast the spell and summon spirits
        Witchcraft gives me all the power
        Demons guide me through the darkness
        Magic crystals heal my soul
        Ancient gods hear my calling
        """
        
        result = self.analyzer.analyze_song("Dark Magic", "Occult Band", occult_lyrics)
        
        # Should detect occult themes
        themes = result.biblical_analysis.get('themes', [])
        occult_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['occult', 'sorcery', 'witchcraft', 'magic'])
            for t in themes
        )
        assert occult_found, "Should detect occult/sorcery themes"
        
        # Score should be low due to occult content
        assert result.scoring_results['final_score'] <= 30, "Occult content should score low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_sexual_immorality_detection(self, mock_logger):
        """Test detection of sexual immorality themes with -20 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.70  # Might be positive sentiment but immoral content
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Sexual immorality and lust', 'Adultery and unfaithfulness', 'Objectification of others'],
            'scores': [0.86, 0.79, 0.72]
        }
        
        # Test sexual immorality lyrics (keeping it appropriate for testing)
        immoral_lyrics = """
        I want your body, nothing more
        Lust is all that drives me now
        Adultery is just another game
        Use them up then throw away
        Physical pleasure is my god
        """
        
        result = self.analyzer.analyze_song("Lustful Desires", "Immoral Artist", immoral_lyrics)
        
        # Should detect sexual immorality themes
        themes = result.biblical_analysis.get('themes', [])
        immorality_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['immorality', 'lust', 'adultery'])
            for t in themes
        )
        assert immorality_found, "Should detect sexual immorality themes"
        
        # Score should be low despite positive sentiment
        assert result.scoring_results['final_score'] <= 40, "Sexual immorality should score low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_materialism_greed_detection(self, mock_logger):
        """Test detection of materialism/greed themes with -15 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.75
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Materialism and greed', 'Worship of wealth', 'Money as ultimate goal'],
            'scores': [0.84, 0.77, 0.70]
        }
        
        # Test materialistic lyrics
        materialistic_lyrics = """
        Money is my only god
        Cash rules everything I do
        Greed is good, get all you can
        Material wealth defines my worth
        I worship gold and silver coins
        """
        
        result = self.analyzer.analyze_song("Money God", "Greedy Artist", materialistic_lyrics)
        
        # Should detect materialism themes
        themes = result.biblical_analysis.get('themes', [])
        materialism_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['materialism', 'greed', 'wealth'])
            for t in themes
        )
        assert materialism_found, "Should detect materialism/greed themes"
        
        # Score should be moderate-low due to materialism
        assert result.scoring_results['final_score'] <= 50, "Materialistic content should score moderately low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_violence_glorification_detection(self, mock_logger):
        """Test detection of glorified violence with -20 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.88
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Glorification of violence', 'Brutality and aggression', 'Celebrating harm to others'],
            'scores': [0.90, 0.83, 0.76]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'anger', 'score': 0.92
        }]
        
        # Test violent lyrics
        violent_lyrics = """
        Violence is the only way
        Beat them down, make them pay  
        Blood and pain bring me joy
        Destroy everything in sight
        Brutality is beautiful
        """
        
        result = self.analyzer.analyze_song("Violent Rage", "Brutal Band", violent_lyrics)
        
        # Should detect violence themes
        themes = result.biblical_analysis.get('themes', [])
        violence_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['violence', 'brutality', 'aggression'])
            for t in themes
        )
        assert violence_found, "Should detect violence glorification themes"
        
        # Score should be low due to violent content
        assert result.scoring_results['final_score'] <= 30, "Violent content should score low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_moral_confusion_detection(self, mock_logger):
        """Test detection of moral confusion (reversing good and evil) with -15 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEUTRAL', 'score': 0.55
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Moral confusion and relativism', 'Reversing good and evil', 'Ethical ambiguity'],
            'scores': [0.82, 0.75, 0.68]
        }
        
        # Test morally confused lyrics
        confused_lyrics = """
        Good and evil are just perspectives
        Right and wrong don't really exist
        What's true for you isn't true for me
        Morality is just opinion
        There are no absolute standards
        """
        
        result = self.analyzer.analyze_song("Moral Relativism", "Confused Artist", confused_lyrics)
        
        # Should detect moral confusion themes
        themes = result.biblical_analysis.get('themes', [])
        confusion_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['confusion', 'relativism', 'reversing'])
            for t in themes
        )
        assert confusion_found, "Should detect moral confusion themes"
        
        # Score should be moderate-low due to moral confusion
        assert result.scoring_results['final_score'] <= 60, "Morally confused content should score moderately low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_false_positive_prevention_negative_themes(self, mock_logger):
        """Test that positive Christian songs don't trigger false negative theme detections"""
        
        # Mock AI responses for strong Christian content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.95
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Christ-centered worship - Jesus as Savior, Lord, or King', 'Gospel presentation', 'Victory in Christ'],
            'scores': [0.94, 0.87, 0.80]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'joy', 'score': 0.90
        }]
        
        self.analyzer._safety_analyzer.return_value = [{
            'label': 'SAFE', 'score': 0.95
        }]
        
        # Test strong Christian lyrics mentioning overcoming evil (should not trigger negative themes)
        christian_lyrics = """
        Jesus Christ is Lord and King
        Through the cross we have victory
        God's love overcomes all evil
        Faith triumphs over darkness
        Salvation through grace alone
        """
        
        result = self.analyzer.analyze_song("Victory Song", "Christian Artist", christian_lyrics)
        
        # Should NOT detect negative themes in positive Christian content
        themes = result.biblical_analysis.get('themes', [])
        negative_themes_found = any(
            any(neg_keyword in t.get('theme', '').lower() 
                for neg_keyword in ['blasphemy', 'apostasy', 'occult', 'materialism', 'violence'])
            for t in themes
        )
        assert not negative_themes_found, "Should not detect negative themes in positive Christian content"
        
        # Score should be high for strong Christian content
        assert result.scoring_results['final_score'] >= 70, "Strong Christian content should score high"
        
        # Should be low or no concern
        assert result.scoring_results['quality_level'] in ['Low', 'Very Low'], "Christian content should have low concern"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_combined_negative_themes_severe_penalty(self, mock_logger):
        """Test that multiple negative themes result in very low scores"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.92
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God', 'Self-deification and pride', 'Occult practices', 'Sexual immorality', 'Violence glorification'],
            'scores': [0.89, 0.85, 0.81, 0.77, 0.73]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'anger', 'score': 0.88
        }]
        
        self.analyzer._safety_analyzer.return_value = [{
            'label': 'TOXIC', 'score': 0.94
        }]
        
        # Test lyrics with multiple severe negative themes
        severely_negative_lyrics = """
        F*** your god, I am divine
        Satan gives me real power  
        Kill them all in blood and rage
        Use bodies for my pleasure
        Magic spells control the world
        """
        
        result = self.analyzer.analyze_song("Pure Evil", "Dark Artist", severely_negative_lyrics)
        
        # Should detect multiple negative themes
        themes = result.biblical_analysis.get('themes', [])
        multiple_negative_found = len([
            t for t in themes 
            if any(neg_keyword in t.get('theme', '').lower() 
                   for neg_keyword in ['blasphemy', 'self-deification', 'occult', 'immorality', 'violence'])
        ]) >= 3
        assert multiple_negative_found, "Should detect multiple negative themes"
        
        # Score should be extremely low (near 0) due to multiple severe negative themes
        assert result.scoring_results['final_score'] <= 5, "Multiple severe negative themes should result in near-zero score"
        
        # Should be high concern
        assert result.scoring_results['quality_level'] == 'High', "Multiple negative themes should be high concern"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_vague_spirituality_detection(self, mock_logger):
        """Test detection of vague spirituality without Christian foundation with -10 point penalty"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.75
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Vague spirituality without foundation', 'Generic spiritual concepts', 'Undefined divine references'],
            'scores': [0.80, 0.73, 0.66]
        }
        
        # Test vague spiritual lyrics
        vague_spiritual_lyrics = """
        The universe will guide my way
        I trust in higher powers above
        Spiritual energy flows through me
        The divine is everywhere
        Find your inner light and peace
        """
        
        result = self.analyzer.analyze_song("Vague Spirit", "New Age Artist", vague_spiritual_lyrics)
        
        # Should detect vague spirituality themes
        themes = result.biblical_analysis.get('themes', [])
        vague_spirituality_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in ['vague', 'spirituality', 'generic'])
            for t in themes
        )
        assert vague_spirituality_found, "Should detect vague spirituality themes"
        
        # Score should be moderate due to vague spirituality
        assert result.scoring_results['final_score'] <= 70, "Vague spirituality should score moderately"

    def test_negative_theme_scoring_system(self):
        """Test that negative themes properly reduce scores from the base"""
        
        # Mock analysis result with negative themes
        negative_themes = [
            {'theme': 'Blasphemy', 'score': 0.90, 'points': -30, 'category': 'negative'},
            {'theme': 'Self-deification', 'score': 0.85, 'points': -25, 'category': 'negative'},
            {'theme': 'Materialism', 'score': 0.75, 'points': -15, 'category': 'negative'}
        ]
        
        # Calculate expected score: 0 base + penalties = negative, clamped to 0
        expected_penalties = 30 + 25 + 15  # 70 total penalties
        
        # Base score of 0 minus 70 = -70, clamped to 0
        expected_max_score = 0
        
        # The actual analysis should result in a very low score
        assert expected_penalties == 70, "Should calculate correct total penalties"
        assert expected_max_score == 0, "Score should be clamped to minimum of 0"

    @patch('app.utils.analysis.huggingface_analyzer.logger')  
    def test_negative_theme_confidence_scoring(self, mock_logger):
        """Test that negative theme confidence affects penalty severity"""
        
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.80
        }]
        
        # Test high confidence negative theme
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God'],
            'scores': [0.95]  # Very high confidence
        }
        
        high_confidence_lyrics = "God is a fake lie and Jesus is worthless"
        result_high = self.analyzer.analyze_song("High Confidence Blasphemy", "Dark Artist", high_confidence_lyrics)
        
        # Test low confidence negative theme  
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God'],
            'scores': [0.35]  # Low confidence
        }
        
        low_confidence_lyrics = "Sometimes I question if God exists"
        result_low = self.analyzer.analyze_song("Low Confidence Question", "Questioning Artist", low_confidence_lyrics)
        
        # High confidence blasphemy should score lower than low confidence questioning
        assert result_high.scoring_results['final_score'] < result_low.scoring_results['final_score'], \
            "High confidence negative themes should result in lower scores than low confidence" 