import pytest
from unittest.mock import MagicMock 
from datetime import datetime
from dateutil import parser
import spotipy # For SpotifyException
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
import logging

from app.models import User, Playlist, Song, PlaylistSong, db
from app.services.list_management_service import ListManagementService
from app.services.spotify_service import SpotifyService


@pytest.mark.usefixtures("app") 
class TestSyncPlaylistFromSpotifyToDb: 
    def test_sync_playlist_from_spotify_to_db_success(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        MockSpotipy = mocker.patch('app.services.list_management_service.spotipy.Spotify')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            # Set caplog level early to capture INFO logs from the service call
            caplog.set_level(logging.INFO)
            list_service = ListManagementService(spotify_service=mock_spotify_service)

            mock_user = mocker.MagicMock(spec=User)
            mock_user.id = 1
            mock_user.access_token = 'test_access_token'
            mock_user.ensure_token_valid.return_value = True

            mock_playlist = mocker.MagicMock(spec=Playlist)
            mock_playlist.id = 101
            mock_playlist.spotify_id = 'spotify_playlist_123'
            mock_playlist.owner_id = mock_user.id
            mock_playlist.spotify_snapshot_id = 'old_snapshot_id'
            mock_playlist.last_synced_from_spotify = parser.parse("2023-01-01T00:00:00Z")
            mock_playlist.updated_at = parser.parse("2023-01-01T00:00:00Z")

            mock_db_session.get.return_value = mock_playlist

            # This is the service call that fetches playlist details including snapshot_id
            mock_spotify_service.get_playlist_details.return_value = {'snapshot_id': 'new_snapshot_id'}

            mock_sp_instance = MockSpotipy.return_value
            mock_sp_instance.playlist_items.side_effect = [
                {'items': [
                    {'track': {'uri': 'spotify:track:uri1', 'id': 'id1', 'name': 'Song 1', 'artists': [{'name': 'Artist 1'}], 'album': {'name': 'Album 1'}}, 'added_at': '2023-10-26T10:00:00Z', 'added_by': {'id': 'user1'}, 'is_local': False},
                    {'track': {'uri': 'spotify:track:uri2', 'id': 'id2', 'name': 'Song 2', 'artists': [{'name': 'Artist 2'}], 'album': {'name': 'Album 2'}}, 'added_at': '2023-10-26T10:01:00Z', 'added_by': {'id': 'user2'}, 'is_local': False}
                ], 'next': 'some_next_url', 'limit': 2, 'offset': 0, 'total': 4},
                {'items': [
                    {'track': {'uri': 'spotify:track:uri3', 'id': 'id3', 'name': 'Song 3', 'artists': [{'name': 'Artist 3'}], 'album': {'name': 'Album 3'}}, 'added_at': '2023-10-26T10:02:00Z', 'added_by': {'id': 'user3'}, 'is_local': False},
                    {'track': {'uri': 'spotify:track:uri4', 'id': 'id4', 'name': 'Song 4', 'artists': [{'name': 'Artist 4'}], 'album': {'name': 'Album 4'}}, 'added_at': '2023-10-26T10:03:00Z', 'added_by': {'id': 'user4'}, 'is_local': False}
                ], 'next': None, 'limit': 2, 'offset': 2, 'total': 4}
            ]

            mock_song1 = mocker.MagicMock(spec=Song, id=1, spotify_id='id1')
            mock_song2 = mocker.MagicMock(spec=Song, id=2, spotify_id='id2')
            mock_song3 = mocker.MagicMock(spec=Song, id=3, spotify_id='id3')
            mock_song4 = mocker.MagicMock(spec=Song, id=4, spotify_id='id4')
            
            list_service._ensure_songs_exist_in_db = mocker.MagicMock(return_value={
                'uri1': mock_song1,
                'uri2': mock_song2,
                'uri3': mock_song3,
                'uri4': mock_song4
            })
            list_service._extract_spotify_track_id = mocker.MagicMock(side_effect=lambda x: x.split(':')[-1])

            mock_base_ps_query = mocker.MagicMock()  # Represents PlaylistSong.query property's return value
            mock_filtered_ps_query = mocker.MagicMock() # Represents result of .filter_by()
            # The .delete() method itself will be a mock on mock_filtered_ps_query

            # Patch where PlaylistSong is used in list_management_service
            # PlaylistSong is imported from app.models, so its .query attribute is accessed via that import path
            mocker.patch('app.services.list_management_service.PlaylistSong.query', 
                         new_callable=mocker.PropertyMock, 
                         return_value=mock_base_ps_query)
            mock_base_ps_query.filter_by.return_value = mock_filtered_ps_query
            # Configure the .delete() method on the mock_filtered_ps_query object
            # Simulate that delete() returns the number of rows deleted, e.g., 4
            mock_filtered_ps_query.delete = mocker.MagicMock(return_value=4) 

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is True
            assert message == f"Playlist {mock_playlist.id} synced successfully from Spotify."
            assert status_code == 200

            mock_user.ensure_token_valid.assert_called_once()
            MockSpotipy.assert_called_once_with(auth=mock_user.access_token)
            
            assert mock_sp_instance.playlist_items.call_count == 2
            mock_sp_instance.playlist_items.assert_any_call(mock_playlist.spotify_id, fields=mocker.ANY, limit=100, offset=0)
            mock_sp_instance.playlist_items.assert_any_call(mock_playlist.spotify_id, fields=mocker.ANY, limit=100, offset=100)

            list_service._ensure_songs_exist_in_db.assert_called_once_with(mock_user, ['spotify:track:uri1', 'spotify:track:uri2', 'spotify:track:uri3', 'spotify:track:uri4'])
            extract_calls = [
                mocker.call('spotify:track:uri1'),
                mocker.call('spotify:track:uri2'),
                mocker.call('spotify:track:uri3'),
                mocker.call('spotify:track:uri4')
            ]
            list_service._extract_spotify_track_id.assert_has_calls(extract_calls, any_order=True)

            mock_base_ps_query.filter_by.assert_called_once_with(playlist_id=mock_playlist.id)
            mock_filtered_ps_query.delete.assert_called_once()

            assert mock_db_session.add_all.call_count == 1
            added_songs_args = mock_db_session.add_all.call_args[0][0]
            assert len(added_songs_args) == 4

            # Ensure INFO logs are captured and check for the specific log record
            expected_log_message = f"Successfully synced playlist {mock_playlist.id} from Spotify."
            log_found = False
            for record in caplog.records:
                if record.levelname == 'INFO' and expected_log_message in record.message:
                    log_found = True
                    break
            assert log_found, f"Expected INFO log message '{expected_log_message}' not found. Logs: {caplog.text}"

            assert mock_playlist.spotify_snapshot_id == 'new_snapshot_id'
            assert isinstance(mock_playlist.last_synced_from_spotify, datetime)
            assert isinstance(mock_playlist.updated_at, datetime)
            mock_db_session.commit.assert_called_once()

    def test_sync_playlist_from_spotify_to_db_playlist_not_found(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1)
            mock_db_session.get.return_value = None

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 999)

            assert success is False
            assert message == "Local playlist not found."
            assert status_code == 404
            mock_db_session.get.assert_called_once_with(Playlist, 999)
            assert "Attempt to sync non-existent local playlist with ID 999" in caplog.text
            assert any(record.levelname == 'WARNING' for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_permission_denied(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1)
            mock_playlist = mocker.MagicMock(spec=Playlist, id=101, owner_id=2) 
            mock_db_session.get.return_value = mock_playlist

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "You do not have permission to sync this playlist."
            assert status_code == 403
            assert f"User {mock_user.id} attempted to sync playlist 101 owned by 2." in caplog.text
            assert any(record.levelname == 'WARNING' for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_spotify_details_fetch_failure(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1)
            mock_playlist = mocker.MagicMock(spec=Playlist, id=101, owner_id=1, spotify_id='sp_id')
            mock_db_session.get.return_value = mock_playlist
            mock_spotify_service.get_playlist_details.return_value = None 

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "Failed to fetch playlist details from Spotify."
            assert status_code == 500
            assert f"Could not fetch details for Spotify playlist {mock_playlist.spotify_id} during sync." in caplog.text
            assert any(record.levelname == 'ERROR' for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_spotify_items_fetch_failure(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        MockSpotipy = mocker.patch('app.services.list_management_service.spotipy.Spotify')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1, access_token='token')
            mock_user.ensure_token_valid.return_value = True
            mock_playlist = mocker.MagicMock(spec=Playlist, id=101, owner_id=1, spotify_id='sp_id')
            mock_db_session.get.return_value = mock_playlist
            mock_spotify_service.get_playlist_details.return_value = {'snapshot_id': 'snap_id'}
            
            mock_sp_instance = MockSpotipy.return_value
            mock_sp_instance.playlist_items.side_effect = spotipy.SpotifyException(400, -1, "Spotify error")

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "Failed to fetch tracks from Spotify."
            assert status_code == 500
            assert any(record.levelname == 'ERROR' and "Spotify API error fetching items for playlist" in record.message for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_ensure_songs_failure(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        MockSpotipy = mocker.patch('app.services.list_management_service.spotipy.Spotify')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1, access_token='token')
            mock_user.ensure_token_valid.return_value = True
            mock_playlist = mocker.MagicMock(spec=Playlist, id=101, owner_id=1, spotify_id='sp_id')
            mock_db_session.get.return_value = mock_playlist
            mock_spotify_service.get_playlist_details.return_value = {'snapshot_id': 'snap_id'}

            mock_sp_instance = MockSpotipy.return_value
            mock_sp_instance.playlist_items.return_value = {'items': [{'track': {'uri': 'spotify:track:uri1'}, 'is_local': False}], 'next': None}

            list_service._ensure_songs_exist_in_db = mocker.MagicMock(return_value={}) 
            list_service._extract_spotify_track_id = mocker.MagicMock(return_value='uri1')

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "Failed to process song details for the local database."
            assert status_code == 500
            assert f"Failed to ensure songs in DB for playlist {mock_playlist.id} during Spotify sync. song_map is empty but URIs were provided." in caplog.text
            assert any(record.levelname == 'ERROR' for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_db_error_on_commit(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        MockSpotipy = mocker.patch('app.services.list_management_service.spotipy.Spotify')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)
            mock_user = mocker.MagicMock(spec=User, id=1, access_token='token')
            mock_user.ensure_token_valid.return_value = True
            mock_playlist = mocker.MagicMock(spec=Playlist, id=101, owner_id=1, spotify_id='sp_id')
            mock_db_session.get.return_value = mock_playlist
            mock_spotify_service.get_playlist_details.return_value = {'snapshot_id': 'snap_id'}

            mock_sp_instance = MockSpotipy.return_value
            mock_sp_instance.playlist_items.return_value = {'items': [], 'next': None}

            list_service._ensure_songs_exist_in_db = mocker.MagicMock(return_value={})
            
            mock_db_session.commit.side_effect = SQLAlchemyError("DB commit failed")

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "Database error during synchronization."
            assert status_code == 500
            mock_db_session.rollback.assert_called_once()
            assert any(record.levelname == 'ERROR' and "Database error during Spotify sync for playlist" in record.message and record.exc_info for record in caplog.records)

    def test_sync_playlist_from_spotify_to_db_token_invalid(self, mocker, caplog): 
        mock_db_session = mocker.patch('app.services.list_management_service.db.session')
        MockSpotipy = mocker.patch('app.services.list_management_service.spotipy.Spotify')
        mock_spotify_service = mocker.MagicMock(spec=SpotifyService)

        with current_app.app_context():
            list_service = ListManagementService(spotify_service=mock_spotify_service)

            mock_user = mocker.MagicMock(spec=User)
            mock_user.id = 1
            mock_user.ensure_token_valid.return_value = False 

            mock_playlist = mocker.MagicMock(spec=Playlist)
            mock_playlist.id = 101
            mock_playlist.spotify_id = 'spotify_playlist_123'
            mock_playlist.owner_id = mock_user.id
            mock_db_session.get.return_value = mock_playlist

            success, message, status_code = list_service.sync_playlist_from_spotify_to_db(mock_user, 101)

            assert success is False
            assert message == "Spotify token error."
            assert status_code == 401
            mock_user.ensure_token_valid.assert_called_once()
            assert f"Spotify token for user {mock_user.id} is invalid or could not be refreshed for sync." in caplog.text
            assert any(record.levelname == 'ERROR' for record in caplog.records)
            MockSpotipy.assert_not_called()
