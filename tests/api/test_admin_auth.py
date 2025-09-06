import json
from datetime import datetime, timedelta, timezone


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_admin_only_endpoints_require_auth(client, app, db):
    resp = client.post("/api/admin/recompute-has-flagged")
    assert resp.status_code in (302, 401)  # redirected or unauthorized

    resp = client.post("/api/admin/prune-analyses")
    assert resp.status_code in (302, 401)


def test_admin_only_endpoints_forbid_non_admin(client, app, db):
    from app.models.models import User

    user = User(
        spotify_id="u2",
        email="u2@example.com",
        display_name="User Two",
        access_token="tok",
        refresh_token="tok",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(user)
    db.session.commit()

    _login(client, user.id)

    resp = client.post("/api/admin/recompute-has-flagged")
    assert resp.status_code == 403

    resp = client.post("/api/admin/prune-analyses", data=json.dumps({"retention_days": 1}), content_type="application/json")
    assert resp.status_code == 403


def test_admin_only_endpoints_allow_admin(client, app, db):
    from app.models.models import User

    admin = User(
        spotify_id="admin1",
        email="admin@example.com",
        display_name="Admin",
        access_token="tok",
        refresh_token="tok",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()

    _login(client, admin.id)

    resp = client.post("/api/admin/recompute-has-flagged", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True

    resp = client.post("/api/admin/prune-analyses", data=json.dumps({"statuses": ["failed"], "retention_days": 0}), content_type="application/json")
    assert resp.status_code == 200
    data2 = resp.get_json()
    assert data2.get("success") is True
