from flask import render_template, jsonify, current_app, session, redirect, url_for, flash
from .models.models import Whitelist # Assuming models.py is in the same directory or app package
from . import db # Assuming db is initialized in __init__.py of the app package
from flask_login import login_required, current_user
import spotipy

def init_app(app):
    """Initialize main application routes and error handlers."""

    @app.route('/')
    def index():
        current_app.logger.info("Index route '/' accessed.")
        # Later this will render a proper template, e.g., index.html
        # return render_template('index.html', title='Home')
        return "Hello, Christian Music Alignment App! Welcome to the main page."

    @app.route('/health')
    def health_check():
        current_app.logger.info("Health check route '/health' accessed.")
        return jsonify(status="UP", message="Application is healthy."), 200

    @app.errorhandler(404)
    def not_found_error(error):
        current_app.logger.warning(f"404 Not Found error: {error}")
        # Later this can render a 404.html template
        # return render_template('404.html'), 404
        return jsonify(error={'message': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.error(f"500 Internal Server error: {error}")
        # db.session.rollback() # If using a database and an error occurs during a request
        # Later this can render a 500.html template
        # return render_template('500.html'), 500
        return jsonify(error={'message': 'Internal server error'}), 500

    # Placeholder for a function that would update a playlist's score
    # This would likely involve re-analyzing its tracks or averaging scores
    def update_playlist_score(playlist_id):
        current_app.logger.info(f"Placeholder: update_playlist_score called for playlist_id: {playlist_id}")
        # Actual implementation would go here, e.g.:
        # playlist_to_update = Playlist.query.get(playlist_id) # If you have a Playlist model with internal ID
        # if playlist_to_update:
        #     # Logic to recalculate and save the score
        #     pass
        pass

    @app.route('/whitelist_song/<playlist_id>/<track_id>')
    @login_required
    def whitelist_song(playlist_id, track_id):
        user_id = current_user.id
        
        existing_whitelist = Whitelist.query.filter_by(
            user_id=user_id,
            spotify_id=track_id,
            item_type='song'
        ).first()
        
        if not existing_whitelist:
            new_whitelist_entry = Whitelist(
                user_id=user_id,
                spotify_id=track_id,
                item_type='song'
            )
            db.session.add(new_whitelist_entry)
            db.session.commit()
            flash(f'Song {track_id} added to your whitelist.', 'success')
            current_app.logger.info(f"User {user_id} whitelisted song {track_id}.")
        else:
            flash(f'Song {track_id} is already in your whitelist.', 'info')
        
        # Assuming you have a route to view playlist details
        # If not, redirect to a more general page like dashboard
        # return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        return redirect(url_for('index')) # Redirecting to index for now

    @app.route('/remove_song/<playlist_id>/<track_id>')
    @login_required
    def remove_song(playlist_id, track_id):
        if not current_user.ensure_token_valid():
            flash('Your Spotify session has expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login')) # Assuming 'auth.login' is your login route

        sp = spotipy.Spotify(auth=current_user.access_token)
        
        try:
            user_spotify_id = sp.current_user()['id']
            playlist_info = sp.playlist(playlist_id, fields='owner.id')
            playlist_owner_id = playlist_info['owner']['id']
            
            if user_spotify_id == playlist_owner_id:
                sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
                update_playlist_score(playlist_id) # Call placeholder
                flash(f'Song {track_id} removed from playlist {playlist_id}.', 'success')
                current_app.logger.info(f"User {user_spotify_id} removed song {track_id} from playlist {playlist_id}.")
            else:
                flash('You can only remove songs from playlists you own.', 'danger')
                current_app.logger.warning(f"User {user_spotify_id} attempt to remove song from unowned playlist {playlist_id}.")
        except spotipy.SpotifyException as e:
            flash(f'Could not remove song from Spotify: {e}', 'danger')
            current_app.logger.error(f"Spotify API error for user {current_user.id} removing song: {e}")
        
        # return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        return redirect(url_for('index')) # Redirecting to index for now

    @app.route('/whitelist_playlist/<playlist_id>')
    @login_required
    def whitelist_playlist(playlist_id):
        user_id = current_user.id
        
        existing_whitelist = Whitelist.query.filter_by(
            user_id=user_id,
            spotify_id=playlist_id,
            item_type='playlist'
        ).first()
        
        if not existing_whitelist:
            new_whitelist_entry = Whitelist(
                user_id=user_id,
                spotify_id=playlist_id,
                item_type='playlist'
            )
            db.session.add(new_whitelist_entry)
            db.session.commit()
            flash(f'Playlist {playlist_id} added to your whitelist.', 'success')
            current_app.logger.info(f"User {user_id} whitelisted playlist {playlist_id}.")
        else:
            flash(f'Playlist {playlist_id} is already in your whitelist.', 'info')
        
        # return redirect(url_for('main.dashboard'))
        return redirect(url_for('index')) # Redirecting to index for now
    
    app.logger.info("Main routes (index, health) and error handlers (404, 500) registered in app/routes.py.")
    app.logger.info("Whitelist and song management routes registered.")
