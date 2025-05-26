"""
Batch operations service for optimizing database performance.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.models import Song, PlaylistSong, AnalysisResult, Playlist
import logging

logger = logging.getLogger(__name__)


class BatchOperationService:
    """Service for performing batch database operations efficiently."""
    
    def create_songs_batch(self, song_data_list: List[Dict[str, Any]]) -> List[Song]:
        """
        Create multiple songs in a single batch operation.
        
        Args:
            song_data_list: List of dictionaries containing song data
            
        Returns:
            List of created Song objects
        """
        if not song_data_list:
            return []
        
        try:
            # Create Song objects
            songs_to_create = []
            for song_data in song_data_list:
                song = Song(
                    spotify_id=song_data['spotify_id'],
                    title=song_data['title'],
                    artist=song_data['artist'],
                    album=song_data.get('album'),
                    duration_ms=song_data.get('duration_ms'),
                    album_art_url=song_data.get('album_art_url'),
                    explicit=song_data.get('explicit', False)
                )
                songs_to_create.append(song)
            
            # Use bulk_save_objects for better performance
            db.session.bulk_save_objects(songs_to_create, return_defaults=True)
            db.session.commit()
            
            logger.info(f"Successfully created {len(songs_to_create)} songs in batch")
            return songs_to_create
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during batch song creation: {e}")
            # Fall back to individual creation with duplicate checking
            return self._create_songs_individually_with_duplicate_check(song_data_list)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during batch song creation: {e}")
            raise
    
    def _create_songs_individually_with_duplicate_check(self, song_data_list: List[Dict[str, Any]]) -> List[Song]:
        """
        Fallback method to create songs individually with duplicate checking.
        """
        created_songs = []
        for song_data in song_data_list:
            # Check if song already exists
            existing_song = Song.query.filter_by(spotify_id=song_data['spotify_id']).first()
            if existing_song:
                created_songs.append(existing_song)
                continue
            
            try:
                song = Song(
                    spotify_id=song_data['spotify_id'],
                    title=song_data['title'],
                    artist=song_data['artist'],
                    album=song_data.get('album'),
                    duration_ms=song_data.get('duration_ms'),
                    album_art_url=song_data.get('album_art_url'),
                    explicit=song_data.get('explicit', False)
                )
                db.session.add(song)
                db.session.commit()
                created_songs.append(song)
            except IntegrityError:
                db.session.rollback()
                # Song was created by another process, fetch it
                existing_song = Song.query.filter_by(spotify_id=song_data['spotify_id']).first()
                if existing_song:
                    created_songs.append(existing_song)
        
        return created_songs
    
    def create_playlist_song_associations_batch(self, association_data_list: List[Dict[str, Any]]) -> List[PlaylistSong]:
        """
        Create multiple playlist-song associations in a single batch operation.
        
        Args:
            association_data_list: List of dictionaries containing association data
            
        Returns:
            List of created PlaylistSong objects
        """
        if not association_data_list:
            return []
        
        try:
            # Create PlaylistSong objects
            associations_to_create = []
            for assoc_data in association_data_list:
                association = PlaylistSong(
                    playlist_id=assoc_data['playlist_id'],
                    song_id=assoc_data['song_id'],
                    track_position=assoc_data.get('track_position', 0),
                    added_at_spotify=assoc_data.get('added_at_spotify'),
                    added_by_spotify_user_id=assoc_data.get('added_by_spotify_user_id')
                )
                associations_to_create.append(association)
            
            # Use bulk_save_objects for better performance
            db.session.bulk_save_objects(associations_to_create, return_defaults=True)
            db.session.commit()
            
            logger.info(f"Successfully created {len(associations_to_create)} playlist-song associations in batch")
            return associations_to_create
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during batch association creation: {e}")
            # Fall back to individual creation with duplicate checking
            return self._create_associations_individually_with_duplicate_check(association_data_list)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during batch association creation: {e}")
            raise
    
    def _create_associations_individually_with_duplicate_check(self, association_data_list: List[Dict[str, Any]]) -> List[PlaylistSong]:
        """
        Fallback method to create associations individually with duplicate checking.
        """
        created_associations = []
        for assoc_data in association_data_list:
            # Check if association already exists
            existing_assoc = PlaylistSong.query.filter_by(
                playlist_id=assoc_data['playlist_id'],
                song_id=assoc_data['song_id']
            ).first()
            if existing_assoc:
                created_associations.append(existing_assoc)
                continue
            
            try:
                association = PlaylistSong(
                    playlist_id=assoc_data['playlist_id'],
                    song_id=assoc_data['song_id'],
                    track_position=assoc_data.get('track_position', 0),
                    added_at_spotify=assoc_data.get('added_at_spotify'),
                    added_by_spotify_user_id=assoc_data.get('added_by_spotify_user_id')
                )
                db.session.add(association)
                db.session.commit()
                created_associations.append(association)
            except IntegrityError:
                db.session.rollback()
                # Association was created by another process, fetch it
                existing_assoc = PlaylistSong.query.filter_by(
                    playlist_id=assoc_data['playlist_id'],
                    song_id=assoc_data['song_id']
                ).first()
                if existing_assoc:
                    created_associations.append(existing_assoc)
        
        return created_associations
    
    def update_analysis_results_batch(self, update_data_list: List[Dict[str, Any]]) -> None:
        """
        Update multiple analysis results in a single batch operation.
        
        Args:
            update_data_list: List of dictionaries containing update data with 'id' field
        """
        if not update_data_list:
            return
        
        try:
            # Use bulk_update_mappings for better performance
            db.session.bulk_update_mappings(AnalysisResult, update_data_list)
            db.session.commit()
            
            logger.info(f"Successfully updated {len(update_data_list)} analysis results in batch")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during batch analysis update: {e}")
            raise
    
    def update_songs_batch(self, update_data_list: List[Dict[str, Any]]) -> None:
        """
        Update multiple songs in a single batch operation.
        
        Args:
            update_data_list: List of dictionaries containing update data with 'id' field
        """
        if not update_data_list:
            return
        
        try:
            # Use bulk_update_mappings for better performance
            db.session.bulk_update_mappings(Song, update_data_list)
            db.session.commit()
            
            logger.info(f"Successfully updated {len(update_data_list)} songs in batch")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during batch song update: {e}")
            raise
    
    def get_or_create_songs_batch(self, song_data_list: List[Dict[str, Any]]) -> List[Song]:
        """
        Get existing songs or create new ones in batch, optimized for playlist synchronization.
        
        Args:
            song_data_list: List of dictionaries containing song data
            
        Returns:
            List of Song objects (existing or newly created)
        """
        if not song_data_list:
            return []
        
        # Extract Spotify IDs for bulk lookup
        spotify_ids = [song_data['spotify_id'] for song_data in song_data_list]
        
        # Get existing songs in one query
        existing_songs = Song.query.filter(Song.spotify_id.in_(spotify_ids)).all()
        existing_songs_dict = {song.spotify_id: song for song in existing_songs}
        
        # Identify songs that need to be created
        songs_to_create = []
        result_songs = []
        
        for song_data in song_data_list:
            spotify_id = song_data['spotify_id']
            if spotify_id in existing_songs_dict:
                result_songs.append(existing_songs_dict[spotify_id])
            else:
                songs_to_create.append(song_data)
        
        # Create missing songs in batch
        if songs_to_create:
            newly_created_songs = self.create_songs_batch(songs_to_create)
            result_songs.extend(newly_created_songs)
        
        return result_songs
    
    def sync_playlist_songs_batch(self, playlist_id: int, spotify_track_data: List[Dict[str, Any]]) -> List[PlaylistSong]:
        """
        Synchronize playlist songs in batch for optimal performance.
        
        Args:
            playlist_id: Database ID of the playlist
            spotify_track_data: List of track data from Spotify API
            
        Returns:
            List of PlaylistSong associations
        """
        if not spotify_track_data:
            return []
        
        # Prepare song data for batch creation/retrieval
        song_data_list = []
        for idx, track_data in enumerate(spotify_track_data):
            if not track_data.get('id'):
                continue
                
            album_data = track_data.get('album', {})
            album_art_url = None
            if album_data.get('images') and len(album_data['images']) > 0:
                album_art_url = album_data['images'][0]['url']
            
            song_data = {
                'spotify_id': track_data['id'],
                'title': track_data.get('name', 'Unknown Title'),
                'artist': ', '.join([artist['name'] for artist in track_data.get('artists', [])]),
                'album': album_data.get('name', 'Unknown Album'),
                'album_art_url': album_art_url,
                'duration_ms': track_data.get('duration_ms'),
                'explicit': track_data.get('explicit', False)
            }
            song_data_list.append(song_data)
        
        # Get or create songs in batch
        songs = self.get_or_create_songs_batch(song_data_list)
        
        # Create song ID mapping for association creation
        song_id_map = {song.spotify_id: song.id for song in songs}
        
        # Prepare association data
        association_data_list = []
        for idx, track_data in enumerate(spotify_track_data):
            if not track_data.get('id') or track_data['id'] not in song_id_map:
                continue
                
            association_data = {
                'playlist_id': playlist_id,
                'song_id': song_id_map[track_data['id']],
                'track_position': idx,
                'added_at_spotify': track_data.get('added_at'),
                'added_by_spotify_user_id': track_data.get('added_by', {}).get('id')
            }
            association_data_list.append(association_data)
        
        # Create associations in batch
        associations = self.create_playlist_song_associations_batch(association_data_list)
        
        logger.info(f"Successfully synchronized {len(associations)} songs for playlist {playlist_id}")
        return associations 