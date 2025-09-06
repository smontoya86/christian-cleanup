# API Documentation

This document provides comprehensive details about all API endpoints for the Christian Music Curator application.

## Authentication

All API endpoints require the user to be authenticated via Flask-Login session cookies. Unauthorized requests will receive a `401 Unauthorized` response with a JSON body:

```json
{
  "error": "Unauthorized"
}
```

## Whitelist API

Base path: `/api/whitelist`

### Add/Update Whitelist Item

*   **Endpoint:** `POST /api/whitelist`
*   **Description:** Adds a new item (song, artist, or album) to the user's whitelist or updates the reason for an existing item. If the item currently exists on the user's blacklist, it will be moved to the whitelist.
*   **Request Body (JSON):**
    ```json
    {
      "spotify_id": "<spotify_item_id>",
      "item_type": "<song|artist|album>",
      "name": "<Optional: Item Name>",
      "reason": "<Optional: Reason for whitelisting>"
    }
    ```
*   **Success Responses:**
    *   `201 Created` (New item added):
        ```json
        {
          "message": "Item added to whitelist",
          "item": {
            "id": <entry_id>,
            "user_id": <user_id>,
            "spotify_id": "<spotify_item_id>",
            "item_type": "<item_type>",
            "name": "<name>",
            "reason": "<reason>",
            "added_date": "<iso_timestamp>"
          }
        }
        ```
    *   `200 OK` (Reason updated for existing item):
        ```json
        {
          "message": "Whitelist item reason updated",
          "item": { ... } // Updated item details
        }
        ```
    *   `200 OK` (Item moved from blacklist):
        ```json
        {
          "message": "Item moved from blacklist to whitelist",
          "item": { ... } // Whitelist item details
        }
        ```
*   **Error Responses:**
    *   `400 Bad Request` (Missing required fields):
        ```json
        {
          "error": "Missing required fields: spotify_id, item_type"
        }
        ```
    *   `400 Bad Request` (Invalid `item_type`):
        ```json
        {
          "error": "Invalid item_type. Must be song, artist, or album."
        }
        ```

### Get Whitelist Items

*   **Endpoint:** `GET /api/whitelist`
*   **Description:** Retrieves all items currently on the user's whitelist. Can be filtered by `item_type`.
*   **Query Parameters:**
    *   `type` (Optional): Filters results by item type (`song`, `artist`, or `album`).
*   **Success Response (`200 OK`):**
    ```json
    [
      {
        "id": <entry_id>,
        "user_id": <user_id>,
        "spotify_id": "<spotify_item_id>",
        "item_type": "<item_type>",
        "name": "<name>",
        "reason": "<reason>",
        "added_date": "<iso_timestamp>"
      },
      ...
    ]
    ```
    _(Returns an empty list `[]` if the whitelist is empty or no items match the filter.)_
*   **Error Responses:** None specific beyond Authentication.

### Remove Whitelist Item

*   **Endpoint:** `DELETE /api/whitelist/<int:entry_id>`
*   **Description:** Removes a specific item from the user's whitelist using its unique database ID (`entry_id`).
*   **URL Parameters:**
    *   `entry_id`: The database ID of the whitelist entry to remove.
*   **Success Response (`200 OK`):**
    ```json
    {
      "message": "Item successfully removed from whitelist."
    }
    ```
*   **Error Responses:**
    *   `404 Not Found` (Item doesn't exist or doesn't belong to the user):
        ```json
        {
          "error": "Whitelist entry not found."
        }
        ```

### Clear All Whitelist Items

*   **Endpoint:** `POST /api/whitelist/clear`
*   **Description:** Removes all items from the user's whitelist.
*   **Success Response (`200 OK`):**
    ```json
    {
      "success": true,
      "message": "Cleared 15 items from whitelist",
      "deleted_count": 15
    }
    ```

## Blacklist API

Base path: `/api/blacklist`

### Add/Update Blacklist Item

*   **Endpoint:** `POST /api/blacklist`
*   **Description:** Adds a new item to the user's blacklist or updates an existing item. If the item exists on the whitelist, it will be moved to the blacklist.
*   **Request Body (JSON):**
    ```json
    {
      "spotify_id": "<spotify_item_id>",
      "item_type": "<song|artist|album>",
      "name": "<Optional: Item Name>",
      "reason": "<Optional: Reason for blacklisting>"
    }
    ```
*   **Success Responses:**
    *   `201 Created` (New item added):
        ```json
        {
          "message": "Item added to blacklist",
          "item": {
            "id": <entry_id>,
            "user_id": <user_id>,
            "spotify_id": "<spotify_item_id>",
            "item_type": "<item_type>",
            "name": "<name>",
            "reason": "<reason>",
            "added_date": "<iso_timestamp>"
          }
        }
        ```
    *   `200 OK` (Item moved from whitelist):
        ```json
        {
          "message": "Item moved from whitelist to blacklist",
          "item": { ... }
        }
        ```

### Get Blacklist Items

*   **Endpoint:** `GET /api/blacklist`
*   **Description:** Retrieves all items currently on the user's blacklist.
*   **Query Parameters:**
    *   `type` (Optional): Filters results by item type (`song`, `artist`, or `album`).
*   **Success Response (`200 OK`):**
    ```json
    [
      {
        "id": <entry_id>,
        "user_id": <user_id>,
        "spotify_id": "<spotify_item_id>",
        "item_type": "<item_type>",
        "name": "<name>",
        "reason": "<reason>",
        "added_date": "<iso_timestamp>"
      },
      ...
    ]
    ```

### Remove Blacklist Item

*   **Endpoint:** `DELETE /api/blacklist/<int:entry_id>`
*   **Description:** Removes a specific item from the user's blacklist.
*   **Success Response (`200 OK`):**
    ```json
    {
      "success": true,
      "message": "Removed 'Song Name' from blacklist",
      "item": {
        "name": "Song Name",
        "type": "song",
        "artist": "Artist Name"
      }
    }
    ```

### Clear All Blacklist Items

*   **Endpoint:** `POST /api/blacklist/clear`
*   **Description:** Removes all items from the user's blacklist.
*   **Success Response (`200 OK`):**
    ```json
    {
      "success": true,
      "message": "Cleared 8 items from blacklist",
      "deleted_count": 8
    }
    ```

## Analysis API

Base path: `/api`

### Get Song Analysis Status

*   **Endpoint:** `GET /api/songs/<int:song_id>/analysis-status`
*   **Description:** Retrieves the current analysis status for a specific song.
*   **Success Response (`200 OK`):**
    ```json
    {
      "song_id": 123,
      "analysis_status": "completed",
      "last_analyzed": "2024-12-01T10:30:00Z",
      "score": 85,
      "concern_level": "low",
      "has_concerns": false
    }
    ```

### Analyze Single Song

*   **Endpoint:** `POST /api/songs/<int:song_id>/analyze`
*   **Description:** Performs analysis immediately using the simplified local analyzer.
*   **Success Response (`200 OK`):**
```json
{
  "success": true,
  "status": "success",
  "message": "Analysis completed using local models",
  "song_id": 123,
  "analysis_id": 456
}
```
*   **Error Responses:**
*   *   `404 Not Found` - Song not found or access denied

### Reanalyze Single Song

*   **Endpoint:** `POST /api/songs/<int:song_id>/reanalyze`
*   **Description:** Forces re-analysis of a song that has already been analyzed.
*   **Success Response (`202 Accepted`):**
```json
{
  "success": true,
  "message": "Song reanalysis started",
  "song_id": 123,
  "job_id": "def456ghi789"
}
```

### Get Playlist Analysis Status

*   **Endpoint:** `GET /api/playlists/<playlist_id>/analysis-status`
*   **Description:** Retrieves analysis status summary for all songs in a playlist.
*   **Success Response (`200 OK`):
```json
{
  "playlist_id": "spotify_playlist_id",
  "total_songs": 25,
  "analyzed_songs": 23,
  "pending_songs": 2,
  "failed_songs": 0,
  "analysis_progress": 92.0,
  "last_updated": "2024-12-01T10:30:00Z"
}
```

### Analyze Unanalyzed Playlist Songs

*   **Endpoint:** `POST /api/playlists/<playlist_id>/analyze-unanalyzed`
*   **Description:** Analyzes all songs in a playlist that do not yet have a completed analysis.
*   **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Analyzed 5 songs",
  "playlist_id": 12,
  "analyzed_count": 5,
  "errors": []
}
```

### Get Analysis Data

*   **Endpoint:** `GET /api/analysis/song/<int:song_id>`
*   **Description:** Retrieves detailed analysis results for a song.
*   **Success Response (`200 OK`):**
    ```json
    {
      "song_id": 123,
      "analysis_result": {
        "score": 85,
        "concern_level": "low",
        "concerns": [],
        "biblical_themes": ["faith", "hope"],
        "content_warnings": [],
        "analyzed_at": "2024-12-01T10:30:00Z",
        "analysis_version": "2.1"
      }
    }
    ```

## Playlist Management API

Base path: `/playlist`

### Update Playlist Tracks and Sync to Spotify

*   **Endpoint:** `POST /playlist/<playlist_id>/update`
*   **Description:** Updates the tracks in a specified local playlist and attempts to synchronize these changes with the corresponding playlist on Spotify. This operation uses Spotify's `snapshot_id` to detect and prevent conflicts if the playlist has been modified on Spotify since the user last loaded it.
*   **URL Parameters:**
    *   `playlist_id`: The Spotify ID of the playlist to update.
*   **Request Body (JSON):**
    ```json
    {
      "track_uris": ["spotify:track:newtrack1", "spotify:track:newtrack2", ...],
      "expected_snapshot_id": "<snapshot_id_from_last_playlist_load>"
    }
    ```
    *   `track_uris`: An ordered list of Spotify track URIs that should replace the current tracks in the playlist.
    *   `expected_snapshot_id`: The `snapshot_id` of the playlist that the client expects. This is used for conflict detection.

*   **Success Response (`200 OK`):**
    *   Returned when the playlist is successfully updated locally and synced with Spotify without conflicts.
    ```json
    {
      "success": true,
      "message": "Playlist updated and synced with Spotify successfully!"
    }
    ```

*   **Conflict Response (`409 Conflict`):**
    *   Returned if the `expected_snapshot_id` does not match the current `snapshot_id` on Spotify, indicating the playlist was modified externally.
    ```json
    {
      "success": false,
      "message": "Playlist has been updated on Spotify since you loaded it. Please refresh and try again."
    }
    ```

*   **Error Responses:**
    *   `400 Bad Request` (e.g., missing `track_uris` or `expected_snapshot_id`):
        ```json
        {
          "success": false,
          "message": "Missing required fields: track_uris, expected_snapshot_id"
        }
        ```
    *   `401 Unauthorized`: If the user is not authenticated.
        ```json
        {
          "error": "Unauthorized"
        }
        ```
    *   `403 Forbidden`: If the authenticated user does not own the specified playlist or if their Spotify token is invalid/missing required scopes.
        ```json
        {
          "success": false,
          "message": "You do not have permission to modify this playlist or your Spotify token is invalid."
        }
        ```
    *   `404 Not Found`: If the playlist with the given `playlist_id` does not exist locally.
        ```json
        {
          "success": false,
          "message": "Playlist not found."
        }
        ```
    *   `500 Internal Server Error`: For unexpected errors during the process.
        ```json
        {
          "success": false,
          "message": "An unexpected error occurred while updating the playlist."
        }
        ```

### Sync Playlists with Spotify

*   **Endpoint:** `POST /sync-playlists`
*   **Description:** Synchronizes all user playlists with Spotify, importing new playlists and updating existing ones.
*   **Success Response (`200 OK`):**
    ```json
    {
      "success": true,
      "message": "Playlists synchronized successfully",
      "stats": {
        "total_playlists": 15,
        "new_playlists": 2,
        "updated_playlists": 3,
        "total_songs": 432,
        "new_songs": 25
      }
    }
    ```

### Analyze Playlist

*   **Endpoint:** `POST /analyze_playlist_api/<playlist_id>`
*   **Description:** Initiates content analysis for all songs in a playlist.
*   **Success Response (`202 Accepted`):**
    ```json
    {
      "success": true,
      "message": "Playlist analysis started",
      "playlist_id": "spotify_playlist_id",
      "total_songs": 20,
      "job_id": "playlist_analysis_abc123"
    }
    ```

## System Status API

### Sync Status

*   **Endpoint:** `GET /api/sync-status`
*   **Description:** Returns the current synchronization status with Spotify.
*   **Success Response (`200 OK`):**
    ```json
    {
      "is_syncing": false,
      "last_sync": "2024-12-01T10:15:30Z",
      "sync_status": "completed",
      "pending_jobs": 0,
      "failed_jobs": 0
    }
    ```

### Health Check

*   **Endpoint:** `GET /health`
*   **Description:** Basic health check endpoint for monitoring.
*   **Success Response (`200 OK`):**
    ```json
    {
      "status": "UP",
      "message": "Application is healthy.",
      "timestamp": "2024-12-01T10:30:00Z"
    }
    ```

### Authentication Status

*   **Endpoint:** `GET /check_auth`
*   **Description:** Checks if the current user is authenticated and has valid tokens.
*   **Success Response (`200 OK`):**
    ```json
    {
      "authenticated": true,
      "user_id": 123,
      "spotify_connected": true,
      "token_valid": true,
      "expires_at": "2024-12-01T11:30:00Z"
    }
    ```

## Administrative API

### Admin Resync All Playlists

*   **Endpoint:** `POST /admin/resync-all-playlists`
*   **Description:** Admin endpoint to force resynchronization of all playlists for the current user.
*   **Authentication:** Admin required
*   **Success Response (`200 OK`):**
    ```json
    {
      "success": true,
      "message": "All playlists resync initiated",
      "job_id": "admin_resync_xyz789"
    }
    ```

### Admin Reanalyze All Songs

*   **Endpoint:** `POST /admin/reanalyze-all-songs`
*   **Description:** Admin endpoint to force reanalysis of all songs for the current user.
*   **Authentication:** Admin required
*   **Success Response (`202 Accepted`):**
    ```json
    {
      "success": true,
      "message": "All songs reanalysis initiated",
      "total_songs": 1250,
      "job_id": "admin_reanalysis_abc456"
    }
    ```

### Admin Reanalysis Status

*   **Endpoint:** `GET /api/admin/reanalysis-status`
*   **Description:** Check the status of admin-initiated reanalysis operations.
*   **Authentication:** Admin required
*   **Success Response (`200 OK`):**
    ```json
    {
      "reanalysis_active": true,
      "total_songs": 1250,
      "completed_songs": 856,
      "failed_songs": 12,
      "progress_percentage": 68.5,
      "started_at": "2024-12-01T09:00:00Z",
      "estimated_completion": "2024-12-01T12:30:00Z"
    }
    ```

## Error Responses

### Common Error Formats

All API endpoints follow consistent error response patterns:

#### Authentication Error
```json
{
  "error": "Unauthorized",
  "message": "Authentication required"
}
```

#### Validation Error
```json
{
  "error": "Validation failed",
  "details": {
    "field_name": ["Field is required", "Field must be valid"]
  }
}
```

#### Resource Not Found
```json
{
  "error": "Resource not found",
  "message": "The requested resource could not be found"
}
```

#### Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred",
  "error_id": "error_uuid_12345"
}
```

### HTTP Status Codes

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **202 Accepted** - Request accepted for processing
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **409 Conflict** - Resource conflict
- **422 Unprocessable Entity** - Validation failed
- **500 Internal Server Error** - Server error

## Rate Limiting

All API endpoints are subject to rate limiting to ensure fair usage:

- **Authenticated users**: 1000 requests per hour
- **Analysis endpoints**: 100 requests per hour (due to processing intensity)
- **Admin endpoints**: 500 requests per hour

When rate limits are exceeded, the API returns:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 3600
}
```

## Pagination

List endpoints support pagination using query parameters:

- `page` - Page number (1-based, default: 1)
- `per_page` - Items per page (default: 20, max: 100)

Paginated responses include metadata:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

**Note**: This API documentation reflects the current blueprint architecture. All endpoints have been migrated to the new blueprint structure while maintaining backward compatibility.
