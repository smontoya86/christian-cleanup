# Route Categorization Analysis for Blueprint Refactoring
## Task 34.1: Analyze and Categorize Routes

### Overview
- **Total Routes**: 55 routes in 2,972 lines
- **Current File**: `app/main/routes.py`
- **Analysis Date**: 2025-01-28

---

## Route Categories Analysis

### 1. **CORE/DASHBOARD Blueprint** (4 routes)
**URL Prefix**: `/` (root)
**Purpose**: Main application entry points and dashboard functionality

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/` | 54 | GET | `index()` | Home page/entry point |
| `/test_base_render` | 60 | GET | `test_base_render_route()` | Testing route |
| `/dashboard` | 169 | GET | `dashboard()` | Main dashboard view |
| `/dashboard` | 228 | POST | `dashboard_post()` | Dashboard POST actions |

**Notes**: Core application routes that serve as main entry points.

---

### 2. **PLAYLIST Blueprint** (5 routes)
**URL Prefix**: `/playlist`
**Purpose**: Playlist viewing, management, and synchronization

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/playlist/<string:playlist_id>` | 612 | GET | `playlist_detail()` | View playlist details |
| `/playlist/<string:playlist_id>/update` | 653 | POST | `update_playlist()` | Update playlist info |
| `/sync-playlists` | 239 | POST | `sync_playlists()` | Sync with Spotify |
| `/remove_song/<playlist_id>/<track_id>` | 706 | POST | `remove_song()` | Remove song from playlist |
| `/analyze_playlist_api/<string:playlist_id>` | 1010 | POST | `analyze_playlist_api()` | Analyze playlist |

**Notes**: Core playlist management functionality, including sync and song removal.

---

### 3. **SONG Blueprint** (3 routes)
**URL Prefix**: `/song`
**Purpose**: Individual song viewing and details

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/songs/<int:song_id>` | 920 | GET | `song_detail()` | View song details |
| `/songs/<int:song_id>/` | 921 | GET | `song_detail()` | View song details (trailing slash) |

**Notes**: Song-specific viewing functionality. Minimal but focused.

---

### 4. **ANALYSIS API Blueprint** (14 routes)
**URL Prefix**: `/api/analysis`
**Purpose**: Analysis operations, status checking, and data retrieval

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/api/songs/<int:song_id>/analysis-status` | 1070 | GET | `get_song_analysis_status()` | Get song analysis status |
| `/api/playlists/<string:playlist_id>/analysis-status/` | 1164 | GET | `get_analysis_status()` | Get playlist analysis status |
| `/api/playlists/<string:playlist_id>/analysis-status` | 1165 | GET | `get_analysis_status()` | Get playlist analysis status (compat) |
| `/api/songs/<int:song_id>/analyze/` | 1378 | POST | `analyze_song_route()` | Analyze single song |
| `/api/songs/<int:song_id>/analyze` | 1379 | POST | `analyze_song_route()` | Analyze single song (compat) |
| `/api/songs/<int:song_id>/reanalyze/` | 1429 | POST | `reanalyze_song_route()` | Reanalyze single song |
| `/api/songs/<int:song_id>/reanalyze` | 1430 | POST | `reanalyze_song_route()` | Reanalyze single song (compat) |
| `/api/playlists/<string:playlist_id>/analyze-unanalyzed/` | 1437 | POST | `analyze_unanalyzed_songs_route()` | Analyze unanalyzed songs |
| `/api/playlists/<string:playlist_id>/analyze-unanalyzed` | 1438 | POST | `analyze_unanalyzed_songs_route()` | Analyze unanalyzed songs (compat) |
| `/api/playlists/<string:playlist_id>/reanalyze-all/` | 1467 | POST | `reanalyze_all_songs_route()` | Reanalyze all songs |
| `/api/playlists/<string:playlist_id>/reanalyze-all` | 1468 | POST | `reanalyze_all_songs_route()` | Reanalyze all songs (compat) |
| `/api/analysis/playlist/<string:playlist_id>` | 2676 | GET | `playlist_analysis_data()` | Get playlist analysis data |
| `/api/analysis/song/<int:song_id>` | 2752 | GET | `song_analysis_data()` | Get song analysis data |
| `/comprehensive_reanalyze_all_user_songs/<int:user_id>` | 2916 | GET | `comprehensive_reanalyze_all_user_songs()` | Comprehensive reanalysis |

**Notes**: Large API section handling all analysis operations. Many duplicate routes for backward compatibility.

---

### 5. **WHITELIST/BLACKLIST API Blueprint** (18 routes)
**URL Prefix**: `/api/whitelist`
**Purpose**: Whitelist and blacklist management operations

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/whitelist_playlist/<string:playlist_id>` | 318 | POST | `whitelist_playlist()` | Add playlist to whitelist |
| `/blacklist_song/<string:playlist_id>/<string:track_id>` | 338 | POST | `blacklist_song()` | Add song to blacklist |
| `/blacklist_playlist/<string:playlist_id>` | 358 | POST | `blacklist_playlist()` | Add playlist to blacklist |
| `/whitelist_song/<string:playlist_id>/<string:track_id>` | 378 | POST | `whitelist_song()` | Add song to whitelist |
| `/remove_whitelist_playlist/<string:playlist_id>` | 776 | POST | `remove_whitelist_playlist()` | Remove playlist from whitelist |
| `/remove_blacklist_playlist/<string:playlist_id>` | 791 | POST | `remove_blacklist_playlist()` | Remove playlist from blacklist |
| `/remove_whitelist_song/<string:playlist_id>/<string:track_id>` | 806 | POST | `remove_whitelist_song()` | Remove song from whitelist |
| `/remove_blacklist_song/<string:playlist_id>/<string:track_id>` | 821 | POST | `remove_blacklist_song()` | Remove song from blacklist |
| `/api/song/<int:song_db_id>/whitelist` | 838 | POST | `api_whitelist_song()` | API: Add song to whitelist |
| `/api/song/<int:song_db_id>/blacklist` | 879 | POST | `api_blacklist_song()` | API: Add song to blacklist |
| `/add-whitelist-item` | 2134 | POST | `add_whitelist_item()` | Add whitelist item |
| `/add-blacklist-item` | 2198 | POST | `add_blacklist_item()` | Add blacklist item |
| `/remove-whitelist-item/<int:item_id>` | 2262 | POST | `remove_whitelist_item()` | Remove whitelist item |
| `/remove-blacklist-item/<int:item_id>` | 2290 | POST | `remove_blacklist_item()` | Remove blacklist item |
| `/edit-whitelist-item/<int:item_id>` | 2318 | POST | `edit_whitelist_item()` | Edit whitelist item |
| `/edit-blacklist-item/<int:item_id>` | 2353 | POST | `edit_blacklist_item()` | Edit blacklist item |
| `/export-whitelist` | 2388 | GET | `export_whitelist()` | Export whitelist |
| `/export-blacklist` | 2430 | GET | `export_blacklist()` | Export blacklist |
| `/bulk-import-whitelist` | 2472 | POST | `bulk_import_whitelist()` | Bulk import whitelist |
| `/bulk-import-blacklist` | 2560 | POST | `bulk_import_blacklist()` | Bulk import blacklist |

**Notes**: Large collection of list management routes. Some overlap between different URL patterns.

---

### 6. **USER/SETTINGS Blueprint** (3 routes)
**URL Prefix**: `/user`
**Purpose**: User settings and profile management

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/settings` | 1949 | GET | `user_settings()` | View user settings |
| `/settings` | 1981 | POST | `update_user_settings()` | Update user settings |
| `/blacklist-whitelist` | 2119 | GET | `blacklist_whitelist()` | Whitelist/blacklist management page |

**Notes**: User-specific settings and preferences management.

---

### 7. **ADMIN Blueprint** (3 routes)
**URL Prefix**: `/admin`
**Purpose**: Administrative functions and operations

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/admin/resync-all-playlists` | 2014 | POST | `admin_resync_all_playlists()` | Admin: Resync all playlists |
| `/admin/reanalyze-all-songs` | 2050 | POST | `admin_reanalyze_all_songs()` | Admin: Reanalyze all songs |
| `/api/admin/reanalysis-status` | 2812 | GET | `get_admin_reanalysis_status()` | Admin: Get reanalysis status |

**Notes**: Administrative operations for system-wide actions.

---

### 8. **SYSTEM/UTILITY Blueprint** (4 routes)
**URL Prefix**: `/system` or `/api/system`
**Purpose**: System health, monitoring, and utility functions

| Route | Line | Method | Function | Purpose |
|-------|------|--------|----------|---------|
| `/api/sync-status` | 277 | GET | `api_sync_status()` | Get sync status |
| `/check_auth` | 299 | GET | `check_auth_status()` | Check authentication status |
| `/health` | 309 | GET | `health_check()` | Health check endpoint |
| `/monitoring` | 2966 | GET | `monitoring_dashboard()` | System monitoring dashboard |

**Notes**: System-level utilities, health checks, and monitoring.

---

## Blueprint Structure Recommendation

Based on the analysis, I recommend the following blueprint structure:

```
app/
├── blueprints/
│   ├── __init__.py
│   ├── core/                    # 4 routes - Dashboard and main entry points
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── playlist/                # 5 routes - Playlist management
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── song/                    # 3 routes - Song viewing
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── analysis/                # 14 routes - Analysis operations
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── whitelist/               # 18 routes - List management
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── user/                    # 3 routes - User settings
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── admin/                   # 3 routes - Admin functions
│   │   ├── __init__.py
│   │   └── routes.py
│   └── system/                  # 4 routes - System utilities
│       ├── __init__.py
│       └── routes.py
```

---

## Migration Priorities

### High Priority (Core Functionality)
1. **Core Blueprint** - Essential for app to function
2. **Playlist Blueprint** - Core feature
3. **Analysis Blueprint** - Core feature

### Medium Priority (Feature Areas)
4. **Whitelist Blueprint** - Important feature
5. **User Blueprint** - User management
6. **Song Blueprint** - Individual song management

### Low Priority (Administrative)
7. **Admin Blueprint** - Administrative functions
8. **System Blueprint** - Monitoring and utilities

---

## Shared Dependencies Analysis

### Common Imports Needed Across Blueprints:
- `flask_login` (login_required, current_user)
- `app.auth.decorators` (spotify_token_required)
- Database models (User, Song, Playlist, etc.)
- Service classes (SpotifyService, UnifiedAnalysisService, etc.)

### Functions That May Need to be Shared:
- `calculate_playlist_score()` (line 2648) - Used across playlist and analysis
- Helper functions for analysis operations
- Database utility functions

### URL Pattern Considerations:
- Many routes have duplicate patterns with/without trailing slashes
- Backward compatibility routes can be grouped together
- API routes should maintain consistent `/api/` prefix

---

## Next Steps

1. **Create Blueprint Directory Structure** (Subtask 34.2)
2. **Migrate Routes by Priority** (Subtask 34.3)
3. **Update URL References** (Subtask 34.4)
4. **Test and Validate** (Subtask 34.5)

---

**Analysis Complete**: Ready to proceed with blueprint creation and migration. 