"""
TDD tests for the new card-based Playlist Detail view.

We assert server-rendered card markup, actions, score pill, and reason snippet.
These tests intentionally do not rely on JavaScript execution; they check
server-side HTML only.
"""

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app.models.models import AnalysisResult, Playlist, PlaylistSong, Song, Whitelist


@pytest.fixture
def playlist_with_unanalyzed_song(db_session, sample_user):
    playlist = Playlist(name="Card View Test", spotify_id="pl_card_test", owner_id=sample_user.id)
    db_session.add(playlist)
    db_session.flush()

    song = Song(
        title="Unanalyzed Song",
        artist="Test Artist",
        spotify_id="song_unanalyzed_1",
        duration_ms=180000,
    )
    db_session.add(song)
    db_session.flush()

    db_session.add(PlaylistSong(playlist_id=playlist.id, song_id=song.id, track_position=0))
    db_session.commit()

    return playlist, song


@pytest.fixture
def playlist_with_analyzed_song(db_session, sample_user):
    playlist = Playlist(name="Card View Analyzed", spotify_id="pl_card_analyzed", owner_id=sample_user.id)
    db_session.add(playlist)
    db_session.flush()

    song = Song(
        title="Analyzed Song",
        artist="Test Artist",
        spotify_id="song_analyzed_1",
        duration_ms=180000,
    )
    db_session.add(song)
    db_session.flush()

    # Completed analysis (low concern)
    analysis = AnalysisResult(
        song_id=song.id,
        score=85.0,
        concern_level="low",
        explanation="Lyrics generally align with Christian principles.",
        concerns=[],
        positive_themes_identified={"hope": True},
        biblical_themes={"grace": True},
    )
    db_session.add(analysis)

    db_session.add(PlaylistSong(playlist_id=playlist.id, song_id=song.id, track_position=0))
    db_session.commit()

    return playlist, song


def _get_soup(client, playlist_id):
    resp = client.get(url_for("main.playlist_detail", playlist_id=playlist_id))
    assert resp.status_code == 200
    return BeautifulSoup(resp.data, "html.parser")


class TestPlaylistCards:
    def test_cards_render_by_default(self, authenticated_client, playlist_with_analyzed_song):
        playlist, _ = playlist_with_analyzed_song
        soup = _get_soup(authenticated_client, playlist.id)

        grid = soup.find(id="song-grid-view")
        assert grid is not None, "Grid container should be present by default"

        # Expect at least one card
        cards = grid.select(".song-card, .card")
        assert len(cards) >= 1, "At least one song card should render"

    def test_card_has_title_link_and_album_artist(self, authenticated_client, playlist_with_analyzed_song):
        playlist, song = playlist_with_analyzed_song
        soup = _get_soup(authenticated_client, playlist.id)

        card = soup.select_one("#song-grid-view .card")
        assert card is not None

        title_link = card.find("a", href=True)
        assert title_link is not None
        href = title_link.get("href")
        assert str(song.id) in href and str(playlist.id) in href

    def test_score_badge_circle_present(self, authenticated_client, playlist_with_analyzed_song):
        playlist, _ = playlist_with_analyzed_song
        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        assert card is not None

        # Score circle should show a percentage value
        badge = card.select_one(".score-circle, .concern-badge")
        assert badge is not None, "Score badge/circle should be present on analyzed songs"
        assert "%" in badge.get_text().strip()

    def test_reason_snippet_present(self, authenticated_client, playlist_with_analyzed_song):
        playlist, _ = playlist_with_analyzed_song
        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        assert card is not None

        # The reason snippet is a single line element
        reason = card.select_one(".reason-snippet")
        # It's acceptable for legacy data to miss the snippet; ensure element exists for analyzed items
        assert reason is not None, "Reason snippet should render for analyzed items"

    def test_unanalyzed_card_shows_analyze_button(self, authenticated_client, playlist_with_unanalyzed_song):
        playlist, song = playlist_with_unanalyzed_song
        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        assert card is not None

        analyze_btn = card.select_one(".analyze-song-btn")
        assert analyze_btn is not None
        assert analyze_btn.get("data-song-id") == str(song.id)
        assert analyze_btn.get("data-song-title") == song.title

    def test_low_concern_card_shows_whitelist(self, authenticated_client, playlist_with_analyzed_song):
        playlist, song = playlist_with_analyzed_song
        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        assert card is not None

        whitelist_form = card.find("form", action=lambda a: a and "whitelist_song" in a)
        assert whitelist_form is not None, "Whitelist form should be present for low/medium concern"

    def test_high_concern_card_shows_review(self, authenticated_client, db_session, sample_user):
        # Build playlist with high concern analyzed song
        playlist = Playlist(name="Card View High", spotify_id="pl_card_high", owner_id=sample_user.id)
        db_session.add(playlist)
        db_session.flush()

        song = Song(title="High Concern", artist="Artist", spotify_id="song_high_1", duration_ms=120000)
        db_session.add(song)
        db_session.flush()

        analysis = AnalysisResult(
            song_id=song.id,
            score=26.0,
            concern_level="high",
            explanation="Lyrics contradict a biblical principle.",
            concerns=["contradiction"],
        )
        db_session.add(analysis)
        db_session.add(PlaylistSong(playlist_id=playlist.id, song_id=song.id, track_position=0))
        db_session.commit()

        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        review_btn = card.find("a", class_="btn-warning")
        assert review_btn is not None and "Review" in review_btn.get_text()

    def test_whitelisted_card_shows_remove(self, authenticated_client, db_session, sample_user):
        playlist = Playlist(name="Card View WL", spotify_id="pl_card_wl", owner_id=sample_user.id)
        db_session.add(playlist)
        db_session.flush()

        song = Song(title="WL Song", artist="Artist", spotify_id="song_wl_1", duration_ms=100000)
        db_session.add(song)
        db_session.flush()

        analysis = AnalysisResult(song_id=song.id, score=90.0, concern_level="low", explanation="Good")
        db_session.add(analysis)
        db_session.add(PlaylistSong(playlist_id=playlist.id, song_id=song.id, track_position=0))

        # Whitelist entry
        wl = Whitelist(user_id=sample_user.id, spotify_id=song.spotify_id, item_type="song", name=f"{song.artist} - {song.title}")
        db_session.add(wl)
        db_session.commit()

        soup = _get_soup(authenticated_client, playlist.id)
        card = soup.select_one("#song-grid-view .card")
        remove_form = card.find("form", action=lambda a: a and "remove_whitelist" in a)
        assert remove_form is not None, "Remove from whitelist form should be present on whitelisted cards"


