import os
import requests
from dotenv import load_dotenv

class BibleClient:
    # Preferred Bible IDs
    BSB_ID = "bba9f40183526463-01"  # Berean Standard Bible
    KJV_ID = "de4e12af7f28f599-01"  # King James Version

    def __init__(self, preferred_bible_id=None):
        load_dotenv()
        self.api_key = os.getenv("BIBLE_API_KEY")
        if not self.api_key:
            raise ValueError("BIBLE_API_KEY not found in .env file")
        self.base_url = "https://api.scripture.api.bible/v1"
        self.default_bible_id = preferred_bible_id if preferred_bible_id else self.BSB_ID
        self.fallback_bible_id = self.KJV_ID

    def _make_request(self, endpoint, params=None, bible_id_in_path=True):
        headers = {'api-key': self.api_key}
        
        # Construct URL: some endpoints include bibleId in path, others as param
        if bible_id_in_path:
            # This case is typical for /verses, /passages, /books, /chapters
            # The actual bible_id part will be part of the 'endpoint' string passed
            full_url = f"{self.base_url}/{endpoint}"
        else:
            # This case is for /bibles (listing all) or potentially /search if bibleId is a query param
            full_url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(full_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} for URL: {full_url} with params: {params}")
            # Attempt fallback if it's an error that might be version-specific (e.g., verse not in BSB)
            # This basic fallback might not always be appropriate, e.g. if BSB itself is invalid.
            # A more sophisticated retry/fallback would check the error type.
            if bible_id_in_path and self.default_bible_id == self.BSB_ID and self.fallback_bible_id:
                 # Construct fallback endpoint by replacing BSB_ID with KJV_ID in the endpoint string
                if self.BSB_ID in endpoint:
                    fallback_endpoint = endpoint.replace(self.BSB_ID, self.fallback_bible_id)
                    print(f"Attempting fallback with KJV: {fallback_endpoint}")
                    try:
                        response = requests.get(f"{self.base_url}/{fallback_endpoint}", headers=headers, params=params)
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.HTTPError as fallback_http_err:
                        print(f"Fallback HTTP error occurred: {fallback_http_err}")
                        return None
                    except Exception as fallback_err:
                        print(f"Fallback other error occurred: {fallback_err}")
                        return None
            return None
        except Exception as err:
            print(f"Other error occurred: {err} for URL: {full_url}")
            return None

    def get_available_bibles(self, language='eng'):
        params = {}
        if language:
            params['language'] = language
        data = self._make_request("bibles", params=params, bible_id_in_path=False)
        if data and 'data' in data:
            return data['data']
        return []

    def get_verse(self, verse_ref, bible_id=None):
        """
        Fetches a single verse.
        verse_ref should be in API format e.g., "JHN.3.16"
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/verses/{verse_ref}"
        # Pass content_type to get plain text if desired, or other options
        params = {'content-type': 'text', 'include-notes': 'false', 'include-titles': 'false'}
        data = self._make_request(endpoint, params=params)
        return data.get('data') if data else None

    def get_passage(self, passage_ref, bible_id=None):
        """
        Fetches a passage (range of verses).
        passage_ref should be in API format e.g., "JHN.3.16-JHN.3.18"
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/passages/{passage_ref}"
        params = {'content-type': 'text', 'include-notes': 'false', 'include-titles': 'false'}
        data = self._make_request(endpoint, params=params)
        return data.get('data') if data else None

    def search(self, query, bible_id=None, limit=5, sort_option='relevance'):
        """
        Searches for verses/passages by query.
        sort_option can be 'relevance' or 'canonical'
        """
        target_bible_id = bible_id if bible_id else self.default_bible_id
        endpoint = f"bibles/{target_bible_id}/search"
        params = {
            'query': query,
            'limit': limit,
            'sort': sort_option
        }
        # For search, bible_id is part of the path, not a query param for the _make_request logic
        data = self._make_request(endpoint, params=params) 
        
        # The search endpoint returns a more complex structure
        if data and 'data' in data and 'verses' in data['data']:
             return data['data']['verses'] # Or passages depending on query
        elif data and 'data' in data and 'passages' in data['data']:
             return data['data']['passages']
        return []


if __name__ == '__main__':
    client = BibleClient()

    # --- Test get_available_bibles ---
    # print("Available English Bible Versions:")
    # bibles = client.get_available_bibles(language='eng')
    # if bibles:
    #     for bible in bibles:
    #         print(f"- ID: {bible.get('id')}, Name: {bible.get('name')}, Abbreviation: {bible.get('abbreviation')}")
    # else:
    #     print("Could not fetch Bible versions.")

    # --- Test get_verse ---
    print("\n--- Testing get_verse (John 3:16) ---")
    verse_data_bsb = client.get_verse("JHN.3.16", bible_id=BibleClient.BSB_ID)
    if verse_data_bsb:
        print(f"BSB (JHN.3.16): {verse_data_bsb.get('content')}")
    else:
        print("Could not fetch John 3:16 from BSB.")

    verse_data_kjv = client.get_verse("JHN.3.16", bible_id=BibleClient.KJV_ID)
    if verse_data_kjv:
        print(f"KJV (JHN.3.16): {verse_data_kjv.get('content')}")
    else:
        print("Could not fetch John 3:16 from KJV.")
    
    # --- Test get_passage ---
    print("\n--- Testing get_passage (Romans 12:1-2) ---")
    passage_data_bsb = client.get_passage("ROM.12.1-ROM.12.2", bible_id=BibleClient.BSB_ID)
    if passage_data_bsb:
        print(f"BSB (ROM.12.1-2): {passage_data_bsb.get('content')}")
    else:
        print("Could not fetch Romans 12:1-2 from BSB.")

    # --- Test search ---
    print("\n--- Testing search ('love never fails') ---")
    search_results_bsb = client.search("love never fails", bible_id=BibleClient.BSB_ID, limit=3)
    if search_results_bsb:
        print("BSB Search results for 'love never fails':")
        for item in search_results_bsb:
            print(f"  - {item.get('reference')}: {item.get('text', item.get('content', 'N/A'))[:100]}...") # text or content field
    else:
        print("No search results from BSB or error.")

    print("\n--- Testing search ('faith hope love') ---")
    search_results_kjv = client.search("faith hope love", bible_id=BibleClient.KJV_ID, limit=3)
    if search_results_kjv:
        print("KJV Search results for 'faith hope love':")
        for item in search_results_kjv:
            print(f"  - {item.get('reference')}: {item.get('text', item.get('content', 'N/A'))[:100]}...")
    else:
        print("No search results from KJV or error.")

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
