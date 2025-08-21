"""
API Routes Tests

TDD tests for API endpoints, authentication, data validation, and error handling.
These tests define the expected behavior for our API layer.
"""

import json
from unittest.mock import patch

import pytest


def mock_authenticated_request(client, authenticated_user, sample_user):
    """Helper function to mock authentication for API requests."""
    # Set up session
    auth_data = authenticated_user(client)

    # Mock Flask-Login current_user
    with patch("flask_login.current_user", sample_user):
        with patch("app.routes.api.current_user", sample_user):
            return auth_data


class TestHealthAPI:
    """Test health check endpoints."""

    @pytest.mark.api
    def test_health_endpoint_success(self, client, db):
        """Test that health endpoint returns healthy status when database is accessible."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "timestamp" in data

    @pytest.mark.api
    def test_health_endpoint_database_failure(self, client, db):
        """Test that health endpoint returns unhealthy status when database fails."""
        with patch("app.routes.api.db.session.execute") as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")

            response = client.get("/api/health")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["status"] == "unhealthy"
            assert "error" in data


class TestPlaylistAPI:
    """Test playlist-related API endpoints."""

    @pytest.mark.api
    def test_get_playlists_requires_authentication(self, client):
        """Test that playlists endpoint requires user authentication."""
        response = client.get("/api/playlists")

        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    @pytest.mark.api
    def test_get_playlists_returns_user_data(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user
    ):
        """Test that playlists endpoint returns user's playlist data with analysis progress."""
        from app.models.models import PlaylistSong

        # Set up authenticated session and mock current_user
        auth_data = authenticated_user(client)

        # Add song to playlist
        playlist_song = PlaylistSong(
            playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0
        )
        auth_data["db"].session.add(playlist_song)
        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get("/api/playlists")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "playlists" in data
        assert len(data["playlists"]) >= 1

        playlist_data = data["playlists"][0]
        assert "id" in playlist_data
        assert "name" in playlist_data
        assert "song_count" in playlist_data
        assert "analyzed_count" in playlist_data
        assert "analysis_progress" in playlist_data

    @pytest.mark.api
    def test_freemium_masks_other_playlists(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user, monkeypatch
    ):
        """Free users see only one unlocked playlist; others flagged in API."""
        from app.models.models import PlaylistSong

        # Enable freemium via app config by monkeypatching
        monkeypatch.setenv("FREEMIUM_ENABLED", "1")

        auth_data = authenticated_user(client)
        # Add a song so the sample playlist is eligible
        ps = PlaylistSong(playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0)
        auth_data["db"].session.add(ps)
        auth_data["db"].session.commit()

        with (
            patch("flask_login.current_user", sample_user),
            patch("app.routes.api.current_user", sample_user),
        ):
            r = client.get("/api/playlists")
        assert r.status_code == 200
        data = r.get_json()
        assert "playlists" in data
        unlocked = [p for p in data["playlists"] if p.get("is_unlocked")]
        assert len(unlocked) >= 1

    @pytest.mark.api
    def test_get_playlist_songs_requires_ownership(
        self, client, authenticated_user, other_user_playlist, sample_user
    ):
        """Test that users can only access their own playlist songs."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/playlist/{other_user_playlist.id}/songs")

        assert response.status_code == 404  # Should not find playlist for this user

    @pytest.mark.api
    def test_get_playlist_songs_returns_song_data(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user
    ):
        """Test that playlist songs endpoint returns detailed song and analysis data."""
        from app.models.models import AnalysisResult, PlaylistSong

        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Add song to playlist
        playlist_song = PlaylistSong(
            playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0
        )
        auth_data["db"].session.add(playlist_song)

        # Add analysis result
        analysis = AnalysisResult(
            song_id=sample_song.id, status="completed", score=85, concern_level="low"
        )
        auth_data["db"].session.add(analysis)
        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/playlist/{sample_playlist.id}/songs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "playlist" in data
        assert "songs" in data
        assert len(data["songs"]) == 1

        song_data = data["songs"][0]
        assert song_data["name"] == sample_song.title
        assert song_data["artist"] == sample_song.artist
        assert song_data["analysis_status"] == "completed"
        assert song_data["analysis_score"] == 85


class TestSongAnalysisAPI:
    """Test song analysis API endpoints."""

    @pytest.mark.api
    def test_get_song_analysis_requires_ownership(
        self, client, authenticated_user, other_user_song, sample_user
    ):
        """Test that users can only access analysis for their own songs."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/song/{other_user_song.id}/analysis")

        assert response.status_code == 404  # Should not find song for this user

    @pytest.mark.api
    def test_get_song_analysis_returns_detailed_data(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user
    ):
        """Test that song analysis endpoint returns comprehensive song and analysis data."""
        from app.models.models import AnalysisResult, PlaylistSong

        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Associate song with user's playlist
        playlist_song = PlaylistSong(
            playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0
        )
        auth_data["db"].session.add(playlist_song)

        # Add detailed analysis
        analysis = AnalysisResult(
            song_id=sample_song.id,
            status="completed",
            score=92,
            concern_level="low",
            themes=["worship", "praise"],
            explanation="Strong Christian worship themes detected",
        )
        auth_data["db"].session.add(analysis)
        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/song/{sample_song.id}/analysis")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "song" in data
        assert "analysis" in data

        song_data = data["song"]
        assert song_data["name"] == sample_song.title
        assert song_data["artist"] == sample_song.artist

        analysis_data = data["analysis"]
        assert analysis_data["status"] == "completed"
        assert analysis_data["score"] == 92
        assert analysis_data["concern_level"] == "low"

    @pytest.mark.api
    def test_get_song_analysis_handles_no_analysis(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user
    ):
        """Test that song analysis endpoint handles songs without analysis results."""
        from app.models.models import PlaylistSong

        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Associate song with user's playlist but no analysis
        playlist_song = PlaylistSong(
            playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0
        )
        auth_data["db"].session.add(playlist_song)
        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/song/{sample_song.id}/analysis")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "song" in data
        assert data["analysis"] is None  # No analysis available


class TestProgressAPI:
    """Test analysis progress tracking endpoints."""

    @pytest.mark.api
    def test_get_analysis_progress_requires_ownership(
        self, client, authenticated_user, other_user_playlist, sample_user
    ):
        """Test that progress endpoint requires playlist ownership."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/playlists/{other_user_playlist.id}/analysis-status")

        assert response.status_code == 404

    @pytest.mark.api
    def test_get_analysis_progress_calculates_correctly(
        self, client, authenticated_user, sample_playlist, sample_user
    ):
        """Test that progress endpoint correctly calculates analysis progress."""
        from app.models.models import AnalysisResult, PlaylistSong, Song

        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Create multiple songs with different analysis states
        songs = []
        for i in range(5):
            song = Song(spotify_id=f"test_song_{i}", title=f"Test Song {i}", artist="Test Artist")
            auth_data["db"].session.add(song)
            auth_data["db"].session.flush()

            playlist_song = PlaylistSong(
                playlist_id=sample_playlist.id, song_id=song.id, track_position=i
            )
            auth_data["db"].session.add(playlist_song)
            songs.append(song)

        # Add analysis for 3 out of 5 songs
        for i in range(3):
            analysis = AnalysisResult(song_id=songs[i].id, status="completed", score=80 + i)
            auth_data["db"].session.add(analysis)

        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/playlists/{sample_playlist.id}/analysis-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total_count"] == 5
        assert data["detailed_status"]["completed"] == 3
        assert data["detailed_status"]["pending"] == 2
        assert data["progress"] == 60.0


class TestSearchAPI:
    """Test song search functionality."""

    @pytest.mark.api
    def test_search_songs_requires_authentication(self, client):
        """Test that search endpoint requires authentication."""
        response = client.get("/api/search_songs?q=test")

        assert response.status_code in [302, 401, 403]

    @pytest.mark.api
    def test_search_songs_returns_matching_results(
        self, client, authenticated_user, sample_playlist, sample_song, sample_user
    ):
        """Test that search returns songs matching the query."""
        from app.models.models import PlaylistSong

        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Associate song with user's playlist
        playlist_song = PlaylistSong(
            playlist_id=sample_playlist.id, song_id=sample_song.id, track_position=0
        )
        auth_data["db"].session.add(playlist_song)
        auth_data["db"].session.commit()

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get(f"/api/search_songs?q={sample_song.title}")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "songs" in data
        assert len(data["songs"]) >= 1

    @pytest.mark.api
    def test_search_songs_handles_empty_query(self, client, authenticated_user, sample_user):
        """Test that search handles empty or missing query parameters."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get("/api/search_songs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["songs"] == []


class TestAPIErrorHandling:
    """Test API error handling and response formats."""

    @pytest.mark.api
    def test_api_404_error_format(self, client, authenticated_user, sample_user):
        """Test that API 404 errors return proper JSON format for authenticated endpoints."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Test a non-existent playlist ID within the API blueprint
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get("/api/playlist/999999/songs")  # Non-existent playlist ID

        # Should return 404 with JSON content type for API endpoints
        assert response.status_code == 404
        assert response.content_type == "application/json"
        data = json.loads(response.data)
        assert "error" in data or "message" in data  # Flask-SQLAlchemy might use 'message'

    @pytest.mark.api
    def test_api_validates_integer_parameters(self, client, authenticated_user):
        """Test that API validates integer parameters properly."""
        response = client.get("/api/playlist/invalid_id/songs")

        # Should handle invalid integer gracefully
        assert response.status_code in [400, 404]


class TestSyncStatusAPI:
    """Test synchronization status endpoints."""

    @pytest.mark.api
    def test_sync_status_requires_authentication(self, client):
        """Test that sync status endpoint requires authentication."""
        response = client.get("/api/sync-status")

        assert response.status_code in [302, 401, 403]

    @pytest.mark.api
    def test_sync_status_returns_sync_information(self, client, authenticated_user, sample_user):
        """Test that sync status returns relevant synchronization data."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get("/api/sync-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should contain sync-related information
        assert isinstance(data, dict)


class TestUserStatsAPI:
    """Test user statistics endpoints."""

    @pytest.mark.api
    def test_user_stats_requires_authentication(self, client):
        """Test that user stats endpoint requires authentication."""
        response = client.get("/api/stats")

        assert response.status_code in [302, 401, 403]

    @pytest.mark.api
    def test_user_stats_returns_aggregated_data(self, client, authenticated_user, sample_user):
        """Test that user stats returns aggregated user data."""
        # Set up authenticated session
        auth_data = authenticated_user(client)

        # Mock Flask-Login current_user for the API request
        with patch("flask_login.current_user", sample_user):
            with patch("app.routes.api.current_user", sample_user):
                response = client.get("/api/stats")

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should contain statistical information
        assert isinstance(data, dict)
