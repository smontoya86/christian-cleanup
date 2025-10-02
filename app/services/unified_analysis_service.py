 
import logging

from .. import db
from ..models import AnalysisResult, Blacklist, Song, Whitelist
from .analyzer_cache import get_shared_analyzer, is_analyzer_ready
from .simplified_christian_analysis_service import SimplifiedChristianAnalysisService

try:
    from ..utils.lyrics import LyricsFetcher
except ImportError:
    class LyricsFetcher:
        def fetch_lyrics(self, artist, title):
            return ""

class UnifiedAnalysisService:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.analysis_service = SimplifiedChristianAnalysisService()
        self.lyrics_fetcher = LyricsFetcher()

    def analyze_song(self, song_id, user_id=None):
        self.logger.info(f"Analyzing song with ID: {song_id}")
        song = db.session.get(Song, song_id)
        if not song:
            raise ValueError(f"Song with ID {song_id} not found")

        analysis_data = self.analyze_song_complete(song, force=True, user_id=user_id)

        analysis = AnalysisResult.query.filter_by(song_id=song_id).first()
        if not analysis:
            analysis = AnalysisResult(song_id=song_id)
            db.session.add(analysis)

        analysis.mark_completed(
            score=analysis_data.get("score", 85),
            concern_level=analysis_data.get("concern_level", "low"),
            themes=analysis_data.get("themes", []),
            concerns=analysis_data.get("detailed_concerns", []),
            explanation=analysis_data.get("explanation", "Analysis completed"),
            purity_flags_details=analysis_data.get("detailed_concerns", []),
            positive_themes_identified=analysis_data.get("positive_themes", []),
            biblical_themes=analysis_data.get("biblical_themes", []),
            supporting_scripture=analysis_data.get("supporting_scripture", []),
        )
        db.session.commit()

        return analysis

    def analyze_song_complete(self, song, force=False, user_id=None):
        self.logger.info(f"Starting complete analysis for song: {song.title}")
        if not force:
            self.logger.info("Checking for existing analysis...")
            existing = (
                AnalysisResult.query.filter_by(song_id=song.id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )
            if existing:
                self.logger.info("Found existing analysis.")
                return {
                    "score": existing.score,
                    "concern_level": existing.concern_level,
                    "themes": existing.themes or [],
                    "explanation": existing.explanation or "Cached result reused",
                    "detailed_concerns": existing.purity_flags_details or [],
                    "positive_themes": existing.positive_themes_identified or [],
                    "biblical_themes": existing.biblical_themes or [],
                    "supporting_scripture": existing.supporting_scripture or [],
                }
        if user_id:
            self.logger.info("Checking blacklist...")
            if self._is_blacklisted(song, user_id):
                self.logger.info("Song is blacklisted.")
                return self._create_blacklisted_result(song, user_id)
            self.logger.info("Checking whitelist...")
            if self._is_whitelisted(song, user_id):
                self.logger.info("Song is whitelisted.")
                return self._create_whitelisted_result(song, user_id)

        self.logger.info("Fetching lyrics...")
        lyrics = song.lyrics
        if hasattr(lyrics, "_mock_name"):
            lyrics = ""
        elif lyrics is None:
            lyrics = ""
        else:
            lyrics = str(lyrics)

        if not lyrics or len(lyrics.strip()) <= 10:
            self.logger.info("Lyrics not found or too short, fetching...")
            try:
                fetched_lyrics = self.lyrics_fetcher.fetch_lyrics(
                    song.title or song.name, song.artist
                )
                if fetched_lyrics and len(fetched_lyrics.strip()) > 10:
                    self.logger.info("Fetched lyrics successfully.")
                    lyrics = fetched_lyrics
                    song.lyrics = lyrics
                    db.session.commit()
            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch lyrics for '{song.title}' by {song.artist} (providers fallback): {e}"
                )

        title = song.title or song.name
        artist = song.artist

        self.logger.info("Checking for router analysis...")
        use_router = False
        router_payload = None
        try:
            if is_analyzer_ready():
                use_router = True
            else:
                _ = get_shared_analyzer()
                use_router = True
            if use_router:
                self.logger.info("Using router for analysis.")
                router = get_shared_analyzer()
                router_payload = router.analyze_song(title, artist, lyrics)
        except Exception as e:
            self.logger.error(f"Router analysis failed: {e}")
            use_router = False
            router_payload = None

        if use_router and isinstance(router_payload, dict):
            self.logger.info("Router analysis successful.")
            detailed_concerns = router_payload.get("concerns") or []
            biblical_themes = router_payload.get("biblical_themes") or []
            theme_names = [
                (t.get("theme") if isinstance(t, dict) else str(t)) for t in biblical_themes
            ]
            return {
                "score": router_payload.get("score", 50),
                "concern_level": self._map_concern_level(router_payload.get("concern_level", "Unknown")),
                "themes": [t for t in theme_names if t],
                "status": "completed",
                "explanation": "Router analysis completed",
                "detailed_concerns": detailed_concerns,
                "positive_themes": [],
                "biblical_themes": biblical_themes,
                "supporting_scripture": router_payload.get("supporting_scripture") or [],
            }

        self.logger.info("Performing simplified analysis...")
        analysis_result = self.analysis_service.analyze_song(title, artist, lyrics)

        biblical_themes = []
        positive_themes = []
        detailed_concerns = []
        supporting_scripture = []

        if analysis_result.biblical_analysis and "themes" in analysis_result.biblical_analysis:
            biblical_themes = [
                {
                    "theme": theme.get("theme", theme) if isinstance(theme, dict) else theme,
                    "relevance": "Identified through AI analysis",
                }
                for theme in analysis_result.biblical_analysis["themes"]
            ]

        if analysis_result.model_analysis and "sentiment" in analysis_result.model_analysis:
            sentiment = analysis_result.model_analysis["sentiment"]
            if sentiment.get("label") == "POSITIVE":
                positive_themes = [
                    {
                        "theme": "Positive Sentiment",
                        "description": f"Song demonstrates positive emotional content (confidence: {sentiment.get('score', 0):.2f})",
                    }
                ]

        if (
            analysis_result.content_analysis
            and "concern_flags" in analysis_result.content_analysis
        ):
            detailed_concerns = analysis_result.content_analysis["concern_flags"]

        if (
            analysis_result.biblical_analysis
            and "supporting_scripture" in analysis_result.biblical_analysis
        ):
            scripture_refs = analysis_result.biblical_analysis["supporting_scripture"]
            supporting_scripture = []
            for ref in scripture_refs:
                if isinstance(ref, dict):
                    supporting_scripture.append(ref)
                elif isinstance(ref, str):
                    supporting_scripture.append(
                        {"reference": ref, "relevance": "Related to identified themes"}
                    )
                else:
                    supporting_scripture.append(
                        {"reference": str(ref), "relevance": "Related to identified themes"}
                    )

        self.logger.info("Simplified analysis successful.")
        return {
            "score": analysis_result.scoring_results["final_score"],
            "concern_level": self._map_concern_level(
                analysis_result.scoring_results.get("quality_level", "Unknown")
            ),
            "themes": self._extract_theme_names(
                analysis_result.biblical_analysis.get("themes", [])
            ),
            "status": "completed",
            "explanation": analysis_result.scoring_results["explanation"],
            "detailed_concerns": detailed_concerns,
            "positive_themes": positive_themes,
            "biblical_themes": biblical_themes,
            "supporting_scripture": supporting_scripture,
        }

    def _is_blacklisted(self, song, user_id):
        song_blacklisted = (
            Blacklist.query.filter_by(
                user_id=user_id, spotify_id=song.spotify_id, item_type="song"
            ).first()
            is not None
        )

        if song_blacklisted:
            return True

        return False

    def _is_whitelisted(self, song, user_id):
        song_whitelisted = (
            Whitelist.query.filter_by(
                user_id=user_id, spotify_id=song.spotify_id, item_type="song"
            ).first()
            is not None
        )

        if song_whitelisted:
            return True

        return False

    def _create_blacklisted_result(self, song, user_id):
        return {
            "score": 0,
            "concern_level": "high",
            "themes": ["Blacklisted"],
            "status": "completed",
            "explanation": f"Song '{song.title}' is blacklisted by the user.",
            "detailed_concerns": [{"concern": "Blacklisted", "details": "This song is on your blacklist."}],
            "positive_themes": [],
            "biblical_themes": [],
            "supporting_scripture": [],
        }

    def _create_whitelisted_result(self, song, user_id):
        return {
            "score": 100,
            "concern_level": "none",
            "themes": ["Whitelisted"],
            "status": "completed",
            "explanation": f"Song '{song.title}' is whitelisted by the user.",
            "detailed_concerns": [],
            "positive_themes": [{"theme": "Whitelisted", "description": "This song is on your whitelist."}],
            "biblical_themes": [],
            "supporting_scripture": [],
        }

    def _map_concern_level(self, level_str):
        level_str = str(level_str).lower()
        if "high" in level_str:
            return "high"
        if "medium" in level_str:
            return "medium"
        if "low" in level_str:
            return "low"
        return "none"

    def _extract_theme_names(self, themes):
        if not themes:
            return []
        return [
            (theme.get("theme") if isinstance(theme, dict) else str(theme))
            for theme in themes
        ]


