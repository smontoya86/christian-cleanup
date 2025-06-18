# Security Documentation

## Table of Contents

1. [Security Architecture Overview](#security-architecture-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Input Validation & Protection](#input-validation--protection)
4. [CSRF Protection](#csrf-protection)
5. [Database Security](#database-security)
6. [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
7. [Security Headers](#security-headers)
8. [Audit Logging](#audit-logging)
9. [Secure Configuration](#secure-configuration)
10. [Security Testing](#security-testing)
11. [Development Security Guidelines](#development-security-guidelines)
12. [Security Checklist](#security-checklist)

## Security Architecture Overview

The Christian Cleanup application implements a comprehensive multi-layered security architecture designed to protect against common web application vulnerabilities and sophisticated attack vectors.

### Security Layers

1. **Network Layer**: Security headers, TLS enforcement, HSTS
2. **Application Layer**: Authentication, authorization, CSRF protection
3. **Input Layer**: Schema validation, sanitization, injection prevention
4. **Data Layer**: Encryption, secure storage, audit logging
5. **Monitoring Layer**: Rate limiting, anomaly detection, security logging

### Core Security Principles

- **Defense in Depth**: Multiple security layers that complement each other
- **Zero Trust**: Validate all inputs and authenticate all requests
- **Principle of Least Privilege**: Minimal necessary permissions
- **Fail Secure**: Secure defaults when errors occur
- **Security by Design**: Security integrated throughout development

## Authentication & Authorization

### Spotify OAuth Integration

The application uses Spotify OAuth 2.0 Authorization Code Flow with enhanced security features:

#### Token Management
- **Encrypted Storage**: All tokens encrypted using Fernet symmetric encryption
- **Secure Access Methods**: Automatic encryption/decryption via model methods
- **Graceful Fallback**: Secure degradation when encryption unavailable

```python
# Secure token access
user.set_access_token(token)  # Automatically encrypted
token = user.get_access_token()  # Automatically decrypted
```

#### Session Security
- **Session Fingerprinting**: Unique fingerprints prevent session hijacking
- **Activity Tracking**: Last activity timestamps for timeout management
- **Automatic Expiration**: Configurable session timeouts (default 8 hours)
- **Failed Attempt Tracking**: Rate limiting for refresh failures

#### Security Features
- **CSRF State Validation**: OAuth state parameter prevents CSRF attacks
- **Replay Attack Protection**: Time-based validation for authentication flows
- **Secure Logout**: Complete session and token cleanup
- **Constant-time Comparisons**: Protection against timing attacks

### Enhanced Authentication Decorator

The `@token_required` decorator provides comprehensive authentication validation:

```python
@token_required
def protected_route():
    # Multi-layer validation:
    # 1. Session fingerprint validation
    # 2. Token validity checking
    # 3. Activity timestamp updates
    # 4. Automatic cleanup on violations
    pass
```

## Input Validation & Protection

### Schema-based Validation

All user inputs are validated using Marshmallow schemas:

```python
class PlaylistRequestSchema(Schema):
    playlist_id = fields.String(
        required=True, 
        validate=validate.Length(min=22, max=22)
    )
    analysis_depth = fields.Integer(
        validate=validate.Range(min=1, max=5)
    )
```

### Input Sanitization

Comprehensive sanitization functions protect against various attacks:

- **HTML Sanitization**: XSS protection with entity escaping
- **SQL Injection Detection**: Pattern-based detection of 15+ attack vectors
- **File Upload Validation**: Extension, size, and content type checking
- **API Key Format Validation**: Provider-specific format verification

### Security Validation Coverage

- **Length Validation**: Configurable maximum input lengths
- **Character Validation**: Alphanumeric and safe character checking
- **Pattern Matching**: SQL injection and XSS pattern detection
- **Content Type Validation**: MIME type verification for uploads

## CSRF Protection

### Implementation

CSRF protection is implemented across all state-changing operations:

```python
# Token generation
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

# Token validation
def validate_csrf_token(token):
    if not token or token != session.get('csrf_token'):
        abort(403, description="CSRF token validation failed")
    return True
```

### Coverage

- All POST/PUT/DELETE endpoints protected
- Form-based CSRF token inclusion
- API endpoint token validation
- Automatic token generation and rotation

## Database Security

### SQL Injection Prevention

Multi-layered approach to prevent SQL injection:

1. **ORM Usage**: SQLAlchemy ORM prevents most injection attacks
2. **Pattern Detection**: Advanced regex-based attack pattern detection
3. **Input Sanitization**: Dangerous character removal and escaping
4. **Parameterized Queries**: When raw SQL necessary, use parameterization

### Database Security Checker

The `DatabaseSecurityChecker` class provides comprehensive protection:

```python
# Attack vector detection includes:
- UNION SELECT attacks
- Boolean blind attacks (1=1, OR true)
- Time-based attacks (SLEEP, WAITFOR DELAY)
- Stacked queries (DROP TABLE, DELETE FROM)
- Comment injection (/* */, --, #)
- System command execution (xp_cmdshell, sp_executesql)
```

### Secure Database Configuration

- **Connection Pooling**: Proper connection management
- **Access Controls**: Database user with minimal privileges
- **Encryption**: Sensitive data encryption before storage
- **Audit Logging**: Database operation logging

## Rate Limiting & DDoS Protection

### Enhanced Rate Limiting System

The `EnhancedRateLimiter` implements sophisticated protection:

#### Features
- **Sliding Window Algorithm**: Accurate rate limiting over time windows
- **Burst Protection**: Short-term spike handling
- **Progressive Penalties**: Escalating restrictions for violators
- **Automatic IP Blocking**: Persistent violator blocking (up to 1 hour)
- **Performance Optimized**: Handles 1000+ requests in <1 second

#### Implementation
```python
# Rate limiting configuration
rate_limiter = EnhancedRateLimiter(
    requests_per_minute=60,
    burst_limit=10,
    violation_penalty_minutes=5,
    max_violations_before_block=3
)
```

### Protection Levels

1. **Authentication Endpoints**: Strict limits to prevent brute force
2. **API Endpoints**: Moderate limits for legitimate usage
3. **Admin Operations**: Enhanced protection with IP-based limiting
4. **File Uploads**: Size and frequency restrictions

## Security Headers

### Comprehensive Header Suite

All responses include security headers for defense-in-depth:

```python
# Content Security Policy
'Content-Security-Policy': (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
    "connect-src 'self' api.spotify.com accounts.spotify.com; "
    "img-src 'self' data: i.scdn.co; "
    "font-src 'self' cdnjs.cloudflare.com; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests"
)

# Additional security headers
'X-Content-Type-Options': 'nosniff'
'X-Frame-Options': 'DENY'
'X-XSS-Protection': '1; mode=block'
'Referrer-Policy': 'strict-origin-when-cross-origin'
'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload'
```

### Header Protection Coverage

- **XSS Protection**: Content Security Policy and X-XSS-Protection
- **Clickjacking Prevention**: X-Frame-Options and CSP frame-ancestors
- **MIME Sniffing Prevention**: X-Content-Type-Options
- **Information Leakage Prevention**: Referrer-Policy
- **Transport Security**: HSTS with preload and subdomains

## Audit Logging

### Security Audit Logger

Comprehensive security event logging system:

```python
class SecurityAuditLogger:
    def log_authentication_attempt(self, user_id, success, ip_address, user_agent):
    def log_session_event(self, user_id, event_type, session_fingerprint):
    def log_security_violation(self, violation_type, ip_address, details):
    def log_rate_limit_violation(self, ip_address, endpoint, current_count):
```

### Logged Events

- **Authentication Events**: Login attempts, token refresh, logout
- **Session Events**: Creation, fingerprint changes, termination
- **Security Violations**: CSRF failures, input validation failures
- **Rate Limit Events**: Threshold breaches, IP blocking
- **Access Events**: Sensitive endpoint access, admin operations

### Log Format

Structured JSON logging with:
- Timestamp (ISO 8601)
- Event type and severity
- User identification (when available)
- IP address and user agent
- Request context and metadata
- Correlation IDs for tracking

## Secure Configuration

### Environment Variables

Security-sensitive configuration managed through environment variables:

```bash
# Encryption
FLASK_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-fernet-key-here

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# External APIs
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
```

### Configuration Security

- **Secret Management**: Environment-based secret storage
- **Key Rotation**: Support for encryption key rotation
- **Default Security**: Secure defaults for all configuration
- **Validation**: Configuration validation on startup

## Security Testing

### Test Coverage

Comprehensive security test suite with 25+ test cases:

#### Authentication Security Tests (26 tests)
- Token encryption/decryption functionality
- Session fingerprint generation and validation
- Session timeout management
- Authentication decorator behavior
- Token refresh security
- Security degradation handling

#### Input Validation Tests (15 tests)
- HTML sanitization and XSS prevention
- SQL injection detection and prevention
- File upload validation
- Schema validation for all input types
- Performance testing for large inputs

#### Rate Limiting Tests (10 tests)
- Sliding window algorithm accuracy
- Burst protection functionality
- Progressive penalty system
- IP blocking and unblocking
- Performance under load

#### Security Headers Tests (8 tests)
- CSP policy validation
- Security header presence and values
- HTTPS enforcement
- Cache control for sensitive data

### Testing Methodology

1. **Unit Tests**: Individual security component testing
2. **Integration Tests**: End-to-end security flow testing
3. **Performance Tests**: Security feature performance validation
4. **Penetration Tests**: Simulated attack scenarios
5. **Automated Scanning**: OWASP ZAP integration (recommended)

## Development Security Guidelines

### Secure Coding Practices

#### Input Handling
- Always validate and sanitize user inputs
- Use schema validation for complex inputs
- Implement length limits and character restrictions
- Escape HTML output to prevent XSS

#### Authentication
- Use the enhanced authentication decorator for protected routes
- Implement proper session management
- Never store passwords in plaintext
- Use secure token generation and storage

#### Database Operations
- Use SQLAlchemy ORM for database interactions
- Validate SQL inputs when raw queries necessary
- Implement proper connection pooling
- Use database transactions appropriately

#### Error Handling
- Don't expose sensitive information in error messages
- Log security events for monitoring
- Implement proper error response formats
- Use appropriate HTTP status codes

### Code Review Security Checklist

- [ ] All user inputs properly validated and sanitized
- [ ] Authentication required for protected endpoints
- [ ] CSRF protection for state-changing operations
- [ ] SQL injection prevention measures in place
- [ ] Security headers configured appropriately
- [ ] Sensitive data encrypted before storage
- [ ] Error handling doesn't leak information
- [ ] Security tests cover new functionality

## Security Checklist

### Pre-deployment Security Checklist

#### Authentication & Authorization
- [ ] All protected routes use `@token_required` decorator
- [ ] Token encryption/decryption working correctly
- [ ] Session fingerprinting enabled
- [ ] Automatic session timeout configured
- [ ] Failed authentication attempt limiting active

#### Input Validation
- [ ] All user inputs validated using schemas
- [ ] HTML output properly escaped
- [ ] File upload validation implemented
- [ ] SQL injection protection active
- [ ] XSS prevention measures in place

#### Security Headers
- [ ] Content Security Policy configured
- [ ] X-Frame-Options set to DENY
- [ ] X-Content-Type-Options set to nosniff
- [ ] HSTS enabled with preload
- [ ] X-XSS-Protection enabled

#### Rate Limiting
- [ ] Authentication endpoints rate limited
- [ ] API endpoints have appropriate limits
- [ ] Admin operations protected
- [ ] DDoS protection measures active

#### Monitoring & Logging
- [ ] Security audit logging enabled
- [ ] Error logging configured
- [ ] Log rotation and retention policies set
- [ ] Monitoring alerts configured

#### Configuration
- [ ] All secrets stored in environment variables
- [ ] Database connections secured
- [ ] Encryption keys properly managed
- [ ] Production configuration hardened

### Regular Security Maintenance

#### Weekly
- [ ] Review security audit logs
- [ ] Check for suspicious authentication patterns
- [ ] Monitor rate limiting effectiveness
- [ ] Verify all services running securely

#### Monthly
- [ ] Update dependencies for security patches
- [ ] Review and rotate API keys
- [ ] Conduct security scan with OWASP ZAP
- [ ] Review user access patterns

#### Quarterly
- [ ] Full security audit and penetration testing
- [ ] Review and update security policies
- [ ] Security training for development team
- [ ] Emergency response plan testing

### Security Contact Information

For security issues or questions:
- **Security Team**: [security@yourcompany.com]
- **Emergency Contact**: [emergency@yourcompany.com]
- **Incident Reporting**: [incidents@yourcompany.com]

### Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.0.x/security/)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)
- [Content Security Policy Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

*This document should be reviewed and updated regularly to reflect changes in the security landscape and application architecture.* 