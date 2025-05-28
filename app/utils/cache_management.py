"""
Cache management utilities for the lyrics caching system.
Provides functions to manage, monitor, and maintain the lyrics cache.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import current_app
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.models import db, LyricsCache

logger = logging.getLogger(__name__)


def clear_old_cache_entries(days: int = 30) -> int:
    """
    Remove cache entries older than specified days.
    
    Args:
        days: Number of days to keep entries (default: 30)
        
    Returns:
        Number of entries removed
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old entries
        old_entries = LyricsCache.query.filter(
            LyricsCache.updated_at < cutoff_date
        ).all()
        
        count = len(old_entries)
        
        if count > 0:
            # Delete old entries
            for entry in old_entries:
                db.session.delete(entry)
            
            db.session.commit()
            logger.info(f"Cleared {count} old lyrics cache entries (older than {days} days)")
        else:
            logger.debug(f"No cache entries older than {days} days found")
        
        return count
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error clearing old cache entries: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error clearing cache entries: {e}")
        raise


def clear_cache_by_source(source: str) -> int:
    """
    Remove all cache entries from a specific source provider.
    
    Args:
        source: Source provider name (e.g., 'LRCLibProvider', 'GeniusProvider')
        
    Returns:
        Number of entries removed
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        entries = LyricsCache.query.filter_by(source=source).all()
        count = len(entries)
        
        if count > 0:
            for entry in entries:
                db.session.delete(entry)
            
            db.session.commit()
            logger.info(f"Cleared {count} cache entries from source '{source}'")
        else:
            logger.debug(f"No cache entries found for source '{source}'")
        
        return count
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error clearing cache entries for source '{source}': {e}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error clearing cache entries for source '{source}': {e}")
        raise


def clear_all_cache() -> int:
    """
    Remove all cache entries.
    
    Returns:
        Number of entries removed
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        count = LyricsCache.query.count()
        
        if count > 0:
            LyricsCache.query.delete()
            db.session.commit()
            logger.info(f"Cleared all {count} lyrics cache entries")
        else:
            logger.debug("No cache entries to clear")
        
        return count
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error clearing all cache entries: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error clearing all cache entries: {e}")
        raise


def get_cache_stats() -> Dict[str, Any]:
    """
    Return comprehensive statistics about the lyrics cache.
    
    Returns:
        Dictionary containing cache statistics including:
        - total_entries: Total number of cached entries
        - sources: Breakdown by source provider
        - oldest_entry: Date of oldest entry
        - newest_entry: Date of newest entry
        - cache_span_days: Number of days between oldest and newest entries
        - size_stats: Statistics about lyrics content size
        - recent_activity: Recent cache activity statistics
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        stats = {}
        
        # Basic counts
        total_entries = LyricsCache.query.count()
        stats['total_entries'] = total_entries
        
        if total_entries == 0:
            return {
                'total_entries': 0,
                'sources': {},
                'oldest_entry': None,
                'newest_entry': None,
                'cache_span_days': 0,
                'size_stats': {},
                'recent_activity': {}
            }
        
        # Source breakdown
        sources = db.session.query(
            LyricsCache.source,
            func.count(LyricsCache.id).label('count')
        ).group_by(LyricsCache.source).all()
        
        stats['sources'] = {source: count for source, count in sources}
        
        # Date range
        oldest_entry = LyricsCache.query.order_by(asc(LyricsCache.created_at)).first()
        newest_entry = LyricsCache.query.order_by(desc(LyricsCache.created_at)).first()
        
        stats['oldest_entry'] = oldest_entry.created_at.isoformat() if oldest_entry else None
        stats['newest_entry'] = newest_entry.created_at.isoformat() if newest_entry else None
        
        # Calculate cache span
        if oldest_entry and newest_entry:
            cache_span = newest_entry.created_at - oldest_entry.created_at
            stats['cache_span_days'] = cache_span.days
        else:
            stats['cache_span_days'] = 0
        
        # Size statistics
        size_stats = db.session.query(
            func.min(func.length(LyricsCache.lyrics)).label('min_size'),
            func.max(func.length(LyricsCache.lyrics)).label('max_size'),
            func.avg(func.length(LyricsCache.lyrics)).label('avg_size')
        ).first()
        
        stats['size_stats'] = {
            'min_lyrics_length': size_stats.min_size or 0,
            'max_lyrics_length': size_stats.max_size or 0,
            'avg_lyrics_length': round(size_stats.avg_size or 0, 2)
        }
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_entries = LyricsCache.query.filter(
            LyricsCache.created_at >= week_ago
        ).count()
        
        stats['recent_activity'] = {
            'entries_last_7_days': recent_entries,
            'avg_entries_per_day': round(recent_entries / 7, 2)
        }
        
        logger.debug(f"Generated cache statistics: {total_entries} total entries")
        return stats
        
    except SQLAlchemyError as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting cache statistics: {e}")
        raise


def get_cache_entries_by_artist(artist: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get cache entries for a specific artist.
    
    Args:
        artist: Artist name (case-insensitive)
        limit: Maximum number of entries to return (default: 50)
        
    Returns:
        List of cache entries as dictionaries
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        entries = LyricsCache.query.filter(
            LyricsCache.artist.ilike(f'%{artist.lower()}%')
        ).order_by(desc(LyricsCache.updated_at)).limit(limit).all()
        
        result = []
        for entry in entries:
            result.append({
                'id': entry.id,
                'artist': entry.artist,
                'title': entry.title,
                'source': entry.source,
                'lyrics_length': len(entry.lyrics),
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat()
            })
        
        logger.debug(f"Found {len(result)} cache entries for artist '{artist}'")
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error getting cache entries for artist '{artist}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting cache entries for artist '{artist}': {e}")
        raise


def get_cache_entries_by_source(source: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get cache entries from a specific source provider.
    
    Args:
        source: Source provider name
        limit: Maximum number of entries to return (default: 50)
        
    Returns:
        List of cache entries as dictionaries
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        entries = LyricsCache.query.filter_by(source=source).order_by(
            desc(LyricsCache.updated_at)
        ).limit(limit).all()
        
        result = []
        for entry in entries:
            result.append({
                'id': entry.id,
                'artist': entry.artist,
                'title': entry.title,
                'source': entry.source,
                'lyrics_length': len(entry.lyrics),
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat()
            })
        
        logger.debug(f"Found {len(result)} cache entries from source '{source}'")
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error getting cache entries for source '{source}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting cache entries for source '{source}': {e}")
        raise


def optimize_cache_storage() -> Dict[str, Any]:
    """
    Optimize cache storage by removing duplicate entries and updating statistics.
    
    Returns:
        Dictionary with optimization results
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        # Find duplicate entries (same artist + title, keep the newest)
        duplicates_query = db.session.query(
            LyricsCache.artist,
            LyricsCache.title,
            func.count(LyricsCache.id).label('count'),
            func.max(LyricsCache.updated_at).label('latest_update')
        ).group_by(
            LyricsCache.artist,
            LyricsCache.title
        ).having(func.count(LyricsCache.id) > 1)
        
        duplicates = duplicates_query.all()
        removed_count = 0
        
        for artist, title, count, latest_update in duplicates:
            # Keep only the most recent entry
            entries_to_remove = LyricsCache.query.filter_by(
                artist=artist,
                title=title
            ).filter(
                LyricsCache.updated_at < latest_update
            ).all()
            
            for entry in entries_to_remove:
                db.session.delete(entry)
                removed_count += 1
        
        if removed_count > 0:
            db.session.commit()
            logger.info(f"Removed {removed_count} duplicate cache entries during optimization")
        
        # Get updated statistics
        stats = get_cache_stats()
        
        return {
            'duplicates_removed': removed_count,
            'optimization_completed': True,
            'current_stats': stats
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error optimizing cache storage: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error optimizing cache storage: {e}")
        raise


def validate_cache_integrity() -> Dict[str, Any]:
    """
    Validate the integrity of the cache data.
    
    Returns:
        Dictionary with validation results
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        issues = []
        
        # Check for entries with empty lyrics
        empty_lyrics = LyricsCache.query.filter(
            (LyricsCache.lyrics == '') | (LyricsCache.lyrics.is_(None))
        ).count()
        
        if empty_lyrics > 0:
            issues.append(f"{empty_lyrics} entries with empty lyrics")
        
        # Check for entries with missing artist or title
        missing_artist = LyricsCache.query.filter(
            (LyricsCache.artist == '') | (LyricsCache.artist.is_(None))
        ).count()
        
        missing_title = LyricsCache.query.filter(
            (LyricsCache.title == '') | (LyricsCache.title.is_(None))
        ).count()
        
        if missing_artist > 0:
            issues.append(f"{missing_artist} entries with missing artist")
        
        if missing_title > 0:
            issues.append(f"{missing_title} entries with missing title")
        
        # Check for entries with invalid timestamps
        invalid_timestamps = LyricsCache.query.filter(
            LyricsCache.created_at > datetime.utcnow()
        ).count()
        
        if invalid_timestamps > 0:
            issues.append(f"{invalid_timestamps} entries with future timestamps")
        
        total_entries = LyricsCache.query.count()
        
        result = {
            'total_entries': total_entries,
            'issues_found': len(issues),
            'issues': issues,
            'integrity_status': 'healthy' if len(issues) == 0 else 'issues_detected'
        }
        
        if len(issues) > 0:
            logger.warning(f"Cache integrity validation found {len(issues)} issues: {issues}")
        else:
            logger.info("Cache integrity validation passed - no issues found")
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error validating cache integrity: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating cache integrity: {e}")
        raise


def get_cache_usage_report(days: int = 30) -> Dict[str, Any]:
    """
    Generate a comprehensive cache usage report for the specified period.
    
    Args:
        days: Number of days to include in the report (default: 30)
        
    Returns:
        Dictionary with usage report data
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Entries created in the period
        new_entries = LyricsCache.query.filter(
            LyricsCache.created_at >= cutoff_date
        ).count()
        
        # Entries updated in the period
        updated_entries = LyricsCache.query.filter(
            LyricsCache.updated_at >= cutoff_date,
            LyricsCache.created_at < cutoff_date
        ).count()
        
        # Source breakdown for the period
        source_breakdown = db.session.query(
            LyricsCache.source,
            func.count(LyricsCache.id).label('count')
        ).filter(
            LyricsCache.created_at >= cutoff_date
        ).group_by(LyricsCache.source).all()
        
        # Most active artists (by cache entries created)
        top_artists = db.session.query(
            LyricsCache.artist,
            func.count(LyricsCache.id).label('count')
        ).filter(
            LyricsCache.created_at >= cutoff_date
        ).group_by(LyricsCache.artist).order_by(
            desc(func.count(LyricsCache.id))
        ).limit(10).all()
        
        report = {
            'report_period_days': days,
            'report_start_date': cutoff_date.isoformat(),
            'report_end_date': datetime.utcnow().isoformat(),
            'new_entries': new_entries,
            'updated_entries': updated_entries,
            'total_activity': new_entries + updated_entries,
            'avg_new_entries_per_day': round(new_entries / days, 2),
            'source_breakdown': {source: count for source, count in source_breakdown},
            'top_artists': [{'artist': artist, 'entries': count} for artist, count in top_artists]
        }
        
        logger.info(f"Generated cache usage report for {days} days: {new_entries} new entries, {updated_entries} updates")
        return report
        
    except SQLAlchemyError as e:
        logger.error(f"Error generating cache usage report: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating cache usage report: {e}")
        raise 