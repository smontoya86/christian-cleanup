from flask import current_app
from .models import User # Assuming User model is in models
from .services.playlist_sync_service import enqueue_playlist_sync, get_sync_status # Use modern playlist sync


def sync_all_playlists_job():
    """Scheduled job to sync playlists for all users using modern playlist sync service."""
    app = current_app._get_current_object() # Get the actual Flask app instance
    with app.app_context():
        # Import db and models *inside* the app context
        from .extensions import db
        from .models import User
        
        current_app.logger.info("Starting scheduled playlist sync job (refactored).")
        # Use modern SQLAlchemy query style with the session
        users = db.session.execute(db.select(User)).scalars().all()
        if not users:
            current_app.logger.info("No users found to sync.")
            return

        enqueued_count = 0
        failed_count = 0

        for user in users:
            current_app.logger.debug(f"Processing playlist sync for user {user.id} ({user.spotify_id})...")
            try:
                # Ensure the user's token is likely valid before attempting sync
                if not user.access_token or user.is_token_expired: 
                    current_app.logger.warning(f"Skipping sync for user {user.id}: Missing or expired token.")
                    failed_count += 1
                    continue

                # Check if sync is already in progress for this user
                sync_status = get_sync_status(user.id)
                if sync_status.get('status') == 'in_progress':
                    current_app.logger.info(f"Sync already in progress for user {user.id}, skipping.")
                    continue

                # Enqueue playlist sync job using modern service
                job = enqueue_playlist_sync(user.id)
                if job:
                    current_app.logger.info(f"Successfully enqueued playlist sync for user {user.id}, job ID: {job.id}")
                    enqueued_count += 1
                else:
                    # Failed to enqueue
                    current_app.logger.warning(f"Failed to enqueue playlist sync for user {user.id}")
                    failed_count += 1

            except Exception as e:
                current_app.logger.error(f"Error processing playlist sync for user {user.id}: {e}", exc_info=True)
                failed_count += 1

        current_app.logger.info(f"Scheduled playlist sync job finished. Enqueued: {enqueued_count}, Failed/Skipped: {failed_count}")
