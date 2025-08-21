import logging
import os

import requests
from dotenv import load_dotenv

from app.config import config

logger = logging.getLogger(__name__)


class BibleClient:
    # Preferred Bible IDs
    BSB_ID = "bba9f40183526463-01"  # Berean Standard Bible
    KJV_ID = "de4e12af7f28f599-01"  # King James Version

    def __init__(self, preferred_bible_id=None):
        load_dotenv()

        # Use centralized config first
        self.api_key = config.BIBLE_API_KEY

        # Fallback to Flask app config if centralized config doesn't have it
        if not self.api_key:
            try:
                from flask import current_app

                if current_app and "BIBLE_API_KEY" in current_app.config:
                    self.api_key = current_app.config["BIBLE_API_KEY"]
            except (RuntimeError, ImportError):  # Not in Flask app context or Flask not available
                pass

        # Final fallback to environment variable for backwards compatibility
        if not self.api_key:
            self.api_key = os.environ.get("BIBLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "BIBLE_API_KEY not found. Set the BIBLE_API_KEY environment variable "
                "or configure it in the centralized config."
            )

        self.base_url = "https://api.scripture.api.bible/v1"
        self.default_bible_id = preferred_bible_id if preferred_bible_id else self.BSB_ID
        self.fallback_bible_id = self.KJV_ID

    def _make_request(self, endpoint, params=None, bible_id_in_path=True):
        headers = {"api-key": self.api_key}

        # Construct URL: some endpoints include bibleId in path, others as param
        if bible_id_in_path:
            # This case is typical for /verses, /passages, /books, /chapters
            # The actual bible_id part will be part of the 'endpoint' string passed
            full_url = f"{self.base_url}/{endpoint}"
        else:
            # This case is for /bibles (listing all) or potentially /search if bibleId is a query param
            full_url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(full_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(
                f"HTTP error occurred: {http_err} for URL: {full_url} with params: {params}"
            )

            # Fallback to KJV if BSB fails
            if bible_id_in_path and self.default_bible_id == self.BSB_ID and self.fallback_bible_id:
                fallback_endpoint = endpoint.replace(self.BSB_ID, self.fallback_bible_id)
                logger.info(f"Attempting fallback with KJV: {fallback_endpoint}")
                try:
                    response = requests.get(
                        fallback_endpoint, headers=headers, params=params, timeout=10
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError as fallback_http_err:
                    logger.error(f"Fallback HTTP error occurred: {fallback_http_err}")
                    return None
                except Exception as fallback_err:
                    logger.error(f"Fallback other error occurred: {fallback_err}")
                    return None
            return None
        except Exception as err:
            logger.error(f"Other error occurred: {err} for URL: {full_url}")
            return None

    def get_available_bibles(self, language="eng"):
        params = {}
        if language:
            params["language"] = language
        data = self._make_request("bibles", params=params, bible_id_in_path=False)
        if data and "data" in data:
            return data["data"]
        return []

    def get_verse(self, verse_ref, bible_id=None):
        """
        Fetches a single verse.
        verse_ref should be in API format e.g., "JHN.3.16"
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/verses/{verse_ref}"
        # Pass content_type to get plain text if desired, or other options
        params = {"content-type": "text", "include-notes": "false", "include-titles": "false"}
        data = self._make_request(endpoint, params=params)
        return data.get("data") if data else None

    def get_passage(self, passage_ref, bible_id=None):
        """
        Fetches a passage (range of verses).
        passage_ref should be in API format e.g., "JHN.3.16-JHN.3.18"
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/passages/{passage_ref}"
        params = {"content-type": "text", "include-notes": "false", "include-titles": "false"}
        data = self._make_request(endpoint, params=params)
        return data.get("data") if data else None

    def search(self, query, bible_id=None, limit=5, sort_option="relevance"):
        """
        Searches for verses/passages by query.
        sort_option can be 'relevance' or 'canonical'
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/search"
        params = {"query": query, "limit": limit, "sort": sort_option}
        # For search, bible_id is part of the path, not a query param for the _make_request logic
        data = self._make_request(endpoint, params=params)

        # The search endpoint returns a more complex structure
        if data and "data" in data and "verses" in data["data"]:
            return data["data"]["verses"]  # Or passages depending on query
        elif data and "data" in data and "passages" in data["data"]:
            return data["data"]["passages"]
        return []


def test_client():
    """Test the BibleClient functionality."""
    client = BibleClient()

    logger.info("--- Testing get_verse (John 3:16) ---")
    verse_data_bsb = client.get_verse("JHN", 3, 16)
    if verse_data_bsb:
        logger.info(f"BSB (JHN.3.16): {verse_data_bsb.get('content')}")
    else:
        logger.info("Could not fetch John 3:16 from BSB.")

    verse_data_kjv = client.get_verse("JHN", 3, 16, bible_id="592420522e16049f-01")
    if verse_data_kjv:
        logger.info(f"KJV (JHN.3.16): {verse_data_kjv.get('content')}")
    else:
        logger.info("Could not fetch John 3:16 from KJV.")

    logger.info("--- Testing get_passage (Romans 12:1-2) ---")
    passage_data_bsb = client.get_passage("ROM", 12, 1, 2)
    if passage_data_bsb:
        logger.info(f"BSB (ROM.12.1-2): {passage_data_bsb.get('content')}")
    else:
        logger.info("Could not fetch Romans 12:1-2 from BSB.")

    logger.info("--- Testing search ('love never fails') ---")
    search_results_bsb = client.search("love never fails")
    if search_results_bsb:
        logger.info("BSB Search results for 'love never fails':")
        for item in search_results_bsb[:3]:  # Show first 3 results
            logger.info(
                f"  - {item.get('reference')}: {item.get('text', item.get('content', 'N/A'))[:100]}..."
            )
    else:
        logger.info("No search results from BSB or error.")

    logger.info("--- Testing search ('faith hope love') ---")
    search_results_kjv = client.search("faith hope love", bible_id="592420522e16049f-01")
    if search_results_kjv:
        logger.info("KJV Search results for 'faith hope love':")
        for item in search_results_kjv[:3]:  # Show first 3 results
            logger.info(
                f"  - {item.get('reference')}: {item.get('text', item.get('content', 'N/A'))[:100]}..."
            )
    else:
        logger.info("No search results from KJV or error.")

    # Test fallback (using a verse that might not be in BSB or some other error)
    # For demonstration, let's assume a hypothetical verse "MAL.5.1" isn't in BSB
    # This part is tricky to reliably test without knowing a verse truly absent in BSB but present in KJV
    # Or by simulating an error. The current fallback is basic.
    # print("\n--- Testing fallback (simulated) ---")
    # verse_data_fallback = client.get_verse("MAL.5.1") # Using default (BSB), hoping it might trigger fallback
    # if verse_data_fallback:
    #    print(f"Verse MAL.5.1 (BSB or KJV fallback): {verse_data_fallback.get('content')}")
    # else:
    #    print("Could not fetch MAL.5.1 from BSB or KJV fallback.")
