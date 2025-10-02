"""
Admin Dashboard Routes

Provides administrative interfaces for:
- System health monitoring
- Cost tracking & projections
- Usage analytics
- Performance metrics
"""

import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func, and_

from app.models.models import (
    User, Song, AnalysisResult, AnalysisCache, LyricsCache, Playlist
)
from app.extensions import db
from app.utils.openai_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # TODO: Add proper admin role check when implemented
        # For now, check if user has admin flag or is first user
        if not getattr(current_user, 'is_admin', False) and current_user.id != 1:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Main admin dashboard page."""
    return render_template('admin/dashboard.html')


@admin_bp.route('/api/overview')
@admin_required
def api_overview():
    """Get system overview metrics."""
    try:
        # User stats
        total_users = User.query.count()
        active_users_30d = User.query.filter(
            User.last_active_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).count() if hasattr(User, 'last_active_at') else 0
        
        # Song stats
        total_songs = Song.query.count()
        total_analyses = AnalysisResult.query.count()
        
        # Cache stats
        cache_stats = AnalysisCache.get_cache_stats()
        total_cached = cache_stats['total_cached']
        cache_hit_rate = (total_cached / max(total_analyses, 1)) * 100 if total_analyses > 0 else 0
        
        # Lyrics cache
        total_lyrics_cached = LyricsCache.query.count()
        
        # Rate limiter metrics
        rate_limiter = get_rate_limiter()
        limiter_metrics = rate_limiter.get_metrics()
        
        # Recent activity (last 24h)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        analyses_24h = AnalysisResult.query.filter(
            AnalysisResult.analyzed_at >= yesterday
        ).count()
        
        return jsonify({
            'users': {
                'total': total_users,
                'active_30d': active_users_30d
            },
            'content': {
                'total_songs': total_songs,
                'total_analyses': total_analyses,
                'analyses_24h': analyses_24h
            },
            'cache': {
                'total_cached': total_cached,
                'cache_hit_rate': round(cache_hit_rate, 1),
                'lyrics_cached': total_lyrics_cached,
                'by_model_version': cache_stats['by_model_version']
            },
            'rate_limiter': limiter_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching overview metrics: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/costs')
@admin_required
def api_costs():
    """Get cost tracking and projections."""
    try:
        # Get time range from query params (default: last 30 days)
        days = int(request.args.get('days', 30))
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get analyses by day
        analyses_by_day = db.session.query(
            func.date(AnalysisResult.analyzed_at).label('date'),
            func.count(AnalysisResult.id).label('count')
        ).filter(
            AnalysisResult.analyzed_at >= start_date
        ).group_by(
            func.date(AnalysisResult.analyzed_at)
        ).order_by('date').all()
        
        # Calculate costs
        # GPT-4o-mini fine-tuned: $0.03/1K input tokens, $0.12/1K output tokens
        # Average: ~500 input tokens (lyrics), ~800 output tokens (analysis)
        INPUT_COST_PER_1K = 0.03
        OUTPUT_COST_PER_1K = 0.12
        AVG_INPUT_TOKENS = 500
        AVG_OUTPUT_TOKENS = 800
        
        COST_PER_ANALYSIS = (
            (AVG_INPUT_TOKENS / 1000 * INPUT_COST_PER_1K) +
            (AVG_OUTPUT_TOKENS / 1000 * OUTPUT_COST_PER_1K)
        )
        
        # Get cache stats
        cache_stats = AnalysisCache.get_cache_stats()
        total_cached = cache_stats['total_cached']
        total_analyses = AnalysisResult.query.count()
        
        # Calculate actual API calls (non-cached)
        api_calls = total_analyses - total_cached
        
        # Calculate costs
        total_cost = api_calls * COST_PER_ANALYSIS
        saved_by_cache = total_cached * COST_PER_ANALYSIS
        
        # Daily breakdown
        daily_costs = []
        for date, count in analyses_by_day:
            # Estimate cache hits (assume 80% after initial period)
            cache_hit_rate = 0.8 if total_cached > 100 else 0
            estimated_api_calls = count * (1 - cache_hit_rate)
            daily_cost = estimated_api_calls * COST_PER_ANALYSIS
            
            daily_costs.append({
                'date': date.isoformat(),
                'analyses': count,
                'estimated_cost': round(daily_cost, 4)
            })
        
        # Projections
        avg_daily_analyses = total_analyses / max(days, 1)
        projected_monthly_analyses = avg_daily_analyses * 30
        projected_monthly_cost = projected_monthly_analyses * COST_PER_ANALYSIS * (1 - 0.8)  # Assume 80% cache hit
        
        return jsonify({
            'summary': {
                'total_analyses': total_analyses,
                'api_calls': api_calls,
                'cached_analyses': total_cached,
                'total_cost': round(total_cost, 2),
                'saved_by_cache': round(saved_by_cache, 2),
                'cost_per_analysis': round(COST_PER_ANALYSIS, 4)
            },
            'daily_costs': daily_costs,
            'projections': {
                'avg_daily_analyses': round(avg_daily_analyses, 1),
                'projected_monthly_analyses': round(projected_monthly_analyses, 0),
                'projected_monthly_cost': round(projected_monthly_cost, 2)
            },
            'cache_performance': {
                'hit_rate': round((total_cached / max(total_analyses, 1)) * 100, 1),
                'by_model_version': cache_stats['by_model_version']
            }
        })
    except Exception as e:
        logger.error(f"Error fetching cost metrics: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/analytics')
@admin_required
def api_analytics():
    """Get usage analytics."""
    try:
        # Top analyzed songs
        top_songs = db.session.query(
            Song.title,
            Song.artist,
            func.count(AnalysisResult.id).label('analysis_count')
        ).join(Analysis).group_by(
            Song.id, Song.title, Song.artist
        ).order_by(
            func.count(AnalysisResult.id).desc()
        ).limit(10).all()
        
        # Verdict distribution
        verdict_dist = db.session.query(
            AnalysisResult.verdict,
            func.count(AnalysisResult.id).label('count')
        ).group_by(AnalysisResult.verdict).all()
        
        # Score distribution (by ranges)
        score_ranges = [
            ('0-20', 0, 20),
            ('21-40', 21, 40),
            ('41-60', 41, 60),
            ('61-80', 61, 80),
            ('81-100', 81, 100)
        ]
        
        score_dist = []
        for label, min_score, max_score in score_ranges:
            count = AnalysisResult.query.filter(
                and_(
                    AnalysisResult.score >= min_score,
                    AnalysisResult.score <= max_score
                )
            ).count()
            score_dist.append({'range': label, 'count': count})
        
        # Analysis frequency over time (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        analyses_by_day = db.session.query(
            func.date(AnalysisResult.analyzed_at).label('date'),
            func.count(AnalysisResult.id).label('count')
        ).filter(
            AnalysisResult.analyzed_at >= thirty_days_ago
        ).group_by(
            func.date(AnalysisResult.analyzed_at)
        ).order_by('date').all()
        
        return jsonify({
            'top_songs': [
                {
                    'title': title,
                    'artist': artist,
                    'analysis_count': count
                }
                for title, artist, count in top_songs
            ],
            'verdict_distribution': [
                {'verdict': verdict, 'count': count}
                for verdict, count in verdict_dist
            ],
            'score_distribution': score_dist,
            'analysis_frequency': [
                {
                    'date': date.isoformat(),
                    'count': count
                }
                for date, count in analyses_by_day
            ]
        })
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/health')
@admin_required
def api_health():
    """Get system health metrics."""
    try:
        # Database health
        try:
            db.session.execute('SELECT 1')
            db_healthy = True
            db_message = 'Connected'
        except Exception as e:
            db_healthy = False
            db_message = str(e)
        
        # Rate limiter health
        rate_limiter = get_rate_limiter()
        limiter_metrics = rate_limiter.get_metrics()
        limiter_healthy = limiter_metrics['capacity_percent'] < 80
        
        # Cache health
        cache_stats = AnalysisCache.get_cache_stats()
        cache_healthy = cache_stats['total_cached'] > 0
        
        # Overall health
        overall_healthy = db_healthy and limiter_healthy
        
        return jsonify({
            'overall': {
                'status': 'healthy' if overall_healthy else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'components': {
                'database': {
                    'status': 'healthy' if db_healthy else 'unhealthy',
                    'message': db_message
                },
                'rate_limiter': {
                    'status': 'healthy' if limiter_healthy else 'warning',
                    'metrics': limiter_metrics
                },
                'cache': {
                    'status': 'healthy' if cache_healthy else 'warning',
                    'total_cached': cache_stats['total_cached']
                }
            }
        })
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/costs')
@admin_required
def costs_page():
    """Cost tracking page."""
    return render_template('admin/costs.html')


@admin_bp.route('/analytics')
@admin_required
def analytics_page():
    """Analytics page."""
    return render_template('admin/analytics.html')


@admin_bp.route('/health')
@admin_required
def health_page():
    """System health page."""
    return render_template('admin/health.html')

