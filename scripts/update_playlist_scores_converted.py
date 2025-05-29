#!/usr/bin/env python3
"""
Script to calculate and update playlist scores for existing playlists.
This should help fix the issue where playlists show "Not Analyzed" instead of their actual scores.
"""

import os
import sys
import time

# Add the project root to the Python path  
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.models import Playlist, Song, AnalysisResult
from app.utils.database import get_all_by_filter, safe_commit
from scripts.utils.script_logging import (
    get_script_logger,
    log_operation_start,
    log_operation_success,
    log_operation_error,
    log_progress,
    log_milestone
)


def calculate_playlist_score(playlist, logger):
    """Calculate the overall score for a playlist based on analyzed songs."""
    try:
        logger.debug("Starting score calculation", extra={
            'extra_fields': {
                'operation': 'calculate_playlist_score',
                'playlist_id': playlist.id,
                'playlist_name': playlist.name,
                'total_songs': len(playlist.songs)
            }
        })
        
        # Get all analysis results for songs in this playlist
        analyzed_songs = []
        for song in playlist.songs:
            analysis_result = song.analysis_results.first()
            if analysis_result and analysis_result.status == 'completed' and analysis_result.score is not None:
                analyzed_songs.append(analysis_result.score)
        
        if not analyzed_songs:
            logger.info("No analyzed songs found for playlist", extra={
                'extra_fields': {
                    'operation': 'calculate_playlist_score',
                    'playlist_id': playlist.id,
                    'playlist_name': playlist.name,
                    'total_songs': len(playlist.songs),
                    'analyzed_songs': 0,
                    'result': 'no_analyzed_songs'
                }
            })
            return None  # No analyzed songs
            
        # Calculate average score (analysis results are 0-100)
        average_score = sum(analyzed_songs) / len(analyzed_songs)
        
        logger.info("Playlist score calculated successfully", extra={
            'extra_fields': {
                'operation': 'calculate_playlist_score',
                'playlist_id': playlist.id,
                'playlist_name': playlist.name,
                'total_songs': len(playlist.songs),
                'analyzed_songs': len(analyzed_songs),
                'calculated_score': average_score,
                'result': 'success'
            }
        })
        
        return average_score
        
    except Exception as e:
        log_operation_error(logger, 'calculate_playlist_score', e,
            playlist_id=playlist.id,
            playlist_name=playlist.name,
            total_songs=len(playlist.songs) if playlist else 0
        )
        return None


def main():
    logger = get_script_logger('update_playlist_scores')
    
    start_time = time.time()
    log_operation_start(logger, "Update playlist scores", 
                       description="Calculate and update scores for existing playlists")
    
    try:
        app = create_app()
        
        with app.app_context():
            log_milestone(logger, "Flask application context established")
            
            # Get all playlists using SQLAlchemy 2.0 pattern
            log_milestone(logger, "Retrieving playlists from database")
            playlists = get_all_by_filter(Playlist)
            
            logger.info("Playlists retrieved from database", extra={
                'extra_fields': {
                    'operation': 'retrieve_playlists',
                    'playlists_found': len(playlists),
                    'phase': 'data_retrieval'
                }
            })
            
            updated_count = 0
            processed_count = 0
            
            for i, playlist in enumerate(playlists):
                processed_count += 1
                
                # Log progress every 10 playlists or for small batches
                if processed_count % 10 == 0 or len(playlists) <= 20:
                    log_progress(logger, "Processing playlists", processed_count, len(playlists))
                
                # Calculate score
                score = calculate_playlist_score(playlist, logger)
                
                if score is not None:
                    old_score = playlist.overall_alignment_score
                    playlist.overall_alignment_score = score
                    
                    logger.info("Playlist score updated", extra={
                        'extra_fields': {
                            'operation': 'update_playlist_score',
                            'playlist_id': playlist.id,
                            'playlist_name': playlist.name,
                            'old_score': old_score,
                            'new_score': round(score, 1),
                            'score_change': round(score - (old_score or 0), 1),
                            'phase': 'score_update'
                        }
                    })
                    updated_count += 1
                else:
                    analyzed_songs_count = sum(1 for song in playlist.songs 
                                             if song.analysis_results.first() and 
                                             song.analysis_results.first().status == 'completed')
                    
                    logger.info("Playlist skipped - no analyzed songs", extra={
                        'extra_fields': {
                            'operation': 'skip_playlist',
                            'playlist_id': playlist.id,
                            'playlist_name': playlist.name,
                            'analyzed_songs_count': analyzed_songs_count,
                            'total_songs_count': len(playlist.songs),
                            'phase': 'skip'
                        }
                    })
            
            log_milestone(logger, "Playlist processing completed", 
                         processed=processed_count, 
                         updated=updated_count)
            
            if updated_count > 0:
                log_milestone(logger, "Committing database changes")
                success = safe_commit(f"Failed to commit playlist score updates")
                
                if success:
                    duration = time.time() - start_time
                    log_operation_success(logger, "Update playlist scores", duration,
                        playlists_processed=processed_count,
                        playlists_updated=updated_count,
                        commit_success=True
                    )
                else:
                    logger.error("Database commit failed", extra={
                        'extra_fields': {
                            'operation': 'commit_changes',
                            'playlists_updated': updated_count,
                            'phase': 'error'
                        }
                    })
            else:
                duration = time.time() - start_time
                log_operation_success(logger, "Update playlist scores", duration,
                    playlists_processed=processed_count,
                    playlists_updated=0,
                    result="no_updates_needed"
                )
                
    except Exception as e:
        log_operation_error(logger, "Update playlist scores", e)
        raise


if __name__ == '__main__':
    main() 