import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests

# Ensure the app directory is in the path for imports
# Adjust the path as necessary based on your project structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Conditional import based on file existence
bible_service_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'services', 'bible_service.py'))
if os.path.exists(bible_service_path):
    from app.services.bible_service import BibleService
else:
    # Define a dummy class if the service doesn't exist to avoid import errors
    # during test discovery before the file is created
    print("Warning: app/services/bible_service.py not found. Using dummy BibleService for tests.")
    class BibleService:
        def __init__(self): self.api_key = None
        def get_scripture_text(self, passage_id, bible_id=None): return None

# --- Test Data ---
MOCK_API_KEY = "test-api-key"
VALID_PASSAGE_ID = "JHN.3.16"
INVALID_PASSAGE_ID = "XYZ.1.1" # Assuming this doesn't exist

# Mock successful API response
MOCK_SUCCESS_RESPONSE = {
    "data": {
        "id": "JHN.3.16",
        "bibleId": BibleService.DEFAULT_BIBLE_ID,
        "bookId": "JHN",
        "chapterId": "JHN.3",
        "content": "<p class=\"p\">[16] For God so loved the world, that he gave his only Son, that whoever believes in him should not perish but have eternal life.</p>",
        "verseCount": 1,
        "copyright": "ESV...",
        "next": None,
        "previous": None
    },
    "meta": {} # Meta content omitted for brevity
}

# Mock response for content not found (but API call successful)
MOCK_NOT_FOUND_CONTENT_RESPONSE = {
    "data": {
        "id": INVALID_PASSAGE_ID,
        "bibleId": BibleService.DEFAULT_BIBLE_ID,
        "bookId": "XYZ", # Fictional book
        "content": "", # Empty content
        # other fields might be present or absent
    },
     "meta": {}
}

# Mock response for API 404 (e.g., invalid Bible ID or endpoint)
# Note: This structure might vary based on API.Bible's actual 404 response
MOCK_404_RESPONSE = {
    "statusCode": 404,
    "error": "Not Found",
    "message": "Bible not found."
}


class TestBibleService(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Ensure API key is set for tests that need it
        os.environ["BIBLE_API_KEY"] = MOCK_API_KEY
        self.service = BibleService()

    def tearDown(self):
        """Clean up after test methods."""
        # Remove environment variable to avoid interference
        if "BIBLE_API_KEY" in os.environ:
            del os.environ["BIBLE_API_KEY"]

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_success(self, mock_get):
        """Test successful retrieval of scripture text."""
        # Configure the mock response for a successful API call
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = MOCK_SUCCESS_RESPONSE
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        text = self.service.get_scripture_text(VALID_PASSAGE_ID)

        self.assertIsNotNone(text)
        self.assertIn("For God so loved the world", text) # Check for expected content
        self.assertNotIn("<p", text) # Check basic HTML stripping
        # Verify the correct URL and headers were used
        expected_url = f"{BibleService.BASE_URL}/bibles/{BibleService.DEFAULT_BIBLE_ID}/passages/{VALID_PASSAGE_ID}"
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], expected_url)
        self.assertEqual(kwargs['headers']['api-key'], MOCK_API_KEY)
        self.assertEqual(kwargs['params']['content-type'], 'text')

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_api_key_missing(self, mock_get):
        """Test behavior when API key is not set."""
        # Unset the API key for this specific test
        if "BIBLE_API_KEY" in os.environ:
            del os.environ["BIBLE_API_KEY"]
        service_no_key = BibleService() # Re-initialize without key

        # Explicitly check the internal api_key attribute
        self.assertIsNone(service_no_key.api_key)

        text = service_no_key.get_scripture_text(VALID_PASSAGE_ID)

        self.assertIsNone(text)
        mock_get.assert_not_called() # API should not be called

        # Restore key for other tests if needed within this class instance lifecycle
        os.environ["BIBLE_API_KEY"] = MOCK_API_KEY
        self.service = BibleService() # Re-initialize service for subsequent tests

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_api_http_error(self, mock_get):
        """Test handling of HTTP errors (e.g., 404, 500) from the API."""
        # Configure the mock to raise an HTTPError
        mock_response = MagicMock()
        # Simulate a 404 error
        error = requests.exceptions.HTTPError("404 Client Error: Not Found for url")
        error.response = MagicMock(status_code=404, text=str(MOCK_404_RESPONSE))
        mock_response.raise_for_status.side_effect = error
        mock_get.return_value = mock_response

        text = self.service.get_scripture_text(INVALID_PASSAGE_ID)

        self.assertIsNone(text)
        mock_get.assert_called_once() # API call was attempted

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_network_error(self, mock_get):
        """Test handling of network connection errors."""
        # Configure the mock to raise a ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        text = self.service.get_scripture_text(VALID_PASSAGE_ID)

        self.assertIsNone(text)
        mock_get.assert_called_once() # API call was attempted

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_no_content_in_response(self, mock_get):
        """Test handling when API returns success but no 'content' field."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # Simulate response missing the 'content' or having empty content
        mock_response.json.return_value = MOCK_NOT_FOUND_CONTENT_RESPONSE
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        text = self.service.get_scripture_text(INVALID_PASSAGE_ID)

        self.assertIsNone(text) # Should return None if content is missing/empty
        mock_get.assert_called_once()

    @patch('app.services.bible_service.requests.get')
    def test_get_scripture_text_with_specific_bible_id(self, mock_get):
        """Test using a non-default Bible ID."""
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # Modify mock response slightly to reflect the different Bible ID if necessary
        mock_success_kjv = MOCK_SUCCESS_RESPONSE.copy()
        mock_success_kjv['data']['bibleId'] = 'kjv-bible-id'
        mock_response.json.return_value = mock_success_kjv
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        specific_bible_id = "kjv-bible-id" # Example KJV ID (replace if known)
        text = self.service.get_scripture_text(VALID_PASSAGE_ID, bible_id=specific_bible_id)

        self.assertIsNotNone(text)
        # Verify the correct URL was called with the specific Bible ID
        expected_url = f"{BibleService.BASE_URL}/bibles/{specific_bible_id}/passages/{VALID_PASSAGE_ID}"
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], expected_url)


if __name__ == '__main__':
    # Ensure the 'tests' directory exists
    if not os.path.exists('tests'):
        os.makedirs('tests')
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
