 
import logging

from sqlalchemy import func

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
            verdict=analysis_data.get("verdict"),
            formation_risk=analysis_data.get("formation_risk"),
            narrative_voice=analysis_data.get("narrative_voice"),
            lament_filter_applied=analysis_data.get("lament_filter_applied"),
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
            
            # Extract themes with scripture mappings
            themes_positive = router_payload.get("themes_positive") or []
            themes_negative = router_payload.get("themes_negative") or []
            
            # Build biblical themes from both positive and negative
            biblical_themes = []
            for theme in themes_positive:
                if isinstance(theme, dict):
                    biblical_themes.append({
                        "theme": theme.get("theme", ""),
                        "points": theme.get("points", 0),
                        "scripture": theme.get("scripture", "")
                    })
            
            theme_names = [t.get("theme") for t in biblical_themes if t.get("theme")]
            
            # Build enriched scripture references with theme context
            supporting_scripture = []
            
            # Add scriptures from positive themes
            for theme in themes_positive:
                if isinstance(theme, dict) and theme.get("scripture"):
                    supporting_scripture.append({
                        "reference": theme.get("scripture"),
                        "theme": theme.get("theme"),
                        "type": "positive",
                        "relevance": f"Supports the positive theme of {theme.get('theme', 'biblical values')}"
                    })
            
            # Add scriptures from negative themes (concerns)
            for theme in themes_negative:
                if isinstance(theme, dict) and theme.get("scripture"):
                    supporting_scripture.append({
                        "reference": theme.get("scripture"),
                        "theme": theme.get("theme"),
                        "type": "concern",
                        "relevance": f"Addresses the concern of {theme.get('theme', 'spiritual formation')}"
                    })
            
            # Add any standalone scripture references not already included
            scripture_refs = router_payload.get("scripture_references") or []
            existing_refs = {s["reference"] for s in supporting_scripture if isinstance(s, dict)}
            for ref in scripture_refs:
                if ref not in existing_refs:
                    supporting_scripture.append(ref)
            
            return {
                "score": router_payload.get("score", 50),
                "concern_level": self._map_concern_level(router_payload.get("concern_level", "Unknown")),
                "themes": theme_names,
                "status": "completed",
                "explanation": router_payload.get("analysis", "Analysis completed"),
                "detailed_concerns": detailed_concerns,
                "positive_themes": [{"theme": t.get("theme"), "description": f"+{t.get('points', 0)} points"} for t in themes_positive if isinstance(t, dict)],
                "biblical_themes": biblical_themes,
                "supporting_scripture": supporting_scripture,
                "verdict": router_payload.get("verdict", "context_required"),
                "formation_risk": router_payload.get("formation_risk", "low"),
                "narrative_voice": router_payload.get("narrative_voice", "artist"),
                "lament_filter_applied": router_payload.get("lament_filter_applied", False),
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
        
        # Map score to verdict
        score = analysis_result.scoring_results["final_score"]
        if score >= 85:
            verdict = "freely_listen"
            formation_risk = "very_low"
        elif score >= 60:
            verdict = "context_required"
            formation_risk = "low"
        elif score >= 40:
            verdict = "caution_limit"
            formation_risk = "high"
        else:
            verdict = "avoid_formation"
            formation_risk = "high"
        
        return {
            "score": score,
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
            "verdict": verdict,
            "formation_risk": formation_risk,
            "narrative_voice": "artist",  # Default for simplified analysis
            "lament_filter_applied": False,  # Not supported in simplified path
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
            "verdict": "avoid_formation",
            "formation_risk": "critical",
            "narrative_voice": "artist",
            "lament_filter_applied": False,
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
            "verdict": "freely_listen",
            "formation_risk": "very_low",
            "narrative_voice": "artist",
            "lament_filter_applied": False,
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

    def auto_analyze_user_after_sync(self, user_id):
        """
        Automatically analyze all unanalyzed songs for a user after sync.
        Prioritizes playlists by track count (larger playlists first).
        Returns status and count of songs queued for analysis.
        """
        try:
            from ..models import Playlist, PlaylistSong
            
            self.logger.info(f"Starting auto-analysis for user {user_id}")
            
            # Get user's playlists ordered by track count (largest first) and updated_at
            playlists = Playlist.query.filter_by(owner_id=user_id).order_by(
                db.desc(Playlist.track_count),
                db.desc(Playlist.updated_at)
            ).all()
            
            if not playlists:
                self.logger.info(f"No playlists found for user {user_id}")
                return {"success": True, "message": "No playlists to analyze", "songs_queued": 0}
            
            # Get all unanalyzed songs from these playlists
            unanalyzed_songs = []
            for playlist in playlists:
                playlist_songs = db.session.query(Song).join(
                    PlaylistSong
                ).filter(
                    PlaylistSong.playlist_id == playlist.id
                ).outerjoin(
                    AnalysisResult, Song.id == AnalysisResult.song_id
                ).filter(
                    db.or_(
                        AnalysisResult.id.is_(None),
                        AnalysisResult.status != 'completed'
                    )
                ).all()
                
                unanalyzed_songs.extend(playlist_songs)
            
            # Remove duplicates (songs in multiple playlists)
            unique_song_ids = list(set([song.id for song in unanalyzed_songs]))
            
            self.logger.info(f"Found {len(unique_song_ids)} unanalyzed songs for user {user_id}")
            
            if not unique_song_ids:
                return {"success": True, "message": "All songs already analyzed", "songs_queued": 0}
            
            # Analyze songs in batches to avoid overwhelming the system
            # For now, we'll analyze them synchronously in chunks
            # In production, you might want to use a job queue
            batch_size = 10
            analyzed_count = 0
            failed_count = 0
            
            for i in range(0, len(unique_song_ids), batch_size):
                batch = unique_song_ids[i:i+batch_size]
                self.logger.info(f"Analyzing batch {i//batch_size + 1}: songs {i+1}-{min(i+batch_size, len(unique_song_ids))}")
                
                for song_id in batch:
                    try:
                        self.analyze_song(song_id, user_id=user_id)
                        analyzed_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to analyze song {song_id}: {e}")
                        failed_count += 1
            
            self.logger.info(f"Auto-analysis complete: {analyzed_count} analyzed, {failed_count} failed")
            
            return {
                "success": True,
                "message": f"Analyzed {analyzed_count} songs",
                "songs_analyzed": analyzed_count,
                "songs_failed": failed_count,
                "total_songs": len(unique_song_ids)
            }
            
        except Exception as e:
            self.logger.error(f"Auto-analysis failed for user {user_id}: {e}")
            return {"success": False, "error": str(e), "songs_queued": 0}

    def get_analysis_progress(self, user_id):
        """
        Get the current analysis progress for a user.
        Returns total songs, analyzed songs, and percentage complete.
        """
        try:
            from ..models import Playlist, PlaylistSong
            
            # Get total songs for user
            total_songs = db.session.query(func.count(Song.id.distinct())).join(
                PlaylistSong
            ).join(
                Playlist
            ).filter(
                Playlist.owner_id == user_id
            ).scalar() or 0
            
            # Get analyzed songs (completed analysis)
            analyzed_songs = db.session.query(func.count(AnalysisResult.id.distinct())).join(
                AnalysisResult.song_rel
            ).join(
                Song.playlist_associations
            ).join(
                PlaylistSong.playlist
            ).filter(
                Playlist.owner_id == user_id,
                AnalysisResult.status == 'completed'
            ).scalar() or 0
            
            # Get failed songs
            failed_songs = db.session.query(func.count(AnalysisResult.id.distinct())).join(
                AnalysisResult.song_rel
            ).join(
                Song.playlist_associations
            ).join(
                PlaylistSong.playlist
            ).filter(
                Playlist.owner_id == user_id,
                AnalysisResult.error.is_not(None)
            ).scalar() or 0
            
            percentage = round((analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1)
            remaining = total_songs - analyzed_songs - failed_songs
            
            return {
                "success": True,
                "total_songs": total_songs,
                "analyzed_songs": analyzed_songs,
                "failed_songs": failed_songs,
                "remaining_songs": remaining,
                "percentage": percentage,
                "is_complete": remaining == 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get analysis progress for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_unanalyzed_songs_count(self, user_id):
        """
        Get count of songs that haven't been analyzed yet for a user.
        """
        try:
            from ..models import Playlist, PlaylistSong
            
            # Get all songs for user
            total_songs = db.session.query(func.count(Song.id.distinct())).join(
                PlaylistSong
            ).join(
                Playlist
            ).filter(
                Playlist.owner_id == user_id
            ).scalar() or 0
            
            # Get analyzed songs
            analyzed_songs = db.session.query(func.count(AnalysisResult.id.distinct())).join(
                AnalysisResult.song_rel
            ).join(
                Song.playlist_associations
            ).join(
                PlaylistSong.playlist
            ).filter(
                Playlist.owner_id == user_id,
                AnalysisResult.status == 'completed'
            ).scalar() or 0
            
            return max(0, total_songs - analyzed_songs)
            
        except Exception as e:
            self.logger.error(f"Failed to get unanalyzed songs count for user {user_id}: {e}")
            return 0

    def detect_playlist_changes(self, user_id):
        """
        Detect changes in user's playlists compared to Spotify.
        Returns dict with changed playlist info.
        """
        try:
            from ..models import Playlist
            from ..services.spotify_service import SpotifyService
            
            spotify_service = SpotifyService()
            
            # Get current playlists from database
            db_playlists = Playlist.query.filter_by(owner_id=user_id).all()
            db_playlist_map = {p.spotify_id: p for p in db_playlists}
            
            # Get playlists from Spotify
            spotify_playlists = spotify_service.get_user_playlists(user_id)
            
            changed_playlists = []
            
            for sp_playlist in spotify_playlists:
                spotify_id = sp_playlist['id']
                spotify_track_count = sp_playlist['tracks']['total']
                
                if spotify_id in db_playlist_map:
                    db_playlist = db_playlist_map[spotify_id]
                    # Check if track count changed
                    if db_playlist.track_count != spotify_track_count:
                        changed_playlists.append({
                            'id': db_playlist.id,
                            'spotify_id': spotify_id,
                            'name': sp_playlist['name'],
                            'old_count': db_playlist.track_count,
                            'new_count': spotify_track_count
                        })
                else:
                    # New playlist
                    changed_playlists.append({
                        'spotify_id': spotify_id,
                        'name': sp_playlist['name'],
                        'new_count': spotify_track_count,
                        'is_new': True
                    })
            
            return {
                "success": True,
                "changed_playlists": changed_playlists,
                "total_changed": len(changed_playlists)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to detect playlist changes for user {user_id}: {e}")
            return {"success": False, "error": str(e), "changed_playlists": [], "total_changed": 0}

    def analyze_changed_playlists(self, changed_playlists):
        """
        Analyze only songs in changed playlists.
        Returns count of songs analyzed.
        """
        try:
            from ..models import PlaylistSong
            
            analyzed_count = 0
            
            for playlist_info in changed_playlists:
                playlist_id = playlist_info.get('id')
                if not playlist_id:
                    continue
                
                # Get unanalyzed songs from this playlist
                unanalyzed_songs = db.session.query(Song).join(
                    PlaylistSong
                ).outerjoin(
                    AnalysisResult, Song.id == AnalysisResult.song_id
                ).filter(
                    PlaylistSong.playlist_id == playlist_id,
                    db.or_(
                        AnalysisResult.id.is_(None),
                        AnalysisResult.status != 'completed'
                    )
                ).all()
                
                # Analyze each song
                for song in unanalyzed_songs:
                    try:
                        self.analyze_song(song.id)
                        analyzed_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to analyze song {song.id}: {e}")
            
            return {
                "success": True,
                "analyzed_songs": analyzed_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze changed playlists: {e}")
            return {"success": False, "error": str(e), "analyzed_songs": 0}


# Background job function for RQ workers
def analyze_playlist_async(playlist_id: int, user_id: int):
    """
    Background job to analyze all unanalyzed songs in a playlist.
    
    This function runs in an RQ worker process and automatically tracks
    progress via RQ's built-in job metadata.
    
    Args:
        playlist_id: ID of the playlist to analyze
        user_id: ID of the user who owns the playlist
        
    Returns:
        dict: Results summary with counts of analyzed/failed songs
    """
    from rq import get_current_job
    from ..models import Playlist, PlaylistSong, Song, AnalysisResult
    from .. import create_app
    
    # Get current RQ job for progress tracking
    job = get_current_job()
    
    # Create app context for database access in worker
    # RQ workers run in separate processes, so we need to create our own app instance
    app = create_app()
    with app.app_context():
        logger = logging.getLogger(__name__)
        logger.info(f"🚀 Background job started for playlist {playlist_id}")
        
        try:
            # Verify playlist exists and belongs to user
            playlist = Playlist.query.get(playlist_id)
            if not playlist:
                raise ValueError(f"Playlist {playlist_id} not found")
            
            if playlist.owner_id != user_id:
                raise ValueError(f"Playlist {playlist_id} does not belong to user {user_id}")
            
            # Get all unanalyzed songs in this playlist
            unanalyzed_songs = db.session.query(Song).join(
                PlaylistSong
            ).outerjoin(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                PlaylistSong.playlist_id == playlist_id,
                db.or_(
                    AnalysisResult.id.is_(None),
                    AnalysisResult.status != 'completed'
                )
            ).all()
            
            total = len(unanalyzed_songs)
            logger.info(f"📊 Found {total} unanalyzed songs in playlist {playlist_id}")
            
            if total == 0:
                return {
                    'playlist_id': playlist_id,
                    'playlist_name': playlist.name,
                    'total': 0,
                    'analyzed': 0,
                    'failed': 0,
                    'message': 'All songs already analyzed'
                }
            
            # Initialize analysis service
            service = UnifiedAnalysisService()
            results = {
                'playlist_id': playlist_id,
                'playlist_name': playlist.name,
                'total': total,
                'analyzed': 0,
                'failed': 0,
                'failed_songs': []
            }
            
            # Analyze each song with progress tracking
            for i, song in enumerate(unanalyzed_songs, 1):
                try:
                    # Update job metadata for progress tracking
                    if job:
                        job.meta['progress'] = {
                            'current': i,
                            'total': total,
                            'percentage': round((i / total) * 100, 1),
                            'current_song': f"{song.artist} - {song.title}"
                        }
                        job.save_meta()
                    
                    # Analyze the song
                    service.analyze_song(song.id, user_id)
                    results['analyzed'] += 1
                    
                    logger.info(f"✅ [{i}/{total}] Analyzed: {song.artist} - {song.title}")
                    
                except Exception as e:
                    results['failed'] += 1
                    results['failed_songs'].append({
                        'id': song.id,
                        'title': song.title,
                        'artist': song.artist,
                        'error': str(e)
                    })
                    logger.error(f"❌ [{i}/{total}] Failed to analyze {song.id}: {e}")
            
            logger.info(
                f"🎉 Playlist {playlist_id} analysis complete: "
                f"{results['analyzed']} succeeded, {results['failed']} failed"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"💥 Fatal error analyzing playlist {playlist_id}: {e}")
            raise
