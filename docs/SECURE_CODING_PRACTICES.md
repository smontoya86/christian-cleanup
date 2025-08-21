# Secure Coding Practices Guide

## Table of Contents

1. [Overview](#overview)
2. [Input Validation and Sanitization](#input-validation-and-sanitization)
3. [Authentication and Authorization](#authentication-and-authorization)
4. [Database Security](#database-security)
5. [Session Management](#session-management)
6. [Error Handling and Logging](#error-handling-and-logging)
7. [Cryptography and Encryption](#cryptography-and-encryption)
8. [API Security](#api-security)
9. [Frontend Security](#frontend-security)
10. [Configuration Management](#configuration-management)
11. [Testing Security](#testing-security)
12. [Code Review Guidelines](#code-review-guidelines)

## Overview

This guide provides practical secure coding standards and best practices for the Christian Cleanup application development team. Following these practices helps prevent common vulnerabilities and ensures the security of our application and user data.

### Security Principles

- **Input Validation**: Validate all inputs at the boundary
- **Output Encoding**: Encode all outputs to prevent injection
- **Authentication**: Verify identity before granting access
- **Authorization**: Ensure proper access controls
- **Encryption**: Protect sensitive data in transit and at rest
- **Logging**: Log security events for monitoring and forensics
- **Fail Secure**: Default to secure behavior when errors occur

## Input Validation and Sanitization

### Schema-Based Validation

Always use Marshmallow schemas for complex input validation:

```python
# ✅ DO: Use schema validation
from marshmallow import Schema, fields, validate

class PlaylistRequestSchema(Schema):
    playlist_id = fields.String(
        required=True,
        validate=validate.Length(min=22, max=22),
        error_messages={'required': 'Playlist ID is required'}
    )
    analysis_depth = fields.Integer(
        validate=validate.Range(min=1, max=5),
        load_default=3
    )

# ❌ DON'T: Accept raw inputs without validation
def analyze_playlist():
    playlist_id = request.form.get('playlist_id')  # Unsafe
    # Process without validation...
```

### Input Sanitization

Use the security utility functions for input sanitization:

```python
from app.utils.security import sanitize_html_input, validate_sql_safe_input

# ✅ DO: Sanitize HTML inputs
def update_user_profile():
    display_name = sanitize_html_input(request.form.get('display_name'))

    # Validate for SQL injection patterns
    if not validate_sql_safe_input(display_name):
        raise SecurityError("Invalid input detected")

# ❌ DON'T: Use raw inputs in database operations
def unsafe_search():
    query = request.args.get('q')  # Potential SQL injection
    results = db.session.execute(f"SELECT * FROM songs WHERE title LIKE '%{query}%'")
```

### File Upload Security

Implement comprehensive file upload validation:

```python
from app.utils.security import validate_file_upload

# ✅ DO: Validate file uploads thoroughly
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Validate file using security utility
    try:
        validate_file_upload(
            file,
            allowed_extensions=['jpg', 'png', 'gif'],
            max_size=5 * 1024 * 1024  # 5MB
        )
    except SecurityError as e:
        return jsonify({'error': str(e)}), 400

    # Process validated file...

# ❌ DON'T: Accept files without validation
def unsafe_upload():
    file = request.files['file']
    file.save(f"uploads/{file.filename}")  # Directory traversal risk
```

### URL Parameter Validation

Validate URL parameters and query strings:

```python
# ✅ DO: Validate URL parameters
@app.route('/playlist/<playlist_id>')
def playlist_detail(playlist_id):
    # Validate Spotify playlist ID format
    if not re.match(r'^[a-zA-Z0-9]{22}$', playlist_id):
        abort(400, description="Invalid playlist ID format")

    # Continue processing...

# ❌ DON'T: Use URL parameters directly
def unsafe_playlist_detail(playlist_id):
    # Direct database query without validation
    playlist = db.session.execute(f"SELECT * FROM playlists WHERE spotify_id = '{playlist_id}'")
```

## Authentication and Authorization

### Token-Based Authentication

Use the enhanced authentication decorator for protected routes:

```python
from app.utils.auth import token_required

# ✅ DO: Use authentication decorator
@app.route('/api/user/playlists')
@token_required
def get_user_playlists():
    user = g.current_user  # Available after authentication
    # Process authenticated request...

# ❌ DON'T: Implement custom authentication logic
def unsafe_get_playlists():
    token = request.headers.get('Authorization')
    if token:  # Weak validation
        # Process request...
```

### Session Management

Implement secure session handling:

```python
# ✅ DO: Use secure session management
from app.utils.security import generate_session_fingerprint

def login_user(user):
    session['user_id'] = user.id
    session['csrf_token'] = secrets.token_hex(32)

    # Generate session fingerprint for security
    fingerprint = generate_session_fingerprint(request)
    user.session_fingerprint = fingerprint
    user.last_activity = datetime.utcnow()
    db.session.commit()

# ❌ DON'T: Use weak session management
def unsafe_login(user):
    session['user'] = user.to_dict()  # Stores too much data
    session['logged_in'] = True  # Weak session tracking
```

### Authorization Checks

Implement proper authorization controls:

```python
# ✅ DO: Check authorization for resources
@app.route('/playlist/<playlist_id>/edit')
@token_required
def edit_playlist(playlist_id):
    user = g.current_user
    playlist = Playlist.query.filter_by(spotify_id=playlist_id).first_or_404()

    # Check if user owns the playlist
    if playlist.user_id != user.id:
        abort(403, description="You don't have permission to edit this playlist")

    # Continue with authorized operation...

# ❌ DON'T: Skip authorization checks
def unsafe_edit_playlist(playlist_id):
    playlist = Playlist.query.filter_by(spotify_id=playlist_id).first_or_404()
    # Process without checking ownership...
```

## Database Security

### ORM Usage

Always use SQLAlchemy ORM for database operations:

```python
# ✅ DO: Use ORM for database operations
def get_user_playlists(user_id):
    return Playlist.query.filter_by(user_id=user_id).all()

def search_songs(query):
    return Song.query.filter(Song.title.ilike(f'%{query}%')).limit(50).all()

# ❌ DON'T: Use raw SQL queries
def unsafe_search(query):
    # SQL injection vulnerability
    sql = f"SELECT * FROM songs WHERE title LIKE '%{query}%'"
    return db.session.execute(sql).fetchall()
```

### Database Transactions

Use proper transaction management:

```python
# ✅ DO: Use database transactions for consistency
def create_playlist_with_songs(playlist_data, song_ids):
    try:
        # Start transaction
        playlist = Playlist(**playlist_data)
        db.session.add(playlist)
        db.session.flush()  # Get playlist ID without committing

        # Add songs to playlist
        for song_id in song_ids:
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song_id
            )
            db.session.add(playlist_song)

        db.session.commit()
        return playlist
    except Exception as e:
        db.session.rollback()
        raise DatabaseError(f"Failed to create playlist: {str(e)}")

# ❌ DON'T: Make multiple database calls without transactions
def unsafe_create_playlist(playlist_data, song_ids):
    playlist = Playlist(**playlist_data)
    db.session.add(playlist)
    db.session.commit()

    # If this fails, playlist exists without songs
    for song_id in song_ids:
        playlist_song = PlaylistSong(playlist_id=playlist.id, song_id=song_id)
        db.session.add(playlist_song)
        db.session.commit()  # Multiple commits
```

### Connection Security

Use secure database connection practices:

```python
# ✅ DO: Use connection pooling and proper configuration
from app.config.centralized import config

# Database configuration with security settings
SQLALCHEMY_DATABASE_URI = config.DATABASE_URL
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'echo': False,  # Don't log SQL in production
}

# ❌ DON'T: Use insecure database configuration
SQLALCHEMY_DATABASE_URI = "postgresql://user:password@localhost/db"  # Hardcoded
SQLALCHEMY_ECHO = True  # Logs SQL in production
```

## Session Management

### Session Security

Implement secure session configuration:

```python
# ✅ DO: Configure secure sessions
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # Prevent XSS access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8)
)

# ❌ DON'T: Use insecure session settings
app.config.update(
    SESSION_COOKIE_SECURE=False,     # Allows HTTP
    SESSION_COOKIE_HTTPONLY=False,   # Accessible via JavaScript
)
```

### Session Validation

Validate sessions on each request:

```python
# ✅ DO: Validate session integrity
@app.before_request
def validate_session():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.session_fingerprint:
            current_fingerprint = generate_session_fingerprint(request)
            if user.session_fingerprint != current_fingerprint:
                session.clear()
                abort(401, description="Session validation failed")

# ❌ DON'T: Trust sessions without validation
def unsafe_session_handling():
    if 'user_id' in session:
        # Assume session is valid without checking
        user = User.query.get(session['user_id'])
```

## Error Handling and Logging

### Secure Error Handling

Implement secure error responses:

```python
from app.utils.error_framework import SecurityError, ValidationError

# ✅ DO: Use structured error handling
@app.errorhandler(SecurityError)
def handle_security_error(error):
    # Log detailed error for developers
    app.logger.error(f"Security error: {error.details}", extra={
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'endpoint': request.endpoint
    })

    # Return generic error to user
    return jsonify({
        'status': 'error',
        'message': 'Security validation failed'
    }), 403

# ❌ DON'T: Expose detailed error information
def unsafe_error_handling():
    try:
        # Some operation
        pass
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Exposes internals
```

### Security Logging

Log security events appropriately:

```python
from app.utils.security import SecurityAuditLogger

# ✅ DO: Log security events
audit_logger = SecurityAuditLogger()

@app.route('/api/auth/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        # Log successful authentication
        audit_logger.log_authentication_attempt(
            user_id=user.id,
            success=True,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify({'status': 'success'})
    else:
        # Log failed authentication
        audit_logger.log_authentication_attempt(
            user_id=user.id if user else None,
            success=False,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify({'status': 'error'}), 401

# ❌ DON'T: Skip security logging
def unsafe_login():
    # Authentication without logging
    user = authenticate_user(username, password)
    if user:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 401
```

## Cryptography and Encryption

### Token Encryption

Use secure token storage:

```python
# ✅ DO: Encrypt sensitive tokens
class User(db.Model):
    def set_access_token(self, token):
        """Securely store encrypted access token"""
        try:
            encrypted_token = encrypt_data(token)
            self.access_token_encrypted = encrypted_token
        except Exception:
            # Fallback to plaintext with warning
            app.logger.warning("Token encryption failed, storing plaintext")
            self.access_token = token

    def get_access_token(self):
        """Retrieve and decrypt access token"""
        if self.access_token_encrypted:
            try:
                return decrypt_data(self.access_token_encrypted)
            except Exception:
                app.logger.warning("Token decryption failed")
                return None
        return self.access_token

# ❌ DON'T: Store sensitive data in plaintext
class UnsafeUser(db.Model):
    access_token = db.Column(db.String(500))  # Plaintext storage

    def set_token(self, token):
        self.access_token = token  # No encryption
```

### Password Handling

Implement secure password practices:

```python
from werkzeug.security import generate_password_hash, check_password_hash

# ✅ DO: Use proper password hashing
class User(db.Model):
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        """Hash password before storing"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

# ❌ DON'T: Store passwords in plaintext or use weak hashing
class UnsafeUser(db.Model):
    password = db.Column(db.String(50))  # Plaintext password

    def set_password(self, password):
        import hashlib
        self.password = hashlib.md5(password.encode()).hexdigest()  # Weak hashing
```

## API Security

### Rate Limiting

Implement rate limiting for API endpoints:

```python
from app.utils.security import EnhancedRateLimiter

# ✅ DO: Use rate limiting for APIs
rate_limiter = EnhancedRateLimiter(
    requests_per_minute=60,
    burst_limit=10
)

@app.route('/api/search')
@token_required
def api_search():
    # Check rate limits
    if not rate_limiter.can_make_request(request.remote_addr):
        abort(429, description="Rate limit exceeded")

    # Record request
    rate_limiter.record_request(request.remote_addr)

    # Process search...

# ❌ DON'T: Leave APIs without rate limiting
def unsafe_api_search():
    # No rate limiting - vulnerable to abuse
    query = request.args.get('q')
    results = perform_expensive_search(query)
    return jsonify(results)
```

### CSRF Protection

Implement CSRF protection for state-changing operations:

```python
from app.utils.security import validate_csrf_token

# ✅ DO: Protect state-changing operations
@app.route('/api/playlist/create', methods=['POST'])
@token_required
def create_playlist():
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    validate_csrf_token(csrf_token)

    # Process playlist creation...

# ❌ DON'T: Skip CSRF protection
def unsafe_create_playlist():
    # No CSRF protection - vulnerable to attacks
    playlist_data = request.json
    playlist = Playlist(**playlist_data)
    db.session.add(playlist)
    db.session.commit()
```

### API Response Security

Structure API responses securely:

```python
# ✅ DO: Use consistent, secure API responses
@app.route('/api/user/profile')
@token_required
def get_user_profile():
    user = g.current_user

    # Return only necessary data
    return jsonify({
        'status': 'success',
        'data': {
            'id': user.id,
            'display_name': user.display_name,
            'email': user.email
            # Don't include sensitive fields like tokens
        }
    })

# ❌ DON'T: Expose sensitive data in responses
def unsafe_user_profile():
    user = g.current_user

    # Exposes all user data including sensitive fields
    return jsonify(user.to_dict())  # May include tokens, hashes, etc.
```

## Frontend Security

### Content Security Policy

Implement and maintain CSP headers:

```python
# ✅ DO: Use strict Content Security Policy
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "connect-src 'self' api.spotify.com accounts.spotify.com; "
        "img-src 'self' data: i.scdn.co; "
        "font-src 'self' cdnjs.cloudflare.com; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )
    return response

# ❌ DON'T: Use overly permissive CSP
def unsafe_csp():
    response.headers['Content-Security-Policy'] = "default-src *"  # Too permissive
```

### XSS Prevention

Prevent cross-site scripting attacks:

```python
from markupsafe import escape

# ✅ DO: Escape user-generated content
@app.template_filter('safe_user_content')
def safe_user_content(text):
    # Escape HTML but allow basic formatting
    return escape(text).replace('\n', '<br>')

# In templates:
# {{ user.bio | safe_user_content | safe }}

# ❌ DON'T: Render user content without escaping
# In templates (unsafe):
# {{ user.bio | safe }}  # Potential XSS vulnerability
```

### JavaScript Security

Implement secure JavaScript practices:

```javascript
// ✅ DO: Validate and sanitize data from APIs
async function loadUserData() {
    try {
        const response = await fetch('/api/user/profile');
        const data = await response.json();

        // Validate response structure
        if (data.status === 'success' && data.data) {
            // Escape content before DOM insertion
            document.getElementById('username').textContent = data.data.display_name;
        }
    } catch (error) {
        console.error('Failed to load user data:', error);
    }
}

// ❌ DON'T: Use innerHTML with unvalidated data
function unsafeLoadUserData() {
    fetch('/api/user/profile')
        .then(response => response.json())
        .then(data => {
            // XSS vulnerability
            document.getElementById('profile').innerHTML = data.bio;
        });
}
```

## Configuration Management

### Environment Variables

Manage configuration securely:

```python
# ✅ DO: Use centralized configuration with validation
from app.config.centralized import config

# Access configuration through centralized system
DATABASE_URL = config.DATABASE_URL
SPOTIFY_CLIENT_ID = config.SPOTIFY_CLIENT_ID
ENCRYPTION_KEY = config.ENCRYPTION_KEY

# ❌ DON'T: Access environment variables directly
import os

# Scattered configuration access
DATABASE_URL = os.environ.get('DATABASE_URL')  # No validation
API_KEY = os.environ.get('API_KEY', 'default')  # Insecure default
```

### Secret Management

Handle secrets properly:

```python
# ✅ DO: Validate required secrets on startup
def validate_configuration():
    required_secrets = ['FLASK_SECRET_KEY', 'ENCRYPTION_KEY', 'DATABASE_URL']
    missing_secrets = []

    for secret in required_secrets:
        if not getattr(config, secret.lower(), None):
            missing_secrets.append(secret)

    if missing_secrets:
        raise ConfigurationError(f"Missing required secrets: {missing_secrets}")

# ❌ DON'T: Use hardcoded secrets or weak defaults
SECRET_KEY = "development-key"  # Hardcoded secret
API_KEY = os.environ.get('API_KEY', 'default-key')  # Weak default
```

## Testing Security

### Security Test Patterns

Write security-focused tests:

```python
# ✅ DO: Test security controls
def test_authentication_required():
    """Test that protected endpoints require authentication"""
    response = client.get('/api/user/playlists')
    assert response.status_code == 401

def test_authorization_check():
    """Test that users can only access their own data"""
    # Create two users
    user1 = create_test_user('user1@example.com')
    user2 = create_test_user('user2@example.com')

    # User1 tries to access User2's data
    with client.session_transaction() as sess:
        sess['user_id'] = user1.id

    response = client.get(f'/api/user/{user2.id}/playlists')
    assert response.status_code == 403

def test_input_validation():
    """Test that invalid inputs are rejected"""
    response = client.post('/api/playlist/create', json={
        'name': 'x' * 1000,  # Too long
        'description': '<script>alert("xss")</script>'  # XSS attempt
    })
    assert response.status_code == 400

# ❌ DON'T: Only test happy path scenarios
def test_create_playlist():
    response = client.post('/api/playlist/create', json={'name': 'Test'})
    assert response.status_code == 200  # Missing security tests
```

### Security Regression Tests

Create tests to prevent security regressions:

```python
# ✅ DO: Test for specific vulnerabilities
def test_sql_injection_prevention():
    """Ensure SQL injection attempts are blocked"""
    malicious_input = "'; DROP TABLE users; --"

    response = client.get(f'/api/search?q={malicious_input}')

    # Should not crash and should return safe response
    assert response.status_code in [200, 400]

    # Verify database integrity
    user_count = User.query.count()
    assert user_count > 0  # Table should still exist

def test_xss_prevention():
    """Ensure XSS payloads are properly handled"""
    xss_payload = '<script>alert("xss")</script>'

    # Test input sanitization
    sanitized = sanitize_html_input(xss_payload)
    assert '<script>' not in sanitized
    assert '&lt;script&gt;' in sanitized

# ❌ DON'T: Skip security regression testing
def test_basic_functionality():
    # Only tests basic functionality without security considerations
    response = client.get('/api/search?q=test')
    assert response.status_code == 200
```

## Code Review Guidelines

### Security Review Checklist

Use this checklist during code reviews:

#### Input Validation
- [ ] All user inputs validated using schemas
- [ ] File uploads properly validated
- [ ] URL parameters validated
- [ ] SQL injection prevention measures in place

#### Authentication & Authorization
- [ ] Protected routes use `@token_required` decorator
- [ ] Authorization checks implemented for resource access
- [ ] Session management follows security guidelines
- [ ] CSRF protection for state-changing operations

#### Data Security
- [ ] Sensitive data encrypted before storage
- [ ] Database operations use ORM instead of raw SQL
- [ ] Proper transaction management implemented
- [ ] No sensitive data in logs or error messages

#### Error Handling
- [ ] Secure error responses (no information leakage)
- [ ] Security events properly logged
- [ ] Exception handling doesn't expose internals
- [ ] Appropriate HTTP status codes used

#### Configuration
- [ ] No hardcoded secrets or credentials
- [ ] Environment variables accessed through centralized config
- [ ] Security settings properly configured
- [ ] Default configurations are secure

### Common Security Anti-Patterns

Watch for these common security mistakes:

```python
# ❌ ANTI-PATTERN: Direct user input in SQL
def bad_search(query):
    sql = f"SELECT * FROM songs WHERE title LIKE '%{query}%'"
    return db.session.execute(sql)

# ✅ CORRECT: Use ORM or parameterized queries
def good_search(query):
    return Song.query.filter(Song.title.ilike(f'%{query}%')).all()

# ❌ ANTI-PATTERN: Exposing sensitive data
def bad_user_api():
    user = g.current_user
    return jsonify(user.__dict__)  # Exposes all attributes

# ✅ CORRECT: Return only necessary data
def good_user_api():
    user = g.current_user
    return jsonify({
        'id': user.id,
        'name': user.display_name,
        'email': user.email
    })

# ❌ ANTI-PATTERN: Weak session validation
def bad_auth_check():
    if 'user_id' in session:
        return True
    return False

# ✅ CORRECT: Comprehensive authentication
@token_required
def good_auth_check():
    # Full authentication and session validation
    return g.current_user
```

### Security Code Review Process

Follow this process for security-focused code reviews:

1. **Automated Checks**: Run security linters and SAST tools
2. **Manual Review**: Focus on security-critical areas
3. **Threat Modeling**: Consider potential attack vectors
4. **Testing Verification**: Ensure security tests are included
5. **Documentation**: Verify security decisions are documented

### Security Documentation Requirements

Document security decisions in code:

```python
# ✅ DO: Document security decisions
def process_user_input(user_input):
    """
    Process user input with security validation.

    Security considerations:
    - Input is validated against injection patterns
    - Length limits enforced to prevent DoS
    - HTML entities escaped to prevent XSS
    - Rate limiting applied to prevent abuse

    Args:
        user_input (str): Raw user input to process

    Returns:
        str: Sanitized and validated input

    Raises:
        SecurityError: If input fails security validation
    """
    # Validate input length (DoS prevention)
    if len(user_input) > MAX_INPUT_LENGTH:
        raise SecurityError("Input exceeds maximum length")

    # Check for SQL injection patterns
    if not validate_sql_safe_input(user_input):
        raise SecurityError("Potentially malicious input detected")

    # Sanitize HTML to prevent XSS
    return sanitize_html_input(user_input)

# ❌ DON'T: Leave security decisions undocumented
def process_input(input_data):
    # Unclear why these specific validations are done
    if len(input_data) > 1000:
        return None
    return escape(input_data)
```

---

## Conclusion

Following these secure coding practices helps protect our application and users from security threats. Remember:

- **Security is everyone's responsibility**
- **Validate all inputs, escape all outputs**
- **Use provided security utilities and patterns**
- **Document security decisions**
- **Test security controls thoroughly**
- **Stay updated on security best practices**

For questions about security practices or to report security concerns, contact the security team or refer to our [Security Documentation](SECURITY.md) and [Incident Response Plan](INCIDENT_RESPONSE_PLAN.md).

**Document Version**: 1.0
**Last Updated**: [Current Date]
**Next Review**: [Date + 6 months]
