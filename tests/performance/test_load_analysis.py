import json
import time
from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.performance
def test_light_load_analyze_multiple_songs(client, app, db):
    from app.models.models import User, Song, Playlist, PlaylistSong

    # Create and login admin
    admin = User(
        spotify_id="admin-load",
        email="admin-load@example.com",
        display_name="Admin",
        access_token="tok",
        refresh_token="tok",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    # Create a playlist owned by admin
    pl = Playlist(spotify_id="pl-load", name="LoadTest", owner_id=admin.id)
    db.session.add(pl)
    db.session.flush()

    # Seed songs and associate with playlist
    songs = []
    for i in range(10):
        s = Song(
            spotify_id=f"song-{i}",
            title=f"Load Song {i}",
            artist="Load Artist",
            album="Load Album",
        )
        db.session.add(s)
        songs.append(s)
    db.session.flush()

    for idx, s in enumerate(songs):
        db.session.add(PlaylistSong(playlist_id=pl.id, song_id=s.id, track_position=idx))
    db.session.commit()

    # Kick off analyzes quickly
    start = time.time()
    for s in songs:
        resp = client.post(f"/api/songs/{s.id}/analyze")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True

    # Poll a subset to keep test short
    completed = 0
    attempts = 0
    while completed < 5 and attempts < 30:
        completed = 0
        for s in songs[:5]:
            r = client.get(f"/api/songs/{s.id}/analysis-status")
            assert r.status_code == 200
            sd = r.get_json()
            if sd.get("completed") or sd.get("has_analysis"):
                completed += 1
        attempts += 1
        time.sleep(0.1)

    elapsed = time.time() - start
    assert completed >= 3
    assert elapsed < 10
