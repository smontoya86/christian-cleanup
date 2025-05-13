import os
import requests
import logging
from flask import current_app
from typing import Optional

logger = logging.getLogger(__name__)

class BibleService:
    BASE_URL = "https://api.scripture.api.bible/v1"
    # Default to ESV Bible ID
    DEFAULT_BIBLE_ID = "de4e12af7f28f599-01"

    def __init__(self):
        self.api_key = os.getenv("BIBLE_API_KEY")
        if not self.api_key:
            logger.error("BIBLE_API_KEY not found in environment variables.")
            # Optionally raise an error or handle appropriately
            # raise ValueError("BIBLE_API_KEY is required.")

    def get_scripture_text(self, passage_id: str, bible_id: str = None) -> Optional[str]:
        """Fetches scripture text for a given passage ID (e.g., 'JHN.3.16') from API.Bible."""
        if not self.api_key:
            logger.error("Cannot fetch scripture: API key is missing.")
            return None

        target_bible_id = bible_id or self.DEFAULT_BIBLE_ID
        # Use the /passages endpoint as it's flexible
        url = f"{self.BASE_URL}/bibles/{target_bible_id}/passages/{passage_id}"
        headers = {"api-key": self.api_key}
        params = {
            'content-type': 'text', # Request plain text
            'include-notes': 'false',
            'include-titles': 'false',
            'include-chapter-numbers': 'false',
            'include-verse-numbers': 'true', # Include verse numbers in the text
            'include-verse-spans': 'false'
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            data = response.json()
            content = data.get("data", {}).get("content")

            if content:
                # Clean up potential HTML tags if content-type 'html' was used, though 'text' is preferred
                # Basic cleanup, might need refinement based on actual API responses
                import re
                text_content = re.sub('<[^>]*>', '', content).strip()
                logger.debug(f"Successfully fetched scripture for {passage_id}: {text_content[:100]}...")
                return text_content
            else:
                logger.warning(f"No content found for passage {passage_id} in Bible {target_bible_id}. Response: {data}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for passage {passage_id}: {e}")
            # Check for specific status codes if needed (e.g., 404 for not found)
            if e.response is not None:
                logger.error(f"Response status: {e.response.status_code}, Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching passage {passage_id}: {e}")
            return None

# Example usage (for testing purposes):
# if __name__ == '__main__':
#     # Make sure BIBLE_API_KEY is set as an environment variable
#     # e.g., export BIBLE_API_KEY='your_actual_key'
#     service = BibleService()
#     if service.api_key:
#         text = service.get_scripture_text("JHN.3.16-17")
#         if text:
#             print("John 3:16-17 (ESV):", text)
#         else:
#             print("Failed to fetch John 3:16-17")
#
#         text_psalm = service.get_scripture_text("PSA.23.1-3")
#         if text_psalm:
#             print("\nPsalm 23:1-3 (ESV):", text_psalm)
#         else:
#             print("Failed to fetch Psalm 23:1-3")
#     else:
#         print("BibleService could not be initialized due to missing API key.")
