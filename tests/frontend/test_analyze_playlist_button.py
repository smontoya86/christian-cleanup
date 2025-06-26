import pytest
from flask import url_for
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from app.models.models import Playlist, Song, PlaylistSong, AnalysisResult
from app import db

@pytest.fixture
def sample_playlist_with_songs(app, db, sample_user, sample_playlist, sample_song, sample_analysis):
    """Create a playlist with songs and analysis for testing"""
    from app.models.models import PlaylistSong
    
    # Create a playlist-song relationship
    playlist_song = PlaylistSong(
        playlist_id=sample_playlist.id,
        song_id=sample_song.id,
        track_position=0
    )
    
    db.session.add(playlist_song)
    db.session.commit()
    
    return {
        'playlist': sample_playlist,
        'songs': [sample_song],
        'analysis': [sample_analysis]
    }

class TestAnalyzePlaylistButton:
    """Test the Analyze All Songs button functionality in playlist detail view"""
    
    def test_analyze_button_present_in_playlist_detail(self, authenticated_client, sample_playlist):
        """Test that the Analyze All Songs button is present in playlist detail"""
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=sample_playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the analyze button
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        assert analyze_btn is not None, "Analyze All Songs button should be present"
        assert 'Analyze All Songs' in analyze_btn.get_text()
        
    def test_analyze_button_has_correct_attributes(self, authenticated_client, sample_playlist):
        """Test that the button has the correct CSS class and data attributes"""
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=sample_playlist.id))
        soup = BeautifulSoup(response.data, 'html.parser')
        
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        assert analyze_btn is not None
        assert 'btn' in analyze_btn.get('class', [])
        assert 'btn-primary' in analyze_btn.get('class', [])
        assert analyze_btn.get('data-playlist-id') == str(sample_playlist.id)
        assert analyze_btn.get('data-playlist-name') == sample_playlist.name
        
    def test_button_shows_analyze_for_unanalyzed_playlist(self, authenticated_client, sample_user, db_session):
        """Test that button shows 'Analyze All Songs' for playlist with unanalyzed songs"""
        # Create playlist with unanalyzed songs
        playlist = Playlist(
            name="Unanalyzed Playlist",
            spotify_id="unanalyzed_123",
            owner_id=sample_user.id
        )
        db_session.add(playlist)
        db_session.flush()
        
        # Add songs without analysis
        for i in range(3):
            song = Song(
                title=f"Song {i+1}",
                artist="Test Artist",
                spotify_id=f"song_{i+1}",
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                track_position=i
            )
            db_session.add(playlist_song)
        
        db_session.commit()
        
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        
        assert analyze_btn is not None
        assert 'Analyze All Songs' in analyze_btn.get_text()
        assert 'btn-primary' in analyze_btn.get('class', [])

    def test_button_shows_reanalyze_for_analyzed_playlist(self, authenticated_client, sample_user, db_session):
        """Test that button shows 'Re-analyze All Songs' for playlist with all songs analyzed"""
        # Create playlist with analyzed songs
        playlist = Playlist(
            name="Analyzed Playlist",
            spotify_id="analyzed_123",
            owner_id=sample_user.id
        )
        db_session.add(playlist)
        db_session.flush()
        
        # Add songs with completed analysis
        for i in range(3):
            song = Song(
                title=f"Analyzed Song {i+1}",
                artist="Test Artist",
                spotify_id=f"analyzed_song_{i+1}",
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            # Add completed analysis
            analysis = AnalysisResult(
                song_id=song.id,
                status='completed',
                score=85.5,
                concern_level='low',
                positive_themes_identified={'love': True, 'hope': True},
                concerns=[],
                biblical_themes={'Love': True, 'Grace': True}
            )
            db_session.add(analysis)
            
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                track_position=i
            )
            db_session.add(playlist_song)
        
        db_session.commit()
        
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        
        assert analyze_btn is not None
        assert 'Re-analyze All Songs' in analyze_btn.get_text()
        assert 'btn-outline-secondary' in analyze_btn.get('class', [])

    def test_button_shows_analyze_for_partially_analyzed_playlist(self, authenticated_client, sample_user, db_session):
        """Test that button shows 'Analyze All Songs' for playlist with some unanalyzed songs"""
        # Create playlist with mix of analyzed and unanalyzed songs
        playlist = Playlist(
            name="Partially Analyzed Playlist",
            spotify_id="partial_123",
            owner_id=sample_user.id
        )
        db_session.add(playlist)
        db_session.flush()
        
        # Add 2 analyzed songs and 1 unanalyzed song
        for i in range(3):
            song = Song(
                title=f"Mixed Song {i+1}",
                artist="Test Artist",
                spotify_id=f"mixed_song_{i+1}",
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            # Only analyze first 2 songs
            if i < 2:
                analysis = AnalysisResult(
                    song_id=song.id,
                    status='completed',
                    score=85.5,
                    concern_level='low',
                    positive_themes_identified={'love': True},
                    concerns=[],
                    biblical_themes={'Love': True}
                )
                db_session.add(analysis)
            
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                track_position=i
            )
            db_session.add(playlist_song)
        
        db_session.commit()
        
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        
        assert analyze_btn is not None
        assert 'Analyze All Songs' in analyze_btn.get_text()
        assert 'btn-primary' in analyze_btn.get('class', [])
        
    @patch('app.routes.main.UnifiedAnalysisService')
    def test_analyze_playlist_route_works(self, mock_service, authenticated_client, sample_playlist_with_songs):
        """Test that the analyze playlist route functions correctly"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Mock the analysis service
        mock_analyzer = MagicMock()
        mock_service.return_value = mock_analyzer
        mock_analyzer.enqueue_analysis_job.return_value = True
        
        # POST to the analyze playlist route
        response = authenticated_client.post(url_for('main.analyze_playlist', playlist_id=playlist.id))
        
        # Should redirect back to playlist detail
        assert response.status_code == 302
        assert f'/playlist/{playlist.id}' in response.location
        
        # Should have called the analysis service
        mock_service.assert_called_once()
        mock_analyzer.enqueue_analysis_job.assert_called()
        
    def test_javascript_includes_song_analyzer(self, authenticated_client, sample_playlist):
        """Test that the playlist detail page includes the song-analyzer.js script"""
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=sample_playlist.id))
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for the JavaScript include
        script_tags = soup.find_all('script', src=True)
        song_analyzer_scripts = [script for script in script_tags if 'song-analyzer.js' in script.get('src', '')]
        assert len(song_analyzer_scripts) > 0, "song-analyzer.js should be included in the page"
        
    def test_analyze_button_has_data_attributes(self, authenticated_client, sample_playlist):
        """Test that the analyze button has the correct data attributes for JavaScript"""
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=sample_playlist.id))
        soup = BeautifulSoup(response.data, 'html.parser')
        
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        assert analyze_btn is not None
        
        # Button should have data attributes for playlist
        playlist_id = analyze_btn.get('data-playlist-id')
        playlist_name = analyze_btn.get('data-playlist-name')
        
        assert playlist_id is not None, "Button should have data-playlist-id attribute"
        assert playlist_name is not None, "Button should have data-playlist-name attribute"
        assert playlist_id == str(sample_playlist.id), f"Expected playlist ID {sample_playlist.id}, got {playlist_id}"
        assert playlist_name == sample_playlist.name, f"Expected playlist name '{sample_playlist.name}', got '{playlist_name}'"
        
    def test_analyze_playlist_button_integration(self, authenticated_client, sample_playlist_with_songs):
        """Test full integration: button exists, has correct data, and JavaScript would make correct API call"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Get the playlist detail page
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Verify button exists with correct attributes
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        assert analyze_btn is not None, "Analyze All Songs button should be present"
        
        # Verify data attributes for JavaScript
        assert analyze_btn.get('data-playlist-id') == str(playlist.id)
        assert analyze_btn.get('data-playlist-name') == playlist.name
        
        # Verify the song-analyzer.js script is included
        script_tags = soup.find_all('script', src=True)
        song_analyzer_scripts = [script for script in script_tags if 'song-analyzer.js' in script.get('src', '')]
        assert len(song_analyzer_scripts) > 0, "song-analyzer.js should be included"
        
        # Test that the route exists and works (this simulates what the JavaScript would do)
        analysis_response = authenticated_client.post(url_for('main.analyze_playlist', playlist_id=playlist.id))
        
        # Should redirect (typical Flask form submission behavior)
        assert analysis_response.status_code == 302
        assert f'/playlist/{playlist.id}' in analysis_response.location
        
    def test_playlist_analysis_progress_tracking(self, authenticated_client, sample_playlist_with_songs):
        """Test that playlist analysis provides real-time progress updates"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Get the playlist detail page
        response = authenticated_client.get(url_for('main.playlist_detail', playlist_id=playlist.id))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Verify button exists and can track progress
        analyze_btn = soup.find('button', class_='analyze-playlist-btn')
        assert analyze_btn is not None
        
        # The JavaScript should be able to poll for playlist analysis status
        # This test verifies the infrastructure exists for progress tracking
        script_content = response.data.decode('utf-8')
        assert 'song-analyzer.js' in script_content, "Should include song analyzer script for progress tracking"
        
    def test_playlist_progress_api_endpoint(self, authenticated_client, sample_playlist_with_songs):
        """Test that the playlist progress API endpoint returns expected data format"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Call the progress API endpoint
        response = authenticated_client.get(f'/api/playlists/{playlist.id}/analysis-status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data is not None, "Should return JSON data"
        
        # Verify required fields for JavaScript progress tracking
        assert 'success' in data, "Should have success field"
        assert 'progress' in data, "Should have progress field"
        assert 'analyzed_count' in data, "Should have analyzed_count field"
        assert 'total_count' in data, "Should have total_count field"
        assert 'message' in data, "Should have message field"
        assert 'completed' in data, "Should have completed field"
        
        # Verify data types
        assert isinstance(data['progress'], (int, float)), "Progress should be numeric"
        assert isinstance(data['analyzed_count'], int), "Analyzed count should be integer"
        assert isinstance(data['total_count'], int), "Total count should be integer"
        assert isinstance(data['completed'], bool), "Completed should be boolean"
                
    def test_playlist_analysis_ajax_response(self, authenticated_client, sample_playlist_with_songs):
        """Test that the playlist analysis route returns proper JSON for AJAX requests"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Make an AJAX request to the playlist analysis endpoint
        response = authenticated_client.post(
            f'/analyze_playlist/{playlist.id}',
            headers={'X-Requested-With': 'XMLHttpRequest'},
            content_type='application/json'
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
        
        # Check that we get JSON response
        assert response.content_type == 'application/json', f"Expected JSON, got {response.content_type}"
        
        data = response.get_json()
        assert data is not None, "Response should contain JSON data"
        assert 'success' in data, "Response should contain 'success' field"
        assert 'message' in data, "Response should contain 'message' field"
        
        if data['success']:
            assert 'jobs_queued' in data, "Successful response should contain 'jobs_queued'"
            assert 'total_songs' in data, "Successful response should contain 'total_songs'"
            assert data['jobs_queued'] > 0, "Should have queued at least one job"
        else:
            assert 'errors' in data, "Failed response should contain 'errors'"
            print(f"❌ Analysis failed: {data}")
            
    def test_playlist_analysis_non_ajax_response(self, authenticated_client, sample_playlist_with_songs):
        """Test that the playlist analysis route redirects for non-AJAX requests"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Make a regular POST request (not AJAX)
        response = authenticated_client.post(f'/analyze_playlist/{playlist.id}')
        
        # Should redirect back to playlist detail page
        assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
        assert f'/playlist/{playlist.id}' in response.location, f"Should redirect to playlist detail page"
        
    def test_playlist_analysis_complete_workflow(self, authenticated_client, sample_playlist_with_songs):
        """Test the complete workflow of playlist analysis with AJAX request and JSON response"""
        playlist = sample_playlist_with_songs['playlist']
        
        # Make an AJAX request to start playlist analysis
        response = authenticated_client.post(
            f'/analyze_playlist/{playlist.id}',
            headers={'X-Requested-With': 'XMLHttpRequest'},
            content_type='application/json'
        )
        
        # Should get successful JSON response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['jobs_queued'] == 1  # We have 1 song in the test playlist
        assert data['total_songs'] == 1
        assert 'message' in data
        
        # Verify that the song was actually analyzed
        from app.models.models import AnalysisResult
        song = sample_playlist_with_songs['songs'][0]  # Get the first song from the list
        analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
        assert analysis is not None, "Analysis should have been created for the song"
        assert analysis.status == 'completed', "Analysis should be completed"
        
        # Check the progress endpoint returns completed status
        progress_response = authenticated_client.get(f'/api/playlists/{playlist.id}/analysis-status')
        assert progress_response.status_code == 200
        progress_data = progress_response.get_json()
        assert progress_data['completed'] is True
        assert progress_data['progress'] == 100.0
        assert progress_data['analyzed_count'] == 1
        assert progress_data['total_count'] == 1 