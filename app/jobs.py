from flask import current_app
from .models import User # Assuming User model is in models
from .services.spotify_service import SpotifyService # Assuming SpotifyService is importable
import spotipy


def sync_all_playlists_job():
    """Scheduled job to sync playlists for all users."""
    app = current_app._get_current_object() # Get the actual Flask app instance
    with app.app_context():
        # Import db and models *inside* the app context
        from .extensions import db
        from .models import User
        
        current_app.logger.info("Starting scheduled playlist sync job.")
        # Use modern SQLAlchemy query style with the session
        users = db.session.execute(db.select(User)).scalars().all()
        if not users:
            current_app.logger.info("No users found to sync.")
            return

        # Get the SpotifyService instance from the app context if possible
        # Or instantiate it if necessary (ensure configuration is available)
        spotify_service = current_app.extensions.get('spotify_service')
        if not spotify_service:
            # Fallback: Instantiate a new one - requires proper config access
            current_app.logger.warning("SpotifyService not found in app extensions, instantiating new one for job.")
            # Note: This instantiation might need adjustment if the service relies
            # on request-specific context or complex setup not available here.
            # It's generally better to ensure services are accessible via app context.
            spotify_service = SpotifyService(logger=current_app.logger)
            # TODO: Verify if this fallback instantiation works correctly in the job context.

        synced_count = 0
        failed_count = 0

        for user in users:
            current_app.logger.debug(f"Syncing playlists for user {user.id} ({user.spotify_id})...")
            try:
                # Ensure the user's token is likely valid before attempting sync
                # This might require adding a check here or ensuring sync_user_playlists_with_db handles it
                if not user.access_token or user.is_token_expired: 
                    current_app.logger.warning(f"Skipping sync for user {user.id}: Missing or expired token.")
                    failed_count += 1
                    continue

                # The sync function needs the user ID
                success = spotify_service.sync_user_playlists_with_db(user.id)
                if success:
                    current_app.logger.info(f"Successfully synced playlists for user {user.id}.")
                    synced_count += 1
                else:
                    # The function itself might log specifics, add a general failure log here
                    current_app.logger.warning(f"Sync failed for user {user.id} (check service logs for details).")
                    failed_count += 1

            except spotipy.SpotifyException as e:
                current_app.logger.error(f"Spotify API error during sync for user {user.id}: {e}")
                # Specific handling for auth errors might be needed if sync_user_playlists_with_db doesn't handle it
                if e.http_status == 401:
                    current_app.logger.warning(f"Spotify token expired for user {user.id}.")
                    # Optionally: Mark user token as invalid in DB
                failed_count += 1
            except Exception as e:
                current_app.logger.error(f"Unexpected error during sync for user {user.id}: {e}", exc_info=True)
                failed_count += 1

        current_app.logger.info(f"Scheduled playlist sync job finished. Synced: {synced_count}, Failed/Skipped: {failed_count}")
