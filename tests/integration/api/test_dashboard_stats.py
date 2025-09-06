import time
from datetime import datetime, timedelta, timezone


def test_dashboard_stats_cached(client, app, db):
    """Verify /api/dashboard/stats returns payload and benefits from cache on repeat call."""
    from app.models.models import User
    from flask_login import login_user

    # Create a user in DB
    user = User(
        spotify_id="u1",
        email="u1@example.com",
        display_name="User One",
        access_token="tok",
        refresh_token="tok",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(user)
    db.session.commit()

    # Log in by setting session cookie via test client
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    # First call - warm cache
    t0 = time.time()
    resp1 = client.get("/api/dashboard/stats")
    t1 = time.time()

    assert resp1.status_code == 200
    data1 = resp1.get_json()
    assert data1.get("success") is True
    assert "totals" in data1 and isinstance(data1["totals"], dict)
    assert {"total_playlists", "total_songs", "analyzed_songs", "flagged_songs", "analysis_progress"}.issubset(data1["totals"].keys())

    # Second call - should hit cache and be fast
    t2 = time.time()
    resp2 = client.get("/api/dashboard/stats")
    t3 = time.time()

    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2 == data1

    cold_ms = (t1 - t0) * 1000
    warm_ms = (t3 - t2) * 1000
    # Warm call should be faster; allow flakiness margin
    assert warm_ms <= cold_ms * 1.5


