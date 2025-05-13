import pytest
from unittest.mock import patch, MagicMock, call, ANY 
from datetime import datetime, timedelta, timezone
from dateutil import parser

from app import create_app, db
from app.models import User, Playlist, Song, PlaylistSong
from app.services.spotify_service import SpotifyService
from sqlalchemy.orm import scoped_session, sessionmaker
from app.extensions import scheduler # Import scheduler

# Sample Mock Data (will be expanded and moved to fixtures/test cases)
MOCK_USER_PLAYLISTS_PAGE_1 = {
    'items': [
        {
            'id': 'playlist_new_1',
            'name': 'New Playlist 1',
            'description': 'A new one',
            'snapshot_id': 'snapshot_new_1',
            'tracks': {'total': 2},
            'images': [{'url': 'http://example.com/new1.jpg'}]
        },
        {
            'id': 'playlist_existing_nochange_1',
            'name': 'Existing No Change',
            'description': 'Should not sync tracks',
            'snapshot_id': 'snapshot_existing_1_v1', # Matches DB
            'tracks': {'total': 1},
            'images': [{'url': 'http://example.com/existing_nochange.jpg'}]
        },
    ],
    'next': 'http://spotify.api/next_playlists_page' # Indicate pagination
}

MOCK_USER_PLAYLISTS_PAGE_2 = {
    'items': [
         {
            'id': 'playlist_existing_change_1',
            'name': 'Existing Changed',
            'description': 'Should sync tracks',
            'snapshot_id': 'snapshot_existing_2_v2', # Different from DB
            'tracks': {'total': 3},
            'images': [{'url': 'http://example.com/existing_change.jpg'}]
        }
    ],
    'next': None # Last page
}

MOCK_PLAYLIST_ITEMS_NEW_1 = {
    'items': [
        {'track': {'id': 'track_a', 'name': 'Song A', 'artists': [{'name': 'Artist X'}], 'album': {'name': 'Album P'}}, 'added_at': '2024-01-01T10:00:00Z', 'added_by': {'id': 'user_spotify_adder'}},
        {'track': {'id': 'track_b', 'name': 'Song B', 'artists': [{'name': 'Artist Y'}], 'album': {'name': 'Album Q'}}, 'added_at': '2024-01-02T11:00:00Z', 'added_by': {'id': 'user_spotify_adder'}},
    ],
    'next': None
}

MOCK_PLAYLIST_ITEMS_EXISTING_CHANGE_1 = {
     'items': [
        {'track': {'id': 'track_c', 'name': 'Song C Updated', 'artists': [{'name': 'Artist Z'}], 'album': {'name': 'Album R'}}, 'added_at': '2024-02-01T12:00:00Z', 'added_by': {'id': 'user_spotify_adder_2'}},
        {'track': {'id': 'track_d', 'name': 'Song D New', 'artists': [{'name': 'Artist W'}], 'album': {'name': 'Album S'}}, 'added_at': '2024-02-02T13:00:00Z', 'added_by': {'id': 'user_spotify_adder_2'}},
        {'track': {'id': 'track_e', 'name': 'Song E New', 'artists': [{'name': 'Artist V'}], 'album': {'name': 'Album T'}}, 'added_at': '2024-02-03T14:00:00Z', 'added_by': {'id': 'user_spotify_adder_2'}},
    ],
    'next': None
}


@pytest.fixture(scope='module')
def test_client():
    """Fixture to create a test client"""
    app = create_app(config_name='testing')
    testing_client = app.test_client()

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    # Ensure scheduler is shutdown if it was started and is running
    if app.extensions.get('scheduler') and app.extensions['scheduler'].running:
        app.extensions['scheduler'].shutdown(wait=False)
    ctx.pop()

@pytest.fixture(scope='function')
def init_database(app):
    """Sets up the database with initial data for Spotify service tests, ensuring isolation via transactions."""
    with app.app_context(): # Ensure operations happen within app context
        db.create_all() # Create tables BEFORE the transaction starts

    # Standard pattern for Flask-SQLAlchemy testing transaction isolation:
    connection = db.engine.connect()
    transaction = connection.begin()

    # Use sessionmaker and scoped_session from SQLAlchemy core
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    original_session = db.session # Store original session
    db.session = session # Monkeypatch the main session for the duration of the test

    try:
        # --- Create Initial Data within the transaction ---
        user = User(
            spotify_id='test_spotify_user',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            token_expiry=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(user)
        db.session.flush() # Get user ID

        # Existing playlist, no snapshot change expected initially
        playlist_nochange = Playlist(
            spotify_id='playlist_existing_nochange_1',
            name='Old Name No Change', # Initial name
            owner_id=user.id,
            spotify_snapshot_id='snapshot_existing_1_v1' # Initial snapshot
        )
        db.session.add(playlist_nochange)
        # Existing playlist, EXPECTED to change snapshot in tests
        playlist_change = Playlist(
            spotify_id='playlist_existing_change_1',
            name='Old Name Change', # Initial name
            owner_id=user.id,
            spotify_snapshot_id='snapshot_existing_2_v1' # Initial snapshot v1
        )
        db.session.add(playlist_change)
        db.session.flush() # Get playlist IDs

        # Add a song to the playlist that will change snapshot
        song_old = Song(spotify_id='track_old', title='Old Song', artist='Old Artist', album='Old Album')
        db.session.add(song_old)
        db.session.flush() # Get song ID

        assoc_old = PlaylistSong(
            playlist_id=playlist_change.id,
            song_id=song_old.id,
            track_position=0,
            added_at_spotify=parser.parse('2024-01-01T00:00:00Z').replace(tzinfo=timezone.utc),
            added_by_spotify_user_id='initial_user'
        )
        db.session.add(assoc_old)

        # Add a song to the playlist that won't change snapshot (to test track sync isn't run)
        song_nochange = Song(spotify_id='track_nochange', title='NoChange Song', artist='NoChange Artist', album='NoChange Album')
        db.session.add(song_nochange)
        db.session.flush() # Get song ID

        assoc_nochange = PlaylistSong(
            playlist_id=playlist_nochange.id,
            song_id=song_nochange.id,
            track_position=0,
            added_at_spotify=parser.parse('2024-01-01T01:00:00Z').replace(tzinfo=timezone.utc),
            added_by_spotify_user_id='initial_user_nc'
        )
        db.session.add(assoc_nochange)

        # Also add Whitelist/Blacklist entries if needed by tests involving them
        # Example:
        # whitelist_entry = Whitelist(user_id=user.id, spotify_id=playlist_nochange.spotify_id, item_type='playlist')
        # db.session.add(whitelist_entry)

        db.session.commit() # Commit initial state *within* the nested transaction

        yield db # Test runs using the nested session

    finally:
        # Teardown: Rollback the transaction, remove session, close connection
        db.session.remove() # Remove the scoped session
        transaction.rollback()
        connection.close()
        db.session = original_session # Restore original session
        with app.app_context():
            db.drop_all() # Drop tables AFTER the transaction cleanup


@pytest.fixture(scope='module')
def mock_spotify_client():
    """Fixture for a mock Spotipy client with predefined return values."""
    mock_client = MagicMock(spec=spotipy.Spotify)

    # Configure side effect for pagination (example)
    mock_client.current_user_playlists.side_effect = [
        # First call (offset=0, limit=50)
        {
            'items': [
                {'id': 'playlist_new_1', 'name': 'New Playlist 1', 'snapshot_id': 'snapshot_new_1', 'tracks': {'total': 2}, 'images': [{'url': 'http://image.url/new1'}]}, 
                {'id': 'playlist_existing_nochange_1', 'name': 'Existing No Change 1', 'snapshot_id': 'snapshot_existing_1_v1', 'tracks': {'total': 5}, 'images': []}
            ],
            'next': 'some_url_page_2', # Indicate more pages
            'limit': 50, 'offset': 0, 'total': 3 # Example total
        },
        # Second call (offset=50, limit=50)
        {
            'items': [
                {'id': 'playlist_existing_change_1', 'name': 'Existing Change 1 - Updated', 'snapshot_id': 'snapshot_existing_2_v2', 'tracks': {'total': 1}, 'images': [{'url': 'http://image.url/change1'}]}
            ],
            'next': None, # No more pages
            'limit': 50, 'offset': 50, 'total': 3
        }
        # Add more pages if needed for other tests
    ]

    mock_client.playlist_items.side_effect = lambda playlist_id, limit=100, offset=0, fields=None, additional_types=('track',): {
        'playlist_new_1': {
            'items': [
                {
                    'added_at': '2024-01-01T12:00:00Z',
                    'added_by': {'id': 'user_who_added'},
                    'track': {'id': 'track_new_1', 'name': 'New Song 1', 'artists': [{'name': 'Artist A'}], 'album': {'name': 'Album X'}, 'explicit': False}
                },
                 {
                    'added_at': '2024-01-02T13:00:00Z',
                    'added_by': {'id': 'user_who_added'},
                    'track': {'id': 'track_new_2', 'name': 'New Song 2', 'artists': [{'name': 'Artist B'}], 'album': {'name': 'Album Y'}, 'explicit': True}
                }
            ],
            'next': None, 'total': 2, 'limit': limit, 'offset': offset
        },
         'playlist_existing_change_1': {
             'items': [
                 {
                    'added_at': '2024-01-03T14:00:00Z',
                    'added_by': {'id': 'user_who_added_updated'},
                    'track': {'id': 'track_new_3', 'name': 'New Song 3', 'artists': [{'name': 'Artist C'}], 'album': {'name': 'Album Z'}, 'explicit': False}
                },
                # Note: Original 'track_old' is assumed removed/replaced in the new snapshot
             ],
            'next': None, 'total': 1, 'limit': limit, 'offset': offset
        }
        # Add other playlist IDs as needed
    }.get(playlist_id, {'items': [], 'next': None, 'total': 0, 'limit': limit, 'offset': offset}) # Default empty if ID not mocked

    return mock_client


class TestSpotifyServiceSync:

    # Patch the Spotify client where it's instantiated within the service
    @patch('app.services.spotify_service.spotipy.Spotify', autospec=True)
    def test_sync_new_playlist(self, mock_spotify_class, test_client, init_database):
        """Verify a new playlist and its tracks are added correctly."""
        # Get the mock instance that the service will create and use
        mock_instance = mock_spotify_class.return_value
        
        # Configure the mock instance with pagination/methods
        # --- Playlist Pagination Mocking ---
        mock_instance.current_user_playlists.side_effect = [
            # First call (offset=0, limit=50)
            {
                'items': [
                    {'id': 'playlist_new_1', 'name': 'New Playlist 1', 'snapshot_id': 'snapshot_new_1', 'tracks': {'total': 2}, 'images': [{'url': 'http://image.url/new1'}]}, 
                    {'id': 'playlist_existing_nochange_1', 'name': 'Existing No Change 1', 'snapshot_id': 'snapshot_existing_1_v1', 'tracks': {'total': 5}, 'images': []}
                ],
                'next': 'some_url_page_2', # Indicate more pages
                'limit': 50, 'offset': 0, 'total': 3 # Example total
            },
            # Second call (offset=50, limit=50)
            {
                'items': [
                    {'id': 'playlist_existing_change_1', 'name': 'Existing Change 1 - Updated', 'snapshot_id': 'snapshot_existing_2_v2', 'tracks': {'total': 1}, 'images': [{'url': 'http://image.url/change1'}]}
                ],
                'next': None, # No more pages
                'limit': 50, 'offset': 50, 'total': 3
            }
        ]
        
        # --- Track Mocking --- 
        mock_instance.playlist_items.side_effect = lambda playlist_id, limit=100, offset=0, fields=None, additional_types=('track',): {
            'playlist_new_1': {
                'items': [
                    {
                        'added_at': '2024-01-01T12:00:00Z',
                        'added_by': {'id': 'user_who_added'},
                        'track': {'id': 'track_new_1', 'name': 'New Song 1', 'artists': [{'name': 'Artist A'}], 'album': {'name': 'Album X'}, 'explicit': False}
                    },
                    {
                        'added_at': '2024-01-02T13:00:00Z',
                        'added_by': {'id': 'user_who_added'},
                        'track': {'id': 'track_new_2', 'name': 'New Song 2', 'artists': [{'name': 'Artist B'}], 'album': {'name': 'Album Y'}, 'explicit': True}
                    }
                ],
                'next': None, 'total': 2, 'limit': limit, 'offset': offset
            },
             'playlist_existing_change_1': {
                 'items': [
                     {
                        'added_at': '2024-01-03T14:00:00Z',
                        'added_by': {'id': 'user_who_added_updated'},
                        'track': {'id': 'track_new_3', 'name': 'New Song 3', 'artists': [{'name': 'Artist C'}], 'album': {'name': 'Album Z'}, 'explicit': False}
                    }
                 ],
                'next': None, 'total': 1, 'limit': limit, 'offset': offset
            }
        }.get(playlist_id, {'items': [], 'next': None, 'total': 0, 'limit': limit, 'offset': offset})


        # Get the test user
        user = User.query.filter_by(spotify_id='test_spotify_user').first()
        assert user is not None

        # Create the service instance (this will now use the mocked Spotify class)
        # Mock the user's token validity check if necessary within the service init
        with patch.object(User, 'ensure_token_valid', return_value=True, autospec=True):
             # Pass the user's token directly, avoiding reliance on current_user in test
             service = SpotifyService(auth_token=user.access_token)

        # Run the sync method
        service.sync_user_playlists_with_db(user_id=user.id)

        # --- Assertions --- 

        # 1. Check if the new playlist was created
        new_playlist = Playlist.query.filter_by(spotify_id='playlist_new_1').first()
        assert new_playlist is not None
        assert new_playlist.name == 'New Playlist 1'
        assert new_playlist.spotify_snapshot_id == 'snapshot_new_1'
        assert new_playlist.owner_id == user.id

        # 2. Check if the tracks for the new playlist were added
        track1 = Song.query.filter_by(spotify_id='track_new_1').first()
        track2 = Song.query.filter_by(spotify_id='track_new_2').first()
        assert track1 is not None
        assert track1.title == 'New Song 1'
        assert track1.artist == 'Artist A'
        assert track1.album == 'Album X'
        assert track2 is not None
        assert track2.title == 'New Song 2'
        assert track2.artist == 'Artist B'
        assert track2.album == 'Album Y'

        # 3. Check PlaylistSong associations for the new playlist
        assoc1 = db.session.get(PlaylistSong, (new_playlist.id, track1.id))
        assoc2 = db.session.get(PlaylistSong, (new_playlist.id, track2.id))
        assert assoc1 is not None
        assert assoc1.track_position == 0 # Assuming order from mock
        # Make DB value UTC-aware for comparison
        assert assoc1.added_at_spotify.replace(tzinfo=timezone.utc) == parser.parse('2024-01-01T12:00:00Z')
        assert assoc1.added_by_spotify_user_id == 'user_who_added'
        assert assoc2 is not None
        assert assoc2.track_position == 1
        # Make DB value UTC-aware for comparison
        assert assoc2.added_at_spotify.replace(tzinfo=timezone.utc) == parser.parse('2024-01-02T13:00:00Z')
        assert assoc2.added_by_spotify_user_id == 'user_who_added'

        # 4. Verify playlist_items was called correctly for the playlists needing sync
        expected_fields = 'items(track(id,name,artists(id,name),album(id,name)),added_at,added_by(id)),next'
        expected_calls = [
            # Call for the new playlist
            call(
                playlist_id='playlist_new_1',
                limit=100,
                offset=0,
                fields=ANY, # Use ANY to avoid strict matching on exact fields string
                additional_types=('track',) # Add missing argument
            ),
            # Call for the changed playlist
            call(
                playlist_id='playlist_existing_change_1',
                limit=100,
                offset=0,
                fields=ANY, # Use ANY to avoid strict matching on exact fields string
                additional_types=('track',) # Add missing argument
            )
        ]
        mock_instance.playlist_items.assert_has_calls(expected_calls, any_order=True)

        # Optionally, assert the total number of calls if necessary
        # assert mock_instance.playlist_items.call_count == 2

        # 5. Verify current_user_playlists was called twice (for pagination)
        assert mock_instance.current_user_playlists.call_count == 2
        mock_instance.current_user_playlists.assert_has_calls([
            call(limit=50, offset=0), 
            call(limit=50, offset=50)
        ])

        # 6. Check that the unchanged playlist was NOT processed for tracks
        # (playlist_items should only be called for new or changed snapshot IDs)
        # Assertions earlier already check it was called only once for 'playlist_new_1'
        # We can be more explicit if needed by checking call_args_list
        calls_to_playlist_items = mock_instance.playlist_items.call_args_list
        assert len(calls_to_playlist_items) == 2
        assert calls_to_playlist_items[0].args[0] in ['playlist_new_1', 'playlist_existing_change_1']
        assert calls_to_playlist_items[1].args[0] in ['playlist_new_1', 'playlist_existing_change_1']

        # 7. Check existing playlist with NO snapshot change was untouched
        nochange_playlist = Playlist.query.filter_by(spotify_id='playlist_existing_nochange_1').first()
        assert nochange_playlist is not None
        # Name SHOULD be updated even if snapshot hasn't changed, based on current logic
        assert nochange_playlist.name == 'Existing No Change 1'
        assert nochange_playlist.spotify_snapshot_id == 'snapshot_existing_1_v1' # Snapshot ID should remain
        # We could also check that the associated songs for this playlist weren't deleted/re-added
        # if the initial fixture included them.

    @patch('app.services.spotify_service.spotipy.Spotify', autospec=True)
    def test_sync_existing_playlist_snapshot_change(self, mock_spotify_class, test_client, init_database):
        """Verify tracks are re-synced when a playlist's snapshot_id changes."""
        # --- Setup ---
        mock_instance = mock_spotify_class.return_value
        user = User.query.filter_by(spotify_id='test_spotify_user').first()
        assert user is not None

        playlist_to_change = Playlist.query.filter_by(
            spotify_id='playlist_existing_change_1', owner_id=user.id
        ).first()
        assert playlist_to_change is not None
        assert playlist_to_change.spotify_snapshot_id == 'snapshot_existing_2_v1' # Verify initial state

        # Get the initial song and association (should be removed after sync)
        initial_song = Song.query.filter_by(spotify_id='track_old').first()
        assert initial_song is not None
        initial_assoc = db.session.get(PlaylistSong, (playlist_to_change.id, initial_song.id)) # Check by composite primary key
        assert initial_assoc is not None
        assert initial_assoc.track_position == 0

        # --- Mock Spotify API Responses ---
        mock_instance.current_user_playlists.return_value = {
            'items': [
                # Return the same playlist but with a NEW snapshot_id and updated name
                {
                    'id': 'playlist_existing_change_1',
                    'name': 'Existing Change 1 - Updated Name', # New name
                    'snapshot_id': 'snapshot_existing_2_v2', # NEW snapshot ID
                    'description': 'Updated description', # New description
                    'tracks': {'total': 1}, # New track count
                    'images': [{'url': 'http://image.url/change1'}]
                },
                 # Include the unchanged playlist as well
                 {'id': 'playlist_existing_nochange_1', 'name': 'Existing No Change 1', 'snapshot_id': 'snapshot_existing_1_v1', 'tracks': {'total': 5}, 'images': []}
            ],
            'next': None, 'limit': 50, 'offset': 0, 'total': 2
        }

        # Mock playlist_items to return the NEW track list for the changed playlist
        new_track_spotify_id = 'track_new_for_changed_playlist'
        new_track_title = 'Replacement Song'
        new_track_artist = 'Artist Replaced'
        new_track_album = 'Album Replaced'
        new_added_at = '2024-05-12T10:00:00Z'
        new_added_by = 'user_updater'

        mock_instance.playlist_items.side_effect = lambda playlist_id, limit=100, offset=0, fields=None, additional_types=('track',): {
            'playlist_existing_change_1': {
                'items': [
                    {
                        'added_at': new_added_at,
                        'added_by': {'id': new_added_by},
                        'track': {'id': new_track_spotify_id, 'name': new_track_title, 'artists': [{'name': new_track_artist}], 'album': {'name': new_track_album}, 'explicit': False}
                    }
                ],
                'next': None, 'total': 1, 'limit': limit, 'offset': offset
            }
            # We don't need to mock items for playlist_existing_nochange_1 as it shouldn't be called
        }.get(playlist_id, {'items': [], 'next': None, 'total': 0, 'limit': limit, 'offset': offset})


        # --- Execution ---
        service = SpotifyService(auth_token=user.access_token)
        service.sync_user_playlists_with_db(user_id=user.id)
        db.session.refresh(playlist_to_change) # Refresh object state from DB

        # --- Assertions ---

        # 1. Playlist metadata updated?
        assert playlist_to_change.name == 'Existing Change 1 - Updated Name'
        assert playlist_to_change.spotify_snapshot_id == 'snapshot_existing_2_v2'
        assert playlist_to_change.description == 'Updated description'

        # 2. Old association removed?
        old_assoc_exists = db.session.get(PlaylistSong, (playlist_to_change.id, initial_song.id)) # Check by composite primary key
        assert old_assoc_exists is None, "Old PlaylistSong association should have been deleted"

        # 3. New Song created?
        new_song = Song.query.filter_by(spotify_id=new_track_spotify_id).first()
        assert new_song is not None
        assert new_song.title == new_track_title
        assert new_song.artist == new_track_artist
        assert new_song.album == new_track_album

        # 4. New PlaylistSong association created?
        new_assoc = db.session.get(PlaylistSong, (playlist_to_change.id, new_song.id))
        assert new_assoc is not None
        assert new_assoc.track_position == 0
        assert new_assoc.added_at_spotify.replace(tzinfo=timezone.utc) == parser.parse(new_added_at)
        assert new_assoc.added_by_spotify_user_id == new_added_by

        # 5. Was playlist_items called for the changed playlist?
        mock_instance.playlist_items.assert_called_once_with(
             playlist_id='playlist_existing_change_1',
             limit=100,
             offset=0,
             fields=ANY, # Use ANY to avoid strict matching on exact fields string
             additional_types=('track',) # Add missing argument
        )

        # 6. Was current_user_playlists called? (Should be called once in this simplified mock)
        mock_instance.current_user_playlists.assert_called_once()


    @patch('app.services.spotify_service.spotipy.Spotify', autospec=True)
    def test_sync_existing_playlist_no_snapshot_change(self, mock_spotify_class, test_client, init_database):
        """
        Verify that tracks are NOT re-synced and playlist_items is NOT called
        for an existing playlist if its snapshot_id has not changed.
        Metadata (name, description, image) should still be updated.
        """
        # --- Setup ---
        mock_instance = mock_spotify_class.return_value
        user = User.query.filter_by(spotify_id='test_spotify_user').first()
        assert user is not None

        playlist_spotify_id = 'playlist_existing_nochange_1'
        original_song_spotify_id = 'track_nochange' # Song associated in init_database

        # Get the playlist from DB before sync
        playlist_db_before_sync = Playlist.query.filter_by(
            spotify_id=playlist_spotify_id, owner_id=user.id
        ).first()
        assert playlist_db_before_sync is not None
        original_snapshot_id = playlist_db_before_sync.spotify_snapshot_id
        assert original_snapshot_id == 'snapshot_existing_1_v1' # From fixture

        # Get its original song and association details
        original_song_db = Song.query.filter_by(spotify_id=original_song_spotify_id).first()
        assert original_song_db is not None
        
        original_assoc = db.session.get(PlaylistSong, (playlist_db_before_sync.id, original_song_db.id))
        assert original_assoc is not None
        original_assoc_pos = original_assoc.track_position
        original_assoc_added_at = original_assoc.added_at_spotify
        original_assoc_added_by = original_assoc.added_by_spotify_user_id

        # --- Mock Spotify API Responses ---
        updated_name = "No Change Playlist - Updated Name"
        updated_description = "This playlist's tracks should not sync, but name can change."
        updated_image_url = "http://image.url/nochange_updated_fixture" # New image url

        mock_instance.current_user_playlists.return_value = {
            'items': [
                {
                    'id': playlist_spotify_id,
                    'name': updated_name,
                    'snapshot_id': original_snapshot_id, # SNAPSHOT ID IS THE SAME
                    'description': updated_description,
                    'tracks': {'total': 1}, # Mock track count, actual tracks won't be fetched
                    'images': [{'url': updated_image_url}] 
                }
                # If testing with multiple playlists, add others here
            ],
            'next': None, 'limit': 50, 'offset': 0, 'total': 1
        }

        # --- Execution ---
        service = SpotifyService(auth_token=user.access_token)
        service.sync_user_playlists_with_db(user_id=user.id)
        
        db.session.refresh(playlist_db_before_sync) # Refresh object state from DB

        # --- Assertions ---
        # 1. Playlist metadata (name, description, image) updated?
        assert playlist_db_before_sync.name == updated_name
        assert playlist_db_before_sync.description == updated_description
        assert playlist_db_before_sync.spotify_snapshot_id == original_snapshot_id # Snapshot ID unchanged
        assert playlist_db_before_sync.image_url == updated_image_url

        # 2. Original Song and PlaylistSong association untouched?
        current_song_db = Song.query.filter_by(spotify_id=original_song_spotify_id).first()
        assert current_song_db is not None
        assert current_song_db.id == original_song_db.id # Same song object

        current_assoc = db.session.get(PlaylistSong, (playlist_db_before_sync.id, current_song_db.id))
        assert current_assoc is not None, "Original association should still exist"
        assert current_assoc.track_position == original_assoc_pos
        assert current_assoc.added_at_spotify == original_assoc_added_at
        assert current_assoc.added_by_spotify_user_id == original_assoc_added_by
        
        associations_count = PlaylistSong.query.filter_by(playlist_id=playlist_db_before_sync.id).count()
        assert associations_count == 1, "Playlist should still have its original one track association."

        # 3. Was playlist_items NOT called?
        # Since current_user_playlists only returns this one playlist and its snapshot_id didn't change,
        # _sync_playlist_tracks (and thus playlist_items) should not be called for it.
        mock_instance.playlist_items.assert_not_called()

        # 4. Was current_user_playlists called?
        mock_instance.current_user_playlists.assert_called_once()


    @patch('app.services.spotify_service.spotipy.Spotify', autospec=True)
    def test_sync_playlist_with_track_pagination(self, mock_spotify_class, test_client, init_database):
        """
        Verify that _sync_playlist_tracks correctly handles pagination 
        when fetching tracks using sp.playlist_items.
        """
        # --- Setup ---
        mock_instance = mock_spotify_class.return_value
        user = User.query.filter_by(spotify_id='test_spotify_user').first()
        assert user is not None

        playlist_spotify_id = 'playlist_tracks_pagination_test'
        new_playlist_name = 'Paginated Playlist'

        # Mock current_user_playlists to return a new playlist that needs track syncing
        mock_instance.current_user_playlists.return_value = {
            'items': [
                {
                    'id': playlist_spotify_id,
                    'name': new_playlist_name,
                    'snapshot_id': 'snapshot_pagination_v1',
                    'description': 'A playlist to test track pagination',
                    'tracks': {'total': 3}, # Total tracks match our paginated items
                    'images': []
                }
            ],
            'next': None, 'limit': 50, 'offset': 0, 'total': 1
        }

        # --- Mock sp.playlist_items to simulate pagination ---
        # Three tracks, to be returned in two pages (2 per page for this mock)
        track_data_page1 = [
            {'added_at': '2024-01-01T10:00:00Z', 'added_by': {'id': 'user1'}, 'track': {'id': 'track_p1_1', 'name': 'Track Page1 Num1', 'artists': [{'name': 'Artist P1'}], 'album': {'name': 'Album P1'}, 'explicit': False}},
            {'added_at': '2024-01-01T10:01:00Z', 'added_by': {'id': 'user1'}, 'track': {'id': 'track_p1_2', 'name': 'Track Page1 Num2', 'artists': [{'name': 'Artist P1'}], 'album': {'name': 'Album P1'}, 'explicit': False}}
        ]
        track_data_page2 = [
            {'added_at': '2024-01-01T10:02:00Z', 'added_by': {'id': 'user2'}, 'track': {'id': 'track_p2_1', 'name': 'Track Page2 Num1', 'artists': [{'name': 'Artist P2'}], 'album': {'name': 'Album P2'}, 'explicit': True}}
        ]

        call_count = 0 # Keep track for assertion, but side_effect logic relies on offset
        def side_effect_playlist_items(playlist_id, limit=100, offset=0, fields=None, additional_types=('track',)):
            nonlocal call_count
            call_count +=1
            
            # The service's _sync_playlist_tracks calls with limit=100
            assert limit == 100 
            
            if playlist_id == playlist_spotify_id:
                if offset == 0: # First call from service
                    return {'items': track_data_page1, 'next': 'mock_next_page_marker', 'total': 3, 'limit': limit, 'offset': 0}
                elif offset == 100: # Second call from service (since limit is 100 and page1 had 'next')
                    return {'items': track_data_page2, 'next': None, 'total': 3, 'limit': limit, 'offset': 100}
            # If offset is something else, or for other playlists, return empty
            return {'items': [], 'next': None, 'total': 0, 'limit': limit, 'offset': offset}

        mock_instance.playlist_items.side_effect = side_effect_playlist_items

        # --- Execution ---
        service = SpotifyService(auth_token=user.access_token)
        service.sync_user_playlists_with_db(user_id=user.id)

        # --- Assertions ---
        # 1. Was playlist_items called multiple times (e.g., twice)?
        assert call_count == 2 # Relies on the side_effect's counter
        assert mock_instance.playlist_items.call_count == 2 # More direct mock assertion
        
        mock_instance.playlist_items.assert_any_call(
            playlist_id=playlist_spotify_id, 
            limit=100, 
            offset=0, 
            fields=ANY, 
            additional_types=('track',)
        )
        mock_instance.playlist_items.assert_any_call(
            playlist_id=playlist_spotify_id, 
            limit=100, 
            offset=100, 
            fields=ANY, 
            additional_types=('track',)
        )

        # 2. Is the playlist created?
        playlist_db = Playlist.query.filter_by(spotify_id=playlist_spotify_id, owner_id=user.id).first()
        assert playlist_db is not None
        assert playlist_db.name == new_playlist_name

        # 3. Are all tracks (3) created and associated?
        song1 = Song.query.filter_by(spotify_id='track_p1_1').first()
        song2 = Song.query.filter_by(spotify_id='track_p1_2').first()
        song3 = Song.query.filter_by(spotify_id='track_p2_1').first()
        assert song1 is not None and song1.title == 'Track Page1 Num1'
        assert song2 is not None and song2.title == 'Track Page1 Num2'
        assert song3 is not None and song3.title == 'Track Page2 Num1'

        associations = PlaylistSong.query.filter_by(playlist_id=playlist_db.id).order_by(PlaylistSong.track_position).all()
        assert len(associations) == 3
        
        assert associations[0].song_id == song1.id
        assert associations[0].track_position == 0
        assert associations[0].added_at_spotify.isoformat().startswith('2024-01-01T10:00:00')
        assert associations[0].added_by_spotify_user_id == 'user1'

        assert associations[1].song_id == song2.id
        assert associations[1].track_position == 1
        assert associations[1].added_at_spotify.isoformat().startswith('2024-01-01T10:01:00')
        assert associations[1].added_by_spotify_user_id == 'user1'

        assert associations[2].song_id == song3.id
        assert associations[2].track_position == 2
        assert associations[2].added_at_spotify.isoformat().startswith('2024-01-01T10:02:00')
        assert associations[2].added_by_spotify_user_id == 'user2'

    # TODO: Add test for handling Spotify API errors (e.g., 401, 403, 429)
    # TODO: Add test for playlists being deleted on Spotify (removed from current_user_playlists)
