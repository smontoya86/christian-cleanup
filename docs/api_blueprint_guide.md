# API Blueprint Guide

This document provides a comprehensive overview of all API routes organized by blueprint in the Christian Music Curator application.

## Blueprint Architecture Overview

The application uses a modular blueprint architecture to organize routes by functionality. Each blueprint handles a specific domain of the application.

## 🔐 Authentication

### auth Blueprint
**Purpose**: Spotify OAuth authentication flow  
**Base Path**: `/auth`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/auth/login` | GET | Initiate Spotify OAuth flow | None |
| `/auth/callback` | GET | OAuth callback handler | None |
| `/auth/logout` | POST | User logout | Required |

## 🏠 Core Application

### core Blueprint  
**Purpose**: Dashboard and main application pages  
**Base Path**: `/`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/` | GET | Homepage/landing page | None |
| `/dashboard` | GET | Main dashboard view | Required |
| `/dashboard` | POST | Handle dashboard actions (clear sync flag) | Required |

## 📋 Playlist Management

### playlist Blueprint
**Purpose**: Playlist viewing, management, and synchronization  
**Base Path**: `/playlist`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/playlist/<playlist_id>` | GET | View playlist details | Required |
| `/playlist/<playlist_id>/update` | POST | Update playlist tracks | Required |
| `/sync-playlists` | POST | Sync with Spotify | Required |
| `/remove_song/<playlist_id>/<track_id>` | POST | Remove song from playlist | Required |
| `/analyze_playlist_api/<playlist_id>` | POST | Analyze playlist content | Required |

## 🎵 Song Management

### song Blueprint
**Purpose**: Individual song operations and details  
**Base Path**: `/song`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/song/<song_id>` | GET | View song details and analysis | Required |
| `/song/<song_id>/analyze` | POST | Analyze single song | Required |
| `/song/<song_id>/edit` | POST | Edit song metadata | Required |

## 🔍 Analysis Operations

### analysis Blueprint
**Purpose**: Content analysis operations and status checking  
**Base Path**: `/api`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/songs/<song_id>/analysis-status` | GET | Get song analysis status | Required |
| `/api/playlists/<playlist_id>/analysis-status` | GET | Get playlist analysis status | Required |
| `/api/songs/<song_id>/analyze` | POST | Analyze single song | Required |
| `/api/songs/<song_id>/reanalyze` | POST | Reanalyze single song | Required |
| `/api/playlists/<playlist_id>/analyze-unanalyzed` | POST | Analyze unanalyzed songs | Required |
| `/api/playlists/<playlist_id>/reanalyze-all` | POST | Reanalyze all playlist songs | Required |
| `/api/analysis/playlist/<playlist_id>` | GET | Get playlist analysis data | Required |
| `/api/analysis/song/<song_id>` | GET | Get song analysis data | Required |
| `/comprehensive_reanalyze_all_user_songs/<user_id>` | GET | Comprehensive user reanalysis | Required |

## 📝 Whitelist/Blacklist Management

### whitelist Blueprint
**Purpose**: Whitelist and blacklist management operations  
**Base Path**: `/`

#### Playlist List Management
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/whitelist_playlist/<playlist_id>` | POST | Add playlist to whitelist | Required |
| `/blacklist_playlist/<playlist_id>` | POST | Add playlist to blacklist | Required |
| `/remove_whitelist_playlist/<playlist_id>` | POST | Remove playlist from whitelist | Required |
| `/remove_blacklist_playlist/<playlist_id>` | POST | Remove playlist from blacklist | Required |

#### Song List Management  
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/whitelist_song/<playlist_id>/<track_id>` | POST | Add song to whitelist | Required |
| `/blacklist_song/<playlist_id>/<track_id>` | POST | Add song to blacklist | Required |
| `/remove_whitelist_song/<playlist_id>/<track_id>` | POST | Remove song from whitelist | Required |
| `/remove_blacklist_song/<playlist_id>/<track_id>` | POST | Remove song from blacklist | Required |

#### API Endpoints for List Management
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/song/<song_db_id>/whitelist` | POST | API: Add song to whitelist | Required |
| `/api/song/<song_db_id>/blacklist` | POST | API: Add song to blacklist | Required |
| `/api/whitelist/clear` | POST | Clear all whitelist items | Required |
| `/api/blacklist/clear` | POST | Clear all blacklist items | Required |
| `/api/blacklist/<item_id>` | DELETE | Delete blacklist item | Required |

#### Item Management
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/add-whitelist-item` | POST | Add whitelist item | Required |
| `/add-blacklist-item` | POST | Add blacklist item | Required |
| `/remove-whitelist-item/<item_id>` | POST | Remove whitelist item | Required |
| `/remove-blacklist-item/<item_id>` | POST | Remove blacklist item | Required |
| `/edit-whitelist-item/<item_id>` | POST | Edit whitelist item | Required |
| `/edit-blacklist-item/<item_id>` | POST | Edit blacklist item | Required |

#### Bulk Operations
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/export-whitelist` | GET | Export whitelist | Required |
| `/export-blacklist` | GET | Export blacklist | Required |
| `/bulk-import-whitelist` | POST | Bulk import whitelist | Required |
| `/bulk-import-blacklist` | POST | Bulk import blacklist | Required |

## 👤 User Management

### user Blueprint
**Purpose**: User settings and profile management  
**Base Path**: `/`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/settings` | GET | View user settings | Required |
| `/settings` | POST | Update user settings | Required |
| `/blacklist-whitelist` | GET | Whitelist/blacklist management page | Required |

## 🔧 Administrative Functions

### admin Blueprint
**Purpose**: Administrative operations and management  
**Base Path**: `/admin`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/admin/resync-all-playlists` | POST | Admin: Resync all playlists | Admin Required |
| `/admin/reanalyze-all-songs` | POST | Admin: Reanalyze all songs | Admin Required |
| `/api/admin/reanalysis-status` | GET | Admin: Get reanalysis status | Admin Required |

## 🔍 System Monitoring

### system Blueprint
**Purpose**: System health, monitoring, and utility functions  
**Base Path**: `/`

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/sync-status` | GET | Get sync status | Required |
| `/check_auth` | GET | Check authentication status | None |
| `/health` | GET | Health check endpoint | None |
| `/monitoring` | GET | System monitoring dashboard | Admin Required |

## 🌐 JSON API Endpoints

### api Blueprint
**Purpose**: RESTful JSON API for programmatic access  
**Base Path**: `/api`

#### Whitelist API
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/whitelist` | GET | Get whitelist items | Required |
| `/api/whitelist` | POST | Add whitelist item | Required |
| `/api/whitelist/<entry_id>` | DELETE | Remove whitelist item | Required |

#### Blacklist API
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/blacklist` | GET | Get blacklist items | Required |
| `/api/blacklist` | POST | Add blacklist item | Required |
| `/api/blacklist/<entry_id>` | DELETE | Remove blacklist item | Required |

## 🔬 Diagnostics & Monitoring

### diagnostics Blueprint (Admin API)
**Purpose**: System diagnostics and performance monitoring  
**Base Path**: `/diagnostics`

#### Performance Monitoring
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/performance/metrics` | GET | Get performance metrics | Admin Required |
| `/performance/thresholds` | GET/POST | Get/update performance thresholds | Admin Required |
| `/performance/monitoring` | POST | Start/stop performance monitoring | Admin Required |

#### Error Tracking
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/errors/recent` | GET | Get recent errors | Admin Required |
| `/errors/track` | POST | Manually track error (testing) | Admin Required |
| `/errors/summary` | GET | Get error summary statistics | Admin Required |

#### System Health
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/health/detailed` | GET | Detailed health check | Admin Required |
| `/health/database` | GET | Database health status | Admin Required |
| `/health/redis` | GET | Redis health status | Admin Required |

## 🔑 Authentication Requirements

### Authentication Levels

1. **None** - No authentication required (public endpoints)
2. **Required** - User must be logged in via Spotify OAuth
3. **Admin Required** - User must be logged in AND have admin privileges

### Authentication Implementation

- **Flask-Login** - Session-based authentication
- **Spotify OAuth2** - Third-party authentication provider
- **Token Validation** - Spotify token validation for API access
- **Admin Decorators** - Role-based access control for admin functions

## 📊 Request/Response Patterns

### Standard Response Formats

#### Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Operation completed successfully"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

#### List Response
```json
{
  "success": true,
  "data": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Common HTTP Status Codes

- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **409 Conflict** - Resource conflict (e.g., playlist snapshot mismatch)
- **500 Internal Server Error** - Server error

## 🔄 Blueprint Registration

Blueprints are registered in `app/__init__.py` in the following order:

1. `auth` - Authentication (highest priority)
2. `core` - Core application routes
3. `playlist` - Playlist management
4. `song` - Song operations
5. `analysis` - Analysis operations
6. `whitelist` - List management
7. `user` - User settings
8. `admin` - Administrative functions
9. `system` - System monitoring
10. `api` - JSON API endpoints
11. `diagnostics` - Admin diagnostics

## 🛡️ Security Considerations

### CSRF Protection
- Enabled for all POST/PUT/DELETE requests
- Uses Flask-WTF for CSRF token validation

### Input Validation
- JSON schema validation for API endpoints
- Form validation for web forms
- SQL injection prevention via SQLAlchemy ORM

### Rate Limiting
- Spotify API rate limiting handled
- User action throttling on sensitive operations

### Error Handling
- Comprehensive error logging
- Sanitized error responses (no sensitive data exposure)
- Centralized exception handling

---

**Note**: This guide reflects the current blueprint architecture implemented in Task 34. All routes have been successfully migrated from the monolithic structure to the modular blueprint architecture while maintaining backward compatibility. 