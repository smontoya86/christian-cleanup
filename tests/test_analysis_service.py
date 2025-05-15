import unittest
from unittest.mock import patch, MagicMock, call
import pytest
import os
import sys
import json

# Adjust path for imports if necessary (often not needed with proper project structure and pytest)
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Direct imports
from app.utils.analysis import SongAnalyzer # Updated import
from app.models import Song, AnalysisResult # Assuming models are defined here
from app import db # Assuming db is initialized here

# --- Test Data ---
MOCK_SONG_ID = 1
MOCK_SONG_TITLE = "Test Song"
# MOCK_SCRIPTURE_REF_1 = "JHN.3.16" # No longer primary source for this test's internal data
# MOCK_SCRIPTURE_REF_2 = "ROM.8.28"
# MOCK_SCRIPTURE_TEXT_1 = "God so loved the world..."
# MOCK_SCRIPTURE_TEXT_2 = "All things work together for good..."

# Scripture data for the specific test case
TEST_CASE_SCRIPTURE_REF_A = "HEB.11.1"
TEST_CASE_SCRIPTURE_TEXT_A = "Now faith is confidence in what we hope for..."
TEST_CASE_SCRIPTURE_REF_B = "PRO.3.5"
TEST_CASE_SCRIPTURE_TEXT_B = "Trust in the LORD with all your heart..."
TEST_CASE_SCRIPTURE_REF_C = "EPH.1.7"
TEST_CASE_SCRIPTURE_TEXT_C = "In him we have redemption through his blood..."

# Mock AI model response structure
# MOCK_AI_ANALYSIS_RAW = { # This constant is not directly used by the test, the test redefines it locally.
# "themes": [
# {"theme": "Faith", "scriptures": [MOCK_SCRIPTURE_REF_1]},
# {"theme": "Hope", "scriptures": [MOCK_SCRIPTURE_REF_2]}
# ]
# }

# Expected structure after BibleService integration - This will be defined locally in the test
# EXPECTED_FINAL_ANALYSIS = [
# {"theme": "Faith", "scriptures": [{"reference": MOCK_SCRIPTURE_REF_1, "text": MOCK_SCRIPTURE_TEXT_1}]},
# {"theme": "Hope", "scriptures": [{"reference": MOCK_SCRIPTURE_REF_2, "text": MOCK_SCRIPTURE_TEXT_2}]}
# ]


class TestAnalysisServiceIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        # Create a mock song object
        self.mock_song = Song(id=MOCK_SONG_ID, title=MOCK_SONG_TITLE)
        # Always reset mocks for safety between tests
        # db.session.reset_mock() # db will be mocked via @patch now


    @pytest.mark.xfail(reason="BibleService integration not yet implemented in AnalysisService methods")
    @patch('app.services.bible_service.BibleService') # Mock BibleService
    @patch('app.services.analysis_service.db') # Mock database used within analysis_service
    def test_analyze_song_integrates_bible_service(self, mock_db_in_service, mock_bible_service_class):
        """Test that analyze_song correctly calls BibleService and formats results."""

        # --- Mock Configuration ---
        # Configure the mock db session that the service will use
        mock_db_session = mock_db_in_service.session

        # Mock Bible Service
        mock_bible_instance = mock_bible_service_class.return_value
        mock_bible_instance.api_key = "fake-key" # Simulate key exists

        # Define side effect for get_scripture_text based on input
        def bible_side_effect(passage_id, bible_id=None):
            # if passage_id == MOCK_SCRIPTURE_REF_1:
            #     return MOCK_SCRIPTURE_TEXT_1
            # elif passage_id == MOCK_SCRIPTURE_REF_2:
            #     return MOCK_SCRIPTURE_TEXT_2
            if passage_id == TEST_CASE_SCRIPTURE_REF_A:
                return TEST_CASE_SCRIPTURE_TEXT_A
            elif passage_id == TEST_CASE_SCRIPTURE_REF_B:
                return TEST_CASE_SCRIPTURE_TEXT_B
            elif passage_id == TEST_CASE_SCRIPTURE_REF_C:
                return TEST_CASE_SCRIPTURE_TEXT_C
            else:
                return "Unknown reference"
        mock_bible_instance.get_scripture_text.side_effect = bible_side_effect

        # --- Data specific to this test case's mocked AI response ---
        # This is the AI response the service code will actually process in this test
        ai_response_for_test = {
            "sensitive_content": [{"category": "Profanity", "level": "Low", "details": "Mild curse word found"}],
            "themes": [
                {"theme": "Faith", "keywords": ["believe", "trust"], "scriptures": [TEST_CASE_SCRIPTURE_REF_A, TEST_CASE_SCRIPTURE_REF_B]},
                {"theme": "Redemption", "keywords": ["saved", "forgiven"], "scriptures": [TEST_CASE_SCRIPTURE_REF_C]}
            ]
        }
        # This is what SongAnalyzer.analyze_song will return, after scripture enrichment
        expected_result_for_this_test_case = [
            {"theme": "Faith", "keywords": ["believe", "trust"], 
             "scriptures": [
                 {"reference": TEST_CASE_SCRIPTURE_REF_A, "text": TEST_CASE_SCRIPTURE_TEXT_A},
                 {"reference": TEST_CASE_SCRIPTURE_REF_B, "text": TEST_CASE_SCRIPTURE_TEXT_B}
             ]},
            {"theme": "Redemption", "keywords": ["saved", "forgiven"], 
             "scriptures": [
                 {"reference": TEST_CASE_SCRIPTURE_REF_C, "text": TEST_CASE_SCRIPTURE_TEXT_C}
             ]}
        ]

        # --- Execution ---
        analyzer = SongAnalyzer()

        # Mocked return value for _get_cardiffnlp_predictions
        # For this test, we are not focused on purity flags from cardiff, so a neutral/empty output is fine.
        mock_cardiff_output = [] 

        # Mocked return value for _detect_christian_themes
        # ai_response_for_test["themes"] is a list of theme dicts like [{"theme": "Faith", ...}, ...]
        # _detect_christian_themes should return (positive_themes, negative_themes)
        # We'll use the "themes" part from ai_response_for_test as positive_themes.
        mock_positive_themes_from_ai_test = ai_response_for_test.get("themes", [])
        mock_negative_themes_from_ai_test = [] # Assuming no negative themes for this specific input

        # Patch the internal methods of the analyzer instance
        with patch.object(analyzer, '_get_cardiffnlp_predictions', return_value=mock_cardiff_output), \
             patch.object(analyzer, '_detect_christian_themes', return_value=(mock_positive_themes_from_ai_test, mock_negative_themes_from_ai_test)):
            # Call analyze_song with title and artist from the mock_song, and provide some dummy lyrics
            # as the actual lyrics content isn't the focus for mocking _detect_christian_themes here.
            result_analysis = analyzer.analyze_song(
                title=self.mock_song.title, 
                artist=self.mock_song.artist, 
                lyrics_text="Some dummy lyrics for testing theme processing."
            )

        # --- Assertions ---
        # 1. Check BibleService was called correctly
        mock_bible_service_class.assert_called_once() # Ensure BibleService was instantiated
        self.assertEqual(mock_bible_instance.get_scripture_text.call_count, 3) # Should be 3 based on mock data
        # mock_bible_instance.get_scripture_text.assert_any_call(MOCK_SCRIPTURE_REF_1)
        # mock_bible_instance.get_scripture_text.assert_any_call(MOCK_SCRIPTURE_REF_2)
        mock_bible_instance.get_scripture_text.assert_any_call(TEST_CASE_SCRIPTURE_REF_A)
        mock_bible_instance.get_scripture_text.assert_any_call(TEST_CASE_SCRIPTURE_REF_B)
        mock_bible_instance.get_scripture_text.assert_any_call(TEST_CASE_SCRIPTURE_REF_C)

        # 2. Check the returned analysis structure matches the expected final format
        self.assertIsNotNone(result_analysis)
        # self.assertEqual(result_analysis, EXPECTED_FINAL_ANALYSIS)
        self.assertEqual(result_analysis, expected_result_for_this_test_case)

        # 3. Check database interaction using the *mocked* db session
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # 4. Verify the object added to the session is AnalysisResult with correct data
        added_object = mock_db_session.add.call_args[0][0]
        self.assertIsInstance(added_object, AnalysisResult)
        self.assertEqual(added_object.song_id, MOCK_SONG_ID)
        # Compare the JSON string stored in the themes field
        # Need to handle potential import issues if AnalysisResult is mocked
        # This check is now more direct as AnalysisResult should be properly imported
        # self.assertEqual(json.loads(added_object.themes), EXPECTED_FINAL_ANALYSIS)
        self.assertEqual(json.loads(added_object.themes), expected_result_for_this_test_case)
        # Optionally check raw_analysis if needed


if __name__ == '__main__':
    # Ensure the 'tests' directory exists
    if not os.path.exists('tests'):
        os.makedirs('tests')
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
