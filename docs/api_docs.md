# API Documentation

This document provides details about the API endpoints for the Spotify Cleanup application.

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
        _(Note: Specific error message may vary based on the missing field.)_
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
    *   `500 Internal Server Error`: For unexpected errors during the process (e.g., issues communicating with the Spotify API not covered by specific conflict/auth errors).
        ```json
        {
          "success": false,
          "message": "An unexpected error occurred while updating the playlist."
        }
        ```
