import os
import requests
import logging
from flask import current_app
from typing import Optional
import re # For reference parsing

logger = logging.getLogger(__name__)

class BibleService:
    BASE_URL = "https://api.scripture.api.bible/v1"
    BSB_BIBLE_ID = "bba9f40183526463-01"  # Berean Standard Bible
    KJV_BIBLE_ID = "de4e12af7f28f599-01"  # King James Version
    DEFAULT_BIBLE_ID = BSB_BIBLE_ID

    BOOK_TO_API_CODE_MAP = {
        # Old Testament (Abbreviated list for brevity, extend as needed)
        "Genesis": "GEN", "Gen": "GEN", "Ge": "GEN",
        "Exodus": "EXO", "Ex": "EXO",
        "Leviticus": "LEV", "Lev": "LEV",
        "Numbers": "NUM", "Num": "NUM",
        "Deuteronomy": "DEU", "Deut": "DEU",
        "Joshua": "JOS", "Josh": "JOS",
        "Judges": "JDG", "Judg": "JDG",
        "Ruth": "RUT", "Ru": "RUT",
        "1 Samuel": "1SA", "1 Sam": "1SA", "1S": "1SA",
        "2 Samuel": "2SA", "2 Sam": "2SA", "2S": "2SA",
        "1 Kings": "1KI", "1 Kgs": "1KI",
        "2 Kings": "2KI", "2 Kgs": "2KI",
        "1 Chronicles": "1CH", "1 Chr": "1CH", "1Chr": "1CH",
        "2 Chronicles": "2CH", "2 Chr": "2CH", "2Chr": "2CH",
        "Ezra": "EZR",
        "Nehemiah": "NEH", "Neh": "NEH",
        "Esther": "EST", "Esth": "EST",
        "Job": "JOB",
        "Psalm": "PSA", "Psalms": "PSA", "Psa": "PSA", "Ps": "PSA",
        "Proverbs": "PRO", "Prov": "PRO", "Prv": "PRO", "Pr": "PRO",
        "Ecclesiastes": "ECC", "Eccl": "ECC", "Ecc": "ECC",
        "Song of Solomon": "SNG", "Song": "SNG", "SOS": "SNG", "Song of Songs": "SNG",
        "Isaiah": "ISA", "Isa": "ISA",
        "Jeremiah": "JER", "Jer": "JER",
        "Lamentations": "LAM", "Lam": "LAM",
        "Ezekiel": "EZK", "Ezek": "EZK",
        "Daniel": "DAN", "Dan": "DAN",
        "Hosea": "HOS", "Hos": "HOS",
        "Joel": "JOL",
        "Amos": "AMO",
        "Obadiah": "OBA", "Obad": "OBA", "Ob": "OBA",
        "Jonah": "JON", "Jnh": "JON",
        "Micah": "MIC", "Mic": "MIC",
        "Nahum": "NAM", "Nah": "NAM",
        "Habakkuk": "HAB", "Hab": "HAB",
        "Zephaniah": "ZEP", "Zeph": "ZEP",
        "Haggai": "HAG", "Hag": "HAG",
        "Zechariah": "ZEC", "Zech": "ZEC",
        "Malachi": "MAL", "Mal": "MAL",

        # New Testament
        "Matthew": "MAT", "Matt": "MAT", "Mt": "MAT",
        "Mark": "MRK", "Mk": "MRK",
        "Luke": "LUK", "Lk": "LUK",
        "John": "JHN", "Jn": "JHN",
        "Acts": "ACT",
        "Romans": "ROM", "Rom": "ROM",
        "1 Corinthians": "1CO", "1 Cor": "1CO", "1Cor": "1CO",
        "2 Corinthians": "2CO", "2 Cor": "2CO", "2Cor": "2CO",
        "Galatians": "GAL", "Gal": "GAL",
        "Ephesians": "EPH", "Eph": "EPH",
        "Philippians": "PHP", "Phil": "PHP",
        "Colossians": "COL", "Col": "COL",
        "1 Thessalonians": "1TH", "1 Thess": "1TH", "1Thess": "1TH",
        "2 Thessalonians": "2TH", "2 Thess": "2TH", "2Thess": "2TH",
        "1 Timothy": "1TI", "1 Tim": "1TI", "1Tim": "1TI",
        "2 Timothy": "2TI", "2 Tim": "2TI", "2Tim": "2TI",
        "Titus": "TIT", "Tit": "TIT",
        "Philemon": "PHM", "Phlm": "PHM", "Phm": "PHM",
        "Hebrews": "HEB", "Heb": "HEB",
        "James": "JAS", "Jas": "JAS",
        "1 Peter": "1PE", "1 Pet": "1PE", "1Pt": "1PE",
        "2 Peter": "2PE", "2 Pet": "2PE", "2Pt": "2PE",
        "1 John": "1JN", "1 Jn": "1JN",
        "2 John": "2JN", "2 Jn": "2JN",
        "3 John": "3JN", "3 Jn": "3JN",
        "Jude": "JUD",
        "Revelation": "REV", "Rev": "REV", "The Revelation": "REV"
    }

    def __init__(self):
        self.api_key = os.getenv("BIBLE_API_KEY")
        if not self.api_key:
            logger.error("BIBLE_API_KEY not found in environment variables.")
            # Optionally raise an error or handle appropriately
            # raise ValueError("BIBLE_API_KEY is required.")

    def _convert_human_reference_to_api_format(self, human_reference: str) -> Optional[str]:
        """Converts a human-readable scripture reference to API.Bible format.
        Example: "Psalm 23:1" -> "PSA.23.1"
                 "1 John 3:16-18" -> "1JN.3.16-18"
        """
        # Regex to capture book, chapter, first verse, and optional end verse
        # Supports book names with or without leading numbers, and spaces.
        # Supports chapter:verse or chapter.verse and verse-verse_end or verse–verse_end
        pattern = r"^(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)*)\s*(\d+)[:\.](\d+)(?:[-–](\d+))?$"
        match = re.match(pattern, human_reference.strip())

        if not match:
            logger.warning(f"Could not parse human reference: '{human_reference}'")
            return None

        book_name_human, chapter, start_verse, end_verse = match.groups()
        book_name_human = book_name_human.strip()

        api_book_code = self.BOOK_TO_API_CODE_MAP.get(book_name_human)
        
        # Try title case if not found (e.g. psalm -> Psalm)
        if not api_book_code and book_name_human.lower() != book_name_human:
             api_book_code = self.BOOK_TO_API_CODE_MAP.get(book_name_human.title())

        # Try common alternative: no space for books like "1John" -> "1 John"
        if not api_book_code and book_name_human[0].isdigit() and len(book_name_human) > 1 and book_name_human[1].isalpha():
            potential_book_name = book_name_human[0] + " " + book_name_human[1:]
            api_book_code = self.BOOK_TO_API_CODE_MAP.get(potential_book_name)
            if not api_book_code:
                api_book_code = self.BOOK_TO_API_CODE_MAP.get(potential_book_name.title())

        if not api_book_code:
            logger.warning(f"API book code not found for '{book_name_human}' in reference '{human_reference}'")
            return None

        if end_verse:
            return f"{api_book_code}.{chapter}.{start_verse}-{end_verse}" # API handles ranges like PSA.23.1-3
        else:
            return f"{api_book_code}.{chapter}.{start_verse}"

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
#             print("John 3:16-17 (BSB):", text)
#         else:
#             print("Failed to fetch John 3:16-17")
#
#         text_psalm = service.get_scripture_text("PSA.23.1-3")
#         if text_psalm:
#             print("\nPsalm 23:1-3 (BSB):", text_psalm)
#         else:
#             print("Failed to fetch Psalm 23:1-3")
#     else:
#         print("BibleService could not be initialized due to missing API key.")
