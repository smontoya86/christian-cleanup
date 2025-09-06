from unittest.mock import patch

import pytest


@pytest.mark.integration
def test_health_and_readiness_endpoints(authenticated_client):
    r = authenticated_client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "healthy"

    r2 = authenticated_client.get("/api/health/live")
    assert r2.status_code == 200


@pytest.mark.integration
def test_analyze_single_song_flow(authenticated_client, db, sample_user):
    from app.models.models import Playlist, PlaylistSong, Song

    # Create song and playlist relationship for access control
    song = Song(spotify_id="e2e_song_1", title="E2E Song", artist="E2E Artist", lyrics="lyrics")
    db.session.add(song)
    db.session.commit()

    pl = Playlist(owner_id=sample_user.id, spotify_id="e2e_pl_1", name="E2E")
    db.session.add(pl)
    db.session.commit()

    link = PlaylistSong(playlist_id=pl.id, song_id=song.id, track_position=0)
    db.session.add(link)
    db.session.commit()

    # Mock router HTTP inside the analysis to avoid network
    with patch("app.services.analyzers.router_analyzer.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"score": 80, "concern_level": "Low", "biblical_themes": [], "supporting_scripture": [], "concerns": [], "verdict": {"summary": "freely_listen"}}'
                        )
                    }
                }
            ]
        }
        mock_post.return_value.raise_for_status = lambda: None

        resp = authenticated_client.post(f"/api/songs/{song.id}/analyze")
        assert resp.status_code == 200
        j = resp.get_json()
        assert j.get("success") is True

    # Fetch song analysis
    detail = authenticated_client.get(f"/api/song/{song.id}/analysis")
    assert detail.status_code == 200
    det = detail.get_json()
    assert det["analysis"] is not None
    assert "score" in det["analysis"]


@pytest.mark.integration
def test_playlist_status_and_unanalyzed_flow(authenticated_client, db, sample_user):
    from app.models.models import Playlist, PlaylistSong, Song

    pl = Playlist(owner_id=sample_user.id, spotify_id="e2e_pl_2", name="E2E2")
    db.session.add(pl)
    db.session.commit()

    s1 = Song(spotify_id="e2e_s1", title="S1", artist="A1", lyrics="l1")
    s2 = Song(spotify_id="e2e_s2", title="S2", artist="A2", lyrics="l2")
    db.session.add_all([s1, s2])
    db.session.commit()

    db.session.add_all([
        PlaylistSong(playlist_id=pl.id, song_id=s1.id, track_position=0),
        PlaylistSong(playlist_id=pl.id, song_id=s2.id, track_position=1),
    ])
    db.session.commit()

    # Start only unanalyzed analysis with router mocked
    with patch("app.services.analyzers.router_analyzer.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"score": 75, "concern_level": "Low", "biblical_themes": [], "supporting_scripture": [], "concerns": [], "verdict": {"summary": "freely_listen"}}'
                        )
                    }
                }
            ]
        }
        mock_post.return_value.raise_for_status = lambda: None

        r = authenticated_client.post(f"/api/playlists/{pl.id}/analyze-unanalyzed")
        assert r.status_code == 200
        jj = r.get_json()
        assert jj.get("success") is True
        assert jj.get("analyzed_count") >= 1

    # Check status endpoint
    st = authenticated_client.get(f"/api/playlists/{pl.id}/analysis-status")
    assert st.status_code == 200
    status = st.get_json()
    assert "success" in status
    assert "progress" in status

