import pytest

from app.models import User
from app.services.spotify_service import SpotifyService


class TestSpotifyService:
    """Test cases for the SpotifyService."""

    def test_initialize_spotify_service(self):
        """Test that SpotifyService initializes correctly."""
        from datetime import datetime, timedelta, timezone

        sample_user = User(
            id=1,
            spotify_id="test_user_123",
            display_name="Test User",
            email="test@example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        service = SpotifyService(sample_user)
        assert service is not None
        assert service.user == sample_user

    def test_initialize_without_token_raises_error(self):
        """Test that SpotifyService raises error without access token."""
        user = User(spotify_id="test", display_name="Test")

        with pytest.raises(ValueError) as exc_info:
            SpotifyService(user)

        assert "User has no access token" in str(exc_info.value)
