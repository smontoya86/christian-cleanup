# Security Features Testing Guide

## Quick Testing Commands

### Test Force Re-authentication

**Simulate a user who logged in 31 days ago:**

```bash
# Set a user's last_login to 31 days ago
docker compose exec -T web python << 'EOF'
from app import create_app, db
from app.models import User
from datetime import datetime, timedelta, timezone

app = create_app()
with app.app_context():
    user = User.query.first()
    if user:
        user.last_login = datetime.now(timezone.utc) - timedelta(days=31)
        db.session.commit()
        print(f"✅ Set user {user.email} last_login to 31 days ago")
        print(f"   User ID: {user.id}")
    else:
        print("❌ No users found in database")
EOF
```

**Expected Behavior:**
1. Try to access dashboard: `http://127.0.0.1:5001/dashboard`
2. Should see flash message: *"For your security, please log in again. It's been more than 30 days since your last login."*
3. Redirected to login page
4. After logging back in, `last_login` updates to current time

---

### Test Session Timeout

**Current Behavior:**
- Sessions expire after **30 days of inactivity**
- Each request extends the session
- Cookie secure flags enabled in production

**To Test Manually:**
1. Log in
2. Check browser dev tools → Application → Cookies
3. Verify session cookie has:
   - `HttpOnly` flag
   - `SameSite=Lax`
   - Expires in ~30 days
4. Close browser, reopen after 30 days → Session expired

**Quick Test (Modify Session Timeout):**
```python
# In app/__init__.py, temporarily change to 1 minute:
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1)

# Restart server
docker compose restart web

# Log in, wait 2 minutes, try to access dashboard
# Should be logged out automatically
```

---

### Test Token Revocation on Logout

**Check Logs for Revocation:**

```bash
# Log out from the app, then check logs
docker compose logs web --tail=20 | grep -i "revoke"
```

**Expected Output:**
```
INFO: Revoked Spotify tokens for user 1
```

**Verify Token is Invalid:**

After logout, the old access token should no longer work with Spotify API.

---

## Detailed Testing Checklist

### ✅ Feature 1: Session Timeout (30 Days)

- [ ] **Verify Session Creation**
  - Log in successfully
  - Check browser cookies for session cookie
  - Verify expiry is ~30 days from now

- [ ] **Verify Session Extension**
  - Log in
  - Wait a few minutes
  - Perform action (load dashboard)
  - Check cookie expiry extends

- [ ] **Verify Session Expiration**
  - Temporarily set `PERMANENT_SESSION_LIFETIME` to 1 minute
  - Log in
  - Wait 2 minutes
  - Try to access protected route
  - Should be logged out

- [ ] **Verify Secure Flags**
  - In production (`FLASK_ENV=production`):
    - Session cookie has `Secure` flag
  - In development:
    - Session cookie does NOT have `Secure` flag
  - All environments:
    - `HttpOnly` = True
    - `SameSite` = Lax

---

### ✅ Feature 2: Token Revocation on Logout

- [ ] **Verify Revocation Call**
  - Log in with Spotify
  - Log out
  - Check logs: Should see "Revoked Spotify tokens for user X"

- [ ] **Verify Token Invalid After Logout**
  - Log in, capture access token from database
  - Log out
  - Try to use old token with Spotify API
  - Should get 401 Unauthorized

- [ ] **Verify Graceful Failure**
  - Disconnect network temporarily
  - Log out
  - Check logs: Should see warning about revocation failure
  - User should still be logged out successfully

---

### ✅ Feature 3: Force Re-authentication (30 Days)

- [ ] **Verify Normal Login**
  - Log in with Spotify
  - Check database: `last_login` should be current timestamp
  - Access dashboard: Should work normally

- [ ] **Verify Re-auth Check**
  - Set `last_login` to 31 days ago (use command above)
  - Try to access any protected route
  - Should be logged out with flash message
  - Should be redirected to login

- [ ] **Verify Skip for Auth Routes**
  - Set `last_login` to 31 days ago
  - Navigate to `/auth/login` directly
  - Should NOT be logged out (already on login page)

- [ ] **Verify last_login Updates**
  - Log in
  - Check `last_login` timestamp in database
  - Wait a few seconds, log out and log back in
  - Verify `last_login` updated to new timestamp

---

## Database Queries for Testing

```bash
# Check a specific user's last_login
docker compose exec -T web python << 'EOF'
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.first()
    if user:
        print(f"User: {user.email}")
        print(f"Last Login: {user.last_login}")
        print(f"Token Expiry: {user.token_expiry}")
        print(f"Needs Reauth (30d): {user.needs_reauth(30)}")
    else:
        print("No users found")
EOF
```

```bash
# Check all users' last_login
docker compose exec -T web python << 'EOF'
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        print(f"{user.id}: {user.email} - Last Login: {user.last_login}")
EOF
```

---

## Expected Logs

### Successful Login:
```
INFO: User 1 logged in successfully
```

### Successful Logout with Revocation:
```
INFO: Revoked Spotify tokens for user 1
```

### Force Re-authentication:
```
INFO: User 1 forced to re-authenticate (30 days since last login)
```

### Failed Token Revocation (network issue):
```
WARNING: Failed to revoke Spotify tokens for user 1: [error details]
```

---

## Production Readiness

All three features are **production-ready** and **enabled by default**.

### Current Configuration:
- Session timeout: **30 days**
- Force re-auth threshold: **30 days**
- Token revocation: **Enabled on logout**

### To Adjust:

**Change session timeout:**
```python
# app/__init__.py
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)  # 60 days
```

**Change re-auth threshold:**
```python
# app/routes/auth.py (line 42)
if current_user.needs_reauth(days_threshold=60):  # 60 days instead of 30
```

**Disable token revocation temporarily:**
```python
# app/routes/auth.py (line 337-341)
# Comment out these lines:
# if was_authenticated and current_user.get_access_token():
#     try:
#         _revoke_spotify_tokens(current_user)
#     except Exception as e:
#         current_app.logger.warning(...)
```

---

## Monitoring in Production

### Key Metrics:
- Sessions created per day
- Sessions expired per day
- Forced re-authentications per day
- Token revocations (successful/failed)

### Log Queries:
```bash
# Count forced re-auths today
docker compose logs web | grep "forced to re-authenticate" | wc -l

# Count token revocations today
docker compose logs web | grep "Revoked Spotify tokens" | wc -l

# Check for revocation failures
docker compose logs web | grep "Failed to revoke" 
```

---

## Status: ✅ Ready for Testing

All security features implemented and deployed. Begin testing with the commands above!

