from unittest.mock import Mock, patch

import pytest

from app.services.unified_analysis_service import UnifiedAnalysisService


class TestUnifiedAnalysisService:
    """Test the unified analysis service."""

    @pytest.fixture
    def analysis_service(self):
        """Create a UnifiedAnalysisService instance for testing."""
        return UnifiedAnalysisService()

    @pytest.fixture
    def sample_song(self, db):
        """Create a sample song for testing."""
        from app.models.models import Song

        song = Song(
            spotify_id="test_song_123", title="Test Song", artist="Test Artist", album="Test Album"
        )
        db.session.add(song)
        db.session.commit()
        return song

    def test_analyze_song_complete(self, analysis_service, sample_song):
        """Test the analyze_song_complete method."""
        # Mock the simplified analysis service
        with patch.object(analysis_service.analysis_service, "analyze_song") as mock_analyze:
            # Mock return value to simulate successful analysis
            mock_result = Mock()
            mock_result.scoring_results = {
                "final_score": 85,
                "quality_level": "Low",
                "explanation": "Test analysis",
            }
            mock_result.biblical_analysis = {"themes": [], "supporting_scripture": []}
            mock_result.content_analysis = {"concern_flags": []}
            mock_result.model_analysis = {"sentiment": {"label": "POSITIVE", "score": 0.8}}
            mock_analyze.return_value = mock_result

            result = analysis_service.analyze_song_complete(sample_song, force=True)

            # Verify the result format
            assert isinstance(result, dict)
            assert "score" in result
            assert "concern_level" in result
            assert "status" in result

    def test_analyze_song_complete_failure(self, analysis_service, sample_song):
        """Test analyze_song_complete when analysis fails."""
        # Mock the simplified analysis service to raise an exception
        with patch.object(
            analysis_service.analysis_service,
            "analyze_song",
            side_effect=Exception("Analysis failed"),
        ):
            result = analysis_service.analyze_song_complete(sample_song, force=True)

            # Verify failure is handled gracefully
            assert result["status"] == "failed"
            assert result["score"] == 0

    @pytest.mark.skip(
        reason="Test expects old direct call behavior, current system uses queue-based approach"
    )
    def test_auto_analyze_after_playlist_sync(self, analysis_service, sample_user, db):
        """Test that analysis is automatically triggered after playlist sync completion."""
        from app.models.models import Playlist, PlaylistSong, Song

        # Create test playlist and songs
        playlist = Playlist(
            owner_id=sample_user.id, spotify_id="test_playlist_123", name="Test Playlist"
        )
        db.session.add(playlist)

        song1 = Song(spotify_id="song1", title="Song 1", artist="Artist 1", lyrics="Test lyrics 1")
        song2 = Song(spotify_id="song2", title="Song 2", artist="Artist 2", lyrics="Test lyrics 2")
        db.session.add_all([song1, song2])
        db.session.commit()

        # Add songs to playlist
        ps1 = PlaylistSong(playlist_id=playlist.id, song_id=song1.id, track_position=0)
        ps2 = PlaylistSong(playlist_id=playlist.id, song_id=song2.id, track_position=1)
        db.session.add_all([ps1, ps2])
        db.session.commit()

        # Mock SimplifiedChristianAnalysisService.analyze_song to track calls
        with patch.object(analysis_service.analysis_service, "analyze_song") as mock_analyze:
            # Mock return value to simulate successful analysis
            mock_result = Mock()
            mock_result.scoring_results = {
                "final_score": 85,
                "quality_level": "Low",
                "explanation": "Test analysis",
            }
            mock_result.biblical_analysis = {"themes": [], "supporting_scripture": []}
            mock_result.content_analysis = {"concern_flags": []}
            mock_result.model_analysis = {"sentiment": {"label": "POSITIVE", "score": 0.8}}
            mock_analyze.return_value = mock_result

            # Call the method that should trigger auto-analysis
            result = analysis_service.auto_analyze_user_after_sync(sample_user.id)

            # Verify analysis was triggered for both songs
            assert result["success"] is True
            assert result["queued_count"] == 2
            assert mock_analyze.call_count == 2

    @pytest.mark.skip(
        reason="Test expects old direct call behavior, current system uses queue-based approach"
    )
    def test_auto_analyze_skips_already_analyzed(self, analysis_service, sample_user, db):
        """Test that auto-analysis skips songs that are already analyzed."""
        from datetime import datetime, timezone

        from app.models.models import AnalysisResult, Playlist, PlaylistSong, Song

        # Create test playlist and songs
        playlist = Playlist(
            owner_id=sample_user.id, spotify_id="test_playlist_123", name="Test Playlist"
        )
        db.session.add(playlist)

        song1 = Song(spotify_id="song1", title="Song 1", artist="Artist 1", lyrics="Test lyrics 1")
        song2 = Song(spotify_id="song2", title="Song 2", artist="Artist 2", lyrics="Test lyrics 2")
        db.session.add_all([song1, song2])
        db.session.commit()

        # Add songs to playlist
        ps1 = PlaylistSong(playlist_id=playlist.id, song_id=song1.id, track_position=0)
        ps2 = PlaylistSong(playlist_id=playlist.id, song_id=song2.id, track_position=1)
        db.session.add_all([ps1, ps2])

        # Add existing analysis for song1
        analysis1 = AnalysisResult(
            song_id=song1.id, status="completed", score=85, created_at=datetime.now(timezone.utc)
        )
        db.session.add(analysis1)
        db.session.commit()

        # Mock SimplifiedChristianAnalysisService.analyze_song to track calls
        with patch.object(analysis_service.analysis_service, "analyze_song") as mock_analyze:
            # Mock return value to simulate successful analysis
            mock_result = Mock()
            mock_result.scoring_results = {
                "final_score": 85,
                "quality_level": "Low",
                "explanation": "Test analysis",
            }
            mock_result.biblical_analysis = {"themes": [], "supporting_scripture": []}
            mock_result.content_analysis = {"concern_flags": []}
            mock_result.model_analysis = {"sentiment": {"label": "POSITIVE", "score": 0.8}}
            mock_analyze.return_value = mock_result

            # Call auto-analysis
            result = analysis_service.auto_analyze_user_after_sync(sample_user.id)

            # Verify only song2 was analyzed (song1 already has analysis)
            assert result["success"] is True
            assert result["queued_count"] == 1
            assert mock_analyze.call_count == 1

    def test_auto_analyze_handles_no_songs(self, analysis_service, sample_user):
        """Test auto-analysis when user has no songs."""
        # Call auto-analysis on user with no playlists/songs
        result = analysis_service.auto_analyze_user_after_sync(sample_user.id)

        # Should handle gracefully
        assert result["success"] is True
        assert result["queued_count"] == 0

    @pytest.mark.skip(
        reason="Test expects old direct call behavior, current system uses queue-based approach"
    )
    def test_analyze_changed_playlists_on_login(self, analysis_service, sample_user, db):
        """Test that playlist change detection triggers analysis of new/modified songs."""
        from datetime import datetime, timezone

        from app.models.models import AnalysisResult, Playlist, PlaylistSong, Song

        # Create existing playlist with old snapshot_id
        playlist = Playlist(
            owner_id=sample_user.id,
            spotify_id="test_playlist_123",
            name="Test Playlist",
            spotify_snapshot_id="old_snapshot_id",
        )
        db.session.add(playlist)

        # Create songs - one analyzed, one new
        song1 = Song(spotify_id="song1", title="Song 1", artist="Artist 1", lyrics="Test lyrics 1")
        song2 = Song(
            spotify_id="song2", title="Song 2", artist="Artist 2", lyrics="Test lyrics 2"
        )  # New song
        db.session.add_all([song1, song2])
        db.session.commit()

        # song1 has existing analysis
        analysis1 = AnalysisResult(
            song_id=song1.id, status="completed", score=85, created_at=datetime.now(timezone.utc)
        )
        db.session.add(analysis1)

        # Add songs to playlist
        ps1 = PlaylistSong(playlist_id=playlist.id, song_id=song1.id, track_position=0)
        ps2 = PlaylistSong(playlist_id=playlist.id, song_id=song2.id, track_position=1)
        db.session.add_all([ps1, ps2])
        db.session.commit()

        # Simulate playlist changes - new snapshot_id detected
        changed_playlists = [
            {
                "playlist_id": playlist.id,
                "old_snapshot_id": "old_snapshot_id",
                "new_snapshot_id": "new_snapshot_id",
                "new_songs": [song2.id],  # Only song2 is new
            }
        ]

        # Mock SimplifiedChristianAnalysisService.analyze_song to track calls
        with patch.object(analysis_service.analysis_service, "analyze_song") as mock_analyze:
            # Mock return value to simulate successful analysis
            mock_result = Mock()
            mock_result.scoring_results = {
                "final_score": 85,
                "quality_level": "Low",
                "explanation": "Test analysis",
            }
            mock_result.biblical_analysis = {"themes": [], "supporting_scripture": []}
            mock_result.content_analysis = {"concern_flags": []}
            mock_result.model_analysis = {"sentiment": {"label": "POSITIVE", "score": 0.8}}
            mock_analyze.return_value = mock_result

            # Call change detection analysis
            result = analysis_service.analyze_changed_playlists(changed_playlists)

            # Verify only new song was analyzed
            assert result["success"] is True
            assert result["analyzed_songs"] == 1
            assert mock_analyze.call_count == 1

    def test_detect_playlist_changes(self, analysis_service, sample_user, db):
        """Test detection of playlist changes based on snapshot_id."""
        from app.models.models import Playlist

        # Create playlists with different snapshot states
        playlist1 = Playlist(
            owner_id=sample_user.id,
            spotify_id="playlist_1",
            name="Unchanged Playlist",
            spotify_snapshot_id="snapshot_123",
        )

        playlist2 = Playlist(
            owner_id=sample_user.id,
            spotify_id="playlist_2",
            name="Changed Playlist",
            spotify_snapshot_id="old_snapshot",
        )

        db.session.add_all([playlist1, playlist2])
        db.session.commit()

        # Simulate Spotify data with new snapshots
        spotify_playlists = [
            {
                "id": "playlist_1",
                "snapshot_id": "snapshot_123",  # Same - no change
                "name": "Unchanged Playlist",
            },
            {
                "id": "playlist_2",
                "snapshot_id": "new_snapshot",  # Different - changed
                "name": "Changed Playlist",
            },
        ]

        # Mock Spotify service
        with patch("app.services.spotify_service.SpotifyService") as mock_spotify:
            mock_spotify.return_value.get_user_playlists.return_value = spotify_playlists

            result = analysis_service.detect_playlist_changes(sample_user.id)

            # Should detect only playlist2 as changed
            assert result["success"] is True
            assert len(result["changed_playlists"]) == 1
            assert result["changed_playlists"][0]["spotify_id"] == "playlist_2"
