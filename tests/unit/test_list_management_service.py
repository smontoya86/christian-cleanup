import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

from flask import Flask, current_app, flash
from app import db, create_app
from app.models import User, Playlist, Song, PlaylistSong
from app.services.spotify_service import SpotifyService
from app.services.list_management_service import ListManagementService
from app.extensions import scheduler

# Helper function to create a test user
def create_test_user(spotify_id='testuser', email='test@example.com'):
    user = User(
        spotify_id=spotify_id,
        email=email,
        access_token='test_access_token',
        refresh_token='test_refresh_token',
        token_expiry=datetime.utcnow() + timedelta(hours=1)
    )
    db.session.add(user)
    db.session.commit()
    return user

# Helper function to create a test playlist
def create_test_playlist(user, spotify_id='testplaylist123', name='Test Playlist', snapshot_id='initialsnapshot'):
    """Helper function to create a Playlist instance for testing."""
    playlist = Playlist(
        spotify_id=spotify_id,
        name=name,
        description='A test playlist',
        owner=user, # Assign the user object to the 'owner' relationship
        spotify_snapshot_id=snapshot_id
    )
    db.session.add(playlist)
    db.session.commit()
    return playlist

class TestListManagementService(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Mock SpotifyService for ListManagementService
        self.mock_spotify_service = MagicMock(spec=SpotifyService)
        
        # Configure a default return for get_playlist_details to avoid issues if called unexpectedly
        # Individual tests will override specific parts like 'snapshot_id' as needed.
        self.mock_spotify_service.get_playlist_details.return_value = MagicMock()
        self.mock_spotify_service.get_playlist_details.return_value.get.return_value = 'some_default_snapshot_id' # Default

        # Instantiate ListManagementService with the mocked SpotifyService
        # We can access the app.extensions version or instantiate directly for testing
        # For more isolated unit tests, direct instantiation with mock is often preferred.
        self.list_management_service = ListManagementService(spotify_service=self.mock_spotify_service)
        
        self.test_user = create_test_user()
        self.test_playlist = create_test_playlist(user=self.test_user) # Pass the user object

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app.extensions.get('scheduler') and self.app.extensions['scheduler'].running:
             self.app.extensions['scheduler'].shutdown(wait=False)
        self.app_context.pop()

    @patch('app.services.list_management_service.flash') # Mock flash to check calls
    def test_update_playlist_and_sync_success_new_and_existing_songs(self, mock_flash):
        # ---- ARRANGE ----
        # Existing song in DB
        existing_song_spotify_id = "existingSong123"
        existing_song = Song(
            title="Existing Song", 
            artist="Artist A", 
            spotify_id=existing_song_spotify_id,
            album="Album X"
        )
        db.session.add(existing_song)
        db.session.commit()

        # New track URIs for the playlist - one existing, one new
        new_song_spotify_uri = "spotify:track:newSong456"
        new_song_spotify_id = "newSong456"
        existing_song_spotify_uri = f"spotify:track:{existing_song_spotify_id}"
        
        new_track_uris_ordered = [new_song_spotify_uri, existing_song_spotify_uri]
        
        # Configure mock for snapshot_id check to pass
        expected_snapshot_id_for_test = "mock_snapshot_id_for_success_test"
        self.mock_spotify_service.get_playlist_details.return_value.get.side_effect = lambda key: \
            expected_snapshot_id_for_test if key == 'snapshot_id' else self.test_playlist.name if key == 'name' else None

        # Mock SpotifyService.replace_playlist_tracks
        new_spotify_snapshot_id = "new_spotify_snapshot_id_123"
        self.mock_spotify_service.replace_playlist_tracks.return_value = new_spotify_snapshot_id

        # Mock SpotifyService.get_multiple_track_details for the new song
        mock_new_song_details = [{
            'id': new_song_spotify_id,
            'name': 'New Awesome Song',
            'artists': [{'name': 'Artist B', 'id': 'artistB_id'}],
            'album': {'id': 'albumY_id', 'name': 'Album Y', 'images': [{'url': 'http://example.com/new_art.jpg'}]},
            'duration_ms': 200000
        }]
        self.mock_spotify_service.get_multiple_track_details.return_value = mock_new_song_details

        # ---- ACT ----
        result_tuple = self.list_management_service.update_playlist_and_sync_to_spotify(
            self.test_user, 
            self.test_playlist.id, 
            new_track_uris_ordered,
            expected_snapshot_id=expected_snapshot_id_for_test
        )

        # ---- ASSERT ----
        self.assertTrue(result_tuple[0], f"Service method should return True on success. Message: {result_tuple[1]}")

        # 1. Check SpotifyService calls
        self.mock_spotify_service.get_playlist_details.assert_called_once_with(self.test_user, self.test_playlist.spotify_id)
        self.mock_spotify_service.replace_playlist_tracks.assert_called_once_with(
            self.test_user, self.test_playlist.spotify_id, new_track_uris_ordered
        )
        self.mock_spotify_service.get_multiple_track_details.assert_called_once_with(
            self.test_user, [new_song_spotify_uri] 
        )

        # 2. Check new Song object creation
        created_song = Song.query.filter_by(spotify_id=new_song_spotify_id).first()
        self.assertIsNotNone(created_song, "New song should be created in the database.")
        self.assertEqual(created_song.title, 'New Awesome Song')
        self.assertEqual(created_song.artist, 'Artist B')

        # 3. Check PlaylistSong associations
        updated_playlist = db.session.get(Playlist, self.test_playlist.id)
        self.assertIsNotNone(updated_playlist)
        
        associations = PlaylistSong.query.filter_by(playlist_id=updated_playlist.id).order_by(PlaylistSong.track_position).all()
        self.assertEqual(len(associations), 2, "Playlist should have 2 tracks after update.")

        self.assertEqual(associations[0].song_id, created_song.id)
        self.assertEqual(associations[0].track_position, 0)
        
        self.assertEqual(associations[1].song_id, existing_song.id)
        self.assertEqual(associations[1].track_position, 1)

        # 4. Check Playlist's snapshot_id update
        self.assertEqual(updated_playlist.spotify_snapshot_id, new_spotify_snapshot_id)
        self.assertIsNotNone(updated_playlist.last_synced_from_spotify) # Should be set on successful sync
        self.assertIsNotNone(updated_playlist.updated_at) # Correct field name

        # 5. Check flash message (service should not flash, route should)
        mock_flash.assert_not_called()

    @patch('app.services.list_management_service.flash')
    def test_update_playlist_spotify_replace_fails(self, mock_flash):
        # ---- ARRANGE ----
        new_track_uris_ordered = ["spotify:track:newSong1", "spotify:track:newSong2"]
        expected_snapshot_id_for_test = "mock_snapshot_id_for_fail_test"

        # Configure mock for snapshot_id check to pass initially
        self.mock_spotify_service.get_playlist_details.return_value.get.side_effect = lambda key: \
            expected_snapshot_id_for_test if key == 'snapshot_id' else self.test_playlist.name if key == 'name' else None
        
        # Mock SpotifyService.replace_playlist_tracks to return None (failure)
        self.mock_spotify_service.replace_playlist_tracks.return_value = None

        # ---- ACT ----
        result_tuple = self.list_management_service.update_playlist_and_sync_to_spotify(
            self.test_user, self.test_playlist.id, new_track_uris_ordered,
            expected_snapshot_id=expected_snapshot_id_for_test
        )

        # ---- ASSERT ----
        self.assertFalse(result_tuple[0], "Service method should return False when Spotify replace fails.")

        # 1. Check SpotifyService calls
        self.mock_spotify_service.get_playlist_details.assert_called_once_with(self.test_user, self.test_playlist.spotify_id)
        self.mock_spotify_service.replace_playlist_tracks.assert_called_once_with(
            self.test_user, self.test_playlist.spotify_id, new_track_uris_ordered
        )
        self.mock_spotify_service.get_multiple_track_details.assert_not_called()

        # 2. Check Database state (should be unchanged)
        updated_playlist = db.session.get(Playlist, self.test_playlist.id)
        self.assertEqual(updated_playlist.spotify_snapshot_id, 'initialsnapshot', "Snapshot ID should not change.")
        associations = PlaylistSong.query.filter_by(playlist_id=updated_playlist.id).all()
        self.assertEqual(len(associations), 0, "PlaylistSong associations should not be created.")

        # 3. Check flash message
        mock_flash.assert_not_called() # Service should not call flash directly

    @patch('app.services.list_management_service.flash') # Keep patch if other parts of test use it, or remove if not needed
    def test_update_playlist_permission_denied(self, mock_flash):
        """Test that updating a playlist not owned by the user is denied."""
        # ---- ARRANGE ----
        other_user = User(id=99, spotify_id='otheruser', email='other@test.com') # Not self.test_user

        # self.test_playlist is owned by self.test_user (id=1)
        new_track_uris = ["spotify:track:irrelevant1"]
        snapshot_id = "irrelevant_snapshot"

        # The service method itself should check ownership and return an error tuple,
        # not directly call flash.

        # ---- ACT ----
        success, message, status_code = self.list_management_service.update_playlist_and_sync_to_spotify(
            other_user, self.test_playlist.id, new_track_uris, snapshot_id
        )

        # ---- ASSERT ----
        self.assertFalse(success, "Service should return False for permission denied.")
        self.assertEqual(message, "You do not have permission to modify this playlist.")
        self.assertEqual(status_code, 403, "Status code should be 403 for permission denied.")
        
        # Ensure flash was NOT called by the service
        mock_flash.assert_not_called()

        # Ensure token was checked for other_user, but other Spotify calls not made
        # Spotify service calls get_playlist_details which internally handles token validation.
        # If permission denied occurs first, get_playlist_details might not be called.
        # In this case, permission is checked before get_playlist_details, so no spotify calls.
        self.mock_spotify_service.get_playlist_details.assert_not_called()
        self.mock_spotify_service.replace_playlist_tracks.assert_not_called()

    @patch('app.services.list_management_service.flash')
    def test_update_playlist_snapshot_id_mismatch(self, mock_flash):
        # ---- ARRANGE ----
        new_track_uris_ordered = ["spotify:track:newSong1", "spotify:track:newSong2"]
        expected_snapshot_id_for_test = "mock_snapshot_id_for_mismatch_test"

        # Configure mock for snapshot_id check to fail
        self.mock_spotify_service.get_playlist_details.return_value.get.side_effect = lambda key: \
            'mismatched_snapshot_id' if key == 'snapshot_id' else self.test_playlist.name if key == 'name' else None

        # ---- ACT ----
        result_tuple = self.list_management_service.update_playlist_and_sync_to_spotify(
            self.test_user, self.test_playlist.id, new_track_uris_ordered,
            expected_snapshot_id=expected_snapshot_id_for_test
        )

        # ---- ASSERT ----
        self.assertFalse(result_tuple[0], "Service method should return False when snapshot IDs mismatch.")

        # 1. Check SpotifyService calls
        self.mock_spotify_service.get_playlist_details.assert_called_once_with(self.test_user, self.test_playlist.spotify_id)
        # replace_playlist_tracks should NOT be called if snapshot IDs mismatch
        self.mock_spotify_service.replace_playlist_tracks.assert_not_called()
        self.mock_spotify_service.get_multiple_track_details.assert_not_called()

        # 2. Check Database state (should be unchanged)
        updated_playlist = db.session.get(Playlist, self.test_playlist.id)
        self.assertEqual(updated_playlist.spotify_snapshot_id, 'initialsnapshot')
        associations = PlaylistSong.query.filter_by(playlist_id=updated_playlist.id).all()
        self.assertEqual(len(associations), 0)

        # 3. Check flash message
        mock_flash.assert_not_called() # Service should not call flash directly

    @patch('app.services.list_management_service.flash')
    def test_update_playlist_ensure_token_fails(self, mock_flash):
        # ---- ARRANGE ----
        new_track_uris_ordered = ["spotify:track:newSong1", "spotify:track:newSong2"]
        expected_snapshot_id_for_test = "mock_snapshot_id_for_ensure_token_fail_test"

        # Simulate SpotifyService.get_playlist_details failing (e.g., due to token issue)
        self.mock_spotify_service.get_playlist_details.return_value = None

        # ---- ACT ----
        success, message, status_code = self.list_management_service.update_playlist_and_sync_to_spotify(
            self.test_user, self.test_playlist.id, new_track_uris_ordered,
            expected_snapshot_id=expected_snapshot_id_for_test
        )

        # ---- ASSERT ----
        self.assertFalse(success, "Service should return False when get_playlist_details fails.")
        self.assertEqual(message, "Could not verify playlist status on Spotify. Update cancelled.")
        self.assertEqual(status_code, 500)

        # 1. Check SpotifyService calls
        self.mock_spotify_service.get_playlist_details.assert_called_once_with(self.test_user, self.test_playlist.spotify_id)
        # Other Spotify service methods should not be called if the first one fails
        self.mock_spotify_service.replace_playlist_tracks.assert_not_called()
        self.mock_spotify_service.get_multiple_track_details.assert_not_called()

        # 2. Check Database state (should be unchanged)
        updated_playlist_db = db.session.get(Playlist, self.test_playlist.id)
        self.assertEqual(updated_playlist_db.spotify_snapshot_id, 'initialsnapshot')
        associations = PlaylistSong.query.filter_by(playlist_id=updated_playlist_db.id).all()
        self.assertEqual(len(associations), 0)

        # 3. Service should not call flash directly
        mock_flash.assert_not_called()

if __name__ == '__main__':
    unittest.main()
